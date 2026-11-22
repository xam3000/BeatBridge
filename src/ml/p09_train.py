"""Train the P09 ladder locally against the sealed P08 train/validation panels."""

import argparse
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch

from src.features.p07_mert import file_sha256
from src.features.p08_pairs import OUTPUT
from src.features.p08_windows import P07
from src.ml.p08_contrastive import PairWindows, batch_order, debiased_loss
from src.ml.p09_metric import ContinuationMetric, HIDDEN, RANK
from src.ml.p09_windows import WindowBank


def save_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def step_loss(model, bank, indices, mask, contract):
    query = model.encode(bank[indices[:, 0]], source=True)
    targets = model.encode(bank[indices[:, 1:]], source=False)
    scores = (query[:, None] * targets).sum(-1)
    negatives = torch.cat((scores[:, 1:], query @ targets[:, 0].T), dim=1)
    valid = torch.cat((torch.ones_like(scores[:, 1:], dtype=torch.bool), mask), dim=1)
    return debiased_loss(scores[:, 0], negatives, valid, temperature=contract["temperature"],
                         tau_plus=contract["tau_plus"])


@torch.no_grad()
def evaluate(model, validation):
    model.eval()
    panels = torch.as_tensor(validation.panels, device=validation.values.device)
    # Encode each distinct window once per role at current checkpoint weights.
    def encoded(source):
        return torch.cat([model.encode(chunk, source=source) for chunk in validation.values.split(256)])

    queries, targets = encoded(True), encoded(False)
    scores = torch.cat([(queries[p[:, :1]] * targets[p[:, 1:]]).sum(-1)
                        for p in panels.split(256)]).cpu().numpy()
    if not np.isfinite(scores).all() or np.max(np.abs(scores)) > 1.0001:
        raise ValueError("Invalid retrieval score")
    ranking = np.argsort(-scores, axis=1, kind="stable")
    ranks = (ranking == validation.truth[:, None]).argmax(axis=1) + 1
    track = validation.tracks
    counts = np.bincount(track)

    def macro(values):
        return float((np.bincount(track, weights=values) / counts).mean())

    return dict(recall1=macro(ranks == 1), mrr=macro(1 / ranks)), ranks


def verify_smoke_batch(data, bank, seed):
    order, indices, masks = bank.epoch(seed, 0, bank.production_offsets(seed), 32)
    rows = [bank.rows[i] for i in order[:32]]
    q, p, e, mask = data.training_batch(rows, seed, 0)
    cached = bank.values[indices[0]].cpu()
    for source, expected in [(cached[:, 0], q.mean(1)), (cached[:, 1], p.mean(1)),
                             (cached[:, 2:], e.mean(2))]:
        torch.testing.assert_close(source, expected, atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(masks[0].cpu(), mask)


def run_head(folder, family, level, seed, train, validation, config, smoke):
    directory = folder / f"{family}_s{level}_{seed or 'deterministic'}"
    directory.mkdir()
    if seed is not None:
        torch.manual_seed(seed)
    device = validation.values.device
    model = ContinuationMetric(family, level).to(device)
    count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    result = dict(family=family, level=level, seed=seed, parameters=count, epochs=0, steps=0,
                  best_epoch=None, checkpoint=None, checkpoint_sha256=None)
    best = -1.
    history = []
    if level:
        optimizer = torch.optim.AdamW(model.parameters(), lr=config["lr"],
                                      weight_decay=config["weight_decay"], fused=device.type == "cuda")
        offsets = train.production_offsets(seed)
        before = {k: v.detach().clone() for k, v in model.named_parameters()} if smoke else {}
        for epoch in range(1 if smoke else config["epochs"]):
            model.train()
            order, batches, masks = train.epoch(seed, epoch, offsets, config["batch_size"])
            losses = []
            for ids, mask in zip(batches, masks, strict=True):
                optimizer.zero_grad(set_to_none=True)
                loss = step_loss(model, train.values, ids, mask, config)
                loss.backward()
                optimizer.step()
                losses.append(loss.detach() * len(ids))
            mean_loss = torch.stack(losses).sum().item() / len(order)
            metrics, _ = evaluate(model, validation)
            result["steps"] += len(batches)
            result["epochs"] = epoch + 1
            history.append(dict(epoch=epoch+1, steps=result["steps"], queries=len(order),
                                order_sha256=hashlib.sha256(order.astype("<i8").tobytes()).hexdigest(),
                                train_dcl=mean_loss, **metrics))
            if metrics["recall1"] > best:
                best = metrics["recall1"]
                result["best_epoch"] = epoch + 1
                tmp = directory / "best.tmp"
                torch.save(dict(format_version=1, family=family, level=level, seed=seed,
                                epoch=epoch+1, parameters=count, metrics=metrics,
                                config_sha256=file_sha256(folder / "config.json"),
                                state_dict=model.state_dict()), tmp)
                tmp.replace(directory / "best.pt")
            save_json(directory / "history.json", history)
            if epoch == 0 or (epoch+1) % 5 == 0:
                print(directory.name, epoch+1, history[-1]["train_dcl"], metrics, flush=True)
        if smoke:
            changes = {k: (v-before[k]).abs().max().item() for k, v in model.named_parameters()}
            if not all(delta > 0 for delta in changes.values()):
                raise ValueError(f"Smoke parameter did not move: {changes}")
            save_json(directory / "updates.json", changes)
        path = directory / "best.pt"
        checkpoint = torch.load(path, map_location=device, weights_only=True)
        model.load_state_dict(checkpoint["state_dict"])
        result.update(checkpoint=path.relative_to(folder).as_posix(), checkpoint_sha256=file_sha256(path))
    metrics, ranks = evaluate(model, validation)
    if level and (metrics != checkpoint["metrics"] or checkpoint["epoch"] != result["best_epoch"]):
        raise ValueError("Reloaded checkpoint does not reproduce selection")
    with (directory / "validation_ranks.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("query_id", "rank"))
        writer.writerows((r["query_id"], rank) for r, rank in zip(validation.rows, ranks, strict=True))
    result.update(metrics)
    save_json(directory / "result.json", result)
    return result


def run(args):
    if args.device.startswith("cuda"):
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for family in ("classical", "mert"):
        datasets = [PairWindows(args.dataset, args.p07, split, family, cache_tracks=1)
                    for split in ("train", "validation")]
        contract = datasets[0].manifest
        seeds = contract["model_seeds"]
        if not results:
            config = {k: contract[k] for k in ("epochs", "batch_size", "model_seeds", "temperature", "tau_plus",
                                               "k", "length_bars", "scaler_id", "p07_manifest_sha256", "freeze_commit")}
            config.update(format_version=1, smoke=args.smoke, dataset_sha256=file_sha256(args.dataset / "manifest.json"),
                          split_sha256={s: contract["files"][f"{s}.jsonl"] for s in ("train", "validation")},
                          lr=.001, weight_decay=.0001, optimizer="AdamW", rank=RANK, hidden=HIDDEN,
                          selection="highest source-recording macro Recall@1; earliest epoch on ties",
                          device=args.device, torch_version=str(torch.__version__),
                          gpu=torch.cuda.get_device_name() if args.device.startswith("cuda") else None)
            save_json(args.output / "config.json", config)
        train_data, val_data = datasets
        train_rows, val_rows = train_data.rows, val_data.rows
        if args.smoke:
            train_rows = next(batch_order(train_rows, seeds[0], 0, 35))
            val_rows = val_rows[:24]
        print("Loading", family, len(train_rows), len(val_rows), flush=True)
        train = WindowBank(train_data, train_rows, args.device)
        validation = WindowBank(val_data, val_rows, args.device)
        if args.smoke:
            verify_smoke_batch(train_data, train, seeds[0])
        for level in range(3):
            for seed in ([None] if level == 0 else seeds[:1] if args.smoke else seeds):
                result = run_head(args.output, family, level, seed, train, validation, config, args.smoke)
                results.append(result)
                print("Completed", result, flush=True)
                if args.journal:
                    with args.journal.open("a", encoding="utf-8") as stream:
                        stream.write(f"\n- {date.today():%d.%m.%Y} · P09 {'Smoke' if args.smoke else 'Hauptlauf'} "
                                     f"{family}, Stufe {level}, Seed {seed or 'entfällt'}. "
                                     f"Frage: Welche Validationsränge erreicht dieser Kopf auf den P08-Panels? "
                                     f"Aufruf und Vertrag: `src.ml.p09_train`, `{args.output.as_posix()}/config.json`. "
                                     f"{len(train_rows)} verfügbare Trainingsqueries, {len(val_rows)} Validationsqueries, "
                                     f"{result['epochs']} Epochen, {result['steps']} Updates. "
                                     f"Recall@1 {result['recall1']:.6f}, MRR {result['mrr']:.6f}, "
                                     f"Bestepoche {result['best_epoch'] or 'entfällt'}. "
                                     f"Einzelränge gespeichert. Weiter mit dem gepaarten Tabellenvergleich.\n")
        del train, validation
    with (args.output / "matrix.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=OUTPUT)
    parser.add_argument("--p07", type=Path, default=P07)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--journal", type=Path)
    run(parser.parse_args())
