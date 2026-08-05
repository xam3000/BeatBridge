"""Shared PyTorch device selection for GPU-accelerated project paths."""

from __future__ import annotations

import torch


DEFAULT_TORCH_DEVICE = "auto"


def validate_torch_device_spec(device: str) -> str:
    """Return a normalized device spec or reject unsupported device types."""
    normalized = str(device).strip().lower()
    if normalized == DEFAULT_TORCH_DEVICE:
        return normalized
    try:
        parsed = torch.device(normalized)
    except (RuntimeError, ValueError) as error:
        raise ValueError("device must be auto, cpu, cuda, or cuda:<index>") from error
    if parsed.type not in {"cpu", "cuda"}:
        raise ValueError("device must be auto, cpu, cuda, or cuda:<index>")
    return normalized


def resolve_torch_device(device: str = DEFAULT_TORCH_DEVICE) -> torch.device:
    """Prefer CUDA for ``auto`` and fail clearly for unavailable CUDA requests."""
    normalized = validate_torch_device_spec(device)
    if normalized == DEFAULT_TORCH_DEVICE:
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    resolved = torch.device(normalized)
    if resolved.type != "cuda":
        return resolved
    if not torch.cuda.is_available():
        raise RuntimeError(f"Requested device is unavailable: {normalized}")
    index = resolved.index if resolved.index is not None else torch.cuda.current_device()
    if index < 0 or index >= torch.cuda.device_count():
        raise RuntimeError(
            f"Requested CUDA device index {index} is unavailable; "
            f"found {torch.cuda.device_count()} CUDA device(s)"
        )
    return torch.device(f"cuda:{index}")
