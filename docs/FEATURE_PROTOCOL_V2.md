# Feature Protocol 2 — variable Übergangslängen

_Vertragsversion 2, additive Ergänzung zu `FEATURE_PROTOCOL.md`, eingeführt am
2026-08-20._

Feature Protocol 1 bleibt unverändert lesbar und testbar. Protocol 2 verwendet
für die extern angeforderte Länge ausschließlich `2`, `4`, `6` oder `8` Takte
im ersten 4/4-Halbbeat-Vertrag:

| Takte | Beats | Halbbeat-Schritte `T` |
|---:|---:|---:|
| 2 | 8 | 16 |
| 4 | 16 | 32 |
| 6 | 24 | 48 |
| 8 | 32 | 64 |

`T` wird aus `transition_length_bars` abgeleitet und nicht aus einer
beobachteten Arrayform geraten. Ein v2-Fenster bestätigt immer gleichzeitig
Takte, Beats und Sequenzlänge.

## Tensorvertrag

```text
features_a:       float32 (T, 54)
features_b:       float32 (T, 54)
global_features:  float32 (16,)
length_condition: float32 (1,)  # transition_length_bars / 8
```

Die 54 Kanäle behalten Reihenfolge, Namen, Wertebereiche und fachliche
Bedeutung aus Protocol 1. Auch der 16-dimensionale globale Vektor bleibt
unverändert; die Längenkonditionierung wird nicht in ihn hineingeschoben.
`length_condition` ist ein sichtbares, separat validiertes Feld.

`transition_position` ist die lokale Mitte jedes tatsächlichen Halbbeat-Bins:
`(i + 0.5) / T`. Die erste und letzte Position sind damit `0.5/T` und
`(T-0.5)/T`. Source A beginnt am Source-Cue mit dem Postroll, Target B endet
am Target-Cue mit dem Preroll. Unvollständige Fenster werden abgewiesen; es
gibt kein Padding im v2-Basispfad.

Der Analysekontext bleibt separat und zunächst 4 Takte vor plus 4 Takte nach
dem Cue. `context_coverage` darf nicht stillschweigend mit `T` skaliert werden.

## Python-Vertrag

```python
from src.features import (
    geometry_for_length,
    validate_variable_feature_array,
)

geometry = geometry_for_length(6)
assert geometry.sequence_length == 48
validate_variable_feature_array(
    features_a,
    transition_length_bars=6,
    sequence_length=48,
)
```

`TrackFeatureArtifact.model_window()` akzeptiert additive optionale
`transition_length_bars`-/`sequence_length`-Parameter. Ohne diese Parameter
bleibt der alte Aufruf exakt ein 32-Schritt-Fenster. Der neue
`extract_variable_track_window()`-Einstieg verlangt die Länge explizit.

## Provenienz und Normalisierung

Die v2-Fenster behalten Audio-SHA, Grid-, Extractor-, BPM-, Cache- und
Normalisierungsprovenienz aus Protocol 1. Flux und Onset werden weiterhin nur
mit Statistiken aus tatsächlich verwendeten Trainingsartefakten normalisiert;
Validation und Test verändern die Statistik nicht. Neue v2-Datasetmanifeste
führen Protocol-, Extractor-, Längen-, `T`- und Split-Map-Hash explizit.

Der v1-Volltrackcache bleibt read-only wiederverwendbar, sofern seine
Provenienz zum Auftrag passt. Ein v2-Fenster wird aber nur über den expliziten
Längenvertrag gelesen und validiert.
