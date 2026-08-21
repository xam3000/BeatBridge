# Rendering-Protokoll

_Vertragsversion: 5, eingeführt am 2026-07-30. Version 4 und 3 wurden am 2026-07-22 eingeführt; Version 2 am 2026-07-21; Version 1 am 2026-07-17._

Dieses Dokument beschreibt die stabile Grenze der programmatisch aufrufbaren Rendering-Pipeline. Änderungen an Version 1 erfolgen nur additiv; inkompatible Änderungen benötigen eine neue `format_version`.

## Einstiegspunkt

```python
from src.pipeline import render_transition

result = render_transition(
    song1,
    song2,
    cutpoint1,
    cutpoint2,
    renderer="equal_power",
)
```

`render_transition()` gibt ein `RenderResult` mit folgenden Feldern zurück:

| Feld | Bedeutung |
|---|---|
| `format_version` | Aktuell `5` |
| `audio` | NumPy-Array in der Form `(channels, samples)` |
| `sample_rate` | Sample-Rate des Ergebnis-Audios |
| `renderer` | Verwendete Rendering-Baseline |
| `tempo_backend` | Tatsächlich verwendeter Tempo-Pfad: `ffmpeg_librubberband`, `rubberband_cli_r3`, `not_needed` oder bei einem explizit injizierten Fremd-Backend dessen Klassenname |
| `transition_start_sample` | Beginn der tatsächlichen Transition relativ zum zurückgegebenen Audio |
| `transition_end_sample` | Ende der tatsächlichen Transition relativ zum zurückgegebenen Audio; beim Hard Cut identisch zum Beginn |

## Audio-Invarianten

- Standard-Sample-Rate intern und im Ergebnis: **44.100 Hz**.
- Standard-Kanalzahl: **Stereo**. Mono-Eingaben werden auf zwei Kanäle dupliziert.
- Abweichende Eingangs-Sample-Raten werden vor dem Rendering resampelt; Beat-Positionen werden auf dasselbe Sample-Raster skaliert.
- Cutpoints sind Sample-Positionen auf dem normalisierten Ziel-Sample-Raster, bevor Song B für jeden Renderer tonhöhenerhaltend auf das BPM von Song A angepasst wird. Cutpoint und Beat-Raster von Song B werden dabei mit skaliert.
- Originaldateien werden ausschließlich gelesen und nicht verändert.
- Renderer geben standardmäßig eine Vorschau mit fünf Sekunden vor und zwölf Sekunden nach dem ausgerichteten Source-Cutpoint zurück. Damit enthalten Batch-Dateien den Übergang samt Kontext statt vollständiger Songs. Die API akzeptiert `preview_seconds_before=None` und `preview_seconds_after=None` für einen vollständigen Render.

## Tempo-Backend ab Version 5

Song B wird tonhöhenerhaltend mit Rubber Band auf das BPM von Song A
angepasst. Die Backend-Reihenfolge ist fest:

1. FFmpeg mit einkompiliertem `rubberband`-Filter,
2. bei fehlendem Programm, fehlendem Filter oder Verarbeitungsfehler das
   eigenständige `rubberband`-CLI mit der hochwertigen R3-Engine (`-3`),
3. Fehler mit beiden Schrittursachen, wenn kein Backend erfolgreich ist.

FFmpeg verarbeitet Stereo gemeinsam (`channels=together`). Ein- und Ausgabe
der externen Backend-Grenze sind 32-Bit-Float-WAVs; erst der spätere
Dateiexport bestimmt das endgültige WAV-Subtype. Die Pipeline passt das
Backend-Ergebnis deterministisch an `round(input_samples / tempo_factor)` an,
damit Cutpoints und das skalierte Beat-Raster auf derselben Sample-Geometrie
bleiben. Bei praktisch identischem Tempo startet kein externer Prozess und
`tempo_backend` ist `not_needed`.

Version 4 und ältere Batches nutzten den vereinfachten
`librosa.effects.time_stretch`-Phase-Vocoder. Historische WAVs und Manifeste
bleiben unverändert.

## Renderer-Namen

| Name | Verhalten |
|---|---|
| `simple` | Tempoangepasster harter Schnitt auf der ausgerichteten Taktgrenze |
| `fade` | Tempoangepasster linearer Bridge-Crossfade zwischen Source-Postroll und Target-Preroll |
| `equal_power` | Tempoangepasster Equal-Power-Bridge-Crossfade mit konstantem quadrierten Gain |
| `tempo_fade` | Kompatibilitätsalias für den tempoangepassten linearen Bridge-Crossfade (`fade`) |

## Bridge-Semantik ab Version 2

Die Fade-Renderer interpretieren die Cutpoints als musikalische Grenzen:

```text
Drop A | Source-Auslauf  ×  Target-Vorlauf | Drop B
       ^ Source-Cut                         ^ Target-Cut
```

- Der Prefix enthält Song A vollständig bis zum Source-Cutpoint.
- Das Mischfenster kombiniert ausschließlich Audio **nach** dem Source-Cut mit Audio **vor** dem Target-Cut.
- Der Suffix beginnt exakt am Target-Cutpoint mit Song B.
- Damit liegen der High-Power-Abschnitt von A und der High-Power-Abschnitt von B außerhalb des überlappenden Fensters.
- Bei unterschiedlichen Beatdauern bestimmt das kürzere verfügbare Übergangsfenster die Samplelänge; die musikalischen Cut-Grenzen bleiben erhalten.

Alle Fade-Renderer verwenden bei direktem API-Aufruf standardmäßig acht Beats. Automatische Kandidaten leiten aktuell 2 oder 4 Takte in die entsprechende Beatanzahl um. Version 1 mischte dagegen die Fenster unmittelbar vor beiden Cutpoints und ist für neue Batches nicht mehr maßgeblich.

## Additiver Exaktdauerpfad für Candidate-v2

Variable Candidate-v2-Exporte verwenden additiv Rendering-Format 6. Die
Fade- und Equal-Power-Renderer erhalten die aus dem tatsächlichen Taktfenster
abgeleitete `transition_length_beats`-Zahl und prüfen nach Alignment die
Source- und Target-Bridge-Sampleanzahl. Beide Seiten müssen exakt gleich lang
sein; der v2-Pfad kürzt nicht still auf die kleinere Seite. Die Rückgabe führt
zusätzlich `transition_length_bars` und `transition_length_beats`.

Der v2-Einstieg validiert die L/Beat-Geometrie bereits vor dem Laden der
Audiodateien. Nach der bestehenden strikten Sampleprüfung werden Kandidaten mit
unterschiedlicher Source-/Target-Bridgeabdeckung verworfen; diese Fälle sind
keine alte v1-„kürzeres Fenster“-Semantik und werden nicht still angepasst.

Der bestehende Rendering-Format-5-Pfad behält seine historische
„kürzeres verfügbares Fenster bestimmt die Samplelänge“-Semantik. Dadurch
bleiben alte direkte Renderaufrufe, Batch-Manifeste und WAV-Artefakte
kompatibel. Nur Candidate-v2-Batchvarianten verwenden den Exaktdauerpfad.
