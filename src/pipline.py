import argparse
from pathlib import Path
import sys

import librosa
import soundfile as sf
import numpy as np

from cutting.fade_cut import FadeCut
from cutting.simple_cut import SimpleCut

# Allow running this file directly via `python src/pipline.py`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.pre_analysis import PreAnalysis
from tempo.simple_tempo_adjust import SimpleTempoAdjust

output_folder="output/"
MUSIK_FOLDER = PROJECT_ROOT.parent / "musik"
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
CUTTERS = {
    "simple": SimpleCut,
    "fade": FadeCut,
}

class BeatBridePipeline:
    def __init__(self, song1_name, song2_name, analysis, tempo_adjuster, cutter):
        self.song1_name = song1_name
        self.song2_name = song2_name
        self.analysis = analysis
        self.tempo_adjuster = tempo_adjuster
        self.cutter = cutter
        self.load_songs()
        self.run_analysis()
   

    def load_songs(self):
        # Code to load songs
        self.song1, self.sr1 = librosa.load(self.song1_name,sr=None,mono=False)
        self.song2, self.sr2 = librosa.load(self.song2_name,sr=None,mono=False)

    def combine_songs(self):
        # Code to combine songs
        # This is a placeholder for the actual combination logic
        self.combined_song = np.concatenate([self.song1, self.song2], axis=1)


    def save__song(self, output_name, song, sr):
        # Code to save the combined song
        sf.write(output_name, song.T, sr)

    def run_analysis(self):
        # Code to run analysis
        self.bpm1, self.beat_frames1 = self.analysis(self.song1_name)
        self.bpm2, self.beat_frames2 = self.analysis(self.song2_name)

    def adjust_tempo(self):
        # Code to adjust tempo
        self.adjusted_song2 = self.tempo_adjuster.adjust_tempo_to_bpm(self.song2, self.sr2, self.bpm2, self.bpm1)
        return self.adjusted_song1, self.adjusted_song2
    
    def cut(self,sample1,sample2):
        # Code to cut songs
        self.cut_song = self.cutter.cut(self.song1, self.song2, sample1, sample2, self.beat_frames1, self.beat_frames2)
        return self.cut_song


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Create a cut between two songs.",
    )
    parser.add_argument("song1", help="Path to the first song file.")
    parser.add_argument("song2", help="Path to the second song file.")
    parser.add_argument("cutpoint1", type=int, help="Sample position in the first song.")
    parser.add_argument("cutpoint2", type=int, help="Sample position in the second song.")
    parser.add_argument(
        "cuttype",
        choices=sorted(CUTTERS),
        help="Type of cut to render.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(Path(output_folder) / "cut_song.wav"),
        help="Output file path.",
    )
    return parser


def build_cutter(cuttype):
    cutter_class = CUTTERS[cuttype]
    if cuttype == "fade":
        return cutter_class(align_bar=True, snap_to_down_beat=True)
    return cutter_class(align_bar=True, snap_to_down_beat=True)


def main():
    args = build_argument_parser().parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pre_analysis = PreAnalysis(output_folder + "pre_analysis/")
    tempo_adjuster = SimpleTempoAdjust()
    cutter = build_cutter(args.cuttype)

    pipeline = BeatBridePipeline(
        args.song1,
        args.song2,
        pre_analysis,
        tempo_adjuster,
        cutter,
    )
    cut_song = pipeline.cut(args.cutpoint1, args.cutpoint2)
    pipeline.save__song(str(output_path), cut_song, pipeline.sr1)
    print(f"Saved cut to {output_path}")

if __name__ == "__main__":
    main()
   
   
    #pipeline.combine_songs()
    #pipeline.save_combined_song(output_folder + "combined_song.wav")
    #for song_path in sorted(MUSIK_FOLDER.iterdir()):
    #    if song_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
    #        continue#

    #    pre_analysis = PreAnalysis(song_path, output_folder+"pre_analysis/")
    #    bpm, beat_frames = pre_analysis()
        #print(f"{song_path.name} BPM: {bpm}")
        #print(f"{song_path.name} Beat frames: {beat_frames}")
    
