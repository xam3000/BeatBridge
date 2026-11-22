"""Join P06 by cue identity, verify the training histories and aggregate over directed pairs."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.evaluation.comparison import new_output, write_json
from src.evaluation.comparison_native import load_json
from src.evaluation.controller_figure import plot_gains
from src.evaluation.controller_preflight import GROUPS, PLAN, historical, verify_run
from src.evaluation.controller_repeats import check_repeat
from src.evaluation.ml_control_study import _file_sha256


def percentage(numerator, denominator):
    return 100 * numerator / denominator if denominator > 1e-8 else None


def avg(items):
    return float(np.mean(items))


def sd(items):
    return float(np.std(items, ddof=1)) if len(items) > 1 else None


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_table(directory):
    protocol = load_json(directory / "protocol.json")
    sha = _file_sha256(directory / "protocol.json")
    conditions = defaultdict(dict)
    for row in load_json(directory / "results.json"):
        key = row["example_id"]
        dest = conditions[row["condition"]]
        if key in dest or row["split"] != "validation" or row["protocol_sha256"] != sha:
            raise ValueError(f"Invalid or duplicate row in {directory}: {key}")
        dest[key] = row
    return protocol, dict(conditions)


def check_history(run, bars, proto, table, original_device_replay=None):
    history = {r["epoch"]: r["validation"] for r in load_json(run / "history.json")["epochs"]}
    errors = {}
    for cond, epoch in [("E0", 0), ("M", proto["checkpoint_epoch"])]:
        if epoch not in history:
            if cond == "E0" and proto["profile"] == "R4":
                continue
            raise ValueError(f"Missing epoch {epoch} in {run}")
        expected = history[epoch]
        expected = expected.get("by_length", {}).get(str(bars), expected)
        if original_device_replay is not None:
            if (original_device_replay["checkpoint_sha256"] != proto["checkpoint_sha256"]
                    or original_device_replay["epoch"] != epoch or original_device_replay["history"] != expected
                    or any(not np.isclose(original_device_replay["observed"][k], v, atol=3e-6, rtol=2e-5)
                           for k, v in expected.items())):
                raise ValueError("Original-device replay differs from bound history")
        rows = list(table[cond].values())
        errors[cond] = {}
        for key in rows[0]["proxy_raw"]:
            actual = avg([r["proxy_raw"][key] for r in rows])
            errors[cond][key] = actual - expected[key]
            if ((original_device_replay is None or key == "loss")
                    and not np.isclose(actual, expected[key], atol=3e-6, rtol=2e-5)):
                raise ValueError(f"History mismatch {run}/{epoch}/{key}: {expected[key]} vs {actual}")
    return errors


def contrasts(equal, value, direct):
    gain = equal - value
    return dict(loss=value, equal_loss=equal, gain=gain, gain_pct_E=percentage(gain, equal),
                direct_gain=equal-direct, share_pct_ED=percentage(gain, equal-direct))


def recording_components(pairs, groups):
    """Keep each directed edge, linking both roles by recording group."""
    incident = defaultdict(list)
    edges = [(groups[a], groups[b]) for a, b in pairs]
    for index, (a, b) in enumerate(edges):
        incident[a].append(index)
        incident[b].append(index)
    components = []
    for a, _ in edges:
        if a not in incident:
            continue
        pending = [a]
        members = set()
        while pending:
            for index in incident.pop(pending.pop(), ()):
                if index not in members:
                    members.add(index)
                    pending.extend(edges[index])
        components.append(sorted(members))
    return components


def component_interval(differences, components):
    """Resample components uniformly, preserving edge weight and multiplicity."""
    rng = np.random.default_rng(20261121)
    draws = rng.integers(len(components), size=(10000, len(components)))
    sums = np.array([differences[indices].sum() for indices in components])
    sizes = np.array([len(indices) for indices in components])
    return np.quantile(sums[draws].sum(axis=1) / sizes[draws].sum(axis=1), [.025, .975])


def summarize_case(root, profile, bars, name, manifest, run, tables, groups):
    base_dir = root / "baseline" / f"{profile}_{bars}"
    model_dir = root / "response" / name
    bp, base = read_table(base_dir)
    mp, model = read_table(model_dir)
    init = mp["control_initialization"]
    if (set(base) != {"E", "F", "D"} or set(base) & model.keys()
            or mp["run_id"] != manifest["run_id"]
            or mp["run_manifest_sha256"] != _file_sha256(run / "manifest.json")
            or mp["checkpoint_sha256"] != manifest["files"]["best_checkpoint"]["sha256"]
            or init != manifest["contract"]["model"]["config"].get("control_initialization", "legacy")):
        raise ValueError(f"Unbound conditions or checkpoint in {name}")
    keys = ("profile", "bars", "dataset_id", "dataset_manifest_sha256", "normalization", "renderer",
            "objective_weights", "run_renderer", "energy_frames", "feature_protocol", "sample_rate")
    if any(mp[k] != bp[k] for k in keys) or bp["updates"] != 80 or mp["limit_per_split"] is not None:
        raise ValueError(f"Unmatched native profile or budget in {name}")
    audit = load_json(root / "preflight" / f"{profile}_{bars}.json")
    # Later preflight versions also read key confidence from the global channels.
    recheck = root / "preflight_recheck" / f"{profile}_{bars}.json"
    feature_audit = load_json(recheck) if recheck.exists() else audit
    ids = audit["validation"]["manifests"]
    if (set(bp["fit_train_ids"]) != set(audit["train"]["manifests"])
            or set(mp["train_mean_ids"]) != set(bp["fit_train_ids"]) or set(bp["fit_train_ids"]) & set(ids)):
        raise ValueError("Training population differs")
    joined = {**base, **model}
    required = {"E", "F", "M", "D", "E0", "swapped", "swapped_other_pair", "mean_train_M"}
    if not required <= joined.keys() or any(set(joined[c]) != set(ids) for c in required):
        raise ValueError("Incomplete paired population")
    for eid, sha in ids.items():
        anchor = base["E"][eid]
        for cond in ("E", "F", "D", "M", "E0", "mean_train_M"):
            r = joined[cond][eid]
            if (r["geometry"]["cache_manifest_sha256"] != sha or r["pair"] != anchor["pair"]
                    or r["bridge_samples"] != anchor["bridge_samples"] or r["candidate_id"] != anchor["candidate_id"]):
                raise ValueError(f"Unmatched geometry {eid}")
        if init == "equal_power_v1" and joined["E0"][eid]["raw_audio_sha256"] != anchor["raw_audio_sha256"]:
            raise ValueError(f"New E0 differs from equal power {eid}")
    replay = load_json(root / "history_replay" / f"R4_{bars}.json") if profile == "R4" else None
    errors = check_history(run, bars, mp, model, replay)
    ident = dict(profile=profile, bars=bars, model_initialization=init, seed=mp["seed"])
    by_pair = defaultdict(list)
    for eid in ids:
        by_pair[tuple(model["M"][eid]["pair"])].append(eid)
    with np.load(model_dir / "swap.npz", allow_pickle=False) as saved:
        ordered = list(saved["example_ids"])
        scores = saved["loss"]
        if (len(set(ordered)) != len(ids) or set(ordered) != set(ids)
                or scores.shape != (len(ids), len(ids)) or not np.isfinite(scores).all()
                or str(saved["control_initialization"]) != init or int(saved["seed"]) != mp["seed"]):
            raise ValueError("Swap matrix differs from response table")
        for i, eid in enumerate(ordered):
            matched = scores[i, i]
            wrong = np.delete(scores[i], i)
            lower = int(np.count_nonzero(wrong < matched))
            tied = int(np.count_nonzero(wrong == matched))
            if not (np.isclose(matched, model["M"][eid]["proxy_raw"]["loss"], atol=3e-6, rtol=2e-5)
                    and np.isclose(wrong.mean(dtype=np.float64), model["swapped"][eid]["proxy_raw"]["loss"])):
                raise ValueError(f"Unmatched swap matrix values: {eid}")
            tables["swaps"].append(dict(**ident, example_id=eid, source=model["M"][eid]["pair"][0],
                target=model["M"][eid]["pair"][1], wrong_donors=len(wrong), lower_loss_donors=lower,
                equal_loss_donors=tied, own_midrank=1 + lower + tied / 2))
    for cond, values in joined.items():
        per_pair, parts, audio = [], defaultdict(list), defaultdict(list)
        used_pairs = []
        for pair, cues in by_pair.items():
            used = [k for k in cues if k in values]
            if not used:
                continue
            rows = [values[k] for k in used]
            def proxy(label):
                return avg([joined[label][k]["proxy_raw"]["loss"] for k in used])
            result = contrasts(proxy("E"), proxy(cond), proxy("D"))
            result["delta_vs_M"] = result["loss"] - proxy("M")
            per_pair.append(result)
            used_pairs.append(pair)
            tables["pairs"].append(dict(**ident, condition=cond, source=pair[0], target=pair[1],
                                        cues=len(used), **result))
            for key in rows[0]["proxy_raw"]:
                parts[key].append(avg([r["proxy_raw"][key] for r in rows]))
            if "relative_rms" in rows[0]:
                for metric in ("relative_rms", "mean_abs_frame_db", "max_abs_frame_db"):
                    audio[metric].append(avg([r[metric] for r in rows]))
        def column(k):
            return [p[k] for p in per_pair]
        summary = contrasts(avg(column("equal_loss")), avg(column("loss")),
                            avg(column("equal_loss")) - avg(column("direct_gain")))
        share = [v for v in column("share_pct_ED") if v is not None]
        gain_pct = [v for v in column("gain_pct_E") if v is not None]
        rms = avg(audio["relative_rms"]) if audio else None
        rms_db = (20 * np.log10(rms) if rms > 0 else "-inf") if rms is not None else None
        diffs = np.array(column("delta_vs_M"))
        components = recording_components(used_pairs, groups)
        ci = (component_interval(diffs, components)
              if profile == "R4" and len(components) > 2 else (None, None))
        tables["matrix"].append(dict(**ident, condition=cond, examples=len(values), pairs=len(per_pair),
            **summary, pair_loss_sd=sd(column("loss")), delta_vs_M=avg(diffs), delta_vs_M_pair_sd=sd(diffs),
            recording_components=len(components), delta_vs_M_pair_min=min(diffs),
            delta_vs_M_pair_max=max(diffs), delta_vs_M_component_boot_lo=ci[0],
            delta_vs_M_component_boot_hi=ci[1],
            mean_pair_gain_pct_E=avg(gain_pct) if gain_pct else None, undefined_pair_gains=len(per_pair)-len(gain_pct),
            mean_defined_pair_share_pct_ED=avg(share) if share else None,
            undefined_pair_shares=len(per_pair)-len(share),
            relative_rms=rms, relative_rms_db=rms_db,
            mean_abs_frame_db=avg(audio["mean_abs_frame_db"]) if audio else None,
            mean_cue_peak_frame_db=avg(audio["max_abs_frame_db"]) if audio else None,
            median_cue_peak_frame_db=float(np.median([v["max_abs_frame_db"] for v in values.values()])) if audio else None))
        for term, contributions in parts.items():
            weight = mp["objective_weights"].get(term + "_weight")
            tables["components"].append(dict(**ident, condition=cond, term=term, raw=avg(contributions),
                pair_sd=sd(contributions), weight=weight, weighted=weight*avg(contributions) if weight is not None else None))
    spread = load_json(model_dir / "control_spread.json")
    for split in ("train", "validation"):
        for k, data in spread[split].items():
            tables["controls"].append(dict(**ident, split=split, channel=k, **data))
    return dict(**ident, run=str(run), run_id=mp["run_id"], status=manifest["status"], best_epoch=mp["checkpoint_epoch"],
                created_at_utc=manifest.get("created_at_utc"), completed_at_utc=manifest.get("completed_at_utc"),
                last_epoch=load_json(run / "history.json")["epochs"][-1]["epoch"], checkpoint_sha256=mp["checkpoint_sha256"],
                manifest_sha256=mp["run_manifest_sha256"], dataset_id=mp["dataset_id"],
                dataset_manifest_sha256=mp["dataset_manifest_sha256"], norm=mp["normalization"],
                feature_protocol=mp["feature_protocol"], feature_vocal_backend=mp["feature_vocal_backend"],
                feature_vocal_model=mp["feature_vocal_model"], waveform_vocals=mp["waveform_vocals"],
                renderer=mp["run_renderer"], objective=mp["objective"], objective_weights=mp["objective_weights"],
                training=manifest["contract"]["training"], requested_max_epochs=manifest.get("requested_max_epochs"),
                train={k: feature_audit["train"][k] for k in ("examples", "pairs", "tracks", "groups",
                       "constant_at_each_step", "constant_globals", "key_confidence")},
                validation={k: feature_audit["validation"][k] for k in ("examples", "pairs", "tracks", "groups",
                            "constant_at_each_step", "constant_globals", "key_confidence")},
                cpu_minus_history=errors, original_device_replay=replay,
                sources={str(f): _file_sha256(f) for d in (model_dir, base_dir) for f in d.iterdir() if f.is_file()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plan = load_json(PLAN)
    with GROUPS.open(encoding="utf-8-sig", newline="") as stream:
        groups = {r["sha256"]: r["recording_group_id"] for r in csv.DictReader(stream)
                  if r["recording_group_id"]}
    tables = {k: [] for k in ("matrix", "pairs", "components", "controls", "swaps")}
    runs = []
    with new_output(args.output) as out:
        for profile in ("R1", "R2", "R3", "R4"):
            hist = historical(profile)
            for bars in ((2, 4, 6, 8) if profile == "R4" else (4,)):
                runs.append(summarize_case(args.root, profile, bars, f"{profile}_{bars}_legacy",
                                           verify_run(hist), hist, tables, groups))
            for spec in (r for r in plan["runs"] if r["profile"] == profile):
                directory = args.root / spec["name"]
                runs.append(summarize_case(args.root, profile, 4, spec["name"],
                                           check_repeat(spec, directory), directory, tables, groups))
        seeds = []
        for profile in ("R1", "R2"):
            for cond in ("E", "F", "M", "D", "swapped", "swapped_other_pair"):
                rows = [r for r in tables["matrix"] if r["profile"] == profile
                        and r["model_initialization"] == "equal_power_v1" and r["condition"] == cond]
                if sorted(r["seed"] for r in rows) != [20260926, 20260927, 20260928]:
                    raise ValueError("Missing predeclared seed")
                for metric in ("loss", "gain", "gain_pct_E", "share_pct_ED", "delta_vs_M"):
                    values = [r[metric] for r in rows]
                    seeds.append(dict(profile=profile, model_initialization="equal_power_v1", condition=cond,
                                      metric=metric, n=3, mean=avg(values), sample_sd=sd(values),
                                      minimum=min(values), maximum=max(values)))
        tables["seeds"] = seeds
        training = []
        for run in runs:
            if run["profile"] == "R4" and run["bars"] != 4:
                continue  # the historical R4 epoch aggregates all four lengths
            history = load_json(Path(run["run"]) / "history.json")["epochs"]
            for epoch in history:
                training.append(dict(profile=run["profile"], model_initialization=run["model_initialization"],
                    seed=run["seed"], epoch=epoch["epoch"], selected=epoch["epoch"] == run["best_epoch"],
                    train_loss=epoch["train"]["loss"], validation_loss=epoch["validation"]["loss"],
                    status=run["status"], last_epoch=run["last_epoch"], run_id=run["run_id"]))
        tables["training"] = training
        for table, rows in tables.items():
            write_csv(out / (table + ".csv"), rows)
        write_json(out / "evidence.json", runs)
        write_json(out / "resampling.json", dict(
            recording_groups=str(GROUPS), recording_groups_sha256=_file_sha256(GROUPS),
            unit="connected recording component across both roles",
            order="first included directed pair in validation preflight ID order",
            statistic="sum of sampled pair contrasts / number of sampled pairs, including multiplicities",
            draws=10000, seed=20261121, percentiles=[2.5, 97.5], donor_pool="fixed observed cues",
            D2="observed pair range only"))
        plot_gains(tables["matrix"], out / "controls.png")
    print(f"{len(runs)} model/length evaluations, {len(tables['matrix'])} contrasts")


if __name__ == "__main__":
    main()
