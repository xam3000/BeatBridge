# Feature→Control-ML-Baseline

_Modellvertrag 1 und Bridge-Waveform-Cacheformat 1, eingeführt am
2026-08-04._

Dieses Dokument definiert die erste kleine ML-Baseline nach dem bestandenen
Direktoptimierungs-Hör-Gate. Änderungen innerhalb einer Version erfolgen nur
additiv; inkompatible Änderungen benötigen eine neue Version.

Die additive Vocal-Erweiterung mit Modellformat 2, Control-Protokoll 4,
Objective v5, eigenem Waveform-Cache und separatem Trainingsrunner Format 2
steht in
[`VOCAL_CONTROL_MODEL_PROTOCOL.md`](./VOCAL_CONTROL_MODEL_PROTOCOL.md).
Sie verändert diesen reproduzierbaren v1-Vertrag nicht.

## 1. Lernpfad

Das Modell erhält keine Audiosamples und keine Ground-Truth-Kurven:

```text
Feature-Protokoll 1
  → time_shared_mlp_v1
  → zwei monotone Control-Kurven
  → differenzierbarer Zwei-Band-Renderer
  → Objective v4
  → Gradientenupdate
```

Direkt optimierte Kurven dürfen als obere Referenz ausgewertet, aber nicht als
Targets für diese self-supervised Baseline verwendet werden.

## 2. Bridge-Waveform-Cacheformat 1

Das Objective benötigt zusätzlich zu den Modellinputs die ausgerichteten
Source-Postroll- und Target-Preroll-Waveforms. Sie werden einmal über den
produktiven 44,1-kHz-Renderingpfad einschließlich Rubber Band rekonstruiert
und danach auf die Trainings-Sample-Rate von standardmäßig 11.025 Hz
heruntergerechnet.

```text
output/ml_cache/bridge_waveform_v1/
└── <example-id>/
    └── <config-hash>/
        ├── manifest.json
        └── bridge_waveforms.npz
```

Der Konfigurationshash umfasst mindestens Audio-SHA beider Tracks, beide
Cues, BPM, Übergangsbeats, Rendering-Protokoll, Stretch-Policy, Kanalzahl,
Render- und Trainings-Sample-Rate. Ein vorhandener gültiger Cache wird nie
überschrieben. Datei- und Array-Hashes sowie Shapes, Backend und tatsächliche
Geometrie stehen im Manifest. Vor einem Erstaufbau werden die aktuellen
Audiodateien gegen die im Dataset gespeicherten SHA-256-Werte geprüft.

`bridge_waveforms.npz` enthält:

```text
source_audio: float32 (2, N)
target_audio: float32 (2, N)
```

Beide Arrays sind endlich, stereo, nicht leer und samplegleich. `N` hängt vom
Source-BPM ab und variiert zwischen Beispielen. Es wird keine zusätzliche
Dauernormalisierung vorgenommen.

## 3. PyTorch-Dataset und Batching

`FeatureControlDataset` prüft die SHA-256-Werte von Split-NPZ,
`examples.jsonl` und Paarmanifest, verbindet die drei Featuretensoren mit dem
zugehörigen Waveform-Cache und gibt pro Beispiel zurück:

```text
features_a:      float32 (32, 54)
features_b:      float32 (32, 54)
global_features: float32 (16,)
source_audio:    float32 (2, N)
target_audio:    float32 (2, N)
```

`collate_feature_control_examples` stapelt nur die festen Featuretensoren.
Waveforms bleiben Tupel variabler Länge. Der Self-Supervised-Batch-Loss
rendert sie einzeln und mittelt anschließend jede Objective-Komponente. So
werden keine Nullpads als vermeintliche Stille bewertet und kein künstliches
Tempo-Resampling eingeführt.

## 4. `time_shared_mlp_v1`

Für jedes der 31 Intervalle werden die Mittelwerte der zwei angrenzenden
Featurepunkte von A und B mit den 16 globalen Features verbunden:

```text
54 A + 54 B + 16 global = 124 Eingänge pro Intervall
```

Dasselbe MLP wird auf alle Intervalle angewendet:

```text
LayerNorm(124) → Linear(124,64) → GELU
               → Linear(64,32) → GELU
               → Linear(32,2)
```

Das Modell hat **10.394 Parameter**. Die zwei Ausgänge sind Inkrement-Logits
für `mix_position` und `low_end_position`. Die vorhandene
`0.6 · tanh → softmax → cumulative sum`-Transformation erzwingt feste
Endpunkte, strenge Monotonie und die Control-v3-Schrittgrenze.

Die letzte Schicht startet exakt mit null. Vor dem ersten Trainingsupdate
erzeugt das Modell daher für jedes Beispiel die lineare Equal-Power-Kurve und
keine zufällige Übergabe.

## 5. Split- und Evaluationsregel

- Optimierung der Modellparameter: nur `train`.
- Early Stopping und Hyperparameterwahl: nur `validation`.
- Der vorhandene `test`-Split wurde bereits für das Objective-v4-Hör-Gate
  gehört und ist damit für eine endgültige unabhängige Modellstudie
  verbraucht. Er darf als technischer Regressionstest dienen, aber nicht als
  unangetasteter finaler Wirksamkeitsnachweis bezeichnet werden.
- Vor dem finalen Modellvergleich werden neue Track-Hashes als externer
  Testsatz benötigt.

## 6. CLI und Python-Einstieg

```powershell
.venv\Scripts\python.exe -m src.ml model-info

.venv\Scripts\python.exe -m src.ml cache-waveforms `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  --split train `
  --training-sample-rate 11025
```

Der Cache-Aufbau kann Rubber Band starten. Ein technischer Probelauf darf mit
`--limit 1` begrenzt werden.

```python
from src.ml import FeatureControlMLP, self_supervised_batch_loss
```

## 7. Trainingslauf Format 1

`self_supervised_train_validation_v1` trainiert ausschließlich auf `train`
und verwendet `validation` nur für Modellwahl und Early Stopping. Epoche 0
misst vor jedem Update die durch die Nullinitialisierung erzeugte lineare
Equal-Power-Baseline. Der Testsplit wird vom Trainingsrunner nicht geladen.

Der Defaultlauf verwendet AdamW, Seed `20260804`, Batchgröße 5,
Lernrate `1e-3`, Weight Decay `1e-4`, Gradient Clipping bei 1,0 und Early
Stopping nach sechs Epochen ohne Verbesserung von mindestens `1e-4`.
Die Reihenfolge der Trainingsbeispiele wird für jede Epoche aus
`seed + epoch` deterministisch erzeugt. PyTorch-Operationen laufen mit
aktivierten deterministischen Algorithmen. Auf CUDA werden derzeit nicht
deterministisch implementierte Backward-Kernel (aktuell lineares Upsampling
und adaptives Average-Pooling) im Warnmodus zugelassen; CUDA-Läufe sind daher
nicht bitgenau reproduzierbar.
`--device auto` ist der Default
und wird vor dem unveränderlichen Run-Vertrag auf `cuda:0` aufgelöst, wenn
CUDA verfügbar ist, sonst auf `cpu`. `--device cpu` beziehungsweise
`--device cuda:<index>` überschreibt die automatische Wahl explizit.

```text
output/training_runs/<run-name>/
├── manifest.json
├── history.json
└── checkpoints/
    ├── best.pt
    └── latest.pt
```

Manifest und History werden atomar ersetzt und enthalten den vollständigen
Dataset-, Modell-, Renderer-, Objective- und Optimierungsvertrag. Beide
Checkpoints enthalten Modell, Optimizer, Epoche, bisherigen Bestwert,
Early-Stopping-Zähler und History. Ihre SHA-256-Werte stehen im Manifest.
`--resume` akzeptiert nur denselben unveränderlichen Vertrag; ausschließlich
`max_epochs` darf erhöht werden. Bereits vorhandene Ausgaben werden ohne
`--resume` nicht überschrieben. Vor jedem Resume wird der SHA-256 von
`latest.pt` gegen den Manifesteintrag geprüft. Resume und Studienexport laden
Checkpoints ausschließlich mit `torch.load(..., weights_only=True)`; der
Checkpointvertrag bleibt daher auf Tensoren, Zustandswörter und einfache
primitive Container beschränkt.

```powershell
.venv\Scripts\python.exe -m src.ml train `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\training_runs\time_shared_mlp_v1_objective_v4_seed20260804_20260804
```

Der Runner meldet zu Beginn `torch_device=cuda:0` beziehungsweise
`torch_device=cpu`; damit ist die tatsächlich verwendete Hardware im Log
sichtbar.

Historische CPU-Läufe müssen wegen ihres eingefrorenen Run-Vertrags mit
`--device cpu --resume` fortgesetzt werden. Ein neuer GPU-Lauf braucht einen
neuen Ausgabeordner.

## 8. Verifizierter Erstlauf

Der erste reale Lauf auf Dataset `f9044dc259b7296c8b28` verwendete 45
Train- und 9 Validation-Beispiele. Alle 54 Bridge-Waveforms liegen danach im
Cache; der Testsplit blieb unberührt. Die Validation-Loss sank gegenüber der
Equal-Power-Initialisierung von `0,305959` auf `0,295999` in Epoche 8
(-3,26 %). Der Train-Loss sank dort von `0,320002` auf `0,303996` (-5,00 %).
Nach sechs weiteren Epochen ohne neue Verbesserung stoppte der Lauf in
Epoche 14.

Das beste Modell erzeugt beispielabhängige Kurven: Auf Validation beträgt
die maximale Abweichung von der linearen Kurve rund 0,185 für
`mix_position` und 0,038 für `low_end_position`; die maximale
Zwischenbeispiel-Standardabweichung beträgt 0,101 beziehungsweise 0,023.
Damit ist technisch belegt, dass das Netz nicht nur eine einzige konstante
Kurve ausgibt. Der niedrigere Proxy-Loss ist noch kein Beleg für hörbar
bessere Übergänge. Ein erster geblendeter Entwicklungsvergleich gegen Equal
Power liegt mit allen neun Validation-Beispielen unter
`output/control_studies/blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun/`;
seine Ratings sind offen. Für einen unabhängigen Wirksamkeitsnachweis und den
Vergleich gegen direkt optimierte Kurven werden weiterhin neue Audio-Hashes
benötigt.

## 9. Additive variable Dataset-2-Baseline

`variable_time_shared_mlp_v1` ist ein neues Modell mit Formatversion `2`.
Es verändert `time_shared_mlp_v1` und `vocal_time_shared_mlp_v2` nicht. Der
Loader liest homogene Dataset-2-Shards für `T=16,32,48,64`; eine additive
Mehrlängenansicht verwendet einen Batch-Sampler, der niemals verschiedene
Längen in einen Featurebatch mischt. Waveforms bleiben pro Beispiel als
ungepadete Tupel und dürfen zwischen Beispielen verschiedene Samplezahlen
haben.

Das Modell erhält die 54 Kanäle und den unveränderten 16-dimensionalen
Globalvektor sowie separat `length_condition = transition_length_bars / 8`.
Für eine explizite Länge werden drei monotone Kurven mit genau `T-1`
Softmax-Inkrementen und genau `T` Kontrollpunkten erzeugt. Die Endpunkte sind
exakt `0` und `1`; die Vocal-Ducking-Kurven beginnen und enden dadurch exakt
bei `0`.

`VariableVocalAwareTransitionObjective` verwendet Objective-v5 mit
`energy_frames=T`. Die Lossaggregation rendert jede Waveform einzeln und
mittelt erst danach skalare, zeitnormalisierte Terme. Checkpoint- und
Resume-Manifeste tragen Datasetformat, unterstützte Längen,
Sequenzlängen, Längenkonditionierung, Modell- und Objective-Namen sowie den
Datasetmanifest-Hash. Der aktuelle Review hat zusätzlich reale Feature-/Global-
und Längenkonditionierungsdaten aus Train und Validation mit je einem kleinen
expliziten Waveform-Callback pro Länge gesmoked. Das ist kein vollständiger
realer Waveform-Cache und keine lange Trainingskampagne; der Testsplit bleibt
außerhalb des Runners.

### Variabler temporaler Hauptvertrag

`variable_tcn_bilstm_transition_control_v1` hat Modellformat `4` und ist
vollständig getrennt von `tcn_bilstm_transition_control_v1`. Ein gemeinsamer
TCN-Encoder verarbeitet A und B, danach folgt die Fusion
`[A, B, A-B, A*B]`, der unveränderte Globalvektor und eine separate,
wirksame Längenprojektion. Die BiLSTM verarbeitet die ganze gültige Länge.
Der Dataset-2-Normalpfad bleibt längenhomogen; ein optionaler gepaddeter
Carrier muss `sequence_lengths` angeben, maskiert die TCN-Eingaben und wird
über `pack_padded_sequence` verarbeitet.

Der Output enthält `(B,T,10)` Diagnose-/Renderercontrols sowie explizite
monotone Mix-, Low-End- und Vocal-Kurven, getrenntes Source-/Target-Ducking
und die daraus abgeleiteten Vocal-Gains. Der neue temporal Runner akzeptiert
nur übergebene Train-/Validation-Batches, nie einen Testsplit. Er speichert
gleiche Längengewichte für die berichtete Kennzahl, Gesamt- und Per-L-Metriken, atomare
`latest.pt`/`best.pt`-Checkpoints und SHA-gebundene Manifeste. W&B bleibt
über dieselben `disabled`/`offline`/`online`-Modi optional.
Der Optimierer aktualisiert die Gewichte einmal je längenhomogenem Batch.
Die Anzahl der Updates je Länge folgt damit der Zahl ihrer Batches. Beim
Wiederaufnehmen des variablen Runners werden die Zufallsgeneratoren erneut
gesetzt. [R4-Verlauf und Auswirkung](TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md)
Ein vollständiger realer CUDA-Lauf ist derzeit noch kein CLI-Befehl: Der Runner
akzeptiert API-seitig bereits gebaute Train-/Validation-Batches, während der
versionierte v2-Waveform-Cache und ein eigener CLI-Subcommand noch fehlen.
