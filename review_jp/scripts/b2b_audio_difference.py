"""B2-Zusatz: Wie stark unterscheidet sich das gerenderte Audio des Modells
vom Equal-Power-Render (Epoche 0)? (validation, lokale Checkpoints)

Kennzahlen pro Beispiel:
  diff_db        RMS(Modell - Equal Power) relativ zu RMS(Equal Power), in dB
                 (-inf = identisch; -20 dB = Differenzsignal 10 % der Amplitude)
  max_frame_db   größte Pegelabweichung in einem der 32 Energie-Frames, in dB
  mean_frame_db  mittlere absolute Pegelabweichung über die 32 Frames, in dB

Start: review_jp/.venv/bin/python review_jp/scripts/b2b_audio_difference.py
"""

from __future__ import annotations

import numpy as np
import torch

from b1_b2_model_response_and_loss import evaluate, predict, row
from common import (RUNS, build_model, build_renderer_and_objective, dump_json, load_run,
                    load_split, load_waveforms)
from src.control.differentiable import _frame_rms_db


def main():
    report = {}
    for name in RUNS:
        spec, manifest, model, _ = load_run(name)
        kind = spec["kind"]
        torch.manual_seed(0)
        fresh = build_model(kind, manifest).eval()
        renderer, objective = build_renderer_and_objective(kind, manifest)
        validation = load_split(spec["dataset"], "validation")
        curves, reference = predict(kind, model, validation), predict(kind, fresh, validation)
        rows = []
        for index, example_id in enumerate(validation["example_ids"]):
            wave = load_waveforms(spec["cache"], example_id)
            fa = torch.from_numpy(validation["features_a"][index])
            fb = torch.from_numpy(validation["features_b"][index])
            with torch.no_grad():
                _, model_render = evaluate(kind, renderer, objective, row(curves, index), wave, fa, fb)
                _, base_render = evaluate(kind, renderer, objective, row(reference, index), wave, fa, fb)
                model_db = _frame_rms_db(model_render.audio.unsqueeze(0), 32, 1e-6)[0].numpy()
                base_db = _frame_rms_db(base_render.audio.unsqueeze(0), 32, 1e-6)[0].numpy()
            difference = (model_render.audio - base_render.audio).numpy()
            base = base_render.audio.numpy()
            rows.append({
                "diff_db": float(20 * np.log10(np.sqrt(np.mean(difference**2))
                                               / np.sqrt(np.mean(base**2)))),
                "max_frame_db": float(np.abs(model_db - base_db).max()),
                "mean_frame_db": float(np.abs(model_db - base_db).mean()),
            })
        summary = {key: {"median": float(np.median([r[key] for r in rows])),
                         "min": float(np.min([r[key] for r in rows])),
                         "max": float(np.max([r[key] for r in rows]))}
                   for key in rows[0]}
        report[name] = {"n": len(rows), "summary": summary, "rows": rows}
        print(name, len(rows), {k: {a: round(b, 2) for a, b in v.items()}
                                 for k, v in summary.items()})
    dump_json("b2b_audio_difference.json", report)


if __name__ == "__main__":
    main()
