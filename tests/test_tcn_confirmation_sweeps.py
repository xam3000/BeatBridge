"""Exercise confirmation YAMLs through the CLI without training or W&B access."""
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.ml import __main__ as cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("candidate", ["vlfwfn7a", "fxhhidgi"])
def test_confirmation_grid_runs_full_budget_and_saves_locally(candidate, monkeypatch, tmp_path):
    spec = yaml.safe_load((ROOT / f"config/wandb/confirm_tcn_bilstm_{candidate}.yaml").read_text())
    assert spec["method"] == "grid"
    assert "early_terminate" not in spec
    params = spec["parameters"]
    varying = {name for name, definition in params.items() if "values" in definition}
    assert varying == {"seed"}
    assert params["seed"]["values"] == [20260930, 20260931, 20260932, 20260933, 20260934]
    command = spec["command"]
    args = command[command.index("sweep-tcn-bilstm"):]
    args[2] = str(tmp_path / candidate)
    monkeypatch.setenv("WANDB_SWEEP_ID", "confirmation")
    calls = []

    def fake_train(dataset, output, **kwargs):
        calls.append((dataset, output, kwargs))
        return SimpleNamespace(output_directory=output, status="completed", last_epoch=150,
                               best_epoch=77, best_validation_loss=.26)

    monkeypatch.setattr(cli, "run_tcn_bilstm_transition_control_training", fake_train)
    for seed in params["seed"]["values"]:
        selected = {name: definition["value"] for name, definition in params.items() if name != "seed"}
        selected["seed"] = seed
        monkeypatch.setenv("WANDB_RUN_ID", f"seed{seed}")
        monkeypatch.setattr(cli, "load_sweep_parameters", lambda: selected)
        monkeypatch.setattr("sys.argv", ["wandb_sweep.py", *args])
        assert cli.main() == 0
        dataset, output, kw = calls[-1]
        assert dataset == "output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805"
        assert output == tmp_path / candidate / "confirmation" / f"seed{seed}"
        assert kw["config"].seed == seed
        assert kw["config"].max_epochs == 150
        assert kw["config"].patience > kw["config"].max_epochs
        assert kw["config"].min_delta == 0
        assert kw["save_checkpoints"] is True
        assert kw["wandb_config"].log_checkpoints is False
        assert kw["resume"] is False
    assert len({call[1] for call in calls}) == 5


def test_existing_tcn_sweeps_keep_checkpoint_default_disabled():
    args = cli.build_argument_parser().parse_args(["sweep-tcn-bilstm", "dataset", "output"])
    assert args.save_checkpoints is False
