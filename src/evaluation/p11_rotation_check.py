"""Audit the unused Run03 institute delivery and replay synthetic sessions on a disposable database."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from itertools import count
import json
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hoertest.app import checked_inventory
from hoertest.session import CURRENT_ROTATING, SELECTORS, Session, digest, file_sha256, layout, read, web_protocol
from src.evaluation.p11_session import CELLS, CURRENT_PROTOCOL, FINAL_PAIRS, PROTOCOL, practice_clips, seal
from src.evaluation.p12_descriptive import analyse


def check(ok, message):
    if not ok:
        raise ValueError(message)


def verify_sources(root, key, run, practice):
    hashes, masters, source_pairs = set(), [], []
    for pair in sorted(FINAL_PAIRS):
        source = run / pair / "stimuli"
        rows = read(source / "results.json")
        reference = {}
        for row in rows:
            sha = file_sha256(source / row["wav"])
            check(sha == row["wav_sha256"], f"Source audio hash differs for {pair}")
            reference[row["selector"], row["condition"]] = sha
        delivered = {(a["selector"], a["condition"]): a["sha256"] for a in key["panels"][pair]}
        check(len(rows) == len(key["panels"][pair]) == 9 and set(reference) == CELLS and delivered == reference,
              f"Delivered master assignments differ for {pair}")
        check(len({(root / asset["path"]).stat().st_size for asset in key["panels"][pair]}) == 1,
              f"Unequal playback sizes within {pair}")
        hashes.update(reference.values())
        masters.extend(rows)
        source_pairs.append(dict(pair=pair, eligible=read(run / pair / "selection.json")["common"]))
    training = {a["sha256"] for a in practice_clips(practice)}
    check(len(hashes) == 63 and len(training) == 2 and hashes.isdisjoint(training)
          and len(key["practice"]) == 2 and training == {a["sha256"] for a in key["practice"]}, "Invalid practice set")
    check({f.name for f in (root / "media").iterdir()} == {h + ".wav" for h in hashes | training},
          "Playback directory contains missing or unexpected assets")
    timing = ("source_residual_ms", "target_residual_ms", "beat_offset_ms", "span_error_ms")
    return dict(source_pairs=source_pairs, masters=len(masters), practice_clips=len(training),
                playback_set_sha256=digest(sorted(hashes)), all_media_sha256=digest(sorted(hashes | training)),
                max_absolute_loudness_deviation_lu=round(max(abs(r["loudness"]["pair_target_lufs"]
                                                               - r["loudness"]["final_lufs"]) for r in masters), 3),
                highest_dbtp=max(r["loudness"]["final_dbtp"] for r in masters),
                max_timing_error_ms={t: round(max(r["geometry"]["tempo_alignment"][t] for r in masters), 3)
                                     for t in timing})


def verify_assignments(mappings):
    orders, anchors, sequences = [], defaultdict(list), set()
    for mapping in mappings:
        check(len(mapping) == 51, "Expected two practice and 49 rated clips")
        order, sequence = [], []
        for page in range(1, 8):
            assets = [a for code, a in mapping.items() if code.startswith(f"{page:02}-")]
            cells = {(a["selector"], a["condition"]) for a in assets}
            anchor, = [a for a in assets if a["condition"] == "anchor"]
            pair = anchor["pair"]
            check(len(assets) == 7 and cells == {c for c in CELLS if c[1] != "anchor"} | {(anchor["selector"], "anchor")}
                  and all(a["pair"] == pair for a in assets), "Incorrect seven-clip panel")
            anchors[pair].append(anchor["selector"])
            order.append(pair)
            sequence.extend(a["sha256"] for a in assets)
        check(set(order) == FINAL_PAIRS, "Session omits a final pair")
        check(sorted(Counter(anchors[p][-1] for p in order).values()) == [2, 2, 3], "Unbalanced within-session anchors")
        orders.append(order)
        sequences.add(tuple(sequence))
    n = len(mappings)
    for pair, selectors in anchors.items():
        for start in range(0, n - 2, 3):
            check(set(selectors[start:start + 3]) == set(SELECTORS), f"Unbalanced anchor block for {pair}")
    for start in range(0, n - 6, 7):
        check(all(set(position) == FINAL_PAIRS for position in zip(*orders[start:start+7], strict=True)),
              "Unbalanced seven-session position block")
    check(len(sequences) == n, "Repeated complete playback sequence")
    return dict(sessions=n, anchor_blocks_per_pair=n // 3, latin_blocks=n // 7)


def empty_database(root):
    uri = (root / "responses.sqlite").as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        totals = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("sessions", "events")}
    check(not any(totals.values()), "An unused delivery database is required")
    return totals


def replay(root, key, scratch):
    shutil.copyfile(root / "study_key.json", scratch / "study_key.json")
    with closing(sqlite3.connect((root / "responses.sqlite").as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(scratch / "responses.sqlite")) as target:
            source.backup(target)
    mappings = []
    for seat in range(6):
        setting = ("Institut", "anderer Hörplatz")[seat % 2]
        s = Session(scratch, f"Technikprobe{seat+1}", verified_key=key)
        s.event(dict(kind="begin", page=-1, profile=dict(music="mittel", dj="wenig", dance="mittel",
                                                        hearing="keine Angabe", setting=setting)))
        for page in range(8):
            for code in s.state()["codes"]:
                asset = s.mapping[code]
                value = 1
                if page and asset["condition"] != "anchor":
                    if setting == "Institut" and asset["selector"] == "ssl":
                        value += 3
                    value += 3 * (asset["condition"] == "D")
                for event in ("play", "ended", "rating"):
                    s.event(dict(kind=event, page=page, code=code, value=value))
            s.event(dict(kind="next", page=page))
        check(s.state()["done"], "Technical session did not finish")
        mappings.append(s.mapping)
    rotation = verify_assignments(mappings)
    originals = scratch / "sealed"
    seal(scratch, originals)
    report = analyse(originals, scratch / "study_key.json", "final")
    audit = read(originals / "neutral_check.json")
    check(not audit["anomalies"] and not any(audit["duplicate_ids"].values()) and not report["exclusions"],
          "Sealed replay contains invalid or duplicate observations")
    check(report["started_sessions"] == report["completed_sessions"] == 6 and report["valid_panels"] == 42
          and report["analysis_scale"] == [1, 7]
          and report["pair_weighted_effects"]["ssl_minus_rule"] == 1.5
          and report["pair_weighted_effects"]["direct_minus_equal"] == 3, "P12 aggregate differs")
    for pair in FINAL_PAIRS:
        check(all(a["n"] == 2 for a in report["anchors"][pair]["by_selector"].values()), "P12 anchor counts differ")
    by_setting = {}
    for setting, expected in (("Institut", 3), ("anderer Hörplatz", 0)):
        group = report["by_listening_setting"][setting]
        check(group["completed_sessions"] == 3 and group["valid_panels"] == 21
              and group["pair_weighted_effects"]["ssl_minus_rule"] == expected, "P12 setting contrasts differ")
        by_setting[setting] = dict(completed_sessions=3, scored_panels=21, ssl_minus_rule=expected)
    return dict(**rotation, scored_panels=report["valid_panels"], each_anchor_per_pair=2, ssl_minus_rule=1.5,
                direct_minus_equal=3, analysis_scale=report["analysis_scale"], by_listening_setting=by_setting,
                sessions_by_rating_scale=report["sessions_by_rating_scale"], human_ratings=0)


def verify(root, run, practice):
    root = root.resolve()
    key = checked_inventory(root)
    check(key["split"] == "final" and key["material"] == CURRENT_ROTATING and key["panels"].keys() == FINAL_PAIRS,
          "Expected the final Run03 rotating package")
    check(key["render_protocol_sha256"] == file_sha256(PROTOCOL)
          and key["protocol_sha256"] == file_sha256(CURRENT_PROTOCOL), "Render or current protocol differs")
    key_hash, db_hash = (file_sha256(root / name) for name in ("study_key.json", "responses.sqlite"))
    empty_database(root)
    material = verify_sources(root, key, run, practice)
    layouts = [layout(key, seat, f"technical-order-{seat}") for seat in range(21)]
    design = verify_assignments(layouts)
    mapping = layouts[0].values()
    playback_bytes = sum((root / a["path"]).stat().st_size for a in mapping)
    with TemporaryDirectory(prefix="beatbridge-rotation-") as temporary:
        with patch("hoertest.session.time.time", side_effect=count(0, 60).__next__):
            technical = replay(root, key, Path(temporary))
    counts = empty_database(root)
    check(key_hash == file_sha256(root / "study_key.json") and db_hash == file_sha256(root / "responses.sqlite"),
          "Delivery key or response database changed")
    return dict(material=key["material"], render=run.name, study_key_sha256=key_hash,
                render_protocol_sha256=key["render_protocol_sha256"], protocol_sha256=key["protocol_sha256"],
                procedure_sha256=file_sha256(web_protocol(key)), **material, rated_clips_per_session=49,
                audio_bytes_per_session_including_practice=playback_bytes, layout_check=design,
                technical_replay=technical, unused_delivery_database=counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--run", type=Path, default=Path("output/review_jp_20261118/p11_hoerversuch/run03"))
    parser.add_argument("--practice", type=Path, default=Path("output/review_jp_20261118/p11_hoerversuch/pilot02"))
    parser.add_argument("--output", type=Path, help="Write the public summary to a new file")
    args = parser.parse_args()
    summary = json.dumps(verify(args.root, args.run, args.practice), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(summary)
    else:
        print(summary, end="")
