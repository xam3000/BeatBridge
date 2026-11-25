# MERT mit einzeln kodierten Vier-Takt-Fenstern

## Vergleich vor der nächsten Stimuluswahl · 23. November 2026

Der erste Lauf prüft den bereits gewählten Studienkopf (Stufe 2, Seed 20260926, Epoche 22) auf den 2.830 eingefrorenen P08-Panels. Alle neun Kandidaten, ihre Reihenfolge, die Gewichte und die vier gleich gewichteten Takte je Fenster bleiben für beide Auswertungen gleich. Nur der Eingang des eingefrorenen Encoders ändert sich. Jede Abfrage und jeder Kandidat erhalten genau die eigenen vier Takte als Audiosignal. Li et al. geben für das MERT-Vortraining eine Ausschnittlänge von fünf Sekunden an. [MERT, ICLR 2024](https://arxiv.org/pdf/2306.00107)

Die ursprüngliche Schichtung ergibt für den Studienkopf 78,7 % Recall@1 ohne Kontakt und 86,4 % mit Kontakt. Die beiden Gruppen enthalten unterschiedliche Abfragen. Der neue Vergleich paart beide Kodierungen für jede einzelne Abfrage. Bei einem Rückgang des Studienkopfs um mindestens fünf Prozentpunkte wird die MERT-Leiter auf isolierten Fenstern mit den P09-Seeds und Budgets neu trainiert. Diese Arbeitsschwelle dient der technischen Entscheidung. Über den Studienkopf entscheidet danach die bestehende P10-Auswahlregel. Bis zur Entscheidung bleibt run02 historisches Hörmaterial. [Schichtung für alle 14 Bedingungen](../../review_jp/results/mert_kontext_check.json)

Als zusätzlicher Zweiervergleich dient je Abfrage eine zufällig, aber reproduzierbar gewählte entfernte Stelle derselben Aufnahme mit demselben P08-Abschnittstyp wie die echte Fortsetzung. Die Distanzregel fordert mehr als 16 freie Takte zu beiden Fenstern. Für diese Kontrolle entfällt die P08-Bedingung einer strukturellen Mindestdifferenz. Die breite Restkategorie `other` ist eine Grenze der Typisierung. Der Hauptvergleich gewichtet jede Quellaufnahme gleich.

## Gegenprobe mit den eingefrorenen Köpfen

Die 5.563 benötigten Fenster aus 54 Aufnahmen dauern 5,79 bis 7,49 Sekunden (Median 6,40 s). Die Tabelle verwendet dieselben neun Kandidaten je Abfrage. Die Köpfe der Stufe 2 verwenden Seed 20260926 und die auf derselben Validation ausgewählte Epoche. Die klassischen Merkmale wurden bereits lokal extrahiert und dienen in beiden Spalten als identische Referenz.

| Bedingung | Recall@1 mit P07-Kodierung | Recall@1 mit isolierten Fenstern | Änderung |
|---|---:|---:|---:|
| MERT, Kosinus ohne Kopf | 44,53 % | 63,51 % | +18,98 Prozentpunkte |
| MERT, bisheriger Studienkopf | 85,59 % | 66,12 % | −19,47 Prozentpunkte |
| Klassische Merkmale, Stufe 2 | 68,66 % | 68,66 % | 0 |

Der alte Studienkopf verliert bei identischen Abfragen und unveränderten Gewichten seinen Vorsprung. Die Änderung betrifft die gesamte Encoder-Eingabe einschließlich ihrer Länge und Normalisierung. Der Vergleich kann den Verlust deshalb nicht vollständig einem einzelnen Mechanismus zuschreiben. Die zusätzlichen Seeds 20260927 und 20260928 ergeben mit isolierten Fenstern 65,40 % und 64,94 %. [Messwerte und Checkpoint-Prüfsummen](review_jp_20261118/mert_fenster/comparison.json)

Für den Zweiervergleich gab es 2.506 ausreichend weit entfernte Gegenbeispiele derselben heuristischen Klasse. Mit gruppenweiser Gewichtung wählt der bisherige Studienkopf bei der alten Kodierung in 86,64 % der Fälle die echte Fortsetzung, bei der isolierten in 74,29 %. Die klassische Stufe 2 desselben Seeds erreicht 74,30 %. Von den Kontrollfällen liegen 1.892 in `other`, 610 in `drop_like` und vier in `intro_like`. Insbesondere `other` umfasst musikalisch unterschiedliche Abschnitte.

**Entscheidung vom 23. November, vor dem Neurender.** Der bisherige Kopf scheidet für neue Hörstimuli aus. Die neue MERT-Leiter verwendet einzeln kodierte Vier-Takt-Fenster in Training, Validation und Anwendung. Der Vergleich übernimmt alle drei P09-Seeds, 30 Epochen, AdamW, DCL, Produktionsvarianten und P08-Panels. Die P10-Regel wählt die Stufe und den Studienseed nach den ursprünglichen Kontrollaufgaben. Für die Wahl der Stufe spielt die nachträglich ergänzte Zweierkontrolle keine Rolle.

## Neuer Studienkopf · Entscheidung vom 23. November 2026

Für künftige Studienpanels gilt **MERT Stufe 2, Seed 20260926, Epoche 6**, unter dem Namen `mert_continuation_v2`. Beide trainierten Stufen bestanden die zwei vorab festgelegten Kontrollaufgaben im Seedmittel und mit dem Studienseed. Stufe 2 erreichte den höheren mittleren Recall@1. Auswahl und Messung erfolgten auf denselben 2.830 Neunerpanels aus 54 Validierungsaufnahmen. [Auswahl und Checkpoint-SHA](review_jp_20261118/mert_fenster/selection.json) · [Sieben Auswertungszeilen](review_jp_20261118/mert_fenster/validation.csv) · [Trainingskonfiguration](review_jp_20261118/mert_fenster/config.json)

| Eingabe und Kopf | Seed 20260926 | Seed 20260927 | Seed 20260928 | Mittlerer Recall@1 |
|---|---:|---:|---:|---:|
| Isoliertes MERT, Kosinus | 63,59 % einmalig | – | – | 63,59 % |
| Isoliertes MERT, bilinear | 60,94 % | 61,02 % | 61,19 % | 61,05 % |
| Isoliertes MERT, gerichtete Türme | **72,23 %** | 71,88 % | 72,60 % | **72,24 %** |
| Klassische Merkmale, gerichtete Türme | 68,66 % | 68,44 % | 68,37 % | **68,49 %** |

Der mittlere Abstand zur klassischen Stufe 2 beträgt **3,75 Prozentpunkte**. Mit dem ursprünglichen Trainings- und Encoderverfahren betrug er 17,18 Punkte. Die klassische Referenz verwendet dieselben Daten, Seeds, Budgets und Auswahlregeln. Eingabedimension, Parameterzahl und die trainierbare MERT-Schichtmischung unterscheiden sich. Ob Hörer die so gewählten Stellen bevorzugen, bleibt offen. [Klassischer Vergleich und historische Leiter](REVIEW_JP_P09_METRIK_20261119.md)

Beim gewählten Kopf beträgt der mittlere reziproke Rang (MRR) 0,8225. Gegen die entfernte strukturfremde Stelle derselben Aufnahme gewinnt die echte Fortsetzung in 81,99 % der Fälle (53 Gruppen), beim Intro/Drop-Kontrast in 85,02 % (844 Fälle, 49 Gruppen). Bei der zusätzlichen Kontrolle mit gleicher Abschnittsklasse sind es 76,94 % (2.506 Fälle, 53 Gruppen). Die Kontrollquoten gewichten Gruppen gleich und zählen einen Gleichstand als halben Treffer.

Der neue Lauf bündelt gleich lange Ausschnitte ohne Padding. Jedes Beispiel hat nur die eigenen vier Takte im Encoder-Eingang. Für die 135 Fenster einer Entwicklungsaufnahme ergab die erneute Berechnung bitgleiche Werte zum Trainingscache. Der einzelne bfloat16-Forward der ersten Gegenprobe und diese gebündelte Berechnung unterscheiden sich numerisch geringfügig. Die Kosinusreferenz beträgt im ersten Versuch 63,51 % und im gebündelten Lauf 63,59 %. [Prüfjournal](../Bemerkungen.md)

## Wie stark hängt der Vorsprung von den Quellgruppen ab? · 25. November 2026

Auf der Auswahl-Validation liegt MERT im Mittel der drei Trainingsseeds um **3,75 Prozentpunkte** vor den klassischen Merkmalen. Das gepaarte 95-%-Bootstrapintervall reicht von **1,65 bis 5,84 Punkten**. Beim Studienseed sind es 3,57 Punkte mit einem Intervall von 1,04 bis 6,07. Beide Differenzen verwenden dieselbe Gewichtung wie die Ergebnistabelle oben. Zunächst zählt jede Abfrage innerhalb ihrer Aufnahme gleich, anschließend jede der 54 Aufnahmen.

| Gewichtung des Recall@1 auf der Auswahl-Validation | Studienseed 20260926, Differenz [95-%-Intervall] in Punkten | Mittel der drei Seeds, Differenz [95-%-Intervall] in Punkten |
|---|---:|---:|
| Je Aufnahme gleich (54 Aufnahmen, Hauptkennzahl) | +3,57 [1,04 bis 6,07] | +3,75 [1,65 bis 5,84] |
| Je Quellgruppe gleich (53 Gruppen) | +3,63 [1,05 bis 6,21] | +3,81 [1,66 bis 5,95] |
| Je Abfrage gleich (2.830 Abfragen) | +4,03 [1,52 bis 6,51] | +4,48 [2,37 bis 6,61] |

Für jeden der Seeds 20260926, 20260927 und 20260928 wurden die Rang-1-Treffer beider Verfahren anhand derselben P08-Abfrage-ID gepaart. Jede der 10.000 Bootstrapstichproben enthält 53 mit Zurücklegen gezogene Quellgruppen samt allen zugehörigen Aufnahmen und Abfragen. Beide Verfahren und alle Seeds erhalten dieselben Ziehungen (NumPy PCG64, Seed 20261125). Die zweite Tabellenzeile mittelt die Trefferquoten der Gruppen, wobei innerhalb jeder Gruppe alle Abfragen gleich zählen. Die Intervallgrenzen sind die 2,5- und 97,5-Perzentile der gepaarten Differenz. Beim Seedmittel werden die drei gepaarten Unterschiede in jeder Ziehung gemittelt. Die Intervalle beschreiben die Streuung über die Quellgruppen bei festen Köpfen. Die Auswahl der Epoche und die Messung erfolgten auf derselben Validation. [Rangdatei-Prüfsummen, aggregierte Trefferzahlen und Intervalle](review_jp_20261118/mert_fenster/group_bootstrap.json)

## Welchen Pegel erhält MERT? · 25. November 2026

Der eingefrorene Vorverarbeiter setzt `do_normalize=true`. In Training und Anwendung zentriert er jedes Vier-Takt-Fenster separat und teilt seine Samples durch die Quadratwurzel aus Fenstervarianz plus 10⁻⁷. Damit geht der absolute Fensterpegel für MERT bei üblichen Signalpegeln praktisch verloren. Der Lautstärkeverlauf innerhalb des Fensters bleibt erhalten. Die klassischen Merkmale enthalten unter anderem den absoluten, zwischen −60 und 0 dBFS skalierten RMS-Pegel. Damit unterscheiden sich die Eingaben beider Verfahren auch in der verfügbaren Pegelinformation. [MERT-Eingabepfad](../../src/features/p07_mert.py) · [Klassische Taktmerkmale](../../src/features/p07_audio.py)

Die Kontrolle am geladenen Modell verwendete dasselbe 6,40 Sekunden lange Signal in zwei Pegeln. Nach Halbierung der Amplitude (−6,02 dB) unterschieden sich die an den Encoder übergebenen Samples um höchstens 2,03 × 10⁻⁶. Beide Eingaben entsprachen der Normierungsformel im Float32-Vergleich exakt. [Messwerte und Prüfsumme der lokalen Modellkonfiguration](review_jp_20261118/mert_fenster/group_bootstrap.json)

## Nachrechnung und Entwicklungsrender

Die Nachrechnung aus dem gewählten Checkpoint reproduzierte die Auswahlregel, alle 2.830 einzelnen Validierungsränge, Recall@1 und MRR. Im historischen P10-Suchraum der 26 disjunkten Entwicklungspaare wählten Regel und neuer Kopf in **0 von 26 Paaren** denselben Cue. Das mittlere Spearman-ρ der Rangfolgen beträgt **0,1682**. Alle 3.744 Cue-IDs und Regelscores entsprachen dem ursprünglichen P10-Vergleich. Das beschreibt unterschiedliche Entscheidungen bei der Stellenwahl. [Prüfnachweis](review_jp_20261118/mert_fenster/verified.json) · [Sieger und Rangkorrelation je Paar](review_jp_20261118/mert_fenster/pairs.csv)

Für „Under Attack“ → „Keep It Raw“ reproduzierte der Ranker aus den beiden Originaldateien alle 144 zwischengespeicherten Scores exakt. Beim normalen CLI-Lauf ließ die aktuelle Tempo-Prüfung neun dieser Cues zu. Der Sieger `candidate-28ec86b17ab759a2` ergab einen 19-s-Stereoexport bei 44.100 Hz mit 282.624 Frames Überblendung. Die neun Scores im Batch wichen höchstens um 1,01 × 10⁻⁷ von der Offlineberechnung ab. Der Lauf verwendete ausschließlich Entwicklungsmaterial. [Batchnachweis](review_jp_20261118/mert_fenster/batch_verified.json) · [Entwicklungs-WAV](../../output/review_jp_20261118/mert_fenster/batch01/rendered/0001__candidate-28ec86b17ab759a2__equal_power.wav)

## Reproduktion aus dem Projektstamm

Der Gruppenbootstrap lässt sich aus den veröffentlichten Trefferzahlen je Aufnahme nachrechnen. Mit den privaten Rangdateien und dem lokalen Modell prüft der zweite Aufruf zusätzlich alle Abfrage-IDs und den Eingang des Encoders. Dafür wird ein neuer Zielpfad benötigt.

```powershell
$py = '.venv/Scripts/python.exe'
& $py -B -X utf8 -m src.evaluation.mert_group_bootstrap --replay docs/masterarbeit/review_jp_20261118/mert_fenster/group_bootstrap.json
$env:HF_HUB_OFFLINE = '1'
$env:PYTHONPATH = (Resolve-Path 'output/review_jp_20261118/p07/runtime').Path
& $py -B -X utf8 -m src.evaluation.mert_group_bootstrap --output output/mert_bootstrap_wiederholung.json
```

Die Befehle verwenden den eingefrorenen lokalen P07-Modellordner, die Originalaufnahmen und die P08-Splits. `cache01` enthält die separat berechneten Vier-Takt-Fenster. Beim erneuten Training prüft der Lader die Identität der Produktionsfassung, den Modellvertrag und die SHA-256 der zwischengespeicherten Daten. Die Zielordner für Vergleich, Training und Prüfung müssen jeweils neu sein. Bei einer frischen Installation über die Projekt-Requirements ist Transformers 4.49.0 bereits vorhanden. Die Umgebungsvariable `PYTHONPATH` unten bindet die separate Laufzeit des ursprünglichen P07-Rechners ein.

```powershell
$py = '.venv/Scripts/python.exe'
$basis = 'output/review_jp_20261118/mert_fenster'
$env:HF_HUB_OFFLINE = '1'
$env:PYTHONPATH = (Resolve-Path 'output/review_jp_20261118/p07/runtime').Path
& $py -B -X utf8 -m src.evaluation.mert_window_check "$basis/vergleich_wiederholung"
& $py -B -X utf8 -m src.ml.mert_isolated_train "$basis/training_wiederholung" --cache "$basis/cache01"
& $py -B -X utf8 -m src.evaluation.mert_isolated_verify "$basis/training_wiederholung/selection.json" "$basis/cache01" "$basis/pruefung_wiederholung"
```

Der normale Batch liest die im Projekt hinterlegte Studienauswahl. Ihr Checkpoint muss am Pfad aus `selection.json` vorliegen.

```powershell
$songs = 'musik/PRIVE Hardstyle Top 1000 of all times - by Scantraxx'
& $py -B -X utf8 -m src.batch_render "$songs/Under Attack - Ran-D.flac" "$songs/Keep It Raw - Public Enemies.flac" --ranking-method mert_continuation_v2 --source-boundaries 12 --target-boundaries 12 --renderers equal_power --top-k 1 --preview-before-seconds 5 --preview-after-seconds 14 --output-dir "$basis/batch_wiederholung"
```
