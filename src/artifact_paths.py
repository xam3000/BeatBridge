"""Portable file references in controller manifests, including historical Windows runs."""

import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def artifact_path(reference, base=None):
    path = Path(str(reference).replace("\\", "/"))
    if not path.is_absolute() and not (len(path.parts) and path.parts[0].endswith(":")):
        return (PROJECT if base is None else base) / path
    if path.exists():
        return path
    # Older manifests used the absolute path of the original BeatBridge checkout.
    parts = path.parts
    for index in range(1, len(parts)):
        if parts[index - 1].casefold() == "beatbridge" and parts[index].casefold() == "output":
            return PROJECT.joinpath(*parts[index:])
    return path


def portable_dataset_identity(identity, output, resume):
    """Serialize new paths relatively and preserve an existing run's exact identity on resume."""
    previous = {}
    manifest = Path(output) / "manifest.json"
    if resume and manifest.is_file():
        previous = json.loads(manifest.read_bytes())["contract"]["dataset"]

    def reference(value, existing):
        path = Path(value).resolve()
        if existing and artifact_path(existing).resolve() == path:
            return existing
        return path.relative_to(PROJECT).as_posix() if path.is_relative_to(PROJECT) else path.as_posix()

    identity["path"] = reference(identity["path"], previous.get("path"))
    for split, records in identity.get("vocal_waveform_cache_manifests", {}).items():
        old = {r["example_id"]: r["path"] for r in previous.get("vocal_waveform_cache_manifests", {}).get(split, [])}
        for record in records:
            record["path"] = reference(record["path"], old.get(record["example_id"]))
    return identity
