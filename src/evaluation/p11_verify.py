"""Verify the closed P11 export without decoding final audio for playback."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import soundfile as sf

from src.evaluation.comparison_study import SELECTORS, final_ssl_provenance, measure_clip
from src.evaluation.p11_alignment import check_timing, sample_hash
from src.evaluation.p11_stimuli import BASE, ORIGINAL_PROTOCOL, PROTOCOL, REVISION, frozen_inputs
from src.features.p07_mert import file_sha256
from src.features.p07_population import FREEZE
from src.features.p08_pairs import rng_for
from src.features.p08_windows import read_json


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify(root):
    frozen, _ = frozen_inputs()
    inventory = read_json(root / "inventory.json")
    revised = inventory.get("revision") == REVISION
    protocol = PROTOCOL if revised else ORIGINAL_PROTOCOL
    if revised:
        require(not (root / "sessions").exists(), "Unexpected secondary participant directory")
        original = Path(inventory["original"])
        historical = read_json(original / "inventory.json")
        historical_receipt = read_json(original / "verified.json")
        require(historical_receipt["inventory_sha256"] == file_sha256(original / "inventory.json") and
                historical["study_protocol_sha256"] == file_sha256(ORIGINAL_PROTOCOL) and
                all(inventory["excluded"].get(k) == v for k, v in historical["excluded"].items()),
                "Historical population or exclusion changed")
    included = inventory["pairs"]
    require(set(included).isdisjoint(inventory["excluded"]) and
            set(included) | set(inventory["excluded"]) == {p["pair_id"] for p in frozen}, "Wrong population")
    require(inventory["study_protocol_sha256"] == file_sha256(protocol), "Study protocol differs")
    require(inventory["population_commit"] == FREEZE and inventory["wav_count"] == 7 * len(included),
            "Wrong inventory contract")
    cells = [(s, c) for s in SELECTORS for c in ("E", "D")] + [("rule", "anchor")]
    results, summaries, session_ids = {}, [], {}
    levels, peaks, durations = [], [], []
    for pair in frozen:
        pid = pair["pair_id"]
        if pid not in included:
            exclusion = read_json(root / pid / "exclusion.json")
            require(inventory["excluded"][pid] == exclusion and exclusion["pair"] == pair
                    and exclusion["reasons"] and exclusion["time"], "Exclusion identity differs")
            for reason in exclusion["reasons"]:
                if isinstance(reason, dict) and "grid_receipt" in reason:
                    path = Path(reason["grid_receipt"])
                    receipt = read_json(path)
                    require(file_sha256(path) == reason["sha256"] and
                            receipt["sha256"] == pair[reason["role"]]["sha256"] and
                            receipt["grid"]["fallback_used"] and
                            receipt["diagnostics"]["acceptance"]["accepted"] is False and
                            receipt["diagnostics"]["acceptance"]["reasons"] == reason["reasons"],
                            "Grid rejection cannot be traced to the frozen recording")
            continue
        directory = root / pid
        selection = read_json(directory / "selection.json")
        require(selection["pair"] == pair and selection["pool_sha256"] == file_sha256(directory / "pool.csv"),
                "Wrong selection binding")
        with (directory / "pool.csv").open(encoding="utf-8") as f:
            pool = list(csv.DictReader(f))
        ids = sorted(r["id"] for r in pool)
        require(len(ids) == len(set(ids)) == selection["common"], "Invalid common pool")
        winners = {k:min(pool, key=lambda r:(-float(r[k]), r["id"]))["id"] for k in ("ssl","rule")}
        winners["random"] = rng_for("random",pid,seed=20261119).choice(ids)
        require(winners == selection["selectors"], "Selector replay differs")
        contract = read_json(directory / "stimuli/protocol.json")
        require(contract["ssl_provenance"] == final_ssl_provenance(selection,winners["ssl"]) and
                contract["panel"]["study_protocol_sha256"] == file_sha256(protocol) and
                contract["panel_sha256"] == file_sha256(directory / "panel.json") and
                contract["panel"]["pair_manifest_sha256"] == file_sha256(directory / "selection.json") and
                contract["panel"]["population_commit"] == FREEZE and contract["panel"]["selectors"] == winners and
                contract["updates"] == 80 and contract["objective_version"] == 4 and
                contract["sample_rate"] == 44100 and contract["fir_taps"] == 511 and
                contract["bars"] == 4 and contract["beats"] == 16 and contract["control_points"] == 32 and
                contract["low_hz"] == 180 and contract["renderer"] == "DifferentiableTwoBandRenderer",
                "Wrong P04 study contract")
        rows = read_json(directory / "stimuli/results.json")
        expected_frames = 13*44100 + min(row["bridge_samples"] for row in rows)
        if revised:
            previous = original / pid
            prior_geometry = {r["candidate_id"]: r["geometry"] for r in
                              read_json(previous / "stimuli/results.json")}
            require(contract["panel"].get("revision") == REVISION and
                    file_sha256(previous / "selection.json") == file_sha256(directory / "selection.json") and
                    contract["panel"]["original_panel_sha256"] == file_sha256(previous / "panel.json"),
                    "Original selector contract differs")
            sizes = {(directory / "stimuli" / r["wav"]).stat().st_size for r in rows}
            require(len(sizes) == 1, "File size discloses selector")
        secondary = read_json(directory / "secondary.json")
        require([(r["selector"], r["condition"]) for r in rows] == cells and
                [(r["selector"], r["condition"]) for r in secondary] == cells[:-1], "Incomplete metrics")
        duplicate = {}
        for row in rows:
            coord = (pid,row["selector"],row["condition"])
            require(coord not in results and row["split"] == "final" and
                    row["pair"] == [pair[k]["sha256"] for k in ("source", "target")] and
                    row["candidate_id"] == winners[row["selector"]] and
                    row["protocol_sha256"] == file_sha256(directory / "stimuli/protocol.json"), "Wrong cell")
            clip = directory / "stimuli" / row["wav"]
            digest = file_sha256(clip)
            info = sf.info(clip)
            require(digest == row["wav_sha256"] and info.subtype == "PCM_24" and info.channels == 2 and
                    info.samplerate == 44100 and info.frames ==
                    (expected_frames if revised else 13*44100+row["bridge_samples"]), "Invalid clip")
            if revised:
                g = row["geometry"]
                prior = prior_geometry[row["candidate_id"]]
                require(all(g[name] == prior[name] for name in ("source_beats", "target_beats",
                            "source_cut_sample", "target_cut_sample", "target_sample_scale")),
                        "Native beat boundaries or cutpoints were changed")
                align = g["local_alignment"]
                require(0 < row["suffix_frames"] <= 8*44100 and
                        row["suffix_frames"] + row["bridge_samples"] + 5*44100 == info.frames,
                        "Wrong suffix crop")
                aligned_path = directory / "stimuli" / align["file"]
                require(file_sha256(aligned_path) == align["sha256"], "Local bridge differs")
                raw, sr = sf.read(aligned_path, always_2d=True, dtype="float32")
                marks, guard = align["output_beats"], align["guard_frames"]
                require(sr == 44100 and raw.shape[1] == 2 and guard == round(.010*sr) and
                        marks[0] == 0 and len(raw) == marks[-1] == row["bridge_samples"]
                        and len(align["intervals"]) == 16, "Wrong local bridge geometry")
                check_timing(g["source_beats"], marks, len(raw), sr)
                for left, right, part in zip(marks[:-1], marks[1:], align["intervals"], strict=True):
                    require(sample_hash(raw[left:left+guard].T) == part["head_sha256"] and
                            sample_hash(raw[right-guard:right].T) == part["tail_sha256"],
                            "Local PCM boundary differs from original B samples")
            loudness = row["loudness"]
            pcm, _ = sf.read(clip, dtype="float32", always_2d=True)
            require(measure_clip(pcm.T) == (loudness["final_lufs"], loudness["final_dbtp"]),
                    "PCM loudness or true peak differs from the manifest")
            durations.append(info.duration)
            diff = loudness["final_lufs"] - loudness["pair_target_lufs"]
            require(abs(diff) <= .2 and loudness["final_dbtp"] <= -.99, "Invalid playback levels")
            levels.append(abs(diff))
            peaks.append(loudness["final_dbtp"])
            require(duplicate.setdefault((row["candidate_id"],row["condition"]),digest) == digest,
                    "Coincident selection rendered differently")
            results[coord] = digest
        summaries.append(dict(pair=pid, cues=len(pool), distinct_selectors=len(set(winners.values())),
                              ssl_equals_rule=winners["ssl"] == winners["rule"]))
        if revised:
            summaries[-1].update(frames_per_clip=expected_frames, bytes_per_clip=sizes.pop(),
                                 suffix_frames_range=[min(r["suffix_frames"] for r in rows),
                                                      max(r["suffix_frames"] for r in rows)],
                                 distinct_cues=len(prior_geometry))
    for person in ("VP01","VP02","VP03") if included else ():
        session = root / "blind" / person
        key = read_json(session / "zuordnung.json")
        page = (session / "player/index.html").read_text(encoding="utf-8")
        session_ids[person] = hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()
        expected_files = {code + ".wav" for code in key} | {"index.html"}
        require({f.name for f in (session / "player").iterdir()} == expected_files, "Unexpected public files")
        public_data = re.search(r"^const session = (.+);$", page, flags=re.MULTILINE)
        expected_pages = [[f"{index:02d}-{chr(65 + pos)}" for pos in range(7)]
                          for index in range(1, len(included) + 1)]
        require(public_data and json.loads(public_data[1]) == dict(person=person, split="final",
                session_id=session_ids[person], pages=expected_pages), "Incorrect player session")
        require(len(key) == len(results) and
                not any(v["cue"] in page for v in key.values()), "Invalid blind player")
        order = sorted(included)
        rng_for("panels", person, seed=20261120).shuffle(order)
        for index, pid in enumerate(order, 1):
            permuted = cells.copy()
            rng_for("clips", person, pid, seed=20261120).shuffle(permuted)
            for position, (selector, condition) in enumerate(permuted):
                entry = key[f"{index:02d}-{chr(65 + position)}"]
                require((entry["pair"], entry["selector"], entry["condition"]) == (pid, selector, condition),
                        "Randomized presentation order differs from the frozen seed")
        coords = set()
        for code, entry in key.items():
            coord = (entry["pair"],entry["selector"],entry["condition"])
            require(results[coord] == entry["sha256"] == file_sha256(session / "player" / (code+".wav")),
                    "Wrong blind mapping")
            coords.add(coord)
        require(coords == set(results), "Incomplete blind session")
    if revised:
        require(set(historical_receipt["session_ids"].values()).isdisjoint(session_ids.values()),
                "A withdrawn run01 session would be accepted as run02")
    result = dict(panels=summaries, exclusions=inventory["excluded"], clips=len(results),
                inventory_sha256=file_sha256(root / "inventory.json"), study_protocol_sha256=file_sha256(protocol),
                duration_seconds=[min(durations), max(durations)] if durations else [], session_ids=session_ids,
                max_abs_lufs_error=max(levels,default=None), max_true_peak_dbtp=max(peaks,default=None),
                sessions=3 if included else 0)
    if revised:
        result.update(revision=REVISION, historical_inventory_sha256=historical_receipt["inventory_sha256"],
                      historical_protocol_sha256=file_sha256(ORIGINAL_PROTOCOL))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=BASE / "run02")
    root = parser.parse_args().root
    result = verify(root)
    with (root / "verified.json").open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(f"{len(result['panels'])} panels, {len(result['exclusions'])} exclusions, "
          f"{result['clips']} clips, {result['sessions']} blind sessions")
