# Kandidaten-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21._

Dieses Dokument beschreibt die stabile Schnittstelle zwischen Analyse, Kandidatengenerierung, künftigem Ranking und Batch-Rendering. Änderungen an Version 1 erfolgen nur additiv; inkompatible Änderungen benötigen eine neue `format_version`.

## Einheiten und Koordinatensystem

- **Beat**: eine erkannte Zählzeit; seine Position wird als `beat_index` und `sample` gespeichert.
- **Takt**: eine Folge von `beats_in_bar` Beats; `bar_index` ist nullbasiert relativ zum ersten erkannten Downbeat eines Tracks.
- **Phrase**: ist bewusst noch kein Kandidatenfeld. Sie wird erst ergänzt, sobald eine belastbare Segmentierungsquelle vorliegt.
- **Sample**: Cutpoints liegen auf dem normalisierten Render-Raster (standardmäßig 44.100 Hz), nicht auf der originalen Eingangs-Sample-Rate.
- **Übergangslänge**: ist kanonisch `transition_length_bars` (initial 1, 2 oder 4 Takte). `transition_length_beats` wird aus dem Taktfenster abgeleitet und an die aktuellen Fade-Renderer übergeben.

## `TransitionCandidate`

Ein akzeptierter Kandidat enthält mindestens:

| Feld | Bedeutung |
|---|---|
| `format_version` | Aktuell `1` |
| `candidate_id` | Deterministische ID aus Track-Hashes, Cutpoints und Taktlänge |
| `source_track`, `target_track` | Lokaler Pfad und SHA-256 der unveränderten Audioquelle |
| `source_cutpoint`, `target_cutpoint` | Downbeat mit Sample-, Beat- und Taktindex sowie Metrum |
| `transition_length_bars` | Nutzernahe, kanonische Übergangslänge |
| `transition_length_beats` | Für Renderer abgeleitete Beatanzahl |
| `source_bpm`, `target_bpm`, `tempo_relative_difference` | Tempo-Provenienz und Filtergrundlage |
| `generator` | Aktuell `bar_grid_v1` |
| `filter_status` | Für ausgegebene Kandidaten immer `accepted` |

Das Python-Datenmodell bietet `to_dict()` für ein späteres JSON-Manifest. Die Abwesenheit eines Kandidaten wird nicht stillschweigend behandelt: `CandidateGenerationResult.rejections` enthält für jeden harten Filter einen maschinenlesbaren Code und eine Erklärung.

## Generator `bar_grid_v1`

Der erste Generator bildet die letzten konfigurierbaren, nutzbaren Taktgrenzen von Song A mit den ersten nutzbaren Taktgrenzen von Song B. Er erzeugt daraus Varianten mit 1, 2 und 4 Takten.

Die derzeitigen Fade-Renderer überblenden Audio **vor** einem Cutpoint. Deshalb ist ein Cutpoint nur nutzbar, wenn davor für die längste angeforderte Variante genügend vollständige Takte liegen. Auf Song B ist die Startgrenze bei Sample 0 daher kein gültiger Fade-Kandidat; der Generator wählt stattdessen die früheste nach ausreichendem Pre-Roll erreichbare Taktgrenze.

Harte Filter in Version 1:

1. vollständige, steigende Beat-/Downbeat-Metadaten mit konsistenten Takten im Übergangsfenster,
2. vollständiges Pre-Roll-Fenster für jede angeforderte Taktlänge,
3. identische abgeleitete Beatanzahl auf beiden Seiten,
4. symmetrische relative Tempoabweichung höchstens 15 % (konfigurierbar).

Vocal-Overlap, Energie, Harmonie, Phrasen- und Segmentinformationen bleiben bewusst spätere weiche Metrik-Komponenten und werden noch nicht vorgetäuscht gefiltert.

## Programmatic API

```python
from src.pipeline import generate_transition_candidates

result = generate_transition_candidates("musik/song_a.wav", "musik/song_b.wav")
for candidate in result.candidates:
    print(candidate.candidate_id, candidate.transition_length_beats)
```

Die Funktion nutzt dieselbe Analyse und dieselbe Sample-Raten-Normalisierung wie `render_transition()`. Batch-Export und Manifest-Datei sind der folgende, bewusst getrennte Meilenstein.
