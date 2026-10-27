# Vocal-aware Feature→Control-Erweiterung

_Control-Protokoll 4, Objective Version 5, Modellformat 2 und
Bridge-Waveform-Cacheformat 2; eingeführt am 2026-08-05._

Dieses Dokument definiert die erste kontrollierte Vocal-Erweiterung der
kleinen MLP-Baseline. Sie ersetzt weder `time_shared_mlp_v1` noch Objective
v4 und verändert vorhandene Checkpoints oder Hörstudien nicht.

## 1. Zweck und Abgrenzung

Die bisherige Baseline kann Vocals nur gemeinsam mit dem kompletten
Mid-/High-Signal übergeben. `vocal_time_shared_mlp_v2` trennt deshalb die
Vocal-Übergabe vom restlichen Mix. Es bleibt bewusst ein zeitgeteiltes MLP
und ist noch nicht das im ursprünglichen Thesis-Entwurf beschriebene
TCN-/BiLSTM-Hauptmodell.

Waveforms sind weiterhin keine Modellinputs. Das Modell erhält ausschließlich:

```text
features_a:      (B, 32, 54)
features_b:      (B, 32, 54)
global_features: (B, 16)
```

Mix- und Vocal-Waveforms werden nur außerhalb des Modells vom
differenzierbaren Renderer und Objective verwendet.

## 2. Modellausgaben

Das Modell hat 20.821 Parameter und erzeugt:

```text
mix_position:  Gesamtübergabe des vocalfreien Rests
low_end_position: separate Bassübergabe unter 180 Hz
vocal_position: eigenständiger monotoner Vocal-Crossfade
vocal_duck_a: zusätzliche Absenkung des Source-Vocals
vocal_duck_b: zusätzliche Absenkung des Target-Vocals
vocal_gain_a: resultierender Source-Vocal-Gain
vocal_gain_b: resultierender Target-Vocal-Gain
```

Die ersten drei Positionen besitzen jeweils 32 Punkte, feste Endpunkte 0/1,
strenge Monotonie und dieselbe begrenzte Inkrementtransformation wie Control
v3. Die Vocal-Basisgains sind Equal Power:

```text
base_a = cos(vocal_position · π/2)
base_b = sin(vocal_position · π/2)
```

Ducking liegt standardmäßig in `[0, 0.75)` und wird mit
`4 · vocal_position · (1 - vocal_position)` gefenstert. Dadurch ist Ducking
an beiden Endpunkten exakt null. Die tatsächlich angewendeten Gains sind:

```text
vocal_gain_a = base_a · (1 - vocal_duck_a)
vocal_gain_b = base_b · (1 - vocal_duck_b)
```

Die Nullinitialisierung erzeugt lineare Positionen und nur rund 1,35 %
maximales Ducking in der Fenstermitte. Das neue Modell beginnt damit nahe an
der bisherigen Equal-Power-Baseline, ohne zufällige starke Vocal-Absenkung.

## 3. Stem-fähiger Renderer

`DifferentiableVocalAwareRenderer` erhält vier samplegleiche Waveforms:

```text
source_audio, target_audio
source_vocal_audio, target_vocal_audio
```

Zuerst wird pro Track `accompaniment = mix - vocal_stem` gebildet. Dieser
Rest wird mit `mix_position` und `low_end_position` durch den bisherigen
Zwei-Band-Renderer verarbeitet. Anschließend werden die Vocal-Stems mit
`vocal_gain_a/b` addiert. So kann ein Vocal früher oder später als Synths,
Drums und übrige Mitten übergeben werden.

Die Demucs-Stems sind Schätzungen. Subtraktion und erneutes Addieren können
Separation-Artefakte offenlegen; dies muss im Hörvergleich gegen den
unveränderten Mix geprüft werden.

## 4. Objective Version 5

Objective v5 behält Energie-, Boundary-, Smoothness-, Curvature-, Clipping-
und Transientenanteile aus v4. Die alten, nur aus `mix_position` abgeleiteten
Vocal-Overlap-/Boundary-Gewichte werden auf null gesetzt und durch
stem-/vocal-gain-spezifische Terme ersetzt:

- `vocal_stem_overlap`: bestraft gleichzeitig hörbare Source- und
  Target-Stems anhand tatsächlicher Stem-Energie, Feature-Aktivität und
  angewendeter Vocal-Gains.
- `vocal_audibility`: bestraft aktive, prominente Vocals, wenn ihr
  resultierender Gain unnötig klein wird. Bei gleichzeitig aktivem Gegenvocal
  bleibt die Strafe reduziert, aber nicht null; das verhindert die triviale
  Lösung, beide Vocals vollständig stumm zu regeln.
- `vocal_mid_phrase_gain_change`: bestraft starke Gain-Änderungen während
  aktiver Phrasen. Beim Source-Vocal reduziert ein erkanntes Offset die
  Strafe, beim Target-Vocal ein erkannter Onset.

Defaultgewichte:

```text
vocal_stem_overlap              1.0
vocal_audibility                0.5
vocal_mid_phrase_gain_change    0.2
```

Diese Gewichte sind Implementierungsdefaults. Der direkte geblendete
Objective-v4-vs-v5-Hörsatz ist bewertet: Objective v5 gewinnt 2/6, Objective
v4 gewinnt 1/6, drei Paare sind Gleichstände. Das positive Gate rechtfertigt
einen ersten v2-Trainingslauf; wegen nur eines Raters und drei
Time-Stretch-dominierten Paaren sind die Gewichte noch keine endgültigen
Forschungsparameter.

## 5. Vocal-Bridge-Cacheformat 2

```text
output/ml_cache/bridge_waveform_v2_vocal/<example-id>/<config-hash>/
├── manifest.json
└── bridge_waveforms.npz
```

Das NPZ enthält vier `float32 (2, N)`-Arrays:

```text
source_audio
target_audio
source_vocal_audio
target_vocal_audio
```

Der Cache-Key enthält zusätzlich Modellname und SHA-256 beider gecachter
Demucs-Artefakte. Mix und Target-Vocal werden mit derselben BPM-Geometrie und
Rubber-Band-Policy ausgerichtet. Datei- und Array-Hashes werden beim Laden
geprüft; Format-1-Caches bleiben unverändert.

## 6. Versionierter Trainingslauf Format 3

`VocalFeatureControlDataset` liefert Features, Mixe und Stems.
`collate_feature_control_examples` hält alle vier Waveformarten als
variable-lange Tupel. `vocal_self_supervised_batch_loss` rendert jedes
Beispiel einzeln, wertet Objective v5 aus und mittelt alle Komponenten.

`self_supervised_vocal_train_validation_v2` trainiert ausschließlich
`vocal_time_shared_mlp_v2` mit Control-Protokoll 4, Objective v5 und
Vocal-Bridge-Cacheformat 2. Der separat versionierte v1-Runner kann seine
alten Checkpoints weiterhin laden.

Der unveränderliche Run-Vertrag bindet Datasetmanifest und Splitgrößen,
Feature-/Modell-/Renderer-/Objective-Versionen, Vocal-Modellname,
Optimierertyp, Lernrate, Weight Decay, Adam-Betas/Epsilon, Scheduler samt
Parametern sowie Pfad und SHA-256 jedes tatsächlich verwendeten
Vocal-Cachemanifests. Der Testsplit wird weder geladen noch gecacht.
`manifest.json`, `history.json`, `best.pt` und `latest.pt` werden atomar
geschrieben und gehasht. Die Checkpoints enthalten Optimizer- und
Schedulerzustand; die verwendete Lernrate wird pro Epoche protokolliert.
Standardmäßig reduziert `ReduceLROnPlateau` die Lernrate anhand des
Validation-Losses. Alternativ sind `CosineAnnealingLR` oder kein Scheduler
verfügbar. Resume akzeptiert nur denselben Vertrag; lediglich `max_epochs` darf
erhöht werden. Checkpoints im alten Trainingsformat 2 können wegen des
fehlenden Schedulerzustands nicht mit Format 3 fortgesetzt werden; der
Studienexport unterstützt ihre Auswertung weiterhin. Vor dem Laden wird
zusätzlich der im Runmanifest gespeicherte SHA-256 des Latest-Checkpoints
geprüft.
Resume und Studienexport verwenden ausschließlich
`torch.load(..., weights_only=True)`; Checkpoints dürfen daher nur Tensoren,
Zustandswörter und einfache primitive Container enthalten.

Epoche 0 misst die deterministische, nahe an Equal Power liegende
Vocal-Modellinitialisierung ohne Update. Danach steuert ausschließlich
`validation` den Best-Checkpoint und Early Stopping.

Training und neu erforderliche Demucs-Separationen verwenden standardmäßig
`cuda:0`, wenn CUDA verfügbar ist, und sonst `cpu`. Der Trainingsrunner
akzeptiert `--device cpu` oder `--device cuda:<index>` als expliziten
Override; der tatsächlich aufgelöste Device-Name wird im Run-Vertrag
gespeichert. Bereits gecachte Demucs-Stems werden unverändert wiederverwendet.
Wegen derzeit nicht strikt deterministisch implementierter CUDA-Backward-
Kernel für lineares Upsampling und adaptives Average-Pooling läuft die
Determinismusprüfung dort im Warnmodus; bitgenaue Reproduktion bleibt dem
CPU-Override vorbehalten. Historische CPU-Läufe werden mit
`--device cpu --resume` fortgesetzt; GPU-Training verwendet einen neuen
Ausgabeordner.

## 7. CLI, Sonde und erster realer Trainingslauf

```powershell
.venv\Scripts\python.exe -m src.ml model-info-vocal

.venv\Scripts\python.exe -m src.ml cache-vocal-waveforms `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  --split train `
  --limit 1

.venv\Scripts\python.exe -m src.ml train-vocal `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\training_runs\vocal_time_shared_mlp_v2_objective_v5_seed20260805_20260805 `
  --seed 20260805 `
  --max-epochs 30 `
  --batch-size 5 `
  --learning-rate 0.001 `
  --patience 6 `
  --min-delta 0.0001 `
  --training-sample-rate 11025
```

Reale Sonde `example-c0a82769f650d763`: alle vier Waveforms haben Shape
`(2, 67328)` bei 11.025 Hz. Erster Zugriff war ein Cache-Miss, der direkte
zweite Zugriff ein Hit. Der initiale Objective-v5-Loss war `0,365197`, davon
`loss_v4 = 0,302488`, `vocal_audibility = 0,125145`,
`vocal_stem_overlap = 0` und `vocal_mid_phrase_gain_change = 0,000684`.
Alle Gradienten waren endlich.

Der reale Lauf verwendete 45 Trainings- und 9 Validation-Beispiele. Er
erreichte den besten Validation-Loss in Epoche 16 und stoppte nach sechs
weiteren Epochen ohne Verbesserung in Epoche 22:

```text
Validation gesamt:          0.267815 -> 0.259337  (-3.17 %)
Vocal-Stem-Overlap:         0.001723 -> 0.001263 (-26.70 %)
Vocal-Audibility:           0.141837 -> 0.105998 (-25.27 %)
alter Objective-v4-Anteil:  0.195017 -> 0.204875  (+5.05 %)
```

Damit lernt der Runner technisch und verbessert auf Validation gerade die
beiden neuen Vocal-Ziele. Gleichzeitig verschlechtern sich der alte
Objective-v4-Anteil, der Energieverlauf und die
Mid-Phrase-Gain-Änderungsstrafe leicht. Der Proxy-Gesamtgewinn ist deshalb
noch kein Hörqualitätsnachweis.

### Erweiterter Lauf mit 145–165 BPM

Der zweite reale Lauf verwendet Dataset `52bc9d1cebfd1b82d2ea` mit 370
Trainings- und 50 Validation-Beispielen. 60 trackgetrennte Testbeispiele
bleiben unberührt. Beste Validation ist Epoche 22; nach sechs weiteren
Epochen stoppt der Lauf in Epoche 28:

```text
Validation gesamt:          0.359040 -> 0.336999  (-6.14 %)
alter Objective-v4-Anteil:  0.299454 -> 0.285000  (-4.83 %)
Energieform:                0.224529 -> 0.204791  (-8.79 %)
Vocal-Stem-Overlap:         0.005435 -> 0.003022 (-44.39 %)
Vocal-Audibility:           0.108057 -> 0.097208 (-10.04 %)
Mid-Phrase-Gain-Änderung:   0.000613 -> 0.001867 (+204.28 %)
```

Anders als im kleinen Erstlauf verbessern sich auf Validation nun auch der
alte v4-Anteil und die Energieform. Die deutliche Verschlechterung der
Mid-Phrase-Gain-Änderung bleibt ein Warnsignal. Das Modell lernt außerdem
stärkeres, beispielabhängiges Target-Ducking (Mittel `0,1689`, Maximum
`0,7164`) als Source-Ducking (Mittel `0,0401`, Maximum `0,5107`). Genau diese
neue Richtung muss im nächsten geblendeten Hörvergleich geprüft werden.

## 8. Direkter Vocal-Hörsatz

`src.evaluation.vocal_objective_study` wählt Kandidaten anhand der
Vocal-Aktivität in genau den vier gerenderten Takten. Beide Seiten müssen
eine mittlere Stärke von mindestens `0,15` erreichen; pro gerichteter
Trackkombination wird höchstens ein Cue verwendet, jeder Track höchstens
zweimal. `STRUGGLING` wird zusätzlich explizit abgefangen.

Der Satz
`output/control_studies/blind_v7_objective_v5_vocal_active6_20260805_rerun/`
enthält sechs geblendete A/B-Paare. Beide Varianten verwenden denselben
stem-fähigen Renderer. Die Baseline nutzt direkt optimierte Objective-v4-
Mix-/Low-End-Kurven, lässt die Vocals der Mixkurve folgen und verwendet kein
Ducking. Die Gegenvariante optimiert alle Objective-v5-Controls.

Alle sechs Source-/Targetfenster enthalten gemessene Vocals auf beiden
Seiten; 13 bis 32 der 32 Halbbeat-Bins sind gleichzeitig über `0,2` aktiv.
Der Objective-v5-Loss sank in allen sechs Paaren (`0,3435→0,2768`,
`0,2115→0,1808`, `0,3990→0,3573`, `0,1748→0,1500`,
`0,3307→0,3079`, `0,3457→0,2762`). Die vollständige geblendete Bewertung
wurde danach entblindet: **Objective v5 gewinnt zwei Paare, Objective v4
eines, drei sind Gleichstände**. Im Fünf-Kriterien-Mittel steigt v4→v5 von
`4,2333` auf `4,3667`. Der Unterschied liegt ausschließlich bei
`vocal_clarity` (`4,3333→5,0`); alle anderen Kriterien sind identisch.
Paar 2, 3 und 5 klingen in beiden Varianten wegen Rubber-Band-Time-Stretch
schlecht und begrenzen die Aussagekraft.

## 9. Geblendeter Modell-Hörsatz

`src.evaluation.vocal_ml_control_study` vergleicht die aus demselben
Modellvertrag rekonstruierte, ungelernte Vocal-v2-Initialisierung gegen den
SHA-geprüften Best-Checkpoint. Beide Varianten verwenden dieselben vier
Waveforms, denselben stem-fähigen Renderer, Kontext und gemeinsamen Peak-Gain.
Runformat, Runnername, Modellformat, Dataset-ID/-Manifesthash sowie
Checkpoint-Epoche und -Hash werden vor dem Export geprüft.

Der noch unbewertete Satz
`output/control_studies/blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806/`
enthält fünf unterschiedliche gerichtete Paarungen aus `validation`. Beide
Übergangsseiten besitzen mittlere Vocal-Stärke mindestens `0,15`; pro
Paarung wird nur der vocal-stärkste tempozulässige Cue verwendet. Die
zulässige Tempoänderung ist auf `0,5 %` begrenzt, alle fünf gewählten Paare
liegen tatsächlich bei `0,0 %` und umgehen damit die bekannte
Time-Stretch-Konfundierung.

Source-Vocal-Stärken reichen von `0,353` bis `0,796`, Target von `0,188` bis
`0,911`; 7 bis 32 der 32 Halbbeat-Bins sind gleichzeitig über `0,2` aktiv.
Der Objective-v5-Loss des Best-Checkpoints ist gegenüber der Initialisierung
auf zwei Paaren kleiner und auf drei größer. Der aggregierte Trainingsgewinn
darf deshalb nicht als Paar-für-Paar- oder Hörqualitätsnachweis gelesen
werden. `ratings.json` ist vollständig `unrated`; erst nach der geblendeten
Bewertung darf `answer_key.json` ausgewertet werden.

## 10. Grenzen und nächstes Gate

- Ein ungünstiger Cue mitten in einem Satz kann durch Gains nicht vollständig
  repariert werden; die Kandidatenauswahl muss später ebenfalls vocal-aware
  werden.
- `vocal_phrase_progress`, Onset und Offset sind heuristisch aus
  Demucs-Energie abgeleitet und nicht sprachlich beziehungsweise phonemisch.
- Das kleine MLP besitzt weiterhin kein TCN-/BiLSTM-Rezeptionsfeld.
- Der erweiterte versionierte v2-Trainingslauf und der tempo-konfundierungsfreie
  geblendete Export sind abgeschlossen. Als Nächstes müssen alle fünf Paare
  bewertet und erst danach entblindet werden. Die Objective-Gewichte erst
  nach diesem Modell-Gate und später mit mehr Ratenden endgültig einfrieren.
