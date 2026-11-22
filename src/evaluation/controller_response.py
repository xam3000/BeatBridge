"""P06 input dependence: matched and every mismatched validation control at fixed audio."""

import argparse
from pathlib import Path

import numpy as np
import torch

from src.evaluation.comparison import new_output, raw_result, save_comparison, write_json
from src.evaluation.comparison_native import load_json, native_setup
from src.evaluation.controller_baselines import audio_delta
from src.evaluation.controller_preflight import historical, verify_run


def predictions(evaluator, model, split):
    data = split.data
    curves = []
    for i in range(len(split)):
        item = {k: torch.from_numpy(getattr(data, k)[i])
                for k in ("features_a", "features_b", "global_features")}
        if evaluator.config.profile == "R4":
            item["length_condition"] = torch.from_numpy(data.length_condition[i])
        curves.append(evaluator.learned(model, item))
    return {k: torch.stack([c[k] for c in curves]) for k in curves[0]}


def stats(controls):
    return {k: {"mean_step_sd": float(v.std(0, unbiased=False).mean()),
                "max_step_sd": float(v.std(0, unbiased=False).max()),
                "max_step_range": float((v.amax(0) - v.amin(0)).max())} for k, v in controls.items()}


@torch.no_grad()
def swapped(evaluator, item, controls, chunk_size):
    def score(curve):
        rendered = evaluator.render(item, curve)
        return evaluator.terms(item, rendered)
    return torch.vmap(score, chunk_size=chunk_size)(controls)


def to_device(item, device):
    return {k: v.to(device) if torch.is_tensor(v) else v for k, v in item.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=["R1", "R2", "R3", "R4"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--bars", type=int, default=4)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--device", default="cuda:0", help="vectorized swap evaluation only")
    parser.add_argument("--chunk", type=int, default=12)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.backends.cudnn.allow_tf32 = False
    run = args.run or historical(args.profile)
    verify_run(run)
    ev, model, splits, protocol = native_setup(args.profile, args.bars, run, None, None, args.limit)
    init = protocol["control_initialization"]
    torch.manual_seed(protocol["seed"])
    fresh = type(model)(model.config).eval()
    with new_output(args.output) as stage, torch.no_grad():
        train = predictions(ev, model, splits["train"])
        mean_train = {k: v.mean(0) for k, v in train.items()}
        split = splits["validation"]
        controls = predictions(ev, model, split)
        donors = to_device(controls, args.device)
        val = [split[i] for i in range(len(split))]
        rows, matrix = [], []
        for i, item in enumerate(val):
            matched = {k: v[i] for k, v in controls.items()}
            base = ev.render(item, ev.equal_power()).audio
            for label, curve in (("M", matched), ("E0", ev.learned(fresh, item)), ("mean_train_M", mean_train)):
                rendered, row = raw_result(ev, item, label, curve)
                row.update(control_initialization=init, seed=protocol["seed"],
                           **audio_delta(rendered.audio, base, ev.config.points))
                rows.append(row)
                if label == "M":
                    own = row
            scores = {k: t.cpu() for k, t in swapped(ev, to_device(item, args.device), donors, args.chunk).items()}
            for k, v in scores.items():
                if not torch.isfinite(v).all() or not np.isclose(float(v[i]), own["proxy_raw"][k],
                                                                atol=3e-6, rtol=2e-5):
                    raise ValueError(f"Swap diagonal differs from native matched row: {i}/{k}")
            matrix.append(scores["loss"].numpy())
            for label, ids in (
                ("swapped", [j for j in range(len(val)) if i != j]),
                ("swapped_same_pair", [j for j, x in enumerate(val) if i != j and x["pair"] == item["pair"]]),
                ("swapped_other_pair", [j for j, x in enumerate(val) if x["pair"] != item["pair"]]),
            ):
                if ids:
                    rows.append({k: own[k] for k in ("profile", "seed", "split", "example_id", "candidate_id",
                                                      "pair", "control_initialization")} |
                                dict(condition=label, donor_count=len(ids),
                                     proxy_raw={k: float(x[ids].double().mean()) for k, x in scores.items()}))
        ids = [x["example_id"] for x in val]
        np.savez_compressed(stage / "swap.npz", example_ids=ids, loss=np.stack(matrix),
                            control_initialization=init, seed=protocol["seed"])
        write_json(stage / "control_spread.json", dict(control_initialization=init, seed=protocol["seed"],
                                                       train=stats(train), validation=stats(controls)))
        save_comparison(stage, {**protocol, "swap_device": args.device, "swap_matrix": "target_row_donor_column",
                                "limit_per_split": args.limit, "train_mean_ids": list(splits["train"].data.example_ids[:len(splits["train"])]),
                                "validation_ids": ids}, rows)
    print("END", args.output, flush=True)


if __name__ == "__main__":
    main()
