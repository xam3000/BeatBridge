# Hörbewertungs-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21._

Menschliche Urteile werden getrennt vom unveränderlichen Batch-Manifest in `ratings.json` im jeweiligen Batch-Ordner gespeichert. Eine erneute Bewertung derselben Kombination aus Kandidaten-ID und Renderer aktualisiert den bestehenden Eintrag atomar.

## Bewertung

`overall` verwendet eine einfache Ordinalskala:

| Wert | Bedeutung |
|---:|---|
| 1 | sehr schlecht |
| 2 | schlecht |
| 3 | mittel / unentschieden |
| 4 | gut |
| 5 | sehr gut |

Optionale Fehler-Tags sind `rhythm`, `phrasing`, `harmony`, `energy`, `loudness`, `vocals`, `artifacts` und `other`. Eine freie Notiz hält konkrete Beobachtungen fest.

Jeder Eintrag enthält `candidate_id`, `renderer`, `output_file`, `overall`, `issues`, `notes` und `updated_at_utc`. Nur tatsächlich im Batch-Manifest vorhandene gerenderte Varianten können bewertet werden.

## Notebook

`notebooks/listen_batch.ipynb` listet Varianten in Feature-Rangfolge und stellt bereit:

```python
plot_cue_points(0, seconds_before=8, seconds_after=8)
play(0)
rate(0, 2, issues=("phrasing", "vocals"), notes="Einstieg wirkt zu früh.")
show_ratings()
```

`plot_cue_points(...)` lädt Source- und Target-Audio um die im Kandidaten
gespeicherten Cue Points, richtet beide Grenzen auf der gemeinsamen relativen
Zeitachse bei `t = 0` aus und zeichnet die Waveforms untereinander.
`play(index)` zeigt diese Cue-Point-Ansicht automatisch vor Metrikkomponenten
und Audio-Player an.

## CLI

Dieselbe Bewertung kann ohne Notebook gespeichert werden:

```powershell
.venv\Scripts\python.exe -m src.evaluation.ratings `
  "output\batches\help_to_breath_drop_bridge" `
  "candidate-..." `
  equal_power `
  2 `
  --issues phrasing vocals `
  --notes "Einstieg wirkt zu früh."
```

Version 1 ist für die persönliche Entwicklungsbewertung gedacht. Mehrere Rater, Randomisierung, Verblindung und paarweise Vergleiche benötigen später ein separates Studienprotokoll.
