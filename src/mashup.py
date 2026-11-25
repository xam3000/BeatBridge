"""Export a sequence of original-track sections and beat-aligned baseline transitions."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from uuid import uuid4

import librosa
import numpy as np
import soundfile as sf

from src.analysis.models import unpack_analysis_result
from src.analysis.pre_analysis import PartialPreAnalysis, PreAnalysis, ensure_bar_metadata_with_provenance
from src.candidates.variable import validate_baseline_cue
from src.pipeline import BeatBridgePipeline, DEFAULT_SAMPLE_RATE, build_cutter
from src.tempo.cue_alignment import measure_cue_alignment, require_observed_grid
from src.tempo.time_stretch import TimeStretch


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _sample(seconds, rate, limit):
    if not np.isfinite(seconds) or seconds < 0:
        raise ValueError("Zeitangaben müssen endlich und nichtnegativ sein.")
    sample = round(seconds * rate)
    if sample > limit:
        raise ValueError("Zeitangabe liegt hinter dem Trackende.")
    return sample


@dataclass
class _Track:
    audio: np.ndarray
    frames: list
    start: int
    end: int
    info: dict

    @classmethod
    def load(cls, section, analysis, rate):
        path = Path(section["path"])
        identity = digest(path)
        if section.get("sha256", identity) != identity:
            raise ValueError(f"Geänderte Quelldatei: {path}")
        audio, native_rate = librosa.load(path, sr=None, mono=False)
        bpm, frames, grid = unpack_analysis_result(analysis(str(path)))
        frames, grid = ensure_bar_metadata_with_provenance(
            frames, bpm=bpm, sample_count=audio.shape[-1], sample_rate=native_rate, existing_metadata=grid)
        require_observed_grid(grid)
        if native_rate != rate:
            audio = librosa.resample(audio, orig_sr=native_rate, target_sr=rate, axis=-1)
        audio = BeatBridgePipeline._normalise_channels(audio, 2)
        frames = BeatBridgePipeline._scale_beat_frames(frames, rate / native_rate)
        size = audio.shape[-1]
        start = _sample(section.get("start_seconds", 0), rate, size)
        end = size if section.get("end_seconds") is None else _sample(section["end_seconds"], rate, size)
        if start >= end:
            raise ValueError(f"Leerer Songabschnitt: {path}")
        info = dict(path=path.as_posix(), sha256=identity, native_rate=native_rate, bpm=float(bpm),
                    grid=grid.to_dict(), original_section=[start, end], original_samples=size,
                    tempo_factor=1.0, backend="not_needed")
        return cls(audio, frames, start, end, info)

    def stretch(self, factor, adjuster, rate):
        if np.isclose(factor, 1.0):
            return
        self.audio = adjuster.adjust_tempo_by_factor(self.audio, rate, factor)
        self.frames = BeatBridgePipeline._scale_beat_frames(self.frames, 1 / factor)
        self.start, self.end = round(self.start / factor), round(self.end / factor)
        self.info.update(tempo_factor=factor, backend=adjuster.last_backend)

    def requested_cue(self, seconds, rate):
        native = _sample(seconds, rate, self.info["original_samples"])
        left, right = self.info["original_section"]
        if not left <= native <= right:
            raise ValueError("Cue liegt außerhalb des gewählten Songabschnitts.")
        return round(native / self.info["tempo_factor"])


def _write_sections(plan, analysis, rate, adjuster, stream):
    sections, edges = plan["sections"], plan["edges"]
    if plan.get("format_version") != 1 or len(sections) < 2 or len(edges) != len(sections) - 1:
        raise ValueError("Jedes benachbarte Songpaar braucht genau einen Übergang.")
    a = _Track.load(sections[0], analysis, rate)
    cursor = a.start
    tracks, transitions = [a.info], []
    for index, (section, edge) in enumerate(zip(sections[1:], edges, strict=True)):
        b = _Track.load(section, analysis, rate)
        bars, renderer = edge["bars"], edge["renderer"]
        if type(bars) is not int or not 1 <= bars <= 4 or renderer not in ("simple", "fade", "equal_power"):
            raise ValueError("Für den Sequenzexport eine Baseline und ein bis vier Takte auswählen.")
        beats = bars * 4
        cutter = build_cutter(renderer, fade_beats=beats)
        s, t = cutter.resolve_cut_samples(a.audio, b.audio, a.requested_cue(edge["source_seconds"], rate),
                                         b.requested_cue(edge["target_seconds"], rate), a.frames, b.frames)
        validate_baseline_cue(a.frames, s, bars, a.audio.shape[-1], "source")
        validate_baseline_cue(b.frames, t, bars, b.audio.shape[-1], "target")
        i = next(i for i, f in enumerate(a.frames) if f[0] == s)
        j = next(j for j, f in enumerate(b.frames) if f[0] == t)
        alignment = measure_cue_alignment(a.frames, b.frames, i, j, beats, rate)
        alignment.require_valid()
        # A is already on the sequence timeline. B is always read from its original.
        b.stretch(alignment.tempo_factor, adjuster, rate)
        t = b.frames[j][0]
        length = a.frames[i + beats][0] - s if renderer != "simple" else 0
        if not (cursor <= s <= s + length <= a.end and b.start <= t - length <= t <= b.end):
            raise ValueError(f"Songabschnitte bei Übergang {index + 1} sind zu kurz oder Cues überlappen.")
        solo_start = stream.tell()
        stream.write(a.audio[:, cursor:s].T)
        bridge_start = stream.tell()
        if length:
            fade_out, fade_in = cutter._build_envelopes(length)
            bridge = a.audio[:, s:s + length] * fade_out + b.audio[:, t - length:t] * fade_in
            stream.write(bridge.T)
        transitions.append(dict(index=index, renderer=renderer, bars=bars, source_beat=i, target_beat=j,
                                source_window=[s, s + length], target_window=[t - length, t],
                                solo_input=[cursor, s], solo_output=[solo_start, bridge_start],
                                bridge_output=[bridge_start, stream.tell()], alignment=alignment.to_dict()))
        tracks.append(b.info)
        a, cursor = b, t
    final_start = stream.tell()
    stream.write(a.audio[:, cursor:a.end].T)
    return dict(tracks=tracks, edges=transitions, final_input=[cursor, a.end],
                final_output=[final_start, stream.tell()], samples=stream.tell())


def export_mashup(plan, destination, analysis, *, sample_rate=DEFAULT_SAMPLE_RATE, tempo_adjuster=None):
    """Publish WAV and its manifest together in a new directory. Never replace an existing export."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.with_name(f".{destination.name}-{uuid4().hex}")
    stage.mkdir()
    try:
        work = stage / "mix.float.wav"
        with sf.SoundFile(work, "w", samplerate=sample_rate, channels=2, subtype="FLOAT") as stream:
            manifest = _write_sections(plan, analysis, sample_rate, tempo_adjuster or TimeStretch(), stream)
        if not manifest["samples"]:
            raise ValueError("Die gewählten Abschnitte ergeben eine leere Sequenz.")
        wav = stage / "mashup.wav"
        peak = 0.0
        with sf.SoundFile(work) as source:
            for block in source.blocks(blocksize=65536, dtype="float32"):
                if not np.isfinite(block).all():
                    raise ValueError("Die Sequenz enthält nicht endliche Samples.")
                peak = max(peak, float(np.abs(block).max()))
            gain = 1 / max(1.0, peak / (1 - 2**-23))
            source.seek(0)
            with sf.SoundFile(wav, "w", samplerate=sample_rate, channels=2, subtype="PCM_24") as output:
                for block in source.blocks(blocksize=65536, dtype="float32"):
                    output.write(block * gain)
        work.unlink()
        manifest.update(format_version=1, plan=plan, sample_rate=sample_rate,
                        file=wav.name, sha256=digest(wav), gain=gain, peak_before_gain=peak)
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                                                        allow_nan=False) + "\n", encoding="utf-8")
        stage.rename(destination)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--analysis-cache", type=Path, default=Path("output/pre_analysis"))
    parser.add_argument("--partial-grid", action="store_true", help="Use the Merge-v2 analysis cache.")
    args = parser.parse_args()
    analyser = PartialPreAnalysis if args.partial_grid else PreAnalysis
    receipt = export_mashup(json.loads(args.plan.read_bytes()), args.output, analyser(args.analysis_cache))
    print(f"{args.output / receipt['file']} ({receipt['samples']} Samples)")
