"""Inference adapter for the locally trained fixed-length control models."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace


from src.artifact_paths import artifact_path


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
            checkpoint_path = artifact_path(checkpoint["path"], manifest_path.parent)
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
    from src.features import (
        BEATS_PER_BAR,
        FEATURE_PROTOCOL_VERSION,
        build_global_pair_features,
        extract_or_load_track_features,
        validate_feature_array,
        validate_global_feature_array,
    )
    from src.ml.inference_contract import fixed_preview_renderer_options, load_fixed_inference_contract
    from src.tempo.coordinates import aligned_cue_sample

    run = _load_model_run(Path(model_run))
    run_contract = run.manifest["contract"]
    contract = load_fixed_inference_contract(run_contract, transition_bars=transition_bars)
    sample_rate = contract.sample_rate
    renderer_options = fixed_preview_renderer_options(run_contract, sample_rate=sample_rate)
    normalization = contract.normalization

    source_path = Path(source_path).resolve()
    target_path = Path(target_path).resolve()
    analyses = {source_path: analysis(str(source_path))}
    if target_path != source_path:
        analyses[target_path] = analysis(str(target_path))

    def pair_analysis(path):
        # A retryable fallback must not change the grid halfway through a render.
        return analyses[Path(path).resolve()]

    detected_source_bpm, source_frames, source_grid = unpack_analysis_result(analyses[source_path])
    detected_target_bpm, target_frames, target_grid = unpack_analysis_result(analyses[target_path])
    source_bpm = _inference_bpm("source", source_bpm, detected_source_bpm)
    target_bpm = _inference_bpm("target", target_bpm, detected_target_bpm)
    source_rate = int(librosa.get_samplerate(str(source_path)))
    target_rate = int(librosa.get_samplerate(str(target_path)))
    aligned_source_seconds = _snap_to_downbeat(source_seconds, source_frames, source_rate)
    aligned_target_seconds = _snap_to_downbeat(target_seconds, target_frames, target_rate)
    source_cut = round(aligned_source_seconds * sample_rate)
    target_cut = round(aligned_target_seconds * sample_rate)

    source_sha = _sha256_file(Path(source_path))
    target_sha = _sha256_file(Path(target_path))
    candidate = {
        "source_track": {"path": str(source_path), "sha256": source_sha},
        "target_track": {"path": str(target_path), "sha256": target_sha},
        "source_bpm": float(source_bpm),
        "target_bpm": float(target_bpm),
        "source_cutpoint": {"sample": source_cut},
        "cue_sample_rate": sample_rate,
        "target_cutpoint": {"sample": target_cut},
        "transition_length_bars": contract.transition_bars,
        "transition_length_beats": contract.transition_bars * BEATS_PER_BAR,
    }

    feature_kwargs = {
        "cache_root": feature_cache,
        "analysis": pair_analysis,
        "analysis_root": analysis_cache,
        "sample_rate": sample_rate,
        "vocal_backend": contract.feature_vocals.backend,
        "vocal_model": contract.feature_vocals.model,
    }
    source_features_artifact = extract_or_load_track_features(
        source_path, target_bpm=None, **feature_kwargs
    )
    target_features_artifact = extract_or_load_track_features(
        target_path, target_bpm=float(source_bpm), **feature_kwargs
    )
    contract.validate_track_features(
        source_features_artifact, role="source", original_bpm=source_bpm, aligned_bpm=source_bpm,
    )
    contract.validate_track_features(
        target_features_artifact, role="target", original_bpm=target_bpm, aligned_bpm=source_bpm,
    )
    source_feature_cue = source_cut
    target_feature_cue = aligned_cue_sample(
        target_cut, original_bpm=target_bpm, aligned_bpm=source_bpm,
    )
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
    validate_feature_array(features_a, name="source model features")
    validate_feature_array(features_b, name="target model features")
    validate_global_feature_array(global_features, name="model global features")

    source_vocal = target_vocal = None
    waveform_vocals = contract.waveform_vocals
    if waveform_vocals is not None:
        source_audio, target_audio, source_vocal, target_vocal, geometry = extract_aligned_vocal_bridge(
            candidate, pair_analysis, sample_rate=sample_rate,
            feature_cache_root=feature_cache,
            vocal_backend=waveform_vocals.backend, vocal_model=waveform_vocals.model,
            include_context_audio=True,
        )
    else:
        source_audio, target_audio, geometry = extract_aligned_bridge(
            candidate, pair_analysis, sample_rate=sample_rate,
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
            renderer = DifferentiableTwoBandRenderer(**renderer_options)
            rendered = renderer(
                source_tensor, target_tensor,
                output.mix_position, output.low_end_position,
            )
        elif run.family == "vocal_time_shared_mlp_v2":
            renderer = DifferentiableVocalAwareRenderer(**renderer_options)
            rendered = renderer(
                source_tensor, target_tensor,
                torch.from_numpy(np.asarray(source_vocal, dtype=np.float32)),
                torch.from_numpy(np.asarray(target_vocal, dtype=np.float32)),
                output.mix_position, output.low_end_position, output.vocal_position,
                output.vocal_duck_a, output.vocal_duck_b,
            )
        else:
            renderer = DifferentiableFullBandTransitionRenderer(**renderer_options)
            controls = output.renderer_arguments(source_tensor.shape[-1])
            rendered = renderer(source_tensor, target_tensor, *controls)

    transition_audio = rendered.audio.detach().cpu().numpy().astype(np.float32, copy=False)
    transition_samples = int(geometry["transition_samples"])
    source_cut_sample = int(geometry["source_cut_sample"])
    target_cut_sample = int(geometry["target_cut_sample"])
    expected_context_samples = int(round(
        candidate["transition_length_beats"] * 60.0 / source_bpm * sample_rate
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
        "feature_protocol_version": FEATURE_PROTOCOL_VERSION,
        "dataset_id": contract.dataset_id,
        "dataset_manifest_sha256": run_contract["dataset"]["manifest_sha256"],
        "model_config": run_contract["model"]["config"],
        "normalization_stats_id": normalization.stats_id,
        "feature_vocal_backend": contract.feature_vocals.backend,
        "feature_vocal_model": contract.feature_vocals.model,
        "waveform_vocal_backend": waveform_vocals.backend if waveform_vocals else None,
        "waveform_vocal_model": waveform_vocals.model if waveform_vocals else None,
        "training_renderer": run_contract["renderer"],
        "preview_renderer": renderer_options,
        "tempo_alignment": geometry.get("tempo_alignment"),
        "analysis_cache": str(analysis_cache),
        "source_grid": source_grid.to_dict(),
        "target_grid": target_grid.to_dict(),
        "source_bpm": source_bpm,
        "target_bpm": target_bpm,
        "feature_cache_source": str(source_features_artifact.cache_directory),
        "feature_cache_target": str(target_features_artifact.cache_directory),
        "cue_source_seconds_snapped": aligned_source_seconds,
        "cue_target_seconds_snapped": aligned_target_seconds,
        "source_feature_cue_sample": source_feature_cue,
        "target_feature_cue_sample": target_feature_cue,
    }
    result = SimpleNamespace(
        audio=audio,
        sample_rate=sample_rate,
        renderer=run.family,
        tempo_backend=geometry["tempo_backend"],
        tempo_alignment=geometry.get("tempo_alignment"),
        transition_start_sample=transition_start_sample,
        transition_end_sample=transition_end_sample,
    )
    return result, model_provenance


def _inference_bpm(role, requested, detected):
    detected = float(detected)
    if not math.isfinite(detected) or detected <= 0:
        raise ValueError(f"Invalid {role} analysis BPM: {detected}")
    if requested is not None and not math.isclose(float(requested), detected):
        raise ValueError(f"Incompatible {role} BPM: requested {requested}, analysis returned {detected}")
    return detected


def _load_model_run(run_directory: Path) -> _ModelRun:
    manifest_path = run_directory / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
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
    if provenance["run_manifest_sha256"] != manifest_sha256:
        raise ValueError(f"Run manifest changed while loading the checkpoint: {manifest_path}")
    model.eval()
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
