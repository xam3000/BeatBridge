"""Materialize the P07 bar cache from original, split-authorized recordings."""

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from filelock import FileLock
import numpy as np
import psutil
import soundfile as sf
import soxr

from src.analysis.pre_analysis import _beat_grid_sha256
from src.features.extract_track import _write_json_atomic, _write_npz_atomic
from src.features.p07_audio import (
    CHANNELS, CLASSICAL_COLUMNS, PRODUCTION_VIEWS, ROOM, bar_geometry, classical_bars,
    production_view,
)
from src.features.p07_mert import (
    FrozenMert, HIDDEN_SIZE, LAYER_COUNT, SAMPLE_RATE, file_sha256, model_identity,
)
from src.features.p07_population import development_population, validate_groups
from src.features.vocal import (
    DEFAULT_ROFORMER_MODEL, _load_cached_vocal, extract_or_load_roformer_vocal_stem,
)


ROOT = Path("output/review_jp_20261118/p07")
ANALYSIS = Path("output/pre_analysis/prive_scantraxx_extension_merge_v2_20260923_run01/v2")
FEATURE_ROOTS = tuple(Path("output") / name for name in (
    "feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run02_local_four_four",
    "feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run01",
    "feature_cache_variable_v2_roformer_20260821",
    "feature_cache_prive_scantraxx_extension_fp2_roformer_smoke_20260924_run01",
    "four_model_shared_feature_cache_20260927",
))
VOCAL_CONTRACT = {
    "backend": "roformer",
    "backend_version": 1,
    "model_name": DEFAULT_ROFORMER_MODEL,
    "bs_roformer_infer_version": "0.1.1",
}
VOCAL_WEIGHTS = {
    "sha256": "24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e",
    "config_sha256": "52df622c95ff3c1f4e1389f476ed737581a2c2dc12324d52c9763be9ccd2be2b",
}


def read_json(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def grid_source(track):
    for source in sorted((ANALYSIS / track["sha256"]).glob("*/analysis.json")):
        analysis = read_json(source)
        result = analysis["result"]
        metadata = result["grid_metadata"]
        if metadata["fallback_used"] is not False:
            continue
        if metadata["grid_source"] != "auftakt_matched_to_librosa_partial_v2":
            continue
        if analysis["source_audio"]["sha256"] != track["sha256"] or (
            metadata["beat_grid_sha256"] != _beat_grid_sha256(result["beat_frames"])
        ):
            raise ValueError(f"Corrupt grid {source}")
        return {**track, "analysis_path": source.as_posix(), "analysis_sha256": file_sha256(source),
                "grid": metadata, "bpm": result["bpm"]}
    return None


def variants_for(split):
    return tuple(PRODUCTION_VIEWS) if split == "train" else ("original",)


def stem_directories(roots, digest):
    for root in roots:
        stem_root = root / "model_artifacts" / "roformer_vocal_v1" / digest[:16]
        yield from sorted(stem_root.glob("*/manifest.json"))


def load_stem(track, destination):
    digest = track["sha256"]
    expected = {**VOCAL_CONTRACT, "source_sha256": digest}
    for path in stem_directories((*FEATURE_ROOTS, destination), digest):
        provenance = read_json(path)
        if any(provenance["weights"][key] != value for key, value in VOCAL_WEIGHTS.items()):
            continue
        cached = _load_cached_vocal(path.parent, expected)
        if cached is not None:
            return cached

    # Supply the same historical model assets locally for new separation.
    import shutil

    model_path = Path("model_artifacts") / "roformer_models" / DEFAULT_ROFORMER_MODEL
    target = destination / model_path
    target.mkdir(parents=True, exist_ok=True)
    for name, digest_key in (("BS-Rofo-SW-Fixed.ckpt", "sha256"), ("BS-Rofo-SW-Fixed.yaml", "config_sha256")):
        asset = target / name
        if asset.is_file() and file_sha256(asset) == VOCAL_WEIGHTS[digest_key]:
            continue
        temporary = target / f"{name}.incomplete"
        shutil.copyfile(FEATURE_ROOTS[0] / model_path / name, temporary)
        if file_sha256(temporary) != VOCAL_WEIGHTS[digest_key]:
            raise ValueError(f"RoFormer asset mismatch: {name}")
        temporary.replace(asset)
    return extract_or_load_roformer_vocal_stem(
        track["path"], cache_root=destination, source_sha256=digest, device="cuda"
    )


def prepare_audio(track):
    path = Path(track["path"])
    if file_sha256(path) != track["sha256"]:
        raise ValueError(f"Original audio SHA-256 mismatch for {path}")
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1, dtype=np.float32)
    if rate != SAMPLE_RATE:
        audio = soxr.resample(audio, rate, SAMPLE_RATE, quality="HQ")
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Original waveform is empty or non-finite")
    grid_path = Path(track["analysis_path"])
    if file_sha256(grid_path) != track["analysis_sha256"]:
        raise ValueError(f"Grid changed after selection: {grid_path}")
    native = np.asarray(read_json(grid_path)["result"]["beat_frames"], dtype=np.int64)
    frames = native.copy()
    frames[:, 0] = np.rint(frames[:, 0] * (SAMPLE_RATE / rate))
    starts, bars = bar_geometry(frames, len(audio))
    return audio, frames, starts, bars


def align_stem(stem, size):
    vocal = stem.audio
    if stem.sample_rate != SAMPLE_RATE:
        vocal = soxr.resample(vocal, stem.sample_rate, SAMPLE_RATE, quality="HQ")
    return np.pad(vocal[:size], (0, max(0, size - len(vocal))))


def cache_entry(directory, spec):
    path = directory / "entry.json"
    if not path.is_file():
        return None
    try:
        entry = read_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(entry, dict) or canonical(entry.get("spec")) != canonical(spec):
        return None
    expected_files = {"bars.npz"} if spec["variant"] == "original" else {"bars.npz", "view.wav"}
    if not isinstance(entry.get("sha256"), dict) or set(entry["sha256"]) != expected_files:
        return None
    for name, expected in entry["sha256"].items():
        artifact = directory / name
        if not artifact.is_file() or file_sha256(artifact) != expected:
            return None
    return entry


def materialize(track, destination, model, runtime, prepared):
    audio, frames, starts, bars = prepared
    if not bars.size:
        return []
    stem = load_stem(track, destination)
    vocal = align_stem(stem, len(audio))
    output = []
    for variant in variants_for(track["split"]):
        started = time.perf_counter()
        params = PRODUCTION_VIEWS[variant]
        spec = dict(format_version=1, track=track, variant=variant, production=params,
                    room=ROOM, model=model_identity(), runtime=runtime, classical_columns=CLASSICAL_COLUMNS,
                    vocal_sha256=stem.manifest["artifact_sha256"], vocal_weights=VOCAL_WEIGHTS,
                    geometry="detected_complete_four_four_half_beats_v1")
        key = identity(spec)
        directory = destination / "cache" / track["sha256"] / key
        entry = cache_entry(directory, spec)
        hit = entry is not None
        if not hit:
            directory.mkdir(parents=True, exist_ok=True)
            mix, voice, gain = production_view(audio, vocal, params)
            classic = classical_bars(mix, voice, frames, bars)
            mert, counts = model.encode(mix, bars)
            if classic.shape != (len(bars), len(CLASSICAL_COLUMNS)) or (
                mert.shape != (len(bars), LAYER_COUNT, HIDDEN_SIZE)
            ) or not (np.isfinite(classic).all() and np.isfinite(mert).all()):
                raise ValueError("Invalid representation shape or non-finite values")
            _write_npz_atomic(directory / "bars.npz", classical_raw=classic, mert=mert,
                              mert_frame_count=counts, bar_boundaries_24k=bars,
                              bar_start_beat_index=starts)
            digests = {"bars.npz": file_sha256(directory / "bars.npz")}
            if params is not None:
                temp = directory / "view.incomplete.wav"
                sf.write(temp, mix, SAMPLE_RATE, subtype="FLOAT")
                temp.replace(directory / "view.wav")
                digests["view.wav"] = file_sha256(directory / "view.wav")
            entry = dict(spec=spec, cache_id=key, sha256=digests, bar_count=len(bars),
                         samples=len(audio), applied_gain_db=gain, seconds=time.perf_counter() - started)
            _write_json_atomic(directory / "entry.json", entry)
        output.append({**track, "variant": variant, "cache_id": key, "bar_count": entry["bar_count"],
                       "entry": (directory / "entry.json").relative_to(destination).as_posix(),
                       "sha256_files": entry["sha256"], "cache_hit": hit})
    return output


def fit_scaler(rows, destination):
    train = [row for row in rows if row["split"] == "train" and row["variant"] == "original"]
    if not train:
        raise ValueError("Training originals are required to fit the classical scaler")
    arrays = [load_classical(destination / row["entry"]).astype(np.float64) for row in train]
    values = np.concatenate(arrays)
    center, scale = values.mean(axis=0), values.std(axis=0)
    scale[scale < 1e-8] = 1.0
    return dict(format_version=1, split="train", variant="original",
                columns=CLASSICAL_COLUMNS, bars=len(values),
                training_entries=[row["cache_id"] for row in train],
                mean=center.tolist(), scale=scale.tolist())


def load_classical(entry_path):
    with np.load(entry_path.parent / "bars.npz", allow_pickle=False) as data:
        return data["classical_raw"]


def write_index(destination, rows, excluded, bindings, resources):
    validate_groups(rows)
    scaler = fit_scaler(rows, destination)
    scaler_id = identity(scaler)
    scale_root = destination / "standardized" / scaler_id
    scale_root.mkdir(parents=True, exist_ok=True)
    mean, scale = np.asarray(scaler["mean"]), np.asarray(scaler["scale"])
    for row in rows:
        path = scale_root / f'{row["cache_id"]}.npz'
        values = load_classical(destination / row["entry"])
        _write_npz_atomic(path, classical=((values - mean) / scale).astype(np.float32))
        row["classical_scaled"] = path.relative_to(destination).as_posix()
        row["classical_scaled_sha256"] = file_sha256(path)
    _write_json_atomic(scale_root / "scaler.json", scaler)
    _write_json_atomic(destination / "manifest.json", dict(
        format_version=1, **bindings, model=model_identity(), channels=CHANNELS,
        classical_columns=CLASSICAL_COLUMNS, scaler_id=scaler_id,
        counts=dict(Counter(f'{row["split"]}/{row["variant"]}' for row in rows)),
        resources=resources, views=rows, exclusions=excluded,
    ))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "full")
    parser.add_argument("--model", type=Path, default=ROOT / "model")
    parser.add_argument("--smoke", action="store_true", help="One train original and its two variants")
    args = parser.parse_args(argv)
    tracks, excluded, bindings = development_population()
    selected = []
    for track in tracks:
        row = grid_source(track)
        if row is None:
            excluded.append({**track, "reasons": ["no_verified_september_partial_grid"]})
        else:
            selected.append(row)
    if args.smoke:
        selected = [next(row for row in selected if row["split"] == "train"
                         and any(stem_directories(FEATURE_ROOTS, row["sha256"])))]
    print(f"P07 selected {dict(Counter(row['split'] for row in selected))}", flush=True)
    destination = args.output
    destination.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination / ".extract.lock"), timeout=0):
        run(selected, excluded, bindings, destination, args.model, args.smoke)


def run(selected, excluded, bindings, destination, model_path, smoke):
    import torch

    started = time.perf_counter()
    torch.set_num_threads(4)
    runtime = {name: importlib.metadata.version(name)
               for name in ("librosa", "numpy", "scipy", "soundfile", "soxr", "torch", "transformers")}
    runtime["cuda_device"] = torch.cuda.get_device_name()
    runtime["cuda_version"] = torch.version.cuda
    model = FrozenMert(model_path, "cuda")
    model_load = time.perf_counter() - started
    rows = []
    for index, track in enumerate(selected, 1):
        track_start = time.perf_counter()
        entries = materialize(track, destination, model, runtime, prepare_audio(track))
        if entries:
            rows.extend(entries)
        else:
            excluded.append({**track, "reasons": ["no_complete_four_four_bar"]})
        print(f"[{index}/{len(selected)}] {track['split']} {track['sha256'][:12]} "
              f"views={len(entries)} hits={sum(row['cache_hit'] for row in entries)} "
              f"seconds={time.perf_counter() - track_start:.2f}", flush=True)
    memory = psutil.Process().memory_info()
    resources = dict(
        wall_seconds=time.perf_counter() - started, model_load_seconds=model_load,
        process_peak_rss_bytes=getattr(memory, "peak_wset", memory.rss),
        cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        gpu=runtime["cuda_device"], smoke=smoke, software=runtime,
    )
    write_index(destination, rows, excluded, bindings, resources)
    print(canonical(resources), flush=True)


if __name__ == "__main__":
    main()
