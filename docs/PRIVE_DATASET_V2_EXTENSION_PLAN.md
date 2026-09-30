# Reproduzierbarer Plan: PRIVE-Erweiterung des Variable-Length-Trainingskorpus

**Stand:** 2026-09-25  
**Status (2026-09-25):** Unveränderlicher Dataset-v2-Vollroot mit Feature
Protocol 2 und BS-RoFormer exportiert und SHA-/Loader-geprüft. Run 02 wurde
wegen offenem Testsplit-Gate verworfen; Run 03 wurde aus fertigen
Pairmanifesten wiederhergestellt und mit bereits geprüften Validation-
Smoke-Paaren ergänzt. Waveformcache, Training und Hörvergleich bleiben
nachgelagerte, nicht ausgeführte Phasen.
**Zielkorpus:** bestehender verifizierter Dataset-v2-Trackbestand plus
`musik\PRIVE Hardstyle Top 1000 of all times - by Scantraxx`

## 1. Entscheidung in Kürze

Die Erweiterung wird als **neue, unveränderliche Dataset-v2-Familie** gebaut.
Der vorhandene Dataset-v2-Root, seine Splitzuordnung, Feature-/Stemcaches,
Waveformcaches und Runs bleiben unverändert.

Der verbindliche neue Datasetpfad ist:

```text
output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run01
```

Der Name bezeichnet den fachlichen Auftrag; `dataset_id`, Manifest-SHA und
Datei-SHAs sind die maschinenlesbare Identität. Der Zielordner muss vor dem
Export fehlen. Er wird atomar publiziert und danach weder fortgesetzt noch
überschrieben. Ein korrigierter Export erhält `run02` und eine neue Identität.

Als Multi-Song-Produzent wird **nicht** einer der vorhandenen PRIVE-Roots
wiederverwendet:

- Der erfolgreiche Root vom 2026-09-21 ist nur ein 2/4-Takt-
  Equal-Power-Baseline-Root auf dem bisherigen `PreAnalysis`-Pfad.
- Der variable Top-3-Root vom 2026-09-22 enthält zwar formal konsistente
  Candidate-v2-Manifeste, aber nur fünf kandidatentragende Paare, vier
  Renderer-Längenfehler und keinen gültigen Render-Score.
- `src.multi_batch_render` rendert außerdem Audio und instanziiert aktuell
  `PreAnalysis`; das ist für einen kompakten, strikten Dataset-v2-Produzenten
  mit `PartialPreAnalysis`/Merge-v2 nicht der richtige Vertrag.

Implementiert ist deshalb ein additiver **analyse- und kandidatenorientierter,
splitbewusster Multi-Song-Produzent**. Er verwendet
`librosa_auftakt_monotonic_partial_v2`, Candidate Protocol 2,
`feature_baseline_v3`, `approximate_grid_policy=reject` und schreibt keine
WAVs. Er hält pro Source nur das beste Target innerhalb desselben Splits und
pro Paar/Länge die besten drei Kandidaten. Vollständige Millionenlisten werden
nicht im Root-JSON gehalten; der Producer verarbeitet jeweils nur eine Länge
als Working Set und persistiert Top-k und aggregierte Rejections in kompakte,
einzeln hashgebundene Pair-Manifeste.

## 2. Verifizierte Ausgangslage

### 2.1 Eingabeinventar

Der Ordner enthält 398 eindeutige FLAC-Dateien und eine Textdatei. Die Audios
umfassen 13.519.656.836 Bytes beziehungsweise 12,59 GiB und 28,5034 Stunden.
Alle geprüften Dateien sind 44,1-kHz-, 16-bit-, Stereo-FLACs. Es gibt weder
interne exakte SHA-Duplikate noch SHA-Überschneidungen mit dem bisherigen
`musik`-Bestand. Der bereits ausgeführte BPM-Preflight akzeptierte 321 Tracks
im Bereich 145--165 BPM; 77 wurden ausgeschlossen. Ungeprüfte Half-Time-
Varianten wurden nicht in die Eligible-Liste übernommen.

### 2.2 Bestehende Verträge

| Bereich | Verifizierter Vertrag | Konsequenz für die Erweiterung |
|---|---|---|
| Feature Protocol 2 | `features_a/features_b: float32 (T,54)`, `global_features: (16,)`, separates `length_condition: (1,)`; 2/4/6/8 Takte entsprechen T=16/32/48/64 | Kanalreihenfolge und Semantik bleiben unverändert; kein Padding und kein stilles Vier-Takt-Fallback |
| Dataset Format 2 | homogene Shards je Länge und Split; eine Audio-SHA-Splitautorität für alle Längen; Cross-Split-Paare werden verworfen | neuer Root; alte Shards werden weder erweitert noch überschrieben |
| BS-RoFormer | `bs-roformer-infer==0.1.1`, Modell `roformer-model-bs-roformer-sw-by-jarredou`; Modell-, Config-, Gewichts- und Stem-SHAs stehen in Manifesten | neue Cacheidentität; alte Einträge nur nach vollständiger SHA-/Vertragsgleichheit read-only vorfüllen |
| Variable Waveform Cache v2 | `local_grid_target_to_source_v1`, vier samplegleiche Float32-Stereoarrays bei 11.025 Hz; Target wird lokal auf die Source-Grid-Dauer gestretcht | eigener Root; nur Train und Validation materialisieren; Test bleibt ohne Waveformcache |
| Variable TCN/BiLSTM | Modellformat 4, explizite Längenkonditionierung, `(T,10)` Diagnosecontrols, vocal-aware Renderer und zeitnormalisiertes Objective v5 | nicht mit dem festen Drei-Band-TCN verwechseln; Scratch-Training ist der primäre Lauf |
| Training/Resume | Runner öffnet nur Train und Validation; Checkpoints werden mit `weights_only=True` und SHA-Prüfung geladen | Test darf weder Loader noch Cache noch Modellwahl erreichen |

Am 2026-09-23 bestanden die fokussierten synthetischen Regressionen für
Feature-v2, Dataset-v2, Split-/Geometrie-Hardening, Variable-Waveformcache,
Variable-TCN/BiLSTM und Multi-Batch mit **45 Tests in 58,12 Sekunden**.

### 2.3 Geschlossene und offene technische Gates

1. **Geschlossen:** `src.variable_producer` ist der explizite
   Partial-Merge-v2-/Candidate-v2-Pfad ohne Rendering; der Datasetexport prüft
   die vom Root deklarierten Pair-Manifest-SHAs.
2. Exakte Audio-SHA-Trennung verhindert Byte-Duplikate, gruppiert aber noch
   keine Alternate/Radio/Album-Versionen derselben Aufnahme. Vor dem Split
   wird daher ein reproduzierbares `recording_group_id` aus normalisierten
   Artist-/Titel-/Versionsmetadaten erzeugt und manuell nur dort bestätigt,
   wo die Heuristik Varianten zusammenführt. Eine Gruppe liegt vollständig in
   genau einem Split; daraus wird weiterhin die kanonische Audio-SHA-Map
   abgeleitet.
3. **Geschlossen:** Der Waveformcache schreibt einen versiegelten Index mit
   Dataset-, Root-, Entry-Manifest- und Payload-SHAs. Der reale
   Variable-TCN/BiLSTM-Wrapper verlangt ihn, bindet Index und Rootmanifest in
   Run/Checkpoint und schreibt ein I/O-Audit mit `test_reads=0`.
4. Die alte PRIVE-Analyse zeigt viele Half-Time-BPMs und nicht verifizierte
   Grids. Es wird weder die BPM-Grenze gelockert noch ein approximatives Raster
   als erkannt umetikettiert. Eine versionierte Oktavkorrektur ist nur nach
   einem separaten, hör- und gridgestützten Audit zulässig.

Die Recording-Group-Map ist erstellt und über alle aktiven Audios SHA-gebunden.
Der erste reale Dataset-Smoke enthält Stems, Features und Datasetshards;
Waveformcache und Gewichte wurden noch nicht erzeugt.

## 3. Korpus-, Split- und Testpolitik

### 3.1 Trackmenge

Die neue Familie ist eine Track-Erweiterung, keine In-place-Migration. Das
Inventarmanifest enthält 86 noch aktive Basis-Tracks und 398 neue PRIVE-Dateien.
Ein Basis-Audio wurde wegen einer Aufnahmegruppen-Kollision zwischen
eingefrorenem Train und Test aus dem aktiven Korpus genommen; die alte
87 Einträge umfassende Splitautorität bleibt als Ursprung unverändert. Das
aktive Inventar umfasst **484 Tracks in 473 Recording-Gruppen**. Die
versiegelte BPM-Vorprüfung wählte 407 Tracks für den Producer: 292 Train,
58 Validation und 57 Test.

Die Ausgangsmenge besteht aus:

- den 87 Zuweisungen der bestehenden verifizierten Variable-v2-Splitautorität
  (davon 86 aktive Basis-Audios nach der protokollierten Konfliktauflösung);
- den 398 eindeutigen PRIVE-FLACs;
- abzüglich dokumentierter Policy-, BPM- und strikter Merge-v2-Rejections.

Die alte Zuordnung der 87 Audio-SHAs bleibt unverändert. Neue PRIVE-SHAs werden
deterministisch und gruppenweise ergänzt. Der neue Datasetroot muss kein
byteweises Superset alter Beispiele sein: Kandidaten werden auf der erweiterten
Trackmenge neu produziert. Die alte Datasetinstanz bleibt die Vergleichs- und
Rollback-Autorität.

### 3.2 Splitautorität

Die neue Datei

```text
output/corpora/prive_scantraxx_extension_v2_20260923_run01/split_authority.json
```

enthält mindestens:

- `audio_sha256 -> train|validation|test` für jede aufgenommene Datei;
- unveränderte Altzuweisungen samt altem Mapping-SHA;
- `recording_group_id -> split` und Gruppenmitglieder;
- Seed, Zielquoten 70/15/15, Algorithmusversion und kanonischen Mapping-SHA;
- Korpusmanifest-SHA, Trackanzahlen und Ausschlussgründe.

Der Producer darf Targets nur im Split der Source suchen. Dataset Format 2
prüft anschließend trotzdem jede Paarzeile erneut und verwirft jede
Cross-Split-Paarung fail-closed. Damit hängt die Isolation nicht nur von einer
Stufe ab.

### 3.3 Geschlossener Testsplit

`test` wird bei der Splitbildung festgelegt, danach aber bis zum finalen
Evaluationsgate nicht verwendet:

- Dataset-v2 darf die vertraglich erforderlichen Test-Feature-Shards
  schreiben und hashen.
- Es wird **kein** Test-Waveformcache aufgebaut.
- Training, Normalizerfit, Early Stopping, Hyperparameterwahl, Thresholds,
  Beispielauswahl, Plots und Hörproben verwenden ausschließlich Train oder
  Validation.
- Der Trainingseinstieg muss einen I/O-Auditbericht mit gelesenen Pfaden und
  `test_reads=0` schreiben.
- Test wird erst nach eingefrorenem Modell-, Checkpoint-, Renderer-,
  Equal-Power-, Auswahl- und Statistikplan in einem getrennten
  `test_evaluation_only`-Prozess geöffnet. Nach Entblindung gibt es keine
  weitere Modellentscheidung auf diesem Testsplit.

## 4. Geplante unveränderliche Artefaktpfade

```text
output/corpora/prive_scantraxx_extension_v2_20260923_run01/
output/pre_analysis/prive_scantraxx_extension_merge_v2_20260923_run01/
output/producers/prive_scantraxx_extension_variable_v2_top1x3_20260923_run02/
output/feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run01/
output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run01/
output/ml_cache/prive_scantraxx_extension_variable_waveform_v2_20260923_run01/
output/training_runs/prive_scantraxx_variable_tcn_bilstm_v1_scratch_20260923_run01/
output/training_runs/prive_scantraxx_variable_tcn_bilstm_v1_finetune_20260923_run01/
output/control_studies/blind_prive_scantraxx_variable_tcn_vs_equal_power_test_v1/
```

Jeder Root wird mit Create-new-Semantik angelegt. Temporäre Stagingordner
liegen als Geschwister und werden erst nach vollständiger Validierung atomar
umbenannt. Ein existierender Root ist ein Fehler, kein Resume-Signal. Nur der
Trainingsroot besitzt ein explizit vertraglich geprüftes Resume innerhalb
desselben Runvertrags.

## 5. Ausführungsphasen und Gates

### Phase A -- Inventar- und Werkzeug-Gate

1. Vorhandene 398 Audio-SHAs gegen den Audit verifizieren, ohne Audio zu
   verändern; Basis-87-SHAs aus dem alten Splitmanifest übernehmen.
2. Python-/Paketlock, FFmpeg-Build, Rubber-Band-Backend, aufTAKT-Binary-SHA,
   BS-RoFormer-Paket, Config- und Checkpoint-SHA erfassen.
3. Half-Time-Cluster getrennt prüfen. Ohne verifizierte Regel bleiben diese
   Tracks ausgeschlossen.

**Gate:** eindeutige Korpusliste, verifizierte Werkzeuge, eingefrorene
Splitautorität und keine ungeklärte Regeländerung.

### Phase B -- Neuer Multi-Song-Produzent

Der neue Producer erhält die erweiterte, bereits gesplittete Trackliste und
arbeitet je Split getrennt. Vorgesehener Vertrag:

```text
analysis:                 PartialPreAnalysis / librosa_auftakt_monotonic_partial_v2
grid policy:              reject approximate/fallback/non-4/4/gapped grids
lengths:                  2, 4, 6, 8 bars
song target ranker:       bestehende feature-basierte Songkompatibilität
targets per source:       1
candidates per pair/L:    3
candidate ranker:         feature_baseline_v3
renderer:                 none
```

Der Learned Cue Ranker wird nicht verwendet: seine reale musikalische
Freigabe fehlt. Der Producer schreibt je Pair Request-SHA, Source-/Target-
Audio-SHA, Split, Analysemanifest-SHAs, Grid-SHAs, Candidate-v2-Payloads,
Scores und aggregierte Rejections. Ein Rootstatus `completed` gilt nur, wenn
auch verschachtelte Fehlerzähler null sind.

**Gate:** mindestens je ein gültiges Paar pro Länge in Train und Validation;
keine Cross-Split-Paare; keine Fallbackgrids; alle Pair-SHAs korrekt; keine
Renderer-/WAV-Artefakte; Target-Wiederverwendung wird berichtet. Nutzt ein
Target mehr als 10 Prozent der Sources eines Splits, wird die Auswahlpolitik
vor dem Datasetexport überprüft.

### Phase C -- Feature Protocol 2 und BS-RoFormer-Cache

1. BS-RoFormer-Vocal-Stems einmal je Audio-SHA bei 44,1 kHz erzeugen oder aus
   dem alten Root nur bei identischer Audio-, Modell-, Config-, Gewichts- und
   Extractor-SHA verifiziert übernehmen.
2. Volltrack-Featurecaches und tempoausgerichtete Targetvarianten unter dem
   neuen Root erzeugen. Phrasenkanäle bleiben `phrase_valid=0`, solange kein
   freigegebener Phrasenextraktor existiert.
3. Fenster exakt mit T=16/32/48/64 schneiden; `transition_position` ist
   `(i+0.5)/T`; `length_condition=L/8`; 54 Kanäle und 16 globale Werte bleiben
   unverändert.
4. Flux-/Onset-Normalisierung ausschließlich aus tatsächlich verwendeten
   Trainingsartefakten fitten. Validation und Test sind read-only
   Konsumenten derselben Statistik.

**Gate:** endliche Werte, exakte Shapes, gültige Masken, vollständige
RoFormer-Provenienz, keine Demucs-Mischung, keine Testdaten im Normalizer.

### Phase D -- Dataset-v2-Export

Der Export erfolgt einmalig in den festgelegten neuen Root. Er bindet die
Union aller ausgewählten Records an dieselbe erweiterte Splitautorität. Je
Länge werden `train.npz`, `validation.npz`, `test.npz` und die korrespondierenden
JSONL-Dateien geschrieben. Leere Shards bleiben explizit leer; Train und
Validation dürfen für keine trainierte Länge leer sein.

**Gate:** eindeutige Example-IDs; null Audio-SHA- und Recording-Group-Leakage;
Datei-, Pair-, Featurecache-, Normalizer- und Split-SHAs stimmen; alle vier
Längen vorhanden; Datasetmanifest ist byteweise erneut validierbar.

### Phase E -- Variable-Waveformcache

Nur Train und Validation werden in
`prive_scantraxx_extension_variable_waveform_v2_20260923_run01`
materialisiert. Der Vertrag bleibt `local_grid_target_to_source_v1`:

- Source-Postroll ist Dauerautorität;
- Target-Preroll und Target-Vocal erhalten denselben Rubber-Band-Stretch;
- Mix und Vocal erhalten identische technische Randkorrekturen;
- alle vier Arrays sind Float32-Stereo, 11.025 Hz, finite und samplegleich;
- Restabweichungen über zwei Samples am 44,1-kHz-Gitter werden abgelehnt.

Nach Abschluss wird ein kanonisch sortierter Cacheindex über
`example_id`, Entry-Manifest-SHA und Payload-SHA geschrieben. Rootmanifest-SHA
und Index-SHA gehen in jeden Trainingsvertrag ein. Es gibt keinen Testeintrag.

### Phase F -- Smoke-Test vor Vollauf

Der Smoke verwendet ausschließlich deterministisch ausgewählte Train- und
Validation-Tracks; alle Test-SHAs werden bereits am Eingang abgewiesen.

1. Zwei PRIVE-Train-Tracks und zwei nach aktuellem Merge-v2-Grid geprüfte
   Validation-Tracks mit vier getrennten Recording-Gruppen verwenden.
2. Producer mit `top_targets=1`, `top_k=1`, ohne Renderer ausführen.
3. RoFormer-/Featurecache nur für diese vier Tracks erzeugen.
4. Dataset-v2-Smoke mit allen vier Längen exportieren und Split-/SHA-Audit
   ausführen.
5. Waveformcache für mindestens zwei Train- und ein Validation-Beispiel je
   Länge erzeugen; mindestens ein Paar muss echten Target-Stretch verwenden.
6. `variable_tcn_bilstm_transition_control_v1` eine Epoche auf CUDA trainieren
   und per SHA-geprüftem Resume auf Epoche 2 fortsetzen.
7. Endliche Losses/Gradienten, `(T,10)`-Outputs, monotone Kurven,
   Cache-Hit-Wiederholung, Checkpoint-/History-SHAs und `test_reads=0`
   bestätigen.

**Abbruch:** jede Cross-Split-Lesung, ein Fallbackgrid, ein Cache-Reject, ein
nicht endlicher Wert, inkonsistente Länge oder fehlende Hashbindung stoppt den
Vollauf. Smoke-Artefakte werden nie in den Vollroot kopiert.

### Phase G -- Training und optionale Feinabstimmung

Der wissenschaftliche Primärlauf ist ein **Training von Grund auf** mit
festem Seed, `equal_length`-Sampling, Batchgröße 8 als Ausgangswert, AdamW,
maximal 100 Epochen, Early Stopping und W&B `disabled` oder `offline`.
Modellwahl erfolgt nur über Validation. Epoche 0 dokumentiert die
neutral/equal-power-nahe Initialisierung.

Optional folgt ein separat benannter Fine-Tuning-Lauf. Er lädt ausschließlich
die Modellgewichte des manifestierten Best-Checkpoints
`variable_tcn_bilstm_v2_wandb_20260826`, setzt Optimizer und Scheduler neu und
bindet Quellrun-, Quellmanifest- und Checkpoint-SHA. Das ist **kein Resume**,
weil Dataset- und Cachevertrag wechseln. Scratch versus Fine-Tune ist eine
vorab deklarierte Validation-Ablation; der Test entscheidet nicht zwischen
beiden.

Der Runvertrag muss Datasetmanifest-SHA, Split-Mapping-SHA, alle vier Shard-
SHAs, Normalizer-SHA, Featurecacheindex-SHA, Waveform-Rootmanifest- und
Waveformindex-SHA, Modell-/Renderer-/Objective-/Schedulervertrag, Toolversionen,
Seed, Git-HEAD sowie einen Hash des Dirty-Diffs enthalten. Best/Latest,
History und finales Manifest werden gegenseitig per SHA gebunden.

### Phase H -- Unabhängiger Hörvergleich gegen Equal Power

Nach dem Validation-Freeze wird genau ein `test_evaluation_only`-Export
erstellt. Modell und Equal Power verwenden je Paar dieselben lokal
ausgerichteten Mix-/Vocal-Waveforms, denselben Kontext, dasselbe Tempo-Backend,
dieselbe Länge und eine gemeinsame Peak-Absenkung. Nur die Controlkurven
unterscheiden sich.

Vorgesehen sind bis zu 12 Paare je Länge (48 Paare), abhängig von der
verfügbaren unabhängigen Testmenge. Eine Aufnahmegruppe soll höchstens einmal
als Source und einmal als Target erscheinen. Auswahlregeln, Ersatzregeln und
Seed werden vor Öffnen des Tests festgeschrieben. A/B-Zuordnung wird
deterministisch geblendet; der Antwortschlüssel bleibt bis zum Abschluss
separat.

Mindestens drei nicht an Modellwahl oder Implementierung beteiligte Hörer
bewerten Gesamtpräferenz, Sauberkeit, Energieverlauf, Low-End-Übergabe,
Vocal-Klarheit, Artefakte und Tanz-Eignung. Die primäre Kennzahl ist die
geblendete Paarpräferenz, getrennt nach 2/4/6/8 Takten; Konfidenzintervalle
und eine trackgruppierte Sensitivitätsanalyse verhindern, dass wiederholte
Tracks als unabhängige Beobachtungen gezählt werden. Nach Entblindung ist der
Test verbraucht. Eine weitere Modelländerung benötigt eine neue externe
Testmenge.

## 6. SHA- und Manifestkette

```text
Audio-SHAs + Korpusinventar
  -> Korpusmanifest-SHA
  -> Analysevertrag + aufTAKT-Binary-SHA + Analysemanifest-SHAs
  -> Split-Mapping-SHA + Recording-Group-Mapping-SHA
  -> Producer-Root-SHA + Pair-Manifest-SHAs + Candidate-Request-SHA
  -> BS-RoFormer-Paket/Config/Weights-SHAs + Stem-Payload-SHAs
  -> Featurecacheindex-SHA + Train-Normalizer-SHA
  -> Datasetmanifest-SHA + NPZ-/JSONL-SHAs
  -> Waveform-Rootmanifest-SHA + Entryindex-/Payload-SHAs
  -> Run-Contract-SHA + Best-/Latest-/History-SHAs
  -> Studienmanifest-SHA + WAV-SHAs + separater Antwortschlüssel
```

Jede Stufe verifiziert die unmittelbar vorgelagerte Stufe vor dem ersten
teuren Zugriff. Pfade allein sind niemals Identität. W&B ist nur Spiegel;
lokale Manifeste bleiben Autorität.

## 7. Speicher- und Laufzeitabschätzung

Die Schätzung ist bewusst als Bandbreite angegeben. Der Smoke ersetzt sie
durch gemessene Durchsätze, bevor der Vollauf freigegeben wird.

Bekannte Messpunkte:

- PRIVE-Quellaudio: 12,59 GiB, bereits vorhanden;
- alter Variable-v2-Feature-/RoFormer-Root: 2,70 GiB für 87 Tracks, rund
  31,8 MiB je Track;
- alter Variable-v2-Waveformcache: 1.164.712.217 Bytes für 468 Beispiele,
  rund 2,37 MiB je Beispiel;
- Dataset-v2: rund 0,01 GiB für 552 Beispiele;
- alter 29-Epochen-Run: 355,62 Sekunden bei 468 Beispielen, Batchgröße 8;
- vollständige Einzeltrackanalyse wurde früher mit ungefähr 2:36 Minuten pro
  Track beobachtet.

Für 407 BPM-vorgeprüfte Tracks (292 Train, 58 Validation, 57 Test) und
`top_targets=1`, `top_k=3` ergibt sich grob. Die neue Vier-Track-Smoke-
Featurecachegröße beträgt 0,78 GiB einschließlich 699.412.152 Byte
BS-RoFormer-Gewichten; der Dataset-v2-Smoke mit 16 Beispielen belegt
362.970 Byte. Das skaliert den Full-Featurecache auf ungefähr 13--15 GiB
und die Datasetshards auf rund 0,1 GiB, bevor Producer- und Waveformzahlen
aus dem Vollmanifest bekannt sind.

| Artefakt | Erwartung |
|---|---:|
| neue Analysemanifeste | unter 0,1 GiB |
| kompakte Producer-/Pair-Manifeste | 0,2--1,0 GiB |
| BS-RoFormer- und Featurecache | 13--15 GiB |
| Dataset-v2 NPZ/JSONL | etwa 0,1 GiB |
| Train-/Validation-Waveformcache | höchstens etwa 10--12 GiB bei 4.200 Beispielen |
| Trainingsrun je Variante | unter 0,1 GiB |
| temporäre FFmpeg-/Stagingreserve | 5--10 GiB |
| **zusätzlicher freier Speicher vor Start** | **mindestens 35 GiB, empfohlen 50 GiB** |

Ohne kompakten, längenweise arbeitenden Producer wäre der Manifestbedarf unvertretbar: Der
frühere 87-Paar-Lauf schrieb 6,15 GB JSON für 1,92 Millionen Kandidaten. Diese
Sackgasse wird nicht wiederholt.

Grobe Laufzeit auf der vorhandenen RTX 5070 Ti und acht Analyseworkern
(20 logische Prozessoren verfügbar; acht parallele aufTAKT-Prozesse liefen
beim Voll-Preflight):

- Merge-v2-Analyse der bis zu 407 Eligible-Tracks: etwa 2,2 Stunden ideal
  aus der Einzeltrackmessung, realistisch 2,5--4 Stunden bei acht Workern;
- BS-RoFormer und Featurecache: im Vier-Track-Smoke wurden Modellgewichte
  einmalig in rund 96 Sekunden geladen; erste Inferenz meldete rund 158
  Sekunden, spätere Tracks rund 17--18 Sekunden. Volltrack-Analyse und
  Featureextraktion liefen zusätzlich je Track. Vorläufig 4--12 Stunden,
  anhand des Vollcache-Durchsatzes neu zu schätzen;
- Producer, Datasetexport und Waveformcache: vorläufig 4--12 Stunden,
  stark abhängig von Strict-Acceptance und Stretchanteil;
- Training: skaliert aus dem alten Run ungefähr 1--3 Stunden bis 100 Epochen,
  meist kürzer bei Early Stopping; der bestehende serielle Objective-Pfad ist
  eher CPU-/Synchronisations- als VRAM-limitiert;
- gesamter Vollauf inklusive Audits: etwa 12--32 Stunden aktive Laufzeit,
  vorzugsweise in getrennten, resumefähigen Phasen statt als ein Shelllauf.

## 8. Ausführungscheckliste

Der Vollauf darf erst starten, wenn alle Punkte belegt sind:

- [x] Splitautorität erweitert, alte Zuordnungen unverändert, Gruppenleckage null.
- [x] BPM-Eligible-Entscheidung manifestiert; keine stille BPM-Korrektur.
- [x] Neuer Partial-Merge-v2-Multi-Song-Produzent implementiert und synthetisch getestet.
- [x] Kompakter Top-k-Persistenzvertrag verhindert die frühere Vollmanifest-Sackgasse.
- [x] Feature-/Dataset-Smoke für 2/4/6/8 bestanden; zusätzlicher Waveformcache-/Training-Smoke für echten Stretch, Cache-Hit, CUDA und Resume bleibt offen.
- [ ] `test_reads=0` über Normalizer, Waveformcache, Training, Modellwahl und Validation-Studie. Für den exportierten Datasetroot ist der Testshard explizit leer und kein Beispiel lädt Testtracks.
- [x] Waveformcacheindex- und Rootmanifest-SHA sind Teil des Runvertrags.
- [ ] Mindestens 50 GiB freier Arbeitsraum oder gemessene kleinere Reserve.
- [ ] Hörstudienprotokoll und Raterkreis vor Testöffnung eingefroren.
- [x] Keine Audiodateien oder Modellgewichte werden committet.

## 9. Implementierungsstand 2026-09-25

Die folgenden additiven Einstiegspunkte stehen bereit:

- `src.variable_split_extension`: unveränderliche Altmap-Fortschreibung über
  Recording-Groups, inklusive Altmap- und Gruppenmap-SHA;
- `src.variable_producer`: splitbewusste Zielauswahl, `PartialPreAnalysis`,
  Candidate Protocol 2 für 2/4/6/8 Takte, `feature_baseline_v3`, kompakte
  Top-k-Pairmanifeste und ausdrücklich keine Renderer/WAVs;
- `export-dataset-v2`: prüft nun auch jeden vom Producerroot deklarierten
  Pair-Manifest-SHA;
- `cache-variable-waveforms`: versiegelt die tatsächlich materialisierten
  Train-/Validation-Einträge in `index.json`;
- `train-variable-tcn-bilstm`: verlangt den versiegelten Cacheindex, bindet
  Cacheindex- und Rootmanifest-SHA, schreibt `io_audit.json` mit
  `test_reads=0` und unterstützt getrennt von Resume eine
  `--initialize-from-manifest`/`--initialize-from-checkpoint`-Initialisierung,
  bei der Optimizer und Scheduler bewusst neu starten.

### Realkorpus-Ausführung 2026-09-25

- Korpusmanifest: 484 Tracks, 473 Recording-Gruppen; SHA-256
  `46a7f677f008ce9d8296b6b1a80db0fbf6d419cddfbe0886c88b3d7ae297b3a4`.
- Splitautorität: 343 Train-, 70 Validation- und 72 Test-Zuweisungen; SHA-256
  `1eaf5672428f030ca9807c5ddf3d1e06bf03c06b2792b8a9a21bf564a318d3ee`;
  kanonischer Mapping-SHA
  `f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
- Eingefrorenes BPM-Eligible-Manifest: 407 Tracks (292/58/57); SHA-256
  `7bcf4a79db6943d78bf53d60f5adbf273245f31c7378a3aaacf360df6dc95be3`.
- Der versiegelte Smoke-Produzent erzeugte vier splitinterne Paare und 16
  ausgewählte Kandidaten, je vier für 2/4/6/8 Takte; Root-SHA
  `0346b1b1b3fcf5b1fa2db7b77402c511cc21e714cee30e5e29019984c94fd287`.
- Der Dataset-v2-Smoke mit BS-RoFormer und Feature Protocol 2 enthält für
  jede Länge zwei Train- und zwei Validation-Beispiele, leere Testshards und
  keine Cross-Split-Paare; Manifest-SHA
  `f687d786c11bd64433a7092d05fe507b9584aaf857916a55f04d1d85b1a3ca32`.
- Die Producerläufe Run 01 und Smoke-Runs 01--04 sind als abgebrochene bzw.
  diagnostische Artefakte erhalten. Gründe und Befunde stehen in
  `docs/Bemerkungen.md`.
- Der erste Voll-Producer Run 02 ist wegen eines offenen Testsplit-Gates
  verworfen; Run 03 und seine Recovery sind im folgenden Abschnitt
  dokumentiert. Der Dataset-v2-Vollroot wurde exportiert. Waveformcache,
  Training und unabhängige Evaluation bleiben nachgelagerte Phasen.

### Geschlossener Testsplit und korrigierter Reallauf, 2026-09-25

Run 02 wurde nach 407/407 Eligible-SHA-Analysen und Beginn der Paarbildung
gestoppt, weil der Producer Testquellen nicht vor der Audioanalyse
ausgeschlossen hatte. Genau ein Pair wurde abgeschlossen; kein Dataset wurde
exportiert und kein Training begonnen. Der Lauf bleibt als partielle
Diagnose-/Cacheevidenz erhalten und wird nicht weiterverwendet.

src.variable_producer filtert Testtracks nun anhand der manifestierten Audio-
SHAs vor dem Hashing und jeder Audioanalyse. Ohne Korpusmanifest wird bei
vorhandenen Testzuweisungen vor Audiozugriff abgebrochen. Die fokussierten
Regressionstests bestehen. Run 03 verarbeitet ausschließlich Train/Validation;
seine fertigen Pairmanifeste wurden nach einem vorzeitigen Root-Abbruch in
einen neuen unveränderlichen Recovery-Root aufgenommen. Zwei geprüfte
Validation-Pairmanifeste aus dem Vier-Track-Smoke schließen die minimale
Validationstichprobe. Run 04 bleibt ungenutzt, weil er null gültige
Validation-Kandidaten enthielt.

Der neue Dataset-v2-Vollroot wurde mit Feature Protocol 2, `roformer`,
2/4/6/8 Takten und `top_k_per_pair=3` exportiert:

```text
output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run01
```

Dataset-ID `6be39995e91c0063a933`, Manifest-SHA-256
`9d11bae795c098376d46a9a02204a7cb6647f77ffb5ff39f5c80c2da94823562`.
152 Beispiele: pro Länge 36 Train, 2 Validation, 0 Test. Die Testshards sind
explizit leer; alle exportierten Source-/Target-Hashes liegen im selben Split.
Alle 24 Sharddateien und 352 Pairmanifest-SHAs stimmen. Die Autorität ist an
Producer-Root-SHA `172c3ba41c9a7b807452e443865e63d43d67bcbd2d792be6ca841ed69b2d8a36`
gebunden und bewahrt Mapping-SHA
`f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
Der Loader las alle 152 Beispiele einschließlich der SHA-Bindungen jedes
referenzierten Featurecaches.

Der RoFormer-/Featurecache umfasst 92 Dateien (1.433.741.822 Bytes; 22 Vocal-
Stem- und 23 Track-Featurecaches, einschließlich der lokalen Modellassets).
Der Datasetroot umfasst 25 Dateien (1.640.132 Bytes). Beides liegt in durch
`.gitignore` ausgeschlossenen `output/`-Pfaden; es wurden keine Audio- oder
Gewichtsdateien dem Repository hinzugefügt. Der erste Exportabschluss scheiterte
beim Anlegen des temporären Datasetroots an einer Workspace-Sandbox-
PermissionError; der Zielpfad war nicht vorhanden, und der fehlgeschlagene
temporäre Root wurde entfernt. Nach gezielter Schreibfreigabe lief derselbe
Befehl mit Exit 0.

Die fokussierte Regression nach Export bestand mit 30 Tests (zwei bestehende
`audioread`-Deprecation-Warnungen). Variable-Waveformcache, Training/Fine-
Tuning und unabhängiger Equal-Power-Hörvergleich wurden nicht gestartet; sie
bleiben separate nächste Schritte. Ausführlicher Laufverlauf und vollständige
Befehle: `docs/Bemerkungen.md`.
