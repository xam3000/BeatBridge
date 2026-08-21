# Implementierungsplan: extern vorgegebene Übergangslängen 2/4/6/8 Takte

**Stand:** 2026-08-20
**Status:** Architekturplan; Candidate-/Feature-/Dataset-v2 sowie der additive
`local_grid_target_to_source_v1`-Waveform-Cache sind real verifiziert. Der
vollständige Variable-TCN/BiLSTM-Trainingslauf bleibt bewusst offen.
**Geltungsbereich:** neue, additive Variable-Length-Verträge neben den bestehenden Vier-Takt-Verträgen

Dieser Plan wurde am 2026-08-20 als unabhängiges Architektur-Review gegen den
tatsächlichen Repository-Stand einschließlich der vorhandenen Nutzeränderungen
geprüft. Die Prüfung war read-only; es wurde kein Produktivcode, Audio-, Dataset-,
Cache- oder Run-Artefakt verändert. Aussagen über den Ist-Stand beziehen sich auf
die aktuell implementierten v1-/v2-Pfade, nicht auf die hier geplante neue Schicht.

## 1. Ziel, Nichtziele und unveränderliche Regeln

BeatBridge soll Übergänge mit einer vom Nutzer vorgegebenen Länge von **2, 4, 6 oder 8 Takten** erzeugen, extrahieren, als Dataset ablegen, trainieren und evaluieren können. `transition_length_bars` ist dabei ein externes hartes Constraint:

- Ein einzelner Render-/Inferenzauftrag enthält genau eine gültige Länge. Eine
  Kandidatensuche oder Mehrlängenstudie darf dagegen eine explizite Menge gültiger
  Längen anfordern; diese Menge ist ein Request-Feld und keine implizite
  Schnittmenge.
- Das Modell erhält die Länge als vertraglich validierte Eingabe und darf sie weder schätzen noch auswählen, optimieren oder durch eine andere Länge ersetzen.
- Ein Modell-Output ist nur gültig, wenn seine Sequenzlänge exakt zur angeforderten Länge passt.
- Eine Mehrlängen-Studie oder ein Mehrlängen-Training besteht aus mehreren explizit angeforderten, längenspezifischen Shards/Batches. Ein Scheduler darf die Länge des Beispiels auswählen, aber nicht das Modell.
- Ungültige Werte, fehlende Längen oder widersprüchliche Angaben zwischen Request, Candidate, Dataset, Batch, Model und Renderer führen zu einem Fehler; es gibt kein stilles Fallback auf 4 Takte.

Nicht Teil dieses Plans sind Änderungen an Audioquellen, bestehenden NPZ-Dateien, RoFormer-Stem-Artefakten, bestehenden Runs, Checkpoints oder dem Feature Protocol 1. Es wird kein bestehendes Artefakt migriert, überschrieben oder gelöscht.

Der aktuelle Candidate-v1-Code ist weiter gefasst als der neue externe Vertrag:
`CandidateGenerationConfig.transition_lengths_bars` akzeptiert positive
Ganzzahlen und die bestehenden Tests verwenden unter anderem 1, 2 und 4 Takte.
Diese v1-Freiheit bleibt erhalten. Nur der neue Request-/Candidate-v2-Pfad
beschränkt die extern vorgegebenen Längen auf `{2,4,6,8}`.

## 2. Verifizierte Ausgangslage

Bei aktuellem 4/4-Metrum und Halbbeat-Raster gilt:

| `transition_length_bars` | Beats | Halbbeat-Schritte `T(L)` |
|---:|---:|---:|
| 2 | 8 | 16 |
| 4 | 16 | 32 |
| 6 | 24 | 48 |
| 8 | 32 | 64 |

Die verbindliche Formel für den neuen Vertrag ist:

```text
T(L) = L * beats_per_bar * steps_per_beat = L * 4 * 2
```

Der aktuelle erweiterte Vier-Takt-Datensatz wurde nur lesend auditiert. Seine Manifestdaten sind `dataset_id=52bc9d1cebfd1b82d2ea`, `format_version=1`, `feature_protocol_version=1`, 370/50/60 Beispiele für Train/Validation/Test und 111 eingefrorene Track-Zuordnungen. Die kanonische Zuordnung `audio_sha256 -> split` hat den Hash `5548a9bf74f20f9022c02b48571bbb8b8e2e9b4cc58d68f2a81131f2d2b12e8b`. Diese konkrete Zuordnung ist die bevorzugte Split-Autorität für die neuen Längen, sofern dieselbe vollständige Track-Menge verwendet wird.

Der Hash ist nicht nur eine Kurzform des Seeds. Er wird exakt über die
kleingeschriebenen Audio-SHAs berechnet:

```python
mapping = {item["sha256"].lower(): item["split"]
           for item in manifest["track_assignments"]}
canonical = json.dumps(mapping, sort_keys=True, separators=(",", ":"))
mapping_sha256 = sha256(canonical.encode("utf-8")).hexdigest()
```

Die neue Familie bindet zusätzlich die SHA des Quellmanifests und dessen
tatsächliche Split-Konfiguration (aktuell Seed `20260805`) ein. Ein bloß gleicher
Seed oder eine gleiche Anzahl von Beispielen genügt nicht.

## 3. Additive Vertrags- und Versionsarchitektur

Die alten Verträge bleiben lesbar und unverändert. Neue Implementierungen verwenden eigene Namen, Validatoren, Manifestfelder und Ausgabeordner. Eine neue Version darf nicht durch eine geänderte Bedeutung einer alten Versionsnummer getarnt werden.

| Bereich | Bestehender Vertrag, unverändert | Neuer Vertrag, vorgeschlagen | Wesentliche Änderung |
|---|---|---|---|
| Externer Request | kein variabler Vertrag | `transition_length_request_v1` | Enum `{2,4,6,8}`, Nutzerwert ist Pflichtfeld |
| Candidate | Candidate Protocol 1 | Candidate Protocol 2, z. B. `bar_grid_v2_length_specific` | Grenzen und Ablehnungen pro Länge statt gemeinsame Schnittmenge |
| Feature | Feature Protocol 1 | Feature Protocol 2 | `T(L)` statt 32; Kanaldefinitionen und Reihenfolge bleiben kompatibel, aber der Validator ist neu |
| Global-Pair | bestehender v1-Extractor | Global-Pair Extractor v2 | Berechnung über `T(L)`; neue Provenienz im Manifest |
| Dataset | Dataset Format 1, NPZ `(N,32,54)` | Dataset Format 2 | längenhomogene, separat versionierte Shards |
| Bridge-Cache | bestehende generische/vocale Cacheversionen | neue Variable-Length-Cacheversionen | Cache-Key enthält Länge, `T(L)` und exakte Dauer; alte Caches werden nicht wiederverwendet |
| Modell | bestehende MLP-, Vocal-MLP- und TCN/BiLSTM-Formate | neue Variable-Length-Modellformate | dynamische Zeitachse plus explizite Längenkonditionierung |
| Training | bestehende Run-Formate | neue Variable-Length-Run-Formate | Längenset, Shard-Hashes, Samplingplan und neue Objective-/Renderer-Verträge |
| Checkpoint | bestehende Payloads und Loader | Checkpoint Format 2 | eigener Vertrag, Run-/Contract-Hash, Längenset und Shard-Provenienz |
| Renderer/Loss | bestehende Control-/Objective-Versionen | neue variable Control-/Objective-Versionen | Dauer- und Zeitnormalisierung über den gesamten Übergang |
| Blindstudie | Control Study Protocol 1 / bestehende Formate | additive Studienversion | `transition_length_bars`, `sequence_length` und längenstratifizierte Auswertung |

Empfohlene neue numerische Versionen sind jeweils größer als die aktuelle Version: Feature 2, Global-Pair 2, Dataset 2, generischer Trainingslauf 2, vokaler Trainingslauf 3, Checkpoint 2; bei den Modellformaten generischer Variable-MLP 2, vokaler Variable-MLP 3 und Variable-TCN/BiLSTM 4. Die genaue Konstantenbenennung wird bei der Implementierung zentral dokumentiert. Feature Protocol 1, `time_shared_mlp_v1`, `vocal_time_shared_mlp_v2`, `tcn_bilstm_transition_control_v1` und alle bestehenden Vier-Takt-Runs bleiben weiterhin ausführbar.

## 4. Gemeinsamer Längenvertrag

Ein zentraler neuer Längenvertrag soll einmalig und ohne implizite Defaults implementiert werden. Er enthält mindestens:

```text
transition_length_bars: int       # 2, 4, 6 oder 8
transition_length_beats: int      # L * 4
sequence_length: int              # L * 8
meter_numerator: 4
meter_denominator: 4
steps_per_beat: 2
grid_protocol_version: ...
```

Der Validator prüft:

1. `L` ist exakt ein Mitglied der erlaubten Enum.
2. 4/4 und Halbbeat-Raster sind für diese erste Variable-Length-Version aktiv.
3. `transition_length_beats == L*4` und `sequence_length == L*8`.
4. Feature-Fenster, Candidate, Waveform, Control-Kurven und Objective verwenden dieselbe Länge.
5. Längenfelder in Metadaten dürfen nicht aus der beobachteten Arrayform rückwärts erraten werden; Arrayform und externes Feld müssen sich gegenseitig bestätigen.

Die numerische Länge wird zusätzlich als normalisierte Modell-Eingabe geführt, etwa `transition_length_bars_normalized = L/8`. Sie ist ein expliziter Konditionskanal und nicht bloß eine Nebenwirkung der Sequenzlänge. Die 16-dimensionale Form und Kanalreihenfolge der globalen Features bleiben erhalten; ihre numerische Semantik darf wegen der variablen lokalen Fenster aber nicht automatisch als unverändert gelten. Deshalb ist der Global-Pair-Extractor v2 separat versioniert und seine Verteilung je Länge zu prüfen.

### Verbindliche Fenstersemantik

Die v2-Fenster behalten die Rollen des tatsächlich implementierten v1-
`TrackFeatureArtifact.model_window()`: Source A beginnt am Source-Cue und nimmt
`T(L)` vollständige Bins danach; Target B endet am Target-Cue und nimmt die
`T(L)` vollständigen Bins davor. Das Feld `transition_position` ist eine lokale
Position innerhalb dieses Übergangs, keine absolute Trackposition. Für die
ersten und letzten Featurezentren gilt daher `0.5/T` beziehungsweise
`(T-0.5)/T`.

Die bestehende Analyseabdeckung von vier Takten vor und vier Takten nach dem Cue
(`context_coverage`) ist ein separater Kontextvertrag. v2 muss
`analysis_context_bars_before/after` explizit im Manifest führen und darf diesen
Kontext nicht stillschweigend mit `T(L)` skalieren. Die Baseline-Empfehlung ist,
für Vergleichbarkeit zunächst 4+4 beizubehalten; für 8-Takt-Übergänge wird dann
aber ausdrücklich nur die vorhandene Kontextabdeckung und nicht ein vollständiger
äußerer 8-Takt-Kontext zugesichert. Eine größere oder nicht überlappende
Kontextabdeckung ist ein eigener, versionierter Vertrag mit eigener Coverage-
Prüfung.

## 5. Kandidatengenerierung: Längen nicht vermischen

### Verifizierter Befund

In `src/candidates/generation.py` verwenden `_eligible_boundaries`, `_eligible_target_boundaries` und `_eligible_bridge_boundaries` für mehrere `lengths_bars` eine `all(...)`-Prüfung. Damit ist eine Boundary nur gültig, wenn sie für **jede** angeforderte Länge vollständige Fenster besitzt. Wird 8 Takte zusätzlich zu 2 oder 4 Takten angefordert, kann die aktuelle gemeinsame Auswahl daher gültige 2-/4-Takt-Kandidaten entfernen. Dieser Befund ist ein konkreter Änderungsgrund für Candidate Protocol 2.

Zusätzlich werden die aktuellen globalen `source_boundary_count`- und
`target_boundary_count`-Limits nach dieser gemeinsamen Eligibility angewendet.
Damit können lange Fenster nicht nur Eligibility, sondern auch das Budget der
kurzen Längen beeinflussen. `Candidate` enthält in v1 bereits
`transition_length_bars` und die ID enthält die Länge; `CandidateRejection`
führt die Länge dagegen noch nicht als eigenes Feld. Das neue Format muss diese
Provenienz explizit machen.

### Neuer Algorithmus

Für jede Länge wird unabhängig gearbeitet:

```text
B_source[L] = source boundaries, die alle vier L-spezifischen Fenster erfüllen
B_target[L] = target boundaries, die alle vier L-spezifischen Fenster erfüllen
C[L]        = Kandidatenpaare aus B_source[L] und B_target[L]
```

Die vier Fenster sind jeweils in Beatkoordinaten mit `transition_length_beats = 4L` zu prüfen: Source-Vorher, Source-Nachher, Target-Vorher und Target-Nachher. Beat-Anzahl, Grid-Provenienz, Tempo-Toleranz und Audio-SHA-Identität bleiben harte Filter.

Regeln für die neue Generierung:

- `C[2]`, `C[4]`, `C[6]` und `C[8]` werden unabhängig erzeugt; eine Union findet erst nach der Längenvalidierung statt.
- Limits wie `max_boundaries_per_track` und `max_candidates_per_pair` gelten pro Länge, damit 8-Takt-Grenzen nicht die 2-/4-Takt-Suche budgetieren.
- Ablehnungsgründe enthalten immer `transition_length_bars` und werden je Länge gezählt.
- Candidate-ID, Manifest und Rank-Datensatz enthalten Länge, Beat-Anzahl und `T(L)`.
- Bei gleicher Quelle/Ziel können mehrere Längen gültige, aber eigenständige Candidates sein.
- Ranking und Qualitätsmetriken werden je Länge normalisiert und je Länge berichtet; 8-Takt-Beispiele dürfen keine Häufigkeitsdominanz erzeugen.
- Ein Regressionstest muss eine Boundary-Konfiguration konstruieren, die für 2/4, aber nicht für 8 Takte gültig ist, und beweisen, dass die 2-/4-Kandidaten bei gemeinsamer Anfrage erhalten bleiben.

Die vorhandene `transition_length_bars`-Information in Candidates sowie die
dynamische Beat-Verwendung in Bridge und Feature-Baseline werden wiederverwendet,
aber nur unter dem neuen Candidate-/Bridge-Vertrag. Die v1-Funktionen und ihre
numerischen Regressionserwartungen werden nicht auf die neue per-L-Semantik
umgebogen.

### Ranking und gerenderte Metriken

`song_compatibility_v1` bleibt als Whole-Track-Vorfilter unverändert; er bewertet keine Übergangsfenster und braucht deshalb keine künstliche Längenwahl. Für Cutpoint-Ranking und Renderbewertung werden dagegen additive Verträge benötigt: ein längenspezifischer Nachfolger der Feature-Baseline und ein neuer Render-Metrikvertrag speichern `transition_length_bars`, `transition_length_beats`, exakte Beatgrenzen und `sequence_length`. Die bisherige BPM-Annäherung an die Fensterlänge darf im neuen Pfad nicht die exakte Bridge- und Featureabdeckung ersetzen.

Die Scores werden je Länge getrennt gerankt und berichtet. Falls ein gemeinsamer Bericht nötig ist, enthält er eine vorher festgelegte Längengewichtung und zusätzlich die vier Einzelverteilungen; ein ungewichtetes Zusammenwerfen der Beispielzahlen ist nicht zulässig. Fehler bleiben pro Kandidat isoliert, und bestehende Batch-Manifeste, WAVs, Sidecars und Ratings werden nur gelesen. Variable Blindstudien erhalten eine neue Studienversion mit Länge im öffentlichen Manifest und bleiben mit dem bestehenden Control-Study-/Ratings-Vertrag kompatibel, ohne historische Ratings umzudeuten.

Die Rankingfenster dürfen dabei nicht mit den ML-Featurefenstern verwechselt
werden: `feature_baseline_v3` misst Source unmittelbar vor dem Source-Cut und
Target unmittelbar nach dem Target-Cut, während der aktuelle
`model_window()`-Vertrag für das Modell Source nach dem Cue und Target vor dem
Cue schneidet. v2 muss beide Rollen im jeweiligen Manifest explizit benennen;
ein gemeinsamer Hilfsname wie „transition window“ reicht nicht. Das bestehende
Batch-Manifest v1, `rendered_transition_baseline_v1` und Ratings v1/v2/v3
bleiben historische, read-only Verträge. Die neue variable Batch-/Metrik-/Study-
Schicht erhält eigene Formatversionen und darf historische Testsplit-
Hörstudien nicht als unabhängige v2-Evidenz umetikettieren.

## 6. Feature- und Datasetformat

### Feature Protocol 2

Feature Protocol 2 erzeugt pro Seite:

```text
features_a / features_b: float32 (T(L), 54)
global_features:         float32 (16,)
length_condition:        float32 (1,)  # normalisierte externe Länge
```

Die 54 Zeitkanäle bleiben in derselben Reihenfolge und mit derselben v2-
Kanaldefinition. `transition_position` wird dynamisch als `(i + 0.5) / T(L)`
geschrieben. `global_features` wird nicht stillschweigend um einen Längenkanal
erweitert; die Längenkonditionierung ist ein getrenntes, sichtbares Feld im neuen
Modellvertrag. Damit bleibt der alte 16-dimensionale Vektor unverändert, ohne
zu behaupten, dass v2-Berechnungen über andere Fenster dieselbe Zahlenverteilung
haben.

Der neue Validator verlangt sowohl das externe `L` als auch die passende Form `(T(L),54)`. `validate_feature_array()` und `feature_schema()` für Protocol 1 bleiben unverändert. Der aktuelle Volltrack-Featurecache enthält dagegen 54-kanalige, längenunabhängige Basisarrays; `transition_position` wird dort noch nicht als Fensterposition geschrieben, sondern erst in `model_window()` für das feste v1-Fenster. Dieser Basiscache darf nur dann über Längen wiederverwendet werden, wenn seine unveränderte Rolle im v2-Manifest ausdrücklich belegt ist. Die v1-Cacheversion darf nicht still als v2-Fensterartefakt gelesen werden. L-, T- und Position-Provenienz gehören in den neuen v2-Fenster-/Datasetvertrag; Grid-, Extractor- und Normalisierungs-Provenienz bleibt vollständig erhalten.

Die v2-Fenster müssen mindestens genug vollständige Halbbeat-Bins für die
jeweils angeforderte Länge plus Boundary besitzen. Source- und Target-Fenster
werden getrennt auf Vollständigkeit geprüft; eine global ausreichende Tracklänge
ersetzt diese rollenbezogene Prüfung nicht.

### Entscheidung: längengetrennte NPZ-Shards

Bevorzugt wird Padding plus Maske **nicht**, sondern ein längenhomogenes Format:

```text
<dataset-root-v2>/
  manifest.json
  lengths/
    2bar/{train,validation,test}.npz
    4bar/{train,validation,test}.npz
    6bar/{train,validation,test}.npz
    8bar/{train,validation,test}.npz
  metadata/
    2bar/{train,validation,test}.jsonl
    ...
```

Jeder NPZ-Shard enthält für seine Länge ausschließlich `T(L)`:

```text
features_a:          (N, T(L), 54)
features_b:          (N, T(L), 54)
global_features:     (N, 16)
length_condition:    (N, 1)
example_ids:         (N,)
```

Das vermeidet künstliche Zeitpunkte, Maskierungsfehler und gemischte Tensorformen im normalen Batch. Der DataLoader lädt genau einen Längen-Shard pro Batch; ein expliziter Scheduler wechselt zwischen homogenen Längen-Batches. Eine Padding-/Maskenvariante bleibt nur als späteres, separat versioniertes Performance-Experiment zulässig, falls Messungen einen klaren Vorteil belegen.

Das Root-Manifest enthält `supported_lengths`, `sequence_lengths`, Shape-/Dtype-Verträge, pro Länge und Split die Anzahl, Datei-SHA-256 und Metadaten-SHA-256, Feature-/Candidate-/Grid-Version, Normalizer-ID, Split-Map-ID sowie die vollständige Trainingskonfiguration. Leere Shards sind formal erlaubt, aber vor Training müssen Train und Validation für jede tatsächlich trainierte Länge nichtleer sein; Unterversorgung wird explizit gemeldet und nicht durch Padding kaschiert.

Der aktuelle v1-Exporter nimmt hingegen genau ein `transition_bars`-Argument,
weist die Splits aus den ausgewählten Records neu zu und schreibt ein gemeinsames
`train.npz`/`validation.npz`/`test.npz`. v2 darf diese Logik nicht durch vier
aufeinanderfolgende Exporte imitieren: Die Union aller Kandidatenlängen muss
zuerst gegen eine einzige Split-Map geprüft werden; erst danach erfolgt die
Auswahl und Shardbildung je Länge. `length_condition` wird trotz homogener
Shards gespeichert, damit Request, Manifest, Dataset und Modell denselben
expliziten Vertragswert prüfen können.

NPZs werden in einem neuen Zielordner atomisch geschrieben. Der Export darf keine bestehende Datei öffnen, ersetzen oder entfernen.

## 7. Splitstrategie und Split-Autorität

Die 111 `audio_sha256 -> split`-Zuordnungen aus dem erweiterten Vier-Takt-Manifest werden eingefroren und für alle neuen Längen wiederverwendet, sofern die Kandidaten-Track-Menge identisch ist. Die neue Dataset-Familie referenziert:

- Quellmanifest und dessen SHA-256,
- den kanonischen Hash der gesamten Track-Zuordnung,
- die verwendete Split-Policy-Version,
- die Zuordnung aller beteiligten Track-SHAs.

Für jede Länge werden Kandidaten mit derselben Zuordnung gefiltert. Ein Track darf durch 2, 4, 6 oder 8 Takte niemals in einen anderen Split gelangen. Kandidaten über Split-Grenzen hinweg werden verworfen; es gibt keine nachträgliche Längenkorrektur.

Falls eine neue Länge Tracks benötigt, die im eingefrorenen Mapping unbekannt sind, wird der Export abgebrochen. Dann muss vor allen neuen Längenshards einmalig ein neues vollständiges Mapping über die gesamte Track-Menge erzeugt, versioniert und für alle Längen verwendet werden. Es darf kein Mapping je Länge separat erzeugt werden.

Die Normalisierung wird ausschließlich auf Train-Artefakten berechnet. Ein gemeinsamer `stats_id` über die Trainings-Shards ist vorzuziehen, damit Längen nicht durch vier voneinander abweichende Skalen ungewollt getrennt werden. Validation dient nur zur Modellwahl. Der aktuelle v1-Exporter besitzt noch keinen Loader für die eingefrorene Map; er ruft `assign_track_disjoint_splits()` auf den ausgewählten Records auf. v2 braucht deshalb einen eigenen read-only Map-Loader und muss unbekannte, doppelte oder widersprüchliche Audio-SHAs vor dem Export abbrechen.

Der Testsplit wird im Training und in der Modellentwicklung weder geladen noch
für Caches, Early Stopping, Gewichte, Schwellen oder Längenauswahl verwendet.
Eine ausdrücklich gestartete, nach dem Vertrag eingefrorene Testauswertung darf
Testdaten in einem getrennten Evaluation-Cache lesen oder materialisieren; diese
Ausnahme muss Prozess, Run-Manifest und Cache-Namespace sichtbar als
`test_evaluation_only` markieren. Die stärkere Formulierung „niemals gecacht“
würde den zulässigen finalen Testlauf und die tatsächliche CLI-Trennung falsch
beschreiben.

## 8. Modelle und Training

### 8.1 Kontrollierte Baseline: dynamisches zeitgeteiltes MLP

Das neue MLP erhält `features_a`, `features_b`, `global_features` und `length_condition`. Es erzeugt Intervalle mit `T(L)-1` Positionen und daraus `T(L)` Controls. Alle bisherigen `SEQUENCE_LENGTH`-Expansionen werden nur im neuen Modellzweig durch die Laufzeitlänge ersetzt. Die Parametrisierung bleibt über die Zeit geteilt, damit die Baseline keine unnötige längenabhängige Parameterzahl bekommt.

### 8.2 Temporales Hauptmodell: variables TCN/BiLSTM

Das TCN/BiLSTM verarbeitet `(B,T(L),C)` mit dynamischer Zeitachse und erzeugt `(B,T(L),10)` Controls. Convolution und LSTM sind prinzipiell zeitlängenagnostisch; alle Validatoren, Positionskonstruktionen und Dokumentationsverträge müssen es aber explizit erlauben. Die monotone Parametrisierung muss auch für 16, 32, 48 und 64 Punkte gültig bleiben.

Das ist nur für die Architektur, nicht für den bestehenden Vertrag, verifiziert:
`TCNBiLSTMTransitionControl` arbeitet intern zeitachsenfähig, während
`_normalise_inputs()` und der v1-Outputvertrag weiterhin 32 Schritte verlangen.
Bei der derzeitigen Monotoniekonstruktion werden die beiden explizit
aufgebauten Ownership-/Positionskurven aus `T-1` Logits zu `T` Punkten
rekonstruiert; die übrigen TCN-Ausgabekanäle werden dadurch nicht automatisch
monoton. v2 muss daher jeden monotonen Kanal einzeln benennen und darf nicht aus
der Form `(B,T,10)` ableiten, dass alle zehn Kanäle dieselbe Eigenschaft haben.

### 8.3 Explizite Längenkonditionierung

Beide Modelle erhalten zusätzlich einen kleinen Längenprojektor für `L/8` oder eine versionierte Längen-Embedding-Tabelle. Die Projektion wird in die temporale Repräsentation eingespeist, nicht nur als zufällige Information aus der Anzahl der Eingabeschritte überlassen. Der Batch enthält zugleich den Integer `L` zur Vertragsprüfung. Ein synthetischer Test muss zeigen, dass bei identischen Zeitfeatures und gleicher Form ein geänderter, gültiger Längenkonditionswert den Modellpfad tatsächlich beeinflusst; der Inferenzvertrag muss gleichzeitig verhindern, dass das Modell ein anderes `L` ausgibt.

Die bestehenden Vier-Takt-Modelle laden ausschließlich ihre alten Shapes und Checkpoints. Ein alter Checkpoint darf nicht in ein variables Modell resümieren. Ein neuer Checkpoint darf nur mit dem exakt gleichen neuen Modell-, Dataset-, Objective-, Renderer- und Längenvertrag geladen werden.

### 8.4 Längensampling im Training

Die bevorzugte Trainingsform ist ein Scheduler über längenhomogene DataLoader. Für die vier Längen werden pro Epoche die Beispielzahlen, effektiven Batches und Gewichte protokolliert. Die kombinierte Loss darf nicht implizit von der Zahl der verfügbaren 8-Takt- oder 2-Takt-Beispiele abhängen; die gewünschte Gewichtung (z. B. gleiche Länge-Gewichte oder klar dokumentierte Beispiel-Gewichte) ist Bestandteil des Run-Vertrags.

Der neue Run-Manifestvertrag enthält unter anderem Dataset-Root-Hash, jeden Shard-Hash, Längenset, Batch-Scheduler, Seed, Device, Modellvertrag, Längenkonditionierungs-Version, Renderer-/Objective-Verträge, Normalisierungs-ID und W&B-Modus. W&B bleibt optional; lokales `manifest.json` und `history.json` sind autoritativ. Lokale Pfade und Audio werden nicht als Ersatz für die Vertrags-Hashes in W&B verwendet.

Die aktuellen Runner laden ausschließlich Train und Validation. Ihre
`_immutable_contract()`-Prüfung bindet bereits Dataset-Manifest, Modell,
Renderer/Objective und Checkpoint-SHA; sie enthält aber noch kein Längenset,
keine per-L-Shard-Hashes und keinen mehrlängigen Scheduler. Der v2-Resumevertrag
muss außerdem die Längenreihenfolge, pro-L-Gewichte, Sampling-/Batchzustände,
Normalizer-Hash, Cache-Manifest-Hashes und den exakten Objective-/Renderer-
Vertrag binden. Abweichungen hiervon sind ein neuer Lauf, nicht ein stilles
Resume; wie bisher darf nur die geplante Epochengrenze als veränderlicher
Fortsetzungsparameter behandelt werden.

## 9. Renderer, exakte Dauer und Lossnormalisierung

### 9.1 Exakte Übergangsdauer

Die aktuelle Bridge-Extraktion nutzt für die Übergangssamples eine `min(...)`-Sicherung. Im neuen Bridge-Vertrag ist ein stilles Kürzen unzulässig. Für jedes Candidate werden aus `L`, Beat-Grid, BPM und Sample-Rate die erwartete Übergangsbeat-Anzahl und die deterministisch gerundete Sample-Anzahl berechnet. Nach Source-/Target-Alignment müssen beide Seiten exakt diese Übergangsabdeckung liefern. Eine Abweichung wird verworfen oder durch eine separat dokumentierte, deterministische Ein-Sample-Rundungsregel behandelt; sie wird nicht durch eine kleinere Dauer verborgen.

Das ist eine additive Korrektur, kein Urteil über den alten Renderer: Rendering-
Protokoll 5 erlaubt für den bestehenden Pfad bei unterschiedlich langen
verfügbaren Fenstern ausdrücklich die kürzere Abdeckung, und
`extract_aligned_bridge()` implementiert dies mit `min(...)`. Der v2-Exaktdauer-
pfad darf diese Semantik nicht verändern. Dasselbe gilt für
`extract_aligned_vocal_bridge()`, das heute über `_match_length()` ganze
Vocal-Waveforms kürzt oder auffüllt; im neuen Pfad sind solche Operationen nur
zulässig, wenn sie als exakt begründete Alignment-/Rundungsregel im Vertrag
stehen, nicht als Fehlerverdeckung.

Die Kontrollkurven werden mit genau `T(L)` Punkten an die Audioanzahl interpoliert. Start-/Endpunktsemantik, monotone Grenzen und der letzte Sample-/Beat-Rundungsfall werden im neuen Renderer-Manifest festgehalten. Metriken prüfen neben Sample-Anzahl auch Beat-Abdeckung und BPM-Kontext.

### 9.2 Längeninvariante Objective-Terme

Die bisherigen Renderer können bereits dynamische Control-Längen interpolieren, aber die Defaults `energy_frames=32` und `control_points=32` dürfen im neuen Pfad nicht die Länge bestimmen. Der neue Objective-Vertrag muss `T(L)` aus dem Request erhalten und Audio-Energie auf eine explizit deklarierte, zur `u`-Achse gehörende Zeitdiskretisierung poolen.

Im aktuellen Objective werden Audioenergien mit `adaptive_avg_pool1d()` auf
`energy_frames` gebracht, Controls auf diese Zahl zurückgeführt und die Terme
als Tensor-Mittelwerte aggregiert. Ein bloßes Ersetzen der Konstante 32 durch
`T(L)` wäre noch kein Zeitnormalisierungsvertrag. v2 muss entweder `Q=T(L)` als
verbindliche Quadratur mit Zellbreiten `1/T` festlegen oder eine separate,
längenunabhängige Quadratur `Q` definieren; in beiden Fällen werden die
Gewichte, Randpunkte und der Loss-Term im Manifest gespeichert. Rohe Summen über
Schritte sind ausgeschlossen.

Für alle zeitlichen Terme wird eine normierte Zeitachse verwendet. Bei `T` Control-Punkten mit Randpunkten gilt beispielsweise `u_i=i/(T-1)`; die Featurezentren bleiben `((i+0.5)/T)`. Glätte und Krümmung werden mit den tatsächlichen `Δu`- bzw. Beat-Abständen berechnet und als Mittelwert bzw. normierte Quadratur über die Übergangsdauer aggregiert:

```text
first_derivative  = Δcontrol / Δu
second_derivative = Δ²control / Δu²
loss_term         = normierte Mittelung über u, nicht rohe Summe über T
```

Energieform, Boundary-Terme, Feature-Konditionierung, Vocal-Terme und Ableitungen müssen für dieselbe `T(L)`-Achse validiert werden. Ein äquivalenter normierter Kurvenverlauf über 2 und 8 Takte muss bei gleicher per-Zeit-Abweichung vergleichbare Losswerte liefern. Jeder Loss-Term wird zusätzlich pro Länge und vor der kombinierten Aggregation ausgegeben; dadurch sind Datenmenge und Schrittzahl sichtbar.

Die vorhandene dynamische `maximum_control_increment(T)`-Logik wird wiederverwendet, aber ihre Bedeutung wird als Schritt- oder Zeitnormalisierung im neuen Vertrag eindeutig festgelegt. Eine fixe Grenze pro Schritt darf nicht unbeabsichtigt längere Übergänge stärker bestrafen.

Für die aktuelle Formel gilt: `bounded_monotone_unit_curve()` erhält `T-1`
Logits und erzeugt `T` Punkte; `maximum_control_increment(T)` hängt von der
Anzahl dieser Intervalle ab. v2 vergleicht deshalb nicht rohe
`control[i+1]-control[i]`-Werte zwischen Längen, sondern normierte
Steigungen/Inkremente pro `Δu`. Der Vertrag muss ausdrücklich festlegen, ob die
T-abhängige Schranke die maximal zulässige Masse pro normiertem Intervall oder
eine andere musikalische Eigenschaft beschreibt. Ein Test mit identischen
normierten Kurven für 2 und 8 Takte muss sowohl Monotonie als auch vergleichbare
zeitnormierte Lossbeiträge belegen.

## 10. Vocal-Pfad und RoFormer-Wiederverwendung

Die vorhandenen RoFormer-/Demucs-gestützten Vocal-Stem-Artefakte sind an Track-SHA, Modell und Backend gebunden, nicht an die Zahl der Übergangstakte. Sie können daher read-only für alle vier Längen wiederverwendet werden, wenn Stem-Provenienz, Sample-Rate und Audio-SHA exakt übereinstimmen. Der aktuell dokumentierte Standard ist RoFormer; Demucs bleibt ein explizites Vergleichsbackend. Der variable Vertrag darf daher nicht pauschal nur `Demucs` als Stem-Provenienz voraussetzen.

Neu zu versionieren sind die daraus geschnittenen Vocal-Bridge-Caches. Der Key enthält mindestens Source-/Target-SHA, `transition_length_bars`, `transition_length_beats`, `sequence_length`, erwartete Sampleanzahl, Sample-Rates, Time-Stretch-Backend und die vollständige Stem-Provenienz (Backend, Modellrevision und Artefakt-SHA je Track). Variable Vocal-Datasets verwenden nur neue Cachepfade; vorhandene Vocal-Caches werden nicht überschrieben.

Der stem-fähige Renderer und die Semantik des aktuellen Vocal Objective v5 werden als fachliche Grundlage wiederverwendet. Vor der Wiederverwendung sind insbesondere Vocal-Aktivität, Vocal-Gain-/Ducking-Kurven und alle zeitlichen Strafterme auf `T(L)` und normierte Zeit zu prüfen. Da diese Normalisierung eine semantische Änderung ist, soll der variable Pfad als neues Vocal Objective v6 versioniert werden, statt Objective v5 still umzudeuten. Die fünf bestehenden Objective-v5-Terme bleiben im neuen Manifest einzeln nachvollziehbar; ein aktiver Vocal-Channel-Test wird für 16/32/48/64 Punkte durchgeführt.

## 11. Cache-, Bridge- und Render-Provenienz

Für neue Variable-Length-Waveform-Caches werden neue Formatnamen und Verzeichnisse verwendet, beispielsweise `bridge_waveform_variable_v2` für den generischen und `vocal_bridge_waveform_variable_v3` für den vocalen Pfad, jeweils mit einer zentralen Konstanten und vollständigem Config-Hash. Eine Cache-Verwendung ist nur erlaubt, wenn der gespeicherte Config-Hash inklusive Länge, Samples und Backend dem aktuellen Auftrag entspricht.

Render-/Batch-Manifeste, Rankingdateien und Control-Study-Artefakte erhalten neue Formatversionen und enthalten Länge plus Shape. `render_transition()` und die dynamische Beat-Länge können als technische Grundlage dienen, aber die neue Schicht muss exakte Dauer verifizieren. Alte Batch-/Render-Artefakte bleiben lesbar und werden ausschließlich gelesen.

Der aktuelle generische Bridge-Config enthält zwar bereits
`transition_length_beats`, der aktuelle Cachepfad/Example-ID macht die Länge
aber nicht zu einem vollständigen, separat validierten Vertragsschlüssel mit
`T(L)` und erwarteter Sampleanzahl. Der aktuelle Vocal-Config enthält Stem-
Provenienz, aber ebenfalls nicht alle neuen Geometrie-/Rundungsfelder. v2 muss
deshalb Länge, Beats, `T`, Meter/Grid-Hash, Cue-/Cut-Samples, Render-/Train-
Sample-Rate, erwartete und tatsächliche Sampleanzahl, Tempo-Backend,
Alignmentregel, Quell-SHAs und Stem-Artefakt-SHAs im Config-Hash und Manifest
führen. Alte `bridge_waveform_v1`-/`bridge_waveform_v2_vocal`-Caches werden vom
variablen Loader nicht als Fallback geöffnet.

## 12. Testmatrix

### Verträge und Geometrie

- Tabelle und Validator für `2 -> 16`, `4 -> 32`, `6 -> 48`, `8 -> 64`.
- Ablehnung von 0, negativen, nicht-ganzzahligen, nicht erlaubten Längen, falschem Metrum und falschem Raster.
- Konsistenz von `L`, Beats, `T`, Featureform, Controlform, Audio-Beat-Abdeckung und Manifest.
- Feature Protocol 1 und alle vorhandenen Vier-Takt-Contract-Tests bleiben unverändert grün.

### Kandidaten

- Per-L-Eligibility und per-L-Rejection-Codes.
- Regression: 2-/4-Takt-Kandidat bleibt erhalten, wenn 8 Takte zusätzlich angefragt werden.
- Vollständigkeit aller vier Vor-/Nachfenster, Grid-Provenienz, BPM-Grenzen und Cross-Split-Filter.
- Keine Längenvermischung in IDs, Limits, Ranking oder Manifest.

### Dataset und Splits

- Jede der vier Längen erzeugt nur homogene `(N,T(L),54)`-Shards.
- Leere-Shard- und nichtleere-Train/Validation-Gates.
- Identischer Split-Map-Hash in allen Längen; keine Audio-SHA-Überschneidung zwischen Train/Validation/Test.
- Cross-split-Paare werden verworfen; Längenvarianten desselben Tracks bleiben im selben Split.
- Normalizer wird nur aus Train berechnet und seine ID/Hash wird geprüft.
- Atomare neue Ausgabe, Datei-Hashes und keine Berührung alter NPZs.

### Modelle

- MLP für 16/32/48/64 Zeitpunkte, inklusive `T-1`-Intervallform.
- TCN/BiLSTM-Ausgabe `(B,T,10)` für alle vier Längen.
- Explizite Längenkonditionierung wird geprüft; falsche Längenpaare werden abgewiesen.
- Monotonie, Endpunkte, Wertebereich und dynamische Increment-Grenzen.
- Lade-/Resume-Negativtests für alte Checkpoints und abweichende neue Verträge.

### Renderer und Loss

- Exakte Samples und Beatdauer für alle Längen, inklusive Tempoanpassung und Rundung.
- Kein stilles `min`-Kürzen im neuen Bridge-Vertrag.
- Renderer akzeptiert genau `T(L)` Controls und erzeugt exakt die deklarierte Übergangsdauer.
- Invarianztests für normierte lineare, gekrümmte und Vocal-Kurven; Ableitungs-/Glättungsterme werden nicht durch `T` skaliert.
- Vocal-Stems, RoFormer-Provenienz, Vocal Objective v6 und aktive/inaktive Vocal-Fälle.

### Training, Evaluation und Regression

- CPU-Smoketest je Länge und ein kombinierter homogener Scheduler-Test.
- Train/Validation werden geladen; der Testsplit wird während Training und Modellentwicklung nicht geladen oder für Entwicklungs-Caches verwendet. Eine separate, nachgelagerte `test_evaluation_only`-Evaluation darf ihn in eigenem Namespace lesen.
- Checkpoint-Payload, Run-Contract, Datei-SHA, `weights_only`-Laden und Resume-Vertrag.
- W&B disabled/offline ohne Netzwerkabhängigkeit; lokales Manifest bleibt vollständig.
- Bestehende Test-Suite einschließlich Candidate-, Feature-, ML-, Renderer-, Vocal- und Split-Tests.
- Längenspezifische Blindstudien gegen Equal Power, mit getrennten Auswahlbudgets und Ergebnissen je Länge. Validation bleibt ein Entwicklungs-Gate; unabhängige Aussagen verwenden den eingefrorenen Testsplit erst in einer separaten Evaluation.
- Bekannte langsame bzw. umgebungsabhängige Testbereiche werden getrennt von Contract-/Smoke-Tests ausgewiesen; ein Timeout ist ein dokumentierter Blocker, kein positives Ergebnis.

## 13. Verifizierte Invarianten

Diese Aussagen sind nach dem Repository-Abgleich belastbare Leitplanken für
die spätere Implementierung:

- Feature Protocol 1, Dataset Format 1, die bestehenden Candidate-v1-
  Funktionen, die drei aktuellen Modellpfade, Control-/Objective-Verträge und
  deren Checkpoints werden nicht semantisch geändert. Neue Bedeutungen erhalten
  neue Versionen und neue Namespaces.
- Für v2 gilt ausschließlich `2 -> 16`, `4 -> 32`, `6 -> 48`, `8 -> 64` bei
  4/4 und zwei Halbbeat-Schritten pro Beat. `L`, Beats und `T` werden in jedem
  Übergabevertrag gegenseitig geprüft und nie aus einer einzelnen Arrayform
  erraten.
- Eine Mehrlängen-Kandidatensuche bildet `B_source[L]`, `B_target[L]` und
  `C[L]` unabhängig. Eligibility, Boundary-Budgets, Rejections, IDs, Ranking
  und Metrikaggregationen sind pro L getrennt.
- Source A beginnt am Source-Cue, Target B endet am Target-Cue; beide Fenster
  enthalten genau `T(L)` vollständige Bins. `transition_position` ist lokal und
  hat die Zentren `0.5/T` bis `(T-0.5)/T`.
- Jede Audio-SHA besitzt innerhalb einer Datasetfamilie genau einen Split. Die
  vollständige Union aller Längen wird gegen dieselbe frozen Map geprüft; ein
  Split pro Länge oder eine Map erst nach Längenfilterung ist unzulässig.
- Neue NPZs sind pro Länge und Split homogen `(N,T(L),54)`, ohne implizites
  Padding im Basispfad. Leere Shards werden als solche manifestiert; ein
  trainierbarer Längen-Shard braucht eigene Train- und Validation-Beispiele.
- Normalisierungsstatistiken stammen ausschließlich aus den tatsächlich
  verwendeten Train-Artefakten und besitzen einen verifizierbaren ID-/Hash-
  Vertrag. Validation und Test verändern sie nicht.
- Variable Bridge-Caches speichern exakte erwartete und tatsächliche Samples,
  Beatabdeckung, `T`, Backend und Quellenprovenienz. Der neue Pfad kürzt nicht
  still mit `min(...)` und füllt nicht still über `_match_length()` auf.
- Stem-Artefakte dürfen über Längen read-only wiederverwendet werden, wenn
  Track-SHA, Modellrevision, Backend, Sample-Rate und Artefakt-SHA stimmen;
  geschnittene Vocal-Bridges sind dennoch längenspezifische Caches.
- Monotone Kurven werden aus `T-1` Intervallwerten zu `T` Punkten konstruiert,
  haben deklarierte Endpunkte und werden mit normierter Zeit verglichen. Nur
  ausdrücklich benannte TCN-Kanäle tragen den Monotonievertrag.
- Loss-Terme sind über deklarierte `u`-/Quadraturgewichte normalisiert und
  werden je Länge berichtet, bevor ein vorab festgelegtes Längengewicht aggregiert.
- Training und Modellentwicklung öffnen ausschließlich Train und Validation.
  Eine finale Testauswertung ist ein separater, explizit markierter Prozess und
  beeinflusst keine Auswahl-, Gewichtungs- oder Early-Stopping-Entscheidung.
- Resume prüft den vollständigen neuen Contract-Hash, Shard-/Cache-/Normalizer-
  Hashes, Längenset, Scheduler und Checkpoint-SHA. Alte Checkpoints werden vom
  variablen Loader abgewiesen; ein variables Checkpoint wird vom alten Loader
  nicht als v1 ausgegeben.

## 14. Latente Risiken

- Für 6 und 8 Takte können Source- oder Target-Tracks trotz ausreichender
  Tracklänge zu wenige vollständige Pre-/Post-Roll-Fenster haben. Das ist eine
  messbare Datenunterversorgung, kein Grund für stilles Kürzen oder Padding.
- Der aktuelle `context_coverage()`-Vertrag beschreibt 4+4 Kontext, während ein
  8-Takt-Übergang länger ist. Ohne explizite v2-Kontextentscheidung könnten
  Fenster formal gültig, musikalisch aber kontextarm sein.
- Der aktuelle Datasetexport erzeugt die Split-Zuordnung neu aus selektierten
  Records. Ein v2-Map-Loader ist daher eine echte neue Sicherheitskomponente,
  nicht nur ein anderes Manifestfeld.
- Die 16 globalen Features behalten ihre Form, aber lokale Key-/Harmonie-
  Berechnungen über 16, 32, 48 oder 64 Bins können andere Verteilungen erzeugen.
  Ein Shape-Check allein erkennt diese semantische Drift nicht.
- Mehrere Längen desselben Trackpaares bleiben zwar split-korrekt, sind aber
  korrelierte Beispiele. Länge, Paar, Track und effektive Batchgewichte müssen
  in Training und Evaluation sichtbar bleiben.
- BPM-Anpassung und Sample-Rundung können Source und Target um ein Sample oder
  mehr auseinanderlaufen lassen. Der neue Bridgepfad braucht dafür eine
  deterministische Regel und eine Probe über BPM-identische sowie gestretchte
  Paare.
- Die aktuelle `min(...)`-Semantik im alten Renderer und `_match_length()` im
  alten Vocalpfad dürfen nicht durch gemeinsame Hilfsfunktionen versehentlich
  in v2 gelangen.
- Die T-abhängige Increment-Schranke verändert die Expressivität der Kurven je
  Länge. Eine mathematisch monotone Kurve ist deshalb noch keine gleiche
  musikalische Änderungsrate.
- Vocal-Stem-Qualität und Bridgequalität hängen am Backend. Der aktuelle
  RoFormer-Standard und der Demucs-Vergleich müssen im Cache getrennt bleiben;
  gleiche Track-SHAs bedeuten nicht gleiche Stems.
- Variable TCN-/Vocal-Batches können Speicher- und Laufzeitspitzen erzeugen,
  besonders bei 64 Punkten und langen Waveforms. Ein Scheduler-/Cache-Test darf
  keine Audioartefakte überschreiben, um diese Kosten zu umgehen.
- W&B ist optional und darf keine Autorität für Dataset-, Split- oder
  Checkpoint-Provenienz werden. Offline/disabled muss ohne Netzwerk funktionieren.
- Historische Test- und Blindstudien bleiben historische Artefakte. Neue v2-
  Ergebnisse dürfen deren Ratings, Auswahlbudgets oder Aussagekraft nicht
  rückwirkend umdeuten.

## 15. Arbeitspakete, Dateigrenzen und Abnahmekriterien

Jedes Arbeitspaket wird additiv in neuen Modulen umgesetzt. Bestehende Module
werden höchstens um explizite Exporte oder neue CLI-Einstiegspunkte ergänzt; ihre
alten Validatoren, Defaults und Loader bleiben unverändert. Die genannten neuen
Dateien sind die verbindliche erste Dateigrenze, nicht eine Erlaubnis, die v1-
Implementierung nebenbei umzubauen.

### WP0 — Baseline und Vertragssnapshot

**Dateigrenze:** nur `docs/VARIABLE_LENGTH_TRANSITIONS_PLAN.md` und der
Audit-Eintrag in `docs/Bemerkungen.md`; keine `src/`- oder Artefaktänderung.

**Abnahme:** `git status` zeigt alle vorher vorhandenen Nutzeränderungen
unverändert; die v1-Dataset-Manifest-SHA, die kanonische 111-Track-Map und ihre
Berechnung sind reproduziert; der aktuelle Vier-Takt-Testanker ist benannt; kein
Audio-, NPZ-, Cache- oder Run-Pfad wurde geschrieben.

### WP1 — Zentraler Request-/Längenvertrag

**Dateigrenze:** neu `src/transition_length.py`, neu
`docs/VARIABLE_LENGTH_PROTOCOL.md`, neu `tests/test_transition_length.py`;
additive Exporte nur in `src/__init__.py`, falls erforderlich.

**Abnahme:** Die vier Mappingfälle und die Rückberechnung `L ↔ Beats ↔ T`
bestehen; 0, negative, nicht-ganzzahlige, nicht erlaubte Längen, falsches Meter,
falsches Raster sowie widersprüchliche externe Felder werden abgewiesen. Kein
Validator liest `L` aus einer Arrayform zurück. Ein einzelner Request und eine
Mehrlängen-Requestmenge sind getrennte Typen.

### WP2 — Frozen Split Authority

**Dateigrenze:** neu `src/features/variable_split.py`, neu
`tests/test_variable_split.py`; keine Änderung an
`src/features/dataset_export.py` oder v1-Manifests.

**Abnahme:** Der Loader liest die 111 Zuordnungen read-only aus dem bekannten
Manifest, berechnet exakt den dokumentierten Mapping-Hash, erkennt unbekannte,
doppelte und widersprüchliche SHAs und bindet Quellmanifest-SHA plus
Map-Version. Eine synthetische Union von 2/4/6/8-Längenrecords erhält dieselbe
Zuordnung; Cross-Split-Paare werden vor jeder Längenauswahl verworfen.

### WP3 — Candidate Protocol 2 mit unabhängigen Boundary-Sets

**Dateigrenze:** neu `src/candidates/variable_models.py`, neu
`src/candidates/variable_generation.py`, neu `src/ranking/variable.py`,
additive Exporte in `src/candidates/__init__.py`, neu
`tests/test_variable_candidates.py` und `tests/test_variable_ranking.py`;
`src/candidates/models.py`, `generation.py` und `tests/test_candidates.py`
bleiben v1-Anker.

**Abnahme:** Für eine gemeinsame Anfrage `{2,4,8}` bleiben synthetisch gültige
2-/4-Takt-Grenzen erhalten, obwohl 8 Takte dort nicht möglich sind. Boundary-
und Candidate-Limits sowie Rejection-Zählungen sind je L getrennt; IDs und
Manifeste unterscheiden dieselbe Quelle/Ziel-Kombination nach L. Vollständige
Pre-/Post-Rolls, Grid-Provenienz, Tempo- und Audio-SHA-Filter bleiben aktiv.

### WP4 — Variable Featurefenster und Global-Pair-v2

**Dateigrenze:** neu `src/features/variable_contract.py`, neu
`src/features/variable_extract.py`, neu `src/features/variable_global_pair.py`,
neu `tests/test_variable_features.py`; `src/features/contract.py`,
`extract_track.py` und `global_pair.py` bleiben in v1 unverändert.

**Abnahme:** Für jede L entstehen Source-Post-Cue- und Target-Pre-Cue-Fenster
mit `(T(L),54)`, korrekt gesetzter lokaler `transition_position` und identischer
Kanalreihenfolge. Unvollständige Bins werden abgewiesen. Die vier Längen
validieren gegen dieselbe explizite Kontextkonfiguration; Global-Pair-v2 führt
seine L-/Extractor-Provenienz und besteht Verteilungs-/Shape-Checks, ohne den
16-dimensionalen v1-Validator zu verändern.

### WP5 — Dataset Format 2 und längenhomogene NPZ-Shards

**Dateigrenze:** neu `src/features/variable_dataset_export.py`, neu
`src/ml/variable_data.py`, neu `tests/test_variable_dataset.py`; die v1-Datei
`src/features/dataset_export.py` und `src/ml/data.py` bleiben unverändert.

**Abnahme:** Ein Export erzeugt je L und Split nur `(N,T(L),54)`, `(N,16)` und
`(N,1)`-Konditionen, vollständige JSONL-Metadaten, Datei-/Normalizer-/Split-
Hashes und einen atomaren neuen Root. Der Export bildet die Split-Union vor
der Längenselektion; die Normalisierung liest nur Train. Kein bestehender NPZ-
oder Datasetroot wird geöffnet, ersetzt oder gelöscht. Ein Scheduler erhält nur
homogene Shards; Padding und Maskierung sind im Basispfad nicht vorhanden.

### WP6 — Exakte variable Bridge- und Vocal-Caches

**Dateigrenze:** neu `src/variable_bridge.py`, neu
`src/variable_batch_render.py`, neu `src/ml/variable_cache.py`, neu
`tests/test_variable_cache.py` und `tests/test_variable_render.py`;
`src/bridge.py`, `src/batch_render.py` und die bestehenden `src/ml/data.py`-
Cachepfade bleiben unverändert.

**Abnahme:** Für alle L und mindestens einen BPM-Stretchfall stimmen erwartete
und tatsächliche Samples sowie Beatabdeckung exakt. Der variable Pfad hat keine
`min(...)`-Kürzung und kein ungekennzeichnetes Padding/Truncating. Cache-Hits
erfordern den vollständigen Config-Hash einschließlich L, T, Rundungsregel,
Backends und Stem-SHAs; alte generische und vocale Cacheroots erzeugen keinen
variablen Hit. Die neue Batch-Manifestversion führt Candidate-Rank, Render-
Rank, exakte Grenzen, Sampleanzahl und `tempo_backend` wie der v1-Vertrag,
aber zusätzlich L/T und die getrennte Fensterrolle. Die Stem-Artefakte selbst
werden nur read-only wiederverwendet.

### WP7 — Variable Controls, Modelle und zeitnormiertes Objective

**Dateigrenze:** neu `src/control/variable_differentiable.py`, neu
`src/ml/variable_model.py`, neu `tests/test_variable_control.py` und
`tests/test_variable_model.py`; `src/control/differentiable.py` und
`src/ml/model.py` bleiben v1/v3-Anker.

**Abnahme:** MLP, Vocal-MLP und TCN/BiLSTM verarbeiten 16/32/48/64 mit genau
passenden Outputs und expliziter Längenkonditionierung. Monotone Kurven haben
gültige Endpunkte, `T-1` Intervalle und keine Rückwärtsbewegung; die zulässigen
Kanäle sind explizit getestet. Lineare und gekrümmte normierte Kurven liefern
über Längen vergleichbare zeitnormierte Lossbeiträge; jeder Term ist je L
sichtbar und nicht als rohe Schrittanzahl aggregiert. Vocal Objective v6 prüft
alle bestehenden Terme einzeln.

### WP8 — Homogener Scheduler, Runner und Checkpoint/Resume

**Dateigrenze:** neu `src/ml/variable_training.py`, neu
`src/ml/variable_runner.py`, additive neue CLI-Einstiegspunkte in
`src/ml/__main__.py`, neu `tests/test_variable_training.py` und
`tests/test_variable_resume.py`; `src/ml/runner.py`, `vocal_runner.py` und
deren v1-/v2-Tests bleiben unverändert.

**Abnahme:** Jeder Batch ist längenhomogen; per-L-Zahlen, Reihenfolge und
Gewichte erscheinen im Run-Manifest. Train/Validation werden geladen, kein
Testpfad oder Testcache wird im Trainings-/Entwicklungsrunner geöffnet. Ein
separater Testprozess wird vom Runner nicht versehentlich aufgerufen. Resume
akzeptiert nur identischen neuen Contract-/Shard-/Cache-/Normalizer-Hash und
Checkpoint-SHA; ein alter Checkpoint, ein anderes Längenset oder ein anderer
Scheduler wird abgewiesen. W&B disabled/offline bleibt optional.

### WP9 — Isolierte Evaluation und Studien

**Dateigrenze:** neu `src/evaluation/variable_metrics.py`, neu
`src/evaluation/variable_control_study.py`, neu `tests/test_variable_evaluation.py`;
keine Änderung an historischen Ratings, Batches oder Study-Roots.

**Abnahme:** Technische Metriken, Equal-Power-Vergleiche und Blindstudien werden
je L mit getrennten Auswahlbudgets und Gewichten berichtet. Der eingefrorene
Testsplit wird erst nach abgeschlossenem Modell-/Schwellenvertrag in einem
expliziten `test_evaluation_only`-Run verwendet. Dieser Run schreibt einen
neuen Evaluation-Cache/Manifest, verändert keine Trainingsentscheidung und
übernimmt keine Testdaten in Normalizer, Ranking oder Checkpoint.

### WP10 — Dokumentation und Abschlussgate

**Dateigrenze:** nach verifizierten Läufen ausschließlich die jeweils
betroffenen Protokolle, `docs/STATUS.md` und `docs/Bemerkungen.md`.

**Abnahme:** Jede ausgeführte Sonde, jeder Test, Export, Render- oder Trainings-
lauf enthält in `docs/Bemerkungen.md` Datum, Fragestellung/Reasoning, Setup,
Befehl/Umfang, Ergebnis inklusive Fehlern/Blockaden sowie Schlussfolgerung und
nächsten Schritt. Dokumentation behauptet nur verifizierte Ergebnisse. Kein
Commit wird erstellt.

Es gibt keine automatische In-place-Migration. Alte Vier-Takt-Runs und
Checkpoints werden nicht in variable Formate umgeschrieben. Eine spätere
Konvertierung wäre ein eigener, read-only validierter Export mit eigenem
Artefakt- und Hashvertrag.

## 16. Feste 32-Schritt-Annahmen: vollständiges Analyseinventar

Die folgenden Stellen wurden als echte Übergangsgeometrie- oder Formvertragsannahmen gefunden. Reine Zahlen wie Sample-Raten, Kanalgrößen oder `float32` sind nicht als 32-Schritt-Annahmen aufgeführt.

### Produktivcode

| Datei | Funktion/Klasse | feste Annahme | Plan für v2 |
|---|---|---|---|
| `src/candidates/models.py` | `CANDIDATE_FORMAT_VERSION`; `CandidateRejection` | v1-Candidate kennt die Länge zwar als Feld, aber Rejections tragen keine per-L-Länge und es gibt keinen Request-/`T`-Vertrag | neue v2-Modelle/Rejections additiv; v1-Serialisierung und IDs bleiben unverändert |
| `src/candidates/generation.py` | `CandidateGenerationConfig`; `_eligible_*_boundaries()`; `generate_candidates()` | positive v1-Längen, gemeinsame `all(...)`-Eligibility sowie globale Boundary-Limits über die angeforderte Längenmenge | neue per-L-Generierung mit unabhängigen Sets, Budgets, IDs und Rejection-Provenienz |
| `src/features/contract.py` | Konstanten `TRANSITION_BARS`, `SEQUENCE_LENGTH`; `validate_feature_array()`; `feature_schema()` | `SEQUENCE_LENGTH=32`, Shape `(32,54)`, Schema und `transition_position` mit `/32` | v1 unverändert; v2-Validator und Schema mit `L`/`T(L)` |
| `src/features/extract_track.py` | `TrackFeatureArtifact.model_window()` | Fensterstart/-ende, `arange(32)` und Positionen `/32` | `T(L)` als geprüfter Parameter |
| `src/features/extract_track.py` | `_half_beat_grid()` | Mindestanforderung `SEQUENCE_LENGTH+1` vollständige Halbbeat-Bins | Mindestanforderung anhand maximal angeforderter Länge |
| `src/features/global_pair.py` | `build_global_pair_features()` | Eingaben müssen `(32,54)` sein; Meldung „32-step windows“ | v2 validiert `(T(L),54)` |
| `src/features/global_pair.py` | `estimate_key()` | Dokumentation/Annahmen über 32 Bins | dynamische Fenstergröße aus v2-Kontext |
| `src/features/global_pair.py` | `context_coverage()` | bestehende Vor-/Nach-Kontextkonstanten sind an aktuellen 4-Takt-Kontext gebunden | Kontext- und Übergangsdeckung getrennt versionieren; L explizit speichern |
| `src/features/dataset_export.py` | `export_feature_dataset()`; `_select_candidate_records()` | v1-Auswahl und Extraktion für `transition_bars=4`; Featurefenster über fixed `model_window()` | v2 pro Länge und neuem Shardvertrag |
| `src/features/dataset_export.py` | `_write_split()` | leere Arrays werden als `(0,32,54)` geschrieben | leere Arrays als `(0,T(L),54)` je L |
| `src/ml/data.py` | `FeatureControlDataset`; `_validate_split_arrays()` | NPZ-Arrays müssen `(N,32,54)` sein | Dataset-v2 lädt einen homogenen L-Shard und prüft `T(L)` |
| `src/ml/data.py` | `collate_feature_control_examples()` | Stapeln der fixed Feature-Tensoren | homogener Längen-Batch plus `length_condition` |
| `src/ml/data.py` | `_bridge_cache_config()` / `_vocal_bridge_cache_config()` | Cachevertrag enthält die aktuelle Feature-/Audio-Provenienz, aber keinen vollständigen T/L-Schlüssel | neue Cacheversion mit L, T und exakter Dauer |
| `src/ml/model.py` | `FeatureControlMLP.forward()` | Expansion mit `SEQUENCE_LENGTH-1` | `T(L)-1` nach Requestvalidierung |
| `src/ml/model.py` | `VocalFeatureControlMLP.forward()` | Expansion mit `SEQUENCE_LENGTH-1` und `SEQUENCE_LENGTH` | dynamische Intervalle/Punkte und expliziter Längenkanal |
| `src/ml/model.py` | `TCNBiLSTMTransitionControlOutput`; `TCNBiLSTMTransitionControl.forward()` | Output-/Dokumentationsvertrag für 32 Positionen; fixed Validator | neue `(B,T(L),10)`-Version |
| `src/ml/model.py` | `_normalise_inputs()` | verlangt `(B,32,54)` | alter Validator bleibt; v2-Validator erhält L |
| `src/control/differentiable.py` | `DifferentiableTransitionObjective.__init__()`; `VocalAwareTransitionObjective.__init__()` | Default `energy_frames=32` | kein Default als Geometrie; `energy_frames=T(L)` aus Vertrag |
| `src/control/differentiable.py` | `OptimizableControlCurves.__init__()`; `OptimizableVocalControlCurves.__init__()` | Default `control_points=32` | v2 erhält T explizit |
| `src/control/differentiable.py` | `optimize_control_curves()`; `optimize_vocal_control_curves()` | Default/Studienpfad auf 32 Control-Punkte | v2 erhält T explizit und normalisiert Loss |
| `src/ml/training.py` | `self_supervised_batch_loss()`; `full_band_self_supervised_batch_loss()`; `vocal_self_supervised_batch_loss()` | aktueller Batch wird mit homogener `(B,32,54)`-Featureform an das Modell gegeben; variable Audio-Längen werden erst innerhalb des Beispiels behandelt | v2-Batch-/Loss-Schicht muss homogene `T(L)`-Batches und per-L-Gewichtung explizit führen; kein stilles Padding |
| `src/ml/runner.py` | `train_feature_control_model()` | Objective wird mit `energy_frames=32` erzeugt | variable Objective-Factory mit T(L) |
| `src/ml/runner.py` | `_immutable_contract()`; `_checkpoint_payload()`; `_validate_checkpoint()` | alter Run-/Checkpointvertrag ohne variable Längenfelder | neue Run-/Checkpointversion und Contract-Hash |
| `src/ml/vocal_runner.py` | `train_vocal_feature_control_model()` | Objective `energy_frames=32` | Variable Vocal Objective v6 mit T(L) |
| `src/ml/vocal_runner.py` | `_immutable_contract()`; `_checkpoint_payload()`; `_validate_checkpoint()` | alter Vocal-Run-/Checkpointvertrag | neuer Vocal-Variable-Run-/Checkpointvertrag |
| `src/evaluation/control_probe.py` | `DEFAULT_CONTROL_POINTS`; `export_control_comparisons()`; `_objective_feature_tensor()` | Default 32 und exakte Feature-/Control-Punktzahl | L aus Candidate/Request, neue Studienversion |
| `src/evaluation/blind_control_study.py` | `export_blind_control_study()`; CLI `--control-points` | Default 32; Auswahl auf vier Takte | `T(L)` und längenspezifische Artefakte |
| `src/evaluation/heldout_control_study.py` | `export_heldout_control_comparisons()`; CLI | Default-Control-Punkte 32 trotz Datasetlänge | L aus Testmanifest nur in separater Evaluation |
| `src/evaluation/ml_control_study.py` | `export_blind_ml_control_study()` | Objective und Equal-Power-Baseline mit `SEQUENCE_LENGTH` | neue variable Studienversion und per-L-Auswertung |
| `src/evaluation/vocal_ml_control_study.py` | `export_blind_vocal_ml_control_study()` | Objective `energy_frames=SEQUENCE_LENGTH` | neue variable Vocal-Studienversion |
| `src/evaluation/vocal_objective_study.py` | `export_blind_vocal_objective_study()`; CLI | Default `control_points=SEQUENCE_LENGTH` | T aus explizitem L |
| `src/ranking/feature_baseline.py` | Übergangsfenster-/BPM-basierte Cutpoint-Metriken | v1 nähert Fensterlänge aus BPM und Beatanzahl an; Rankingrollen sind nicht dieselben wie ML-Featurerollen | v2-Ranking mit Länge, exakten Beatgrenzen und klarer Fensterrollen-Provenienz |
| `src/ranking/rendered_transition.py` | `rank_rendered_transitions()` | v1 bewertet vorhandenes Audio mit deklarierter Beatlänge und Rendergrenzen, aber ohne Variable-Length-Manifestvertrag | additive v2-Metrik mit exakter L/T-/Sampleprüfung |
| `src/batch_render.py` | Batch-Manifest und Auswahl-/Render-API | v1-Manifest/Renderprotokoll 5, bestehende Candidate-Längen und historische WAV-/Sidecar-Identitäten | neuer variabler Batch-Wrapper/Manifestvertrag; v1-API und Ausgabepfade unverändert |
| `src/ranking/song_compatibility.py` | `_resample_profile()` über `_track_features()` | 32-Punkt-Rhythmusprofil; dies ist Whole-Track-Vorranking, nicht das Übergangsfenster | als v1-Baseline dokumentiert belassen oder nur in eigenem Rankingvertrag längenspezifisch parametrieren |

`src/bridge.py` (`extract_aligned_bridge()` und `extract_aligned_vocal_bridge()`) enthält keine fixe 32-Schrittform, verwendet aber eine dynamische Beat-Länge mit einer `min(...)`-Kürzung. Diese Stelle ist deshalb für den neuen Exaktdauervertrag kritisch und in Abschnitt 9 berücksichtigt.

### Bestehende Regressionstests mit absichtlich fixierter Vier-Takt-Geometrie

Diese Tests bleiben als v1-Regressionsanker bestehen; sie werden nicht auf v2 umgebogen. Ergänzend entstehen parametrisierte v2-Tests:

| Datei | betroffene Testfunktionen/Fixtures |
|---|---|
| `tests/test_feature_contract.py` | Shape-/Schemaasserts auf `SEQUENCE_LENGTH == 32` |
| `tests/test_feature_dataset_export.py` | NPZ- und Empty-Split-Shapes in den Exporttests |
| `tests/test_track_feature_cache.py` | `model_window`-Shape und Positionen `0.5/32`, `31.5/32` |
| `tests/test_global_pair_features.py` | v1-Featurearrays mit `SEQUENCE_LENGTH` |
| `tests/test_ml_data.py` | Dataset-/Collate-Fixtures mit `(32,54)` und global 16 |
| `tests/test_feature_control_model.py` | MLP-Output, Objective und Increment-Grenze mit `SEQUENCE_LENGTH` |
| `tests/test_tcn_bilstm_model.py` | TCN/BiLSTM-Output `(B,32,10)` und Single-Example-Form |
| `tests/test_vocal_control_model.py` | Vocal-Controls, Objective und Control-Punkte mit 32 |
| `tests/test_differentiable_control.py` | Objective, Control-Kurven und 32-Punkt-Increment-Regression |
| `tests/test_full_band_renderer.py` | Full-Band-Control- und Objective-Shapes mit 32 |
| `tests/test_ml_training_runner.py` | v1-Training-Fixtures/Runvertrag mit fixed Features |
| `tests/test_vocal_ml_training_runner.py` | v2-Vocal-Training-Fixtures mit fixed Features |
| `tests/test_vocal_objective_study.py` | v1-Statistik/Featurefixture mit `SEQUENCE_LENGTH` |
| `tests/test_batch_render.py`, `tests/test_multi_batch_render.py` | v1-Batch-/Multi-Batch-Manifeste, atomare Ausgabe und historische Renderer |
| `tests/test_ranking.py`, `tests/test_rendered_transition_metric.py` | v1-Cutpoint- und gerenderte-Metrik-Verträge |
| `tests/test_control_study_ratings.py`, `tests/test_analyze_control_study.py` | historische Ratings-/Blindstudienverträge |

`tests/test_candidates.py` enthält zusätzlich eine numerische Erwartung für die Anzahl eines bestehenden Candidate-Falls. Diese Erwartung bleibt v1; ein neuer Test prüft ausdrücklich die per-L-Intersection und darf die alte Testsemantik nicht still verändern.

## 17. Risiken und Gesamt-Abnahmekriterien

Hauptrisiken sind zu wenige vollständige 8-Takt-Fenster, ungleiche Datenmengen je Länge, längere Audio-/RoFormer-Kosten, Tempo-Stretch-Artefakte, versehentliche Split-Drift, eine ungewollte Längen-Abkürzung durch Sample-Rundung sowie ein Modell, das die Längenkonditionierung als Shortcut statt als kontrollierte Bedingung nutzt. Die Datenmenge und Qualitätsmetriken werden daher immer je Länge veröffentlicht.

Der Plan gilt als umgesetzt, wenn:

1. der externe Längenwert hart validiert und nie vom Modell bestimmt wird;
2. 2/4/6/8 exakt 16/32/48/64 Halbbeat-Schritte erzeugen;
3. alle neuen Feature-, Dataset-, Modell-, Training-, Checkpoint-, Renderer- und Objective-Verträge versioniert sind;
4. Feature Protocol 1 und bestehende Vier-Takt-Modelle unverändert funktionieren;
5. Candidate-Gültigkeit pro Länge berechnet wird und 8 Takte keine gültigen 2-/4-Takt-Kandidaten entfernen;
6. alle Längenshards dieselbe eingefrorene Audio-SHA-Split-Autorität verwenden;
7. MLP-Baseline und TCN/BiLSTM alle vier Längen mit expliziter Längenkonditionierung verarbeiten;
8. Renderer und Loss exakt dauern und pro Beat/normierter Zeit vergleichbar sind;
9. der RoFormer-gestützte Vocal-Pfad mit neuer, geprüfter variabler Objective-/Cache-Version funktioniert;
10. die Testmatrix einschließlich Isolation des Testsplits aus Training/Entwicklung, der explizit getrennten `test_evaluation_only`-Evaluation, Checkpoint-Hashes und Regressionssuite bestanden sowie jeder Lauf in `docs/Bemerkungen.md` dokumentiert ist.

## 18. Additiver Merge-v2-Vertrag und konkrete Arbeitspakete

Der bisherige Librosa-/aufTAKT-Merge-v1 bleibt der Default von
`PreAnalysis`. Der neue `PartialPreAnalysis`-/`PreAnalysisV2`-Pfad verwendet
`librosa_auftakt_monotonic_partial_v2`, einen eigenen Analysehash und eigene
Cacheordner. Damit bleiben v1-Analysen lesbar, ohne dass ein alter Cache durch
eine neue Provenienz umgedeutet wird.

### Verifizierte Invarianten

- Jede v2-Zuordnung ist monoton, eins-zu-eins und innerhalb von `0.2` Sekunden;
  die Distanzgrenze wird nicht erhöht.
- Ein ausgegebenes v2-Grid enthält ausschließlich reale Librosa-/aufTAKT-Paare;
  fehlende Beats bleiben nur in `diagnostics.merge` und `missing_beats`.
- `fallback_used=false` verlangt mindestens `98 %` Abdeckung beider Folgen im
  gemeinsamen Zeitbereich, endlich streng steigende Samples und acht
  zusammenhängende vollständige Takte. Die Schwelle ist durch `LESS_IS_MORE`
  (`528/533 = 99.06 %` Librosa-Matchabdeckung und vollständige gemeinsame
  aufTAKT-Abdeckung) sowie zwei Vier-Takt-Phrasen begründet.
- Der variable Candidate-v2-Parser verlangt Count-Vollständigkeit und
  zeitliche Adjazenz. Ein Abstand über `1.5 ×` dem Median-Interbeat-Abstand
  erzeugt eine Blockgrenze; Fenster dürfen sie nicht überqueren.
- Die strikte `approximate_grid_policy=reject` bleibt unverändert. v1-Modelle,
  Datasets, Analysecaches und deren numerische Regressionstests bleiben
  außerhalb des v2-Pfads.

### Latente Risiken

- Ein ungewöhnlich stark schwankendes, aber tatsächlich vollständiges Tempo kann
  die medianbasierte Lückenprüfung zu konservativ machen; das erzeugt eine
  nachvollziehbare Rejection, keine erfundene Taktinformation.
- Ein vollständig ausgelassener Takt ist aus Count-Werten allein nicht
  erkennbar. Deshalb ist die zeitliche Adjazenzprüfung für v2 verpflichtend;
  ihre `1.5`-Faktorentscheidung bleibt versionierter Vertragsbestandteil.
- Die acht-Takt-Abnahmeschwelle kann kurze reale Tracks auf Fallback setzen,
  obwohl einzelne kurze Fenster korrekt wirken. Solche Tracks werden als
  fehlende Kandidaten dokumentiert, nicht durch Qualitätsfilter-Lockerung
  freigegeben.
- Die drei Realtracks sind ein Audit und keine statistische Qualitätsaussage;
  ein einzelner Fallback bleibt sichtbar und blockiert die Realfreigabe des
  neuen Mergepfads.

### Arbeitspakete, Dateigrenzen und Abnahme

| Arbeitspaket | zulässige Dateigrenze | Abnahmekriterium |
|---|---|---|
| Merge-v2 und Cacheidentität | `src/analysis/pre_analysis.py`, neue Tests unter `tests/` | v1-`PreAnalysis`-Tests bleiben grün; v2 erzeugt eine andere `analysis_id`, lädt eigene Caches wieder und schreibt atomar |
| Merge-Diagnostik | `src/analysis/pre_analysis.py`, `docs/ANALYSIS_PROTOCOL.md` | Counts, gemeinsamer Bereich, Matches, Coverage, Regionen, Distanzquantile, Barstatistik und Acceptance-Gründe sind reproduzierbar vorhanden |
| Gap-sichere Candidate-v2-Prüfung | `src/candidates/generation.py`, `src/candidates/variable.py`, neue Candidate-Tests | Lücke innerhalb oder zwischen Takten wird nicht von 2/4/6/8-Fenstern überquert; späterer vollständiger Block bleibt nutzbar |
| Synthetic Merge-Audit | `tests/test_partial_merge.py` und `docs/Bemerkungen.md` | exakter Match, Randbeats, fünf fehlende Librosa-Beats, Doppelzuordnung, Mismatch und alte v1-Regressionen sind getestet |
| Realer Drei-Track-Audit | ausschließlich neue Pfade unter `output/`, `docs/Bemerkungen.md` | `LESS_IS_MORE`, `HELP_LESS` und ein Intro/Outro-Track werden mit Stats, Provenienz, Fallback, Blocklänge und Kandidatenlängen vollständig berichtet; kein Batch, Featurecache oder Dataset |

Die Merge-v2-Arbeit endet vor Multi-Song-Batch, Featureexport und Dataset. Erst
nach bestandenem Review darf Prompt 7 mit neuen Analyse- und Exportpfaden
fortgesetzt werden.
