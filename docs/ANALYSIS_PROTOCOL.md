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
| `backend_version` | Analysebackend; für aufTAKT nach Möglichkeit einschließlich Binary-SHA-256 (sonst `unavailable`), für den Fallback dessen Version und librosa-Version |
| `confidence` | `0..1`; beim aufTAKT/librosa-Merge mittlere normierte Matchnähe, beim Fallback `0`, bei Legacy/extern unbekannt `null` |
| `analysis_id` | Hash des vollständigen Analysevertrags; bei Legacy/extern unbekannt `null` |
| `beat_grid_sha256` | SHA-256 der geordneten Beat-/Taktwerte |

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

## Cacheformat 2

Neue Analysen verwenden seit 2026-08-12 einen inhalts- und
analysevertragsadressierten Cache:

```text
output/pre_analysis/
└── v2/
    └── <vollständiger Audio-SHA-256>/
        └── <analysis_id>/
            └── analysis.json
```

Der Track-Stem ist kein Bestandteil der Identität. Gleichnamige Dateien mit
verschiedenem Inhalt kollidieren deshalb nicht; byteidentische Dateien unter
verschiedenen Namen dürfen denselben Eintrag verwenden.

`analysis_id` ist der SHA-256 über den vollständigen Analysevertrag:

- `beatbridge_pre_analysis_v2`,
- `librosa.beat.beat_track` samt librosa-Version und relevanten Parametern,
- `aufTAKTCl` samt vollständigem Binary-SHA-256 und Dateigröße; eine nicht
  vorhandene Produktversion wird als `null` gespeichert und nicht geraten,
- Merge-Algorithmus und maximale Matchdistanz,
- Fallbackalgorithmus und angenommene Beats pro Takt.

Ein Wechsel von Algorithmus, librosa-Version, aufTAKT-Binary oder Parametern
erzeugt einen neuen Cacheeintrag. `analysis.json` speichert außerdem
Audiohash/-größe, BPM, Beatwerte, vollständige Grid-Provenienz und die
Diskrepanzdiagnostik. Es ist die einzige Autorität dieses Cacheeintrags und
wird über eine temporäre Geschwisterdatei plus `os.replace` atomar publiziert.

Format-1-Caches unter `<track-stem>/00_pre_analysis.txt` und deren optionale
Sidecars bleiben read-only lesbar. Ohne belastbare Provenienz werden sie als
`legacy_cache_unknown`, `fallback_used = null`, `analysis_id = null`
behandelt. Sie werden weder umgeschrieben noch automatisch als Format 2
ausgegeben. Ein kollidierender Legacy-Stem wird nur verwendet, wenn sein
gespeicherter Audiohash zur angeforderten Datei passt.

Die Herkunfts- und Lizenzlage der lokalen aufTAKT-Binary ist getrennt in
`EXTERNAL_TOOLS.md` und `config/auftakt_binary_provenance.json` dokumentiert.

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
