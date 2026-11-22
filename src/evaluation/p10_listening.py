"""Prepare a bounded author review of development disagreements after the offline table is sealed."""

import argparse
import csv
from pathlib import Path

import numpy as np
import soundfile as sf

from src.evaluation.comparison import write_json
from src.evaluation.p10_pairs import RATE, development_views, pair_generation
from src.evaluation.p10_validation import ROOT, write_csv
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import publish_dataset
from src.features.p08_windows import checked, read_json
from src.pipeline import render_transition
from src.ranking.continuation import SELECTION


def prepare(out, pairs):
    bindings = read_json(pairs / "provenance.json")
    checked(pairs / "offline.csv", bindings["offline_table_sha256"])
    selection = read_json(checked(SELECTION, bindings["selection_sha256"]))["selected"]
    views = {v["sha256"]: v for v in development_views()}
    pair_index = {r["pair"]: r for r in read_json(pairs / "pairs.json")["pairs"]}
    with (pairs / "pair_metrics.csv").open(encoding="utf-8") as f:
        conflicts = [r for r in csv.DictReader(f) if r["family"] == selection["family"]
                     and int(r["level"]) == selection["level"] and r["seed"] == str(selection["seed"] or "")
                     and r["model_top"] != r["rule_top"]]
    key, notes, links = [], [], []
    for i, r in enumerate(conflicts[:10]):
        pair = pair_index[r["pair"]]
        a, b = [views[pair[k]] for k in ("source", "target")]
        generation, analysis = pair_generation(a, b)
        candidates = {c.candidate_id: c for c in generation.candidates}
        clips = []
        for method in (("model", "rule") if i % 2 == 0 else ("rule", "model")):
            candidate = candidates[r[method + "_top"]]
            render = render_transition(a["path"], b["path"], candidate.source_cutpoint.sample,
                                       candidate.target_cutpoint.sample, renderer="equal_power", baseline_bars=4,
                                       target_sample_rate=RATE, analysis=analysis, source_bpm=candidate.source_bpm,
                                       target_bpm=candidate.target_bpm, preview_seconds_before=5,
                                       preview_seconds_after=14)
            if render.audio.shape != (2, 19 * RATE) or not np.isfinite(render.audio).all():
                raise ValueError(f"Incomplete development clip for {candidate.candidate_id}")
            clips.append((method, candidate, render))
        # One common gain only when required for PCM headroom.
        peak = max(float(np.abs(render.audio).max()) for _, _, render in clips)
        gain = 1 / max(1., peak / .99)
        files = []
        for label, (method, candidate, render) in zip(("A", "B"), clips, strict=True):
            name = f'{r["pair"]}-{label}.wav'
            sf.write(out / name, (render.audio * gain).T, RATE, subtype="PCM_24")
            audio, sr = sf.read(out / name, always_2d=True)
            if (sr != RATE or audio.shape != (RATE * 19, 2) or
                    np.abs(audio.T - render.audio * gain).max() > 1.3e-7):
                raise ValueError(f"Export PCM differs: {name}")
            key.append(dict(pair=r["pair"], file=name, sha256=file_sha256(out / name), method=method,
                            candidate_id=candidate.candidate_id, source=a["sha256"], target=b["sha256"],
                            source_sample=candidate.source_cutpoint.sample, target_sample=candidate.target_cutpoint.sample,
                            transition_start=render.transition_start_sample, transition_end=render.transition_end_sample,
                            tempo_backend=render.tempo_backend, common_gain=gain))
            files.append(f"[{label}]({name})")
        notes.append(dict(Paar=r["pair"], Datum="", Minuten="", Gehoerte_Dateien="", Beobachtung=""))
        links.append(f'| {r["pair"]} | {" | ".join(files)} |')
        print(r["pair"], flush=True)
    write_json(out / "zuordnung.json", dict(offline_sha256=bindings["offline_table_sha256"],
               available_disagreements=len(conflicts), clips=key))
    if notes:
        write_csv(out / "sichtungsnotizen.csv", notes)
    (out / "Sichtung.md").write_text(
        "# Autorensichtung auf Entwicklungsdaten\n\n"
        f"Die beiden Clips jedes Paars verwenden verschiedene Top-1-Cues und denselben Equal-Power-Fade. "
        f"Hier stehen die ersten {len(notes)} von {len(conflicts)} widersprüchlichen Paaren in der "
        "festen Paarreihenfolge. Jeder Clip dauert 19 Sekunden.\n\n"
        "Je Paar A und B anhören, auffällige Stellen bei Bedarf wiederholen und die tatsächlich "
        "gehörten Dateien, Dauer und Beobachtungen in [sichtungsnotizen.csv](sichtungsnotizen.csv) "
        "eintragen. Wie wirken die Anschlüsse von Rhythmus und Energie am Cue? Wo ist der Vergleich "
        "uneindeutig? Etwa fünf Minuten pro Paar einplanen, insgesamt nach spätestens einer Stunde "
        "aufhören. Erst nach den Notizen zuordnung.json öffnen. Die A/B-Reihenfolge wechselt nach "
        "Paarindex. Diese offene Entwicklungssichtung liefert beschreibende Notizen. Sie gehen "
        "weder in die P11-Auswahl noch als Präferenzdaten in die Hypothesenprüfung ein.\n\n"
        "| Paar | Clip A | Clip B |\n|---|---|---|\n" + "\n".join(links) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, default=ROOT / "pairs")
    parser.add_argument("--output", type=Path, default=ROOT / "autorensichtung")
    args = parser.parse_args()
    with publish_dataset(args.output) as stage:
        prepare(stage, args.pairs)
