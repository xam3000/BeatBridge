"""Train P09's MERT heads on independent four-bar inputs and apply P10's selection."""

import argparse
import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from src.evaluation.mert_window_check import same_section_rows
from src.evaluation.p10_validation import control, decision, panel_scores, write_csv
from src.features.p07_extract import prepare_audio
from src.features.p07_mert import FrozenMert, SAMPLE_RATE, file_sha256, model_identity
from src.features.p08_pairs import OUTPUT, publish_dataset
from src.features.p08_windows import P07, checked, contiguous_starts, read_json
from src.ml.p08_contrastive import PairWindows
from src.ml.p09_train import run_head, save_json
from src.ml.p09_windows import WindowBank
from src.ranking.continuation import ISOLATED_METHOD, MODEL_DIR, SELECTION, encoder_runtime, load_head


class IsolatedCache:
    """Cache windows per immutable P07 production view. Verify bytes before reuse."""

    def __init__(self, root, data, encoder):
        self.root, self.data, self.encoder = root, data, encoder
        self.runtime = encoder_runtime()
        self.receipts = {}

    def __call__(self, sha, variant, requested):
        view = self.data.views[sha, variant]
        dest = self.root / view["cache_id"]
        binding = dict(view=view["cache_id"], method=ISOLATED_METHOD, runtime=self.runtime,
                       torch=str(torch.__version__), representation=model_identity())
        if not dest.exists():
            base = (self.data.root / view["entry"]).parent
            with np.load(checked(base / "bars.npz", view["sha256_files"]["bars.npz"])) as z:
                beats, bars = z["bar_start_beat_index"], z["bar_boundaries_24k"]
            if variant == "original":
                audio, _, native_beats, native_bars = prepare_audio(view)
                if not np.array_equal(beats, native_beats) or not np.array_equal(bars, native_bars):
                    raise ValueError("Frozen grid differs from native recording")
            else:
                audio, rate = sf.read(checked(base / "view.wav", view["sha256_files"]["view.wav"]),
                                      dtype="float32")
                if rate != SAMPLE_RATE or audio.ndim != 1:
                    raise ValueError("Unexpected P07 production audio format")
            starts = contiguous_starts(beats, bars, self.data.k)
            values = self.encoder.isolated_means(audio, bars, starts)
            if not np.isfinite(values).all():
                raise ValueError("Nonfinite isolated MERT values")
            with publish_dataset(dest) as stage:
                np.savez(stage / "means.npz", starts=starts, means=values)
                save_json(stage / "receipt.json", dict(binding=binding, windows=len(starts),
                                                       sha256=file_sha256(stage / "means.npz")))
        receipt = read_json(dest / "receipt.json")
        if receipt["binding"] != binding:
            raise ValueError(f"Isolated window cache contract differs at {dest}")
        self.receipts[view["cache_id"]] = file_sha256(dest / "receipt.json")
        with np.load(checked(dest / "means.npz", receipt["sha256"])) as z:
            starts = z["starts"]
            idx = np.searchsorted(starts, requested)
            if np.any(idx == len(starts)) or not np.array_equal(starts[idx], requested):
                raise ValueError("Missing isolated window")
            result = z["means"][idx]
        if len(self.receipts) % 20 == 0:
            print(self.data.split, len(self.receipts), "views", flush=True)
        return result


def train(output, cache):
    if output.exists():
        raise FileExistsError(output)
    # Keep every hyperparameter and every ordered P08 panel from the original run.
    old = read_json(SELECTION)
    config = read_json(checked(Path(old["run"]) / "config.json", old["config_sha256"]))
    runtime = encoder_runtime()
    config.update(format_version=2, input_encoding=ISOLATED_METHOD, representation=model_identity(),
                  device=runtime["device"], gpu=runtime["gpu"], torch_version=str(torch.__version__))
    encoder = FrozenMert(MODEL_DIR, runtime["device"])
    cache.mkdir(parents=True, exist_ok=True)
    datasets = [PairWindows(OUTPUT, P07, split, "mert", cache_tracks=1) for split in ("train", "validation")]
    if any(d.manifest["files"][d.split + ".jsonl"] != config["split_sha256"][d.split] for d in datasets):
        raise ValueError("Split differs from the P09 training contract")
    loaders = [IsolatedCache(cache, data, encoder) for data in datasets]
    val_data = datasets[1]
    training, validation = [WindowBank(d, d.rows, runtime["device"], window_means=loader)
                            for d, loader in zip(datasets, loaders, strict=True)]
    controls = same_section_rows(val_data, read_json(P07 / "manifest.json"))
    diagnostics = [dict(r, candidates=[*r["candidates"], (r["intro_drop_control"] or
                       {"candidate": r["positive"]})["candidate"]]) for r in val_data.rows]
    control_bank, same_bank = [WindowBank(val_data, rows, runtime["device"], window_means=loaders[1])
                               for rows in (diagnostics, controls)]
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / "cache.json", {d.split: loader.receipts for d, loader in zip(datasets, loaders, strict=True)})
    config["cache_sha256"] = file_sha256(output / "cache.json")
    save_json(output / "config.json", config)
    digest = file_sha256(output / "config.json")
    groups = np.array([r["group"] for r in val_data.rows])
    has_intro = np.array([r["intro_drop_control"] is not None for r in val_data.rows])
    same = [r["candidates"].index(r["same_control"]) for r in val_data.rows]
    idx = np.arange(len(val_data.rows))
    results = []
    for level in range(3):
        for seed in ([None] if level == 0 else config["model_seeds"]):
            row = run_head(output, "mert", level, seed, training, validation, config, False)
            model = load_head(row, output, digest).to(runtime["device"])
            scores = panel_scores(model, control_bank)
            pos = scores[idx, control_bank.truth]
            hard_scores = panel_scores(model, same_bank)
            hard_idx = np.arange(len(controls))
            row.update(same=control(pos, scores[idx, same], groups), same_groups=len(set(groups)),
                       intro_drop=control(pos[has_intro], scores[has_intro, 9], groups[has_intro]),
                       intro_drop_groups=len(set(groups[has_intro])), intro_drop_queries=int(has_intro.sum()),
                       same_section=control(hard_scores[hard_idx, same_bank.truth],
                                            hard_scores[hard_idx, 1 - same_bank.truth], [r["group"] for r in controls]),
                       same_section_queries=len(controls), queries=len(idx), recordings=len(set(validation.tracks)))
            results.append(row)
    write_csv(output / "validation.csv", results)
    stages, best = decision(results)
    selection = dict(format_version=2, stages=stages, ranking_method=ISOLATED_METHOD,
                     run=output.as_posix(), config_sha256=digest, representation=model_identity(),
                     p08_manifest_sha256=config["dataset_sha256"], validation_sha256=config["split_sha256"]["validation"],
                     validation_table_sha256=file_sha256(output / "validation.csv"),
                     status="requires_one_train_negative_refinement" if best is None else "selected")
    if best:
        selection["selected"] = next(r for r in results if r["level"] == best["level"]
                                     and r["seed"] == config["model_seeds"][0])
    save_json(output / "selection.json", selection)
    print(selection, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train(args.output, args.cache)
