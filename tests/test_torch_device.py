import pytest
import torch

from src.torch_device import resolve_torch_device, validate_torch_device_spec


def test_auto_prefers_cuda_when_available(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_torch_device("auto") == torch.device("cuda:0")


def test_auto_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_torch_device("auto") == torch.device("cpu")


def test_device_validation_rejects_other_accelerators():
    with pytest.raises(ValueError, match="auto, cpu, cuda"):
        validate_torch_device_spec("mps")
