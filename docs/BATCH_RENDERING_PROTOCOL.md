# Batch-Rendering-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21._

Das Batch-Rendering ist die stabile Grenze zwischen Kandidatengenerierung und dem späteren Hörvergleich. Es rendert ausschließlich akzeptierte `TransitionCandidate`-Einträge und schreibt pro Lauf WAV-Dateien sowie ein vollständiges JSON-Manifest.

## Ausgabe-Struktur

```text
output/batches/help_to_breath/
├── manifest.json
├── ratings.json                 # optional, nach menschlicher Bewertung
└── rendered/
    ├── 0001__candidate-…__simple.wav
    ├── 0001__candidate-…__fade.wav
    └── …
```

Der Nummernpräfix folgt der deterministischen Kandidatenreihenfolge. Der Dateiname enthält zusätzlich Kandidaten-ID und Renderer, sodass jede WAV-Datei ohne Kontext dem Manifest zugeordnet werden kann.

## `manifest.json`

Das Manifest hat `format_version = 1` und enthält:

| Feld | Bedeutung |
|---|---|
| `renderers` | In diesem Lauf angeforderte Renderer |
| `render_protocol_version` | Semantik der gerenderten Audiodateien; aktuell Version 4 mit Bridge-Crossfade, verpflichtender Tempoanpassung und kurzer Vorschau |
| `candidate_generation` | Vollständiges Ergebnis nach `CANDIDATE_PROTOCOL.md`, einschließlich abgelehnter Kandidaten |
| `candidate_ranking` | Feature-Ränge, Einzelkomponenten, Messwerte und Rankingfehler nach `RANKING_PROTOCOL.md` |
| `render_selection` | Gerenderte Kandidaten-IDs und optionales `top_k` |
| `render_preview` | Vorschau-Kontext in Sekunden vor/nach dem Source-Cutpoint |
| `rendered_variants` | Erfolgreiche Exporte: Kandidaten-ID, Renderer, relativer Dateipfad, Sample-Rate und Sample-Anzahl |
| `failures` | Pro fehlgeschlagener Variante Fehlertyp, Meldung, Kandidaten-ID und Renderer |

`rendered_variants` enthält additiv den Feature-Rang und Gesamtscore des Kandidaten. Ein Lauf ohne akzeptierte Kandidaten erzeugt trotzdem ein Manifest. So bleiben harte Filterentscheidungen nachvollziehbar. Einzelne fehlgeschlagene Varianten brechen die übrigen unabhängigen Exporte nicht ab, werden aber sichtbar im Manifest erfasst und führen in der CLI zu Exit-Code `1`.

## Schreib- und Überschreiberegeln

- Audio und Manifest werden zuerst in einer temporären Datei geschrieben und anschließend atomar an ihren Zielpfad verschoben.
- Bestehende Dateien werden standardmäßig **nicht** überschrieben. Der Lauf bricht vor dem ersten Export mit einer konkreten Fehlermeldung ab.
- Nur die explizite CLI-Option `--overwrite` beziehungsweise der API-Parameter `overwrite=True` erlaubt das Ersetzen gleichnamiger Exportdateien.
- Quelldateien bleiben unverändert; sie werden ausschließlich gelesen.

## Programmatische API

```python
from src.batch_render import generate_and_render_batch

result = generate_and_render_batch(
    "musik/song_a.wav",
    "musik/song_b.wav",
    "output/batches/song_a_to_song_b",
    renderers=("simple", "fade", "equal_power", "tempo_fade"),
)
print(result.manifest_path)
```

Die Funktion verwendet Kandidatengenerierung, Feature-Ranking und das normalisierte Sample-Raster der Pipeline. Für jeden Renderer werden die im Kandidaten gespeicherten BPM verwendet und Song B tonhöhenerhaltend auf Song A angepasst. Standardmäßig enthält jede WAV fünf Sekunden vor und zwölf Sekunden nach dem Source-Cutpoint; die Werte stehen auditierbar im Manifest und sind über die API beziehungsweise CLI konfigurierbar. Standardmäßig werden nur die fünf bestbewerteten Kandidaten gerendert; das Manifest enthält weiterhin alle erzeugten Kandidaten und Scores. `top_k=None` rendert über die programmatische API alle Kandidaten. Für fortlaufende Experimente sollte jeder Lauf einen neuen Ausgabepfad erhalten.
