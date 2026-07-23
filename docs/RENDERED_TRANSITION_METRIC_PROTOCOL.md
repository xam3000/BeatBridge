# Metrik für gerenderte Übergänge

_Vertragsversion: 1, eingeführt am 2026-07-23._

Dieses Dokument beschreibt `rendered_transition_baseline_v1`. Die Metrik
bewertet das bereits erzeugte Audio eines konkreten Renderer-Kandidaten. Damit
liegt sie nach Songpaar-Auswahl, Cutpoint-Ranking und Rendering:

```text
song_compatibility_v1
  → feature_baseline_v3
  → Renderer
  → rendered_transition_baseline_v1
```

Änderungen an Version 1 erfolgen nur additiv. Inkompatible Änderungen benötigen
eine neue `format_version` und einen neuen Metriknamen.

## Einstiegspunkt

```python
from src.ranking import RenderedTransitionInput, rank_rendered_transitions

ranking = rank_rendered_transitions(
    (
        RenderedTransitionInput(
            candidate_id="candidate-...",
            renderer="equal_power",
            audio=render_result.audio,
            sample_rate=render_result.sample_rate,
            transition_start_sample=render_result.transition_start_sample,
            transition_end_sample=render_result.transition_end_sample,
            transition_length_beats=16,
            bpm=160.0,
        ),
    )
)
```

`audio` ist das vollständige Renderer-Ergebnis im Speicher und enthält daher
Time-Stretch-, Schnitt- und Crossfade-Effekte. Die Originaltracks werden von
dieser Metrik nicht erneut geladen.

## Komponenten

| Komponente | Gewicht | Bedeutung |
|---|---:|---|
| `energy_shape` | 0,30 | Energie fällt von Drop A zur Bridge und steigt zu Drop B wieder an |
| `boundary_smoothness` | 0,30 | Lokale RMS-Sprünge und ungewöhnlich große Sample-Sprünge an den tatsächlichen Rendergrenzen bleiben klein |
| `harmonic_continuity` | 0,20 | Chromaprofile schließen am Beginn und Ende der gerenderten Bridge an |
| `rhythmic_stability` | 0,20 | Onset-Autokorrelation bleibt beim erwarteten Beat-Abstand stabil |

Alle Komponenten und der Gesamtscore liegen zwischen 0 und 1. Die Gewichte und
Toleranzen stehen vollständig in `RenderedTransitionMetricConfig` und werden im
Manifest gespeichert. Die Werte sind eine transparente Baseline und noch kein
perzeptuell validiertes Qualitätsmodell.

Bei einem Hard Cut sind `transition_start_sample` und
`transition_end_sample` identisch. Für die Analyse wird dann ein Fenster in der
angeforderten Übergangslänge nach dem Schnitt verwendet; die einzige
tatsächliche Rendergrenze ist der Schnitt selbst.

## Ergebnis und Fehlerisolation

`RenderedTransitionRankingResult` enthält:

- `format_version`
- `metric`
- die vollständige `config`
- nach Score sortierte `scores` mit `rank`, Komponenten und Messwerten
- isolierte `failures`

Ein Fehler in einer Variante verhindert weder den WAV-Export noch die Bewertung
anderer Varianten. Im Batch-Manifest stehen Score und Rang zusätzlich direkt
am jeweiligen Eintrag unter `rendered_variants`.

## Historische Batches nachbewerten

Bestehende Multi-Song-Batches werden ohne Änderung ihrer historischen
`manifest.json`-Dateien und WAVs bewertet:

```powershell
.venv\Scripts\python.exe -m src.evaluation.backfill_transition_metrics `
  output\batches\all_songs_top3_targets_top3_transitions_20260722
```

Der Befehl rekonstruiert die tatsächlichen Rendergrenzen samplegenau aus
Kandidaten-Beat-Index, unverändertem Analyse-Cache und damaliger
Tempoanpassung. Pro Paar und im Wurzelordner entsteht atomisch eine
`transition_metrics.json` mit `format_version = 1`. Das Wurzel-Sidecar dient
zugleich als Fortschritts- und Summenmanifest. Vorhandene Sidecars werden nur
mit dem expliziten Schalter `--overwrite` ersetzt.

Das Hör-Notebook liest diese Sidecars automatisch, wenn das historische
Batch-Manifest noch kein eingebettetes `rendered_transition_ranking` besitzt.

## Methodische Grenze

Die Baseline ist kein Ersatz für menschliche Urteile. Sie muss gegen
Hörbewertungen geprüft und später mit einer Embedding-/ML-Metrik auf exakt
denselben gerenderten Varianten verglichen werden. Insbesondere Vocal-Clashes
und komplexe Time-Stretch-Artefakte werden in Version 1 noch nicht explizit
modelliert.
