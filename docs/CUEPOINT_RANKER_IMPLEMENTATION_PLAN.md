# Implementierungsplan: `learned_cue_ranker_v1`

**Stand:** 2026-08-25  
**Status:** verbindlicher Architekturplan, **nicht implementiert**. Dieser Plan
ändert keine bestehenden Modelle, Datensätze, Caches oder Checkpoints.  
**Geltungsbereich:** additive erste Stufe zur Auswahl von Source-Cuepoint,
Target-Cuepoint und – bei mehreren angeforderten Längen –
`transition_length_bars`.

## 1. Ziel und verbindliche Abgrenzung

Der neue Pfad ist eine Auswahlstufe vor dem vorhandenen
`variable_tcn_bilstm_transition_control_v1`:

```text
Beat-/Downbeat-Analyse
  -> bar_grid_v1/v2: nur harte, gültige Kandidaten
  -> learned_cue_ranker_v1: ein Score je Kandidat
  -> globale Top-K-Auswahl je gerichtetem Trackpaar
  -> bestehendes Variable-TCN/BiLSTM-Control-Modell
  -> bestehender Renderer und Objective
```

`learned_cue_ranker_v1` **regressiert keine Samples**. Jeder seiner Ausgänge
referenziert ausschließlich einen bereits akzeptierten `TransitionCandidate`.
Damit bleiben diese Regeln unverändert und dem Modell vorgeschaltet:

- Downbeat-/Bar-Alignment, vollständige vier Fenster, Metrum, Tempo-Limit,
  Grid-Provenienz und `approximate_grid_policy`;
- der Candidate-v2-Längenvertrag `{2, 4, 6, 8}` und die daraus abgeleiteten
  Beats und Halbbeat-Schritte;
- die lokale Grid-Ausrichtung `local_grid_target_to_source_v1` im
  Waveform-/Rendererpfad;
- alle existierenden Candidate-, Feature-v1/v2-, Dataset-v1/v2- und
  Control-Model-Verträge.

**Bestätigte Invariante (Review 2026-08-25):** Im aktuellen Code erzeugt
`bar_grid_v2_length_specific` einen Cue nur aus einer `CutPoint`-Boundary,
prüft alle vier vollständigen Fenster und lehnt unter der Default-Policy jede
Grid-Provenienz ab, deren `fallback_used` nicht exakt `false` ist. Diese
Invariante gilt für den gelernten Pfad nur dann fort, wenn er ausschließlich
v2-Candidates mit `approximate_grid_policy="reject"` akzeptiert. Ein
`--cue-ranker learned_cue_ranker_v1`-Lauf mit `allow`, unbekannter
Grid-Provenienz, fehlendem `beat_grid_sha256`, nicht-4/4 oder einem von v2
abweichenden Generator ist daher ein harter Preflight-Fehler, kein
Experiment-Opt-in. Der Ranker erzeugt nie eigene Cues oder korrigiert
Cutpoint-Samples.

Bei genau einer angeforderten Länge ist diese Länge weiterhin ein harter
Nutzer-Constraint. Werden mehrere bereits zulässige Längen angefordert, liegen
ihre Kandidaten in derselben Ranggruppe; die ausgewählte Candidate-ID bestimmt
dann auch die Länge. Das ist die einzige Bedeutung von „Länge auswählen“.

Der bestehende Testsplit bleibt versiegelt: Er wird weder als Kandidaten-
Manifest geöffnet noch als Feature-, Waveform- oder Teacher-Artifact
materialisiert. Die Split-Autorität darf lediglich die Test-SHAs als
Abweisungsmenge enthalten. Das Format-3-Root schreibt absichtlich keinen
`test/`-Shard und keine Test-Counts.

## 2. Festgelegte Entscheidungen

| Frage | Entscheidung | Begründung |
|---|---|---|
| Modellgrenze | Eigenes `learned_cue_ranker_v1` vor dem Control-Modell | Cue-Auswahl und zeitabhängige Controls haben andere Ausgaben, Lernsignale, Caches und Fehlermodi. |
| Encoder | Wiederverwendung von Feature Protocol 2 und der TCN-Form, aber **keine** geteilten Gewichte oder Aktivierungen mit dem Control-Modell | Der Ranker kann günstig alle Kandidaten scoren und bleibt trainierbar, ohne eine Änderung des Control-Objectives oder dessen Checkpoints zu erzwingen. |
| Dataset | Neuer, separater **Cue-Ranker Dataset Format 3** | Eine variable Kandidatenliste pro gerichtetem Paar samt Teacher-Labels lässt sich nicht korrekt als v2-Top-K-Einzelbeispiel ausdrücken. |
| Lernziel | debiaster, gruppierter Soft-Target-Listwise-Loss | Die Aufgabe ist „besten Kandidaten innerhalb einer Liste wählen“, nicht unabhängige binäre Klassifikation. |
| Teacher | eingefrorener Control-Checkpoint + eingefrorener Renderer + zeitnormalisiertes Objective v5; kein gleichzeitiges Teacher-Training | Der Score beschreibt die Qualität, die der tatsächlich nachgeschaltete Controller unter einem festgehaltenen Vertrag erreicht. |
| `feature_baseline_v3` | Baseline und Sampling-Stratifikation; **kein** Bestandteil des Teacher-Targets, kein Ranker-Feature und kein stiller Inferenz-Fallback | Der vollständige Universumsindex beseitigt die aktuelle *Top-K-Auswahl* als Trainingsfilter. Das beweist noch nicht, dass der Ranker keine mit der Heuristik korrelierende Funktion lernt; das wird nur durch die festgelegten Baselines/Ablationen bewertet. |
| Skalierung | vollständiger leichter Kandidatenindex, aber Teacher-/Featurearbeit nur auf reproduzierbar stratifizierten Gruppen-Samples | Rund 1,9 Mio. vollständige Render-/Objective-Aufrufe und Waveform-Caches wären nicht vertretbar. |
| Testsplit | SHA-sealed und nie gelesen | Train/Validation bleiben SHA-isoliert; der Testsplit wird nicht implizit durch Export oder Cachebau verbraucht. |

## 3. Modellinput und Architektur

### 3.1 Candidate-Input

Für jeden akzeptierten Kandidaten `c` werden die bestehenden variablen Fenster
verwendet, nicht erneut aus Rohsamples gelernt:

```text
features_a[c]       float32 (T, 54)  # Source-Postroll ab Source-Cue
features_b[c]       float32 (T, 54)  # Target-Preroll bis Target-Cue
global_features[c]  float32 (16,)
length_condition[c] float32 (1,) = L / 8
```

`T` ist weiter exakt `16/32/48/64` für `L=2/4/6/8`. Die 54 Kanäle, die 16
globalen Features, die Validitätskanäle und die Trainings-only-Normalisierung
bleiben unverändert. Source-/Target-Audio, Vocal-Stems und Rohsamplepositionen
sind keine Ranker-Eingaben.

Zusätzlich erhält der Ranker einen versionierten
`candidate_context_v1`-Vektor. Er enthält nur Informationen, die bei der
Kandidatengenerierung bzw. Feature-Provenienz bereits vorliegen:

| Teil | Werte | Zweck |
|---|---|---|
| Cue-Position | pro Seite normierter `bar_index`, vollständige Takte vor/nach dem Cue relativ zur Trackabdeckung | Intro-/Outro- und Randkontext sichtbar machen, ohne Sample-Koordinaten zu lernen |
| Kandidatenraum | Anzahl zulässiger Source-/Target-Boundaries für diese Länge, Anzahl aller Kandidaten der Gruppe, jeweils `log1p`-skaliert | Die Dichte des tatsächlich verfügbaren Auswahlraums sichtbar machen |
| Grid-/Metrumkontext | Source-/Target-Grid-Quelle als kleine kategoriale Embeddings, Match-Confidence, `fallback_used`, Zähler/Metrum | Provenienz bleibt kontrollier- und auditierbar; unter der Default-Policy sind Fallback-Bits stets null |
| lokale Zeitdiagnostik | pro Seite Abweichung der lokalen Gridfensterdauer von der globalen BPM-Daueratio | Erlaubt dem Score, schwierige lokale Anpassungen zu erkennen; die lokale Griddauer bleibt trotzdem Renderer-Autorität |
| Länge | der separate, validierte `length_condition` | Identische Bedeutung wie im variablen Control-Modell; nicht in die 16 globalen Features geschoben |

Die genaue Reihenfolge, Normalisierung, Kategorien und Missingness-Regeln
werden vor Code in einem neuen Modellvertrag eingefroren. Trackpfade, Audio-
SHAs, `candidate_id`, absolute Samples und `group_id` sind ausschließlich
Provenienz/Index und dürfen nie als lernbare Eingabe dienen.

### 3.2 `CueRankerTemporalModel`

Der Ranker verwendet die bewährte zeitliche Repräsentationsform, ist aber ein
eigenes Modell mit eigenem `state_dict`:

```text
A/B (T, 54)
  -> gemeinsamer TCN innerhalb des Rankers: Conv1d 54 -> 64 -> 128,
     dilated Conv1d 128 -> 128, GELU
  -> [A, B, A-B, A*B] je Halbbeat -> Linear 512 -> 192
  + Projektion(global_features: 16 -> 192)
  + Projektion(length_condition: 1 -> 192)
  -> attention-gewichtetes Mean-Pooling + Masked-Max-Pooling über T
  -> Kandidatenrepräsentation

candidate_context_v1 + Grid-Embeddings -> MLP -> 64
Kandidatenrepräsentation + Kontext -> MLP(256, 64) -> scalar score s(c)
```

Die A/B-Gewichte sind **innerhalb des Rankers** geteilt. Der existierende
`VariableTCNBiLSTMTransitionControl.shared_tcn_encoder` wird weder importiert
noch aktualisiert; insbesondere gibt es keinen gemeinsamen Encoder und keinen
Control-Head. Das vermeidet, dass eine Ranking-Iteration die nachweislich
reproduzierbaren Control-Checkpoint-Ausgaben verändert. Eine spätere
distillierte oder eingefrorene Encoder-Initialisierung wäre ein eigener
Versionsschritt, nicht Teil von v1.

Das Modell gibt pro Candidate genau einen unbeschränkten endlichen Skalar aus.
`group_id` wird erst im Loader zum gruppierten Loss benutzt. Das Modell erzeugt
weder eine Cue-Koordinate noch Controls.

## 4. Cue-Ranker Dataset Format 3

### 4.1 Warum nicht Dataset v2 erweitern

Dataset v2 ist absichtlich ein homogener, einzelner Feature→Control-Record
pro Zeile und exportiert heute nur `top_k_per_pair` nach
`feature_baseline_v3`. Diese Vorauswahl würde ein Modell nur auf Beispiele
trainieren lassen, die die alte Heuristik bereits bevorzugt. Außerdem kann ein
NPZ-Shard mit Einzelbeispielen weder die vollständige, längenübergreifende
Ranggruppe noch Sampling-Wahrscheinlichkeiten ausdrücken.

Format 3 ist deshalb ein neuer, additiver **Index-/Ranking-Datensatz**. Feature
Protocol 2 und die Volltrack-Caches werden wiederverwendet; die v2-Datensätze
und Loader werden nicht geändert.

### 4.2 Identitäten, Gruppen und Provenienz

Eine Gruppe umfasst alle akzeptierten Kandidaten eines gerichteten Trackpaars
unter einem identischen Candidate-Universum:

```text
group_id = sha256(
  "cue_ranker_group_v1" |
  source_audio_sha256 | target_audio_sha256 |
  candidate_generator | candidate_request_config_sha256 |
  canonical_group_member_identity_sha256
)
```

Source und Target bleiben geordnet; `A -> B` und `B -> A` sind verschiedene
Gruppen. Kandidaten aller angeforderten Längen liegen in derselben Gruppe,
weil sie im automatischen Längenmodus konkurrieren. Bei einer einzelnen
Nutzerlänge enthält die Gruppe nur diese Länge. Die Member-Identity ist der
kanonisch sortierte, vollständige Satz aus der **vollen** Candidate-Identity
(Generator, beide Audio-SHAs, beide Cues mit Sample/Beat/Bar/Metrum,
Länge/Beats und Grid-Hashes), nicht nur der heutige 16-hex-stellige
`candidate_id`. Damit entsteht keine Zirkularität zwischen `group_id` und dem
Manifest, und eine ID-Kollision oder zwei abweichende Kandidaten mit derselben
ID führt zu einem harten Exportfehler.

Jeder Candidate-Indexeintrag führt mindestens:

- `group_id`, deterministische `candidate_id` und eine gruppenlokale,
  nach `candidate_id` sortierte Reihenfolge;
- Source-/Target-Audio-SHA, `source_cutpoint` und `target_cutpoint` mit
  Sample-, Beat-, Taktindex und Metrum;
- `transition_length_bars`, `transition_length_beats`, `sequence_length` und
  `length_condition`;
- Candidate-Format, Generator, Anfrage-/Hard-filter-Hash, Source-/Target-
  Gridprovenienz einschließlich Grid-Hash;
- Referenzen und Manifest-SHAs der vollständigen Source- und
  tempoausgerichteten Target-Featureartefakte;
- vorhandenen `feature_baseline_v3`-Score/Rang oder expliziten
  `baseline_status=unscored`; und
- Sampling-Stratum, exakte Einschlusswahrscheinlichkeit sowie späteren
  Teacher-Status und Teacher-Score.

Ein Gruppenrecord enthält gemeinsame Track-/Grid-/Pair-Manifest-Provenienz,
Größe des vollständigen Universums und Größe des gelabelten Samples. So bleibt
eine Candidate-ID mit Cuepoint und Grid lückenlos erklärbar, ohne Trackdaten
pro Zeile zu duplizieren.

### 4.3 Dateiformat und sealed split

```text
<cue-ranker-dataset-v3>/
  manifest.json
  groups/
    train.jsonl
    validation.jsonl
  index/
    train-candidates-00000.npz
    validation-candidates-00000.npz
    train-ragged-groups.npz
    validation-ragged-groups.npz
  teacher/
    train-labels-00000.npz
    validation-labels-00000.npz
  normalization/
    train_only_stats.json
```

Die Candidate-Shards enthalten kompakte, spaltenorientierte IDs, Cue-/Längen-
und Kontextfelder sowie Cache-Referenzen; sie duplizieren keine `(T,54)`-
Tensoren. Der Loader löst Fenster erst beim Sample aus den hashgebundenen
Volltrack-Artefakten auf und wendet die manifestierte
Trainings-Normalisierung an. Das hält den Format-3-Index bei 1,9 Mio.
Kandidaten handhabbar.

`*-ragged-groups.npz` enthält `group_ids`, `group_offsets` mit Länge `G+1`
und `member_row_ids`. Damit darf jede Gruppe unterschiedlich viele Kandidaten
und Längen enthalten. Pro Trainingsschritt werden die betroffenen Kandidaten
nach `T` in höchstens vier homogene Mikrobatches geteilt; ihre Scores werden
danach wieder zur ursprünglichen Gruppe zusammengesetzt.

Eine eingefrorene Audio-SHA-Split-Map bleibt die einzige Autorität. Der
Format-3-Exporter liest vor dem Öffnen eines Pair-Manifests dessen
Source-/Target-SHA aus einem neuen leichten, selbst gehashten Root-`pair_index`;
nur Paare mit zwei **gleichen**, nicht-Test-Splits (`train/train` oder
`validation/validation`) dürfen geöffnet werden. Der Index enthält selbst
keine Test-Pair-Referenz, Test-Count oder Test-Statistik. Er wird beim
ursprünglichen, split-autorisierten Train/Validation-Export atomar geschrieben
und bindet Pair-Manifestpfad, Pair-Manifest-SHA, beide Audio-SHAs,
Generator-/Request-Hash und seine eigene Split-Map-SHA. Paare mit Test-SHA
werden schon vor einer Pair-Manifest-Referenz verworfen. Fehlt dieser Index
bei einem historischen Root, bricht der Export mit
`sealed_test_pair_index_required` ab; er darf nicht ersatzweise Root- oder
Pair-Manifeste inspizieren. Der Dataset-Root enthält nur
`test: {"state": "sealed_not_materialized"}`.

**Korrigierte Entscheidung (Review 2026-08-25):** Der aktuelle
`variable_dataset_export.py` entdeckt und öffnet zunächst alle completed
Pair-Manifeste und trennt erst danach nach Audio-SHA; er ist deshalb kein
sicherer Ausgangspunkt für Format 3. Der neue Pfad darf weder diese Discovery
noch deren Fallback wiederverwenden.

## 5. Sampling und Rechenbudget

### 5.1 Vollständiges Universum, kein Heuristik-Top-K

Der Universums-Builder übernimmt **alle** vom `bar_grid_v2_length_specific`
akzeptierten Kandidaten einer erlaubten Train-/Validation-Gruppe. Er ruft
nicht `_select_variable_candidate_records()` auf und schneidet nicht
`choices[:top_k_per_pair]` ab. `feature_baseline_v3` wird nur aus dem
vorliegenden Pair-Manifest gelesen, nicht erneut als Auswahlregel ausgeführt.

Für jede Gruppe wird danach ein hash-deterministisches, stratifiziertes
Teacher-Sample gezogen. Die anfängliche Quote lautet:

```text
q_g = min(512, max(128, ceil(16 * sqrt(n_g))))
```

mit `n_g` als Größe des vollständigen Kandidatenuniversums. Für typische
Gruppen der Größenordnung 20.000–25.000 ergibt dies 512 statt zehntausender
Renderaufträge. Die Slots verteilen sich zuerst auf die disjunkten
gruppeninternen `feature_baseline_v3`-Quantile `[0,.1)`, `[.1,.4)`,
`[.4,.7)`, `[.7,.9)`, `[.9,1]` mit den Anteilen `10/20/30/25/15 %`.
Unscored-Candidates erhalten ein eigenes Stratum mit bis zu 5 % der Slots;
leere Strata werden deterministisch auf die übrigen Strata verteilt.

Die Auswahl erfolgt per kleinster stabiler Priorität
`sha256(seed | group_id | stratum | candidate_id)`, nicht über eine
prozessabhängige Zufallsreihenfolge. Jedes Manifest speichert Stratumgröße,
gezogene Quote, Seed und Einschlusswahrscheinlichkeit `q_h / n_h`. Damit sind
gute, mittlere und schlechte Kandidaten reproduzierbar vertreten und die
nachfolgende Listwise-Schätzung kann die bewusste Stichprobe nur als
selbstnormalisierte inverse-probability-Näherung korrigieren. Die Quote wird
erst nach vollständiger, deterministischer Stratumzählung zu ganzzahligen
`q_h` aufgelöst; leere Strata, Restplätze und `q_h=0` werden explizit
gespeichert. Jede für den Loss verwendete Row muss `0 < p_inclusion <= 1`
haben. Eine Behauptung exakt unverzerrter Softmax- oder NDCG-Schätzung aus
diesem festen Teilsample ist verboten.

### 5.2 Caches und Teacher-Durchsatz

Es gibt drei Ebenen, alle unter neuen Roots und atomar:

1. bestehende Volltrack-Feature- und Vocal-Artefakte bleiben wiederverwendbar;
2. `cue_ranker_window_v1` speichert nur hashgebundene, normalisierte
   Featurefenster für tatsächlich gelabelte/trainierte vollständige
   Candidate-Identitäten;
3. `cue_ranker_teacher_waveform_v1` speichert nur für diese IDs die vier
   exakt ausgerichteten 11.025-Hz-Waveforms. Sein Key enthält vollständige
   Candidate-Identity, Source-/Target-Featurepayload- und -Manifest-SHA,
   beide Grid-Hashes samt Boundary-Indizes, Audio- und Stem-Payload-SHAs,
   `local_grid_target_to_source_v1`, die exakte lokale Source-Fensterdauer,
   Rubber-Band-Backend-/Executable-SHA, Teacher-Release-SHA,
   Renderer-/Objective-Code- und Konfigurations-Hashes sowie Normalizer-SHA.

**Bestätigte Invariante (Review 2026-08-25):** Der vorhandene v2-Cache
verwendet bereits `local_grid_target_to_source_v1`: Die Source-Griddauer ist
die Ausgabeautorität, das Target wird auf diese lokale Dauer gestretcht und
die globale BPM-Ratio ist nur Diagnose. Der Cue-Ranker darf diese Geometrie
weder mit einer BPM-Ratio ersetzen noch nur als Cache-Text führen. Jeder
Teacher-Cache-Hit muss die genannten Boundary-/Grid-/Payload-Hashes erneut
prüfen; ein Alignment-, Backend-Rundungs- oder Renderfehler wird als
technisch fehlgeschlagenes Label protokolliert.

Die v2-Waveform-Caches werden nicht umgedeutet, weil ihr Key an Dataset v2
gebunden ist. Ein bevorstehender großer Lauf erhält zuerst eine dokumentierte
1.000-Candidate-Pilotmessung auf **Train/Validation**: GPU-Zeit pro Länge,
Cache-Bytes pro Candidate, Cache-Hit-Rate, Rejects und Spitzen-VRAM. Erst
danach darf die Quote erhöht werden; 1,9 Mio. Waveform-Caches oder
Objective-Auswertungen sind ausdrücklich kein v1-Ziel.

**Offenes Risiko / Stopbedingung (Review 2026-08-25):** 1,9 Mio. sind bislang
nur als Größenordnung für einen spaltenorientierten Vollindex plausibel, nicht
als bestätigte Laufzeit- oder Speicherzusage. Vor dem Pilot müssen im Vertrag
harte Budgets für Peak-RAM, Peak-VRAM, GPU-Sekunden/Candidate, Bytes/Candidate
und maximale technische Failure-Rate stehen. Fehlt eines dieser Budgets oder
überschreitet der 1.000-Candidate-Pilot eines davon, STOPP: keine
Quotenerhöhung, kein Großlauf und insbesondere kein Versuch, alle Candidates
zu rendern/cachen. Der Vollindex muss die Zahlen ohne Feature-Tensor- oder
Waveform-Duplikate und mit einer gemessenen Worst-Group-Chunkgröße ausweisen.

### 5.3 Hard Negatives

**Korrigierte Entscheidung (Review 2026-08-25):** Im v1 wird kein
candidate-weises Hard-Negative-Subsampling innerhalb einer Listwise-Gruppe
verwendet. Es würde die manifestierte Einschlusswahrscheinlichkeit verändern,
die Gruppen-Softmax auf einen modellabhängigen Teil der Liste beschränken und
damit den angegebenen Loss ungültig machen. Jeder Listwise-Schritt verwendet
alle gelabelten, loss-zulässigen Mitglieder seiner Gruppe (nach Länge in
Mikrobatches, danach wieder exakt zusammengesetzt). Zulässig ist nur ein
deterministischer **Gruppen**-Scheduler oder ein separater, klar gewichteter
Pairwise-Hilfsterm in einer späteren Version.

Ein optionaler zweiter Mining-Durchlauf ist frühestens nach einer
Validation-Entscheidung und nur für **Train**-Gruppen erlaubt: maximal 16
bisher ungelabelte, modellseitig hoch gerankte Candidates pro Gruppe werden
vom **identischen eingefrorenen** Teacher gelabelt. Der Validation-
Candidate-/Labelsnapshot bleibt vollständig geschlossen. Mining erzeugt ein
neues Train-Dataset-/Teacher-Manifest, ersetzt keine vorhandenen Labels und
ist nie Grundlage für die primäre Validierungsmetrik. Ein gleichzeitig
trainierter oder nach Ranker-Ergebnis veränderter Teacher ist verboten.

## 6. Teacher, Lernsignal und Schutz vor Reward-Hacking

### 6.1 Eingefrorener Offline-Teacher

Die Teacher-Pipeline ist exakt:

```text
Candidate-Fenster
  -> SHA-geprüfter best.pt von variable_tcn_bilstm_transition_control_v1
  -> DifferentiableVocalAwareRenderer
  -> VariableVocalAwareTransitionObjective (Objective v5, zeitnormalisiert)
  -> teacher_utility
```

Der Teacher-Controller wird im Eval-Modus verwendet; es gibt keine
Direktoptimierung der Controls und keine Gradienten in diesem Job. Der
Datasetauftrag verlangt einen Checkpoint mit `weights_only=True`-Load sowie
Run-Manifest- und Checkpoint-SHA. Modellname/-format, Checkpoint-SHA,
Dataset-/Cache-Shas, Renderer-, Alignment-, Objective- und
Normalizer-Konfiguration bilden den unveränderlichen `teacher_contract_sha`.
Zusätzlich erzeugt die Auswahl einen unveränderlichen
`teacher_release.json`: Controller-Checkpoint- und Producer-Run-Manifest-SHA,
State-dict-Schlüssel-/Tensorform-Hash, Python/PyTorch-/NumPy-Version,
Device, deterministische Torch-Flags, CUDA/cuDNN-Tupel (falls GPU),
Rubber-Band-Backend/Executable-SHA sowie Renderer-/Objective-Code- und
Konfigurations-Hashes. CPU ist der bitgenaue Referenzmodus; ein GPU-Release
ist nur mit identischem Environment und vorab festgelegter numerischer
Toleranz reproduzierbar. Ein abweichender Release erzeugt einen neuen Teacher,
nie ein Resume desselben Labelroots.
Ein erst noch auszuwählender produktiver best.pt wird als explizite
Voraussetzung übergeben; ein zweiepochiger Smoke-Checkpoint ist kein
stillschweigender Default.

Für einen technisch gültigen Candidate ist die rohe Lehrgröße
`u(c) = - total_loss_v5(c)`. Die Loss-Version ist bereits längennormalisiert;
der Labeljob muss trotzdem pro Länge Mittelwert, Streuung und
Gruppenverteilung berichten. Kandidaten mit nichtendlichen Controls/Waveforms,
Vertragsbruch oder Renderfehler erhalten keinen künstlichen guten Score,
sondern `teacher_status=failed` und sind für positive Listen unzulässig.

Als unabhängige Offline-Schutzprüfung wird das gerenderte Ergebnis zusätzlich
mit der eingefrorenen `rendered_transition_baseline_v1` bewertet. Ein
technisch gültiger Teacher-Label benötigt `render_guard_score >= 0.50` und
keine Guard-Fehler; andernfalls ist der Candidate als
`teacher_status=guard_rejected` ein dokumentierter schlechter Kandidat. Der
Guard ist nicht differenzierbar, nicht trainierbar und wird nie während eines
Ranker-Laufs umgewichtet.

### 6.2 Listwise Soft Target

Die primäre Loss ist ein gruppierter Soft-Target-Listwise-Cross-Entropy-Loss,
nicht eine Regression eines absoluten Qualitätswerts. Für die gelabelten,
nicht abgewiesenen Kandidaten `i` einer Gruppe gilt:

```text
q_i = softmax((u_i / tau_teacher) - log(p_inclusion_i))
p_i = softmax((s_i / tau_model) - log(p_inclusion_i))
L_g = - sum_i q_i log(p_i)
L = mean_g(L_g)
```

`tau_teacher` und `tau_model` sind vor dem Start im Run-Manifest fixierte,
positive Konfigurationswerte. Die `- log(p_inclusion)`-Terme bilden eine
selbstnormalisierte Horvitz-Thompson-artige Näherung für das absichtlich
stratifizierte **Labelsample**, keine exakte Entbiasing-Garantie. `L` mittelt
zuerst über Gruppen, damit Gruppen mit vielen zulässigen Downbeats nicht
dominieren. Guard-Rejections bleiben als negativer Anker mit
`u_guard_g = min(u_finite,g) - guard_margin`; `guard_margin` ist positiv und
Teil des Teachervertrags. Hat eine Gruppe kein endliches Teacher-Label oder
weniger als zwei loss-zulässige Mitglieder, wird sie nicht trainiert und als
`group_status=insufficient_teacher_support` gezählt. Technische
`failed`-Rows bleiben aus Loss **und Qualitätsmetriken** ausgeschlossen; sie
bleiben jedoch im Universumsindex samt kanonischem Fehlercode, Cache-/Backend-
Provenienz und Zähler erhalten. Eine technische Failure-Rate oberhalb der
festgelegten Stop-Schwelle wird nicht weggemittelt.

`feature_baseline_v3` ist weder in `u` noch in `q` enthalten. Für jede
Validation-Gruppe werden auf derselben loss-zulässigen, fest gelabelten Liste
vier deterministische Ranking-Baselines berichtet: (1) uniformer Zufall mit
fest manifestierten Seeds und Mittelwert/Konfidenzintervall, (2)
`feature_baseline_v3` mit dokumentierter Tie-Break-Regel, (3) der Ranker und
(4) Oracle/Teacher als obere, nicht deploybare Referenz. Gemessen werden
Top-1-/Top-K-Teacher-Utility, NDCG, MRR und Guard-Rate; außerdem die
Verbesserung des Rankers gegenüber der Heuristik je Gruppe. Ohne eine spätere
unabhängige Hörstudie bleiben diese Werte Teacher-Übereinstimmung, kein
Musikqualitätsbeweis. Nur ein vorab festgelegter Nichtunterlegenheits- und
Verbesserungsgate gegenüber `feature_baseline_v3` darf die Aussage stützen,
dass der Ranker mehr als dessen Auswahlmuster lernt.

Die primäre Cue-Ranking-Evaluation bleibt dabei von der Online-Ausführung des
Control-Modells getrennt: Sie konsumiert nur eingefrorene Teacher-Labels und
Ranker-Scores auf dem validierten Candidate-Snapshot. Eine spätere
End-to-End-Renderer-Auswertung ist eine separat benannte sekundäre Metrik und
darf den Ranker-Checkpoint, den Teacher oder die Auswahlregel nicht ändern.

Die vier Schutzlinien gegen Objective-Reward-Hacking sind damit: fester
Teacher-Checkpoint, fester Renderer/Objective-Vertrag, unabhängiger gefrorener
Render-Guard und eine später getrennte Hör-/neue-SHA-Evaluation. Weder
Ranker-Gradienten noch Validation-Ergebnisse dürfen den Teacher oder seine
Gewichte im selben Datensatz verändern.

## 7. Training, Checkpoints und Inferenz

### 7.1 Gruppierter Loader und Runvertrag

`CueRankerGroupedDataset` liest nur `train` bzw. `validation`, löst
Featurefenster cache-first auf und gibt variable Gruppen zurück. Ein Optimizer-
Batch enthält mehrere Gruppen; jede Gruppe wird intern nach Länge geteilt und
anschließend wieder zusammengesetzt. Es gibt kein Zeitpadding im v1-Basispfad
und keine Cross-Group-Softmax.

Der Run speichert atomar `manifest.json`, `history.json`, `best.pt` und
`latest.pt`, jeweils mit SHA. Die Manifest-SHA steht in einer atomar
geschriebenen externen Datei `manifest.sha256` (nicht zirkulär im Manifest);
das Manifest enthält SHA-256 und Bytezahl von History und beiden
Checkpoints. Der Vertrag umfasst mindestens Dataset- und Teacher-Manifest-SHA,
Feature-/Kontextschema-Hash, Split-Map-Hash, Normalizer-SHA,
Auswahl-/Hard-Negative-Plan, Modellkonfiguration, Device, Seeds, alle Längen,
Objective-/Guard-Konfiguration und Code-/Modelnamen sowie Universumsindex-,
Gruppenindex-, Pair-Index-, Teacher-Release-, Featurecache-, Grid-,
Stem-Payload-, Alignment- und Software-/Backend-Hashes. Resume verifiziert
alle diese Artefakte, ihre Hashalgorithmen und die externe Manifest-SHA vor
`weights_only=True`; ein veränderter Cache ist kein Hit.

Validation bestimmt Early Stopping über den listweisen Loss und berichtet
zusätzlich die oben genannten Teacher-/Guard-Metriken. Sie ändert weder
Normalisierung noch Samplingplan. Der Testsplit ist weder eine Loader-Option
noch ein versteckter Default.

### 7.2 Inferenz und Rückwärtskompatibilität

`learned_cue_ranker_v1` scoret alle bereits akzeptierten Kandidaten eines
gerichteten Paars in längenhomogenen Chunks, führt sie wieder zu einer globalen
Liste zusammen und sortiert deterministisch nach `(-score, candidate_id)`.
Die ersten K Candidate-IDs werden unverändert an den vorhandenen
Control-/Rendererpfad übergeben. Bei mehreren Längen kann die Top-K-Liste
verschiedene Längen enthalten; bei einer einzigen angeforderten Länge nicht.

Neue Pair-Manifeste führen zusätzlich ein strikt versioniertes
`cue_ranking`-Objekt mit `ranker=learned_cue_ranker_v1`, Checkpoint-/Run-SHA,
Dataset-/Teacher-Vertrag, Request-Längen, Zahl gescorter/ausgewählter
Kandidaten, Scores und Fehlern. Es enthält `selection_candidate_ids` als
eindeutige Autorität, einen `renderability_preflight` je Kandidat und
Backfill-Entscheidungen. Schlägt der nachgelagerte Controller-/Rendererpfad
für einen ausgewählten Kandidaten technisch fehl, wird dieser nicht als
schlecht gelabelt: der Fehler wird kanonisch protokolliert, der Kandidat
übersprungen und deterministisch mit dem nächsten erfolgreich vorgeprüften
Candidate aufgefüllt. Bei weniger als K renderbaren Kandidaten ist das
Ergebnis partiell und sichtbar, nie still erfolgreich.

Das bestehende `candidate_ranking`-Objekt für `feature_baseline_v3` bleibt für
historische Batches byte- und semantikgleich. Ein gelernter Lauf verwendet
eine neue, additive `cue_ranking.format_version`; er überschreibt weder
`candidate_ranking` noch dessen `total_score`. Adapter lesen ausschließlich
`cue_ranking.selection_candidate_ids`, sodass historische Renderer/Auswerter
nicht versehentlich gelernte Scores als Heuristikwerte interpretieren.

Vorgesehene CLI-Ergänzungen:

```powershell
# Nur Train/Validation; der Befehl verweigert Legacy-Roots ohne pair_index.
.venv\Scripts\python.exe -m src.features build-cue-ranker-universe <batch-root> <universe-root> --split-map <map>
.venv\Scripts\python.exe -m src.ml label-cue-ranker-teacher <universe-root> <teacher-run> <label-root>
.venv\Scripts\python.exe -m src.features export-cue-ranker-dataset <universe-root> <label-root> <dataset-root>
.venv\Scripts\python.exe -m src.ml train-cue-ranker <dataset-root> <run-root> --device cuda:0

# Standard bleibt feature_baseline_v3; learned ist ein expliziter Opt-in.
.venv\Scripts\python.exe -m src.multi_batch_render <tracks> --cue-ranker learned_cue_ranker_v1 --cue-ranker-run <run-root>
```

`--cue-ranker feature_baseline_v3` bleibt Default. Fehlen learned-Checkpoint,
Vertrag oder Cache, bricht der explizit gelernte Modus mit begründetem Fehler
ab; er fällt nicht still auf die Heuristik zurück. Ein bewusster
`--cue-ranker feature_baseline_v3`-Lauf bleibt jederzeit möglich.

## 8. Datei-für-Datei-Arbeitspakete

| Paket | Dateien | Änderung und Abnahmepunkt |
|---|---|---|
| A – Verträge | neu `docs/CUE_RANKER_DATASET_PROTOCOL_V3.md`, neu `docs/CUE_RANKER_MODEL_PROTOCOL.md`, diese Plan-Datei, später `docs/CLI.md` | Format 3, Kontextschema, Teachervertrag, sealed-test-Regel und CLI vor Code einfrieren. Keine Änderung von v1/v2-Semantik. |
| B – Kandidatenindex | `src/multi_batch_render.py`, `src/batch_render.py`, neu `src/features/cue_ranker_universe.py`, `src/features/__main__.py` | Neuer Root-`pair_index` mit SHA-Deklaration vor Pair-Manifestzugriff; vollständiger, leichter Universumsindex ohne heuristisches Top-K. Historische Batches bleiben lesbar; learned Export verweigert fehlenden sicheren Index. |
| C – Format 3 | neu `src/features/cue_ranker_dataset.py`, `src/features/cue_ranker_context.py`, `src/features/__init__.py`, `src/features/__main__.py` | Deterministische Strata, ragged Gruppenindex, Cache-Referenzen, train-only Normalizer und atomarer Export. `variable_dataset_export.py` bleibt für Dataset v2 unverändert. |
| D – Teacher | neu `src/ml/cue_ranker_teacher.py`, ggf. kleine additive Leser in `src/ml/variable_runner.py` und `src/ml/variable_waveform_cache.py`, `src/ml/__main__.py` | SHA-verifizierter frozen Controller, v5-Renderer/Objective, Render-Guard, getrennte Teacher-Caches und label sidecars. Keine Optimizer-Schritte, keine Test-I/O. |
| E – Ranker-Modell | neu `src/ml/cue_ranker_model.py`, neu `src/ml/cue_ranker_data.py`, neu `src/ml/cue_ranker_runner.py`, `src/ml/__init__.py`, `src/ml/__main__.py` | Geteilter A/B-TCN nur im Ranker, scalar head, ragged/listwise Training, Checkpoint-/Resume-Vertrag. `variable_model.py` und der Control-Checkpoint bleiben unverändert. |
| F – Inferenzintegration | neu `src/ranking/learned_cue_ranker.py`, `src/ranking/__init__.py`, `src/batch_render.py`, `src/multi_batch_render.py`, optional `src/pipeline.py` | Explizite Rangerauswahl, deterministische Top-K und `cue_ranking`-Manifestprovenienz; danach unveränderte Candidate→Control→Renderer-Übergabe. |
| G – Doku-/Statuspflege | `docs/ML_MODEL_CURRENT_STATE.md`, `docs/STATUS.md`, `docs/Bemerkungen.md` | Erst nach realer Implementierung/Verifikation Modellübersicht und Status aktualisieren; jeden tatsächlich ausgeführten Testlauf nach Repositoryregel in Bemerkungen dokumentieren. |

## 9. Geplante Tests und Abnahmekriterien

Neue synthetische Tests werden in getrennten Dateien angelegt; in dieser
Planungssession werden **keine Tests ausgeführt**.

| Testdatei | Kernprüfungen |
|---|---|
| `tests/test_cue_ranker_universe.py` | alle akzeptierten v2-Candidates werden indexiert; keine `top_k_per_pair`-Beschneidung; nichtzirkuläre deterministische `group_id` und Collision-Reject; gerichtete Paare bleiben getrennt; Test-Pair-Manifestzugriff und jeder Legacy-Discovery-Fallback lösen absichtlich Fehler aus. |
| `tests/test_cue_ranker_dataset.py` | Strata decken gut/mittel/schlecht/unscored ab, Auswahl und Einschlusswahrscheinlichkeiten sind wiederholbar, ragged Offsets sind korrekt, Train-only-Statistik, keine Testdatei/-Counts; Gruppen mit zu wenig Teacher-Support werden ausgeschlossen statt still gepaddet. |
| `tests/test_cue_ranker_teacher.py` | Checkpoint-/Manifest-/Release-SHA vor Load, Eval-only Teacher, v5-Zeitnormalisierung, `local_grid_target_to_source_v1`, Guard-Rejection, Cache-Key bindet alle Verträge/Backends, Fehler werden nicht als gute Labels behandelt. |
| `tests/test_cue_ranker_model.py` | `(T,54)` für alle vier Längen, ein endlicher Skalar pro Candidate, keine IDs/Samples als Modellinput, A/B-Gewichtsteilung nur innerhalb des Rankers. |
| `tests/test_cue_ranker_runner.py` | gruppierter selbstnormalisierter Soft-Target-Loss mit Samplingkorrektur, pro-Gruppe-Mittel, gemischte Längen ohne Padding, vollständige Listwise-Gruppen ohne candidatespezifisches Mining, SHA-gesichertes Resume und Train/Validation-only Loader. |
| `tests/test_learned_cue_ranker_inference.py` | stabile Rangtie-breaks, globale Längenauswahl, feste Nutzerlänge, `reject`-only Grid-Preflight, Top-K übergibt exakt bestehende Candidate-IDs, renderability-Backfill, additive Manifestfelder und kein stiller Fallback. |
| bestehende Candidate-/v2-/Batch-/Control-Tests | Regression: harte Filter, Grid-Provenienz, Variable-Waveform-Alignment, `feature_baseline_v3`-Default, historische Manifeste und Control-Outputs unverändert. |

Ein Implementierungsmeilenstein gilt erst als angenommen, wenn:

1. ein Audit den kompletten leichten Train-/Validation-Kandidatenindex und
   keinerlei geöffnete/materialisierte Test-Candidates belegt;
2. jedes Format-3-Mitglied `group_id`, `candidate_id`, Länge, Cues und
   Grid-/Feature-/Teacher-Provenienz hashgebunden nachweisen kann;
3. die stratifizierte Auswahl nicht aus `feature_baseline_v3`-Top-K besteht
   und ihre tatsächlichen Quantil-/Stratumzahlen protokolliert;
4. der Teacher mit festem Control-Checkpoint, Objective, Renderer und Guard
   reproduzierbar denselben Labelvertrag erzeugt oder im GPU-Modus die vorab
   fixierte numerische Toleranz und Environment-Identität belegt;
5. die Ranker-Inferenz genau einen Skalar je gültigem Candidate liefert und
   ausschließlich Candidate-IDs an den unveränderten Controller übergibt;
6. ein Train-/Validation-Smoketest endliche Verluste, Checkpoint-SHAs,
   gruppierte Metriken und Cache-Statistiken schreibt; und
7. der vollständige Regressionstest erst nach Dokumentation in
   `docs/Bemerkungen.md` durchgeführt wird.

Zusätzliche harte **STOPP-Bedingungen** vor jeder Implementierungsfortsetzung:

1. Ein Test-SHA, Testpfad, Test-Pair-Manifest oder Test-Count wird im
   Cue-Ranker-Pfad geöffnet, materialisiert oder in ein Artefakt geschrieben.
2. Eine Gruppe enthält kollidierende/uneindeutige Candidate-Identitäten,
   Split-übergreifende Audio-SHAs oder keinen vollständigen v2-
   `reject`-Provenienzvertrag.
3. Teacher-Release, Controller-Checkpoint, Renderer/Objective, Alignment,
   Normalizer oder Backend ist nicht vollständig hash- und versionsgebunden.
4. Der Pilot fehlt, überschreitet ein vorab manifestiertes Budget oder die
   technische Failure-Rate überschreitet seine vorab manifestierte Schwelle.
5. Die Validation-Baselines Zufall, `feature_baseline_v3` und
   Oracle/Teacher sind nicht auf exakt demselben gelabelten Snapshot
   auswertbar, oder ein candidatespezifisches Mining verändert ihn.

## 10. Reihenfolge und Status dieser Session

Die sichere Reihenfolge ist: Verträge und Root-`pair_index` -> vollständiger
leichter Universumsindex -> 1.000-Candidate-Teacher-Pilot -> Format-3-Export
-> Ranker-Smoketest auf Train/Validation -> Inferenzintegration -> getrennte
Audit-/Hör-Evaluation auf später freigegebenen neuen Audio-SHAs. Ein
Produktivtraining oder eine Änderung des Teachers vor dem Pilot wäre eine
Abweichung vom Plan.

`docs/STATUS.md` wird in dieser Session nicht ergänzt: Es liegt eine geplante
Architekturentscheidung, aber kein ausgeführter oder verifizierter
Implementierungsmeilenstein vor. Die Plan-Datei ist die persistente
Entscheidungs- und Begründungsquelle, bis ein späterer Schritt tatsächlich
implementiert und geprüft ist.

## 11. Strenges Architektur-Review vom 2026-08-25

Dieses Review beruht auf den aktuellen Candidate-, Ranking-, Feature-v2-,
Dataset-v2-, Variable-Waveform-, TCN/BiLSTM-, Rendering- und
Vocal-Control-Verträgen sowie auf den entsprechenden Quellpfaden. Es wurden
keine Tests, kein Training und keine Testsplit-Dateien ausgeführt/geöffnet.

| Prüfpunkt | Review-Urteil | Verbindliche Folge |
|---|---|---|
| Verifizierte Downbeats | **BESTÄTIGTE INVARIANTE.** v2 erzeugt Cues nur aus Grid-Boundaries und erzwingt unter `reject` `fallback_used=false`; vier Fenster und 4/4 werden geprüft. | Learned akzeptiert nur exakt diesen v2-`reject`-Vertrag; sonst STOPP. |
| Additive Abwärtskompatibilität | **BESTÄTIGT, nach Korrektur.** Format 3, neue Caches und `cue_ranking` sind additiv; v1/v2 bleiben unverändert. | `candidate_ranking` wird nie umgedeutet oder überschrieben; nur ein neuer Adapter liest `selection_candidate_ids`. |
| Top-K-Selection-Bias | **TEILWEISE KORRIGIERT.** Der aktuelle v2-Exporter wählt tatsächlich `choices[:top_k_per_pair]` nach `feature_baseline_v3`. Ein vollständiger Universumsindex entfernt diesen Filter. | Nicht als vollständige Entbiasing-Garantie ausgeben: die stratifizierte Labelstichprobe bleibt eine selbstnormalisierte IPW-Näherung. |
| Gruppen und Audio-SHA-Splits | **KORRIGIERT.** Track-SHA-Splits sind geeignet, aber die alte Discovery liest zu früh und die ursprüngliche Gruppen-ID wäre zirkulär gewesen. | Nur split-vorgeprüfter, testfreier Pair-Index; nichtzirkuläre vollständige Member-Identity; Collision- und Cross-Split-STOPP. |
| Geschlossener Testsplit | **RISIKO GESCHLOSSEN NUR MIT NEUEM INDEX.** Der bestehende Export öffnet completed Pair-Manifeste vor dem Split. | Kein Legacy-Fallback; der neue Root enthält weder Testreferenz noch Count. Jede Test-I/O ist STOPP. |
| Eingefrorener Teacher | **KORRIGIERT.** `eval()` und `weights_only=True` genügen ohne Execution-/Backendvertrag nicht für Reproduktion. | Sealed `teacher_release.json`; CPU bitgenau, GPU nur mit identischem Environment und Toleranz. |
| Mehr als Heuristikimitat | **OFFENES RISIKO.** Baseline nicht als Input zu verwenden verhindert Korrelation nicht. | Zufall, Heuristik, Ranker und Oracle/Teacher werden auf demselben Validation-Snapshot verglichen; Aussage nur nach vorab festgelegtem Gate. |
| Loss bei variabler Gruppenlänge | **KORRIGIERT.** Ragged Reassembly ist richtig, aber dynamisches Candidate-Mining machte die Loss-Formel inkonsistent. | Vollständige gelabelte Gruppe, mindestens zwei zulässige Mitglieder, keine Cross-Group-Softmax; nur Gruppen-Scheduler in v1. |
| Kandidaten ohne Rendering | **KORRIGIERT.** Technischer Fehler ist kein schlechter musikalischer Labelwert. | Im Index behalten, aus Loss/Metriken ausschließen, Failure-Rate stoppen lassen; Inferenz preflightet und backfillt sichtbar. |
| 1,9 Mio. Kandidaten | **OFFENES RISIKO.** Ein leichter Index ist denkbar, 1,9 Mio. Render-/Waveformjobs sind explizit nicht vertretbar. | Erst 1.000-Candidate-Pilot gegen vorab manifestierte Ressourcen-/Failure-Budgets; andernfalls STOPP. |
| `local_grid_target_to_source_v1` | **BESTÄTIGTE INVARIANTE.** Der bestehende Cache nutzt die lokale Source-Dauer als Autorität. | Im Teachercache als vollständige Geometrie/Hash validieren, nie durch globale BPM-Ratio ersetzen. |
| Checkpoint-, Manifest- und Cache-Hashes | **KORRIGIERT.** Ein selbstgehashter Manifest wäre zirkulär; bestehende v2-Keys decken nicht den kompletten geplanten Teachervertrag ab. | Externe `manifest.sha256`, Artefakt-SHAs im Manifest und vollständige Release-/Feature-/Grid-/Stem-/Backend-Hashes. |
| Separate Cue-Ranking-Evaluation | **BESTÄTIGT, präzisiert.** Ranking kann auf dem eingefrorenen Teacher-Snapshot ausgewertet werden; es ist nicht die End-to-End-Qualitätsaussage. | Ranking-Metriken und spätere Renderer-/Hörmessung bleiben getrennte, nicht rückgekoppelte Protokolle. |

Die in diesem Review neu festgelegten Punkte sind Architekturentscheidungen,
keine Implementierungs- oder Verifikationsbehauptungen. Sie ersetzen keine
spätere Testdokumentation in `docs/Bemerkungen.md`.
