"""Private master inventory, counterbalancing and durable state for the supervised study."""

from collections import Counter
from contextlib import closing
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re
import secrets
import sqlite3
import string
import time

import soundfile as sf

from src.features.p07_mert import file_sha256
from src.features.p07_population import POPULATION, committed
from src.features.p08_pairs import publish_dataset, rng_for


VERSION = "p11-local-v2.1"
REVISION = "cue_grid_regression_v3"
SELECTORS = ("ssl", "rule", "random")
CELLS = {(s, c) for s in SELECTORS for c in ("E", "D", "anchor")}
PROTOCOL = Path("docs/EVALUATION_PROTOCOL_V2.md")
FINAL_PAIRS = {"P01", "P02", "P03", "P06", "P07", "P09", "P10"}


def read(path):
    return json.loads(path.read_bytes())


def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


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


def master_panel(directory, split):
    contract = read(directory / "protocol.json")
    panel = contract["panel"]
    rows = read(directory / "results.json")
    protocol_sha = file_sha256(directory / "protocol.json")
    if (panel.get("revision") != REVISION or panel["split"] != split or len(rows) != 9
            or {(r["selector"], r["condition"]) for r in rows} != CELLS):
        raise ValueError(f"Expected nine revised {split} masters in {directory}")
    pid = panel["pair_id"]
    if split == "final" and panel.get("study_protocol_sha256") != file_sha256(PROTOCOL):
        raise ValueError(f"Study protocol differs for {pid}")
    tracks = rows[0]["pair"]
    if split == "final":
        pair = next(p for p in json.loads(committed(POPULATION))["pairs"] if p["pair_id"] == pid)
        if tracks != [pair[side]["sha256"] for side in ("source", "target")]:
            raise ValueError(f"Audio identity differs for {pid}")
        check_final_panel(directory, contract, rows, pair)
    assets = []
    for row in rows:
        path = (directory / row["wav"]).resolve()
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


def prepare(root, directories, practice, split):
    panels = dict(master_panel(d, split) for d in directories)
    if not panels or len(panels) != len(directories) or (split == "final" and panels.keys() != FINAL_PAIRS):
        raise ValueError("Missing, duplicate or unexpected study pairs")
    key = dict(seed=secrets.token_hex(32), split=split, panels=panels, practice=practice_clips(practice),
               version=VERSION, protocol_sha256=file_sha256(PROTOCOL))
    if split == "final":
        groups = {p["pair_id"]:[p[s]["recording_group_id"] for s in ("source","target")]
                  for p in json.loads(committed(POPULATION))["pairs"] if p["pair_id"] in panels}
        if len({g for pair in groups.values() for g in pair}) != 2 * len(panels):
            raise ValueError("The final pairs must have disjoint recording groups")
        key["groups"] = groups
    with publish_dataset(root) as stage:
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


def layout(key, ordinal):
    def rng(*parts):
        return random.Random(digest([key["seed"], *parts]))

    pairs = sorted(key["panels"])
    rng("latin").shuffle(pairs)
    anchor_order = list(SELECTORS)
    rng("anchors").shuffle(anchor_order)
    shift = ordinal % len(pairs)
    order = pairs[shift:] + pairs[:shift]
    pages = [key["practice"]]
    for pair in order:
        anchor = anchor_order[(pairs.index(pair) + ordinal) % 3]
        assets = [a for a in key["panels"][pair] if a["condition"] != "anchor" or a["selector"] == anchor]
        rng("page", ordinal, pair).shuffle(assets)
        pages.append([dict(a, pair=pair) for a in assets])
    mapping = {}
    for i, assets in enumerate(pages):
        for letter, asset in zip(string.ascii_uppercase, assets):
            mapping[f"{i:02}-{letter}"] = asset
    return mapping


def public_layout(mapping):
    pages = {}
    for code, asset in mapping.items():
        page = code.split("-")[0]
        pages.setdefault(page, []).append(dict(code=code, sha256=asset["sha256"]))
    return list(pages.values())


class Session:
    def __init__(self, root, person):
        self.root = Path(root)
        self.key = read(self.root / "study_key.json")
        if self.key["version"] != VERSION:
            raise ValueError("Incompatible study version")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT ordinal,sid,key_hash FROM sessions WHERE person=?", (person,)).fetchone()
            if row is None:
                ordinal = db.execute("SELECT count(*) FROM sessions").fetchone()[0]
                sid = secrets.token_hex(16)
            else:
                ordinal, sid, _ = row
            self.sid = sid
            self.mapping = layout(self.key, ordinal)
            self.pages = public_layout(self.mapping)
            if row is not None and row[2] != digest(self.mapping):
                raise ValueError("Session key differs from the registered assignment")
            for asset in self.mapping.values():
                if file_sha256(Path(asset["path"])) != asset["sha256"]:
                    raise ValueError("Assigned audio changed")
            if row is None:
                state = dict(page=-1, split=self.key["split"], protocol_sha256=self.key["protocol_sha256"],
                             ratings={}, plays={}, heard=[], profile=None, finished=None,
                             entered=utc(), started=utc(), page_seconds={}, active=None)
                db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)",
                           (ordinal, person, sid, json.dumps(state), json.dumps(self.pages), digest(self.mapping)))

    def connect(self):
        return sqlite3.connect(self.root / "responses.sqlite", timeout=10)

    def state(self):
        with self.connect() as db:
            state = read_state(db, self.sid)
        page = state["page"]
        codes = [c["code"] for c in self.pages[page]] if page >= 0 else []
        return dict(page=page, total=len(self.pages)-1, done=bool(state["finished"]), codes=codes,
                    ratings={c:state["ratings"].get(c) for c in codes},
                    heard=[c for c in codes if c in state["heard"]])

    def event(self, event):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = read_state(db, self.sid)
            if state["finished"]:
                raise ValueError("Die Sitzung ist abgeschlossen.")
            page = state["page"]
            if type(event.get("page")) is not int or event["page"] != page:
                raise ValueError("Bitte laden Sie die aktuelle Seite neu.")
            kind = event.get("kind")
            stamp = utc()
            code = event.get("code")
            codes = [c["code"] for c in self.pages[page]] if page >= 0 else []
            log = dict(page=page, kind=kind)
            if kind in ("play", "ended", "rating"):
                if code not in codes:
                    raise ValueError("Unbekannter Ausschnitt auf dieser Seite.")
                log["code"] = code
                if kind == "play":
                    state["plays"][code] = state["plays"].get(code, 0) + 1
                    state["active"] = [code, time.time()]
                elif kind == "ended":
                    active = state["active"]
                    seconds = self.mapping[code]["frames"] / 44100
                    if not active or active[0] != code or time.time() - active[1] + .25 < seconds:
                        raise ValueError("Bitte spielen Sie den Ausschnitt vollständig ab.")
                    if code not in state["heard"]:
                        state["heard"].append(code)
                    state["active"] = None
                else:
                    value = event.get("value")
                    if type(value) is not int or not 0 <= value <= 100:
                        raise ValueError("Bitte eine ganze Zahl von 0 bis 100 eingeben.")
                    log["previous"] = state["ratings"].get(code)
                    log["value"] = state["ratings"][code] = value
            elif kind in ("begin", "next", "back"):
                if kind == "begin":
                    profile = event.get("profile")
                    if (page != -1 or not isinstance(profile, dict)
                            or set(profile) != {"music", "dj", "dance", "hearing"}
                            or any(v not in ("wenig", "mittel", "viel") for k,v in profile.items() if k != "hearing")
                            or profile["hearing"] not in ("ja", "nein", "keine Angabe")):
                        raise ValueError("Bitte füllen Sie die vier Angaben aus.")
                    log["profile"] = state["profile"] = profile
                elif kind == "back":
                    if page <= 1:
                        raise ValueError("Die erste Bewertungsseite ist erreicht.")
                elif page < 0 or any(c not in state["heard"] or c not in state["ratings"] for c in codes):
                    raise ValueError("Bitte jeden Ausschnitt vollständig anhören und bewerten.")
                elapsed = (datetime.fromisoformat(stamp) - datetime.fromisoformat(state["entered"])).total_seconds()
                log["seconds"] = max(0., elapsed)
                state["page_seconds"][str(page)] = state["page_seconds"].get(str(page), 0.) + log["seconds"]
                state["entered"] = stamp
                state["active"] = None
                if kind == "next" and page == len(self.pages)-1:
                    state["finished"] = stamp
                else:
                    state["page"] += -1 if kind == "back" else 1
            else:
                raise ValueError("Unbekannte Eingabe.")
            db.execute("UPDATE sessions SET state=? WHERE sid=?", (json.dumps(state), self.sid))
            db.execute("INSERT INTO events(sid,stamp,data) VALUES (?,?,?)", (self.sid, stamp, json.dumps(log)))


def read_state(db, sid):
    return json.loads(db.execute("SELECT state FROM sessions WHERE sid=?", (sid,)).fetchone()[0])


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
            record = dict(version=VERSION, ordinal=ordinal, person=person, sid=sid, key_hash=key_hash,
                          pages=json.loads(pages), state=state, events=events)
            records.append(record)
            path = out / (sid + ".json")
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            files[path.name] = file_sha256(path)
        if not files:
            raise ValueError("No completed sessions to seal")
        audit_path = out / "neutral_check.json"
        audit_path.write_text(json.dumps(neutral_check(records), indent=2), encoding="utf-8")
        (out / "receipt.json").write_text(json.dumps(dict(created=utc(), files=files, incomplete=incomplete,
                                                           neutral_check_sha256=file_sha256(audit_path)),
                                                     indent=2), encoding="utf-8")
