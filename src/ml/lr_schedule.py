"""Learning-rate schedule helpers shared by the TCN/BiLSTM runners."""

from __future__ import annotations

import torch


def validate_lr_schedule_config(
    *,
    warmup_epochs,
    warmup_start_factor,
    scheduler_patience,
    scheduler_factor,
    scheduler_threshold,
    scheduler_min_lr_factor,
):
    if int(warmup_epochs) < 0:
        raise ValueError("lr_warmup_epochs must be non-negative")
    if not 0 < float(warmup_start_factor) <= 1:
        raise ValueError("lr_warmup_start_factor must be in (0, 1]")
    if int(scheduler_patience) < 1:
        raise ValueError("lr_scheduler_patience must be at least 1")
    if not 0 < float(scheduler_factor) < 1:
        raise ValueError("lr_scheduler_factor must be in (0, 1)")
    if float(scheduler_threshold) < 0:
        raise ValueError("lr_scheduler_threshold must be non-negative")
    if not 0 < float(scheduler_min_lr_factor) <= 1:
        raise ValueError("lr_scheduler_min_lr_factor must be in (0, 1]")


def make_plateau_scheduler(optimizer, config):
    """Build a validation-loss scheduler with a floor relative to the base LR."""

    return torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=config.lr_scheduler_factor,
        patience=config.lr_scheduler_patience,
        threshold=config.lr_scheduler_threshold,
        threshold_mode="abs",
        min_lr=[
            float(group.get("initial_lr", group["lr"]))
            * config.lr_scheduler_min_lr_factor
            for group in optimizer.param_groups
        ],
    )


def apply_linear_warmup(
    optimizer,
    *,
    epoch,
    warmup_epochs,
    start_factor,
):
    """Set this epoch's LR on a linear ramp from start_factor to the base LR."""

    warmup_epochs = int(warmup_epochs)
    epoch = int(epoch)
    if warmup_epochs < 1 or epoch > warmup_epochs:
        return

    progress = 1.0 if warmup_epochs == 1 else (epoch - 1) / (warmup_epochs - 1)
    factor = float(start_factor) + (1.0 - float(start_factor)) * progress
    for group in optimizer.param_groups:
        base_lr = float(group.setdefault("initial_lr", group["lr"]))
        group["lr"] = base_lr * factor


def step_plateau_after_warmup(scheduler, validation_loss, *, epoch, warmup_epochs):
    """Start reacting to validation loss only after the ramp-up is complete."""

    if scheduler is not None and int(epoch) >= int(warmup_epochs):
        scheduler.step(float(validation_loss))


def current_learning_rate(optimizer):
    return float(optimizer.param_groups[0]["lr"])
