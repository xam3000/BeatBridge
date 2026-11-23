# BeatBridge – Gesamtaudit von Code und Dokumentation

**Stand:** 23. November 2026 · **Hauptrepository:** `4651e51` · **Overleaf:** `75a8664`

Die höchste technische Priorität haben der Schutz der Originalaufnahmen beim Einzelrender, die korrekte Cue-Position bei anderen Sampleraten als 44,1 kHz und der funktionsfähige Einstieg ins Teacher-Labeling. Für den Projektabschluss stehen die menschlichen Hörurteile, der Nachweis eines vollständigen Mashup-Exports und die Überarbeitung der Thesis aus.

## Prüfumfang und Aussagekraft

Die statische Prüfung erfasste 220 versionierte Python-Dateien mit rund 55.300 Zeilen, darunter 66 Testdateien, sowie 84 Markdown-Dateien. Einbezogen waren die LaTeX-Quellen des eingebundenen Overleaf-Stands, das Aufgaben-PDF, das Hör-Notebook, die Web- und Präsentationsquellen sowie ausgewählte Studienmanifeste, Ergebnistabellen und Git-Nachweise. Alle Python-Dateien ließen sich parsen. Alle 26 unterschiedlichen Literaturschlüssel aus den Thesis-Kapiteln waren im Literaturverzeichnis vorhanden.

Die fachliche Detailprüfung folgte den Bedienwegen für Rendering, Ranking, Training und GUI sowie den Belegen für Studie und Abschluss. Es gab keine neuen Projekt-Testläufe, Trainings, Audio-Renderings, Hörsitzungen oder GUI-Durchläufe. Wo ein Befund eine Laufzeitfolge beschreibt, ist diese aus dem konkreten Codepfad abgeleitet. Bereits protokollierte Versuchsergebnisse sind als solche benannt.

**Priorität:** Hoch bedeutet möglicher Datenverlust, ein blockierter Bedienweg, ein falsches fachliches Ergebnis oder eine ausstehende Voraussetzung für die Abnahme. Mittel betrifft die Reproduzierbarkeit, einzelne Nutzungssituationen oder widersprüchliche Arbeitsanweisungen. Niedrig betrifft die historische Nachvollziehbarkeit oder die Portabilität von Begleitmaterial. Bei offenen Fragen bezeichnet die Priorität die Bedeutung der Klärung.

## Befunde im Code

### C1 · Hoch · Der Einzelrenderer kann eine Originalaufnahme überschreiben

Die CLI übergibt den mit `--output` gewählten Pfad nach dem Render direkt an `sf.write`. Sie prüft nicht, ob der Pfad dieselbe Datei wie eine der beiden Eingaben bezeichnet. Wählt man eine Eingabe-WAV als Ziel, kann die standardmäßig kurze Vorschau die vollständige Originalaufnahme ersetzen. [CLI und Schreibstelle](../src/pipeline.py#L536)

### C2 · Hoch · Candidate-v2 skaliert Cue-Positionen bei abweichender Samplerate doppelt

Bei einem Batch mit 48 kHz rechnet die Kandidatenerzeugung die Beatpositionen bereits auf das gewünschte 48-kHz-Raster um. Der variable Fade und der gelernte Cue-Ranker behandeln diese Positionen anschließend wie 44,1-kHz-Koordinaten und multiplizieren nochmals mit `48000 / 44100`. So wird aus einem Cue bei 60 Sekunden vor dem Einrasten auf den Downbeat eine Position bei rund 65,31 Sekunden. Der Hard Cut verwendet beim selben Kandidaten die ursprüngliche Position. Dadurch können Ranking und Renderervarianten verschiedene musikalische Stellen vergleichen. Bei 44,1 kHz ist der Faktor eins. [Kandidatenerzeugung](../src/pipeline.py#L437) · [Hard Cut](../src/variable_rendering.py#L58) · [Variabler Fade](../src/variable_rendering.py#L108) · [Gelernter Cue-Ranker](../src/ranking/learned_cue_ranker.py#L326)

### C3 · Hoch · Der reguläre CLI-Aufruf zum Teacher-Labeling endet vor der ersten Bewertung

`label-cue-ranker-teacher` verlangt `--split-map`. Bei übergebener Split-Zuordnung ruft der Teacher `_normalise_split_map` auf. Die Funktion ist im Modul für das Kandidatenuniversum definiert, im Teacher aber weder definiert noch importiert. Bei ansonsten gültigen Eingaben ergibt sich auf diesem Pfad ein `NameError`. Die Funktionstests können den Fehler übersehen, weil sie die Python-Funktion auch ohne die für die CLI verpflichtende Split-Map aufrufen. [CLI-Pflichtargument](../src/ml/__main__.py#L282) · [Aufruf im Teacher](../src/ml/cue_ranker_teacher.py#L515) · [Funktionsdefinition](../src/features/cue_ranker_universe.py#L652) · [Beispiel aus den Tests](../tests/test_cue_ranker_teacher.py#L99)

### C4 · Mittel · Das gemeldete Übergangsende kann außerhalb der gespeicherten Vorschau liegen

Der Renderer schneidet das Audio am konfigurierten Vorschauende ab und meldet weiterhin das Ende der vollständigen Überblendung. Acht Takte im 4/4-Takt bei 150 BPM dauern 12,8 Sekunden. Der Standardnachlauf ab dem Source-Cue beträgt zwölf Sekunden. Der Batch kann die gekürzte WAV speichern, während die Render-Metrik die Endposition als außerhalb der Datei zurückweist. Damit kann eine abspielbare Variante ohne technischen Score bleiben. [Zuschnitt und Rückgabe](../src/variable_rendering.py#L169) · [Vorschau im Einzelrenderer](../src/pipeline.py#L363) · [WAV-Export](../src/batch_render.py#L291) · [Grenzprüfung der Metrik](../src/ranking/rendered_transition.py#L200)

### C5 · Mittel · Nach dem Ändern der Sequenz kann die GUI einen Bereich dem falschen Track zuordnen

Die GUI speichert die ausgewählten Zeitbereiche unter dem Listenindex des Songpaars. Beim Entfernen oder Verschieben eines Songs leert sie gespeicherte Cues, Einstellungen und Renderresultate. Die Bereichsauswahl bleibt unter dem alten Index erhalten. Wird in der Sequenz A → B → C der mittlere Song B entfernt, kann die frühere B-Auswahl auf der Wellenform von C erscheinen und die nächste Cue-Suche einschränken. [Sequenz ändern](../src/gui/transition_builder.py#L971) · [Bereiche speichern](../src/gui/transition_builder.py#L1253) · [Bereiche wiederherstellen](../src/gui/transition_builder.py#L951)

### C6 · Mittel · Ein fortgesetztes variables TCN/BiLSTM-Training kann unter derselben Run-ID anders weiterlernen

Die Batchgröße bestimmt, welche Beispiele zu einem Optimiererschritt zusammengefasst werden. Sie fehlt im geprüften Run-Vertrag. Ein Resume kann daher eine andere Batchgröße akzeptieren. Bei aktivem Dropout kommt eine zweite Abweichung hinzu. Der Runner setzt beim Neustart den ursprünglichen Seed, der Checkpoint enthält aber keinen Zufallszustand der letzten Epoche. Damit ist für diese Konfiguration die Fortsetzung eines unterbrochenen Laufs mit identischem Trainingsverlauf nicht gewährleistet. [Bildung der Batches](../src/ml/variable_runner.py#L427) · [Vertrag und Run-ID](../src/ml/variable_runner.py#L202) · [Seed und Resume](../src/ml/variable_runner.py#L230) · [Checkpoint-Inhalt](../src/ml/variable_runner.py#L663)

### C7 · Mittel · Der P10-Prüfnachweis hängt von den Git-Zeilenenden ab

P10 erwartet für `selection.json` den SHA-256 mit Präfix `c6b71de9`. Diesen Wert liefert der lokale CRLF-Arbeitsbaum. Der eingecheckte LF-Blob derselben Datei liefert `0eb235fa`. Die Modellwahl ist in beiden JSON-Fassungen identisch. Ein Checkout mit LF scheitert beim Vergleich mit dem vorhandenen P10-Nachweis. Auch der finale P11-Pfad vergleicht den Hash der ausgecheckten Auswahldatei unmittelbar mit dem gespeicherten Wert. [Erwartete Prüfsumme](masterarbeit/review_jp_20261118/p10/verified.json#L7) · [Auswahldatei](masterarbeit/review_jp_20261118/p10/selection.json) · [P10-Prüfung](../src/evaluation/p10_verify.py#L35) · [P11-Prüfung](../src/evaluation/comparison_study.py#L172)

## Befunde in der Dokumentation

| ID | Priorität | Befund und Auswirkung |
|---|---|---|
| D1 | Mittel | **Drei Einstiegsdokumente nennen unterschiedliche Arbeitsstände.** Die Haupt-README nennt die Bewertung des älteren Vocal-v2-Hörsatzes als nächsten Schritt. Der aktuelle Status nennt die Prüfung des P11-Hörplatzes. Die als maßgeblich bezeichnete Gesamtübersicht führt vorn noch den Verzicht auf Teilnehmererhebung vom 11. November, während der Auftrag vom 18. November den geschlossenen Hörversuch vorsieht. Wer das Projekt über die README oder die Gesamtübersicht übernimmt, kann den falschen Auftrag verfolgen. [Haupt-README](../README.md#L37) · [Gesamtübersicht](Projekt-Gesamtuebersicht.md#L5) · [Aktueller Status](STATUS.md#L3) · [Auftrag vom 18. November](REVIEW_JP_UMSETZUNG.md#L21) |
| D2 | Mittel | **Die P11-Anleitung führt erledigte Voraussetzungen als offen.** Laut Anleitung stehen technischer Review und Nutzercommit vor der ersten Sitzung noch aus. Der Review liegt vor, und Commit `16c525e` schließt die Versionierung ab. Offen bleibt die Kontrolle des tatsächlichen Hörplatzes mit dem Teilnehmerkonto. [Durchführungsanleitung](masterarbeit/review_jp_20261118/p11/durchfuehrung.md#L3) · [Commit- und Freigabenachweis](Bemerkungen.md#L3) |
| D3 | Mittel | **Der P06-Befund F-8 ist nur teilweise geklärt.** Das Register nennt den ausstehenden Nutzercommit. Die korrigierte Matrix, die Ergebnisnachweise und der Auswertungscode sind seit `4651e51` vom 22. November versioniert. Das frühere Problem unversionierter Dateien ist damit erledigt. Offen bleibt, ob der Autor zusätzlich eine gesonderte Freigabe für die Verwendung in der Thesis verlangt. [Register](REVIEW_JP_UMSETZUNG.md#L133) · [Ursprünglicher F-8-Befund](masterarbeit/REVIEW_JP_P06_UNABHAENGIG_20261119.md#L82) · [Korrigierte Matrix](masterarbeit/review_jp_20261118/p06_run02/matrix.csv) |
| D4 | Mittel | **Die Installation laut README deckt die empfohlene Testsuite nicht vollständig ab.** Die Anleitung installiert CUDA- und Entwicklungsanforderungen und ruft anschließend die gesamte Suite auf. Ein regulärer GUI-Test importiert `PySide6` voraussetzungslos. Das Paket steht separat in den GUI-Anforderungen. Auf einem frischen System ohne PySide6 scheitert dieser Test trotz befolgter README. [Installation](../README.md#L17) · [GUI-Test](../tests/test_baseline_lengths.py#L45) · [GUI-Anforderungen](../requirements-gui.txt#L2) |
| D5 | Niedrig | **Acht relative Links im archivierten P01-Bericht für run03 führen ins Leere.** Betroffen sind das Evaluationsprotokoll, das Prüfjournal, zwei run01-Dateien, das Evidence Ledger, die Höranalyse, das Control-Study-Protokoll und der Umsetzungsplan. Die Herkunftskette lässt sich vom archivierten Bericht aus nur teilweise verfolgen. [Archivierter Herkunftsbericht](masterarbeit/review_jp_20261118/p01/bestand_20261118_run03/EXPOSITION.md#L3) |
| D6 | Niedrig | **Der Neubau der Präsentationen ist an die Maschine des Autors gebunden.** Beide Builder verwenden absolute, versionsspezifische WindowsApps- und Benutzerpfade. Die fertigen PowerPoints liegen im Repository. Wer sie auf einem anderen Rechner neu bauen will, muss laut Anleitung zuvor den Quelltext anpassen. [Ursprünglicher Builder](../presentations/build.mjs#L6) · [Stilrevision](../presentations/build-style.mjs#L6) · [Bauanleitung](../presentations/README.md#L30) |

## Offene Fragen für Studie und Abschluss

### F1 · Hoch · Wurde der Hörplatz geprüft, und liegen echte Teilnehmerexporte vor?

Der Nachweis für run02 umfasst sieben zugelassene Songpaare, vier ausgeschlossene Paare, 49 Clips und drei vorbereitete Sitzungskennungen. Eine Kennung belegt die Vorbereitung des Players. Für eine abgeschlossene Teilnahme braucht P12 den gesicherten Originalexport. Der letzte dokumentierte Stand nennt die Kontrolle des beaufsichtigten Teilnehmerkontos und die Erhebung als offen. Bei sieben unabhängigen Paaren sieht das Protokoll eine deskriptive Auswertung vor. [Materialnachweis](masterarbeit/review_jp_20261118/p11/run02_verified.json) · [Stand der Erhebung](REVIEW_JP_UMSETZUNG.md#L200) · [Auswertungsregel](masterarbeit/review_jp_20261118/p11/studienprotokoll.md#L29)

### F2 · Hoch · Welcher Nachweis erfüllt die Abnahme des vollständigen Prototyps?

Das Aufgaben-PDF verlangt den Export eines finalen Mashup-Tracks. P14 sieht dafür eine vollständige Entwicklungs-Audiodatei aus mindestens drei Songs samt Sequenz- und Kantenmanifest vor und steht im Register auf „geplant“. Der manuelle P13-Durchklick ist ebenfalls offen. Für die Vorführung muss außerdem klar sein, welcher Bedienweg die gelernte Cue-Wahl zeigt. Die GUI bewertet per Feature-Regel bis zu 400 Kandidaten. Der Batch unterstützt den MERT-Selektor. [Aufgabenstellung](../angepasste_aufgabenstellung_masterarbeit.pdf) · [Abnahmeregister P13–P16](REVIEW_JP_UMSETZUNG.md#L128) · [GUI-Cue-Auswahl](../src/gui/transition_builder.py#L377) · [MERT im Batch](../src/batch_render.py#L184)

### F3 · Hoch · Welche Aussage über musikalische Qualität trägt die finale Thesis?

Die Offlinetabelle bestätigt **85,59 % Recall@1** für den gewählten MERT-Kopf. Epoche und Modellstufe wurden auf derselben Validation ausgewählt. Die positiven Fortsetzungen stammen jeweils aus derselben Aufnahme. Die MERT-Fenster können akustischen Kontext aus demselben Encoderchunk enthalten. Ob die gelernte Auswahl hörbar bessere Übergänge zwischen **verschiedenen** Songs findet, bleibt damit offen. Beide Abstracts beschreiben noch den älteren, auf Controller fokussierten Stand. Ihre Verwendung von „selbstüberwacht“ weicht von der späteren Unterscheidung zwischen gelernter Fortsetzungsmetrik und label-freier Controlleroptimierung ab. [Offlinetabelle](masterarbeit/review_jp_20261118/p10/offline.csv) · [Interpretation P10](masterarbeit/REVIEW_JP_P10_RANKING_20261119.md#L7) · [Fenstergeometrie P08](masterarbeit/REVIEW_JP_P08_PAARE_20261119.md#L69) · [Deutscher Abstract](../overleaf/chapters/00_abstract.tex#L7) · [Englischer Abstract](../overleaf/chapters/00_abstractEnglish.tex#L4)

### F4 · Hoch · Welche Abweichungen von der Aufgabenstellung hat die Betreuung bestätigt?

Manueller Korrekturaufwand und Nutzbarkeit für Tanzperformances stehen im Aufgaben-PDF als Evaluationsziele. Der Autor hat beide Nachweise und die Darstellung der GUI aus dem Thesisumfang genommen. Das Register nennt die datierte Bestätigung dieser Aufgabenabdeckung durch die Betreuung als offen. Für den Abschluss ist zu klären, ob Abschnittsauswahl, Mashup-Export, Übergänge von einem bis vier Takten und die Untersuchungen F1–F3 den vereinbarten Umfang erfüllen. [Aufgabenstellung](../angepasste_aufgabenstellung_masterarbeit.pdf) · [Autorenentscheidung und offene Rückmeldung](REVIEW_JP_UMSETZUNG.md#L26)

### F5 · Mittel · Welches Material darf mit dem Repository weitergegeben werden?

Für die geschlossenen Hörsitzungen liegt die dokumentierte Auskunft des Autors vor. Das Repository enthält außerdem `aufTAKTCl.exe` und 100 WAVs des historischen Modellhörvergleichs. Für die Weitergabe der Binärdatei fehlt laut Werkzeugdokumentation ein Beleg. Für die Musik beschreibt das Register die geschlossene Nutzung ohne Weitergabe. Vor einer Weitergabe des Repositorys bleibt zu klären, welche Binär- und Audiodateien sie umfassen darf. [Autorenangabe zu E3](REVIEW_JP_UMSETZUNG.md#L27) · [Werkzeugnachweis](EXTERNAL_TOOLS.md#L31) · [Historischer WAV-Bestand](LISTENING_STUDY_ANALYSE_20261106.md#L28)
