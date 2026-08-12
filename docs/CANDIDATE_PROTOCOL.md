# Kandidaten-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21; additive Grid-Provenienz seit 2026-08-12._

Dieses Dokument beschreibt die stabile Schnittstelle zwischen Analyse, Kandidatengenerierung, künftigem Ranking und Batch-Rendering. Änderungen an Version 1 erfolgen nur additiv; inkompatible Änderungen benötigen eine neue `format_version`.

## Einheiten und Koordinatensystem

- **Beat**: eine erkannte Zählzeit; seine Position wird als `beat_index` und `sample` gespeichert.
- **Takt**: eine Folge von `beats_in_bar` Beats; `bar_index` ist nullbasiert relativ zum ersten erkannten Downbeat eines Tracks.
- **Phrase**: ist bewusst noch kein Kandidatenfeld. Sie wird erst ergänzt, sobald eine belastbare Segmentierungsquelle vorliegt.
- **Sample**: Cutpoints liegen auf dem normalisierten Render-Raster (standardmäßig 44.100 Hz), nicht auf der originalen Eingangs-Sample-Rate.
- **Übergangslänge**: ist kanonisch `transition_length_bars`. Unterstützt bleiben positive Taktzahlen; der aktuelle High-Power-Workflow verwendet standardmäßig 2 oder 4 Takte. `transition_length_beats` wird aus dem Taktfenster abgeleitet und an die aktuellen Fade-Renderer übergeben.

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
| `source_grid`, `target_grid` | Herkunft, Fallbackstatus, Backend-Version und Confidence des jeweiligen Taktrasters gemäß `ANALYSIS_PROTOCOL.md` |
| `filter_status` | Für ausgegebene Kandidaten immer `accepted` |

Das Python-Datenmodell bietet `to_dict()` für ein späteres JSON-Manifest. Die Abwesenheit eines Kandidaten wird nicht stillschweigend behandelt: `CandidateGenerationResult.rejections` enthält für jeden harten Filter einen maschinenlesbaren Code und eine Erklärung.

## Generator `bar_grid_v1`

Der Generator bildet standardmäßig **alle** nutzbaren Taktgrenzen von Song A mit allen nutzbaren Taktgrenzen von Song B. So kann das Ranking natürliche Drop-Enden in A und spätere Drop-/Refrain-Anfänge in B erreichen. `source_boundary_count` begrenzt optional auf die letzten N Source-Grenzen; `target_boundary_count` begrenzt optional auf die ersten N Target-Grenzen. Der aktuelle Default erzeugt Varianten mit 2 und 4 Takten.

Die Fade-Renderer ab Rendering-Vertrag Version 2 mischen Source-Audio **nach** dem Source-Cutpoint mit Target-Audio **vor** dem Target-Cutpoint. Deshalb müssen vor und nach beiden Grenzen genügend vollständige Takte liegen: vor A wird Drop A bewertet, nach A liegt der Source-Auslauf; vor B liegt der Target-Vorlauf, nach B wird Drop B bewertet.

Harte Filter in Version 1:

1. bei der Default-Policy `approximate_grid_policy = reject` nachweislich erkannte Raster (`fallback_used = false`); approximative und historisch/extern unbekannte Raster werden abgelehnt,
2. vollständige, steigende Beat-/Downbeat-Metadaten mit konsistenten Takten im Übergangsfenster,
3. vollständige Pre- und Post-Roll-Fenster auf beiden Songs für jede angeforderte Taktlänge,
4. identische abgeleitete Beatanzahl auf beiden Seiten,
5. symmetrische relative Tempoabweichung höchstens 15 % (konfigurierbar).

`approximate_grid_policy = allow` erlaubt Fallback- und unbekannte Raster nur
nach explizitem Opt-in. Die Herkunft bleibt trotzdem in
`CandidateGenerationResult.source_grid/target_grid` und in jedem Kandidaten
gespeichert. Vollständige Tupel allein gelten nicht mehr als
Downbeat-Erkennungsnachweis. Alte Analyse-Caches ohne Provenienz werden als
`legacy_cache_unknown` behandelt und unter `reject` abgewiesen.

Energie und Harmonie bleiben weiche Ranking-Komponenten; Vocal-Overlap, Phrasen- und Segmentinformationen fehlen weiterhin. „High Power“ wird daher nicht als harter Generatorfilter vorgetäuscht, sondern relativ zur Energieverteilung jedes Tracks im dokumentierten Ranking gemessen.

## Programmatic API

```python
from src.pipeline import generate_transition_candidates

result = generate_transition_candidates("musik/song_a.wav", "musik/song_b.wav")
for candidate in result.candidates:
    print(candidate.candidate_id, candidate.transition_length_beats)
```

Der CLI-Schalter `--approximate-grid-policy allow` ist für bewusst
approximative Experimente verfügbar; der Default bleibt `reject`.

Die Funktion nutzt dieselbe Analyse und dieselbe Sample-Raten-Normalisierung wie `render_transition()`. Batch-Export und Manifest-Datei sind der folgende, bewusst getrennte Meilenstein.
