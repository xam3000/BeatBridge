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
