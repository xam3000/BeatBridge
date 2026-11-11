# Auswertung des renderfix-Hörtests vom 6. November 2026

In allen **19 bewerteten Beispielen** erhielten Equal Power und die vier
trainierten Modelle denselben Platz. Der Test zeigt damit **keinen
beobachteten Präferenzvorteil der gelernten Controller** gegenüber Equal Power
auf diesen Beispielen. Er belegt weder eine generelle Gleichwertigkeit der
Methoden noch eine hohe absolute Übergangsqualität.

## Datengrundlage und Ausschluss

Ausgewertet wurde ausschließlich
`output/four_models_shared_20pairs_validation_20261105_renderfix/` mit dem
Bewertungsexport vom **2026-11-06, 11:00:13 MEZ**
(`exported_at_utc=2026-11-06T10:00:13.657Z`). Der Nutzer meldete das Hören als
abgeschlossen. Der ausgemusterte September-Satz und seine alten
Browserbewertungen gehen nicht in diese Auswertung ein.

Der Export enthält 20 Beispielzeilen mit fünf Kandidaten. In 19 Zeilen sind
alle fünf Plätze explizit als `1` eingetragen: 95 gültige Platzangaben.
Beispiel 11 enthält fünf `null`-Werte. Auf Rückfrage bestätigte der Nutzer am
6. November: **„Wegen Tempoproblem ohne Ranking lassen“**. Dieses Beispiel
bleibt als gehörtes, kommentiertes Beispiel erhalten, wird aber aus allen
Präferenzzahlen ausgeschlossen. Fehlende Plätze werden nicht als
Gleichstand oder schlechte Bewertung ersetzt.

Erst nach dieser Klärung und Prüfung der übrigen Bewertungen wurde der
Antwortschlüssel inhaltlich geöffnet. Seine 20 Zuordnungen enthalten jeweils
genau einmal alle fünf Methoden. Alle 100 WAV-Dateien wurden ausschließlich
per SHA-256 gegen das öffentliche Manifest geprüft; sämtliche Hashes stimmen.
Originalbewertungen, Player, Manifeste und Audiodateien blieben unverändert.
Es wurden keine Audios neu angehört, gerendert oder akustisch vermessen.

## Präferenzergebnis

| Methode | Bewertete Beispiele | Allein bester Kandidat | Gemeinsam bester Kandidat | Siege / Gleichstände / Niederlagen gegen Equal Power |
|---|---:|---:|---:|---|
| Equal Power | 19 | 0 | 19 | Referenz |
| Time-shared MLP v1 | 19 | 0 | 19 | 0 / 19 / 0 |
| Vocal MLP v2 | 19 | 0 | 19 | 0 / 19 / 0 |
| TCN/BiLSTM v1 | 19 | 0 | 19 | 0 / 19 / 0 |
| Variable TCN/BiLSTM v1 | 19 | 0 | 19 | 0 / 19 / 0 |

Auch sämtliche Modell-Modell-Vergleiche enden mit 0 Siegen, 19 Gleichständen
und 0 Niederlagen. Über die zehn möglichen Methodenpaare entstehen 190
abgeleitete paarweise Gleichstände. Das sind **keine 190 unabhängigen
Beobachtungen**, sondern Umkodierungen derselben 19 Rankings.

Die leeren Legacy-Listen `ranking=[]` bedeuten hier nicht „unbewertet“:
Dieses Feld kann nur strikte Reihenfolgen darstellen. Maßgeblich sind die
expliziten `ranks`. Ein neuer Player setzt leere Felder auf `null`; die 95
Einsen sind daher keine automatisch vorausgewählte Standardeinstellung.

Der Mittelwert der eingegebenen Plätze beträgt bei jeder Methode 1,0. Für
eine übliche Rangdarstellung mit Gleichständen teilen sich fünf gleich
platzierte Kandidaten jedoch die Positionen 1 bis 5: Der mittlere Rang
(Midrank) ist jeweils **3,0**. Weder die eingegebene Eins noch die 19
geteilten ersten Plätze sind eine absolute Qualitätsnote oder 19 Siege.
Kriterienscores für Sauberkeit, Energieverlauf, Bassübergabe, Vocal-Klarheit
oder Artefaktfreiheit sind im Export nicht enthalten und werden nicht ergänzt.

## Hörnotizen

| Beispiel | Songpaar | Originalnotiz | Einordnung |
|---|---|---|---|
| 8 | 2 The Dancefloor → Won’t Let Me Down | „störende note im übergang in allen “ | Alle fünf Varianten wurden gleich platziert. Ein gemeinsames Problem von Songkombination, Cue oder Rendering ist eine zu prüfende Hypothese; die Notiz belegt keine Ursache und keinen modellspezifischen Fehler. |
| 11 | Mess Of My Creation → Who Is She | „song b ist schneller in der passage“ | Bewusst ohne Ranking belassen und aus dem Präferenzvergleich ausgeschlossen. Ein lokales Tempo- oder Rasterproblem ist noch nicht messtechnisch bestätigt. |

Im öffentlichen Manifest ist `tempo_adjustment_fraction` für beide Beispiele
0,0. Dieser globale Auswahlwert widerlegt den lokalen Höreindruck bei
Beispiel 11 nicht. Die konkrete Passage und ihre Beat-/Downbeat-Abstände
müssten separat geprüft werden. Beispiel 8 bleibt trotz seines kommentierten
Problems im Ranking enthalten; der Nutzer hat dort alle fünf Plätze vergeben.

## Reichweite des Ergebnisses

Die 20 ausgewählten Vier-Takt-Cues stammen aus fünf gerichteten Songpaaren
und insgesamt fünf Audiohashes. Nach Ausschluss bleiben pro Songpaar
4, 5, 3, 4 und 3 bewertete Cues. Die wiederholten Tracks und Cues innerhalb
eines Songpaars begrenzen die unabhängige Information. Alle fünf gerichteten
Songpaare bleiben im Präferenzvergleich vertreten.

Es handelt sich um die Bewertung eines Nutzers auf ausgewählten
Dataset-v1-Validierungsbeispielen. Die Kandidaten waren pro Zeile zufällig
beschriftet; die bereits dokumentierte Wiedererkennbarkeit des variablen
Modells begrenzt die Verblindung. Die Modelle verwenden unterschiedliche
Trainings-, Feature-, Objective- und Renderer-Verträge. Das variable Modell
nutzt auf den gemeinsamen v1-Cues neu berechnete Protokoll-2-Merkmale; diese
Studie ist kein protokollgleicher Vergleich auf seiner eigenen Validation.
Die v1-Validierungszuordnung garantiert außerdem keine globale Held-out-
Population über alle Modellkorpora hinweg.

Die korrigierte 44,1-kHz-Ausgabe beseitigt den dokumentierten
Bandbegrenzungsfehler des alten Satzes. Daraus folgt keine vollständige
Kontrolle aller Unterschiede zwischen den Modellpfaden. Die im bisherigen
Projektstand fehlenden passenden ungelernten Baselines und unabhängigen
Hörvergleiche werden durch diesen Satz nicht ersetzt.

Alle verwertbaren Vergleiche sind Gleichstände. Deshalb werden keine
p-Werte, Konfidenzintervalle einer unabhängigen Cue-Stichprobe oder
Äquivalenzaussagen berichtet. Die erhobenen Rankings enthalten keine
gerichtete Präferenzinformation, mit der sich eine Rangfolge begründen ließe.

## Folgerung für die Arbeit

Die vier gelernten Controller wurden nun im korrigierten gemeinsamen
Hörsatz bewertet. Ein hörbarer Präferenzgewinn gegenüber Equal Power ist
darin nicht belegt. Die früheren Proxy-Loss-Verbesserungen bleiben technische
Trainingsresultate; sie lassen sich anhand dieses Hörtests nicht in einen
beobachteten Präferenzvorteil übersetzen. Ebenso wenig zeigt der Test eine
Präferenzverschlechterung. Für die verbleibenden Forschungsfragen bleiben
die Beschränkungen der Stichprobe und der Baselinezuordnung bestehen.

Als nächster sachlicher Schritt sollten die gemeinsame Störung in Beispiel 8
und die lokale Tempoabweichung in Beispiel 11 geprüft werden. Falls eine
weitere Wirksamkeitsstudie folgt, benötigt sie vorab festgelegte Vergleiche,
passende Baselines, global getrennte Tracks und weitere unabhängige Rater.
Aus dem vollständigen Gleichstand allein lässt sich keine bestimmte
Trainingsänderung ableiten. Es wurde keine neue Studienfreigabe, kein
Training und kein Thesis-Umbau vorgenommen.

## Nachvollziehbarkeit

- [Maschinenlesbare Ergebnisse](./LISTENING_STUDY_ANALYSE_20261106.json):
  Einzelbewertungen mit Methodenauflösung, zehn Paarvergleiche,
  Songpaargruppen, Ausschlussgrund und 100 Audiohashes.
- [Auswertungsskript](../scripts/analyze_listening_export_20261106.py):
  `.venv\Scripts\python.exe -X utf8 -B scripts/analyze_listening_export_20261106.py`.
  Das Skript erzeugt einen neuen Ergebnissnapshot und lehnt das Überschreiben
  einer vorhandenen Ergebnisdatei ab; zum Wiederholen den vorhandenen Snapshot
  vorher gesondert archivieren oder einen neuen Ausgabepfad wählen.
- [Test- und Entscheidungsprotokoll](./Bemerkungen.md), Eintrag vom
  2026-11-06 zur Auswertung des renderfix-Hörtests.

SHA-256 der unveränderten Eingangsdaten:

| Datei | SHA-256 |
|---|---|
| `manifest.json` | `a3c1edc7fd4e68399777f733c1364cdb84782cfbf43176824a21df48cd8e4909` |
| `ratings.json` | `c32b48d50fb19590201b5cf3943fc1f558f051fd4a58d223528502b09c0091a0` |
| `answer_key.json` | `dd991b096de0738b05c44c1265e8f6dfbec4014d184e5a86f141717d020205f2` |
