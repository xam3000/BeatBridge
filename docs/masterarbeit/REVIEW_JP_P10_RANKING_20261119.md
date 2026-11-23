# P10 · Welche Fortsetzungsmetrik geht in den Hörversuch?

**Nachtrag vom 23. November 2026.** Die Auswahl unten dokumentiert die früheren P11-Pakete. Für Protokoll V2 gilt der auf einzeln kodierten Fenstern trainierte Kopf der Stufe 2 aus Epoche 6. [Aktueller Vergleich und Auswahl](REVIEW_JP_MERT_FENSTER_20261123.md)

**Auswahl am 19. November 2026.** Für die SSL-Cues in P11 gilt der gerichtete MERT-Kopf der Stufe 2, Seed 20260926, Bestepoche 22. Beide trainierten MERT-Stufen bestanden die beiden vorab festgelegten Kontrollen. Stufe 2 erreicht den höheren mittleren Validation-Recall@1 (85,67 % gegenüber 62,09 %). Damit war die Entscheidung vor dem Vergleich der Regel-Cues und vor der Autorensichtung getroffen. Es gab keinen weiteren Trainingslauf. [Eingefrorene Entscheidungsregel](../EVALUATION_PROTOCOL.md#fortsetzungsmetrik-f2-g1-g5g7) · [Auswahl mit Checkpoint-SHA und beiden Stufen](review_jp_20261118/p10/selection.json)

## Validation und Abkürzungsprüfung

**Präzisierung nach R_P10_01.** Die 85,59 % sind Recall@1 auf der Auswahl-Validation. P09 wählte Epoche 22 nach dem höchsten Recall auf denselben 2.830 Queries, P10 danach die Stufe. Beim festen Checkpoint ergibt ein Perzentilbootstrap über 54 Quellaufnahmen (10.000 Ziehungen, Seed 20261119) 83,2–87,9 %. Dieses Intervall beschreibt die Streuung unter erneut gezogenen Aufnahmen der Auswahl-Validation. Die Optimierung der Epoche und Stufe ist darin nicht berücksichtigt. Bei gleicher Gewichtung jeder der 53 Recording-Gruppen ergeben sich ergänzend 85,33 %. Die Gruppe `recording-bab66d3ae3b59d8ee3cc` enthält zwei Originaldateien.

Die korrekte Fortsetzung folgt nach vier Takten, die strukturfremde Alternative liegt mehr als 16 Takte entfernt. Die Kontrollen zeigen eine Präferenz für die nahe Fortsetzung bei festgehaltener Aufnahmeidentität. Zeitliche Nähe und lokale Klangkontinuität sind dabei nicht getrennt kontrolliert. Alle positiven Trainings- und Retrievalpaare stammen jeweils aus derselben Aufnahme. Die Anwendung auf zwei verschiedene Aufnahmen setzt eine musikalisch sinnvolle Querübertragung voraus. H1 prüft diese Annahme mit menschlichen Bewertungen.

Die 2.830 Queries stammen von 54 Originalaufnahmen in 53 Validation-Gruppen der P07-Septemberinstanz. Für jede Query bewertet jeder Kopf dieselbe richtige Fortsetzung und acht feste Negative aus P08. Vier davon kommen aus anderen Gruppen mit höchstens 5 % BPM-Abstand, zwei weitere aus fremden Gruppen und zwei aus strukturell verschiedenen Abschnitten der eigenen Aufnahme. Alle 53 Gruppen dienen mehrfach als Fremdspender, bis zu 428-mal je Gruppe. Recall@1 und MRR gewichten zuerst Queries innerhalb der Quellaufnahme und dann jede der 54 Aufnahmen gleich. Die vorab permutierte Reihenfolge löst Scoregleichstände im Neunerpanel auf. Alle 39.620 neu berechneten Einzelränge reproduzierten P09. [P08-Panels und Gruppenherkunft](REVIEW_JP_P08_PAARE_20261119.md) · [P09-Trainingsbudget, Features und Parameter](REVIEW_JP_P09_METRIK_20261119.md)

| Kontrolle | Geeignete Fälle und Herkunft |
|---|---|
| Same-Track | Je Query der erste der beiden vorab gezogenen Same-Track-Negativen. **2.830 Kontraste aus 53 Gruppen.** Zwischen Gegenbeispiel und positivem Zwölftaktfenster liegen mehr als 16 vollständige Takte. Mindestens zwei der vier Strukturmerkmale RMS, Bassenergiequote, Kick-Prominenz und Vocal-Aktivität unterscheiden sich um mindestens eine auf Trainingsoriginalen geschätzte Standardabweichung. |
| Intro↔Drop | **844 Kontraste aus 49 Gruppen.** Davon haben 217 Queries aus 40 Gruppen eine introartige richtige Fortsetzung und ein dropartiges Gegenbeispiel. Bei 627 aus 49 Gruppen ist die Richtung umgekehrt. Die Gruppen überlappen. Für 1.986 Queries fehlt ein Gegenabschnitt dieser Art. Sie zählen weiterhin zum Retrieval und zur allgemeinen Kontrolle. |

P08 bestimmte die Abschnittstypen vor dem Scoring je Aufnahme. Introartige Fenster liegen in den ersten 32 nominalen Takten und höchstens beim RMS-Median. Dropartige Fenster liegen später, mindestens am oberen RMS-Quartil und mindestens am Kick-Median. Beide Kontrollstellen stammen aus derselben Originaldatei wie die richtige Antwort. Ein Treffer verlangt einen höheren Score für die echte Fortsetzung, bei Gleichstand zählt ein halber Treffer. Die Kontrollquoten gewichten zuerst innerhalb der Quellgruppe und dann jede Gruppe gleich. Die Abschnittstypen sind akustische Näherungen. [Einzelfälle mit Gruppen, Zielstellen und Scores](../../output/review_jp_20261118/p10_ranking/run01/validation/mert_s2_20260926.csv)

## Offlinetabelle

Die ersten vier Ergebnisspalten betreffen das Retrieval und die beiden Kontrollen. Die letzten zwei betreffen die Reihenfolge der Cues zwischen verschiedenen Aufnahmen. Alle 26 Paare liefern ein definiertes ρ. Die [CSV-Tabelle in voller Genauigkeit](review_jp_20261118/p10/offline.csv) enthält außerdem Parameterzahlen, Fallzahlen, Nenner, Budgets und Checkpoint-Hashes.

| Familie | Stufe | Seed | Bestepoche | Recall@1 (%) | MRR | Same-Track (%) | Intro↔Drop (%) | Top-1 gleich Regel | mittleres ρ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Klassisch | 0 | entfällt | – | 55,75 | 0,6800 | 70,93 | 71,96 | 0/26 | 0,2026 |
| Klassisch | 1 | 20260926 | 30 | 61,35 | 0,7304 | 76,47 | 76,69 | 0/26 | 0,1966 |
| Klassisch | 1 | 20260927 | 27 | 61,02 | 0,7272 | 76,15 | 76,76 | 0/26 | 0,2122 |
| Klassisch | 1 | 20260928 | 26 | 61,15 | 0,7276 | 76,11 | 76,31 | 0/26 | 0,2038 |
| Klassisch | 2 | 20260926 | 3 | 68,66 | 0,7934 | 80,34 | 80,60 | 0/26 | -0,0324 |
| Klassisch | 2 | 20260927 | 4 | 68,44 | 0,7929 | 80,88 | 80,47 | 0/26 | -0,0990 |
| Klassisch | 2 | 20260928 | 5 | 68,37 | 0,7920 | 80,44 | 79,99 | 0/26 | 0,0279 |
| MERT, gleichgewichtetes Mittel über alle 13 Schichten vor dem Kosinus | 0 | entfällt | – | 44,53 | 0,5710 | 64,29 | 67,86 | 0/26 | 0,2399 |
| MERT | 1 | 20260926 | 26 | 62,54 | 0,7487 | 85,11 | 88,30 | 0/26 | 0,0413 |
| MERT | 1 | 20260927 | 29 | 61,91 | 0,7457 | 84,54 | 87,08 | 1/26 | 0,0179 |
| MERT | 1 | 20260928 | 26 | 61,82 | 0,7461 | 84,73 | 88,44 | 1/26 | 0,0253 |
| MERT | 2 | 20260926 | 22 | 85,59 | 0,9151 | 91,97 | 93,24 | 0/26 | -0,0275 |
| MERT | 2 | 20260927 | 17 | 85,90 | 0,9164 | 93,11 | 94,15 | 0/26 | 0,0031 |
| MERT | 2 | 20260928 | 18 | 85,54 | 0,9138 | 92,49 | 94,31 | 1/26 | 0,0554 |

Für MERT-Stufe 1 liegen die beiden Kontrollquoten im Dreiseedmittel bei 84,79 % und 87,94 %, für Stufe 2 bei 92,52 % und 93,90 %. Auch der vorab bestimmte Studienseed liegt bei beiden Stufen in beiden Kontrollen über 50 %. Für jede Kontrolle sind mindestens fünf Gruppen erforderlich. Damit kann der ausgewählte Kopf die echte Fortsetzung auch bei gleicher Aufnahmeidentität häufiger erkennen als ihr strukturfremdes Gegenstück. Wie viel Information über die Aufnahme er daneben nutzt, bleibt offen. MERT-Zustände enthalten Kontext aus dem Encoderchunk, die strukturabhängige Negativziehung begrenzt die Übertragbarkeit auf andere Kandidaten.

**Klassischer Vergleich.** Ohne neuen Kopf erreicht der klassische Kosinus 55,75 % Recall@1, der Kosinus der eingefrorenen MERT-Fenster nach gleichgewichteter Mittelung über alle 13 Schichten 44,53 %. Mit den gerichteten Türmen erreicht die klassische Bedingung 68,49 % im Seedmittel. Der Vorsprung der klassischen Nullstufe ist ein eigener Offlinebefund. Die drei Cue-Bedingungen in P11 sind SSL, Regel und Zufall. Der rohe MERT-Kosinus war die vorgesehene Rückfallvariante mit eingefrorener Repräsentation ohne neu trainierten Kopf.

## Vergleich der Entwicklungs-Cues

Für den Entwicklungsvergleich vertritt der kleinste Datei-SHA jede Validation-Gruppe. In aufsteigender Gruppen-ID-Reihenfolge bilden benachbarte Gruppen ein gerichtetes Paar. Damit entstehen 26 disjunkte Paare aus 52 Gruppen, die letzte Gruppe bleibt übrig. Diese Festlegung und die Begrenzung auf die letzten zwölf verwendbaren Quell- und die ersten zwölf Zielgrenzen sind technische Entscheidungen für diesen Entwicklungsvergleich. Pro Paar bleiben alle 144 Kombinationen erhalten, insgesamt 3.744 Vier-Takt-Cues. Alle 14 Bedingungen und `feature_baseline_v3` verwenden dieselben Cue-IDs. Top-1-Gleichstand entscheidet die kleinere ID. Spearman verwendet mittlere Ränge bei Scoregleichständen. Jedes Paar trägt dasselbe Gewicht. [Paar- und Filtermanifest](../../output/review_jp_20261118/p10_ranking/run01/pairs/pairs.json) · [Scores jeder Methode und jedes Cues](../../output/review_jp_20261118/p10_ranking/run01/pairs/candidate_scores.csv)

Der Studienkopf wählt in **0 von 26 Paaren** denselben Cue wie die Regel. Die mittlere Rangkorrelation beträgt **−0,0275**. Das beschreibt die Cue-Wahl in diesen Suchbereichen. Welche Wahl Hörer bevorzugen, ist offen. Für die auf höchstens eine Stunde begrenzte Autorensichtung stehen die ersten zehn widersprüchlichen Paare der festen Reihenfolge bereit. Je Paar gibt es zwei 19-s-Clips mit demselben Equal-Power-Fade. Der Autor kann nach rund fünf Minuten je Paar die tatsächlich gehörten Dateien und seine Beobachtungen eintragen. Die Notizvorlage ist leer. Sämtliche P10-Audiodaten stammen aus der Entwicklung. [Sichtung mit 20 abspielbaren Dateien und Notizvorlage](../../output/review_jp_20261118/p10_ranking/run02/autorensichtung/Sichtung.md)

## Batch-Render und Reproduktion

Die Paar-ρ reichen von −0,717 bis +0,612 (Stichproben-SD 0,386). Das deskriptive t-95-%-Intervall für den Mittelwert über die 26 disjunkten Paare beträgt [−0,184; +0,129]. Zwei unabhängige uniforme Wahlen aus jeweils 144 Cues hätten im Mittel 26/144 = 0,181 Treffer. Unter diesem Referenzmodell beträgt die Wahrscheinlichkeit für null Treffer (143/144)²⁶ = 0,834. Die beobachtete Null erlaubt daher keine Aussage über systematisch gegensätzliche Entscheidungen.

`mert_continuation_v1` verwendet S und T auf den ursprünglichen Rastern. Der Kopf erhält die Mittel der vier Takte vor S und der vier Takte ab T. Der Ranker prüft Datei-SHA, nachgewiesenes aufTAKT-Raster, Beatindex, Render-Samplekoordinate und vollständige Takte. Das Zielaudio wird erst für den Render an das Quelltempo angepasst. Der Batch schreibt das MERT-Ranking mit Auswahl- und Gewichtsprovenienz in `cue_ranking`, die Regelwerte in `candidate_ranking` und die tatsächliche Wahl in `render_selection`. Historische Proxywerte liefern kein Lernsignal für diesen Kopf. [Ranker](../../src/ranking/continuation.py) · [Batchvertrag](../BATCH_RENDERING_PROTOCOL.md)

Auf „Under Attack“ → „Keep It Raw“ reproduzierte die Inferenz aus den beiden Originalen alle 144 zwischengespeicherten MERT-Scores exakt. Der Sieger `candidate-91852b13b5134942` steht bei der Regel auf Rang 8. Das Equal-Power-WAV enthält 837.900 Stereo-Sampleframes bei 44.100 Hz, davon 277.473 in der Überlagerung. Der Wiederholungslauf lieferte denselben Audio- und Manifest-SHA. [Abspielbares Batch-WAV](../../output/review_jp_20261118/p10_ranking/run01/batch/rendered/0001__candidate-91852b13b5134942__equal_power.wav) · [Batchmanifest](../../output/review_jp_20261118/p10_ranking/run01/batch/manifest.json) · [Prüfnachweis](review_jp_20261118/p10/verified.json)

Im Repositoryroot lassen sich Validation und Regelvergleich mit neuen Ausgabezielen nachspielen. Zum Rendern ergänzt der in P07 installierte Runtime-Pfad den Projektinterpreter.

```powershell
$py = '.venv/Scripts/python.exe'
$replay = 'output/review_jp_20261118/p10_ranking/replay'
& $py -B -X utf8 -m src.evaluation.p10_validation --output "$replay/validation"
& $py -B -X utf8 -m src.evaluation.p10_pairs --validation "$replay/validation" --output "$replay/pairs"
& $py -B -X utf8 -m src.evaluation.p10_listening --pairs "$replay/pairs" --output "$replay/autorensichtung"
$env:PYTHONPATH = (Resolve-Path 'output/review_jp_20261118/p07/runtime').Path
$songs = 'musik/PRIVE Hardstyle Top 1000 of all times - by Scantraxx'
& $py -B -X utf8 -m src.batch_render "$songs/Under Attack - Ran-D.flac" "$songs/Keep It Raw - Public Enemies.flac" --ranking-method mert_continuation_v1 --tempo-alignment global_bpm_v1 --source-boundaries 12 --target-boundaries 12 --renderers equal_power --top-k 1 --preview-before-seconds 5 --preview-after-seconds 14 --output-dir "$replay/batch"
& $py -B -X utf8 -m src.evaluation.p10_verify --root $replay
```

**Gültigkeit nach F am 19.11.** Die Offlinetabelle und die Auswahl aus run01 gelten weiter. Der aktuelle [Batchnachweis aus run02](../../output/review_jp_20261118/p10_ranking/run02/batch/manifest.json) bindet Gerät und Präzision. Die [aktuelle Sichtungsanleitung](../../output/review_jp_20261118/p10_ranking/run02/autorensichtung/Sichtung.md) trennt offene Entwicklungsnotizen von Präferenzdaten. Der [unabhängige Review](review_jp_20261118/reviews/R_P10_01.md) und der ursprüngliche Run bleiben als historische Nachweise erhalten.
