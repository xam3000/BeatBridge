"""Run a paired native diagnosis or render one complete P11 playback panel."""

import argparse
from pathlib import Path

import torch

from src.analysis.pre_analysis import MERGE_ALGORITHM_VERSION, MERGE_ALGORITHM_VERSION_V2
from src.evaluation.comparison import new_output
from src.evaluation.comparison_native import diagnose, FAMILIES
from src.evaluation.comparison_study import study


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(required=True)
    native = modes.add_parser("diagnose", help="E/F/M/D under one September run contract")
    native.set_defaults(execute=diagnose)
    native.add_argument("profile", choices=FAMILIES)
    native.add_argument("--bars", type=int, default=4)
    native.add_argument("--run", type=Path, help="compatible run directory (default: September best)")
    native.add_argument("--dataset", type=Path, help="must match the run's dataset digest")
    native.add_argument("--cache", type=Path)
    native.add_argument("--limit", type=positive_int, help="development smoke: first N examples per split")
    listening = modes.add_parser("study", help="six selector/curve cells and one hard-cut anchor")
    listening.set_defaults(execute=study)
    listening.add_argument("panel", type=Path)
    listening.add_argument("--analysis-root", type=Path, default=Path("output/pre_analysis"))
    listening.add_argument("--merge-algorithm", choices=(MERGE_ALGORITHM_VERSION, MERGE_ALGORITHM_VERSION_V2),
                           default=MERGE_ALGORITHM_VERSION)
    for mode in (native, listening):
        mode.add_argument("--output", type=Path, required=True)
        mode.add_argument("--steps", type=positive_int, default=80, help="Adam updates for F/D")
        mode.add_argument("--threads", type=positive_int, default=2, help="CPU Torch threads")
    args = parser.parse_args(argv)
    torch.set_num_threads(args.threads)
    with new_output(args.output) as stage:
        args.execute(stage, args)
    print(args.output / "results.json")


if __name__ == "__main__":
    main()
