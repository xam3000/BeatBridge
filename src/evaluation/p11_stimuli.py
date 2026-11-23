"""Materialize the eleven frozen P01 pairs under the dated P11 protocol."""

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import soundfile as sf
import torch
from threadpoolctl import threadpool_limits

from src.analysis.pre_analysis import PartialPreAnalysis, MERGE_ALGORITHM_VERSION_V2
from src.bridge import prepare_bridge_pair
from src.candidates import BaselineCandidateGenerationConfig
from src.evaluation.comparison import write_json
from src.evaluation.comparison_study import study, RATE
from src.evaluation.p11_player import package
from src.evaluation.p11_alignment import LocalGridFailure
from src.features.extract_track import extract_or_load_track_features
from src.features.p07_mert import file_sha256
from src.features.p07_population import FREEZE, POPULATION, PUBLIC, committed
from src.features.p08_pairs import publish_dataset, rng_for
from src.pipeline import generate_transition_candidates
from src.ranking.continuation import METHOD, SELECTION, rank_continuations
from src.ranking.feature_baseline import rank_candidates
from src.ranking.rendered_transition import RenderedTransitionInput, rank_rendered_transitions


BASE = Path("output/review_jp_20261118/p11_hoerversuch")
PROTOCOL = Path("docs/masterarbeit/review_jp_20261118/p11/studienprotokoll.md")
ORIGINAL_PROTOCOL = PROTOCOL.with_name("studienprotokoll_run01.md")
REVISION = "local_grid_equal_duration_v2"


def carry_selection(stage, directory, original, pair):
    """Bind run02 to the untouched run01 choices and cached feature provenance."""
    previous = original / pair["pair_id"]
    if (previous / "exclusion.json").is_file():
        shutil.copyfile(previous / "exclusion.json", stage / "exclusion.json")
        return
    panel = json.loads((previous / "panel.json").read_bytes())
    selection = json.loads((previous / "selection.json").read_bytes())
    prior_contract = json.loads((previous / "stimuli/protocol.json").read_bytes())
    if (selection["pair"] != pair or selection["selectors"] != panel["selectors"]
            or panel != prior_contract["panel"]
            or file_sha256(previous / "panel.json") != prior_contract["panel_sha256"]
            or file_sha256(previous / "selection.json") != panel["pair_manifest_sha256"]
            or file_sha256(previous / "pool.csv") != selection["pool_sha256"]
            or panel["study_protocol_sha256"] != file_sha256(ORIGINAL_PROTOCOL)):
        raise ValueError("Historical pair selection differs")
    for name in ("pool.csv", "selection.json"):
        shutil.copyfile(previous / name, stage / name)
    panel.update(revision=REVISION, original_panel_sha256=prior_contract["panel_sha256"],
                 study_protocol_sha256=file_sha256(PROTOCOL), pair_manifest=(directory / "selection.json").as_posix())
    write_json(stage / "panel.json", panel)


def prepare(directory, pair, paths, cache, *, rotated=False):
    from src.tempo.cue_alignment import CUE_ALIGNMENT, LEGACY_ALIGNMENT, CueAlignmentError, measure_cue_alignment
    from src.evaluation.p11_session import PROTOCOL as ROTATED_PROTOCOL, REVISION as ROTATED_REVISION
    pid = pair["pair_id"]
    a, b = (paths[pair[k]["sha256"]] for k in ("source", "target"))
    for k, path in (("source", a), ("target", b)):
        if file_sha256(path) != pair[k]["sha256"]:
            raise ValueError(f"Frozen audio mismatch: {pid}/{k}")
    analysis = PartialPreAnalysis(str(cache / "analysis"))
    generated = generate_transition_candidates(a, b, analysis=analysis, target_sample_rate=RATE,
                                      config=BaselineCandidateGenerationConfig(transition_lengths_bars=(4,)))
    reasons = [r.to_dict() for r in generated.rejections]
    cues = generated.candidates
    if cues and abs(cues[0].target_bpm / cues[0].source_bpm - 1) > .15:
        reasons.append({"code": "source_relative_tempo_limit"})
        cues = ()
    if cues:
        pipeline = prepare_bridge_pair(cues[0].to_dict(), analysis,
                                       tempo_alignment=CUE_ALIGNMENT if rotated else LEGACY_ALIGNMENT)
        if rotated:
            eligible = []
            rejected_grid = 0
            rejected_tempo = 0
            rejected_context = 0
            for cue in cues:
                try:
                    timing = measure_cue_alignment(pipeline.beat_frames1, pipeline.beat_frames2,
                                                   cue.source_cutpoint.beat_index, cue.target_cutpoint.beat_index,
                                                   16, RATE)
                    timing.require_valid()
                except CueAlignmentError:
                    rejected_grid += 1
                    continue
                scale = 1 / timing.tempo_factor
                if abs(scale - 1) > .15:
                    rejected_tempo += 1
                    continue
                if (cue.source_cutpoint.sample >= 5 * RATE and
                        round(cue.target_cutpoint.sample * scale) + 8 * RATE <= round(pipeline.song2.shape[-1] * scale)):
                    eligible.append(cue)
                else:
                    rejected_context += 1
            cues = eligible
            if not cues:
                reasons.append(dict(code="empty_pool_after_tempo_and_context_gate",
                                    rejected_grid=rejected_grid, rejected_tempo=rejected_tempo,
                                    rejected_context=rejected_context))
            scale = None  # Each cue has its own regression in this protocol.
        else:
            scale = pipeline.adjusted_sample_scale2
            target_size = pipeline.adjusted_song2.shape[-1]
            cues = [c for c in cues if c.source_cutpoint.sample >= 5*RATE and
                    round(c.target_cutpoint.sample * scale) + 8*RATE <= target_size]
        del pipeline
    if not cues:
        write_json(directory / "exclusion.json", dict(pair=pair, reasons=reasons or ["insufficient_context"],
                   time=datetime.now(timezone.utc).isoformat(), affected="all seven conditions"))
        return
    if rotated:
        from src.ranking.continuation import ISOLATED_METHOD, ISOLATED_SELECTION
        ssl = rank_continuations(cues, analysis, RATE, selection_path=ISOLATED_SELECTION)
        method = ISOLATED_METHOD
    else:
        ssl = rank_continuations(cues, analysis, RATE, selection_path=SELECTION)
        method = METHOD
    eligible = {s.candidate_id for s in ssl.scores}
    common = [c for c in cues if c.candidate_id in eligible]
    if not common:
        write_json(directory / "exclusion.json", dict(pair=pair, reasons=["no_contiguous_P07_windows"],
                   time=datetime.now(timezone.utc).isoformat(), affected="all seven conditions"))
        return
    rule = rank_candidates(common, target_sample_rate=RATE)
    if rule.failures:
        raise ValueError(f"Rule scoring failed for {pid}: {rule.failures[0]}")
    selectors = dict(ssl=ssl.scores[0].candidate_id, rule=rule.scores[0].candidate_id,
                     random=rng_for("random", pid, seed=20261119).choice(sorted(eligible)))
    selected = [c for c in common if c.candidate_id in selectors.values()]
    ssl_values = {s.candidate_id:s.total_score for s in ssl.scores}
    rule_values = {s.candidate_id:s.total_score for s in rule.scores}
    with (directory / "pool.csv").open("x", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("id", "source_sample", "target_sample", "source_beat", "target_beat", "ssl", "rule"))
        for c in common:
            w.writerow((c.candidate_id, c.source_cutpoint.sample, c.target_cutpoint.sample,
                        c.source_cutpoint.beat_index, c.target_cutpoint.beat_index,
                        ssl_values[c.candidate_id], rule_values[c.candidate_id]))
    manifest = directory / "selection.json"
    write_json(manifest, dict(ranking_method=method, pair=pair, generated=len(generated.candidates),
               context_eligible=len(cues), common=len(common), tempo_scale=scale, cue_ranking=ssl.to_dict(),
               pool_sha256=file_sha256(directory / "pool.csv"), selectors=selectors,
               **({"rejected_grid": rejected_grid, "rejected_tempo": rejected_tempo,
                   "rejected_context": rejected_context} if rotated else {}),
               candidate_generation=dict(candidates=[c.to_dict() for c in selected])))
    features = []
    for path in (a,b):
        artifact = extract_or_load_track_features(path, cache_root=cache / "features", analysis=analysis,
                       target_bpm=common[0].source_bpm, vocal_backend="demucs", vocal_model="htdemucs")
        features.append(artifact.cache_directory.as_posix())
    # Paths in the panel must survive atomic publication of the pair directory.
    write_json(directory / "panel.json", dict(format_version=1, split="final", pair_id=pid,
               pair_manifest=(directory.parent / pid / manifest.name).as_posix(),
               pair_manifest_sha256=file_sha256(manifest), selectors=selectors,
               source_feature_directory=features[0], target_feature_directory=features[1],
               study_protocol_sha256=file_sha256(ROTATED_PROTOCOL if rotated else ORIGINAL_PROTOCOL),
               population_commit=FREEZE, **({"revision": ROTATED_REVISION} if rotated else {})))


def frozen_inputs():
    population = json.loads(committed(POPULATION))
    catalog = csv.DictReader(io.StringIO(committed(PUBLIC / "exposure_tracks.csv").decode("utf-8")))
    paths = {r["sha256"]: r["path"] for r in catalog if Path(r["path"]).parts[:2] == ("musik","erweiterung")}
    return population["pairs"], paths


def preanalyse(root, skip, workers):
    pairs, paths = frozen_inputs()
    def one(track):
        sha = track["sha256"]
        path = paths[sha]
        if file_sha256(path) != sha:
            raise ValueError("Frozen recording differs")
        folder = root / "cache/grid_receipts"
        folder.mkdir(parents=True, exist_ok=True)
        receipt = folder / (sha + ".json")
        if receipt.exists():
            return
        analyser = PartialPreAnalysis(str(root / "cache/analysis"))
        result = analyser(path)
        write_json(receipt, dict(sha256=sha, bpm=result.bpm, grid=result.grid_metadata.to_dict(),
                   diagnostics=analyser.merge_diagnostics))
        print(sha, result.grid_metadata.grid_source, flush=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(one, [pair[k] for pair in pairs[skip:] for k in ("source","target")]))


def record_grid_exclusions(root):
    """Retain the actual detector's rejection before any scoring or audio rendering."""
    pairs, _ = frozen_inputs()
    for pair in pairs:
        pid = pair["pair_id"]
        dest = root / pid
        if dest.exists() or any(root.glob(f".{pid}-*")):
            continue
        reasons = []
        for role in ("source","target"):
            sha = pair[role]["sha256"]
            path = root / "cache/grid_receipts" / (sha + ".json")
            if not path.exists():
                continue
            rec = json.loads(path.read_bytes())
            acceptance = (rec["diagnostics"] or {}).get("acceptance", {})
            if (rec["sha256"] == sha and rec["grid"]["fallback_used"] is True
                    and acceptance.get("accepted") is False):
                reasons.append(dict(code="unverified_grid", role=role, grid_receipt=path.as_posix(),
                                    sha256=file_sha256(path), reasons=acceptance["reasons"]))
        if reasons:
            with publish_dataset(dest) as stage:
                write_json(stage / "exclusion.json", dict(pair=pair, reasons=reasons,
                      time=datetime.now(timezone.utc).isoformat(), affected="all seven conditions"))
            print(pid, "grid exclusion", flush=True)


def run(root, original=None, *, rotated=False):
    from src.evaluation.p11_session import FINAL_PAIRS, PROTOCOL as ROTATED_PROTOCOL, REVISION as ROTATED_REVISION
    from src.tempo.cue_alignment import CueAlignmentError
    if rotated:
        from src.ranking.continuation import ISOLATED_SELECTION, ISOLATED_METHOD
        if not ISOLATED_SELECTION.is_file():
            raise ValueError("A selected isolated-window study head is required before rendering")
        decision = json.loads(ISOLATED_SELECTION.read_bytes())
        if decision.get("status") != "selected" or decision.get("ranking_method") != ISOLATED_METHOD:
            raise ValueError("A selected isolated-window study head is required before rendering")
        if original:
            raise ValueError("Rotating anchors require fresh selection after the revised cue gate")
    pairs, paths = frozen_inputs()
    if original:
        history = json.loads((original / "inventory.json").read_bytes())
        verified = json.loads((original / "verified.json").read_bytes())
        if (root.resolve() == original.resolve() or
                history["study_protocol_sha256"] != file_sha256(ORIGINAL_PROTOCOL) or
                verified["inventory_sha256"] != file_sha256(original / "inventory.json")):
            raise ValueError("Invalid historical inventory or destination")
    root.mkdir(parents=True, exist_ok=True)
    if (root / "inventory.json").exists():
        raise FileExistsError(f"Finished run at {root}. Choose a new output path for another run.")
    panels, excluded = {}, {}
    analysis_root = (original or root) / "cache/analysis"
    protocol = ROTATED_PROTOCOL if rotated else (PROTOCOL if original else ORIGINAL_PROTOCOL)
    for pair in pairs:
        pid = pair["pair_id"]
        if rotated and pid not in FINAL_PAIRS:
            excluded[pid] = dict(pair=pair, reasons=["frozen_run02_grid_exclusion"])
            continue
        directory = root / pid
        print(pid, "prepare", flush=True)
        if not directory.exists():
            with publish_dataset(directory) as stage:
                if original:
                    carry_selection(stage, directory, original, pair)
                else:
                    prepare(stage, pair, paths, root / "cache", rotated=rotated)
        if (directory / "exclusion.json").exists():
            excluded[pid] = json.loads((directory / "exclusion.json").read_bytes())
            print(pid, "excluded", excluded[pid]["reasons"], flush=True)
            continue
        dest = directory / "stimuli"
        panel = json.loads((directory / "panel.json").read_bytes())
        if panel["study_protocol_sha256"] != file_sha256(protocol) or (
                original and panel.get("revision") != REVISION) or (
                rotated and panel.get("revision") != ROTATED_REVISION):
            raise ValueError(f"Existing panel at {directory} has a different study contract")
        if not dest.exists():
            print(pid, "P04 render", flush=True)
            try:
                with publish_dataset(dest) as stage:
                    study(stage, SimpleNamespace(panel=directory / "panel.json", steps=80,
                             analysis_root=analysis_root, merge_algorithm=MERGE_ALGORITHM_VERSION_V2))
            except (LocalGridFailure, CueAlignmentError) as error:
                if not (rotated or original):
                    raise
                record = dict(pair=pair, reasons=[dict(code="local_grid_gate", detail=str(error))],
                              time=datetime.now(timezone.utc).isoformat(), affected="all seven conditions")
                write_json(directory / "exclusion.json", record)
                excluded[pid] = record
                continue
        panels[pid] = dest
        if (directory / "secondary.json").exists():
            continue
        rows = json.loads((dest / "results.json").read_bytes())
        manifest = json.loads((directory / "selection.json").read_bytes())
        cue = manifest["candidate_generation"]["candidates"][0]
        with (directory / "pool.csv").open(encoding="utf-8") as f:
            scores = {r["id"]: r for r in csv.DictReader(f)}
        metrics = []
        for row in rows:
            if row["condition"] == "anchor":
                continue
            pcm, sr = sf.read(dest / row["wav"], always_2d=True, dtype="float32")
            inputs = [RenderedTransitionInput(row["candidate_id"], row["condition"], pcm.T, sr,
                      5*sr, 5*sr+row["bridge_samples"], 16, cue["source_bpm"])]
            ranked = rank_rendered_transitions(inputs)
            metrics.append(dict(wav=row["wav"], selector=row["selector"], condition=row["condition"],
                     ssl=float(scores[row["candidate_id"]]["ssl"]), rule=float(scores[row["candidate_id"]]["rule"]),
                     render_score=ranked.scores[0].total_score, proxy_raw=row["proxy_raw"]["loss"]))
        temporary = directory / "secondary.pending.json"
        write_json(temporary, metrics)
        temporary.replace(directory / "secondary.json")
        print(pid, "nine verified WAVs" if rotated else "seven verified WAVs", flush=True)
    write_json(root / "inventory.json", dict(pairs=list(panels), excluded=excluded,
               wav_count=(9 if rotated else 7)*len(panels),
               study_protocol_sha256=file_sha256(protocol), population_commit=FREEZE,
               revision=ROTATED_REVISION if rotated else (REVISION if original else "original"),
               original=str(original) if original else None))


def package_final(root):
    inventory = json.loads((root / "inventory.json").read_bytes())
    panels = {pid:root / pid / "stimuli" for pid in inventory["pairs"]}
    if not panels:
        return
    with publish_dataset(root / "blind") as folder:
        for person in ("VP01","VP02","VP03"):
            package(panels, folder / person, person, "final")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE / "run02")
    parser.add_argument("--preanalyse-after", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--record-grid-exclusions", action="store_true")
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--revise-from", type=Path, help="Reuse frozen selectors and correct the local render")
    parser.add_argument("--historical", action="store_true", help="Reproduce the withdrawn run01 protocol")
    parser.add_argument("--protocol-v2", action="store_true", help="New single-factor render with three anchors per pair")
    args = parser.parse_args()
    torch.set_num_threads(4)
    with threadpool_limits(limits=4):
        if args.protocol_v2:
            if (args.historical or args.package_only or args.revise_from or args.preanalyse_after is not None
                    or args.record_grid_exclusions or args.output.resolve() in ((BASE / "run01").resolve(), (BASE / "run02").resolve())):
                parser.error("--protocol-v2 requires a separate output directory and a fresh selection")
            run(args.output, rotated=True)
        elif args.package_only:
            package_final(args.output)
        elif args.record_grid_exclusions:
            record_grid_exclusions(args.output)
        elif args.preanalyse_after is None:
            if args.historical and args.revise_from:
                parser.error("Choose either the historical or revised render")
            run(args.output, None if args.historical else (args.revise_from or BASE / "run01"))
            if not (args.output / "blind").exists():
                package_final(args.output)
        else:
            preanalyse(args.output, args.preanalyse_after, args.workers)
