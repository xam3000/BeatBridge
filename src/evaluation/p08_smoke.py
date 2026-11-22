"""Run one CPU optimizer step per representation on identical sealed P08 queries."""

import argparse
from collections import Counter
from pathlib import Path

import torch
from torch import nn

from src.evaluation.comparison import write_json
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import MODEL_SEEDS, OUTPUT
from src.features.p08_windows import P07
from src.ml.p08_contrastive import PairWindows, batch_order, contrastive_step_loss, productions


def run(dataset, p07):
    torch.set_num_threads(1)
    seed, epoch = MODEL_SEEDS[0], 0
    result = dict(format_version=1, device="cpu", torch=str(torch.__version__), seed=seed,
                  epoch=epoch, dataset_sha256=file_sha256(dataset / "manifest.json"), families={})
    for family in ("classical", "mert"):
        data = PairWindows(dataset, p07, "train", family)
        rows = next(batch_order(data.rows, seed, epoch, data.manifest["batch_size"]))
        qids = [row["query_id"] for row in rows]
        if result.setdefault("query_ids", qids) != qids:
            raise ValueError("Smoke batches differ")
        q, p, negatives, mask = data.training_batch(rows, seed, epoch)
        torch.manual_seed(seed)
        head = nn.Linear(q.shape[-1], 32)
        optimizer = torch.optim.AdamW(head.parameters(), lr=.001, weight_decay=.0001)

        def encode(x):
            # Smoke only: equal-weight MERT layers, then pool the four bars.
            if family == "mert":
                x = x.mean(dim=-2)
            return head(x.mean(dim=-2))

        before = head.weight.detach().clone()
        loss = contrastive_step_loss(encode(q), encode(p), encode(negatives), mask,
                                     tau_plus=data.manifest["tau_plus"],
                                     temperature=data.manifest["temperature"])
        loss.backward()
        gradient = torch.linalg.vector_norm(head.weight.grad)
        optimizer.step()
        delta = torch.max(torch.abs(head.weight.detach() - before))
        if not (torch.isfinite(loss) and torch.isfinite(gradient) and gradient > 0
                and torch.isfinite(delta) and delta > 0):
            raise ValueError(f"Invalid optimizer step for {family}")
        result["families"][family] = dict(
            query_shape=list(q.shape), explicit_negative_shape=list(negatives.shape),
            loss=loss.item(), gradient_norm=gradient.item(), max_weight_delta=delta.item(),
            in_batch_negatives=dict(Counter(map(str, mask.sum(dim=1).tolist()))),
            source_views=dict(Counter(productions(qid, seed, epoch)[0] for qid in qids)),
            target_views=dict(Counter(productions(qid, seed, epoch)[1] for qid in qids)),
        )
        validation = PairWindows(dataset, p07, "validation", family)
        query, candidates, positive_index = validation.retrieval_item(0)
        result["families"][family]["validation_item"] = dict(
            query_id=validation.rows[0]["query_id"], query_shape=list(query.shape),
            candidates_shape=list(candidates.shape), positive_index=positive_index,
        )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=OUTPUT)
    parser.add_argument("--p07", type=Path, default=P07)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    receipt = run(args.dataset, args.p07)
    write_json(args.receipt, receipt)
    print(receipt["families"])
