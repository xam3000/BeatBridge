# Rückmeldung vom 25. November zur Umsetzung vom 23. November

Rückmeldung vom 25. November 2026. Geprüfter Stand: Commit `69a5c59` vom 23. November (deine Commits `e61ae2d` und `69a5c59`). Bezug: [Rückmeldung vom 22.11.](./RUECKMELDUNG_20261122.md) und dein [Umsetzungsdokument](../docs/REVIEW_JP_UMSETZUNG.md). Einstieg in alle Review-Dokumente: [README](./README.md).

Verlauf: erste Fassung am 23.11. geschrieben, am 25.11. übergeben. Am 25.11. kam die ausführliche Fassung von Abschnitt 9 dazu: die Schritte vor dem Hörtest und was außerdem vor der ersten Einladung feststehen muss. An den Befunden hat sich dabei nichts geändert. Die Datei hieß bis zum 25.11. `RUECKMELDUNG_20261123.md`.

## 1. Kurzfassung

Du hast an einem Tag alle drei Befunde bearbeitet, den Mashup-Export gebaut und die Auswertung geschrieben. Der MERT-Gegenversuch ist vorbildlich: Er bestätigt den Verdacht, du berichtest den Einbruch offen, und die Entscheidung über den Studienkopf steht datiert vor dem Neurender.

Vor der ersten Einladung zum Hörtest sind drei Dinge offen:

1. Der harte Schnitt rotiert in der Erhebung nicht, obwohl dein Protokoll Version 2 das verlangt. Die Betreuung hat am 23.11. entschieden: Er soll rotieren (Abschnitt 10).
2. Die Hörprobe der neuen Tempo-Angleichung steht aus, die Clips sind aber schon gerendert.
3. Der Probelauf mit einer außenstehenden Person fehlt.

Für die Thesis kommen zwei Nachträge dazu: eine Unsicherheitsangabe für den MERT-Vorsprung und die Einordnung der Tempo-Prüfung, die fast alle Stellen verwirft. Ein zweites Audit (Abschnitt 13) bringt zwei weitere Pflichtpunkte: einen Überschreibschutz im Einzelrenderer und die Zeilenenden der P09- und P10-Belege.

## 2. Wie geprüft wurde

| Marke | Bedeutung |
|---|---|
| **[C]** | von mir selbst im Code gelesen |
| **[C*]** | von einem Hilfsagenten gelesen, die Fundstelle habe ich nachgelesen |
| **[A]** | von einem Hilfsagenten gelesen, von mir nicht nachgeprüft |
| **[B]** | aus deinen versionierten Belegen, nicht neu gerechnet |
| **[M]** | von mir ausgeführt |
| **[K*]** | aus dem zweiten Audit (Abschnitt 13), die Fundstelle habe ich nachgelesen |
| **[K]** | aus dem zweiten Audit, von mir nicht nachgeprüft |

Tests **[M]**: 426 bestanden, 6 übersprungen, kein Fehlschlag. Das sind zwei Läufe, weil PySide6 erst nachinstalliert werden musste ([Testläufe](./TESTLAEUFE.md), Nr. 14 und 15). Die neuen Tests prüfen Verhalten und nicht nur Formate, zum Beispiel einen verrutschten Schlag bei gleicher Spanne oder die Wiederfindung bekannter Effekte in der Auswertung.

Die Artefakte unter `output/` liegen weiter nur bei dir. Ich habe nichts nachgerechnet, was unterhalb der versionierten Tabellen liegt, und nichts angehört.

## 3. Überblick

| Punkt | Umgesetzt | Richtig | Offen |
|---|---|---|---|
| Befund 1: MERT einzeln kodieren | ja, mit Neutraining | ja | Intervall für den Vorsprung, Normierung prüfen |
| Befund 2: Tempo-Angleichung | ja, ein Weg für alle Pfade | ja | Hörprobe, Einordnung der Prüfung |
| Befund 3: Hörtest | ja, als Web-Anwendung | fast | Rotation des harten Schnitts, Probelauf |
| Auswertung vor dem Entblinden | ja | ja, laut Test an Kunstdaten **[A]** | – |
| Mashup-Export | ja | teilweise | vier Punkte in Abschnitt 7 |
| GUI-Zustand nach dem Umsortieren | ja | ja | – |

## 4. Befund 1: MERT

### Umsetzung

- Das Audio wird vor MERT geschnitten. Jedes Fenster geht mit genau seinen vier Takten in den Encoder (`src/features/p07_mert.py:136-175`, Schnitt in `:160`) **[C]**.
- Training und Anwendung nutzen dieselbe Funktion (`src/ml/mert_isolated_train.py:23-69`, `src/ranking/continuation.py:86`, `:115`) **[C]**.
- Ein Vertrag verhindert, dass ein Kopf mit der falschen Kodierung geladen wird (`src/ranking/continuation.py:162`) **[C]**.
- Ein Test zeigt, dass Audio außerhalb des Fensters das Ergebnis nicht ändert (`tests/test_isolated_mert.py:30-31`) **[C]**.

### Ergebnisse **[B]**

Recall@1 auf denselben 2.830 Abfragen (`docs/masterarbeit/REVIEW_JP_MERT_FENSTER_20261123.md`):

| Bedingung | gemeinsam kodiert | einzeln kodiert |
|---|---|---|
| MERT, bisheriger Studienkopf | 85,59 % | 66,12 % |
| MERT, Kosinus ohne Kopf | 44,53 % | 63,51 % |
| klassische Merkmale, gleicher Seed | 68,66 % | 68,66 % |

Nach dem Neutraining auf einzeln kodierten Fenstern, Mittel über drei Seeds:

| Bedingung | Recall@1 |
|---|---|
| MERT, zwei Türme | 72,24 % |
| klassische Merkmale, zwei Türme | 68,49 % |

- Der Vorsprung beträgt 3,75 Punkte statt vorher 17,18.
- Die Schichtung mit unserem Skript ergab 78,7 % ohne und 86,4 % mit gemeinsamem Kontext.
- Die Zusatzkontrolle mit gleichem Abschnittstyp besteht der neue Kopf in 76,94 % der Fälle.
- Regel und neuer Kopf wählen in 0 von 26 Entwicklungspaaren dieselbe Stelle.

### Bewertung

Der Verdacht aus Befund 1 hat sich bestätigt: Der alte Vorsprung war überwiegend ein Artefakt der gemeinsamen Kodierung. Das Kriterium „fertig, wenn" vom 22.11. ist erfüllt. Der Einbruch von 85,6 % auf 66,1 % ist selbst ein berichtenswertes Ergebnis und gehört in die Thesis.

### Nachträge

1. **Unsicherheit des Vorsprungs.** Die 3,75 Punkte sind jetzt die Kernaussage zu F2. Die drei Seeds streuen um rund 0,4 Punkte; das ist die Streuung des Trainings, nicht die der Daten. Es fehlt ein gepaartes Bootstrap über die Quellgruppen der Validation: Differenz MERT minus klassisch je Gruppe, 10.000 Ziehungen, für den Studienseed und das Seedmittel. Die Einzelränge liegen dir vor.
   - **Fertig, wenn** der MERT-Bericht die Differenz mit 95-%-Intervall nennt.
2. **Normierung prüfen.** Der Vorverarbeiter (`src/features/p07_mert.py:95`, `:161`) normiert vermutlich jeden Ausschnitt einzeln auf Mittelwert 0 und Varianz 1. Die Datei `preprocessor_config.json` konnte ich hier nicht einsehen. Ist `do_normalize` gesetzt, sieht MERT bei einzeln kodierten Fenstern den Pegel eines Fensters nicht mehr; die klassischen Merkmale enthalten die Lautheit. Das ist kein Fehler, weil Training und Anwendung gleich arbeiten, aber eine Grenze, die in die Thesis gehört.
   - Optional: die Lautheit des Fensters als Zusatzgröße an den Kopf geben und als eigene Zeile berichten.
3. **Auswahl und Messung auf derselben Validation.** Das steht in deinem Bericht und gehört weiter in jede Tabelle.

## 5. Befund 2: Tempo-Angleichung

### Umsetzung

- Regression der Schlagzeiten über bis zu 64 Schläge um die Stelle (`src/tempo/cue_alignment.py:49-66`, `:12`) **[C]**.
- Ein Streckfaktor für B, in der Pipeline selbst (`src/pipeline.py:226-244`), genutzt auch von der Brückenextraktion (`src/bridge.py:88`) **[C]**. Pipeline, GUI, Batch, Trainingsexport und Hörtest nehmen damit denselben Weg.
- Die Prüfung vergleicht beobachtete Schläge beider Tracks und kann jetzt scheitern (`src/tempo/cue_alignment.py:78-87`, Grenze 20 ms in `:13` und `:35-42`) **[C]**.
- Die Streckung pro Schlag läuft nur noch für die alte Fassung (`src/evaluation/comparison_study.py:256`). Der harte Schnitt bekommt denselben gestreckten Kontext wie die anderen Clips (`:145`) **[C]**.

Von den Kriterien „fertig, wenn" vom 22.11. sind die Fehlertabelle und der gemeinsame Code erfüllt. Die protokollierte Hörprobe fehlt.

### Nebenwirkung **[B]**

Die 20-ms-Prüfung verwirft fast alle Stellen:

| Bestand | zugelassen |
|---|---|
| Stellen je Songpaar im Hörtest | 13 bis 1.128 (P06: 13, P02: 46) |
| die 21 früher gewählten Stellen | 1 |
| Trainingsbeispiele im größten Datensatz | 217 von 2.649 |

Die Prüfung habe ich so empfohlen. Sie misst, wie weit einzelne erkannte Schläge von der Regressionsgeraden abweichen. Bei Musik mit festem Tempo ist das die Streuung der Beat-Erkennung und nicht der Versatz im Audio. Deine Fehlertabelle zeigt es: Die Regression senkt die Zahl der Fälle über 20 ms kaum, in einem Bestand steigt sie sogar von 240 auf 254. Beide Spalten sind an denselben verrauschten Marken gemessen.

### Folgen

- **Hörtest:** Alle drei Verfahren wählen aus einer stark vorgefilterten Menge, bei P06 aus 13 Stellen. Vermutlich sind das Stellen mit klarem Kick auf beiden Seiten. Das kann den Abstand zwischen gelernter Metrik, Regel und Zufall verkleinern.
- **Controller:** Die Trainingsfenster der bisherigen Controller bestehen die neue Prüfung überwiegend nicht. Die Controller-Ergebnisse bleiben Diagnose.

### Was zu tun ist

1. **Vor der ersten Einladung:** die Hörprobe an den sechs vorbereiteten Clips durchführen und protokollieren. Klingt die neue Angleichung nicht mindestens so gut wie die alte, ist Run03 nicht zu verwenden.
2. **Vor dem Hörtest nichts an der Prüfung ändern.** Die Stellen sind gewählt.
3. **Für die Thesis:** die Zahl der zugelassenen Stellen je Paar in die Ergebnistabelle aufnehmen und die Prüfung als konservativ beschreiben.
4. **Vorschlag für einen echten Nachweis:** den Versatz im Audio messen statt an den Marken. Zum Beispiel die Kreuzkorrelation der Onset-Hüllkurven im Tiefband zwischen A und gestrecktem B über die Brücke, für die 21 Stellen von Run03 und eine Stichprobe abgelehnter Stellen. Das zeigt, ob die zugelassenen Stellen wirklich unter 20 ms liegen und wie viele abgelehnte in Wahrheit gut wären.
5. **Später, optional:** Stellen am Regressionsraster ausrichten statt an Einzelmarken. Dazu passt Abschnitt 11 der Rückmeldung vom 22.11.

## 6. Befund 3: Hörtest

### Umgesetzt aus dem Designabschnitt **[C]**

| Anforderung | Fundstelle |
|---|---|
| Reihenfolge der Paare als lateinisches Quadrat in Siebenerblöcken | `hoertest/session.py:54-61` |
| Clip-Positionen je Sitzung und Paar gemischt | `hoertest/session.py:84-85` |
| Schlüssel nur auf dem Server, Audio über neutrale Codes | `hoertest/app.py:202-204` |
| Regler ohne sichtbaren Startwert | `hoertest/player.html:13`, `:101-105` |
| beschriftete Skala in fünf Bereichen | `hoertest/player.html:68` |
| vollständiges Anhören wird auf dem Server geprüft | `hoertest/session.py:172-179` |
| jede Wertänderung mit altem und neuem Wert | `hoertest/session.py:180-185`, `:216` |
| ein Seitenaufruf verbraucht keinen Platz, erst der bestätigte Start | `hoertest/app.py:167-184` |

Dazu kommen die Übungsseite, die Angaben zur Person und das Sperren nach der Abgabe. Im Repository liegt kein Schlüssel: `hoertest/.gitignore` lässt nur die Anwendung zu, und `run03_49_verified.json` enthält keine Zuordnung **[C]**. Protokoll Version 2 und die Auswertung (`src/evaluation/p12_descriptive.py`, Test in `tests/test_p11_local_study.py:148`) sind vor der ersten Bewertung committet.

### Abweichung: der harte Schnitt rotiert nicht

- Die Rotation ist programmiert, für das Erhebungsmaterial aber abgeschaltet (`hoertest/session.py:81-82`) **[C]**. Alle hören den harten Schnitt nur an der Regel-Stelle.
- Dein Protokoll Version 2 sagt in Zeile 3, die Betreuung habe die Rotation verlangt. `hoertest/PROTOKOLL_FESTE_ANKER.md` hält die Abschaltung als Autorenentscheidung vom 23.11. fest. Die beiden Dokumente widersprechen sich.
- Die Ungleichbehandlung aus Befund 3 bleibt damit bestehen: Die Regel-Stelle ist dreimal zu hören, die anderen zweimal. Das trifft den Hauptvergleich gelernte Metrik gegen Regel.
- Die 63 Clips für die Rotation sind gerendert. Es genügt, das Paket ohne `--fixed-rule-anchors` neu vorzubereiten.

**Entscheidung der Betreuung vom 23.11.2026:** Der harte Schnitt rotiert, wie in Protokoll Version 2 festgelegt. Dass alle dieselben 49 Clips hören, wiegt weniger als ein unverzerrter Hauptvergleich. Das Erhebungspaket wird ohne `--fixed-rule-anchors` neu vorbereitet (`src/evaluation/p11_web.py:101`). `hoertest/PROTOKOLL_FESTE_ANKER.md` gilt für die Erhebung nicht; bitte dort und im Umsetzungsdokument vermerken. Wie bisher werden die tatsächlich besetzten Anker je Paar berichtet, weil Abbrüche und eine Personenzahl, die kein Vielfaches von 3 ist, die Verteilung verschieben.

### Geändert: Erhebung über die Institutswebseite

Statt eines betreuten Hörplatzes läuft der Test über einen gemeinsamen Link, auch von zu Hause (`hoertest/PROTOKOLL.md`). Protokoll Version 2 nennt noch denselben Hörplatz und denselben Kopfhörer. Folgen:

- Kopfhörer, Lautstärke und Umgebung sind nicht kontrolliert.
- Eine Person kann mehrere Sitzungen starten; die Zahl der Personen lässt sich nicht bestimmen.
- Der Ausschluss von Autor und Betreuung ist nur eine Zusage.

Das ist vertretbar und bringt mehr Teilnehmende. Es gehört als Grenze in die Thesis, und die Ergebnisse sollten nach Hörort getrennt ausgewiesen werden. Die Einladung sollte ausdrücklich sagen: einmal, allein, mit Kopfhörer.

### Offen

- Probelauf mit einer außenstehenden Person über den echten Zugang, mit gemessener Dauer und Ladezeit.
- Die Zufalls-Stelle ist weiter eine einzige Ziehung je Paar. Das war optional.

## 7. Mashup-Export und GUI

### Mashup-Export

Der Export verbindet beliebig viele Songs mit Übergängen von 1 bis 4 Takten zu einer WAV (`src/mashup.py`). Die Sample-Buchhaltung stimmt nach Durchsicht: Kein Abschnitt wird doppelt geschrieben oder ausgelassen (`src/mashup.py:100-127`) **[C*]**. Damit ist die Funktion aus der Aufgabenstellung technisch vorhanden. Vier Punkte sind offen:

| Punkt | Fundstelle | Was tun |
|---|---|---|
| Am Audio getestet ist nur der Fall ohne Streckung. Der Test mit verschiedenen Tempi nutzt eine Attrappe und prüft keinen Audioinhalt. Deine Doku sagt hier mehr. **[A]** | `tests/test_mashup.py:53-75`, `docs/masterarbeit/review_jp_20261118/p14/mashup.md:35` | einen Test mit echter Streckung ergänzen, Doku angleichen |
| Ein reines BPM-Ersatzraster wird nicht abgewiesen. Der Paar-Renderer ruft `require_observed_grid` auf, der Export nicht. **[C]** | `src/mashup.py:105-106`, `src/pipeline.py:234-235` | Aufruf ergänzen |
| Jeder Folgesong wird auf den Vorgänger gestreckt. Das ganze Mashup läuft im Tempo des ersten Songs, ohne Obergrenze für den Faktor. **[C*]** | `src/mashup.py:107-108` | Grenze wie bei den Kandidaten (15 %) setzen oder die Regel benennen |
| Es gibt nur einen Pegelfaktor für die ganze Datei und keinen Lautheitsabgleich zwischen den Songs. **[C*]** | `src/mashup.py:147-153` | je Song angleichen oder als Grenze benennen |

Gelernte Controller sind vom Export ausgeschlossen **[A]**. Die Beispieldatei hat laut deiner Doku noch niemand angehört.

### GUI

Der Fehler beim Umsortieren ist behoben: Cues, Bereiche, Einstellungen und Vorschau hängen jetzt am Songpaar statt an der Position (`src/gui/transition_builder.py:970-980`) **[C*]**. Der Test dazu läuft hier durch **[M]**.

## 8. Kleinere Punkte

| Punkt vom 22.11. | Stand | Fundstelle |
|---|---|---|
| Fehlende Abhängigkeiten | behoben; einige direkt importierte Pakete sind weiter nur über andere Pakete vorhanden **[A]** | `requirements.txt:9-11`, `requirements-dev.txt:2` |
| Sweeps im alten Startmodus | behoben **[C*]** | `src/ml/__main__.py:866`, `:920` |
| Verlust bewertet die Sinus-Gain-Kurve als Mix-Position | unverändert, jetzt als Grenze dokumentiert; das entspricht der Einordnung „benennen"; Größe in Abschnitt 13.3 **[C]** | `src/control/differentiable.py:435` |
| Ersatzraster wird nie gespeichert | teilweise: gespeichert, aber jeder Aufruf lädt das Audio neu und versucht aufTAKT erneut **[A]** | `src/analysis/pre_analysis.py:253-281` |
| `tempo_fade` gleich `fade` | als Alias im Hilfetext benannt **[C*]** | `src/pipeline.py:521` |
| Windows-Pfade in Manifesten | teilweise: neue Pfade relativ, alte werden umgebogen; in anderen Manifesten weiter absolut **[A]** | `src/artifact_paths.py:10-42` |

Dazu ein Punkt in der Doku: `docs/GESAMTAUDIT_20261123.md` steht auf dem alten Commit `4651e51` und führt den GUI-Fehler, PySide6 und den Mashup-Export als offen, obwohl alle drei im selben Commit bearbeitet sind **[C*]**. Bitte angleichen oder als Stand vor der Umsetzung kennzeichnen.

## 9. Reihenfolge

### Vor der ersten Einladung

| Nr. | Schritt | Fertig, wenn |
|---|---|---|
| 1 | Rotation des harten Schnitts einschalten: Paket ohne `--fixed-rule-anchors` neu vorbereiten | neues Paket technisch geprüft, feste Anker in der Doku als nicht verwendet gekennzeichnet |
| 2 | Tempo-Hörprobe | Protokoll mit Urteil je Clip in `docs/Bemerkungen.md` |
| 3 | Probelauf mit einer außenstehenden Person über den echten Zugang | Dauer, Ladezeit und Verständnisprobleme notiert |

### Schritt 1 im Einzelnen: Rotation des harten Schnitts

- **Was.** Pro Songpaar gibt es drei harte Schnitte, je einen an der Stelle der gelernten Metrik, der Regel und des Zufalls. Jede Person hört pro Paar genau einen davon. Welche Stelle es ist, wechselt reihum über die Personen. Bisher hören alle den harten Schnitt nur an der Regel-Stelle.
- **Warum.** Mit festem Anker ist die Regel-Stelle dreimal zu hören und die anderen zweimal, eine Fassung davon ist absichtlich roh. Das kann die Bewertung der Regel-Stelle verschieben und trifft den Hauptvergleich gelernte Metrik gegen Regel. Mit Rotation trifft derselbe Effekt alle drei Stellen gleich.
- **Wie.** Das Paket in einem neuen Zielordner vorbereiten, mit dem Befehl aus `hoertest/README.md:20`, aber ohne den Schalter `--fixed-rule-anchors`. Neu gerendert wird nichts; die 63 Masterdateien liegen vor und müssen alle auf dem Server liegen. Für die Sitzungen gilt dann `hoertest/PROTOKOLL.md` statt `hoertest/PROTOKOLL_FESTE_ANKER.md` (`hoertest/session.py:21-24`).
- **Danach.** Denselben technischen Nachweis wie `run03_49_verified.json` für das neue Paket erzeugen: mindestens sechs Probesitzungen nachspielen, prüfen, dass jeder harte Schnitt je Paar einmal pro Dreierblock vorkommt, und die Prüfsumme des Wiedergabesatzes festhalten.
- **Doku.** Statusdokument, Umsetzungsdokument und die README des Hörtests nennen das neue Paket. Das Protokoll der festen Anker wird als nicht verwendet gekennzeichnet.

### Schritt 2 im Einzelnen: Tempo-Hörprobe

- **Was.** Sechs Entwicklungsclips liegen bereit: zwei Songpaare, je derselbe Übergang in drei Fassungen. Das sind die alte Angleichung über die globale BPM, die neue Angleichung mit einem Faktor aus der Regression und die Streckung pro Schlag aus dem früheren Studienrender (`docs/masterarbeit/REVIEW_JP_TEMPO_20261123.md`).
- **Warum.** Alle Clips des Hörtests nutzen die neue Angleichung. Dass sie besser klingt als die alte, zeigt bisher keine Messung, weil die Fehlertabelle an verrauschten Marken misst (Abschnitt 5). Die Hörprobe ist der einzige Beleg. Ein Problem würde den ganzen Stimulussatz treffen und ließe sich nach dem Start nicht mehr beheben.
- **Wie.** Die drei Fassungen je Paar über Kopfhörer und mehrfach hören, ohne die Zuordnung zu kennen. Dazu die Dateien von jemand anderem umbenennen lassen oder per Skript mischen. Je Clip notieren:
  - doppelte Kick-Anschläge und an welcher Stelle,
  - hörbare Nahtstellen oder Artefakte der Streckung,
  - die Rangfolge der drei Fassungen.

  Erst danach die Zuordnung auflösen. Besser hören zwei Personen; die Betreuung kann mithören, weil es Entwicklungsmaterial ist.
- **Entscheidungsregel, vorab.** Die neue Angleichung muss in beiden Paaren mindestens so gut sein wie die alte. Ist sie es nicht, wird Run03 nicht verwendet, und die Ursache wird vor einem Neurender geklärt.

### Schritt 3 im Einzelnen: Probelauf

- **Was.** Eine Person, die Projekt und Design nicht kennt, durchläuft den Test einmal vollständig über den echten Zugang (Institutsserver, HTTPS, Gruppenschutz) an ihrem eigenen Gerät. Sie hört Entwicklungsmaterial, ihre Bewertungen zählen nicht.
- **Warum.** Der Probelauf prüft, was kein automatischer Test prüft: ob die Aufgabe verstanden wird, wie lange es wirklich dauert und wie lange das Laden braucht. Ein Durchgang lädt nach deinem Methodenreview rund 246 MB unkomprimiertes Audio **[B]**.
- **Wie.** Das Paket `pilot01` reicht für die Bedienung. Für die Dauer ist ein Pilot mit mehreren Entwicklungspaaren besser, sonst wird von einem Paar auf sieben hochgerechnet. Zu notieren sind:
  - Zeit je Paarseite und Ladezeit je Clip,
  - was an Anleitung, Regler oder Wiedergabe unklar war,
  - ob Unterbrechen und Fortsetzen im selben Browser klappt,
  - ob die Abgabe als abgeschlossen erkannt wird.

  Zusätzlich von außerhalb der eingeladenen Gruppe prüfen, dass weder die Startseite noch eine Audio-Adresse ohne Anmeldung erreichbar ist.
- **Danach.** Nötige Änderungen an Anleitung und Einladung einarbeiten. Die Pilotperson nimmt an der Erhebung nicht teil.

### Was außerdem vor der ersten Einladung feststehen muss

Die drei Schritte reichen nicht ganz. Diese Punkte kosten wenig, lassen sich nach dem Start aber nicht nachholen:

| | Punkt | Fertig, wenn |
|---|---|---|
| A | **Entscheidung der Betreuung zum Hören von zu Hause** (Abschnitt 10). Protokoll Version 2 nennt noch den betreuten Hörplatz mit demselben Kopfhörer. | Entscheidung in Abschnitt 10 eingetragen; ein datierter Satz in Version 2 sagt, welche Erhebungsart gilt |
| B | **Technische Hörkontrolle der Studienclips.** Pegel, Länge und Zeitfehler sind automatisch geprüft, angehört hat die Clips niemand. Die Versuchsleitung hört alle 63 Masterdateien einmal durch, nur auf Fehler: Knackser, Aussetzer, falscher Einsatz, abgeschnittenes Ende. Sie bewertet ohnehin nicht mit. | Notiz mit Datum; ein fehlerhaftes Paar wird nach Protokoll zurückgestellt |
| C | **Ende der Erhebung vorab festlegen:** ein Datum oder eine Zahl abgeschlossener Sitzungen (Ziel 6 bis 9, möglichst ein Vielfaches von 3). Bis dahin keine Zwischenauswertung. Das verhindert, dass nach einem Blick auf die Zahlen weiter gesammelt oder aufgehört wird. | Satz im Protokoll |
| D | **Einladungstext:** einmal teilnehmen, allein, mit Kopfhörer, in ruhiger Umgebung, Lautstärke nach der Übung nicht mehr ändern, nicht mit anderen über die Clips sprechen, 30 bis 40 Minuten. Kein Hinweis auf die Verfahren. Autor und Betreuung nehmen nicht teil. | Text liegt im Repository |
| E | **Betrieb:** Datenordner außerhalb des Webverzeichnisses, getrennte Ordner für Probe und Erhebung, Sicherung der Antwortdatenbank, Aufbewahrung der Daten mit dem Institut geklärt. So steht es in deiner README; es muss beim Aufsetzen bestätigt werden. | kurze Notiz nach dem Aufsetzen |
| F | **Stand einfrieren.** Paket, Nachweis, Protokolle und Einladung sind committet, bevor die erste Einladung hinausgeht. Danach ändert sich an Anwendung, Paket und Auswertung nichts mehr. | Commit vor der ersten Sitzung |

Nicht vor dem Hörtest nötig sind die Schritte 4 bis 12 unten. Sie ändern nichts an den Clips.

### Für die Thesis, unabhängig vom Hörtest

| Nr. | Schritt | Fertig, wenn |
|---|---|---|
| 4 | Intervall für den MERT-Vorsprung | Differenz mit 95-%-Intervall im MERT-Bericht |
| 5 | Normierung des MERT-Vorverarbeiters prüfen | ein Satz im Bericht, ob der Pegel erhalten bleibt |
| 6 | Zugelassene Stellen je Paar berichten, Prüfung einordnen | Spalte in der Ergebnistabelle |
| 7 | Vier Punkte am Mashup-Export, Beispieldatei anhören | Abschnitt 7 abgearbeitet, Hörnotiz vorhanden |
| 8 | Gesamtaudit an den Stand angleichen | kein Widerspruch zum Umsetzungsdokument |
| 9 | Überschreibschutz im Einzelrenderer (Abschnitt 13.1), vor weiteren Renderläufen | Zielpfad gleich Eingabe wird abgelehnt, mit Test |
| 10 | Zeilenenden der P09- und P10-Belege festlegen (Abschnitt 13.1) | frischer Checkout unter Linux oder macOS bestätigt die Prüfsummen |
| 11 | Alten Cue-Ranker stilllegen, Auftrag im Thesis-Entwurf streichen (Abschnitt 13.4) | Pfad gekennzeichnet, keine Zahl daraus im Ergebniskapitel |
| 12 | Punkte aus 13.2 und 13.3 in Protokollen und Thesis benennen | je ein Satz an der passenden Stelle |

Der Versatz im Audio (Abschnitt 5, Punkt 4) ist ein Vorschlag und keine Pflicht.

## 10. Entscheidungen der Betreuung

Offen:

- Die Erhebung über die Institutswebseite mit Hören von zu Hause bestätigen.
- Die Frage zur Aufgabenstellung aus der Rückmeldung vom 22.11., Abschnitt 9.

Die Antworten werden hier nachgetragen.

Entschieden:

- 23.11.2026: Der harte Schnitt rotiert über die drei Stellen, wie in Protokoll Version 2. Die festen Anker sind nicht genehmigt.

## 11. Was nicht geprüft werden konnte

- Alles unter `output/`: Stimuli, Checkpoints, Caches, Einzelränge, das Serverpaket.
- Der Klang: neue Tempo-Angleichung, Run03, Mashup-Beispiel.
- `preprocessor_config.json` des MERT-Modells.
- Der Betrieb auf dem Institutsserver.
- Der Inhalt der Tests zu Tempo und Auswertung; gelesen habe ich dort nur die Testnamen und einzelne Zeilen.
- Die Thesis unter `overleaf/`.

## 12. Was aus der Rückmeldung vom 22.11. weiter gilt

- Abschnitt 8, „Was umgesetzt werden muss und was zu benennen reicht".
- Abschnitt 11, das Vorgehen mit zwei Beat-Trackern.
- Abschnitt 12, das Design des Hörversuchs. Bis auf die Rotation des harten Schnitts und die optionale Zufalls-Stelle ist es umgesetzt.

## 13. Ergänzung aus einem zweiten Audit

Die Betreuung hat für denselben Commit ein zweites, rein statisches Audit eines anderen KI-Modells (Kimi) eingeholt. Es hat nichts ausgeführt. Ich habe die Punkte, die für den Abschluss zählen, am Code nachgelesen und zwei davon nachgerechnet ([Testläufe](./TESTLAEUFE.md), Nr. 16 und 17). Das Audit bestätigt außerdem zwei unserer Ergebnisse: An Zuteilung, Versiegelung, Ausschlüssen und Kontrasten des Hörtests fand es keinen Fehler, und die Zahlen des neuen MERT-Kopfs sind in sich stimmig **[K]**.

### 13.1 Neu als Pflicht

| Punkt | Fundstelle | Was tun |
|---|---|---|
| Der Einzelrenderer schreibt den frei wählbaren Zielpfad ohne Prüfung. Ist das Ziel eine der beiden Eingabedateien, ersetzt die gekürzte Vorschau das Original. Dein eigenes Gesamtaudit führt das als höchste Priorität. **[K*]** | `src/pipeline.py:573-575` | Zielpfad gegen beide Eingaben prüfen und abbrechen |
| Die Prüfsummen der P09- und P10-Belege passen nur mit Windows-Zeilenenden. Im Repository liegen die drei Dateien mit LF; mit CRLF ergeben sich genau die erwarteten Werte (`841dd01c…`, `c6b71de9…`, `db091547…`). Der Inhalt ist unverändert. Auf jedem Rechner ohne CRLF schlägt die Prüfung fehl. **[M]** | `docs/masterarbeit/P09_VERIFIED_20261119.json`, `docs/masterarbeit/review_jp_20261118/p10/selection.json`, `docs/masterarbeit/review_jp_20261118/p10/offline.csv`; Prüfung in `src/evaluation/mert_window_check.py:60` | die drei Dateien in `.gitattributes` aufnehmen, wie du es für `mert_fenster/` schon getan hast |

Das zweite Audit hielt bei den Prüfsummen eine reine Zeilenenden-Erklärung für unzureichend. Die Nachrechnung zeigt, dass sie alle drei Abweichungen vollständig erklärt.

- **Fertig, wenn** ein frischer Checkout unter Linux oder macOS die drei Prüfsummen bestätigt und der Einzelrenderer einen Zielpfad ablehnt, der eine Eingabe ist.

### 13.2 Neu als „benennen"

| Punkt | Fundstelle | Einordnung |
|---|---|---|
| Features und Audio nutzen verschiedene Tempo-Geometrien. Die Features von B werden mit dem Verhältnis der globalen BPM gestreckt, das Audio mit dem lokalen Verhältnis der Schlagdauern. Bei 3 % Unterschied sind das über 16 Schläge rund 180 ms. Dein Kommentar im Studienrenderer nennt das selbst. **[K*]** | `src/features/dataset_export.py:283-284`, `src/pipeline.py:226-244`, `src/evaluation/comparison_study.py:95-100` | benennen. Pflicht nur, falls noch ein Controller neu trainiert wird. |
| Die Render-Metrik bekommt nach der lokalen Angleichung weiter die globale BPM und skaliert damit ihre Fenster. **[K*]** | `src/batch_render.py:367` | benennen, weil die Nebenauswertung des Hörtests den Render-Score nutzt; oder die lokale Schlagdauer übergeben |
| Beim variablen TCN ist nur die berichtete Kennzahl über die Längen gleich gewichtet. Der Optimizer macht einen Schritt je Batch, also mehr Schritte für häufigere Längen. Das Protokoll verspricht gleiche Gewichte je Länge. **[K*]** | `src/ml/variable_runner.py:811-836` | in Protokoll und Thesis genau beschreiben |
| Das Fortsetzen eines variablen Trainings ist nicht gleichwertig zu einem durchgehenden Lauf, und die Batch-Reihenfolge ist in jeder Epoche dieselbe. **[K]** | `src/ml/variable_runner.py:225-258`, `:427-440` | benennen, falls ein berichteter Lauf fortgesetzt wurde |
| Die ältere Zusammenführung der Beat-Raster kann einen aufTAKT-Schlag mehreren librosa-Schlägen zuordnen und gilt trotzdem als geprüft. Die Studie nutzt die neuere Fassung. **[K*]** | `src/analysis/pre_analysis.py:524-547` | benennen für die älteren Caches; passt zu Abschnitt 11 der Rückmeldung vom 22.11. |

### 13.3 Glättungsterm im Full-Band-Pfad: jetzt mit Größe

Der Punkt steht schon in Abschnitt 8. Das zweite Audit stuft ihn hoch ein, weil exaktes Equal Power dort einen Strafterm bekommt, obwohl dein Protokoll null verspricht (`docs/DIFFERENTIABLE_CONTROL_PROTOCOL.md:136-139`). Nachgerechnet **[M]** sind es für den Mix-Anteil bei 32 Stützstellen 0,233 im Glättungsterm und 0,003 im Krümmungsterm, mit den Gewichten 0,02 und 0,05 zusammen rund 0,005. Das sind 1 bis 2 % der berichteten Equal-Power-Werte (0,27 bis 0,41).

Der Fehler ist also echt, aber klein. Es bleibt bei „benennen". Zu korrigieren ist der Satz im Protokoll, und in der Thesis gehört ein Satz dazu, dass die Equal-Power-Referenz im Full-Band-Pfad diesen Anteil enthält.

### 13.4 Alter Cue-Ranker mit Lehrer: stilllegen statt reparieren

Vier Punkte des zweiten Audits betreffen den Cue-Ranker mit Proxy-Lehrer:

- Der Lehrer nutzt standardmäßig RoFormer-Vocal-Features, die Anwendung keine (`src/ml/cue_ranker_teacher_resolver.py:76`, `src/ranking/learned_cue_ranker.py:240`) **[K*]**.
- Der Wächter setzt die beiden unbearbeiteten Brücken-Eingänge als Außenkontext ein (`src/ml/cue_ranker_teacher.py:264-287`) **[K*]**. Das ist Nr. 10 aus dem Code-Review vom 13.11.
- Der Befehl zum Labeln bricht mit einem `NameError` ab: `_normalise_split_map` wird benutzt, aber nicht importiert (`src/ml/cue_ranker_teacher.py:515`, definiert in `src/features/cue_ranker_universe.py:652`) **[K*]**.
- Bei anderen Abtastraten als 44,1 kHz werden Cue-Positionen falsch umgerechnet **[K]**.

Dein Umsetzungsdokument führt den Lehrer als eingestellt (`docs/REVIEW_JP_UMSETZUNG.md:89`). Reparieren lohnt deshalb nicht. Zu tun ist:

1. Den Pfad im Code und in der CLI als nicht gepflegt kennzeichnen oder entfernen.
2. Im Thesis-Entwurf den offenen Auftrag streichen, das Labeln mit echten Daten abzuschließen (`overleaf/chapters/05_results.tex:88-90`), und den Lehrer als eingestellten Ansatz beschreiben.
3. Keine Zahl aus diesem Pfad als Ergebnis berichten.

### 13.5 Stand der Thesis

Im vorliegenden Arbeitsstand sind beide Abstracts und das Fazit noch Platzhalter (`overleaf/chapters/00_abstract.tex:7`, `overleaf/chapters/07_conclusion.tex:5`), und das Ergebniskapitel enthält keine MERT-Ergebnisse **[K*]**. Das deckt sich mit dem offenen Paket P15 und bestätigt, dass für die Thesis die volle eingeplante Woche gebraucht wird.

### 13.6 Nicht übernommen oder anders bewertet

- **Feste Anker:** Das zweite Audit sieht darin keinen Fehler, nur einen Widerspruch der Dokumente. Die Betreuung hat die Rotation entschieden (Abschnitt 10).
- **Reihenfolge:** Das zweite Audit will die Lehrer-Punkte vor weiteren Läufen behoben sehen. Weil der Lehrer eingestellt ist, entfällt das.
- **Uhr bei der Wiedergabeprüfung:** `time.time()` statt einer monotonen Uhr (`hoertest/session.py:171-175`) **[K*]**. Das Risiko ist vernachlässigbar und kann bleiben.
- **Von mir nicht nachgeprüft, für den Abschluss nachrangig [K]:** Bei 8 Takten und 150 BPM liegt das gemeldete Übergangsende hinter dem Ende der Vorschau, sodass kein Render-Score entsteht. Die Metriken mitteln Stereo auf Mono. Der Feature-Cache bindet weder das Streck-Werkzeug noch dessen Version. Der neue Ranker ist im Live-Pfad nur an einem Entwicklungspaar nachgerechnet.
