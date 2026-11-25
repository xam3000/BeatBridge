"""Session assignment and responses shared by the local and institute players."""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import secrets
import sqlite3
import string
import time

from .procedure import (PROTOCOL as WINDOW_PROTOCOL, PROFILE_VERSION, WINDOW_FILE, assigned_windows,
                        load_windows, merge_ranges, questions, valid_profile, window_complete)

VERSION = "p11-local-v2.1"
WEB_VERSION = "p11-institut-v1"
RUN02 = "run02"
CURRENT_FIXED = "cue_grid_regression_v3_fixed_rule"
CURRENT_ROTATING = "cue_grid_regression_v3_rotating"
SELECTORS = ("ssl", "rule", "random")
LISTENING_SETTINGS = ("Institut", "anderer Hörplatz")
RATING_SCALE = (1, 7)
RATING_PROTOCOL = Path(__file__).with_name("BEWERTUNG_20261125.md")
PLAYBACK_PROTOCOL = Path(__file__).with_name("BEDIENUNG_20261125.md")
COMMENT_LIMIT = 2000


def playback_mode(state):
    mode = state.get("playback_mode", "complete")
    protocol = {"seek": PLAYBACK_PROTOCOL, "window": WINDOW_PROTOCOL}.get(mode)
    if mode not in ("complete", "seek", "window") or (protocol and
            state.get("playback_protocol_sha256") != file_sha256(protocol)):
        raise ValueError("Playback procedure differs from the saved session")
    return mode


def playback_complete(state, code):
    mode = playback_mode(state)
    return state["plays"].get(code, 0) > 0 and (window_complete(state, code) if mode == "window"
                                              else mode == "seek" or code in state["heard"])


def rating_scale(state):
    # Sessions created before the seven-point scale have no scale field.
    bounds = tuple(state.get("rating_scale", (0, 100)))
    if bounds not in (RATING_SCALE, (0, 100)):
        raise ValueError("Unbekannte Bewertungsskala.")
    return bounds


def valid_rating(value, bounds):
    return type(value) is int and bounds[0] <= value <= bounds[1]


def web_protocol(key):
    name = {RUN02: "PROTOKOLL_RUN02.md", CURRENT_FIXED: "PROTOKOLL_FESTE_ANKER_20261123.md",
            "v2": "PROTOKOLL_20261123.md", CURRENT_ROTATING: "PROTOKOLL.md"}[key.get("material", "v2")]
    return Path(__file__).with_name(name)


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def layout(key, ordinal, sid=None):
    def rng(*parts):
        return random.Random(digest([key["seed"], *parts]))

    pairs = sorted(key["panels"])
    anchor_order = list(SELECTORS)
    online = key["version"] == WEB_VERSION
    if online:
        if not sid:
            raise ValueError("The institute layout requires its saved session ID")
        n = len(pairs)
        block, seat = divmod(ordinal, n)
        rng("pairs", block).shuffle(pairs)
        rows = list(range(n))
        columns = list(range(n))
        rng("rows", block).shuffle(rows)
        rng("columns", block).shuffle(columns)
        order = [pairs[(rows[seat] + col) % n] for col in columns]
        anchor_block, anchor_seat = divmod(ordinal, 3)
        anchor_pairs = sorted(pairs)
        rng("anchor-pairs", anchor_block).shuffle(anchor_pairs)
        rng("anchor-types", anchor_block).shuffle(anchor_order)
        shifts = [0, 1, 2]
        rng("anchor-shifts", anchor_block).shuffle(shifts)
        anchor_offset = shifts[anchor_seat]
    else:
        rng("latin").shuffle(pairs)
        rng("anchors").shuffle(anchor_order)
        shift = ordinal % len(pairs)
        order = pairs[shift:] + pairs[:shift]
        anchor_pairs, anchor_offset = pairs, ordinal
    practice = list(key["practice"])
    if online:
        rng("practice", sid).shuffle(practice)
    pages = [practice]
    for pair in order:
        anchor = anchor_order[(anchor_pairs.index(pair) + anchor_offset) % 3]
        if key.get("material") in (RUN02, CURRENT_FIXED):
            anchor = "rule"  # The same hard cut is presented to every listener.
        assets = [a for a in key["panels"][pair] if a["condition"] != "anchor" or a["selector"] == anchor]
        page_rng = rng("clips", sid, pair) if online else rng("page", ordinal, pair)
        page_rng.shuffle(assets)
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
    def __init__(self, root, person, *, verified_key=None, create=True):
        self.root = Path(root)
        self.key = verified_key if verified_key is not None else read(self.root / "study_key.json")
        self.online = self.key["version"] == WEB_VERSION
        if self.key["version"] not in (VERSION, WEB_VERSION):
            raise ValueError("Incompatible study version")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT ordinal,sid,key_hash FROM sessions WHERE person=?", (person,)).fetchone()
            if row is None:
                if not create:
                    raise KeyError("Unbekannte Sitzung")
                ordinal = db.execute("SELECT count(*) FROM sessions").fetchone()[0]
                sid = secrets.token_hex(16)
            else:
                ordinal, sid, _ = row
            self.sid = sid
            self.person = person
            self.mapping = layout(self.key, ordinal, sid)
            self.pages = public_layout(self.mapping)
            if row is not None and row[2] != digest(self.mapping):
                raise ValueError("Session key differs from the registered assignment")
            if verified_key is None:
                for asset in self.mapping.values():
                    if file_sha256(self.root / asset["path"]) != asset["sha256"]:
                        raise ValueError("Assigned audio changed")
            if row is None:
                windows = load_windows(self.root, self.key, digest(self.key))
                state = dict(page=-1, split=self.key["split"], protocol_sha256=self.key["protocol_sha256"],
                             rating_scale=RATING_SCALE, rating_protocol_sha256=file_sha256(RATING_PROTOCOL),
                             playback_mode="window", playback_protocol_sha256=file_sha256(WINDOW_PROTOCOL), comments={},
                             profile_version=PROFILE_VERSION, profile_protocol_sha256=file_sha256(WINDOW_PROTOCOL),
                             window_manifest_sha256=file_sha256(self.root / WINDOW_FILE),
                             listening_windows=assigned_windows(windows, self.mapping), listened={},
                             ratings={}, plays={}, heard=[], profile=None, finished=None,
                             entered=utc(), started=utc(), page_seconds={}, active=None)
                if self.online:
                    state["procedure_sha256"] = self.key["procedure_sha256"]
                db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)",
                           (ordinal, person, sid, json.dumps(state), json.dumps(self.pages), digest(self.mapping)))

    def connect(self):
        return sqlite3.connect(self.root / "responses.sqlite", timeout=10)

    def state(self):
        with closing(self.connect()) as db:
            state = read_state(db, self.sid)
        page = state["page"]
        codes = [c["code"] for c in self.pages[page]] if page >= 0 else []
        return dict(page=page, total=len(self.pages)-1, done=bool(state["finished"]), codes=codes,
                    **({"session_code": self.person} if self.online else {}),
                    rating_scale=rating_scale(state), ratings={c:state["ratings"].get(c) for c in codes},
                    playback_mode=playback_mode(state), ready=[c for c in codes if playback_complete(state, c)],
                    profile_version=state.get("profile_version", 1),
                    profile_questions=questions(state.get("profile_version", 1), self.online) if page == -1 else [],
                    windows={c:[v / 44100 for v in state["listening_windows"][c]] for c in codes}
                            if playback_mode(state) == "window" else {},
                    durations={c:self.mapping[c]["frames"] / 44100 for c in codes},
                    comment=state.get("comments", {}).get(str(page), ""), comment_limit=COMMENT_LIMIT,
                    heard=[c for c in codes if c in state["heard"]])

    def event(self, event):
        with closing(self.connect()) as db, db:
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
            if kind in ("arm", "play", "progress", "ended", "rating"):
                if code not in codes:
                    raise ValueError("Unbekannter Ausschnitt auf dieser Seite.")
                log["code"] = code
                if kind == "arm":
                    if playback_mode(state) != "window":
                        raise ValueError("Unbekannte Wiedergabevorbereitung.")
                    state["active"] = [code, time.time()]
                    state["active_coverage"] = 0.
                    state["awaiting_play"] = code
                elif kind == "play":
                    if playback_mode(state) == "window":
                        if state.get("awaiting_play") != code or not state["active"] or state["active"][0] != code:
                            raise ValueError("Bitte die Wiedergabe erneut starten.")
                        state["awaiting_play"] = None
                    else:
                        state["active"] = [code, time.time()]
                    state["plays"][code] = state["plays"].get(code, 0) + 1
                elif kind == "progress":
                    active = state["active"]
                    if (playback_mode(state) != "window" or not active or active[0] != code
                            or state.get("awaiting_play") is not None):
                        raise ValueError("Keine aktive Wiedergabe für diesen Ausschnitt.")
                    seconds = self.mapping[code]["frames"] / 44100
                    intervals = merge_ranges(event.get("ranges"), seconds)
                    previous = state["listened"].get(code, [])
                    combined = merge_ranges(previous + intervals, seconds)
                    added = sum(b-a for a, b in combined) - sum(b-a for a, b in previous)
                    covered = state.get("active_coverage", 0.) + added
                    if covered > max(0., time.time() - active[1]) + .25:
                        raise ValueError("Die gemeldete Hörzeit übersteigt die Wiedergabedauer.")
                    state["active_coverage"] = covered
                    state["listened"][code] = combined
                    log["ranges"] = intervals
                elif kind == "ended":
                    active = state["active"]
                    seconds = self.mapping[code]["frames"] / 44100
                    if not active or active[0] != code or (playback_mode(state) == "complete" and
                            time.time() - active[1] + .25 < seconds):
                        raise ValueError("Bitte spielen Sie den Ausschnitt vollständig ab.")
                    if code not in state["heard"]:
                        state["heard"].append(code)
                    state["active"] = None
                else:
                    value = event.get("value")
                    bounds = rating_scale(state)
                    if not valid_rating(value, bounds):
                        raise ValueError(f"Bitte eine ganze Zahl von {bounds[0]} bis {bounds[1]} wählen.")
                    log["previous"] = state["ratings"].get(code)
                    log["value"] = state["ratings"][code] = value
            elif kind == "comment":
                value = event.get("value")
                if page < 1 or not isinstance(value, str) or len(value) > COMMENT_LIMIT:
                    raise ValueError(f"Bitte höchstens {COMMENT_LIMIT} Zeichen zum Songpaar eingeben.")
                comments = state.setdefault("comments", {})
                log["previous"] = comments.get(str(page), "")
                log["value"] = comments[str(page)] = value
            elif kind in ("begin", "next", "back"):
                if kind == "begin":
                    profile = event.get("profile")
                    if page != -1 or not valid_profile(profile, state.get("profile_version", 1), self.online):
                        raise ValueError("Bitte prüfen Sie die Angaben zum Einstieg.")
                    log["profile"] = state["profile"] = profile
                elif kind == "back":
                    if page <= 1:
                        raise ValueError("Die erste Bewertungsseite ist erreicht.")
                elif page < 0 or any(not playback_complete(state, c) or c not in state["ratings"] for c in codes):
                    raise ValueError("Bitte jeden Ausschnitt anhören und bewerten.")
                elapsed = (datetime.fromisoformat(stamp) - datetime.fromisoformat(state["entered"])).total_seconds()
                log["seconds"] = max(0., elapsed)
                state["page_seconds"][str(page)] = state["page_seconds"].get(str(page), 0.) + log["seconds"]
                state["entered"] = stamp
                state["active"] = None
                state["awaiting_play"] = None
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
