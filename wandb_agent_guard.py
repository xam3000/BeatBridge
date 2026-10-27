"""Run a W&B agent while guarding teardown from Windows NTSTATUS codes.

Some completed sweep subprocesses can exit with a Windows native status code
outside the signed 32-bit range accepted by W&B's teardown protobuf. This
launcher lets W&B continue only when local training and W&B upload records
prove that the affected trial completed successfully.
"""

from __future__ import annotations

import functools
import json
import math
import sys
from pathlib import Path
from typing import Any


_INT32_MIN = -(2**31)
_INT32_MAX = 2**31 - 1
_SWEEP_COMMANDS = {"sweep-tcn-bilstm", "sweep-variable-tcn-bilstm"}


def _agent_trial_paths(agent_process: Any) -> tuple[Path, str, str] | None:
    env = getattr(agent_process, "_beatbridge_sweep_env", {})
    command = getattr(agent_process, "_beatbridge_sweep_command", ())
    sweep_id = env.get("WANDB_SWEEP_ID")
    run_id = env.get("WANDB_RUN_ID")
    if not sweep_id or not run_id:
        return None

    for index, token in enumerate(command):
        if token not in _SWEEP_COMMANDS or index + 2 >= len(command):
            continue
        output_root = Path(command[index + 2])
        if not output_root.is_absolute():
            output_root = Path.cwd() / output_root
        return output_root.resolve() / sweep_id / run_id, sweep_id, run_id
    return None


def _finite_loss(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        loss = float(value)
    except (OverflowError, ValueError):
        return None
    return loss if math.isfinite(loss) else None


def _upload_was_acknowledged(debug_log: Path) -> bool:
    try:
        lines = debug_log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False

    final_completion_sent = False
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        if (
            record.get("msg") == "filestream: sending request"
            and record.get("complete") is True
            and record.get("exit_code") == 0
        ):
            final_completion_sent = True
        elif (
            final_completion_sent
            and record.get("msg") == "filestream: request sent"
            and record.get("status") == "200 OK"
        ):
            return True
    return False


def _trial_is_proven_complete(agent_process: Any) -> bool:
    trial_info = _agent_trial_paths(agent_process)
    if trial_info is None:
        return False
    trial_dir, _sweep_id, run_id = trial_info

    try:
        manifest = json.loads((trial_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(manifest, dict):
        return False
    manifest_loss = _finite_loss(manifest.get("best_validation_loss"))
    if manifest.get("status") != "completed" or manifest_loss is None:
        return False

    summary_files = (trial_dir / "wandb" / "wandb").glob(
        f"run-*-{run_id}/files/wandb-summary.json"
    )
    for summary_path in summary_files:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(summary, dict):
            continue
        summary_loss = _finite_loss(summary.get("best_validation_loss"))
        if (
            summary.get("status") == "completed"
            and summary_loss is not None
            and math.isclose(
                manifest_loss, summary_loss, rel_tol=0.0, abs_tol=1e-12
            )
            and _upload_was_acknowledged(
                summary_path.parent.parent / "logs" / "debug-internal.log"
            )
        ):
            return True
    return False


def _install_agent_guard() -> None:
    from wandb import wandb_agent

    agent_process_class = wandb_agent.AgentProcess
    original_init = agent_process_class.__init__
    original_poll = agent_process_class.poll

    @functools.wraps(original_init)
    def capture_sweep_context(self: Any, *args: Any, **kwargs: Any) -> Any:
        env = kwargs.get("env", args[0] if args else None)
        command = kwargs.get("command", args[1] if len(args) > 1 else None)
        self._beatbridge_sweep_env = dict(env) if isinstance(env, dict) else {}
        self._beatbridge_sweep_command = tuple(command or ())
        return original_init(self, *args, **kwargs)

    @functools.wraps(original_poll)
    def guard_out_of_range_exit_code(self: Any) -> Any:
        exit_code = original_poll(self)
        if (
            exit_code is None
            or isinstance(exit_code, bool)
            or not isinstance(exit_code, int)
            or _INT32_MIN <= exit_code <= _INT32_MAX
        ):
            return exit_code

        rendered_code = f"{exit_code} (0x{exit_code & 0xFFFFFFFF:08X})"
        try:
            completion_proven = _trial_is_proven_complete(self)
        except Exception as exc:
            print(
                "[wandb_agent_guard] Could not verify trial completion "
                f"({type(exc).__name__}); treating the child as failed.",
                file=sys.stderr,
                flush=True,
            )
            completion_proven = False

        if completion_proven:
            print(
                "[wandb_agent_guard] Trial manifest, W&B summary, and final upload "
                f"acknowledgement confirm completion despite child exit {rendered_code}; "
                "reporting success to the W&B agent.",
                file=sys.stderr,
                flush=True,
            )
            return 0

        print(
            "[wandb_agent_guard] Child exit "
            f"{rendered_code} is outside W&B's protobuf range and the trial's "
            "completion could not be proven; reporting failure to the W&B agent "
            "to avoid a teardown ValueError.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    agent_process_class.__init__ = capture_sweep_context
    agent_process_class.poll = guard_out_of_range_exit_code


def main() -> None:
    _install_agent_guard()
    from wandb.cli.cli import cli

    cli()


if __name__ == "__main__":
    main()
