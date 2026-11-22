"""Shared renderer, objective and paired controls for P06 and P11."""

from collections import Counter
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager

import torch
from torch import nn

from src.control.differentiable import (
    DifferentiableFullBandTransitionRenderer, DifferentiableTransitionObjective,
    DifferentiableTransitionObjectiveConfig, DifferentiableTwoBandRenderer,
    DifferentiableVocalAwareRenderer, VocalAwareTransitionObjective,
    VocalAwareTransitionObjectiveConfig,
    bounded_monotone_unit_curve,
)
from src.control.variable_differentiable import VariableVocalAwareTransitionObjective
from src.ml.control_initialization import full_band_arguments
from src.ml.model import TRANSITION_CONTROL_OUTPUT_NAMES


POSITION_NAMES = ("mix_position", "low_end_position", "vocal_position")
VOCAL_NAMES = (*POSITION_NAMES, "vocal_duck_a", "vocal_duck_b")
FULL_NAMES = TRANSITION_CONTROL_OUTPUT_NAMES


@dataclass(frozen=True)
class Comparison:
    profile: str
    bars: int = 4
    sample_rate: int = 11025
    taps: int = 127
    low_hz: float = 180.
    mid_hz: float = 3500.
    increment_bound: float = 0.6
    maximum_duck: float = 0.75

    def __post_init__(self):
        if self.profile not in {"R1", "R2", "R3", "R4", "study"}:
            raise ValueError(f"Unknown comparison profile {self.profile}")
        if self.bars not in ((2, 4, 6, 8) if self.profile == "R4" else (4,)):
            raise ValueError("Unsupported transition length for this profile")
        rate, taps = (44100, 511) if self.profile == "study" else (11025, 127)
        if (self.sample_rate, self.taps, self.low_hz, self.mid_hz) != (rate, taps, 180., 3500.):
            raise ValueError("Sample rate or FIR differs from the comparison protocol")

    @classmethod
    def study(cls):
        return cls("study", sample_rate=44100, taps=511)

    @property
    def vocal(self):
        return self.profile in {"R2", "R4"}

    @property
    def points(self):
        return self.bars * 8


class FreeCurves(nn.Module):
    """Shared F/D parameter space. Project bounded EQ/duck parameters after Adam."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        count = 3 if config.vocal else 2
        self.increments = nn.Parameter(torch.zeros(count, config.points - 1))
        if config.vocal or config.profile == "R3":
            channels = 2 if config.vocal else 7
            initial = torch.zeros(channels, config.points)
            if config.profile == "R3":
                initial[:6] = 1.
            self.auxiliary = nn.Parameter(initial)

    def forward(self):
        positions = bounded_monotone_unit_curve(self.increments, self.config.increment_bound)
        controls = dict(zip(POSITION_NAMES, positions))
        if self.config.vocal:
            window = 4 * positions[2] * (1 - positions[2])
            controls.update(zip(VOCAL_NAMES[3:], self.config.maximum_duck * window * self.auxiliary))
        elif self.config.profile == "R3":
            controls.update(zip((*FULL_NAMES[2:8], "vocal_ducking"), self.auxiliary))
        return controls

    @torch.no_grad()
    def project(self):
        if hasattr(self, "auxiliary"):
            self.auxiliary.clamp_(0, 1)


class Evaluator:
    def __init__(self, config, objective_weights=None):
        self.config = config
        options = dict(sample_rate=config.sample_rate, lowpass_cutoff_hz=config.low_hz,
                       lowpass_kernel_size=config.taps)
        if config.vocal:
            self.renderer = DifferentiableVocalAwareRenderer(**options)
            weights = VocalAwareTransitionObjectiveConfig(**(objective_weights or {}))
            if config.profile == "R4":
                self.objective = VariableVocalAwareTransitionObjective(weights)
            else:
                self.objective = VocalAwareTransitionObjective(weights, config.points)
        else:
            self.renderer = (DifferentiableFullBandTransitionRenderer(
                **options, midpass_cutoff_hz=config.mid_hz,
            ) if config.profile == "R3" else DifferentiableTwoBandRenderer(**options))
            weights = DifferentiableTransitionObjectiveConfig(**(objective_weights or {}))
            self.objective = DifferentiableTransitionObjective(weights, config.points)

    def protocol(self):
        cfg = self.config
        study = cfg.profile == "study"
        return {
            "format_version": 1, "profile": cfg.profile, "renderer": type(self.renderer).__name__,
            "sample_rate": cfg.sample_rate, "channels": 2, "dtype": "float32",
            "fir_taps": cfg.taps, "low_hz": cfg.low_hz,
            "mid_hz": cfg.mid_hz if cfg.profile == "R3" else None,
            "bars": cfg.bars, "beats": cfg.bars * 4, "control_points": cfg.points,
            "increment_logit_bound": cfg.increment_bound,
            "maximum_vocal_ducking": cfg.maximum_duck if cfg.vocal else None,
            "objective": type(self.objective).__name__, "objective_version": 5 if cfg.vocal else 4,
            "objective_weights": asdict(self.objective.config), "energy_frames": cfg.points,
            "context_seconds": [5, 8] if study else [0, 0],
            "gain": "integrated_LUFS_then_pair_true_peak" if study else "unity",
            "optimizer": "Adam", "learning_rate": 0.06,
            "device": "cpu", "torch_version": str(torch.__version__), "threads": torch.get_num_threads(),
        }

    def equal_power(self):
        with torch.no_grad():
            return FreeCurves(self.config)()

    @torch.no_grad()
    def learned(self, model, item):
        options = {}
        if self.config.profile == "R4":
            options.update(transition_length_bars=self.config.bars, length_condition=item["length_condition"])
        result = model(item["features_a"], item["features_b"], item["global_features"], **options)
        if self.config.profile == "R3":
            return result.render_controls()
        names = VOCAL_NAMES if self.config.vocal else POSITION_NAMES[:2]
        return {name: getattr(result, name) for name in names}

    def _inputs(self, item):
        names = ["source_audio", "target_audio"]
        if self.config.vocal:
            names.extend(("source_vocal_audio", "target_vocal_audio"))
        return [item[name] for name in names]

    def render(self, item, controls):
        audio = self._inputs(item)
        if (item["sample_rate"], item["transition_length_bars"]) != (self.config.sample_rate, self.config.bars):
            raise ValueError("Input rate or bridge length differs from the comparison protocol")
        if any(x.shape != audio[0].shape or x.ndim != 2 or x.shape[0] != 2
               or x.dtype != torch.float32 for x in audio):
            raise ValueError("Expected aligned stereo float32 bridge waveforms")
        if any(value.shape != (self.config.points,) for value in controls.values()):
            raise ValueError("Control geometry differs from the comparison protocol")
        if item["features_a"].shape != (self.config.points, 54) or item["features_b"].shape != item["features_a"].shape:
            raise ValueError("Feature geometry differs from the comparison protocol")
        if self.config.profile == "R3":
            args = full_band_arguments(controls, FULL_NAMES, audio[0].shape[-1])
        else:
            names = VOCAL_NAMES if self.config.vocal else POSITION_NAMES[:2]
            args = [controls[k] for k in names]
        return self.renderer(*audio, *args)

    def terms(self, item, rendered, gain=1., playback_audio=None):
        references = self._inputs(item)
        if playback_audio is not None:
            rendered = replace(rendered, audio=playback_audio)
            references = [audio * gain for audio in references]
        options = {"transition_length_bars": self.config.bars} if self.config.profile == "R4" else {}
        return self.objective(rendered, *references, item["features_a"], item["features_b"], **options)

    def optimize(self, items, pairs, *, steps, fixed):
        """Each training pair contributes equally, then each cue within its pair."""
        if steps < 1 or len(items) != len(pairs) or not pairs or (not fixed and len(items) != 1):
            raise ValueError("Invalid optimization budget or population")
        counts = Counter(pairs)
        curves = FreeCurves(self.config)
        optimizer = torch.optim.Adam(curves.parameters(), lr=0.06)
        for step in range(1, steps + 1):
            optimizer.zero_grad()
            for index, pair in enumerate(pairs):
                item = items[index]
                if fixed and item["split"] != "train":
                    raise ValueError("Fixed curves can only be fitted on train")
                if pair != item["pair"]:
                    raise ValueError("Optimization weight assigned to a different track pair")
                loss = self.terms(item, self.render(item, curves()))["loss"]
                if not torch.isfinite(loss):
                    raise ValueError(f"Nonfinite loss at step {step}, example {item['example_id']}")
                (loss / (len(counts) * counts[pair])).backward()
            if any(not torch.isfinite(p.grad).all() for p in curves.parameters()):
                raise ValueError(f"Nonfinite gradient at step {step}")
            optimizer.step()
            curves.project()
        with torch.no_grad():
            return curves()


def raw_result(evaluator, item, condition, controls):
    with torch.no_grad():
        rendered = evaluator.render(item, controls)
        if condition == "E":
            replay = evaluator.render(item, evaluator.equal_power())
            if not torch.equal(rendered.audio.view(torch.int32), replay.audio.view(torch.int32)):
                raise ValueError(f"Equal Power replay differs for {item['example_id']}")
        terms = {k: float(v) for k, v in evaluator.terms(item, rendered).items()}
    return rendered, result_row(evaluator, item, condition, rendered.audio, controls, terms)


def result_row(evaluator, item, condition, audio, controls, terms):
    return {
        "profile": evaluator.config.profile, "split": item["split"],
        "example_id": item["example_id"], "candidate_id": item["candidate_id"],
        "pair": item["pair"], "geometry": item["geometry"], "condition": condition,
        "selector": None, "bridge_samples": audio.shape[-1],
        "controls": {k: v.detach().tolist() for k, v in controls.items()},
        "raw_audio_sha256": hashlib.sha256(audio.detach().contiguous().numpy().tobytes()).hexdigest(),
        "proxy_raw": terms, "proxy_playback": None, "loudness": None, "wav": None, "wav_sha256": None,
    }


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                          encoding="utf-8")


def save_comparison(directory, protocol, rows):
    path = directory / "protocol.json"
    write_json(path, protocol)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(directory / "results.json", [dict(row, protocol_sha256=digest) for row in rows])


@contextmanager
def new_output(directory):
    """Publish a verified complete comparison in one rename."""
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=directory.parent) as scratch:
        stage = Path(scratch) / "run"
        stage.mkdir()
        yield stage
        stage.rename(directory)
