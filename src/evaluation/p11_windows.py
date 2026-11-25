"""Build neutral listening windows from the original, SHA-bound render metadata."""

import json
from pathlib import Path
import tempfile

from hoertest.procedure import RATE, WINDOW_FILE, WINDOW_VERSION, validate_windows
from hoertest.session import digest, file_sha256, read


def build_windows(key, directories):
    rows, sources = {}, []
    for directory in directories:
        path = Path(directory) / "results.json"
        sources.append(file_sha256(path))
        protocol_path = path.with_name("protocol.json")
        protocol_sha = file_sha256(protocol_path)
        panel = read(protocol_path)["panel"]
        if (panel.get("split") != key["split"] or panel.get("pair_id") not in key["panels"]
                or panel.get("revision") not in ("cue_grid_regression_v3", "local_grid_equal_duration_v2")):
            raise ValueError("Das Renderprotokoll gehört nicht zu diesem Studienmaterial.")
        for row in read(path):
            if (row.get("protocol_sha256") != protocol_sha or row.get("split") != key["split"]
                    or row.get("candidate_id") != panel["selectors"].get(row["selector"])):
                raise ValueError("Render-Metadaten und gebundenes Protokoll stimmen nicht überein.")
            identity = panel["pair_id"], row["wav_sha256"], row["selector"], row["condition"]
            if identity in rows and rows[identity] != row:
                raise ValueError("Widersprüchliche Render-Metadaten für dieselbe Audiodatei.")
            rows[identity] = row
    clips = {}

    def put(asset, bounds):
        entry = dict(frames=asset["frames"], window_frames=list(bounds))
        if asset["sha256"] in clips and clips[asset["sha256"]] != entry:
            raise ValueError("Dieselbe Audiodatei wurde mit unterschiedlichen Hörfenstern zugeteilt.")
        clips[asset["sha256"]] = entry

    for pair, panel in key["panels"].items():
        spans = []
        for asset in panel:
            row = rows.get((pair, asset["sha256"], asset["selector"], asset["condition"]))
            if row is None:
                raise ValueError("Render-Metadaten für einen zugeteilten Ausschnitt fehlen.")
            prefix, bridge, suffix = row.get("prefix_frames", 5 * RATE), row.get("bridge_samples"), row.get("suffix_frames")
            if (any(type(v) is not int for v in (prefix, bridge, suffix))
                    or prefix < 0 or bridge <= 0 or suffix < 0
                    or prefix + bridge + suffix != asset["frames"]
                    or row.get("geometry", {}).get("transition_samples") != bridge
                    or (key["split"] == "final" and prefix != 5 * RATE)):
                raise ValueError("Die Übergangsgeometrie passt nicht zur zugeteilten Audiodatei.")
            spans.append((prefix, prefix + bridge))
        durations = {a["frames"] for a in panel}
        if len(durations) != 1:
            raise ValueError("Ungleiche Cliplängen innerhalb des Songpaars.")
        window = max(0, min(a for a, _ in spans) - 2 * RATE), min(durations.pop(), max(b for _, b in spans) + 2 * RATE)
        for asset in panel:
            put(asset, window)
    for asset in key["practice"]:
        put(asset, (0, asset["frames"]))
    manifest = dict(version=WINDOW_VERSION, study_key_digest=digest(key), sample_rate=RATE,
                    context_seconds=2, practice="complete", source_results_sha256=sorted(set(sources)), clips=clips)
    return validate_windows(manifest, key, digest(key))


def prepare_windows(root, directories):
    root = Path(root)
    key = read(root / "study_key.json")
    manifest = build_windows(key, directories)
    target = root / WINDOW_FILE
    if target.exists():
        if read(target) != manifest:
            raise ValueError("Ein anderer Fensterindex ist bereits vorhanden; ein neues Studienpaket vorbereiten.")
        return target
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as stream:
        temp = Path(stream.name)
        try:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    temp.replace(target)
    return target
