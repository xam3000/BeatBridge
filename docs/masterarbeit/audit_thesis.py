r"""Read-only thesis checks; never opens audio, test tensors, or blind answer keys.

Run from the repository root with .venv\Scripts\python.exe -B.
Writes a JSON report only to the explicitly supplied --report path.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = {"scope": "metadata and file hashes; no audio, test NPZ, test-only JSONL, or blind keys opened"}
    thesis = ROOT / "overleaf"
    files = [thesis / "CGThesis.tex", thesis / "meta.tex", *sorted((thesis / "chapters").glob("*.tex"))]
    labels, refs, cites, todos, figures, environments = defaultdict(list), [], set(), [], [], []
    source_hashes = {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        source_hashes[rel] = digest(path)
        active_lines = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "TODO" in line:
                todos.append({"file": rel, "line": number, "text": line.strip()})
            active = re.split(r"(?<!\\)%", line)[0]
            active_lines.append(active)
            for label in re.findall(r"\\label\{([^}]+)\}", active):
                labels[label].append(f"{rel}:{number}")
            for ref in re.findall(r"\\(?:[cC]?ref|eqref|autoref|pageref)\*?\{([^}]+)\}", active):
                refs.extend((key.strip(), f"{rel}:{number}") for key in ref.split(","))
            for cite in re.findall(r"\\(?:cite\w*|parencite|textcite)\*?(?:\[[^]]*\])*\{([^}]+)\}", active):
                cites.update(key.strip() for key in cite.split(","))
            for name in re.findall(r"\\(?:include|input|includegraphics)(?:\[[^]]*\])?\{([^}]+)\}", active):
                candidates = [thesis / name, thesis / (name + ".tex")]
                candidates += [thesis / (name + ext) for ext in [".png", ".pdf", ".jpg", ".eps"]]
                if not any(candidate.exists() for candidate in candidates):
                    figures.append({"file": rel, "line": number, "missing": name})
        text = "\n".join(active_lines)
        stack = []
        for direction, name in re.findall(r"\\(begin|end)\{([^}]+)\}", text):
            if direction == "begin":
                stack.append(name)
            elif not stack or stack.pop() != name:
                environments.append(rel + ": mismatched environment " + name)
        if stack:
            environments.append(rel + ": unclosed " + str(stack))
    bib = (thesis / "bibliography.bib").read_text(encoding="utf-8")
    keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib)
    report["latex"] = {
        "source_sha256": source_hashes,
        "duplicate_labels": {k: v for k, v in labels.items() if len(v) > 1},
        "undefined_references": [{"label": k, "location": v} for k, v in refs if k not in labels],
        "missing_citations": sorted(cites - set(keys)),
        "duplicate_bibliography_keys": [k for k, n in Counter(keys).items() if n > 1],
        "unused_bibliography_keys": sorted(set(keys) - cites),
        "citation_count": len(cites), "bibliography_entry_count": len(keys),
        "missing_inputs_or_graphics": figures, "environment_errors": environments,
        "todos": todos,
    }
    datasets, assignments, hash_checks = [], {}, []
    roots = [
        "feature_protocol_v1_top3_4bar_track_split_20260731",
        "feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805",
        "variable_v2_strict_20260820_selected_roformer_run01",
        "prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four",
    ]
    for name in roots:
        root = ROOT / "output/datasets" / name
        manifest = read(root / "manifest.json")
        by_hash = defaultdict(set)
        for item in manifest["track_assignments"]:
            by_hash[item["sha256"]].add(item["split"])
        assignments[manifest["dataset_id"]] = {key: next(iter(values)) for key, values in by_hash.items()}
        errors, observed, checked_rows = [], Counter(), 0
        for key, entry in manifest["files"].items():
            if "test" in key:  # Do not open or hash held-out payloads.
                continue
            path = root / entry["path"]
            actual = digest(path)
            hash_checks.append({"file": path.relative_to(ROOT).as_posix(), "matches": actual == entry["sha256"], "sha256": actual})
            if path.suffix != ".jsonl":
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row["split"] == "test":  # Mixed format-1 metadata: do not inspect test rows further.
                    continue
                checked_rows += 1
                observed[str(row.get("transition_length_bars")) + ":" + row["split"]] += 1
                for role in ["source_track", "target_track"]:
                    if assignments[manifest["dataset_id"]].get(row[role]["sha256"]) != row["split"]:
                        errors.append({"example": row["example_id"], "role": role})
        datasets.append({"root": str(root.relative_to(ROOT)), "manifest_sha256": digest(root / "manifest.json"),
                         "dataset_id": manifest["dataset_id"], "split_counts": manifest["split_counts"],
                         "assignment_count": len(by_hash), "conflicting_assignments": sum(len(v) > 1 for v in by_hash.values()),
                         "normalization": manifest["normalization"], "checked_train_validation_rows": checked_rows,
                         "observed_train_validation_counts": dict(observed), "row_assignment_errors": errors})
    report["datasets"] = datasets
    cross = []
    for (a, left), (b, right) in itertools.combinations(assignments.items(), 2):
        counts = Counter(f"{left[h]}->{right[h]}" for h in left.keys() & right.keys())
        cross.append({"from": a, "to": b, "shared_assignments": dict(sorted(counts.items()))})
    report["cross_dataset_split_exposure"] = cross
    shared = read(ROOT / "output/four_models_shared_20pairs_validation_20260930/manifest.json")
    variable_map = assignments[shared["variable_dataset_id"]]
    fixed_map = assignments[shared["dataset_id"]]
    shared_exposure = []
    for pair in shared["selection"]["examples_per_track_pair"]:
        roles = {}
        for role in ["source", "target"]:
            prefix = pair[role + "_sha256_prefix"]
            matches = [h for h in fixed_map if h.startswith(prefix)]
            if len(matches) != 1:
                raise ValueError("Non-unique shared-study track prefix")
            roles[role] = {"sha256": matches[0], "fixed_assignment": fixed_map[matches[0]],
                           "variable_assignment": variable_map.get(matches[0], "outside_authority")}
        shared_exposure.append({"cue_count": pair["count"], **roles})
    report["shared_study_exposure"] = shared_exposure
    import torch  # Restricted checkpoint metadata loading; no forward pass.
    runs = []
    for path in sorted((ROOT / "output/training_runs").glob("prive*/manifest.json")):
        manifest = read(path)
        contract = manifest["contract"]
        for entry in manifest["files"].values():
            file = path.parent / entry["path"]
            actual = digest(file)
            hash_checks.append({"file": file.relative_to(ROOT).as_posix(), "matches": actual == entry["sha256"], "sha256": actual})
        history = read(path.with_name("history.json"))
        epochs = history["epochs"]
        def loss(epoch):
            return epoch["validation"]["loss"]
        best = min(epochs, key=loss)
        checkpoint_metadata = {}
        for key in ["best_checkpoint", "latest_checkpoint"]:
            checkpoint = torch.load(path.parent / manifest["files"][key]["path"], map_location="cpu", weights_only=True)
            checkpoint_metadata[key] = {k: checkpoint.get(k) for k in ["epoch", "best_epoch", "best_validation_loss", "run_id"]}
            checkpoint_metadata[key]["state_parameter_count"] = sum(t.numel() for t in checkpoint["model_state_dict"].values())
        declared = checkpoint_metadata["best_checkpoint"]
        runs.append({"root": path.parent.relative_to(ROOT).as_posix(), "manifest_sha256": digest(path),
                     "status": manifest["status"], "last_epoch": manifest["last_epoch"],
                     "declared_best_epoch": manifest.get("best_epoch", declared["best_epoch"]),
                     "declared_best_validation_loss": manifest.get("best_validation_loss", declared["best_validation_loss"]),
                     "checkpoint_metadata": checkpoint_metadata,
                     "first_epoch": epochs[0]["epoch"], "first_loss": loss(epochs[0]),
                     "minimum_epoch": best["epoch"], "minimum_loss": loss(best),
                     "parameter_count": manifest.get("model_parameter_count"), "contract": contract,
                     "io_audit": read(path.with_name("io_audit.json")) if path.with_name("io_audit.json").exists() else None})
    report["runs"] = runs
    report["file_hash_checks"] = hash_checks
    studies = []
    for path in sorted((ROOT / "output/control_studies").glob("*/study_results.json")):
        result = read(path)
        counted = Counter(row["preferred_method"] for row in result["pairs"])
        studies.append({"root": path.parent.relative_to(ROOT).as_posix(), "sha256": digest(path),
                        "sample": result["sample"], "preference_counts": result["preference_counts"],
                        "recomputed_preference_counts": dict(counted),
                        "count_agreement": all(counted[k] == n for k, n in result["preference_counts"].items()),
                        "criterion_summary": result["criterion_summary"]})
    report["completed_studies"] = studies
    ratings = []
    for path in [*sorted((ROOT / "output/control_studies").glob("*/ratings.json")), ROOT / "output/four_models_shared_20pairs_validation_20260930/ratings.json"]:
        value = read(path)
        ratings.append({"file": path.relative_to(ROOT).as_posix(), "status": value.get("status"),
                        "has_analysis": path.with_name("study_results.json").exists()})
    report["rating_status"] = ratings
    batches = []
    for name in ["prive/_top1000/_baseline/_20260921_fixed", "prive_top1000_variable_top3_20260922"]:
        path = ROOT / "output/batches" / name / "manifest.json"
        manifest = read(path)
        pairs = [pair for source in manifest["sources"] for pair in source["pairs"]]
        batches.append({"file": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "pairs": len(pairs),
                        "status_counts": dict(Counter(p.get("status") for p in pairs)),
                        "pairs_with_candidates": sum(p.get("candidate_count", 0) > 0 for p in pairs),
                        **{key: sum(p.get(key, 0) for p in pairs) for key in ["candidate_count", "rendered_variant_count", "render_failure_count", "transition_metric_failure_count"]}})
    report["batches"] = batches
    csv_path = ROOT / "wandb_export_2026-10-02T09_20_57.391+02_00.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    sweep_root = ROOT / "output/training_runs/wandb_sweeps/tcn_bilstm_transition_control_v1/nqntmdi0"
    sweep_runs = []
    for path in sorted(sweep_root.glob("*/manifest.json")):
        manifest = read(path)
        entry = manifest.get("files", {}).get("history")
        if not entry:
            continue
        history_path = path.parent / entry["path"]
        epochs = read(history_path)["epochs"]
        best = min(epochs, key=lambda e: e["validation"]["loss"])
        sweep_runs.append({"run": path.parent.name, "history_matches": digest(history_path) == entry["sha256"],
                           "best_epoch": best["epoch"], "best_loss": best["validation"]["loss"],
                           "best_validation_components": best["validation"],
                           "last_epoch": epochs[-1]["epoch"], "has_best_checkpoint": "best_checkpoint" in manifest.get("files", {})})
    report["sweep"] = {"csv_sha256": digest(csv_path), "rows": len(rows),
                       "state_counts": dict(Counter(row["State"] for row in rows)), "local_runs": sweep_runs}
    report["latex_tools_on_path"] = {name: shutil.which(name) for name in ["pdflatex", "latexmk", "xelatex", "lualatex", "tectonic", "bibtex", "biber"]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "hash_checks": len(hash_checks),
                      "hash_failures": sum(not item["matches"] for item in hash_checks),
                      "undefined_references": report["latex"]["undefined_references"],
                      "dataset_row_errors": sum(len(d["row_assignment_errors"]) for d in datasets),
                      "todo_count": len(todos)}, indent=2))


if __name__ == "__main__":
    main()
