# Differenzierbare Mixing-Controls

_Aktuelle Vertragsversion: 2, eingeführt am 2026-07-29. Version 1 wurde am
2026-07-29 eingeführt._

Dieses Dokument beschreibt den ersten lernbaren BeatBridge-Kern
`differentiable_control_v1`. Änderungen an Version 1 erfolgen nur additiv;
inkompatible Änderungen benötigen eine neue `format_version` und einen neuen
Namen.

## Ziel und Abgrenzung

Das ML-Modell erhält ausschließlich vorab berechnete, beat-synchrone Features.
Es erzeugt keine Audiosamples, sondern zeitdiskrete Mixing-Controls. Während
des Trainings wendet ein separater differenzierbarer Renderer diese Controls
auf die Original-Waveforms an. Eine eingefrorene, differenzierbare
Übergangsmetrik liefert den Loss; Ground-Truth-Kontrollkurven sind nicht
erforderlich.

```text
Features A/B
  → Control-Modell
  → Mixing-Controls
  → differenzierbarer Renderer mit Waveforms A/B
  → gerenderte Bridge
  → eingefrorenes Objective
```

Die Waveforms sind damit Teil des Trainingspfads, aber kein Input des
Control-Modells.

## Musikalische Fenster

Version 1 verwendet vier Takte im 4/4-Metrum:

- Source A: vier Takte nach dem vom Nutzer gesetzten Ende von Drop A,
- Target B: vier Takte vor dem vom Nutzer gesetzten Anfang von Drop B,
- 32 Kontrollpunkte pro Kurve, also ein Kontrollpunkt pro halbem Beat.

Diese Fenster entsprechen der Bridge-Semantik des Rendering-Protokolls ab
Version 2. Beide Eingangstensoren müssen bereits tempo- und samplegenau
ausgerichtet sein und dieselbe Länge besitzen.

## Controls

Der Minimalvertrag enthält genau zwei normalisierte Kurven:

| Control | Bereich | Bedeutung |
|---|---:|---|
| `mix_position` | `[0, 1]` | Full-/High-Band-Übergabe von A nach B |
| `low_end_position` | `[0, 1]` | Low-End-Übergabe von A nach B |

Aus jeder Position `p` leitet der Renderer ein komplementäres
Equal-Power-Paar ab:

```text
gain_A = cos(p · π/2)
gain_B = sin(p · π/2)
gain_A² + gain_B² = 1
```

Unabhängige A-/B-Gains sind bewusst nicht Teil des Modelloutputs. Der Vertrag
verhindert dadurch triviale Lösungen, die beide Tracks gleichzeitig
verstärken oder stummschalten.

Die Endpunkte der direkt optimierbaren Kurven sind fest:

```text
mix_position[0] = low_end_position[0] = 0
mix_position[-1] = low_end_position[-1] = 1
```

Ab Version 2 sind beide Kurven zusätzlich **streng monoton steigend**. Das
Modell optimiert positive Inkremente über `softmax`; deren kumulierte Summe
bildet die Control-Kurve. Dadurch kann Song A nach einer Absenkung nicht kurz
vor dem Ende erneut hörbar werden. Version 1 verwendete unabhängige innere
Kontrollpunkte und erlaubte trotz weicher Monotoniestrafe hörbare Rückläufe.

## Tensorformen und Einstiegspunkt

```python
from src.control import DifferentiableTwoBandRenderer

renderer = DifferentiableTwoBandRenderer(
    sample_rate=44_100,
    lowpass_cutoff_hz=180.0,
)
result = renderer(
    source_audio,       # (B, C, N) oder (C, N)
    target_audio,       # (B, C, N) oder (C, N)
    mix_position,       # (B, T) oder (T,)
    low_end_position,   # (B, T) oder (T,)
)
```

Der Renderer interpoliert die Kontrollpunkte linear auf Sampleebene. Ein
fester, linearphasiger FIR-Tiefpass trennt Low- und High-Band. Das High-Band
folgt `mix_position`, das Low-Band `low_end_position`.

## Objective Version 1

`DifferentiableTransitionObjective` kombiniert ausschließlich
differenzierbare Terme:

- `energy_shape`: U-förmiger Energieverlauf zwischen beiden Drops,
- `boundary`: RMS-Anschluss an Source A und Target B,
- `control_smoothness`: kleine Änderungen zwischen Kontrollpunkten,
- `monotonicity`: Strafe für rückwärts laufende Übergaben,
- `clipping`: Strafe für Beträge oberhalb von 1.

Die Objective-Komponenten sind eine technische Lernsonde, noch keine
perzeptuell validierte Qualitätsmetrik. Vor einem Training auf größeren Daten
müssen ihre Rangfolgen gegen menschliche Hörurteile geprüft werden.

## Direkte Optimierung als Pflichtsonde

Vor einem neuronalen Netz werden die beiden Kurven eines einzelnen
Übergangs direkt per Gradient Descent optimiert:

```python
from src.control import optimize_control_curves

optimization = optimize_control_curves(
    source_audio,
    target_audio,
    renderer=renderer,
)
```

Nur wenn diese Optimierung den Objective-Wert reproduzierbar verbessert und
die Ergebnisse im Hörtest plausibel bleiben, wird darauf ein Feature→Control-
Modell aufgebaut. Die erste Modellbaseline ist ein MLP; TCN/BiLSTM folgen erst
danach.

## Reale Vergleichsexporte

`src.evaluation.control_probe` erzeugt aus einem bestehenden Multi-Song-Batch
einen unveränderlichen Vergleichsordner. Die Auswahl erfolgt in Version 1
greedy:

1. nur Kandidaten mit vier Takten,
2. höchster vorhandener `rendered_transition_baseline_v1`-Score zuerst,
3. kein Track wird innerhalb der Auswahl erneut verwendet.

Pro Songpaar werden zwei WAVs mit identischem Kontext und gemeinsamer
Peak-Absenkung exportiert:

```text
01_baseline_equal_power.wav
02_optimized_proxy.wav
```

`manifest.json` hat `format_version = 1` und enthält Quellbatch,
Kandidaten-ID, Track-Hashes, Cutpoints, vorhandenen Render-Score,
Optimierungskonfiguration, Loss-Komponenten, Kontrollpunkte, technische
WAV-Metadaten und das Ranking beider Exporte durch die historische
Render-Metrik. Bestehende Batch-Artefakte werden ausschließlich gelesen.

Für die perzeptuelle Validierung verpackt
`src.evaluation.blind_control_study` diese Exporte als A/B-Dateien, trennt den
Antwortschlüssel vom öffentlichen Manifest und erzeugt ein persistentes
Ratings-Sidecar. Der vollständige Vertrag steht in
`CONTROL_STUDY_PROTOCOL.md`.

## Bekannte Grenzen

- Der FIR-Crossover ist eine technische Baseline, kein produktionsreifer DJ-EQ.
- Energie- und Grenzterme können musikalische Qualität nicht vollständig
  abbilden und sind anfällig für Metric Hacking.
- Harmonie, Rhythmus, Vocals, Mid-/High-Ownership und gelernte
  Repräsentationen fehlen in Version 1.
- Vier Takte und 4/4-Metrum sind zunächst feste Forschungsannahmen.
