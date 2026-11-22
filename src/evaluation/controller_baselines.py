"""P06 E/F/D references. Batch only equal-length waveforms with equal cue weights."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import torch
from torch import nn

from src.evaluation.comparison import (
    FULL_NAMES, POSITION_NAMES, VOCAL_NAMES, FreeCurves, new_output, raw_result, save_comparison,
)
from src.evaluation.comparison_native import load_json, native_setup
from src.evaluation.controller_preflight import historical
from src.ml.control_initialization import full_band_arguments


def batches(items, max_batch, fixed):
    counts = Counter(item["pair"] for item in items)
    grouped = defaultdict(list)
    for i, item in enumerate(items):
        if fixed and item["split"] != "train":
            raise ValueError("Attempt to fit shared controls outside train")
        grouped[item["source_audio"].shape[-1], counts[item["pair"]] if fixed else 1].append(i)
    for (_, count), indices in grouped.items():
        for start in range(0, len(indices), max_batch):
            group = indices[start:start + max_batch]
            yield group, len(group) / (len(counts) * count)


def pack(evaluator, items, ids, device):
    names = ["source_audio", "target_audio", "features_a", "features_b"]
    if evaluator.config.vocal:
        names.extend(["source_vocal_audio", "target_vocal_audio"])
    return {k: torch.stack([items[i][k] for i in ids]).to(device) for k in names}


def batch_loss(evaluator, batch, curves):
    """The native objective reduces each term by the same arithmetic batch mean."""
    audio = evaluator._inputs(batch)
    if evaluator.config.profile == "R3":
        args = [full_band_arguments(c, FULL_NAMES, audio[0].shape[-1]) for c in curves]
        controls = [torch.stack(column) for column in zip(*args)]
    else:
        names = VOCAL_NAMES if evaluator.config.vocal else POSITION_NAMES[:2]
        controls = [torch.stack([c[k] for c in curves]) for k in names]
    rendered = evaluator.renderer(*audio, *controls)
    return evaluator.terms(batch, rendered)["loss"]


def checked_step(optimizer, modules, step):
    if not all(torch.isfinite(p.grad).all() for m in modules for p in m.parameters()):
        raise FloatingPointError(f"Nonfinite gradient at update {step}")
    optimizer.step()
    for module in modules:
        module.project()


def to_cpu(module):
    with torch.no_grad():
        return {k: v.detach().cpu() for k, v in module().items()}


def fit(evaluator, items, steps, max_batch, device):
    prepared = [(pack(evaluator, items, ids, device), weight)
                for ids, weight in batches(items, max_batch, True)]
    module = FreeCurves(evaluator.config).to(device)
    optimizer = torch.optim.Adam(module.parameters(), lr=0.06)
    for step in range(1, steps + 1):
        optimizer.zero_grad()
        for batch, weight in prepared:
            loss = batch_loss(evaluator, batch, [module()])
            (loss * weight).backward()
        checked_step(optimizer, [module], step)
        if step == 1 or step % 10 == 0:
            print("F", step, flush=True)
    return to_cpu(module)


def direct(evaluator, items, steps, max_batch, device):
    results = [None] * len(items)
    for ids, _ in batches(items, max_batch, False):
        batch = pack(evaluator, items, ids, device)
        modules = nn.ModuleList([FreeCurves(evaluator.config) for _ in ids]).to(device)
        optimizer = torch.optim.Adam(modules.parameters(), lr=0.06)
        for step in range(1, steps + 1):
            optimizer.zero_grad()
            # Sum restores the single-example gradient scale (including Adam epsilon).
            loss = batch_loss(evaluator, batch, [m() for m in modules])
            (loss * len(ids)).backward()
            checked_step(optimizer, modules, step)
        for i, m in zip(ids, modules):
            results[i] = to_cpu(m)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=["R1", "R2", "R3", "R4"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--bars", type=int, default=4)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    if min(args.steps, args.batch) < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("Budgets must be positive")
    torch.set_num_threads(1)
    # Native CPU measurement at unity gain. CUDA is used only for fitting F and D.
    torch.backends.cudnn.allow_tf32 = False
    audit = load_json(args.preflight / f"{args.profile}_{args.bars}.json")
    evaluator, _, splits, protocol = native_setup(args.profile, args.bars, historical(args.profile),
                                                  None, None, args.limit)
    with new_output(args.output) as stage:
        arrays = {}
        for name, split in splits.items():
            items = [split[i] for i in range(len(split))]
            if any(audit[name]["manifests"][x["example_id"]] != x["geometry"]["cache_manifest_sha256"]
                   for x in items):
                raise ValueError("Cache changed after preflight")
            arrays[name] = items
        fixed = fit(evaluator, arrays["train"], args.steps, args.batch, args.device)
        values = direct(evaluator, arrays["validation"], args.steps, args.batch, args.device)
        rows = []
        equal = evaluator.equal_power()
        for item, local in zip(arrays["validation"], values):
            for condition, controls in (("E", equal), ("F", fixed), ("D", local)):
                rendered, row = raw_result(evaluator, item, condition, controls)
                if condition == "E":
                    reference = rendered.audio
                row.update(control_initialization="equal_power_reference", model_initialization="legacy",
                           **audio_delta(rendered.audio, reference, evaluator.config.points))
                rows.append(row)
        save_comparison(stage, {**protocol, "fit_device": args.device, "max_batch": args.batch,
                                "reference_initialization": "equal_power_reference", "updates": args.steps,
                                "fit_train_ids": [x["example_id"] for x in arrays["train"]],
                                "limit_per_split": args.limit}, rows)
    print("END", args.output, flush=True)


def audio_delta(audio, reference, frames):
    from src.control.differentiable import _frame_rms_db

    delta = audio - reference
    ratio = float(delta.square().mean().sqrt() / reference.square().mean().sqrt())
    frames_db = (_frame_rms_db(audio[None], frames, 1e-6)
                 - _frame_rms_db(reference[None], frames, 1e-6)).abs()
    return dict(relative_rms=ratio, mean_abs_frame_db=float(frames_db.mean()),
                max_abs_frame_db=float(frames_db.max()))


if __name__ == "__main__":
    main()
