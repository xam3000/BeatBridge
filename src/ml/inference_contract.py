"""Read the fixed-controller input contract used by training."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from src.features import (
    DATASET_FORMAT_VERSION,
    FEATURE_PROTOCOL_VERSION,
    GLOBAL_PAIR_EXTRACTOR_VERSION,
    TRANSITION_BARS,
    FeatureNormalizationStats,
    feature_schema,
)
from src.features.vocal import DEFAULT_DEMUCS_MODEL
from src.artifact_paths import artifact_path
from src.pipeline import DEFAULT_SAMPLE_RATE


@dataclass(frozen=True)
class VocalInput:
    backend: str
    model: str | None


@dataclass(frozen=True)
class FixedInferenceContract:
    dataset_id: str
    sample_rate: int
    transition_bars: int
    normalization: FeatureNormalizationStats
    feature_vocals: VocalInput
    waveform_vocals: VocalInput | None

    def validate_track_features(self, artifact, *, role, original_bpm, aligned_bpm):
        for key, expected in {
            "feature_protocol_version": FEATURE_PROTOCOL_VERSION,
            "sample_rate": self.sample_rate,
            "original_bpm": original_bpm,
            "aligned_bpm": aligned_bpm,
            "vocal_backend": self.feature_vocals.backend,
            "vocal_model": self.feature_vocals.model,
        }.items():
            _expect(f"{role} features.{key}", artifact.manifest.get(key), expected)


def load_fixed_inference_contract(run_contract, *, transition_bars):
    """Resolve input features/normalization and renderer stems independently."""
    declared = run_contract["dataset"]
    dataset_path = artifact_path(declared["path"]) / "manifest.json"
    dataset = _read_bound_manifest(dataset_path, declared["manifest_sha256"])
    _expect("dataset.dataset_id", dataset.get("dataset_id"), declared["dataset_id"])
    _expect("dataset.format_version", dataset.get("format_version"), DATASET_FORMAT_VERSION)
    _expect(
        "dataset.feature_protocol_version",
        dataset.get("feature_protocol_version"),
        FEATURE_PROTOCOL_VERSION,
    )
    _expect(
        "dataset.global_pair_extractor_version",
        dataset.get("global_pair_extractor_version"),
        GLOBAL_PAIR_EXTRACTOR_VERSION,
    )
    _expect("dataset.sample_rate", dataset.get("sample_rate"), DEFAULT_SAMPLE_RATE)
    _expect("dataset.transition_bars", dataset.get("transition_bars"), TRANSITION_BARS)
    _expect("requested transition_bars", transition_bars, dataset["transition_bars"])
    schema = dataset.get("feature_schema", {})
    for key, expected in feature_schema().items():
        if key in ("features", "global_features"):
            _expect(
                f"dataset.feature_schema.{key} channel order",
                [channel["name"] for channel in schema.get(key, [])],
                [channel["name"] for channel in expected],
            )
        else:
            _expect(f"dataset.feature_schema.{key}", schema.get(key), expected)

    normalizer = dataset.get("normalization", {})
    _expect(
        "dataset.normalization.fit_scope", normalizer.get("fit_scope"), "training_tracks_only",
    )
    stats_id = normalizer.get("stats_id")
    if not isinstance(stats_id, str) or not stats_id.strip():
        raise ValueError(f"Invalid dataset.normalization.stats_id: {stats_id!r}")
    try:
        normalization = FeatureNormalizationStats(
            spectral_flux_log1p_p99=float(normalizer["spectral_flux_log1p_p99"]),
            onset_strength_log1p_p99=float(normalizer["onset_strength_log1p_p99"]),
            stats_id=stats_id,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid dataset.normalization: {error}") from error

    feature_vocals = _vocal_input(dataset, "dataset", allow_disabled=True)
    waveform_vocals = None
    if run_contract["model"]["name"] == "vocal_time_shared_mlp_v2":
        waveform_vocals = _load_waveform_vocals(run_contract)
    return FixedInferenceContract(
        dataset_id=dataset["dataset_id"],
        sample_rate=dataset["sample_rate"],
        transition_bars=dataset["transition_bars"],
        normalization=normalization,
        feature_vocals=feature_vocals,
        waveform_vocals=waveform_vocals,
    )


def fixed_preview_renderer_options(run_contract, *, sample_rate):
    """Use the trained filter settings at the preview's full sample rate."""
    family = run_contract["model"]["name"]
    renderer = run_contract["renderer"]
    protocol = renderer.get("control_protocol_version")
    if family == "tcn_bilstm_transition_control_v1":
        _expect(
            "renderer.name", renderer.get("name"), "differentiable_full_band_transition_v1",
        )
        # The historical full-band runner recorded the inherited protocol 3.
        if protocol != 5:
            _expect("renderer.control_protocol_version", protocol, 3)
        _expect("renderer.control_outputs", renderer.get("control_outputs"), 10)
    else:
        expected_protocol = 4 if family == "vocal_time_shared_mlp_v2" else 3
        _expect("renderer.control_protocol_version", protocol, expected_protocol)

    training_rate = renderer.get("sample_rate")
    kernel = renderer.get("lowpass_kernel_size")
    if not isinstance(training_rate, int) or training_rate <= 0:
        raise ValueError(f"Invalid renderer.sample_rate: {training_rate!r}")
    if not isinstance(kernel, int) or kernel < 3 or kernel % 2 != 1:
        raise ValueError(f"Invalid renderer.lowpass_kernel_size, expected odd taps >= 3: {kernel!r}")
    half_window = round((kernel + 1) / 2 * sample_rate / training_rate)
    options = {"sample_rate": sample_rate, "lowpass_kernel_size": max(3, 2 * half_window - 1)}
    cutoff_names = ["lowpass_cutoff_hz"]
    if family == "tcn_bilstm_transition_control_v1":
        cutoff_names.append("midpass_cutoff_hz")
    previous_cutoff = 0.0
    for name in cutoff_names:
        cutoff = renderer.get(name)
        if not isinstance(cutoff, (int, float)) or not math.isfinite(cutoff) or not (
            previous_cutoff < cutoff < min(training_rate, sample_rate) / 2
        ):
            raise ValueError(f"Invalid renderer.{name}: {cutoff!r} for {training_rate} Hz training")
        options[name] = float(cutoff)
        previous_cutoff = cutoff
    return options


def _load_waveform_vocals(run_contract):
    waveform = run_contract.get("waveform_cache", {})
    declared_backend = waveform.get("vocal_backend")
    declared_model = waveform.get("vocal_model")
    records = run_contract["dataset"].get("vocal_waveform_cache_manifests", {})
    backends = set()
    for split in ("train", "validation"):
        for record in records.get(split, []):
            path = artifact_path(record["path"])
            cache = _read_bound_manifest(path, record["sha256"])
            _expect(f"{path}.vocal_model", cache.get("vocal_model"), declared_model)
            backend = cache.get("vocal_backend")
            # August format-2 waveform manifests predate the backend field.
            if backend is None and cache.get("format_version") == 2 and declared_model == DEFAULT_DEMUCS_MODEL:
                backend = "demucs"
            if backend not in {"demucs", "roformer"}:
                raise ValueError(f"Missing or unsupported waveform vocal backend {backend!r} in {path}")
            if declared_backend is not None:
                _expect(f"{path}.vocal_backend", backend, declared_backend)
            backends.add(backend)
    if len(backends) > 1:
        raise ValueError(f"Training waveform manifests declare multiple vocal backends: {sorted(backends)}")
    return _vocal_input(
        {"vocal_backend": declared_backend or next(iter(backends), None), "vocal_model": declared_model},
        "run.waveform_cache",
    )


def _vocal_input(contract, name, *, allow_disabled=False):
    backend = contract.get("vocal_backend")
    model = contract.get("vocal_model")
    if allow_disabled and backend == "disabled":
        _expect(f"{name}.vocal_model", model, None)
    elif backend not in {"demucs", "roformer"}:
        raise ValueError(f"Missing or unsupported {name}.vocal_backend: {backend!r}")
    elif not isinstance(model, str) or not model.strip():
        raise ValueError(f"Missing or invalid {name}.vocal_model for {backend}: {model!r}")
    return VocalInput(backend, model)


def _read_bound_manifest(path, expected_sha):
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(f"Cannot read training manifest {path}: {error}") from error
    _expect(f"{path} SHA-256", hashlib.sha256(raw).hexdigest(), expected_sha)
    try:
        manifest = json.loads(raw)
    except ValueError as error:
        raise ValueError(f"Invalid training manifest {path}: {error}") from error
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid training manifest {path}: expected a JSON object")
    return manifest


def _expect(field, actual, expected):
    if actual != expected:
        raise ValueError(f"Incompatible {field}: expected {expected!r}, got {actual!r}")
