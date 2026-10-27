"""Read-only adapter for BeatBridge single-pair batch manifests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid


@dataclass(frozen=True)
class ReviewVariant:
    key: str
    candidate_id: str
    renderer: str
    output_file: str
    audio_path: Path
    status: str
    candidate_rank: int | None
    candidate_score: float | None
    selection_rank: int | None
    selection_score: float | None
    selection_method: str
    transition_rank: int | None
    transition_score: float | None
    transition_start_sample: int | None
    transition_end_sample: int | None
    sample_rate: int | None
    sample_count: int | None
    candidate: dict
    candidate_measurements: dict
    candidate_components: dict
    transition_components: dict


@dataclass(frozen=True)
class BatchReview:
    manifest_path: Path
    manifest_sha256: str
    format_version: int
    ranking_method: str
    variants: tuple[ReviewVariant, ...]
    failures: tuple[dict, ...]
    candidates: dict[str, dict]


def load_batch_manifest(path: Path) -> BatchReview:
    """Read and adapt a single-pair batch manifest without changing it."""
    path = path.expanduser().resolve()
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(f"Manifest kann nicht gelesen werden: {error}") from error
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Manifest ist kein gültiges UTF-8-JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Das JSON-Wurzelelement muss ein Objekt sein.")

    candidate_generation = payload.get("candidate_generation")
    if not isinstance(candidate_generation, dict):
        raise ValueError(
            "Das ist kein einzelnes BeatBridge-Batchmanifest: "
            "candidate_generation fehlt. Öffne das manifest.json eines Paar-Batchordners."
        )
    candidates_list = candidate_generation.get("candidates", [])
    raw_variants = payload.get("rendered_variants", [])
    if not isinstance(candidates_list, list) or not isinstance(raw_variants, list):
        raise ValueError("Kandidaten oder gerenderte Varianten haben ein ungültiges Format.")

    candidates = {
        str(candidate.get("candidate_id")): candidate
        for candidate in candidates_list
        if isinstance(candidate, dict) and candidate.get("candidate_id") is not None
    }
    candidate_ranking = payload.get("candidate_ranking")
    candidate_scores = _score_index(
        candidate_ranking.get("scores", []) if isinstance(candidate_ranking, dict) else []
    )
    transition_ranking = payload.get("rendered_transition_ranking")
    sidecar = _load_transition_metrics_sidecar(
        path.parent / "transition_metrics.json", raw_variants, payload.get("format_version")
    )
    used_transition_sidecar = not isinstance(transition_ranking, dict) and sidecar is not None
    if used_transition_sidecar:
        transition_ranking = sidecar.get("ranking")
    transition_scores = _score_index(
        transition_ranking.get("scores", []) if isinstance(transition_ranking, dict) else []
    )

    variants: list[ReviewVariant] = []
    root = path.parent.resolve()
    for raw_variant in raw_variants:
        if not isinstance(raw_variant, dict):
            continue
        candidate_id = str(raw_variant.get("candidate_id", ""))
        renderer = str(raw_variant.get("renderer", "unbekannt"))
        output_file = str(raw_variant.get("output_file", ""))
        variant_key = "|".join((candidate_id, renderer, output_file))
        audio_path, path_error = _resolve_audio_path(root, output_file)
        candidate = candidates.get(candidate_id, {})
        candidate_score = candidate_scores.get(candidate_id, {})
        transition_score = transition_scores.get(variant_key) or transition_scores.get(
            f"{candidate_id}|{renderer}"
        ) or {}
        measurements = transition_score.get("measurements", {})
        sample_rate = _optional_int(raw_variant.get("sample_rate"))
        transition_start = _optional_int(raw_variant.get("transition_start_sample"))
        transition_end = _optional_int(raw_variant.get("transition_end_sample"))
        if isinstance(measurements, dict) and sample_rate:
            if transition_start is None:
                transition_start = _seconds_to_samples(measurements.get("transition_start_seconds"), sample_rate)
            if transition_end is None:
                transition_end = _seconds_to_samples(measurements.get("transition_end_seconds"), sample_rate)
        variants.append(
            ReviewVariant(
                key=variant_key,
                candidate_id=candidate_id or "Nicht verfügbar",
                renderer=renderer,
                output_file=output_file or "Nicht verfügbar",
                audio_path=audio_path,
                status=path_error or str(raw_variant.get("status", "rendered")),
                candidate_rank=_optional_int(raw_variant.get("candidate_rank", candidate_score.get("rank"))),
                candidate_score=_optional_float(raw_variant.get("candidate_score", candidate_score.get("total_score"))),
                selection_rank=_optional_int(raw_variant.get("selection_rank")),
                selection_score=_optional_float(raw_variant.get("selection_score")),
                selection_method=str(raw_variant.get("selection_method", payload.get("ranking_method", "Nicht verfügbar"))),
                transition_rank=_optional_int(raw_variant.get("transition_rank", transition_score.get("rank"))),
                transition_score=_optional_float(raw_variant.get("transition_score", transition_score.get("total_score"))),
                transition_start_sample=transition_start,
                transition_end_sample=transition_end,
                sample_rate=sample_rate,
                sample_count=_optional_int(raw_variant.get("sample_count")),
                candidate=candidate,
                candidate_measurements=candidate_score.get("measurements", {}),
                candidate_components=candidate_score.get("component_scores", {}),
                transition_components=transition_score.get("component_scores", {}),
            )
        )

    failures = payload.get("failures", [])
    failures = list(failures) if isinstance(failures, list) else []
    if used_transition_sidecar and isinstance(transition_ranking, dict):
        sidecar_failures = transition_ranking.get("failures", [])
        if isinstance(sidecar_failures, list):
            failures.extend(sidecar_failures)
    return BatchReview(
        manifest_path=path,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        format_version=_optional_int(payload.get("format_version")) or 1,
        ranking_method=str(payload.get("ranking_method", "Nicht verfügbar")),
        variants=tuple(variants),
        failures=tuple(item for item in failures if isinstance(item, dict)),
        candidates=candidates,
    )


def _score_index(scores) -> dict[str, dict]:
    if not isinstance(scores, list):
        return {}
    result = {}
    for score in scores:
        if not isinstance(score, dict):
            continue
        candidate_id = score.get("candidate_id")
        if candidate_id is None:
            continue
        renderer = score.get("renderer")
        key = f"{candidate_id}|{renderer}" if renderer is not None else str(candidate_id)
        result[key] = score
    return result


def _load_transition_metrics_sidecar(path: Path, raw_variants: list, manifest_version) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("format_version") != 1
        or payload.get("source_manifest") != "manifest.json"
        or payload.get("source_manifest_format_version") != manifest_version
    ):
        return None
    sidecar_variants = payload.get("variants")
    if not isinstance(sidecar_variants, list) or len(sidecar_variants) != len(raw_variants):
        return None
    sidecar_bindings = {
        (item.get("candidate_id"), item.get("renderer"), item.get("output_file"))
        for item in sidecar_variants
        if isinstance(item, dict)
    }
    manifest_bindings = {
        (item.get("candidate_id"), item.get("renderer"), item.get("output_file"))
        for item in raw_variants
        if isinstance(item, dict)
    }
    if sidecar_bindings != manifest_bindings:
        return None
    return payload


def _resolve_audio_path(root: Path, relative_path: str) -> tuple[Path, str]:
    if not relative_path or Path(relative_path).is_absolute():
        return root / relative_path, "Dateipfad fehlt oder ist absolut"
    path = (root / Path(relative_path)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return path, "Dateipfad liegt außerhalb des Batchordners"
    if not path.is_file():
        return path, "WAV-Datei fehlt"
    return path, "rendered"


def _optional_int(value):
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _optional_float(value):
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _seconds_to_samples(value, sample_rate):
    try:
        return int(round(float(value) * sample_rate))
    except (TypeError, ValueError, OverflowError):
        return None


def selection_sidecar_path(manifest_path: Path) -> Path:
    return manifest_path.with_name(f"{manifest_path.stem}.selections.json")


def load_saved_selection(review: BatchReview) -> str | None:
    sidecar = selection_sidecar_path(review.manifest_path)
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("format_version") != 1 or payload.get("manifest_sha256") != review.manifest_sha256:
        return None
    selected = payload.get("selected_variant")
    return str(selected.get("variant_key")) if isinstance(selected, dict) else None


def save_selection(review: BatchReview, variant: ReviewVariant) -> Path:
    """Atomically save a selection sidecar; never overwrite manifest or audio."""
    sidecar = selection_sidecar_path(review.manifest_path)
    payload = {
        "format_version": 1,
        "manifest_sha256": review.manifest_sha256,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_variant": {
            "variant_key": variant.key,
            "candidate_id": variant.candidate_id,
            "renderer": variant.renderer,
            "output_file": variant.output_file,
        },
    }
    temporary = sidecar.with_name(f".{sidecar.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, sidecar)
    finally:
        temporary.unlink(missing_ok=True)
    return sidecar
