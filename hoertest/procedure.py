"""Neutral questions and playback-window contract for new listening sessions."""

import json
import math
from pathlib import Path


PROTOCOL = Path(__file__).with_name("DURCHFUEHRUNG_20261125.md")
WINDOW_FILE = "listening_windows.json"
WINDOW_VERSION = "p11-listening-windows-v1"
PROFILE_VERSION = 2
RATE = 44100
EDGE_TOLERANCE = .025  # Browser time quantisation at the two outer boundaries only.


def questions(version, online):
    years = [("none_or_rare", "Nie bzw. nur seltener"), ("lt1", "Unter einem Jahr"),
             ("1to5", "Ein bis fünf Jahre"), ("gt5", "Mehr als fünf Jahre"),
             ("no_answer", "Keine Angabe")]
    if version == PROFILE_VERSION:
        result = [
            dict(key="music_practice", title="Wie lange haben Sie insgesamt mindestens einmal pro Woche selbst Musik gemacht?",
                 help="Instrument, Gesang oder Produktion eigener Musik zählen dazu – auch selbst beigebracht. Längere Pausen nicht mitzählen.", choices=years),
            dict(key="dj_practice", title="Wie lange haben Sie insgesamt mindestens einmal pro Monat selbst Übergänge zwischen Songs gemischt?",
                 help="Zum Beispiel mit DJ-Software oder beim Auflegen. Üben zu Hause zählt ebenfalls. Längere Pausen nicht mitzählen.", choices=years),
            dict(key="edm_listening", title="Wie häufig haben Sie in den letzten zwölf Monaten elektronische Tanzmusik gehört?",
                 help="Zum Beispiel Techno, House oder Hardstyle.",
                 choices=[("never", "Nie"), ("lt_monthly", "Seltener als monatlich"),
                          ("monthly", "Mindestens monatlich, aber seltener als wöchentlich"),
                          ("weekly", "Mindestens wöchentlich"), ("no_answer", "Keine Angabe")]),
        ]
    elif version == 1:
        result = [dict(key=key, title=title, help="", choices=[(v, v) for v in ("wenig", "mittel", "viel")])
                  for key, title in (("music", "Musik"), ("dj", "DJing"), ("dance", "Tanz"))]
    else:
        raise ValueError("Unbekannte Fassung der Erfahrungsfragen.")
    result.append(dict(key="hearing", title="Haben Sie bekannte Einschränkungen beim Hören?", help="",
                       choices=[(v, v) for v in ("nein", "ja", "keine Angabe")]))
    if online:
        result.append(dict(key="setting", title="Wo hören Sie?", help="",
                           choices=[(v, v) for v in ("Institut", "anderer Hörplatz")]))
    return result


def valid_profile(profile, version, online):
    fields = questions(version, online)
    return (isinstance(profile, dict) and set(profile) == {q["key"] for q in fields}
            and all(profile[q["key"]] in [value for value, _ in q["choices"]] for q in fields))


def validate_windows(manifest, key, key_digest):
    if (manifest.get("version") != WINDOW_VERSION or manifest.get("study_key_digest") != key_digest
            or manifest.get("sample_rate") != RATE or manifest.get("context_seconds") != 2
            or manifest.get("practice") != "complete"):
        raise ValueError("Der Fensterindex gehört nicht zu diesem Medienpaket.")
    assets = [*key["practice"], *(a for panel in key["panels"].values() for a in panel)]
    clips = manifest.get("clips", {})
    if set(clips) != {a["sha256"] for a in assets}:
        raise ValueError("Der Fensterindex enthält nicht genau die zugeteilten Audiodateien.")
    for asset in assets:
        entry = clips[asset["sha256"]]
        bounds = entry.get("window_frames", [])
        if (entry.get("frames") != asset["frames"] or len(bounds) != 2
                or any(type(v) is not int for v in bounds) or not 0 <= bounds[0] < bounds[1] <= asset["frames"]):
            raise ValueError("Ungültiges Übergangsfenster.")
    for panel in key["panels"].values():
        if len({tuple(clips[a["sha256"]]["window_frames"]) for a in panel}) != 1:
            raise ValueError("Alle Varianten eines Songpaars benötigen dasselbe neutrale Fenster.")
    if any(clips[a["sha256"]]["window_frames"] != [0, a["frames"]] for a in key["practice"]):
        raise ValueError("Die beiden Übungsclips müssen vollständig im Hörfenster liegen.")
    return manifest


def load_windows(root, key, key_digest):
    path = Path(root) / WINDOW_FILE
    if not path.is_file():
        raise ValueError("Der Übergangsfensterindex fehlt. Bitte zuerst prepare-windows für dieses Medienpaket ausführen.")
    return validate_windows(json.loads(path.read_bytes()), key, key_digest)


def assigned_windows(manifest, mapping):
    return {code: manifest["clips"][asset["sha256"]]["window_frames"] for code, asset in mapping.items()}


def merge_ranges(ranges, duration):
    if not isinstance(ranges, list) or len(ranges) > 256:
        raise ValueError("Ungültige Wiedergabeintervalle.")
    checked = []
    for interval in ranges:
        if (not isinstance(interval, list) or len(interval) != 2
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in interval)):
            raise ValueError("Ungültige Wiedergabeintervalle.")
        start, end = interval
        if not (0 <= start < min(end, duration) and end <= duration + EDGE_TOLERANCE):
            raise ValueError("Wiedergabeintervall außerhalb des Ausschnitts.")
        checked.append([start, min(end, duration)])
    merged = []
    for start, end in sorted(checked):
        if merged and start <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


def window_complete(state, code):
    first, last = state["listening_windows"][code]
    return any(start <= first / RATE + EDGE_TOLERANCE and end >= last / RATE - EDGE_TOLERANCE
               for start, end in state.get("listened", {}).get(code, []))


def verify_record_windows(records, manifest, manifest_sha):
    """Bind the saved neutral windows to the separately sealed index."""
    for record in records:
        state = record["state"]
        if state.get("playback_mode") != "window":
            continue
        expected = {clip["code"]: manifest["clips"][clip["sha256"]]["window_frames"]
                    for page in record["pages"] for clip in page}
        if state.get("window_manifest_sha256") != manifest_sha or state.get("listening_windows") != expected:
            raise ValueError("Die gespeicherten Hörfenster weichen vom versiegelten Fensterindex ab.")
