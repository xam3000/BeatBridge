"""Frozen, locally verified MERT inference on a sample-aligned frame lattice."""

import hashlib
import importlib
import json
from pathlib import Path
import sys
import types

import numpy as np


SAMPLE_RATE = 24_000
REPO_ID = "m-a-p/MERT-v1-95M"
REVISION = "12af15fef9d0ac838c3f475bfbbf26d2060dd4f5"
MODEL_FILES = {
    "README.md": "4bd95e900185d8b393785c0038aa662355a904e5a98ec692003b8011c802455d",
    "config.json": "ea2627c4c7825cd66f3c944b6b966331604c35928174e0100cd4a82829424e32",
    "configuration_MERT.py": "ae0ec2bab8f59c724ba9878a7c20b67210189536ea62d34a56775968e9decb03",
    "modeling_MERT.py": "6c3ee73cef6f0c30ef494f88d96f891fa6925ffe663fa391b512f4b57abecc6c",
    "preprocessor_config.json": "cc5a5e4a5d3b1a758a5ed984b2eaa15bb0522d811d44a9eed82bfca4baa0dc8f",
    "pytorch_model.bin": "a2b8b747f72c06e0595aeae41ae5473f4364938c6b39b2c58be38c48e6bd3fcd",
}
TRANSFORMERS_VERSION = "4.49.0"
FRAME_STEP = 320
RECEPTIVE_FIELD = 400
LAYER_COUNT = 13
HIDDEN_SIZE = 768
CORE_SAMPLES = 20 * SAMPLE_RATE
CONTEXT_SAMPLES = 2 * SAMPLE_RATE


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model_identity():
    return dict(repo_id=REPO_ID, revision=REVISION, license="CC-BY-NC-4.0",
                sha256=MODEL_FILES, transformers=TRANSFORMERS_VERSION,
                sample_rate=SAMPLE_RATE, frame_step=FRAME_STEP,
                receptive_field=RECEPTIVE_FIELD, core_samples=CORE_SAMPLES,
                context_samples=CONTEXT_SAMPLES, attention="sdpa",
                precision="cuda_bfloat16_autocast_or_cpu_float32")


def chunk_spans(size):
    """Partition frame ownership by core interval; context overlaps adjacent cores."""
    if size < RECEPTIVE_FIELD:
        raise ValueError("Audio shorter than one MERT convolution frame")
    for start in range(0, size, CORE_SAMPLES):
        end = min(start + CORE_SAMPLES, size)
        yield start, end, max(0, start - CONTEXT_SAMPLES), min(size, end + CONTEXT_SAMPLES)


def frame_centres_twice(start, count):
    """Use integer coordinates to retain the half-sample convolution centre."""
    return 2 * (start + FRAME_STEP * np.arange(count, dtype=np.int64)) + RECEPTIVE_FIELD - 1


def bar_frame_slots(centres_twice, bars):
    indices = np.searchsorted(2 * bars[:, 0], centres_twice, side="right") - 1
    valid = (indices >= 0) & (centres_twice < 2 * bars[np.maximum(indices, 0), -1])
    return indices, valid


class FrozenMert:
    def __init__(self, directory, device):
        import torch
        import transformers

        self.torch = torch
        self.device = torch.device(device)
        if transformers.__version__ != TRANSFORMERS_VERSION:
            raise ValueError(f"P07 requires transformers {TRANSFORMERS_VERSION}")
        directory = Path(directory).resolve()
        for name, expected in MODEL_FILES.items():
            if file_sha256(directory / name) != expected:
                raise ValueError(f"Official MERT SHA-256 mismatch: {name}")

        # Import the two reviewed, hash-verified modules from this snapshot only.
        package_name = f"_beatbridge_mert_{REVISION}"
        package = types.ModuleType(package_name)
        package.__path__ = [str(directory)]
        sys.modules[package_name] = package
        config_type = importlib.import_module(f"{package_name}.configuration_MERT").MERTConfig
        model_type = importlib.import_module(f"{package_name}.modeling_MERT").MERTModel
        config = config_type.from_dict(json.loads((directory / "config.json").read_bytes()))
        config._attn_implementation = "sdpa"
        model = model_type(config)
        weights = torch.load(directory / "pytorch_model.bin", map_location="cpu", weights_only=True)
        model.load_state_dict(weights, strict=True)
        self.model = model.requires_grad_(False).eval().to(self.device)
        self.processor = transformers.Wav2Vec2FeatureExtractor.from_pretrained(
            str(directory), local_files_only=True
        )
        if self.processor.sampling_rate != SAMPLE_RATE:
            raise ValueError("Unexpected MERT input sample rate")

    def encode(self, audio, bars):
        if not len(bars):
            raise ValueError("MERT pooling requires a complete bar")
        torch = self.torch
        sums = torch.zeros((len(bars), LAYER_COUNT, HIDDEN_SIZE), device=self.device)
        counts = np.zeros(len(bars), dtype=np.int64)
        with torch.inference_mode():
            for start, end, left, right in chunk_spans(len(audio)):
                count = 1 + (right - left - RECEPTIVE_FIELD) // FRAME_STEP
                centres = frame_centres_twice(left, count)
                indices, valid = bar_frame_slots(centres, bars)
                valid &= (centres >= 2 * start) & (centres < 2 * end)
                if not valid.any():
                    continue
                encoded = self.processor(audio[left:right], sampling_rate=SAMPLE_RATE, return_tensors="pt")
                with torch.autocast(self.device.type, dtype=torch.bfloat16, enabled=self.device.type == "cuda"):
                    layers = self.model(
                        encoded.input_values.to(self.device), output_hidden_states=True
                    ).hidden_states
                if len(layers) != LAYER_COUNT or layers[-1].shape != (1, count, HIDDEN_SIZE):
                    raise ValueError("Unexpected MERT layer count or frame geometry")
                frame_ids = torch.as_tensor(np.flatnonzero(valid), device=self.device)
                frames = torch.stack([layer[0].index_select(0, frame_ids) for layer in layers], dim=1)
                selected = indices[valid]
                # Contiguous frame groups per bar. Reduce on GPU before moving to RAM.
                bar_ids, bar_counts = np.unique(selected, return_counts=True)
                lengths = torch.as_tensor(bar_counts, device=self.device)
                bar_sums = torch.segment_reduce(frames.float(), "sum", lengths=lengths)
                sums[torch.as_tensor(bar_ids, device=self.device)] += bar_sums
                counts[bar_ids] += bar_counts
            if np.any(counts == 0):
                raise ValueError("A complete bar has no MERT frames")
            result = (sums / torch.as_tensor(counts, device=self.device)[:, None, None]).cpu().numpy()
        return result, counts
