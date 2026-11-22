# Review JP · Unabhängige Prüfung von P06 (Controllerdiagnose), R_P06_02

Datum: 19. November 2026. Prüfgegenstand: Paket P06 laut `docs/REVIEW_JP_UMSETZUNG.md`, Stand Checkout `b40a60a` mit unversionierten Änderungen. Die Prüfung ist eine eigene Reviewsitzung. Sie hat weder Produktionscode, Originale, Gewichte noch Ergebnisartefakte verändert. Es wurde kein Training gestartet. Finale Testdaten wurden nicht ausgewertet (Details in Abschnitt 6).

Befundstatus in der Aufgabenliste: P06 ist als abgeschlossen geführt. Die Korrekturen aus Abschnitt 3 sind für den Schritt F offen.

## 1. Geprüfte Behauptungen

Drei tragende Aussagen des Kapitels `docs/masterarbeit/REVIEW_JP_P06_CONTROLLER_20261118.md` wurden eigenständig aus den Rohdateien nachgerechnet:

- **A.** Das Intervall für S−M bei R4, vier Takte, `0,034835 bis 0,057884` (Kapitel Zeile 62). Prüfung der Bootstrap-Einheit gegen das Protokoll.
- **B.** Die Anteile am direkt erreichten Gewinn: M 77,60 %, F 47,29 % und F 93,37 % am gedämpften Start bei R3 mit EP-v1 (Zeile 60, 66–68). Dazu R4 mit M 76,88 bis 78,56 % und F 22,39 bis 30,30 % (Zeile 62).
- **C.** Die Trennung von Train und Validation nach Recording-Gruppen sowie die Auswahlregel des Best-Checkpoints (Zeilen 30, 36, 48, 60).

## 2. Befunde mit echten Fehlern

### F-1 · Hoch · Bootstrap zieht Trackpaare statt Recording-Komponenten

- **Fundstellen:** `src/evaluation/controller_summary.py:145` (`rng.integers(len(by_pair), …)` zieht einzelne gerichtete Paare mit Zurücklegen) und `:174` (Intervall aus `diffs[bootstrap]`). Protokollvorgabe in `docs/EVALUATION_PROTOCOL.md:83`: „Bei geteilten Aufnahmen ganze Komponenten statt einzelner Kanten mit Zurücklegen ziehen.“ Kapitel `REVIEW_JP_P06_CONTROLLER_20261118.md:38` nennt die Einheit „gerichteter Paare“. Zeile 62 berichtet das Paarintervall als Ergebnis.
- **Befund:** Der Code folgt nicht dem Protokoll. In den P06-Daten teilen sich Aufnahmen mehrere Paare. Bei R4 hat die größte Aufnahme 6 Paare. Das Recording-Netz hat 52 Kanten in 12 Komponenten, die größte davon 15 Kanten. Bei R1–R3 (D2) gibt es 5 Kanten in 2 Komponenten, die größte Aufnahme wird 3-mal verwendet.
- **Nachrechnung** (Skript `docs/masterarbeit/review_jp_20261118/reviews/R_P06_02_pruefung.py`):

| Bedingung | Paar-Bootstrap (Code) | Komponenten-Bootstrap (Protokoll, Variante B) |
|---|---|---|
| R4, 4 Takte, S−M | 0,034835 bis 0,057884 (reproduziert) | 0,035708 bis 0,058904 |
| R4, 2 / 6 / 8 Takte, S−M | 0,027413 bis 0,035341 / 0,034139 bis 0,047382 / 0,031763 bis 0,043417 | 0,028314 bis 0,034670 / 0,033021 bis 0,046891 / 0,030559 bis 0,044577 |
| R3 EP-v1, S−M (5 Paare, 2 Komponenten) | 0,065123 bis 0,181457 | 0,103475 bis 0,127067 |
| R2, S−M (5 Paare, 2 Komponenten) | 0,013573 bis 0,046594 | 0,019757 bis 0,033150 |

- **Auswirkung:** Der Punktschätzer (S−M = 0,045078 bei R4, 4 Takte) bleibt unverändert. Die Aussage „S−M > 0“ bleibt in der Komponentenvariante erhalten. Die Intervallgrenzen verschieben sich um etwa 0,001 nach oben. Bei R1–R3 ist das Intervall mit zwei Komponenten nicht belastbar, und die Breite ändert sich stark. Die Spalten `delta_vs_M_boot_lo/hi` in `p06/matrix.csv` sind für R1–R3 deshalb nicht als Unsicherheitsangabe verwendbar.
- **Korrekturanforderung:**
  1. In `controller_summary.py` die Ziehung auf Komponenten umstellen (Zeilen 145 und 174). Komponenten aus dem Gruppengraphen (Knoten = Recording-Gruppe, Kante = gerichtetes Trackpaar) bilden. Die Gruppen sind über `p01/exposure_tracks.csv` abbildbar.
  2. Den Schätzer eindeutig festlegen, siehe F-4.
  3. Die bisherigen Paarintervalle als „Paar-Bootstrap, nicht protokollkonform“ kennzeichnen. Die Komponentenintervalle in einem neuen Ergebnispfad erzeugen.
  4. Im Kapitel Zeile 38 und 62 das Verfahren nennen und die Komponentenzahl angeben (R4: 12). R1–R3 ohne Intervall berichten oder deskriptiv mit „zwei Komponenten“ kennzeichnen.

## 3. Befunde mit mittlerer oder niedriger Priorität

Diese Punkte sind keine Rechenfehler. Sie betreffen Aussagekraft und Wortwahl, das Kapitel muss sie aber korrigieren, bevor es in die Thesis geht.

### F-2 · Mittel · Auswahl und Berichtswert verwenden dieselbe Validation

- **Fundstellen:** Die Auswahl erfolgt auf dem Validation-Loss (`src/ml/cue_ranker_runner.py:260`, ebenso `src/ml/runner.py:521`, `src/ml/vocal_runner.py:443`, `src/ml/variable_runner.py:321`). Das Kapitel berichtet M auf denselben Validation-Paaren (Zeile 30 und 36). Die Headline in Zeile 3 sagt „senken den Validierungsproxy … stärker als eine einzige Kurve“.
- **Auswirkung:** M ist auf genau den Daten gewählt, auf denen der Vergleich M gegen F gemessen wird. Der Vorteil von M gegenüber F ist dadurch optimistisch, die Größe der Verzerrung ist unbekannt. Das Protokoll lässt diese Auswahl ausdrücklich zu (`EVALUATION_PROTOCOL.md:37`), das Kapitel nennt die Konsequenz aber nicht.
- **Korrekturanforderung:** In Zeile 3 und in der Diskussion zu R2 und R4 festhalten: „Best-Checkpoint auf derselben Validation gewählt, Werte sind In-Sample für die Auswahl, keine Generalisierungsaussage.“ Keine neue Validation oder neuer Test anlegen; das liegt außerhalb des Plans.

### F-3 · Mittel · Stichprobenbasis R1–R3 ist klein

- **Fundstellen:** Zeile 36 (5 Validierungspaare aus 5 Aufnahmen, 2 Komponenten) und Zeile 60 (R3 mit einem Seed). Zeile 3 formuliert die Aussage allgemein.
- **Auswirkung:** Die Befunde für R2 und R3 stützen sich auf fünf gerichtete Paare mit effektiv zwei unabhängigen Aufnahmegruppen. Die Richtung ist plausibel, der Umfang nicht belastbar.
- **Korrekturanforderung:** In Zeile 3 die Stichprobenbasis nennen: „fünf Paare, zwei Aufnahmekomponenten, bei R3 ein Seed“. Die Formulierung „Der R3-Vergleich beruht auf einem Seed“ (Zeile 36) bleibt als Einschränkung stehen.

### F-4 · Mittel · Der Komponenten-Schätzer ist nicht eindeutig definiert, die Zahl im Journal lässt sich nicht reproduzieren

- **Fundstelle:** Das Journal `docs/Bemerkungen.md` enthält im Eintrag vom 19.11. zu R_P06_01 für R4 bei vier Takten die Komponentenzahl `0,035693 bis 0,058477`.
- **Befund:** Drei naheliegende Schätzer ergeben andere Grenzen:
  - Variante A, Mittel der Komponentenmittel: 0,032750 bis 0,059672.
  - Variante B, Mittel über die Kanten der gezogenen Komponenten mit Vielfachheit (Protokollwortlaut „im Mittel über die gezogenen Kanten“): 0,035708 bis 0,058904.
  - Variante C, eindeutige Kanten der gezogenen Komponenten: 0,036856 bis 0,055810.
  Keine der Varianten trifft `0,035693 bis 0,058477` genau. Die Abweichung zu Variante B liegt bei 0,00002 unten und 0,00043 oben.
- **Auswirkung:** Die Grenzen hängen vom Schätzer um etwa 0,001 bis 0,002 ab. Die Aussage „untere Grenze über null“ gilt in allen drei Varianten (kleinste untere Grenze 0,0328).
- **Korrekturanforderung:** Den Schätzer im Protokoll mit einem Satz festlegen, Variante B ist der Protokollwortlaut. Das Komponentenintervall mit dem Skript im Repo erzeugen. Die Zahl im Journal daraufhin prüfen und ersetzen.

### F-5 · Mittel · R3-Ergebnis hängt vom 30-Epochen-Budget ab

- **Fundstellen:** Kapitel Zeile 60 (Obergrenze erreicht). `p06/training.csv`: EP-v1 R3 mit Best E27, letzte Epoche E30. Die Patience von 6 hätte erst bei E33 gegriffen, der Lauf endete also am Budget. Der Legacy-R3 endete dagegen durch Patience bei E24 (Best E18).
- **Auswirkung:** Der Wert „M erreicht 77,60 % des Gewinns E−D“ ist ein Wert am Budgetende bei einem Seed. Die Obergrenze 30 war vorab festgelegt, die Aussage darf also nur für dieses Budget gelten. Eine Verlängerung ist außerhalb des Plans und wird hier nicht verlangt.
- **Korrekturanforderung:** Bei der Zahl in Zeile 60 und in der Headline „bei 30 Epochen (Budgetende), ein Seed“ ergänzen. Die unterschiedliche Abbruchart der beiden R3-Läufe (Budget gegen Patience) im Kapitel nennen.

### F-6 · Niedrig · R1 wurde nach einer einzigen Epoche gewählt

- **Fundstellen:** Zeile 48 (Epoche 1 bei allen drei Seeds) und Zeile 54 (`M` bei R1 = 0,415208). `training.csv`: Minimum bei E1, danach steigt der Validation-Loss bis E7 auf 0,416783 (Legacy) bzw. 0,418703 (Seed 20260928).
- **Auswirkung:** Die Aussage „Der passende Übergabezeitpunkt hilft diesem Modell“ (Zeile 54) beruht auf einem Zustand nach einer Epoche. Die Aussage ist gültig, sie beschreibt aber einen früh gestoppten Zustand.
- **Korrekturanforderung:** Im Absatz zu R1 „nach einer Trainingsepoche (Auswahl E1)“ ergänzen.

### F-7 · Niedrig · Statusangabe und Unabhängigkeit des bestehenden Reviews

- **Fundstellen:** `docs/REVIEW_JP_UMSETZUNG.md`, Zeile 109 (P06 abgeschlossen), Zeile 120 (R_P06_01 abgeschlossen), Zeile 121 (F zu P06 offen). Die Datei `docs/masterarbeit/review_jp_20261118/reviews/R_P06_01.md` nennt sich „Unabhängiger Review“.
- **Befund:** Der Auftrag beschreibt P06 als noch nicht unabhängig geprüft. Die Aufgabenliste führt aber bereits einen Review R_P06_01 vom 19.11. Ob dieser von einer eigenständigen Sitzung geschrieben wurde, geht aus den Dokumenten nicht hervor. Dieser Bericht ersetzt ihn nicht, er ergänzt ihn. Die Befunde überschneiden sich in F-1 und stimmen dort überein.
- **Korrekturanforderung:** Die Aufgabenliste führt beide Reviews nebeneinander mit Datum, Verfasser und Stand von F. Der Status „P06 abgeschlossen“ bleibt nur mit offenem F zulässig.

### F-8 · Hinweis · Unversionierte Artefakte

- **Befund:** `git status` zeigt `docs/masterarbeit/review_jp_20261118/`, `src/evaluation/controller_summary.py`, `src/ml/control_initialization.py` und weitere P06-Dateien als unversioniert. Der Nutzer muss sie committen. Das ist kein Fehler im Code, aber die Ergebnisse lassen sich ohne den Commit nicht eindeutig zuordnen.
- **Korrekturanforderung:** Nutzercommit vor Verwendung in der Thesis. Keine Commits durch den Agenten.

## 4. Unsicherheiten, die nicht als Fehler gelten

- **U-1 · Schätzer des Komponenten-Bootstraps.** Siehe F-4. Die exakte Zahl hängt von einer nicht festgelegten Konvention ab.
- **U-2 · Selektionsoptimismus.** Siehe F-2. Die Größe ist unbekannt. Bei R4 mit 52 Paaren dürfte sie kleiner sein als bei R1–R3 mit fünf Paaren, das ist aber nicht gemessen.
- **U-3 · Oracle-Referenz D.** D ist eine Optimierung pro Validation-Cue mit 80 Schritten und liefert einen erreichten Vergleichswert, kein Optimum. Das Kapitel benennt dies (Zeile 30). Die 77,60 % gelten deshalb relativ zu diesem Wert und können bei besserer Optimierung anders ausfallen.
- **U-4 · R4-E0 ist rekonstruiert.** Die historische Epoche 0 fehlt. Die rekonstruierte Ausgabe wird als solche gekennzeichnet (Zeile 40). Nicht verifiziert wurde, ob die Rekonstruktion dem Initialisierungsvertrag entspricht.
- **U-5 · Kanalstatistik.** Die Angabe „13 der 54 Kanäle konstant“ (Zeile 42) gilt laut Kapitel für die Train-Shards. Die Preflight-Datei für D2 listet in der Validation zusätzlich `silence_probability` als konstant (14). Das ist kein Widerspruch, da das Kapitel nur Train nennt.
- **U-6 · Hörbezug.** Die Aussagen zur wahrgenommenen Qualität sind korrekt als nicht belegt markiert (Zeile 70). Dieser Review prüft keine Hörbewertung.

## 5. Geprüfte Invarianten (bestanden)

| Nr. | Invariante | Prüfung | Ergebnis |
|---|---|---|---|
| I-1 | Trainings- und Validation-Gruppen sind disjunkt, D2 | `output/datasets/…split_20260805/examples.jsonl` mit `exposure_tracks.csv` | 43 bzw. 5 Gruppen, Schnittmenge 0 bei Gruppen und Tracks, 0 nicht zugeordnete Trackreferenzen |
| I-2 | Trainings- und Validation-Gruppen sind disjunkt, D4 für 2/4/6/8 Takte | `metadata/<n>bar/{train,validation}.jsonl` | 223/53 bzw. 222/53 Gruppen, Schnittmenge 0 bei Gruppen und Tracks |
| I-3 | D4-Validation: 53 vs. 52 Gruppen in der Preflight-Datei | Abgleich mit den Preflight-Manifesten | Die eine Abweichung ist eine Gruppe mit genau 3 Fenstern. Diese 3 Fenster fehlen in den 156 Preflight-Manifesten, entsprechen also dem Kapitel (156 von 159). Kein Leck. |
| I-4 | Auswahlregel Best-Checkpoint | `p06/training.csv`, Regel aus `EVALUATION_PROTOCOL.md:37` | Alle Auswahlen konsistent: R1 E1 (×3 Seeds und Legacy), R2 E34/E10/E35, R2-Legacy E34 (Min E38 innerhalb 0,0001), R3 E27, R3-Legacy E18, R4 E34 |
| I-5 | Prozentwerte R3 EP-v1 | `p06/matrix.csv` | M 77,60 %, F 47,29 %, F am gedämpften Start 93,37 % |
| I-6 | Prozentwerte R4 | `p06/matrix.csv` | M 76,88 bis 78,56 %, F 22,39 bis 30,30 %, Übereinstimmung mit Zeile 62 |
| I-7 | Punktschätzer S−M, R4, 4 Takte | `p06/pairs.csv` | 0,045078 |
| I-8 | Paar-Bootstrap im Code entspricht seiner Beschreibung | Nachrechnung mit Seed 20261121 | 0,034835 bis 0,057884, identisch mit Zeile 62 |
| I-9 | CPU-Rekonstruktion des R3-Checkpoints | `matrix.csv` M gegen `training.csv` E27 | 0,2400383 gegen 0,2400352 (Abweichung 3·10⁻⁶) |
| I-10 | Konstante Eingabekanäle D2 (Train) | `preflight/R1_4.json` | 13 Sequenzkanäle und 5 globale Merkmale, passend zu Zeile 42 |
| I-11 | Synthetische Regressionen, Initialisierung und Evaluation | `pytest` auf `tests/test_control_initialization.py` und `tests/test_evaluation_exposure.py` | 44 bestanden |
| I-12 | Renderer-Regressionen | `pytest` auf `tests/test_render_comparison.py` | 23 bestanden (Lauf mit beschreibbarem `--basetemp`) |

Nicht erneut geprüft: die 121.724 Matrixeinträge, die Diagonalen und die Gleichheit der E0-Audiohashes. Die Konsistenz dieser Werte ist durch den Review R_P06_01 dokumentiert, ich habe sie nicht unabhängig wiederholt.

## 6. Grenzen dieser Prüfung

- Es wurde kein Audio erneut gerendert und kein Modell neu berechnet.
- Die Datei `output/datasets/…split_20260805/examples.jsonl` enthält auch Testzeilen. Das Prüfskript liest die Datei vollständig, verwendet aber nur Zeilen mit `split` gleich `train` oder `validation`. Testinhalte wurden nicht ausgewertet. Die D4-Testdatei ist laut Dateigröße leer (0 Byte).
- Die Prüfung nimmt die Gruppenzuordnung aus `p01/exposure_tracks.csv` an. Eine Gruppenzuordnung, die von dieser Datei abweicht, würde I-1 bis I-3 verändern.
- Die Hörbewertung ist nicht Gegenstand dieses Reviews.

## 7. Korrekturliste für Schritt F

| Nr. | Priorität | Korrektur | Abhängigkeit |
|---|---|---|---|
| F-1 | hoch | Bootstrap auf Komponenten umstellen, neuer Ergebnispfad | Keine externe Abhängigkeit |
| F-2 | mittel | Wortlaut zur Auswahl auf derselben Validation | Keine |
| F-3 | mittel | Stichprobenbasis R1–R3 in der Headline nennen | Keine |
| F-4 | mittel | Schätzer festlegen, Zahl im Journal ersetzen | F-1 |
| F-5 | mittel | Budgetabhängigkeit R3 nennen | Keine |
| F-6 | niedrig | R1 als Auswahl nach einer Epoche kennzeichnen | Keine |
| F-7 | niedrig | Beide Reviews in der Aufgabenliste führen | Keine |
| F-8 | hinweis | Nutzercommit der P06-Artefakte | Nutzer |

Keine dieser Korrekturen verlangt neues Training, einen neuen Sweep, eine neue Population oder einen weiteren Hörversuch.
