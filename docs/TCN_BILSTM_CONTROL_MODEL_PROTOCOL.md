# TCN/BiLSTM-Transition-Control-Modell

_Modellvertrag 3, additive Architektursonde, eingeführt am 2026-08-12._

Dieses Dokument beschreibt die größere Architektur nach den kleinen MLP-
Baselines. Die v1-/v2-Checkpoints, Trainingsrunner und Hörstudien bleiben
unverändert. Ein separater Architektur-Trainingsrunner ist implementiert und
nutzt einen additiven Drei-Band-Renderer mit Objective v4.

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
Transformation beschränkt die aktuellen Controls auf `[0, 1]`. `gain_A` und
`gain_B` werden dabei komplementär aus einer monotonen Ownership-Kurve
abgeleitet; `low_end_ownership` wird ebenfalls monoton konstruiert.

## 3. Bewusste Grenze der ersten Implementierung

Die Architektur gibt zehn bounded Controls aus. Der additive
`DifferentiableFullBandTransitionRenderer` verwendet alle zehn Ausgänge:

- `gain_A/B` steuern Mid- und High-Band,
- `low_end_ownership` steuert das Low-Band,
- `eq_low/mid/high_A/B` skalieren die drei Frequenzbänder separat,
- `vocal_ducking` senkt bei vorhandenen Vocal-Stems beide Vocals ab.

Ohne Stems wird Vocal-Ducking ausschließlich auf das Mid-Band als expliziter
Proxy angewendet. Der aktuelle generische TCN-Datensatz nutzt diesen Proxy;
ein zukünftiger stem-basierter Lauf kann die vorhandenen Demucs-Stems direkt
übergeben. Dadurch werden die validierten v1-/v2-Controlverträge nicht
stillschweigend verändert.

## 4. Python-Einstieg

```python
from src.ml import TCNBiLSTMTransitionControl

model = TCNBiLSTMTransitionControl()
output = model(features_a, features_b, global_features)
assert output.controls.shape == (batch_size, 32, 10)
```

Der Modellname ist `tcn_bilstm_transition_control_v1`; die interne
Formatversion ist `3`.

## 5. Trainingssonde

```powershell
.venv\Scripts\python.exe -m src.ml train-tcn-bilstm `
  output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 `
  output\training_runs\tcn_bilstm_transition_control_v1_full_band_extended_bpm145_165_top10_20260812 `
  --device cuda:0 --max-epochs 30 --batch-size 5 --patience 6 --seed 20260812
```

Der reale Full-Band-Lauf auf 370 Train- und 50 Validation-Beispielen stoppte
nach Epoche 20 per Early Stopping. Der beste Checkpoint stammt aus Epoche 14
und erreichte einen Validation-Proxy-Loss von `0,3206756`, gegenüber
`1,9383116` bei der Initialisierung. Der Testsplit wurde nicht geladen.

## 6. Nächste Schritte

1. Den Vocal-v2-Hörsatz vollständig bewerten.
2. Einen stem-basierten TCN-Lauf mit Objective v5 durchführen und gegen den
   Mid-Band-Vocal-Proxy vergleichen.
3. Mid-/High-EQ- und Vocal-Controls gegen Hörbewertungen evaluieren.
5. Gegen Equal Power, MLP v1/v2, direkte Kurvenoptimierung und Embedding-
   Baselines evaluieren.

## Additiver Variable-v2-Smoke (verifiziert 2026-08-21)

Die additive Modellvariante `variable_tcn_bilstm_transition_control_v1`
verwendet Dataset-/Feature-Protocol 2 mit `T=16/32/48/64` und den separaten
Längenkanal `length_condition=L/8`. Sie ist an den Vertrag
`local_grid_target_to_source_v1` und den Cache
`output/ml_cache/variable_bridge_waveform_v2` gebunden. Der reale Smoke-Test
auf 420 Train- und 48 Validation-Beispielen lief mit `cuda:0` eine Epoche und
wurde auf zwei Epochen resumed; beide Läufe meldeten 468 Cache-Hits. Der
Testsplit wurde nicht geladen. Der vollständige 100-Epochen-Lauf ist weiterhin
nicht ausgeführt.
