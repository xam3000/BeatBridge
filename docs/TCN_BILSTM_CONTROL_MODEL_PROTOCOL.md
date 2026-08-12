# TCN/BiLSTM-Transition-Control-Modell

_Modellvertrag 3, additive Architektursonde, eingeführt am 2026-08-12._

Dieses Dokument beschreibt die größere Architektur nach den kleinen MLP-
Baselines. Die v1-/v2-Checkpoints, Trainingsrunner und Hörstudien bleiben
unverändert. Ein produktiver selbstüberwachter Trainingsrunner für dieses
Modell ist ein nachgelagerter Arbeitsschritt.

## 1. Eingaben

Das Modell verwendet den bestehenden Featurevertrag:

```text
features_a:      float32 (B, 32, 54)
features_b:      float32 (B, 32, 54)
global_features: float32 (B, 16)
```

Die 32 Zeitschritte entsprechen den Halbbeat-Positionen der vier
Übergangstakte. Audiosamples sind keine direkten Modelleingaben.

## 2. Architektur

Die Encodergewichte werden für Track A und Track B geteilt:

```text
A/B (B, 32, 54)
  → Conv1d 54 → 64
  → Conv1d 64 → 128
  → dilated Conv1d 128 → 128
  → (B, 32, 128)
```

Danach werden die beiden kodierten Sequenzen paarweise fusioniert:

```text
[A, B, A - B, A * B] → (B, 32, 512) → Linear(512, 256)
```

Die globalen Paarmerkmale werden separat auf 256 Dimensionen projiziert und
zeitlich auf alle 32 Schritte addiert. Ein zweilagiger bidirektionaler LSTM
verarbeitet die Sequenz:

```text
input_size=256
hidden_size=128
num_layers=2
bidirectional=True
→ (B, 32, 256)
```

Der Controller erzeugt zehn Werte pro Zeitschritt:

```text
gain_A, gain_B,
eq_low_A, eq_low_B,
eq_mid_A, eq_mid_B,
eq_high_A, eq_high_B,
low_end_ownership,
vocal_ducking
```

Die öffentliche Ausgabe hat damit die Form `(B, 32, 10)`. Eine Sigmoid-
Transformation beschränkt die aktuellen Controls auf `[0, 1]`.

## 3. Bewusste Grenze der ersten Implementierung

Die Architektur gibt zunächst zehn bounded Controls aus. Monotonie,
komplementäre Gain-Kurven, Frequenzband-Semantik und die genaue Abbildung auf
den differenzierbaren Renderer werden in einem nachfolgenden Control-Adapter
beziehungsweise Objective-Vertrag festgelegt. Das verhindert, dass die neue
Architektur stillschweigend die bereits validierten v1-/v2-Controlverträge
ändert.

## 4. Python-Einstieg

```python
from src.ml import TCNBiLSTMTransitionControl

model = TCNBiLSTMTransitionControl()
output = model(features_a, features_b, global_features)
assert output.controls.shape == (batch_size, 32, 10)
```

Der Modellname ist `tcn_bilstm_transition_control_v1`; die interne
Formatversion ist `3`.

## 5. Nächste Schritte

1. Den Vocal-v2-Hörsatz vollständig bewerten.
2. Einen Control-Adapter mit monotonen Ownership-Kurven und komplementären
   Gains definieren.
3. Mid-/High-EQ-Controls an den differenzierbaren Renderer anbinden.
4. Einen separaten self-supervised Trainingsrunner mit Objective v5 und
   trackgetrennten Splits ergänzen.
5. Gegen Equal Power, MLP v1/v2, direkte Kurvenoptimierung und Embedding-
   Baselines evaluieren.
