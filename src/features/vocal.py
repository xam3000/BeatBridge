"""Cached vocal-stem extraction with citable pretrained Demucs weights."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import uuid

import numpy as np


DEMUCS_BACKEND_VERSION = 1
DEFAULT_DEMUCS_MODEL = "htdemucs"
DEMUCS_HF_NAMESPACE = "adefossez"
DEMUCS_PAPER = {
    "citation_key": "rouard2023hybrid",
    "title": "Hybrid Transformers for Music Source Separation",
    "authors": ["Simon Rouard", "Francisco Massa", "Alexandre Défossez"],
    "venue": "IEEE International Conference on Acoustics, Speech and Signal Processing",
    "year": 2023,
    "doi": "10.1109/ICASSP49357.2023.10096956",
    "arxiv": "2211.08553",
    "url": "https://arxiv.org/abs/2211.08553",
}


@dataclass(frozen=True)
class VocalStemArtifact:
    """One immutable mono vocal stem plus exact model provenance."""

    cache_directory: Path
    manifest: dict
    audio: np.ndarray
    sample_rate: int
    cache_hit: bool


def extract_or_load_vocal_stem(
    song_path,
    *,
    cache_root,
    source_sha256=None,
    model_name=DEFAULT_DEMUCS_MODEL,
    separator_factory=None,
):
    """Separate vocals once per source/model and reuse the cached stem."""
    song_path = Path(song_path)
    if not song_path.is_file():
        raise FileNotFoundError(f"Audio track does not exist: {song_path}")
    source_sha256 = source_sha256 or _file_sha256(song_path)
    model_name = str(model_name)
    demucs_version = importlib.metadata.version("demucs")
    cache_config = {
        "backend": "demucs",
        "backend_version": DEMUCS_BACKEND_VERSION,
        "demucs_version": demucs_version,
        "model_name": model_name,
        "source_sha256": source_sha256,
    }
    cache_id = hashlib.sha256(
        json.dumps(cache_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    cache_directory = (
        Path(cache_root)
        / "model_artifacts"
        / f"demucs_vocal_v{DEMUCS_BACKEND_VERSION}"
        / source_sha256[:16]
        / cache_id
    )
    cached = _load_cached_vocal(cache_directory, cache_config)
    if cached is not None:
        return cached

    if separator_factory is None:
        from demucs.api import Separator

        separator_factory = Separator
    separator = separator_factory(
        model=model_name,
        device="cpu",
        shifts=1,
        split=True,
        overlap=0.25,
        jobs=0,
        progress=False,
    )
    _, stems = separator.separate_audio_file(song_path)
    if "vocals" not in stems:
        raise ValueError(
            f"Demucs model {model_name!r} did not return a 'vocals' source"
        )
    vocal = stems["vocals"].detach().cpu().numpy()
    if vocal.ndim != 2 or vocal.shape[0] < 1:
        raise ValueError(f"Unexpected Demucs vocal tensor shape: {vocal.shape}")
    vocal = np.mean(vocal, axis=0, dtype=np.float32).astype(np.float32, copy=False)
    if vocal.size == 0 or not np.isfinite(vocal).all():
        raise ValueError("Demucs returned an empty or non-finite vocal stem")

    weights = _demucs_weight_provenance(model_name)
    cache_directory.mkdir(parents=True, exist_ok=True)
    data_path = cache_directory / "vocal_stem.npz"
    _write_npz_atomic(data_path, audio=vocal)
    artifact_sha256 = _file_sha256(data_path)
    manifest = {
        "format_version": 1,
        **cache_config,
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(song_path),
        "sample_rate": int(separator.samplerate),
        "sample_count": int(vocal.size),
        "dtype": "float32",
        "data_file": data_path.name,
        "artifact_sha256": artifact_sha256,
        "weights": weights,
        "paper": DEMUCS_PAPER,
        "model_card_url": weights["model_card_url"],
    }
    _write_json_atomic(cache_directory / "manifest.json", manifest)
    return VocalStemArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        audio=vocal,
        sample_rate=int(separator.samplerate),
        cache_hit=False,
    )


def _demucs_weight_provenance(model_name):
    """Record the exact locally used Hugging Face revision and file hashes."""
    try:
        from demucs.hf import hf_repo_name
        from huggingface_hub import scan_cache_dir

        repo_id = f"{DEMUCS_HF_NAMESPACE}/{hf_repo_name(model_name)}"
        cache_info = scan_cache_dir()
        matching_repos = [repo for repo in cache_info.repos if repo.repo_id == repo_id]
        if not matching_repos:
            raise LookupError(f"No cached Hugging Face repository found for {repo_id}")
        revisions = [
            revision
            for repo in matching_repos
            for revision in repo.revisions
        ]
        revision = max(revisions, key=lambda item: item.last_modified)
        files = []
        for cached_file in sorted(revision.files, key=lambda item: item.file_name):
            if not (
                cached_file.file_name.endswith(".safetensors")
                or cached_file.file_name.endswith(".yaml")
            ):
                continue
            files.append(
                {
                    "name": cached_file.file_name,
                    "sha256": _file_sha256(cached_file.file_path),
                    "size_bytes": int(cached_file.size_on_disk),
                }
            )
        return {
            "provider": "Hugging Face Hub",
            "repo_id": repo_id,
            "revision": revision.commit_hash,
            "files": files,
            "model_card_url": f"https://huggingface.co/{repo_id}",
        }
    except Exception as error:
        return {
            "provider": "Demucs model loader",
            "repo_id": None,
            "revision": None,
            "files": [],
            "provenance_error": f"{type(error).__name__}: {error}",
            "model_card_url": "https://github.com/adefossez/demucs",
        }


def _load_cached_vocal(cache_directory, expected_config):
    manifest_path = cache_directory / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if any(manifest.get(key) != value for key, value in expected_config.items()):
        return None
    data_path = cache_directory / manifest["data_file"]
    if not data_path.is_file() or _file_sha256(data_path) != manifest["artifact_sha256"]:
        return None
    with np.load(data_path, allow_pickle=False) as payload:
        audio = payload["audio"].astype(np.float32, copy=False)
    if audio.ndim != 1 or audio.size != manifest["sample_count"]:
        raise ValueError(f"Cached vocal stem has an invalid shape: {data_path}")
    if not np.isfinite(audio).all():
        raise ValueError(f"Cached vocal stem contains non-finite samples: {data_path}")
    return VocalStemArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        audio=audio,
        sample_rate=int(manifest["sample_rate"]),
        cache_hit=True,
    )


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_npz_atomic(path, **arrays):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary_path.open("wb") as output:
            np.savez_compressed(output, **arrays)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_json_atomic(path, payload):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
