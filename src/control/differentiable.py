"""Differentiable two-band transition rendering and direct curve optimization."""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import nn
from torch.nn import functional as F

from src.features.contract import feature_index


CONTROL_PROTOCOL_VERSION = 3
OBJECTIVE_VERSION = 4
VOCAL_CONTROL_PROTOCOL_VERSION = 4
VOCAL_OBJECTIVE_VERSION = 5
FULL_BAND_CONTROL_PROTOCOL_VERSION = 5
CONTROL_NAMES = ("mix_position", "low_end_position")
DEFAULT_INCREMENT_LOGIT_BOUND = 0.6


@dataclass(frozen=True)
class DifferentiableRenderResult:
    """Audio plus sample-resolution controls produced by the renderer."""

    format_version: int
    audio: torch.Tensor
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    gain_a: torch.Tensor
    gain_b: torch.Tensor
    low_gain_a: torch.Tensor
    low_gain_b: torch.Tensor


@dataclass(frozen=True)
class VocalAwareRenderResult:
    """Rendered audio and sample-resolution mix, low-end, and vocal controls."""

    format_version: int
    audio: torch.Tensor
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    vocal_position: torch.Tensor
    gain_a: torch.Tensor
    gain_b: torch.Tensor
    low_gain_a: torch.Tensor
    low_gain_b: torch.Tensor
    vocal_gain_a: torch.Tensor
    vocal_gain_b: torch.Tensor
    vocal_duck_a: torch.Tensor
    vocal_duck_b: torch.Tensor


@dataclass(frozen=True)
class FullBandRenderResult:
    """Rendered audio and all ten TCN/BiLSTM control channels."""

    format_version: int
    audio: torch.Tensor
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    gain_a: torch.Tensor
    gain_b: torch.Tensor
    eq_low_a: torch.Tensor
    eq_low_b: torch.Tensor
    eq_mid_a: torch.Tensor
    eq_mid_b: torch.Tensor
    eq_high_a: torch.Tensor
    eq_high_b: torch.Tensor
    vocal_ducking: torch.Tensor
    vocal_gain_a: torch.Tensor
    vocal_gain_b: torch.Tensor
    low_gain_a: torch.Tensor
    low_gain_b: torch.Tensor


@dataclass(frozen=True)
class DifferentiableTransitionObjectiveConfig:
    """Weights and tolerances for the differentiable training objective."""

    energy_shape_weight: float = 1.0
    boundary_weight: float = 0.5
    control_smoothness_weight: float = 0.02
    control_curvature_weight: float = 0.05
    monotonicity_weight: float = 0.1
    clipping_weight: float = 2.0
    vocal_overlap_weight: float = 1.0
    vocal_boundary_weight: float = 0.30
    transient_artifact_weight: float = 0.08
    valley_depth_db: float = 6.0
    energy_tolerance_db: float = 12.0
    boundary_tolerance_db: float = 6.0
    epsilon: float = 1e-6

    def __post_init__(self):
        weights = (
            self.energy_shape_weight,
            self.boundary_weight,
            self.control_smoothness_weight,
            self.control_curvature_weight,
            self.monotonicity_weight,
            self.clipping_weight,
            self.vocal_overlap_weight,
            self.vocal_boundary_weight,
            self.transient_artifact_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("Objective weights must be greater than or equal to 0")
        if self.valley_depth_db < 0:
            raise ValueError("valley_depth_db must be greater than or equal to 0")
        if self.energy_tolerance_db <= 0 or self.boundary_tolerance_db <= 0:
            raise ValueError("Objective tolerances must be greater than 0")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be greater than 0")


@dataclass(frozen=True)
class VocalAwareTransitionObjectiveConfig(DifferentiableTransitionObjectiveConfig):
    """Objective-v5 weights for stem overlap and audible active vocals."""

    vocal_overlap_weight: float = 0.0
    vocal_boundary_weight: float = 0.0
    vocal_stem_overlap_weight: float = 1.0
    vocal_audibility_weight: float = 0.5
    vocal_mid_phrase_gain_change_weight: float = 0.2

    def __post_init__(self):
        super().__post_init__()
        if any(
            weight < 0
            for weight in (
                self.vocal_stem_overlap_weight,
                self.vocal_audibility_weight,
                self.vocal_mid_phrase_gain_change_weight,
            )
        ):
            raise ValueError("Vocal-aware objective weights must be non-negative")


class DifferentiableTwoBandRenderer(nn.Module):
    """Apply complementary full/high- and low-band ownership curves."""

    def __init__(
        self,
        sample_rate: int = 44_100,
        lowpass_cutoff_hz: float = 180.0,
        lowpass_kernel_size: int = 255,
    ):
        super().__init__()
        self.sample_rate = int(sample_rate)
        self.lowpass_cutoff_hz = float(lowpass_cutoff_hz)
        self.lowpass_kernel_size = int(lowpass_kernel_size)
        self._validate_config()
        self.register_buffer(
            "lowpass_kernel",
            _windowed_sinc_lowpass(
                self.sample_rate,
                self.lowpass_cutoff_hz,
                self.lowpass_kernel_size,
            ),
        )

    def _validate_config(self):
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")
        if not 0 < self.lowpass_cutoff_hz < self.sample_rate / 2:
            raise ValueError("lowpass_cutoff_hz must be between 0 and Nyquist")
        if self.lowpass_kernel_size < 3 or self.lowpass_kernel_size % 2 == 0:
            raise ValueError("lowpass_kernel_size must be an odd integer of at least 3")

    def forward(
        self,
        source_audio: torch.Tensor,
        target_audio: torch.Tensor,
        mix_position: torch.Tensor,
        low_end_position: torch.Tensor,
    ) -> DifferentiableRenderResult:
        source, squeezed = _normalise_audio(source_audio, "source_audio")
        target, target_squeezed = _normalise_audio(target_audio, "target_audio")
        if squeezed != target_squeezed:
            raise ValueError("source_audio and target_audio must have the same rank")
        if source.shape != target.shape:
            raise ValueError("source_audio and target_audio must have identical shapes")
        if source.device != target.device or source.dtype != target.dtype:
            raise ValueError("source_audio and target_audio must share device and dtype")
        if not source.is_floating_point():
            raise TypeError("Audio tensors must use a floating-point dtype")

        batch_size, _, sample_count = source.shape
        if sample_count <= self.lowpass_kernel_size // 2:
            raise ValueError("Audio is too short for the configured low-pass filter")

        mix_control = _normalise_control(
            mix_position,
            batch_size,
            source.device,
            source.dtype,
            "mix_position",
        )
        low_control = _normalise_control(
            low_end_position,
            batch_size,
            source.device,
            source.dtype,
            "low_end_position",
        )
        if mix_control.shape != low_control.shape:
            raise ValueError("mix_position and low_end_position must have identical shapes")

        mix_samples = _interpolate_control(mix_control, sample_count)
        low_samples = _interpolate_control(low_control, sample_count)
        gain_a, gain_b = _equal_power_pair(mix_samples)
        low_gain_a, low_gain_b = _equal_power_pair(low_samples)

        source_low = self._lowpass(source)
        target_low = self._lowpass(target)
        source_high = source - source_low
        target_high = target - target_low

        audio = (
            source_high * gain_a.unsqueeze(1)
            + target_high * gain_b.unsqueeze(1)
            + source_low * low_gain_a.unsqueeze(1)
            + target_low * low_gain_b.unsqueeze(1)
        )

        if squeezed:
            audio = audio.squeeze(0)

        return DifferentiableRenderResult(
            format_version=CONTROL_PROTOCOL_VERSION,
            audio=audio,
            mix_position=mix_samples,
            low_end_position=low_samples,
            gain_a=gain_a,
            gain_b=gain_b,
            low_gain_a=low_gain_a,
            low_gain_b=low_gain_b,
        )

    def _lowpass(self, audio: torch.Tensor) -> torch.Tensor:
        batch_size, channels, sample_count = audio.shape
        flat = audio.reshape(batch_size * channels, 1, sample_count)
        padding = self.lowpass_kernel_size // 2
        padded = F.pad(flat, (padding, padding), mode="reflect")
        kernel = self.lowpass_kernel.to(device=audio.device, dtype=audio.dtype)
        filtered = F.conv1d(padded, kernel.view(1, 1, -1))
        return filtered.reshape(batch_size, channels, sample_count)


class DifferentiableFullBandTransitionRenderer(nn.Module):
    """Render gain, three-band EQ, low-end ownership, and vocal ducking.

    The renderer accepts the ten per-control-point outputs of the
    TCN/BiLSTM model. With vocal stems, ducking is applied to the actual vocal
    stems. Without stems, it is applied only to the mid-band as an explicit
    differentiable vocal proxy; this keeps the generic feature dataset usable
    without pretending that vocals were separated.
    """

    def __init__(
        self,
        sample_rate: int = 44_100,
        lowpass_cutoff_hz: float = 180.0,
        midpass_cutoff_hz: float = 3_500.0,
        lowpass_kernel_size: int = 255,
    ):
        super().__init__()
        self.sample_rate = int(sample_rate)
        self.lowpass_cutoff_hz = float(lowpass_cutoff_hz)
        self.midpass_cutoff_hz = float(midpass_cutoff_hz)
        self.lowpass_kernel_size = int(lowpass_kernel_size)
        self._validate_config()
        self.register_buffer(
            "lowpass_kernel",
            _windowed_sinc_lowpass(
                self.sample_rate,
                self.lowpass_cutoff_hz,
                self.lowpass_kernel_size,
            ),
        )
        self.register_buffer(
            "midpass_kernel",
            _windowed_sinc_lowpass(
                self.sample_rate,
                self.midpass_cutoff_hz,
                self.lowpass_kernel_size,
            ),
        )

    def _validate_config(self):
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")
        if not 0 < self.lowpass_cutoff_hz < self.midpass_cutoff_hz:
            raise ValueError("lowpass_cutoff_hz must be below midpass_cutoff_hz")
        if not self.midpass_cutoff_hz < self.sample_rate / 2:
            raise ValueError("midpass_cutoff_hz must be below Nyquist")
        if self.lowpass_kernel_size < 3 or self.lowpass_kernel_size % 2 == 0:
            raise ValueError("lowpass_kernel_size must be an odd integer of at least 3")

    def forward(
        self,
        source_audio: torch.Tensor,
        target_audio: torch.Tensor,
        gain_a: torch.Tensor,
        gain_b: torch.Tensor,
        eq_low_a: torch.Tensor,
        eq_low_b: torch.Tensor,
        eq_mid_a: torch.Tensor,
        eq_mid_b: torch.Tensor,
        eq_high_a: torch.Tensor,
        eq_high_b: torch.Tensor,
        low_end_ownership: torch.Tensor,
        vocal_ducking: torch.Tensor,
        *,
        source_vocal_audio: torch.Tensor | None = None,
        target_vocal_audio: torch.Tensor | None = None,
    ) -> FullBandRenderResult:
        source, squeezed = _normalise_audio(source_audio, "source_audio")
        target, target_squeezed = _normalise_audio(target_audio, "target_audio")
        if squeezed != target_squeezed:
            raise ValueError("source_audio and target_audio must have the same rank")
        if source.shape != target.shape:
            raise ValueError("source_audio and target_audio must have identical shapes")
        if source.device != target.device or source.dtype != target.dtype:
            raise ValueError("source_audio and target_audio must share device and dtype")
        if not source.is_floating_point():
            raise TypeError("Audio tensors must use a floating-point dtype")
        if not torch.isfinite(source).all() or not torch.isfinite(target).all():
            raise ValueError("Audio tensors must contain only finite values")

        source_vocal = target_vocal = None
        if (source_vocal_audio is None) != (target_vocal_audio is None):
            raise ValueError("Both vocal stems must be supplied together")
        if source_vocal_audio is not None:
            source_vocal, source_vocal_squeezed = _normalise_audio(
                source_vocal_audio,
                "source_vocal_audio",
            )
            target_vocal, target_vocal_squeezed = _normalise_audio(
                target_vocal_audio,
                "target_vocal_audio",
            )
            if len({squeezed, target_squeezed, source_vocal_squeezed, target_vocal_squeezed}) != 1:
                raise ValueError("Mix and vocal tensors must have the same rank")
            if not (source.shape == target.shape == source_vocal.shape == target_vocal.shape):
                raise ValueError("Mix and vocal tensors must have identical shapes")
            if not (
                source.device == target.device == source_vocal.device == target_vocal.device
                and source.dtype == target.dtype == source_vocal.dtype == target_vocal.dtype
            ):
                raise ValueError("Mix and vocal tensors must share device and dtype")
            if not torch.isfinite(source_vocal).all() or not torch.isfinite(target_vocal).all():
                raise ValueError("Vocal tensors must contain only finite values")

        batch_size, _, sample_count = source.shape
        if sample_count <= self.lowpass_kernel_size // 2:
            raise ValueError("Audio is too short for the configured low-pass filter")
        controls = {
            "gain_a": gain_a,
            "gain_b": gain_b,
            "eq_low_a": eq_low_a,
            "eq_low_b": eq_low_b,
            "eq_mid_a": eq_mid_a,
            "eq_mid_b": eq_mid_b,
            "eq_high_a": eq_high_a,
            "eq_high_b": eq_high_b,
            "low_end_ownership": low_end_ownership,
            "vocal_ducking": vocal_ducking,
        }
        normalised = {
            name: _normalise_control(value, batch_size, source.device, source.dtype, name)
            for name, value in controls.items()
        }
        control_shape = normalised["gain_a"].shape
        if any(value.shape != control_shape for value in normalised.values()):
            raise ValueError("All full-band controls must have identical shapes")
        samples = {
            name: _interpolate_control(value, sample_count)
            for name, value in normalised.items()
        }

        source_render = source if source_vocal is None else source - source_vocal
        target_render = target if target_vocal is None else target - target_vocal
        source_low = self._filter(source_render, self.lowpass_kernel)
        target_low = self._filter(target_render, self.lowpass_kernel)
        source_below_mid = self._filter(source_render, self.midpass_kernel)
        target_below_mid = self._filter(target_render, self.midpass_kernel)
        source_mid = source_below_mid - source_low
        target_mid = target_below_mid - target_low
        source_high = source_render - source_below_mid
        target_high = target_render - target_below_mid

        low_gain_a, low_gain_b = _equal_power_pair(samples["low_end_ownership"])
        gain_a = samples["gain_a"].clamp(0.0, 1.0)
        gain_b = samples["gain_b"].clamp(0.0, 1.0)
        vocal_duck = samples["vocal_ducking"].clamp(0.0, 1.0)

        low_source_gain = low_gain_a * samples["eq_low_a"]
        low_target_gain = low_gain_b * samples["eq_low_b"]
        mid_source_gain = gain_a * samples["eq_mid_a"]
        mid_target_gain = gain_b * samples["eq_mid_b"]
        high_source_gain = gain_a * samples["eq_high_a"]
        high_target_gain = gain_b * samples["eq_high_b"]

        if source_vocal is None:
            # No vocal stems: use the 180–3500 Hz band as a documented proxy.
            mid_source_gain = mid_source_gain * (1.0 - vocal_duck)
            mid_target_gain = mid_target_gain * (1.0 - vocal_duck)

        audio = (
            source_low * low_source_gain.unsqueeze(1)
            + target_low * low_target_gain.unsqueeze(1)
            + source_mid * mid_source_gain.unsqueeze(1)
            + target_mid * mid_target_gain.unsqueeze(1)
            + source_high * high_source_gain.unsqueeze(1)
            + target_high * high_target_gain.unsqueeze(1)
        )
        vocal_gain_a = gain_a * (1.0 - vocal_duck)
        vocal_gain_b = gain_b * (1.0 - vocal_duck)
        if source_vocal is not None:
            audio = (
                audio
                + source_vocal * vocal_gain_a.unsqueeze(1)
                + target_vocal * vocal_gain_b.unsqueeze(1)
            )
        if squeezed:
            audio = audio.squeeze(0)
        return FullBandRenderResult(
            format_version=FULL_BAND_CONTROL_PROTOCOL_VERSION,
            audio=audio,
            mix_position=samples["gain_b"],
            low_end_position=samples["low_end_ownership"],
            gain_a=gain_a,
            gain_b=gain_b,
            eq_low_a=samples["eq_low_a"],
            eq_low_b=samples["eq_low_b"],
            eq_mid_a=samples["eq_mid_a"],
            eq_mid_b=samples["eq_mid_b"],
            eq_high_a=samples["eq_high_a"],
            eq_high_b=samples["eq_high_b"],
            vocal_ducking=vocal_duck,
            vocal_gain_a=vocal_gain_a,
            vocal_gain_b=vocal_gain_b,
            low_gain_a=low_gain_a,
            low_gain_b=low_gain_b,
        )

    def _filter(self, audio: torch.Tensor, kernel: torch.Tensor) -> torch.Tensor:
        batch_size, channels, sample_count = audio.shape
        flat = audio.reshape(batch_size * channels, 1, sample_count)
        padding = self.lowpass_kernel_size // 2
        padded = F.pad(flat, (padding, padding), mode="reflect")
        filtered = F.conv1d(
            padded,
            kernel.to(device=audio.device, dtype=audio.dtype).view(1, 1, -1),
        )
        return filtered.reshape(batch_size, channels, sample_count)


class DifferentiableVocalAwareRenderer(nn.Module):
    """Render accompaniment in two bands and vocals with independent gains."""

    def __init__(
        self,
        sample_rate: int = 44_100,
        lowpass_cutoff_hz: float = 180.0,
        lowpass_kernel_size: int = 255,
    ):
        super().__init__()
        self.accompaniment_renderer = DifferentiableTwoBandRenderer(
            sample_rate=sample_rate,
            lowpass_cutoff_hz=lowpass_cutoff_hz,
            lowpass_kernel_size=lowpass_kernel_size,
        )

    @property
    def sample_rate(self):
        return self.accompaniment_renderer.sample_rate

    def forward(
        self,
        source_audio: torch.Tensor,
        target_audio: torch.Tensor,
        source_vocal_audio: torch.Tensor,
        target_vocal_audio: torch.Tensor,
        mix_position: torch.Tensor,
        low_end_position: torch.Tensor,
        vocal_position: torch.Tensor,
        vocal_duck_a: torch.Tensor,
        vocal_duck_b: torch.Tensor,
    ) -> VocalAwareRenderResult:
        source, squeezed = _normalise_audio(source_audio, "source_audio")
        target, target_squeezed = _normalise_audio(target_audio, "target_audio")
        source_vocal, source_vocal_squeezed = _normalise_audio(
            source_vocal_audio,
            "source_vocal_audio",
        )
        target_vocal, target_vocal_squeezed = _normalise_audio(
            target_vocal_audio,
            "target_vocal_audio",
        )
        if len({squeezed, target_squeezed, source_vocal_squeezed, target_vocal_squeezed}) != 1:
            raise ValueError("Mix and vocal tensors must have the same rank")
        if not (source.shape == target.shape == source_vocal.shape == target_vocal.shape):
            raise ValueError("Mix and vocal tensors must have identical shapes")
        if not (
            source.device == target.device == source_vocal.device == target_vocal.device
            and source.dtype == target.dtype == source_vocal.dtype == target_vocal.dtype
        ):
            raise ValueError("Mix and vocal tensors must share device and dtype")
        if not all(
            torch.isfinite(value).all()
            for value in (source, target, source_vocal, target_vocal)
        ):
            raise ValueError("Mix and vocal tensors must contain only finite values")

        accompaniment = self.accompaniment_renderer(
            source - source_vocal,
            target - target_vocal,
            mix_position,
            low_end_position,
        )
        batch_size, _, sample_count = source.shape
        vocal_control = _normalise_control(
            vocal_position,
            batch_size,
            source.device,
            source.dtype,
            "vocal_position",
        )
        duck_a_control = _normalise_control(
            vocal_duck_a,
            batch_size,
            source.device,
            source.dtype,
            "vocal_duck_a",
        )
        duck_b_control = _normalise_control(
            vocal_duck_b,
            batch_size,
            source.device,
            source.dtype,
            "vocal_duck_b",
        )
        if not (vocal_control.shape == duck_a_control.shape == duck_b_control.shape):
            raise ValueError("Vocal position and ducking controls must have identical shapes")
        vocal_samples = _interpolate_control(vocal_control, sample_count)
        duck_a_samples = _interpolate_control(duck_a_control, sample_count)
        duck_b_samples = _interpolate_control(duck_b_control, sample_count)
        vocal_base_a, vocal_base_b = _equal_power_pair(vocal_samples)
        vocal_gain_a = vocal_base_a * (1.0 - duck_a_samples)
        vocal_gain_b = vocal_base_b * (1.0 - duck_b_samples)
        accompaniment_audio, _ = _normalise_audio(
            accompaniment.audio,
            "accompaniment.audio",
        )
        audio = (
            accompaniment_audio
            + source_vocal * vocal_gain_a.unsqueeze(1)
            + target_vocal * vocal_gain_b.unsqueeze(1)
        )
        if squeezed:
            audio = audio.squeeze(0)
        return VocalAwareRenderResult(
            format_version=VOCAL_CONTROL_PROTOCOL_VERSION,
            audio=audio,
            mix_position=accompaniment.mix_position,
            low_end_position=accompaniment.low_end_position,
            vocal_position=vocal_samples,
            gain_a=accompaniment.gain_a,
            gain_b=accompaniment.gain_b,
            low_gain_a=accompaniment.low_gain_a,
            low_gain_b=accompaniment.low_gain_b,
            vocal_gain_a=vocal_gain_a,
            vocal_gain_b=vocal_gain_b,
            vocal_duck_a=duck_a_samples,
            vocal_duck_b=duck_b_samples,
        )


class DifferentiableTransitionObjective(nn.Module):
    """Differentiable proxy objective for the first control-learning probe."""

    def __init__(
        self,
        config: DifferentiableTransitionObjectiveConfig | None = None,
        energy_frames: int = 32,
    ):
        super().__init__()
        self.config = config or DifferentiableTransitionObjectiveConfig()
        self.energy_frames = int(energy_frames)
        if self.energy_frames < 3:
            raise ValueError("energy_frames must be at least 3")

    def forward(
        self,
        render_result: DifferentiableRenderResult,
        source_audio: torch.Tensor,
        target_audio: torch.Tensor,
        features_a: torch.Tensor | None = None,
        features_b: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        rendered, _ = _normalise_audio(render_result.audio, "render_result.audio")
        source, _ = _normalise_audio(source_audio, "source_audio")
        target, _ = _normalise_audio(target_audio, "target_audio")
        if rendered.shape != source.shape or rendered.shape != target.shape:
            raise ValueError("Rendered, source, and target audio must have identical shapes")

        rendered_db = _frame_rms_db(
            rendered,
            self.energy_frames,
            self.config.epsilon,
        )
        source_db = _frame_rms_db(source, self.energy_frames, self.config.epsilon)
        target_db = _frame_rms_db(target, self.energy_frames, self.config.epsilon)
        target_shape_db = _u_shaped_energy_target(
            source_db[:, 0],
            target_db[:, -1],
            self.energy_frames,
            self.config.valley_depth_db,
        )

        energy_shape = torch.mean(
            ((rendered_db - target_shape_db) / self.config.energy_tolerance_db) ** 2
        )
        boundary = torch.mean(
            torch.stack(
                (
                    (rendered_db[:, 0] - source_db[:, 0])
                    / self.config.boundary_tolerance_db,
                    (rendered_db[:, -1] - target_db[:, -1])
                    / self.config.boundary_tolerance_db,
                ),
                dim=-1,
            )
            ** 2
        )

        mix_control = _restore_control_points(render_result.mix_position, self.energy_frames)
        low_control = _restore_control_points(
            render_result.low_end_position,
            self.energy_frames,
        )
        mix_delta = torch.diff(mix_control, dim=-1)
        low_delta = torch.diff(low_control, dim=-1)
        uniform_delta = 1.0 / float(self.energy_frames - 1)
        control_smoothness = torch.mean(
            ((mix_delta - uniform_delta) / uniform_delta) ** 2
            + ((low_delta - uniform_delta) / uniform_delta) ** 2
        )
        mix_curvature = torch.diff(mix_delta, dim=-1)
        low_curvature = torch.diff(low_delta, dim=-1)
        control_curvature = torch.mean(
            (mix_curvature / uniform_delta) ** 2
            + (low_curvature / uniform_delta) ** 2
        )
        monotonicity = torch.mean(F.relu(-mix_delta) ** 2 + F.relu(-low_delta) ** 2)
        clipping = torch.mean(F.relu(torch.abs(rendered) - 1.0) ** 2)
        conditioned = _conditioned_objective_terms(
            mix_control,
            low_control,
            features_a,
            features_b,
        )

        total = (
            self.config.energy_shape_weight * energy_shape
            + self.config.boundary_weight * boundary
            + self.config.control_smoothness_weight * control_smoothness
            + self.config.control_curvature_weight * control_curvature
            + self.config.monotonicity_weight * monotonicity
            + self.config.clipping_weight * clipping
            + self.config.vocal_overlap_weight * conditioned["vocal_overlap"]
            + self.config.vocal_boundary_weight * conditioned["vocal_boundary"]
            + self.config.transient_artifact_weight
            * conditioned["transient_artifact"]
        )
        return {
            "loss": total,
            "energy_shape": energy_shape,
            "boundary": boundary,
            "control_smoothness": control_smoothness,
            "control_curvature": control_curvature,
            "monotonicity": monotonicity,
            "clipping": clipping,
            **conditioned,
        }


class VocalAwareTransitionObjective(DifferentiableTransitionObjective):
    """Objective v5: prevent clashes without making active vocals needlessly quiet."""

    def __init__(
        self,
        config: VocalAwareTransitionObjectiveConfig | None = None,
        energy_frames: int = 32,
    ):
        config = config or VocalAwareTransitionObjectiveConfig()
        super().__init__(config=config, energy_frames=energy_frames)
        self.config = config

    def forward(
        self,
        render_result: VocalAwareRenderResult,
        source_audio: torch.Tensor,
        target_audio: torch.Tensor,
        source_vocal_audio: torch.Tensor,
        target_vocal_audio: torch.Tensor,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        terms = super().forward(
            render_result,
            source_audio,
            target_audio,
            features_a,
            features_b,
        )
        source_features = _normalise_objective_features(
            features_a,
            _restore_control_points(render_result.vocal_gain_a, self.energy_frames),
            "features_a",
        )
        target_features = _normalise_objective_features(
            features_b,
            _restore_control_points(render_result.vocal_gain_b, self.energy_frames),
            "features_b",
        )
        source_vocal, _ = _normalise_audio(source_vocal_audio, "source_vocal_audio")
        target_vocal, _ = _normalise_audio(target_vocal_audio, "target_vocal_audio")
        if source_vocal.shape != target_vocal.shape:
            raise ValueError("Source and target vocal stems must have identical shapes")
        vocal_gain_a = _restore_control_points(
            render_result.vocal_gain_a,
            self.energy_frames,
        )
        vocal_gain_b = _restore_control_points(
            render_result.vocal_gain_b,
            self.energy_frames,
        )
        source_strength = _vocal_strength(source_features) * _channel(
            source_features,
            "vocal_valid",
        )
        target_strength = _vocal_strength(target_features) * _channel(
            target_features,
            "vocal_valid",
        )
        source_stem_strength = _normalised_stem_strength(
            source_vocal,
            self.energy_frames,
            self.config.epsilon,
        )
        target_stem_strength = _normalised_stem_strength(
            target_vocal,
            self.energy_frames,
            self.config.epsilon,
        )
        source_strength = source_strength * source_stem_strength
        target_strength = target_strength * target_stem_strength

        vocal_stem_overlap = torch.mean(
            source_strength
            * target_strength
            * (vocal_gain_a * vocal_gain_b) ** 2
        )
        source_audibility_weight = source_strength * (1.0 - 0.75 * target_strength)
        target_audibility_weight = target_strength * (1.0 - 0.75 * source_strength)
        vocal_audibility = torch.mean(
            source_audibility_weight * (1.0 - vocal_gain_a) ** 2
            + target_audibility_weight * (1.0 - vocal_gain_b) ** 2
        )

        source_mid_phrase = source_strength * (
            1.0 - _channel(source_features, "vocal_offset_probability")
        )
        target_mid_phrase = target_strength * (
            1.0 - _channel(target_features, "vocal_onset_probability")
        )
        vocal_mid_phrase_gain_change = torch.mean(
            _midpoint(source_mid_phrase) * torch.diff(vocal_gain_a, dim=-1) ** 2
            + _midpoint(target_mid_phrase) * torch.diff(vocal_gain_b, dim=-1) ** 2
        )
        total = (
            terms["loss"]
            + self.config.vocal_stem_overlap_weight * vocal_stem_overlap
            + self.config.vocal_audibility_weight * vocal_audibility
            + self.config.vocal_mid_phrase_gain_change_weight
            * vocal_mid_phrase_gain_change
        )
        return {
            **terms,
            "loss_v4": terms["loss"],
            "loss": total,
            "vocal_stem_overlap": vocal_stem_overlap,
            "vocal_audibility": vocal_audibility,
            "vocal_mid_phrase_gain_change": vocal_mid_phrase_gain_change,
        }


class OptimizableControlCurves(nn.Module):
    """Strictly monotone curves with constructively bounded increments."""

    def __init__(
        self,
        control_points: int = 32,
        increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND,
    ):
        super().__init__()
        self.control_points = int(control_points)
        if self.control_points < 3:
            raise ValueError("control_points must be at least 3")
        self.increment_logit_bound = float(increment_logit_bound)
        if (
            not math.isfinite(self.increment_logit_bound)
            or self.increment_logit_bound <= 0
        ):
            raise ValueError("increment_logit_bound must be a finite value above 0")
        initial_increment_logits = torch.zeros(self.control_points - 1)
        self.mix_increment_logits = nn.Parameter(initial_increment_logits.clone())
        self.low_end_increment_logits = nn.Parameter(initial_increment_logits.clone())

    def forward(self) -> tuple[torch.Tensor, torch.Tensor]:
        mix_position = bounded_monotone_unit_curve(
            self.mix_increment_logits,
            self.increment_logit_bound,
        )
        low_end_position = bounded_monotone_unit_curve(
            self.low_end_increment_logits,
            self.increment_logit_bound,
        )
        return mix_position, low_end_position


class OptimizableVocalControlCurves(nn.Module):
    """Directly optimizable mix, low-end, vocal, and vocal-duck controls."""

    def __init__(
        self,
        control_points: int = 32,
        increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND,
        maximum_vocal_ducking: float = 0.75,
        initial_vocal_duck_logit: float = -4.0,
    ):
        super().__init__()
        self.control_points = int(control_points)
        self.increment_logit_bound = float(increment_logit_bound)
        self.maximum_vocal_ducking = float(maximum_vocal_ducking)
        if self.control_points < 3:
            raise ValueError("control_points must be at least 3")
        if not math.isfinite(self.increment_logit_bound) or self.increment_logit_bound <= 0:
            raise ValueError("increment_logit_bound must be a finite value above 0")
        if not 0.0 <= self.maximum_vocal_ducking < 1.0:
            raise ValueError("maximum_vocal_ducking must be in [0, 1)")
        if not math.isfinite(float(initial_vocal_duck_logit)):
            raise ValueError("initial_vocal_duck_logit must be finite")
        initial_increment_logits = torch.zeros(self.control_points - 1)
        self.mix_increment_logits = nn.Parameter(initial_increment_logits.clone())
        self.low_end_increment_logits = nn.Parameter(initial_increment_logits.clone())
        self.vocal_increment_logits = nn.Parameter(initial_increment_logits.clone())
        self.vocal_duck_logits = nn.Parameter(
            torch.full((2, self.control_points), float(initial_vocal_duck_logit))
        )

    def forward(self):
        positions = tuple(
            bounded_monotone_unit_curve(logits, self.increment_logit_bound)
            for logits in (
                self.mix_increment_logits,
                self.low_end_increment_logits,
                self.vocal_increment_logits,
            )
        )
        vocal_position = positions[2]
        duck_window = 4.0 * vocal_position * (1.0 - vocal_position)
        vocal_duck = (
            self.maximum_vocal_ducking
            * torch.sigmoid(self.vocal_duck_logits)
            * duck_window.unsqueeze(0)
        )
        return (*positions, vocal_duck[0], vocal_duck[1])


@dataclass(frozen=True)
class ControlOptimizationResult:
    """Detached result of one direct control-curve optimization."""

    format_version: int
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    audio: torch.Tensor
    initial_loss: float
    final_loss: float
    loss_history: tuple[float, ...]
    increment_logit_bound: float
    maximum_control_increment: float


@dataclass(frozen=True)
class VocalControlOptimizationResult:
    """Detached result of direct Objective-v5 control optimization."""

    format_version: int
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    vocal_position: torch.Tensor
    vocal_duck_a: torch.Tensor
    vocal_duck_b: torch.Tensor
    audio: torch.Tensor
    initial_loss: float
    final_loss: float
    loss_history: tuple[float, ...]
    increment_logit_bound: float
    maximum_control_increment: float
    maximum_vocal_ducking: float


def optimize_control_curves(
    source_audio: torch.Tensor,
    target_audio: torch.Tensor,
    *,
    renderer: DifferentiableTwoBandRenderer,
    objective: DifferentiableTransitionObjective | None = None,
    control_points: int = 32,
    steps: int = 100,
    learning_rate: float = 0.05,
    increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND,
    features_a: torch.Tensor | None = None,
    features_b: torch.Tensor | None = None,
) -> ControlOptimizationResult:
    """Directly optimize two curves without a feature-to-control model."""
    if steps < 1:
        raise ValueError("steps must be at least 1")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be greater than 0")
    if source_audio.device != target_audio.device or source_audio.dtype != target_audio.dtype:
        raise ValueError("source_audio and target_audio must share device and dtype")

    objective = objective or DifferentiableTransitionObjective(energy_frames=control_points)
    curves = OptimizableControlCurves(
        control_points,
        increment_logit_bound=increment_logit_bound,
    ).to(
        device=source_audio.device,
        dtype=source_audio.dtype,
    )
    optimizer = torch.optim.Adam(curves.parameters(), lr=learning_rate)
    loss_history = []

    for _ in range(steps):
        optimizer.zero_grad()
        mix_position, low_end_position = curves()
        rendered = renderer(
            source_audio,
            target_audio,
            mix_position,
            low_end_position,
        )
        terms = objective(
            rendered,
            source_audio,
            target_audio,
            features_a,
            features_b,
        )
        terms["loss"].backward()
        optimizer.step()
        loss_history.append(float(terms["loss"].detach().cpu()))

    with torch.no_grad():
        mix_position, low_end_position = curves()
        rendered = renderer(
            source_audio,
            target_audio,
            mix_position,
            low_end_position,
        )
        final_loss = float(
            objective(
                rendered,
                source_audio,
                target_audio,
                features_a,
                features_b,
            )["loss"].detach().cpu()
        )

    return ControlOptimizationResult(
        format_version=CONTROL_PROTOCOL_VERSION,
        mix_position=mix_position.detach(),
        low_end_position=low_end_position.detach(),
        audio=rendered.audio.detach(),
        initial_loss=loss_history[0],
        final_loss=final_loss,
        loss_history=tuple(loss_history),
        increment_logit_bound=float(increment_logit_bound),
        maximum_control_increment=maximum_control_increment(
            control_points,
            increment_logit_bound,
        ),
    )


def optimize_vocal_control_curves(
    source_audio: torch.Tensor,
    target_audio: torch.Tensor,
    source_vocal_audio: torch.Tensor,
    target_vocal_audio: torch.Tensor,
    *,
    renderer: DifferentiableVocalAwareRenderer,
    objective: VocalAwareTransitionObjective | None = None,
    control_points: int = 32,
    steps: int = 100,
    learning_rate: float = 0.05,
    increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND,
    maximum_vocal_ducking: float = 0.75,
    features_a: torch.Tensor,
    features_b: torch.Tensor,
) -> VocalControlOptimizationResult:
    """Directly optimize vocal-aware controls without a prediction model."""
    if steps < 1:
        raise ValueError("steps must be at least 1")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be greater than 0")
    audio = (source_audio, target_audio, source_vocal_audio, target_vocal_audio)
    if len({(item.device, item.dtype) for item in audio}) != 1:
        raise ValueError("Mix and vocal tensors must share device and dtype")

    objective = objective or VocalAwareTransitionObjective(energy_frames=control_points)
    curves = OptimizableVocalControlCurves(
        control_points,
        increment_logit_bound=increment_logit_bound,
        maximum_vocal_ducking=maximum_vocal_ducking,
    ).to(device=source_audio.device, dtype=source_audio.dtype)
    optimizer = torch.optim.Adam(curves.parameters(), lr=learning_rate)
    loss_history = []

    for _ in range(steps):
        optimizer.zero_grad()
        controls = curves()
        rendered = renderer(*audio, *controls)
        terms = objective(rendered, *audio, features_a, features_b)
        terms["loss"].backward()
        optimizer.step()
        loss_history.append(float(terms["loss"].detach().cpu()))

    with torch.no_grad():
        controls = curves()
        rendered = renderer(*audio, *controls)
        final_loss = float(
            objective(rendered, *audio, features_a, features_b)["loss"].detach().cpu()
        )

    return VocalControlOptimizationResult(
        format_version=VOCAL_CONTROL_PROTOCOL_VERSION,
        mix_position=controls[0].detach(),
        low_end_position=controls[1].detach(),
        vocal_position=controls[2].detach(),
        vocal_duck_a=controls[3].detach(),
        vocal_duck_b=controls[4].detach(),
        audio=rendered.audio.detach(),
        initial_loss=loss_history[0],
        final_loss=final_loss,
        loss_history=tuple(loss_history),
        increment_logit_bound=float(increment_logit_bound),
        maximum_control_increment=maximum_control_increment(
            control_points,
            increment_logit_bound,
        ),
        maximum_vocal_ducking=float(maximum_vocal_ducking),
    )


def _normalise_audio(audio: torch.Tensor, name: str) -> tuple[torch.Tensor, bool]:
    if not isinstance(audio, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if audio.ndim == 2:
        return audio.unsqueeze(0), True
    if audio.ndim == 3:
        return audio, False
    raise ValueError(f"{name} must have shape (C, N) or (B, C, N)")


def _normalise_control(control, batch_size, device, dtype, name):
    if not isinstance(control, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    control = control.to(device=device, dtype=dtype)
    if control.ndim == 1:
        control = control.unsqueeze(0)
    elif control.ndim == 3 and control.shape[-1] == 1:
        control = control.squeeze(-1)
    if control.ndim != 2:
        raise ValueError(f"{name} must have shape (T,), (B, T), or (B, T, 1)")
    if control.shape[0] == 1 and batch_size > 1:
        control = control.expand(batch_size, -1)
    if control.shape[0] != batch_size:
        raise ValueError(f"{name} batch dimension does not match the audio")
    if control.shape[-1] < 2:
        raise ValueError(f"{name} needs at least two control points")
    return control.clamp(0.0, 1.0)


def _interpolate_control(control: torch.Tensor, sample_count: int) -> torch.Tensor:
    return F.interpolate(
        control.unsqueeze(1),
        size=sample_count,
        mode="linear",
        align_corners=True,
    ).squeeze(1)


def _restore_control_points(control: torch.Tensor, points: int) -> torch.Tensor:
    return F.interpolate(
        control.unsqueeze(1),
        size=points,
        mode="linear",
        align_corners=True,
    ).squeeze(1)


def _equal_power_pair(position: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    angle = position * (math.pi / 2.0)
    return torch.cos(angle), torch.sin(angle)


def maximum_control_increment(
    control_points: int,
    increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND,
) -> float:
    """Return the constructive upper bound for one normalized curve step."""
    increment_count = int(control_points) - 1
    increment_logit_bound = float(increment_logit_bound)
    if increment_count < 2:
        raise ValueError("control_points must be at least 3")
    if not math.isfinite(increment_logit_bound) or increment_logit_bound <= 0:
        raise ValueError("increment_logit_bound must be a finite value above 0")
    return 1.0 / (
        1.0
        + (increment_count - 1) * math.exp(-2.0 * increment_logit_bound)
    )


def bounded_monotone_unit_curve(
    increment_logits: torch.Tensor,
    increment_logit_bound: float,
) -> torch.Tensor:
    """Map arbitrary logits to a strictly increasing unit curve."""
    bounded_logits = float(increment_logit_bound) * torch.tanh(increment_logits)
    increments = torch.softmax(bounded_logits, dim=-1)
    zero = increment_logits.new_zeros(*increment_logits.shape[:-1], 1)
    return torch.cat((zero, torch.cumsum(increments, dim=-1)), dim=-1)


def _windowed_sinc_lowpass(sample_rate, cutoff_hz, kernel_size):
    centre = (kernel_size - 1) / 2.0
    samples = torch.arange(kernel_size, dtype=torch.float32) - centre
    normalised_cutoff = float(cutoff_hz) / float(sample_rate)
    kernel = 2.0 * normalised_cutoff * torch.sinc(
        2.0 * normalised_cutoff * samples
    )
    kernel = kernel * torch.hann_window(kernel_size, periodic=False)
    return kernel / kernel.sum()


def _frame_rms_db(audio: torch.Tensor, frames: int, epsilon: float) -> torch.Tensor:
    power = torch.mean(audio**2, dim=1, keepdim=True)
    frame_power = F.adaptive_avg_pool1d(power, frames).squeeze(1)
    rms = torch.sqrt(frame_power + epsilon**2)
    return 20.0 * torch.log10(rms.clamp_min(epsilon))


def _normalised_stem_strength(
    audio: torch.Tensor,
    frames: int,
    epsilon: float,
) -> torch.Tensor:
    power = torch.mean(audio**2, dim=1, keepdim=True)
    frame_rms = torch.sqrt(
        F.adaptive_avg_pool1d(power, frames).squeeze(1) + epsilon**2
    )
    peak_rms = torch.amax(frame_rms, dim=-1, keepdim=True)
    active = (peak_rms > 10.0 * epsilon).to(frame_rms.dtype)
    return (frame_rms / peak_rms.clamp_min(epsilon)).clamp(0.0, 1.0) * active


def _u_shaped_energy_target(
    start_db: torch.Tensor,
    end_db: torch.Tensor,
    frames: int,
    valley_depth_db: float,
) -> torch.Tensor:
    position = torch.linspace(
        0.0,
        1.0,
        frames,
        device=start_db.device,
        dtype=start_db.dtype,
    ).unsqueeze(0)
    start = start_db.unsqueeze(-1)
    end = end_db.unsqueeze(-1)
    valley = torch.minimum(start, end) - float(valley_depth_db)
    left = start + (valley - start) * (position * 2.0)
    right = valley + (end - valley) * ((position - 0.5) * 2.0)
    return torch.where(position <= 0.5, left, right)


def _conditioned_objective_terms(
    mix_control: torch.Tensor,
    low_control: torch.Tensor,
    features_a: torch.Tensor | None,
    features_b: torch.Tensor | None,
) -> dict[str, torch.Tensor]:
    """Return feature-conditioned losses, or exact zeros without conditioning."""
    zero = mix_control.sum() * 0.0
    if features_a is None and features_b is None:
        return {
            "vocal_overlap": zero,
            "vocal_boundary": zero,
            "transient_artifact": zero,
            "conditioning_valid_fraction": zero,
        }
    if features_a is None or features_b is None:
        raise ValueError("features_a and features_b must either both be set or both be None")

    source_features = _normalise_objective_features(
        features_a,
        mix_control,
        "features_a",
    )
    target_features = _normalise_objective_features(
        features_b,
        mix_control,
        "features_b",
    )

    vocal_valid = (
        _channel(source_features, "vocal_valid")
        * _channel(target_features, "vocal_valid")
    )
    source_vocal = _vocal_strength(source_features) * vocal_valid
    target_vocal = _vocal_strength(target_features) * vocal_valid
    gain_a, gain_b = _equal_power_pair(mix_control)
    vocal_overlap = torch.mean(
        source_vocal * target_vocal * (gain_a * gain_b) ** 2
    )

    uniform_delta = 1.0 / float(mix_control.shape[-1] - 1)
    handover_rate = torch.diff(mix_control, dim=-1) / uniform_delta
    source_cut_cost = source_vocal * (1.0 - _channel(source_features, "vocal_offset_probability"))
    target_entry_cost = (
        target_vocal
        * (1.0 - _channel(target_features, "vocal_onset_probability"))
        * (0.25 + 0.75 * _channel(target_features, "vocal_phrase_progress"))
    )
    vocal_boundary = torch.mean(
        handover_rate
        * 0.5
        * (
            _midpoint(source_cut_cost)
            + _midpoint(target_entry_cost)
        )
    )

    audio_valid = (
        _channel(source_features, "audio_valid")
        * _channel(target_features, "audio_valid")
    )
    source_transient = torch.maximum(
        _channel(source_features, "spectral_flux"),
        _channel(source_features, "onset_strength"),
    )
    target_transient = torch.maximum(
        _channel(target_features, "spectral_flux"),
        _channel(target_features, "onset_strength"),
    )
    transient_importance = _midpoint(
        torch.maximum(source_transient, target_transient) * audio_valid
    )
    low_handover_rate = torch.diff(low_control, dim=-1) / uniform_delta
    transient_artifact = torch.mean(
        transient_importance
        * (handover_rate + 0.5 * low_handover_rate)
    )

    valid_fraction = torch.mean(vocal_valid)
    return {
        "vocal_overlap": vocal_overlap,
        "vocal_boundary": vocal_boundary,
        "transient_artifact": transient_artifact,
        "conditioning_valid_fraction": valid_fraction,
    }


def _normalise_objective_features(
    features: torch.Tensor,
    control: torch.Tensor,
    name: str,
) -> torch.Tensor:
    if not isinstance(features, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    features = features.to(device=control.device, dtype=control.dtype)
    if features.ndim == 2:
        features = features.unsqueeze(0)
    if features.ndim != 3:
        raise ValueError(f"{name} must have shape (T, F) or (B, T, F)")
    if features.shape[0] == 1 and control.shape[0] > 1:
        features = features.expand(control.shape[0], -1, -1)
    if features.shape[:2] != control.shape:
        raise ValueError(
            f"{name} batch/time dimensions must match the restored control points"
        )
    required_channels = max(
        feature_index(name)
        for name in (
            "audio_valid",
            "spectral_flux",
            "onset_strength",
            "vocal_activity",
            "vocal_prominence",
            "vocal_onset_probability",
            "vocal_offset_probability",
            "vocal_phrase_progress",
            "vocal_confidence",
            "vocal_valid",
        )
    ) + 1
    if features.shape[-1] < required_channels:
        raise ValueError(f"{name} has fewer than {required_channels} feature channels")
    if not torch.isfinite(features).all():
        raise ValueError(f"{name} must contain only finite values")
    return features


def _channel(features: torch.Tensor, name: str) -> torch.Tensor:
    return features[..., feature_index(name)].clamp(0.0, 1.0)


def _vocal_strength(features: torch.Tensor) -> torch.Tensor:
    confidence_weight = 0.5 + 0.5 * _channel(features, "vocal_confidence")
    return (
        _channel(features, "vocal_activity")
        * _channel(features, "vocal_prominence")
        * confidence_weight
    )


def _midpoint(values: torch.Tensor) -> torch.Tensor:
    return 0.5 * (values[..., :-1] + values[..., 1:])
