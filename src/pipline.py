from pathlib import Path
import sys

import librosa
import soundfile as sf
import numpy as np

# Allow running this file directly via `python src/pipline.py`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.pre_analysis import PreAnalysis

output_folder="output/"
MUSIK_FOLDER = PROJECT_ROOT.parent / "musik"
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}

class BeatBridePipeline:
    def __init__(self, song1_name, song2_name):
        self.song1_name = song1_name
        self.song2_name = song2_name
        self.load_songs()

    def load_songs(self):
        # Code to load songs
        self.song1, self.sr1 = librosa.load(self.song1_name,sr=None,mono=False)
        self.song2, self.sr2 = librosa.load(self.song2_name,sr=None,mono=False)

    def combine_songs(self):
        # Code to combine songs
        # This is a placeholder for the actual combination logic
        self.combined_song = np.concatenate([self.song1, self.song2], axis=1)


    def save_combined_song(self, output_name):
        # Code to save the combined song
        sf.write(output_name, self.combined_song.T, self.sr1)

if __name__ == "__main__":
    #pipeline = BeatBridePipeline("../musik/HELP_LESS.mp3", "../musik/HELP_LESS.mp3")
    #pipeline.combine_songs()
    #pipeline.save_combined_song(output_folder + "combined_song.wav")
    for song_path in sorted(MUSIK_FOLDER.iterdir()):
        if song_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            continue

        pre_analysis = PreAnalysis(song_path, output_folder+"pre_analysis/")
        bpm, beat_frames = pre_analysis()
        #print(f"{song_path.name} BPM: {bpm}")
        #print(f"{song_path.name} Beat frames: {beat_frames}")
