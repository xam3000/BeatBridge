# Rendering-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-17._

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
| `format_version` | Aktuell `1` |
| `audio` | NumPy-Array in der Form `(channels, samples)` |
| `sample_rate` | Sample-Rate des Ergebnis-Audios |
| `renderer` | Verwendete Rendering-Baseline |

## Audio-Invarianten

- Standard-Sample-Rate intern und im Ergebnis: **44.100 Hz**.
- Standard-Kanalzahl: **Stereo**. Mono-Eingaben werden auf zwei Kanäle dupliziert.
- Abweichende Eingangs-Sample-Raten werden vor dem Rendering resampelt; Beat-Positionen werden auf dasselbe Sample-Raster skaliert.
- Cutpoints sind Sample-Positionen auf dem normalisierten Ziel-Sample-Raster, bevor eine optionale Tempoanpassung angewendet wird.
- Originaldateien werden ausschließlich gelesen und nicht verändert.

## Renderer-Namen

| Name | Verhalten |
|---|---|
| `simple` | Harter Schnitt auf der ausgerichteten Taktgrenze |
| `fade` | Linearer Crossfade |
| `equal_power` | Equal-Power-Crossfade mit konstantem quadrierten Gain |
| `tempo_fade` | Tonhöhenerhaltende Tempoanpassung von Song B auf BPM von Song A, danach linearer Crossfade |

Alle Fade-Renderer verwenden standardmäßig acht Beats. Die Länge kann über `fade_beats` verändert werden.
