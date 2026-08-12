import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import sys

import librosa
import numpy as np
import soundfile as sf


# Support both `python src/pipeline.py` and `from src.pipeline import ...`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.models import BeatGridMetadata, unpack_analysis_result
from src.analysis.pre_analysis import (
    PreAnalysis,
    ensure_bar_metadata_with_provenance,
)
from src.candidates import CandidateGenerationConfig, TrackReference
from src.candidates.generation import generate_candidates as generate_candidates_from_grids
from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.cutting.fade_cut import FadeCut
from src.cutting.simple_cut import SimpleCut
from src.tempo.time_stretch import TimeStretch


output_folder = "output/"
MUSIK_FOLDER = PROJECT_ROOT / "musik"
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
DEFAULT_SAMPLE_RATE = 44_100
DEFAULT_CHANNELS = 2
RENDER_RESULT_FORMAT_VERSION = 5
DEFAULT_PREVIEW_SECONDS_BEFORE = 5.0
DEFAULT_PREVIEW_SECONDS_AFTER = 12.0

CUTTERS = {
    "simple": SimpleCut,
    "fade": FadeCut,
    "equal_power": EqualPowerFadeCut,
    "tempo_fade": FadeCut,
}


@dataclass(frozen=True)
class RenderResult:
    """Stable return value for programmatic transition rendering."""

    audio: np.ndarray
    sample_rate: int
    renderer: str
    tempo_backend: str = "not_needed"
    transition_start_sample: int = 0
    transition_end_sample: int = 0
    format_version: int = RENDER_RESULT_FORMAT_VERSION
    source_grid: BeatGridMetadata | None = None
    target_grid: BeatGridMetadata | None = None


class BeatBridgePipeline:
    """Load, analyse, normalise, and render a transition between two tracks."""

    def __init__(
        self,
        song1_name,
        song2_name,
        analysis,
        tempo_adjuster,
        cutter,
        target_sample_rate=DEFAULT_SAMPLE_RATE,
        target_channels=DEFAULT_CHANNELS,
        bpm1=None,
        bpm2=None,
    ):
        if int(target_sample_rate) <= 0:
            raise ValueError("target_sample_rate must be greater than 0")
        if int(target_channels) not in {1, 2}:
            raise ValueError("target_channels must be 1 or 2")

        self.song1_name = str(song1_name)
        self.song2_name = str(song2_name)
        self.analysis = analysis
        self.tempo_adjuster = tempo_adjuster
        self.cutter = cutter
        self.target_sample_rate = int(target_sample_rate)
        self.target_channels = int(target_channels)
        self.bpm_override1 = None if bpm1 is None else float(bpm1)
        self.bpm_override2 = None if bpm2 is None else float(bpm2)
        self.tempo_backend = "not_needed"

        self.load_songs()
        self.run_analysis()
        self.normalise_tracks()

    def load_songs(self):
        self.song1, self.source_sr1 = librosa.load(
            self.song1_name,
            sr=None,
            mono=False,
        )
        self.song2, self.source_sr2 = librosa.load(
            self.song2_name,
            sr=None,
            mono=False,
        )

    def run_analysis(self):
        analysed_bpm1, self.beat_frames1, self.grid_metadata1 = unpack_analysis_result(
            self.analysis(self.song1_name)
        )
        analysed_bpm2, self.beat_frames2, self.grid_metadata2 = unpack_analysis_result(
            self.analysis(self.song2_name)
        )
        self.bpm1 = analysed_bpm1 if self.bpm_override1 is None else self.bpm_override1
        self.bpm2 = analysed_bpm2 if self.bpm_override2 is None else self.bpm_override2
        self.bpm1 = float(self.bpm1)
        self.bpm2 = float(self.bpm2)
        self.beat_frames1, self.grid_metadata1 = ensure_bar_metadata_with_provenance(
            self.beat_frames1,
            bpm=self.bpm1,
            sample_count=self.song1.shape[-1],
            sample_rate=self.source_sr1,
            existing_metadata=self.grid_metadata1,
        )
        self.beat_frames2, self.grid_metadata2 = ensure_bar_metadata_with_provenance(
            self.beat_frames2,
            bpm=self.bpm2,
            sample_count=self.song2.shape[-1],
            sample_rate=self.source_sr2,
            existing_metadata=self.grid_metadata2,
        )

    def normalise_tracks(self):
        self.song1, self.beat_frames1 = self._normalise_track(
            self.song1,
            self.source_sr1,
            self.beat_frames1,
        )
        self.song2, self.beat_frames2 = self._normalise_track(
            self.song2,
            self.source_sr2,
            self.beat_frames2,
        )
        self.sr1 = self.target_sample_rate
        self.sr2 = self.target_sample_rate

    def _normalise_track(self, audio, source_sample_rate, beat_frames):
        sample_scale = self.target_sample_rate / float(source_sample_rate)
        if source_sample_rate != self.target_sample_rate:
            audio = librosa.resample(
                np.asarray(audio),
                orig_sr=source_sample_rate,
                target_sr=self.target_sample_rate,
                axis=-1,
                res_type="soxr_hq",
            )

        audio = self._normalise_channels(audio, self.target_channels)
        beat_frames = self._scale_beat_frames(beat_frames, sample_scale)
        return audio.astype(np.float32, copy=False), beat_frames

    @staticmethod
    def _normalise_channels(audio, target_channels):
        audio = np.asarray(audio)
        if audio.ndim == 1:
            audio = audio[np.newaxis, :]
        if audio.ndim != 2:
            raise ValueError("audio must have shape (samples,) or (channels, samples)")

        source_channels = audio.shape[0]
        if source_channels == target_channels:
            return audio
        if source_channels == 1 and target_channels == 2:
            return np.repeat(audio, 2, axis=0)
        if source_channels == 2 and target_channels == 1:
            return np.mean(audio, axis=0, keepdims=True)
        raise ValueError(
            f"cannot normalise {source_channels} audio channels to {target_channels}"
        )

    @staticmethod
    def _scale_beat_frames(beat_frames, factor):
        if beat_frames is None:
            return None

        scaled = []
        for frame in beat_frames:
            if isinstance(frame, (tuple, list)):
                values = list(frame)
                values[0] = int(round(int(values[0]) * factor))
                scaled.append(tuple(values))
            else:
                scaled.append(int(round(int(frame) * factor)))
        return scaled

    def combine_songs(self):
        self.combined_song = np.concatenate([self.song1, self.song2], axis=-1)
        return self.combined_song

    def save_song(self, output_name, song, sample_rate=None):
        output_path = Path(output_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(
            str(output_path),
            np.asarray(song).T,
            self.target_sample_rate if sample_rate is None else int(sample_rate),
        )

    # Backwards-compatible alias for the original misspelled method.
    def save__song(self, output_name, song, sr):
        self.save_song(output_name, song, sr)

    def adjust_tempo(self):
        if hasattr(self, "adjusted_song2"):
            return self.adjusted_song1, self.adjusted_song2
        if self.bpm1 <= 0 or self.bpm2 <= 0:
            raise ValueError("Both BPM values must be greater than 0")

        tempo_factor = self.bpm1 / self.bpm2
        self.adjusted_song1 = self.song1
        if np.isclose(tempo_factor, 1.0):
            self.adjusted_song2 = self.song2
            self.adjusted_sample_scale2 = 1.0
            self.adjusted_beat_frames2 = self.beat_frames2
            self.tempo_backend = "not_needed"
            return self.adjusted_song1, self.adjusted_song2

        self.adjusted_song2 = self.tempo_adjuster.adjust_tempo_to_bpm(
            self.song2,
            self.target_sample_rate,
            self.bpm2,
            self.bpm1,
        )
        self.tempo_backend = (
            getattr(self.tempo_adjuster, "last_backend", None)
            or type(self.tempo_adjuster).__name__
        )
        self.adjusted_sample_scale2 = 1.0 / tempo_factor
        self.adjusted_beat_frames2 = self._scale_beat_frames(
            self.beat_frames2,
            self.adjusted_sample_scale2,
        )
        return self.adjusted_song1, self.adjusted_song2

    def cut(self, sample1, sample2, adjust_tempo=True):
        song1 = self.song1
        song2 = self.song2
        beat_frames2 = self.beat_frames2

        if adjust_tempo:
            song1, song2 = self.adjust_tempo()
            sample2 = int(round(int(sample2) * self.adjusted_sample_scale2))
            beat_frames2 = self.adjusted_beat_frames2

        self.cut_song = self.cutter.cut(
            song1,
            song2,
            sample1,
            sample2,
            self.beat_frames1,
            beat_frames2,
        )
        self.effective_source_cutpoint, self.effective_target_cutpoint = self.cutter.resolve_cut_samples(
            song1,
            song2,
            sample1,
            sample2,
            self.beat_frames1,
            beat_frames2,
        )
        return self.cut_song


def build_cutter(cuttype, fade_beats=8):
    if cuttype not in CUTTERS:
        raise ValueError(f"Unknown renderer: {cuttype}")

    common = {"align_bar": True, "snap_to_down_beat": True}
    if cuttype == "simple":
        return SimpleCut(**common)
    if cuttype == "equal_power":
        return EqualPowerFadeCut(fade_beats=fade_beats, **common)
    return FadeCut(fade_beats=fade_beats, **common)


def render_transition(
    song1,
    song2,
    cutpoint1,
    cutpoint2,
    renderer="fade",
    *,
    fade_beats=8,
    target_sample_rate=DEFAULT_SAMPLE_RATE,
    target_channels=DEFAULT_CHANNELS,
    analysis=None,
    analysis_location=None,
    tempo_adjuster=None,
    source_bpm=None,
    target_bpm=None,
    preview_seconds_before=DEFAULT_PREVIEW_SECONDS_BEFORE,
    preview_seconds_after=DEFAULT_PREVIEW_SECONDS_AFTER,
):
    """Render one transition and return audio plus stable metadata.

    Cutpoints are sample positions on the normalised target sample-rate grid.
    Song two is adjusted tonality-preservingly to song one's BPM before every
    renderer is applied. Optional BPM arguments make batch rendering use the
    BPM values recorded with its candidate instead of a second analysis result.
    By default the result is a short preview around the aligned source cutpoint.
    Pass ``None`` for both preview values to render the complete transition.
    """
    if analysis is None:
        cache_path = (
            Path(output_folder) / "pre_analysis"
            if analysis_location is None
            else Path(analysis_location)
        )
        analysis = PreAnalysis(str(cache_path) + os.sep)
    if tempo_adjuster is None:
        tempo_adjuster = TimeStretch()

    cutter = build_cutter(renderer, fade_beats=fade_beats)
    pipeline = BeatBridgePipeline(
        song1,
        song2,
        analysis,
        tempo_adjuster,
        cutter,
        target_sample_rate=target_sample_rate,
        target_channels=target_channels,
        bpm1=source_bpm,
        bpm2=target_bpm,
    )
    audio = pipeline.cut(
        cutpoint1,
        cutpoint2,
        adjust_tempo=True,
    )
    transition_start_sample = pipeline.effective_source_cutpoint
    transition_end_sample = transition_start_sample + int(
        getattr(cutter, "effective_transition_samples", 0)
    )
    audio, preview_start = _limit_to_preview(
        audio,
        pipeline.effective_source_cutpoint,
        pipeline.target_sample_rate,
        preview_seconds_before,
        preview_seconds_after,
    )
    return RenderResult(
        audio=audio,
        sample_rate=pipeline.target_sample_rate,
        renderer=renderer,
        tempo_backend=pipeline.tempo_backend,
        transition_start_sample=transition_start_sample - preview_start,
        transition_end_sample=transition_end_sample - preview_start,
        source_grid=pipeline.grid_metadata1,
        target_grid=pipeline.grid_metadata2,
    )


def generate_transition_candidates(
    song1,
    song2,
    *,
    analysis=None,
    analysis_location=None,
    target_sample_rate=DEFAULT_SAMPLE_RATE,
    config=None,
):
    """Generate bar-grid candidates on the same sample grid used by renderers.

    This is deliberately separate from rendering: the result is an auditable
    candidate set that the later batch-rendering and ranking stages consume.
    """
    if int(target_sample_rate) <= 0:
        raise ValueError("target_sample_rate must be greater than 0")
    if analysis is None:
        cache_path = (
            Path(output_folder) / "pre_analysis"
            if analysis_location is None
            else Path(analysis_location)
        )
        analysis = PreAnalysis(str(cache_path) + os.sep)
    if config is None:
        config = CandidateGenerationConfig()

    song1_path = Path(song1)
    song2_path = Path(song2)
    bpm1, beat_frames1, grid_metadata1 = unpack_analysis_result(
        analysis(str(song1_path))
    )
    bpm2, beat_frames2, grid_metadata2 = unpack_analysis_result(
        analysis(str(song2_path))
    )
    sample_rate1 = librosa.get_samplerate(str(song1_path))
    sample_rate2 = librosa.get_samplerate(str(song2_path))
    if sample_rate1 is None or sample_rate2 is None:
        raise ValueError("Could not determine an input track sample rate")

    info1 = sf.info(str(song1_path))
    info2 = sf.info(str(song2_path))
    beat_frames1, grid_metadata1 = ensure_bar_metadata_with_provenance(
        beat_frames1,
        bpm=bpm1,
        sample_count=info1.frames,
        sample_rate=sample_rate1,
        existing_metadata=grid_metadata1,
    )
    beat_frames2, grid_metadata2 = ensure_bar_metadata_with_provenance(
        beat_frames2,
        bpm=bpm2,
        sample_count=info2.frames,
        sample_rate=sample_rate2,
        existing_metadata=grid_metadata2,
    )
    beat_frames1 = BeatBridgePipeline._scale_beat_frames(
        beat_frames1,
        int(target_sample_rate) / float(sample_rate1),
    )
    beat_frames2 = BeatBridgePipeline._scale_beat_frames(
        beat_frames2,
        int(target_sample_rate) / float(sample_rate2),
    )
    return generate_candidates_from_grids(
        TrackReference(str(song1_path), _file_sha256(song1_path)),
        bpm1,
        beat_frames1,
        TrackReference(str(song2_path), _file_sha256(song2_path)),
        bpm2,
        beat_frames2,
        source_grid_metadata=grid_metadata1,
        target_grid_metadata=grid_metadata2,
        config=config,
    )


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as audio_file:
        for chunk in iter(lambda: audio_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _limit_to_preview(audio, cutpoint, sample_rate, seconds_before, seconds_after):
    if seconds_before is None and seconds_after is None:
        return audio, 0
    if seconds_before is None or seconds_after is None:
        raise ValueError("preview_seconds_before and preview_seconds_after must both be set or both be None")
    if seconds_before < 0 or seconds_after < 0:
        raise ValueError("Preview durations must be greater than or equal to 0")
    if seconds_before == 0 and seconds_after == 0:
        raise ValueError("Preview needs audio before or after the cutpoint")
    start = max(0, int(round(cutpoint - float(seconds_before) * sample_rate)))
    end = min(audio.shape[-1], int(round(cutpoint + float(seconds_after) * sample_rate)))
    if end <= start:
        raise ValueError("Preview window contains no rendered audio")
    return audio[..., start:end], start


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Create a bar-aligned transition between two songs.",
    )
    parser.add_argument("song1", help="Path to the first song file.")
    parser.add_argument("song2", help="Path to the second song file.")
    parser.add_argument(
        "cutpoint1",
        type=int,
        help="End of Drop A / start of source transition on the target sample-rate grid.",
    )
    parser.add_argument(
        "cutpoint2",
        type=int,
        help="End of target transition / start of Drop B on the target sample-rate grid.",
    )
    parser.add_argument(
        "cuttype",
        choices=sorted(CUTTERS),
        help="Transition renderer.",
    )
    parser.add_argument(
        "--fade-beats",
        type=int,
        default=8,
        help="Transition length in beats for fade renderers (default: 8).",
    )
    parser.add_argument(
        "--target-sample-rate",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"Internal/output sample rate (default: {DEFAULT_SAMPLE_RATE}).",
    )
    parser.add_argument(
        "--preview-before-seconds",
        type=float,
        default=DEFAULT_PREVIEW_SECONDS_BEFORE,
        help=f"Seconds to retain before the source cutpoint (default: {DEFAULT_PREVIEW_SECONDS_BEFORE:g}).",
    )
    parser.add_argument(
        "--preview-after-seconds",
        type=float,
        default=DEFAULT_PREVIEW_SECONDS_AFTER,
        help=f"Seconds to retain after the source cutpoint (default: {DEFAULT_PREVIEW_SECONDS_AFTER:g}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(Path(output_folder) / "cut_song.wav"),
        help="Output file path.",
    )
    return parser


def main():
    args = build_argument_parser().parse_args()
    result = render_transition(
        args.song1,
        args.song2,
        args.cutpoint1,
        args.cutpoint2,
        renderer=args.cuttype,
        fade_beats=args.fade_beats,
        target_sample_rate=args.target_sample_rate,
        preview_seconds_before=args.preview_before_seconds,
        preview_seconds_after=args.preview_after_seconds,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), result.audio.T, result.sample_rate)
    print(f"Saved {result.renderer} transition to {output_path}")


if __name__ == "__main__":
    main()
