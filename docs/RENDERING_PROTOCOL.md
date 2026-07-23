# Rendering-Protokoll

_Vertragsversion: 4, eingeführt am 2026-07-22. Version 3 wurde am 2026-07-22 eingeführt; Version 2 am 2026-07-21; Version 1 am 2026-07-17._

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
| `format_version` | Aktuell `4` |
| `audio` | NumPy-Array in der Form `(channels, samples)` |
| `sample_rate` | Sample-Rate des Ergebnis-Audios |
| `renderer` | Verwendete Rendering-Baseline |
| `transition_start_sample` | Beginn der tatsächlichen Transition relativ zum zurückgegebenen Audio |
| `transition_end_sample` | Ende der tatsächlichen Transition relativ zum zurückgegebenen Audio; beim Hard Cut identisch zum Beginn |

## Audio-Invarianten

- Standard-Sample-Rate intern und im Ergebnis: **44.100 Hz**.
- Standard-Kanalzahl: **Stereo**. Mono-Eingaben werden auf zwei Kanäle dupliziert.
- Abweichende Eingangs-Sample-Raten werden vor dem Rendering resampelt; Beat-Positionen werden auf dasselbe Sample-Raster skaliert.
- Cutpoints sind Sample-Positionen auf dem normalisierten Ziel-Sample-Raster, bevor Song B für jeden Renderer tonhöhenerhaltend auf das BPM von Song A angepasst wird. Cutpoint und Beat-Raster von Song B werden dabei mit skaliert.
- Originaldateien werden ausschließlich gelesen und nicht verändert.
- Renderer geben standardmäßig eine Vorschau mit fünf Sekunden vor und zwölf Sekunden nach dem ausgerichteten Source-Cutpoint zurück. Damit enthalten Batch-Dateien den Übergang samt Kontext statt vollständiger Songs. Die API akzeptiert `preview_seconds_before=None` und `preview_seconds_after=None` für einen vollständigen Render.

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
