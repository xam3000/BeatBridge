"""Short CPU development check of the five fresh controllers and legacy replay."""

import argparse
from dataclasses import replace
import json
from pathlib import Path

import torch

from src.evaluation.comparison import new_output, raw_result, write_json
from src.evaluation.comparison_native import FAMILIES, MODEL_RUNS, RUNS, native_setup
from src.ml import VariableTimeSharedMLP
from src.ml.control_initialization import EQUAL_POWER
from src.ml.data import collate_feature_control_examples
from src.ml.training import full_band_self_supervised_batch_loss, self_supervised_batch_loss, vocal_self_supervised_batch_loss
from src.ml.variable_data import collate_variable_feature_examples
from src.ml.variable_training import variable_vocal_self_supervised_batch_loss


def probe(evaluator, model, item):
    """Measure E0 through the application adapter and backpropagate the training loss."""
    profile = evaluator.config.profile
    functions = {"R1": self_supervised_batch_loss, "R2": vocal_self_supervised_batch_loss,
                 "R3": full_band_self_supervised_batch_loss, "R4": variable_vocal_self_supervised_batch_loss}
    collate = collate_variable_feature_examples if profile == "R4" else collate_feature_control_examples
    batch = collate([dict(item, waveform_cache_hit=True)])
    model.eval()
    with torch.no_grad():
        equal = evaluator.render(item, evaluator.equal_power())
        initial = evaluator.render(item, evaluator.learned(model, item))
    torch.testing.assert_close(initial.audio, equal.audio, atol=1e-6, rtol=0)
    for gain_pair in ("gain", "low_gain", "vocal_gain"):
        if not hasattr(initial, gain_pair + "_a"):
            continue
        gain_a = getattr(initial, gain_pair + "_a")
        gain_b = getattr(initial, gain_pair + "_b")
        torch.testing.assert_close(gain_a, getattr(equal, gain_pair + "_a"), atol=3e-7, rtol=0)
        torch.testing.assert_close(gain_b, getattr(equal, gain_pair + "_b"), atol=3e-7, rtol=0)
        torch.testing.assert_close(gain_a.square() + gain_b.square(), torch.ones_like(gain_a), atol=3e-7, rtol=0)
        for gain, endpoints in ((gain_a, [1., 0.]), (gain_b, [0., 1.])):
            observed = gain[..., [0, -1]]
            torch.testing.assert_close(observed, gain.new_tensor(endpoints).expand_as(observed), atol=1e-7, rtol=0)
    result = functions[profile](model, batch, renderer=evaluator.renderer, objective=evaluator.objective)
    reference = evaluator.terms(item, equal)
    for key in reference:
        torch.testing.assert_close(result.terms[key], reference[key], rtol=2e-6, atol=1e-6)
    controls = result.controls
    for name in ("mix_position", "low_end_position", "vocal_position"):
        if hasattr(controls, name):
            curve = getattr(controls, name)[0]
            torch.testing.assert_close(curve, torch.linspace(0, 1, len(curve)), rtol=0, atol=1.5e-7)
    if evaluator.config.vocal:
        assert not torch.count_nonzero(controls.vocal_duck_a) and not torch.count_nonzero(controls.vocal_duck_b)
    if profile == "R3":
        assert torch.all(controls.controls[..., 2:8] == 1) and torch.all(controls.vocal_ducking == 0)
    loss = result.terms["loss"]
    loss.backward()
    gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), float("inf"), error_if_nonfinite=True)
    if gradient_norm <= 0:
        raise ValueError("Training loss has no effective gradient at E0")
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    optimizer.step()
    updated = evaluator.render(item, evaluator.learned(model, item))
    audio_delta = float((updated.audio - initial.audio).abs().max())
    if not 0 < audio_delta < float("inf"):
        raise ValueError("Gradient step did not produce a finite change in rendered audio")
    return {
        "controller": type(model).__name__, "control_initialization": model.config.control_initialization,
        "example_id": item["example_id"], "split": item["split"], "bars": evaluator.config.bars,
        "e0_max_abs_audio_error": float((initial.audio - equal.audio).abs().max()),
        "e0_proxy": float(loss.detach()), "gradient_l2": float(gradient_norm),
        "sgd_lr": 0.01, "step1_max_abs_audio_change": audio_delta,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p04-reference", type=Path, help="verify the archived validation M rows")
    args = parser.parse_args()
    torch.set_num_threads(2)
    with new_output(args.output) as stage:
        starts, replay = [], []
        for profile, family in FAMILIES.items():
            evaluator, legacy, splits, protocol = native_setup(profile, 4, RUNS / MODEL_RUNS[family], None, None, 1)
            val = splits["validation"][0]
            _, row = raw_result(evaluator, val, "M", evaluator.learned(legacy, val))
            if args.p04_reference:
                rows = json.loads((args.p04_reference / profile / "results.json").read_bytes())
                old = next(r for r in rows if r["condition"] == "M" and r["example_id"] == val["example_id"])
                for key in ("raw_audio_sha256", "controls", "proxy_raw"):
                    if old[key] != row[key]:
                        raise ValueError(f"Legacy {profile} replay differs in {key}")
            replay.append({"profile": profile, "checkpoint_sha256": protocol["checkpoint_sha256"],
                           "example_id": val["example_id"], "raw_audio_sha256": row["raw_audio_sha256"]})
            torch.manual_seed(protocol["seed"])
            fresh = type(legacy)(replace(legacy.config, control_initialization=EQUAL_POWER))
            train = splits["train"][0]
            starts.append(dict(probe(evaluator, fresh, train), seed=protocol["seed"], profile=profile))
            if profile == "R4":
                torch.manual_seed(protocol["seed"])
                starts.append(dict(probe(evaluator, VariableTimeSharedMLP(), train), seed=protocol["seed"], profile=profile))
        write_json(stage / "probe.json", {"format_version": 1, "torch": str(torch.__version__),
                                         "p04_reference": str(args.p04_reference) if args.p04_reference else None,
                                         "starts": starts, "legacy_replay": replay})
    print(args.output / "probe.json")


if __name__ == "__main__":
    main()
