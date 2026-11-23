"""Prepare checked listening material and seal neutral responses on the research computer."""

from collections import Counter
from contextlib import closing
import csv
import json
import math
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import string

import soundfile as sf

from hoertest.session import (CURRENT_FIXED, RUN02, SELECTORS, VERSION, WEB_VERSION, Session, digest, file_sha256,
                             layout, public_layout, read, utc, web_protocol)
from src.features.p07_population import POPULATION, committed
from src.features.p08_pairs import publish_dataset, rng_for


REVISION = "cue_grid_regression_v3"
CELLS = {(s, c) for s in SELECTORS for c in ("E", "D", "anchor")}
PROTOCOL = Path("docs/EVALUATION_PROTOCOL_V2.md")
WEB_PROTOCOL = Path(__file__).resolve().parents[2] / "hoertest" / "PROTOKOLL.md"
RUN02_DOCS = WEB_PROTOCOL.parents[1] / "docs/masterarbeit/review_jp_20261118/p11"
FINAL_PAIRS = {"P01", "P02", "P03", "P06", "P07", "P09", "P10"}


def check_final_panel(directory, contract, rows, pair):
    from src.evaluation.comparison_study import CEILING_DBTP, RATE, TARGET_LUFS, final_ssl_provenance, measure_clip

    panel = contract["panel"]
    inputs = directory.parent
    selection = read(inputs / "selection.json")
    if (contract["panel_sha256"] != file_sha256(inputs / "panel.json") or panel != read(inputs / "panel.json")
            or selection["pair"] != pair or panel["pair_manifest_sha256"] != file_sha256(inputs / "selection.json")
            or selection["pool_sha256"] != file_sha256(inputs / "pool.csv") or contract["updates"] != 80):
        raise ValueError("Final study panel differs from the bound selection or rendering budget")
    with (inputs / "pool.csv").open(newline="", encoding="utf-8") as stream:
        pool = list(csv.DictReader(stream))
    ids = sorted(r["id"] for r in pool)
    if not pool or len(ids) != len(set(ids)) or len(ids) != selection["common"]:
        raise ValueError("Invalid common cue pool")
    winners = {name:min(pool, key=lambda r:(-float(r[name]), r["id"]))["id"] for name in ("ssl", "rule")}
    winners["random"] = rng_for("random", panel["pair_id"], seed=20261119).choice(ids)
    if winners != panel["selectors"] or winners != selection["selectors"]:
        raise ValueError("Final selector replay differs")
    if final_ssl_provenance(selection, winners["ssl"], rotated=True) != contract["ssl_provenance"]:
        raise ValueError("Final isolated-window head differs")
    targets = {r["loudness"]["pair_target_lufs"] for r in rows}
    if len(targets) != 1 or next(iter(targets)) > TARGET_LUFS:
        raise ValueError("Inconsistent pair loudness target")
    target, = targets
    for r in rows:
        timing = r["geometry"]["tempo_alignment"]
        errors = [timing[k] for k in ("source_residual_ms", "target_residual_ms", "beat_offset_ms", "span_error_ms")]
        if (timing["contract"] != REVISION or timing["max_error_ms"] != 20.
                or not all(math.isfinite(v) and 0 <= v <= 20.+1e-8 for v in errors)):
            raise ValueError("Study geometry violates the v2 timing gate")
        audio, rate = sf.read(directory / r["wav"], always_2d=True, dtype="float32")
        lufs, peak = measure_clip(audio.T)
        if (rate != RATE or abs(lufs - target) > .2 or peak > CEILING_DBTP+.01
                or lufs != r["loudness"]["final_lufs"] or peak != r["loudness"]["final_dbtp"]):
            raise ValueError("Final playback measurement differs")


def master_panel(directory, split, *, run02_cells=None):
    contract = read(directory / "protocol.json")
    panel = contract["panel"]
    rows = read(directory / "results.json")
    protocol_sha = file_sha256(directory / "protocol.json")
    revision, cells = REVISION, CELLS
    protocol = PROTOCOL
    if run02_cells is not None:
        revision = "local_grid_equal_duration_v2"
        cells = CELLS - {("ssl", "anchor"), ("random", "anchor")}
        protocol = RUN02_DOCS / "studienprotokoll.md"
    if (panel.get("revision") != revision or panel["split"] != split or len(rows) != len(cells)
            or {(r["selector"], r["condition"]) for r in rows} != cells):
        raise ValueError(f"Expected {len(cells)} {revision} {split} masters in {directory}")
    pid = panel["pair_id"]
    if split == "final" and panel.get("study_protocol_sha256") != file_sha256(protocol):
        raise ValueError(f"Study protocol differs for {pid}")
    tracks = rows[0]["pair"]
    if split == "final":
        pair = next(p for p in json.loads(committed(POPULATION))["pairs"] if p["pair_id"] == pid)
        if tracks != [pair[side]["sha256"] for side in ("source", "target")]:
            raise ValueError(f"Audio identity differs for {pid}")
        if run02_cells is None:
            check_final_panel(directory, contract, rows, pair)
    assets = []
    for row in rows:
        path = (directory / row["wav"]).resolve()
        if run02_cells is not None and (row["wav_sha256"], row["candidate_id"]) != run02_cells.get(
                (pid, row["selector"], row["condition"])):
            raise ValueError(f"Clip differs from the verified Run02 assignment: {pid} {row['wav']}")
        info = sf.info(path)
        if (row["split"] != split or row["pair"] != tracks
                or row["protocol_sha256"] != protocol_sha
                or row["candidate_id"] != panel["selectors"][row["selector"]]
                or info.subtype != "PCM_24" or info.channels != 2 or info.samplerate != 44100
                or info.frames <= 0 or row["wav_sha256"] != file_sha256(path)):
            raise ValueError(f"Invalid master {path}")
        assets.append(dict(path=str(path), frames=info.frames, sha256=row["wav_sha256"],
                           selector=row["selector"], condition=row["condition"]))
    if len({a["frames"] for a in assets}) != 1:
        raise ValueError(f"Unequal clip durations for {pid}")
    secondary_file = directory.parent / "secondary.json"
    if split == "final" or secondary_file.is_file():
        secondary = read(secondary_file)
        metrics = {(r["selector"], r["condition"]): r for r in secondary}
        if len(secondary) != 6 or len(metrics) != 6:
            raise ValueError(f"Incomplete secondary metrics for {pid}")
        for asset in assets:
            if asset["condition"] != "anchor":
                ref = metrics[asset["selector"], asset["condition"]]
                if ref["wav"] != Path(asset["path"]).name:
                    raise ValueError(f"Secondary metric refers to a different clip in {pid}")
                asset["metrics"] = dict(proxy=-ref["proxy_raw"], rule=ref["rule"],
                                        render=ref["render_score"], ssl=ref["ssl"])
    return pid, assets


def practice_clips(package):
    # Historical blind development package, with its original clip hashes and split.
    html = (package / "player/index.html").read_text(encoding="utf-8")
    session = re.search(r"^const session = (.+);$", html, re.MULTILINE)
    if not session or json.loads(session[1]).get("split") != "development":
        raise ValueError("Practice requires a development player package")
    mapping = read(package / "zuordnung.json")
    clips = []
    packed = json.loads(session[1])
    if packed.get("session_id") != digest(mapping):
        raise ValueError("Development package key differs")
    for code in sorted(mapping)[:2]:
        path = (package / "player" / (code + ".wav")).resolve()
        if file_sha256(path) != mapping[code]["sha256"]:
            raise ValueError("Practice audio changed")
        frames, rate = sf.info(path).frames, sf.info(path).samplerate
        if rate != 44100 or frames <= 0:
            raise ValueError("Invalid practice audio")
        clips.append(dict(path=str(path), frames=frames, sha256=mapping[code]["sha256"]))
    if len(clips) != 2:
        raise ValueError("Two practice clips required")
    return clips


def prepare(root, directories, practice, split, *, institute=False, fixed_rule_anchors=False):
    if fixed_rule_anchors and not (institute and split == "final"):
        raise ValueError("Fixed rule anchors require a final institute study")
    panels = dict(master_panel(d, split) for d in directories)
    if not panels or len(panels) != len(directories) or (split == "final" and panels.keys() != FINAL_PAIRS):
        raise ValueError("Missing, duplicate or unexpected study pairs")
    material = None
    if fixed_rule_anchors:
        material = CURRENT_FIXED
        panels = {pair: [asset for asset in assets if asset["condition"] != "anchor" or asset["selector"] == "rule"]
                  for pair, assets in panels.items()}
    publish_study(root, panels, practice, split, institute, material=material)


def prepare_run02(root, source, practice):
    receipt = read(RUN02_DOCS / "run02_verified.json")
    mapping = read(source / "blind/VP01/zuordnung.json")
    if (digest(mapping) != receipt["session_ids"]["VP01"] or len(mapping) != 49
            or receipt["study_protocol_sha256"] != file_sha256(RUN02_DOCS / "studienprotokoll.md")):
        raise ValueError("Run02 assignment or study protocol differs from the verified release")
    approved = {(r["pair"], r["selector"], r["condition"]): (r["sha256"], r["cue"]) for r in mapping.values()}
    panels = dict(master_panel(source / pid / "stimuli", "final", run02_cells=approved) for pid in sorted(FINAL_PAIRS))
    if len(approved) != 49 or panels.keys() != FINAL_PAIRS:
        raise ValueError("Expected all seven verified Run02 pairs")
    publish_study(root, panels, practice, "final", True, material=RUN02)


def publish_study(root, panels, practice, split, institute, *, material=None):
    if institute and Path(root).resolve().is_relative_to(WEB_PROTOCOL.parent):
        raise ValueError("Private Studiendaten außerhalb des Anwendungsordners vorbereiten.")
    protocol = RUN02_DOCS / "studienprotokoll.md" if material == RUN02 else PROTOCOL
    key = dict(seed=secrets.token_hex(32), split=split, panels=panels, practice=practice_clips(practice),
               version=VERSION, protocol_sha256=file_sha256(protocol))
    if material is not None:
        key["material"] = material
    if split == "final":
        groups = {p["pair_id"]:[p[s]["recording_group_id"] for s in ("source","target")]
                  for p in json.loads(committed(POPULATION))["pairs"] if p["pair_id"] in panels}
        if len({g for pair in groups.values() for g in pair}) != 2 * len(panels):
            raise ValueError("The final pairs must have disjoint recording groups")
        key["groups"] = groups
    with publish_dataset(root) as stage:
        if institute:
            key.update(version=WEB_VERSION, procedure_sha256=file_sha256(web_protocol(key)))
            media = stage / "media"
            media.mkdir()
            for assets in [key["practice"], *panels.values()]:
                for asset in assets:
                    relative = Path("media") / (asset["sha256"] + ".wav")
                    target = stage / relative
                    if not target.exists():
                        shutil.copyfile(asset["path"], target)
                        if file_sha256(target) != asset["sha256"]:
                            raise ValueError("Copied clip differs from the checked master")
                    asset["path"] = relative.as_posix()
        (stage / "study_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
        with closing(sqlite3.connect(stage / "responses.sqlite")) as db, db:
            db.executescript("""
                CREATE TABLE sessions (
                    ordinal INTEGER PRIMARY KEY, person TEXT NOT NULL UNIQUE, sid TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL, layout TEXT NOT NULL, key_hash TEXT NOT NULL
                );
                CREATE TABLE events (
                    seq INTEGER PRIMARY KEY, sid TEXT NOT NULL, stamp TEXT NOT NULL, data TEXT NOT NULL
                );
            """)


def neutral_check(records):
    """List anomalies using only codes present in the sealed, still-blind originals."""
    duplicates = {}
    for field in ("person", "ordinal", "sid"):
        counts = Counter(r[field] for r in records)
        duplicates[field] = sorted(k for k, n in counts.items() if n > 1)
    panels = []
    for r in records:
        state = r["state"]
        assigned = set()
        for i, page in enumerate(r["pages"]):
            expected = [f"{i:02}-{letter}" for letter in string.ascii_uppercase[:2 if i == 0 else 7]]
            actual = [clip["code"] for clip in page]
            assigned.update(actual)
            bad_hash = [c["code"] for c in page if not re.fullmatch("[0-9a-f]{64}", str(c.get("sha256", "")))]
            scores = state["ratings"]
            invalid = [c for c in expected if type(scores.get(c)) is not int or not 0 <= scores[c] <= 100]
            unheard = [c for c in expected if c not in state["heard"] or state["plays"].get(c, 0) < 1]
            if expected != actual or bad_hash or invalid or unheard:
                panels.append(dict(sid=r["sid"], page=i, invalid_layout=actual != expected,
                                   invalid_hash=bad_hash, missing_or_invalid_rating=invalid,
                                   incomplete_playback=unheard))
        extra = (set(state["ratings"]) | set(state["heard"]) | set(state["plays"])) - assigned
        if extra:
            panels.append(dict(sid=r["sid"], unexpected_codes=sorted(extra)))
    return dict(completed_sessions=len(records), duplicate_ids=duplicates, anomalies=panels)


def seal(root, destination):
    """Copy completed neutral originals in one consistent read transaction before opening the key."""
    version = read(root / "study_key.json")["version"]
    if version not in (VERSION, WEB_VERSION):
        raise ValueError("Unknown study version")
    with sqlite3.connect(root / "responses.sqlite") as db, publish_dataset(destination) as out:
        db.execute("BEGIN")
        files, incomplete, records = {}, [], []
        for ordinal, person, sid, raw, pages, key_hash in db.execute("SELECT * FROM sessions ORDER BY ordinal"):
            state = json.loads(raw)
            if not state["finished"]:
                incomplete.append(dict(person=person, sid=sid))
                continue
            events = [dict(time=t, **json.loads(e)) for t,e in db.execute(
                "SELECT stamp,data FROM events WHERE sid=? ORDER BY seq", (sid,))]
            record = dict(version=version, ordinal=ordinal, person=person, sid=sid, key_hash=key_hash,
                          pages=json.loads(pages), state=state, events=events)
            records.append(record)
            path = out / (sid + ".json")
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            files[path.name] = file_sha256(path)
        if not files and version == VERSION:
            raise ValueError("No completed sessions to seal")
        audit_path = out / "neutral_check.json"
        audit_path.write_text(json.dumps(neutral_check(records), indent=2), encoding="utf-8")
        receipt = dict(created=utc(), files=files, incomplete=incomplete, neutral_check_sha256=file_sha256(audit_path))
        if version == WEB_VERSION:
            receipt["study_key_sha256"] = file_sha256(root / "study_key.json")
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
