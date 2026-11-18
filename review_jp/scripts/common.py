"""Gemeinsame Helfer für die Review-Skripte (nur lesend auf dem Repo).

Alle Skripte werden aus dem Repo-Root gestartet:

    review_jp/.venv/bin/python review_jp/scripts/<skript>.py

Pfade, die auf einem anderen Rechner anzupassen sind, stehen in RUNS unten.
Es wird bewusst NICHT die Dataset-Klasse des Repos benutzt: sie verlangt die
Original-Audiodateien und absolute Windows-Pfade aus examples.jsonl. Hier
werden nur die NPZ-Features und die fertigen Waveform-Caches gelesen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
OUT = REPO / "review_jp" / "results"
PLOTS = REPO / "review_jp" / "plots"
OUT.mkdir(parents=True, exist_ok=True)
PLOTS.mkdir(parents=True, exist_ok=True)

DATASETS = REPO / "output" / "datasets"
TOP3 = DATASETS / "feature_protocol_v1_top3_4bar_track_split_20260731"
TOP10 = DATASETS / "feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805"
CACHE_V1 = REPO / "output" / "ml_cache" / "bridge_waveform_v1"
CACHE_V2 = REPO / "output" / "ml_cache" / "bridge_waveform_v2_vocal"
RUN_ROOT = REPO / "output" / "training_runs"

# ---------------------------------------------------------------------------
# HIER ANPASSEN, wenn andere Läufe geprüft werden sollen (z. B. TCN/BiLSTM
# oder die September-Läufe). kind: "mlp_v1" | "vocal_mlp_v2" | "tcn_v1".
# ---------------------------------------------------------------------------
RUNS = {
    "mlp_v1_top3": {
        "kind": "mlp_v1",
        "run": RUN_ROOT / "time_shared_mlp_v1_objective_v4_seed20260804_20260804",
        "dataset": TOP3,
        "cache": CACHE_V1,
    },
    "vocal_v2_top3": {
        "kind": "vocal_mlp_v2",
        "run": RUN_ROOT / "vocal_time_shared_mlp_v2_objective_v5_seed20260805_20260805",
        "dataset": TOP3,
        "cache": CACHE_V2,
    },
    "vocal_v2_top10": {
        "kind": "vocal_mlp_v2",
        "run": RUN_ROOT
        / "vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805",
        "dataset": TOP10,
        "cache": CACHE_V2,
    },
}

ALLOWED_SPLITS = ("train", "validation")


def load_split(dataset_dir: Path, split: str) -> dict:
    """Lädt train/validation. Der Test-Split wird absichtlich verweigert."""
    if split not in ALLOWED_SPLITS:
        raise ValueError("Review-Regel: Test-Split wird nicht geöffnet")
    with np.load(Path(dataset_dir) / f"{split}.npz", allow_pickle=False) as payload:
        return {
            "example_ids": [str(v) for v in payload["example_ids"]],
            "features_a": np.asarray(payload["features_a"], dtype=np.float32),
            "features_b": np.asarray(payload["features_b"], dtype=np.float32),
            "global_features": np.asarray(payload["global_features"], dtype=np.float32),
        }


def load_metadata(dataset_dir: Path) -> dict:
    """examples.jsonl, nur Zeilen der Splits train/validation."""
    rows = {}
    for line in (Path(dataset_dir) / "examples.jsonl").read_text("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["split"] in ALLOWED_SPLITS:
            rows[row["example_id"]] = row
    return rows


def load_waveforms(cache_root: Path, example_id: str, sample_rate: int = 11025) -> dict:
    """Liest den (einzigen) passenden Bridge-Waveform-Cache eines Beispiels."""
    matches = []
    for directory in sorted((Path(cache_root) / example_id).glob("*")):
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text("utf-8"))
        if int(manifest.get("training_sample_rate", -1)) == sample_rate:
            matches.append(directory)
    if len(matches) != 1:
        raise FileNotFoundError(
            f"{example_id}: erwartet genau einen Cache mit {sample_rate} Hz, "
            f"gefunden {len(matches)} unter {cache_root}"
        )
    with np.load(matches[0] / "bridge_waveforms.npz", allow_pickle=False) as payload:
        return {name: torch.from_numpy(np.asarray(payload[name], dtype=np.float32))
                for name in payload.files}


def load_checkpoint_state(run_dir: Path, which: str = "best") -> dict:
    checkpoint = torch.load(
        Path(run_dir) / "checkpoints" / f"{which}.pt",
        map_location="cpu",
        weights_only=True,
    )
    return checkpoint


def build_model(kind: str, manifest: dict):
    from src.ml.model import (
        FeatureControlMLP,
        FeatureControlMLPConfig,
        TCNBiLSTMTransitionControl,
        TCNBiLSTMTransitionControlConfig,
        VocalFeatureControlMLP,
        VocalFeatureControlMLPConfig,
    )

    config = dict(manifest["contract"]["model"]["config"])
    if kind == "mlp_v1":
        config["hidden_dimensions"] = tuple(config["hidden_dimensions"])
        return FeatureControlMLP(FeatureControlMLPConfig(**config))
    if kind == "vocal_mlp_v2":
        config["hidden_dimensions"] = tuple(config["hidden_dimensions"])
        return VocalFeatureControlMLP(VocalFeatureControlMLPConfig(**config))
    if kind == "tcn_v1":
        config["encoder_channels"] = tuple(config["encoder_channels"])
        return TCNBiLSTMTransitionControl(TCNBiLSTMTransitionControlConfig(**config))
    raise ValueError(kind)


def load_run(name: str, which: str = "best"):
    spec = RUNS[name]
    manifest = json.loads((spec["run"] / "manifest.json").read_text("utf-8"))
    model = build_model(spec["kind"], manifest)
    checkpoint = load_checkpoint_state(spec["run"], which)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return spec, manifest, model, checkpoint


def build_renderer_and_objective(kind: str, manifest: dict):
    from src.control import (
        DifferentiableTransitionObjective,
        DifferentiableTransitionObjectiveConfig,
        DifferentiableTwoBandRenderer,
        DifferentiableVocalAwareRenderer,
        VocalAwareTransitionObjective,
    )
    from src.control.differentiable import (
        DifferentiableFullBandTransitionRenderer,
        VocalAwareTransitionObjectiveConfig,
    )

    training = manifest["contract"]["training"]
    renderer_kwargs = {
        "sample_rate": int(training["training_sample_rate"]),
        "lowpass_cutoff_hz": float(training["lowpass_cutoff_hz"]),
        "lowpass_kernel_size": int(training["lowpass_kernel_size"]),
    }
    objective_config = manifest["contract"]["objective"]["config"]
    frames = int(manifest["contract"]["objective"]["energy_frames"])
    if kind == "vocal_mlp_v2":
        return (
            DifferentiableVocalAwareRenderer(**renderer_kwargs),
            VocalAwareTransitionObjective(
                VocalAwareTransitionObjectiveConfig(**objective_config), energy_frames=frames
            ),
        )
    objective = DifferentiableTransitionObjective(
        DifferentiableTransitionObjectiveConfig(**objective_config), energy_frames=frames
    )
    if kind == "tcn_v1":
        return DifferentiableFullBandTransitionRenderer(**renderer_kwargs), objective
    return DifferentiableTwoBandRenderer(**renderer_kwargs), objective


def equal_power_reference(points: int = 32) -> torch.Tensor:
    """Lineare Positionskurve 0..1; cos/sin davon ist der Equal-Power-Crossfade."""
    return torch.linspace(0.0, 1.0, points)


def dump_json(name: str, payload) -> Path:
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return path
