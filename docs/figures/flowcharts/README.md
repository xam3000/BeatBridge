# Flowcharts für die Masterarbeit

**Ergänzung vom 29.10.2026:** Die [Metrik-Erklärbilder 12–23](./METRICS_README.md)
zeigen Eingaben, Berechnung, Gewichtung und Grenzen der Auswahl-Scores,
Render-Metrik, Trainings-Losses, Cue-Ranker-Metriken und Hörbewertung.

Erstellt am **28.10.2026** auf Basis der am 27.10.2026 dokumentierten und
codegeprüften [Gesamtübersicht](../../PIPELINE_UEBERSICHT.md).
Die englischen Beschriftungen passen zur aktuellen englischen Thesis.
Die Dateien sind eigenständige SVGs mit editierbarem Text und Vektorformen;
sie enthalten keine eingebetteten Rasterbilder, Skripte oder externen Assets.

## Abbildungen und vorgeschlagene englische Captions

Die Gesamtübersicht bleibt bewusst kurz. Die Detailabbildungen lassen sich
einzeln in die jeweiligen Methodik-/Implementierungsabschnitte übernehmen.
Die Captions erklären ausgelassene Details und begrenzen die Aussagekraft.

### 01 — Gesamte Pipeline

[01-overall-pipeline.svg](./01-overall-pipeline.svg)

**Caption:** Overview of BeatBridge. Track analysis and automatic or manual
cue selection provide the inputs for transition rendering. Controller
training is a separate workflow that supplies a checkpoint for learned
inference. Technical evaluation and listening studies assess the resulting
variants; they are not steps of every interactive render request.

### 02 — Beat-/Taktanalyse

[02-audio-analysis.svg](./02-audio-analysis.svg)

**Caption:** Beat and bar-grid analysis. Beat positions from librosa are
matched to bar-position metadata from aufTAKT. The versioned merge either
produces a detected grid or records an explicit fallback. Both the grid and
its provenance are cached. Automatic candidate generation rejects approximate
or unknown grids by default.

**Quellen:** [Analysevertrag](../../ANALYSIS_PROTOCOL.md),
[Implementierung](../../../src/analysis/pre_analysis.py).
Die Grafik abstrahiert über Merge-v1 und den additiven Partial-Merge-v2;
sie behauptet keine musikalisch fehlerfreie Downbeat-Erkennung.

### 03 — Automatische Kandidatenauswahl

[03-candidate-selection.svg](./03-candidate-selection.svg)

**Caption:** Automatic song-target and cue-candidate selection. Candidate
generation enumerates bar-boundary combinations for each requested transition
length. Feasibility checks precede feature-based ranking and top-k selection.
Candidate-v1 defaults to two and four bars; Candidate-v2 supports two, four,
six and eight bars with local 4/4 windows. Manually selected GUI cues bypass
this automatic selection workflow.

**Quellen:** [Kandidatenvertrag](../../CANDIDATE_PROTOCOL.md),
[Cue-Ranking](../../RANKING_PROTOCOL.md),
[Songpaar-Ranking](../../SONG_COMPATIBILITY_PROTOCOL.md).
Die vollständigen Pre-/Postfenster, Grid-Provenienz und standardmäßig maximal
15 % relative Tempoabweichung sind harte Bedingungen. High Power,
Non-Overlap, Harmonie, Energie und Klang sind weiche Rankingkomponenten.

### 04 — Featureextraktion

[04-feature-extraction.svg](./04-feature-extraction.svg)

**Caption:** Construction of controller inputs from reusable full-track feature
artifacts. Cue-aligned feature sequences represent the source postroll and
target preroll. Each sequence has 54 channels and is accompanied by 16 global
pair features. Protocol 1 uses T=32; Protocol 2 uses T=16/32/48/64 and a
separate length condition L/8. Feature artifacts and training waveform caches
are distinct data products.

**Quellen:** [Feature-Protokoll 1](../../FEATURE_PROTOCOL.md),
[Feature-Protokoll 2](../../FEATURE_PROTOCOL_V2.md),
[Extractor](../../../src/features/extract_track.py),
[globale Merkmale](../../../src/features/global_pair.py).
Vocal-Separation liefert Hilfsmerkmale und Stems; sie wird nicht als eigener
wissenschaftlicher Lernbeitrag dargestellt. Phrasenkanäle bleiben mit
`phrase_valid=0` deaktiviert. Die Featurefenster werden mit den ausschließlich
aus Train gefitteten Flux-/Onset-Statistiken vervollständigt (Abb. 05).

### 05 — Datensatz und Splittrennung

[05-dataset-construction.svg](./05-dataset-construction.svg)

**Caption:** Dataset export under track-level split isolation. Audio hashes
define the split authority and cross-split pairs are rejected. Normalisation
statistics are fitted on training artifacts only and reused for the exported
splits. Test export depends on the corpus protocol. Dataset files, metadata
and provenance are published in a new versioned root.

**Quellen:** [Dataset-v1](../../DATASET_PROTOCOL.md),
[Dataset-v2](../../DATASET_PROTOCOL_V2.md),
[PRIVE-Erweiterung](../../PRIVE_DATASET_V2_EXTENSION_PLAN.md).
Das Diagramm zeigt die logischen Abhängigkeiten, nicht eine universelle
Ausführungsreihenfolge aller Produzenten: Der PRIVE-v2-Producer wählt bereits
vor der Kandidatenerzeugung nur Targets aus demselben Split. Alle Längen
verwenden dieselbe Splitautorität. Die PRIVE-v2-Erweiterung exportiert keine
Testbeispiele; andere Datasets enthalten getrennte Test-Shards.

### 06 — Selbstüberwachtes Controllertraining

[06-self-supervised-training.svg](./06-self-supervised-training.svg)

**Caption:** Self-supervised feature-to-control learning. The controller
predicts mixing curves that a differentiable renderer applies to cached audio.
A fixed proxy objective supplies gradients for updating controller parameters.
Validation uses the corresponding renderer and objective without a weight
update and determines checkpoint selection. No ground-truth control curves or
human quality labels are required for controller training.

**Quellen:** [Training](../../../src/ml/training.py),
[variabler Trainingsloss](../../../src/ml/variable_training.py),
[fester Runner](../../../src/ml/runner.py),
[Vocal-Runner](../../../src/ml/vocal_runner.py).
Gestrichelte Pfeile zeigen hier ausschließlich Gradienten-/Updatefeedback.
Die reduzierte Zeichnung lässt direkte Hilfseingänge von Features,
Source-/Target-Waveforms und gegebenenfalls Stems in das Objective weg;
sie sind nicht ausschließlich über das gerenderte Audio erreichbar.
Die separate Inferenz aktualisiert keine Gewichte. Der Waveformcache nutzt
11.025-Hz-Stereo für das Training, nicht für alle Audioausgaben.

### 07 — Architektur des festen TCN/BiLSTM

[07-fixed-tcn-bilstm.svg](./07-fixed-tcn-bilstm.svg)

**Caption:** Fixed four-bar TCN/BiLSTM controller. The two feature sequences
share a temporal encoder. Encoded A/B features, their difference and their
element-wise product are concatenated and projected to 256 dimensions.
Projected global features are added at each time step. A two-layer
bidirectional LSTM and a constrained output head produce ten control channels
at each of 32 half-beat positions.

**Quellen:** [Modellvertrag](../../TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md),
[Modellcode](../../../src/ml/model.py).
`A * B` bezeichnet im Diagramm das elementweise Produkt, nicht eine
Matrixmultiplikation. Normierungs-, Aktivierungs- und Dropoutdetails sind
zugunsten der Lesbarkeit ausgelassen. Dies ist die feste Vier-Takt-Architektur,
kein vollständiger Architekturplan der separat längenkonditionierten Variante.

### 08 — Modell-/Renderer-/Objective-Zuordnung

[08-controller-renderer-contracts.svg](./08-controller-renderer-contracts.svg)

**Caption:** Renderer and proxy-objective contracts of the four trained
controller families. The baseline MLP uses a two-band renderer, the fixed
TCN/BiLSTM uses a three-band renderer, and both vocal-aware families use a
stem-aware renderer. The variable controller applies a time-normalised
Objective-v5 adapter. Raw losses from these paths do not form a fair ranking
of model quality.

**Quellen:** [Trainingsimplementierung](../../../src/ml/training.py),
[variabler Pfad](../../../src/ml/variable_training.py),
[Variable-Objective](../../../src/control/variable_differentiable.py),
[Ergebnisevidenz](../../RESULTS_EVIDENCE_LEDGER.md).
Die Kurznamen stehen für `time_shared_mlp_v1`, `vocal_time_shared_mlp_v2`,
`tcn_bilstm_transition_control_v1` und
`variable_tcn_bilstm_transition_control_v1` in dieser Reihenfolge.
Die zehn Diagnosekanäle des variablen Modells bedeuten nicht, dass dessen
EQ-Kanäle im selben Drei-Band-Pfad wie beim festen TCN trainiert werden.
Das Objective gehört zum Trainingsvertrag; bei der Inferenz ist es kein
notwendiger Rendernachschritt.

### 09 — Lokales Bridge-Alignment

[09-variable-bridge-alignment.svg](./09-variable-bridge-alignment.svg)

**Caption:** Local-grid alignment in the variable vocal-aware waveform path.
The source postroll defines the bridge duration. Target mix and vocal preroll
receive the same pitch-preserving Rubber Band transformation. The aligned
windows are rendered with mixing controls and placed between source and
target context. The adjacent high-power sections are not mixed together.

**Quellen:** [Variable-Waveformvertrag](../../VARIABLE_WAVEFORM_CACHE_PROTOCOL.md),
[Bridgegeometrie](../../PIPELINE_UEBERSICHT.md).
Diese Abbildung gilt für `local_grid_target_to_source_v1` im variablen
Vocal-Pfad, nicht pauschal für alle historischen Renderer. Größere
Längenfehler werden verworfen; die dokumentierte Rundungskorrektur erlaubt
nur höchstens zwei Samples am 44,1-kHz-Raster. Die Sample-Raten-Konvertierung
auf 11.025 Hz ist hier ausgelassen. Hard Cut ist eine separate Baseline ohne
ausgedehnte Bridge.

### 10 — Technische und perzeptuelle Evaluation

[10-transition-evaluation.svg](./10-transition-evaluation.svg)

**Caption:** Distinct technical and perceptual evaluation branches. The render
metric reports energy shape, boundary smoothness, harmonic continuity and
rhythmic stability. A separate blinded listening workflow matches context and
peak gain across variants, collects ratings, and reveals method identities
only after the required ratings are complete. Technical scores alone do not
establish perceptual superiority.

**Quellen:** [Render-Metrik](../../RENDERED_TRANSITION_METRIC_PROTOCOL.md),
[Studienvertrag](../../CONTROL_STUDY_PROTOCOL.md),
[Studienauswertung](../../../src/evaluation/analyze_control_study.py),
[Evidenzgrenzen](../../RESULTS_EVIDENCE_LEDGER.md).
Das ist ein Prozessdiagramm, kein Nachweis, dass jeder vorbereitete Hörsatz
bewertet ist. Die ausstehende unabhängige Controller-Hörevaluation bleibt
offen. Direkte Objective-Hör-Gates sind keine Resultate eines gelernten
Controllers.

### 11 — Experimenteller Cue-Ranker

[11-experimental-cue-ranker.svg](./11-experimental-cue-ranker.svg)

**Caption:** Experimental learned cue-ranking extension, verified with
synthetic fixtures only. A split-isolated candidate universe and a frozen
teacher provide labels for a grouped Format-3 dataset. A temporal ranker is
trained with a grouped ranking loss and can supply candidate IDs to the
existing render pipeline. Real-data training and independent musical-quality
evidence remain unestablished.

**Quellen:** [Rankervertrag](../../CUE_RANKER_MODEL_PROTOCOL.md),
[Format-3-Vertrag](../../CUE_RANKER_DATASET_PROTOCOL_V3.md),
[Inferenz](../../../src/ranking/learned_cue_ranker.py),
[Auditstand](../../STATUS.md).
Diese Abbildung gehört in einen Abschnitt zu experimentellen Erweiterungen,
nicht als gleichwertig validierter Bestandteil der Hauptpipeline.
Gestrichelte Umrandung/Pfeile markieren hier den optionalen Inferenzanschluss.
Technische Teacherfehler werden nicht als positive Trainingslabels behandelt;
Guard-Rejections bleiben negative Anker. Teacher-Agreement ist kein
Hörqualitätsnachweis.

## Gestaltung und Nutzung

- **Blau:** Analyse und Auswahl. **Türkis:** Daten und Features.
  **Orange:** Controller und Optimierung. **Violett:** Rendering.
  **Grün:** Objectives und Evaluation. Grau bezeichnet allgemeine
  Ein-/Ausgaben; Rot eine explizite Ablehnung/einen Fallback.
- Die Bedeutung bleibt durch Text und Entscheidungssymbole auch ohne Farbe
  erkennbar. Gestrichelte Verbindungen sind lokal beschriftet bzw. oben in
  der zugehörigen Caption erläutert; sie haben keine universelle Statusbedeutung.
- Jede SVG besitzt einen eigenen `viewBox`, eine nominelle Breite von
  **160 mm**, weißen Hintergrund und Arial mit expliziten Zeilenumbrüchen.
  Haupttexte verwenden 20/22 SVG-Einheiten (etwa 9/10 pt bei 160 mm Breite);
  einzelne Kantenlabels 18 Einheiten. Für den Satz auf Spaltenbreite prüfen,
  ob die Beschriftung noch lesbar ist; die Abbildungen sind für Textbreite
  konzipiert. Sichtbare Diagrammtitel und Abbildungsnummern sind ausgelassen,
  damit die Caption der Arbeit diese Aufgabe übernimmt.
- Farben, Texte, Positionen und Linien lassen sich im SVG oder im Generator
  bearbeiten. Arial muss für dieselbe Textdarstellung verfügbar sein; die
  Schriftdateien werden nicht mitgeliefert. Der SVG-Text bleibt editierbar.
- Die bestehende Thesis und ihre Abbildungsnummerierung wurden nicht geändert.
  Eine LaTeX-Integration oder ein Gesamtbuild wurde für diese SVG-Lieferung
  nicht durchgeführt.

## Reproduktion und Prüfung

Vom Repositoryroot:

```powershell
.venv\Scripts\python.exe -X utf8 docs/figures/flowcharts/generate_flowcharts.py --preview-dir output/flowchart_previews_20261028
```

Der [Generator](./generate_flowcharts.py) schreibt die elf SVGs in diesen
Ordner. Er prüft Nodegrenzen, Font-Glyphen, Textbreiten/-höhen, überlappende
Nodes, orthogonale Verbindungen und Kanten durch fremde Nodes. QtSvg lädt
und rendert jede SVG vollständig. PNG-Prüfbilder, Kontaktbogen und
`verification.json` liegen getrennt im angegebenen Outputordner.

Der Prüflauf verarbeitet keine Audiodateien, Dataset-NPZs oder Modellgewichte.
Die Schriftarten werden für die Windows-Offscreen-Vorschau explizit aus dem
Systemfontordner geladen. Alle elf Diagramme wurden als Kontaktbogen und die
detailreichen Abbildungen zusätzlich einzeln visuell geprüft. Der genaue
Verlauf einschließlich verworfener erster Layout-/Fontversuche steht in
[Bemerkungen.md](../../Bemerkungen.md).
