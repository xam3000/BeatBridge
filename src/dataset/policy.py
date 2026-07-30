"""Versioned, data-driven track exclusion policy."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


TRACK_EXCLUSIONS_FORMAT_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACK_EXCLUSIONS_PATH = PROJECT_ROOT / "config" / "track_exclusions.json"


@dataclass(frozen=True)
class ExcludedTrack:
    path: str
    sha256: str
    reason: str
    scopes: tuple[str, ...]
    excluded_at: str

    def to_dict(self):
        return {
            "path": self.path,
            "sha256": self.sha256,
            "reason": self.reason,
            "scopes": list(self.scopes),
            "excluded_at": self.excluded_at,
        }


def load_track_exclusions(policy_path=DEFAULT_TRACK_EXCLUSIONS_PATH):
    """Load and validate the repository's persistent track policy."""
    policy_path = Path(policy_path)
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    if int(payload.get("format_version", 0)) != TRACK_EXCLUSIONS_FORMAT_VERSION:
        raise ValueError(
            "Unsupported track exclusion format_version: "
            f"{payload.get('format_version')}"
        )
    exclusions = []
    for entry in payload.get("tracks", ()):
        sha256 = str(entry.get("sha256", "")).lower()
        if len(sha256) != 64:
            raise ValueError(f"Excluded track needs a SHA-256 hash: {entry.get('path')}")
        scopes = tuple(str(scope) for scope in entry.get("scopes", ()))
        if not scopes:
            raise ValueError(f"Excluded track needs at least one scope: {entry.get('path')}")
        exclusions.append(
            ExcludedTrack(
                path=str(entry["path"]),
                sha256=sha256,
                reason=str(entry["reason"]),
                scopes=scopes,
                excluded_at=str(entry["excluded_at"]),
            )
        )
    return tuple(exclusions)


def is_track_excluded(
    track_path,
    *,
    sha256=None,
    scope,
    exclusions=None,
):
    """Return the matching exclusion, or ``None`` when a track is allowed."""
    if exclusions is None:
        exclusions = load_track_exclusions()
    normalised_path = _normalise_path(track_path)
    normalised_hash = None if sha256 is None else str(sha256).lower()
    for exclusion in exclusions:
        if scope not in exclusion.scopes:
            continue
        if normalised_hash is not None and normalised_hash == exclusion.sha256:
            return exclusion
        if normalised_path == _normalise_path(exclusion.path):
            return exclusion
    return None


def filter_excluded_tracks(
    track_paths,
    *,
    scope,
    exclusions=None,
):
    """Split paths into allowed paths and auditable exclusion records."""
    if exclusions is None:
        exclusions = load_track_exclusions()
    allowed = []
    rejected = []
    for track_path in track_paths:
        exclusion = is_track_excluded(
            track_path,
            scope=scope,
            exclusions=exclusions,
        )
        if exclusion is None:
            allowed.append(track_path)
        else:
            rejected.append(
                {
                    "path": str(track_path),
                    "policy": exclusion.to_dict(),
                }
            )
    return tuple(allowed), tuple(rejected)


def _normalise_path(path):
    path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve(strict=False)).replace("\\", "/").casefold()
