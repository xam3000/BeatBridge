# BeatBridge – Stand & Next Steps

**Geblendeter Hörtest mit vier trainierten Modellen auf 20 Beispielen am
2026-09-30:** Unter
`output/four_models_shared_20pairs_validation_20260930/` liegen zwanzig
verschiedene 4-Takt-Cue-Beispiele, je mit Equal Power plus
`time_shared_mlp_v1`, `vocal_time_shared_mlp_v2`,
`tcn_bilstm_transition_control_v1` und
`variable_tcn_bilstm_transition_control_v1`. Alle fünf Labels pro Beispiel
nutzen dieselben Cues, 5-s/8-s-Kontexte und den gemeinsamen Peak-Gain. Die
20 Cues verteilen sich balanciert 3/3/4/5/5 über nur fünf Trackpaare; die
Trackpaare/Cues sind daher nicht als zwanzig unabhängige Tracktests zu zählen.
Smoke-Test, Export sowie 100 WAV-SHAs und alle vier Run-/Checkpoint-SHAs
bestanden; Testsplit blieb geschlossen. Player:
`output/four_models_shared_20pairs_validation_20260930/index.html`.
Die ältere, unveränderte Zwei-Paar-Ausgabe liegt weiter unter
`output/four_models_shared_2pairs_validation_20260927/`. Einschränkung:
Validation-Sets von Dataset-v1 und v2 teilen keine Trackpaare. Die drei festen
Modelle bleiben auf v1; die Variable-TCN erhält Feature-Protocol-2-Eingaben
mit v2-Trainingsnormalisierung für dieselben v1-Stimuli, ist dort aber
out-of-domain. Explorativer gemeinsamer Stimulus-Hörvergleich, kein
protokollgleicher Benchmark und nicht gemeinsam statistisch poolen.
Entscheidungen und Sackgassen: `docs/Bemerkungen.md`.

**Fortgesetzte PRIVE-Trainingsläufe am 2026-09-27:** Die beiden Läufe, die am
Vortag am 30-Epochen-Limit endeten, wurden aus ihren SHA-validierten letzten
Checkpoints fortgesetzt; beide besaßen Early Stopping (Patience 6). Vocal
`vocal_time_shared_mlp_v2`: Epoche 40, Best-Checkpoint Epoche 34, Validation-
Loss 0,32491, Status `early_stopped`; W&B-Run
[`1d4dc62c31b2985fb4e2`](https://wandb.ai/xamdoesmc-technische-universit-t-braunschweig/beatbridge/runs/1d4dc62c31b2985fb4e2).
Variable `variable_tcn_bilstm_transition_control_v1`: Epoche 40, Best-
Checkpoint Epoche 34, Validation-Loss 0,227169, Patience erreicht; W&B-Run
[`875000043610a50d8e24`](https://wandb.ai/xamdoesmc-technische-universit-t-braunschweig/beatbridge/runs/875000043610a50d8e24).
Dataset-/Cacheverträge blieben unverändert, Variable-`io_audit.json` bestätigt
`test_reads=0`. W&B enthält nur Metriken/Konfiguration; alle Gewichte blieben
lokal. Ausführung, Checkpoint-/Manifest-SHAs und der fehlgeschlagene erste
Online-Start stehen im aktuellen Block von `docs/Bemerkungen.md`.

**PRIVE-Trainingsläufe über alle Modellpfade am 2026-09-26:** Alle vier
registrierten Modelle haben abgeschlossene, getrennte W&B-Läufe. Das
`variable_tcn_bilstm_transition_control_v1` nutzt Dataset-v2
`2a124caf5625b4c8f683` (Manifest-SHA
`bf82442d82713bdb21b7f7429f7aee1845eda3c44abcd6d5f4fdca688a78a422`): Run
`875000043610a50d8e24`, 30 Epochen, beste Epoche 28, Validation-Loss 0,22794.
Der vollständige Waveformcache enthält 3.271 SHA-geprüfte Einträge; alle 2.649
Trainbeispiele sind enthalten, in Validation wurden 14 einzeln reportgebundene
Cache-Rejections ausgeschlossen (622 verbleibende Beispiele). `io_audit.json`
bestätigt `test_reads=0`. Die drei Format-1-Modelle wurden separat auf dem
kompatiblen Dataset `52bc9d1cebfd1b82d2ea` (SHA
`4708a8fa983354903759a934f48d36b6450510809773dda2a12f9408821886b7`)
trainiert: `time_shared_mlp_v1` Run `3295dc7d3ac5ee773b9c`, Val-Loss 0,41521;
`vocal_time_shared_mlp_v2` Run `1d4dc62c31b2985fb4e2`, Val-Loss 0,32583;
`tcn_bilstm_transition_control_v1` Run `4c2d8caa663d38f24385`, Val-Loss
0,32078. Das sind keine gleich-datasetigen Modellvergleiche. W&B enthält nur
Konfigurationen/Metriken; Gewichte und Audiodateien blieben lokal. Der
unabhängige Hörvergleich gegen Equal Power bleibt offen. SHA-Bindungen,
Rejected-Gründe und Sackgassen sind in `docs/Bemerkungen.md` protokolliert.

**PRIVE-Dataset-v2-Erweiterung am 2026-09-26:** Der neue unveränderliche
Datasetroot
`output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four`
ist mit Feature Protocol 2, Partial-Merge-v2-Raster und BS-RoFormer vollständig
exportiert. Dataset-ID `2a124caf5625b4c8f683`, Manifest-SHA-256
`bf82442d82713bdb21b7f7429f7aee1845eda3c44abcd6d5f4fdca688a78a422`.
Er enthält 3.285 Beispiele: 2 Takte 663 Train/159 Validation, 4 Takte
663/159, 6 Takte 663/159 und 8 Takte 660/159; Test jeweils 0. Alle 24
Datei-SHAs und 350 Pairmanifest-SHAs stimmen. Producer-Root-SHA ist
`26c5a98ee98bba43dc9e733da4e7b6180fb2e63fc19bb80882dd19da28a224e3`; die
Split-Mapping-SHA lautet weiterhin
`f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
Der ML-Loader hat alle zwölf Shards geprüft; Train-/Validation-Track-Leckage
und Testbeispiele: null. Der frühere unveränderliche Datasetroot
`output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run01`
bleibt unverändert: Dataset-ID `6be39995e91c0063a933`, 152 Beispiele (je
Länge 36 Train, 2 Validation und 0 Test). Der RoFormer-/Featurecache liegt
getrennt und ignoriert unter `output/`; Audiodateien oder Gewichte wurden
nicht committet.

Der korrigierte Voll-Producer Run 06 verwendete ausschließlich Train- und
Validationquellen und wurde aus seinen vollständigen Pairmanifesten
SHA-validiert. Zwei bereits geprüfte Validation-Smoke-Paare ergänzen die
Validationstichprobe.
Der frühere Run 02 mit offenem Testsplit-Gate wird nicht als Datasetquelle
verwendet. Ein erster Exportabschluss wurde von der Workspace-Sandbox beim
Anlegen seines temporären Datasetverzeichnisses blockiert; derselbe Export
lief nach gezielter Freigabe erfolgreich durch. Run-SHAs, Sackgassen,
Exportbefehl und Prüfdetails stehen in `docs/Bemerkungen.md`.

Waveformcache und das Training/Fine-Tuning von
`variable_tcn_bilstm_transition_control_v1` wurden am 2026-09-26 nachgeholt;
der vollständige Cache- und Trainingsaudit steht im aktuellen Block oben.
Der unabhängige Hörvergleich gegen Equal Power bleibt nachgelagert/offen.

**Lokaler Metrumfilter für Variable Candidate-v2 (2026-09-25):** Die globale
Ablehnung bei einzelnen Nicht-4/4-Beat-Tupeln ist aufgehoben. Nur die
vollständigen Pre-/Postfenster eines Kandidaten müssen jetzt in beiden Tracks
4/4 sein; andere Rasterabschnitte werden weder umgedeutet noch paarweit
abgewiesen. `unsupported_meter` wird nur zurückgegeben, wenn keine Länge einen
Kandidaten ergibt, auf beiden Seiten vollständige Fenster existieren und
mindestens eine Seite für jede mögliche Paarung kein gültiges 4/4-Fenster hat.
Der bestehende PRIVE-Datasetroot bleibt unverändert (weiterhin 152 Beispiele);
Producer und Export wurden nicht erneut ausgeführt. Regressionen für
Kandidatengenerator, Partial-Merge, Producer und Multi-Batch sind dokumentiert
in `docs/Bemerkungen.md`. Ein read-only In-Memory-Smoke findet nun lokale
Kandidaten in zwei realen Paaren (Birds → 02 ASCENSION: 10.602/5.841/3.306/1.575;
Inferno → VENGEANCE: 6.298/3.570/2.184/1.296 für 2/4/6/8 Takte); das dritte
Paar bleibt wegen Fallback-Provenienz gesperrt. Die Rohkombinationen sind keine
exportierten Trainingsbeispiele.

**Architekturstand der PRIVE-Dataset-v2-Erweiterung:** Der neue Ordner wird
nicht aus den vorhandenen PRIVE-Batchroots und nicht durch In-place-Erweiterung
des bestehenden Dataset-v2 übernommen. Der verbindliche Plan unter
[`PRIVE_DATASET_V2_EXTENSION_PLAN.md`](./PRIVE_DATASET_V2_EXTENSION_PLAN.md)
sieht einen neuen splitbewussten Partial-Merge-v2-Produzenten ohne Rendering,
eine für Recording-Groups vorbereitete und für bestehende Tracks unveränderte
Splitautorität, Feature Protocol 2, einen eigenen BS-RoFormer-
Featurecache, einen neuen unveränderlichen 2/4/6/8-Takt-Datasetroot, einen nur
für Train/Validation gebauten Variable-Waveformcache und Scratch-Training des
`variable_tcn_bilstm_transition_control_v1` vor. Testdaten bleiben bis zum
separat eingefrorenen Evaluation-Gate geschlossen. `src.variable_split_extension`,
der candidate-only `src.variable_producer`, Pair-Manifest-SHA-Prüfung, ein
versiegelter Waveformcacheindex und Model-only-Fine-Tune-Initialisierung sind
implementiert. Der PRIVE-Dataset-v2-Root ist nun real exportiert und anhand
seiner Manifest-, Datei- und Pair-SHAs sowie des ML-Loaders geprüft (Details
im aktuellen Ausführungsblock oben und im Plan). Variable-Waveformcache und
Training wurden am 2026-09-26 abgeschlossen; der unabhängige Hörvergleich ist
noch nicht ausgeführt.

**Unabhängiger Audit des variablen PRIVE-Top-3-Batches am 2026-09-23:**
Der vorhandene Batch
`output/batches/prive_top1000_variable_top3_20260922` ist auf Manifestebene
vollständig referenziert (321 Sources, 963/963 Pair-Manifeste, alle
Pair-Manifest-SHAs korrekt), aber kein technisch vollständiger Hörbatch.
958/963 ausgewählte Paare besitzen wegen Grid-/Metrum-Rejections keine
Kandidaten. Von den fünf kandidatentragenden Paaren scheitern vier am
Variable-Renderer wegen unterschiedlicher Source-/Target-Fensterlängen; die
einzige erzeugte WAV scheitert anschließend an der Render-Metrik, weil das
manifestierte Übergangsende 35.024 Samples außerhalb der Datei liegt. Daher
existiert kein gültiger Render-Score und nur eine eingeschränkt prüfbare
Hördatei. Root- und Source-Status `completed` bedeuten hier nur abgeschlossene
Verarbeitung, nicht Fehlerfreiheit; die fünf Fehler stehen ausschließlich in
den Pair-Manifests/-Summen. Die vollständige read-only Prüfung, Score- und
Rejection-Verteilungen sowie der konditionale Hörsetvorschlag stehen in
`docs/Bemerkungen.md`. Es wurde nichts neu gerendert oder trainiert.

**Verifizierter PRIVE-Top-1000-Baseline-Meilenstein am 2026-09-21:** Die
API-Inkompatibilität zwischen `src/multi_batch_render.py` und
`generate_and_render_batch` wurde behoben, indem die veraltete optionale
`cue_ranker`-Keyword-Übergabe entfernt wurde. Der rekursive Lauf mit
`feature_baseline_v3`, `equal_power`, 2-/4-Takt-Übergängen, BPM 145–165,
`analysis_workers=4` und `approximate_grid_policy=reject` endete mit Exit-Code
0. Das Root-Manifest unter
`output/batches/prive/_top1000/_baseline/_20260921_fixed/manifest.json`
verzeichnet 321 abgeschlossene Songpaare, 122 WAV-Renderings, keine Pair- oder
Renderfehler und 77 BPM-Ausschlüsse. Die vollständige Prüfung und der exakte
Befehl stehen in `docs/Bemerkungen.md`.

**Implementation-Kapitel am 2026-09-21:** Der Templateinhalt von
`overleaf/chapters/04_implementation.tex` wurde durch ein englisches,
evidenzbasiertes Kapitel ersetzt. Es beschreibt den manifestorientierten
Datenfluss von Analyse und Candidate-Erzeugung über Feature-/Waveformcaches,
Datasetexport und Training bis zu geblendeten Studienartefakten. Feature-
Protokoll 1 und 2, fester Full-Band-TCN-Renderer und variabler Vocal-Renderer,
Default-Feature-Ranker und nur synthetisch verifizierter Learned-Ranker sowie
real ausgeführte, audit-only und geplante Komponenten bleiben explizit
getrennt. Der aktuelle Nutzerworkflow ist korrekt als CLI-, Notebook- und
lokaler HTML-Workflow beschrieben; GUI, manuelle Korrekturstudie,
Multi-Track-Assembly und finaler Projekt-Export bleiben TODO.

Lokale Dataset-/Runmanifeste stützen die Format-1-Aussagen. Format-2- und
spätere Controllerzahlen werden wegen fehlender Primärartefakte in diesem
Checkout nur als dokumentierte Audit-Evidenz bezeichnet. Die bestehende
BS-RoFormer-Zitation `lu2024bsroformer` wurde wiederverwendet; die
Bibliographie blieb unverändert. Ein isolierter Doppelbuild erzeugte ein
zehnseitiges Kapitel-PDF ohne LaTeX-Fehler, undefinierte Referenzen oder
Overfull-Boxen; vier repräsentative Seiten wurden visuell geprüft. Der
Gesamtbuild scheitert weiterhin vor Kapitelinklusion an fehlendem
`ngerman.ldf`. Fehlversuche und genaue Befehle stehen in `Bemerkungen.md`.

**Methodology-/System-Design-Kapitel am 2026-09-16:**
Der verifizierte deutsche Entwurf `docs/masterarbeit/methodik.tex` wurde als
zusammenhängendes englisches Kapitel in
`overleaf/chapters/03_mainPart.tex` übertragen. Das Kapitel trennt
Forschungsdesign und Evidenzstufen, SHA-basierte Splits, Grid-/Alignment-
Verträge, beat-synchrone Repräsentation, Candidate-Baselines und den nur
synthetisch verifizierten Cue-Ranker, die inkompatiblen Controller-/Renderer-
Familien, Proxy-Objectives, Training, objektive und perzeptuelle Evaluation
sowie bekannte Grenzen. Mathematische Definitionen und bestehende
Overleaf-Labels bleiben erhalten; fehlende Rechte-/Korpusdaten,
Format-2-Primärartefakte, Repräsentationsversuch, realer Ranker, 1-/3-Takt-
Fälle, gelernte Controller-Hörstudie und Nutzer-/Tanzevaluation bleiben als
LaTeX-TODO sichtbar.

Die Format-1-Datasetzahlen wurden gegen die zwei lokalen Manifeste und
Trainingseinstellungen/Parameterzahlen gegen die drei lokalen Runmanifeste
abgeglichen. Format-2-Zahlen und spätere TCN-/RoFormer-/Variable-Runs werden
ausdrücklich nur als dokumentierte Audit-Evidenz geführt, weil ihre
Primärartefakte in diesem Checkout fehlen. Der einzige neue Zitationsschlüssel
im Kapitel ist der bereits vorhandene und zuvor geprüfte
`lu2024bsroformer`; die Bibliographie wurde nicht verändert. Whitespace-,
Klammer-, Label- und Zitationschecks bestanden. Der Gesamtbuild scheitert
weiterhin vor Kapitelinklusion an fehlendem `ngerman.ldf`. Ein isolierter
Kapitelbuild mit `amsmath`, `amssymb` und `booktabs` erzeugte dagegen ein
warnungsfreies 16-seitiges Prüf-PDF ohne Overfull-Boxen; die beiden Tabellen
wurden über Ghostscript gerendert und visuell geprüft. Details einschließlich
aller Fehlversuche stehen in `Bemerkungen.md`.

**Claim-Level-Literaturaudit am 2026-09-16:**
`overleaf/chapters/02_relatedWork.tex` ist jetzt als technischer Vergleich
statt als Literaturkatalog aufgebaut. Für automatische Sequenzierung,
Cuepoint-Auswahl und Übergangssysteme, gelernte Controls und differenzierbare
Audioverarbeitung, MIR-Frontends, selbstüberwachte Musikrepräsentationen,
Kompatibilitätslernen und Evaluation werden jeweils Problem, Supervision,
Output, Auswertung und Abgrenzung zu BeatBridge benannt. Die Gap-Aussage ist
auf das Lernen zeitabhängiger interpretierbarer Controls für ein festes
Cue-Paar über einen getrennten differenzierbaren Renderer und ein fixes
Proxy-Objective ohne Ground-Truth-Controlkurven oder menschliche Qualitätslabels
begrenzt. DJ AI (2025) und die Princeton-Senior-Thesis von Hein (2025) wurden
als neuere direkte Arbeiten ergänzt; deshalb wird weder die erstmalige Nutzung
von Musik-SSL in einer Übergangspipeline noch eine allgemeine Neuheit der
Control-Vorhersage behauptet. Die Bibliographie enthält nun nur die 23 im
Kapitel verwendeten Primärquellen und korrigierte Publikationsdaten. Offene
Repräsentations- und Perzeptionsevidenz bleibt als LaTeX-TODO erhalten. Der
lokale Gesamtbuild bleibt wegen fehlendem `ngerman.ldf`, `biblatex.sty` und
Biber blockiert; isolierte Syntax-, BibTeX-, Schlüssel- und Diff-Prüfungen sind
in `Bemerkungen.md` dokumentiert.

**Thesis-Blueprint am 2026-09-16:**
[`masterarbeit/THESIS_BLUEPRINT.md`](./masterarbeit/THESIS_BLUEPRINT.md)
leitet aus der verbindlichen Aufgabenstellung und dem verifizierbaren
Repository-Stand eine englische Argumentations- und Evidenzstruktur ab, ohne
Thesis-Prosa zu ersetzen. Das Dokument enthält eine primäre Forschungsfrage
mit drei Teilfragen, Problem und Scope, getrennte wissenschaftliche und
Software-Engineering-Beiträge, eine Claim-to-Evidence-Matrix, die vollständige
Kapitel-/Abschnittsplanung und eine Negativliste derzeit unbelegter Aussagen.
Der wissenschaftliche Kern ist das Lernen zeitabhängiger interpretierbarer
Mixing-Controls ohne Ground-Truth-Kurven über einen differenzierbaren Renderer
und ein pro Lauf eingefrorenes Proxy-Objective; Cuepoint-Auswahl bleibt ein
getrenntes vorgelagertes Problem.

Der Blueprint trennt den festen Vier-Takt-Pfad vom variablen
2/4/6/8-Takt-Pfad und hält 1/3 Takte, Repräsentationsversuch, reale
Cue-Ranker-Evidenz, GUI/Endexport sowie Korrekturaufwand und Tanz-Nutzbarkeit
als offene Aufgabenstellungsanforderungen fest. Drei lokal vorhandene reale
Control-Runs wurden über Manifest, History, Datasetbindung und neun
Run-Dateihashes geprüft; vier abgeschlossene historische Hörsätze wurden auf
konsistente Bewertungs-/Ergebniszahlen geprüft. Die später dokumentierten
TCN-/Variable-Runs und September-Hörsätze fehlen in diesem Checkout und sind
deshalb als frühere Audit-Evidenz statt als frisch geprüfte Primärartefakte
klassifiziert. Das ist kein Hörqualitätsnachweis für gelernte Controller.
Overleaf-/Thesis-Prosa und Bibliographie wurden in dieser Aufgabe nicht
verändert; LaTeX wurde nicht neu kompiliert. Ein unabhängiger lesender Review
führte zu drei Korrekturen im Plan (Hörartefaktstatus, explizite
Analyse-/GUI-Anforderung und Titelstatus) und fand danach keine weitere
umsetzungsrelevante Inkonsistenz. Details stehen in
`Bemerkungen.md`.

**LaTeX-Strukturaudit am 2026-09-14 (aktueller lokaler Dateistand):**
Die Overleaf-Dateien und eine versionierte `.gitmodules` mit Overleaf-URL
sind jetzt lokal vorhanden; der ältere Leerordner-Befund direkt darunter
beschreibt nicht diesen Dateistand. Eine neue Prüfung der Remote-Erreichbarkeit
oder eines frischen Checkouts wurde nicht durchgeführt. Zu Beginn des
Reaudits am 2026-09-14 verwendete der Live-Checkout `LR`; er ist jetzt auf
`MA, twosided` korrigiert. Der erhaltene Vorher-Snapshot vom 2026-09-13
enthält dagegen bereits `MA`; wann und wodurch der Live-Checkout
zwischenzeitlich auf `LR` wechselte, wurde nicht nachgewiesen. Beide
Abstracts, sieben getrennte
Hauptkapitel und der Anhang sind aktiviert; Template-Beispiele wurden durch
englische Gliederungen und konkrete Evidenz-TODOs ersetzt. Der englische
Titel bleibt unverändert, weil die Aufgabenstellungs-PDF nur einen abweichenden
deutschen Titel und keinen registrierten englischen Wortlaut belegt.
Der Audit unter [`masterarbeit/THESIS_SETUP_AUDIT.md`](./masterarbeit/THESIS_SETUP_AUDIT.md)
hält Struktur, Quellen und offene Anforderungen fest. Dies ist keine neue
Ergebnis- oder Literaturfreigabe. Die statische Strukturprüfung und der
unabhängige Strukturreview bestanden. Der lokale `pdflatex`-Versuch scheiterte
an fehlendem `ngerman.ldf`; auch `biblatex.sty` und Biber fehlen. Es entstand
kein PDF; ein vollständiger Build und die visuelle Prüfung bleiben offen.
Prüfungen und der erneute Abgleich des zuvor widersprüchlichen Live-Zustands
stehen in `Bemerkungen.md`.

**Repository-/Overleaf-Audit am 2026-09-13:** Der Hauptbranch ist nach einem
frischen Fetch exakt mit `origin/main` synchron. Der Pfad `overleaf` wurde im
Commit `95f7e1d` jedoch nur als Gitlink auf den fremden Commit
`6469dfac57062f654c0d9b4d5b87b6e2f6f9e45d` aufgenommen. Da keine
`.gitmodules`-Datei mit Repository-URL versioniert ist und das Commitobjekt im
Hauptrepository nicht existiert, kann ein frischer Checkout die dort erwarteten
Dateien wie `CGThesis.tex`, `meta.tex` und die Kapiteldateien nicht beziehen;
der lokale Ordner ist auf diesem Rechner leer. Der Push des Hauptbranches ist
damit angekommen, die Overleaf-Arbeit aber nicht reproduzierbar im
BeatBridge-Repository enthalten. Vor weiteren Thesis-Arbeiten muss der Inhalt
entweder als normale Dateien eingecheckt oder als korrekt konfiguriertes und
separat erreichbares Submodule veröffentlicht werden.

**GUI-Zielbild definiert und fuer Mehrtrack-Projekte praezisiert am
2026-09-10:**
[`GUI_SPECIFICATION.md`](./GUI_SPECIFICATION.md) beschreibt den spaeter
implementierbaren Mehrtrack-Workflow: Ein Projekt darf beliebig viele Tracks
und Abschnittsinstanzen in einer linearen Mashup-Sequenz enthalten; jeder
einzelne Uebergang bleibt strikt ein gerichtetes Songpaar. Der Paar-Editor
zeigt deshalb immer nur die beiden Spuren der aktuell gewaehlten Sequenzkante.
Die Spezifikation umfasst ausserdem die DAW-artige Timeline,
Cuepoint-/Constraint-Bearbeitung, synchrone
Datenvisualisierung, Baseline-/Modellvergleich, Zustands- und Fehlerkonzept
sowie Datenbindung an die vorhandenen versionierten Manifeste. Die Umsetzung
ist bewusst in manifestbasierten Review-MVP, interaktiven Paar-Editor,
Mashup-Assembly und Evaluationsmodus gestuft. Das Bild unter
[`gui-mockups/beatbridge-daw-data-concept-v1.png`](./gui-mockups/beatbridge-daw-data-concept-v1.png)
ist visuelle Referenz, aber kein fachlicher oder pixelgenauer Vertrag. Es wurde
noch kein GUI-Code implementiert und kein GUI-Test ausgefuehrt.

**Thesis-Strukturabgleich am 2026-09-09:** Die verbindliche Aufgabenstellung
`angepasste_aufgabenstellung_masterarbeit.pdf` wurde gegen den Repository- und
Overleaf-Stand geprüft. Die englischen Kapitelgerüste gewichten nun gelernte
beziehungsweise verwendete Audio-Repräsentationen, Übergangsmetrik und
-Ranking, Control-basierte Übergangsgenerierung sowie GUI-/Nutzerworkflow und
Evaluation des manuellen Korrekturaufwands getrennt. Offene Evidenz ist direkt
in den TeX-Gerüsten als `TODO` markiert. Besonders offen bleiben reale
Embedding-/Cue-Ranker-Experimente, eine minimale GUI, End-to-End-Mashup-Export,
die in der Aufgabenstellung genannten 1-/3-Takt-Fälle und eine Evaluation der
Nutzbarkeit für Tanzperformances. Die vorhandenen 6-/8-Takt-Versuche sind als
zusätzliche Generalisierung eingeordnet, nicht als Ersatz für den primären
Umfang von ein bis vier Takten.

**Artefaktabgleich am 2026-09-07 (Repository-/Modellübersicht):** Die lokalen
Variable-TCN-Runmanifeste dokumentieren mittlerweile abgeschlossene Läufe mit
20 Epochen (`variable_tcn_bilstm_waveform_v2_full_20260821`) beziehungsweise
29 Epochen (`variable_tcn_bilstm_v2_wandb_20260826`). Die jeweiligen minimalen
History-Validation-Losses liegen in Epoche 14 bei `0.24643995364507038` und
Epoche 23 bei `0.24559853225946426`. History- und Best-Checkpoint-SHAs stimmen
in beiden Runs mit ihren Manifesten überein. Frühere Zwei-Epochen-Smoke-
Aussagen beschreiben damit nur den damaligen Stand. Dies ist keine neue
Hörqualitätsfreigabe und kein Nachweis eines 100-Epochen-Laufs. Details und
die Abgrenzung des Variable-Vocal-Renderers vom festen Full-Band-TCN stehen
in `ML_MODEL_CURRENT_STATE.md`; die Prüfung steht in `Bemerkungen.md`.

**Verifiziert am 2026-09-04 (separate Beispiele für inkompatible
Modellpfade):** Das Variable-TCN/BiLSTM-v2 besitzt jetzt einen eigenen
geblendeten Hörsatz auf seinem Dataset-/Feature-/Waveform-Protokoll 2. Unter
`output/control_studies/blind_variable_tcn_lengths_20260904/` liegen je ein
Validation-Beispiel für 2/4/6/8 Takte, jeweils Variable-TCN-Best-Checkpoint
gegen eine identisch gerenderte Equal-Power-Referenz. Alle 8 WAVs sind
SHA-geprüft, finite, paarweise samplegleich, auf Peak ≤ 0,98 begrenzt und
verwenden die Cache-Samplerate 11.025 Hz; sie enthalten bewusst nur das
ausgerichtete Übergangsfenster. Die Vergleichszentrale
`output/control_studies/model_comparison_hub_20260904/index.html` verlinkt
diesen Satz und den Dataset-v1-Mehrmodellvergleich getrennt. Zusätzlich zeigt
sie die 2/4/6/8-Takt-Metriken des ausschließlich synthetischen Cue-Ranker-
Smokes als nicht hörbare Funktionsdemo mit expliziter Warnung vor einer
Qualitätsinterpretation. Die fokussierte Regression bestand mit `27 passed in
12.98s`; ein kontrollierter Browser-DOM-Test lokaler `file:`-URLs blieb durch
die Browser-Sicherheitsrichtlinie blockiert und ist manuell zu prüfen.

**Verifiziert am 2026-09-04 (geblendeter Hörvergleich der kompatiblen
Control-Modelle):** Der neue Exporter
`src.evaluation.all_models_control_study` rendert auf identischen
Dataset-v1-Validation-Kandidaten Equal Power sowie je einen SHA-geprüften
repräsentativen Best-Checkpoint von `time_shared_mlp_v1`,
`vocal_time_shared_mlp_v2` und dem Full-Band-
`tcn_bilstm_transition_control_v1`. Cuepoint, Kontext und Peak-Gain sind je
Paar gemeinsam; A/B/C/D werden deterministisch neu gemischt und die
Methodenzuordnung bleibt ausschließlich im Antwortschlüssel. Der fertige Satz
unter `output/control_studies/blind_all_models_validation_20260904/` enthält
5 Paare und 20 geprüfte Float32-WAVs bei 44,1 kHz. Alle Audio-SHAs, endlichen
Samples, paarweisen Shapes und Peaks ≤ 0,98 wurden bestätigt; die fokussierte
Regression bestand mit `21 passed in 8.88s`. `index.html` bietet lokale
Audioplayer, persistente Eingaben und Ratings-Download. Die Auswertung ist
noch offen. Variable-TCN v2 bleibt wegen Dataset-/Feature-Protokoll 2 in einem
separaten Vergleich; die ausschließlich synthetischen Cue-Ranker wählen
Cuepoints und sind keine direkt renderbare Control-Variante.

**Frischer unabhängiger Cuepoint-Ranker-Audit am 2026-08-27 (nur
synthetisch, Realpilot weiterhin gesperrt):** Der vollständige aktuelle Diff,
die Cue-Ranker-Protokolle und die Änderungen der vorigen Tasks wurden gegen
die gesamte Kette Pair-Index → Candidate-v2-Universe → eingefrorener Teacher
→ Resolver/Waveformcache → Labels → train-only-Normalizer → Format-3 →
gruppierter Ranker → Offline-W&B → Learned-Inferenz → Render-Backfill
geprüft. Vier klar reproduzierte Grenzdefekte sind behoben und regressions-
getestet: `WandbLogger.finish()` verwendet nun die Instanzkonfiguration;
Format-3 verweigert eine fremde Normalizer-Universe-SHA; die Inferenz prüft
die tatsächlich gelesene Normalizerpayload einschließlich Scope-, Universe-,
Source- und Track-SHAs; und der fortsetzbare Teacher-Candidate-Cache bindet
jede Zeile nun an kanonische Label- und Provenance-SHAs (Format 2) und bricht
bei Manipulation vor jedem Finalshard fail-closed ab.

Der neue dauerhafte synthetische E2E-Smoke belegt Pair-Index bis zweimal
deterministische Learned-Inferenz: Candidate-v2 mit echten 4/4-Metadaten und
`approximate_grid_policy=reject`, ein `guard_rejected`-Anker, train-only
Format-3-Normalisierung, ausschließlich vorhandene Featurecache-Attrappen,
Offline-Epoche 1 und SHA-geprüftes `weights_only`-Resume auf Epoche 2 sowie
Manifest-/History-/Best-/Latest-SHAs. Der getrennte Teacher-Unterbrechungs-
und Resume-Test belegt Cache-Hits nach Failure-/Candidate-Budget-Abbruch.
Die fokussierte Kette bestand mit `72 passed, 6 warnings in 27.62 s`; die
vollständige Suite lieferte maschinell im finalen temporären JUnit-Protokoll `266
tests, 0 failures, 0 errors, 0 skipped in 48.370 s`. Der wortgetreu
angeforderte Optionsaufbau `python -m pytest -q -B` ist technisch ungültig,
weil `-B` eine Interpreteroption ist; die semantisch identische, erfolgreiche
Form war `python -B -m pytest -q -p no:cacheprovider`. Alle Testläufe,
einschließlich der abgewiesenen Variante, stehen in
[`Bemerkungen.md`](./Bemerkungen.md).

Damit besteht eine **bedingte Codefreigabe für den synthetisch verifizierten
Pfad**, aber **keine Freigabe eines realen Pilotlaufs**. Vor dessen Start
müssen ein testfrei veröffentlichter Pair-Index/Universe-Root samt
Split-Autorität, ein abgeschlossener Variable-TCN-Best-Checkpoint als
vollständiger Teacher-Release, ein exakt daran gebundener train-only
Normalizer, vollständige und SHA-verifizierbare Feature-/Vocal-/Analysis-
und Waveformcache-Artefakte sowie die festgelegte Rubber-Band-
Backendprovenienz vorliegen. Erst danach sind ein ausdrücklich autorisierter
Train-/Validation-Labeling- und Offline-Trainingslauf sowie eine unabhängige
musikalische Qualitäts-/Agreementprüfung zulässig. Weder Test-Pair-Manifeste,
Testaudio, Testfeatures, Testcounts noch Testloader wurden im Cue-Ranker-Pfad
geöffnet oder materialisiert; reales Teacher-Labeling und reales Training
blieben ungestartet.

**Verifiziert am 2026-08-26 (Cuepoint-Ranker-W&B-Integration, nur lokal):**
`train-cue-ranker` unterstützt `--wandb-mode disabled|offline|online` sowie
Projekt, Entity, Gruppe, Tags und Run-Name. Verschachtelte Train-/Validation-
Rankingmetriken werden deterministisch in skalare W&B-Keys abgeflacht; die
Metriken umfassen global und für 2/4/6/8 Takte sämtliche Baseline-, Ranker-
und Oracle-Felder. Der Runner startet, loggt epochweise und beendet W&B auch
auf kontrollierten Fehlerpfaden. Ranker-Artefakte werden explizit aus dem
Run-Root (`best.pt`, `latest.pt`, `history.json`, `manifest.json`) veröffentlicht;
Control-Runner behalten `output/checkpoints/...`. Ein synthetischer Offline-
CLI-Smoke und die vollständige Suite liefen erfolgreich mit `261 passed, 8
warnings`; kein Login, Upload, reales Training oder bestehender Run wurde
verändert.

_Stand: 2026-08-26_

**Verifiziert am 2026-08-26 (realer Format-3-Cue-Ranker-Trainingspfad,
nur Synthetik):** `CueRankerGroupedDataset` verwendet ohne injizierte
Testseams nun einen produktiven, fail-closed Featureloader. Er verfolgt die
Dataset→Universe→Teacher-Label-Kette über Manifest-/Shard-SHAs, akzeptiert
nur die bestehende, passend gehashte Feature-Protocol-2-Cachepayload und
extrahiert Fenster, Globalfeatures und train-only Normalisierung exakt wie
der Teacher. T=16/32/48/64, 54 Featurekanäle, 16 Globals, length condition,
Grid-Kontext, volle Universumsgröße und endliche Float32-Werte sind geprüft.
Der Export bindet ein eigenständiges train-only Normalizerartefakt samt
stats_id/Input-SHAs an die Datasetprovenienz. Der offizielle Einstieg
`python -m src.ml train-cue-ranker` konstruiert ausschliesslich explizite
Train-/Validation-Loader; Batchgröße, Epochen, Seed, Device, Runpfad und
SHA-geprüftes `weights_only`-Resume sind verfügbar, ein Testsplit weder
Option noch Codepfad. Die CPU-Synthetik inklusive echter Loader-Training- und
Validation-Epoche, Manipulationsfällen und CLI bestand mit `48 passed, 6
warnings`; kein CUDA- oder Realtraining wurde gestartet.

**Verifiziert am 2026-08-26 (produktionsfähiger Cue-Ranker-Teacher-Pfad,
nur Synthetik):** `python -m src.ml seal-cue-ranker-teacher` verlangt jetzt
einen explizit übergebenen, abgeschlossenen Variable-TCN-Run und akzeptiert
allein dessen hashgebundenen `best_checkpoint` per `weights_only=True`. Der
Release bindet Run/Checkpoint, State-dict-Schema, Modellvertrag, Renderer,
Objective v5 und Alignment zusätzlich mit einzelnen SHA-Verträgen sowie
Render-Guard, trainings-only Normalizer, Backend, Code und Umgebung.
`python -m src.ml label-cue-ranker-teacher` verarbeitet
nur SHA-geprüfte Train-/Validation-Universe-Shards gegen eine explizite
Split-Autorität. Der neue Resolver verwendet die bestehenden Feature-/Vocal-
Artefakte und exakt `local_grid_target_to_source_v1`; ein eigener
unveränderlicher Waveformcache und ein atomarer Candidate-Labelcache erlauben
verifizierte Resume-Hits. `guard_rejected` bleibt ein negativer Anker,
technische Fehler bleiben aus dem Loss. Die synthetische Regression bestand
mit `44 passed, 4 warnings`; Testsplit, reales Teacher-Release und großer
Labeling-Lauf blieben unmaterialisiert. Für einen echten Pilot fehlen noch
ein ausdrücklich veröffentlichter trainings-only Normalizer, gebundene
Rubber-Band-Backend-Provenienz sowie ein freigegebener echter Universe-Root.

**Verifiziert am 2026-08-26 (produktionsfähiger Cue-Ranker-Datenanfang):**
Der additive Einstieg `python -m src.features build-cue-ranker-pair-index`
erzeugt aus einem Producer-Root-Manifest und der SHA-geprüften Split-Autorität
einen reproduzierbaren, testfreien Pair-Index. Der Batch-Producer schreibt
dafür geordnete Source-/Target-Audio-SHAs, Pair-Manifest-SHA, Candidate-v2-
Generator sowie die vollständige Request-Konfiguration. Der Index delegiert
seine Vertragserstellung an `write_cue_ranker_pair_index()` und bindet Root-
Manifest-, optionale Dataset-Manifest- und Split-Map-SHAs. Der Universe-CLI
verifiziert diese Kette vor dem Öffnen eines gleichsplitigen Pair-Manifests;
Test-Pair-Manifeste werden schon durch die Split-Autorität ausgesiebt.
Historische Roots ohne Producer-Provenienz werden fail-closed abgelehnt.
Die fokussierte synthetische Datenanfangs-/Regression bestand mit `67 passed,
2 warnings`; kein großer realer Universe-Lauf, kein Training und kein
Testsplitzugriff wurden gestartet.

**Verifiziert am 2026-08-25 (frischer unabhängiger Cuepoint-Ranker-Audit):**
Der Review begann mit gezielten synthetischen Vertrags-/Negativtests und lief
anschließend vollständig mit `239 passed, 4 warnings in 36.37s` (Exit-Code 0;
`-B -p no:cacheprovider`). Vier eindeutig reproduzierte Fehler wurden
additiv behoben: (1) `guard_rejected` wird nun trotz endlicher hoher
Objective-Utility immer als relativer negativer Teacher-Anker in Loss **und**
Validation-Metriken behandelt; (2) der Loader übergibt für
`candidate_context_v1` die vollständige Universumsgröße statt nur die
gelabelte Stichprobengröße; (3) Learned-Top-K versucht bei einem vollständigen
Renderfehler deterministisch den nächsten Modellkandidaten und manifestiert
Auslassung/Backfill; (4) der Teacher-Sealer/-Verifier/-Loader akzeptiert nur
den hashgebundenen `best_checkpoint` eines abgeschlossenen Variable-TCN-Runs
mit passendem Checkpointvertrag. Testsplit und reales Training blieben
ungeöffnet beziehungsweise ungestartet.

Der größere reale Validation-Lauf ist **noch nicht freigegeben**: Es fehlt ein
testfrei veröffentlichter echter Format-3-Teacher-Snapshot samt sicherem
End-to-End-Feature-/Waveformresolver; außerdem fehlen die im Architekturplan
vorgesehenen `src.ml`-CLIs für Teacher-Labeling und Ranker-Training. Die
vollständige Testdokumentation einschließlich vorheriger Fixture-Korrekturen
und Warnungen steht in [`Bemerkungen.md`](./Bemerkungen.md). Teacher-Agreement
bleibt ohne unabhängige Renderer-/Hörstudie kein Musikqualitätsnachweis.

**Verifiziert am 2026-08-25 (additive Batch-/CLI-Integration von
`learned_cue_ranker_v1`):** Batch und Multi-Batch akzeptieren explizit
`ranking_method=feature_baseline_v3|learned_cue_ranker_v1`; ohne Auswahl bleibt
`feature_baseline_v3` der Default. Der Learned-Pfad lädt ausschließlich einen
SHA-geprüften abgeschlossenen Run mit Best-Checkpoint und ein SHA-gebundenes
Format-3-Dataset mit Teacher-/train-only-Normalizervertrag. Er sortiert alle
bereits akzeptierten Candidate-v2-Entries deterministisch nach Modellscore,
übergibt nur `selection_candidate_ids` an die unveränderten Renderer und
schreibt additiv `cue_ranking` mit Modell-/Format-/Checkpoint-/Dataset-/Teacher-
Provenienz, Scores, Preflight und Backfill. `candidate_ranking` bleibt die
historische `feature_baseline_v3`-Struktur. Fehlende/ungültige Runs, unzulässige
Candidate-Formate, Fallback-Grids und `allow`-Provenienz werden klar abgelehnt;
es gibt keinen stillen Ranking-Fallback. Die fokussierte synthetische Suite
bestand mit `40 passed, 2 warnings`; kein Testsplit und kein umfangreicher
Realbatch wurden verwendet.

**Verifiziert am 2026-08-25 (learned_cue_ranker_v1, reproduzierbare
Train-/Validation-Auswertung):** Der gruppierte Runner protokolliert jetzt
epochweise Listwise-Ranking-Loss, Top-1-/Top-K-Teacher-Agreement, NDCG,
Score-Korrelation und Top-1-Teacher-Utility, jeweils global sowie getrennt
für 2/4/6/8 Takte. Validation vergleicht auf demselben eingefrorenen
Label-Snapshot deterministischen Zufall, `feature_baseline_v3`, BPM-only,
Harmonie-only, Ranker und Teacher-Oracle. Der Loader lässt die vollständige
Universumsprovenienz auditierbar, führt aber ausschließlich die eingefrorene
gelabelte Stichprobe mit positiver Einschlusswahrscheinlichkeit in den
IPW-Loss. Ein CPU-Synthetik-Smoke mit allen vier Längen lief eine Epoche;
Manifest-, History-, Best- und Latest-SHAs wurden maschinell bestätigt und
der Testsplit blieb `sealed_not_materialized`. Teacher-Agreement ist
ausdrücklich kein Hörqualitätsnachweis. Es wurde kein Produktionsdefault
geändert und kein realer Train-/Validation-Smoke gestartet, weil noch kein
testfrei veröffentlichter Format-3-Teacher-Snapshot mit echten Labels
vorliegt.

**Verifiziert am 2026-08-25 (learned_cue_ranker_v1, nur Modell-/Trainingsstufe):**
Der additive Cue-Ranker ist auf dem freigegebenen Format-3-Gruppendataset
implementiert. `CueRankerTemporalModel` verwendet den planfestgelegten
geteilten A/B-TCN, globale Features, die separate `length_condition`,
`candidate_context_v1`, Grid-Embeddings, masked Mean/Max-Pooling und einen
skalaren Candidate-Score. Der gruppierte Runner verwendet ausschließlich
explizit gelieferte Train-/Validation-Loader, den maskierten
IPW-Soft-Target-Listwise-Loss und behandelt Ein-Kandidaten-Gruppen als
insufficient support. Initialisierung/Training sind deterministisch; Best- und
Latest-Checkpoints werden atomar geschrieben und vor dem einzigen
`weights_only=True`-Resume-Load SHA-geprüft. Die synthetische kombinierte Suite
bestand mit 41 Tests und 2 bekannten, bestehenden PyTorch-CUDA-Warnings.
Die zuvor isolierte Modell-/Trainingsstufe ist nun additiv über
`batch_render.py` und `multi_batch_render.py` an den verifizierten
Ranker angebunden; Auswahl bestehender Candidate-IDs und alle Control-Modelle
bleiben unverändert. Es wurde kein reales Training und kein Testsplitzugriff
ausgeführt.

**Verifiziert am 2026-08-25 (Cue-Ranker Dataset-/Teacher-Stufe, nur
Synthetik):** Der neue additive Format-3-Pfad liegt getrennt neben
Candidate-/Dataset-v1/v2. Ein SHA-geprüfter `pair_index` filtert ausschließlich
gleichsplitige Train-/Validation-Paare, bevor Pair-Manifeste geöffnet werden;
es gibt keinen Legacy-Discovery-Fallback und keinerlei Test-Artifact,
Testcount oder Testloader. Der vollständige v2-Kandidatenindex bildet stabile,
nichtzirkuläre Gruppen-IDs aus den vollen Cue-/Grid-Identitäten, behält alle
akzeptierten Kandidaten statt `feature_baseline_v3`-Top-K und führt dessen
Wert nur als Baseline/Stratifizierung. Das stratifizierte Sampling, variable
Ragged-Gruppen, Einschlusswahrscheinlichkeiten und die fehlende
candidatespezifische Hard-Negative-Nachauswahl sind manifestiert.

Die Teacher-Stufe akzeptiert nur einen SHA-gebundenen, eval-only Release mit
`weights_only=True`, Objective-v5-/Renderer-/Alignment-/Normalizer- und
Backendvertrag. Guard-Rejections und technische Failures werden je Kandidat
auditierbar geschrieben und blockieren andere Gruppen nicht. Der finale
Datasetexport schreibt ausschließlich Train/Validation, gruppierte Indexe,
Teacher-Label und Trainings-only-Normalizerprovenienz. Die fokussierte
synthetische Suite bestand mit 6 neuen Tests; 17 bestehende Candidate- und
Dataset-v2-Tests bestanden separat. Es gab weder reale Materialisierung noch
Training noch Zugriff auf Test-Audio/-Manifeste. Die damalige Dataset-/Teacher-
Stufe war zu diesem Zeitpunkt noch nicht an Batch-Rendering angebunden; die
heutige additive Integration steht im aktuellen Verifizierungsblock oben.

**Verifiziert am 2026-08-21 (Variable-v2 Waveform-Alignment, Cache und CUDA-
Smoke):** Der blockierende Source-/Target-Samplelängenfehler ist additiv durch
den versionierten Vertrag `local_grid_target_to_source_v1` gelöst. Die
Source-Griddauer ist die Autorität; das Target-Preroll wird mit einem
tonhöhenerhaltenden Rubber-Band-Backend auf diese lokale Dauer transformiert.
Die tatsächliche lokale Ratio wird aus den gespeicherten Gridgrenzen berechnet;
die globale BPM-Ratio bleibt als Diagnosewert erhalten. Ein isoliertes
Rubber-Band-Fenster mit einem Rohrest von 3.423–3.640 Samples wurde korrekt
abgelehnt; ein Guard-Kontextpfad liefert exakt grenzbezogene Fenster ohne
Cropping-/Padding-Fallback.

Der unveränderliche Cache unter
`output/ml_cache/variable_bridge_waveform_v2` bindet Dataset-ID,
Dataset-Manifest-SHA, Example-ID, Länge, Alignment-Vertrag, Grid-/Audio-/Stem-
und Payload-SHAs. Er enthält 468/468 reale Train-/Validation-Beispiele:
420 Train und 48 Validation, je 105/12 für 2/4/6/8 Takte. Alle vier
Waveforms sind finite Float32-Stereoarrays mit 11.025 Hz und exakt gleicher
Shape; 377 Einträge nutzten Guard-Kontext, 91 direkt. Die lokale Ratio reicht
über alle Längen von 0,935849… bis 1,102564…; es gab 0 Rejects. Der Testsplit
wurde weder materialisiert noch geöffnet.

Der neue CLI-/Loaderpfad `cache-variable-waveforms` und
`train-variable-tcn-bilstm` verwendet nur vollständige Cache-Hits und
`VariableLengthBatchSampler`. Der echte CUDA-Smoke auf `cuda:0` lief eine
Epoche (Train/Validation `0,310062/0,260667`), der Resume lief auf Epoche 2
(`0,303663/0,265043`), jeweils mit 468 Cache-Hits und W&B disabled. Der
CUDA-/Checkpoint-Audit bestätigte eine RTX 5070 Ti, finite Losses/Gradienten,
gültige Checkpoint-SHAs, Per-Length-Validation und Controls
`(16,10)/(32,10)/(48,10)/(64,10)`. Die vollständige Suite besteht mit
`209 passed, 4 warnings in 38.06s`. Ein 100-Epochen-Lauf wurde nicht
gestartet.

**Verifiziert am 2026-08-20 (additiver Librosa-/aufTAKT-Merge-v2-Audit):**
Der neue `PartialPreAnalysis`-Pfad mit
`librosa_auftakt_monotonic_partial_v2` wurde auf drei realen Tracks unter
neuen Analyse-Roots geprüft. `LESS_IS_MORE` (533 Librosa-/632 aufTAKT-Beats,
527 monotone eindeutige Matches, Coverage 0,988743/1,0, 131 vollständige
Takte, längster Block 93) und `HELP_LESS` (451/491, 449 Matches, Coverage
0,995556/1,0, 113 vollständige Takte, längster Block 113) erhalten
`grid_source=auftakt_matched_to_librosa_partial_v2`, `fallback_used=false` und
Self-Pair-Kandidaten für 2/4/6/8 Takte. Für `END OF THE STORY` (601/316, 300
Matches) beträgt die Librosa-Coverage im gemeinsamen Bereich nur 0,499168;
der Track bleibt daher korrekt bei `fallback_from_detected_beats`, ohne
erfundene Metadaten oder Kandidaten. Die Binary-SHA
`35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`, alle drei
neuen Cache-Hashes und `diagnostics.merge` wurden maschinell validiert. Es
wurde kein Batch, Featurecache, Dataset oder Training gestartet. Details und
die vollständigen Distanz-/Unmatched-Zahlen stehen in
[`Bemerkungen.md`](./Bemerkungen.md).

**Verifiziert am 2026-08-12 (BS-RoFormer als Vocal-Default):** Die bisherige
HT-Demucs-Vocaltrennung wurde um ein RoFormer-Backend ergänzt. Standardmäßig
verwendet Featureextraktion, Vocal-Bridge-Cache und Vocal-ML-Pipeline jetzt
`bs-roformer-infer==0.1.1` mit
`roformer-model-bs-roformer-sw-by-jarredou`. Modell- und Config-Assets werden
beim ersten Bedarf in einem getrennten Cache geladen; Stem-Manifest und
Featurecache speichern Backend-, Software-, Modell- und SHA-Provenienz.
`--vocal-backend demucs` bleibt als expliziter Vergleichspfad erhalten.
Die RoFormer-Cachetests bestehen; `pip check` meldet keine defekten
Abhängigkeiten. Die breitere Suite bleibt auf dieser Windows/Python-3.14-
Umgebung bei Librosa/Numba-JIT-Initialisierung beziehungsweise einem bekannten
Numba-Fehler in `librosa.resample` hängen; das ist separat von der RoFormer-
Integration zu behandeln.

**Verifiziert am 2026-08-12 (RoFormer-Vocal-Cache aktueller Datensatz):** Der
Datensatz `output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805`
ist vollstÃ¤ndig mit dem Default `roformer-model-bs-roformer-sw-by-jarredou`
verarbeitet: Train 370/370, Validation 50/50 und Test 60/60. Der Bridge-Cache
enthÃ¤lt damit 480 RoFormer-Beispiele; 55 eindeutige RoFormer-Vocal-Stem-
Manifeste liegen unter `output/feature_cache/model_artifacts/roformer_vocal_v1/`.
Alle geprÃ¼ften Stem-Manifeste melden Backend `roformer`, Modellkennung,
`cuda:0`, SHA-256 des Checkpoints und 44,1-kHz-Audio; bestehende Demucs-
Artefakte wurden nicht verÃ¤ndert. Der ursprÃ¼ngliche SW-Download unter dem
gelÃ¶schten `jarredou`-Repository wurde fÃ¼r diesen Lauf auf den Ã¶ffentlichen
`enerjazzer/BS-ROFO-SW-Fixed`-Mirror umgeleitet; die Checkpoint-SHA stimmt mit
der dokumentierten 699.412.152-Byte-Datei Ã¼berein.

**Verifiziert am 2026-08-12 (RoFormer-Trainingslauf):** Der Vocal-Control-
Runner `self_supervised_vocal_train_validation_v2` wurde auf demselben
370/50-Datensatz mit `roformer-model-bs-roformer-sw-by-jarredou` und
`cuda:0` ausgefÃ¼hrt. Alle 420 materialisierten Train-/Validation-Bridge-
Manifeste meldeten Backend `roformer` und wurden als Cache-Hits verwendet.
Der Lauf endete per Early Stopping nach Epoche 27; der beste Checkpoint ist
Epoche 21 mit Validation-Loss `0.3318392038` (Initialisierung: `0.350723`).
Run-Artefakte liegen unter
`output/training_runs/vocal_roformer_extended_bpm145_165_top10_seed20260812/`.

**Rolle dieser Datei:** Einstieg, verifizierter aktueller Stand und priorisierte
nächste Schritte. Der ausführliche chronologische Experimentlog gehört in
[`Bemerkungen.md`](./Bemerkungen.md); die älteren Verifizierungsblöcke hier
bleiben als Übergangsarchiv erhalten und sind keine zusätzlichen To-do-Listen.
Eine grafische Übersicht der aktuellen ML-Pfade steht in
[`ML_MODEL_CURRENT_STATE.md`](./ML_MODEL_CURRENT_STATE.md).
**Maßgeblicher Kontext: [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) (Exposé).** Diese Datei hält den *technischen Prototyp-Stand der Startphase* (Monat 1 / erste 2–3 Wochen) fest. Ziel, Scope, wissenschaftlicher Beitrag, Related Work, Datenstrategie, Evaluation, 6-Monats-Plan und Risiken stehen im Exposé.

**Forschungsfrage (präzisiert am 2026-07-29):** Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue, nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu **bewerten** und zu **erzeugen** — möglichst ohne explizite Annotationen? Wissenschaftlicher Kern ist jetzt das **Lernen zeitabhängiger Mixing-Kurven ohne Ground-Truth-Kontrollkurven**; eine eingefrorene Übergangsmetrik liefert über einen differenzierbaren Renderer das Lernsignal. Compatibility- und Render-Metriken bleiben Baselines und Hilfskomponenten.

**Wichtigstes Erfolgskriterium der Startphase (Exposé Abschn. 14):** Nach spätestens drei Wochen sollen *mehrere automatisch erzeugte* Übergänge *hörbar* sein und *systematisch verglichen* werden können.

Kurzfazit Prototyp: Kandidaten können jetzt aus taktsynchronen Downbeats automatisch erzeugt, als Drop-Ende-A→energiearme Bridge→Drop-Anfang-B vorgerankt, ohne Überlappung der High-Power-Abschnitte gerendert und anschließend anhand des tatsächlichen Renderergebnisses erneut bewertet werden. Objective-v4-optimierte Kurven gewannen den zurückgehaltenen Hörsatz 9/9 gegen Equal Power. Volltrack-Features einschließlich vortrainierter Vocal-Separation, persistente Trainings-Waveform-Caches und die erste kleine Feature→Control-MLP-Baseline samt versioniertem Trainingslauf sind implementiert. Der MLP-Hörvergleich zeigte qualitativ nur geringe Unterschiede und weiterhin Vocal-Overlap beziehungsweise unnatürlich leise eingeblendete Vocals. Deshalb wurden ein stem-fähiger Renderer, Vocal-Control-Modell v2 und Objective v5 mit explizitem Audibility-Loss ergänzt. Im gezielt Vocal-reichen Hörsatz gewinnt Objective v5 zwei Paare gegen einen v4-Sieg und drei Gleichstände; nur die Vocal-Klarheit verbessert sich. Nach dem ersten 45/9-Lauf wurde der Musikbestand auf 119 FLAC-Pfade erweitert und reproduzierbar auf 145–165 BPM gefiltert. Der neue SHA-getrennte Datensatz enthält 370/50/60 Train-/Validation-/Testbeispiele. Der zweite Vocal-v2-Lauf erreicht die beste Validation in Epoche 22 und verbessert den Gesamt-Proxy um 6,14 %, nun auch den alten v4- und Energieanteil. Die Mid-Phrase-Gain-Änderung wird jedoch deutlich schlechter. Ein geblendeter Vergleich des Best-Checkpoints gegen die ungelernte Initialisierung liegt jetzt mit fünf vocal-aktiven Paaren ohne Time-Stretch bereit; die Bewertung ist offen. Die lokale RTX 5070 Ti ist inzwischen über PyTorch 2.13.0+cu130 nutzbar; neue Trainings- und Demucs-Läufe wählen CUDA standardmäßig automatisch.

## Aktueller Stand (implementiert)

- **Projektstruktur / API / CLI**: `src/pipeline.py` bietet `render_transition()` sowie `generate_transition_candidates()` als programmatische Einstiege; argparse deckt weiterhin den einzelnen Render-Export ab. Struktur `src/analysis/`, `src/candidates/`, `src/cutting/`, `src/tempo/`.
- **Audio-I/O**: Laden über `librosa.load`, Export über `soundfile.write`; intern standardmäßig 44,1 kHz Stereo. Abweichende Sample-Raten werden resampelt, Mono wird auf Stereo erweitert und Beat-Positionen werden mit skaliert.
- **Beat-/Bar-Analyse** (`src/analysis/pre_analysis.py`):
  - librosa `beat_track` für BPM + Beats.
  - aufTAKT (`aufTAKTCl.exe`) für Taktposition; Nicht-WAV wird per ffmpeg konvertiert.
  - Merge beider Quellen zu bar-annotierten Beats (`sample, count_in_bar, beats_in_bar`); Abweichungen werden protokolliert.
  - Analyse-Cacheformat 2 unter `v2/<audio-sha256>/<analysis-id>/analysis.json`: kollisionsfrei für gleiche Stems, an Audio und vollständigen Analysevertrag gebunden und atomar geschrieben. Die JSON-Datei enthält BPM, Beats, Grid-Provenienz und Diskrepanzdiagnostik; alte Stem-/Text-Caches bleiben read-only lesbar.
  - Fallback: Wenn aufTAKT fehlt, fehlschlägt oder unvollständige Metadaten liefert, werden die Beat-Positionen als approximatives 4/4-Raster annotiert; ohne Beats wird bei gültigem BPM ein gleichmäßiges Raster erzeugt.
  - Analyseformat 1 trennt seit 2026-08-12 Raster und Herkunft: `grid_source`, `fallback_used`, Backend-Version, Confidence, `analysis_id` und Beat-Grid-Hash werden additiv gespeichert. Alt-Caches ohne Sidecar werden als `legacy_cache_unknown` markiert und nicht nachträglich als erkannt klassifiziert. Verträge: `ANALYSIS_PROTOCOL.md`, `EXTERNAL_TOOLS.md`.
- **Übergänge**:
  - `src/cutting/simple_cut.py`: Hard Cut, Snap auf den nächstgelegenen Downbeat, Bar-Alignment zwischen beiden Songs.
  - `src/cutting/fade_cut.py`: linearer Crossfade über N Beats (Default 8), Bar-aligned.
  - `src/cutting/equal_power_fade_cut.py`: Equal-Power-Crossfade.
  - Alle Renderer passen Song B tonhöhenerhaltend auf BPM von Song A an; `tempo_fade` ist ein Kompatibilitätsalias für den linearen Crossfade.
- **Bridge-Rendering Version 2**: Fade-Renderer erhalten Drop A vollständig bis zum Source-Cut, mischen ausschließlich Source-Postroll mit Target-Preroll und beginnen Drop B exakt am Target-Cut. Die beiden High-Power-Abschnitte liegen dadurch außerhalb des überlappenden Fensters.
- **Tempo** (`src/tempo/`): Resample-basierte Variante (`SimpleTempoAdjust`, verändert Tonhöhe) und tonhöhenerhaltender `TimeStretch` über Rubber Band. Primär läuft FFmpegs `rubberband`-Filter mit gemeinsamem Stereo; bei Fehlern folgt das eigenständige Rubber-Band-CLI mit R3-Engine. Der frühere Librosa-Phase-Vocoder ist nicht mehr im Produktionspfad.
- **Tests**: `pytest`-Suite mit synthetischen Audiodaten prüft alle vier Renderer, FFmpeg-Priorität, Rubber-Band-CLI-Fallback, Float32-Zwischenformat, Tempoanpassung, 48→44,1-kHz-Resampling, Mono→Stereo und den Fehlerpfad bei fehlenden Downbeat-Metadaten.
- **Kandidatengenerierung** (`src/candidates/`): versionierter Vertrag `CANDIDATE_PROTOCOL.md` und Generator `bar_grid_v1`. Er kombiniert standardmäßig alle nutzbaren Taktgrenzen beider Songs für 2/4 Takte; nachweislich erkannte Downbeat-Herkunft, vollständige Downbeat-Metadaten, Pre-/Post-Roll auf beiden Seiten, kompatible Beatanzahl in allen vier Fenstern und maximal 15 % Tempoabweichung sind harte Filter. `approximate_grid_policy = reject|allow` ist standardmäßig strikt; neue Kandidaten und Manifeste tragen Source-/Target-Grid-Provenienz.
- **Feature-Ranking** (`src/ranking/`): `feature_baseline_v3` bewertet Drop A, Source-Auslauf, Target-Vorlauf und Drop B getrennt. Je 30 % entfallen auf High Power der Drops und Non-Overlap (Energieabfall nach A, niedrige Transition-Energie, Energieanstieg vor B); Chroma, RMS-Kontinuität, Spektrum und Tempo ergänzen den Score.
- **Featurevertrag, globale Paarfeatures und Datasetexport** (`src/features/`): Feature-Protokoll 1 definiert `features_a/features_b` als `float32 (32, 54)` und 16 globale Merkmale. `extract_track.py` berechnet und cached Volltrackmerkmale, `vocal.py` trennt standardmäßig mit BS-RoFormer einmal pro Song einen wiederverwendbaren Vocal-Stem (HT Demucs bleibt explizit wählbar), `global_pair.py` erzeugt Tempo-, lokale Key-/Harmonie- und Kontextwerte. `dataset_export.py` wählt gerankte Vier-Takt-Kandidaten, wendet Trainingsausschlüsse an, bildet Audio-SHA-getrennte Splits, fitttet Flux-/Onset-Normalisierung nur auf Trainingsartefakten und exportiert atomar NPZ/JSONL mit vollständiger Provenienz. Phrasenkanäle bleiben mit `phrase_valid = 0` deaktiviert. Verträge: `FEATURE_PROTOCOL.md`, `DATASET_PROTOCOL.md`, `PRETRAINED_MODELS.md`.
- **Feature-/Dataset-v2 für variable Längen (2026-08-20)**: Additive Protocol-2-Module erzeugen aus 2/4/6/8 Takten homogene `T=16/32/48/64`-Fenster, behalten 54 Kanäle und 16 globale Features stabil, führen `length_condition` getrennt und exportieren reproduzierbare NPZ-/JSONL-Shards über eine gemeinsame Audio-SHA-Split-Autorität. Leere Shards werden explizit manifestiert; v1-APIs und v1-Datasets bleiben unverändert testbar. Der synthetische v2-Testumfang besteht, ein großer realer Export wurde nicht erzeugt. Verträge: `FEATURE_PROTOCOL_V2.md`, `DATASET_PROTOCOL_V2.md`.
- **Metrik für gerenderte Übergänge** (`src/ranking/rendered_transition.py`): `rendered_transition_baseline_v1` bewertet nach dem Rendering das tatsächliche Audio inklusive Time-Stretch und Crossfade. Energieform und Grenzglätte zählen je 30 %, harmonische Kontinuität und rhythmische Stabilität je 20 %. Score, Teilwerte, Messwerte, Rang und isolierte Fehler stehen additiv im Batch-Manifest.
- **Differenzierbarer Control-Prototyp** (`src/control/`): `differentiable_control_v3` rendert vier Takte aus zwei komplementären, konstruktiv monotonen Kurven (`mix_position`, `low_end_position`) mit Equal-Power-Gains und festem FIR-Crossover. Bei 32 Punkten ist jeder Halbbeat-Schritt konstruktiv kleiner als 0,099644; normalisierte Abweichungs- und Krümmungsterme bestrafen abrupte Übergaben. Objective Version 4 ergänzt gültigkeitsmaskierte Vocal-Overlap-, Vocal-Onset/-Offset-Grenz- und Transientenartefakt-Terme aus den gespeicherten Featurefenstern. Frei parametrisierte Kurven können vor einem neuronalen Netz direkt optimiert werden; der Vertrag steht in `DIFFERENTIABLE_CONTROL_PROTOCOL.md`.
- **Reale Control-Vergleiche** (`src/evaluation/control_probe.py`): wählt aus einem nachbewerteten Multi-Song-Batch hoch bewertete 4-Takt-Kandidaten, rekonstruiert Source-Postroll und Target-Preroll, optimiert die zwei Control-Kurven und exportiert pro Paar Baseline/Optimiert mit identischem Kontext, gemeinsamer Peak-Absenkung und versioniertem Manifest. Der aktuelle blinde v3-Control-Satz mit Rubber Band liegt unter `output/control_studies/blind_v4_control_v3_rubberband_top8_4bar_20260730/`; frühere v1/v2-Versuche bleiben unverändert.
- **Blinde Control-Hörstudie** (`src/evaluation/blind_control_study.py`, `control_study_ratings.py`, `analyze_control_study.py`): erzeugt A/B-Dateien ohne Methodenlabel, trennt den unveränderlichen Antwortschlüssel vom öffentlichen Manifest, speichert Ratings atomisch und entblindet erst nach vollständiger Bewertung in ein reproduzierbares `study_results.json`. Vertrag: `CONTROL_STUDY_PROTOCOL.md`.
- **Historische Render-Metrik** (`src/evaluation/backfill_transition_metrics.py`): bewertet vorhandene Multi-Song-Batches ohne Änderung der WAVs oder ursprünglichen Manifeste. Samplegenaue Grenzen werden aus Kandidaten-Beat-Index, Read-only-Analyse-Cache und Tempoanpassung rekonstruiert; atomische `transition_metrics.json`-Sidecars dokumentieren Fortschritt und Ergebnisse.
- **Songpaar-Kompatibilität** (`src/ranking/song_compatibility.py`): `rank_song_targets()` ordnet Target-Songs pro Source-Song vor der Cutpoint-Generierung nach Harmonie, Tempoanpassungsstärke, Klang, Energie und Rhythmus.
- **Batch-Rendering** (`src/batch_render.py`, `src/multi_batch_render.py`): rankt akzeptierte Kandidaten und rendert standardmäßig die Top 5 × ausgewählte Renderer als kurze WAV-Vorschauen. Multi-Batches akzeptieren rekursive Musikordner, deduplizieren identisches Audio per SHA-256, filtern optional inklusive BPM-Grenzen und teilen Volltrack-Kompatibilitätsfeatures über alle Quellen. Mehrere Analyseworker verwenden getrennte temporäre aufTAKT-Dateien. Exporte werden atomar geschrieben; vorhandene Dateien werden ohne explizites `--overwrite` nicht ersetzt. Source-/Paarfehler isolieren unabhängige Arbeit und bleiben im finalen Manifest; jeder dort dokumentierte Analyse-, Render- oder Metrikfehler führt anschließend zu CLI-Exit-Code 1. Seit 2026-07-22 übernehmen alle Renderer Source-/Target-BPM explizit aus dem Kandidatenvertrag und passen Song B konsistent auf Song A an.
- **Hörbewertung und Visualisierung** (`src/evaluation/ratings.py`, `notebooks/listen_batch.ipynb`): das Notebook listet Varianten in Rangfolge, zeigt für den umgebenden Multi-Song-Batch die Render-Score-Verteilung sowie Cutpoint-gegen-Render-Score und hebt das aktuelle Songpaar hervor. Pro Hörprobe werden die Source- und Target-Waveform an ihren jeweiligen Cue Points bei `t = 0` ausgerichtet untereinander sowie Gesamtscore und vier Render-Metrikkomponenten visualisiert. Zusätzlich zeigt es an einem echten Validation-Beispiel die Modellinputs `features_a/features_b (32, 54)`, `global_features (16,)`, die MLP-Fusion `(31, 124)` und die dazugehörigen Bridge-Waveforms. Eine separate Ansicht beschriftet ausschließlich die sechs Vocal-Features je Source/Target als `6 × 32`-Heatmaps; eine weitere zeigt die beschrifteten MLP-Outputs `mix_position`, `low_end_position` und deren Diagnose-Logits. Der beste gelernte Vocal-Checkpoint wird auf dasselbe Validation-Beispiel angewendet und visualisiert `vocal_position`, Vocal-Ducking sowie die resultierenden Vocal-Gains. WAVs werden über `IPython.display.Audio` eingebettet. `rate()` speichert eine 1–5-Bewertung mit Fehler-Tags und Notiz atomar in einer getrennten `ratings.json`; dieselbe Funktionalität ist als CLI verfügbar. Der Startpfad verweist auf ein nachbewertetes reales Songpaar.
- **Dataset und Ausschlüsse**: 119 FLAC-Pfade liegen rekursiv im ignorierten Ordner `musik/`. `config/track_exclusions.json` schließt `14 - STRUGGLING.flac` aus neuen Multi-Batches, Control-Vergleichen und Training aus. Der neue Batch entfernt zusätzlich ein byteidentisches BREATH_LESS-Duplikat und sechs Tracks unter 145 BPM; keiner lag über 165 BPM. Der erweiterte SHA-getrennte Datensatz enthält 370/50/60 Beispiele über 43/5/7 verwendete Trackhashes. Der historische 45/9/9-Datensatz und frühere Läufe bleiben unverändert. Kuratierte Track-Notizen und Lizenzstatus fehlen weiterhin.
- **ML-Baseline Version 1** (`src/ml/`): `FeatureControlDataset` verbindet die bestehenden Feature-Splits mit unveränderlichen, hashbasiert gecachten Source-/Target-Bridge-Waveforms. `time_shared_mlp_v1` hat 10.394 Parameter, wird auf alle 31 Halbbeat-Intervalle geteilt angewendet und erzeugt über dieselbe konstruktive Control-v3-Transformation zwei gültige Kurven. Die Nullinitialisierung startet exakt bei Equal Power; `self_supervised_batch_loss` rendert variable Audiolängen ohne Padding einzeln und mittelt Objective v4. `self_supervised_train_validation_v1` ergänzt deterministische Seeds, Equal-Power-Epoche 0, atomare Best-/Latest-Checkpoints mit SHA-256, vollständige Loss-History, Early Stopping und vertragsgeprüftes Resume. Resume und Studienexport prüfen den Manifesthash vor dem eingeschränkten `weights_only`-Laden. Vertrag: `ML_CONTROL_MODEL_PROTOCOL.md`.
- **Vocal-Control-Erweiterung Version 2** (`src/control/`, `src/ml/`): `vocal_time_shared_mlp_v2` hat 20.821 Parameter und erzeugt zusätzlich eine monotone Vocal-Übergabe sowie getrenntes Source-/Target-Ducking. `DifferentiableVocalAwareRenderer` verarbeitet gecachte Demucs-Stems separat vom Zwei-Band-Accompaniment. Objective v5 ersetzt die alten mixgebundenen Vocal-Gewichte durch tatsächlichen Stem-Overlap, einen Audibility-Loss gegen unnötig leise aktive Vocals und eine Strafe für Gain-Änderungen mitten in Phrasen. Der Cache v2 speichert Mix und beide samplegleichen Vocal-Stems. `self_supervised_vocal_train_validation_v2` trainiert diese Kette reproduzierbar mit atomaren Checkpoints, Early Stopping, strengem Vertrags-/Hash-Resume und ohne Zugriff auf den Testsplit; Checkpoint-Loads sind auf `weights_only` beschränkt. Vertrag: `VOCAL_CONTROL_MODEL_PROTOCOL.md`.
- **ML-Modellübersicht (2026-08-19):** [`ML_MODEL_CURRENT_STATE.md`](./ML_MODEL_CURRENT_STATE.md) visualisiert den aktuellen RoFormer-gestützten `vocal_time_shared_mlp_v2`-Default, die historische `time_shared_mlp_v1`-Baseline und den implementierten, aber noch experimentellen `tcn_bilstm_transition_control_v1`-Pfad einschließlich Run-Status und offener Hörvalidierung.
- **GPU-Ausführung** (`src/torch_device.py`): `auto` wählt für Training und neue Demucs-Separationen CUDA, wenn verfügbar, andernfalls CPU. Der aufgelöste Trainings-Device wird im unveränderlichen Run-Vertrag gespeichert; explizite Overrides bleiben mit `--device cpu` und `--device cuda:<index>` möglich. `requirements-cuda.txt` fixiert den offiziellen CUDA-13.0-Wheel zusätzlich zum plattformneutralen Basis-Requirement.
- **W&B-Logging (2026-08-20)** (`src/ml/wandb_logging.py`): Beide Trainingsrunner loggen epochweise Train-/Validation-Losses und Objective-Teilmetriken nach W&B. `--wandb-mode offline|online|disabled` sowie `WANDB_*`-Umgebungsvariablen steuern die Integration; Checkpoints, `history.json` und `manifest.json` können als Artifact gespeichert werden. Lokale Run-Dateien und Run-Verträge bleiben maßgeblich, Dataset-Pfade werden nicht an W&B übertragen. Drei reale CUDA-Läufe wurden mit gemeinsamer Gruppe `beatbridge-all-models-20260820` ausgeführt: MLP beste Validation `0,4149939463`, Vocal-v2 `0,3292209521`, TCN/BiLSTM `0,3226487994`. Die Online-Synchronisation ist wegen eines ungültigen/stale API-Keys noch offen; die W&B-Offline-Runs liegen lokal vor. Abhängigkeit: `wandb==0.28.1`.

### Verifiziert am 2026-08-12 (Codex, Multi-Batch-Exitstatus)

- `src.multi_batch_render` verarbeitet unabhängige Sources und Paare trotz
  Einzelfehlern weiter und schreibt das finale Wurzelmanifest weiterhin
  atomar.
- Danach liefert die CLI Exit-Code `1` für dokumentierte BPM-Analyse-,
  Source-, Paar-, Render- oder Render-Metrikfehler. Exit-Code `0` ist auf
  Läufe ohne aufgezeichnete Fehler beschränkt; reguläre Ausschlüsse und
  Duplikate sind keine Fehler.
- CLI-Tests decken Source-/Paarfehler, BPM-Analysefehler, verschachtelte
  Render-/Metrikfehler und den fehlerfreien Exit-0-Fall ab.
- `.venv\Scripts\python.exe -m pytest -q`: **128 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

### Verifiziert am 2026-08-12 (Codex, sichere Checkpoint-Loads)

- Alle vier Produktionspfade für v1-/v2-Resume und Studienexport verwenden
  `torch.load(..., weights_only=True)`; es gibt keinen verbleibenden
  `weights_only=False`-Aufruf unter `src/`.
- Der v1-Runner prüft nun wie v2 den SHA-256 von `latest.pt` gegen
  `manifest.json`, bevor PyTorch die Datei öffnet. Beide Studienloader prüfen
  den manifestierten Best-Checkpoint ebenfalls vor dem Laden.
- Tests verankern den `weights_only`-Parameter an allen vier Loadpfaden und
  weisen manipulierte v1-/v2-`latest.pt` sowie beide `best.pt` vor dem Laden
  ab.
- Alle sechs vorhandenen manifestierten Checkpoints aus den drei realen
  v1-/v2-Trainingsläufen bestanden ihre SHA-256-Prüfung und ließen sich mit
  `weights_only=True` auf CPU laden.
- `.venv\Scripts\python.exe -m pytest -q`: **123 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

### Verifiziert am 2026-08-12 (Codex, Downbeat-Grid-Provenienz)

- `AnalysisResult` ergänzt die bisherigen BPM-/Beat-Tupel um
  `BeatGridMetadata`; Zweiwert-Unpacking bleibt kompatibel. Direkte
  `RenderResult`-Objekte führen Source-/Target-Provenienz ebenfalls additiv.
- Frische vollständige aufTAKT/librosa-Merges speichern `fallback_used = false`,
  beide Backendidentitäten und eine normierte Match-Confidence. Beat- und
  BPM-Fallbacks speichern `fallback_used = true`, ihre genaue Quelle und
  Confidence `0,0`; Alt-Caches bleiben explizit
  `legacy_cache_unknown` mit `fallback_used = null`.
- Der Default `approximate_grid_policy = reject` weist Fallback und unbekannte
  Herkunft mit getrennten Source-/Target-Rejectioncodes ab. `allow` ist ein
  expliziter Opt-in und entfernt die Provenienz nicht.
- Neue Batchkandidaten tragen `source_grid`/`target_grid`; neue Datasetzeilen
  übernehmen diese Felder. Historische Kandidaten werden als `null` behandelt,
  nicht rückwirkend geraten.
- Volltrack-Featurecaches führen `beat_grid_metadata` im Manifest und im
  Cache-Key, sodass eine geänderte Herkunft keinen alten Cache-Hit erzeugt.
- Cacheformat 2 adressiert Ergebnisse über vollständigen Audio-SHA und einen
  Hash aus Algorithmusversion, librosa-Version/-Parametern,
  aufTAKT-Binary-SHA, Merge- und Fallbackvertrag. `analysis.json` wird atomar
  geschrieben; gleichnamige, inhaltlich verschiedene Dateien besitzen
  getrennte Cachepfade. Legacy-Caches werden nur bei passendem Audiohash
  read-only geladen.
- Die lokale `aufTAKTCl.exe` hat SHA-256
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`
  und keine eingebettete Versions-/Herstellerinformation. Die CLI passt zur
  zplane-AUFTAKT-SDK-Dokumentation; exakte Lieferkette, lokale Lizenz und
  Weitergaberecht sind im Repository nicht belegt. Maschinenlesbarer Stand:
  `config/auftakt_binary_provenance.json`.
- `.venv\Scripts\python.exe -m pytest -q`: **121 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

### Verifiziert am 2026-07-30 (Codex, Feature-Protokoll 1)

- Kanonische Modellinputs: pro Track **32 Halbbeat-Schritte × 54 skalare
  Features**, dazu **16 globale Features**. Die Dimensionen entstehen aus
  stabil benannten Gruppen und nicht aus einer vorgegebenen 64er-Zielgröße.
- Die Vocal-Gruppe enthält `vocal_activity`, `vocal_prominence`,
  `vocal_onset_probability`, `vocal_offset_probability`,
  `vocal_phrase_progress` und `vocal_confidence`; `vocal_valid` trennt
  fehlende Analyse von tatsächlich inaktivem Gesang.
- Phrasenmerkmale beziehen sich auf erkannte 8-Takt-Phrasen. Ein
  `bar_index modulo 8`-Fallback ist ausdrücklich nicht als gültige
  Phrasenerkennung erlaubt.
- Target-Features werden auf genau der tempoangepassten Waveform berechnet,
  die der Renderer verwendet. Richtung und Betrag der Tempoänderung sind
  globale Inputs; der Backendname bleibt Dataset-Provenienz.
- Shape, dtype, endliche Werte, Wertebereiche und binäre Masken werden durch
  `src.features` validiert. Vocal-/Phrasen-Extractor und Datasetexport sind
  noch offen.
- `.venv\Scripts\python.exe -m pytest -q`: **59 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Volltrack-Featurecache v1)

- Hashbasierte Cacheeinträge enthalten Volltrack-Basiskanäle,
  Halbbeat-Samplegrenzen und rohe Flux-/Onset-Kanäle. Audioänderung,
  Beat-Grid, Ziel-BPM, Sample-Rate oder Protokoll-/Extractor-Version ändern
  den Cache-Key.
- Source-Postroll und Target-Preroll werden als `(32, 54)` aus einem
  Volltrack-Artefakt geschnitten. Erst dabei werden
  `transition_position`, Flux und Onset mit Trainingssplit-Statistiken
  vervollständigt und gegen Feature-Protokoll 1 validiert.
- Reale Sonde `GHOST`: **990 Halbbeat-Bins × 54 Kanäle**; erster Lauf
  `cache_hit = false`, unmittelbar wiederholter Lauf `cache_hit = true` auf
  demselben Artefakt. Kein Time-Stretch war nötig.
- Vocal und Phrase stehen im Cachemanifest auf `not_implemented`;
  `vocal_valid = phrase_valid = 0` verhindert eine Verwechslung mit
  tatsächlich inaktiven Signalen.
- Aus dem realen GHOST-Cache wurden ohne Neuberechnung gültige Source- und
  Target-Fenster mit Shape `(32, 54)` und ausschließlich endlichen Werten
  geschnitten.
- `.venv\Scripts\python.exe -m pytest -q`: **65 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, HT-Demucs-Vocalcache v1)

- Demucs `4.1.0` läuft mit der vorhandenen Python-3.14-/Torch-2.13-CPU-Umgebung.
  Verwendet wurde `htdemucs` aus `adefossez/HTDemucs`, Revision
  `bf35a81b663819a8255c8fefee17f9d812b786b5`; der SHA-256 der
  `955717e8.safetensors`-Gewichte ist
  `d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd`.
- Reale Sonde `GHOST`: Der erste Lauf erzeugte einen persistenten Vocal-Stem
  und ein neues Featureartefakt mit **990 × 54** Werten. Der
  Vocal-Aktivitätsscore reicht von rund `1,87e-7` bis `0,9971`;
  `vocal_valid` ist in allen vollständigen Bins eins.
- Der unmittelbar wiederholte CLI-Lauf verwendete das vorhandene
  Featureartefakt mit `cache_hit = true`; weder Separation noch
  Volltrack-Features wurden erneut berechnet.
- Das Manifest enthält Demucs-Version, Modellname, Hub-Revision,
  Gewichtsdatei-Hashes, Vocal-Stem-Hash und die zitierfähigen Paper-Metadaten.
  BibTeX: `docs/REFERENCES.bib`.
- `.venv\Scripts\python.exe -m pytest -q`: **67 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-31 (Codex, globale Features und Datasetformat 1)

- `global_pair_v1` erzeugt alle **16** Vertragswerte: fünf Tempowerte,
  lokale Tonika/Modus/Confidence für A und B, harmonische Kompatibilität und
  Abdeckung des acht Takte breiten Cue-Kontexts. Fehlende tonale Evidenz ist
  explizit Confidence null und Kompatibilität neutral `0,5`.
- Aus 60 historischen Paarmanifesten wurden 165 gerankte Vier-Takt-Beispiele
  ausgewählt. Die Trainingspolicy entfernte neun Beispiele mit `STRUGGLING`;
  die strikt track-getrennte Zuordnung verwarf weitere 93 kreuzende Paare.
- Finaler Datensatz: `dataset_id = f9044dc259b7296c8b28`, **63 eindeutige
  Beispiele** in **45 Train / 9 Validation / 9 Test**. Die Trackzuordnung ist
  12/2/3 über 17 vorkommende erlaubte Audio-Hashes; `TIME_LESS` ist zwar dem
  Trainingssplit zugeordnet, kommt nach Cross-Split-Filterung aber in keinem
  exportierten Beispiel vor.
- Shapes sind Train `(45,32,54)/(45,32,54)/(45,16)`, Validation und Test je
  `(9,32,54)/(9,32,54)/(9,16)`. Alle Werte sind endlich, alle exportierten
  Source-/Targetfenster haben `vocal_valid = 1`, 63 Example-IDs sind eindeutig
  und kein Audio-Hash liegt in mehreren Splits.
- Flux-/Onset-Statistiken wurden ausschließlich aus verwendeten
  Trainingsartefakten gefittet (`stats_id = train-d361f7da6414a9e6`). Die
  SHA-256-Werte aller fünf Datasetdateien wurden gegen das Manifest geprüft.
- `.venv\Scripts\python.exe -m pytest -q`: **72 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-31 (Codex, Objective v4 und zurückgehaltener Hörsatz)

- Objective v4 verwendet drei neue differenzierbare Terme:
  gaingewichtetes `vocal_overlap`, onset-/offsetbewusstes `vocal_boundary`
  und `transient_artifact` für Übergabebewegung auf starken
  Onset-/Spectral-Flux-Bins. Ohne beide Featuretensoren sind die neuen Terme
  exakt null; ein nur einseitig vorhandener Tensor wird abgelehnt.
- Die Gewichte `1.0 / 0.30 / 0.08` wurden auf zwei inhaltlich eindeutigen
  Validation-Paaren eingefroren. Der Loss sank dort von `0.2180 → 0.1916`
  und `0.2906 → 0.2740`. Beim vocalreichen zweiten Paar sank
  Vocal-Overlap `0.0168 → 0.0068` und Vocal-Grenze `0.4647 → 0.4078`.
- `src.evaluation.heldout_control_study` rendert Datasetbeispiele direkt mit
  ihren gespeicherten Featurefenstern und dokumentiert Dataset-ID, Split,
  Objective-Version, Controls und Loss-Komponenten. Der Testsplit bleibt
  strikt von Training und Validation getrennt.
- Neuer geblendeter Testsatz:
  `output/control_studies/blind_v5_objective_v4_heldout_test9_4bar_20260731_rerun/`.
  Er enthält alle neun Testbeispiele als 18 Float32-WAVs, 44,1 kHz Stereo,
  paarweise identische Länge und ausschließlich endliche Samples. Drei
  Frontliner-Paare verwenden `ffmpeg_librubberband`, die übrigen sechs
  benötigen keine Tempoanpassung. `STRUGGLING` kommt nicht vor.
- Der Objective-Loss sank in allen neun Testbeispielen (je nach Paar rund
  5,3–19,5 %). Der Satz ist noch geblendet und unbewertet; ein hörbarer
  Vorteil gegenüber Equal Power ist daher ausdrücklich noch nicht belegt.
- Ratings-Format 2 ergänzt `vocal_clarity` sowie `vocal_clash` und
  `cut_lyrics`; alte Format-1-Ratings bleiben lesbar.
- `.venv\Scripts\python.exe -m pytest -q`: **77 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-04 (Nutzerhörtest, Objective v4)

- Der geblendete Testsplit-Hörsatz ist vollständig bewertet und erst danach
  über `src.evaluation.analyze_control_study` entblindet worden. Persistente
  Ergebnisse: `ratings.json` und `study_results.json` im v5-Hörsatz.
- Präferenz: **9/9 für die Objective-v4-optimierten Kurven**, 0 für Equal
  Power, 0 Gleichstände. Das gilt in allen drei gerichteten Paargruppen mit
  jeweils drei unterschiedlichen Cue-Kombinationen.
- Mittel über sechs Kriterien: Equal Power **4,7593**, optimiert **4,9259**.
  Der Unterschied stammt ausschließlich aus `cleanliness`: **4,0 → 5,0** in
  jedem Paar. Energieform, Low-End und Artefaktfreiheit sind jeweils 5,0 für
  beide Methoden; Rhythmik und Vocal-Klarheit jeweils 4,7778 für beide.
- Interpretation: Das direkte Optimierungs-Gate gegen Equal Power ist für
  diesen zurückgehaltenen Satz bestanden. Eine spezifische hörbare
  Verbesserung durch die neuen Vocal-Terme ist damit noch nicht gezeigt;
  acht Paare hatten dort Deckeneffekte, Paar 3 erhielt für beide Methoden
  Vocal-Klarheit 3.
- Statistische Grenze: neun Cue-Beispiele sind wegen Track-/Paarwiederholung
  keine neun unabhängigen Beobachtungen. Der Testsplit enthält drei
  Audio-Hashes; insbesondere teilen die drei Paargruppen Tracks. Das Ergebnis
  ist ein starkes Entwicklungs-Gate, noch kein populationsweiter Nachweis.

### Verifiziert am 2026-08-04 (Codex, ML-Baseline Version 1)

- Bridge-Waveform-Cacheformat 1 speichert pro Beispiel zwei samplegleiche
  Float32-Stereo-Waveforms mit Konfigurations-, Datei- und Array-Hashes. Die
  produktive 44,1-kHz-Ausrichtung einschließlich Time-Stretch wird vor der
  Ablage auf standardmäßig 11.025 Hz heruntergerechnet und nicht pro Epoche
  wiederholt.
- Das PyTorch-Dataset prüft Split-NPZ, `examples.jsonl`, Paarmanifest und bei
  einem Cache-Erstaufbau beide Audio-SHAs. Features werden gestapelt;
  BPM-abhängig lange Waveforms bleiben ungepaddet und werden im Loss einzeln
  gerendert.
- `time_shared_mlp_v1`: 124 Eingänge je Intervall, Hidden-Dimensionen 64/32,
  zwei Inkrement-Logits, **10.394 Parameter**. Vor dem ersten Update sind
  beide Kurven exakt linear; Endpunkte, strenge Monotonie und maximale
  Schrittgröße bleiben konstruktiv garantiert.
- Reale Train-Sonde `example-c0a82769f650d763`: Cache-Erstlauf
  `cache_hit = false`, unmittelbare Wiederholung `true`, Waveformshape
  `(2, 67328)`, Backend `not_needed`. Der initiale self-supervised Loss ist
  `0,303036`; alle vorhandenen Modellgradienten sind endlich.
- Der endgültige unabhängige Modelltest benötigt neue Track-Hashes, weil der
  aktuelle Testsplit bereits für die Objective-v4-Hörstudie verwendet wurde.
- `.venv\Scripts\python.exe -m pytest -q`: **81 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Control-/Objective-v3 und neuer Hörsatz)

- Control-Protokoll 3 beschränkt die Inkrement-Logits konstruktiv auf
  `0.6 · tanh(logit)`. Für 32 Kontrollpunkte beträgt die theoretische
  Obergrenze eines Kurvenschritts **0,0996431**; Endpunkte 0/1 und strenge
  Monotonie bleiben erhalten.
- Das Objective bewertet die Abweichung vom gleichmäßigen Inkrement und die
  Änderung aufeinanderfolgender Inkremente nun skalenunabhängig. Equal Power
  hat für beide neuen Formterme den Wert null.
- `output/control_studies/blind_v4_control_v3_rubberband_top8_4bar_20260730/`
  enthält dieselben acht gerichteten Songpaare wie der bewertete v2-Satz,
  vollständig neu als **16 Float32-WAVs**, 44,1 kHz Stereo, paarweise gleiche
  Länge, endliche Samples und ohne Exportfehler.
- `FALLING → Aversion` und `FALLING → HELP_LESS` wurden über
  `ffmpeg_librubberband` tempoangepasst. Die sechs BPM-identischen Paare
  dokumentieren `not_needed`; `STRUGGLING` kommt nicht vor.
- Der öffentliche Satz enthält keine Methodenabbildung, `ratings.json` steht
  nach der Hörbewertung auf **8/8**. Erst danach wurde `answer_key.json`
  geöffnet und `study_results.json` erzeugt. Da dieselben acht früheren
  Urteile v3 mitmotiviert haben, ist dieser Satz ein kontrollierter
  Vorher-/Nachher-Vergleich, kein unabhängiger Testsatz.
- Ergebnis: **8 Gleichstände**, keine Präferenz für Baseline oder Optimiert.
  Beide Methoden erreichen denselben Gesamtmittelwert **4,45** und identische
  Kriterienmittel: Sauberkeit 4,25; Energieform 4,50; Low-End 4,625;
  Rhythmik 4,50; Artefaktfreiheit 4,375. Der Proxy-Loss sank je Paar trotzdem
  um 2,39–36,43 %, ohne einen erkennbaren Methodenunterschied zu erzeugen.
- Gemeinsame Fehler beider Methoden: unterbrochene Lyrics, zurückkehrende
  Source-Melodie, Vocal-Clash und ein schlecht klingendes Target in Paar 5.
  Dort wurde Aversion per `ffmpeg_librubberband` von 161,499 auf 156,605 BPM
  verlangsamt (−3,03 % Tempo); beide A/B-Varianten verwenden dieselbe
  gestretchte Waveform.
- `.venv\Scripts\python.exe -m pytest -q`: **54 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Rubber-Band-Time-Stretch)

- Der installierte FFmpeg-8.1-Build stellt den Filter `rubberband` bereit; die
  verfügbaren Optionen einschließlich `channels=together` wurden über
  `ffmpeg -hide_banner -h filter=rubberband` verifiziert.
- Eine reale Prozesssonde verarbeitete synthetisches 44,1-kHz-Stereo-Audio
  über `ffmpeg_librubberband` bei Faktor 1,1 zu exakt 80.182 Samples,
  Float32, endlichen Werten und zwei Kanälen.
- Das eigenständige `rubberband`-CLI ist lokal derzeit nicht installiert.
  Priorität, R3-Aufruf, inverses Zeitverhältnis und Fallback wurden deshalb
  mit isolierten Prozessdoubles getestet; ein fehlendes zweites Backend
  erscheint mit beiden Schrittursachen statt als stiller Librosa-Fallback.
- Rendering-Protokoll 5 und neue Batch-Manifeste führen
  `tempo_backend`; historische Version-4-Artefakte bleiben unverändert.
- `.venv\Scripts\python.exe -m pytest -q`: **52 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Auswertung blinder v3-Hörsatz)

- `ratings.json` enthält **8/8** vollständige Urteile einer Person. Erst danach wurde `answer_key.json` geöffnet und `study_results.json` erzeugt.
- Präferenzen: **Equal-Power-Baseline 4, optimierte Proxy-Kurve 3, Gleichstand 1**. Ohne Gleichstand entspricht das 57,1 % zu 42,9 %.
- Gesamtmittel über fünf Kriterien: Baseline **4,325**, Optimiert **4,250**. Optimiert minus Baseline: Sauberkeit 0,000, Energieform −0,125, Low-End-Übergabe 0,000, rhythmische Stabilität 0,000, Artefaktfreiheit −0,250.
- Interpretation: v2 liegt hörend nahe an der starken Baseline und der eindeutige v1-Fehler ist behoben, aber eine konsistente Verbesserung durch das aktuelle Proxy-Objective ist nicht belegt. Die Notizen markieren insbesondere abrupte Melodie-/Gain-Übergaben, Vocal-Timing, Time-Stretch-Artefakte und eine nicht erfasste 8/4-Phrasengrenze.
- Einschränkung: ein Rater, acht gezielt ausgewählte Paare, keine unabhängige Zufallsstichprobe; eine 5 bedeutet „kein negativer Punkt aufgefallen“, nicht Perfektion.
- `.venv\Scripts\python.exe -m pytest -q`: **49 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten.

### Verifiziert am 2026-07-29 (Codex, blinder v3-Hörsatz)

- `output/control_studies/blind_v3_top8_4bar_20260729/` enthält **8 unterschiedliche gerichtete Paare / 16 WAVs**, ausschließlich `A.wav`/`B.wav`, 44,1 kHz Stereo, paarweise identische Dauer, endliche Samples und keine Exportfehler.
- `STRUGGLING` kommt nicht vor; kein Track wird häufiger als zweimal verwendet. Das öffentliche `manifest.json` enthält keine Methodenabbildung. `answer_key.json` liegt separat; `ratings.json` war zum Exportzeitpunkt mit **0/8** Bewertungen initialisiert und wurde später vollständig ausgefüllt.
- `.venv\Scripts\python.exe -m pytest -q`: **46 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten.

### Verifiziert am 2026-07-29 (Codex, monotone Controls v2)

- Das menschliche Urteil für v1 war in allen vier Paaren eindeutig zugunsten der Baseline: Song A kam kurz vor dem Ende erneut zurück. Die gespeicherten v1-Kurven bestätigten 4–12 rückwärts laufende Mix-Schritte pro Paar und einen maximalen Einzelschritt von −0,468.
- Control-Protokoll 2 parametrisiert nur noch positive, per Softmax auf Summe 1 normierte Inkremente. Alle acht v2-Kurven (`mix_position` und `low_end_position` über vier Paare) haben **0 rückwärts laufende Schritte**, beginnen exakt bei 0 und enden exakt bei 1.
- Unter `output/control_comparisons/batch_20260722_top4_4bar_v2_monotone/` liegen acht neue WAVs, 44,1 kHz Stereo, paarweise identische Länge, endliche Samples und keine Exportfehler. Der Proxy-Loss sank weiterhin um 19,6 %, 72,9 %, 55,0 % und 57,4 %.
- Nutzerurteil: v2 klingt bereits besser; `STRUGGLING → ASCENSION` ist wegen des Tempo-Ausreißers kein gültiger Metrikvergleich und wird künftig ausgeschlossen. Eine erneute read-only Auswahl ersetzt das Paar durch `Frontliner - Tell Me → FALLING`.
- `.venv\Scripts\python.exe -m pytest -q`: **43 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. Ausschluss greift verifiziert in den Scopes `multi_batch`, `control_probe` und `training`.

### Verifiziert am 2026-07-29 (Codex, reale Control-Vergleiche)

- Vier unterschiedliche hoch bewertete 4-Takt-Paare aus dem Batch vom 22.07 wurden verarbeitet: `GHOST → REBIRTH`, `LESS_IS_MORE → HELP_LESS`, `STRUGGLING → ASCENSION` und `Aversion → The Sky`.
- **8/8 WAVs**, 44,1 kHz Stereo, paarweise identische Länge, endliche Samples, keine Exportfehler. Der Proxy-Loss sank um 24,1 %, 97,2 %, 60,7 % und 69,6 %.
- Die historische Render-Metrik bevorzugte Optimiert bei zwei Paaren und Baseline bei zwei Paaren; die Differenzen waren klein. Das menschliche Hörurteil verwarf Optimiert jedoch in allen vier Paaren wegen rückwärts laufender Übergaben. Dieser v1-Lauf ist damit ein dokumentierter Fehlschlag und Motivator für Protokoll 2.
- `.venv\Scripts\python.exe -m pytest -q`: **40 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten.

### Verifiziert am 2026-07-29 (Codex, differenzierbare Controls)

- PyTorch 2.13.0 CPU ist unter Python 3.14.2 installiert und in `requirements.txt` festgehalten.
- Die synthetische Direktoptimierung senkte den Proxy-Loss in 40 Schritten von 0,2191 auf 0,1049 (**−52,1 %**). Das belegt einen funktionierenden Gradientenpfad, noch keine hörbare Qualität.
- `.venv\Scripts\python.exe -m pytest -q`: **39 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-29 (Codex, Cue-Point-Waveforms)

- `notebooks/listen_batch.ipynb` wurde mit dem realen, nachbewerteten Paar `05_HELP_LESS → 07_BREATH_LESS` vollständig headless ausgeführt. `play(index)` erzeugt für Source A und Target B zwei übereinanderliegende Waveform-Plots mit gemeinsamer relativer Zeitachse, markiert beide Cue Points bei `t = 0` und zeigt danach weiterhin Metrikkomponenten und Audio-Player. Die Bildausgabe wurde stichprobenartig visuell geprüft.

### Verifiziert am 2026-07-27 (Codex, Metrikvisualisierung)

- `notebooks/listen_batch.ipynb` wurde mit dem realen, nachbewerteten Paar `05_HELP_LESS → 07_BREATH_LESS` vollständig headless ausgeführt. Die Übersicht aggregiert alle 165 bewerteten Varianten des umgebenden Multi-Song-Batches; Komponentenbalken und Audio-Player wurden ohne Fehler erzeugt. Beispielbewertungen werden beim Ausführen nicht automatisch gespeichert.
- Matplotlib 3.11.1 ist für Python 3.14 in `requirements.txt` festgehalten.

### Verifiziert am 2026-07-23 (Codex, nach Render-Metrik-Meilenstein)

- Multi-Song-Batch: `output/batches/all_songs_top3_targets_top3_transitions_20260722/`; für alle 20 aktuellen Tracks wurden die drei global kompatibelsten Zieltracks ausgewählt und pro Songpaar bis zu drei Equal-Power-Übergänge gerendert. Ergebnis: 60 abgeschlossene Paar-Manifeste, 165 WAV-Vorschauen, keine Runner- oder Renderfehler. `src.multi_batch_render` schreibt das Auswahl- und Fortschrittsmanifest nach jedem Songpaar atomar fort; Wildcards wie `musik\*.flac` werden auf Windows intern aufgelöst.
- Derselbe Multi-Song-Batch wurde am 2026-07-23 vollständig mit `rendered_transition_baseline_v1` nachbewertet: **165/165 Varianten aus 60/60 Paaren, 0 Fehler**. Scorebereich 0,569–0,943, Mittelwert 0,857, Median 0,883. Komponentenmittel: Energieform 0,817, Grenzglätte 0,900, harmonische Kontinuität 0,961, rhythmische Stabilität 0,749. Ergebnisse liegen als unveränderliche Sidecar-Auswertung unter `transition_metrics.json`.
- Python-Version der Projektumgebung: **3.14.2**.
- `.venv\Scripts\python.exe -m pytest -q`: **35 Tests bestanden**; zwei nicht blockierende Deprecation-Warnungen aus `audioread` unter Python 3.14.
- Synthetische Kontrolle: Die Render-Metrik bevorzugt eine glatte Bridge mit abgesenkter Energie gegenüber einem gleichförmig lauten Übergangsfenster; eine fehlerhafte Variante blockiert die übrigen Scores nicht. Reale Hörvalidierung und Gewichtsabstimmung stehen bewusst noch aus.
- Read-only-Stichprobe auf dem vorhandenen Equal-Power-Rang-1 aus `help_to_breath_drop_bridge`: Gesamtscore 0,807; Energieform 0,516, Grenzglätte 0,929, harmonische Kontinuität 0,968 und rhythmische Stabilität 0,902; keine Metrikfehler. Das ist nur ein technischer Plausibilitätscheck, noch kein Qualitätsnachweis.
- `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten; `pytest 9.1.1` ist installiert und in `requirements-dev.txt` festgehalten.
- CLI und programmatischer Import laufen; verfügbare Renderer: `simple`, `fade`, `equal_power`, `tempo_fade`; alle gleichen dabei das Tempo an.
- `generate_transition_candidates()` erzeugt Kandidaten auf demselben normalisierten 44,1-kHz-Sample-Raster wie die Renderer; ein Integrationstest deckt 48→44,1-kHz-Cutpoint-Skalierung ab.
- Batch-Export testet WAV-Dateien, Manifest-Inhalt, Renderer-/Kandidaten-Rückverfolgbarkeit und den Schutz vor unbeabsichtigtem Überschreiben.
- Erster realer Batch: `output/batches/help_to_breath_first/`, Songpaar `05 - HELP_LESS.flac` → `07 - BREATH_LESS.flac`; ein 2-Takt-Kandidat (`candidate-6a5d9f74efd4ad1f`, beide 161,499 BPM) wurde als linearer und Equal-Power-Crossfade exportiert. Zwei 44,1-kHz-Stereo-WAVs à 63.102.084 Bytes, keine Rejections und keine Renderfehler.
- Erster realer Ranking-Lauf: `output/batches/help_to_breath_ranked/`; 48 Kandidaten aus 4×4 Taktgrenzen und 1/2/4 Takten wurden bewertet, die Top 3 als Equal-Power-WAV exportiert. Rang 1 ist `candidate-33640deded712342` mit Score 0,845; keine Ranking- oder Renderfehler. Noch keine menschlichen Bewertungen.
- High-Power-Ranking-Lauf: `output/batches/help_to_breath_high_power/`; 736 Kandidaten aus den letzten vier Source-Grenzen, allen nutzbaren Target-Grenzen und 2/4 Takten wurden bewertet, die globalen Top 3 als Equal-Power-WAV exportiert. Rang 1 (`candidate-a39b3732c9444fb6`, Score 0,927) verbindet Source-Takt 112 mit Target-Takt 65 bei 91,60 s; Source/Target liegen bei −5,33/−5,47 dB statt Target-Intro bei ungefähr −16 dB. Da die globalen Top 3 alle 2 Takte verwenden, exportiert `output/batches/help_to_breath_high_power_4bar/` zusätzlich den besten 4-Takt-Kandidaten (`candidate-966e75d1a240fc27`, Score 0,919, Target-Takt 63). Keine Ranking- oder Renderfehler; menschliche Hörbewertung offen.
- Drop-Bridge-Lauf: `output/batches/help_to_breath_drop_bridge/`; 14.196 kompatible Kandidaten aus allen nutzbaren Grenzen wurden mit `feature_baseline_v3` bewertet, die Top 3 als Equal-Power-Bridge nach Rendering-Protokoll 2 exportiert. Rang 1 (`candidate-5f8a2a500211a427`, Score 0,751) verbindet Source-Takt 50 (74,47 s) über 4 Takte mit Target-Takt 109 (157,52 s): nach Drop A fällt RMS um 3,36 dB auf −9,02 dB, vor Drop B liegt der Vorlauf bei −13,11 dB und der Anstieg beträgt 6,54 dB. Keine Ranking- oder Renderfehler; Hörurteil offen.
- Multi-Paar-Batch: `output/batches/all_music_adjacent_equal_power_20260721/`; 18 aufeinanderfolgende gerichtete Paare aus 19 Tracks wurden verarbeitet, `Deezl - BREATH_LESS.flac` wurde ausgeschlossen. Sechs Paare lieferten jeweils die Top 5 als Equal-Power-WAVs (30 WAVs insgesamt), zwölf Paare hatten wegen der harten Kandidatenfilter keine akzeptierten Kandidaten. Alle 18 Manifeste wurden geschrieben; es gab keine Renderfehler.
- `aufTAKTCl.exe` und `tmp/` sind lokal vorhanden. `ffmpeg 8.1` ist über `PATH` auflösbar und wurde mit `ffmpeg -version` erfolgreich ausgeführt. Eine vorherige Prüfung innerhalb der eingeschränkten Codex-Dateisandbox lieferte wegen fehlendem Zugriff auf das WinGet-Paketverzeichnis fälschlich „nicht gefunden“.
- Reales Entwicklungsset gemessen: 20 Tracks mit 44,1 kHz Stereo, ein Track mit 48 kHz Stereo.
- Bereits vorhanden: `output/combined_song.wav` (375,84 s) und `output/cut_song.wav` (214,70 s), beide 44,1 kHz Stereo. Das ist noch kein systematischer Batch-Vergleich.

### Verifiziert am 2026-08-04 (Codex, erster MLP-Trainingslauf)

- `self_supervised_train_validation_v1` speichert den vollständigen
  Dataset-/Modell-/Renderer-/Objective-/Optimierungsvertrag, atomare
  `best.pt`-/`latest.pt`-Checkpoints samt SHA-256, alle Loss-Komponenten und
  vertragsgeprüftes Resume. Epoche 0 ist die unveränderte Equal-Power-Kurve.
- Reale Instanz:
  `output/training_runs/time_shared_mlp_v1_objective_v4_seed20260804_20260804/`
  auf Dataset `f9044dc259b7296c8b28`, **45 Train / 9 Validation**. Alle 54
  Bridge-Waveform-Caches wurden aufgebaut; der Testsplit wurde nicht geladen.
- Validation-Loss: **0,305959 → 0,295999** in der besten Epoche 8
  (**−3,26 %**). Train-Loss in derselben Epoche: **0,320002 → 0,303996**
  (**−5,00 %**). Nach sechs Epochen ohne weitere Verbesserung stoppte der
  Lauf in Epoche 14.
- Auf Validation weichen die vorhergesagten `mix_position`-Kurven maximal
  0,185 und `low_end_position` maximal 0,038 von linear ab. Die maximale
  Standardabweichung zwischen Beispielen beträgt 0,101 beziehungsweise
  0,023; das Netz gibt damit keine einzelne konstante Kurve aus.
- Manifest-, History-, Best- und Latest-Hashes wurden erneut berechnet und
  stimmen. `best.pt` enthält Epoche 8, `latest.pt` Epoche 14.
- Der Proxy-Loss-Rückgang ist nur ein technischer Lernnachweis, kein
  Hörqualitätsnachweis. Der bestehende Testsplit ist durch das frühere
  Objective-v4-Hör-Gate bereits verbraucht; ein finaler Modellvergleich
  benötigt neue Audio-Hashes.
- `.venv\Scripts\python.exe -m pytest -q`: **84 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-04 (Codex, blinder MLP-Entwicklungsvergleich)

- `src.evaluation.ml_control_study` prüft Dataset-, Paarmanifest- und
  Best-Checkpoint-Hashes, lädt `best.pt` aus Epoche 8 und rendert Equal Power
  sowie die vorhergesagten MLP-Kurven mit identischem Kontext und gemeinsamer
  Peak-Absenkung. Die A/B-Zuordnung steht nur in `answer_key.json`.
- Vollständiger Satz:
  `output/control_studies/blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun/`
  mit **9 Paaren / 18 Float32-WAVs**, 44,1 kHz Stereo. Alle Audio-Hashes
  stimmen; A und B sind je Paar samplegleich, alle Werte endlich, maximaler
  Peak 0,98.
- Der Objective-Loss sinkt in allen neun Paaren; im Mittel
  **0,305959 → 0,295999** (−3,26 %), paarweise rund 0,98–8,00 %. Diese Werte
  sind nur im Antwortschlüssel dokumentiert und werden vor der Bewertung
  nicht zur A/B-Zuordnung offengelegt.
- `ratings.json` verwendet Format 2 und steht auf `unrated`. Der Satz enthält
  alle Validation-Beispiele, darunter sechs Cue-Varianten von
  BREATH_LESS→BREATH_LESS und drei ASCENSION→BREATH_LESS. Wegen Modellwahl
  auf demselben Split ist dies kein unabhängiger Test.
- Ein erster Export mit der üblichen Obergrenze von drei Beispielen pro
  gerichteter Trackkombination bleibt unverändert als 6-Paar-Zwischenartefakt
  unter dem gleichnamigen Ordner ohne `_rerun` erhalten.
- `.venv\Scripts\python.exe -m pytest -q`: **87 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, Vocal-Control v2 und Objective v5)

- `vocal_time_shared_mlp_v2` erzeugt `mix_position`, `low_end_position`,
  `vocal_position`, getrenntes `vocal_duck_a/b` und die resultierenden
  `vocal_gain_a/b`. Mix-, Low-End- und Vocal-Position bleiben konstruktiv
  monoton mit festen Endpunkten; Ducking ist an beiden Enden exakt null.
- Der stem-fähige Renderer bildet pro Track `mix - Demucs-Vocal`, rendert den
  Rest zweibandig und addiert beide Vocal-Stems mit unabhängigen Gains.
- Objective v5 ergänzt `vocal_stem_overlap`, `vocal_audibility` und
  `vocal_mid_phrase_gain_change`. Synthetische Tests bestätigen: unnötiges
  Absenken eines aktiven Einzelvocals erhöht Audibility-Loss; Ducking bei zwei
  aktiven Vocals senkt den Stem-Overlap-Term.
- Vocal-Bridge-Cacheformat 2 enthält vier samplegleiche Float32-Stereoarrays
  und bindet beide Demucs-Artefakt-SHAs in den Cache-Key ein. Reale Sonde
  `example-c0a82769f650d763`: viermal `(2, 67328)` bei 11.025 Hz, erster Lauf
  Miss, direkter Wiederholungslauf Hit.
- Reale Gradientensonde: Objective v5 `0,365197`, davon v4 `0,302488`,
  Audibility `0,125145`, Stem-Overlap `0` und Mid-Phrase-Änderung `0,000684`;
  alle Gradienten endlich.
- Der additive v2-Trainingsrunner wurde anschließend separat implementiert;
  der v1-Vertrag und seine Checkpoints bleiben unverändert. Die Objective-
  Gewichte bleiben wegen der kleinen Hörstichprobe Entwicklungsparameter.
- `.venv\Scripts\python.exe -m pytest -q`: **92 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, Vocal-reicher Objective-v5-Hörsatz)

- Die Auswahl bewertet Vocal-Aktivität in exakt den 32 Halbbeat-Bins des
  Source-Postrolls und Target-Prerolls. Beide Seiten müssen im Mittel
  mindestens `0,15` erreichen; je gerichteter Paarung wird nur ein Cue und
  je Track höchstens zwei Verwendungen zugelassen. `STRUGGLING` kommt nicht
  vor.
- Vollständiger geblendeter Satz:
  `output/control_studies/blind_v7_objective_v5_vocal_active6_20260805_rerun/`
  mit sechs Paaren / zwölf Float32-WAVs bei 44,1 kHz. Die Source-Mittelwerte
  reichen von `0,374` bis `0,894`, Target von `0,491` bis `0,792`; je Paar
  sind 13 bis 32 von 32 Bins gleichzeitig vocal-aktiv über `0,2`.
- Beide A/B-Varianten verwenden denselben Vocal-Renderer, Kontext und
  gemeinsamen Peak-Gain. Verglichen werden Objective-v4-Mix-/Low-End-
  Controls ohne Ducking gegen vollständig optimierte Objective-v5-Controls.
- Der Objective-v5-Loss sank in allen sechs Paaren um rund 6,9–20,1 %.
  Alle WAV-Hashes stimmen, A/B sind je Paar samplegleich, alle Werte endlich
  und der gemeinsame Peak liegt bei höchstens 0,98.
- Nach vollständiger geblendeter Bewertung und anschließender Entblindung:
  Objective v5 **2 Siege**, Objective v4 **1 Sieg**, **3 Gleichstände**.
  Der Mittelwert über fünf Kriterien steigt `4,2333→4,3667`; ausschließlich
  Vocal-Klarheit steigt (`4,3333→5,0`). Sauberkeit, Energie, Low-End und
  Artefaktfreiheit sind identisch.
- Nutzerentscheidung 2026-08-05: `rhythmic_stability` wird aus neuen
  Control-Modell-Ratings entfernt, weil die verglichenen Controls Beat-Grid
  und Time-Stretch nicht beeinflussen. Ratings-Format 3 speichert fünf
  Kriterien; historische Versionen 1/2 bleiben lesbar.
- Paar 2, 3 und 5 verwenden `ffmpeg_librubberband` mit Faktoren 0,9697,
  0,9697 und 0,9706. Der Nutzer hört in beiden Methoden ein schlechtes
  Target; diese drei Gleichstände validieren primär den gemeinsamen
  Time-Stretch-Pfad, nicht die Vocal-Controls.
- Gelernt (2026-08-05, erster Exportversuch): Ein Sandbox-Start von FFmpeg
  scheiterte beim zweiten Paar mit `WinError 5`; der unvollständige Ordner
  ohne `_rerun` blieb unverändert, der freigegebene `_rerun` ist vollständig.
- `.venv\Scripts\python.exe -m pytest -q`: **97 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, erster Vocal-v2-Trainingslauf)

- `self_supervised_vocal_train_validation_v2` bindet Modellformat 2,
  Control-Protokoll 4, Objective v5, Vocal-Cacheformat 2 und `htdemucs` in
  einen unveränderlichen Vertrag. Pfad und SHA-256 aller tatsächlich
  verwendeten Cachemanifeste werden gespeichert. Checkpoints und History
  werden atomar geschrieben; Resume prüft Vertrag und Latest-Checkpoint-Hash.
- Reale Instanz:
  `output/training_runs/vocal_time_shared_mlp_v2_objective_v5_seed20260805_20260805/`
  auf Dataset `f9044dc259b7296c8b28`, **45 Train / 9 Validation**. Train und
  Validation besitzen vollständige Vocal-Waveform-Caches; der Testsplit
  blieb mit **0/9** absichtlich unangetastet.
- Validation-Loss: **0,267815 → 0,259337** in der besten Epoche 16
  (**−3,17 %**). Nach sechs Epochen ohne weitere Verbesserung stoppte der
  Lauf in Epoche 22. Train-Loss bis Epoche 16: **0,243792 → 0,225894**
  (**−7,34 %**).
- Auf Validation sinken `vocal_stem_overlap` um **26,70 %** und
  `vocal_audibility` um **25,27 %**. Gleichzeitig steigen der alte
  `loss_v4` um **5,05 %**, `energy_shape` um 4,21 % und
  `vocal_mid_phrase_gain_change` um 27,78 %. Der Gesamt-Proxygewinn stammt
  damit gezielt aus den neuen Vocal-Termen und muss hörend bestätigt werden.
- Die gelernte Validation-Sonde zeigt vor allem Source-Ducking: Mittelwert
  `0,1452`, Maximum `0,5088`; Target-Ducking bleibt klein (Mittelwert
  `0,0037`, Maximum `0,0092`). Alle Positionen bleiben monoton und alle
  Ducking-Endpunkte liegen numerisch bei null.
- Manifest-, History-, Best- und Latest-Hashes wurden erneut berechnet und
  stimmen. `best.pt` enthält Epoche 16, `latest.pt` Epoche 22.
- `.venv\Scripts\python.exe -m pytest -q`: **100 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, erweiterter 145–165-BPM-Datensatz und Retraining)

- Rekursiver Inventarbestand: **119 FLAC-Pfade**. Vor dem Songranking wurden
  `STRUGGLING` per Policy, ein SHA-identisches Duplikat von BREATH_LESS und
  sechs Tracks unter 145 BPM ausgeschlossen; kein Track lag über 165 BPM.
  Die Grenzen sind inklusiv und stehen in Batch- und Datasetmanifest.
- `output/batches/all_music_recursive_bpm145_165_top1_20260805/` enthält
  **111/111 abgeschlossene Quellen und Paarmanifeste, 0 Fehler**. Die
  Paarmanifeste enthalten 1.730.938 Kandidaten mit BPM 147,656–161,499;
  kein Kandidat liegt außerhalb des Vertrags.
- Dataset `52bc9d1cebfd1b82d2ea` unter
  `output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805/`:
  1.110 ausgewählte Cues vor Splitfilterung, 630 Cross-Split-Verwerfungen,
  **480 Exportbeispiele = 370 Train / 50 Validation / 60 Test**. Verwendete
  Trackhashes: 43/5/7, keine Überschneidung. Alle fünf Dateihashes stimmen.
- Neuer Trainingslauf:
  `output/training_runs/vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805/`.
  Beste Validation in Epoche 22, Early Stopping in Epoche 28. Train-Loss
  **0,307197→0,269025 (−12,43 %)**; Validation
  **0,359040→0,336999 (−6,14 %)**.
- Auf Validation verbessern sich `loss_v4` um **4,83 %**, `energy_shape` um
  **8,79 %**, `vocal_stem_overlap` um **44,39 %** und `vocal_audibility` um
  **10,04 %**. `vocal_mid_phrase_gain_change` steigt dagegen um
  **204,28 %** und bleibt das wichtigste Hör-Risiko.
- Das neue Modell duckt auf den 50 Validation-Beispielen eher Target-Vocals
  (Mittel 0,1689, Maximum 0,7164) als Source-Vocals (Mittel 0,0401, Maximum
  0,5107). Alle Positionen bleiben monoton und Ducking-Endpunkte null.
- Alle 420 Train-/Validation-Cachemanifest-Hashes, History sowie Best-/Latest-
  Checkpoint stimmen. Best enthält Epoche 22, Latest Epoche 28. Für **0/60**
  Testbeispiele wurde ein Vocal-Waveform-Cache erzeugt.
- Gelernt (2026-08-05, erster erweiterter Batchversuch): Das Tool-Timeout
  beendete den Shell-Wrapper, nicht dessen Python-Kindprozess. Mehrfaches
  Fortsetzen auf demselben Ordner erzeugte zwei `FileExistsError`; der
  kollidierte Top-3-Zwischenordner bleibt unverändert. Für den sauberen
  Top-1-Lauf wurde genau ein Prozess in einem neuen Ordner verwendet.
- `.venv\Scripts\python.exe -m pytest -q`: **105 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, CUDA-Aktivierung)

- Lokale GPU: **NVIDIA GeForce RTX 5070 Ti**, 16 GB VRAM, Compute Capability
  12.0. NVIDIA-Treiber 610.74 meldet CUDA UMD 13.3.
- Die Projekt-`.venv` verwendet jetzt **PyTorch 2.13.0+cu130** statt des
  CPU-Wheels. `torch.cuda.is_available()` ist wahr; eine reale Tensor- und
  Gradientenprobe lief auf `cuda:0` mit endlichen Gradienten.
- Beide Trainingsrunner lösen den neuen Default `auto` vor Erstellung des
  Run-Vertrags auf `cuda:0` oder `cpu` auf. Ein vollständiger synthetischer
  Train-/Validation-Lauf auf `cuda:0` schrieb den erwarteten CUDA-Vertrag.
- Neue Demucs-Separationen verwenden denselben Auto-Device-Pfad und schreiben
  `compute_device` additiv ins Stemmanifest. Vorhandene gültige Stem-Caches
  bleiben unverändert und werden nicht neu berechnet. Eine reale HT-Demucs-
  Sonde auf einer synthetischen Sekunde Stereo-Audio lief auf `cuda:0`, gab
  vier endliche Stems zurück und belegte maximal rund 793 MiB GPU-Speicher.
- CUDA-Backward-Kernel für lineares Upsampling und adaptives Average-Pooling
  sind in PyTorch 2.13 nicht strikt deterministisch. Sie laufen deshalb unter
  CUDA mit Determinismuswarnung; für bitgenaue Wiederholung bleibt
  `--device cpu` verfügbar. Historische CPU-Runs benötigen beim Resume
  weiterhin ausdrücklich `--device cpu`.
- `.venv\Scripts\python.exe -m pytest -q`: **109 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen. `.venv\Scripts\python.exe -m pip check`:
  keine defekten Abhängigkeiten.

### Verifiziert am 2026-08-06 (Codex, Vocal-v2-Modell-Hörsatz)

- `src.evaluation.vocal_ml_control_study` prüft Runformat, Runnername,
  Modellvertrag, Dataset-ID/-Manifesthash sowie SHA-256 und Epoche des
  Best-Checkpoints. Verglichen werden die ungelernte Vocal-v2-Initialisierung
  und der Best-Checkpoint aus Epoche 22 im identischen stem-fähigen Renderer.
- Die Auswahl arbeitet ausschließlich auf `validation`, verlangt auf beiden
  Seiten mittlere Vocal-Stärke mindestens `0,15`, verwendet höchstens einen
  Cue pro gerichteter Paarung und begrenzt die Tempoanpassung auf `0,5 %`.
  Der aktuelle Split liefert fünf unterschiedliche gerichtete Paarungen;
  tatsächlich benötigen alle **0,0 %** Tempoanpassung (`tempo_backend =
  not_needed`).
- Vollständiger geblendeter, noch unbewerteter Satz:
  `output/control_studies/blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806/`
  mit fünf Paaren / zehn Float32-WAVs bei 44,1 kHz. Source-Vocal-Stärke
  `0,353–0,796`, Target `0,188–0,911`; 7 bis 32 von 32 Bins sind gleichzeitig
  über `0,2` aktiv.
- Alle öffentlichen WAV-Hashes stimmen; A/B sind je Paar samplegleich,
  endlich und haben gemeinsame Peak-Absenkung auf höchstens 0,98.
  `ratings.json` verwendet Format 3 und enthält **0/5 Ratings**; ein
  `study_results.json` existiert noch nicht. `answer_key.json` wurde zur
  Wahrung der Blendung nicht geöffnet.
- Der Objective-v5-Proxy verbessert sich pro Paar nicht einheitlich: zwei
  Paare sinken, drei steigen. Damit darf der Trainingsmittelwert nicht als
  Ersatz für die ausstehende Hörbewertung interpretiert werden.
- `.venv\Scripts\python.exe -m pytest -q`: **111 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

## Abgleich mit dem geplanten Systemablauf

| Komponente aus dem Exposé | Umsetzungsstand | Nachweis / Lücke |
|---|:--:|---|
| 1. Audioimport & Abschnittsauswahl | 🟡 | Zwei Audiodateien können verarbeitet werden; Abschnittsgrenzen sind manuelle Sample-Cutpoints. Mehrere Songs, Abschnittsobjekte und Reihenfolge-Constraints fehlen. |
| 2. Musikanalyse | 🟡 | BPM, Beats, Downbeats, Taktpositionen und HT-Demucs-basierte Vocal-Aktivität sind vorhanden. Phrasen-/Segmentgrenzen, Strukturtypen und eine plattformunabhängige Downbeat-Lösung fehlen. |
| 3. Kandidatengenerierung | 🟡 | Bar-synchrone 2/4-Takt-Kandidaten über beide vollständigen Tracks mit vier vollständigen Drop-/Bridge-Fenstern vorhanden. Phrasen/Struktur und Vocal-Filter fehlen noch. |
| 4. Übergangsmetrik | 🟡 | `feature_baseline_v3` rankt Cutpoints vorab; `rendered_transition_baseline_v1` bewertet Renderergebnisse. Objective v5 enthält stem-basierten Vocal-Overlap und Audibility und gewann sein direktes Hör-Gate knapp 2:1 bei drei Gleichständen. Phrasen, Embeddings und eine gelernte Metrik fehlen. |
| 5. Rendering | ✅ | Hard Cut sowie lineare, Equal-Power-, Zwei-Band- und stem-fähige Vocal-Control-Renderer sind implementiert; Tempoangleichung und Drop-Grenzen sind getestet. |
| 6. Vorschau & Export | 🟡 | Batch-WAV-Export, auditierbares Manifest, Cue-Point-/Metrikvisualisierung und Notebook-Inline-Playback funktionieren. Auswahlworkflow und GUI fehlen. |

Damit ist die technische Grundlage aus Monat 1 weitgehend vorhanden. Das frühe Erfolgskriterium „automatisch erzeugt und systematisch vergleichbar“ ist erfüllt; v1- und Vocal-v2-Training sowie die direkten Objective-Hör-Gates sind abgeschlossen. Der Vocal-v2-Modell-Hörsatz ist gerendert, aber noch unbewertet. Offen sind dessen geblendete Bewertung, weitere Rater und der breitere wissenschaftliche Vergleich aus Monat 2–3.

## Fortschritt gegen die Startphase (Exposé Abschn. 13–14)

| Baustein | Status | Kurz |
|---|:--:|---|
| Reproduzierbares Repository | 🟡 | Git, MD-Doku und Requirements-Dateien vorhanden; aufTAKT und ffmpeg funktionieren lokal, sind aber externe Windows-Komponenten. aufTAKT ist technisch per SHA identifiziert, konkrete Lizenz/Weitergabeberechtigung bleibt ungeklärt. |
| Kleines Entwicklungsset (10–20 Tracks) | 🟡 | Technisch auf 119 lokale FLAC-Pfade beziehungsweise 111 eindeutige BPM-zugelassene Tracks erweitert; Kuratierung, Track-Notizen und Rechte fehlen weiterhin |
| Beat-/Bar-Analyse | ✅ | librosa + aufTAKT-Merge, mit Diskrepanz-Log |
| Mehrere gerenderte Übergänge | 🟡 | Automatischer Batch-Export vorhanden; erster realer 2-Varianten-Lauf HELP_LESS → BREATH_LESS ohne Fehler dokumentiert |
| Automatische Kandidaten | 🟡 | `bar_grid_v1` erzeugt standardmäßig 2/4-Takt-Varianten über alle nutzbaren Downbeats beider Songs; keine Phrasen-/Strukturinformationen |
| Systematischer Vergleich / Höranalyse | 🟡 | Gerankter Batch, Inline-Playback sowie bewertete blinde Control-/Objective-Hörsätze vorhanden; der aktuelle Vocal-v2-Modellhörsatz ist mit 0/5 Ratings noch offen, weitere Rater und ein breiterer Testsatz fehlen |
| Erste Baseline-Renderer (4 Stück) | ✅ | Tempoangepasster Hard Cut, linearer Crossfade, Equal-Power und Kompatibilitätsalias `tempo_fade` getestet |
| Einfache Feature-Metrik | ✅ | `feature_baseline_v3` mit High-Power- und Non-Overlap-Komponente, auditierbaren Messwerten und Top-k-Rendering |
| Render-Audio-Metrik | ✅ | `rendered_transition_baseline_v1` mit vier erklärbaren Komponenten, eigenem Ranking und Fehlerisolation im Batch-Manifest |
| Erste Embedding-Tests | ❌ | offen (Monat 3) |
| Liste typischer Fehlerfälle | 🟡 | fortlaufend in [`Bemerkungen.md`](./Bemerkungen.md), noch nicht vollständig systematisiert |
| Entscheidung ML-Fokus | ✅ | Self-supervised Feature→Control-Lernen ohne Ground-Truth-Kurven; differenzierbarer Renderer und eingefrorenes Objective als Lernpfad |

## Bekannte Bugs / Baustellen

- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als zusätzliche einfache Baseline bewusst behandeln; alle Renderer verwenden den tonhöhenerhaltenden Rubber-Band-`TimeStretch`.
- **Time-Stretch-Hörvalidierung**: Rubber Band wurde im neuen Hörsatz real verwendet, aber Paar 5 klingt laut Nutzer in beiden Methoden schlecht. Noch offen ist die isolierte Diagnose Originalsegment versus gestretchtes Segment versus musikalisch ungeeignetes Target-Fenster.
- **Downbeat-Fallback**: Bei fehlenden Taktinformationen bleibt ein approximatives 4/4-Raster für explizite Experimente verfügbar. Es ist jetzt per Provenienz von erkannten Downbeats unterscheidbar und wird von der Kandidatengenerierung standardmäßig abgelehnt. Historische Artefakte ohne Provenienz bleiben methodisch `unknown`.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Kandidatengenerierung).
- **Repo-/Cache-Hygiene**: Neue Caches sind Audio-SHA-/Analyse-ID-adressiert und kollidieren nicht über Track-Stems. Historische Stem-Caches bleiben unverändert; darunter befindet sich ein zusätzlicher veralteter `HELP_LESS`-Eintrag ohne gleichnamigen aktuellen Audio-Stem.
- **aufTAKT-Lizenz**: Die eingecheckte Binärdatei ist per SHA-256 fixiert, aber ihre exakte Quelle und Weitergabeberechtigung sind nicht belegt. Vor Veröffentlichung klären beziehungsweise Binary aus dem Distributionsartefakt entfernen.

## GUI-Frage: jetzt oder später? (Entscheidung)

**Empfehlung: noch kein echtes GUI — vom Exposé bestätigt** (GUI ist nur Interaktionsschicht; Risiko 15: „GUI-/Audio-Engineering verdrängt den Forschungsbeitrag"). Erst die Pipeline tragfähig machen und billig „sehen & hören" ermöglichen. Ein ausgebautes GUI lohnt sich erst, wenn Kandidaten + Metrik stehen und es einen Workflow gibt, den es einpackt (gerankte Kandidaten durchblättern, probehören, annehmen/verwerfen) — laut Zeitplan Monat 4.

Billiger Zwischenschritt statt GUI: `matplotlib`-Visualisierung (Waveform/Spektrogramm + (Down)Beats + Übergangsfenster) und ein Jupyter-Notebook (oder dünnes Streamlit/Gradio) mit Inline-Playback (`IPython.display.Audio`).

## Next Steps (priorisiert)

Ziel: den neuen Lernkern zuerst als messbare Schleife
**Controls → differenzierbar rendern → Objective → optimieren → anhören**
auf realem Audio validieren.

**Abgeschlossen am 2026-07-17:** programmatische Pipeline, Audio-Normalisierung, vier Rendering-Baselines, versionierter Rendering-Vertrag und automatisierte Tests.

**Abgeschlossen am 2026-07-29:** versionierter differenzierbarer Zwei-Control-Renderer, direkte Kurvenoptimierung sowie acht reale Baseline/Optimiert-WAVs aus vier unterschiedlichen 4-Takt-Paaren mit vollständiger Provenienz.

**Abgeschlossen am 2026-07-30:** acht geblendete v3-Paare vollständig bewertet und erst danach entblindet; v2 liegt nahe an Equal Power, zeigt aber noch keinen konsistenten Vorteil.

**Abgeschlossen am 2026-07-30:** Control-/Objective-v3 begrenzt lokale Kurvensprünge konstruktiv; alle acht Vergleichspaare wurden mit Rendering-Protokoll 5 neu gerendert.

**Abgeschlossen am 2026-07-31:** alle 16 globalen Paarfeatures, atomarer Feature-Datasetexport und SHA-basierte track-getrennte Train/Validation/Test-Splits; realer 45/9/9-Datensatz mit gültigen Demucs-Vocals.

**Abgeschlossen am 2026-08-04:** zurückgehaltener Objective-v4-Hörsatz vollständig bewertet und entblindet; optimierte Kurven gewinnen 9/9 gegen Equal Power, mit Vorteil ausschließlich bei Sauberkeit.

**Abgeschlossen am 2026-08-04:** versionierter, reproduzierbarer MLP-Trainingsrunner und erster realer 45/9-Train/Validation-Lauf; beste Validation in Epoche 8, Early Stopping in Epoche 14.

**Abgeschlossen am 2026-08-05:** Vocal-Control-Modell v2, stem-fähiger differenzierbarer Renderer, Objective v5 mit Vocal-Audibility-Loss und Vocal-Bridge-Cacheformat 2 samt realer Gradientensonde.

**Abgeschlossen am 2026-08-05:** sechs gezielt Vocal-reiche Objective-v4/v5-A/B-Paare vollständig bewertet und erst danach entblindet; v5 gewinnt 2:1 bei drei Gleichständen und verbessert ausschließlich Vocal-Klarheit.

**Abgeschlossen am 2026-08-05:** separater versionierter Vocal-v2-Trainingsrunner und erster realer 45/9-Train-/Validation-Lauf; beste Validation in Epoche 16, Early Stopping in Epoche 22.

**Abgeschlossen am 2026-08-05:** rekursiver 145–165-BPM-Datenlauf, fehlerfreier 111-Paar-Batch, erweiterter 370/50/60-Datensatz und Vocal-v2-Retraining; beste Validation in Epoche 22, Early Stopping in Epoche 28.

**Abgeschlossen am 2026-08-06:** geblendeter Vocal-v2-Modell-Hörsatz mit fünf vocal-aktiven, gerichteten Validation-Paaren ohne Time-Stretch; Best-Checkpoint aus Epoche 22 gegen die ungelernte Initialisierung. Der Satz ist weiterhin **0/5 bewertet**, und es gibt noch kein `study_results.json`.

1. **Time-Stretch und Target-Fenster von Paar 5 isolieren** — Original-Targetsegment und Rubber-Band-Variante mit identischem Ausschnitt separat exportieren und hören. So wird unterschieden, ob der schlechte Klang vom Backend, der Tempoänderung oder bereits vom gewählten Aversion-Fenster stammt.
2. **Feature-Protokoll 1 auditieren** — globale Paarfeatures, Datasetexport und track-getrennte Splits sind implementiert. Als Nächstes die Vocal-Scores gegen gehörte Lyrics-/Clash-Fälle prüfen und ein semantisch passendes Phrasenverfahren validieren. Kein stilles 4/4→8-Takt-Fallback; Downbeat-Fallbacks bleiben über `source_grid`/`target_grid` sichtbar.
3. **Objective v5 direkt hörvalidieren** — Gate bestanden: 2 v5-Siege, 1 v4-Sieg, 3 Gleichstände; Vocal-Klarheit `4,3333→5,0`. Für endgültige Gewichte später mit mehr Ratenden und ohne Time-Stretch-dominierte Paare wiederholen.
4. **Gelerntes Vocal-v2-Modell hörvalidieren** — Hörsatz ist gerendert: fünf vocal-aktive gerichtete Paarungen, alle ohne Time-Stretch; aktuell **0/5 Ratings**, noch kein `study_results.json`. Als Nächstes A/B vollständig bewerten, erst danach entblinden und auswerten; dabei starkes Target-Ducking und Mid-Phrase-Pegeländerungen gezielt notieren. Objective-Gewichte oder Architektur erst nach diesem Gate ändern.
5. **Entwicklungsset kuratieren** — die 111 eindeutigen BPM-zugelassenen Tracks als reproduzierbares Set definieren, Varianz prüfen, Track-Notizen ergänzen und Lizenzfrage klären (parallel, eher Handarbeit).

Danach: TCN-/BiLSTM-Hauptmodell und Mid-/High-Controls als neue Modellversion untersuchen sowie vortrainierte Embeddings auf demselben trackgetrennten Evaluationssatz vergleichen.

### Verifiziert am 2026-08-12 (TCN/BiLSTM-Hauptmodell, Architektursonde)

- Eine additive `tcn_bilstm_transition_control_v1`-Architektur ist unter
  `src/ml/model.py` implementiert. Sie verwendet einen für A/B geteilten
  temporalen Conv1d-Encoder `54 → 64 → 128`, die Fusion
  `[A, B, A-B, A*B]` mit `512 → 256`, die Projektion der 16 globalen
  Paarfeatures und einen zweilagigen bidirektionalen LSTM mit
  `input_size=256` und `hidden_size=128`.
- Der Controller gibt pro Halbbeat zehn sigmoid-beschränkte Werte als
  `(B, 32, 10)` aus: Gain A/B, Low-/Mid-/High-EQ A/B, Low-End-Ownership und
  Vocal-Ducking. Der Einstieg ist `python -m src.ml model-info-tcn-bilstm`.
- Ein separater `train-tcn-bilstm`-Runner nutzt den additiven
  `DifferentiableFullBandTransitionRenderer` mit Low-/Mid-/High-Band,
  sechs EQ-Gains und Vocal-Ducking. Der generische Datensatz verwendet für
  Vocal-Ducking den dokumentierten Mid-Band-Proxy; die Renderer-API kann
  alternativ Vocal-Stems verarbeiten.

### Verifiziert am 2026-08-12 (TCN/BiLSTM-Trainingslauf)

- Der aktuelle erweiterte SHA-getrennte Datensatz mit 370 Train- und 50
  Validation-Beispielen wurde auf `cuda:0` trainiert. Bridge-Waveform-Caches
  wurden vollständig materialisiert und anschließend wiederverwendet.
- Der Lauf
  `output/training_runs/tcn_bilstm_transition_control_v1_extended_bpm145_165_top10_20260812`
  stoppte nach Epoche 10 per Early Stopping; der beste Checkpoint liegt in
  Epoche 4.
- Der Validation-Proxy-Loss sank von `0,4210349` auf `0,4139656`. Der
  manifestierte SHA-256 des Best-Checkpoints wurde geprüft und der Checkpoint
  mit `weights_only=True` geladen. Eine Vorhersage hatte die Form
  `(1, 32, 10)` und positive monotone Mix-/Low-End-Schritte.
- Der Testsplit blieb unberührt; v1/v2-Runs und Checkpoints wurden nicht
  verändert.

### Verifiziert am 2026-08-12 (TCN/BiLSTM Full-Band-Renderer und Training)

- `DifferentiableFullBandTransitionRenderer` verarbeitet drei Bänder:
  Low `<180 Hz`, Mid `180–3500 Hz` und High `>3500 Hz`. Alle zehn
  Modellkanäle beeinflussen differentiabel das gerenderte Audio; mit
  Vocal-Stems wird Ducking auf die tatsächlichen Stems angewendet.
- Der neue Lauf
  `output/training_runs/tcn_bilstm_transition_control_v1_full_band_extended_bpm145_165_top10_20260812`
  stoppte nach Epoche 20 per Early Stopping; der beste Checkpoint liegt in
  Epoche 14.
- Der Validation-Proxy-Loss sank von `1,9383116` auf `0,3206756`. Der
  Best-Checkpoint-SHA wurde geprüft und mit `weights_only=True` geladen; die
  Vorhersage besitzt die Form `(32, 10)` für ein einzelnes Beispiel und zeigt
  nicht-konstante zeitabhängige EQ-/Ownership-Controls.
- Die vollständige Suite umfasst **142 bestandene Tests**; vier bekannte
  Warnungen bleiben bestehen.

## Offene Fragen / Entscheidungen (technisch)

- BPM-/Beat-Grid: was ist maßgeblich, wenn librosa und aufTAKT abweichen (HELP_LESS 161 vs. 157)?
- Übergangslänge: **entschieden am 2026-07-21** — Kandidaten führen sie kanonisch in Takten und leiten die für FadeCut benötigten Beats aus dem analysierten Fenster ab. Offene Folgefrage: Wie sollen spätere Renderer mit wechselndem Metrum umgehen?
- Vocal-Overlap: HT-Demucs-Scores sind verfügbar; offen ist ihre Kalibrierung und ob sie als harter Filter, weiche Metrik-Penalty oder nur als Modelleingang verwendet werden.
- **aufTAKT (Windows-Binary) vs. plattformunabhängiges Downbeat-Tracking** (z. B. madmom) — Reproduzierbarkeit vs. Aufwand.
- Rechte an den Testtracks (HELP_LESS/BREATH_LESS) — eigene Produktion oder lizenzpflichtig? (Exposé Abschn. 8: rechtlich handhabbares Set nötig.)
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?

_Vom Exposé bereits beantwortet: Forschungsfrage, Scope/Abgrenzung, Rolle der GUI, Related-Work-Rahmen, Evaluationsansatz, ML-Priorisierung._
## Verifiziert am 2026-08-21: Realer Dataset v2 abgeschlossen

Die reale variable Materialisierung ist unter neuen, eindeutigen Outputpfaden abgeschlossen. Die Korpusinventur akzeptierte 87 Tracks strikt mit Merge-v2; 24 Fallback-Tracks, 7 BPM-/Policy-Ausschlüsse und 1 Audio-SHA-Duplikat wurden nicht in den Batch übernommen. Der Batch enthält 87/87 Paarmanifeste mit 1.922.730 Kandidaten: 789.021 (2 Takte), 529.434 (4), 360.231 (6), 244.044 (8); alle sind v2-verifiziert und ohne `None`-Beatlängen.

Dataset v2: `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`, `dataset_id=2a9679f687c50696692b`. Pro Länge wurden exportiert: Train 105, Validation 12, Test 21; Sequenzlängen sind 16/32/48/64. Der Export umfasst 552 eindeutige Beispiele und verwendet eine gemeinsame Audio-SHA-Split-Autorität über alle Längen (87 Trackzuweisungen: 61/13/13). Die maschinelle Prüfung `DATASET_V2_VALIDATION_OK` bestätigte Shapes, finite Werte, transition_position, Manifest-/Dateihashes, Audio-SHA-Isolation und RoFormer-Provenienz.

Es wurde kein Training und kein Prompt 8 gestartet. Die abgeleitete Top-k-Auswahl liegt unter `output/batch_variable_v2_strict_20260820_selected_top3_run01`; die vollständigen Batchmanifeste bleiben unverändert erhalten. Der neue RoFormer-Cache liegt unter `output/feature_cache_variable_v2_roformer_20260821`; bestehende Demucs-/RoFormer-Artefakte wurden nicht überschrieben.

## Verifiziert am 2026-08-21: Fresh End-to-End-Review Variable-Length

Der additive Dataset-/ML-/Renderingpfad wurde frisch geprüft. Der reale Loader
öffnete ausschließlich `train` und `validation`: je Länge 105 Train- und 12
Validationbeispiele, insgesamt 420/48, mit T=16/32/48/64, endlichen Features,
korrekter `length_condition` und längenhomogenen Batches. Kein Test-Shard wurde
geladen.

Die neue Hardening-Prüfung behob und regressionsprüfte drei reproduzierbare
v2-Fehler: Split-Autoritätsdateien prüfen jetzt die deklarierte Mapping-SHA;
fractionale Längen werden nicht mehr still zu Integern gecastet; Candidate-v2
lehnt Nicht-4/4-Raster ab. Zusätzlich validiert der v2-Renderer die
L/Beat-Geometrie vor Audio-I/O. Die v1-Verträge und Modelle blieben unverändert.

Der kurze reale Feature-Trainings-Smoke nutzte je ein echtes Train- und
Validation-Featurebeispiel pro Länge, deterministische synthetische Waveforms
als expliziten Loss-Callback, CPU und W&B `disabled`. Zwei Epochen liefen über
alle vier Längen; Epoche 2 wurde aus dem SHA-geprüften Latest-Checkpoint von
Epoche 1 resumed. Gesamt-Validation-Loss: `0,2956906296` (Epoche 1) und
`0,2944503240` (Epoche 2). Gesamt- und Per-L-Metriken stehen in
`output/review_variable_v2_training_smoke_20260821_run01/history.json`; der
abschließende Reviewreport liegt daneben. Inferenz auf je einem Validationbeispiel
bestätigte endliche `(T,10)`-Controls und monotone Kurven für 2/4/6/8 Takte.

Vier neue reale Validation-Equal-Power-Renderings liegen unter
`output/review_variable_v2_e2e_20260821_run04/`. Sie verwenden je einen
samplegleichen Kandidaten aus der Validation, Rendering-Format 6, 44.100 Hz,
endliche Stereo-Float-WAVs und exakte Bridge-Samplegrenzen von 136.704,
268.288, 401.920 und 546.304 Samples für 2/4/6/8 Takte. Kandidaten mit
unterschiedlichen Source-/Target-Gridfenstern werden vom v2-Vertrag weiterhin
abgelehnt; der Pfad kürzt nicht still.

Die gezielte v2-/Hardening-/v1-Regression sowie die Batch-/Candidate-Regression
bestanden. Die vollständige Suite bestand frisch mit **199 Tests und 4
Warnungen in 46,34 s**. Die Warnungen sind die bekannten `aifc`-/`sunau`-
Deprecations und zwei CUDA-Determinismuswarnungen. Das ältere, separat bekannte
Librosa-/Numba-JIT-/`librosa.resample`-Problem wurde in diesem Lauf nicht
beobachtet und ist nicht als v2-Fehler zu werten.

Ein vollständiger realer CUDA-Trainingslauf wurde ausdrücklich nicht gestartet.
Der aktuelle v2-Runner ist eine API für bereits gebaute Train-/Validation-Batches;
ein realer v2-Waveform-Cache und ein eigener CLI-Subcommand fehlen noch. Der
empfohlene spätere Befehl nach Abschluss dieser Cache-/CLI-Stufe ist daher:

```powershell
.venv\Scripts\python.exe -m src.ml train-variable-tcn-bilstm output\datasets\variable_v2_strict_20260820_selected_roformer_run01 output\training_runs\variable_tcn_bilstm_variable_v2_full_cuda --waveform-cache-root output\ml_cache\variable_bridge_waveform_v2 --batch-size 8 --max-epochs 100 --device cuda:0 --wandb-mode disabled
```

Dieser Befehl wurde nicht ausgeführt; vor seiner Freigabe muss der neue
Waveform-Cache-/CLI-Pfad implementiert und separat verifiziert werden.

## Verifiziert am 2026-08-21: Waveform-v2-Alignment-Gate blockiert

Die vorgeschaltete Längenanalyse wurde ausschließlich auf den realen
Train-/Validation-Shards des Dataset-v2 ausgeführt: 420/48 Beispiele,
gleichmäßig 117 je Länge für 2/4/6/8 Takte. In den referenzierten aligned
Feature-/Beatgrid-Fenstern liegen Source- und Target-Bridge-Längen bereits bei
44.100 Hz systematisch auseinander: exakt gleich sind nur 85/468; 383/468
überschreiten ein strenges Rundungskriterium. Die Differenzbereiche betragen
−12.288…+8.704 (2 Takte), −8.192…+10.752 (4), −9.216…+12.288 (6) und
−15.360…+14.848 Samples (8). Die 46 eindeutigen RoFormer-Stem-Manifeste
sind vorhanden; ihre erwarteten tempoangepassten Gesamtlängen stimmen in
allen 468 Fällen mit den aligned Audio-Gesamtlängen überein. Die Ursache ist
damit die lokale Source-/Target-Griddauer, nicht fehlende Vocal-Provenienz.

Gemäß der Stopbedingung wurde keine willkürliche Cropping-, Padding- oder
Resampling-Regel eingebaut. Der zulässige nächste Vertrag ist ein
Reject-Vertrag um die reproduzierbare kanonische Länge
`round(transition_length_beats * 60 / source_bpm * training_sample_rate)`;
eine symmetrische Korrektur ist nur für echte Sample-Rundung zulässig und muss
für Mix und Vocal identisch sein. Der neue Waveform-Cache, sein CLI-Pfad,
CUDA-Smoke-Test und Resume bleiben bis zur Klärung der Grid-/Datenautorität
offen. Der Testsplit wurde in dieser Analyse nicht geöffnet.
