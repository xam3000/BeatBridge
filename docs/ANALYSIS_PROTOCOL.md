# Beat-/Bar-Analyse-Protokoll

_Analyseformat 1, eingeführt am 2026-08-12._

Dieses Protokoll trennt Beat-/Taktkoordinaten von ihrer Herkunft. Ein formal
vollständiges Raster ist damit kein impliziter Nachweis mehr, dass seine
Downbeats tatsächlich erkannt wurden. Änderungen an Format 1 erfolgen nur
additiv.

## Ergebnisformat

`PreAnalysis` liefert ein `AnalysisResult` mit:

- `bpm`,
- `beat_frames` als bestehende Tupel `(sample, count_in_bar, beats_in_bar)`,
- `grid_metadata` als `BeatGridMetadata`.

Zweiwertiges Unpacking (`bpm, beat_frames = analysis(path)`) bleibt
kompatibel. Neue Consumer müssen zusätzlich `result.grid_metadata` auswerten,
wenn die Vertrauenswürdigkeit der Taktgrenzen relevant ist.
`render_transition()` gibt dieselbe Herkunft additiv als
`RenderResult.source_grid/target_grid` weiter; Rendering darf approximative
Raster weiterhin technisch verwenden, während die Kandidaten-Policy deren
Zulässigkeit entscheidet.

`BeatGridMetadata` enthält:

| Feld | Bedeutung |
|---|---|
| `format_version` | Aktuell `1` |
| `grid_source` | Erkennungs-, Fallback- oder Legacy-Herkunft |
| `fallback_used` | `false` erkannt, `true` approximiert, `null` historisch/unbekannt |
| `backend_version` | Analysebackend; für aufTAKT nach Möglichkeit einschließlich Binary-SHA-256 (sonst `unreported`), für den Fallback dessen Version und librosa-Version |
| `confidence` | `0..1`; beim aufTAKT/librosa-Merge mittlere normierte Matchnähe, beim Fallback `0`, bei Legacy/extern unbekannt `null` |

Aktuelle `grid_source`-Werte sind:

- `auftakt_matched_to_librosa`: aufTAKT-Taktpositionen wurden vollständig auf
  librosa-Beats abgebildet;
- `fallback_from_detected_beats`: der erste vorhandene Beat wurde als
  Downbeat gesetzt und anschließend ein 4/4-Raster gezählt;
- `fallback_from_bpm`: ohne Beats wurde ein gleichmäßiges BPM-basiertes
  4/4-Raster erzeugt;
- `legacy_cache_unknown`: alter Cache ohne Provenienz; erkannt und
  approximiert sind rückwirkend nicht unterscheidbar;
- `external_unknown`: externer Analyse-Callable oder direkt übergebenes Raster
  ohne Provenienzvertrag.

Die Confidence ist eine versionierte technische Matchheuristik und keine
kalibrierte Wahrscheinlichkeit für einen musikalisch korrekten Downbeat.

## Cacheformat

`00_pre_analysis.txt` bleibt für alte Leser unverändert. Additiv liegt im
gleichen Trackordner:

```text
02_grid_metadata.json
```

Die Sidecar-Datei enthält exakt die fünf Felder von `BeatGridMetadata` und
wird atomar geschrieben. Wird ein gültiger Altcache ohne Sidecar gelesen,
wird `legacy_cache_unknown`, `fallback_used = null` gespeichert. Der Altcache
wird ausdrücklich nicht nachträglich als erkannte oder approximierte Analyse
klassifiziert.

## Downstream-Policy

`CandidateGenerationConfig.approximate_grid_policy` ist `reject|allow` und
standardmäßig `reject`:

- `reject` akzeptiert nur `fallback_used = false`; Fallback sowie unbekannte
  Legacy-/External-Herkunft erzeugen auditable Rejections.
- `allow` ist ein expliziter Opt-in für approximative und unbekannte Raster.

`CandidateGenerationResult` und jeder neue Kandidat speichern
`source_grid`, `target_grid` sowie die verwendete Policy. Dadurch bleibt die
Herkunft in Batch-, Dataset- und daraus erzeugten Studienartefakten sichtbar.
Historische Artefakte werden nicht umgedeutet oder rückwirkend verändert.

Volltrack-Featurecaches speichern dieselben Metadaten als
`beat_grid_metadata`; sie sind Bestandteil des Cache-Keys. Dasselbe
Koordinatenraster mit anderer oder nun bekannter Herkunft wird daher nicht mit
einem alten Provenienzzustand wiederverwendet.
