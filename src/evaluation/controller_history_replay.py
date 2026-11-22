"""Replay R4's checkpoint with the training device, archived batch size and native epoch code."""

import argparse
from pathlib import Path

import numpy as np
import torch

from src.evaluation.comparison import new_output, write_json
from src.evaluation.comparison_native import load_json, native_setup
from src.evaluation.controller_preflight import historical
from src.ml.variable_data import collate_variable_feature_examples
from src.ml.variable_runner import _run_temporal_epoch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    run = historical("R4")
    metadata = sorted((run / "wandb").rglob("wandb-metadata.json"))
    sizes = set()
    for path in metadata:
        argv = load_json(path)["args"]
        sizes.add(int(argv[argv.index("--batch-size") + 1]))
    if len(sizes) != 1:
        raise ValueError("Missing or inconsistent historical batch size")
    size = sizes.pop()
    device = torch.device(load_json(run / "manifest.json")["contract"]["training"]["device"])
    with new_output(args.output) as out, torch.no_grad():
        for bars in (2, 4, 6, 8):
            ev, model, splits, proto = native_setup("R4", bars, run, None, None, None)
            split = splits["validation"]
            batches = (collate_variable_feature_examples([split[i] for i in range(start, min(start + size, len(split)))])
                       for start in range(0, len(split), size))
            result = _run_temporal_epoch(model.to(device), batches, ev.renderer.to(device),
                                         ev.objective.to(device), None, None, device)["by_length"][str(bars)]
            epoch = proto["checkpoint_epoch"]
            history = next(r for r in load_json(run / "history.json")["epochs"] if r["epoch"] == epoch)
            expected = history["validation"]["by_length"][str(bars)]
            errors = {k: result[k] - v for k, v in expected.items()}
            write_json(out / f"R4_{bars}.json", dict(control_initialization="legacy", seed=proto["seed"],
                       batch_size=size, batch_size_sources=[str(p) for p in metadata], device=str(device),
                       epoch=epoch, checkpoint_sha256=proto["checkpoint_sha256"], examples=len(split),
                       observed=result, history=expected, errors=errors))
            print(bars, max(map(abs, errors.values())), flush=True)
            if any(not np.isclose(result[k], v, atol=3e-6, rtol=2e-5) for k, v in expected.items()):
                raise ValueError(f"R4 original-device history differs at {bars} bars: {errors}")


if __name__ == "__main__":
    main()
