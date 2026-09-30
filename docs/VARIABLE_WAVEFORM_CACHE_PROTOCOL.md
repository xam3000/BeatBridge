# Variable-v2 Waveform-Cache- und Alignment-Vertrag

_Vertragsversion: `local_grid_target_to_source_v1`, eingeführt am 2026-08-21._

Dieser Vertrag ist additiv zu allen v1-/Vocal-v2-Bridge-Caches. Er gilt für
`output/ml_cache/variable_bridge_waveform_v2` und wird nicht durch eine alte
Cacheversion gelesen oder überschrieben.

## Autorität und Fenster

Die Source-Zeitachse ist die Dauerautorität: Das Target wird musikalisch auf
den Source-Übergang angepasst. Für eine Länge `L` gelten in 4/4 exakt
`beats = 4*L` und `T = 2*beats` Halbbeat-Schritte. Die Source ist das
Postroll-Fenster `[source_cue, source_cue+T]`; das Target ist das Preroll-
Fenster `[target_cue-T, target_cue]`. Start-, Ende- und Cue-Grenzen werden aus
den gespeicherten Feature-Cache-Gridgrenzen gelesen, nicht aus BPM-Näherungen.

Die lokale Ausgabelängenratio ist

```text
local_stretch_ratio = source_grid_duration / target_grid_duration
target_tempo_factor = target_grid_duration / source_grid_duration
```

Die globale Provenienz bleibt zusätzlich erhalten:
`global_bpm_ratio = target_bpm / source_bpm` und
`global_duration_ratio = 1 / global_bpm_ratio`. Die Differenz zwischen lokaler
und globaler Daueratio ist ein Diagnosewert, kein Filter, der die lokale
Gridmessung ersetzt.

## Transformationen

1. Source-Mix und Source-Vocal werden am selben Source-Gridfenster geschnitten.
2. Target-Mix und Target-Vocal werden am selben Target-Gridfenster geschnitten.
3. Beide Target-Fenster erhalten denselben tonhöhenerhaltenden Rubber-Band-
   Stretch mit `target_tempo_factor`; es wird kein gewöhnliches Resampling zur
   musikalischen Zeitkorrektur verwendet.
4. Nach dem Stretch werden alle vier Waveforms mit derselben technischen
   Sample-Raten-Konvertierung auf 11.025 Hz gebracht.
5. Eine verbleibende Backend-/Resampling-Abweichung darf höchstens zwei Samples
   am 44,1-kHz-Rendergitter betragen (`rounding_correction_version=1`). Die
   Source-Korrektur erfolgt ausschließlich am Ende, die Target-Korrektur
   ausschließlich am Anfang; Mix und Vocal erhalten jeweils dieselbe
   Korrektur. Größere Abweichungen werden mit vollständiger Diagnose abgelehnt.

Die vier veröffentlichten Arrays sind immer `float32`, Stereo in der festen
Kanalreihenfolge `[left, right]`, 11.025 Hz und exakt gleich geformt. Endliche
Werte und Array-/Payload-SHAs werden beim Cache-Hit erneut geprüft.

## Provenienz und Unveränderlichkeit

Jeder Eintrag bindet Dataset-ID, Dataset-Manifest-SHA, Example-/Candidate-ID,
Länge, Sequenzlänge und diesen Vertrag. Die Manifestdaten enthalten außerdem
Source-/Target-Grid-Hashes, rohe Fenstergrenzen und Samplelängen, lokale und
globale Ratios, Tempo-Backend und versionierten Backendvertrag, kanonische
Ausgabelänge, Rundungskorrektur, Audio-SHAs, Stem-Payload-SHAs und Payload-
SHA. Nicht verifizierte oder als Fallback markierte Gridprovenienz wird nicht
nachträglich zugelassen.

Einträge werden in einem temporären Verzeichnis vollständig geschrieben und
atomar veröffentlicht. Fehlende, korrupte oder widersprüchliche Einträge sind
Fehler; sie werden nicht still repariert. Der Trainingsloader verwendet
standardmäßig nur vollständige Cache-Hits und öffnet ausschließlich Train und
Validation. Der Testsplit wird weder materialisiert noch geladen.

## Versiegelter Cacheindex und Trainingsbindung (additiv, 2026-09-23)

Nach jeder expliziten Materialisierung schreibt der v2-Pfad zusätzlich ein
unveränderliches `index.json`. Es enthält nur die tatsächlich erzeugten
Train-/Validation-Einträge, sortiert nach `example_id`, und bindet für jeden
Eintrag Cache-ID, Split, Länge, Entry-Manifest-SHA und `waveforms.npz`-SHA.
Der Index bindet außerdem Datasetmanifest-SHA und Cache-Rootmanifest-SHA; sein
kanonischer Payload-Hash steht im Index, sein Datei-SHA im
Materialisierungsbericht.

Der reale `train-variable-tcn-bilstm`-Wrapper verlangt diesen Index, prüft
Root, alle referenzierten Entry-Manifeste und Payloads vor dem Training und
nimmt Index- und Rootmanifest-SHA in Runmanifest und Checkpoints auf. Ein
fehlendes Beispiel, ein abweichender Hash oder ein Testsplitzugriff bricht
fail-closed ab. Der Wrapper schreibt anschließend `io_audit.json` mit den
geöffneten Splits und `test_reads=0` und bindet die Datei im Runmanifest.
