"""Build a blinded A/B study from real control-comparison exports."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import uuid

from src.dataset import DEFAULT_TRACK_EXCLUSIONS_PATH
from src.evaluation.control_probe import export_control_comparisons
from src.evaluation.control_study_ratings import create_control_study_ratings


BLIND_CONTROL_STUDY_FORMAT_VERSION = 1
DEFAULT_BLIND_SEED = 20_260_729


def export_blind_control_study(
    batch_directory,
    output_directory,
    *,
    analysis_location=Path("output") / "pre_analysis",
    pair_count=8,
    transition_bars=4,
    control_points=32,
    optimization_steps=60,
    optimization_learning_rate=0.08,
    optimization_sample_rate=11_025,
    prefix_seconds=5.0,
    suffix_seconds=8.0,
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    max_track_uses=2,
    blind_seed=DEFAULT_BLIND_SEED,
):
    """Export A/B WAVs, a public manifest, a separate key, and ratings."""
    output_directory = Path(output_directory)
    full_manifest_path = export_control_comparisons(
        batch_directory,
        output_directory,
        analysis_location=analysis_location,
        pair_count=pair_count,
        transition_bars=transition_bars,
        control_points=control_points,
        optimization_steps=optimization_steps,
        optimization_learning_rate=optimization_learning_rate,
        optimization_sample_rate=optimization_sample_rate,
        prefix_seconds=prefix_seconds,
        suffix_seconds=suffix_seconds,
        track_exclusions_path=track_exclusions_path,
        max_track_uses=max_track_uses,
    )
    full_manifest = _read_json(full_manifest_path)
    if full_manifest["status"] != "completed":
        raise RuntimeError("Cannot blind a comparison export with failures")

    rng = random.Random(int(blind_seed))
    public_pairs = []
    answer_pairs = []
    for pair in full_manifest["pairs"]:
        pair_directory = output_directory / pair["directory"]
        baseline_label = rng.choice(("A", "B"))
        optimized_label = "B" if baseline_label == "A" else "A"
        baseline_old = pair_directory / pair["exports"]["baseline"]["path"]
        optimized_old = pair_directory / pair["exports"]["optimized"]["path"]
        baseline_new = pair_directory / f"{baseline_label}.wav"
        optimized_new = pair_directory / f"{optimized_label}.wav"
        os.replace(baseline_old, baseline_new)
        os.replace(optimized_old, optimized_new)

        baseline_metadata = dict(pair["exports"]["baseline"])
        optimized_metadata = dict(pair["exports"]["optimized"])
        baseline_metadata["path"] = baseline_new.name
        optimized_metadata["path"] = optimized_new.name
        files_by_label = {
            baseline_label: baseline_metadata,
            optimized_label: optimized_metadata,
        }
        public_pairs.append(
            {
                "index": int(pair["index"]),
                "directory": pair["directory"],
                "source_track": pair["candidate"]["source_track"]["path"],
                "target_track": pair["candidate"]["target_track"]["path"],
                "transition_length_bars": int(
                    pair["candidate"]["transition_length_bars"]
                ),
                "files": {
                    label: files_by_label[label]
                    for label in ("A", "B")
                },
            }
        )
        pair["exports"]["baseline"] = baseline_metadata
        pair["exports"]["optimized"] = optimized_metadata
        answer_pairs.append(
            {
                "index": int(pair["index"]),
                "directory": pair["directory"],
                "mapping": {
                    baseline_label: "baseline_equal_power",
                    optimized_label: "optimized_proxy",
                },
                "details": pair,
            }
        )

    answer_key = {
        "format_version": BLIND_CONTROL_STUDY_FORMAT_VERSION,
        "blind_seed": int(blind_seed),
        "warning": "Do not inspect before completing ratings.json.",
        "pairs": answer_pairs,
    }
    public_manifest = {
        "format_version": BLIND_CONTROL_STUDY_FORMAT_VERSION,
        "blind": True,
        "status": "completed",
        "created_at_utc": full_manifest["created_at_utc"],
        "completed_at_utc": full_manifest["completed_at_utc"],
        "control_protocol_version": full_manifest["control_protocol_version"],
        "source_batch": full_manifest["source_batch"],
        "selection_policy": full_manifest["selection_policy"],
        "track_exclusions_path": full_manifest["track_exclusions_path"],
        "config": {
            **full_manifest["config"],
            "blind_seed": int(blind_seed),
        },
        "answer_key": "answer_key.json",
        "ratings": "ratings.json",
        "pairs": public_pairs,
        "failures": [],
    }
    _write_json_atomic(output_directory / "answer_key.json", answer_key)
    _write_json_atomic(output_directory / "manifest.json", public_manifest)
    create_control_study_ratings(output_directory)
    _write_blind_readme(output_directory, public_manifest)
    return output_directory / "manifest.json"


def _write_blind_readme(output_directory, manifest):
    lines = [
        "# Blinder Control-A/B-Vergleich",
        "",
        "Höre in jedem Paar zuerst `A.wav` und `B.wav`, ohne `answer_key.json`",
        "zu öffnen. Beide Dateien besitzen denselben Kontext und dieselbe",
        "gemeinsame Peak-Absenkung.",
        "",
        "Bewerte je Variante von 1 bis 5:",
        "",
        "- Sauberkeit des Übergangs",
        "- Energieverlauf",
        "- Low-End-Übergabe",
        "- rhythmische Stabilität",
        "- Freiheit von Artefakten",
        "",
        "Notiere außerdem `A`, `B` oder `tie` als Präferenz. Die Bewertungen",
        "werden atomisch in `ratings.json` gespeichert. Der Antwortschlüssel",
        "soll erst nach allen Bewertungen geöffnet werden.",
        "",
        f"Paare: {len(manifest['pairs'])}; Control-Protokoll: "
        f"{manifest['control_protocol_version']}.",
        "",
    ]
    _write_text_atomic(output_directory / "README.md", "\n".join(lines))


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload):
    _write_text_atomic(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _write_text_atomic(path, text):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(text, encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Export a blinded A/B control study from a historical batch.",
    )
    parser.add_argument("batch_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--pair-count", type=int, default=8)
    parser.add_argument("--transition-bars", type=int, default=4)
    parser.add_argument("--control-points", type=int, default=32)
    parser.add_argument("--optimization-steps", type=int, default=60)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--optimization-sample-rate", type=int, default=11_025)
    parser.add_argument("--prefix-seconds", type=float, default=5.0)
    parser.add_argument("--suffix-seconds", type=float, default=8.0)
    parser.add_argument("--track-exclusions", default=str(DEFAULT_TRACK_EXCLUSIONS_PATH))
    parser.add_argument("--max-track-uses", type=int, default=2)
    parser.add_argument("--blind-seed", type=int, default=DEFAULT_BLIND_SEED)
    return parser


def main():
    args = build_argument_parser().parse_args()
    manifest_path = export_blind_control_study(
        args.batch_directory,
        args.output_directory,
        analysis_location=args.analysis_location,
        pair_count=args.pair_count,
        transition_bars=args.transition_bars,
        control_points=args.control_points,
        optimization_steps=args.optimization_steps,
        optimization_learning_rate=args.learning_rate,
        optimization_sample_rate=args.optimization_sample_rate,
        prefix_seconds=args.prefix_seconds,
        suffix_seconds=args.suffix_seconds,
        track_exclusions_path=args.track_exclusions,
        max_track_uses=args.max_track_uses,
        blind_seed=args.blind_seed,
    )
    manifest = _read_json(manifest_path)
    print(f"Exported {len(manifest['pairs'])} blind A/B pairs")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
