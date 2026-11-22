"""Execute the frozen P05 training plan and verify every completed run against September."""

import argparse
import copy
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import torch

from src.evaluation.comparison_native import load_json
from src.evaluation.controller_preflight import PLAN, historical, verify_run
from src.ml.vocal_runner import VOCAL_TRAINING_RUN_FORMAT_VERSION, VocalTrainingConfig


def check_repeat(spec, directory):
    old = verify_run(historical(spec["profile"]))
    new = verify_run(directory)
    expected = copy.deepcopy(old["contract"])
    expected["model"]["config"]["control_initialization"] = "equal_power_v1"
    expected["training"]["seed"] = spec["seed"]
    if spec["profile"] == "R2":
        # The new serialization explicitly records AdamW and inactive scheduler settings.
        settings = VocalTrainingConfig(**expected["training"], lr_scheduler="none").to_dict()
        settings.pop("max_epochs")
        expected.update(format_version=VOCAL_TRAINING_RUN_FORMAT_VERSION, training=settings)
    if new["contract"] != expected:
        fields = [k for k in expected.keys() | new["contract"].keys()
                  if new["contract"].get(k) != expected.get(k)]
        raise ValueError(f"Contract differs beyond initialization and seed: {fields}")
    if new["requested_max_epochs"] != old["requested_max_epochs"]:
        raise ValueError("Training budget differs from September")
    groups = []
    for path in (historical(spec["profile"]), directory):
        cp = torch.load(path / "checkpoints/best.pt", map_location="cpu", weights_only=True)
        if cp.get("lr_scheduler_state_dict") is not None:
            raise ValueError("Unexpected learning-rate scheduler")
        groups.append(cp["optimizer_state_dict"]["param_groups"])
    if groups[0] != groups[1]:
        raise ValueError("Realized optimizer settings differ from September")
    epochs = load_json(directory / "history.json")["epochs"]
    if [e["epoch"] for e in epochs] != list(range(new["last_epoch"] + 1)):
        raise ValueError("Incomplete history")
    if epochs[new["best_epoch"]]["validation"]["loss"] != new["best_validation_loss"]:
        raise ValueError("Best checkpoint and validation history disagree")
    return new


def journal(message):
    with Path("docs/Bemerkungen.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n### {datetime.now():%d.%m.%Y %H:%M} – P06 Trainingslauf\n\n{message}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--only", nargs="+", help="named runs from the frozen plan")
    args = parser.parse_args()
    plan = load_json(PLAN)
    root = args.output_root or Path(plan["output_root"])
    selected = [r for r in plan["runs"] if not args.only or r["name"] in args.only]
    if args.only and len(set(args.only)) != len(selected):
        raise ValueError("Unknown training run")
    for run in selected:
        name = run["name"]
        profile = run["profile"]
        directory = root / name
        if directory.exists():
            raise FileExistsError(directory)
        audit = load_json(root / "preflight" / f"{profile}_4.json")
        if (audit["dataset_manifest_sha256"] != plan["dataset_manifest_sha256"]
                or audit["run_id"] != plan["profiles"][profile]["reference_run_id"]):
            raise ValueError("Preflight differs from plan")
        cfg = plan["profiles"][profile]
        command = [sys.executable, "-u", "-m", "src.ml", cfg["command"], plan["dataset"],
                   str(directory), "--seed", str(run["seed"]), *plan["common_args"], *cfg["args"]]
        log = root / (name + ".log")
        prefix = (f"Prüfung der Seedstreuung bzw. des R3-Startvertrags auf D2, Train/Validation 370/50. "
                  f"Aufruf `{subprocess.list2cmdline(command)}`. Protokoll `{log.as_posix()}`. ")
        print("START", name, flush=True)
        try:
            with log.open("x", encoding="utf-8") as stream:
                subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
            m = check_repeat(run, directory)
        except Exception as exc:
            journal(prefix + f"Fehler: {exc}. Laufprotokoll und Manifest vor einem weiteren Versuch prüfen.")
            raise
        journal(prefix + f"Endstatus `{m['status']}`, letzte Epoche {m['last_epoch']}, "
                f"Best E{m['best_epoch']} mit Validation-Loss {m['best_validation_loss']:.9f}. "
                "September-Vertrag, Budget, Dateihashes und History bestätigt. Best-Checkpoint gepaart auswerten.")
        print("END", name, m["last_epoch"], m["best_epoch"], flush=True)


if __name__ == "__main__":
    main()
