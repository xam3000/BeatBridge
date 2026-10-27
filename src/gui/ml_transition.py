"""Inference adapter for the locally trained fixed-length control models."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


SUPPORTED_GUI_MODELS = {
    "time_shared_mlp_v1",
    "vocal_time_shared_mlp_v2",
    "tcn_bilstm_transition_control_v1",
}


def discover_control_models(run_root: Path):
    """Return completed fixed-length model runs with a declared best checkpoint."""
    items = []
    if not run_root.is_dir():
        return items
    for manifest_path in run_root.rglob("manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            model_name = manifest.get("contract", {}).get("model", {}).get("name")
            checkpoint = manifest.get("files", {}).get("best_checkpoint")
            if (
                model_name not in SUPPORTED_GUI_MODELS
                or manifest.get("status") not in {"completed", "early_stopped"}
                or not isinstance(checkpoint, dict)
            ):
                continue
            checkpoint_path = manifest_path.parent / checkpoint["path"]
            if checkpoint_path.is_file():
                label = f"{model_name} · {manifest_path.parent.name}"
                items.append((label, manifest_path.parent.resolve()))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(items, key=lambda item: (item[0].split(" · ")[0], item[0]), reverse=False)


@dataclass(frozen=True)
class _ModelRun:
    model: object
    family: str
    manifest: dict
    manifest_path: Path
    provenance: dict


def render_model_transition(
    source_path,
    target_path,
    *,
    source_seconds,
    target_seconds,
    source_bpm,
    target_bpm,
    transition_bars,
    analysis,
    analysis_cache,
    feature_cache,
    model_run,
):
    """Extract protocol-matched features, infer controls, and render one pair."""
    import librosa
    import numpy as np
    import torch

    from src.analysis.models import unpack_analysis_result
    from src.bridge import extract_aligned_bridge, extract_aligned_vocal_bridge
    from src.control import (
        DifferentiableFullBandTransitionRenderer,
        DifferentiableTwoBandRenderer,
        DifferentiableVocalAwareRenderer,
    )
    from src.features import FeatureNormalizationStats, build_global_pair_features, extract_or_load_track_features
    from src.pipeline import DEFAULT_SAMPLE_RATE

    run = _load_model_run(Path(model_run))
    dataset_contract = run.manifest["contract"]["dataset"]
    dataset_root = Path(dataset_contract["path"])
    dataset_manifest_path = dataset_root / "manifest.json"
    dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    expected_dataset_sha = dataset_contract["manifest_sha256"]
    actual_dataset_sha = _sha256_file(dataset_manifest_path)
    if actual_dataset_sha != expected_dataset_sha:
        raise ValueError("Dataset manifest SHA differs from the model training contract")
    if int(dataset_manifest.get("sample_rate", 0)) != DEFAULT_SAMPLE_RATE:
        raise ValueError("The selected model uses a feature sample rate this GUI adapter does not support")
    normalizer = dataset_manifest.get("normalization", {})
    normalization = FeatureNormalizationStats(
        spectral_flux_log1p_p99=float(normalizer["spectral_flux_log1p_p99"]),
        onset_strength_log1p_p99=float(normalizer["onset_strength_log1p_p99"]),
        stats_id=str(normalizer["stats_id"]),
    )

    source_result = analysis(str(source_path))
    target_result = analysis(str(target_path))
    _, source_frames, _ = unpack_analysis_result(source_result)
    _, target_frames, _ = unpack_analysis_result(target_result)
    source_rate = int(librosa.get_samplerate(str(source_path)))
    target_rate = int(librosa.get_samplerate(str(target_path)))
    aligned_source_seconds = _snap_to_downbeat(source_seconds, source_frames, source_rate)
    aligned_target_seconds = _snap_to_downbeat(target_seconds, target_frames, target_rate)
    source_cut = int(round(aligned_source_seconds * DEFAULT_SAMPLE_RATE))
    target_cut = int(round(aligned_target_seconds * DEFAULT_SAMPLE_RATE))

    source_sha = _sha256_file(Path(source_path))
    target_sha = _sha256_file(Path(target_path))
    candidate = {
        "source_track": {"path": str(Path(source_path).resolve()), "sha256": source_sha},
        "target_track": {"path": str(Path(target_path).resolve()), "sha256": target_sha},
        "source_bpm": float(source_bpm),
        "target_bpm": float(target_bpm),
        "source_cutpoint": {"sample": source_cut},
        "target_cutpoint": {"sample": target_cut},
        "transition_length_bars": int(transition_bars),
        "transition_length_beats": int(transition_bars) * 4,
    }

    if run.family == "vocal_time_shared_mlp_v2":
        from src.features.vocal import DEFAULT_ROFORMER_MODEL

        vocal_backend, vocal_model = "roformer", DEFAULT_ROFORMER_MODEL
    else:
        vocal_backend = str(dataset_manifest.get("vocal_backend", "disabled"))
        vocal_model = str(dataset_manifest.get("vocal_model", "htdemucs"))
    feature_kwargs = {
        "cache_root": feature_cache,
        "analysis": analysis,
        "analysis_root": analysis_cache,
        "sample_rate": DEFAULT_SAMPLE_RATE,
        "vocal_backend": vocal_backend,
        "vocal_model": vocal_model,
    }
    source_features_artifact = extract_or_load_track_features(
        source_path, target_bpm=None, **feature_kwargs
    )
    target_features_artifact = extract_or_load_track_features(
        target_path, target_bpm=float(source_bpm), **feature_kwargs
    )
    source_feature_cue = int(round(aligned_source_seconds * DEFAULT_SAMPLE_RATE))
    target_feature_cue = int(round(aligned_target_seconds * DEFAULT_SAMPLE_RATE * float(source_bpm) / float(target_bpm)))
    features_a = source_features_artifact.model_window(
        source_feature_cue, role="source", normalization=normalization
    )
    features_b = target_features_artifact.model_window(
        target_feature_cue, role="target", normalization=normalization
    )
    global_features = build_global_pair_features(
        features_a, features_b,
        bpm_a=float(source_bpm), bpm_b=float(target_bpm),
        artifact_a=source_features_artifact, artifact_b=target_features_artifact,
        cue_sample_a=source_feature_cue, cue_sample_b=target_feature_cue,
    )

    source_vocal = target_vocal = None
    if run.family == "vocal_time_shared_mlp_v2":
        source_audio, target_audio, source_vocal, target_vocal, geometry = extract_aligned_vocal_bridge(
            candidate, analysis, sample_rate=DEFAULT_SAMPLE_RATE,
            vocal_backend=vocal_backend, vocal_model=vocal_model,
            include_context_audio=True,
        )
    else:
        source_audio, target_audio, geometry = extract_aligned_bridge(
            candidate, analysis, sample_rate=DEFAULT_SAMPLE_RATE,
            include_context_audio=True,
        )
    source_tensor = torch.from_numpy(np.asarray(source_audio, dtype=np.float32))
    target_tensor = torch.from_numpy(np.asarray(target_audio, dtype=np.float32))
    with torch.no_grad():
        output = run.model(
            torch.from_numpy(features_a),
            torch.from_numpy(features_b),
            torch.from_numpy(global_features),
        )
        if run.family == "time_shared_mlp_v1":
            renderer_contract = run.manifest["contract"]["renderer"]
            renderer = DifferentiableTwoBandRenderer(
                sample_rate=DEFAULT_SAMPLE_RATE,
                lowpass_cutoff_hz=float(renderer_contract["lowpass_cutoff_hz"]),
                lowpass_kernel_size=511,
            )
            rendered = renderer(
                source_tensor, target_tensor,
                output.mix_position, output.low_end_position,
            )
        elif run.family == "vocal_time_shared_mlp_v2":
            renderer_contract = run.manifest["contract"]["renderer"]
            renderer = DifferentiableVocalAwareRenderer(
                sample_rate=DEFAULT_SAMPLE_RATE,
                lowpass_cutoff_hz=float(renderer_contract["lowpass_cutoff_hz"]),
                lowpass_kernel_size=511,
            )
            rendered = renderer(
                source_tensor, target_tensor,
                torch.from_numpy(np.asarray(source_vocal, dtype=np.float32)),
                torch.from_numpy(np.asarray(target_vocal, dtype=np.float32)),
                output.mix_position, output.low_end_position, output.vocal_position,
                output.vocal_duck_a, output.vocal_duck_b,
            )
        else:
            renderer_contract = run.manifest["contract"]["renderer"]
            renderer = DifferentiableFullBandTransitionRenderer(
                sample_rate=DEFAULT_SAMPLE_RATE,
                lowpass_cutoff_hz=float(renderer_contract["lowpass_cutoff_hz"]),
                midpass_cutoff_hz=float(renderer_contract.get("midpass_cutoff_hz", 3500.0)),
                lowpass_kernel_size=511,
            )
            controls = [output[name] for name in (
                "gain_A", "gain_B", "eq_low_A", "eq_low_B", "eq_mid_A",
                "eq_mid_B", "eq_high_A", "eq_high_B", "low_end_ownership", "vocal_ducking",
            )]
            rendered = renderer(source_tensor, target_tensor, *controls)

    transition_audio = rendered.audio.detach().cpu().numpy().astype(np.float32, copy=False)
    transition_samples = int(geometry["transition_samples"])
    source_cut_sample = int(geometry["source_cut_sample"])
    target_cut_sample = int(geometry["target_cut_sample"])
    expected_context_samples = int(round(
        int(transition_bars) * 4 * 60.0 / float(source_bpm) * DEFAULT_SAMPLE_RATE
    ))
    context_samples = max(transition_samples, expected_context_samples)
    source_context = geometry["source_audio"]
    target_context = geometry["target_audio"]
    pre_audio = source_context[..., max(0, source_cut_sample - context_samples):source_cut_sample]
    post_audio = target_context[..., target_cut_sample:target_cut_sample + context_samples]
    if pre_audio.shape[-1] != context_samples or post_audio.shape[-1] != context_samples:
        raise ValueError("Das Modellpreview braucht einen vollständigen Vor- und Nachlauf von je vier Takten")
    audio = np.concatenate((pre_audio, transition_audio, post_audio), axis=-1).astype(np.float32, copy=False)
    transition_start_sample = int(pre_audio.shape[-1])
    transition_end_sample = transition_start_sample + int(transition_audio.shape[-1])
    model_provenance = {
        "model_name": run.family,
        "run_id": run.manifest.get("run_id"),
        "run_manifest": str(run.manifest_path.resolve()),
        "run_manifest_sha256": run.provenance["run_manifest_sha256"],
        "checkpoint": run.provenance["checkpoint_path"],
        "checkpoint_sha256": run.provenance["checkpoint_sha256"],
        "checkpoint_epoch": run.provenance["checkpoint_epoch"],
        "feature_protocol_version": 1,
        "normalization_stats_id": normalization.stats_id,
        "analysis_cache": str(analysis_cache),
        "feature_cache_source": str(source_features_artifact.cache_directory),
        "feature_cache_target": str(target_features_artifact.cache_directory),
        "cue_source_seconds_snapped": aligned_source_seconds,
        "cue_target_seconds_snapped": aligned_target_seconds,
    }
    result = SimpleNamespace(
        audio=audio,
        sample_rate=DEFAULT_SAMPLE_RATE,
        renderer=run.family,
        tempo_backend=geometry["tempo_backend"],
        transition_start_sample=transition_start_sample,
        transition_end_sample=transition_end_sample,
    )
    return result, model_provenance


def _load_model_run(run_directory: Path) -> _ModelRun:
    manifest_path = run_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    family = manifest.get("contract", {}).get("model", {}).get("name")
    if family == "time_shared_mlp_v1":
        from src.evaluation.ml_control_study import _load_best_model

        model, provenance, _, _ = _load_best_model(run_directory)
    elif family == "vocal_time_shared_mlp_v2":
        from src.evaluation.vocal_ml_control_study import _load_best_vocal_model

        model, _, provenance, _, _ = _load_best_vocal_model(run_directory)
    elif family == "tcn_bilstm_transition_control_v1":
        from src.evaluation.all_models_control_study import _load_best_tcn

        model, provenance = _load_best_tcn(run_directory)
    else:
        raise ValueError(f"Nicht unterstütztes GUI-Modell: {family}")
    model.eval()
    provenance["run_manifest_sha256"] = _sha256_file(manifest_path)
    return _ModelRun(model, family, manifest, manifest_path, provenance)


def _snap_to_downbeat(seconds: float, beat_frames, sample_rate: int) -> float:
    downbeats = [
        int(frame[0]) / int(sample_rate)
        for frame in beat_frames
        if isinstance(frame, (tuple, list)) and len(frame) >= 3 and int(frame[1]) == 1
    ]
    if not downbeats:
        raise ValueError("Für das ausgewählte Modell wurde kein Downbeat im Analyse-Cache gefunden")
    return min(downbeats, key=lambda value: abs(value - float(seconds)))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
