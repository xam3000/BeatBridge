# Aktuelle Form der ML-Modelle

_Stand: 2026-09-04_

## Ergänzung aus lokaler Artefaktprüfung am 2026-09-07

Für die angefragte Repository-/Modellübersicht wurden Code, Runmanifeste und
Trainingshistorien gelesen. Die älteren Aussagen weiter unten, Variable-TCN
sei ausschließlich über zwei Epochen gesmoked worden, sind inzwischen überholt:

- `output/training_runs/variable_tcn_bilstm_waveform_v2_full_20260821/`:
  Manifeststatus `completed`, letzte Epoche 20; kleinstes protokolliertes
  Validation-Loss in Epoche 14: `0.24643995364507038`.
- `output/training_runs/variable_tcn_bilstm_v2_wandb_20260826/`:
  Manifeststatus `completed`, letzte Epoche 29; kleinstes protokolliertes
  Validation-Loss in Epoche 23: `0.24559853225946426`.
- In beiden Runs stimmen die neu berechneten SHA-256-Werte von `history.json`
  und dem deklarierten Best-Checkpoint mit dem Runmanifest überein. Es wurde
  kein Checkpoint deserialisiert, kein Training und kein Audio-Hörtest gestartet.
- Der Variable-TCN-Trainingspfad nutzt den stem-fähigen
  `DifferentiableVocalAwareRenderer` mit Mix-/Low-End-/Vocal-Position und
  getrenntem Vocal-Ducking. Seine zehn Diagnose-Controlkanäle bedeuten nicht,
  dass hier derselbe Drei-Band-EQ-Pfad wie beim festen Full-Band-TCN trainiert
  wird (siehe `src/ml/variable_training.py`).
- Zusätzlich ist `variable_time_shared_mlp_v1` als kleine, vocal-aware
  Variable-Length-Baseline in `src/ml/variable_model.py` implementiert; im
  inspizierten `output/training_runs/` wurde kein eigener Run identifiziert.
- Die Cue-Ranker-CLIs für Teacher-Labeling und Training sind inzwischen
  implementiert (`src/ml/__main__.py`, Status-Audits vom 2026-08-26/27).
  Frühere Aussagen über fehlende CLIs sind historisch. Ein real trainierter
  Ranker und eine unabhängige musikalische Qualitätsfreigabe bleiben unbelegt.

Die Zahlen sind Proxy-Losses innerhalb ihrer jeweiligen Protokolle und keine
vergleichbare Rangliste der Hörqualität. Prüfprotokoll: `Bemerkungen.md`,
Eintrag vom 2026-09-07.

Diese Übersicht trennt den aktuell verwendeten Modellpfad von den historischen
Baselines und dem bereits implementierten, aber noch experimentellen größeren
Modell. Sie beschreibt den verifizierten Code- und Run-Stand; ein niedrigerer
Validation-Proxy-Loss ist dabei kein Hörqualitätsnachweis.

## Architektur und Lernpfad

```mermaid
flowchart LR
    A[Songfenster A und B] --> F[Feature-Protokoll 1<br/>A: 32 x 54<br/>B: 32 x 54<br/>Global: 16]
    A --> W[Bridge-Waveform-Cache<br/>Mix A/B + Vocal-Stems]
    S[BS-RoFormer<br/>Vocal-Separation] --> W

    subgraph CURRENT[Aktueller gelernter Pfad]
        F --> V[vocal_time_shared_mlp_v2<br/>20.821 Parameter<br/>zeitgeteiltes MLP]
        V --> VC[mix_position<br/>low_end_position<br/>vocal_position<br/>vocal_duck_a/b<br/>vocal_gain_a/b]
        VC --> VR[DifferentiableVocalAwareRenderer<br/>Accompaniment + Vocal-Stems]
        W --> VR
        VR --> O5[Objective v5<br/>Self-Supervised Loss]
        O5 --> U[Gradientenupdate<br/>AdamW + Early Stopping]
        U --> V
    end

    subgraph BASELINE[Historische Baseline]
        F --> M[time_shared_mlp_v1<br/>10.394 Parameter]
        M --> C2[mix_position<br/>low_end_position]
        C2 --> R2[Zwei-Band-Renderer]
        R2 --> O4[Objective v4]
    end

    subgraph EXPERIMENTAL[Experimenteller Hauptmodellpfad]
        F --> T[TCN-BiLSTM v1<br/>1.013.226 Parameter]
        T --> TC[10 zeitabhängige Controls<br/>Gain / EQ / Low-End / Vocal-Ducking]
        TC --> FR[Full-Band-Renderer<br/>Low / Mid / High]
        FR --> O4B[Objective v4]
    end

    X[Testsplit<br/>60 Beispiele<br/>beim Training unberührt]
    X -. separate Evaluation .-> E[Hörvergleich / externe Evaluation]
```

Der aktuelle Default ist der Vocal-aware-Pfad. Die Waveforms und Vocal-Stems
sind zusätzliche Inputs für Renderer und Objective, nicht direkte Eingaben des
MLP. Das Netz arbeitet ausschließlich auf den Feature-Tensoren und erzeugt
zeitabhängige Kontrollen für 32 Halbbeat-Positionen beziehungsweise 31
Intervalle.

## Verifizierter Modellstatus

| Pfad | Architektur / Ausgaben | Run-Stand | Einordnung |
|---|---|---|---|
| **`vocal_time_shared_mlp_v2`** | Zeitgeteiltes MLP mit Hidden-Dimensionen `(64, 32)`; drei monotone Positionen sowie Source-/Target-Vocal-Ducking und resultierende Gains; **20.821 Parameter** | Aktueller RoFormer-Lauf: `output/training_runs/vocal_roformer_extended_bpm145_165_top10_seed20260812/`; 370 Train / 50 Validation; `cuda:0`; Early Stopping nach Epoche 27, bester Checkpoint Epoche 21, Validation-Loss `0,3318392038` | **Aktueller gelernter Pfad / Default** |
| `time_shared_mlp_v1` | Zeitgeteiltes MLP mit `(64, 32)`; `mix_position` und `low_end_position`; **10.394 Parameter** | Historischer Lauf auf 45 Train / 9 Validation; CPU; bester Checkpoint Epoche 8, Validation-Loss `0,2959988448` | Reproduzierbare Baseline; Testsplit ist historisch bereits für Entwicklungsevaluation verwendet |
| `tcn_bilstm_transition_control_v1` | Geteilter TCN-Encoder `54 → 64 → 128`, Fusion `[A, B, A-B, A*B]`, zweilagiger BiLSTM; 10 Full-Band-Controls; **1.013.226 Parameter** | Full-Band-Lauf auf 370 Train / 50 Validation; `cuda:0`; Early Stopping nach Epoche 20, bester Checkpoint Epoche 14, Validation-Loss `0,3206755668` | Implementiert und trainiert, aber **experimentell**, noch nicht als Default |

Der aktuelle Vocal-Lauf verwendet den RoFormer-Stem-Backend
`roformer-model-bs-roformer-sw-by-jarredou`. Dadurch ist
`vocal_time_shared_mlp_v2` das gleiche Modellformat wie zuvor, aber der aktuelle
Trainings- und Featurepfad nutzt die verifizierte RoFormer-Separation. Die 60
Testbeispiele des erweiterten Datensatzes bleiben vom Training ausgeschlossen.

## Additiver Cuepoint-Ranker v1 (Auditstand 2026-08-25)

`learned_cue_ranker_v1` ist ein separater, nicht als Default aktivierter
Kandidatenranker vor Controller und Renderer. Er akzeptiert ausschließlich
bereits akzeptierte Candidate-v2-Einträge mit 4/4-Downbeats,
`approximate_grid_policy=reject` und verifizierter Grid-Provenienz. Die
historische `feature_baseline_v3` bleibt Batch-/CLI-Default und bleibt im
Manifest unter `candidate_ranking` unverändert; der Learned-Opt-in schreibt
seine Scores und Auswahl getrennt unter `cue_ranking`.

Ein frischer unabhängiger Audit bestätigte mit synthetischen Fixtures
vollständige Split-/Gruppenisolation, variable Ragged-Gruppen,
Samplingwahrscheinlichkeiten, `weights_only`-Checkpointloads,
deterministisches Resume und Learned-Render-Backfill. Dabei wurden vier echte
Datenfluss-/Sicherheitsfehler korrigiert: Guard-Rejections sind nun immer
negative Teacher-Anker; der Gruppenkontext verwendet die vollständige
Kandidatenmenge; Renderfehler füllen deterministisch auf; der Teacher ist an
einen abgeschlossenen Variable-TCN-Run und dessen deklarierten Best-Checkpoint
gebunden. Die betroffene Regression bestand mit `82 passed, 2 warnings`, die
vollständige Suite mit `239 passed, 4 warnings`; Testsplit und reales Training
blieben geschlossen.

Der Pfad ist dennoch **nicht für einen größeren realen Validation-Lauf
freigegeben**. Es existiert weder ein testfrei veröffentlichter Format-3-
Teacher-Snapshot mit echten Labels noch ein sicherer End-to-End-CLI-Einstieg
für `label-cue-ranker-teacher` und `train-cue-ranker`. Alle gegenwärtigen
Ranker-Metriken messen nur Agreement mit dem eingefrorenen Objective-v5-
Teacher; sie belegen weder Überlegenheit über `feature_baseline_v3` auf realen
Validation-Gruppen noch hörbare Übergangsqualität. Dafür ist anschließend ein
vorab festgelegter Vergleich auf demselben echten Validation-Snapshot und ein
unabhängiges menschliches Hör-Gate erforderlich.

## Additiver Variable-Length-Stand (2026-08-21)

Der neue, nicht als Default aktivierte Pfad
`variable_tcn_bilstm_transition_control_v1` (Modellformat 4) arbeitet mit
homogenen `T=16/32/48/64`-Batches und der separaten Konditionierung
`length_condition = L/8`. Der reale Dataset-v2-Loader wurde ausschließlich für
Train und Validation geöffnet. Ein kurzer CPU-Smoke über alle vier Längen lief
über zwei Epochen; die zweite Epoche wurde sicher aus dem Latest-Checkpoint
resumed. Der Run ist unter
`output/review_variable_v2_training_smoke_20260821_run01/` dokumentiert.

Die Inferenzprüfung eines Validationbeispiels je Länge erzeugte endliche
`(T,10)`-Controls mit exakt monotonen Positionskurven und T=16/32/48/64. Das
ist eine technische Vertragsprüfung, kein Nachweis musikalischer Qualität und
keine lange Trainingskampagne. Der Testsplit wurde in diesem Pfad nicht geladen.
Ein realer v2-Waveform-Cache und ein CLI-Einstieg für einen vollständigen
CUDA-Lauf fehlen noch; der Pfad kann deshalb derzeit nur über die API mit
explizit gelieferten Waveform-Batches gesmoked werden.

## Eingabe, Ausgabe und Constraints des Defaults

```text
features_a      float32 (B, 32, 54)
features_b      float32 (B, 32, 54)
global_features float32 (B, 16)
                         │
                         ▼
                 vocal_time_shared_mlp_v2
                         │
                         ├─ mix_position       (B, 32)
                         ├─ low_end_position   (B, 32)
                         ├─ vocal_position     (B, 32)
                         ├─ vocal_duck_a/b     (B, 32)
                         └─ vocal_gain_a/b     (B, 32)
```

- Die drei Positionskurven haben feste Endpunkte `0/1`, sind konstruktiv
  monoton und verwenden die begrenzte Inkrementtransformation aus
  Control-Protokoll 4.
- Vocal-Ducking ist auf maximal `0,75` begrenzt, an den Übergangsendpunkten
  null und wird zusätzlich durch die Vocal-Position gefenstert.
- Der stem-fähige Renderer verarbeitet den vocalfreien Rest zweibandig und
  addiert die beiden Vocal-Stems mit den gelernten Vocal-Gains.
- Objective v5 liefert das Lernsignal aus Energieform, Boundary-/Glätte-,
  Clipping-/Transienten- und Vocal-spezifischen Termen. Es gibt keine
  Ground-Truth-Control-Kurven.

## Aktuelle Aussagekraft und nächstes Gate

Technisch ist der aktuelle RoFormer-Lauf reproduzierbar materialisiert und der
Best-Checkpoint wurde manifest- und SHA-geprüft geladen. Der Validation-Loss
belegt jedoch nur Lernen gegen den eingefrorenen Proxy. Seit 2026-09-04 liegt
unter `output/control_studies/blind_all_models_validation_20260904/` ein
gemeinsamer geblendeter Hörsatz für Equal Power, Time-shared MLP v1, Vocal-MLP
v2 und den Full-Band-TCN/BiLSTM v1 bereit: fünf identische Validation-Paare,
vier Varianten je Paar und eine lokale HTML-Bewertungsoberfläche. Das nächste
fachliche Gate sind die noch offenen `0/5` Mehrmodell-Ratings. Erst danach
sollte entschieden werden, ob Objective-Gewichte, Vocal-Ducking oder die
Architektur verändert werden. Variable-TCN v2 benötigt wegen seines
Dataset-/Feature-Protokolls 2 einen getrennten protokollgleichen Hörsatz. Ein
solcher Satz liegt seit 2026-09-04 unter
`output/control_studies/blind_variable_tcn_lengths_20260904/` mit je einem
A/B-Beispiel für 2/4/6/8 Takte bereit. Beide Studien sind ohne Zusammenlegung
ihrer Ratings über
`output/control_studies/model_comparison_hub_20260904/index.html` erreichbar;
der Cue-Ranker erscheint dort ausschließlich als ausdrücklich synthetische,
nicht hörbare Funktionsdemo.

## Quellen im Repository

- Modellimplementierung: [`src/ml/model.py`](../src/ml/model.py)
- Baseline-Vertrag: [`ML_CONTROL_MODEL_PROTOCOL.md`](./ML_CONTROL_MODEL_PROTOCOL.md)
- Vocal-Vertrag: [`VOCAL_CONTROL_MODEL_PROTOCOL.md`](./VOCAL_CONTROL_MODEL_PROTOCOL.md)
- TCN-/BiLSTM-Vertrag: [`TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md`](./TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md)
- Verifizierter Projektstand: [`STATUS.md`](./STATUS.md)

## Verifizierter Real-Cache- und CUDA-Stand (2026-08-21)

Der Variable-Length-Pfad verwendet nun den separaten
`local_grid_target_to_source_v1`-Waveformvertrag und den unveränderlichen
Cache `output/ml_cache/variable_bridge_waveform_v2`. Der reale Datensatz
enthält 420 Train- und 48 Validation-Entries, je 105/12 für 2/4/6/8 Takte;
der Testsplit bleibt geschlossen. Der reale TCN/BiLSTM-Smoke lief mit
`cuda:0` eine Epoche und wurde im selben Run auf zwei Epochen resumed. Beide
Läufe meldeten 468 Cache-Hits; der CUDA-Audit bestätigte die RTX 5070 Ti,
finite Gradienten, Checkpoint-SHAs und Controls mit `T=16/32/48/64` und zehn
Kanälen. Dieser Pfad ist technisch verifiziert, aber weiterhin nicht der
Projekt-Default und kein vollständiger 100-Epochen-Lauf.
