"""Prüft, ob der MERT-Vorsprung der Fortsetzungsmetrik am gemeinsamen Encoder-Kontext hängt.

Hintergrund (Rückmeldung vom 22.11.2026, Befund 1)
---------------------------------------------------
P07 berechnet MERT über den ganzen Track in Kernen von 20 s mit 2 s Kontext
je Seite (src/features/p07_mert.py, CORE_SAMPLES / CONTEXT_SAMPLES). MERT ist
ein Transformer mit voller Selbstaufmerksamkeit über den Eingabeblock. Liegen
das Abfragefenster [d-k, d) und die richtige Fortsetzung [d+L, d+L+k) im selben
Block, hat die Abfrage die Fortsetzung bereits "gesehen". Die falschen
Kandidaten (andere Tracks oder mehr als 16 Takte entfernt) teilen nie einen
Block mit der Abfrage. Bei der Anwendung auf zwei verschiedene Songs gibt es
diesen gemeinsamen Kontext nicht.

Was das Skript tut
------------------
Es schichtet die vorhandenen Validation-Ergebnisse aus P09 danach, ob Abfrage
und Fortsetzung Encoder-Kontext teilen:

  getrennt    Kein Frame der Abfrage sah Audio der Fortsetzung und umgekehrt
              (eine Kerngrenze liegt mit je 2 s Abstand in der Lücke).
  teilweise   Ein Teil der Frames teilt Kontext.
  gemeinsam   Alle Frames beider Fenster lagen im selben Eingabeblock.
  kontakt     teilweise und gemeinsam zusammen (Vergleichsgruppe für "getrennt").

Für jede P09-Bedingung berichtet es Recall@1 je Schicht. Die klassischen
Merkmale sind die Kontrolle: Sie sind lokal berechnet und dürfen zwischen den
Schichten nicht systematisch abweichen. Fällt MERT in "getrennt" deutlich
stärker ab als klassisch, trägt der gemeinsame Kontext einen Teil des
Ergebnisses.

Grenzen: Das ist eine Schichtung vorhandener Ergebnisse, kein sauberer Test.
Die Schicht "getrennt" ist klein (rund 10 bis 12 % der Abfragen), und die
Köpfe wurden auf gemischten Fällen trainiert. Der saubere Test ist das
Neuberechnen einzeln kodierter Fenster (siehe Rückmeldung, Befund 1).

Es wird nur gelesen. Geschrieben wird eine JSON-Datei unter review_jp/results/.

Aufruf (Windows, aus dem Repo-Root):
  .venv\\Scripts\\python.exe -B -X utf8 review_jp\\scripts\\mert_kontext_check.py

Pfade, falls abweichend:
  --p07  output/review_jp_20261118/p07/full
  --p08  output/review_jp_20261118/p08_paare/run02
  --p09  output/review_jp_20261118/p09_metrik/run01

Selbsttest ohne Daten:
  python review_jp/scripts/mert_kontext_check.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.features.p07_mert import CONTEXT_SAMPLES, CORE_SAMPLES  # noqa: E402

STRATA = ("getrennt", "teilweise", "gemeinsam")


def seen_share(start, end, other_start, other_end, core=CORE_SAMPLES, context=CONTEXT_SAMPLES):
    """Anteil der Samples in [start, end), deren Kern-Eingabeblock [other_start, other_end) berührt.

    Ein Frame gehört zum Kern c = Sample // core. Dessen Eingabe reicht von
    c*core - context bis (c+1)*core + context (p07_mert.chunk_spans).
    """
    if end <= start:
        raise ValueError("Leeres Fenster")
    seen = 0
    for c in range(start // core, (end - 1) // core + 1):
        left, right = max(start, c * core), min(end, (c + 1) * core)
        block_start, block_end = c * core - context, (c + 1) * core + context
        if block_start < other_end and other_start < block_end:
            seen += right - left
    return seen / (end - start)


def stratum(query, target):
    """query/target: (start, end) in 24-kHz-Samples."""
    q = seen_share(*query, *target)
    t = seen_share(*target, *query)
    if q == 0 and t == 0:
        return "getrennt", q, t
    if q == 1 and t == 1:
        return "gemeinsam", q, t
    return "teilweise", q, t


def windows_for(bars, d, k, length):
    """Sample-Grenzen der Fenster [d-k, d) und [d+length, d+length+k) aus (n, 9)-Taktgrenzen."""
    t = d + length
    if d - k < 0 or t + k > len(bars):
        raise ValueError("Fenster außerhalb der Taktliste")
    return (int(bars[d - k, 0]), int(bars[d - 1, -1])), (int(bars[t, 0]), int(bars[t + k - 1, -1]))


def recall_by_stratum(labels, recordings, ranks):
    """Recall@1 je Schicht: erst je Aufnahme mitteln, dann Aufnahmen gleich gewichten (wie P09)."""
    labels, recordings, hits = np.asarray(labels), np.asarray(recordings), np.asarray(ranks) == 1
    out = {}
    for name in (*STRATA, "kontakt"):
        # "kontakt" fasst alle Abfragen mit geteiltem Kontext zusammen.
        mask = labels != "getrennt" if name == "kontakt" else labels == name
        if not mask.any():
            out[name] = dict(queries=0, recordings=0, recall1_macro=None, recall1_micro=None)
            continue
        per_recording = [hits[mask & (recordings == r)].mean() for r in np.unique(recordings[mask])]
        out[name] = dict(queries=int(mask.sum()), recordings=len(per_recording),
                         recall1_macro=float(np.mean(per_recording)),
                         recall1_micro=float(hits[mask].mean()))
    return out


def load_real(args):
    manifest = json.loads((args.p07 / "manifest.json").read_text(encoding="utf-8"))
    bars = {}
    for view in manifest["views"]:
        if view["variant"] != "original" or view["split"] != "validation":
            continue
        with np.load((args.p07 / view["entry"]).with_name("bars.npz")) as archive:
            bars[view["sha256"]] = archive["bar_boundaries_24k"].astype(np.int64)
    contract = json.loads((args.p08 / "manifest.json").read_text(encoding="utf-8"))
    k, length = int(contract["k"]), int(contract["length_bars"])
    rows = [json.loads(line) for line in (args.p08 / "validation.jsonl").read_text(encoding="utf-8").splitlines()]
    conditions = {}
    for directory in sorted(p for p in args.p09.iterdir() if (p / "validation_ranks.csv").is_file()):
        with (directory / "validation_ranks.csv").open(newline="", encoding="utf-8") as stream:
            conditions[directory.name] = {r["query_id"]: int(r["rank"]) for r in csv.DictReader(stream)}
    return bars, rows, k, length, conditions


def analyse(bars, rows, k, length, conditions):
    labels, recordings, ids, shares = [], [], [], []
    for row in rows:
        sha, d = row["query_id"].split(":")
        query, target = windows_for(bars[sha], int(d), k, length)
        name, q, t = stratum(query, target)
        labels.append(name)
        recordings.append(sha)
        ids.append(row["query_id"])
        shares.append((q, t))
    report = dict(
        core_seconds=CORE_SAMPLES / 24000, context_seconds=CONTEXT_SAMPLES / 24000,
        k=k, length_bars=length, queries=len(ids),
        strata_counts={name: labels.count(name) for name in STRATA},
        mean_query_share_seeing_target=float(np.mean([s[0] for s in shares])),
        mean_target_share_seeing_query=float(np.mean([s[1] for s in shares])),
        conditions={},
    )
    for name, ranks in conditions.items():
        missing = [i for i in ids if i not in ranks]
        if missing:
            raise ValueError(f"{name}: {len(missing)} Abfragen ohne Rang, z. B. {missing[0]}")
        result = recall_by_stratum(labels, recordings, [ranks[i] for i in ids])
        apart, contact = result["getrennt"]["recall1_macro"], result["kontakt"]["recall1_macro"]
        result["drop_getrennt_vs_kontakt"] = (
            None if apart is None or contact is None else float(contact - apart))
        report["conditions"][name] = result
    return report


def print_report(report):
    print(f"Abfragen: {report['queries']}  Schichten: {report['strata_counts']}")
    columns = (*STRATA, "kontakt")
    print(f"{'Bedingung':32} " + " ".join(f"{name:>11}" for name in columns) + "   Abfall")
    for name, result in report["conditions"].items():
        cells = []
        for s in columns:
            value = result[s]["recall1_macro"]
            cells.append(f"{'-':>11}" if value is None else f"{100 * value:10.1f}%")
        drop = result["drop_getrennt_vs_kontakt"]
        print(f"{name:32} " + " ".join(cells) + ("        -" if drop is None else f"  {100 * drop:6.1f} Pkt."))
    print("\nLesart: 'kontakt' = teilweise und gemeinsam zusammen. 'Abfall' = Recall@1 mit Kontakt "
          "minus Recall@1 ohne (getrennt).\nVergleiche den Abfall der MERT-Zeilen mit dem der "
          "klassischen Zeilen.")


def selftest():
    core, ctx = 100, 10
    # Beide Fenster im selben Kern: alles gesehen.
    assert seen_share(10, 30, 60, 80, core, ctx) == 1.0
    # Abfrage endet 10 vor der Kerngrenze (100), Fortsetzung beginnt 10 danach: gerade getrennt.
    assert seen_share(60, 90, 110, 140, core, ctx) == 0.0
    assert seen_share(110, 140, 60, 90, core, ctx) == 0.0
    # Fortsetzung beginnt 5 nach der Grenze: Abfrage-Kern (bis 110) sieht sie.
    assert seen_share(60, 90, 105, 140, core, ctx) == 1.0
    # Abfrage über die Grenze: nur der Teil im zweiten Kern teilt den Block mit der Fortsetzung.
    assert abs(seen_share(80, 120, 150, 180, core, ctx) - 0.5) < 1e-12
    name, q, t = "", 0, 0
    old = (CORE_SAMPLES, CONTEXT_SAMPLES)
    bars = np.array([[i * 38400 + j * 4800 for j in range(9)] for i in range(40)], dtype=np.int64)
    query, target = windows_for(bars, 6, 4, 4)
    assert query == (2 * 38400, 6 * 38400) and target == (10 * 38400, 14 * 38400)
    name, q, t = stratum(query, target)
    assert name in STRATA and old == (480000, 48000)
    result = recall_by_stratum(["getrennt", "getrennt", "gemeinsam", "gemeinsam"],
                               ["a", "b", "a", "a"], [1, 2, 1, 1])
    assert result["getrennt"]["recall1_macro"] == 0.5 and result["gemeinsam"]["recall1_macro"] == 1.0
    assert result["teilweise"]["queries"] == 0 and result["kontakt"]["queries"] == 2
    rows = [dict(query_id=f"x:{d:06d}") for d in range(4, 30)]
    report = analyse({"x": bars}, rows, 4, 4, {"demo": {r["query_id"]: 1 + (i % 3 == 0) for i, r in enumerate(rows)}})
    assert sum(report["strata_counts"].values()) == len(rows)
    print_report(report)
    print("Selbsttest bestanden.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = REPO / "output" / "review_jp_20261118"
    parser.add_argument("--p07", type=Path, default=root / "p07" / "full")
    parser.add_argument("--p08", type=Path, default=root / "p08_paare" / "run02")
    parser.add_argument("--p09", type=Path, default=root / "p09_metrik" / "run01")
    parser.add_argument("--output", type=Path, default=REPO / "review_jp" / "results" / "mert_kontext_check.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    report = analyse(*load_real(args))
    print_report(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("geschrieben:", args.output)


if __name__ == "__main__":
    main()
