"""Audit a completed P07 release against its inputs and artifact bytes."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import time

import numpy as np
import soundfile as sf

from src.features.extract_track import _write_json_atomic
from src.features.p07_audio import CLASSICAL_COLUMNS
from src.features.p07_extract import ROOT, cache_entry, grid_source, identity, read_json, variants_for
from src.features.p07_mert import (
    FRAME_STEP, HIDDEN_SIZE, LAYER_COUNT, RECEPTIVE_FIELD, SAMPLE_RATE, file_sha256,
    frame_centres_twice, model_identity,
)
from src.features.p07_population import development_population, validate_groups


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def verify(source):
    started = time.perf_counter()
    manifest_path = source / "manifest.json"
    manifest = read_json(manifest_path)
    rows = manifest["views"]
    validate_groups(rows)
    require(manifest["model"] == model_identity(), "Unexpected MERT version")
    require(tuple(manifest["classical_columns"]) == CLASSICAL_COLUMNS, "Invalid classical columns")
    tracks, denied, bindings = development_population()
    require(all(manifest[key] == value for key, value in bindings.items()), "Split binding mismatch")
    selected = {row["sha256"]: row for track in tracks if (row := grid_source(track)) is not None}
    deny_shas = {track["sha256"] for track in denied}
    observed = defaultdict(list)
    for row in rows:
        observed[row["sha256"]].append(row)
    omitted = {row["sha256"] for row in manifest["exclusions"]}
    require(not set(observed) & omitted, "An excluded track is cached")
    require(deny_shas <= omitted, "Missing recorded test exclusions")
    if not manifest["resources"]["smoke"]:
        require(set(selected) <= set(observed) | omitted, "Incomplete September export")
        require(set(observed) | omitted == {r["sha256"] for r in tracks + denied},
                "Selected and excluded tracks must cover all September candidates")

    scale_root = source / "standardized" / manifest["scaler_id"]
    scaler = read_json(scale_root / "scaler.json")
    require(identity(scaler) == manifest["scaler_id"], "Classical scaler identity mismatch")
    mean, scale = np.asarray(scaler["mean"]), np.asarray(scaler["scale"])
    training = {}
    bar_totals = Counter()
    frame_counts = []
    for digest, views in observed.items():
        track = selected[digest]
        split = track["split"]
        require(sorted(row["variant"] for row in views) == sorted(variants_for(split)),
                f"Wrong view set: {digest}")
        require(file_sha256(track["path"]) == digest, f"Changed original: {digest}")
        header = sf.info(track["path"])
        grid = read_json(Path(track["analysis_path"]))["result"]["beat_frames"]
        native = np.asarray(grid, dtype=np.int64)
        expected_audio_samples = round(header.frames * SAMPLE_RATE / header.samplerate)
        shared = None
        for row in views:
            key = row["cache_id"]
            entry_path = source / row["entry"]
            entry = read_json(entry_path)
            spec = entry["spec"]
            require(spec["track"] == track and row["variant"] == spec["variant"] and row["split"] == split,
                    f"View disagrees with the original identity: {key}")
            require(row["recording_group_id"] == track["recording_group_id"], f"View group changed: {key}")
            require(identity(spec) == key == entry["cache_id"] == entry_path.parent.name, f"Cache ID: {key}")
            require(entry["sha256"] == row["sha256_files"] and cache_entry(entry_path.parent, spec),
                    f"Cache integrity failed: {key}")
            size = entry["samples"]
            require(abs(size - expected_audio_samples) <= 1, f"Audio length mismatch: {key}")
            with np.load(entry_path.parent / "bars.npz", allow_pickle=False) as archive:
                bars = archive["bar_boundaries_24k"]
                starts = archive["bar_start_beat_index"]
                counts = archive["mert_frame_count"]
                mert = archive["mert"]
                classical = archive["classical_raw"]
            length = len(starts)
            require(length == row["bar_count"] == entry["bar_count"], f"Bar count mismatch: {key}")
            require(np.all(np.diff(bars, axis=1) > 0) and np.all(bars[1:, 0] >= bars[:-1, -1]),
                    f"Invalid bar order: {key}")
            require(bars[0, 0] >= 0 and bars[-1, -1] <= size, f"Bar outside audio: {key}")
            selected_beats = native[starts[:, None] + np.arange(5)]
            expected = np.rint(selected_beats[:, :, 0] * (SAMPLE_RATE / header.samplerate))
            np.testing.assert_array_equal(selected_beats[:, :, 1], np.broadcast_to([1, 2, 3, 4, 1], expected.shape))
            np.testing.assert_array_equal(bars[:, ::2], expected)
            np.testing.assert_array_equal(bars[:, 1::2], np.rint((expected[:, :-1] + expected[:, 1:]) / 2))
            centres = frame_centres_twice(0, 1 + (size - RECEPTIVE_FIELD) // FRAME_STEP)
            expected_counts = np.searchsorted(centres, 2 * bars[:, -1]) - np.searchsorted(centres, 2 * bars[:, 0])
            np.testing.assert_array_equal(counts, expected_counts)
            if shared is None:
                shared = bars
            np.testing.assert_array_equal(bars, shared)
            require(mert.dtype == np.float32 and mert.shape == (length, LAYER_COUNT, HIDDEN_SIZE)
                    and np.isfinite(mert).all(), f"Invalid MERT tensor: {key}")
            require(classical.dtype == np.float32 and classical.shape == (length, len(CLASSICAL_COLUMNS))
                    and np.isfinite(classical).all(), f"Invalid classical tensor: {key}")
            scaled = source / row["classical_scaled"]
            require(scaled.parent == scale_root and file_sha256(scaled) == row["classical_scaled_sha256"],
                    f"Standardized file checksum: {key}")
            with np.load(scaled, allow_pickle=False) as archive:
                np.testing.assert_array_equal(archive["classical"], ((classical - mean) / scale).astype(np.float32))
            if row["variant"] != "original":
                aug = sf.info(entry_path.parent / "view.wav")
                require((aug.frames, aug.channels, aug.samplerate, aug.subtype) == (size, 1, SAMPLE_RATE, "FLOAT"),
                        f"Augmentation header mismatch: {key}")
                require(entry["applied_gain_db"] <= spec["production"]["gain_db"], f"Unexpected gain: {key}")
            elif split == "train":
                training[key] = classical
            frame_counts.extend((int(counts.min()), int(counts.max())))
            bar_totals[f"{split}/{row['variant']}"] += length

    keys = scaler["training_entries"]
    require(len(keys) == len(training) and set(keys) == training.keys(), "Training scaler membership mismatch")
    train = np.concatenate([training[key] for key in keys]).astype(np.float64)
    require(len(train) == scaler["bars"], "Scaler training bar count mismatch")
    np.testing.assert_array_equal(train.mean(axis=0), mean, strict=True)
    expected_scale = train.std(axis=0)
    expected_scale[expected_scale < 1e-8] = 1.0
    np.testing.assert_array_equal(expected_scale, scale, strict=True)

    counts = dict(Counter(f'{row["split"]}/{row["variant"]}' for row in rows))
    require(manifest["counts"] == counts, "Manifest count mismatch")
    groups = {split: len({row["recording_group_id"] for row in rows if row["split"] == split})
              for split in ("train", "validation")}
    return dict(
        format_version=1, result="passed", manifest=manifest_path.as_posix(),
        manifest_sha256=file_sha256(manifest_path),
        **bindings, model=manifest["model"], counts=counts, recording_groups=groups,
        bars=dict(bar_totals), mert_frames_per_bar=[min(frame_counts), max(frame_counts)],
        scaler_id=manifest["scaler_id"], training_bars=scaler["bars"],
        exclusions=dict(Counter(reason for row in manifest["exclusions"] for reason in row["reasons"])),
        cache_file_bytes=sum(path.stat().st_size for path in source.rglob("*") if path.is_file()),
        extraction=manifest["resources"], verification_seconds=time.perf_counter() - started,
    )


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "full")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    result = verify(args.source)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(args.receipt, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
