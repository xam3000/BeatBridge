"""Cached vocal-stem extraction with citable pretrained separators."""

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
import soundfile as sf

from src.torch_device import DEFAULT_TORCH_DEVICE, resolve_torch_device


DEMUCS_BACKEND_VERSION = 1
DEFAULT_DEMUCS_MODEL = "htdemucs"
DEFAULT_VOCAL_BACKEND = "roformer"
ROFORMER_BACKEND_VERSION = 1
DEFAULT_ROFORMER_MODEL = "roformer-model-bs-roformer-sw-by-jarredou"
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
ROFORMER_PAPER = {
    "citation_key": "lu2024bsroformer",
    "title": "Music Source Separation with Band-Split RoPE Transformer",
    "authors": [
        "Wei-Tsung Lu",
        "Ju-Chiang Wang",
        "Qiuqiang Kong",
        "Yun-Ning Hung",
    ],
    "venue": "IEEE International Conference on Acoustics, Speech and Signal Processing",
    "year": 2024,
    "doi": "10.1109/ICASSP48485.2024.10446843",
    "arxiv": "2309.02612",
    "url": "https://arxiv.org/abs/2309.02612",
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
    device=DEFAULT_TORCH_DEVICE,
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
    compute_device = resolve_torch_device(device)
    separator = separator_factory(
        model=model_name,
        device=str(compute_device),
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
        "compute_device": str(compute_device),
    }
    _write_json_atomic(cache_directory / "manifest.json", manifest)
    return VocalStemArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        audio=vocal,
        sample_rate=int(separator.samplerate),
        cache_hit=False,
    )


def extract_or_load_roformer_vocal_stem(
    song_path,
    *,
    cache_root,
    source_sha256=None,
    model_name=DEFAULT_ROFORMER_MODEL,
    device=DEFAULT_TORCH_DEVICE,
    separator_factory=None,
):
    """Separate and cache the vocal stem with an audio-separator RoFormer model.

    ``bs-roformer-infer`` owns model configuration and inference. Model assets
    are downloaded into the cache root and the resulting vocal array is copied
    into BeatBridge's immutable cache. ``separator_factory`` is injectable for
    deterministic tests.
    """
    song_path = Path(song_path)
    if not song_path.is_file():
        raise FileNotFoundError(f"Audio track does not exist: {song_path}")
    source_sha256 = source_sha256 or _file_sha256(song_path)
    model_name = str(model_name)
    separator_version = _package_version("bs-roformer-infer")
    cache_config = {
        "backend": "roformer",
        "backend_version": ROFORMER_BACKEND_VERSION,
        "bs_roformer_infer_version": separator_version,
        "model_name": model_name,
        "source_sha256": source_sha256,
    }
    cache_id = hashlib.sha256(
        json.dumps(cache_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    cache_directory = (
        Path(cache_root)
        / "model_artifacts"
        / f"roformer_vocal_v{ROFORMER_BACKEND_VERSION}"
        / source_sha256[:16]
        / cache_id
    )
    cached = _load_cached_vocal(cache_directory, cache_config)
    if cached is not None:
        return cached

    compute_device = resolve_torch_device(device)
    model_directory = (
        Path(cache_root) / "model_artifacts" / "roformer_models" / model_name
    )
    model_directory.mkdir(parents=True, exist_ok=True)
    cache_directory.parent.mkdir(parents=True, exist_ok=True)
    if separator_factory is not None:
        vocal, sample_rate, weights = separator_factory(
            song_path=song_path,
            model_name=model_name,
            model_directory=model_directory,
            device=str(compute_device),
        )
    else:
        vocal, sample_rate, weights = _run_bs_roformer(
            song_path,
            model_name=model_name,
            model_directory=model_directory,
            device=compute_device,
        )
    vocal = np.asarray(vocal, dtype=np.float32)
    if vocal.ndim == 2:
        vocal = np.mean(vocal, axis=0, dtype=np.float32)
    if vocal.ndim != 1 or vocal.size == 0 or not np.isfinite(vocal).all():
        raise ValueError(f"RoFormer returned an invalid vocal stem shape: {vocal.shape}")

    data_path = cache_directory / "vocal_stem.npz"
    cache_directory.mkdir(parents=True, exist_ok=True)
    _write_npz_atomic(data_path, audio=vocal)
    artifact_sha256 = _file_sha256(data_path)
    manifest = {
        "format_version": 1,
        **cache_config,
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(song_path),
        "sample_rate": int(sample_rate),
        "sample_count": int(vocal.size),
        "dtype": "float32",
        "data_file": data_path.name,
        "artifact_sha256": artifact_sha256,
        "weights": weights,
        "paper": ROFORMER_PAPER,
        "model_card_url": "https://github.com/openmirlab/bs-roformer-infer",
        "compute_device": str(compute_device),
    }
    _write_json_atomic(cache_directory / "manifest.json", manifest)
    return VocalStemArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        audio=vocal,
        sample_rate=int(sample_rate),
        cache_hit=False,
    )


def extract_or_load_vocal_stem_with_backend(
    song_path,
    *,
    backend=DEFAULT_VOCAL_BACKEND,
    cache_root,
    source_sha256=None,
    model_name=None,
    device=DEFAULT_TORCH_DEVICE,
    separator_factory=None,
):
    """Dispatch to the requested vocal separator, defaulting to RoFormer."""
    backend = str(backend).lower()
    if backend == "roformer":
        return extract_or_load_roformer_vocal_stem(
            song_path,
            cache_root=cache_root,
            source_sha256=source_sha256,
            model_name=model_name or DEFAULT_ROFORMER_MODEL,
            device=device,
            separator_factory=separator_factory,
        )
    if backend == "demucs":
        return extract_or_load_vocal_stem(
            song_path,
            cache_root=cache_root,
            source_sha256=source_sha256,
            model_name=model_name or DEFAULT_DEMUCS_MODEL,
            device=device,
            separator_factory=separator_factory,
        )
    raise ValueError("backend must be 'roformer' or 'demucs'")


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


def _roformer_weight_provenance(model_path, model_name):
    """Record local model-file identity when BS-RoFormer downloaded it."""
    if model_path.is_file():
        return {
            "provider": "BS-RoFormer model registry",
            "model_filename": str(model_name),
            "path": str(model_path),
            "sha256": _file_sha256(model_path),
            "size_bytes": int(model_path.stat().st_size),
        }
    return {
        "provider": "BS-RoFormer model registry",
        "model_filename": str(model_name),
        "path": str(model_path),
        "sha256": None,
        "size_bytes": None,
        "provenance_error": "Downloaded model file was not found after loading",
    }


def _run_bs_roformer(song_path, *, model_name, model_directory, device):
    """Download, load and run one BS-RoFormer model on a complete track."""
    import torch
    import yaml
    from ml_collections import ConfigDict
    from bs_roformer import MODEL_REGISTRY, demix_track, get_model_from_config
    from bs_roformer.inference import SafeLoaderWithTuple
    from bs_roformer.download import download_model_assets

    try:
        model = MODEL_REGISTRY.get(model_name)
    except KeyError as error:
        raise ValueError(f"Unknown BS-RoFormer model: {model_name}") from error
    asset_directory = model_directory.parent / model.slug
    if not download_model_assets([model], model_directory.parent):
        raise RuntimeError(f"Could not download BS-RoFormer assets for {model_name}")
    model_path = asset_directory / model.checkpoint
    config_path = asset_directory / model.config
    with config_path.open(encoding="utf-8") as handle:
        config = ConfigDict(yaml.load(handle, Loader=SafeLoaderWithTuple))
    network = get_model_from_config("bs_roformer", config)
    state = torch.load(model_path, map_location="cpu", weights_only=True)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    network.load_state_dict(state)
    network = network.to(device).eval()
    mixture, sample_rate = sf.read(song_path, dtype="float32", always_2d=False)
    mixture = np.asarray(mixture, dtype=np.float32)
    if mixture.ndim == 1:
        mixture = np.stack((mixture, mixture), axis=1)
    mixture_tensor = torch.from_numpy(mixture.T)
    separated, _ = demix_track(config, network, mixture_tensor, device)
    if "vocals" not in separated:
        raise ValueError(f"BS-RoFormer model {model_name!r} returned no vocals stem")
    weights = _roformer_weight_provenance(model_path, model_name)
    weights["config_filename"] = model.config
    weights["config_sha256"] = _file_sha256(config_path)
    return separated["vocals"], int(sample_rate), weights


def _package_version(distribution_name):
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return "uninstalled"


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
