# P08 · Vier Takte überbrücken

## Festlegung am 19. November 2026 vor der ersten Paarziehung

Das [eingefrorene F2-Protokoll](../EVALUATION_PROTOCOL.md#fortsetzungsmetrik-f2-g1-g5g7) gibt k = L = 4, den Samplingseed 20261118 und höchstens 64 verschiedene Downbeats d pro Recording-Gruppe vor. Der Split stammt aus dem verifizierten P07-Manifest. P09 erhält dieselben IDs für beide Familien und alle Stufen. Vorgesehen sind 30 Epochen mit Batchgröße 32 einschließlich Restbatch, Seeds 20260926, 20260927 und 20260928, AdamW mit Lernrate 0,001 und Weight Decay 0,0001. P08 führt je Familie einen Optimiererschritt auf demselben ersten Trainingsbatch aus.

### Welche Takte gehören zum positiven Paar?

S bezeichnet das Ende von Drop A, T den Beginn von Drop B. Beide sind Downbeats in der Zeitbasis ihres jeweiligen Tracks. Beim Ausrichten des Zieltempos wird auch die Sampleposition von T umgerechnet. Die Taktindizes im Schema sind nullbasiert, Intervalle rechts offen.

```text
Zeit im Mix       vier Takte davor    |  vier Takte Überlagerung  | vier Takte danach
Quelle A          S−4 S−3 S−2 S−1     |  S   S+1   S+2   S+3     |
Ziel B                                |  T−4 T−3   T−2   T−1     | T   T+1 T+2 T+3
Selbstfortsetzung d−4 d−3 d−2 d−1     |  d   d+1   d+2   d+3     | d+4 d+5 d+6 d+7
                  Query               |  ausgelassene Takte       | positive Antwort
```

Bei der Selbstfortsetzung liegen S = d und T = d+L auf demselben Raster. Der Loader liefert die k Takte vor S und die k Takte ab T. Er verlangt lückenlose Beatindizes **und** anschließende Samplegrenzen über alle 2k+L Takte. Eine P07-Zeilennummer zählt nur gespeicherte vollständige Takte. Erst die Prüfung gegen das Ursprungsraster erlaubt die Addition innerhalb des Fensters. Beim Zwei-Track-Render bestimmen die beiden Raster zunächst [S,S+L) und [T−L,T). In ausgerichteten Samples verwendet der Fade die kürzere Dauer n. Er mischt [S,S+n) mit [T−n,T) und setzt den Zieltrack bei T fort. [Cuevertrag](../CANDIDATE_PROTOCOL.md) · [Renderer](../../src/cutting/fade_cut.py)

### Ziehung, Struktur und Kontrollen

- Kandidat ist ein Ziel-Downbeat mit L Takten gültigem Vorlauf und k Takten Fortsetzung. Eine Query braucht zusätzlich k Takte vor d. Aus den nach Aufnahme-SHA und d sortierten Queries je Gruppe ziehen wir ohne Zurücklegen. Wir halten Ausschlüsse nach der Budgetziehung mit Grund fest. Separate, aus Seed und ID abgeleitete Zufallsströme binden Budget, Negative und Ranggleichstände.
- Je Validationquery ziehen wir vier BPM-nahe und zwei weitere fremde Recording-Gruppen ohne Zurücklegen. Pro Gruppe wählen wir eine zulässige Zielstelle. Die BPM-Regel folgt dem Cuegenerator, |a−b|/max(a,b) ≤ 0,05. Zwei weitere Stellen stammen aus derselben Originaldatei. Die neun Kandidaten stehen in einer vorab permutierten Reihenfolge, die zugleich Ranggleichstände auflöst. Der erste gezogene Same-Track-Fall dient als feste Einzelkontrolle.
- Für die Struktur beschreiben wir jedes k-Takt-Zielfenster durch seine mittlere Lautheit (RMS in dBFS), Bassenergiequote, Kick-Prominenz und Vocal-Aktivität. Wir verwenden die P07-z-Werte aus dem Fit auf Trainingsoriginalen. In mindestens zwei der vier Größen muss die alternative Stelle um mindestens eine Trainingsstandardabweichung von der richtigen Fortsetzung abweichen. Zwischen Alternative und dem gesamten positiven Zwölftaktfenster müssen mehr als 16 vollständige gespeicherte Takte liegen. Diese konservative Untergrenze zählt Rasterlücken als null. Position allein genügt damit auch bei wiederholten Drops nicht. Die Deskriptoren steuern ausschließlich die Negativziehung.
- Für die separate Intro↔Drop-Kontrolle kennzeichnen wir vor dem Scoring Zielfenster anhand des Originals. Ein introartiges Fenster beginnt in den ersten 32 nominalen Takten ab Dateianfang und hat höchstens den Median der Fenster-RMS dieser Aufnahme. Ein dropartiges Fenster beginnt später und erreicht sowohl das obere RMS-Quartil als auch mindestens den Median der Kick-Prominenz. Quantile über gültige Zielfenster derselben Aufnahme, linear interpoliert. Bei entgegengesetzter Kennzeichnung und erfüllter Struktur-/Abstandsregel ziehen wir einen festen Kontrollkandidaten. Diese akustische Operationalisierung liefert keine manuell bestätigten Abschnittsgrenzen. Fehlende Fälle werden gezählt.
- Training verwendet je Query zwei BPM-nahe, einen weiteren fremden und einen strukturfremden Same-Track-Kandidaten sowie die positiven Fortsetzungen der anderen Recording-Gruppen im Batch. Jede physische Zielstelle zählt pro Query nur einmal, auch bei alternativer Produktion. Eine Trainingsquery wird je Epoche einmal gesehen. Quell- und Zielansicht rotieren deterministisch über die P07-Fassungen. Die expliziten Alternativen verwenden die Zielproduktion der Query. Validation bleibt beim Original.

### Verlust bei möglichen falschen Negativen

Chuang, Robinson, Lin, Torralba und Jegelka leiten aus einer Mischung positiver und negativer Beispiele eine Korrektur der geschätzten negativen Masse ab. Wir übernehmen Gleichungen (7) und (8) mit einer positiven Selbstfortsetzung (M = 1). Für Kosinuswerte s, Temperatur t, u = exp(s⁺/t) und vᵢ = exp(sᵢ/t) gilt pro Query mit N gültigen Negativen

```text
g = max((mean(vᵢ) − τ⁺ u)/(1 − τ⁺), exp(−1/t))
ℓ = log(1 + N g/u)
```

Vorab setzen wir t = 0,2 und τ⁺ = 0,05 für alle Köpfe und beide Familien. Fünf Prozent modellieren eine kleine, verbleibende Kontamination trotz Strukturfilter. Weder diese Rate noch ein Hörurteil lassen sich aus der Zeitordnung bestimmen. Die harte, bedingte Ziehung weicht von der marginalen Stichprobe im Paper ab. Die Korrektur ist hier eine Modellannahme ohne Garantie eines unverzerrten Schätzers. Die Untergrenze folgt aus s ≥ −1. Bei τ⁺ = 0 ergibt sich für gültige Kosinuswerte gewöhnliches InfoNCE. Die Zeitfolge bestimmt das positive Paar. [Chuang et al., NeurIPS 2020, Abschnitt 4](https://proceedings.neurips.cc/paper/2020/file/63c3ddcc7b23daa1e42dc41f9a44a873-Paper.pdf)

## Messung an einem gerenderten Cue und einer P07-Selbstfortsetzung

Der Vier-Takt-Render `candidate-a8a01bebc98c1203` verwendet zwei Entwicklungstracks bei je 156,605 BPM. Die Zeilen stammen aus den zugehörigen aufTAKT-Rastern. Der Renderer arbeitet hier bei 44.100 Hz.

| Fenster | Beatindizes der Grenzen | Samples im Raster | Effektive Samples im Fade |
|---|---|---|---|
| Query vor S auf A | 203 → 219 | [3.428.352, 3.701.760) | vor dem Fade |
| Ausblendung ab S auf A | 219 → 235 | [3.701.760, 3.969.536) | [3.701.760, 3.969.536) |
| Einblendung bis T auf B | 484 → 500 | [8.466.432, 8.734.720) | [8.466.944, 8.734.720) |
| Fortsetzung ab T auf B | 500 → 516 | [8.734.720, 9.001.984) | nach dem Fade |

Die Vorschau verzeichnet 267.776 Überlagerungssamples. Der B-Vorlauf ist im Raster 512 Samples länger. Das Kürzen an seinem Anfang erhält die erste Ziel-Zählzeit bei T. Die erste versiegelte P07-Validationsquery hat d in Cachezeile 5. Die Query umfasst Zeilen 1–4, die Überlagerung 5–8 und die richtige Antwort 9–12. Im nativen Beatindex liegen die vier Grenzen bei 6, 22, 38 und 54, bei 24 kHz an den Samples 159.939, 315.977, 470.343 und 623.595. [Rohmanifest, Downbeats und geprüfte Fenster](P08_VERIFIED_20261119.json)

## Paarbestand für P09

| Größe | Training | Validation |
|---|---:|---:|
| P07-Originale / Recording-Gruppen | 236 / 230 | 54 / 53 |
| Geometrisch gültige d vor Budgetziehung | 20.613 | 4.202 |
| Gezogene Queries | 13.351 | 3.016 |
| Ausschluss wegen zu kleiner Same-Track-Auswahl | 352 | 186 |
| Verwendbare positive Paare | **12.999** | **2.830** |
| Vertretene Quellaufnahmen / Quellgruppen | 234 / 228 | 54 / 53 |
| Explizite Negative, BPM-nah / weitere fremde / eigene Aufnahme | 25.998 / 12.999 / 12.999 | 11.320 / 5.660 / 5.660 |

Alle 53 Validationsgruppen kommen mehrfach als fremde Donoren vor, maximal 428-mal pro Gruppe. Die 2.830 Panels enthalten je neun unterschiedliche Zielstellen. Der größte gemessene BPM-Abstand im BPM-Stratum beträgt 3,0303 %. Bei den zwei frei gezogenen fremden Gruppen lagen ebenfalls 4.560 von 5.660 Stellen innerhalb der 5-%-Grenze. Der kleinste Abstand über die Same-Track-Proben beträgt 17 vollständige Takte. Für den Identitätstest liegen 2.830 feste Same-Track-Kontraste vor. Beim separaten Abschnittstest haben 217 Queries eine introartige und 627 eine dropartige richtige Antwort. Zusammen decken sie 49 Quellgruppen ab. Die übrigen 1.986 Queries liefern weiterhin ein Retrievalpanel. [Paarmanifest und Gruppenzähler](../../output/review_jp_20261118/p08_paare/run02/manifest.json)

Beim technischen CPU-Smoke erhielt der klassische Kopf Eingaben der Form 32 × 4 × 82 und der MERT-Kopf 32 × 4 × 13 × 768. Die Smoke-Köpfe mitteln Takte und bei MERT zusätzlich die Zustände, projizieren auf 32 Dimensionen und normieren für den Kosinus. Bei 28 Queries gingen 31, bei vier Queries 30 verschiedene fremde Batchfortsetzungen zusätzlich in den Verlust ein. Auf denselben IDs ergaben sich Gradientennormen von 3,52236 und 3,10114. Ein AdamW-Schritt änderte beide Projektionen. Diese Messung bestätigt den Trainingspfad. Die Wahl eines Rankers erfordert P09/P10. [Smoke-Nachweis mit IDs](P08_SMOKE_20261119.json)

Die vier ausgewählten Strukturmerkmale prägen die Schwierigkeit der Aufgabe für beide Familien. Die Vorgabe kann einen klassischen Kopf begünstigen, der dieselben Größen als Eingaben erhält. Außerdem enthalten die P07-MERT-Zustände bereits den Kontext ihrer Encoderchunks. Die Taktlücke gilt für die übergebenen Zeilen. Sie garantiert keine akustische Trennung der rezeptiven Felder. Die Auswertung in P09/P10 gilt für genau diese vorberechneten Repräsentationen.

## Reproduktion

Aus dem Repositoryroot in ein neues Ausgabeverzeichnis schreiben. Der Vollaudit benötigt den lokalen Vier-Takt-Rohbericht aus P13. Der Trainingsloader prüft das Paarmanifest gegen die SHA im dauerhaften Vollaudit und prüft die Hashes der verwendeten P07-Arrays.

```powershell
$replay = 'output/review_jp_20261118/p08_paare/replay'
.venv/Scripts/python.exe -B -X utf8 -m src.features.p08_pairs --output $replay
.venv/Scripts/python.exe -B -X utf8 -m src.evaluation.p08_verify --dataset $replay --receipt "$replay/audit.json"
.venv/Scripts/python.exe -B -X utf8 -m src.evaluation.p08_smoke --dataset $replay --receipt "$replay/smoke.json"
```

`train.jsonl` und `validation.jsonl` identifizieren Punkte als Aufnahme-SHA plus nullbasierte P07-Zeile. Bei der Query ist das die Zeile d, bei jedem Kandidaten der Anfang seines Zielfensters. Die Splitdateien mit Suffix `_budget.json` und `_excluded.jsonl` enthalten Nenner und Ausschlüsse. `PairWindows.training_batch` liest die expliziten Fenster und liefert die Maske für in-batch ergänzte Ziele. `retrieval_item` liefert die fest permutierten neun Zielsequenzen und den Index der richtigen Antwort. Bei Scoregleichheit ist die gespeicherte Reihenfolge beizubehalten. `same_control` und das gegebenenfalls vorliegende `intro_drop_control` identifizieren die gesonderten P10-Proben. Beim Training ist Epoche 0 die erste Epoche. [Loader und DCL](../../src/ml/p08_contrastive.py) · [Sampling](../../src/features/p08_pairs.py) · [Prüfjournal mit Laufhistorie](../Bemerkungen.md)
