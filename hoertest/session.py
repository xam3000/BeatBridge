"""Session assignment and responses shared by the local and institute players."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import secrets
import sqlite3
import string
import time


VERSION = "p11-local-v2.1"
WEB_VERSION = "p11-institut-v1"
RUN02 = "run02"
CURRENT_FIXED = "cue_grid_regression_v3_fixed_rule"
SELECTORS = ("ssl", "rule", "random")


def web_protocol(key):
    name = {RUN02: "PROTOKOLL_RUN02.md", CURRENT_FIXED: "PROTOKOLL_FESTE_ANKER.md",
            "v2": "PROTOKOLL.md"}[key.get("material", "v2")]
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
        with self.connect() as db:
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
                state = dict(page=-1, split=self.key["split"], protocol_sha256=self.key["protocol_sha256"],
                             ratings={}, plays={}, heard=[], profile=None, finished=None,
                             entered=utc(), started=utc(), page_seconds={}, active=None)
                if self.online:
                    state["procedure_sha256"] = self.key["procedure_sha256"]
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
                    **({"session_code": self.person} if self.online else {}),
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
                    fields = {"music", "dj", "dance", "hearing"}
                    if self.online:
                        fields.add("setting")
                    if (page != -1 or not isinstance(profile, dict)
                            or set(profile) != fields
                            or any(profile[k] not in ("wenig", "mittel", "viel") for k in ("music", "dj", "dance"))
                            or (self.online and profile["setting"] not in ("Institut", "anderer Hörplatz"))
                            or profile["hearing"] not in ("ja", "nein", "keine Angabe")):
                        raise ValueError("Bitte prüfen Sie die Angaben zum Einstieg.")
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
