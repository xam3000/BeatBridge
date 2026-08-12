from pathlib import Path
from dataclasses import replace
import hashlib
import json
import logging
import numpy as np
import os
import shutil
import subprocess
import uuid

import librosa

from .models import AnalysisResult, BeatGridMetadata

tmp_folder = Path("tmp/")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_BEAT_MATCH_DISTANCE_SECONDS = 0.2
FALLBACK_BEATS_PER_BAR = 4
logger = logging.getLogger(__name__)
# Legacy format-1 sidecar name. New cache entries use one authoritative JSON.
GRID_METADATA_FILENAME = "02_grid_metadata.json"
FALLBACK_BACKEND_VERSION = "beatbridge_4_4_fallback_v1"
ANALYSIS_CACHE_FORMAT_VERSION = 2
ANALYSIS_CACHE_NAMESPACE = "v2"
ANALYSIS_CACHE_FILENAME = "analysis.json"
ANALYSIS_ALGORITHM_VERSION = "beatbridge_pre_analysis_v2"
BEAT_BACKEND_NAME = "librosa.beat.beat_track"
BAR_BACKEND_NAME = "zplane_AUFTAKT_aufTAKTCl"
MERGE_ALGORITHM_VERSION = "librosa_auftakt_merge_v1"
AUFTAKT_EXECUTABLE_NAME = "aufTAKTCl.exe"


def ensure_bar_metadata(beat_frames, *, bpm=None, sample_count=None, sample_rate=None):
    """Return a complete 4/4 bar grid when beat frames lack bar metadata.

    The fallback preserves the detected beat positions and treats the first
    beat as a downbeat. If no beats were detected at all, it builds an evenly
    spaced grid from BPM. This is intentionally a usable fallback rather than
    a claim that the inferred downbeats are ground truth.
    """
    frames, _ = ensure_bar_metadata_with_provenance(
        beat_frames,
        bpm=bpm,
        sample_count=sample_count,
        sample_rate=sample_rate,
    )
    return frames


def ensure_bar_metadata_with_provenance(
    beat_frames,
    *,
    bpm=None,
    sample_count=None,
    sample_rate=None,
    existing_metadata=None,
):
    """Return a complete grid plus explicit detected/fallback provenance."""
    frames = [] if beat_frames is None else list(beat_frames)
    if _has_complete_bar_metadata(frames):
        metadata = existing_metadata or BeatGridMetadata(
            grid_source="external_unknown",
            fallback_used=None,
            backend_version=None,
            confidence=None,
        )
        return [tuple(int(value) for value in frame) for frame in frames], metadata

    samples = []
    for frame in frames:
        sample = int(frame[0]) if isinstance(frame, (tuple, list)) else int(frame)
        if sample < 0:
            raise ValueError("Beat samples must be greater than or equal to 0")
        if samples and sample <= samples[-1]:
            raise ValueError("Beat samples must be strictly increasing")
        samples.append(sample)

    grid_source = "fallback_from_detected_beats"
    if not samples:
        if bpm is None or float(bpm) <= 0:
            raise ValueError("Fallback beat grid requires detected beats or a BPM value greater than 0")
        if sample_count is None or sample_rate is None:
            raise ValueError("Fallback beat grid without detected beats requires sample_count and sample_rate")
        beat_samples = max(1, int(round(float(sample_rate) * 60.0 / float(bpm))))
        samples = list(range(0, int(sample_count), beat_samples))
        grid_source = "fallback_from_bpm"

    logger.warning(
        "Using 4/4 fallback bar metadata for %d beat positions; inferred downbeats are approximate.",
        len(samples),
    )
    grid = [
        (sample, index % FALLBACK_BEATS_PER_BAR + 1, FALLBACK_BEATS_PER_BAR)
        for index, sample in enumerate(samples)
    ]
    return grid, BeatGridMetadata(
        grid_source=grid_source,
        fallback_used=True,
        backend_version=f"{FALLBACK_BACKEND_VERSION};librosa={librosa.__version__}",
        confidence=0.0,
    )


def _has_complete_bar_metadata(beat_frames):
    if not beat_frames:
        return False
    previous_sample = -1
    for frame in beat_frames:
        if not isinstance(frame, (tuple, list)) or len(frame) != 3:
            return False
        sample, count_in_bar, beats_in_bar = (int(value) for value in frame)
        if (
            sample <= previous_sample
            or count_in_bar < 1
            or beats_in_bar < 1
            or count_in_bar > beats_in_bar
        ):
            return False
        previous_sample = sample
    return True


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _beat_grid_sha256(beat_frames):
    encoded = json.dumps(
        [[int(value) for value in frame] for frame in beat_frames],
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_auftakt_executable():
    project_executable = PROJECT_ROOT / AUFTAKT_EXECUTABLE_NAME
    if project_executable.is_file():
        return project_executable.resolve()
    executable = shutil.which(AUFTAKT_EXECUTABLE_NAME)
    return None if executable is None else Path(executable).resolve()


def _describe_auftakt_binary(executable):
    if executable is None:
        return {
            "name": BAR_BACKEND_NAME,
            "reported_version": None,
            "binary_sha256": None,
            "binary_size_bytes": None,
            "version_identity": "unavailable",
        }
    executable = Path(executable)
    return {
        "name": BAR_BACKEND_NAME,
        "reported_version": None,
        "binary_sha256": _file_sha256(executable),
        "binary_size_bytes": executable.stat().st_size,
        "version_identity": "sha256",
    }


def _analysis_config(auftakt_binary):
    return {
        "analysis_algorithm": ANALYSIS_ALGORITHM_VERSION,
        "beat_backend": {
            "name": BEAT_BACKEND_NAME,
            "library": "librosa",
            "library_version": librosa.__version__,
            "onset_strength_aggregate": "median",
            "beat_units": "samples",
        },
        "bar_backend": dict(auftakt_binary),
        "merge": {
            "algorithm": MERGE_ALGORITHM_VERSION,
            "maximum_match_distance_seconds": MAX_BEAT_MATCH_DISTANCE_SECONDS,
        },
        "fallback": {
            "algorithm": FALLBACK_BACKEND_VERSION,
            "beats_per_bar": FALLBACK_BEATS_PER_BAR,
        },
    }


def _analysis_id(config):
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


class PreAnalysis:
    def __init__(self,analysis_location):
        self.analysis_location = Path(analysis_location)
        self.missing_beats = {"librosa": [], "auftakt": []}
        self.auftakt_executable = _resolve_auftakt_executable()
        self.auftakt_binary = _describe_auftakt_binary(self.auftakt_executable)
        self.analysis_config = _analysis_config(self.auftakt_binary)
        self.analysis_id = _analysis_id(self.analysis_config)

    def __call__(self,song_path):
        self.song_path = Path(song_path)
        self.missing_beats = {"librosa": [], "auftakt": []}
        self.song_hash = _file_sha256(self.song_path)
        self.cache_directory = (
            self.analysis_location
            / ANALYSIS_CACHE_NAMESPACE
            / self.song_hash
            / self.analysis_id
        )
        self.grid_metadata = None
        self.previous_analysis = self.find_previous_analysis()
        if self.previous_analysis and self.load_previous_analysis():
            try:
                self.beat_frames, self.grid_metadata = ensure_bar_metadata_with_provenance(
                    self.beat_frames,
                    bpm=self.bpm,
                    existing_metadata=self.grid_metadata,
                )
            except ValueError:
                # An empty legacy cache has no usable beat positions; analyse again.
                self.previous_analysis = None
            else:
                self._finalize_grid_metadata()
                return self._result()
        # A stale or malformed cache must not affect provenance of a fresh run.
        self.previous_analysis_kind = None
        self.load_song()
        self.find_bpm()

        self.auftakt_analysis_comparison()
        self.beat_frames, self.grid_metadata = ensure_bar_metadata_with_provenance(
            self.beat_frames,
            bpm=self.bpm,
            sample_count=self.song.size,
            sample_rate=self.sr,
            existing_metadata=getattr(self, "grid_metadata", None),
        )
        self._finalize_grid_metadata()

        self.save_previous_analysis()
        
        return self._result()

    def _result(self):
        return AnalysisResult(
            bpm=float(self.bpm),
            beat_frames=tuple(tuple(int(value) for value in frame) for frame in self.beat_frames),
            grid_metadata=self.grid_metadata,
        )

    def _finalize_grid_metadata(self):
        analysis_id = self.analysis_id if self.previous_analysis_kind != "legacy" else None
        self.grid_metadata = replace(
            self.grid_metadata,
            analysis_id=analysis_id,
            beat_grid_sha256=_beat_grid_sha256(self.beat_frames),
        )

    def find_previous_analysis(self):
        current_path = self.cache_directory / ANALYSIS_CACHE_FILENAME
        if current_path.is_file():
            self.previous_analysis_kind = "current"
            return current_path

        legacy_path = self.analysis_location / self.song_path.stem / "00_pre_analysis.txt"
        if legacy_path.is_file():
            self.previous_analysis_kind = "legacy"
            return legacy_path

        self.previous_analysis_kind = None
        return None

    def load_previous_analysis(self):
        if self.previous_analysis_kind == "current":
            return self._load_current_analysis()
        if self.previous_analysis_kind == "legacy":
            return self._load_legacy_analysis()
        return False

    def _load_current_analysis(self):
        analysis_path = Path(self.previous_analysis)
        if not analysis_path.is_file():
            return False
        try:
            payload = json.loads(analysis_path.read_text(encoding="utf-8"))
            if (
                int(payload["format_version"]) != ANALYSIS_CACHE_FORMAT_VERSION
                or payload["analysis_id"] != self.analysis_id
                or payload["analysis_config"] != self.analysis_config
                or payload["source_audio"]["sha256"] != self.song_hash
            ):
                return False
            result = payload["result"]
            self.bpm = float(result["bpm"])
            if not np.isfinite(self.bpm) or self.bpm <= 0:
                return False
            self.beat_frames = [
                tuple(int(value) for value in frame)
                for frame in result["beat_frames"]
            ]
            if not _has_complete_bar_metadata(self.beat_frames):
                return False
            self.grid_metadata = BeatGridMetadata.from_dict(result["grid_metadata"])
            if (
                self.grid_metadata.analysis_id != self.analysis_id
                or self.grid_metadata.beat_grid_sha256
                != _beat_grid_sha256(self.beat_frames)
            ):
                return False
            self.missing_beats = payload.get(
                "diagnostics", {}
            ).get("missing_beats", {"librosa": [], "auftakt": []})
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False
        return True

    def _load_legacy_analysis(self):
        # Legacy: hash, BPM, then one comma-separated beat entry per line.
        analysis_path = Path(self.previous_analysis)
        if not analysis_path.is_file():
            return False
        try:
            analysis_lines = analysis_path.read_text(encoding="utf-8").splitlines()
            if analysis_lines[0] != self.song_hash:
                return False
            self.bpm = float(analysis_lines[1])
            self.beat_frames = [
                self._parse_saved_beat_line(line)
                for line in analysis_lines[2:]
                if line.strip()
            ]
            metadata_path = analysis_path.with_name(GRID_METADATA_FILENAME)
            if metadata_path.is_file():
                self.grid_metadata = BeatGridMetadata.from_dict(
                    json.loads(metadata_path.read_text(encoding="utf-8"))
                )
            else:
                self.grid_metadata = BeatGridMetadata(
                    grid_source="legacy_cache_unknown",
                    fallback_used=None,
                    backend_version=None,
                    confidence=None,
                )
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False
        return True

    def save_previous_analysis(self):
        analysis_path = self.cache_directory / ANALYSIS_CACHE_FILENAME
        payload = {
            "format_version": ANALYSIS_CACHE_FORMAT_VERSION,
            "analysis_id": self.analysis_id,
            "analysis_config": self.analysis_config,
            "source_audio": {
                "sha256": self.song_hash,
                "size_bytes": self.song_path.stat().st_size,
            },
            "result": {
                "bpm": float(self.bpm),
                "beat_frames": [
                    [int(value) for value in frame] for frame in self.beat_frames
                ],
                "grid_metadata": self.grid_metadata.to_dict(),
            },
            "diagnostics": {"missing_beats": self.missing_beats},
        }
        _write_json_atomic(analysis_path, payload)
        self.previous_analysis = analysis_path
        self.previous_analysis_kind = "current"

    def load_song(self):
        self.song, self.sr = librosa.load(self.song_path, sr=None, mono=True)

    def find_bpm(self):
        onset_env = librosa.onset.onset_strength(y=self.song, sr=self.sr,
                                         aggregate=np.median)
        self.bpm, self.beat_frames = librosa.beat.beat_track(y=self.song, sr=self.sr, units="samples",onset_envelope=onset_env)
        self.bpm = self.bpm[0] if isinstance(self.bpm, (list, np.ndarray)) else self.bpm

    def auftakt_analysis_comparison(self):
        tmp_folder.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        temp_wav_path = None
        auftakt_output_path = tmp_folder / f"auftakt-output-{token}.txt"
        try:
            # run auftakt
            if self.song_path.suffix.lower() != ".wav":
                temp_wav_path = tmp_folder / f"audio-{token}.wav"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(self.song_path), str(temp_wav_path)],
                    check=True,
                )
                song_to_analyze = temp_wav_path
            else:
                song_to_analyze = self.song_path

            command = [
                (
                    str(self.auftakt_executable)
                    if self.auftakt_executable is not None
                    else AUFTAKT_EXECUTABLE_NAME
                ),
                "-i",
                str(song_to_analyze),
                "-r",
                str(auftakt_output_path),
            ]
            subprocess.run(command, check=True)
            backend_version = self._auftakt_backend_version()

            auftakt_lines = auftakt_output_path.read_text().splitlines()[1:]
            auftakt_beats = []
            for line in auftakt_lines:
                if not line.strip():
                    continue

                time_seconds, count_in_bar, beats_in_bar = [part.strip() for part in line.split(",")]
                auftakt_beats.append((float(time_seconds), int(count_in_bar), int(beats_in_bar)))

            if auftakt_beats:
                auftakt_times = np.array([beat[0] for beat in auftakt_beats], dtype=float)
                librosa_times = librosa.samples_to_time(np.asarray(self.beat_frames), sr=self.sr)
                combined_beats = []
                matched_confidences = []
                matched_auftakt_indices = set()
                self.missing_beats = {"librosa": [], "auftakt": []}

                for sample, beat_time in zip(self.beat_frames, librosa_times):
                    closest_index, distance = self._find_closest_beat_index(auftakt_times, beat_time)
                    if distance > MAX_BEAT_MATCH_DISTANCE_SECONDS:
                        logger.warning(
                            "No matching aufTAKT beat for librosa beat at %.3fs (distance %.3fs)",
                            beat_time,
                            distance,
                        )
                        self.missing_beats["librosa"].append(
                            {
                                "sample": int(sample),
                                "time_seconds": float(beat_time),
                                "distance_seconds": float(distance),
                            }
                        )
                        combined_beats.append(int(sample))
                        continue

                    matched_auftakt_indices.add(closest_index)
                    matched_confidences.append(
                        max(0.0, 1.0 - distance / MAX_BEAT_MATCH_DISTANCE_SECONDS)
                    )
                    _, count_in_bar, beats_in_bar = auftakt_beats[closest_index]
                    combined_beats.append((int(sample), count_in_bar, beats_in_bar))

                for idx, auftakt_time in enumerate(auftakt_times):
                    closest_index, distance = self._find_closest_beat_index(librosa_times, auftakt_time)
                    if distance > MAX_BEAT_MATCH_DISTANCE_SECONDS or idx not in matched_auftakt_indices:
                        logger.warning(
                            "No matching librosa beat for aufTAKT beat at %.3fs (distance %.3fs, bar beat %s/%s)",
                            auftakt_time,
                            distance,
                            auftakt_beats[idx][1],
                            auftakt_beats[idx][2],
                        )
                        self.missing_beats["auftakt"].append(
                            {
                                "time_seconds": float(auftakt_time),
                                "count_in_bar": int(auftakt_beats[idx][1]),
                                "beats_in_bar": int(auftakt_beats[idx][2]),
                                "distance_seconds": float(distance),
                            }
                        )

                self.beat_frames = combined_beats
                if _has_complete_bar_metadata(combined_beats):
                    self.grid_metadata = BeatGridMetadata(
                        grid_source="auftakt_matched_to_librosa",
                        fallback_used=False,
                        backend_version=(
                            f"librosa={librosa.__version__};aufTAKTCl={backend_version}"
                        ),
                        confidence=float(np.mean(matched_confidences)),
                    )
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            logger.warning(
                "aufTAKT analysis failed for %s; falling back to inferred 4/4 bar metadata: %s",
                self.song_path,
                error,
            )
        finally:
            auftakt_output_path.unlink(missing_ok=True)
            if temp_wav_path is not None:
                temp_wav_path.unlink(missing_ok=True)

    def _auftakt_backend_version(self):
        binary_sha256 = self.auftakt_binary["binary_sha256"]
        if binary_sha256 is None:
            return "unavailable"
        return f"sha256:{binary_sha256}"

    @staticmethod
    def _parse_saved_beat_line(line):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 1:
            return int(parts[0])
        if len(parts) == 3:
            sample, count_in_bar, beats_in_bar = parts
            return int(sample), int(count_in_bar), int(beats_in_bar)
        raise ValueError(f"Invalid beat line: {line}")

    @staticmethod
    def _format_saved_beat_line(frame):
        if isinstance(frame, tuple):
            sample, count_in_bar, beats_in_bar = frame
            return f"{int(sample)},{int(count_in_bar)},{int(beats_in_bar)}"
        return str(int(frame))

    @staticmethod
    def _find_closest_beat_index(beat_times, target_time):
        insert_index = np.searchsorted(beat_times, target_time)
        candidate_indices = []
        if insert_index > 0:
            candidate_indices.append(insert_index - 1)
        if insert_index < len(beat_times):
            candidate_indices.append(insert_index)

        closest_index = min(
            candidate_indices,
            key=lambda idx: abs(float(beat_times[idx]) - target_time),
        )
        distance = abs(float(beat_times[closest_index]) - target_time)
        return closest_index, distance
