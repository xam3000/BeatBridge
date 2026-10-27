# Weights & Biases

BeatBridge logs the self-supervised training runs from the MLP, TCN/BiLSTM
and vocal runners through the optional W&B adapter in `src/ml/wandb_logging.py`.
The local `history.json` and `manifest.json` remain authoritative; W&B is an
additional dashboard and artifact sink.

Artifact staging is redirected into the local run output directory so managed
Windows permissions on the global W&B cache do not prevent checkpoint logging.

Each local output directory receives a stable, separate W&B run ID. Re-running
with `--resume` in the same output directory continues that W&B run; a new
output directory creates a new W&B run.

## Installation and login

The pinned dependency is included in `requirements.txt`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\wandb.exe login
```

The login is only needed for online synchronization. Offline runs do not need
an account or network access.

## Training modes

W&B is disabled by default so existing tests and local runs stay network-free.
Enable it explicitly on any training command:

```powershell
# Live dashboard synchronization
.venv\Scripts\python.exe -m src.ml train DATASET_DIR OUTPUT_DIR `
  --wandb-mode online --wandb-project beatbridge

# Local logging for later synchronization
.venv\Scripts\python.exe -m src.ml train DATASET_DIR OUTPUT_DIR `
  --wandb-mode offline --wandb-project beatbridge

# Explicitly disable logging
.venv\Scripts\python.exe -m src.ml train DATASET_DIR OUTPUT_DIR `
  --wandb-mode disabled
```

The same options are available for `train-vocal` and `train-tcn-bilstm`.
`--wandb-log-checkpoints` is enabled by default when W&B is active; use
`--no-wandb-log-checkpoints` to log metrics only. At run completion, the best
and latest checkpoints plus `history.json` and `manifest.json` are stored as a
model artifact. Audio files are not uploaded.

The CLI options can also be configured with `WANDB_MODE`, `WANDB_PROJECT`,
`WANDB_ENTITY`, `WANDB_GROUP` and `WANDB_LOG_CHECKPOINTS`. For offline runs,
W&B prints the exact local run directory; synchronize it later with:

```powershell
.venv\Scripts\wandb.exe sync PATH_TO_OFFLINE_RUN
```

## Vocal MLP hyperparameter sweep

The ready-to-run Bayesian sweep is `config/wandb/sweep_vocal_mlp.yaml`. It
uses the current vocal-aware MLP and the existing Feature Protocol 1
train/validation dataset. It tunes the optimizer (Adam/AdamW), learning rate,
weight decay, Adam betas and epsilon, batch size, early stopping, gradient
clipping, hidden dimensions, dropout, vocal-ducking bounds, and the
learning-rate scheduler. The sweep uses validation-loss-driven
`ReduceLROnPlateau` and tunes its factor, patience, threshold, cooldown, and
minimum learning rate. `train-vocal` also supports `CosineAnnealingLR` for
individual runs.

Create a sweep and start an agent from the repository root:

```powershell
.venv\Scripts\wandb.exe sweep --project beatbridge config\wandb\sweep_vocal_mlp.yaml
.venv\Scripts\wandb.exe agent --count 30 ENTITY/beatbridge/SWEEP_ID
```

Replace `ENTITY/beatbridge/SWEEP_ID` with the identifier printed by the first
command. The YAML points at
`output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805`;
change that command argument if using a different compatible Feature Protocol
1 dataset. The agent uses `device=auto`.

Each trial is stored locally at
`output/training_runs/wandb_sweeps/vocal_time_shared_mlp_v2/<SWEEP_ID>/<RUN_ID>`.
Trials log `best_validation_loss` for Bayesian minimization and record their
learning rate by epoch. Model checkpoints are not uploaded by default; add
`--wandb-log-checkpoints` to the `sweep-vocal` command in the YAML if checkpoint
artifacts are wanted. The dataset, renderer, sample rate, and objective remain
fixed so the validation losses stay comparable. The config sets `max_epochs`
to 100 and relies on per-trial early stopping.

## TCN/BiLSTM hyperparameter sweeps

The fixed four-bar model and variable-length model have separate sweep
definitions and CLI trial runners:

- `config/wandb/sweep_tcn_bilstm.yaml` runs
  `tcn_bilstm_transition_control_v1` on the Feature Protocol 1 dataset. It
  searches learning rate, weight decay, batch size, gradient
  clipping, TCN kernel size/dilation, and dropout. W&B Hyperband handles early
  termination from the per-epoch `best_validation_loss` metric. Its first
  pruning bracket is now `min_iter: 50`, so runs get at least about 50 logged
  epochs before pruning is considered; W&B checks periodically, so the stop can
  arrive after that point. The encoder and controller widths,
  control transform, renderer, objective, dataset, and sample rate stay fixed.
  Every trial ramps its sampled base learning rate linearly from 10% to 100%
  over its first 5 epochs, then uses `ReduceLROnPlateau` on validation loss
  (factor 0.5, patience 10, absolute threshold 0.0001, minimum 5% of base LR).
  The active learning rate is logged each epoch as `learning_rate`, with epoch
  configured as its W&B chart axis. The waveform cache can be built by the
  runner if entries are missing.
- `config/wandb/sweep_variable_tcn_bilstm.yaml` runs
  `variable_tcn_bilstm_transition_control_v1` on the 2/4/6/8-bar Feature
  Protocol 2 dataset. It searches the same optimization/training settings and
  TCN settings, plus the vocal-ducking bound and its initial logit. W&B
  Hyperband uses the same 50-epoch minimum before pruning. For both sweeps, the
  runner-local patience is set beyond the 150-epoch limit and `min_delta` is
  zero so every validation improvement updates the checkpoint. The dataset,
  complete train/validation waveform-cache index, four transition lengths,
  equal-length weighting, renderer, objective, and sample rate stay fixed.
  This runner requires the cache to be materialized before starting agents.
  Its trials use the same 5-epoch LR ramp and validation-loss-driven plateau
  schedule as the fixed-length model. `learning_rate` is available in W&B's
  automatically generated charts against `epoch`.

Create and launch each sweep independently from the repository root:

Start agents from the repository root so the relative paths resolve. Use
`wandb_agent_guard.py` as the agent entry point; it invokes the W&B CLI from
`.venv` and protects teardown from Windows native exit codes that exceed the
integer range accepted by W&B's protobuf. For an out-of-range child code, it
reports success only when that same trial has a completed local manifest, a
completed W&B summary with the same best validation loss, and a final W&B
upload acknowledged with HTTP 200. Otherwise it reports a valid failure code,
so the agent does not crash with a teardown `ValueError`. The guard does not
identify or prevent the underlying native Python process abort.

```powershell
.venv\Scripts\wandb.exe sweep --project beatbridge config\wandb\sweep_tcn_bilstm.yaml
.venv\Scripts\python.exe wandb_agent_guard.py agent --count 30 ENTITY/beatbridge/SWEEP_ID

.venv\Scripts\wandb.exe sweep --project beatbridge config\wandb\sweep_variable_tcn_bilstm.yaml
.venv\Scripts\python.exe wandb_agent_guard.py agent --count 30 ENTITY/beatbridge/SWEEP_ID
```

Replace each `SWEEP_ID` with the ID printed by its corresponding `sweep`
command. The fixed-length YAML targets Dataset-v1 ID
`52bc9d1cebfd1b82d2ea`. The variable-length YAML targets Dataset-v2 ID
`2a124caf5625b4c8f683` and the verified cache root
`output/ml_cache/variable_bridge_waveform_v2/prive_scantraxx_extension_run02_wandb_full_20260926`.
Adjust those paths if the local immutable dataset or cache root has moved.

Each trial writes to a separate local directory under
`output/training_runs/wandb_sweeps/<model>/<SWEEP_ID>/<RUN_ID>`. The sweep
commands explicitly disable W&B model-artifact uploads and local model
checkpoints. Trial directories retain the metric history and manifests (plus
the variable runner's I/O audit), but have no `best.pt` or `latest.pt` files.
Use the winning W&B configuration to train a final model separately with
checkpoint saving enabled. Both searches minimize `best_validation_loss` on
their own validation split. The two model families use different datasets,
feature protocols, renderers, and objectives; do not compare or pool their
absolute validation-loss values. The first fixed TCN trial (`kux6f586` /
`6eqzbl9s`) completed 100 epochs with best validation loss 0.3191189. Its
Python 3.14.2 process then emitted Windows exit code `0xC0000409`; the W&B
agent hit a `ValueError` while handling that code during teardown. The
`wandb_agent_guard.py` launcher lets the agent continue when local files prove
the run completed and uploaded successfully. Resume an existing sweep with its
existing ID; after one completed run out of a planned 30, start with
`--count 29`. The guard has not yet been exercised by another agent run. The
native process-abort source is not yet identified. The local YAMLs now use
`min_iter: 50` and `eta: 3`; this creates pruning brackets at 50 and 150
logged epochs, matching the current 150-epoch trial limit. The
prior remote sweep `kux6f586` keeps its original server-side schedule
(`max_iter: 100`, `s: 2`, `eta: 3`). Create a new sweep from the updated YAML to
use the later pruning point.

## Confirm the two leading fixed TCN configurations (2026-10-02)

The snapshot analysis in `docs/WANDB_SWEEP_ANALYSE_20261002.md` identifies
`nqntmdi0/vlfwfn7a` and `nqntmdi0/fxhhidgi` as nearly tied. Two separate
grid sweeps reproduce their exact fixed hyperparameters:

- `config/wandb/confirm_tcn_bilstm_vlfwfn7a.yaml`
- `config/wandb/confirm_tcn_bilstm_fxhhidgi.yaml`

Each grid varies only the seed over `[20260930, 20260931, 20260932, 20260933,
20260934]`. These are integer seed IDs, not calendar dates. The original seed
is included for a reproduction check; four additional shared seeds provide
new repetitions. Each trial gets 150 epochs, with no Hyperband configuration
and runner patience 151. Dataset, renderer, objective, warm-up and plateau
scheduler stay identical to the source trials.

The new fixed-TCN CLI option `--save-checkpoints` enables local `best.pt` and
`latest.pt` files plus SHA references in the manifest. It defaults to false
for existing sweeps. The confirmation commands enable local saving and
explicitly disable W&B checkpoint-artifact uploads with
`--no-wandb-log-checkpoints`. Metrik/config logging remains online.
`--wandb-log-checkpoints` controls upload separately from local saving.

Create both sweeps from the repository root:

```powershell
.venv\Scripts\wandb.exe sweep --project beatbridge config\wandb\confirm_tcn_bilstm_vlfwfn7a.yaml
.venv\Scripts\wandb.exe sweep --project beatbridge config\wandb\confirm_tcn_bilstm_fxhhidgi.yaml
```

Use the two full sweep identifiers printed by those commands. Run each agent
with its matching identifier (replace `ENTITY` and `SWEEP_ID_A/B`):

```powershell
.venv\Scripts\python.exe wandb_agent_guard.py agent --count 5 ENTITY/beatbridge/SWEEP_ID_A
.venv\Scripts\python.exe wandb_agent_guard.py agent --count 5 ENTITY/beatbridge/SWEEP_ID_B
```

Run them sequentially on the same GPU to avoid sharing its resources. The
grids contain five combinations each, ten trials total. Local results are
isolated under
`output/training_runs/wandb_confirmation/tcn_bilstm_vlfwfn7a/<SWEEP_ID>/<RUN_ID>`
and
`output/training_runs/wandb_confirmation/tcn_bilstm_fxhhidgi/<SWEEP_ID>/<RUN_ID>`.

Evaluate configuration means, sample standard deviations, and paired
per-seed differences in best validation loss. Report the four new seeds
separately from the original-seed reproduction, since the configurations were
selected using that original seed. Use the best checkpoint for listening,
not automatically the last epoch. Testsplit stays closed. The configs and
CLI plumbing were checked locally; these confirmation sweeps have not been
registered with W&B or executed yet.
