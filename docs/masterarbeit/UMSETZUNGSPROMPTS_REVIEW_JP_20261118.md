# Prompts zur Umsetzung des BeatBridge Aktionsplans

Stand 18. November 2026. Grundlage ist der vom Nutzer als eigener Plan
bestätigte `review_jp/ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md`. Diese Promptfolge
setzt dessen vollständigen Umfang um. Sie ist für neue Agentensitzungen im
Repository `D:\Documents\00Uni\00master\BeatBridge` gedacht.

## Verwendung und Modelle

Wähle das angegebene Modell und die Denktiefe vor dem Absenden. Kopiere dann
den jeweiligen Textblock in eine neue Sitzung mit Repositoryzugriff. Jeder
Block verweist auf den gemeinsamen Arbeitsrahmen dieser Datei; er muss nicht
zusätzlich kopiert werden. Die Anweisungen dienen auch Claude Code mit
Repositoryzugriff. Eine reine Chatsitzung ohne Dateien und Ausführungswerkzeuge
kann die Implementierungsaufträge nicht vollständig ausführen.

Die Zuordnung ist eine Empfehlung für diese Aufgaben: GPT-6.2 Sol für klar
umrissene Implementierung, GPT-6.2 Astra für anspruchsvolles Versuchsdesign,
Diagnose und Interpretation. High entspricht `high`, Extra High `xhigh`.
Die verfügbaren Modelle hängen vom Client und Konto ab. OpenAI beschreibt
Astra für anspruchsvolle Projekte und Sol für alltägliche Code- und
Schreibaufgaben; die konkrete Aufgabenverteilung unten stammt aus diesem Plan.
Quellen: [Modelle in Codex](https://learn.chatgpt.com/docs/models?surface=app)
und [Modellauswahl](https://developers.openai.com/api/docs/guides/model-selection).

Für unabhängige Reviews verwende möglichst dein bisheriges Claude-Reviewmodell
in einer frischen Sitzung. Das nutzt eine andere Modellfamilie; eine konkrete
Claude-Version wird hier nicht vorausgesetzt. Wenn Claude nicht zur Verfügung
steht, nutze einen separaten Astra-Review für eine Sol-Implementierung und einen
Sol-Review für eine Astra-Implementierung. Ein Review ist ein eigener Auftrag,
keine Selbstfreigabe des Bauagenten.

| Prompt | Aufgabe | Modell | Denktiefe | Voraussetzung |
|---|---|---|---|---|
| P00 | Umfang und Ausführungsstand festhalten | GPT-6.2 Astra | Extra High | zuerst |
| P01 | Evaluationsprotokoll und neue Evaluationspopulation | GPT-6.2 Astra | Extra High | P00 |
| P02 | Vergleichsmatrix der bisherigen Ergebnisse | GPT-6.2 Sol | High | P00 |
| P03 | Training und Anwendung angleichen | GPT-6.2 Sol | High | P00 |
| P04 | Gemeinsamen Render- und Auswertungspfad bauen | GPT-6.2 Astra | High | P01, P03 |
| P05 | Equal-Power-Initialisierung korrigieren | GPT-6.2 Astra | High | P04 |
| P06 | Controllerdiagnose und geplante Wiederholungsläufe | GPT-6.2 Astra | Extra High | P02, P04, P05 |
| P07 | MERT und klassische Taktrepräsentationen | GPT-6.2 Sol | High | P01 eingefroren und vom Nutzer committet |
| P08 | Kontrastive Paare und harte Negative | GPT-6.2 Astra | Extra High | P07 |
| P09 | Fortsetzungsmetrik trainieren | GPT-6.2 Astra | High | P08 |
| P10 | Offlinevergleich und Rankerintegration | GPT-6.2 Astra | Extra High | P09 |
| P11 | Hörversuch vorbereiten und Stimuli erzeugen | GPT-6.2 Astra | Extra High | P04, P10, E3 geklärt |
| P12 | Echte Hörbewertungen auswerten | GPT-6.2 Astra | Extra High | P11 und tatsächliche Bewertungen |
| P13 | Ein bis vier Takte und Strategien vervollständigen | GPT-6.2 Sol | High | P03; kann vor P11 erfolgen |
| P14 | Abschnittsauswahl und Mashup-Export | GPT-6.2 Astra | High | P13; kann vor P12 erfolgen |
| P15 | Thesis anhand aller neuen Ergebnisse überarbeiten | GPT-6.2 Astra | Extra High | P06, P10, P12, P14 |
| P16 | Abschlussprüfung und Abdeckungsbericht | anderes Modell als letzte Umsetzung | Extra High bei Astra, High bei Sol | P15 |
| R | Review eines Meilensteins | vorhandenes Claude-Reviewmodell | hohe Denktiefe, falls wählbar | nach den unten genannten Meilensteinen |
| F | Reviewbefunde korrigieren | Modell des jeweiligen Bauauftrags | High | nach R |
| O1 | Optionaler gelernter Kritiker | GPT-6.2 Astra | Extra High | erst nach Woche 3 bei Zeitreserve |
| O2 | Optionaler Beat-This-Pfad | GPT-6.2 Sol | High | erst bei Zeitreserve |

Sol High reicht für viele Codeänderungen. Verwende Astra Extra High dort,
wo eine falsche Schlussfolgerung das Experiment entwerten könnte. Mehr
Denktiefe ersetzt keine Messung. Falls nur ein Modell verfügbar ist, lassen
sich alle Prompts damit ausführen; die angegebenen Rollen bleiben bestehen.

## Gemeinsamer Arbeitsrahmen für alle Prompts

Dieser Abschnitt ist Bestandteil jedes untenstehenden Auftrags.

1. Lies `AGENTS.md`, `.agents/AGENT.md`, die in
   `.agents/multi-session-project-discipline.skill` enthaltene `SKILL.md`,
   `docs/STATUS.md` und `docs/Projekt-Gesamtuebersicht.md`. Die `.skill` ist
   ein ZIP-Archiv. Lies anschließend den Aktionsplan und die für deinen
   Teilauftrag einschlägigen Verträge, Code- und Ergebnisdateien.
2. Der Nutzer möchte den vollständigen Aktionsplan umsetzen. Ältere
   Scopebeschränkungen vom 11. November und die frühere Einordnung unter
   `docs/masterarbeit/REVIEW_JP_EINORDNUNG_20261118.md` dürfen diesen Auftrag
   nicht auf reine Diagnose reduzieren. Erhalte historische Entscheidungen
   und dokumentiere ihre Ablösung. Eine Zustimmung der Betreuung oder eine
   Lizenzfreigabe darf nur als tatsächlich erfolgt bezeichnet werden.
3. Setze den benannten Teilauftrag um. Liefere den Code, die Artefakte und
   die angemessene Prüfung. Technische Routineentscheidungen triffst du
   selbst. Frage nur nach wirklich fehlenden externen Entscheidungen oder
   Eingaben und arbeite währenddessen an unabhängigen Teilen weiter.
4. Prüfe zu Beginn den Arbeitsbaum und den Ausführungsstand. Bewahre vorhandene
   Nutzeränderungen. Nutze ein geeignetes vorhandenes Checkout; erzeuge nicht
   ohne Anlass weitere Worktrees. Keine Commits, Stagingaktionen oder Pushes.
   Der Nutzer committet. Wenn ein Planabschnitt vor dem Experiment einen
   Commit voraussetzt, liefere die fertigen Dateien und weise auf genau
   diesen ausstehenden Nutzercommit hin. Andere Aufgaben laufen weiter.
5. Nutze `.venv\Scripts\python.exe` für Python und Prüfungen. Originalaudio,
   historische Datasets, Checkpoints, Manifeste und Hörbewertungen bleiben
   unverändert. Neue Läufe bekommen eigene Pfade. Neue Formate sind additiv;
   alte Artefakte bleiben auswertbar. Experimentelle Änderungen an Renderer
   oder Initialisierung erhalten einen klar getrennten Vertrag.
6. Schreibe jeden ausgeführten Testlauf sofort in `docs/Bemerkungen.md`:
   Datum, Frage und Begründung, Eingaben/Setup, Befehl und Umfang, Ergebnis
   einschließlich Fehlern sowie Schlussfolgerung und nächster Schritt.
   Führe Tests aus, die den fachlichen Inhalt der Änderung prüfen. Eine
   technische Prüfung ist kein Hörurteil.
7. Lege keine neuen Qualitätslabels aus dem bisherigen Controller-Objective
   für die SSL-Metrik an. Trenne Entwicklungsdaten, Validation und die neue
   abschließende Evaluationspopulation nach Recording-Gruppen. Die neue
   Population wird vor den einschlägigen Experimenten festgelegt. Kein
   Training, Tuning, Probeanhören oder Kandidatenentscheid anhand dieses Sets;
   nur die vorab festgelegten Schritte der abschließenden Evaluation sind erlaubt.
8. Historische Befunde dürfen widerlegt oder präzisiert werden. Behandle
   Reviewaussagen als prüfbare Behauptungen, nicht als gewünschte Resultate.
   Keine erfundenen Seeds, Teilnehmer, Bewertungen, Literatur oder Messwerte.
   Roh-Losswerte ungleicher Pfade sind kein Architekturvergleich. Behalte
   nichtaktive Schutzterme und Positionsfeatures bei, solange keine fachliche
   Prüfung eine Änderung rechtfertigt.
9. Bestehende lokale Ressourcen haben Vorrang. Für neue Modellgewichte und
   externe Abhängigkeiten prüfe offizielle Quelle, Revision und Lizenz;
   nutze vorhandene Skills, darunter `hf-cli` für Hugging Face. Keine
   Audio-/Stemdaten oder Gewichte hochladen und keine kostenpflichtigen
   Cloudjobs ohne entsprechenden Auftrag starten. Die geplanten lokalen
   Experimente werden im jeweils zuständigen Prompt ausgeführt und überwacht.
10. Pflege `docs/REVIEW_JP_UMSETZUNG.md` als gemeinsame Aufgabenliste mit
    Status, Ergebnispfaden, offenen Abhängigkeiten und nächstem Prompt.
    Halte verifizierte Meilensteine auch in `docs/STATUS.md` fest. Ein kurzer
    offener Punkt ist kein Anlass, alle anderen Aufgaben anzuhalten.
11. Zum Abschluss: Was ist fertig, welche Dateien enthalten das Ergebnis,
    welche Tests liefen, was fehlt tatsächlich und welcher Prompt folgt?
    Behaupte keinen Abschluss, wenn nur ein Gerüst oder eine synthetische
    Probe existiert. Stelle keine neue umfassende Genehmigungsfrage für
    bereits beauftragte Arbeiten.

Die gemeinsame Aufgabenliste wird erst mit P00 angelegt. Hier werden nur
Prompts bereitgestellt; keine darin beschriebenen Experimente sind schon ausgeführt.

## P00 Umfang und Ausführungsstand

```text
Arbeite im BeatBridge-Repository. Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md und befolge ihn.
Setze jetzt P00 um; implementiere noch keine Modelle und starte kein Training.

Überführe review_jp/ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md vollständig in
docs/REVIEW_JP_UMSETZUNG.md. Ordne jede Phase, jeden Grundsatz G1–G10,
jede Entscheidung E1–E5 und jeden optionalen Teil einem Arbeitspaket,
einem Ergebnis und einem überprüfbaren Abschlusskriterium zu.

Der neue Plan ist vom Autor zur Umsetzung bestimmt. Halte neue Leitfrage,
Fortsetzungsmetrik, Controllerdiagnose, Hörversuch, Mashup-Export und
Übergangslängen 1–4 als vorgesehenen Umfang fest. Markiere gesondert,
welche formalen Betreuungsentscheidungen noch tatsächlich fehlen.
Erfinde insbesondere keine Zustimmung zu E2 oder Lizenzklärung zu E3.
Bereite dafür konkrete kurze Entscheidungsfragen vor und frage sie ab,
ohne die übrigen Arbeitspakete zu blockieren.

Erfasse vorhandene lokale Hardware, Modelle, Datensätze, Caches und
September-Runs anhand ihrer Metadaten. Reserviere eindeutige neue
Artefaktpfade. Erhalte die historischen 6-/8-Takt-Daten, aber plane keine
weiteren Sweeps dafür. Dokumentiere die neuen Prioritäten in STATUS.

Fertig: vollständige Aufgabenliste mit Abhängigkeiten, Entscheidungsstand,
Nachweisen und klarer Übergabe an P01–P03. Keine bloße Empfehlungsliste.
```

## P01 Evaluationsprotokoll und neue Population

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P01 um.

Erstelle docs/EVALUATION_PROTOCOL.md gemäß Phase 1.1 und G1–G10 des Plans.
Präzisiere Hauptkennzahlen, Seeds, Budgets, Checkpointregel, Trennung von
Training/Validation/Evaluation, Ausschlüsse und die gemeinsame Renderkonfiguration.
Definiere vorab die Vergleiche und die Auswertungseinheit Trackpaar.
Prüfe zusätzliche Abhängigkeiten durch wiederverwendete Tracks; bevorzuge
für das finale Set disjunkte Trackpaare aus 20–24 neuen Recording-Gruppen.

Erstelle aus bisher unbenutztem Material ein abschließendes Set von 10–12
Paaren. Prüfe frühere Verwendung anhand Manifeste, Ledger und Hörstudien;
ein anderer Dateihash derselben Aufnahme macht sie nicht unabhängig.
Nutze für die Auswahl nur vorab definierte Zulässigkeitskriterien und
Metadaten, kein Anhören oder Qualitätsranking. Schreibe die Hash-/Gruppenliste.
Falls nicht genug wirklich neue Aufnahmen vorliegen, dokumentiere genau
die fehlende Anzahl und frage nach zusätzlichem Material. Erstelle trotzdem
das vollständige Protokoll und die Werkzeuge zur Expositionsprüfung.

Schreibe keine ausgedachten Hashes. Bereite Protokoll und Liste für den
Nutzercommit vor; erst danach dürfen die zugehörigen neuen Experimente
aus Phase 2/3 beginnen. Bestehende Diagnosearbeit bleibt unabhängig möglich.

Fertig: konkretes Protokoll, belegte Expositionsprüfung, echte Hashliste
oder genau abgegrenzter Materialmangel und dokumentierter Commitstatus.
```

## P02 Vergleichsmatrix

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P02 um.

Erweitere docs/RESULTS_EVIDENCE_LEDGER.md additiv um die Vergleichsmatrix
aus Phase 1.2. Erfasse jede empirische Zahl in Kapitel 5 mit Fundstelle,
Dataset-ID, Split, Recording-/Track-/Paaranzahl, Feature-Protokoll,
Vocal-Backend, Renderer und Konfiguration, Objectiveversion, Abtastrate,
Seed, Referenzzustand, Checkpointregel und Artefaktpfad.

Kennzeichne jede Aussage als kontrollierter Vergleich, Befund innerhalb
eines Laufs oder explorativer Vergleich. Gruppiere wiederholte Tabellenwerte
sinnvoll, aber lasse keine Zahl ohne zuordenbare Zeile. Rechne erforderliche
relative Verbesserungen aus den tatsächlichen Rohwerten nach. Trenne
Equal Power, untrainierten TCN und erste bereits trainierte Variable-Epoche.

Die neuen Reviewmessungen auf August-Daten dürfen nicht stillschweigend
als September-Befunde erscheinen. Historische Tabellen und Manifeste
werden nicht überschrieben. Dokumentiere echte Lücken präzise.

Fertig: vollständige Matrix und Prüfung der Kapitel-5-Abdeckung sowie
eine Liste der für P06 noch fehlenden Vergleichsbedingungen.
```

## P03 Training und Anwendung angleichen

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P03 um.

Behebe die in Phase 1.3 benannten Fehler: inverse Cue-Skalierung im
GUI-ML-Pfad, festes RoFormer-Backend trotz abweichendem Trainingsvertrag
und dauerhaftes Cachen fehlgeschlagener aufTAKT-Analysen als erfolgreicher
Analysepfad. Bestätige zuerst die Ursache im aktuellen Code.

Führe gemeinsam genutzte Berechnungen für Tempo-/Cue-Koordinaten ein,
soweit das die Divergenz verhindert. Lade Backend, Normalisierung und
Modellkonfiguration aus dem tatsächlichen Run-/Datasetvertrag. Prüfe diese
Verträge bei Inferenz explizit und erkläre konkrete Unverträglichkeiten.
Markiere Fallbacks und ermögliche einen erneuten echten Analyseversuch,
ohne historische Caches oder Originale pauschal zu löschen.

Teste insbesondere ungleiche BPM in beiden Richtungen, identische BPM,
abweichende Vocal-Backends sowie Fallback gefolgt von erfolgreicher Analyse.
Prüfe sinnvoll betroffene bestehende Tests. Keine Objectiveänderung und
kein neues Training in diesem Auftrag.

Fertig: implementierte Korrekturen, bestandene fachliche Regressionen,
dokumentierte Auswirkungen auf alte Artefakte und Übergabe an P04.
```

## P04 Gemeinsamer Render und Auswertungspfad

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P04 um.

Baue den gemeinsamen Render- und Auswertungspfad aus Phase 1.3. Verwende
vorhandene Renderer und Adapter; vermeide eine weitere unabhängige
Implementierung der Audiogeometrie. Die Schnittstelle muss die historisch
verschiedenen Pfade explizit konfigurieren können und gleiche Bedingungen
innerhalb jedes Vergleichs erzwingen. Getrennte alte Verträge bleiben lesbar.

Unterstütze Equal Power, eine auf Training optimierte feste Kurve,
gelernte Controls und direkte Optimierung pro Beispiel. Speichere für alle
Bedingungen dieselbe Ergebnistabellenstruktur. Halte Abtastrate, Filterkerne,
Fenster, Kontexte und Gainverfahren im Protokoll fest. Für den Hörversuch
baue den vorgesehenen LUFS-Abgleich ein und dokumentiere Messfenster,
Zielwert, Spitzenpegelbehandlung und Einfluss auf die Energieinterpretation.
Proxywerte vor und nach Hörstimulus-Normalisierung müssen unterscheidbar bleiben.

Teste Zwei-Band mit linearer Positionskurve gegen EqualPowerFadeCut und
zweimalige bitgleiche Wiedergabe der gleichen Equal-Power-Bedingung.
Nutze zuerst synthetische Signale und Entwicklungsdaten, kein finales Set.

Fertig: ausführbarer gemeinsamer Pfad, fachliche Tests, ein echter kleiner
Entwicklungs-Smoke und dokumentierter Aufruf für P06 und P11.
```

## P05 Initialisierung aller Controller

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P05 um.

Erzeuge für künftige Läufe einen fachlich geprüften Equal-Power-Start
jedes Controllers. Prüfe Gainkurven, EQ-Neutralität, Ducking und den
tatsächlich gerenderten Audiostart. Der feste TCN startet aktuell mit
linearen Hauptgains und 0,5-Hilfscontrols. Auch der bisherige Vocal-Start
ist wegen kleinen Duckings nicht exakt neutral.

Entwirf die kleinste additive Formatänderung, die echte Equal-Power-
Initialisierung und trainierbare Controls verbindet. Begründe die konkrete
Parametrisierung und prüfe ihre Gradienten, damit eine neutrale Schranke
nicht das weitere Lernen verhindert. Erhalte die Interpretation alter
Checkpoints über eine klar getrennte Legacy-Konfiguration. Alte Gewichte
und historische Epoche-0-Werte bleiben unverändert.

Logge auch für variable Läufe eine echte Epoche 0. Teste gerendertes Audio
gegen die passende Equal-Power-Bedingung, Endpunkte, Neutralität und
einen endlichen wirksamen Gradienten. Führe nur die hierfür erforderlichen
kurzen Prüfungen aus; Wiederholungstrainings gehören zu P06.

Fertig: geprüfter neuer Initialisierungsvertrag, Rückwärtskompatibilität
und eindeutig benannte neue Konfigurationen für die geplanten Läufe.
```

## P06 Controllerdiagnose und Wiederholungsläufe

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P06 um.

Übertrage die Reviewdiagnostik aus review_jp/scripts/ auf die September-
Läufe R1–R4. Prüfe vorab Artefaktvollständigkeit und die Verträge; verwende
neue Ergebnispfade. Vergleiche je Pfad Equal Power, eine ausschließlich
auf Train optimierte feste Kurve, das Modell und direkte Optimierung pro
Beispiel. Ergänze Vertauschungstests, komponentenweisen Loss und Audio-
abweichungen. Unterschiede zwischen Legacy- und neuem Initialisierungsvertrag
müssen in jeder Tabelle erkennbar sein.

Führe die geplanten lokalen Wiederholungen für MLP v1 und Vocal-MLP v2
mit jeweils drei vorab dokumentierten Seeds durch. Trainiere den festen
TCN zusätzlich mit echtem Equal-Power-Start. Isoliere beim TCN-Vergleich
die Initialisierungsänderung; ändere nicht zugleich Objective und Daten.
Überwache die Läufe bis zum dokumentierten Ende und erfasse Fehler.
Keine neuen Architektur- oder Hyperparametersweeps.

Berichte Streuung und die Bezugsgröße jedes Prozentwerts. Direkte
Optimierung nach endlicher Schrittzahl ist kein bewiesenes globales Optimum.
Die 99,9-%-Reviewzahl darf nicht aus einem gedämpften Start heraus als
allgemeine Überflüssigkeit des Netzes interpretiert werden.

Fertig: Diagnose aller vier Pfade, tatsächlich abgeschlossene geplante
Wiederholungsläufe und ein evidenzgebundener Kapitelentwurf zur Frage,
welchen Nutzen die eingabeabhängigen Controls bisher liefern.
```

## P07 Taktrepräsentationen und Augmentierung

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P07 um.
Prüfe, dass Protokoll und neue Evaluationspopulation aus P01 eingefroren
und vom Nutzer committet sind. Bearbeite hier nur Trainings-/Validationmaterial.

Implementiere Phase 2.1: eingefrorene MERT-Repräsentationen auf unverändertem
Originalaudio bei 24 kHz mono, alle Hidden Layers, gemittelt über die
tatsächlichen Taktgrenzen. Wähle anhand lokaler GPU-/RAM-Ressourcen eine
konkrete MERT-Variante, prüfe offizielle Modellkarte und Lizenz und binde
Revision sowie Gewichtshashes. Nutze den Hugging-Face-Skill. Starte mit
einem kleinen Laufzeit-/Speicher-Smoke und extrahiere danach den vorgesehenen
Train-/Validationbestand mit wiederaufnehmbarem Cache.

Implementiere daneben die klassische Repräsentation des Plans: Mittel
und Streuung je Takt über acht Halbbeats, Skalierung nur auf Training.
Definiere die im Plan vorgesehenen 41 Audiokanäle explizit. Entferne dabei
keine Positionskanäle aus alten Controllerverträgen; zeitliche Koordinaten
sind von inaktiven Audioinformationen zu unterscheiden.

Erzeuge zwei bis drei Fassungen pro Track mit dokumentiertem EQ, Pegel
und leichtem Hall. Keine Tonhöhenänderung; Originale bleiben erhalten.
Teste Taktausrichtung, Cacheidentität und Gruppentrennung der Augmentierungen.

Fertig: echte gecachte Repräsentationen beider Familien für Train/Validation,
Augmentierungen, Modellprovenienz und dokumentierter Ressourcenbedarf.
```

## P08 Kontrastive Paare und Negative

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P08 um.

Implementiere Phase 2.2 auf den Repräsentationen aus P07. Leite die genaue
Fenstergeometrie aus Renderer und Cuevertrag her: Ein- und Ausblendfenster,
Quellgrenze S, Zielgrenze T sowie die L Takte der Überlagerung. Zeige mit
einem Taktschema, welche k Takte vor d und welche ab d+L das positive Paar
bilden. Prüfe die Indizes gegen echte Metadaten, statt eine Annahme aus
dem Review unbesehen zu übernehmen.

Erzeuge zunächst L=4. Negative: andere Tracks im Batch, tempoähnliche
Tracks mit höchstens 5 % Unterschied und weit entfernte, strukturell
abweichende Stellen desselben Songs mit mehr als 16 Takten Abstand.
Behandle mögliche falsche Negative in repetitiver Musik mit einer
begründeten Umsetzung von Debiased Contrastive Learning. Verifiziere die
Primärquelle und die Formel; verwende nicht den bisherigen Proxy als Label.

Splitte nach Recording-Gruppen und binde alle Augmentierungen an dieselbe
Gruppe. Validationnegative und Retrieval-Kandidaten müssen reproduzierbar
feststehen. Definiere k, Samplingbudget und Seeds vor den Modellvergleichen.

Fertig: realer Paarbestand, geprüfte Geometrie, getrennte Splits, negative
Kontrollen und ausgeführter Trainingsbatch-Smoke für beide Repräsentationen.
```

## P09 Fortsetzungsmetrik trainieren

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P09 um.

Implementiere die Kapazitätsleiter aus Phase 2.3 für MERT und klassische
Merkmale: Stufe 0 ohne Training als Kosinus, Stufe 1 als Bilinearabbildung
mit niedrigem Rang, Stufe 2 als gerichtete Zwei-Turm-Metrik mit Ausgabe
128 und je einer versteckten Schicht. Für MERT kommt die lernbare
Schichtgewichtung hinzu. Berichtige die tatsächlichen Parameterzahlen
anhand der Implementierung; die Reviewzahlen sind ungefähre Zielgrößen.

Nutze InfoNCE mit der in P08 festgelegten Behandlung falscher Negative.
Verwende dieselben Paare, vorab festgelegten Trainingsbudgets, drei Seeds
und Auswahlregeln für beide Repräsentationen. Berichte Unterschiede durch
Eingabedimension und Schichtgewichtung, statt Kapazitätsgleichheit zu behaupten.
Wähle Checkpoints anhand Validation-Recall@1. Skalierung wird nur auf Train
gefittet. Ein identischer deterministischer Stufe-0-Lauf ist kein neuer Seed.

Führe zuerst einen kleinen technischen Smoke und danach die vorgesehenen
lokalen Trainings tatsächlich aus. Überwache sie bis zum Ende. Nutze
keinen finalen Test und keine Hörurteile zur Modellwahl. Stufe 3 ist Reserve;
implementiere sie nur bei einer dokumentierten Notwendigkeit nach Stufe 2.

Fertig: abgeschlossene Stufen 0–2 für beide Repräsentationen mit drei
Seeds der trainierten Stufen, echten Checkpoints, Lernverläufen und Tabelle.
```

## P10 Offlineprüfung und Rankerintegration

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P10 um.

Führe Phasen 2.4–2.6 aus. Ermittle Recall@1 und MRR bei festgelegten harten
Negativen auf Validation. Prüfe Aufnahmeidentität als Abkürzung mit
geeigneten Same-Track-Negativen sowie Intro-/Drop-Kontrasten und berichte
die Zahl und Herkunft der Fälle. Ein einzelner unpassender Intro/Drop-Fall
beweist die Abkürzung nicht; prüfe das vorher festgelegte Muster.

Vergleiche Top-1 und Rangkorrelation mit feature_baseline_v3. Bereite die
im Plan vorgesehene begrenzte Sichtung widersprüchlicher Entwicklungsfälle
für den Autor vor; erfinde kein Anhören. Verwende dafür niemals das neue
finale Evaluationsmaterial.

Entscheide ausschließlich anhand der vorab definierten Validationregeln,
welches Modell in den Hörversuch geht. Falls keines die Abkürzungsprüfung
besteht, schärfe im festgelegten Budget die Negative nach. Nutze bei
ausgeschöpftem Budget die dokumentierte Nullvariante aus dem Plan.
Kennzeichne diese als eingefrorene Repräsentation ohne neu trainierten Kopf.
Halte MERT- und klassische Bedingungen getrennt. Der geplante Hörversuch
bleibt SSL/Regel/Zufall; ein besserer klassischer Offlinewert ersetzt die
SSL-Bedingung nicht stillschweigend und wird als eigener Befund berichtet.

Integriere den ausgewählten Ranker als eigenen ranking_method unter
src/ranking/ und im Batch-Render. Der alte Proxy-Lehrer wird nicht für
diese neue Metrik benutzt; historische Ergebnisse bleiben erhalten.

Fertig: vollständige Offlinetabelle, dokumentierte Auswahl und ein echter
Batch-Render mit dem neuen Ranker auf Entwicklungsdaten.
```

## P11 Hörversuch vorbereiten

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P11 um.

Bereite Phase 3 vor. Halte vor dem Rendern die Hypothesen und die gesamte
Auswertung datiert fest: H1 SSL-Cues gegenüber Regel-Cues, H2 Cue-Effekt
gegenüber Kurveneffekt, H3 direkt optimiert nicht schlechter als Equal
Power. Operationalisiere H2 mit einem vorab festgelegten Kontrast. Für H3
definiere eine fachlich begründete Nichtunterlegenheitsmarge und Auswertung.
Wenn eine externe Entscheidung hierzu nötig ist, lege eine konkrete
Auswahl vor. Unklare Hypothesen dürfen nicht erst nach Ratings präzisiert werden.

Erzeuge über P04 die vorgesehenen sechs Bedingungen pro Paar: SSL/Regel/
Zufalls-Cue mal Equal Power/direkt optimiert (Objective v4, Zwei-Band),
plus einen im Protokoll eindeutig definierten harten Schnitt als Anker.
10–12 neue Paare, ungefähr 20 Sekunden je Stimulus, gemeinsame technische
Konfiguration, dokumentierter LUFS-Abgleich, anonyme und randomisierte
Labels. Coincidente Top-1-Cues und eventuelle technische Ausschlüsse
werden nach vorab festgelegter Regel behandelt.

Baue den Player mit Skala 0–100 und optionalem Kommentar, Export und
Zuordnungsschutz. Prüfe ihn zuerst mit separaten Entwicklungsstimuli.
Der Versuchsleiter kann die Zuordnung verwalten; die Hörenden dürfen sie
vor Abschluss nicht sehen. Veröffentliche kein Audio.

E3 ist eine reale Voraussetzung für Durchführung und Teilnehmerzugang.
Bei ungeklärter Freigabe bereite Code und Anleitung mit Entwicklungsdaten
fertig vor und frage nur diese konkrete Entscheidung ab. Der Agent
rekrutiert und kontaktiert niemanden selbst. Die Bewertungen kommen von Menschen.

Fertig: vorab festgelegtes Protokoll, geprüfter Player und bei erfüllten
Voraussetzungen der komplette finale Stimulusbestand samt Studienanleitung.
```

## P12 Hörbewertungen auswerten

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P12 um.

Prüfe zuerst, ob echte abgeschlossene Bewertungsexporte aus P11 vorliegen.
Falls sie fehlen, benenne genau die benötigten Exporte und implementiere
die Auswertung anhand separat erzeugter synthetischer Testdaten. Bezeichne
diese nie als Studienergebnis und arbeite an unabhängigen Aufgaben weiter.

Werte echte Exporte anschließend unverändert nach dem vorab festgelegten
Protokoll aus. Prüfe Vollständigkeit, Stimulusidentitäten, Ausschlüsse und
Teilnehmerzuordnung. Entblinde erst nach dem vorgesehenen Abschluss.
Nutze Bewertung ~ Cue × Kurve mit den geplanten zufälligen Effekten für
Trackpaar und Person. Führe die geplanten Bootstrapintervalle über die
definierten unabhängigen Gruppen aus und berücksichtige etwaige gemeinsame
Tracks. Bei Singularität oder zu wenig Daten berichte den Befund und den
vorab definierten deskriptiven Ausweichpfad; erzeuge keine künstliche Präzision.

Berichte H1–H3 und die sekundären Korrelationen der Metriken innerhalb der
Trackpaare. Nicht signifikant bedeutet weder gleichwertig noch nicht
unterlegen. Bei nur einem zulässigen Rater gilt der explorative Ausweichpfad.
Neue Beobachtungen werden von vorab geplanten Analysen getrennt.

Fertig: unveränderte Rohbewertungen, reproduzierbares Auswertungsskript,
Ergebnistabellen und Abbildungen, protokollierte Abweichungen und Matrixzeilen.
```

## P13 Übergangslängen und Strategien

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P13 um.

Vervollständige Phase 4 für die Baselinepfade: 1, 2, 3 und 4 Takte in
Kandidatenerzeugung, Konfiguration, Renderer und GUI. Prüfe reale
Fenster-/Taktgrenzen und klare Meldungen bei zu kurzen Abschnitten.
Bestehende feste Vier-Takt-ML-Checkpoints dürfen nicht still auf andere
Längen angewendet werden. Die alten variablen 2/4/6/8-Verträge bleiben
lesbar; dieser Auftrag verlangt kein ungeplantes ML-Neutraining auf 1/3.

Klare außerdem tempo_fade: Wenn es nur ein Alias des normalen Fades ist,
führe es für alte Konfigurationen als dokumentierten Alias weiter, zeige
es aber nicht als eigenständige wissenschaftliche Strategie. Eine neue
Tempokurve wird nur implementiert, wenn sie im Ausführungsstand beschlossen ist.

Teste Samplelängen, Taktgrenzen, Kandidatenfilter, GUI-Modellbeschränkung
und Konfigurationskompatibilität. Rendere kleine Entwicklungsbeispiele
für 1–4 Takte. Eine GUI-Abnahme durch den Nutzer bleibt als solche sichtbar.

Fertig: technisch nutzbare Baselineübergänge für alle vier Längen und
ein korrekter Strategieumfang, bereit für den Sequenzexport aus P14.
```

## P14 Abschnittsauswahl und Mashup Export

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P14 um.

Implementiere einen vollständigen Export aus einer Sequenz ausgewählter
Songabschnitte. Erweitere die bestehende Sequenz um die hierfür nötigen
Start-/Endgrenzen und konsistente Cue-Zustände. Ein Suchbereich für
Cue-Kandidaten ist kein vollständiger Abschnitt. Korrigiere dabei die
Zuordnung von Cues und Bereichen nach Umsortieren der Sequenz.

Lege die Tempobehandlung über mehrere Kanten explizit fest und vermeide
mehrfaches Strecken bereits gestreckten Audios. Wende Source-/Target-
Koordinaten, Samplingrate und Überlagerungslängen einheitlich an.
Verkette erhaltene Songabschnitte und Übergänge ohne doppelte oder
fehlende Samples. Nutze die vorhandenen Renderer und biete den finalen
Export im bestehenden Workflow an. Erhalte Paarvorschauen und Originaldateien.

Teste drei oder mehr Songs, gemischte 1–4-Takt-Übergänge, unterschiedliche
BPM, Umsortieren und ungültige kurze Abschnitte. Prüfe erwartete Gesamtdauer,
Kantenpositionen und den deterministischen Export. Erzeuge abschließend
eine echte vollständige Entwicklungs-Audiodatei samt Metadaten.

Fertig: ein nutzbarer Mashup-Export aus mindestens drei Songs mit
gemischten Übergangslängen und dokumentierter technischer Prüfung.
```

## P15 Thesis überarbeiten

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze P15 um.

Überarbeite die Thesis nach Phase 5 und den tatsächlich abgeschlossenen
Ergebnissen. Zentrale Fragen: Wo gegenüber Wie; SSL-Metrik gegenüber
Regeln und klassischen Merkmalen; Erklärung des bisherigen Controllerbefunds.
Erstelle zuerst eine kurze Zuordnung Frage → Experiment → Matrixzeile
→ belegte Antwort und überarbeite danach die betreffenden Kapitel.

Aktualisiere Methodik, Implementierung, Ergebnisse und Diskussion; gleiche
Einleitung, Forschungsbeiträge, beide Zusammenfassungen, Fazit und Anhang
damit ab. Bezeichne den Controller als label-freie Proxy-Optimierung und
die neue Repräsentation/Metrik entsprechend ihrer tatsächlichen Lernart.
Berichte negative Resultate ebenso präzise wie positive und trenne den
historischen P5-Hörtest von der neuen Studie.

Prüfe die Primärquellen zu Audio Match Cutting, CPC, Debiased Contrastive
Learning, MARBLE und SUPERB. Ergänze nur inhaltlich relevante Aussagen
mit verifizierter Bibliografie; bloßes Nennen deckt keinen Beitrag ab.
Bewahre den etablierten englischen Schreibstil des Autors und gültige
Labels/Zitate. Übernimm GUI-/Exportumfang gemäß dem neuen Ausführungsstand,
ohne eine nicht erfolgte Betreuungsentscheidung zu behaupten.

Baue die Thesis und prüfe die gerenderten Seiten, besonders neue Tabellen,
Diagramme und Verweise. Falls ein Werkzeug fehlt, behebe den konkreten
Buildpfad soweit möglich und berichte die verbleibende Grenze genau.

Fertig: durchgehend konsistente Thesis mit belegten Antworten auf die
drei neuen Fragen, vollständigen Matrixbezügen, Build und visueller Prüfung.
```

## P16 Abschlussprüfung

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Führe P16 als
frischer Reviewer aus. Ändere zunächst keine Produktions- oder Thesisdateien.

Prüfe den gesamten Aktionsplan gegen den erreichten Stand. Kontrolliere
jede Pflichtphase, E1–E5, G1–G10, die experimentellen Rohartefakte,
Recording-Gruppen, Evaluationsexposition, Seeds, Baselines, Rendergleichheit,
Studienrandomisierung, echte Ratings und die Hypothesenauswertung.
Prüfe passende fachliche Regressionen, den vollständigen Mashup-Export
und den Thesisbuild einschließlich neuer gerenderter Seiten.

Ziehe für tragende Aussagen unabhängige Stichproben aus tatsächlichen
Artefakten; eine grüne Testsuite und der Bericht des Bauagenten reichen
nicht. Trenne technische Fertigstellung von wissenschaftlicher Evidenz
und formalen offenen Entscheidungen. Benenne unbelegte Neuheits- oder
Kausalbehauptungen mit exakten Fundstellen.

Schreibe docs/REVIEW_JP_ABSCHLUSSAUDIT.md mit priorisierten Befunden,
prüfbaren Invarianten und verbleibenden Einschränkungen. Protokolliere
eigene Testläufe in Bemerkungen. Starte kein neues Training und keinen
zusätzlichen Hörversuch. Behaupte keinen Abschluss fehlender Pflichtteile.

Fertig: eindeutiger Abdeckungsbericht und konkrete Korrekturliste für F.
```

## R Review eines Meilensteins

Nach P01, P06, P10, P11 und P14 in einer frischen Sitzung einsetzen.
Der erste Satz kann um den konkreten Meilenstein ergänzt werden; andernfalls
ermittelt der Reviewer ihn aus der gemeinsamen Aufgabenliste.

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Reviewe den
zuletzt fertiggestellten, noch nicht unabhängig geprüften Meilenstein
in docs/REVIEW_JP_UMSETZUNG.md. Du bist Reviewer, nicht der Bauagent.

Lies den zugehörigen Planabschnitt, Diff, Verträge, Tests und tatsächliche
Ergebnisartefakte. Prüfe zwei bis drei tragende Behauptungen eigenständig.
Suche nach Datenleckage, Index-/Tempo-/Renderfehlern, unfairen Bedingungen,
unbelegten Schlussfolgerungen und nur scheinbar bestandenen Abschlusskriterien.
Führe gezielte sinnvolle Prüfungen aus und protokolliere sie in Bemerkungen.
Kein neues Training, keine finalen Testdaten außerhalb des festgelegten
Evaluationsschritts und keine Änderungen an Produktionscode oder Originalen.

Schreibe die Befunde mit Priorität, Datei-/Zeilenfundstelle, Auswirkung
und konkreter Korrekturanforderung in einen eindeutig benannten Bericht
unter docs/masterarbeit/. Gib echte Fehler und Unsicherheiten getrennt an.
Bei fehlenden Befunden nenne die tatsächlich geprüften Invarianten.
Verlange keine Erweiterungen außerhalb des vereinbarten Plans.
```

## F Korrekturen nach einem Review

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Bearbeite den
neuesten offenen Meilenstein-Review aus docs/REVIEW_JP_UMSETZUNG.md.

Prüfe jeden Befund gegen Code und Rohartefakte. Behebe bestätigte Fehler
und führe die betroffenen fachlichen Prüfungen erneut aus. Unberechtigte
Befunde begründest du mit konkretem Nachweis. Lösche weder den Review
noch historische Ergebnisse. Korrigierte Experimente erhalten neue Pfade;
die Gültigkeit früherer Tabellen wird eindeutig markiert.

Aktualisiere Aufgabenliste, Evidenzmatrix und Testprotokoll. Gib zum
Abschluss für jeden Befund an: behoben, widerlegt oder mit konkreter
externer Abhängigkeit offen. Setze danach nur den nächsten vorgesehenen
Teilauftrag fort; beginne keine zusätzlichen Sweeps oder Studien.
```

## O1 Optionaler gelernter Kritiker

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Setze O1 nur
um, wenn die Pflichtphasen einschließlich neuer Studie abgeschlossen
sind und die Aufgabenliste dafür ausdrücklich Zeitreserve ausweist.

Implementiere Phase 6 als klar getrenntes Experiment: Nutze die eingefrorene
SSL-Metrik als differenzierbaren Kritiker für gerendertes Audio. Prüfe
zuerst, ob ihre Fenstergeometrie und Trainingsaufgabe dafür überhaupt
geeignet sind, und teste die Gradienten durch Resampling, Encoder und
Renderer. Keine diskrete oder abgetrennte Berechnung als differenzierbar ausgeben.

Vergleiche unter identischen Daten, Initialisierung und Budgets gegen den
bisherigen Proxy. Untersuche Ausnutzung des Kritikers durch künstliche
Artefakte, Lautheit oder Spektralverformung auf Entwicklungsdaten. Verwende
die schon gehörte finale Studie nicht erneut als unberührten Test und
verändere keine Ergebnisse der Pflichtphasen.

Fertig: abgeschlossener kleiner Machbarkeitslauf, Ressourcenmessung und
ehrlicher Befund. Ein neuer perzeptueller Nachweis braucht ein separates
vorab festgelegtes Protokoll und echte Hörbewertungen.
```

## O2 Optionaler Beat This Pfad

```text
Lies den gemeinsamen Arbeitsrahmen in
docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md. Bearbeite O2 nur
bei dokumentierter Zeitreserve, ohne Pflichtphasen zu verschieben.

Prüfe offizielle Beat-This-Implementierung, Gewichte und Lizenz. Ergänze
einen optionalen Analyseadapter mit dem bestehenden Beat-/Downbeatvertrag.
Erhalte aufTAKT und historische Analyse-/Datasetartefakte. Erzwinge einen
neuen expliziten Backend-/Cachevertrag, damit Modelle nicht versehentlich
mit anders erzeugten Merkmalen evaluiert werden.

Teste bekannte synthetische Taktfälle und ein kuratiertes Entwicklungsset.
Berichte Genauigkeit nur gegen tatsächliche Referenzannotation und messe
Laufzeit sowie Fehlerfälle. Ein Ersatzbackend begründet noch keine
Plattformunabhängigkeit der übrigen Audio-/GUI-Pipeline.

Fertig: optionaler geprüfter Adapter mit begrenzter Migration; kein
ungeplanter Neuaufbau sämtlicher Daten und Experimente.
```

## Reihenfolge der Sitzungen

Starte mit P00, dann P01 und R. P02 und P03 können danach unabhängig
bearbeitet werden, jedoch nicht mit gleichzeitigen Schreibzugriffen auf
dieselben Dateien. Es folgen P04–P06 und R. Erst mit eingefrorenem,
committetem Protokoll folgen P07–P10 und R. P13/P14 können unabhängig von
der tatsächlichen Bewertungsphase vorbereitet und abgeschlossen werden.
Nach P11 und R hört der Nutzer beziehungsweise hören die vorgesehenen
Teilnehmenden bei erfüllter E3. Anschließend P12, P15 und P16;
bestätigte Reviewfehler werden
mit F behoben. Optionale Arbeiten stehen hinter den Pflichtphasen.

Wenn du eine angefangene Sitzung fortsetzen willst, reicht dieser Prompt:

```text
Lies docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md und den
Ausführungsstand in docs/REVIEW_JP_UMSETZUNG.md. Setze das erste begonnene,
noch nicht abgeschlossene Arbeitspaket anhand seines zugehörigen Prompts
fort. Verifiziere vorhandene Artefakte, bevor du Arbeit wiederholst.
Falls es auf externe Eingaben wartet, arbeite an dem nächsten unabhängigen
vorgesehenen Paket weiter und halte die fehlende Eingabe konkret fest.
```
