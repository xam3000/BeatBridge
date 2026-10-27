# Beobachtungen, Entscheidungen und Gelerntes

## 2026-10-26 — Related-Work-Kapitel in den Schreibstil des Nutzers überführt

- **Fragestellung/Reasoning:** Kann Kapitel 2 so umformuliert werden, dass es
  wie vom Nutzer selbst geschrieben klingt (Referenz: dessen Bachelorarbeit),
  ohne die am 2026-09-16 auditierten Claims, Zahlen, Quellen, Labels oder
  TODO-Kommentare zu verändern?
- **Eingaben/Setup:** Bachelorarbeits-PDF des Nutzers
  (`Move_to_the_Music__Analyzing_Dance_Synchronicity_using_Smart_Watch_Motion_Sensors.pdf`,
  51 Seiten, aus `C:\Users\max_h\Downloads`), vorheriger Stand von
  `overleaf/chapters/02_relatedWork.tex`, `overleaf/bibliography.bib`. Für die
  PDF-Textextraktion wurde `pypdf` in die Projekt-venv (`.venv`)
  nachinstalliert; der Extrakt liegt unter
  `C:\Users\max_h\AppData\Local\Temp\opencode\ba_thesis.txt`.
- **Prüflauf 1 (Stilanalyse, kein maschineller Test):** Vollständige Lektüre
  des Extrakts (Introduction, Related Work, Methods, Results, Conclusion).
  Stilmerkmale des Nutzers: Wir-Perspektive, kurze und direkte Sätze,
  Aufbau „X et al. machen …, dafür …, Ergebnis …", Verknüpfungen wie „For
  this"/„To do this"/„Because of this", ehrliche Limitationen („in our
  testing", „to the best of our knowledge"). Der Rewrite ersetzt die
  ChatGPT-typische dichte, nominalisierte Schreibweise durch diesen Stil;
  Inhalt, Abschnittstitel und Abschnittsreihenfolge blieben unverändert.
- **Prüflauf 2 (statische Strukturprüfung nach dem Rewrite):**
  `.venv\Scripts\python.exe C:\Users\max_h\AppData\Local\Temp\opencode\check_relatedwork.py`
  prüfte den neuen Kapiteltext gegen `bibliography.bib`. Ergebnis: 23/23
  zitierte Schlüssel definiert, Klammern ausgeglichen, keine
  `\begin`/`\end`-Umgebungen (wie zuvor), Kapitel und acht Abschnitte mit
  unveränderten Titeln, `\label{sec:related_work}` erhalten, beide
  TODO-Kommentarblöcke wortgleich erhalten, einziges Nicht-ASCII-Zeichen
  U+00FC (Argüello, wie zuvor), `$F_1$` zweimal (wie zuvor). Exit 0.
  `git -C overleaf diff --check` meldete keine Whitespace-Fehler;
  `diff --stat`: 20 Insertions/20 Deletions (eine Zeile pro Absatz, keine
  Strukturänderung).
- **Prüflauf 3 (lokaler LaTeX-Build):** Nicht ausführbar: weder `pdflatex`,
  `latexmk` noch `tectonic` sind auf diesem Rechner installiert (PATH und
  übliche Installationspfade geprüft). Der integrierte Compiler-Build vom
  2026-10-21 wurde in dieser Session nicht wiederholt; ein Kompilat des
  neuen Texts liegt daher nicht vor.
- **Schlussfolgerung/nächster Schritt:** Das Kapitel ist stilistisch
  überführt; Inhalt und Quellenlage sind maschinell geprüft unverändert.
  Beim nächsten Zugriff auf den integrierten LaTeX-Compiler den Gesamtbuild
  ausführen und die Related-Work-Seiten visuell prüfen. Hinweis: Kapitel 1
  und die übrigen Kapitel nutzen weiterhin die unpersönliche
  ChatGPT-Schreibweise; falls gewünscht, kann der gleiche Stilabgleich dort
  folgen.

## 2026-10-21 — Lokalen Thesis-Gesamtbuild repariert

- **Fragestellung/Reasoning:** Warum lässt sich das PDF beim Arbeiten im
  `overleaf`-Ordner nicht vollständig kompilieren, und kann die bestehende
  BibLaTeX-Literatur mit einem verfügbaren Backend verarbeitet werden?
- **Eingaben/Setup:** Aktueller unveränderter Overleaf-Inhalt als Baseline,
  `CGThesis.tex` als Hauptdatei, integrierter Codex-Desktop-LaTeX-Compiler.
  Die Arbeitskopie enthielt bereits Nutzeränderungen; diese blieben erhalten.
- **Testlauf 1 (Baseline):** Vollständige Kompilation von `overleaf/CGThesis.tex`
  mit `backend=biber`. Alle Kapitel wurden bis zum 61-seitigen XDV verarbeitet;
  danach meldete der Compiler beim externen Biber-Aufruf `program not found`
  und `compile-failed`. Literatur und Referenzen waren deshalb noch undefiniert.
  Schluss: Der lokale Bibliographieprozessor ist die konkrete Build-Blockade.
- **Testlauf 2 (isolierte Variante):** Der erste Python-Kopierversuch für
  `latex_compile_probe/` scheiterte mit `FileNotFoundError`, weil Unterordner
  nicht angelegt waren. Nach Korrektur wurden alle Projektquellen in die
  Testkopie kopiert und nur dort `backend=bibtex` gesetzt. Der vollständige
  Build dieser Kopie meldete `success`. Schluss: BibTeX ist in der
  integrierten Compilerumgebung für dieses Dokument nutzbar.
- **Testlauf 3 (tatsächliches Projekt):** `backend=bibtex` in
  `overleaf/cg.cls` gesetzt und `overleaf/CGThesis.tex` vollständig kompiliert:
  `success`. Nach bytegetreuer Wiederherstellung der ursprünglichen
  Dateiformatierung mit ausschließlich dieser einen Änderung wurde der
  Gesamtbuild erneut mit `success` ausgeführt. `git -C overleaf diff --check`
  meldete keine Whitespace-Fehler.
  Umfang: Build der gesamten Thesis einschließlich Literaturverarbeitung;
  keine inhaltliche oder visuelle Seitenprüfung. Der Overleaf-Online-Build
  wurde hier nicht separat ausgeführt.
- **Schlussfolgerung/nächster Schritt:** Die lokale PDF-Vorschau kann den
  Gesamttext wieder kompilieren. Bei weiteren Thesis-Änderungen den
  Gesamtbuild ausführen und die betroffenen Seiten visuell prüfen.

## 2026-10-15 — Einleitung nach Blueprint und Aufgabenstellung

- **Fragestellung/Reasoning:** Kann Kapitel 1 den praktischen
  Tanz-Mashup-Auftrag, die controllerzentrierte Forschungsfrage und die
  evidenzgebundenen Beiträge konsistent einführen, ohne offene Anforderungen
  als erfüllt auszugeben? Die offizielle Aufgabenstellung bleibt
  Scope-Autorität; das Blueprint liefert die operativen Fragen.
- **Eingaben/Setup:** Alle drei Seiten von
  `angepasste_aufgabenstellung_masterarbeit.pdf` wurden mit lokalem
  `pdfjs-dist` textuell gelesen; `pdftotext.exe` und Python-`pypdf` waren in
  den geprüften Runtimes nicht verfügbar. Dazu Blueprint, Projektstatus,
  Ergebnis- und Diskussionskapitel, Evidenzledger, relevante Methoden- und
  Protokolldateien. Die vier verwendeten Literaturquellen wurden anhand ihrer
  Primärveröffentlichungen gegengeprüft. Keine Experimentartefakte oder
  Audio-Dateien verändert.
- **Prüflauf 1 (statische LaTeX-Struktur):** `.venv\Scripts\python.exe -X
  utf8 -` prüfte `overleaf/chapters/01_introduction.tex` gegen
  `overleaf/bibliography.bib` und alle Kapitel-Labels. Ergebnis: vier
  vorhandene BibTeX-Keys, keine fehlenden `\ref`-Ziele, sechs eigene Labels,
  ausgeglichene Klammern und `\begin`/`\end`-Anzahlen, drei explizite
  TODO-Kommentare; Exit 0. Umfang: Textstruktur, keine inhaltliche Evaluation.
- **Prüflauf 2 (LaTeX-Kompilation):** Temporärer Standalone-Wrapper mit
  `report`-Klasse und vollständig eingebettetem Kapitel 1 unter
  `overleaf/introduction_compile_check.tex`. Codex-Desktop-Compiler meldete
  `success`; Wrapper danach entfernt. Kapitelverweise und Literatur wurden
  zusätzlich statisch geprüft; ein vollständiger Thesis-/BibLaTeX-Build und
  eine PDF-Sichtprüfung wurden nicht ausgeführt.
- **Prüflauf 3 (Diff/Umfang):** `git -C overleaf diff --check --
  chapters/01_introduction.tex chapters/06_discussion.tex` ohne Befund;
  `Measure-Object` ergab 1.732 Wörter für die Einleitung. Das ist nur ein
  Umfangsindikator, keine bestätigte Seitenzahl.
- **Schlussfolgerung/nächster Schritt:** Einleitung und Forschungsfragen
  stehen als wissenschaftlicher Text. Formale Scope-Entscheidung,
  Repräsentationsvergleich, gelernte Controller-Hörstudie, reale
  Cue-Ranker-Evaluation, Ein-/Drei-Takt-Fälle, GUI-Abnahme, finaler Export,
  Korrekturaufwand und Tanz-Nutzbarkeit bleiben offene Evidenzgates.

## 2026-10-15 — Evidenzgebundenes Diskussionskapitel

- **Fragestellung/Reasoning:** Kann Kapitel 6 die abgeschlossenen Ergebnisse
  entlang der operativen Forschungsfragen interpretieren, ohne Proxy-Loss,
  Direkt-Control-Hörurteile, gelernte Controller und synthetische Ranker-Checks
  zu vermischen? Offene Evidenz wurde als LaTeX-TODO erhalten.
- **Eingaben/Setup:** `overleaf/chapters/05_results.tex`,
  `docs/RESULTS_EVIDENCE_LEDGER.md`, Projektstatus, Methoden-/Implementierungs-
  kapitel, Kontrollstudien-, Ranking-, Dataset-, Analyse- und Cacheprotokolle
  sowie vorhandene `bibliography.bib`-Keys. Keine Audio-, Test-NPZ-, Checkpoint-
  oder Run-Artefakte verändert; kein Training oder Rendering.
- **Prüflauf 1 (Whitespace/Diff):** `git diff --check --
  overleaf/chapters/06_discussion.tex` im Repository-Root und
  `git -C overleaf diff --check -- chapters/06_discussion.tex`. Beide ohne
  Befund; der zweite Befehl prüft den tatsächlich geänderten Submodule-Text.
- **Prüflauf 2 (statische LaTeX-Verweise):** Erster `.venv\Scripts\python.exe
  -X utf8 -c`-Probeaufruf enthielt falsch escapte reguläre Ausdrücke und
  meldete fälschlich null Zitate/Labels; die Sonde wurde korrigiert. Der
  korrigierte `.venv\Scripts\python.exe -X utf8 -`-Lauf fand sieben verwendete
  Zitatschlüssel, alle in `overleaf/bibliography.bib`; keine fehlenden
  `\ref`-Ziele, acht eigene Labels, ausgeglichene geschweifte Klammern und
  `\begin`/`\end`-Anzahlen. Dies ist eine Strukturprüfung, keine inhaltliche
  Quellenverifikation.
- **Prüflauf 3 (isolierte LaTeX-Kompilation):** Temporärer Standalone-Wrapper
  `overleaf/discussion_compile_check.tex` mit `report`, `booktabs` und den
  vollständigen Kapiteln 5 und 6; der Codex-Desktop-Compiler meldete
  `success`. Wrapper danach entfernt. Keine vollständige Thesis-Kompilation
  und keine manuelle PDF-Sichtprüfung ausgeführt.
- **Schlussfolgerung/nächster Schritt:** Kapitel 6 ist syntaktisch
  kompilierbar und referenziert nur vorhandene BibTeX-Keys. Forschungsfragen
  in Kapitel 1, unabhängige Controller-/Ranker-Evaluation, GUI-Abnahme,
  Korpus-/Lizenzdaten und Teilnehmerprotokoll bleiben offene Evidenzgates.

## 2026-10-14 — Evidenzgebundenes Ergebniskapitel

- **Fragestellung/Reasoning:** Welche abgeschlossenen Experimente tragen
  belastbare Aussagen für `overleaf/chapters/05_results.tex`, und welche
  Hör- und Ranker-Aussagen bleiben ohne Primärergebnis offen? Zahlen wurden
  vor dem Schreiben in `docs/RESULTS_EVIDENCE_LEDGER.md` auf konkrete
  Manifeste, Histories, Audits und Studienergebnisse zurückgeführt.
- **Eingaben/Setup:** Repository-Regeln und Protokolle, vier lokale
  Datasetmanifeste, PRIVE-Pairbatches, vier September-Runmanifeste samt
  Histories/Checkpoints, Sweep-Analyse/CSV und Rating-/Result-Dateien.
  Ausschließlich Read-only-Prüfung der Experimentartefakte; kein Training,
  Rendering, Öffnen von Test-NPZ oder Audio, keine Commit-Erstellung.
- **Prüflauf 1 (Artefakt-Inventur):** PowerShell- und
  `.venv\Scripts\python.exe -`-Sonden lasen Dataset-`split_counts`,
  Batch-`sources[].pairs[]`, Runstatus und History-Epochen sowie
  Study-`status`, `sample` und `preference_counts`. Ergebnis: vier
  abgeschlossene September-Runs; Datasetzahlen und Batchzahlen wie im
  Ledger; drei ausgewertete Direkt-Control-Hörsätze; vier neuere Hörsätze
  ausdrücklich `unrated` ohne `study_results.json`. Die `.venv` meldete
  bei Python-Starts eine pyenv-Pfadwarnung, führte die Leseprüfungen aber
  erfolgreich aus. Schluss: Nur ausgewertete Hörsätze als Resultat melden.
- **Prüflauf 2 (Integrität):** `.venv\Scripts\python.exe -` berechnete
  SHA-256 für History, Best- und Latest-Checkpoint der vier September-Runs
  sowie den variablen IO-Audit und verglich sie mit den jeweiligen
  Runmanifesten. Ergebnis: 13/13 Dateien vorhanden und Hashes identisch;
  Datasetmanifest-SHAs der beiden verwendeten September-Datensätze stimmten
  mit den Runverträgen. Die Vocal-MLP-History protokolliert in Epoche 38
  `0.324840` gegenüber dem deklarierten Best-Checkpoint in Epoche 34 mit
  `0.324910`; die Differenz wird im Kapitel als Checkpoint-Auswahl unter
  `min_delta` offengelegt. Nächster Schritt: keine spätere History-Epoche
  stillschweigend als gespeichertes Bestmodell ausgeben.
- **Prüflauf 3 (Text-/LaTeX-Struktur):** `git diff --check` für Kapitel und
  Ledger ohne Befund; Python-Read-only-Sonde fand zwölf Labels, keine
  ungelösten kapitelinternen Referenzen, ausgeglichene Klammern und drei
  gepaarte Tabellenumgebungen. Vier Ratingdateien wurden erneut als
  `unrated` ohne Ergebnisdatei geprüft. Studienmanifeste bestätigten den
  historischen Testsplit für Objective v4 sowie `train`/`validation` für
  Objective v5; die Tabellenbezeichnungen wurden entsprechend korrigiert.
- **Prüflauf 3a (Best-Checkpoint-Metadaten):** Vier
  `.venv\Scripts\python.exe -`-Leseprüfungen mit
  `torch.load(..., map_location="cpu", weights_only=True)` öffneten die
  bereits SHA-geprüften September-Best-Checkpoints. Ergebnis: gespeicherte
  `epoch`, `best_epoch` und `best_validation_loss` stimmen mit den
  Kapitelwerten überein (1/0.415208, 34/0.324910, 18/0.320778,
  34/0.227169); Exit 0. Ein erster kombinierter Aufruf lieferte vor
  dem Standard-Wartefenster nur die pyenv-Pfadwarnung; die anschließenden
  getrennten Aufrufe mit 30-s-Wartefenster waren erfolgreich. Keine
  Modellinferenz oder Testdaten wurden ausgeführt.
- **Prüflauf 4 (isolierte LaTeX-Kompilation):** Temporärer Standalone-Wrapper
  mit `report`, `booktabs` und dem Ergebniskapitel unter
  `overleaf/results_compile_check.tex`; Codex-Desktop-Compiler meldete
  `success`; nach der Split-Textkorrektur wurde derselbe Standalone-Build
  erneut mit `success` ausgeführt. Der Wrapper wurde danach entfernt. Eine
  vollständige Thesis-Kompilation wurde nicht ausgeführt: die lokale Shell bot kein
  `latexmk`, `pdflatex`, `xelatex` oder `lualatex`, und der Desktop-Compiler
  unterstützt keine zusätzlichen Projektdateien.
- **Schlussfolgerung/nächster Schritt:** Das Kapitel berichtet nur
  manifestierte Daten-/Trainingsläufe, technische Batch-Ergebnisse und drei
  abgeschlossene Ein-Rater-Direkt-Control-Vergleiche. Finale unabhängige
  Controller-/Cue-Ranker-Evaluation und unbewertete Hörsätze bleiben TODO.

## 2026-10-02 — Bestätigungs-Sweeps für vlfwfn7a und fxhhidgi

- **Fragestellung/Reasoning:** Der Nutzer fordert Sweep-Konfigurationen,
  um die besten Konfigurationen zu bestätigen. Die beiden Spitzenruns
  unterscheiden sich nur um 0,014 %, deshalb unveränderte Parameter und
  gemeinsame Seeds statt erneuter Hyperparametersuche. Originalseed plus
  vier neue Seeds pro Konfiguration; volle 150 Epochen ohne Hyperband.
- **Eingaben/Setup:** CSV-Snapshot vom 2026-10-02, bestehende TCN-Sweep-YAML,
  `src/ml/__main__.py`, bestehender Runner und Agent-Guard. Vorhandene
  Nutzeränderungen in CLI und Dokumentation erhalten. Kein Commit erstellt.
- **Implementierung:** Zwei getrennte `method: grid`-YAMLs mit Seeds
  20260930–20260934 und unveränderten 20 festen Parameterwerten je Kandidat.
  Eigenständige Outputroots unter `output/training_runs/wandb_confirmation/`.
  Neue additive CLI-Option `--save-checkpoints` für den festen TCN-Sweep
  (Standard false) wird an den Runner weitergegeben. Best-/Latest-Dateien
  werden bei Bestätigung lokal gespeichert; YAMLs deaktivieren W&B-
  Checkpointuploads weiterhin explizit. Keine Variable-/Vocal-Runneränderung.
- **Testlauf 1:**
  `.venv\Scripts\python.exe -m pytest tests/test_tcn_confirmation_sweeps.py -q`.
  Umfang: beide YAMLs durch den tatsächlichen CLI-Pfad mit allen fünf Seeds,
  gemockter Trainingsfunktion und Sweep-Parameterquelle; Prüfung von
  Parametervertrag, Seed-only-Grid, fehlendem Hyperband, Datasetpfad,
  Outputisolation, 150 Epochen/Patience 151, min_delta 0,
  Checkpoints lokal an/Upload aus, Resume aus und unverändertem CLI-Standard.
  Ergebnis: **3 passed in 3.78s**, Exit 0. Keine Trainings-/Netzwerkaufrufe.
- **Testlauf 2:** `.venv\Scripts\python.exe -X utf8 -c` mit
  `csv.DictReader`, `yaml.safe_load` und JSON-Typkonversion der CSV-Werte.
  Beide YAMLs gegen ihre tatsächlichen Exportzeilen verglichen, alle
  festen Parameter einschließlich exakter Lernrate/Scheduler/Architektur;
  identische Seedlisten und getrennte Outputroots geprüft.
  Ergebnis: **40/40 Parametervergleiche identisch**, Exit 0.
- **Schlussfolgerung/nächster Schritt:** Konfigurationen lokal vorbereitet
  und CLI-Weitergabe geprüft, noch keine W&B-Registrierung und keine
  Bestätigungstrainings. Startbefehle in `docs/WANDB.md`. Nach Ausführung
  Mittelwert/Streuung und gepaarte Seed-Differenzen auswerten, Originalseed
  getrennt von den vier neuen Seeds berichten und Best-Checkpoints hören.
  Testsplit bleibt geschlossen.

## 2026-10-02 — Analyse des W&B-TCN-Sweep-Exports

- **Fragestellung/Reasoning:** Welche Konfigurationen liefern im vom Nutzer
  bereitgestellten Snapshot gute Validation-Scores, wodurch entstehen die
  Gewinne und begrenzen Abbrüche die Aussagekraft? Originalexport und
  vorhandene Arbeitsänderungen erhalten; ausschließlich Datenanalyse.
- **Eingaben/Setup:** CSV `wandb_export_2026-10-02T09_20_57.391+02_00.csv`
  (SHA `aa342d7813fcca2a5bdfc4cbb87445bc4d0b7970025ef7b597f125c7267a431e`),
  92 Runs/329 Spalten, lokale Sweep-Histories/Manifeste, Sweep-YAML und
  W&B-Logger. Alle Python-Aufrufe mit `.venv\Scripts\python.exe`.
- **Prüflauf 1:** Read-only CSV-Sonde via `python -X utf8 -c` mit
  `csv.DictReader`, Countern und Loss-Ranking. Ergebnis: ausschließlich
  `nqntmdi0`, 35 finished, 56 killed, 1 running ohne Loss. Keine Parsefehler.
- **Prüflauf 2:** Read-only CSV-Sonde via `python -X utf8 -c` mit
  Vertrags-Countern, Gruppenmedians, Metrikalias-Abgleich, Best-Epochen und
  finalen Loss-Abweichungen. Ergebnis: ein gemeinsamer Dataset-/Objective-
  Vertrag, Alias-Abweichungen 0, Top 4 bei 0,2616–0,2649, zwei deutlich
  verschlechterte finale Epochen. Die Suche nach `src/ml/objective.py`
  schlug fehl (Datei existiert dort nicht); Objective-Gewichte wurden danach
  aus den Runmanifesten gelesen. Kein Produktfehler.
- **Prüflauf 3:** Struktursonde auf History/Manifest von `vlfwfn7a` via
  `python -X utf8 -c`. Ergebnis: Epochenlisten mit Train-/Validation-
  Komponenten vorhanden, Best-Epoche 77 und Checkpointreferenz null.
- **Prüflauf 4:**
  `.venv\Scripts\python.exe -X utf8 scripts/analyze_wandb_export_20261002.py`.
  Scope: alle 91 Metrik-Runs, lokale History-Minima, SHA-Abgleich,
  Best-Epochen-Komponenten für Top 4 und `1w51w9t6`, Gruppenstatistik und
  JSON-Ausgabe. Exit 0, 91/91 Histories vorhanden, 0 Loss-Abweichungen,
  0 Hash-Abweichungen. Weighted-Komponentensummen stimmen innerhalb
  Floating-Point-Rundung (~1e-8) mit den jeweiligen Losses überein.
- **Prüflauf 5:** Zusammenfassungs-Sonde via `python -X utf8 -c` auf
  `summary.json`: Gruppenmedians für completed separat, Komponentensummen,
  Checkpointreferenzen und Manifestzustände. Ergebnis: 35 completed,
  56 weiterhin running in lokalen Manifesten trotz CSV killed,
  0 referenzierte Best-Checkpoints. Gewinner 17,30 % unter Completed-Median,
  Abstand Platz 1/2 nur 0,01386 %. Kein Ausführungsfehler.
- **Prüflauf 6:** Derselbe Analysebefehl nach Ergänzung der Matplotlib-Grafik
  erneut ausgeführt. Exit 0, Ergebnisse unverändert, PNG erfolgreich erzeugt.
  Grafik per `view_image` visuell geprüft: Achsen, Legenden, Runs und
  Kurven lesbar. Die eingegrenzte Loss-Achse blendet die hohe Initialisierung
  aus und ist im Bericht beschrieben. Keine Code-Tests oder Trainingsläufe
  ausgeführt, Testsplit und Audiodateien nicht geöffnet.
- **Blockade/Gelernt:** Beim ersten Auslesen des ZIP-basierten Repository-
  Skills scheiterte nur die Konsolenausgabe an CP1252 (`UnicodeEncodeError`).
  Wiederholung mit `-X utf8` erfolgreich; keine Änderungen am Skill.
- **Schlussfolgerung/nächster Schritt:** Export-Ranking und lokale Evidenz
  stimmen überein. Best-Konfigurationen mit mehreren Seeds und aktivierten
  Checkpoints bestätigen. `xdmd5cma` (killed nach Epoche 57, Loss 0,293404)
  mit vollem Budget prüfen; späte Verbesserung von `sifded82` zeigt das
  Risiko früher Selektion. Hörqualität bleibt offen. Vollständiger Bericht:
  `docs/WANDB_SWEEP_ANALYSE_20261002.md`. Keine Sweep-Konfiguration geändert,
  kein Commit erstellt.

## 2026-09-30 — TCN/BiLSTM-LR-Warm-up, Plateau-Scheduler und W&B-Metrik

- **Fragestellung/Reasoning:** Für die beiden TCN/BiLSTM-Modelle soll die
  gesweepte Basis-Lernrate anfangs linear hochgefahren und danach bei
  stagnierendem Validierungsverlust reduziert werden. Die Lernrate soll pro
  Epoche in W&B protokolliert und gegen die Epoche chartbar sein.
- **Eingaben/Setup:** `src/ml/runner.py`, `src/ml/variable_runner.py`,
  `src/ml/wandb_logging.py` sowie die beiden YAMLs unter `config/wandb/`.
  Bestehende Arbeitsänderungen in diesen Dateien blieben erhalten.
- **Änderung/Prüfumfang:** Beide Modelle verwenden nun 5 Epochen linearen
  Warm-up von 10 % auf 100 % der jeweiligen Sweep-Lernrate. Danach überwacht
  `ReduceLROnPlateau` den Validierungsverlust und halbiert die Lernrate nach
  10 Epochen ohne relevante Verbesserung; der absolute Schwellenwert ist
  `0.0001`, die Untergrenze 5 % der Basis-Lernrate. Für lokale TCN-Läufe beträgt
  die Standard-Patience nun 30 Epochen, damit der Plateau-Scheduler reagieren
  kann; Sweep-Runs behalten die deaktivierte lokale Early-Stop-Logik und laufen
  bis zum Epochenlimit oder W&B-Hyperband-Stopp. Scheduler-Zustand wird in
  Checkpoints gesichert und beim Resume geladen. Die Sweep-YAMLs halten die
  Scheduler-Werte fest. Der W&B-Logger loggt `learning_rate` und weist dieser
  Metrik `epoch` als Standard-Chartachse zu. Es wurden keine Test-, Trainings-
  oder Sweep-Läufe ausgeführt.
- **Schlussfolgerung und nächster Schritt:** Neue Sweeps müssen mit den
  aktualisierten YAMLs angelegt werden, damit die serverseitig gespeicherte
  Sweep-Konfiguration den LR-Scheduler enthält. W&B zeigt `learning_rate` in
  automatisch generierten Charts; bei manuell gepflegten Workspace-Layouts
  kann die nun verfügbare Metrik als Line-Plot hinzugefügt werden.

## 2026-09-30 — TCN-Sweep-Agent an das Projektvenv gebunden

- **Fragestellung/Reasoning:** Ein TCN-Sweep-Agent schlug beim Import von
  `librosa` fehl. Der Agent-Log zeigt den gestarteten Befehl als
  `python wandb_sweep.py ...`; in der interaktiven Shell löst `python` auf
  `C:\Python314\python.exe` auf. Der Fehler passt dazu, dass der Agent den
  globalen Interpreter verwendet, beweist dessen Auflösung im damaligen
  Agent-Prozess aber nicht unmittelbar.
- **Eingaben/Setup:** `wandb/debug-cli.max_h.log` sowie der Interpreter- und
  Importcheck
  `.venv\Scripts\python.exe -c "import sys; print(sys.executable); import librosa; print(librosa.__version__)"`.
  Das Projektvenv meldet seinen erwarteten Pfad und `librosa` 0.11.0.
- **Änderung/Prüfumfang:** Die `command`-Einträge der beiden TCN/BiLSTM-Sweep-
  YAMLs verwenden jetzt `.venv/Scripts/python.exe` statt `${interpreter}`.
  Die Befehle müssen vom Repository-Root gestartet werden. Es wurde kein
  Sweep, Training oder Testlauf gestartet.
- **Schlussfolgerung und nächster Schritt:** Die Trial-Ausführung ist in den
  geänderten Konfigurationen an das Projektvenv gebunden. W&B interpoliert
  Command-Makros beim Ausführen eines Sweep-Laufs; deshalb muss ein bereits
  angelegter Sweep mit der korrigierten YAML neu angelegt werden, damit seine
  gespeicherte Agent-Konfiguration den expliziten Interpreter enthält. Danach
  den Agent vom Repository-Root starten.

## 2026-09-30 — Erster TCN-Sweep-Trial abgeschlossen, Agent-Absturz danach

- **Fragestellung/Reasoning:** Der Benutzer meldete, dass der Sweep-Agent nach
  einem Lauf mit `ValueError: Value out of range: 3221226505` beendet wurde.
  Zu prüfen war, ob der Trial fehlschlug oder erst der Agent nach Abschluss.
- **Eingaben/Setup:** Sweep `kux6f586`, W&B-Run `6eqzbl9s`, lokaler Laufordner
  `output/training_runs/wandb_sweeps/tcn_bilstm_transition_control_v1/kux6f586/6eqzbl9s`.
  Interpreter: Projektvenv auf Python 3.14.2, W&B 0.28.1, PyTorch
  2.13.0+cu130; der Lauf nutzte `cuda:0`. Geprüft wurden `manifest.json`,
  W&B-`wandb-summary.json`, `debug.log`, `debug-internal.log` und die Windows-
  Application-/WER-Ereignisse um 19:58 Uhr.
- **Prüfumfang/Befehle:** Nur vorhandene Laufdateien, W&B-Logs und Windows-
  Ereignisse gelesen; kein weiterer Sweep, Trainings- oder Testlauf gestartet.
  Manifest und W&B-Zusammenfassung melden `completed`, Epoche 100, beste
  Epoche 93 und `best_validation_loss=0.31911887019872665`. Die W&B-interne
  Abschlussmeldung enthält `exit_code=0` und Uploadstatus `200 OK`. Windows
  protokolliert um 19:58:14 für Python 3.14.2 in `ucrtbase.dll` den Code
  `0xc0000409` mit Fast-Fail-Subcode 7 (`FAST_FAIL_FATAL_APP_EXIT`). Rund 20
  Sekunden später verarbeitet der Agent den Child-Prozess und scheitert beim
  Übergeben von dessen Code `3221226505` an das W&B-Protobuf-Feld `int32`.
- **Schlussfolgerung und nächster Schritt:** Der Sweep-Trial wurde erfolgreich
  geloggt; es wurden wie konfiguriert keine Modellcheckpoint-Dateien erzeugt.
  Der Python-Child-Prozess ist beim Beenden dennoch nativ abgebrochen. Der
  sichtbare W&B-`ValueError` ist der Folgefehler beim Agent-Teardown; das
  Windows-Ereignis benennt `ucrtbase.dll`, lokalisiert aber nicht, welche
  native Bibliothek den Fatal-Abbruch ausgelöst hat. Der Agent kann mit
  derselben Sweep-ID für weitere Trials neu gestartet werden. Bei erneutem
  Abbruch nach einem Trial braucht es einen Dump mit Stacktrace, um den
  auslösenden nativen Aufrufer zu bestimmen.

## 2026-09-30 — W&B-Agent-Teardown gegen Windows-Exitcode abgesichert

- **Fragestellung/Reasoning:** Den Folgefehler `ValueError: Value out of
  range: 3221226505` beheben, damit ein erfolgreicher W&B-Trial den Agenten
  nicht beendet. Gleichzeitig darf ein echter, nicht abgeschlossener Trial
  nicht als Erfolg gewertet werden.
- **Eingaben/Setup:** Vorhandene Sweep-Dateien unter
  `output/training_runs/wandb_sweeps/tcn_bilstm_transition_control_v1/kux6f586/6eqzbl9s`
  und dem darin gespeicherten W&B-Lauf; W&B 0.28.1 aus `.venv`; Windows-WER-
  Ereignis und Archivbericht. Der Archivbericht enthält nur Fehler-Metadaten;
  der referenzierte temporäre `.dmp`-Speicherabbildpfad existiert nicht mehr.
  Das Ereignis nennt Python 3.14.2, `ucrtbase.dll`, `0xc0000409` und
  Fast-Fail-Subcode 7. Geladene Module belegen, dass der Lauf das Projektvenv
  mit PyTorch/CUDA verwendet hat. Es wurden keine Debugger-Werkzeuge gefunden.
- **Prüfumfang/Änderung:** Die W&B-Implementierung in der installierten
  Version wurde lesend geprüft: `AgentProcess.poll()` liefert den Child-
  Exitcode an `wandb.teardown()`, dessen Protobuf-Feld einen vorzeichen-
  behafteten 32-Bit-Wert erwartet. Der neue `wandb_agent_guard.py` fängt nur
  Exitcodes außerhalb dieses Bereichs ab. Er meldet dem W&B-Agenten Erfolg,
  wenn zum Sweep-/Run-Pfad ein abgeschlossenes Manifest, eine abgeschlossene
  W&B-Zusammenfassung mit übereinstimmendem Best-Loss und eine abschließende
  W&B-Uploadbestätigung mit HTTP `200 OK` vorliegen. Sonst übergibt er den
  gültigen Fehlercode 1, um den Protobuf-Absturz zu verhindern. Die Datei
  `wandb_sweep.py` wurde als Trial-Einstiegspunkt wiederhergestellt. Die
  Startanleitung in `docs/WANDB.md` verwendet nun den Guard. Keine Tests,
  Trainingsläufe oder Sweep-Agentläufe ausgeführt.
- **Schlussfolgerung und nächster Schritt:** Der konkrete W&B-Teardown-
  `ValueError` ist im Projekt-Agent-Startpfad abgesichert; ein verifiziert
  erfolgreicher Trial wird trotz des Windows-Abbruchcodes als abgeschlossen
  behandelt und kann den Agenten nicht über diesen Fehler beenden. Der native
  Python-Abbruch selbst bleibt ungelöst, da sein Dump fehlt. Für eine exakte
  Ursachenanalyse ist bei einer künftigen Reproduktion ein vollständiger
  Prozess-Dump mit Stacktrace nötig. Der Guard ist implementiert, aber noch
  nicht durch einen weiteren Sweep-Agentlauf verifiziert.

## 2026-09-30 — Hyperband-Stopp während des TCN-Sweep-Trials

- **Fragestellung/Reasoning:** Ein weiterer TCN-Trial endete nach ungefähr
  38 Epochen mit `KeyboardInterrupt`; das W&B-Dashboard nennt den Run
  „killed by the user“, und der Agent startete danach einen neuen Run. Zu
  klären war, ob dies derselbe native Absturz wie zuvor oder ein vom Sweep
  ausgelöster Stopp war.
- **Eingaben/Setup:** W&B-Run `nz2flewh` unter
  `output/training_runs/wandb_sweeps/tcn_bilstm_transition_control_v1/kux6f586/nz2flewh`;
  Sweep-Konfiguration `config/wandb/sweep_tcn_bilstm.yaml`; W&B 0.28.1 aus
  `.venv`.
- **Prüfumfang/Befehle:** Lokales `manifest.json`, `wandb-summary.json` und
  `debug-internal.log` gelesen sowie die installierte W&B-Agent-Implementierung
  geprüft. Der Agent loggte wiederholt `Agent received command: stop` und
  `Stop: nz2flewh`. Der Windows-Pfad in W&B 0.28.1 sendet dafür
  `CTRL_C_EVENT` an den Kindprozess. Der Stacktrace endet mit
  `KeyboardInterrupt` in `loss.backward()`; W&B protokolliert den finalen
  Upload als `complete=true`, `exit_code=255`, HTTP `200 OK`. Lokales Manifest
  und Summary haben Epoche 38, Best-Epoche 14 und
  `best_validation_loss=0.3229850932955742`; das Manifest bleibt wegen des
  Interrupts auf `running`. Danach wurde ein weiterer Sweep-Run angefordert.
  Kein Trainings- oder Testlauf ausgeführt. W&B dokumentiert, dass SIGINT den
  Run-Status `KILLED` ergeben kann:
  https://docs.wandb.ai/models/sweeps/signal-handling-sweep-runs.
- **Schlussfolgerung und nächster Schritt:** Das Stop-Kommando und der folgende
  `KeyboardInterrupt` sind mit Hyperband-Pruning konsistent; sie sind nicht
  der vorherige `0xc0000409`-Absturz und lösen keinen Protobuf-Rangefehler aus.
  Der UI-Text „killed by the user“ beweist nicht, dass eine Person den Run
  manuell gestoppt hat: auch ein vom Sweep-Agenten weitergeleiteter SIGINT kann
  diesen Status erzeugen. Da Hyperband für diese Sweeps ausdrücklich aktiviert
  ist, gehört das Verwerfen schwächerer Trials zum erwarteten Sweep-Verhalten.
  W&Bs serverseitiger Grund (Hyperband oder manuelles Stoppen) ist allein aus
  den lokalen Logs nicht unterscheidbar. Falls jeder Trial bis Epoche 100 laufen
  soll, muss `early_terminate` für einen neu angelegten Sweep deaktiviert werden.

## 2026-09-30 — Hyperband-Pruning später beginnen lassen

- **Fragestellung/Reasoning:** W&B stoppte einen TCN-Trial nach rund 38
  Epochen. Die TCN-Sweeps sollen weiterhin W&B-Hyperband verwenden, aber jedem
  Trial mehr Lernzeit geben, bevor Hyperband ihn verwerfen kann.
- **Eingaben/Setup:** `config/wandb/sweep_tcn_bilstm.yaml`,
  `config/wandb/sweep_variable_tcn_bilstm.yaml`, je 100 `max_epochs` und ein
  `best_validation_loss`-Log pro Epoche. Die W&B-Dokumentation erlaubt
  `min_iter` als ersten Bracket-Punkt anstelle eines `max_iter`-Zeitplans:
  https://docs.wandb.ai/models/sweeps/define-sweep-configuration.
- **Änderung/Prüfumfang:** Beide YAMLs verwenden jetzt
  `early_terminate: {type: hyperband, min_iter: 50, eta: 3}` anstelle von
  `max_iter: 100, s: 2, eta: 3`. W&B prüft frühestens am 50. geloggten
  Epochenschritt; die tatsächliche Stop-Meldung kann wegen periodischer
  Serverprüfungen später eintreffen. Die folgenden Brackets bei 150 und 450
  liegen über dem 100-Epochen-Limit. Der Sweep-Name markiert `miniter50`. Keine
  Trainings-, Sweep- oder Testläufe ausgeführt.
- **Schlussfolgerung und nächster Schritt:** Neue Sweeps erhalten späteres,
  weniger aggressives Hyperband-Pruning. W&B speichert Sweep-Konfigurationen
  serverseitig; der bereits angelegte Sweep `kux6f586` verwendet weiterhin
  `max_iter: 100`, `s: 2`, `eta: 3`. Für die geänderte Schwelle muss ein neuer
  Sweep mit der passenden YAML angelegt und dessen neue ID für den Agenten
  verwendet werden.

## 2026-09-30 — W&B-Sweeps für TCN/BiLSTM vorbereitet (nicht ausgeführt)

- **Fragestellung/Reasoning:** Für das feste Vier-Takt-TCN/BiLSTM und das
  Variable-TCN/BiLSTM sollen getrennte W&B-Sweeps bereitstehen. Beide müssen
  die echten Runner verwenden und innerhalb einer Sweep-Runde denselben
  Dataset-, Cache-, Renderer- und Objective-Vertrag behalten. Da die beiden
  Modellpfade inkompatible Feature-/Datenverträge nutzen, erhalten sie eigene
  Sweep-IDs und ihre absoluten Validation-Losses werden nicht miteinander
  verglichen.
- **Eingaben/Setup:** Fester Pfad: Dataset-v1
  `52bc9d1cebfd1b82d2ea`, Waveformcache `output/ml_cache/bridge_waveform_v1`.
  Variabler Pfad: Dataset-v2 `2a124caf5625b4c8f683`, alle vier Längen
  2/4/6/8 Takte und der vollständige Train-/Validation-Cache
  `output/ml_cache/variable_bridge_waveform_v2/prive_scantraxx_extension_run02_wandb_full_20260926`.
  Die YAMLs halten Seed, Epoch-Obergrenze 100, Renderer, Objective und feste
  Architekturbreiten fest. Sie variieren Lernrate, Weight Decay, Batchgröße,
  Gradient-Clipping, Kernelgröße, TCN-Dilatation und Dropout; nur der variable
  Sweep variiert zusätzlich maximale Vocal-Ducking-Stärke und
  Initiallogit. W&B-Hyperband verwendet `best_validation_loss` pro Epoche mit
  `max_iter=100`, `s=2` und `eta=3`. Runner-Patience ist auf 101 Epochen
  gesetzt und kann vor dem 100-Epochen-Limit nicht auslösen; `min_delta=0`
  übernimmt jede Validationverbesserung in das gemeldete Best-Ergebnis. Jede
  Trial-Ausgabe wird nach Sweep-ID und Run-ID getrennt. W&B-Modellartefakt-Uploads sind in
  beiden YAML-Commands explizit ausgeschaltet. Auf Wunsch sollen auch lokale
  Modellgewichte nicht pro Trial aufgehoben werden: `save_checkpoints=False`
  verhindert `best.pt`/`latest.pt`; History und Manifest bleiben für die
  Parameterauswertung erhalten. Das finale Modell kann danach mit der besten
  W&B-Konfiguration regulär trainiert werden.
- **Prüfumfang/Befehle:** Kein Sweep, Training oder Testlauf wurde gestartet.
  Die Parameterfelder wurden anhand der beiden Runner- und Model-Config-
  Definitionen abgestimmt. Startanleitung: [`WANDB.md`](./WANDB.md).
- **Schlussfolgerung und nächster Schritt:** Konfigurationen und Agent-CLI-
  Einstiege sind vorbereitet. Vor dem variablen Sweep muss der vollständige
  indexgebundene Train-/Validation-Waveformcache am konfigurierten Ort
  vorhanden sein. Anschließend können beide Sweeps getrennt gestartet werden;
  Ergebnisse gelten jeweils nur für ihren eigenen Validation-Vertrag.

## 2026-09-30 — W&B-Sweep für vocal-aware MLP vorbereitet (nicht ausgeführt)

- **Fragestellung/Reasoning:** Der dokumentierte Default `vocal_time_shared_mlp_v2`
  soll reproduzierbar mit W&B-Sweeps optimiert werden. Die Trials müssen echte
  Runner-Parameter verwenden, einen Learning-Rate-Scheduler unterstützen und
  Validation-Losses auf demselben Dataset-/Renderer-/Objective-Vertrag
  vergleichen.
- **Implementierung/Setup:** `config/wandb/sweep_vocal_mlp.yaml` verwendet
  Bayesian Minimization von `best_validation_loss` auf dem Feature-Protocol-1-
  Train/Validation-Dataset. Optimizer/Betas/Epsilon, Lernrate, Weight Decay,
  Batchgröße, Scheduler samt Parametern, Early Stopping, Gradient-Clipping,
  Hidden Dimensions, Dropout und Vocal-Ducking-Konfiguration werden gesweept.
  Neue Trials erhalten je W&B-Sweep-ID und W&B-Run-ID einen eigenen lokalen
  Outputordner. Schedulerzustand wird mit dem Checkpoint gesichert; die
  Vocal-Checkpointformatversion ist daher 3. Checkpoints werden standardmäßig
  nicht hochgeladen. Vorhandene Format-2-Vocal-Checkpoints sind mit dem neuen
  Runner nicht fortsetzbar.
- **Prüfumfang/Befehle:** Kein Sweep, Training oder Testlauf wurde gestartet.
  Die Ausführung ist in [`WANDB.md`](./WANDB.md) dokumentiert.
- **Schlussfolgerung und nächster Schritt:** Implementierung und Sweep-Konfig
  sind vorbereitet. Die tatsächlichen W&B-Agent-Runs und ihre Ergebnisse
  bleiben offen; die gesetzten Suchbereiche sind keine gemessenen Gewinner.

## 2026-09-30 — Erweiterung des Vier-Modell-Hörtests auf 20 Beispiele (abgeschlossen)

- **Fragestellung/Reasoning:** Korrektur der gewünschten Hörtestgröße von
  zwei auf zwanzig Paarbeispiele. Die frühere Zwei-Paar-Ausgabe bleibt
  unverändert. Alle fünf Varianten pro Zeile (vier Modelle plus Equal Power)
  müssen exakt denselben Übergang verwenden.
- **Eingaben/Setup:** Dataset-v1-Validation mit 50 Datensätzen; Kandidaten
  mussten beidseitige Vocal-Feature-Stärke ≥ 0,15 und Tempoänderung ≤ 0,5 %
  erfüllen. Damit waren 29 Cue-Beispiele geeignet, aber nur fünf gerichtete
  Trackpaare (10/7/6/3/3 Cues); alle fünf RoFormer-Stems der gewählten
  Trackliste waren bereits im lokalen Cache. Die strikte Vorregel „höchstens
  ein Beispiel pro Track“ erlaubte nur fünf Beispiele insgesamt. Für die
  Korrektur wurde eine deterministische Round-Robin-Auswahl über die fünf
  Trackpaare verwendet. Sie wählt 20 unterschiedliche Candidate-/Cue-IDs,
  balanciert 3/3/4/5/5 Beispiele auf die Paare und verwendet Tracks/Cues nicht
  doppelt. Alle Hörbeispiele bleiben aus Validation; kein Testsplit wurde
  gelesen. Die v1-/v2-Modellvertragsgrenzen aus dem Zwei-Paar-Hörtest gelten
  weiterhin.
- **Prüfumfang/Befehle:** Vorab-Kapazitäts-/Cacheprüfung: 20 selektierbare
  Cues, fünf Trackpaare, fünf Stemcache-Treffer; geschätzte WAV-Größe ~670 MB,
  freier Speicher ~3,3 TB. Smoke:
  `.venv\Scripts\python.exe -X utf8 -B -m src.evaluation.four_model_listening_study --smoke-only --allow-track-reuse --output-directory output/four_models_shared_20pairs_validation_20260930 --feature-cache-root output/four_model_shared_feature_cache_20260927 --vocal-cache-root output/feature_cache`
  bestand mit einem ausgewählten 4-Takt-Cue und fünf validen Stereo-Renderings
  (260.096 Übergangssamples). Vollständiger Export:
  `.venv\Scripts\python.exe -X utf8 -B -m src.evaluation.four_model_listening_study --pair-count 20 --allow-track-reuse --output-directory output/four_models_shared_20pairs_validation_20260930 --feature-cache-root output/four_model_shared_feature_cache_20260927 --vocal-cache-root output/feature_cache`
  bestand bei 20/20 Paaren und 100 WAVs. Der erste SHA-/Format-Auditaufruf
  enthielt versehentlich Zeilenumbrüche in `python -c` und endete mit
  `SyntaxError`; die erneut ausgeführte Einzeilenprüfung bestand:
  `FINAL_20_PAIR_VERIFY_OK`, 100/100 WAV-SHAs, 4/4 Run-/Checkpoint-SHA-Bindungen,
  gleiche 44,1-kHz-Samplerate, Kanal- und Samplezahl je Beispiel. Gesamtausgabe
  674.487.520 Bytes. Player:
  `output/four_models_shared_20pairs_validation_20260930/index.html`.
- **Schlussfolgerung und nächster Schritt:** Gewünschte Größe ist umgesetzt.
  Für alle 20 Cue-Beispiele gibt es fünf blind/randomisiert beschriftete
  Varianten desselben Übergangs mit identischem Kontext und gemeinsamem
  Peak-Gain; die frühere Zwei-Paar-Ausgabe bleibt reproduzierbar erhalten.
  Da nur fünf Trackpaare vertreten sind, sind Hörerurteile innerhalb eines
  Trackpaars korreliert und nicht als 20 unabhängige Tracktests auszuwerten.
  Der variable Checkpoint bleibt auf v1-Stimuli out-of-domain; der Satz ist
  explorativ, kein protokollgleicher Benchmark. `answer_key.json` erst nach
  vollständiger Bewertung öffnen. Es wurden keine Gewichte/Audios committed.

## 2026-09-27 — Geblendeter gemeinsamer Hörtest für vier Modelle (abgeschlossen)

- **Fragestellung/Reasoning:** Vier bereits trainierte Modelle sollen anhand
  derselben 2 Paarbeispiele hörbar verglichen werden. `2p` wurde als zwei
  unterschiedliche Trackpaar-Beispiele interpretiert; wegen der drei festen
  Format-1-Modelle sind beide Übergänge vier Takte lang. Equal Power ist als
  Referenz zusätzlich enthalten.
- **Eingaben/Setup:** Ausschließlich Dataset-v1-Validation (50 Beispiele,
  Dataset-ID `52bc9d1cebfd1b82d2ea`, Manifest-SHA
  `4708a8fa983354903759a934f48d36b6450510809773dda2a12f9408821886b7`)
  sowie der abgeschlossene Variable-Run und Dataset-v2
  (`2a124caf5625b4c8f683`, SHA
  `bf82442d82713bdb21b7f7429f7aee1845eda3c44abcd6d5f4fdca688a78a422`).
  Beide ausgewählten Paare haben getrennte Tracks (max. eine Verwendung pro
  Track), 0,5 % maximale Tempoanpassung und Vocal-Feature-Mindeststärke 0,15.
  Kein Testsplit wurde geöffnet. Für das variable Modell wurden seine
  Feature-Protocol-2-Features auf denselben v1-Cues mit den im v2-Manifest
  gespeicherten, ausschließlich auf Train-Tracks gefitteten Normalisierungs-
  Statistiken berechnet. Seine Waveforms benutzen denselben ausgerichteten
  44,1-kHz-Mix-/RoFormer-Stimulus; gerendert wird mit seinem 11,025-kHz-
  Renderer und anschließend auf 44,1 kHz resampelt. Alle Varianten je Paar
  teilen exakt denselben Vor-/Nachlauf und gemeinsamen Peak-Gain.
- **Prüfumfang/Befehle:** Neuer reproduzierbarer Exporter
  `src/evaluation/four_model_listening_study.py`. Smoke:
  `.venv\Scripts\python.exe -X utf8 -B -m src.evaluation.four_model_listening_study --smoke-only --feature-cache-root output/four_model_shared_feature_cache_20260927 --vocal-cache-root output/feature_cache`
  bestand auf einem Paar für Equal Power und alle vier Modelle; finite
  Stereoausgaben, 273.920 Übergangssamples, keine Hördatei geschrieben.
  Anschließend vollständiger Export mit denselben Cache-Argumenten und
  `--pair-count 2` (Default) bestand. SHA-Nachprüfung bestätigte beide
  Datasetmanifeste, alle vier Run-Manifeste und Checkpoints sowie alle zehn
  WAV-Dateien. Jede WAV hat 44.100 Hz; die fünf Dateien je Paar haben jeweils
  dieselbe Samplezahl (847.220 beziehungsweise 829.812). Ergebnis:
  `output/four_models_shared_2pairs_validation_20260927/` mit `index.html`,
  blindem `manifest.json`, lokalem `answer_key.json` und unrated
  `ratings.json`.
- **Fehler und Sackgassen:** Direkter `py_compile`-Aufruf konnte die
  Bytecode-Datei im vorhandenen `__pycache__` nicht anlegen; der Import-/CLI-
  Help-Check mit `-B` validierte danach das Modul ohne Bytecode-Schreiben.
  Erster Smoke scheiterte beim Schreiben in den bestehenden
  `output/feature_cache/feature_protocol_v1`-Pfad (Access denied). Ein
  isolierter neuer Cachepfad löste zunächst einen RoFormer-Asset-Download aus,
  der an der Windows-CP1252-Ausgabe scheiterte; danach wurde der vorhandene
  RoFormer-Artefaktcache explizit wiederverwendet und nur der neue Featurecache
  getrennt angelegt. Zwei Exporter-Smoke-Fehler (doppeltes `cache_root`-
  Argument; im Smoke-Modus angelegtes Paarverzeichnis ohne Studienroot) wurden
  behoben; der folgende Smoke bestand. Der erste vollständige Export konnte
  den vorhandenen `output/control_studies`-Pfad nicht beschreiben; der finale
  Export nutzt daher einen neuen Ordner direkt unter `output/`. Keine dieser
  Sackgassen änderte bestehende Quellen, Datensätze, Checkpoints oder Caches.
- **Schlussfolgerung und nächster Schritt:** Der Hörtest ist bereit unter
  `output/four_models_shared_2pairs_validation_20260927/index.html`.
  Methode/Labels bleiben bis zum Abschluss geblendet; `answer_key.json` erst
  danach öffnen. Die v1- und v2-Validation-Bestände haben null identische
  Trackpaare. Deshalb ist dies ein gemeinsamer Stimulus-Hörvergleich, kein
  protokollgleicher Qualitätsbenchmark: das variable Modell ist auf den v1-
  Tracks out-of-domain und seine Eingabe-/Rendererverträge bleiben v2. Nicht
  über Modellverträge hinweg statistisch poolen. Testsplit bleibt geschlossen.

## 2026-09-27 — Resume der beiden 30-Epochen-Läufe (abgeschlossen)

- **Fragestellung/Reasoning:** `variable_tcn_bilstm_transition_control_v1`
  und `vocal_time_shared_mlp_v2` sollen über das ursprüngliche Limit von 30
  Epochen hinaus trainieren. Die Läufe hatten Early Stopping (Patience 6),
  erreichten dieses beim ersten Lauf aber nicht vor `max_epochs=30`. Daher
  wurde jeweils der letzte Checkpoint einschließlich Optimizerzustand geladen,
  `max_epochs` auf 100 erweitert und die bestehende Geduld-/Min-Delta-Policy
  beibehalten. Das Limit 100 ist nur eine Obergrenze, kein Sollziel.
- **Eingaben/Setup:** Unveränderte Runverträge und lokale Checkpoints vom
  2026-09-26. Vocal-MLP: Dataset-v1-ID `52bc9d1cebfd1b82d2ea`, Manifest-SHA
  `4708a8fa983354903759a934f48d36b6450510809773dda2a12f9408821886b7`,
  370 Train-/50 Validationbeispiele; alle 420 Vocalcacheeinträge waren
  Treffer. Variable TCN/BiLSTM: Dataset-v2-ID `2a124caf5625b4c8f683`,
  Manifest-SHA `bf82442d82713bdb21b7f7429f7aee1845eda3c44abcd6d5f4fdca688a78a422`,
  Waveformcacheindex-SHA
  `902e53a8491354000adcc9acad9f94d39eceae2a96a662891190438881c4c30`,
  2.649 Train-/622 Validationbeispiele, `test_reads=0`. Seed 20260926,
  CUDA `cuda:0`, Patience 6, W&B-Projekt/Gruppe unverändert. W&B loggt nur
  Konfiguration und Metriken (`--no-wandb-log-checkpoints`); lokale
  Checkpoints bleiben lokal.
- **Fehlstart/Sackgasse:** Der erste Vocal-Resume-Aufruf mit Standard-
  Sandbox-Netzwerkzugriff scheiterte nach 90 Sekunden in `wandb.init`
  (`CommError: Run initialization has timed out`); es begann keine neue
  Epoche und die Checkpoints blieben unverändert. Gelernt: Online-Resume
  benötigt bei diesem Setup explizit erlaubten Netzwerkzugriff. Der erneute
  Aufruf mit freigegebenem Netzwerk startete denselben W&B-Run erfolgreich.
- **Vocal-MLP-Lauf/Befehl:**

  ```powershell
  .venv\Scripts\python.exe -u -B -m src.ml train-vocal output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 output\training_runs\prive_scantraxx_all_models_dataset_v1_vocal_time_shared_mlp_v2_20260926_run01 --cache-root output\ml_cache\bridge_waveform_v2_vocal --feature-cache-root output\feature_cache --seed 20260926 --max-epochs 100 --batch-size 5 --device cuda:0 --resume --wandb-mode online --wandb-project beatbridge --wandb-group prive-scantraxx-extension-all-models-20260926 --wandb-name vocal_time_shared_mlp_v2-dataset-v1-continue-to100 --wandb-tags prive_scantraxx_extension dataset_format_v1 dataset_52bc9d1cebfd1b82d2ea vocal_time_shared_mlp_v2 resume_30_to_100 --no-wandb-log-checkpoints
  ```

  Epoche 31–40 wurden ergänzt; Early Stopping beendete den Lauf in Epoche
  40. Best-Checkpoint nach der konfigurierten Min-Delta-Policy: Epoche 34,
  Validation-Loss `0.324909533560276`; spätere minimale Loss-Schwankungen
  unterschritten die Min-Delta-Schwelle nicht. W&B-Run
  [`1d4dc62c31b2985fb4e2`](https://wandb.ai/xamdoesmc-technische-universit-t-braunschweig/beatbridge/runs/1d4dc62c31b2985fb4e2).
  Finales Manifest-SHA `9a15c5536910b27beb13377ba1cb887feae0af94f44e3d88264ca198ccd0d621`;
  Best-/Latest-Checkpoint-SHAs `4c3561d46e42976d259eef9d0b07094ed726c455d22c829b25e431173f48e474` /
  `628d4c87b1385b0ca762af0fdacf64a2eced0f51189c91c1286a597bba880f7e`.
- **Variable-TCN/BiLSTM-Lauf/Befehl:**

  ```powershell
  .venv\Scripts\python.exe -u -B -m src.ml train-variable-tcn-bilstm output\datasets\prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four output\training_runs\prive_scantraxx_all_models_dataset_v2_variable_tcn_bilstm_20260926_run01 --cache-root output\ml_cache\variable_bridge_waveform_v2\prive_scantraxx_extension_run02_wandb_full_20260926 --transition-bars 2 4 6 8 --seed 20260926 --max-epochs 100 --batch-size 4 --device cuda:0 --resume --wandb-mode online --wandb-project beatbridge --wandb-group prive-scantraxx-extension-all-models-20260926 --wandb-name variable_tcn_bilstm_transition_control_v1-dataset-v2-continue-to100 --wandb-tags prive_scantraxx_extension dataset_format_v2 dataset_2a124caf5625b4c8f683 variable_tcn_bilstm_transition_control_v1 resume_30_to_100 --no-wandb-log-checkpoints
  ```

  Epoche 31–40 wurden ergänzt; sechs aufeinanderfolgende Epochen ohne
  Min-Delta-Verbesserung beendeten den Lauf nach Epoche 40. Best-Checkpoint:
  Epoche 34, Validation-Loss `0.2271690967781491`. W&B-Run
  [`875000043610a50d8e24`](https://wandb.ai/xamdoesmc-technische-universit-t-braunschweig/beatbridge/runs/875000043610a50d8e24).
  Finales Manifest-SHA `e7ae40fe07ca6199e4de09fb2bac710f9993d8bf8c6ab6c5b3b5e8a4b3626658`;
  Best-/Latest-Checkpoint-SHAs `1822d86a7672912844b538284113a46d89a3e3914afa562f39e27e6d11c63b68` /
  `d22fb4910c5fd993c42464beec9460d65dc658d6ac951312786a7a707d10ae21`.
- **Ergebnis/Schlussfolgerung:** Beide Läufe gingen über Epoche 30 hinaus
  und endeten vor dem Sicherheitslimit 100 aufgrund der bestehenden
  Early-Stopping-Regel. Beide W&B-IDs wurden fortgesetzt; W&B bestätigte je
  0 Media- und 0 Artifactdateien. Die lokalen Manifeste binden History sowie
  Best-/Latest-Checkpoint-SHAs; beim Variable-Run bestätigt `io_audit.json`
  ausschließlich Train/Validation und `test_reads=0`. Auf CUDA erschienen
  erwartete PyTorch-Warnungen zu nichtdeterministischen CUDA-Backward-Op-
  Implementierungen unter `warn_only=True`; beide Läufe endeten regulär.
  Es wurden weder Audio noch Modellgewichte committet. Kein Commit erstellt.

## 2026-09-26 — PRIVE-Trainingsläufe über Modellfamilien (abgeschlossen)

- **Fragestellung/Reasoning:** Die vier registrierten Modellpfade sollen auf
  dem neuen PRIVE-Dataset geprüft werden. Format 2 wird ausschließlich vom
  `variable_tcn_bilstm_transition_control_v1`-Runner unterstützt; die drei
  Format-1-Modelle werden deshalb separat auf dem kompatiblen, eingefrorenen
  Format-1-Dataset trainiert. Das ist kein direkter Vergleich auf demselben
  Dataset. Test bleibt geschlossen.
- **Eingaben/Setup:** Dataset-v2-ID `2a124caf5625b4c8f683`, Manifest-SHA-256
  `bf82442d82713bdb21b7f7429f7aee1845eda3c44abcd6d5f4fdca688a78a422`,
  2.649 Train-/636 Validationbeispiele (2/4/6/8 Takte, kein Test). Für
  Format 1: Dataset-ID `52bc9d1cebfd1b82d2ea`, SHA-256
  `4708a8fa983354903759a934f48d36b6450510809773dda2a12f9408821886b7`,
  370 Train-/50 Validationbeispiele. Alle Läufe verwenden Seed 20260926,
  höchstens 30 Epochen, CUDA `cuda:0`, W&B-Projekt `beatbridge`, Gruppe
  `prive-scantraxx-extension-all-models-20260926`; W&B protokolliert nur
  Konfiguration/Metriken. `--no-wandb-log-checkpoints` hält Gewichte lokal.
  Die vorherige Freigabeanfrage für Checkpointuploads wurde vom Auto-Review
  blockiert; Uploads wurden nicht erzwungen oder umgangen.
- **Format-1-Läufe:**
  `time_shared_mlp_v1`: Output
  `output/training_runs/prive_scantraxx_all_models_dataset_v1_time_shared_mlp_v1_20260926_run01`,
  W&B `3295dc7d3ac5ee773b9c`, Early Stop Epoche 7, beste Epoche 1,
  Val-Loss 0,4152084. `vocal_time_shared_mlp_v2`: Output
  `output/training_runs/prive_scantraxx_all_models_dataset_v1_vocal_time_shared_mlp_v2_20260926_run01`,
  W&B `1d4dc62c31b2985fb4e2`, Abschluss Epoche 30, beste Epoche 27,
  Val-Loss 0,3258285. `tcn_bilstm_transition_control_v1`: Output
  `output/training_runs/prive_scantraxx_all_models_dataset_v1_tcn_bilstm_transition_control_v1_20260926_run01`,
  W&B `4c2d8caa663d38f24385`, Early Stop Epoche 24, beste Epoche 18,
  Val-Loss 0,3207784. Alle drei lokalen Runmanifeste binden obige v1-Dataset-
  ID/SHA und hashen Best-/Latest-Checkpoint sowie History. Für Vocal-MLP und
  TCN wurden je 370/370 Train- und 50/50 Validationcachetreffer geprüft;
  Test wurde nicht geladen. W&B meldete je 0 Medien-/Artifactdateien.
- **Format-1-Befehle:**

  ```powershell
  .venv\Scripts\python.exe -u -B -m src.ml train output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 output\training_runs\prive_scantraxx_all_models_dataset_v1_time_shared_mlp_v1_20260926_run01 --cache-root output\ml_cache\bridge_waveform_v1 --seed 20260926 --max-epochs 30 --batch-size 5 --device cuda:0 --wandb-mode online --wandb-project beatbridge --wandb-group prive-scantraxx-extension-all-models-20260926 --wandb-name time_shared_mlp_v1-dataset-v1-run01 --wandb-tags prive_scantraxx_extension dataset_format_v1 dataset_52bc9d1cebfd1b82d2ea time_shared_mlp_v1 --no-wandb-log-checkpoints
  .venv\Scripts\python.exe -u -B -m src.ml train-vocal output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 output\training_runs\prive_scantraxx_all_models_dataset_v1_vocal_time_shared_mlp_v2_20260926_run01 --cache-root output\ml_cache\bridge_waveform_v2_vocal --feature-cache-root output\feature_cache --seed 20260926 --max-epochs 30 --batch-size 5 --device cuda:0 --wandb-mode online --wandb-project beatbridge --wandb-group prive-scantraxx-extension-all-models-20260926 --wandb-name vocal_time_shared_mlp_v2-dataset-v1-run01 --wandb-tags prive_scantraxx_extension dataset_format_v1 dataset_52bc9d1cebfd1b82d2ea vocal_time_shared_mlp_v2 --no-wandb-log-checkpoints
  .venv\Scripts\python.exe -u -B -m src.ml train-tcn-bilstm output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 output\training_runs\prive_scantraxx_all_models_dataset_v1_tcn_bilstm_transition_control_v1_20260926_run01 --cache-root output\ml_cache\bridge_waveform_v1 --seed 20260926 --max-epochs 30 --batch-size 5 --device cuda:0 --wandb-mode online --wandb-project beatbridge --wandb-group prive-scantraxx-extension-all-models-20260926 --wandb-name tcn_bilstm_transition_control_v1-dataset-v1-run01 --wandb-tags prive_scantraxx_extension dataset_format_v1 dataset_52bc9d1cebfd1b82d2ea tcn_bilstm_transition_control_v1 --no-wandb-log-checkpoints
  ```

- **Variable-Waveformcache:** Smoke-Befehl mit `--limit 1`, Splits Train und
  Validation sowie 2/4/6/8 Takten: **8/8 erzeugt, 0 rejected**. Der Vollbefehl
  verwendet Dataset-v2 oben, Cache
  `output/ml_cache/variable_bridge_waveform_v2/prive_scantraxx_extension_run02_wandb_20260926`,
  Featurecache
  `output/feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run02_local_four_four`,
  Trainingrate 11025 Hz, Renderrate 44100 Hz und Toleranz 2 Samples. Zwei
  Vollmaterialisierungs-/Recheck-Befehle wurden ausgeführt; der finale
  Cache-Recheck war:

  ```powershell
  .venv\Scripts\python.exe -u -B -m src.ml cache-variable-waveforms output\datasets\prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four --cache-root output\ml_cache\variable_bridge_waveform_v2\prive_scantraxx_extension_run02_wandb_full_20260926 --feature-cache-root output\feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run02_local_four_four --transition-bars 2 4 6 8 --training-sample-rate 11025 --render-sample-rate 44100 --rounding-tolerance-samples 2
  ```

  Der isolierte Smoke verwendete denselben Befehl mit dem ursprünglichen
  `...run02_wandb_20260926`-Root und `--limit 1`.
  Zwei
  frühere Vollversuche scheiterten bei `os.replace` mit WinError 5; ein
  gleich-parentiger atomarer Rename-Smoke bestand. Daraufhin wurde nur ein
  begrenzter Retry auf `PermissionError` ergänzt (50/100/250/500 ms,
  fehlersicher nach vier Retries) samt Regression. Der fokussierte Test
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_variable_waveform_cache.py`
  bestand mit **12 passed in 5,41 s**. Der erste Vollcachelauf legte 3.271
  vollständige Cacheeinträge an, scheiterte aber absichtlich fail-closed beim
  Überschreiben des zuvor erzeugten 8-Einträge-Smoke-Index. Dieser bleibt im
  ursprünglichen Root unverändert. Entries und Rootvertrag (7,83 GiB) wurden
  in einen neuen Root
  `...prive_scantraxx_extension_run02_wandb_full_20260926` kopiert; der
  erste Kopierversuch war ACL-blockiert und wurde nach gezielter
  Schreibfreigabe erfolgreich wiederholt. Der
  vollständige Materialisierungsbefehl lief dort ausschließlich auf
  Cachetreffern durch: 3.271 Indexeinträge, null Train-Rejections, 14
  Validation-Rejections, 0 Cachemisses im Recheck. Rejections: 12
  `feature_grid_provenance_mismatch` und zwei
  `backend_rounding_residual_exceeds_tolerance`. Für 2/4/6/8 Takte liegen in
  Validation 156/156/156/154 und in Train 663/663/663/660 Cacheeinträge vor.
  Indexdatei-SHA `902e53a8491354000adcc9acad9f94d39eceae2a96a662891190438881c4c30`,
  Payload-SHA `9f497d898ef1615314e3a58233dfed3cc19c9598a082d6d0d07caeb328ee58a7`;
  Report-SHA `888c27eff632eba9aa8b65d8149ee15c1aa64f3fbc4575b95b02e0c1985b0eac`.
- **Runnerkorrektur für Cache-Rejections:** Vor dem Training wird jetzt
  geprüft, dass der Materialisierungsreport denselben Dataset-SHA und den
  versiegelten Index-SHA bindet, alle Datasetbeispiele nach Split/Länge
  abdeckt und dass fehlende IDs genau den dokumentierten Validation-
  Rejections entsprechen. Kein Train-Beispiel darf fehlen; nur exakt diese
  Validation-IDs werden vor dem Batching ausgeschlossen. ID-Liste und
  Materialisierungsreport-SHA landen im `io_audit.json`, das im Runmanifest
  gehasht ist. Erster fokussierter Regressionstest: **1 failed, 15 passed**
  (`SimpleNamespace`-Fixture hatte kein `len()`); die Zählung wurde auf die
  Beispielmetadaten abgestellt. Wiederholung
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_variable_dataset.py tests\test_variable_tcn_bilstm.py`
  bestand mit **16 passed in 6,35 s**. Zwei nachgelagerte read-only
  Auditaufrufe schlugen nur bei der angenommenen Manifestposition für
  `best_epoch` fehl; die finale Wiederholung las den Bestepoch aus der
  gespeicherten History und bestand mit allen Dataset-/Index-/Report-/Run-
  Bindungen. Die abschließende Wiederholung desselben fokussierten Tests nach
  den Run-/Statusdokumentationsänderungen bestand mit **16 passed in 6,34 s**.
  `git diff --check` bestand; Git meldete nur die im Projekt üblichen
  LF/CRLF-Hinweise.
- **Variable-Format-2-Lauf:** Befehl
  `.venv\Scripts\python.exe -u -B -m src.ml train-variable-tcn-bilstm output\datasets\prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four output\training_runs\prive_scantraxx_all_models_dataset_v2_variable_tcn_bilstm_20260926_run01 --cache-root output\ml_cache\variable_bridge_waveform_v2\prive_scantraxx_extension_run02_wandb_full_20260926 --transition-bars 2 4 6 8 --seed 20260926 --max-epochs 30 --batch-size 4 --device cuda:0 --wandb-mode online --wandb-project beatbridge --wandb-group prive-scantraxx-extension-all-models-20260926 --wandb-name variable_tcn_bilstm_transition_control_v1-dataset-v2-run01 --wandb-tags prive_scantraxx_extension dataset_format_v2 dataset_2a124caf5625b4c8f683 variable_tcn_bilstm_transition_control_v1 --no-wandb-log-checkpoints`.
  W&B `875000043610a50d8e24`, Status `completed`, Epoche 30, beste Epoche
  28, Val-Loss `0.2279368011548227`; lokal gebundener Run-ID
  `627905c3371fdd8c8ea4`. Das `io_audit.json` meldet ausschließlich Train und
  Validation, 2.649 Train-/622 Validationbeispiele und `test_reads=0`.
  Vor dem Voll-Lauf bestanden der 8-Einträge-/4-Längen-Cache-Smoke und der
  synthetische Ein-Epochen-Runner-Smoke
  `test_temporal_runner_records_length_metrics_and_rejects_resume_length_mismatch`
  (im oben protokollierten fokussierten Regressionstest).
  Runmanifest bindet Dataset-SHA und Cacheindex-SHA; finaler read-only Auditor
  validierte alle 3.271 Cachepayload-/Manifest-SHAs, Zählungen je Länge/Split,
  Report-SHA, Runvertrag, History und I/O-Audit. Ein zusätzlicher
  SHA-256-Abgleich der referenzierten Best-/Latest-Checkpoints und History in
  allen vier lokalen Runmanifesten bestand ohne Abweichung. W&B meldet 0
  Medien- und 0 Artifactdateien. Der separate W&B-/Checkpointuploadversuch
  bleibt vom Auto-Review abgelehnt; Gewichte liegen lokal.
- **Vollständige Modellabdeckung/Schlussfolgerung:** Die drei inkompatiblen
  Format-1-Modelle wurden separat auf dem gebundenen v1-Dataset trainiert;
  das Format-2-Modell auf Dataset-v2. Es sind damit vier getrennte, korrekt
  protokollierte Trainingsläufe abgeschlossen, aber kein Same-Dataset-
  Leistungsvergleich. Die in der ursprünglichen Erweiterungsplanung
  vorgesehene unabhängige Hörstudie gegen Equal Power bleibt ein eigener,
  noch offener Evaluationsschritt. Es wurde kein Audio und kein Gewicht
  committet; es wurde kein Commit erstellt.

## 2026-09-26 — PRIVE Dataset-v2 Erweiterung, Producer Run 06 (abgeschlossen)

- **Fragestellung/Reasoning:** Nach der Änderung an Candidate Protocol 2 soll
  der PRIVE-Datensatz reproduzierbar erneut erweitert werden. Kandidaten dürfen
  lokale Nicht-4/4-Inseln im Track tolerieren, müssen aber für jede Transition
  ausschließlich vollständige, zusammenhängende 4/4-Fenster verwenden.
  Train-/Validation-Paare bleiben splitintern; Testtracks werden vor
  Hashing/Analyse geschlossen ausgeschlossen. Der frühere Dataset-v2-Root
  `...run01` bleibt unverändert.
- **Eingaben/Setup:** BPM-eligible Corpusmanifest mit 407 Tracks, davon 292
  Train, 58 Validation und 57 Test; Split-Mapping-SHA
  `f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
  Partial-Merge-v2-Analyse unter
  `output/pre_analysis/prive_scantraxx_extension_merge_v2_20260923_run01`;
  `feature_baseline_v3`; 44.100 Hz; 2/4/6/8 Takte; Top-1-Target und Top-3
  Kandidaten je Länge; vier Analyse- und acht Featureworker. Testsplit ist
  geschlossen.
- **Lauf/Befehl:**
  `.venv\Scripts\python.exe -B -m src.variable_producer --corpus-manifest output\corpora\prive_scantraxx_extension_v2_20260923_run01\eligible_corpus_manifest.json --output-dir output\producers\prive_scantraxx_extension_variable_v2_top1x3_20260923_run06_local_four_four --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority.json --analysis-location output\pre_analysis\prive_scantraxx_extension_merge_v2_20260923_run01 --top-targets 1 --top-candidates-per-length 3 --transition-bars 2 4 6 8 --target-sample-rate 44100 --min-bpm 145 --max-bpm 165 --analysis-workers 8 --source-workers 4`.
- **Producer-Ergebnis/Audit:** `completed`, 350/350 Train-/Validationquellen,
  null Producerfehler; 292 Train- und 58 Validationquellen, 57 Testtracks
  geschlossen ausgeschlossen. Es entstanden 3.285 gespeicherte Top-3-
  Kandidaten (2.649 Train, 636 Validation) über 2/4/6/8 Takte und 282
  verschiedene Endpunkttracks. 71 Train- und fünf Validationpaare blieben ohne
  Kandidaten. Pairmanifest-SHAs stimmen mit dem Root überein; kein Track
  überquert Train/Validation, und es gibt keine Testpaare. Finaler Producer-
  Root-SHA `26c5a98ee98bba43dc9e733da4e7b6180fb2e63fc19bb80882dd19da28a224e3`,
  Split-Mapping-SHA `f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
  Eine erste manuelle Prüfroutine scheiterte an zwischenzeitlich falsch
  angenommenen Feldnamen bzw. daran, dass Pairmanifeste nur Top-3-Kandidaten
  statt der gesamten Rohmenge speichern; nach Anpassung an das tatsächliche
  Schema bestand der read-only Audit. Producerartefakte wurden dabei nicht
  verändert.
- **Dataset-Export-Eingaben/Befehle:** Zuerst wurde exakt der geplante
  `export-dataset-v2`-Befehl mit neuem Run02-Ziel gestartet. Der erste Versuch
  brach beim Abruf des öffentlichen BS-RoFormer-Checkpoints mit
  `WinError 10013` (Netzwerksocket im Sandboxlauf verweigert) ab; Datasetroot
  wurde nicht angelegt und es waren noch keine Stem-/Featureartefakte
  geschrieben. Nach genehmigter Netzfreigabe wurde derselbe Befehl wiederholt:
  `.venv\Scripts\python.exe -B -m src.features export-dataset-v2 output\producers\prive_scantraxx_extension_variable_v2_top1x3_20260923_run06_local_four_four\manifest.json output\datasets\prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four --cache-root output\feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run02_local_four_four --analysis-root output\pre_analysis\prive_scantraxx_extension_merge_v2_20260923_run01 --transition-bars 2 4 6 8 --top-k-per-pair 3 --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority_for_producer_run06_local_four_four.json --vocal-backend roformer --min-bpm 145 --max-bpm 165`.
- **Zwischenstand:** Der frühere Voll-Export lief nach Fertigstellung der
  Featurecaches zunächst mehrere Minuten auf CPU, scheiterte aber beim letzten
  Staging-Schritt: `PermissionError: [WinError 5] Zugriff verweigert` beim
  Anlegen des temporären Unterordners in `output/datasets`. Der unveränderliche
  Datasetroot war noch nicht veröffentlicht. Das Checkpointartefakt liegt nur
  im ignorierten Cache (`BS-Rofo-SW-Fixed.ckpt`, 699.412.152 Bytes); Audio und
  Modellgewichte wurden nicht committet. Der frühere Run01-Datasetroot blieb
  unverändert.
- **Contract-Korrektur/Sackgasse:** Der erste Export wurde nach zwei
  Track-Featurecaches kontrolliert mit `Ctrl+C` beendet (Exit-Code 1); es war
  noch kein Datasetroot veröffentlicht. Inspektion zeigte, dass der
  Dataset-v2-Exporter `extract_or_load_track_features` ohne Analyseobjekt
  aufrief und damit trotz des Merge-v2-Analysisroots `PreAnalysis`/Merge-v1
  instanziierte. Damit wurden vorhandene Merge-v2-Raster nicht wiederverwendet
  und Feature-Bin/Cue-Autorität war nicht explizit gebunden. Der v2-Exporter
  erzeugt nun standardmäßig ein gemeinsames `PartialPreAnalysis`-Objekt und
  bindet `beat_grid_analysis_contract=partial_merge_v2` im Datasetmanifest.
  Die Regression `.venv\Scripts\python.exe -B -m pytest -q
  tests/test_variable_dataset.py -p no:cacheprovider` bestand danach mit Exit-
  Code 0 (`7 passed in 5.24s`). Bereits geschriebene Stem-/Featurecaches
  bleiben als ignorierte, SHA-gebundene Artefakte erhalten; sie werden nicht
  entfernt. Der Run01-Datasetroot ist unberührt.
- **Wiederanlauf/Sackgassen:** Der erste Start nach der Contract-Korrektur
  scheiterte vor dem Schreiben weiterer Daten mit `UnicodeEncodeError` in der
  RoFormer-Bibliothek (Emoji-Statusausgabe gegen Windows-CP1252); der
  Datasetroot blieb abwesend. Derselbe Export wurde mit
  `$env:PYTHONIOENCODING='utf-8'` gestartet. Die Partial-Merge-v2-Caches
  wurden wiederverwendet (keine erneute aufTAKT-Analyse pro Track). Dieser
  Wiederanlauf berechnete die Beispiele, konnte aber den temporären Ordner
  wegen verweigerter Datasetordner-Schreibrechte nicht anlegen. Der
  Schreibtestbefehl `.venv\Scripts\python.exe -B -c "from pathlib import Path;
  p=Path('output/datasets/.codex_write_probe.tmp'); p.mkdir(); print(p.resolve());
  p.rmdir()"` bestätigte dieselbe `WinError 5`-Blockade in `output/datasets`.
  Der genehmigte Wiederanlauf mit Schreibzugriff auf genau diesen Exportpfad
  wurde am 26.09.2026 um 09:38 gestartet und nach etwa 4 Minuten 20 Sekunden
  erfolgreich veröffentlicht (Exit-Code 0). Verwendet wurden derselbe
  Producer, Splitmap, Feature-/Stemcache und Exportbefehl; keine Quelldaten
  oder bestehenden Datasetroots wurden überschrieben.
- **Cache-Wiederverwendung:** Vorhandene RoFormer-Caches aus den früheren
  PRIVE-Run01-, PRIVE-Smoke- und Variable-v2-Caches wurden read-only auf
  Überschneidung geprüft. 72 der 282 benötigten Track-SHAs hatten 83 passende
  Stemcache-Verzeichnisse. Für den laufenden Run02 wurden danach 61 noch
  fehlende Verzeichnisse kopiert; ihre `vocal_stem.npz`-SHA stimmt jeweils mit
  `artifact_sha256` des Manifests überein, Track-SHA, BS-RoFormer-Modellname und
  Cache-ID passen. 22 bereits vorhandene Verzeichnisse wurden übersprungen,
  null ungültige Einträge. Originalcaches blieben unverändert; der laufende
  Export verwendet die übernommenen Einträge bei ihrem normalen SHA-Cache-Lookup.
- **Export- und Contract-Audit:** Dataset-v2-Run02 wurde vollständig erstellt:
  Dataset-ID `2a124caf5625b4c8f683`, Manifest-SHA-256
  `bf82442d82713bdb21b7f7429f7aee1845eda3c44abcd6d5f4fdca688a78a422`,
  Datasetdateien insgesamt 30.623.521 Bytes. 3.285/3.285 ausgewählte
  Beispiele wurden exportiert. Verteilung je Länge: 2 Takte 663 Train/159
  Validation; 4 Takte 663/159; 6 Takte 663/159; 8 Takte 660/159; jeweils
  0 Testbeispiele. Alle 350 gebundenen Pairmanifeste und alle 24 Datasetdateien
  (NPZ plus JSONL einschließlich ausdrücklich leerer Testshards) stimmen mit
  den SHA-256-Werten im Manifest überein. Producer-Manifest-SHA ist
  `26c5a98ee98bba43dc9e733da4e7b6180fb2e63fc19bb80882dd19da28a224e3`,
  Split-Mapping-SHA bleibt
  `f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
  Der Loader hat alle 12 Längen-/Split-Shards gelesen und Featureformen,
  Längenkonditionierung sowie Metadaten geprüft. Beispielendpunkte sind ihren
  autorisierten Splits zugeordnet; kein Train-/Validation-Track-Leakage,
  keine Testbeispiele. Audit erster Versuch endete mit `AttributeError`, weil
  die Prüfroutine `track_assignments` fälschlich als Dictionary statt der
  manifestierten Liste annahm; nach Anpassung an das Schema bestand dasselbe
  PowerShell-Here-String-Prüfskript über
  `.venv\Scripts\python.exe -B -` vollständig (Exit-Code 0).
- **Testläufe/Ergebnis:** Regressionstest
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_variable_dataset.py -p no:cacheprovider`
  bestand am 26.09.2026 mit Exit-Code 0 (`7 passed in 4.04s`). Der vollständige
  Loader-/SHA-/Leakageaudit bestand ebenfalls mit Exit-Code 0. `git diff
  --check` meldete keine Whitespacefehler; nur die vorhandenen Hinweise zu
  LF→CRLF bei geänderten Textdateien. `git status --short` bestätigt: keine
  Dataset-, Audio- oder Modellgewichtsdateien sind Git-Änderungen; bestehende
  Nutzungsänderungen wurden nicht bereinigt oder committet.
- **Schlussfolgerung/nächster Schritt:** Dataset-v2-Erweiterung ist vollständig
  und reproduzierbar materialisiert. Der separate Run01-Datasetroot blieb
  unverändert. Keine Waveformcache-, Trainings-/Fine-Tuning- oder unabhängigen
  Hörvergleichsläufe wurden angefordert oder ausgeführt; sie bleiben getrennte
  nächste Schritte.

## Test- und Renderläufe am 2026-09-04 (nichttrivial vergleichbare Modelle)

- **Fragestellung und Reasoning:** Für die zuvor bewusst ausgeschlossenen
  Modellpfade sollten eigene Beispiele entstehen, ohne inkompatible Dataset-,
  Alignment- oder Aufgabenverträge in eine gemeinsame Auswertung zu mischen.
  Variable-TCN v2 wird daher gegen Equal Power auf seinem eigenen
  Feature-/Waveform-Protokoll 2 gehört. Der Cue-Ranker wird nur als
  synthetische Ranking-Funktionsdemo gezeigt, weil er Cuepoints statt
  Control-Kurven erzeugt und noch keinen realen freigegebenen Checkpoint hat.
- **Eingaben/Setup:** Dataset
  `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`,
  dessen vorhandener unveränderlicher Validation-Waveformcache bei 11.025 Hz,
  Best-Checkpoint aus
  `output/training_runs/variable_tcn_bilstm_v2_wandb_20260826` und der
  synthetische All-Lengths-Cue-Ranker-Smoke vom 2026-08-25. Testsplit,
  Originalaudio und bestehende Caches blieben unangetastet.
- **Testumfang bzw. Befehle und Ergebnisse:** Der fokussierte neue Testlauf
  `.venv\Scripts\python.exe -m pytest -q tests/test_all_models_control_study.py tests/test_nontrivial_model_examples.py -p no:cacheprovider`
  bestand mit Exit-Code 0 (`3 passed in 2.52s`). Der reale Export
  `.venv\Scripts\python.exe -m src.evaluation.nontrivial_model_examples ...`
  schrieb vier A/B-Paare für 2/4/6/8 Takte und eine Vergleichszentrale. Eine
  read-only SoundFile-/SHA-Sonde bestätigte alle acht WAV-SHAs, 11.025 Hz,
  finite Samples, paarweise identische Shapes, Peaks ≤ 0,98, Blindheit der
  Hörseite und vier Cue-Ranker-Tabellenzeilen; Exit-Code 0. Die fokussierte
  Regression über beide neuen Exporte sowie Variable-TCN-, Waveformcache- und
  Variable-ML-Verträge bestand mit Exit-Code 0 (`27 passed in 12.98s`). Der
  abschließende fokussierte Wiederholungslauf nach der Dokumentationspflege
  bestand mit Exit-Code 0 (`3 passed in 2.83s`); `git diff --check` meldete
  keine Whitespacefehler, nur die bestehenden Windows-LF/CRLF-Hinweise. Der
  zusätzliche visuelle Browser-Test der lokalen `file:`-URL wurde von der
  Browser-Sicherheitsrichtlinie blockiert; es wurde kein Umgehungsversuch
  unternommen. DOM-/Interaktions-QA im kontrollierten Browser bleibt daher
  eine offene manuelle Prüfung.
- **Ergebnis:** Der Variable-TCN-Hörsatz liegt unter
  `output/control_studies/blind_variable_tcn_lengths_20260904/`. Die neue
  Vergleichszentrale unter
  `output/control_studies/model_comparison_hub_20260904/` verlinkt getrennt
  den vierfachen Dataset-v1-Hörvergleich und die Variable-TCN-A/B-Beispiele.
  Sie zeigt zusätzlich den letzten synthetischen Validation-Snapshot des
  Cue-Rankers für 2/4/6/8 Takte mit deutlicher Warnung, dass eine Gruppe je
  Länge kein realer Qualitätsnachweis ist.
- **Schlussfolgerung und nächster Schritt:** Alle derzeit materialisierten
  Modellfamilien sind nun entweder hörbar unter ihrem eigenen Vertrag oder
  ehrlich als nicht hörbare synthetische Funktionsdemo vertreten. Als Nächstes
  sollte der Nutzer beide geblendeten Hörsätze bewerten. Ein echter hörbarer
  Cue-Ranker-Vergleich bleibt bis zu einem freigegebenen realen Ranker-Release
  samt Controller-/Renderer-Backfill gesperrt.

## Test- und Renderläufe am 2026-09-04 (geblendeter Mehrmodell-Hörvergleich)

- **Fragestellung und Reasoning:** Für einen direkten Hörvergleich sollten die
  trainierten, mit demselben Dataset-v1-Vertrag kompatiblen Control-
  Modellfamilien auf exakt denselben Übergängen gerendert werden. Geprüft
  wurden insbesondere repräsentative Run-Auswahl, Checkpoint-/Dataset-SHAs,
  geblendete Zuordnung, gemeinsame Peak-Absenkung sowie die lokale HTML-
  Bedienung. Der synthetische Cue-Ranker ist kein Renderer; Variable-TCN v2
  besitzt einen anderen Dataset-/Featurevertrag und wurde deshalb nicht
  scheinbar vergleichbar in denselben Hörsatz gemischt.
- **Eingaben/Setup:** Dataset
  `output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805`,
  ausschließlich dessen Validation-Split, vorhandene RoFormer-Stems und
  Best-Checkpoints. Automatisch gewählt wurden der Full-Band-TCN-Lauf vom
  2026-08-12 sowie die W&B-Reruns von MLP v1 und Vocal-MLP v2. Equal Power
  dient als vierte Referenz. Kein Training, kein Testsplit und keine Änderung
  vorhandener Audio-/Modelldateien.
- **Testumfang bzw. Befehle und Ergebnisse:** Der erste fokussierte Lauf
  `.venv\Scripts\python.exe -m pytest -q tests/test_all_models_control_study.py -p no:cacheprovider`
  endete mit Exit-Code 1 (`2 failed in 22.94s`): dem neuen Modul fehlte der
  lokale JSON-Reader und eine HTML-Assertion erwartete fälschlich einen erst
  zur Laufzeit gebildeten Dateinamen als Literal. Nach Korrektur bestand der
  identische Lauf mit Exit-Code 0 (`2 passed in 2.86s`). Der erste reale
  Exportversuch wurde vor jedem Schreiben durch die Dateisandbox mit
  `PermissionError [WinError 5]` blockiert; die autorisierte Wiederholung
  `.venv\Scripts\python.exe -m src.evaluation.all_models_control_study ... --pair-count 5`
  endete erfolgreich und schrieb fünf Paare mit je vier Varianten. Eine
  read-only SoundFile-/SHA-Sonde prüfte alle 20 WAVs: 44,1 kHz, finite Samples,
  Peak höchstens 0,98, identische Shape je Paar, korrekte Datei-SHAs und keine
  Methodennamen im geblendeten HTML; Exit-Code 0. Die fokussierte Regression
  über neuen Exporter, bestehende MLP-/Vocal-Studien, Ratings und TCN-Modell
  bestand mit Exit-Code 0 (`21 passed in 8.88s`).
- **Ergebnis:** Der fertige Hörsatz liegt unter
  `output/control_studies/blind_all_models_validation_20260904/`. `index.html`
  spielt A/B/C/D pro Paar ab, speichert Eingaben lokal und exportiert ein
  `ratings.json`; `answer_key.json` enthält erst für die spätere Auswertung
  die Zuordnung zu Equal Power, TCN/BiLSTM v1, Time-shared MLP v1 und Vocal
  MLP v2.
- **Schlussfolgerung und nächster Schritt:** Der Vergleich ist technisch
  vollständig und reproduzierbar, bleibt aber wegen Modellwahl auf Validation
  ein Entwicklungsgate. Als Nächstes hört und bewertet der Nutzer alle fünf
  Paare, lädt die Ratings herunter und öffnet erst danach den Antwortschlüssel.
  Ein gemeinsamer Vergleich einschließlich Variable-TCN erfordert einen
  separaten protokollgleichen Hörsatz; der Cue-Ranker muss über seine
  Cuepointauswahl plus nachgelagerten Controller evaluiert werden.

## Testläufe am 2026-08-26 (W&B-Cue-Ranker-Integration)

- **Fragestellung und Reasoning:** Die neue rekursive Metrikabflachung, der
  Cue-Ranker-W&B-Lifecycle, Root-Artifactpfade und die Regression bestehender
  Runner sollten zunächst fokussiert und danach vollständig geprüft werden.
  Alle Läufe nutzten nur synthetische Fixtures bzw. Pytest-Temporary-Dateien;
  es erfolgte kein Login und kein Online-Upload.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`,
  `-p no:cacheprovider`, uncommitteter Arbeitsbaum. Ein erster fokussierter
  Lauf deckte ein fehlendes Test-`mkdir` auf; ein zweiter Lauf war danach grün.
  Beim Offline-Smoke zeigte ein dritter Lauf den W&B-Verzeichnis-/Existenz-
  Randfall; nach der Korrektur war der vierte fokussierte Lauf grün.
- **Testumfang bzw. Befehle und Ergebnisse:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_wandb_logging.py tests/test_cue_ranker_runner.py tests/test_cue_ranker_feature_loader.py`
  → zunächst Exit-Code 1 (`17 passed, 1 failed`, fehlendes Fixture-Verzeichnis);
  Wiederholung → Exit-Code 0 (`18 passed in 5.78s`). Nach Umstellung des
  Offline-Smokes auf `--wandb-mode offline` → Exit-Code 1 (`17 passed, 1 failed`,
  W&B legte `wandb/` vor dem Runner-Guard an); nach Lifecycle-Fix → Exit-Code 0
  (`18 passed in 9.47s`).
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_ml_training_runner.py tests/test_variable_tcn_bilstm.py tests/test_vocal_ml_training_runner.py tests/test_wandb_logging.py`
  → Exit-Code 0, `19 passed, 2 warnings in 9.55s`.
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests`
  → Exit-Code 0, `261 passed, 8 warnings in 27.44s`.
- **Schlussfolgerung und nächster Schritt:** Rekursives Flattening liefert
  deterministische skalare Keys wie
  `validation/ranking/all/ranker/ndcg`; Nichtskalare werden klar abgelehnt,
  optionale `None`-Werte ausgelassen. Offline erzeugt lokale Run-Dateien und
  W&B-Daten, disabled bleibt ohne W&B-Seiteneffekt, und Control-Runner bleiben
  kompatibel. Nächster Schritt ist ein ausdrücklich freigegebener echter
  Online-Trainingslauf; der Befehl wird nur ausgegeben und nicht gestartet.

## Testlauf am 2026-08-25 (frischer Cuepoint-Ranker-Audit, gezielte Kernprüfung)

- **Fragestellung und Reasoning:** Als unabhängiger Reviewer sollten zunächst
  die neuen, sicherheitskritischen Cue-Ranker-Grenzen isoliert geprüft werden:
  versiegelter Testsplit, v2-/Grid-Preflight, Split-/Gruppenisolation,
  Teacher-/Checkpointvertrag, variable Gruppen, Resume sowie additive
  Batch-/Renderer-Manifeste. Dies ist kein Nachweis für einen realen
  Trainings- oder Hörlauf.
- **Eingaben/Setup:** Aktueller uncommitteter Arbeitsbaum,
  `.venv\Scripts\python.exe -B`, ausschliesslich Pytest-Temporary- und
  synthetische Fixture-Daten (einschliesslich temporärer Test-WAVs),
  `-p no:cacheprovider`. Kein realer Batch, kein reales Training und kein
  Zugriff auf einen realen Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 0;
  `26 passed, 2 warnings in 11.32s`. Die Warnungen sind
  `audioread`-Deprecations für `aifc` und `sunau` im synthetischen
  Integrationsrender-Test; keine Cue-Ranker-Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die vorhandene gezielte Suite
  bestätigt die abgedeckten Verträge, ersetzt aber keinen Quell-/Negativ-Audit.
  Als Nächstes folgen statische Datenflussprüfung und zusätzliche gezielte
  Negativsonden; nur bei eindeutig reproduziertem Contract-Verstoss wird Code
  geändert.

## Testlauf am 2026-08-25 (Audit-Negativsonde, erster Guard-/Gruppenkontextversuch)

- **Fragestellung und Reasoning:** Zwei statisch gefundene Grenzfälle sollten
  vor jedem Fix gegen den unveränderten Code reproduziert werden: ein
  `guard_rejected`-Label mit endlicher hoher Utility und die Kontextgröße einer
  gegenüber dem vollständigen Universum kleineren Labelstichprobe.
- **Eingaben/Setup:** Neue, rein In-Memory-synthetische Regressionstests;
  `.venv\Scripts\python.exe -B`, `-p no:cacheprovider`; kein Audio,
  Testsplit, Cache oder Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_runner.py::test_guard_rejection_is_always_a_negative_anchor_even_with_finite_utility tests/test_cue_ranker_dataset.py::test_grouped_loader_context_uses_full_universe_size_not_label_sample_size`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 1,
  `2 failed in 3.55s`. Der Guard-Test zeigte bereits den Contract-Verstoss
  (Gradient für den abgelehnten Kandidaten `-0.5` statt negativer Anker).
  Der Kontext-Test erreichte seine Assertion noch nicht, weil die neue
  Fixture die verpflichtende `transition_position`-Feature-Invariante nicht
  gesetzt hatte.
- **Schlussfolgerung und nächster Schritt:** Der Fixturefehler ist kein
  Produktfehler und wurde vor der Wiederholung korrigiert; am unveränderten
  Produktcode wurde nichts geändert.

## Testlauf am 2026-08-25 (Audit-Negativsonde, Fixture-Nachkorrektur)

- **Fragestellung und Reasoning:** Nach Setzen der normierten
  `transition_position` sollte die Gruppenkontextsonde bis zur beabsichtigten
  Contract-Assertion gelangen; der Guard-Befund wurde parallel erneut geprüft.
- **Eingaben/Setup:** Ausschliesslich die zwei In-Memory-synthetischen
  Regressionstests mit `.venv\Scripts\python.exe -B` und deaktiviertem
  Pytest-Cacheprovider; kein Testsplit, Audio oder Training.
- **Testumfang bzw. Befehl:** Derselbe gezielte Pytest-Befehl wie im
  unmittelbar vorherigen Testlauf.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 1,
  `2 failed in 3.35s`. Der Guard-Befund blieb unverändert. Die zweite Fixture
  erreichte wegen eines fehlenden lokalen `split`-Attributs des absichtlich
  minimal konstruierten Dataset-Objekts noch nicht die Soll-Assertion.
- **Schlussfolgerung und nächster Schritt:** Auch dies war ein Testsetupfehler,
  nicht ein Produktbefund; `split="train"` wurde gesetzt und die Sonde ohne
  Codeänderung wiederholt.

## Testlauf am 2026-08-25 (Audit-Negativsonde, zwei reproduzierte Contract-Verstösse)

- **Fragestellung und Reasoning:** Die bereinigte Sonde sollte die zwei
  vermuteten Datenflussfehler eindeutig vom Testsetup trennen.
- **Eingaben/Setup:** Rein synthetische In-Memory-Inputs,
  `.venv\Scripts\python.exe -B`, `-p no:cacheprovider`; kein Audio,
  Testsplit, Cache oder Training.
- **Testumfang bzw. Befehl:** Derselbe gezielte Pytest-Befehl wie in den zwei
  vorherigen Testläufen.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 1,
  `2 failed in 3.18s`. Ein `guard_rejected` mit Utility `100` erhielt im
  Listwise-Loss einen bevorzugenden Gradienten (`-0.5` gegenüber `+0.5` für
  den gültigen Kandidaten). Die Loader-Kontextkomponente
  `log1p(group_size)` war `log1p(1)=0.693147…` statt
  `log1p(600)=6.398594…`; Training und Inferenz hätten damit unterschiedliche
  Kandidatenraumgrößen gesehen.
- **Schlussfolgerung und nächster Schritt:** Beide Fehler sind reproduziert
  und widersprechen dem festgelegten negativen Guard-Anker beziehungsweise dem
  vollständigen Gruppenkontext. Sie werden jetzt mit Regressionstests behoben;
  keine anderen statischen Beobachtungen werden vorsorglich geändert.

## Testlauf am 2026-08-25 (Audit-Regression, Guard-Anker und vollständiger Gruppenkontext)

- **Fragestellung und Reasoning:** Nach den zwei minimalen Fixes musste
  bestätigt werden, dass ein `guard_rejected` immer gegenüber einer endlichen
  hohen Utility negativ verankert wird und dass der Loader im Training die
  vollständige statt der nur gelabelten Gruppengröße an den Kontext übergibt.
- **Eingaben/Setup:** Die zwei neuen In-Memory-synthetischen
  Regressionstests mit `.venv\Scripts\python.exe -B` und
  `-p no:cacheprovider`; kein Audio, Testsplit, Cache oder Training.
- **Testumfang bzw. Befehl:** Derselbe gezielte Pytest-Befehl wie in den drei
  vorherigen Testläufen.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 0;
  `2 passed in 3.31s`. Kein Warning, Fehler oder Blockade.
- **Schlussfolgerung und nächster Schritt:** Der Loss ersetzt jetzt jede
  Guard-Rejection durch den festen relativen Negativanker; die
  Validation-Auswertung verwendet dieselbe Semantik. Die Kontextdichte ist
  zwischen gelabelter Trainingsstichprobe und vollständiger Inferenzgruppe
  konsistent. Als Nächstes wird der separate Render-Backfill-Vertrag
  reproduziert und geprüft.

## Testlauf am 2026-08-25 (Audit-Negativsonde, Learned-Render-Backfill)

- **Fragestellung und Reasoning:** Der explizite Inferenzvertrag verlangt bei
  einem technischen Renderfehler eines Top-K-Kandidaten einen deterministischen
  Backfill mit dem nächsten gelernten Kandidaten. Die Sonde isoliert genau
  diesen Fall mit Top-K 1.
- **Eingaben/Setup:** Synthetische Temporary-WAVs und Candidate-v2-Fixture;
  ein Mock lässt nur den topgerankten Kandidaten beim variablen Renderer
  kontrolliert fehlschlagen. `.venv\Scripts\python.exe -B`,
  `-p no:cacheprovider`; kein Testsplit, Realbatch oder Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_learned_cue_ranker_integration.py::test_learned_render_failure_backfills_next_ranked_candidate`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 1;
  `1 failed, 2 warnings in 7.66s`. Der erste Kandidat erhielt den erwarteten
  synthetischen Renderfehler, aber es wurde kein Fallback-Kandidat gerendert
  (`rendered_variants=[]`). Die zwei Warnings sind die bekannten
  `audioread`-Deprecations `aifc`/`sunau`.
- **Schlussfolgerung und nächster Schritt:** Der dokumentierte Backfill war
  tatsächlich nicht implementiert; die bestehenden Manifestfelder meldeten
  stattdessen alle vorher ausgewählten Kandidaten pauschal als `eligible`.
  Der Fehler wird nun gezielt im Learned-Pfad behoben und danach gegen diese
  Regression verifiziert.

## Testlauf am 2026-08-25 (Audit-Regression, Learned-Render-Backfill)

- **Fragestellung und Reasoning:** Nach der punktuellen Inferenzkorrektur
  musste derselbe Top-K-1-Failurefall den nächsten erfolgreichen Kandidaten
  selektieren, ohne die etablierte additive Manifestsemantik zu verändern.
- **Eingaben/Setup:** Synthetische Temporary-WAV-/Candidate-v2-Fixtures;
  deterministischer Renderer-Mock für genau den ersten Learned-Kandidaten;
  `.venv\Scripts\python.exe -B`, `-p no:cacheprovider`. Kein Testsplit,
  Realbatch oder Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_learned_cue_ranker_integration.py::test_learned_render_failure_backfills_next_ranked_candidate tests/test_learned_cue_ranker_integration.py::test_learned_selection_is_additive_and_renderer_manifest_compatible`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 0;
  `2 passed, 2 warnings in 7.33s`. Der Fallback wurde gerendert und als
  einzige `selection_candidate_id` manifestiert; der verworfene Kandidat steht
  in `backfill.skipped_candidate_ids`. Die Warnings sind unverändert die
  `audioread`-Deprecations `aifc`/`sunau`.
- **Schlussfolgerung und nächster Schritt:** Learned-Rendering versucht nun
  deterministisch die absteigende Score-Reihenfolge, füllt renderunfähige
  Kandidaten auf und dokumentiert `rendered`, `render_failed` sowie nach
  erreichter Top-K-Grenze nicht gestartete Kandidaten. Der historische
  `feature_baseline_v3`-Pfad bleibt unverändert. Als Nächstes folgen die
  restlichen gezielten Regressionen und ein Sicherheits-/Teacher-Audit.

## Testlauf am 2026-08-25 (Audit-Sonde, Cue-Ranker-CLI-Erreichbarkeit)

- **Fragestellung und Reasoning:** Die im verbindlichen Implementierungsplan
  aufgeführten Offline-Schritte `label-cue-ranker-teacher` und
  `train-cue-ranker` müssen als echte CLI-Einstiegspunkte auffindbar sein,
  damit der sichere Format-3-Pfad nicht nur über Test-APIs existiert.
- **Eingaben/Setup:** Ausschliesslich `--help` und textuelle Quellsuche mit
  `.venv\Scripts\python.exe -B`; keine Dataset-, Audio-, Cache-, Testsplit-
  oder Trainingsoperation.
- **Testumfang bzw. Befehle:**
  `.venv\Scripts\python.exe -B -m src.ml --help`;
  `.venv\Scripts\python.exe -B -m src.features --help`; sowie `rg` nach den
  beiden geplanten CLI-Kommandos und den exportierten Cue-Ranker-APIs.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Beide Help-Aufrufe
  endeten mit Exit-Code 0. `src.features` bietet Universe- und Datasetexport,
  aber `src.ml` listet weder `label-cue-ranker-teacher` noch
  `train-cue-ranker`; die Suche fand nur Python-APIs und Testaufrufe. Es gab
  keine Warnings.
- **Schlussfolgerung und nächster Schritt:** Der produktionsnahe Offline-
  Label-/Train-CLI-Pfad aus dem Plan ist nicht implementiert. Da die nötige
  reale Format-3-Feature-/Waveformauflösung ebenfalls keinen sicheren
  End-to-End-CLI-Vertrag besitzt, wird dies als verbleibender Freigabeblocker
  dokumentiert statt mit einem spekulativen CLI-Wrapper zu überdecken.

## Testlauf am 2026-08-25 (Audit-Negativsonde, Teacher-Run-/Best-Checkpoint-Bindung)

- **Fragestellung und Reasoning:** Ein eingefrorener Teacher darf nicht aus
  einem beliebigen Checkpoint plus einem nur nebenstehenden Runmanifest
  zusammengesetzt werden. Der Test übergibt deshalb einen Checkpoint, während
  das als abgeschlossen deklarierte Variable-TCN-Runmanifest einen anderen
  `best_checkpoint` mit gültigem SHA nennt.
- **Eingaben/Setup:** Zwei rein synthetische `weights_only`-Checkpointdateien
  und ein synthetisches Runmanifest im Pytest-Temporary-Verzeichnis;
  `.venv\Scripts\python.exe -B`, `-p no:cacheprovider`. Kein Testsplit,
  Audio, Cache oder Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_teacher.py::test_teacher_release_rejects_checkpoint_not_declared_as_completed_run_best`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 1;
  `1 failed in 3.89s`. `seal_teacher_release()` akzeptierte die ungebundene
  Kombination und erzeugte trotz abweichendem Best-Pfad einen Release.
- **Schlussfolgerung und nächster Schritt:** Die reine SHA-Aufzeichnung war
  kein ausreichender Freeze-Vertrag. Der Sealer/Verifier/Loader wird auf
  abgeschlossenes Variable-TCN-Runformat, deklarierten Best-Pfad/-SHA und
  Checkpoint-Run-/Modellvertrag gehärtet.

## Testlauf am 2026-08-25 (Audit-Regression, Teacher-Run-/Best-Checkpoint-Bindung)

- **Fragestellung und Reasoning:** Nach der Härtung müssen der neue
  Mismatch-Reject, bestehendes eval-only Teacher-Loading, Failure-Isolation
  sowie der Format-3-Export gemeinsam funktionieren.
- **Eingaben/Setup:** Nur synthetische Variable-TCN-State-Dicts, abgeschlossene
  synthetische Runmanifeste und Temporary-Format-3-Artefakte;
  `.venv\Scripts\python.exe -B`, `-p no:cacheprovider`. Kein Testsplit,
  Audio, Cache oder Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_teacher.py tests/test_cue_ranker_dataset.py`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 0;
  `5 passed in 4.61s`, ohne Warnings oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der Teacher-Sealer, -Verifier und
  -Loader akzeptieren jetzt nur den `best_checkpoint` eines abgeschlossenen
  `variable_tcn_bilstm_transition_control_v1`-Runs, dessen Hash und
  Checkpointvertrag zusammenpassen. Die Objective-/Rendererbindung bleibt
  releasegebunden; die fehlenden End-to-End-CLIs bleiben davon getrennt ein
  offener Freigabeblocker.

## Testlauf am 2026-08-25 (frischer Cuepoint-Ranker-Audit, betroffene Regression)

- **Fragestellung und Reasoning:** Nach den vier reproduzierten Fixes musste
  der gesamte betroffene Umfang gemeinsam prüfen: v2-/Grid-/Splitgrenzen,
  Volluniversum/Sampling, Teacher-Release, variable Gruppen, Listenloss und
  Resume, Learned-Inferenz/Backfill sowie die historischen Batch-, Multi-Batch-
  und Variable-Control-Verträge.
- **Eingaben/Setup:** Ausschliesslich Pytest-Temporary- und synthetische
  Fixture-Daten, `.venv\Scripts\python.exe -B`, deaktivierter Cacheprovider.
  Kein reales Training, kein Realbatch und kein Zugriff auf einen realen
  Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py tests/test_batch_render.py tests/test_multi_batch_render.py tests/test_candidates.py tests/test_variable_dataset.py tests/test_variable_ml.py tests/test_tcn_bilstm_model.py`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 0;
  `82 passed, 2 warnings in 17.03s`. Die Warnings sind die bekannten
  `audioread`-Deprecations `aifc`/`sunau` im Integrationsrender-Test; keine
  Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die behobenen Datenfluss-,
  Teacher- und Renderfehler regressieren nicht gegen die unmittelbaren
  Verträge. Die vollständige Suite kann nun gemäß Auftrag gestartet werden;
  sie ist weiterhin kein Ersatz für den fehlenden realen, testfrei
  materialisierten Format-3-CLI-Validierungspfad.

## Testlauf am 2026-08-25 (frischer Cuepoint-Ranker-Audit, vollständige Suite)

- **Fragestellung und Reasoning:** Nach den gezielten Korrekturen musste die
  gesamte Repository-Suite auf Querregressionen in Candidate-, Rendering-,
  Feature-, Dataset-, Control- und Batchpfaden geprüft werden.
- **Eingaben/Setup:** Aktueller Arbeitsbaum mit den Audit-Regressionstests,
  `.venv\Scripts\python.exe -B`, `-p no:cacheprovider`; die Suite nutzte
  nur ihre bestehenden synthetischen beziehungsweise Temporary-Fixtures. Kein
  reales Training und kein Zugriff auf einen realen Cue-Ranker-Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider`.
- **Ergebnis einschliesslich Fehlern oder Blockaden:** Exit-Code 0;
  `239 passed, 4 warnings in 36.37s`. Zwei bekannte `audioread`-
  DeprecationWarnings betreffen `aifc`/`sunau` im Batch-Render-Test. Zwei
  bekannte PyTorch-CUDA-Warnings melden nichtdeterministische Backwards für
  `upsample_linear1d` und `adaptive_avg_pool2d` im bestehenden
  Control-Runner-Test. Keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der Arbeitsbaum ist vollständig
  regressionsgrün. Die CUDA-Warnings erlauben weiterhin keine bitgenaue GPU-
  Reproduzierbarkeitsbehauptung für den älteren Control-Runner. Für den
  Cue-Ranker bleiben ein testfrei materialisierter echter Format-3-
  Teacher-Snapshot, sichere End-to-End-Label-/Train-CLIs und eine unabhängige
  Hörstudie die nächsten Freigabegates.

## Verifiziert am 2026-08-25 (additive Learned-Cue-Ranker-Integration)

- **Fragestellung und Reasoning:** Vor der Integration musste geprüft werden,
  ob Syntax/Importe und die bestehenden Batch-, Multi-Batch- und Ranking-
  Verträge unverändert funktionieren. Der Syntax-Teil sollte ohne Realbatch
  laufen; die Tests verwenden ausschließlich synthetische Daten.
- **Eingaben/Setup:** Repository-Arbeitsbaum, `.venv\Scripts\python.exe`,
  neue `src/ranking/learned_cue_ranker.py`-Schnittstelle und additive CLI-/
  Manifeständerungen. Kein Testsplit, kein realer Batch und keine bestehenden
  Audio-/Output-Artefakte wurden geöffnet oder überschrieben.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m py_compile src\ranking\learned_cue_ranker.py src\batch_render.py src\multi_batch_render.py src\features\cue_ranker_dataset.py; .venv\Scripts\python.exe -m pytest -q tests\test_batch_render.py tests\test_multi_batch_render.py tests\test_ranking.py`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Der `py_compile`-Teil
  scheiterte an einer Windows-PyCache-Berechtigung (`Errno 13` beim Schreiben
  einer temporären `.pyc`); der anschließende Testlauf lief unabhängig davon
  mit `18 passed, 2 warnings` durch.
- **Schlussfolgerung und nächster Schritt:** Kein Quellsyntaxfehler wurde im
  Testimportpfad sichtbar; für weitere Prüfungen wurde korrekt
  `python -B` verwendet, damit kein PyCache-Schreibzugriff erforderlich ist.

## Verifiziert am 2026-08-25 (erste Learned-Integrationssuite, Korrekturlauf)

- **Fragestellung und Reasoning:** CLI-Defaults/Opt-in, fehlender Run,
  Candidate-Hard-Filter, additive Manifeststruktur und Rendererübergabe
  sollten zunächst mit synthetischen Fixtures geprüft werden.
- **Eingaben/Setup:** `tests/test_learned_cue_ranker_integration.py` sowie die
  vorhandenen Cue-Ranker-Modell-, Dataset- und Runner-Tests; `.venv` mit
  `python -B`; kein Testsplit und kein umfangreicher Realbatch.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_learned_cue_ranker_integration.py tests\test_cue_ranker_model.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_runner.py`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Erster Lauf: `16
  passed, 2 errors`; beide Fehler waren fehlende lokale `batch_inputs`-
  Fixture-Definitionen in der neuen Testdatei. Nach Ergänzung einer eigenen
  synthetischen Fixture: `18 passed, 2 warnings`.
- **Schlussfolgerung und nächster Schritt:** Die Fixture-Isolation war die
  einzige Blockade; danach waren die neuen CLI-/Fehlerpfad-Grundprüfungen
  reproduzierbar grün.

## Verifiziert am 2026-08-25 (Learned-Manifest-End-to-End-Korrektur)

- **Fragestellung und Reasoning:** Der synthetische End-to-End-Test musste die
  echte v2-Renderroute verwenden, damit Auswahl-IDs, Learned-Scores und
  bestehende Renderer gemeinsam geprüft werden.
- **Eingaben/Setup:** Synthetische WAVs, Candidate-v2-Metadaten mit verifizierter
  Grid-Provenienz und ein deterministischer Learned-Score-Stub; kein
  Modelltraining, Testsplitzugriff oder Realbatch.
- **Testumfang bzw. Befehl:** Erneut
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_learned_cue_ranker_integration.py`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Ein Zwischenlauf mit
  v1-/1-Takt-Fixture endete mit `1 failed, 4 passed`, weil die v2-Rendereroute
  die nicht unterstützte 1-Takt-Länge korrekt ablehnte. Nach Umstellung auf
  eine gültige 2-Takt-v2-Fixture bestanden der fokussierte Test und danach der
  Einzeltest mit `1 passed`.
- **Schlussfolgerung und nächster Schritt:** Der Fehler bestätigte den
  gewünschten Hard-Filter-/Längenvertrag; die korrigierte E2E-Fixture prüft
  nun echte v2-Auswahl und Rendering-Kompatibilität.

## Verifiziert am 2026-08-25 (Learned-Preflight und CLI-Sonden)

- **Fragestellung und Reasoning:** Beschädigte oder fehlende Checkpoints müssen
  vor Output-Erzeugung klar scheitern; CLI-Optionen müssen sichtbar sein und
  der Default darf nicht kippen.
- **Eingaben/Setup:** Synthetische Run-/Dataset-3-Manifeste, absichtlich
  beschädigte `best.pt`, `python -B`; nur Manifest-/Hash-Dateien in temporären
  Testverzeichnissen, kein Audio- oder Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_learned_cue_ranker_integration.py`;
  `.venv\Scripts\python.exe -B -c "import src.batch_render, src.multi_batch_render, src.ranking.learned_cue_ranker; print('IMPORTS_OK')"`;
  `.venv\Scripts\python.exe -B -m src.batch_render --help | Select-String -Pattern 'ranking-method|cue-ranker-run|feature_baseline_v3|learned_cue_ranker_v1'`;
  entsprechender `src.multi_batch_render --help`-Aufruf.
- **Ergebnis einschließlich Fehlern oder Blockaden:** `6 passed, 2 warnings`;
  `IMPORTS_OK`; beide Help-Sonden zeigen `feature_baseline_v3` als Default und
  `learned_cue_ranker_v1` sowie `--cue-ranker-run`. Keine Outputartefakte
  entstanden.
- **Schlussfolgerung und nächster Schritt:** Fehlerpfad, Manifestvertrag,
  CLI-Opt-in und Importgrenzen sind maschinell bestätigt; anschließend folgt
  die gemeinsame Regression.

## Verifiziert am 2026-08-25 (gemeinsame Batch-/Cue-Ranker-Regression)

- **Fragestellung und Reasoning:** Die additive Integration darf bestehende
  Renderer, Multi-Batch-Fehlersemantik, Feature-Ranking und die bisherige
  Cue-Ranker-Modell-/Dataset-/Teacher-/Runner-Suite nicht brechen.
- **Eingaben/Setup:** Ausschließlich synthetische Pytest-Fixtures und die
  betroffenen Quellmodule; `.venv\Scripts\python.exe -B`; kein Testsplit und
  kein umfangreicher Realbatch.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_learned_cue_ranker_integration.py tests\test_batch_render.py tests\test_multi_batch_render.py tests\test_ranking.py tests\test_cue_ranker_model.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_runner.py tests\test_cue_ranker_teacher.py`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** `40 passed, 2
  warnings in 12.60s`. Die Warnings sind die bekannten Python-3.14-
  `aifc`/`sunau`-Deprecations aus `audioread`; keine Testfehler oder
  Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die Learned-Auswahl ist additiv
  verifiziert: `candidate_ranking` bleibt `feature_baseline_v3`,
  `cue_ranking` trägt Learned-Provenienz/Scores/Selection-IDs, harte v2-
  Filter bleiben vorgeschaltet und Top-K-Rendering bleibt kompatibel.

## Verifiziert am 2026-08-25 (vollständige synthetische Regression)

- **Fragestellung und Reasoning:** Nach der fokussierten Abnahme musste
  ausgeschlossen werden, dass Import-, API- oder Modellregressionen außerhalb
  der direkt betroffenen Batch-/Cue-Ranker-Tests verbleiben.
- **Eingaben/Setup:** Gesamtes Repository-Testset mit `.venv\Scripts\python.exe
  -B`; Pytest-Fixtures und temporäre synthetische Artefakte, kein
  Testsplitzugriff und kein umfangreicher Realbatch.
- **Testumfang bzw. Befehl:** `.venv\Scripts\python.exe -B -m pytest -q`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** `235 passed, 4
  warnings in 34.95s`. Die vier bekannten Warnings sind zwei
  `aifc`/`sunau`-Deprecations aus `audioread` und zwei bestehende PyTorch-
  CUDA-Determinismus-Warnings; keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die additive Integration ist gegen
  die vollständige synthetische Regression abgesichert. Es bleibt nur die
  Übergabe ohne Commit; reale Learned-Batches und Testsplitzugriff wurden
  bewusst nicht gestartet.

## Verifiziert am 2026-08-25 (vollständige Regression nach Manifest-Audit)

- **Fragestellung und Reasoning:** Nach den expliziten Manifestfeldern für
  Modellname, Checkpoint-/Dataset-SHA und Teachervertrag musste die vollständige
  Suite erneut laufen, damit genau diese letzte Änderung keine Regression
  erzeugt.
- **Eingaben/Setup:** Aktueller Arbeitsbaum, `.venv\Scripts\python.exe -B`,
  unveränderte synthetische Testfixtures; kein Testsplit und kein Realbatch.
- **Testumfang bzw. Befehl:** `.venv\Scripts\python.exe -B -m pytest -q`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** `235 passed, 4
  warnings in 36.04s`; dieselben bekannten `aifc`/`sunau`- und PyTorch-CUDA-
  Determinismus-Warnings, keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der finale Arbeitsbaum ist
  synthetisch vollständig regressionsgeprüft und bereit zur Übergabe; es wurde
  kein Commit erstellt.

## Verifiziert am 2026-08-22 (Repository-Audit: Feature-Manifest-Hashsemantik)

- **Fragestellung und Reasoning:** Ein erster Vergleich des in erlaubten
  Train-Metadaten deklarierten `source_feature_cache.manifest_sha256` mit dem
  Bytehash der referenzierten Datei war unterschiedlich. Vor einer
  Fehlklassifikation als Artefaktkorruption musste geprüft werden, welche
  Hashsemantik der Exporter tatsächlich verwendet.
- **Eingaben/Setup:** Nur die erste Zeile von
  `metadata/2bar/train.jsonl` des realen Dataset-2 und das darin referenzierte
  Source-Feature-`manifest.json`; `.venv\Scripts\python.exe -B`. Kein
  Testsplit und keine Feature-NPZ wurden geöffnet.
- **Testumfang bzw. Befehl:** Read-only Berechnung (a) des SHA-256 über die
  kanonische, sortierte JSON-Darstellung analog
  `variable_dataset_export._artifact_metadata()` und (b) des SHA-256 über die
  tatsächlichen Manifestbytes; Vergleich mit dem deklarierten Feld.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Exit-Code 0. Der
  deklarierte Hash
  `fd85363714601bbfe66c322d61569eae5d67523033770e4274052000a5812efe`
  stimmt exakt mit dem kanonischen JSON-Hash überein. Der Datei-Bytehash ist
  erwartungsgemäß ein anderer Wert
  (`f60f3cb3793fd0724d0b2bd8a08330a28a909378a80d9d9e53fba3cf2eb7cfde`).
  Es liegt damit in dieser Sonde keine Manifestkorruption vor.
- **Schlussfolgerung und nächster Schritt:** Das Feld ist ein kanonischer
  Inhalts-Hash, obwohl der Name keine Semantik unterscheidet. Relevant für
  das Audit bleibt, dass der spätere variable Waveform-Loader diesen im
  Dataset gespeicherten Hash nicht vergleicht und der Track-Feature-Payload
  selbst keinen manifestierten Datei-/Arrayhash besitzt. Keine Reparatur
  wurde vorgenommen.

## Verifiziert am 2026-08-22 (Repository-Audit: Diff- und Statusabschluss)

- **Fragestellung und Reasoning:** Nach allen Auditprüfungen musste bestätigt
  werden, dass keine unerlaubten Produktions-, Test-, Konfigurations-,
  Vertrags-, Audio- oder Artefaktänderungen entstanden sind und der erlaubte
  Dokumentationsdiff keine Whitespacefehler enthält.
- **Eingaben/Setup:** Arbeitsbaum nach den vier vorgeschriebenen
  Audit-Testeinträgen in `docs/Bemerkungen.md`; keine weiteren geplanten
  Dateischreibzugriffe.
- **Testumfang bzw. Befehl:** `git diff --check` und
  `git status --short --branch`.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Exit-Code 0; keine
  Whitespacefehler. Git meldete lediglich den erwarteten LF/CRLF-Hinweis für
  `docs/Bemerkungen.md`. Der Status war `main...origin/main` mit genau dieser
  einen geänderten Datei.
- **Schlussfolgerung und nächster Schritt:** Der Audit-Arbeitsbaum enthält nur
  die laut Auftrag erlaubte Testdokumentation; es wurde kein Commit erstellt.
  Es folgen keine Reparaturen, sondern ausschließlich der Abschlussbericht.

## Verifiziert am 2026-08-22 (Repository-Audit: reale erlaubte Artefakte)

- **Fragestellung und Reasoning:** Die zentralen aktuellen Claims zu
  Dataset-2-Train/Validation, Binärprovenienz, Cachebindung und den zwei
  vorhandenen variablen Run-Verzeichnissen sollten gegen die gespeicherten
  Artefakte geprüft werden, ohne einen Test-Shard, Test-Metadaten oder
  Checkpoint-Inhalt zu öffnen.
- **Eingaben/Setup:** Dataset
  `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`, nur
  dessen `train`- und `validation`-NPZ/JSONL-Dateien; Cache-Rootmanifest
  `output/ml_cache/variable_bridge_waveform_v2/manifest.json`; öffentliche
  Manifeste und manifestierte Dateihashes der variablen CUDA-Smoke- und
  20-Epochen-Runs; `aufTAKTCl.exe` plus versionierte Provenienzdatei.
  Python lief ausschließlich über `.venv\Scripts\python.exe -B`.
- **Testumfang bzw. Befehle:** Read-only Laden aller acht erlaubten
  Dataset-2-Shards mit `VariableFeatureDataset` und Finite-/Shapeprüfung;
  anschließend PowerShell-SHA-256-Prüfung des aufTAKT-Binaries, der 16
  Train-/Validation-Dateien, der Datasetbindung im Cache-Rootmanifest und der
  sechs manifestierten History-/Best-/Latest-Dateien beider variablen Runs.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Die erste kompakte
  Python-Reportform gab wegen einer ungeeigneten
  List-Comprehension-Ausdrucksform nur den Erfolgsmarker, aber keine Zeilen
  aus; sie wurde ohne Artefaktschreibzugriff klarer wiederholt. Die
  Wiederholung bestätigte Train `105` und Validation `12` je Länge, Shapes
  `(N,16/32/48/64,54)`, globale Shapes `(N,16)`, endliche Werte und
  `length_condition=0,25/0,5/0,75/1,0`. Der erste PowerShell-Hashcheck brach
  vor der Prüfung mit einem Parserfehler an `"run:$run:$name"` ab; die
  korrigierte Wiederholung endete mit Exit-Code 0 und `BAD_COUNT=0`.
  Verifiziert wurden aufTAKT-SHA
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`
  bei 7.195.648 Bytes, Datasetmanifest-SHA
  `b86d0c46329c653a6984d9a3eed59b1f763165bee308b9c67925cf8727bed5cd`,
  Cache-Rootmanifest-SHA
  `5dc9982e167b1b8610fde4b2b4e3e01899eae3ba255dc69c4e5080233b313a2e`
  sowie alle 16 beziehungsweise sechs geprüften Dateihashes.
- **Schlussfolgerung und nächster Schritt:** Die erlaubten realen
  Train-/Validation-Artefakte und ihre unmittelbaren Hashbindungen sind
  intakt. Nicht geprüft wurden bewusst alle Test-Shard-Bytes, Test-Metadaten,
  Answer Keys und die numerischen Inhalte der Checkpoints. Der Arbeitsbaum
  wird abschließend auf unerlaubte Änderungen und Diff-Whitespace geprüft.

## Verifiziert am 2026-08-22 (Repository-Audit: vollständige Regression)

- **Fragestellung und Reasoning:** Nach vollständig gelesenen Tests, grüner
  gezielter Regression und drei isolierten Negativsonden sollte die gesamte
  vorhandene Testsuite auf Regressionen geprüft werden. Die Suite war nach
  dem dokumentierten Laufumfang von rund 40 Sekunden verhältnismäßig; sie
  ersetzt keine Prüfung der im Audit identifizierten ungetesteten Pfade.
- **Eingaben/Setup:** Aktueller Arbeitsbaum mit ausschließlich den für dieses
  Audit vorgeschriebenen Einträgen in `docs/Bemerkungen.md`;
  `.venv\Scripts\python.exe -B`; pytest-Cacheprovider deaktiviert. Die Tests
  verwendeten ihre synthetischen beziehungsweise temporären Fixtures; der
  reale Testsplit, Originalaudio und bestehende Output-Artefakte wurden nicht
  als Audit-Eingabe geöffnet oder verändert.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider`
- **Ergebnis einschließlich Fehlern oder Blockaden:** `209 passed, 4 warnings
  in 44.81s`; Exit-Code 0. Die Warnungen waren die zwei bekannten
  `aifc`-/`sunau`-DeprecationWarnings aus `audioread` sowie zwei
  PyTorch-Hinweise, dass CUDA-Backwards für `upsample_linear1d` und
  `adaptive_avg_pool2d` trotz `torch.use_deterministic_algorithms(...,
  warn_only=True)` keine deterministische Implementierung besitzen. Keine
  Testfehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die aktuelle Regression ist
  vollständig grün und reproduziert den dokumentierten Umfang von 209 Tests.
  Wegen der beiden CUDA-Warnungen ist daraus keine bitgenaue
  GPU-Reproduzierbarkeit ableitbar. Zudem bleiben die durch Negativsonden und
  statische Analyse belegten, in der Suite nicht behaupteten Grenzfälle echte
  Audit-Findings. Es folgen nur noch Artefakt-/Hash- und Arbeitsbaumchecks.

## Verifiziert am 2026-08-22 (Repository-Audit: drei read-only Negativsonden)

- **Fragestellung und Reasoning:** Drei statisch gefundene, von der grünen
  Regression nicht abgedeckte Pfade sollten ohne Artefaktschreibzugriff
  reproduziert werden: Wiederverwendung eines aufTAKT-Beats im historischen
  Merge-v1 trotz erfolgreichem Struktur-Gate, Rekonstruktion der
  A/B-Zuordnung aus dem öffentlichen Blind-Seed sowie eine Kollision der
  variablen Trainings-Run-ID bei unterschiedlichen vorhandenen Läufen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`; ausschließlich
  In-Memory-Beatzeiten sowie die öffentlichen
  `manifest.json`-Dateien des abgeschlossenen v4-Hörsatzes und der vorhandenen
  variablen CUDA-Smoke-/20-Epochen-Run-Verzeichnisse. Kein
  `answer_key.json`, kein Dataset-Shard, kein Testsplit und kein Checkpoint
  wurde geöffnet; es wurden keine Dateien geschrieben.
- **Testumfang bzw. Befehl:** Read-only Python-Sonde mit
  `PreAnalysis._find_closest_beat_index()` und
  `_has_complete_bar_metadata()`, `random.Random(blind_seed)` aus dem
  öffentlichen Studienmanifest sowie Vergleich von `run_id`, vollständigem
  Run-Vertrag, Epochenzahl und manifestierten Latest-Checkpoint-SHAs der zwei
  variablen Run-Manifeste.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Exit-Code 0. Merge-v1
  ordnete vier Librosa-Zeiten den aufTAKT-Indizes `[0, 1, 1, 2]` zu und das
  Struktur-Gate akzeptierte die daraus gebildeten 3-Tupel trotzdem. Aus dem
  öffentlichen Seed `20260730` ließ sich für die acht öffentlichen Paare die
  Baseline-Label-Folge `ABAABAAB` bestimmen. Die zwei variablen Runs tragen
  denselben `run_id=80978bbff5046b30f53c` und denselben Vertrag, aber
  `last_epoch=2` beziehungsweise `20` sowie unterschiedliche
  Latest-Checkpoint-SHAs.
- **Schlussfolgerung und nächster Schritt:** Alle drei Auditbefunde sind über
  erreichbare read-only Pfade reproduziert. Die Sonde beweist nicht, dass ein
  Rater den Blind-Seed tatsächlich ausgenutzt hat; sie beweist aber, dass die
  technische Verblindung aus den öffentlichen Daten rekonstruierbar ist.
  Als Nächstes wird die verhältnismäßige Vollsuite ausgeführt.

## Verifiziert am 2026-08-22 (Repository-Audit: gezielte Regression)

- **Fragestellung und Reasoning:** Vor einer Vollsuite sollten die im Audit
  besonders relevanten Verträge für den monotonen Merge-v2, den variablen
  Waveform-Cache, den variablen TCN/BiLSTM-Runner samt Resume, den
  Heldout-Studienloader und das Rubber-Band-Time-Stretching mit ihren bereits
  gelesenen synthetischen Tests geprüft werden. Der Lauf diente der
  Regressionserfassung, nicht der Behebung gefundener Audit-Findings.
- **Eingaben/Setup:** Repository-Stand vom 2026-08-22; ausschließlich
  vorhandene synthetische beziehungsweise pytest-temporäre Fixtures;
  `.venv\Scripts\python.exe -B`; pytest-Cacheprovider deaktiviert. Reale
  Audio-, Dataset-, Cache- und Run-Artefakte sowie der reale Testsplit wurden
  nicht geöffnet oder verändert.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py tests/test_heldout_control_study.py tests/test_time_stretch.py`
- **Ergebnis einschließlich Fehlern oder Blockaden:** `32 passed in 63.53s`;
  Exit-Code 0, keine Fehler, Warnungen oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die vorhandenen Regressionstests
  dieser fünf Risikogruppen sind grün. Das widerlegt die statisch gefundenen,
  von diesen Tests nicht abgedeckten Fälle (unter anderem öffentlich
  rekonstruierbare Blindzuordnung, unvollständiger variabler Run-Vertrag und
  nicht äquivalenter Resume-Zustand) nicht. Als Nächstes folgen kleine
  read-only Audit-Sonden und danach, sofern weiterhin verhältnismäßig, die
  vollständige Suite.

## Verifiziert am 2026-08-20 (W&B-Trainingsläufe aller Modelle)

- **Fragestellung und Reasoning:** Nach der W&B-Integration sollten alle drei
  aktuell vorhandenen Modellpfade auf demselben erweiterten Datensatz mit
  identischem Seed, GPU-Setup und gemeinsamer W&B-Gruppe trainiert werden.
  Wegen der fehlgeschlagenen Online-Authentifizierung wurden die Runs lokal
  als W&B-Offline-Runs aufgezeichnet, damit Metriken und Checkpoint-Artefakte
  nach einem gültigen Login synchronisiert werden können.
- **Eingaben/Setup:** Dataset
  `output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805`
  mit 370 Train- und 50 Validation-Beispielen; Seed `20260820`;
  `--device auto` löste auf `cuda:0` (NVIDIA GeForce RTX 5070 Ti) auf;
  `--max-epochs 30`; W&B-Projekt `beatbridge`; Gruppe
  `beatbridge-all-models-20260820`; W&B SDK `0.28.1`; Checkpoint-Logging
  aktiviert. Der RoFormer-Vocal-Run nutzte
  `roformer-model-bs-roformer-sw-by-jarredou`.
- **Testumfang bzw. Befehle:** Ausgeführt wurden die CLI-Pfade
  `src.ml train`, `src.ml train-vocal` und `src.ml train-tcn-bilstm`, jeweils
  mit `--wandb-mode offline --wandb-project beatbridge
  --wandb-group beatbridge-all-models-20260820 --wandb-log-checkpoints`.
  Der MLP-Lauf wurde nach der Korrektur von `WANDB_DATA_DIR` einmal unter
  einem separaten Output-Verzeichnis wiederholt, damit auch sein Artefakt
  vollständig gestaged wird.
- **Ergebnis:**
  - `time_shared_mlp_v1`: Early Stopping in Epoche 8, beste Validation in
    Epoche 2, Loss `0,4149939463`; Offline-Run unter
    `output/training_runs/wandb_time_shared_mlp_v1_extended_bpm145_165_offline_20260820_rerun/`.
  - `vocal_time_shared_mlp_v2`: abgeschlossen bis Epoche 30, beste Validation
    in Epoche 25, Loss `0,3292209521`; Offline-Run unter
    `output/training_runs/wandb_vocal_time_shared_mlp_v2_roformer_extended_bpm145_165_offline_20260820/`.
  - `tcn_bilstm_transition_control_v1`: Early Stopping in Epoche 17, beste
    Validation in Epoche 11, Loss `0,3226487994`; Offline-Run unter
    `output/training_runs/wandb_tcn_bilstm_transition_control_v1_extended_bpm145_165_offline_20260820/`.
  Alle drei Läufe meldeten vollständige Cache-Hits und legten lokale
  `history.json`, `manifest.json`, `checkpoints/best.pt`,
  `checkpoints/latest.pt` sowie W&B-Run-Dateien an. Für den wiederholten MLP-,
  Vocal- und TCN-Lauf wurden Artefakt-Staging-Dateien im jeweiligen lokalen
  W&B-Datenverzeichnis erzeugt.
- **Fehler/Blockaden:** `.venv\Scripts\wandb.exe login --verify` schlug mit
  „API key verification failed“ fehl; ein anschließender Online-Trainingsstart
  meldete „user is not logged in“. Die eigentlichen Offline-Trainings und das
  lokale Logging waren davon nicht betroffen. Die beiden vorherigen, nur
  teilweise gestarteten Online-Versuche wurden nicht gelöscht.
- **Schlussfolgerung und nächster Schritt:** Die drei Modellpfade trainieren
  mit W&B-Logging reproduzierbar auf CUDA. Nach einem erneuten gültigen Login
  sind die Offline-Runs mit `.venv\Scripts\wandb.exe sync <offline-run>` in
  die Cloud übertragbar; die lokalen Manifeste bleiben die maßgebliche
  Provenienz.

## Verifiziert am 2026-08-20 (W&B-Trainingsabschlusschecks)

- **Fragestellung und Reasoning:** Nach den realen Läufen sollten Adapter,
  Abhängigkeiten, Manifeste, Checkpoints und lokale W&B-Run-Dateien nochmals
  gemeinsam geprüft werden.
- **Eingaben/Setup:** Die drei neuen Offline-Output-Verzeichnisse des
  MLP-Reruns, Vocal-v2-Runs und TCN/BiLSTM-Runs; `.venv` mit `wandb==0.28.1`.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q tests\test_wandb_logging.py`,
  `.venv\Scripts\python.exe -m pip check`, PowerShell-JSON-Prüfung der
  drei `manifest.json` inklusive `cuda:0`, Checkpoint-Dateien und Offline-Run-
  Anzahl sowie `git diff --check`.
- **Ergebnis:** W&B-Tests **3 passed in 2,43 s**; `pip check` meldet
  `No broken requirements found`. Alle drei Manifeste sind lesbar, enthalten
  `best.pt` und `latest.pt`, melden jeweils `cuda:0` und je einen lokalen
  W&B-Offline-Run. Das Artefakt-Staging enthält bei jedem Lauf vier Dateien.
  `git diff --check` meldete keine Whitespace-Fehler; nur erwartete
  LF/CRLF-Konvertierungswarnungen.
- **Schlussfolgerung und nächster Schritt:** Der lokale Trainings- und
  Logging-Workflow ist abgeschlossen. Offen bleibt nur die Cloud-Synchroni-
  sation nach Korrektur des W&B-API-Keys.

## Offene Beobachtungen

- **Beobachtung (2026-08-18, gelernte Vocal-Outputs):** Das Notebook lädt jetzt den manifest- und SHA-geprüften Best-Checkpoint `vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805`, Epoche 22, mit 20.821 Parametern. Er wird auf das echte Validation-Beispiel `example-826d104398f9b3d2` aus demselben Dataset angewendet. Visualisiert und beschriftet werden `mix_position`, `low_end_position`, `vocal_position`, `vocal_duck_a`, `vocal_duck_b`, `vocal_gain_a` und `vocal_gain_b`. Die gelernten Vocal-Positionen, Ducking-Werte und resultierenden Gains weichen sichtbar von der linearen Nullinitialisierung ab.
- **Testlauf (2026-08-18, gelernter Vocal-Checkpoint):** Fragestellung war, ob der reale Best-Checkpoint sicher geladen und auf das Notebook-Validation-Beispiel angewendet werden kann. Setup: `.venv`, `MPLBACKEND=Agg`, Dataset `feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805`, Loader `_load_best_vocal_model` mit `weights_only=True`, Checkpoint-Epoche 22. Ergebnis: fehlerfrei; Dataset-ID und Manifest-SHA stimmen überein, Output-Shapes sind für `mix_position`, `low_end_position`, `vocal_position`, `vocal_duck_a/b` und `vocal_gain_a/b` jeweils `(1, 32)`, Figure `1400×900` visuell geprüft. Der erste Versuch hatte eine Abhängigkeit von einer Hilfsfunktion aus der vorherigen Output-Zelle; diese wurde entfernt, sodass die gelernte Vocal-Zelle nun eigenständig nach der ML-Eingabezelle ausführbar ist. Schlussfolgerung: Gelernte Vocal-Outputs sind reproduzierbar und mit dem konkreten Validation-Beispiel verknüpft.
- **Beobachtung (2026-08-18, ML-Output-Ansicht):** Das Notebook visualisiert nun auch die beschrifteten Outputs von `time_shared_mlp_v1`: `mix_position` und `low_end_position` als zwei Kurven mit jeweils `(1, 32)` sowie `mix_increment_logits` und `low_end_increment_logits` als separate Diagnosekurven mit `(1, 31)`. Die Grafik zeigt die 0–1-Ausgabebegrenzung und die 32 beziehungsweise 31 Halbbeat-/Intervallpositionen. Für das aktuell verwendete frisch instanziierte Modell sind die Kurven wegen der dokumentierten Nullinitialisierung zunächst deckungsgleich mit der linearen Equal-Power-Baseline; ein geladener Checkpoint kann davon abweichen.
- **Testlauf (2026-08-18, ML-Output-Smoke-Test):** Fragestellung war, ob die neue Output-Grafik die tatsächlichen `FeatureControlOutput`-Tensoren aus dem Validation-Beispiel robust in Kurven umwandelt und beschriftet. Setup: Projektwurzel, `.venv`, `MPLBACKEND=Agg`, Initialisierungszelle, ML-Eingabezelle und Output-Zelle aus `listen_batch.ipynb`. Ergebnis: fehlerfrei; `mix_position (1, 32)`, `low_end_position (1, 32)`, `mix_increment_logits (1, 31)`, `low_end_increment_logits (1, 31)`, Figure `1300×700` visuell geprüft. Schlussfolgerung: Output-Visualisierung ist reproduzierbar; nächster Schritt ist die Prüfung mit einem geladenen trainierten Checkpoint.
- **Beobachtung (2026-08-18, Vocal-Feature-Ansicht):** Das Notebook enthält zusätzlich eine separate Ansicht ausschließlich für die sechs Vocal-Features aus dem Vertrag. Source A und Target B werden als beschriftete `6 × 32`-Heatmaps visualisiert; die Vertragsindizes sind 45–50: `vocal_activity`, `vocal_prominence`, `vocal_onset_probability`, `vocal_offset_probability`, `vocal_phrase_progress` und `vocal_confidence`. Die Darstellung nutzt die gültige 0–1-Skala; `vocal_valid` bleibt als separate Gültigkeitsmaske bewusst außerhalb. Der headless Lauf und die visuelle Renderkontrolle waren fehlerfrei.
- **Testlauf (2026-08-18, Vocal-Feature-Smoke-Test):** Fragestellung war, ob die neue reine Vocal-Ansicht aus dem bereits geladenen ML-Beispiel die Vertragskanäle korrekt findet, beschriftet und rendert. Setup: Projektwurzel, `.venv`, `MPLBACKEND=Agg`, `listen_batch.ipynb`, Validation-Beispiel `example-826d104398f9b3d2`; ausgeführt wurden die Initialisierungszelle, die ML-Visualisierungszelle und die neue Vocal-Zelle per Python-`exec`, zusätzlich wurde die Figure als temporäres PNG gerendert und visuell geprüft. Ergebnis: fehlerfrei, exakt sechs Kanäle auf Indizes 45–50, Shape je Track `6 × 32`, Ausgabe `Figure(1500x560)`. Schlussfolgerung: Die Vocal-Beschriftungen und die getrennte Source-/Target-Ansicht sind korrekt; nächster Schritt ist die Nutzung im geöffneten Jupyter-Notebook.

- **Beobachtung (2026-08-18, Notebook-ML-Visualisierung):** `notebooks/listen_batch.ipynb` visualisiert jetzt neben den ausgerichteten Bridge-Waveforms ein echtes Validation-Beispiel (`example-826d104398f9b3d2`) aus dem aktuellen Datensatz. Die Heatmaps zeigen `features_a/features_b` mit jeweils `(32, 54)`, der globale Balkenplot `(16,)`; zusätzlich werden die MLP-Fusion `(31, 124)` und die beiden Ausgabekurven `(1, 32)` ausgewiesen. Der zugehörige Objective-Waveform-Cache hat `(2, 69632)` bei 11.025 Hz und ist ausdrücklich als Zusatzinput, nicht als direkter MLP-Input markiert. Der headless Notebook-Zelltest lief ohne Fehler; nächster Schritt ist die visuelle Kontrolle beim Öffnen in Jupyter.
- **Testlauf (2026-08-18, Notebook-Smoke-Test):** Fragestellung war, ob die neue Notebook-Zelle aus einer frischen Python-Namespace die gespeicherten Dataset-/Cache-Artefakte laden, die Shape-Verträge validieren, `time_shared_mlp_v1` ausführen und eine Figure erzeugen kann. Setup: Projektwurzel, `.venv`, `MPLBACKEND=Agg`, `notebooks/listen_batch.ipynb`, Validation-Split des erweiterten Datensatzes. Befehl: `.venv\\Scripts\\python.exe -c \"import json; nb=json.load(open('notebooks/listen_batch.ipynb',encoding='utf-8')); ns={}; exec(''.join(nb['cells'][1]['source']),ns); exec(''.join(nb['cells'][7]['source']),ns)\"`. Ergebnis: fehlerfrei; Beispiel `example-826d104398f9b3d2`, Waveforms `(2, 69632)`, Features `(32,54)/(32,54)/(16,)`, MLP-Ausgaben `(1,32)`. Die Figure wurde zusätzlich gerendert und visuell auf abgeschnittene Titel und überfüllte Global-Labels geprüft; danach wurden beide Layoutpunkte behoben. Schlussfolgerung: Notebook-Artefakt ist reproduzierbar und lesbar; nächster Schritt ist die Nutzung in Jupyter durch den Menschen.
- **Testlauf (2026-08-18, ML-Modellregression):** Fragestellung war, ob die unveränderte MLP-Modellimplementierung weiterhin mit dem Notebook-Beispielvertrag kompatibel ist. Setup: `.venv`, gezielter Pytest-Lauf. Befehl: `.venv\\Scripts\\python.exe -m pytest -q tests/test_feature_control_model.py`. Ergebnis: **2 passed in 3,08 s**, keine Fehler. Schlussfolgerung: Der Modellvertrag bleibt grün.
- **Testlauf (2026-08-18, ML-Datasetregression — Blockade):** Ergänzend wurde `.venv\\Scripts\\python.exe -m pytest -q tests/test_feature_control_model.py tests/test_ml_data.py` ausgeführt, um auch die Waveform-Dataset-Verbindung abzudecken. Nach den zwei bestandenen Modelltests blieb der Lauf während `tests/test_ml_data.py` ohne weitere Ausgabe hängen und wurde nach wiederholten Polls manuell mit `Ctrl+C` beendet (Exit-Code 1); kein Assertion-Fehler wurde ausgegeben. Schlussfolgerung: Die Notebook-Zelle ist unabhängig davon erfolgreich; die bekannte Librosa/Numba-Initialisierungsblockade bei breiteren ML-Dataset-Tests bleibt offen und ist kein Fehler der Notebook-Änderung.

- **Beobachtung (2026-08-12, RoFormer-Training):** Der selbstüberwachte Vocal-Control-Trainingslauf v2 verwendete für alle 370 Train- und 50 Validation-Beispiele ausschließlich vorhandene RoFormer-Bridge-Caches. Auf `cuda:0` stoppte der Lauf nach Epoche 27 frühzeitig; der beste Checkpoint stammt aus Epoche 21 mit Validation-Loss `0,3318392038` gegenüber `0,350723` bei der Initialisierung. Der Testsplit blieb unberührt.

- **Beobachtung (2026-08-12, aktueller Datensatz):** Der RoFormer-Vocal-Cache wurde für den erweiterten SHA-getrennten Datensatz vollständig erzeugt (370/50/60 Train-/Validation-/Testbeispiele). Dabei entstanden 55 eindeutige Vocal-Stem-Artefakte und 480 RoFormer-Bridge-Caches. Der konfigurierte `jarredou`-SW-Download war nicht mehr öffentlich erreichbar (`401`); der identische Checkpoint wurde deshalb über den dokumentierten `enerjazzer/BS-ROFO-SW-Fixed`-Mirror geladen und per SHA-256 verifiziert.

- **Beobachtung (2026-08-12, Dokumentationsaudit):** Der aktuelle Vocal-v2-Modellhörsatz unter `output/control_studies/blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806/` enthält fünf geblendete Paarungen und `ratings.json` mit **0/5 Ratings**. Es gibt noch kein `study_results.json`; der Satz gilt daher weiterhin als offen und nicht als ausgewertete Hörstudie.
- **Entscheidung (2026-08-12, Dokumentationsrollen):** `STATUS.md` bleibt Einstieg mit aktuellem Stand und priorisierten nächsten Schritten. Chronologische Beobachtungen, Entscheidungen und gelernte Lektionen werden in dieser Datei fortgeführt; die detaillierten historischen Verifizierungsblöcke in `STATUS.md` sind Übergangsarchiv und keine parallelen Backlogs.
- **Gelernt (2026-08-12, Dokumentationsaudit):** Die Aussage „fehlende Downbeat-Metadaten führen zum Abbruch, ohne Fallback“ beschreibt nicht den aktuellen Stand. Die Analyse erzeugt ein markiertes approximatives Raster; erst die Kandidatengenerierung lehnt es standardmäßig mit `approximate_grid_policy = reject` ab. `allow` ist ein expliziter Opt-in.
- **Beobachtung (übernommen am 2026-07-17):** Die BPM-Ergebnisse von librosa und aufTAKT weichen für `HELP_LESS` voneinander ab (librosa: 161 BPM, aufTAKT: 157 BPM). Ursache und maßgebliches Grid sind noch nicht entschieden.
- **Beobachtung (übernommen am 2026-07-17):** Das erkannte Taktraster umfasst überwiegend vier Beats, musikalisch relevante Phrasen im Entwicklungsset häufig acht Beats. Kandidatengenerierung muss deshalb Beat, Takt und Phrase getrennt modellieren.
- **Beobachtung (2026-07-21):** Der erste reale Batch `HELP_LESS → BREATH_LESS` erzeugte einen akzeptierten 2-Takt-Kandidaten und zwei WAV-Varianten (`fade`, `equal_power`) ohne Fehler. Die BPM-Werte der gecachten librosa-Analyse stimmen für dieses Paar mit 161,499 überein; eine menschliche Hörbewertung steht noch aus.
- **Beobachtung (2026-07-21):** `feature_baseline_v1` bewertete für `HELP_LESS → BREATH_LESS` 48 Kandidaten und exportierte die Top 3 fehlerfrei als Equal-Power-Fades. Rang 1 (`candidate-33640deded712342`, Score 0,845) hat trotz sehr hoher Chroma-/Spektralähnlichkeit noch 11,22 dB RMS-Differenz. Ob das Ranking hörbar besser ist, muss durch die neue menschliche Bewertung geprüft werden.
- **Beobachtung (2026-07-21):** Die ersten vier nutzbaren Target-Grenzen von `BREATH_LESS` liegen im leisen Intro bei ungefähr −16 dB RMS; energiereiche 4-Takt-Fenster liegen später, unter anderem ab Takt 52/57/63. Der auf vier frühe Grenzen begrenzte Suchraum war daher die primäre Ursache dafür, dass Ranking v1 keinen High-Power-Zielteil wählen konnte.
- **Beobachtung (2026-07-21):** `feature_baseline_v2` bewertete 736 HELP_LESS→BREATH_LESS-Kandidaten über den gesamten Target-Track. Rang 1 verbindet Source-Takt 112 mit Target-Takt 65 (91,60 s) über 2 Takte; Source und Target messen −5,33/−5,47 dB, High-Power-Komponente 0,829. Die globalen Top 3 verwenden 2 Takte. Der beste 4-Takt-Kandidat (`candidate-966e75d1a240fc27`, Score 0,919, Target-Takt 63) wurde separat exportiert. Keine Fehler; Hörurteil offen.
- **Beobachtung (2026-07-21):** Die letzten Source-Grenzen markieren kein klares Drop-Ende (nur rund 1 dB Abfall). HELP_LESS zeigt einen deutlich stärkeren natürlichen Abfall um Takt 52; deshalb muss auch der Source-Suchraum den ganzen Track umfassen.
- **Beobachtung (2026-07-21):** `feature_baseline_v3` bewertete 14.196 kompatible HELP_LESS→BREATH_LESS-Kandidaten. Rang 1 verbindet Source-Takt 50 mit Target-Takt 109 über 4 Takte: 3,36 dB Abfall nach A, Source-Auslauf −9,02 dB, Target-Vorlauf −13,11 dB und 6,54 dB Anstieg zu B. Drei Bridge-WAVs wurden ohne Fehler exportiert; Hörurteil offen.
- **Beobachtung (2026-07-29):** Die reale `differentiable_control_v1`-Sonde exportierte acht WAVs für vier unterschiedliche 4-Takt-Paare aus dem Multi-Song-Batch vom 22.07. Der Proxy-Loss sank je Paar um 24,1 %, 97,2 %, 60,7 % und 69,6 %. Die historische Render-Metrik bevorzugt die optimierte Variante nur in zwei von vier Fällen und bewertet die anderen beiden geringfügig schlechter. Das ist ein erwünschtes Differentialsignal für den Hörtest; Proxy-Verbesserung darf nicht mit musikalischer Verbesserung gleichgesetzt werden.
- **Beobachtung (2026-07-29):** Die monotonen v2-Übergänge klingen laut Nutzerurteil bereits besser. Der verbleibende problematische Fall `STRUGGLING → ASCENSION` wird nicht der Metrik zugeschrieben, sondern dem mit 172,266 BPM gegenüber 161,499 BPM musikalisch zu schnellen Source-Track.
- **Beobachtung (2026-07-30):** Im vollständig geblendeten v3-Hörsatz mit acht Paaren erhielt die Equal-Power-Baseline vier Präferenzen, die direkt proxy-optimierte monotone Kurve drei und ein Paar einen Gleichstand. Über alle fünf Kriterien lagen die Mittelwerte bei 4,325 für Baseline und 4,250 für Optimiert. Die methodischen Differenzen waren 0,000 bei Sauberkeit, −0,125 bei Energieform, 0,000 bei Low-End-Übergabe, 0,000 bei rhythmischer Stabilität und −0,250 bei Artefaktfreiheit, jeweils Optimiert minus Baseline. Das ist kein Nachweis einer allgemeinen Überlegenheit: Es liegt nur ein vollständiger Bewertungssatz einer Person auf einer gezielt ausgewählten, kleinen Stichprobe vor.

## Entscheidungen und Gelerntes

- **Entscheidung (2026-08-12):** Das geplante größere Hauptmodell wird als
  additive `tcn_bilstm_transition_control_v1`-Architektur neben den kleinen
  MLP-Baselines implementiert: geteilter temporaler Encoder, explizite
  `[A, B, A-B, A*B]`-Fusion, globale Paarfeatures und zweilagiger BiLSTM.
  Grund: Die Architektur soll zeitliche Übergangszusammenhänge lernen, ohne
  die reproduzierbaren v1/v2-Checkpoints oder deren Verträge zu verändern.

- **Entscheidung (2026-07-17):** Rendering arbeitet standardmäßig mit 44,1 kHz und kanalorientiertem Stereo-Audio. Grund: Das Entwicklungsset enthält sowohl 44,1-kHz- als auch 48-kHz-Dateien; ein gemeinsames Raster verhindert stilles Fehl-Timing.
- **Entscheidung (2026-07-17):** Der programmatische Rückgabevertrag startet mit `format_version = 1`; inkompatible Änderungen benötigen eine neue Version.
- **Entscheidung (2026-07-21):** Übergangskandidaten führen die Länge kanonisch in Takten (`1/2/4`); die Beatanzahl wird aus dem vollständigen Taktfenster abgeleitet. Grund: Takte sind die musikalisch und für Nutzer:innen verständliche Constraint-Einheit, während die bestehenden Fade-Renderer weiterhin Beatanzahlen benötigen.
- **Entscheidung (2026-07-21):** `bar_grid_v1` akzeptiert nur Kandidaten mit vollständiger Downbeat-/Taktmetadaten, vollständigem Pre-Roll und höchstens 15 % relativer BPM-Differenz. Grund: Diese Eigenschaften sind vor dem Rendering zuverlässig messbar; Phrasen, Vocal-Overlap und Energie bleiben spätere, explizit modellierte Komponenten statt stiller Heuristiken.
- **Entscheidung (2026-07-21):** Batch-Exporte schreiben WAVs und `manifest.json` atomar und verweigern vorhandene Zielartefakte ohne explizites `--overwrite`. Grund: Vergleichsexperimente müssen auf Kandidaten, Renderer und Quell-Hashes zurückführbar bleiben; ein stilles Überschreiben würde diese Provenienz zerstören.
- **Entscheidung (2026-07-21):** Das erste Ranking bleibt eine transparente, versionierte Feature-Baseline aus Chroma, RMS, spektralem Schwerpunkt und Tempo; Phrasen und Vocals werden als bekannte Lücken ausgewiesen. Grund: Einzelkomponenten und Fehlannahmen müssen vor Embedding- oder ML-Vergleichen nachvollziehbar sein.
- **Entscheidung (2026-07-21):** Der aktuelle Standardworkflow sucht High Power A → 2-/4-Takt-Übergang → High Power B. Dafür wird der gesamte nutzbare Target-Track durchsucht, die Target-Energie nach dem Cut gemessen und relativ zur Energieverteilung des jeweiligen Tracks bewertet. Grund: Absolute Lautheit ist masteringabhängig, und frühe Target-Grenzen schließen spätere Drops/Refrains systematisch aus.
- **Entscheidung (2026-07-21):** Rendering-Protokoll 2 definiert Source-Cut = Ende Drop A/Start Auslauf und Target-Cut = Ende Vorlauf/Start Drop B. Fade-Renderer mischen nur Source-Postroll mit Target-Preroll. Grund: Die High-Power-Abschnitte sollen nicht miteinander überblendet werden; der Übergang liegt explizit zwischen ihnen.
- **Entscheidung (2026-07-21):** `feature_baseline_v3` durchsucht beide Tracks vollständig und bewertet zusätzlich Energieabfall nach A, niedrige Energie in beiden Bridge-Fenstern und Energieanstieg vor B. Grund: Ein korrekter Renderer allein garantiert noch keine musikalisch passenden Drop-Grenzen.
- **Entscheidung (2026-07-21):** Menschliche Bewertungen liegen mutierbar in `ratings.json` getrennt vom Batch-Manifest und beziehen sich auf Kandidat plus Renderer. Grund: Das Manifest dokumentiert den unveränderlichen Experimentlauf, während Hörurteile iterativ ergänzt werden und Renderer den Höreindruck verändern können.
- **Entscheidung (2026-07-23):** `rendered_transition_baseline_v1` bewertet nach dem Rendering das tatsächliche Audio mit Energieform, Grenzglätte, harmonischer Kontinuität und rhythmischer Stabilität. Die Cutpoint-Metrik bleibt als günstiger Vorfilter bestehen. Grund: Renderer- und Time-Stretch-Effekte sind erst im erzeugten Signal sichtbar; beide Stufen müssen für spätere Embedding-/ML-Vergleiche getrennt und auditierbar bleiben.
- **Entscheidung (2026-07-23):** Nachträgliche Metriken für historische Batches werden als versionierte `transition_metrics.json`-Sidecars gespeichert und verändern weder WAVs noch ursprüngliche Batch-Manifeste. Grund: Der Experimentlauf bleibt unveränderlich, während neue Auswertungen mit eigener Provenienz additiv ergänzt werden können.
- **Entscheidung (2026-07-29):** Wissenschaftlicher Kern ist das selbstüberwachte Lernen von Mixing-Kurven ohne Ground-Truth-Kontrollkurven. Ein differenzierbarer Renderer und eine eingefrorene Übergangsmetrik liefern den Trainingspfad; das bisherige Compatibility-Ranking bleibt Baseline und Kandidatenvorfilter. Grund: Die Arbeit soll nicht nur Übergangspunkte bewerten, sondern aus beat-synchronen Merkmalen tatsächlich nutzbare Mixing-Entscheidungen lernen.
- **Entscheidung (2026-07-29):** `differentiable_control_v1` startet mit vier Takten im 4/4-Metrum, 32 Kontrollpunkten sowie `mix_position` und `low_end_position`. A-/B-Gains werden als komplementäre Equal-Power-Paare abgeleitet und nicht unabhängig vorhergesagt. Grund: Die kleine, beschränkte Parametrisierung macht die Lernbarkeit messbar und verhindert triviale Lautheitslösungen.
- **Entscheidung (2026-07-29):** Vor einem Feature→Control-Modell müssen frei parametrisierte Kurven den differenzierbaren Proxy-Loss direkt verbessern. Erst danach folgen Featurevertrag, MLP-Baseline und TCN/BiLSTM. Grund: Wenn Renderer oder Objective kein brauchbares Lernsignal liefern, kann eine komplexere Modellarchitektur dieses Problem nicht beheben.
- **Entscheidung (2026-07-29):** `musik\14 - STRUGGLING.flac` wird per Pfad und SHA-256 in `config/track_exclusions.json` für neue Multi-Batches, Control-Vergleiche und Training ausgeschlossen. Grund: Der Nutzer bewertet den Track als Tempo-Ausreißer für das übrige Vergleichsset; historische Artefakte bleiben zur Reproduzierbarkeit unverändert.
- **Entscheidung (2026-07-29):** Vor Feature-Pipeline und MLP wird `differentiable_control_v2` an acht geblendeten A/B-Paaren bewertet. Ein gerichtetes Paar darf nur einmal, ein Track höchstens zweimal vorkommen; `answer_key.json` bleibt bis 8/8 Ratings geschlossen. Grund: Die ersten offenen Vergleiche zeigten einen echten Erwartungseffekt und einen Track-Ausreißer; die Zielmetrik braucht deshalb breitere, methodenblinde Hörvalidierung.
- **Entscheidung (2026-07-30):** Rendering-Protokoll 5 ersetzt den vereinfachten Librosa-Phase-Vocoder durch Rubber Band. BeatBridge nutzt zuerst FFmpeg mit einkompiliertem `rubberband`-Filter und gemeinsam verarbeitetem Stereo; bei Fehlern folgt das eigenständige `rubberband`-CLI mit R3-Engine. Float32-WAVs bilden die externe Backend-Grenze, und `tempo_backend` wird pro Render dokumentiert. Grund: Die zuvor gehörten verwaschenen Transienten waren keine niedrige Export-Bitrate, sondern eine bekannte Grenze des Librosa-Verfahrens; Backend-Wahl und Quantisierung müssen für Vergleichsexperimente nachvollziehbar sein.
- **Entscheidung (2026-07-30):** Control-Protokoll 3 beschränkt rohe Inkrement-Logits vor dem Softmax symmetrisch durch `0.6 · tanh`; bei 32 Punkten kann ein einzelner Halbbeat-Schritt dadurch höchstens 0,0996431 der gesamten Übergabe übernehmen. Das Objective misst zusätzlich normalisierte Inkrementabweichung und Krümmung. Grund: v2 war zwar monoton, konnte die Mischung aber weiterhin innerhalb weniger Kontrollpunkte abrupt umschalten.
- **Entscheidung (2026-07-30):** Feature-Protokoll 1 definiert pro Track `float32 (32, 54)` auf einem Halbbeat-Raster und 16 globale Features. Der Extractor untersucht je Cue vier Takte davor und danach, gibt aber nur die vier Bridge-Takte an das Modell. Sechs Vocal-Kanäle unterscheiden Aktivität, Prominenz, Onset, Offset, Phrasenfortschritt und Confidence; `audio_valid`, `phrase_valid` und `vocal_valid` verhindern stille Ersatzannahmen. Grund: Die Hörtests zeigten methodenunabhängige unterbrochene Lyrics, Vocal-Clashes und eine nicht erfasste 8-Takt-Phrase; ein bloßer Vocal-Anteil oder ein fest angenommenes `feature_dimension = 64` bildet diese Fehler nicht eindeutig ab.
- **Entscheidung (2026-07-30):** Zeitaufwendige Audiofeatures werden als immutable Volltrack-Artefakte nach Audio-SHA, Beat-Grid-Hash, Feature-/Extractor-/Rendering-Version, Sample-Rate und ausgerichteter BPM gecacht. Cue-spezifische 32-Schritt-Fenster sind nur Slices dieses Caches. Spektralfluss und Onset Strength bleiben roh gespeichert und werden erst mit eingefrorenen Trainingssplit-Perzentilen normalisiert. Grund: Derselbe Song kommt in vielen gerichteten Paaren und Cue-Kombinationen vor; erneute FFT-/Chroma-/Tonnetz-Berechnung wäre unnötig, während bereits normalisierte Cachewerte Datenlecks oder teure Neuberechnung bei neuen Splits erzwingen würden.
- **Entscheidung (2026-07-30):** Vortrainierte Modelle dürfen für Featuregruppen eingesetzt werden, wenn wissenschaftliche Referenz, Software-/Modellversion, konkrete Gewichtsrevision und Gewichts-Hash dokumentiert werden. Vocal-Separation verwendet zunächst `htdemucs` aus Demucs 4.1.0; der Stem wird einmal pro Audio-SHA und Modell gecacht und anschließend für Cue Points sowie Zieltempi wiederverwendet. Grund: Vocal-Aktivität selbst neu zu trainieren ist nicht der wissenschaftliche Kern der Arbeit, die abgeleiteten Merkmale müssen aber zitierbar und exakt reproduzierbar bleiben.
- **Entscheidung (2026-07-30):** `All-In-One` wird trotz zitierfähigem Strukturmodell noch nicht als Phrasenbackend aktiviert. Grund: Der offizielle Windows-Pfad erfordert einen NATTEN-Build außerhalb der aktuell dokumentierten Python-3.14-Unterstützung; außerdem entsprechen funktionale Verse-/Chorus-Grenzen nicht automatisch den benötigten 8-Takt-Phrasengrenzen. Bis zur getrennten Validierung bleibt `phrase_valid = 0`.
- **Entscheidung (2026-07-31):** Feature-Datasets werden ausschließlich auf Ebene des Audio-SHA in Train, Validation und Test geteilt. Nur Paare innerhalb desselben Splits werden exportiert; kreuzende Paare werden gezählt und verworfen. Flux-/Onset-Normalisierung wird nur aus tatsächlich verwendeten Trainingsartefakten gefittet. Grund: Kandidaten-, Rollen- oder Paar-Splits würden denselben Song und dessen Volltrackstatistiken in mehrere Splits leaken und die Generalisierung auf unbekannte Musik vortäuschen.
- **Entscheidung (2026-07-31):** Der erste Datasetexport wählt pro historischem Songpaar die drei bestgerankten Kandidaten mit exakt vier Takten. Bereits gerenderte Top-3-Dateien sind nicht maßgeblich, weil sie häufig zwei Takte lang sind. Grund: Feature- und Control-Protokoll 1 haben eine feste Geometrie von vier Takten beziehungsweise 32 Halbbeats.
- **Beobachtung (2026-07-30):** Die erste reale Cache-Sonde für `04 - GHOST.flac` erzeugte 990 vollständige Halbbeat-Bins mit 54 Kanälen unter `output/feature_cache/feature_protocol_v1/8ccc02a43fffe602/ef5ba67c7f95414bb49c/`. Ein unmittelbar wiederholter Aufruf verwendete denselben Eintrag mit `cache_hit = true`; Vocal und Phrase sind im Manifest ehrlich als `not_implemented` ausgewiesen.
- **Beobachtung (2026-07-30):** Die erste reale HT-Demucs-Sonde für `04 - GHOST.flac` verwendete Modellrevision `bf35a81b663819a8255c8fefee17f9d812b786b5` und Gewichts-SHA-256 `d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd`. Der daraus erzeugte neue Featurecache enthält erneut 990 Halbbeat-Bins; `vocal_valid = 1` und der Aktivitätsscore deckt mit rund `1,87e-7` bis `0,9971` sowohl inaktive als auch stark aktive Bereiche ab. Ein zweiter Lauf war ein vollständiger Cachetreffer.
- **Beobachtung (2026-07-31):** Der reale Datasetexport aus 60 Paarmanifesten wählte 165 Vier-Takt-Beispiele, entfernte neun `STRUGGLING`-Beispiele und verwarf 93 Cross-Split-Paare. Übrig bleiben 45/9/9 Beispiele mit Shapes `(N,32,54)` je Track und `(N,16)` global. Alle Werte und Vocal-Masken sind gültig; kein Trackhash und keine Example-ID überschneidet Splits.
- **Gelernt (2026-07-31, 1. Voll-Exportversuch):** Der eingeschränkte Codex-Prozess durfte das installierte FFmpeg beim ersten tempoangepassten Target nicht starten (`WinError 5`) → Datasetordner blieb dank atomarem Verzeichnisexport unsichtbar und bereits erzeugte Stems blieben wiederverwendbar → reale Datasetläufe mit Rubber-Band-Varianten benötigen dieselbe externe Prozessfreigabe wie Renderläufe; kein Ersatz durch ein anderes Time-Stretch-Verfahren.
- **Beobachtung (2026-07-30):** Der neue geblendete Satz `blind_v4_control_v3_rubberband_top8_4bar_20260730` rendert dieselben acht Paare wie der bewertete v2-Satz vollständig neu. 16/16 Float32-WAVs sind technisch gültig; Paar 5 `FALLING → Aversion` und Paar 7 `FALLING → HELP_LESS` verwenden tatsächlich `ffmpeg_librubberband`, die sechs BPM-identischen Paare benötigen keinen Time-Stretch. Damit lassen sich bekannte Höreindrücke kontrolliert vergleichen, aber wegen der aus denselben Urteilen abgeleiteten v3-Änderung nicht als unabhängiger finaler Testsatz interpretieren.
- **Beobachtung (2026-07-30):** Im vollständig bewerteten Control-v3-/Rubber-Band-Hörsatz waren bei allen acht Paaren keine Unterschiede zwischen Equal Power und proxy-optimierter Kurve erkennbar: acht Gleichstände, identischer Gesamtmittelwert 4,45. Auch alle Kriterienmittel sind identisch (Sauberkeit 4,25; Energieform 4,50; Low-End 4,625; Rhythmik 4,50; Artefaktfreiheit 4,375). Das Proxy-Objective sank je Paar dennoch um 2,39–36,43 %. Niedrigerer Proxy-Loss ist damit erneut kein Beleg für einen wahrnehmbaren Gewinn.
- **Beobachtung (2026-07-30, Paar 5):** `FALLING → Aversion` passt Song B von 161,499 auf 156,605 BPM an (`tempo_factor = 0,969697`, rund 3,03 % langsamer beziehungsweise 3,125 % länger) und dokumentiert `ffmpeg_librubberband`. Song B klang laut Nutzer in beiden A/B-Varianten schlecht. Da beide Varianten exakt dieselbe tempoangepasste Target-Waveform erhalten, ist dies kein Unterschied des Control-Objectives; Time-Stretch, Track-Kompatibilität und gewähltes Target-Fenster müssen separat gegeneinander isoliert werden.
- **Gelernt (2026-07-30, Time-Stretch-Diagnose):** Die geprüften Batch-WAVs waren unkomprimiertes 44,1-kHz-Stereo-PCM16 mit 1.411,2 kbit/s und damit nicht niedrigbitratig. Der bisherige `librosa.effects.time_stretch`-Pfad verwendete einen vereinfachten Phase-Vocoder ohne Transientenbehandlung; eine synthetische Click-Sonde zeigte deutliches zeitliches Verschmieren. Daraus folgt: keine Qualitätskorrektur über höhere Export-Bitrate vortäuschen, sondern einen transientenschonenden Rubber-Band-Pfad verwenden und anschließend auf realen Paaren blind gegen historische Renderings prüfen.
- **Gelernt (2026-07-29, 1. reale Hörprobe):** Alle vier optimierten v1-Vergleiche klangen schlechter als die Equal-Power-Baseline; Song A wurde kurz vor dem Ende erneut lauter. Die gespeicherten Kurven bestätigten 4–12 rückwärts laufende `mix_position`-Schritte pro Paar, bei `GHOST → REBIRTH` bis zu −0,468 in einem Schritt → eine weiche Monotoniestrafe ist für musikalische Übergabe-Invarianten ungeeignet → Control-Protokoll 2 parametrisiert ausschließlich positive, auf Summe 1 normierte Inkremente und garantiert monotone Kurven konstruktiv.
- **Gelernt (2026-07-30, blinder v3-Hörsatz):** Die konstruktive Monotonie beseitigte den eindeutigen v1-Fehler, machte die Proxy-Optimierung aber noch nicht konsistent besser als Equal Power. Auffällige Restfehler betreffen abrupte Melodie-/Gain-Übergaben, gehaltene oder abgeschnittene Vocals, Time-Stretch-Artefakte und eine 8/4-Phrasengrenze, die das 4/4-Raster nicht abbildet. Daraus folgt: Equal Power bleibt die starke Baseline; Control-/Objective-v3 muss lokale Kurvensprünge begrenzen und Phrasen-/Vocal-Kontext sowie robuste Artefaktkontrolle adressieren. Das Feature→Control-Training wartet, bis frei optimierte Kurven diesen Hör-Gate auf neuen Paaren bestehen.
- **Gelernt (2026-07-30, Control-v3-Hörsatz):** Die v3-Schranken machen optimierte Kurven hörend nicht schlechter, aber auch nicht unterscheidbar besser als Equal Power. Gleichzeitig treten gemeinsame Fehler in beiden Varianten auf: unterbrochene Lyrics, zurückkehrende Source-Melodie, Vocal-Clash und ein schlecht klingendes tempoangepasstes Target. Der nächste Engpass liegt daher vor beziehungsweise neben der Control-Optimierung: musikalische Fensterwahl, Phrasen-/Vocal-Kontext und isolierte Time-Stretch-Qualität. Ein Feature→Control-Netz wird weiterhin nicht trainiert, solange die direkt optimierte Zielgröße keinen hörbaren Vorteil zeigt.
- **Entscheidung (2026-07-17):** Die Root-`README.md` bleibt eine kompakte Projekt- und Bedienungsübersicht; der veränderliche Arbeitsplan wird ausschließlich in `docs/STATUS.md` gepflegt. Grund: Doppelte Aktionspläne waren bereits auseinander gelaufen und enthielten erledigte Renderer weiterhin als offene Arbeit.
- **Historischer Stand (2026-07-17, 1. Versuch; durch die Analyse-/Provenienzänderung vom 2026-08-12 überholt):** Fehlende Downbeat-Metadaten führten zuvor zu stillem Fallback auf beliebige Beats → Downbeat-Snapping brach mit einer konkreten Fehlermeldung ab → kein vorgetäuschtes Bar-Alignment. Heute bleibt der Analyse-Fallback verfügbar, wird aber als approximativ markiert und von der Kandidatengenerierung standardmäßig abgelehnt.
- **Gelernt (2026-07-17, 1. Versuch):** Eine Prüfung innerhalb der Codex-Dateisandbox meldete `ffmpeg` als nicht auffindbar, obwohl dessen WinGet-Verzeichnis im `PATH` stand → die Sandbox verweigerte Zugriff und Ausführung im Paketverzeichnis → externe Programme bei einem solchen Widerspruch durch einen tatsächlichen Prozessstart außerhalb der eingeschränkten Sandbox verifizieren. `ffmpeg 8.1` ist installiert und ausführbar.
**Entscheidung (2026-08-12):** RoFormer wird als Standard für Vocal-Stems
verwendet. `audio-separator` wurde zunächst geprüft, ist unter Python 3.14
unter Windows aber an `diffq-fixed`/zusätzlichen ONNX-Abhängigkeiten nicht
reproduzierbar installierbar. Deshalb nutzt BeatBridge das schlanke,
inference-only `bs-roformer-infer==0.1.1` mit verifizierten Modell-Downloads.
Demucs bleibt als explizites Vergleichsbackend erhalten; bestehende Demucs-
Caches werden nicht migriert oder überschrieben.

## Verifiziert am 2026-08-20 (W&B-Integration, gezielter Testlauf)

- **Fragestellung und Reasoning:** Die neue optionale W&B-Schicht muss beide
  Trainingsrunner erreichen, ohne lokale Resume-/Checkpoint-Verträge zu
  verändern oder Tests von Netzwerk/Login abhängig zu machen. Deshalb wurden
  Offline-/Online-/Disabled-Modi, epochweise Metriken, Artefakte und die
  Pfad-Redaktion separat geprüft.
- **Eingaben/Setup:** Repository-Stand vom 2026-08-20; synthetische CPU-
  Beispiele der bestehenden MLP- und Vocal-Runner-Tests; W&B-SDK im
  gezielten Testlauf durch ein Fake-Modul ersetzt. Die echte Abhängigkeit ist
  in `requirements.txt` als `wandb==0.28.1` ergänzt.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_wandb_logging.py tests/test_ml_training_runner.py tests/test_vocal_ml_training_runner.py`
- **Ergebnis:** 11 Tests bestanden. Zwei erwartete PyTorch-CUDA-
  Determinismuswarnungen; keine Fehler oder Blockaden. Geprüft wurden
  Disabled-No-op, Offline-Initialisierung, Train-/Validation-Metriken,
  Summary, Ergebnis-Artifact, Resume-Kompatibilität beider Runner und die
  Entfernung lokaler Dataset-Pfade aus der W&B-Konfiguration.
- **Schlussfolgerung und nächster Schritt:** Die Integration ist funktional
  eingebunden. Als nächster Schritt folgen Abhängigkeitsinstallation bzw.
  Importprüfung mit `wandb==0.28.1`, CLI-Help-/Disabled-Sonde und danach der
  vollständige Testlauf.

## Verifiziert am 2026-08-20 (W&B-SDK und CLI-Sonde)

- **Fragestellung und Reasoning:** Die Fake-SDK-Tests prüfen die interne
  Adapterlogik, aber nicht den echten W&B-Prozess. Deshalb wurde die
  festgelegte SDK-Version installiert und ein echter Offline-Run mit einer
  Epoche, CLI-Hilfe und Dependency-Prüfung ausgeführt. Online-Login und
  Cloud-Synchronisation waren für diese Verifikation nicht erforderlich.
- **Eingaben/Setup:** `.venv` mit Python 3.14; `wandb==0.28.1` aus PyPI;
  synthetische Metriken und temporäres Output-Verzeichnis; W&B-Modus
  `offline`.
- **Testumfang bzw. Befehl:** Offline-Logging-Sonde über
  `.venv\Scripts\python.exe -c "... WandbLogger.start(...); log_epoch(...); finish(...) ..."`,
  anschließend `.venv\Scripts\python.exe -m src.ml train --help | rg --
  '--wandb-(mode|project|log-checkpoints)'` und
  `.venv\Scripts\python.exe -m pip check`.
- **Ergebnis:** Echter W&B-Offline-Run erfolgreich; Metriken wurden in einem
  lokalen Offline-Run gespeichert und der SDK-Sync-Hinweis wurde ausgegeben.
  Die drei W&B-CLI-Optionen sind sichtbar. `pip check` meldet keine defekten
  Abhängigkeiten. W&B meldete lediglich eine Windows-Berechtigungswarnung
  für den globalen lokalen Logpfad; der Run selbst blieb erfolgreich.
- **Schlussfolgerung und nächster Schritt:** Die echte SDK-Anbindung und der
  CLI-Steuerpfad funktionieren. Danach folgt die vollständige pytest-Suite
  sowie ein abschließender Diff-/Status-Check.

## Verifiziert am 2026-08-20 (W&B-Integration, Vollsuite-Versuch)

- **Fragestellung und Reasoning:** Nach den gezielten Runner-Tests sollte
  geprüft werden, ob die additive W&B-Änderung die übrige Regression-Suite
  beeinflusst. Der Gesamtstatus ist nur belastbar, wenn ein regulärer
  pytest-Exit abgewartet oder eine bekannte Blockade mit Prozesszustand
  belegt wird.
- **Eingaben/Setup:** Repository-Stand vom 2026-08-20; `.venv` mit
  installiertem `wandb==0.28.1`; Standard-Testumgebung ohne W&B-Online-Login.
- **Testumfang bzw. Befehl:** `.venv\Scripts\python.exe -m pytest -q`.
- **Ergebnis:** Nach mehr als sieben Minuten blieb der Prozess im bekannten
  langsamen Audio-/JIT-Bereich aktiv (Python-Prozess reagierte und verbrauchte
  CPU), ohne weiteren pytest-Fortschritt oder Fehlerausgabe. Der Lauf wurde
  deshalb kontrolliert mit `Ctrl+C` beendet und endete mit Exit-Code 1; es
  liegt kein W&B-bezogener Fehler vor. Der bekannte Suite-Engpass bleibt
  separat offen.
- **Schlussfolgerung und nächster Schritt:** Für diese Änderung sind die
  gezielten ML-/W&B-Tests und die echte Offline-SDK-Sonde maßgeblich grün.
  Vor dem Abschluss folgen `git diff --check`, Syntax-/Importprüfung sowie
  eine Wiederholung der gezielten W&B-Tests nach dem letzten Patch.

## Verifiziert am 2026-08-20 (W&B-Integration, Abschlusschecks)

- **Fragestellung und Reasoning:** Nach dem letzten Offline-SDK-Patch sollten
  die W&B-Adaptertests sowie Import, CLI-Argumente und Whitespace des Diffs
  nochmals geprüft werden.
- **Eingaben/Setup:** `.venv` mit `wandb==0.28.1`; W&B im Disabled-Modus für
  den Testlauf; bytecodefreier Import für die abschließende Python-Sonde.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_wandb_logging.py`
  sowie zunächst `... -m compileall -q src\ml tests\test_wandb_logging.py`;
  danach bytecodefreier Import-/CLI-Aufruf mit
  `PYTHONDONTWRITEBYTECODE=1` und `git diff --check`.
- **Ergebnis:** 3 Tests bestanden. `compileall` konnte wegen gesperrter
  temporärer `.pyc`-Dateien in den vorhandenen Cache-Verzeichnissen keine
  neuen Dateien schreiben und meldete `PermissionError`; die bytecodefreie
  Import-/CLI-Sonde war erfolgreich. `git diff --check` meldete keine
  Whitespace-Fehler; Git zeigte nur erwartete LF/CRLF-Warnungen.
- **Schlussfolgerung und nächster Schritt:** W&B-Adapter, Runner-Imports und
  CLI-Argumente sind abschließend geprüft. Es bleibt nur die optionale
  Online-Anmeldung/Synchronisation des Nutzers; ein Commit wurde nicht erstellt.

## Verifiziert am 2026-08-20 (W&B-Pfadredaktion, final)

- **Fragestellung und Reasoning:** Die abschließende W&B-Konfigurationsprüfung
  musste auch verschachtelte Dataset-/Cache-Pfade aus der Cloud-Konfiguration
  entfernen, nicht nur den obersten Dataset-Pfad.
- **Eingaben/Setup:** Aktualisierte `_public_contract()`-Implementierung und
  synthetischer verschachtelter Dataset-Contract; W&B-SDK `0.28.1`.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_wandb_logging.py`,
  bytecodefreie Import-/Redaktionssonde und `git diff --check`.
- **Ergebnis:** 3 Tests bestanden; verschachtelte Pfade werden entfernt,
  Import und CLI-nahe Konfiguration funktionieren. Keine Diff-Whitespace-
  Fehler; nur erwartete LF/CRLF-Warnungen von Git.
- **Schlussfolgerung und nächster Schritt:** Die W&B-Implementierung ist
  fertig verifiziert und kann vom Nutzer mit `--wandb-mode online` oder
  `offline` verwendet werden. Ein Commit wurde nicht erstellt.

## Verifiziert am 2026-08-19 (ML-Modellübersicht)

- **Fragestellung und Reasoning:** Die aktuelle Form der ML-Modelle sollte so
  visualisiert werden, dass Default, Baseline und experimenteller
  Hauptmodellpfad nicht verwechselt werden. Dafür wurden Projektstatus,
  Modellverträge, `src/ml/model.py` und die realen Trainingsmanifeste gemeinsam
  abgeglichen.
- **Eingaben/Setup:** Repository-Stand vom 2026-08-19; gelesen wurden
  `docs/STATUS.md`, `docs/Projekt-Gesamtuebersicht.md`, `.agents/AGENT.md`,
  `.agents/multi-session-project-discipline.skill`,
  `docs/ML_CONTROL_MODEL_PROTOCOL.md`,
  `docs/VOCAL_CONTROL_MODEL_PROTOCOL.md`,
  `docs/TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md`, `src/ml/model.py` sowie die
  Manifeste unter `output/training_runs/`.
- **Testumfang bzw. Befehl:** Read-only-Abgleich mit `rg`, PowerShell-
  Dateiausgaben und `.venv\Scripts\python.exe` zum Parsen der JSON-Manifeste;
  anschließend strukturelle Markdown-/Mermaid-Dokumentation in
  `docs/ML_MODEL_CURRENT_STATE.md` sowie Verweise in `STATUS.md`.
- **Ergebnis:** Die Übersicht weist `vocal_time_shared_mlp_v2` mit
  20.821 Parametern und aktuellem RoFormer-Run als Default aus. Sie hält
  `time_shared_mlp_v1` mit 10.394 Parametern als Baseline und
  `tcn_bilstm_transition_control_v1` mit 1.013.226 Parametern als
  implementiert/trainiert, aber experimentell fest. Die reale TCN- und
  Vocal-Run-Provenienz (Dataset, Splits, Device, Early Stopping und bester
  Validation-Loss) wurde aus den Manifesten übernommen. Keine Fehler oder
  Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die aktuelle Modellform ist
  dokumentiert und verlinkt. Inhaltlich bleibt der geblendete Hörvergleich
  des gelernten Vocal-v2-Checkpoints gegen die Initialisierung das nächste
  Gate; der dokumentierte Stand meldet weiterhin `0/5` Ratings.
- **Nachprüfung:** Befehl
 `.venv\Scripts\python.exe -c "from src.ml.model import FeatureControlMLP, VocalFeatureControlMLP, TCNBiLSTMTransitionControl; assert ...; parse training_runs manifests and docs/ML_MODEL_CURRENT_STATE.md"` sowie `git diff --check` bestätigten die neue Datei, die Mermaid-Codeumgebung, die Verweise in `STATUS.md` und die Modell-/Run-Kennungen ohne Fehler. Ergebnis: Parameterzahlen `10394/20821/1013226` und drei Manifeste stimmen.

## Verifiziert am 2026-08-20 (Plan variable Übergangslängen)

- **Fragestellung und Reasoning:** Für den Implementierungsplan zu extern
  vorgegebenen Übergangslängen musste geprüft werden, ob alle geforderten
  Geometrien, additiven Verträge, Split-/Testsplit-Regeln, Kandidatenrisiken,
  Modell-/Vocalpfade, Lossnormalisierung und die gefundenen festen
  32-Schritt-Annahmen vollständig abgedeckt sind. Die Codeanalyse sollte
  insbesondere die gemeinsame Boundary-Auswahl und die bestehende
  Vier-Takt-Split-Autorität absichern.
- **Eingaben/Setup:** Read-only Repositoryanalyse im Stand vom 2026-08-20;
  Pflichtlektüre von `AGENTS.md`, `docs/STATUS.md`,
  `docs/Projekt-Gesamtuebersicht.md`, `.agents/AGENT.md`,
  `.agents/multi-session-project-discipline.skill` und den relevanten
  Candidate-, Feature-, Dataset-, ML-, TCN/BiLSTM-, Rendering-, Batch-,
  Vocal-, W&B- und Control-Study-Protokollen. Bestehende Nutzeränderungen
  blieben erhalten; Audio-, Dataset-, Cache- und Run-Artefakte wurden nicht
  geschrieben.
- **Testumfang bzw. Befehl:** Read-only `git status`, gezielte `rg`-Analyse
  der festen `32`-/`SEQUENCE_LENGTH`-Stellen und der Candidate-/Split-
  Verträge; danach
  `git diff --check` sowie
  `.venv\Scripts\python.exe -X utf8 -c "... prüft Existenz, Pflichtbegriffe,
  Geometrieeinträge und fehlende Planabschnitte ..."` für
  `docs/VARIABLE_LENGTH_TRANSITIONS_PLAN.md`.
- **Ergebnis:** Der Plan wurde als neue Datei mit 380 Zeilen und 34.454
  Bytes angelegt. Die strukturelle Python-Prüfung meldete
  `exists=True`, keine fehlenden Pflichtinhalte und Exit-Code 0. `git
  diff --check` meldete keine Whitespace-Fehler; Git zeigte nur die bereits
  erwarteten LF/CRLF-Hinweise. Es wurde kein `pytest`-, Trainings-, Render-
  oder Dataset-Exportlauf ausgeführt, weil ausdrücklich noch kein
  Produktivcode implementiert werden sollte.
- **Schlussfolgerung und nächster Schritt:** Der Plan ist vollständig als
  additive Migrationsgrundlage abgelegt und hält Feature Protocol 1 sowie
  bestehende Vier-Takt-Modelle getrennt. Der nächste sinnvolle Schritt ist
  die Umsetzung des zentralen Längenvertrags und der per-L-
  Kandidatenvalidierung mit neuen Tests; dabei bleibt der Testsplit aus
 Training und Modellentwicklung ausgeschlossen. Kein Commit wurde erstellt.

## Verifiziert am 2026-08-20 (Plan-Endkontrolle nach Rankingergänzung)

- **Fragestellung und Reasoning:** Nach der ergänzten Einordnung von
  Ranking-, Render-Metrik- und Ratings-Verträgen musste die finale
  Planstruktur erneut auf Pflichtinhalte und Diff-Whitespace geprüft
  werden.
- **Eingaben/Setup:** Neue Planfassung mit 386 Zeilen und 35.656 Bytes;
  `.venv`-Python für die statische Inhaltsprüfung; keine Audio-, Dataset-,
  Cache-, Run- oder Testsplit-Dateien geladen oder verändert.
- **Testumfang bzw. Befehl:** Zunächst eine strukturelle Python-Sonde mit
  zu wörtlichen Suchbegriffen; sie meldete fälschlich fehlende Begriffe
  (`gemeinsame Boundary-Auswahl`, `längenspezifische Validierung`,
  `längengehomogene`, danach noch `per Länge`). Die Sonde wurde auf die
  tatsächlich verwendeten fachlich gleichwertigen Begriffe korrigiert und
  erneut mit `.venv\Scripts\python.exe -X utf8 -c "... Pflichtinhalte,
  Geometrie und Ranking-/Metrikabschnitte ..."` ausgeführt. Zusätzlich
  lief erneut `git diff --check`.
- **Ergebnis:** Die korrigierte Sonde meldete
  `lines=386`, `bytes=35656`, `missing=[]` und Exit-Code 0. `git
  diff --check` meldete keine Whitespace-Fehler; nur die erwarteten
  LF/CRLF-Hinweise erschienen. Die zwei vorherigen Sondenfehler waren
  reine Prüfscript-Falschnegativen und keine Planlücken. Kein pytest-,
  Trainings-, Render- oder Dataset-Exportlauf wurde ausgeführt.
- **Schlussfolgerung und nächster Schritt:** Der Plan ist final geprüft.
  Als nächstes kann die Umsetzung mit dem zentralen Längenvertrag und der
  per-L-Kandidatenvalidierung beginnen; bestehende Vier-Takt-Verträge und
  der Testsplit-Isolationsgrundsatz bleiben unverändert. Kein Commit wurde
  erstellt.

## Verifiziert am 2026-08-20 (unabhängiges Architektur-Review Variable Length)

- **Fragestellung und Reasoning:** `docs/VARIABLE_LENGTH_TRANSITIONS_PLAN.md`
  wurde unabhängig gegen Candidate-, Feature-, Dataset-, Bridge-, Vocal-,
  Control-, ML-Training-, Runner-, Checkpoint- und Testsplit-Code geprüft.
  Ziel war, tatsächliche v1-Annahmen von geplanten v2-Verträgen zu trennen und
  insbesondere Mehrlängen-Boundaries, Featurefenster, Cacheidentitäten,
  zeitnormalisierte Losses sowie additive Resume-/Split-Verträge nicht nur
  konzeptionell, sondern mit konkreten Dateigrenzen zu beschreiben.
- **Eingaben/Setup:** Repository `D:\Documents\00Uni\00master\BeatBridge`,
  Stand 2026-08-20; Pflichtdokumente und relevante Protokolle vollständig
  gelesen; vorhandene Nutzeränderungen, Audio-, Dataset-, Cache- und Run-
  Artefakte blieben erhalten. Es wurde kein Produktivcode implementiert.
- **Testumfang bzw. Befehl:** Read-only `git status`, gezielte Code-/Test-
  Analyse mit `rg` und PowerShell; danach
  `.venv\Scripts\python.exe -X utf8 -c "... strukturelle Planpflichten,
  Abschnittsnummern und Split-Map-Hash ..."` sowie `git diff --check`.
- **Ergebnis:** Der korrigierte Plan umfasst 787 Zeilen. Die abschließende
  strukturelle Sonde meldete `missing=[]`, eindeutige Abschnitte für Invarianten, Risiken,
  Arbeitspakete und das Analyseinventar sowie `mapping_count=111` und den
  reproduzierten kanonischen Hash
  `5548a9bf74f20f9022c02b48571bbb8b8e2e9b4cc58d68f2a81131f2d2b12e8b`.
  `git diff --check` meldete keine Whitespace-Fehler; Git gab nur die bereits
  bekannten LF/CRLF-Konvertierungswarnungen aus.
- **Nachkontrolle:** Eine erneute bytefreie Planstruktur-Sonde
  (`final_plan_lines=787`), `git diff --check` und `git status --short --branch`
  bestätigten die unveränderte Planstruktur, den fehlerfreien Whitespace-Status
  und die Erhaltung der vorher vorhandenen Nutzeränderungen.
- **Fehler/Blockaden:** Die erste erweiterte Struktursonde meldete wegen zwei
  absichtlicher Markdown-Zeilenumbruch-Leerzeichen in den Kopfzeilen zunächst
  `trailing_whitespace=[3,4]`. Die Kopfzeilen wurden ohne Bedeutungsänderung
  bereinigt; die Wiederholung war mit `trailing_whitespace=[]` erfolgreich.
  Kein pytest-, Trainings-, Render- oder Dataset-Exportlauf wurde gestartet,
  weil die Aufgabe ausdrücklich auf ein Architektur-Review ohne
  Produktivimplementierung begrenzt war. Es gab keine fachliche Blockade und
  keinen Artefakt-Schreibzugriff.
- **Schlussfolgerung und nächster Schritt:** Der Plan beschreibt jetzt die
  verifizierten Invarianten, latenten Risiken, tatsächlichen v1-Abweichungen,
  exakten neuen Dateigrenzen und die Abnahmekriterien je Implementierungsschritt.
  Als nächster Schritt kann WP1 (zentraler Längenvertrag) mit isolierten v2-
  Tests begonnen werden; die alten Vier-Takt-Verträge und der Testsplit bleiben
  dabei getrennt. Kein Commit wurde erstellt.

## Verifiziert am 2026-08-20 (variable Kandidaten- und Baseline-Rendering-Stufe)

- **Fragestellung und Reasoning:** Die additive v2-Stufe sollte die
  angeforderten Längen 2, 4, 6 und 8 Takte je Boundary unabhängig prüfen,
  gültige kürzere Kandidaten bei fehlender 8-Takt-Abdeckung erhalten und die
  tatsächliche Beatanzahl ohne `None` oder Misch-Meter in Candidate und
  Rendering weiterreichen. Zusätzlich mussten Fade und Equal-Power für 2, 6
  und 8 Takte taktgenau bleiben, während der v1-Pfad unverändert nutzbar
  bleibt.
- **Eingaben/Setup:** Repository `D:\Documents\00Uni\00master\BeatBridge`,
  ausschließlich synthetische WAV-Testsignale, `.venv\Scripts\python.exe`,
  keine ML-/Dataset-Formatänderung. Vor der Änderung wurden die Pflicht-
  dokumente und die relevanten Candidate-, Rendering-, Batch- und CLI-
  Protokolle vollständig gelesen. Vorhandene Nutzeränderungen sowie Audio-,
  Dataset-, Cache- und Run-Artefakte blieben erhalten.
- **Testumfang bzw. Befehl:**
  - `.venv\Scripts\python.exe -m pytest -q tests\test_candidates.py -k variable`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_rendering.py -k variable`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_batch_render.py -k variable`
  - `.venv\Scripts\python.exe -m pytest -vv -s tests\test_rendering.py -k "variable_fade_renderers_are_exactly_taktgenau and fade and 2"`
  - `.venv\Scripts\python.exe -c "... variable candidate/render/CLI imports ..."`
  - `.venv\Scripts\python.exe -m src.batch_render --help | Select-String ...`
  - abschließend `git diff --check`.
- **Ergebnis:** Kandidatentests `3 passed, 11 deselected`; Renderingtests
  `6 passed, 13 deselected`; CLI-Test `1 passed, 3 deselected`; der gezielte
  Fade/Equal-Power-Lauf für die 2-Takt-Fälle `2 passed, 17 deselected`.
  Die Importsonde nach Korrektur meldete `variable candidate/render/CLI
  imports OK`; die CLI-Hilfe enthält `--transition-bars`. `git diff --check`
  meldete keine Whitespace-Fehler, nur die bekannten LF/CRLF-Hinweise.
- **Fehler/Blockaden:** Ein erster gemeinsamer Lauf von
  `tests\test_candidates.py tests\test_rendering.py tests\test_batch_render.py`
  überschritt 120 Sekunden nach acht erfolgreichen Tests; der vollständige
  Kandidatenlauf überschritt 60 Sekunden ebenfalls nach acht Tests. Ein
  initialer variabler Renderinglauf überschritt 120 Sekunden. Die isolierte
  Wiederholung mit dem synthetischen Testpfad lief vollständig erfolgreich;
  die verbleibende Blockade betrifft die bestehende Umgebung bei alten
  `librosa.load`-Pipelines, nicht die neue variable Testgruppe. Eine erste
  Importsonde verwendete versehentlich `generate_transition_candidates` aus
  dem falschen Paket und endete mit `ImportError`; die korrigierte Sonde war
  erfolgreich. Kein Test schrieb in bestehende Audio-, Dataset-, Cache- oder
  Run-Verzeichnisse.
- **Schlussfolgerung und nächster Schritt:** Die variable Kandidatenstufe und
  der additive Rendering-6-Pfad sind für die geprüften synthetischen 2/4/6/8-
  Taktfälle abgenommen; v1-Kandidaten und v1-Batchpfade bleiben separat. Die
  nächsten Schritte aus dem Plan sind Dataset-/Feature- und ML-Verträge; sie
  wurden in dieser Aufgabe ausdrücklich nicht implementiert. Kein Commit wurde
  erstellt.

## Verifiziert am 2026-08-20 (Feature Protocol 2 und Dataset Format 2)

- **Fragestellung und Reasoning:** Die additive Feature-/Dataset-Stufe sollte
  aus `transition_length_bars` deterministisch `T = 16/32/48/64` ableiten,
  Source-Postroll und Target-Preroll ohne Padding ausschneiden,
  `transition_position` mit dem tatsächlichen T normalisieren und die 54
  bestehenden Kanäle sowie den 16-dimensionalen Global-Pair-Vektor semantisch
  stabil halten. Der Export musste mehrere Längen gemeinsam, mit Top-k je
  Songpaar und Länge, einer einzigen Audio-SHA-Split-Zuordnung, Training-only-
  Normalisierung, expliziten L/Beats/T-Feldern, leeren Shards und
  reproduzierbaren Datei-Hashes verarbeiten.
- **Eingaben/Setup:** Repository `D:\Documents\00Uni\00master\BeatBridge`,
  venv-Interpreter `.venv\Scripts\python.exe`, ausschließlich synthetische
  Feature-/Artifact-Fixtures für die neuen Tests; kein großer realer Datensatz,
  kein ML-Training und kein Zugriff auf bestehende Audio-, Dataset-, Cache- oder
  Run-Artefakte. Pflichtdokumente und alle relevanten Feature-, Dataset-,
  Candidate-, Analyse-, Batch- und ML-Protokolle wurden vor den Änderungen
  vollständig gelesen; vorhandene Nutzeränderungen blieben erhalten.
- **Implementierungsumfang:** Neue additive Module
  `src/features/variable_contract.py`, `variable_extract.py`,
  `variable_global_pair.py`, `variable_split.py`,
  `variable_dataset_export.py` und `src/ml/variable_data.py`. Der bestehende
  `TrackFeatureArtifact.model_window()`-Aufruf bleibt ohne neue Parameter ein
  32-Schritt-v1-Aufruf; variable Parameter sind additiv. Dazu kamen
  `FEATURE_PROTOCOL_V2.md`, `DATASET_PROTOCOL_V2.md`, ein
  `export-dataset-v2`-CLI, homogene Längen-/Split-Shards und synthetische
  Unit-/Integrationstests.
- **Testumfang bzw. Befehle:**
  - Bytefreier Import: `.venv\Scripts\python.exe -B -c "import src.features; ..."`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_variable_features.py`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_variable_dataset.py`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_feature_contract.py tests\test_global_pair_features.py tests\test_ml_data.py`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_feature_dataset_export.py`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_track_feature_cache.py`
  - `.venv\Scripts\python.exe -m pytest -q tests\test_variable_features.py tests\test_variable_dataset.py`
  - `.venv\Scripts\python.exe -B -c "... Geometrie 2/4/6/8 -> 16/32/48/64 und Schema ..."`
  - `.venv\Scripts\python.exe -m src.features --help` sowie
    `export-dataset-v2 --help | Select-String ...`
  - abschließend `git diff --check`.
- **Ergebnis:** Der erste erfolgreiche v2-Featurelauf ergab `7 passed`; der
  Datasetlauf danach `2 passed`, nach dem expliziten L/Beats/T-NPZ-Feld und
  deterministischen NPZ-Writer erneut `2 passed`. Der abschließende
  v2-Gesamtlauf ergab `11 passed`. Er deckt alle vier T-Werte, variable
  Fenstergrenzen, normalisierte Positionen, 16 globale Features, separate
  Längenkonditionierung, leere Validation-/Test-Shards, dieselbe Split-Map,
  Top-k pro Paar/Länge, homogene Loader-Batches und identische Datei-Hash-
  Tabellen zweier identischer Exporte ab. Die v1-Regressionen bestanden mit
  `12 passed` (Featurevertrag, Global-Pair, ML-Daten), `3 passed` (v1-
  Datasetexport) und `7 passed` (v1-Featurecache). Die v1-Läufe meldeten je
  zwei bekannte `aifc`-/`sunau`-Deprecation-Warnungen unter Python 3.14.
  Import-, Geometrie-/Schema- und CLI-Sonden waren erfolgreich. `git
  diff --check` meldete keine Whitespace-Fehler, nur die bekannten
  LF/CRLF-Hinweise.
- **Fehler/Blockaden:** Der erste `py_compile`-Versuch für die neuen Module
  wurde von einer bestehenden geschützten `__pycache__`-Datei mit
  `Permission denied` blockiert; bytefreie Imports waren erfolgreich und
  schrieben keinen Bytecode. Ein erster Featuretest enthielt einen falschen
  Erwartungswert (`2/8` statt eines fehlerhaften Werts) und schlug mit `1
  failed, 6 passed` fehl. Zwei erste Datasetläufe schlugen ausschließlich
  wegen der synthetischen Fake-Loader-Fixture fehl (SHA nicht an das Fake-
  Manifest weitergereicht beziehungsweise veraltete Fixture-Aufrufe); nach
  Korrektur liefen sie erfolgreich. Diese Fehler änderten keine
  Produktivartefakte. Kein großer Datensatz wurde erzeugt.
- **Schlussfolgerung und nächster Schritt:** Feature Protocol 2 und Dataset
  Format 2 sind als additive, synthetisch geprüfte Export-/Ladestufe
  implementiert. V1-APIs und v1-Datasets bleiben testbar; v2 nutzt getrennte
  Protokoll-/Namespace-/CLI-Verträge, längenhomogene Shards ohne Padding und
  eine gemeinsame Split-Autorität. Der nächste sinnvolle Schritt ist ein
  separater Review der v2-ML-/Checkpoint-/Loss-Schicht; in dieser Aufgabe
  wurden keine ML-Modelle, Trainingsrunner oder realen Großexporte geändert.
  Kein Commit wurde erstellt.

- **Nachkontrolle:** Nach der letzten Manifest-/Statuskorrektur liefen erneut
  `.venv\Scripts\python.exe -m pytest -q tests\test_variable_features.py tests\test_variable_dataset.py`
  mit `11 passed` sowie
  `.venv\Scripts\python.exe -m pytest -q tests\test_feature_contract.py tests\test_global_pair_features.py tests\test_ml_data.py tests\test_feature_dataset_export.py tests\test_track_feature_cache.py`
  mit `22 passed` und denselben zwei bekannten `aifc`-/`sunau`-
  Deprecation-Warnungen. Der bytefreie Import-/Geometriesmoke meldete
  `final v2 imports and geometry OK`; `git diff --check` blieb fehlerfrei.
  Damit ist der dokumentierte Stand mit dem letzten Arbeitsbaum verifiziert.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Erster synthetischer Integrationslauf für den
  additiven Dataset-2-Loader, homogene Mehrlängen-Batches, variable MLP-Ausgaben,
  Objective-v5-Forward-/Backward-Pfad und Checkpoint-Vertrag. Ziel war es,
  Form-/Längenfehler vor dem nächsten Implementierungsschritt sichtbar zu
  machen.
- **Setup/Eingaben:** Repository BeatBridge, ausschließlich synthetische
  Feature- und Audio-Tensoren; Dataset-2-Export mit Längen 2/4/6/8 und
  variablen Waveform-Samplezahlen; `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_dataset.py tests/test_variable_ml.py`
- **Ergebnis inklusive Fehlern:** `10 passed, 2 failed`. Fehler 1 war ein
  Test-Fixture-Verweis auf ein nicht existentes Ergebnisfeld
  `dataset_directory`; der Exporter verwendet nachweislich
  `output_directory`. Fehler 2 war ein Testfehler: Die für den absichtlich
  falschen Längenfall verwendete `length_condition` entsprach weiterhin der
  Länge 2 und konnte daher korrekt akzeptiert werden. Kein Produktivartefakt
  wurde verändert oder gelöscht.
- **Schlussfolgerung/nächster Schritt:** Der neue Pfad importiert und läuft
  bis auf zwei isolierte Testannahmen. Die beiden Tests werden auf die
  tatsächlich verifizierten API-/Konditionsverträge korrigiert; anschließend
  folgt derselbe synthetische Lauf erneut.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Nach Korrektur der beiden isolierten
  Testannahmen sollte der vollständige synthetische Dataset-2-/variable-ML-
  Umfang ohne Padding- oder Längenfehler laufen.
- **Setup/Eingaben:** Dieselben ausschließlich synthetischen Dataset-2-
  Exportdaten, Featuretensore und variablen Waveforms wie im vorherigen Lauf;
  `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_dataset.py tests/test_variable_ml.py`
- **Ergebnis inklusive Fehlern:** `12 passed in 5.26s`; keine Fehler oder
  Blockaden.
- **Schlussfolgerung/nächster Schritt:** Dataset-2-Loader, homogener
  Mehrlängen-Batch-Sampler, dynamische 16/32/48/64-Kontrollpunkte,
  exakte monotone Endpunkte, variable Audio-Samplezahlen, Objective-v5-
  Backpropagation und der neue Checkpoint-/Resume-Vertrag sind synthetisch
  verifiziert. Als nächstes werden die unveränderten v1-Regressionen und ein
  kleiner expliziter Trainings-Smoke-Test ausgeführt.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Der additive v2-Pfad darf bestehende v1-
  Loader, MLP-Modelle, Audio-Cache-Nutzung und den v1-Training-Runner nicht
  verändern. Deshalb wurde die gezielte v1-Regression nach dem neuen Import-
  und Modellpfad erneut ausgeführt.
- **Setup/Eingaben:** Bestehende Repository-Tests mit ihren synthetischen
  Fixtures; kein neuer Datensatz; `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_feature_control_model.py tests/test_vocal_control_model.py tests/test_ml_data.py tests/test_ml_training_runner.py`
- **Ergebnis inklusive Fehlern:** `15 passed in 9.31s`; zwei bekannte CUDA-
  Determinismus-Warnungen aus dem bestehenden Runner-Test, keine Fehler.
- **Schlussfolgerung/nächster Schritt:** v1-Loader, v1-Misch-/Vocal-Modelle
  und der v1-Runner bleiben testbar und unverändert semantisch nutzbar. Es
  folgt nur noch der kleine synthetische Trainings-Smoke-Test des neuen
  variablen Pfades sowie die Abschlussprüfung von Diff und Arbeitsbaum.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Minimaler Trainings-Smoke-Test des neuen
  `variable_time_shared_mlp_v1`: Verifiziert werden sollten ein synthetischer
  Dataset-2-Batch, der dynamische `T=48`-Forwardlauf, Objective-v5-
  Gradiententransport und genau ein Optimizer-Schritt, ohne einen großen oder
  realen Datensatz anzulegen.
- **Setup/Eingaben:** Zwei synthetische Beispiele mit jeweils 48 Feature-
  Kontrollpunkten, unterschiedlichen Waveform-Samplezahlen 320 und 384,
  synthetischen Vocal-Stems, kleiner differentiabler Renderer mit
  Kernelgröße 31; `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_ml.py::test_variable_loss_forward_backward_and_audio_lengths_are_unpadded`
- **Ergebnis inklusive Fehlern:** `1 passed in 4.43s`; Forward, Loss,
  Backward und ein Optimizer-Schritt erfolgreich; keine Fehler oder
  Blockaden.
- **Schlussfolgerung/nächster Schritt:** Der kleine synthetische
  Trainingspfad ist verifiziert. Es folgt nur die abschließende statische
  Prüfung, ein letzter gezielter v2-/v1-Testlauf und die Kontrolle, dass keine
  bestehenden Audio-, Dataset-, Cache- oder Run-Artefakte angefasst wurden.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Abschlussregression nach der additiven
  Dokumentation: Der variable Dataset-/ML-Pfad und die betroffenen v1-
  Loader/Modelle sollen gemeinsam grün bleiben.
- **Setup/Eingaben:** Ausschließlich synthetische v2-Fixtures sowie die
  bestehenden v1-Test-Fixtures; kein Testsplit wurde im Training verwendet;
  `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_dataset.py tests/test_variable_ml.py tests/test_feature_control_model.py tests/test_vocal_control_model.py tests/test_ml_data.py`
- **Ergebnis inklusive Fehlern:** `23 passed in 8.49s`; keine Fehler,
  Blockaden oder Warnungen in diesem kombinierten Lauf.
- **Schlussfolgerung/nächster Schritt:** Die implementierte additive
  Dataset-2-/variable-ML-Baseline ist für den angeforderten synthetischen
  Umfang verifiziert. Es folgt die reine Arbeitsbaum-/Diff-Prüfung; kein
  Commit und kein großer Datensatz werden erstellt.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Synthetische Abnahme des neuen additiven
  variablen TCN/BiLSTM-Hauptmodells: dynamische 2/4/6/8-Takt-Geometrie,
  konstruktive Kurven, Padding-/Packing-Invarianz, stem-aware Objective-v5
  und der neue per-Längen-Runner-/Resume-Vertrag sollten ohne den v1-
  Checkpointpfad zu berühren funktionieren.
- **Setup/Eingaben:** Ausschließlich synthetische 54-Kanal-Featuretensore,
  globale 16er Features und Vocal-/Mix-Waveforms; Längen 2/4/6/8 mit
  T=16/32/48/64; lokaler temporärer Run-Ordner; W&B im Defaultmodus
  `disabled`; `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_tcn_bilstm.py`
- **Ergebnis inklusive Fehlern:** `7 passed in 5.71s`; keine Fehler,
  Blockaden oder Warnungen. Geprüft wurden Single-/Batch-Outputs,
  Gradientenfluss, monotone Endpunkte, gepackte Padding-Invarianz,
  DifferentiableVocalAwareRenderer mit Objective v5, atomare
  Checkpoint-/Manifest-Dateien mit SHA sowie Resume-Ablehnung bei anderem
  Längenset.
- **Schlussfolgerung/nächster Schritt:** Der neue temporale Modellvertrag
  erfüllt den synthetisch geprüften Umfang. Als nächstes folgen die v1-TCN-
  Regression und der kombinierte variable Regressionstest; Testsplit-APIs
  wurden vom neuen Runner nicht eingeführt oder geöffnet.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Abschlussregression des variablen temporalen
  TCN/BiLSTM-Pfads gegen den bestehenden vier-Takt-TCN/BiLSTM-Checkpoint-
  und Training-Runnerpfad.
- **Setup/Eingaben:** Ausschließlich vorhandene synthetische Test-Fixtures;
  kein realer Datensatz, keine Audio-/Cache-/Run-Artefakte; W&B nicht aktiv;
  `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_tcn_bilstm_model.py tests/test_ml_training_runner.py tests/test_variable_ml.py tests/test_variable_dataset.py tests/test_variable_tcn_bilstm.py`
- **Ergebnis inklusive Fehlern:** `33 passed in 7.48s`; zwei bekannte CUDA-
  Determinismus-Warnungen aus dem bestehenden v1-Runner-Test, keine Fehler.
- **Schlussfolgerung/nächster Schritt:** Der v1-
  `tcn_bilstm_transition_control_v1`-Checkpointpfad bleibt testbar, während
  das neue Modell-/Runnerformat separat arbeitet. Es folgen nur noch
  statische Diff-/Arbeitsbaumprüfungen; kein Commit und kein Großtraining.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Vor der Materialisierung des realen Dataset-2-
  Bestands wurde geprüft, ob die vorhandene Analyseumgebung ein strikt
  erkanntes Beat-/Downbeat-Grid (`fallback_used=false`) liefern kann. Das ist
  eine harte Voraussetzung der Kandidatenstufe; ein approximatives 4/4-
  Fallback darf nicht als striktes Grid ausgegeben werden.
- **Setup/Eingaben:** Reeller Track
  `musik/01 - LESS_IS_MORE.flac`; frischer, eindeutiger Pre-Analysis-
  Prüfpfad `output/_preflight_strict_grid_20260820`; keine vorhandenen Audio-,
  Dataset- oder Cache-Artefakte überschrieben; `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -` mit `PreAnalysis` und Ausgabe von
  `grid_source`, `fallback_used`, `is_verified_detection` und
  `beat_grid_sha256`.
- **Ergebnis inklusive Fehlern:** reproduzierbar fehlgeschlagen:
  `grid_source='fallback_from_detected_beats'`, `fallback_used=True`,
  `is_verified_detection=False`; die aufgerufene AUFTAKT-Komponente war nicht
  verfügbar bzw. endete mit `[WinError 5] Zugriff verweigert`. Der Prozess
  endete mit `STRICT_GRID_UNAVAILABLE`. Zusätzlich zeigen die vorhandenen
  Feature-Protocol-1-Manifeste 72 Demucs-Caches und keinen RoFormer-
  Featurecache; vorhandene RoFormer-Stem-Artefakte allein erfüllen diesen
  Featurecache-Vertrag nicht.
- **Schlussfolgerung/nächster Schritt:** Die reale Materialisierung darf
  unter den geforderten strikten Grid- und RoFormer-Provenienzbedingungen
  nicht begonnen werden. Es wurde kein Produktivcode geändert und kein
  Dataset-2-Output angelegt. Nächster Schritt ist die Bereitstellung bzw.
  Freigabe einer funktionierenden, reproduzierbar identifizierten AUFTAKT-
  Umgebung und anschließend die erneute Vorprüfung; Qualitätsfilter werden
  nicht gelockert.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Prompt 7 verlangte eine erneute isolierte
  Strict-Grid-Prüfung mit dem nun verifizierten Repository-Binary. Zuerst
  wurde derselbe Ein-Track-Lauf in der Prozess-Sandbox wiederholt. Danach
  wurde ausschließlich für dieses konkrete Binary eine externe Ausführung
  angefordert, weil `WinError 5` als Sandbox-Ausführungsverweigerung nicht
  als fehlendes oder unbrauchbares Werkzeug interpretiert werden darf.
- **Setup/Eingaben:** Arbeitsverzeichnis
  `D:\Documents\00Uni\00master\BeatBridge`; Eingabe
  `musik\01 - LESS_IS_MORE.flac`; Binary
  `D:\Documents\00Uni\00master\BeatBridge\aufTAKTCl.exe`; verifizierte
  SHA-256
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`;
  neuer Analysepfad
  `output\_preflight_strict_grid_20260820_rerun_01` beziehungsweise für
  den freigegebenen Wiederholungslauf
  `output\_preflight_strict_grid_20260820_rerun_01_escalated`;
  `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:** Sandbox-Lauf und anschließend freigegebener Lauf
  mit dem vollständigen Befehl:
  `.venv\Scripts\python.exe -` aus dem genannten Arbeitsverzeichnis. Der
  Python-Aufruf prüfte zuerst die Binary-SHA und rief anschließend
  `PreAnalysis(str(analysis_root) + "\\")(str(track))` auf. Für den FLAC-
  Track verwendet `PreAnalysis` intern den vollständigen aufTAKT-Aufruf
  `D:\Documents\00Uni\00master\BeatBridge\aufTAKTCl.exe -i
  tmp\audio-<uuid>.wav -r tmp\auftakt-output-<uuid>.txt`; danach werden
  `grid_source`, `fallback_used`, `is_verified_detection`,
  `backend_version`, `analysis_id` und `beat_grid_sha256` geprüft.
- **Ergebnis inklusive Fehlern:** Der Sandbox-Lauf bestätigte die Binary-
  SHA, scheiterte beim Prozessstart erneut mit `[WinError 5] Zugriff
  verweigert` und erzeugte nur
  `grid_source='fallback_from_detected_beats'`, `fallback_used=True` und
  `is_verified_detection=False`. Die ausdrücklich angeforderte externe
  Ausführung startete aufTAKT nachweislich: Der Prozess
  `D:\Documents\00Uni\00master\BeatBridge\aufTAKTCl.exe` war während des
  Laufs mit `Responding=True` vorhanden. Sie lieferte jedoch innerhalb des
  120-Sekunden-Limits kein Ergebnis; der Wrapper endete mit `Exit code 124`
  nach `124047 ms`. Der freigegebene Analyse-Outputpfad wurde nicht erzeugt,
  und im `tmp`-Verzeichnis lag keine fertige
  `auftakt-output-<uuid>.txt`-Datei vor. Damit ist der Fehler nicht der
  Prozessstart, sondern ein Hängen während oder nach dem gestarteten
  aufTAKT-Prozess; ein späterer Datei- oder Lizenzzugriff lässt sich aus dem
  fehlenden aufTAKT-Diagnoseoutput nicht weiter unterscheiden. Der noch
  laufende, exakt zu diesem Preflight gehörende aufTAKT-Prozess wurde danach
  beendet. Kein Produktivcode, Qualitätsfilter, Audio-, Dataset- oder Cache-
  Artefakt wurde geändert.
- **Schlussfolgerung/nächster Schritt:** Der Strict-Grid-Preflight ist auch
  nach der genehmigten Ausführung nicht erfolgreich. Gemäß Prompt 7 wird
  erneut gestoppt; Kandidaten- und Dataset-2-Materialisierung, RoFormer-
  Featurecache-Export und Training werden nicht gestartet. Es gibt weiterhin
  keinen belastbaren Nachweis für `fallback_used=false`,
  `is_verified_detection=true` und einen gültigen Strict-Grid-Hash. Die
  Qualitätsfilter wurden nicht gelockert.

## Verifiziert am 2026-08-20 (additive Multi-Song-Variable-Length-Anbindung)

- **Fragestellung/Reasoning:** Der Multi-Song-Batchpfad sollte additiv die
  Candidate-v2-Längen `2/4/6/8` an jedes Paar weiterreichen, ohne den
  bisherigen v1-Default `(2, 4)` zu verändern. Geprüft wurden CLI-Parsing,
  zentrale Längenvalidierung, Paarweitergabe, Root-Manifest und unabhängige
  Rejection fehlender 8-Takt-Abdeckung. Alle Eingaben waren synthetisch;
  kein realer Batch und kein Dataset wurden erzeugt.
- **Setup:** Repository `D:\Documents\00Uni\00master\BeatBridge`,
  `.venv\Scripts\python.exe`, synthetische WAVs bzw. synthetische Beat-/Grid-
  Fixtures in pytest-Tempordnern; bestehende Nutzeränderungen und Artefakte
  blieben erhalten.
- **Befehl/Testumfang und Ergebnisse:**
  - `.venv\Scripts\python.exe -m pytest -q tests\test_multi_batch_render.py`:
    zunächst `2 passed, 2 failed`. Die beiden Fehler waren Test-Fixture-
    Annahmen: identische Nullsignale wurden korrekt per Audio-SHA dedupliziert
    und ein 12-Takt-Fixture bot keinen ausreichenden 6-Takt-Kontext.
  - Derselbe Lauf nach Fixturekorrektur: `4 passed`.
  - Nach additiver Wiederherstellung der zuvor vorhandenen Regressionstests:
    `8 failed, 4 passed`; alle acht Fehler waren vorübergehende `NameError`
    durch noch fehlende historische Testimporte, kein Produktionsfehler.
  - Derselbe Lauf nach Importkorrektur: `12 passed in 2.64s`.
  - `.venv\Scripts\python.exe -m pytest -q tests\test_multi_batch_render.py tests\test_batch_render.py tests\test_candidates.py`:
    `30 passed in 4.08s`; zwei bekannte `aifc`-/`sunau`-Deprecation-Warnungen
    aus dem bestehenden Audio-Regressionstest.
  - `.venv\Scripts\python.exe -m src.multi_batch_render --help | Select-String
    -Pattern '--transition-bars|transition lengths'` sowie bytefreie
    Konfigurationssonde mit
    `.venv\Scripts\python.exe -B -c ...`: Hilfe zeigt
    `--transition-bars {2,4,6,8}`, Normalisierung von `(8,2,6,4)` ergibt
    `(2,4,6,8)`, erfolgreich.
  - Abschließende Wiederholung desselben Regressionstests nach der rein
    formatierenden Testdatei-Korrektur: `30 passed in 4.08s`, dieselben zwei
    Deprecation-Warnungen.
  - Abschließendes `git diff --check`: keine Whitespace-Fehler; nur die
    bekannten LF/CRLF-Hinweise der Windows-Arbeitskopie.
- **Schlussfolgerung/nächster Schritt:** `generate_multi_song_batch()` nimmt
  nun additiv `transition_lengths_bars=(2, 4)` an, validiert über
  `VariableCandidateGenerationConfig`, verwendet für 6/8 den v2-Konfigurations-
  pfad und schreibt die sortierten Längen in das Root-Manifest. Bei `(2,4)`
  bleibt der v1-Konfigurationspfad erhalten. Die synthetische Paarprüfung
  bestätigt Candidate-v2-Kandidaten für 2/4/6/8 sowie den Erhalt kürzerer
  Kandidaten bei fehlendem 8-Takt-Kontext. Kein Commit, kein realer Batch und
  kein Training.

- **Datum:** 2026-08-20
- **Fragestellung/Reasoning:** Isolierte aufTAKT-Differentialdiagnose nach dem
  vorherigen 120-Sekunden-Abbruch. Unterschieden werden sollten regulär lange
  Verarbeitung, track-/WAV-abhängiges Verhalten, Arbeitsverzeichnis-/Pfad-
  und Schreibprobleme, ein möglicher Lizenz-/GUI-Dialog sowie ein genereller
  Binary-Hänger. Gemäß Diagnoseauftrag wurden keine Kandidaten, Featurecaches,
  Datasets oder Trainingsartefakte materialisiert und kein Produktivcode
  geändert.
- **Setup/Vorabprüfung:** Ausschließlich neuer Ordner
  `output/_auftakt_diagnostic_20260820_01`; Arbeitsverzeichnis
  `D:\Documents\00Uni\00master\BeatBridge`; Binary
  `D:\Documents\00Uni\00master\BeatBridge\aufTAKTCl.exe`; Eingabe
  `D:\Documents\00Uni\00master\BeatBridge\musik\01 - LESS_IS_MORE.flac`.
  Die Binary-SHA-256 war vor jedem direkten Lauf
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`, die
  Binary war 7.195.648 Bytes groß. Die Eingabe existierte, war lesbar und
  hatte 33.552.633 Bytes; der Diagnoseordner wurde neu angelegt und ein
  Schreibprobe-Byte erfolgreich geschrieben. Alle aufTAKT-Eingaben und
  Resultatpfade waren absolut.
- **Werkzeug-/Konvertierungslauf:** Der zunächst gefundene
  `C:\Program Files\SteelSeries\GG\apps\moments\ffmpeg.exe` war ein
  eingeschränkter Capture-Build ohne FLAC-Demuxer und ohne ffprobe; drei
  Konvertierungsversuche scheiterten deshalb mit `Invalid data found when
  processing input` und erzeugten keine WAV. Der gültige FLAC wurde separat
  mit `soundfile` bestätigt (44.100 Hz, Stereo, 4:23,430). Danach wurde ein
  vollwertiges FFmpeg/ffprobe-Paar (`Gyan.FFmpeg.Shared` 9.0.1) verwendet.
  Der Befehl lautete je Ausschnitt `ffmpeg -nostdin -i <absoluter FLAC>
  [-t 10|60] -ar 44100 -ac 2 -c:a pcm_s16le -map_metadata -1 <absoluter WAV>`;
  für den Volltrack entfiel `-t`. `ffprobe` bestätigte für
  `01_10s.wav`, `02_60s.wav` und `03_full.wav` jeweils `sample_rate=44100`,
  `channels=2`, `sample_fmt=s16` und Dauern `10.000000 s`, `60.000000 s`
  beziehungsweise `263.429569 s`. Die Konvertierung schrieb ausschließlich
  in den neuen Diagnoseordner.
- **Befehl/Testumfang – 10-Sekunden-Lauf:** Direkter Aufruf über den isolierten
  Monitor mit maximal 60 Sekunden und 5-Sekunden-Polls:
  `aufTAKTCl.exe -i
  D:\Documents\00Uni\00master\BeatBridge\output\_auftakt_diagnostic_20260820_01\01_10s.wav
  -r
  D:\Documents\00Uni\00master\BeatBridge\output\_auftakt_diagnostic_20260820_01\10s_result.txt`.
  Der Monitor prüfte SHA, PID, Startzeit, CPU-Zeit, Working Set,
  Threadanzahl, `Responding`, stdout/stderr sowie Existenz/Größe und
  Parsebarkeit der Resultatdatei.
- **Ergebnis 10-Sekunden-Lauf:** PID `15880`, Start `16:28:08.162 +02:00`,
  Ende nach `30,347 s`, kein Timeout und kein Kill. CPU-Zeit: `0 ms` beim
  Start, maximal `24.484,375 ms`; Working Set maximal `22.401.024 Bytes`;
  Threads `1–4`; `Responding=True` bei allen lebenden Polls. Die getrennten
  Logs sind `10s.stdout.log` (2.913 Bytes) und `10s.stderr.log` (0 Bytes).
  `10s_result.txt` existierte am Ende mit 240 Bytes und war gemäß dem
  bestehenden drei-spaltigen aufTAKT-Format parsebar.
- **Schlussfolgerung 10-Sekunden-Lauf:** Erfolgreicher Kurztest. Kein
  genereller Binary-Hänger, kein sichtbarer Hinweis auf einen blockierenden
  Lizenz-/GUI-Dialog und kein Ausgabepfadfehler. Deshalb wurden die
  60-Sekunden- und Volltrack-Läufe gemäß Auftrag gestartet; Windows-
  Application-Events und ein sichtbarer manueller Lauf waren nach Regel 9
  nicht erforderlich.
- **Befehl/Testumfang – 60-Sekunden-Lauf:** Derselbe direkte Aufruf mit
  `02_60s.wav`, Resultat `60s_result.txt` und maximal 180 Sekunden;
  Pollintervall 5 Sekunden. Die Binary-SHA wurde vor dem Start erneut
  geprüft.
- **Ergebnis 60-Sekunden-Lauf:** PID `35904`, Start `16:28:49.222 +02:00`,
  Ende nach `55,350 s`, kein Timeout und kein Kill. CPU-Zeit: `0 ms` beim
  Start, maximal `49.578,125 ms`; Working Set maximal `53.194.752 Bytes`;
  Threads `1–4`; `Responding=True` bei allen lebenden Polls. Die getrennten
  Logs sind `60s.stdout.log` (15.946 Bytes) und `60s.stderr.log` (0 Bytes).
  `60s_result.txt` existierte am Ende mit 1.231 Bytes und war parsebar.
- **Schlussfolgerung 60-Sekunden-Lauf:** Erfolgreiche, längere reguläre
  Verarbeitung. Das Verhalten skaliert mit der Eingangslänge und zeigt
  weiterhin CPU-Fortschritt statt eines Hängers.
- **Befehl/Testumfang – vollständiger Track:** Derselbe direkte Aufruf mit
  `03_full.wav`, Resultat `full_result.txt` und maximal 600 Sekunden;
  Pollintervall 5 Sekunden. Fortschritt wurde in `full.polls.ndjson`
  gespeichert; die Binary-SHA wurde vor dem Start erneut geprüft.
- **Ergebnis vollständiger Track:** PID `40328`, Start `16:29:56.948 +02:00`,
  Ende nach ungefähr `156,040 s`, kein Timeout und kein Kill. CPU-Zeit stieg
  von `15,625 ms` beim ersten Snapshot auf maximal `149.250 ms`; Working Set
  maximal `182.337.536 Bytes`; Threads `1–4`; `Responding=True` bei allen
  lebenden Polls. Die getrennten Logs sind `full.stdout.log` (73.308 Bytes)
  und `full.stderr.log` (0 Bytes). `full_result.txt` existierte am Ende mit
  9.863 Bytes und war parsebar.
- **Schlussfolgerung vollständiger Track:** Der vollständige Track benötigt
  in dieser Umgebung rund 2:36 Minuten. Der frühere äußere Abbruch nach
  120 Sekunden war daher nachweislich zu kurz; er war kein Beleg für einen
  Hänger. Qualitätsfilter und Timeouts im Produktivcode wurden nicht
  geändert.
- **Eindeutige Differentialdiagnose:** (1) **Lange reguläre Verarbeitung** ist
  bestätigt: 10 s Audio → 30,347 s, 60 s Audio → 55,350 s, Volltrack →
  156,040 s, jeweils mit CPU-Fortschritt und parsebarer Ausgabe. (2) Ein
  track-/WAV-formatabhängiger Hänger ist für diesen gültigen PCM-WAV-Pfad
  nicht beobachtet; andere Tracks/Formate sind damit nicht pauschal
  freigegeben. (3) Falsches Arbeitsverzeichnis bzw. relative Pfade sind für
  den direkten Lauf mit absolutem Input/Output und dokumentiertem Repository-
  Arbeitsverzeichnis ausgeschlossen. (4) Ein nicht beschreibbarer
  Ausgabepfad ist ausgeschlossen: Schreibprobe und Resultatdateien waren
  erfolgreich. (5) Ein versteckter Lizenz-/GUI-Dialog wurde in den drei
  Läufen nicht beobachtet; der Prozess blieb responsiv und beendete sich
  selbst, daher war kein ungefragter sichtbarer manueller Lauf nötig. (6) Ein
  genereller Hänger des geprüften Binaries ist in dieser Umgebung
  ausgeschlossen. Der bisherige Strict-Grid-/PreAnalysis-Befund ist damit
  als **zu kurzer äußerer Timeout bei regulär langer aufTAKT-Verarbeitung**
  klassifiziert, nicht als Binary-Hänger. Keine Lizenzumgehung, kein Dataset
  und kein Training wurden gestartet.

## Verifiziert am 2026-08-20 (finaler vollständiger Strict-Grid-Preflight)

- **Fragestellung/Reasoning:** Nach der isolierten aufTAKT-Diagnose sollte der
  vollständige `PreAnalysis`-Vertrag auf einem neuen, bisher unbenutzten
  Analysepfad geprüft werden. Der äußere Lauf durfte nicht nach 120 Sekunden
  abbrechen; deshalb wurde die freigegebene Session mit 900 Sekunden Timeout
  und regulärem Polling gestartet. Kandidaten-, Feature- und Datasetpfade
  durften erst nach `auftakt_matched_to_librosa` fortgesetzt werden.
- **Setup/Eingaben:** Arbeitsverzeichnis
  `D:\Documents\00Uni\00master\BeatBridge`; Track
  `musik\01 - LESS_IS_MORE.flac`; neuer Analysepfad
  `output\pre_analysis_strict_final_20260820_01`; Binary
  `D:\Documents\00Uni\00master\BeatBridge\aufTAKTCl.exe`; erwartete und
  geprüfte Binary-SHA-256
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`;
  `.venv\Scripts\python.exe`; externe Ausführung des konkreten Binaries war
  freigegeben.
- **Vollständiger Befehl/Testumfang:**
  `.venv\Scripts\python.exe -u -` mit Prüfung der Binary-SHA und
  `PreAnalysis(str(Path('output/pre_analysis_strict_final_20260820_01')) + '\\')(str(Path('musik/01 - LESS_IS_MORE.flac')))`;
  die interne aufTAKT-Stufe lief mit
  `aufTAKTCl.exe -i tmp\audio-<uuid>.wav -r tmp\auftakt-output-<uuid>.txt`.
  Der äußere freigegebene Prozess lief als fortlaufende Session; aufTAKT war
  währenddessen responsiv und wurde nicht vorzeitig beendet. Gesamtdauer bis
  zum regulären Abschluss: ca. `162,9 s`.
- **Ergebnis inklusive Fehlern:** Die Binary-SHA und die vollständige
  Analyse-Identität wurden gespeichert. Der gespeicherte Analyseeintrag ist
  `output\pre_analysis_strict_final_20260820_01\v2\<audio-sha>\<analysis-id>\analysis.json`
  (die vollständige Datei liegt dort; die tatsächliche
  `analysis_id` lautet
  `f703964b74ab78cb6a3ffcc518c0b66014cb721b528e1d7e1d8bee9efe31d3933dc`).
  Der Binary-SHA im Analysevertrag stimmt. Der Merge ergab jedoch
  `grid_source='fallback_from_detected_beats'`, `fallback_used=true`,
  `is_verified_detection=false`, `confidence=0`, 533 Beatframes,
  `missing_librosa=5` und `missing_auftakt=105`. Der erzeugte
  `beat_grid_sha256` lautet
  `b4ae1803b36bce3dfc749d3453fdf785b5f5a030ef838d63ed68ea5aaae28f27`.
  Der Hash ist syntaktisch gültig, belegt aber wegen des Fallbacks kein
  strikt erkanntes Downbeat-Grid. Der Preflight endete deshalb mit
  `STRICT_GRID_SOURCE_MISMATCH`; es trat kein äußerer Timeout und kein
  Prozessstartfehler auf.
- **Schlussfolgerung/nächster Schritt:** Der vollständige PreAnalysis-
  Vertrag ist fachlich nicht erfüllt. Gemäß Vorgabe wird hier gestoppt;
  `output/pre_analysis_variable_v2_strict_20260820`, ein neuer Multi-Song-
  Batch, neue RoFormer-Featurecaches und Datasetformat 2 wurden nicht
  angelegt. Keine Qualitätsfilter wurden gelockert, kein Produktivcode und
  kein bestehendes Audio-, Dataset-, Cache- oder Run-Artefakt wurde geändert.
  Training und Prompt 8 bleiben ausgesetzt.
## Verifiziert am 2026-08-20 (Merge-v2-Syntaxcheck, Versuch 1)

- **Fragestellung/Reasoning:** Vor dem ersten synthetischen Merge-v2-Test sollte
  geprüft werden, ob die neuen Analyse- und Candidate-Dateien syntaktisch
  kompilieren. Der Standardcheck wurde gewählt, weil er Importfehler früh
  sichtbar macht.
- **Setup/Eingaben:** Repository `D:\Documents\00Uni\00master\BeatBridge`;
  ausschließlich `.venv\Scripts\python.exe`; geprüft wurden
  `src\analysis\pre_analysis.py`, `src\candidates\generation.py`,
  `src\candidates\variable.py` und `tests\test_partial_merge.py`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m py_compile src\analysis\pre_analysis.py src\candidates\generation.py src\candidates\variable.py tests\test_partial_merge.py`
- **Ergebnis einschließlich Fehlern:** Der Check startete nicht bis zur
  Codeauswertung. Python erhielt beim Ersetzen der vorhandenen Datei
  `src\analysis\__pycache__\pre_analysis.cpython-314.pyc` den Fehler
  `[WinError 5] Zugriff verweigert` beim Rename der temporären `.pyc`.
  Es wurden keine Produktivdateien, Audio-, Dataset-, Cache- oder Run-Artefakte
  verändert.
- **Schlussfolgerung/nächster Schritt:** Der Fehler ist ein Schreibschutz des
  bestehenden Bytecode-Caches und kein Nachweis eines Syntaxfehlers. Kein Cache
  wird gelöscht oder überschrieben; der nächste Check liest die Quellen
  schreibfrei per AST und führt anschließend die synthetischen Tests aus.

## Verifiziert am 2026-08-20 (Merge-v2-Syntaxcheck, schreibfrei)

- **Fragestellung/Reasoning:** Nach dem schreibgeschützten `py_compile`-Fehler
  wurde derselbe Syntaxumfang ohne Bytecode-Erzeugung geprüft, damit bestehende
  `__pycache__`-Artefakte unangetastet bleiben.
- **Setup/Eingaben:** `.venv\Scripts\python.exe -B`; vier neue/geänderte
  Python-Quellen wie im vorherigen Lauf.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -B -c "import ast, pathlib; paths=[pathlib.Path(r'src/analysis/pre_analysis.py'), pathlib.Path(r'src/candidates/generation.py'), pathlib.Path(r'src/candidates/variable.py'), pathlib.Path(r'tests/test_partial_merge.py')]; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in paths]; print('AST_OK', len(paths))"`
- **Ergebnis einschließlich Fehlern:** Erfolgreich; Ausgabe `AST_OK 4`.
  Keine Dateien wurden geschrieben.
- **Schlussfolgerung/nächster Schritt:** Die vier Quellen sind syntaktisch
  parsebar. Danach folgt der gezielte synthetische pytest-Lauf für Merge-v2 und
  lückenbewusste Candidate-v2-Generierung.

## Verifiziert am 2026-08-20 (Merge-v2-Synthesetests, Versuch 1)

- **Fragestellung/Reasoning:** Der neue monotone Merge, seine Acceptance-
  Diagnostik und die lückenbewusste Candidate-v2-Prüfung sollten gegen die
  geforderten synthetischen Grenzfälle sowie die vorhandenen v1-Analyse- und
  Candidate-Regressionen geprüft werden.
- **Setup/Eingaben:** Ausschließlich im Test erzeugte Beat-/Taktfolgen; kein
  Audio, kein Analysecache und kein Dataset. Der pytest-Cacheprovider wurde
  deaktiviert. Tests: `tests/test_partial_merge.py`,
  `tests/test_pre_analysis.py`, `tests/test_candidates.py`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_pre_analysis.py tests/test_candidates.py`
- **Ergebnis einschließlich Fehlern:** 24 Tests bestanden, 3 Tests schlugen
  fehl. Die Fehler waren Testfixture-/Erwartungsfehler: Das Missing-Librosa-
  Fixture entfernte die Librosa- statt der aufTAKT-Beats; ein Gleichabstands-
  Match erzwingt keine bestimmte der zwei gleichwertigen Librosa-Indizes; und
  ein Shift um genau einen Beat erzeugte wegen der regelmäßigen Folge weiterhin
  Matches. Es gab keinen Produktivartefakt- oder Cachefehler.
- **Schlussfolgerung/nächster Schritt:** Die synthetischen Daten werden so
  korrigiert, dass sie tatsächlich fünf unbeantwortete Librosa-Beats, eine
  gleichwertige eindeutige Zuordnung und einen Shift außerhalb von `0.2 s`
  darstellen. Danach wird derselbe Testumfang wiederholt.

## Verifiziert am 2026-08-20 (Merge-v2-Synthesetests, Versuch 2)

- **Fragestellung/Reasoning:** Nach der Korrektur der drei Testfixtures sollte
  derselbe Grenzfallumfang ohne Änderung an v1-Verträgen erneut vollständig
  geprüft werden.
- **Setup/Eingaben:** Nur synthetische In-Memory-Beatfolgen; v1-Tests und
  Candidate-v2-Lückentest wie im vorherigen Lauf; pytest-Cacheprovider
  deaktiviert; Python ausschließlich `.venv\Scripts\python.exe`.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_pre_analysis.py tests/test_candidates.py`
- **Ergebnis einschließlich Fehlern:** Erfolgreich: `27 passed in 2.89s`.
  Abgedeckt sind exakter Vollmatch, Randbeats, fünf fehlende Librosa-Matches,
  doppelte unabhängige Nearest-Neighbor-Gefahr, vollständiger Mismatch,
  monotone eindeutige Paarung, Count-/Zeitlücke ohne Kandidatenüberquerung,
  spätere 2/4/6/8-Bar-Kandidaten sowie die vorhandenen v1-Analyse- und
  Candidate-Tests.
- **Schlussfolgerung/nächster Schritt:** Der synthetische Merge-v2- und
  Candidate-v2-Kern ist bestanden. Als nächstes werden Cache-Roundtrip und
  vollständiger bestehender Analyse-/Candidate-Regressionstest geprüft, bevor
  der Drei-Track-Real-Audit beginnt.

## Verifiziert am 2026-08-20 (Merge-v2-Cache-Roundtrip, Versuch 1)

- **Fragestellung/Reasoning:** Der tatsächliche `PartialPreAnalysis`-Aufruf
  sollte mit synthetischem aufTAKT-Output eine neue Cacheidentität, v2-
  Provenienz und einen wiederladbaren Analyse-Cache erzeugen, ohne v1-Caches zu
  berühren.
- **Setup/Eingaben:** Synthetische Beatfolge und ein temporärer Platzhaltertrack;
  aufTAKT wurde im Test gezielt simuliert. Tests weiterhin nur
  `tests/test_partial_merge.py`, `tests/test_pre_analysis.py` und
  `tests/test_candidates.py`; pytest-Cacheprovider deaktiviert.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_pre_analysis.py tests/test_candidates.py`
- **Ergebnis einschließlich Fehlern:** 27 Tests bestanden, 1 Test schlug fehl.
  Der Stub ersetzte global `subprocess.run` und fing deshalb beim Lazy-Import
  von Librosa/Numba zusätzlich den internen `ver`-Aufruf mit unerwarteten
  Keyword-Argumenten ab. Das ist ein Testharness-Fehler; der Produktivcode
  und keine bestehenden Artefakte wurden verändert.
- **Schlussfolgerung/nächster Schritt:** Der Stub wird auf den konkreten
  aufTAKT-Befehl beschränkt und delegiert fremde Subprocess-Aufrufe an die
  Originalfunktion. Danach wird derselbe Umfang wiederholt.

## Verifiziert am 2026-08-20 (Merge-v2-Cache-Roundtrip, Versuch 2)

- **Fragestellung/Reasoning:** Nach der Isolierung des aufTAKT-Stubs sollte der
  tatsächliche v2-Aufruf einschließlich Cache-Roundtrip vollständig bestehen.
- **Setup/Eingaben:** Nur synthetischer Platzhaltertrack, synthetischer
  aufTAKT-Text und temporärer Analyse-Root; kein realer Track, Batch,
  Featurecache oder Dataset.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_pre_analysis.py tests/test_candidates.py`
- **Ergebnis einschließlich Fehlern:** Erfolgreich: `28 passed in 2.95s`.
  Der Test bestätigt neue Merge-v2-Analyse-ID und Cachepfad, SHA-Provenienz,
  `fallback_used=false`, gespeicherte Merge-Diagnostik sowie Wiederladen des
  v2-Caches ohne zweiten aufTAKT-Aufruf. Die v1-Analyse- und Candidate-Tests
  bleiben ebenfalls erfolgreich.
- **Schlussfolgerung/nächster Schritt:** Der additive synthetische Pfad ist
  inklusive Cache-Roundtrip bestanden. Vor dem Real-Audit folgt noch ein
  breiterer read-only Regressionstest der direkt betroffenen Analyse-,
  Candidate- und Pipeline-Tests.

## Verifiziert am 2026-08-20 (direkte Merge-v2-Regressionen)

- **Fragestellung/Reasoning:** Der neue Pfad darf die bestehenden v1-
  Analyse-, Candidate-, Batch-, Multi-Batch-, Rendering- und
  Song-Compatibility-Verträge nicht verändern. Deshalb wurden die direkt
  importierenden/verbrauchenden Testgruppen gemeinsam ausgeführt.
- **Setup/Eingaben:** Synthetische Fixtures der bestehenden Tests und die neuen
  synthetischen Merge-v2-Fixtures; pytest-Cacheprovider deaktiviert; keine
  realen Musikdateien oder bestehenden Outputpfade als Schreibziel.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_pre_analysis.py tests/test_candidates.py tests/test_batch_render.py tests/test_multi_batch_render.py tests/test_rendering.py tests/test_song_compatibility.py`
- **Ergebnis einschließlich Fehlern:** Erfolgreich: `65 passed, 2 warnings in
  6.79s`. Die einzigen Hinweise sind bekannte DeprecationWarnings aus
  `audioread` zu `aifc`/`sunau`; kein Testfehler und keine Artefaktänderung.
- **Schlussfolgerung/nächster Schritt:** Der additive Merge-v2-Pfad ist gegen
  die direkt abhängigen synthetischen v1-Verträge regressionsfrei. Der nächste
  Schritt ist der geforderte kleine Audit auf drei realen Tracks mit neuen,
  eindeutigen Analysepfaden; Batch-, Feature- und Datasetexport bleiben dabei
  ausdrücklich gesperrt.
## Verifiziert am 2026-08-20 (Merge-v2-Real-Audit, Sessionstarts und Blockaden)

- **Fragestellung/Reasoning:** Vor einer späteren Dataset-2-Freigabe musste der
  neue monotone partielle Merge auf `LESS_IS_MORE`, `HELP_LESS` und einem
  repräsentativen Intro/Outro-Track mit dem realen aufTAKT-Binary geprüft
  werden. Der Lauf sollte als fortlaufende Session ohne äußeren 120-Sekunden-
  Timeout arbeiten und pro Track Matchstatistik, Provenienz, vollständige
  Taktblöcke und die verfügbaren 2/4/6/8-Takt-Längen speichern.
- **Setup:** Arbeitsverzeichnis
  `D:\Documents\00Uni\00master\BeatBridge`; Python ausschließlich
  `.venv\Scripts\python.exe`; aufTAKT-Binary
  `D:\Documents\00Uni\00master\BeatBridge\aufTAKTCl.exe`, SHA-256
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`;
  `approximate_grid_policy=reject`; Kandidaten nur als In-Memory-Self-Pair-
  Verfügbarkeitsdiagnose, kein Batch, Featurecache oder Dataset.
- **Lauf 1:** Neuer Root
  `output\pre_analysis_merge_v2_audit_20260820_01`, getrennte
  `audit.stdout.log`/`audit.stderr.log`, Eingaben
  `musik\01 - LESS_IS_MORE.flac`, `musik\05 - HELP_LESS.flac` und
  `musik\10 - END_OF_THE_STORY.flac`. Der Startbefehl verwendete einen
  fortlaufenden `Start-Process`-Wrapper für `.venv\Scripts\python.exe -c`.
  **Ergebnis:** Der Wrapper übergab nur `import`; Python meldete in
  `audit.stderr.log` `SyntaxError: Expected one or more names after 'import'`.
  aufTAKT wurde in diesem Lauf nicht gestartet. Der Fehler liegt in der
  Prozessargument-Quotierung, nicht in Sandbox, Binary oder Analyse.
- **Lauf 2:** Neuer Root
  `output\pre_analysis_merge_v2_audit_20260820_02`, gleicher logischer
  Auditbefehl. Nach dem Polling wurde der Lauf vollständig abgeschlossen;
  die anfängliche Startausgabe war wegen des äußeren Wrappers leer. Die beiden
  gültigen Tracks wurden analysiert; der dritte Pfad war falsch geschrieben
  (`musik\10 - END_OF_THE_STORY.flac`) und erzeugte den aufgezeichneten
  `FileNotFoundError`. Die beiden erfolgreichen Ergebnisse wurden nicht als
  vollständiger Drei-Track-Audit gewertet.
- **Lauf 3:** Neuer Root
  `output\pre_analysis_merge_v2_audit_20260820_03`; der Base64-PowerShell-
  Wrapper erreichte Python nicht, weil der expandierte Interpreterpfad als
  `python.exe.Path` endete. `audit.stderr.log` enthält den
  `CommandNotFoundException`; aufTAKT wurde in diesem Lauf nicht gestartet.
- **Lauf 4:** Neuer Root
  `output\pre_analysis_merge_v2_audit_20260820_04`; korrigierter Wrapper,
  fortlaufend gestartet und regelmäßig gepollt. Der vollständige aufTAKT-
  Aufruf für LESS_IS_MORE und HELP_LESS lief jeweils mehrere Minuten ohne
  äußeren 120-Sekunden-Timeout. Der dritte Eintrag hatte erneut den falschen
  Dateinamen und wurde als `FileNotFoundError` isoliert. Die beiden korrekten
  Trackresultate und drei atomare v2-`analysis.json`-Caches (zwei Trackcaches
  plus der spätere gültige Intro/Outro-Cache) wurden separat validiert.
- **Lauf 5:** Neuer Root
  `output\pre_analysis_merge_v2_audit_20260820_05`, nur mit dem korrekten
  Intro/Outro-Track `musik\10 - END OF THE STORY.flac`. Der Prozess wurde als
  fortlaufende Session gestartet und gepollt; FLAC→WAV und aufTAKT liefen ohne
  Prozessstartfehler durch. Das Ergebnis wurde in
  `output\pre_analysis_merge_v2_audit_20260820_05\audit.json` geschrieben.
- **Schlussfolgerung:** Die Wrapperfehler waren vollständig vor dem Binary-
  bzw. Analysevertrag isoliert. Der finale fachliche Audit besteht aus den
  erfolgreichen LESS_IS_MORE-/HELP_LESS-Records aus `_04` und dem korrekten
  END-OF-THE-STORY-Record aus `_05`; kein Sandbox- oder Binary-Fehler wurde
  als Analyseergebnis fehlinterpretiert.

## Verifiziert am 2026-08-20 (Merge-v2-Real-Audit, fachliche Ergebnisse)

- **Fragestellung/Reasoning:** Verifiziert wurden die neue `grid_source`,
  `fallback_used`, Matchabdeckungen, Distanzquantile, vollständige Taktblöcke,
  Candidate-Längen, aufTAKT-SHA, Beat-Grid-SHA und Cachekonsistenz. Für die
  Kandidatenzahl wurde je Track ein synthetisch nicht verändernder Self-Pair
  auf dem realen analysierten Grid verwendet; dies ist keine Multi-Song-
  Batchmaterialisierung.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -B -c "... liest ausschließlich die beiden neuen audit.json-Roots und deren analysis.json, berechnet Beat-Grid-SHAs und prüft die v2-Mergekennung ..."`
  mit den Roots `output\pre_analysis_merge_v2_audit_20260820_04` und
  `output\pre_analysis_merge_v2_audit_20260820_05`.
- **Ergebnis einschließlich Fehlern:** Erfolgreich: Ausgabe
  `AUDIT_VALIDATION_OK 3 records 3 caches`. Alle drei Records melden die
  dokumentierte Binary-SHA und vollständige 3-Tupel; alle drei Cachedateien
  tragen `librosa_auftakt_monotonic_partial_v2`, passende
  `diagnostics.merge`-Daten, konsistente `beat_grid_sha256`-Werte und keine
  temporären Geschwisterdateien.

  | Track | Librosa / aufTAKT | Matches | Coverage Librosa / aufTAKT im gemeinsamen Bereich | Grid/Fallback | vollständige Takte; längster Block | Self-Pair-Längen |
  |---|---:|---:|---:|---|---:|---|
  | `01 - LESS_IS_MORE.flac` | 533 / 632 | 527 | 0,988743 / 1,0 | `auftakt_matched_to_librosa_partial_v2` / `false` | 131; 93 | 2, 4, 6, 8 |
  | `05 - HELP_LESS.flac` | 451 / 491 | 449 | 0,995556 / 1,0 | `auftakt_matched_to_librosa_partial_v2` / `false` | 113; 113 | 2, 4, 6, 8 |
  | `10 - END OF THE STORY.flac` | 601 / 316 | 300 | 0,499168 / 1,0 | `fallback_from_detected_beats` / `true` | 75; 75 (nur Diagnostik) | keine, strikt abgelehnt |

  Für LESS_IS_MORE wurden zusätzlich `unmatched aufTAKT before/inside/after =
  64/0/41`, `unmatched Librosa inside = 6`, Distanz `p50/p95/max =
  0,022653/0,142331/0,183923 s` und gemeinsamer Bereich
  `48,297506..247,780136 s` verifiziert. HELP_LESS meldet `unmatched aufTAKT =
  0/0/42`, `unmatched Librosa inside = 2`, Distanz
  `0,025646/0,163664/0,181791 s` und gemeinsamen Bereich
  `0,14..168,460771 s`. END OF THE STORY meldet wegen der realen
  Librosa-/aufTAKT-Differenz `0,499168` Librosa-Abdeckung und bleibt deshalb
  korrekt im Fallback; es wurden keine Metadaten erfunden.
- **Schlussfolgerung/nächster Schritt:** Der neue Mergepfad ist auf zwei der
  drei repräsentativen Tracks strikt partiell verifiziert und liefert dort
  alle Kandidatenlängen. Der dritte Track ist ein ehrlicher, reproduzierbarer
  Fallback und blockiert eine pauschale Drei-Track-Freigabe. Es werden daher
  weiterhin kein Multi-Song-Batch, kein Featurecache, kein Dataset und kein
  Training gestartet; die Abweichung muss im Review bewertet werden.

## Verifiziert am 2026-08-20 (Merge-v2-Regression nach Diagnostikpräzisierung)

- **Fragestellung/Reasoning:** Die zusätzliche Kennzeichnung eines disjunkten
  gemeinsamen Zeitbereichs (`overlap=false`) sollte die v2-Diagnostik verbessern,
  ohne den monotone Merge, die Candidate-Lückenprüfung oder bestehende v1-
  Pfade zu verändern.
- **Setup/Eingaben:** Synthetische Merge-/Lückenfixtures sowie die bestehenden
  v1-Analyse-, Candidate-, Batch-, Multi-Batch-, Rendering- und
  Song-Compatibility-Tests; pytest-Cacheprovider deaktiviert.
- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_partial_merge.py tests/test_pre_analysis.py tests/test_candidates.py tests/test_batch_render.py tests/test_multi_batch_render.py tests/test_rendering.py tests/test_song_compatibility.py`
- **Ergebnis einschließlich Fehlern:** Erfolgreich: `66 passed, 2 warnings in
  5.86s`. Die zwei bekannten `audioread`-DeprecationWarnings zu `aifc` und
  `sunau` blieben ohne Testfehler.
- **Schlussfolgerung/nächster Schritt:** Der Merge-v2-Pfad und die direkten
  v1-Regressionen bleiben bestanden. Wegen des ehrlichen END-OF-THE-STORY-
  Fallbacks wird weiterhin kein realer Multi-Song-Batch, Featurecache oder
  Dataset erzeugt.
## Verifiziert am 2026-08-20 (Materialisierung-Preflight: v2-Runner-Blocker)

- **Fragestellung/Reasoning:** Vor der realen Korpusinventur wurde geprüft, ob
  der bestehende Multi-Song-Runner den bereits verifizierten Merge-v2-Pfad
  verwenden kann, ohne v1-Verträge umzudeuten.
- **Setup/Eingaben:** Repository-Arbeitsbaum, `src\multi_batch_render.py`,
  `src\batch_render.py` und die vorhandenen v2-Analyse-/Candidate-Verträge;
  Korpusprüfung unter `musik\`.
- **Befehl/Testumfang:** Read-only-Inspektion mit `rg`/PowerShell sowie
  `Get-ChildItem musik -Recurse`; festgestellt wurden 119 Audio-Dateien und
  der bisher nicht vorhandene Zielpfad
  `output\pre_analysis_variable_v2_strict_20260820`.
- **Ergebnis einschließlich Blockade:** `src\multi_batch_render.py` importiert
  und instanziiert fest `PreAnalysis` (auch in den Analyseworker-Threads).
  Es gibt keinen Parameter oder CLI-Schalter für `PartialPreAnalysis` bzw.
  `librosa_auftakt_monotonic_partial_v2`. Ein unveränderter CLI-Aufruf würde
  deshalb v1-Analysegrids erzeugen und ist für Phase 2 nicht vertragskonform.
  Das ist ein reproduzierbarer Integrationsblocker, kein Analyse- oder
  Binaryfehler. Es wurde noch kein Batch und kein Dataset gestartet.
- **Schlussfolgerung/nächster Schritt:** Phase 1 läuft zunächst über einen
  separaten, reproduzierbaren v2-Corpus-Worker mit maximal vier Analyseworkern.
  Ein additiver Runner-Anschluss wird erst nach der Inventur und nur falls für
  Phase 2 erforderlich vorgenommen; v1-Standardverhalten bleibt unverändert.
## Verifiziert am 2026-08-20 (Materialisierung-Preflight: Inventurstart 01)

- Fragestellung/Reasoning: Die corpusweite Merge-v2-Inventur sollte unter `output/pre_analysis_variable_v2_strict_20260820` mit vier Workern und ausschließlich neuen Artefakten starten.
- Setup: 119 Musikdateien; fortlaufender PowerShell-Worker; `.venv\\Scripts\\python.exe` vorgesehen; aufTAKTCl-Merge-v2; noch keine Kandidaten-, Feature- oder Datasetstufe.
- Befehl/Testumfang: Start-Process mit eingebettetem Python-Inventurskript. Der PowerShell-String verlor beim Aufbau des Pfads die Backslashes und resolvte `'.venvScriptspython.exe'` statt `.venv\\Scripts\\python.exe`.
- Ergebnis inklusive Fehlern: Der Worker wurde nicht mit Python gestartet. Es entstand ausschließlich der neue leere Zielpfad mit `inventory.stdout.log` und `inventory.stderr.log`; kein Analysecache und keine Nutzerartefakte wurden überschrieben. Der Fehler trat vor dem Prozessstart des Python-Workers auf; aufTAKTCl wurde nicht erreicht.
- Schlussfolgerung/nächster Schritt: Der exakte, nun belegte Zielpfad wird nicht wiederverwendet. Die Inventur wird reproduzierbar unter einem neuen eindeutigen Suffixpfad gestartet; der Pfadfehler wird nicht als Analyse- oder aufTAKT-Fehler gewertet.
## Verifiziert am 2026-08-20 (Materialisierung-Preflight: Inventurstart 02)

- Fragestellung/Reasoning: Die korrigierte Inventur sollte mit dem korrekten `.venv\\Scripts\\python.exe` im neuen Retry-Analysepfad starten.
- Setup: `output/pre_analysis_variable_v2_strict_20260820_retry01`; vier Worker; Merge-v2; keine Kandidaten-/Feature-/Datasetstufe.
- Befehl/Testumfang: `Start-Process` mit `.venv\\Scripts\\python.exe -u output/pre_analysis_variable_v2_strict_20260820_retry01/inventory_worker.py`.
- Ergebnis inklusive Fehlern: Der Python-Prozess startete, scheiterte aber vor jeder Analyse mit `ModuleNotFoundError: No module named 'src'`, weil das Skriptverzeichnis und nicht der Repository-Root im Importpfad lag. Es wurde kein aufTAKTCl-Prozess gestartet und kein Analysecache geschrieben.
- Schlussfolgerung/nächster Schritt: Der Fehler liegt im Einmal-Wrapper, nicht im Analysewerkzeug. Der Wrapper wurde additiv um den Repository-Root ergänzt und wird im selben noch cachefreien Retrypfad erneut gestartet; der Lauf wird separat als korrigierter Versuch protokolliert.
## Verifiziert am 2026-08-20 (Materialisierung Phase 1: Merge-v2-Korpusinventur)

- Fragestellung/Reasoning: Der vollständige Musikbestand wurde mit Merge-v2 inventarisiert, bevor Kandidaten, Features oder Dataset v2 erzeugt werden. Zulässig sind nur `fallback_used=false` und `is_verified_detection=true`; BPM- und bestehende Policy-Ausschlüsse bleiben ausgeschlossen.
- Setup: neuer Analysepfad `output/pre_analysis_variable_v2_strict_20260820_retry01` (der ursprünglich angeforderte Pfad war durch zwei dokumentierte Wrapper-Fehlstarts reserviert); 119 Audio-Dateien, 118 kanonische Audio-SHAs, 4 Analyseworker; `.venv\\Scripts\\python.exe`; Binary-SHA gemäß `docs/EXTERNAL_TOOLS.md`; BPM 145..165; `approximate_grid_policy=reject`; Merge-Algorithmus `librosa_auftakt_monotonic_partial_v2`.
- Befehl/Testumfang: corpusweiter atomarer Worker mit aufTAKT-Aufruf pro kanonischer Audio-SHA, v2-Analysecache sowie Self-Pair-Kandidatenprüfung für 2/4/6/8 Takte. Anschließend atomarer Cache-Join zu `inventory_verified.json` mit Cache-Dateihashes.
- Ergebnis inklusive Fehlern: 119 Inventurdatensätze: 87 `strict_accepted`, 24 `fallback_rejected`, 7 `BPM-/Policy-ausgeschlossen`, 1 `Audio-SHA-Duplikat`, 0 `analysis_failed`. Alle 87 strikt akzeptierten Tracks bieten Self-Pair-Kandidaten für 2, 4, 6 und 8 Takte; Matrix: 2=87, 4=87, 6=87, 8=87. Alle akzeptierten Datensätze tragen `grid_source=auftakt_matched_to_librosa_partial_v2`, `fallback_used=false`, `is_verified_detection=true`, eine `analysis_id` und einen `beat_grid_sha256`. Die Cache-Join-Prüfung fand 119/119 passende Analysecaches mit Hash.
- Schlussfolgerung/nächster Schritt: Die Stop-Bedingung wegen fehlender Längen oder unzureichender Trackanzahl ist nicht erfüllt. Die Kandidatenstufe darf ausschließlich mit den 87 Strict-Accepted-Pfaden beginnen; die 24 ehrlichen Fallbacks und 7 BPM/Policy-Ausschlüsse werden nicht weitergereicht. `inventory.json` bleibt als atomarer Rohinventar erhalten; `inventory_verified.json` ist die verifizierte, um Cache-/Taktblockdaten ergänzte Inventur.
## Verifiziert am 2026-08-20 (Materialisierung-Preflight: Batchstart 01)

- Fragestellung/Reasoning: Der Multi-Song-Kandidatenlauf sollte ausschließlich die 87 Strict-Accepted-Tracks verwenden und v2 explizit an den bestehenden Runner anbinden.
- Setup: neues Ziel `output/batch_variable_v2_strict_20260820_run01`; Wrapper mit `PartialPreAnalysis`, 2/4/6/8 Takten, BPM 145..165, vier Workern, `approximate_grid_policy=reject`.
- Befehl/Testumfang: Start des Wrappers mit `.venv\\Scripts\\python.exe -u` als fortlaufender Prozess.
- Ergebnis inklusive Fehlern: Python startete, aber der Wrapper scheiterte vor dem Runnerimport mit `ModuleNotFoundError: No module named 'src'`, da bei einem Skript unter `output/` der Repository-Root nicht automatisch im Importpfad liegt. Kein Multi-Batch-Ziel, keine Kandidaten und keine Renderartefakte wurden geschrieben.
- Schlussfolgerung/nächster Schritt: Reproduzierbarer Wrapperfehler vor Produktivcode und vor Kandidatenexport; der Wrapper erhält ausschließlich den fehlenden Repository-Root im Importpfad und wird erneut gestartet.
## Verifiziert am 2026-08-21 (Materialisierung Fortsetzung: abgeleitete Top-k-Auswahl)

- Fragestellung/Reasoning: Der vorherige Dataset-v2-Exporter wurde durch den PC-Neustart während der Auswahlphase beendet. Der bestehende Batch ist vollständig, aber 87 Paarmanifeste umfassen 6,15 GB JSON; die Auswahlfunktion sortiert dabei alle 1.922.730 Ranking-Einträge erneut. Zur reproduzierbaren Fortsetzung wird nur ein neues, abgeleitetes Auswahlmanifest erzeugt.
- Setup: Quelle `output/batch_variable_v2_strict_20260820_run01`; neuer Zielpfad `output/batch_variable_v2_strict_20260820_selected_top3_run01`; keine Änderung an Produktivcode, Quellbatch oder Audio-/Featureartefakten.
- Befehl/Testumfang: `.venv\\Scripts\\python.exe output/batch_variable_v2_strict_20260820/materialize_topk_selection.py`; pro abgeschlossenem Paar werden anhand der bereits verifizierten monotonen Ranking-Reihenfolge die besten drei Kandidaten je Länge 2/4/6/8 ausgewählt. Quellmanifest- und Paarhashes werden in `selection_provenance.json` gebunden.
- Ergebnis inklusive Fehlern: Lauf gestartet; Ergebnis wird nach Abschluss mit Paaranzahl, Längenzählung und Hashbindung geprüft. Der frühere Exportabbruch durch Neustart wird nicht als fachlicher Datasetfehler gewertet.
- Schlussfolgerung/nächster Schritt: Nach erfolgreicher Auswahl wird der v2-Exporter ausschließlich gegen dieses abgeleitete, kleine Manifest gestartet; der finale Datasetpfad bleibt neu und atomar. Kein Training.
- Verifiziertes Ergebnis des Auswahlruns: 87/87 Paarmanifeste, exakt 261 Kandidaten je Länge (2/4/6/8), 1.044 eindeutige Candidate-IDs, keine `None`-Beatlängen und ausschließlich Merge-v2-Grids mit `fallback_used=false`. Die maschinelle Prüfung jedes reduzierten Paarmanifests ist bestanden.
## Verifiziert am 2026-08-21 (Materialisierung: RoFormer-Cache-Schreibblocker)

- Fragestellung/Reasoning: Der Dataset-v2-Export gegen das kompakte Auswahlmanifest sollte vorhandene passende RoFormer-Stems wiederverwenden und neue v2-Featurecaches schreiben.
- Setup: `.venv\\Scripts\\python.exe output/batch_variable_v2_strict_20260820/export_dataset_v2_selected.py`; neues Datasetziel; `cache_root=output/feature_cache`; `vocal_backend=roformer`; Merge-v2-Analyse.
- Befehl/Testumfang: Exportstart mit 1.044 ausgewählten Kandidaten.
- Ergebnis inklusive Fehlern: Vor dem ersten neuen Featurecache scheiterte der Lauf reproduzierbar mit `PermissionError: [WinError 5]` beim Anlegen von `output\\feature_cache\\model_artifacts\\roformer_vocal_v1\\006a6624a23b6193`. Es wurde kein Datasetziel finalisiert. Die bestehende Cachehierarchie wurde nicht verändert; der Fehler liegt am Schreibzugriff auf den bestehenden Cache-Root, nicht an fehlender RoFormer-Provenienz.
- Schlussfolgerung/nächster Schritt: Der Export wird nicht mit erzwungenem Überschreiben oder ACL-Änderung fortgesetzt. Ein neuer eindeutiger v2-Cache-Root wird angelegt; passende vorhandene RoFormer-Artefakte werden read-only anhand ihrer SHA/Modellprovenienz in den neuen Root übernommen, danach schreibt der Export nur neue Cache-IDs und Datasetartefakte.
## Verifiziert am 2026-08-21 (Materialisierung: RoFormer-Prefill partiell)

- Fragestellung/Reasoning: Die passenden bestehenden RoFormer-Stems sollten read-only in den neuen v2-Cache-Root übernommen werden, damit der Export weder den geschützten alten Root noch Demucs-Artefakte verwendet.
- Setup: Quelle `output/feature_cache/model_artifacts/roformer_vocal_v1`; neuer Root `output/feature_cache_variable_v2_roformer_20260821`; 87 Strict-Accepted-Audio-SHAs; Modell `roformer-model-bs-roformer-sw-by-jarredou`.
- Befehl/Testumfang: `.venv\\Scripts\\python.exe output/batch_variable_v2_strict_20260820/prefill_roformer_cache_v2.py`; Manifest-/Datenhashprüfung je kopiertem Stem.
- Ergebnis inklusive Fehlern: 44 passende RoFormer-Artefakte wurden in den neuen Root kopiert und provenancegebunden. 43 Strict-Accepted-SHAs haben keinen passenden bestehenden RoFormer-Stem; der Lauf brach ehrlich mit `RuntimeError: Missing matching RoFormer stems for 43 strict tracks` ab. Keine Demucs-Artefakte wurden akzeptiert oder verändert.
- Schlussfolgerung/nächster Schritt: Der partielle Prefill ist verwendbar; für die 43 fehlenden Tracks muss der neue Root die vertragsgemäße RoFormer-Extraktion mit neuer Cacheidentität ausführen. Der alte Cache bleibt unverändert.
## Verifiziert am 2026-08-21 (Materialisierung: RoFormer-Extraktionsstart)

- Fragestellung/Reasoning: Die 43 fehlenden RoFormer-Stems sollten im neuen v2-Cache-Root erzeugt werden; die 44 Prefill-Hits sollten unverändert als Cache-Hits dienen.
- Setup: neuer Cache-Root `output/feature_cache_variable_v2_roformer_20260821`, 44 Prefill-Hits, Datasetziel `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`, Modell `roformer-model-bs-roformer-sw-by-jarredou`.
- Befehl/Testumfang: `.venv\\Scripts\\python.exe -u output/batch_variable_v2_strict_20260820/export_dataset_v2_roformer_prefilled.py`.
- Ergebnis inklusive Fehlern: Der Export erreichte die RoFormer-Assetvorbereitung, scheiterte aber vor der Extraktion mit `UnicodeEncodeError` beim bs_roformer-Downloadbanner (`cp1252` kann `📦` nicht ausgeben). Kein Dataset wurde finalisiert; der neue Cache-Root wurde nicht als Demucs-Root verwendet.
- Schlussfolgerung/nächster Schritt: Der Fehler ist eine reproduzierbare Konsolen-Encoding-Blockade, kein fehlender RoFormer-Vertrag. Der gleiche Lauf wird mit explizitem UTF-8-IO fortgesetzt; keine Qualitätsfilter werden gelockert.
## Verifiziert am 2026-08-21 (Materialisierung Phase 4: Dataset v2 abgeschlossen)

- Fragestellung/Reasoning: Der reale variable Dataset-v2-Export sollte nach der PC-Unterbrechung mit einem reproduzierbar verkleinerten Top-k-Auswahlmanifest, strikt getrennten Audio-SHA-Splits und RoFormer-Provenienz abgeschlossen werden.
- Setup: Auswahlmanifest `output/batch_variable_v2_strict_20260820_selected_top3_run01`; 87 Paarmanifeste; je Paar und Länge top-k=3; Analyse-Root `output/pre_analysis_variable_v2_strict_20260820_retry01`; neuer RoFormer-Cache-Root `output/feature_cache_variable_v2_roformer_20260821`; Dataset `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`; kein Training und kein ML-Runner.
- Befehl/Testumfang: `.venv\\Scripts\\python.exe -u output/batch_variable_v2_strict_20260820/export_dataset_v2_roformer_prefilled.py` mit UTF-8-IO; danach `.venv\\Scripts\\python.exe output/batch_variable_v2_strict_20260820/verify_real_dataset_v2.py`.
- Ergebnis inklusive Fehlern: RoFormer-Checkpoint wurde einmalig in den neuen Cache-Root geladen; 44 passende bestehende RoFormer-Stems wurden wiederverwendet, weitere benötigte Stems wurden mit neuer Cacheidentität erzeugt. Dataset `dataset_id=2a9679f687c50696692b`, Format/Feature Protocol 2. Verifizierte Matrix je Länge: 2 Takte T=16: train=105, validation=12, test=21; 4 Takte T=32: 105/12/21; 6 Takte T=48: 105/12/21; 8 Takte T=64: 105/12/21. Insgesamt 552 eindeutige Example-IDs und 53 tatsächlich in exportierten Beispielen verwendete Tracks. Die gemeinsame Split-Autorität enthält alle 87 ausgewählten Track-SHAs: train=61, validation=13, test=13; Audio-SHA-Isolation und Längenkonstanz bestanden.
- Verifikation: `DATASET_V2_VALIDATION_OK`; alle NPZ-/JSONL-Dateihashes stimmen mit dem Datasetmanifest überein; alle Werte sind endlich; `transition_position` entspricht je T exakt `(i+0.5)/T`; keine None-/inkonsistenten Beatlängen; alle Quellen-/Zielgrids sind `auftakt_matched_to_librosa_partial_v2` mit `fallback_used=false`; 54 verwendete Featurecache-Manifeste und deren RoFormer-Stemdateien wurden auf Manifest-/Artefakthash geprüft; keine Demucs-Provenienz.
- Schlussfolgerung/nächster Schritt: Dataset v2 ist vollständig und reproduzierbar verifiziert. Es wird kein Training und kein Prompt 8 gestartet, solange dies nicht separat beauftragt wird. Der lange, durch Neustart abgebrochene Exportlauf gegen 6,15 GB Rohmanifeste bleibt als abgebrochener Lauf dokumentiert; die abgeleitete Auswahl ist hashgebunden und ändert die Rohbatchartefakte nicht.

## Verifiziert am 2026-08-21 (frisches End-to-End-Review Variable-Length)

- **Fragestellung/Reasoning:** Die gesamte additive Variable-Length-Kette sollte
  nach der realen Datasetmaterialisierung noch einmal von Code und Protokollen
  bis zu Loader, Training, Inferenz, Rendering, Checkpoint/Resume und
  Längenmetriken geprüft werden. Der Testsplit musste vollständig außerhalb
  von Training und Modellentwicklung bleiben; eine lange Trainingskampagne war
  nicht erlaubt.
- **Setup:** Repository mit den vorbestehenden Nutzeränderungen; Pflichtlektüre
  von `AGENTS.md`, `docs/STATUS.md`,
  `docs/Projekt-Gesamtuebersicht.md`, `.agents/AGENT.md`,
  `.agents/multi-session-project-discipline.skill` und den relevanten
  Candidate-, Analysis-, Feature-, Dataset-, Rendering-, ML-, W&B- und
  Variable-Length-Protokollen. Python ausschließlich über
  `.venv\Scripts\python.exe`; keine Commits; Audio-, Dataset-, Cache- und
  bestehende Runartefakte wurden nicht überschrieben oder gelöscht.

### Code- und gezielte Regressionstests

- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_features.py tests/test_variable_ml.py tests/test_variable_tcn_bilstm.py tests/test_partial_merge.py tests/test_candidates.py tests/test_variable_dataset.py -k "not export_writes_all_lengths_and_reuses_one_split_map and not documents_empty_length_shards"`
- **Ergebnis inklusive Fehlern:** `47 passed, 2 deselected in 25.58s`.
  Die zwei ausgelassenen synthetischen Tests erzeugen beziehungsweise prüfen
  Test-Shards; sie wurden in diesem Review nicht ausgeführt.
- **Schlussfolgerung/nächster Schritt:** Variable Geometrie, Features,
  Objective-v5, MLP-/TCN/BiLSTM-Kurven, Candidate-v2, Partial-Merge und der
  testsplitfreie ausgewählte Dataset-Umfang waren gezielt grün.

- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_feature_control_model.py tests/test_vocal_control_model.py tests/test_ml_data.py tests/test_ml_training_runner.py`
- **Ergebnis inklusive Fehlern:** `15 passed in 16.43s`; zwei erwartete CUDA-
  Determinismuswarnungen aus dem bestehenden v1-Runner.
- **Schlussfolgerung/nächster Schritt:** Die bisherige Vier-Takt-MLP-, Vocal-,
  Loader- und v1-Runner-Suite bleibt rückwärtskompatibel.

- **Befehl/Testumfang:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_multi_batch_render.py tests/test_batch_render.py tests/test_candidates.py`
- **Ergebnis inklusive Fehlern:** `30 passed in 6.99s`; zwei bekannte
  `aifc`-/`sunau`-Deprecationwarnungen aus dem bestehenden Audio-Regressionstest.
- **Schlussfolgerung/nächster Schritt:** Bestehende Batch-/Candidate-/Rendering-
  Pfade und die additive Mehrlängen-Konfiguration bleiben gemeinsam testbar.

### Reale Train-/Validation-Loaderprüfung

- **Befehl/Testumfang:** Erste read-only Python-Sonde mit
  `VariableFeatureDatasetCollection(..., lengths=(2,4,6,8))` gegen
  `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`.
- **Ergebnis inklusive Fehlern:** Die Sonde scheiterte mit einem
  Prüfskriptfehler `TypeError: ... unexpected keyword argument 'lengths'`; der
  Loader hatte korrekt nur das Datasetmanifest gelesen, kein Test-Shard wurde
  geöffnet.
- **Schlussfolgerung/nächster Schritt:** API-Aufruf auf den tatsächlichen
  Parameter `transition_length_bars` korrigiert; kein Produktionsfehler.

- **Befehl/Testumfang:** Korrigierte `.venv\Scripts\python.exe -B -c`-Sonde mit
  `VariableFeatureDataset` und `VariableFeatureDatasetCollection` für nur
  `train` und `validation`, alle Längen, NPZ-/JSONL-Loader, Finite-Prüfung,
  `VariableLengthBatchSampler` und Collation.
- **Ergebnis inklusive Fehlern:** Train `420` Beispiele (`105` je Länge),
  Validation `48` (`12` je Länge); Shapes T=16/32/48/64, `float32`, finite,
  `length_condition` 0,25/0,5/0,75/1,0 und alle Batches homogen. Kein
  Testsplit geladen.
- **Schlussfolgerung/nächster Schritt:** Der reale v2-Loader ist für den
  vorgesehenen Train-/Validation-Einstieg funktionsfähig.

### Reproduzierte v2-Fehler und Hardening

- **Befehl/Testumfang:** Read-only Negativsonden mit `.venv\Scripts\python.exe
  -B -c` für manipulierte Split-SHA, `VariableCandidateGenerationConfig`
  mit `2.5` und gleichartigen 3/4-Grids.
- **Ergebnis inklusive Fehlern:** Eine falsche deklarierte Split-Mapping-SHA
  wurde zunächst akzeptiert; `2.5` wurde zunächst zu `2` gecastet; ein
  gleichartiges 3/4-Raster erzeugte zunächst einen v2-Kandidaten. Das gemischte
  4/4-gegen-3/4-Raster wurde bereits korrekt wegen inkompatibler Beatanzahl
  abgelehnt.
- **Schlussfolgerung/nächster Schritt:** Reproduzierbare Fehler im neuen Pfad
  wurden additiv behoben: deklarierte Split-SHA wird jetzt geprüft, Längen
  werden strikt validiert, v2-Candidates verlangen 4/4, und der Renderer prüft
  L/Beat vor Audio-I/O.

- **Befehl/Testumfang:** Erster Hardeningtest nach der Änderung:
  `.venv\Scripts\python.exe -m pytest -q tests/test_variable_contract_hardening.py tests/test_candidates.py tests/test_variable_features.py tests/test_variable_tcn_bilstm.py -k "not test_variable_generation_keeps_short_candidates_when_eight_bars_are_unavailable"`.
- **Ergebnis inklusive Fehlern:** Collectionfehler wegen eines von der ersten
  Hardeningfassung eingeführten zirkulären Imports über den `src.features`-
  Package-Initializer. Kein Audio-/Datasetartefakt betroffen.
- **Schlussfolgerung/nächster Schritt:** Der Candidate-Check wurde lokal ohne
  Package-Querimport umgesetzt.

- **Befehl/Testumfang:** Derselbe Hardeningumfang nach der Korrektur.
- **Ergebnis inklusive Fehlern:** `30 passed, 1 deselected in 11.81s`.
  Danach isoliert: `.venv\Scripts\python.exe -m pytest -q
  tests/test_variable_contract_hardening.py` → `4 passed in 3.28s`.
- **Schlussfolgerung/nächster Schritt:** Split-Hash-, Integer-, Meter- und
  Renderer-Geometrie-Härtung ist regressionsgeprüft; v1 bleibt unberührt.

### Reales Rendering und Dauerprüfung

- **Befehl/Testumfang:** Erster v2-Renderlauf mit je dem ersten Validation-
  Beispiel, `PreAnalysis`-v2-Cache, Equal-Power, 44.100 Hz und neuem
  Outputpfad `output/review_variable_v2_e2e_20260821_run01`.
- **Ergebnis inklusive Fehlern:** Der Lauf wurde beim ersten Beispiel ehrlich
  mit `ValueError: ... different sample lengths: source=135680,
  target=136704` abgelehnt; es gab keine WAV-Ausgabe. Das ist ein neuer
  Grid-/Dauerbefund, kein Librosa-/Numba-Problem und keine stille Kürzung.

- **Befehl/Testumfang:** Read-only Sonde über die 12 realen Validation-
  Beispiele je Länge gegen die vorhandenen v2-Analysis-Caches, um Kandidaten
  mit samplegleichem Source-/Target-Fenster zu bestimmen.
- **Ergebnis inklusive Fehlern:** Samplegleiche Kandidaten verfügbar: 2 Takte
  `2/12`, 4 Takte `3/12`, 6 Takte `5/12`, 8 Takte `2/12`; die übrigen werden
  durch den strikten v2-Renderer abgelehnt.
- **Schlussfolgerung/nächster Schritt:** Für die E2E-Abnahme wird je Länge
  genau ein samplegleicher Validation-Kandidat verwendet; die Ablehnung der
  übrigen Fälle bleibt dokumentiert.

- **Befehl/Testumfang:** Equal-Power-Renderings in neuen Pfaden
  `...run02`, `...run03` und abschließend `...run04`; WAV-Export als Float32,
  `soundfile.info`, endliche Samples, Transition-Grenzen und exakte
  Source-/Target-Samplegleichheit.
- **Ergebnis inklusive Fehlern:** `run02` renderte 2/4/6 Takte, scheiterte
  danach nur wegen zu kurzer 12-Sekunden-Previewgrenze beim 8-Takt-Beispiel;
  die drei WAVs blieben erhalten. `run03` renderte alle vier WAVs, hatte aber
  einen Fehler im Hilfsreport (`sequence_length = L*16` statt `L*8`). Der
  kanonische Lauf `output/review_variable_v2_e2e_20260821_run04` bestand für
  alle vier Längen: T=16/32/48/64, 44.100 Hz, Stereo, finite Samples und
  Bridge-Samples `136704/268288/401920/546304`; WAV-Framezahl und Sample-Rate
  stimmen mit dem Renderergebnis überein.
- **Schlussfolgerung/nächster Schritt:** Vier neue reale Validation-WAVs sind
  technisch gültig. Der v2-Pfad kürzt ungleiche Fenster nicht und behandelt
  den BPM-Idealwert getrennt von der tatsächlich verifizierten Grid-
  Samplegeometrie.

### Training, Checkpoint/Resume, Inferenz und Metriken

- **Befehl/Testumfang:** `.venv\Scripts\python.exe -B -c`-Smoke gegen die realen
  Train-/Validation-Feature-Shards, ein Beispiel je Länge, deterministische
  synthetische explizite Waveforms, TCN/BiLSTM v2, CPU, W&B disabled,
  `max_epochs=1`, anschließend Resume mit `max_epochs=2`. Kein Testsplit.
- **Ergebnis inklusive Fehlern:** Training Epoch 1: Gesamt-Train-Loss
  `0,3691570163`, Validation `0,2956906296`; Resume Epoch 2: Train
  `0,3675513119`, Validation `0,2944503240`. Checkpoint wurde vor und nach
  Resume mit Manifest-SHA, Contract und `weights_only=True` sicher geladen.
  Das erste Hilfsskript scheiterte erst nach erfolgreichem Resume beim Lesen
  von `manifest['history']` (`KeyError`); die History liegt korrekt in
  `history.json`.
- **Schlussfolgerung/nächster Schritt:** Runner, Objective, atomare
  Checkpoints, Resume und Gesamt-/Per-L-Metriken funktionieren. Der korrigierte
  Report `output/review_variable_v2_training_smoke_20260821_run01/e2e_review_report.json`
  bestätigt `test_split_loaded=false`.

- **Befehl/Testumfang:** Korrigierte read-only Report-/Inferenzsonde mit sicherem
  Latest-Load, je einem Validationbeispiel für 2/4/6/8 Takte und Prüfung von
  `controls` `(T,10)`, Endpunkten, Monotonie, Wertebereich und Finiteheit.
- **Ergebnis inklusive Fehlern:** Alle vier Inferenzfälle bestanden mit
  T=16/32/48/64; alle Controls und Gains waren finite, die drei
  Positionskurven je Beispiel waren streng monoton mit Endpunkten 0/1.
- **Schlussfolgerung/nächster Schritt:** Technischer E2E-Smoke ist bestanden;
  dies ist kein Hörqualitätsnachweis und keine lange Trainingskampagne.

### Gesamtsuite und Altprobleme

- **Befehl/Testumfang:** `.venv\Scripts\python.exe -m pytest -q`, innerhalb
  einer 120-Sekunden-Timeout-Sonde, ohne Testsplitzugriff im neuen Runner.
- **Ergebnis inklusive Fehlern:** `199 passed, 4 warnings in 46.34s`. Die
  Warnungen sind zwei `aifc`-/`sunau`-Deprecations und zwei bekannte CUDA-
  Determinismuswarnungen; die Suite hing in diesem Lauf nicht.
- **Bekannte alte Probleme, getrennt:** Historische Librosa-/Numba-JIT-
  Initialisierungsprobleme sowie der bekannte `librosa.resample`-/Numba-Fehler
  bleiben als Altprobleme dokumentiert. Sie traten in diesem bounded Lauf nicht
  auf und wurden nicht dem neuen Variable-Length-Pfad zugerechnet.
- **Schlussfolgerung/nächster Schritt:** Der frische aktuelle Testlauf ist
  vollständig grün; daraus folgt nicht, dass die bekannten historischen
  Librosa-/Numba-Probleme behoben sind. `git diff --check` war ohne
  Whitespacefehler. Es wurde kein Commit erstellt. Nächster sinnvoller Schritt
  ist ein versionierter realer v2-Waveform-Cache samt eigenem CLI-Einstieg;
  erst danach darf der vollständige CUDA-Befehl ausgeführt werden.

## Verifiziert am 2026-08-21 (Alignment-Gate für Waveform-Cache-v2 — blockiert)

- **Fragestellung und Reasoning:** Vor einer neuen Waveform-Cache-, Loader-
  und CLI-Implementierung musste ausschließlich auf Train und Validation
  geprüft werden, ob Source-Mix, tempoangepasster Target-Mix sowie die beiden
  RoFormer-Vocal-Bridges auf eine wissenschaftlich vertretbare kanonische
  Samplelänge gebracht werden können. Die Regel darf keine stille
  `min(source_length, target_length)`-Kürzung enthalten; die kanonische Länge
  muss aus `transition_length_beats`, BPM und der Trainings-Samplerate
  reproduzierbar sein. Größere lokale Grid-Abweichungen müssen abgelehnt
  werden, statt sie zu normalisieren.
- **Eingaben/Setup:** Ausschließlich
  `output/datasets/variable_v2_strict_20260820_selected_roformer_run01/metadata/*/(train|validation).jsonl`
  und die darin referenzierten RoFormer-Featurecaches unter
  `output/feature_cache_variable_v2_roformer_20260821`. Gelesen wurden 420
  Train- und 48 Validation-Beispiele, also 468 Beispiele je 117 für 2, 4, 6
  und 8 Takte. Der Test-Shard, Test-Metadaten, Test-Features und Test-Audio
  wurden nicht geöffnet. Die geplante Trainings-Samplerate war 11.025 Hz;
  die vorhandenen Feature-/Grid-Caches liegen bei 44.100 Hz. Die Vocalprüfung
  umfasste 46 eindeutige RoFormer-Stem-Manifeste mit Backend `roformer`,
  Modellkennung `roformer-model-bs-roformer-sw-by-jarredou` und vorhandener
  Stem-Provenienz.
- **Testumfang bzw. Befehl:** Read-only-Python-Sonden mit
  `.venv\Scripts\python.exe -B -c ...` luden pro Train-/Validation-Metadatei
  nur `bin_boundaries`, Cachemanifeste und die referenzierten RoFormer-
  Stemmanifeste. Für jede Länge wurden die vollständigen Source-Postroll- und
  Target-Preroll-Fenster anhand von Cue, `T=16/32/48/64` und den gespeicherten
  Gridgrenzen vermessen; zusätzlich wurde die erwartete tempoangepasste
  Vocal-Gesamtlänge gegen die aligned Audio-Gesamtlänge geprüft.
- **Ergebnis — Bridge-Längen bei 44.100 Hz:**

  | Länge | T | Source-Bereich | Target-Bereich | Differenzbereich Target−Source | exakt gleich | `|Diff|≤512` |
  |---:|---:|---:|---:|---:|---:|---:|
  | 2 Takte | 16 | 126.976–142.848 | 119.808–139.776 | −12.288…+8.704 | 15/117 | 37/117 |
  | 4 Takte | 32 | 257.536–282.112 | 256.000–276.480 | −8.192…+10.752 | 22/117 | 52/117 |
  | 6 Takte | 48 | 388.608–423.936 | 388.096–417.792 | −9.216…+12.288 | 24/117 | 44/117 |
  | 8 Takte | 64 | 520.704–565.248 | 520.704–553.472 | −15.360…+14.848 | 24/117 | 51/117 |

  Bei 11.025 Hz entsprechen die maximalen Differenzen −3.840…+3.712
  Samples. Über alle Längen waren nur 85/468 Bridge-Paare exakt gleich;
  383/468 wiesen bereits bei einem strengen Rundungskriterium von mehr als
  2 Samples auf 44,1 kHz eine größere Abweichung auf. Die Verteilung ist
  damit nicht durch eine einzelne Ausreißerdatei erklärbar.
- **Vocalbefund:** Für alle 468 geprüften Beispiele war die erwartete,
  BPM-angepasste RoFormer-Stem-Gesamtlänge identisch zur aligned Audio-
  Gesamtlänge (`0` Differenz in allen Fällen). Die vier Vocal-Bridge-Slices
  würden bei identischer Transformation dieselben Längen wie ihre Mix-
  Gegenstücke haben; sie lösen die Source/Target-Grid-Diskrepanz nicht.
- **Deterministische Alignment-Entscheidung:** Der einzig zulässige Vertrag
  für die nächste Implementierungsstufe ist derzeit ein Reject-Vertrag:
  `N_canonical = round(transition_length_beats * 60 / source_bpm *
  training_sample_rate)`, mit expliziter symmetrischer Korrektur nur für
  echte Sample-Rundung und mit identischer Korrektur für Mix und Vocal. Jede
  darüber hinausgehende Source/Target-Abweichung muss mit Example-ID,
  Längenset, Grid-Hashes und gemessenen Roh-/kanonischen Längen abgelehnt
  werden. Eine produktive Cropping-, Padding- oder Resampling-Regel für die
  beobachteten Abweichungen ist wissenschaftlich nicht begründbar und wurde
  daher nicht eingebaut.
- **Fehler/Blockade:** Der reale Waveform-Cache
  `output/ml_cache/variable_bridge_waveform_v2` wurde nicht erzeugt
  (Verzeichnis war nicht vorhanden). Es wurden kein neuer Cachevertrag, kein
  Materialisierungs-CLI, kein CUDA-Training und kein Resume ausgeführt. Die
  explizite Stopbedingung der Aufgabe ist wegen der großen, systematischen
  lokalen Grid-Abweichungen erfüllt.
- **Schlussfolgerung und nächster Schritt:** Vor der Freigabe des neuen
  Produktionspfads muss die Daten-/Grid-Autorität geklärt werden: entweder
  müssen Kandidaten bereits auf ein gemeinsames, samplegleiches
  Source/Target-Beatfenster mit ausreichender Qualitätsgarantie beschränkt
  werden, oder es braucht eine fachlich begründete, separat versionierte
  Zeitnormalisierung. Erst danach sind Cachevertrag, Cache-Hits,
  Waveform-Shape-Tests, vollständige Suite und der reale CUDA-Smoke-Test
  sinnvoll. Bestehende v1-Caches und der Testsplit blieben unangetastet.
- **Dokumentationsintegritätscheck:** Anschließend wurde
  `git diff --check` gegen den vorhandenen Nutzerarbeitsbaum ausgeführt; der
  Check meldete keine Whitespacefehler. Es wurde kein Commit erstellt.

## Verifiziert am 2026-08-21 (Alignment-/Cache-v2-Synthetikregression)

- **Fragestellung und Reasoning:** Nach der additiven Implementierung des
  Vertrags `local_grid_target_to_source_v1` musste zuerst ausgeschlossen
  werden, dass die bestehende variable Dataset-/ML-Schicht durch die neuen
  Cache- und Runner-Imports regressiert. Dieser Lauf prüfte ausschließlich
  synthetische v2-Fixtures; ein vollständiger Lauf und reale Audioartefakte
  waren für diese Stufe bewusst noch nicht Teil des Setups.
- **Eingaben/Setup:** Repository-Arbeitsbaum am 2026-08-21, ausschließlich
  `.venv\Scripts\python.exe`, die bestehenden synthetischen Fixtures der
  Variable-Length-Tests; kein Testsplit des realen Datensatzes.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests/test_variable_contract_hardening.py tests/test_variable_dataset.py tests/test_variable_ml.py tests/test_variable_tcn_bilstm.py`
- **Ergebnis inklusive Fehlern:** `23 passed in 11.62s`; keine Testfehler und
  keine Blockade.
- **Schlussfolgerung und nächster Schritt:** Die bestehenden v2-Verträge,
  homogenen Batchsampler, variable TCN/BiLSTM-Geometrien und Resume-
  Regressionen bleiben grün. Als nächstes folgen eigene Cache-Vertragstests
  einschließlich Korruption, Provenienz-Mismatch und grenzenerhaltender
  Rundungskorrektur sowie ein kleiner realer Train-/Validation-Cache.

## Verifiziert am 2026-08-21 (Waveform-Cache-v2-Vertragstests)

- **Fragestellung und Reasoning:** Der neue Alignmentkern musste die vier
  Längen, gemeinsame Mix-/Vocal-Transformation, exakte Shapes,
  grenzenerhaltende Korrekturen, Rejects bei großen Restfehlern und die
  Unveränderlichkeit des Caches nachweisen, bevor reale Audiofenster geöffnet
  werden.
- **Eingaben/Setup:** Ausschließlich synthetische In-Memory-Waveforms und
  temporäre Cacheverzeichnisse; `.venv\Scripts\python.exe`; kein realer
  Datensatz und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests/test_variable_waveform_cache.py`
- **Ergebnis inklusive Fehlern:** `10 passed in 25.88s`; Cache-Hit/Miss,
  Payloadkorruption, Root-Provenienz-Mismatch, atomare Veröffentlichung,
  vier Längen, CLI-Parsing und Alignment-Rejects bestanden.
- **Schlussfolgerung und nächster Schritt:** Der synthetische Vertrag ist
  isoliert prüfbar. Die nächste Verifikation ist ein Read-only-Inspektionslauf
  über ausschließlich Train/Validation, gefolgt von einem kleinen realen
  Cache mit je einem Beispiel pro Länge und Split.

## Verifiziert am 2026-08-21 (kleiner realer Waveform-Cache und Hörproben)

- **Fragestellung und Reasoning:** Die erste reale Freigabe sollte zeigen,
  dass der lokale Grid-Vertrag nicht nur synthetisch, sondern mit den
  vorhandenen RoFormer-Featurecaches und Audio-SHAs für alle vier Längen
  materialisierbar ist. Ein initialer Lauf ohne Kontext wurde absichtlich
  nicht akzeptiert: FFmpeg/Rubber-Band lieferte bei zwei Beispielen Rohreste
  von `-3.640` beziehungsweise `-3.423` Samples und wurde daher korrekt
  abgelehnt. Eine Train-Window-Sonde mit 0/1/2/4 Sekunden Guard-Kontext
  zeigte, dass die transformierten gespeicherten Grenzen im Kontextoutput
  exakt die gewünschte lokale Länge abdecken; daraus wurde der additive
  Kontextpfad abgeleitet.
- **Eingaben/Setup:** Ausschließlich
  `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`, die
  referenzierten Train-/Validation-Metadaten, reale Mix-Audios und die
  RoFormer-Stempayloads aus
  `output/feature_cache_variable_v2_roformer_20260821`; 11.025-Hz-Training,
  44.100-Hz-Rendergitter, Toleranz 2 Samples; Testsplit nicht geöffnet.
- **Testumfang bzw. Befehle:** Kleine Materialisierung mit
  `.venv\Scripts\python.exe -u -m src.ml cache-variable-waveforms ... --transition-bars 2 4 6 8 --limit 1 --training-sample-rate 11025 --render-sample-rate 44100 --rounding-tolerance-samples 2`; danach erneuter Cache-Hit-Lauf. Die Guard-Kontext-Sonde verwendete nur ein Train-Beispiel und
  FFmpeg/Rubber-Band; anschließend wurden vier Equal-Power-Technik-Hörproben
  unter `output/ml_cache/variable_bridge_waveform_v2/technical_listen/`
  erzeugt.
- **Ergebnis inklusive Fehlern:** Der finale kleine Bericht meldet 8/8
  Cache-Hits (Train 1/1 und Validation 1/1 je 2/4/6/8), 0 Rejects und 0
  temporäre Verzeichnisse. Alle vier Waveforms je Eintrag sind finite
  Float32-Stereoarrays in exakt gleicher Form; die Hörproben haben bei 11.025
  Hz exakt `N=32384/65536/99456/132480` Samples für 2/4/6/8 Takte. Die
  technische Korrekturstatistik ist für diese acht Einträge überall 0 Samples;
  lokale Ratios liegen je nach Länge zwischen `0,9806201550` und
  `1,0038759690`, globale BPM-Ratio jeweils `1,0`. Die sechs Einträge ohne
  Guard-Kontext und die zwei mit Guard-Kontext sind im jeweiligen Manifest
  provenancegebunden; keine Mix-/Vocal-Shape-Abweichung wurde gefunden.
- **Schlussfolgerung und nächster Schritt:** Der neue Vertrag ist auf realen
  Beispielen für alle vier Längen freigegeben. Vor dem CUDA-Test muss der
  vollständige Train-/Validation-Cache materialisiert und auf 468 Einträge
  sowie Ausschlüsse/Ratioverteilung geprüft werden.

## Verifiziert am 2026-08-21 (vollständiger realer Waveform-Cache-Audit)

- **Fragestellung und Reasoning:** Nach dem langen Real-Lauf musste unabhängig
  vom Materialisierungszähler geprüft werden, dass jedes Train-/Validation-
  Beispiel genau einen v2-Entry besitzt und dass Payload-SHA, Array-SHA,
  Float32-Dtype, Finite-Werte und vierfache Shape-Gleichheit tatsächlich
  stimmen. Der Audit las ausschließlich die 420 Train- und 48
  Validation-Metadaten; Testdateien wurden nicht geöffnet.
- **Eingaben/Setup:** Dataset
  `output/datasets/variable_v2_strict_20260820_selected_roformer_run01`,
  Cache `output/ml_cache/variable_bridge_waveform_v2`, exakt der verifizierte
  Root-Manifest-SHA `b86d0c46329c653a6984d9a3eed59b1f763165bee308b9c67925cf8727bed5cd`.
- **Testumfang bzw. Befehle:** Vollmaterialisierung mit
  `.venv\Scripts\python.exe -u -m src.ml cache-variable-waveforms ...` ohne
  `--limit`; danach ein `.venv\Scripts\python.exe -B -c ...`-Audit über die
  Train-/Validation-JSONL und alle 468 Cachepayloads.
- **Ergebnis inklusive Fehlern:** `468/468` geprüft, davon Train
  `105/105/105/105` und Validation `12/12/12/12` für 2/4/6/8 Takte;
  Materialisierungsbericht: 468 angefordert, 0 Rejects. `bad_count=0`, alle
  vier Arrays je Entry exakt gleich geformt, Float32 und finite; 377 Entries
  nutzten Guard-Kontext, 91 konnten direkt gestretcht werden. Die Ratio-
  Bereiche stimmen mit dem Bericht überein: 2 Takte `0,935849…–1,102564…`,
  4 `0,96–1,032`, 6 `0,969349…–1,023747…`, 8 `0,973148…–1,027933…`.
- **Schlussfolgerung und nächster Schritt:** Der vollständige reale
  Train-/Validation-Cache ist technisch freigegeben. Jetzt folgt der echte
  CUDA-Smoke-Lauf mit einer Epoche und anschließendem Resume auf zwei
  Epochen; ein vollständiger Trainingslauf bleibt ausgeschlossen.

## Verifiziert am 2026-08-21 (CUDA-Smoke, Resume und Gesamtregression)

- **Fragestellung und Reasoning:** Die reale Freigabe musste nun den
  tatsächlich verwendeten CUDA-Pfad, Resume-Verhalten, finite Losses und
  Gradienten, SHA-geprüfte Checkpoints, längenstratifizierte Metriken und die
  vier Kontrollgeometrien nachweisen. Danach sollte die vollständige Suite
  sicherstellen, dass die additive Pipeline keine v1-Regression erzeugt.
- **Eingaben/Setup:** Reale Dataset-2-Features sowie ausschließlich die 468
  zuvor veröffentlichten Train-/Validation-Cacheentries; Run
  `output/training_runs/variable_tcn_bilstm_waveform_v2_cuda_smoke_20260821`;
  `cuda:0`, Seed `20260821`, Sample-Rate 11.025 Hz, Batchgröße 4, W&B
  disabled. Der Runner instanziiert nur Train und Validation; der Testsplit
  wurde nicht geöffnet.
- **Testumfang bzw. Befehle:** Erster Lauf:
  `.venv\Scripts\python.exe -u -m src.ml train-variable-tcn-bilstm ... --device cuda:0 --max-epochs 1 --batch-size 4 --wandb-mode disabled`; anschließend Resume mit `--max-epochs 2 --resume`. Danach CUDA-/Checkpoint-/Metrik-Sonde mit `.venv\Scripts\python.exe -u -B -c ...` und vollständige Suite mit `.venv\Scripts\python.exe -B -m pytest -q`.
- **Ergebnis inklusive Fehlern:** Epoch 1 Train/Validation `0,310062/0,260667`,
  Epoch 2 `0,303663/0,265043`; beide CLI-Läufe meldeten jeweils `cache_hits=468`.
  CUDA war tatsächlich verfügbar und aktiv: Gerät 0, `NVIDIA GeForce RTX 5070 Ti`.
  Checkpoint-SHAs für `latest.pt` und `best.pt` stimmten, historische Losses
  und Probe-Losses waren finite, alle Probegradienten finite. Controls waren
  für 2/4/6/8 Takte exakt `(1,16,10)`, `(1,32,10)`, `(1,48,10)`, `(1,64,10)`;
  per-Length-Validation-Metriken lagen für alle vier Längen vor. Die
  Gesamtregression bestand mit `209 passed, 4 warnings in 42.88s`; Warnungen
  waren bekannte `aifc`-/`sunau`-Deprecations und zwei PyTorch-CUDA-
  Determinismuswarnungen, keine Fehler.
- **Schlussfolgerung und nächster Schritt:** Alignment, vollständiger Cache,
  Loader, CUDA-Smoke und Resume sind verifiziert. Der angeforderte
  100-Epochen-Lauf wurde nicht gestartet; nach Status-/Protokollpflege bleibt
  nur die fachliche Nachsichtung der Hörproben und die bewusste Entscheidung,
  ob der empfohlene Volltrainingsbefehl ausgeführt werden soll.

## Verifiziert am 2026-08-21 (abschließende Suite nach Cache-Hit-Härtung)

- **Fragestellung und Reasoning:** Nach dem Real-Lauf wurde die Cache-Hit-
  Validierung zusätzlich verschärft: ein Payload mit falschem Dtype darf nicht
  durch stilles Casten als Float32-Hit gelten; technische Sample-Raten- und
  Shape-Felder müssen ebenfalls mit dem Manifest übereinstimmen. Danach war
  eine letzte Gesamtregression erforderlich.
- **Eingaben/Setup:** Repository-Arbeitsbaum mit unveränderten realen v2-
  Cachepayloads; `.venv\Scripts\python.exe`; keine neue Materialisierung,
  kein Testsplit und kein Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q; git diff --check`
- **Ergebnis inklusive Fehlern:** `209 passed, 4 warnings in 38.06s` und
  `git diff --check` ohne Whitespacefehler. Die vier Warnungen entsprechen
  den bereits dokumentierten aifc-/sunau-Deprecations und PyTorch-CUDA-
  Determinismuswarnungen; keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der finale Code- und
  Dokumentationsstand ist regressionsfrei geprüft. Der empfohlene
  100-Epochen-Befehl ist dokumentiert, aber nicht ausgeführt.

## Testlauf am 2026-08-25 (Cue-Ranker Dataset-/Teacher-Syntaxcheck, blockiert)

- **Fragestellung und Reasoning:** Die neuen additiven Dataset-3-/Teacher-
  Module sollten vor dem synthetischen Testlauf auf Syntaxfehler geprüft
  werden, ohne Audio, Cachematerialisierung, Training oder Testsplit-I/O.
- **Eingaben/Setup:** Nur neue Python-Quell- und Testdateien; Python strikt
  über `.venv\Scripts\python.exe`.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m py_compile src\features\cue_ranker_universe.py src\features\cue_ranker_dataset.py src\ml\cue_ranker_teacher.py ...`.
- **Ergebnis inklusive Fehlern:** Der Check brach vor der Syntaxbewertung mit
  `Permission denied` beim Schreiben einer temporären `.pyc`-Datei unter
  `src\features\__pycache__` ab. Es wurde keine Projektdatei fachlich
  verändert und kein Testsplit geöffnet.
- **Schlussfolgerung und nächster Schritt:** Der folgende Testlauf verwendet
  `-B`, damit keine Bytecode-Artefakte geschrieben werden; der Fehler ist
  eine Ausführungsumgebungsblockade, kein diagnostizierter Codefehler.

## Testlauf am 2026-08-25 (Cue-Ranker Dataset-/Teacher-Synthetik)

- **Fragestellung und Reasoning:** Der neue, von v1/v2 getrennte Pfad musste
  seine nichtzirkulären Gruppen, variablen Ragged-Gruppen, deterministische
  Strata, fehlende Top-K-Beschneidung, Testsplit-Sperre und hashgebundene
  Teacher-Labels ohne reale Musikdaten beweisen.
- **Eingaben/Setup:** Ausschließlich `tmp_path`-JSON/NPZ-Fixtures mit
  künstlichen SHA-256-Werten und einer minimalen Torch-Checkpoint-Attrappe;
  kein echter Pair-Manifest-, Audio-, Waveformcache- oder Testsplitzugriff.
- **Testumfang bzw. Befehle:** Zunächst
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py`
  (6 Fehler wegen eines serialisierten `numpy.float32`-Werts), danach nach
  der gezielten Konvertierung
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py`
  und
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py`.
- **Ergebnis inklusive Fehlern:** Nach dem Fix bestehen die Universumstests
  mit `3 passed in 4.41s` und Teacher-/Datasettests mit `3 passed in 4.49s`.
  Sie belegen deterministische IDs, vollständige 9/3-Candidate-Indizes,
  Ragged-Offsets, Test-Manifest-Nichtzugriff, Samplingwahrscheinlichkeiten,
  Guard-Rejection, isolierte technische Failure, Teacher-Release-SHA und den
  unveränderten Dataset-v2-Formatwert. Der anfängliche Float32-Fehler war
  vollständig lokalisiert und behoben; kein Testsplit wurde geöffnet.
- **Schlussfolgerung und nächster Schritt:** Als Nächstes folgt nur die
  bestehende Candidate-v2-/Dataset-v2-Regression sowie eine CLI-/Diff-Prüfung.

## Testlauf am 2026-08-25 (Cue-Ranker v1/v2-Regressionsauswahl)

- **Fragestellung und Reasoning:** Die neuen Imports und CLI-Unterbefehle
  dürfen die unveränderten Candidate- und Dataset-v2-Pfade nicht verändern.
  Der bekannte pipeline-/Librosa-lastige Rest bleibt außerhalb dieser
  Dataset-/Teacher-Stufe.
- **Eingaben/Setup:** Bestehende rein synthetische Candidate- und
  Variable-Dataset-Tests; `.venv\Scripts\python.exe -B`; keine realen
  Materialisierungen und kein Testsplit.
- **Testumfang bzw. Befehle:** Zunächst
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_candidates.py tests\test_variable_dataset.py`
  (es erschienen acht Fortschrittspunkte, der bekannte länger laufende
  Pipeline-Teil lieferte über die Umgebung keine zusammenfassende Rückgabe).
  Danach gezielt
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_variable_dataset.py`
  sowie
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_candidates.py -k "not pipeline"`.
- **Ergebnis inklusive Fehlern:** Dataset-v2 besteht unverändert mit
  `5 passed in 4.70s`; die nicht-pipelinegebundenen Candidate- inklusive
  v2-Längenprüfungen bestehen mit `12 passed, 2 deselected in 0.31s`.
  Der vorangehende kombinierte Lauf ist wegen der fehlenden Schlussrückgabe
  bewusst nicht als vollständiger Erfolg gewertet. Kein neuer funktionaler
  Fehler wurde beobachtet; der ausgeklammerte Pfad ist die bekannte
  Librosa-/Pipeline-Initialisierung, nicht eine Cue-Ranker-Änderung.
- **Schlussfolgerung und nächster Schritt:** Die kompatiblen v1/v2-Pfade sind
  für diese Änderung gezielt regressionsgeprüft. Vor einem späteren großen
  Lauf bleibt der 1.000-Candidate-Teacher-Pilot mit seinen Budgets separat
  zu planen und freizugeben.

## Testlauf am 2026-08-25 (Cue-Ranker Abschlusscheck)

- **Fragestellung und Reasoning:** Nach Ergänzung des expliziten
  Teacher-Provenienz-Hashes musste die vollständige neue Synthetik erneut
  bestehen; zusätzlich darf der Patch keine Whitespacefehler enthalten.
- **Eingaben/Setup:** Die drei neuen synthetischen Testdateien, keine realen
  Audio-/Feature-/Waveformartefakte; `.venv\Scripts\python.exe -B`.
- **Testumfang bzw. Befehle:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py; git diff --check`.
- **Ergebnis inklusive Fehlern:** `6 passed in 4.31s`; `git diff --check`
  meldete keine Whitespacefehler. Die Ausgabe enthielt nur die bekannte
  Git-Warnung zur künftigen LF→CRLF-Arbeitskopiekonvertierung. Kein Fehler,
  keine reale Materialisierung, kein Training und kein Testsplitzugriff.
- **Schlussfolgerung und nächster Schritt:** Dataset- und Teacher-Score-Stufe
  sind synthetisch verifiziert. Ranking-Modell, Training, Teacher-Pilot und
  Batch-Rendering-Integration bleiben absichtlich unimplementiert.

## Testlauf am 2026-08-25 (Cue-Ranker Hard-Negative-Anker)

- **Fragestellung und Reasoning:** Die Planvorgabe erlaubt kein
  kandidatenweises, modellabhängiges Mining innerhalb der listweisen Gruppe;
  trotzdem müssen schlechte Qualitätsbereiche als nachvollziehbare Hard-
  Negative vertreten sein.
- **Eingaben/Setup:** Unveränderte synthetische Cue-Ranker-Fixtures, kein
  Audio-/Waveform-/Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py; git diff --check`.
- **Ergebnis inklusive Fehlern:** `6 passed in 4.35s`; die Universumsprüfung
  bestätigt jetzt zusätzlich mindestens einen deterministischen Anker aus
  dem untersten Baseline-Quantil. Der Manifestvertrag markiert ihn explizit
  und verbietet weiter candidatespezifisches Nachmining. `git diff --check`
  blieb ohne Whitespacefehler; nur die bekannte LF→CRLF-Gitwarnung erschien.
- **Schlussfolgerung und nächster Schritt:** Sampling deckt gute bis schlechte
  Bereiche inklusive listenintegrer Hard-Negative ab. Es wurde weiterhin
  keine reale Teacher-Materialisierung oder Ranker-Arbeit gestartet.

## Testlauf am 2026-08-25 (Cue-Ranker Release-Pfad-Provenienz)

- **Fragestellung und Reasoning:** Ein gesiegelter Teacher-Release muss seinen
  Checkpoint und sein Runmanifest auch dann eindeutig öffnen können, wenn der
  Release in einem anderen Verzeichnis liegt; daher wurden diese Artefaktpfade
  als absolute Provenienz referenziert und erneut geprüft.
- **Eingaben/Setup:** Nur die synthetischen Teacher-Release- und
  Dataset-3-Fixtures; kein realer Checkpoint, Audio, Cache oder Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py; git diff --check; git status --short`.
- **Ergebnis inklusive Fehlern:** `6 passed in 4.49s`; der Release-SHA wird
  vor Nutzung weiter geprüft und die Artefakte sind nun pfadunabhängig
  nachvollziehbar. Der Diffcheck blieb sauber; Git meldete ausschließlich die
  bekannte LF→CRLF-Warnung. Der Status zeigte nur die vorgesehenen neuen
  Dataset-/Teacher-Dateien sowie die Dokumentationsänderungen.
- **Schlussfolgerung und nächster Schritt:** Die neue Stufe ist synthetisch
  abgeschlossen. Kein Commit wurde erzeugt; reale Pilot-Materialisierung,
  Ranking-Modell und Batch-Integration bleiben außerhalb dieses Auftrags.

## Testlauf am 2026-08-25 (Cue-Ranker Qualitätsstrata und Hard Negatives)

- **Fragestellung und Reasoning:** Die vorherigen kleinen Gruppen wählten
  wegen ihrer Größe vollständig aus. Eine größere reine Speicherfixture musste
  deshalb die echte Teilstichprobe, positive Einschlusswahrscheinlichkeiten,
  Unscored-Stratum und deterministische Hard-Negative-Anker belegen.
- **Eingaben/Setup:** 600 rein synthetische Kandidatenzeilen (560 mit
  Baselinewert, 40 unscored), keine Dateien, kein Audio und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py; git diff --check`.
- **Ergebnis inklusive Fehlern:** `7 passed in 4.26s`. Der neue Test bestätigt
  eine echte Teilstichprobe mit wiederholbar identischer Auswahl,
  `0 < p_inclusion <= 1` für alle gezogenen Zeilen, ein Unscored-Sample und
  mindestens einen Anker aus dem niedrigsten Baseline-Quantil. Keine Fehler;
  der Diffcheck blieb bis auf die bekannte LF→CRLF-Warnung sauber.
- **Schlussfolgerung und nächster Schritt:** Die Sampling-/Hard-Negative-
  Vorgabe ist jetzt auch außerhalb der Vollauswahl synthetisch verifiziert.
  Reale Teacher-Pilotmessung bleibt eine separat freizugebende Folgearbeit.

## Testlauf am 2026-08-25 (Cue-Ranker eingefrorener Eval-Teacher)

- **Fragestellung und Reasoning:** Neben Hashprüfung muss der reale
  Controller-Load aus einem kompatiblen `state_dict` den eval-only-Modus
  tatsächlich setzen; ein Attrappen-Checkpoint wäre dafür nicht ausreichend.
- **Eingaben/Setup:** Synthetischer Checkpoint mit dem unveränderten
  `VariableTCNBiLSTMTransitionControl().state_dict()`, synthetisches
  Runmanifest und keine Waveforms oder Testsplitdateien.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py; git diff --check`.
- **Ergebnis inklusive Fehlern:** `7 passed in 4.79s`. Der Test lädt den
  Checkpoint über den SHA-geprüften Release mit `weights_only=True` und
  bestätigt `model.training is False`. Es gab keine Fehler; der Diffcheck
  blieb sauber abgesehen von der bekannten LF→CRLF-Warnung.
- **Schlussfolgerung und nächster Schritt:** Der eingesetzte Teacher ist
  technisch eingefroren und eval-only. Ein realer, budgetierter Pilot wird
  dadurch nicht vorweggenommen.

## Testlauf am 2026-08-25 (Ranker-Pfad: Regression der Dataset-/Teacher-Stufe)

- **Fragestellung und Reasoning:** Vor den neuen Modell- und Runner-Tests musste
  sichergestellt werden, dass die bereits uncommitteten Format-3-Dataset-,
  Universe- und Teacher-Änderungen sowie die bestehenden Control-Modelle durch
  den additiven Importpfad unverändert testbar bleiben.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Fixtures aus den
  bestehenden Tests, kein Audio und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_variable_ml.py`.
- **Ergebnis inklusive Fehlern:** `14 passed`. Der Lauf enthielt Universe-,
  Dataset-, Teacher- und bestehende Variable-Control-Regressionstests; es gab
  keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Die additive Ranker-Importstufe
  verändert die vorhandene Dataset-/Teacher-/Control-Semantik nicht. Als
  Nächstes werden Shapes, Loss-Maskierung, Permutation sowie atomisches,
  SHA-gesichertes Resume des neuen Rankers geprüft.

## Testlauf am 2026-08-25 (Cue-Ranker Modell, Loss und Resume-Smoke)

- **Fragestellung und Reasoning:** Die Planinvarianten mussten isoliert auf
  synthetischen Eingaben geprüft werden: ein endlicher Skalar je Candidate für
  alle vier T-Längen, geteilte A/B-TCN-Gewichte, maskierte Zeit-Padding- und
  Gruppenbehandlung, Rankinggradient, Kandidaten-Permutation sowie ein
  reproduzierbarer Train-/Validation-Resume-Pfad.
- **Eingaben/Setup:** 11 rein synthetische Tests mit Float-Tensoren `(T,54)`,
  globalen `(16,)`, `length_condition`, `candidate_context_v1`, drei
  Candidates pro Gruppe und CPU; kein Audio und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py`.
- **Ergebnis inklusive Fehlern:** `11 passed in 5.98s`. Alle Scores waren
  `float32` und finite; T=16/32/48/64, masked Padding, Listwise-Gradient,
  Ein-Kandidaten-Gruppe, Kandidaten-Permutation sowie atomare `best.pt`/
  `latest.pt`-Artefakte wurden bestätigt. Ein absichtlich veränderter Latest-
  Checkpoint wurde vor jedem `torch.load` abgewiesen; der echte Resume-Load
  wurde mit `weights_only=True` beobachtet. Keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Modell-/Loss-/Checkpoint-Kern ist
  synthetisch verifiziert. Es folgt der kombinierte Ranker-/Dataset- und
  Control-Regressionslauf sowie ein SHA-/Diff-Audit; eine reale Trainingskampagne
  bleibt ausgeschlossen.

## Testlauf am 2026-08-25 (kombinierter Regressionserstlauf, Korrekturschleife)

- **Fragestellung und Reasoning:** Der additive Ranker sollte gemeinsam mit
  Format-3-Universe/Dataset/Teacher und den bestehenden Feature-/TCN-/Variable-
  Control-Tests ohne Semantikänderung laufen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`, synthetische Ranker- und
  bestehende Control-Fixtures, kein Audio- oder Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_feature_control_model.py tests/test_tcn_bilstm_model.py tests/test_variable_ml.py tests/test_ml_training_runner.py`.
- **Ergebnis inklusive Fehlern:** `40 passed, 1 failed, 2 warnings in 15.62s`.
  Der einzige Fehler war die synthetische Score-Gleichheitsassertion beim
  Vergleich von T=16 mit maskiertem T=64; die CPU-Convolution wich um
  `1.2044e-05` ab, obwohl der zugrunde liegende Loss bereits maskiert war.
  Die zwei Warnings stammten aus dem bestehenden CUDA-Control-Test zu nicht
  deterministischen PyTorch-Backward-Implementierungen und nicht aus dem
  Ranker.
- **Schlussfolgerung und nächster Schritt:** Der Fehler war eine zu enge
  Testtoleranz, kein Contract-Verstoß; sie wurde auf `2e-5` als numerische
  CPU-Toleranz erweitert. Der kombinierte Lauf wird vollständig wiederholt,
  danach folgt der dokumentierte Diff-/Status-Audit.

## Testlauf am 2026-08-25 (kombinierte Regression nach Toleranzkorrektur)

- **Fragestellung und Reasoning:** Die Korrekturschleife musste bestätigen, dass
  die numerische Padding-Toleranz nur den synthetischen Convolution-Vergleich
  betrifft und der vollständige additive Rankerpfad sowie bestehende Controls
  weiterhin grün sind.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`, 41 synthetische Tests,
  CPU-Ranker und bestehende CUDA-Control-Smokes; kein Audio und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_feature_control_model.py tests/test_tcn_bilstm_model.py tests/test_variable_ml.py tests/test_ml_training_runner.py`.
- **Ergebnis inklusive Fehlern:** `41 passed, 2 warnings in 9.33s`. Die Warnings
  sind die bereits bekannte PyTorch-CUDA-Meldung zu nicht deterministischem
  Backward in bestehenden Control-Tests; kein Rankerfehler und keine
  Blockade.
- **Schlussfolgerung und nächster Schritt:** Der Ranker bleibt additiv und die
  bestehenden Control-Modelle sind unverändert testbar. Es folgt nur noch der
  abschließende Quell-/Diff-Audit; kein echtes Training wird gestartet.

## Testlauf am 2026-08-25 (vollständige Regression)

- **Fragestellung und Reasoning:** Nach der fokussierten Abnahme musste die
  komplette vorhandene Suite zeigen, dass der neue Ranker weder Candidate-,
  Dataset-, Batch-, Rendering- noch Control-Verhalten regressiv verändert.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`, Repository-Testfixture-
  daten und synthetische Audios der bestehenden Suite; keine reale
  Trainingskampagne. Der Cue-Ranker öffnete keinen Testsplit.
- **Testumfang bzw. Befehl:** `.venv\Scripts\python.exe -B -m pytest -q`.
- **Ergebnis inklusive Fehlern:** `227 passed, 4 warnings in 57.21s`. Die
  Warnings waren zwei bestehende `aifc`/`sunau`-Deprecations aus dem
  Batch-Render-Test und zwei bekannte PyTorch-CUDA-Determinismus-Warnings aus
  einem bestehenden Control-Runner-Test. Keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der implementierte Meilenstein ist
  vollständig regressionsgeprüft. Es bleibt bei der Offline-Trainings-/Modell-
  stufe; Produktionsintegration und reales Training sind ausdrücklich nicht
  Bestandteil dieser Änderung.

## Testlauf am 2026-08-25 (Determinismus ohne globalen Testseiten-Effekt)

- **Fragestellung und Reasoning:** Der Runner soll deterministische Torch-
  Algorithmen nur während seiner eigenen Epochen aktivieren und danach den
  vorherigen globalen Zustand restaurieren, damit bestehende Control-Runner
  nicht durch den neuen Ranker beeinflusst werden.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`, synthetische Ranker-
  Loader und bestehender ML-Runner-Smoke auf CPU/CUDA; kein Audiozugriff durch
  den Ranker und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_ml_training_runner.py`.
- **Ergebnis inklusive Fehlern:** `15 passed, 2 warnings in 8.25s`. Die
  Warnings stammen ausschließlich aus dem bestehenden Control-Test zu dessen
  nicht deterministischen CUDA-Backward-Operatoren; der Ranker-Runner stellte
  seinen Determinismuszustand korrekt wieder her.
- **Schlussfolgerung und nächster Schritt:** Der Seiten-Effekt ist behoben.
  Der abschließende volle Lauf wird nach dieser letzten Runner-Korrektur noch
  einmal ausgeführt und dokumentiert.

## Testlauf am 2026-08-25 (abschließende vollständige Regression)

- **Fragestellung und Reasoning:** Nach der letzten Determinismus-Korrektur
  musste der komplette Repository-Zustand erneut gegen alle vorhandenen
  Regressionen geprüft werden.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`, vollständige synthetische
  Repository-Suite, kein reales Training und kein Cue-Ranker-Testsplitzugriff.
- **Testumfang bzw. Befehl:** `.venv\Scripts\python.exe -B -m pytest -q`.
- **Ergebnis inklusive Fehlern:** `227 passed, 4 warnings in 34.95s`. Die vier
  Warnings sind unverändert die zwei Audio-Deprecations aus dem bestehenden
  Batch-Render-Test und zwei bekannte CUDA-Determinismus-Warnings aus dem
  bestehenden Control-Runner-Test. Keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der Ranker-Meilenstein ist ohne
  Regression verifiziert. Es werden keine weiteren Tests, Trainingsläufe oder
  Produktionsänderungen gestartet.

## Testlauf am 2026-08-25 (Cue-Ranker Trainings-/Evaluationsmetriken)

- **Fragestellung und Reasoning:** Die additive Trainingsstufe musste die
  geforderten Teacher-Agreement-Metriken und alle Validation-Baselines auf
  einem festen Label-Snapshot berichten, ohne Candidate-/Audio-SHA als Input
  oder einen Testloader einzuführen. Zusätzlich durfte nur die eingefrorene,
  positiv eingeschlossene Teacher-Stichprobe in den IPW-Softmax gelangen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, ausschliesslich
  synthetische Format-3-Gruppen mit 2/4/6/8 Takten und gefrorenen
  `teacher_utility`-Werten; CPU, eine Epoche, kein W&B und keine Audio- oder
  Testsplitdatei.
- **Testumfang bzw. Befehle:**
  `.venv\Scripts\python.exe -m pytest tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py -q`
  sowie ein ein-epochiger CPU-Smoke nach
  `output/training_runs/cue_ranker_synthetic_train_validation_smoke_all_lengths_20260825`.
- **Ergebnis inklusive Fehlern:** `19 passed in 8.82s`. Der Smoke schrieb
  endliche Train-/Validation-Losses `0.700030/0.676469`; die Validation hatte
  je eine auswertbare Gruppe für 2/4/6/8 Takte. `manifest.sha256`,
  `history.json`, `best.pt` und `latest.pt` wurden programmatisch gegen SHA-256
  und Bytezahl geprüft; alle Werte stimmten. Ein erster Einzeiler mit einer
  `def` nach Semikolon endete erwartbar mit `SyntaxError` und schrieb kein
  Artefakt; der nachfolgende Smoke lief erfolgreich. Kein externer Dienst
  erhielt lokale Audiodateipfade.
- **Schlussfolgerung und nächster Schritt:** Die Metrik-/Checkpointstufe ist
  reproduzierbar für eingefrorene Labels. Ein begrenzter realer Smoke wurde
  bewusst nicht simuliert: Im Workspace existiert noch kein testfrei
  veröffentlichter Format-3-Teacher-Snapshot mit echten gelabelten Gruppen.
  Ein v2-Top-K-Dataset oder synthetische Pseudo-Utilities wäre kein zulässiger
  Ersatz. Teacher-Agreement bleibt kein Hörqualitätsnachweis; der
  Produktionsdefault bleibt unverändert.

## Testlauf am 2026-08-25 (Vollsuite, Terminalrückgabe unvollständig)

- **Fragestellung und Reasoning:** Nach der Metrikänderung wurde zusätzlich
  die komplette Suite gestartet, um unerwartete Querregressionen zu finden.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -m pytest -q`, vorhandene
  Testfixtures; keine absichtliche reale Cue-Ranker-Materialisierung.
- **Testumfang bzw. Befehl:** `.venv\Scripts\python.exe -m pytest -q`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Die Terminalintegration gab
  nur Fortschrittspunkte zurück und lieferte keinen abschließenden pytest-
  Summary-/Exit-Code, obwohl die gestarteten Python-Prozesse danach beendet
  waren. Dieser Lauf wird daher nicht als grüner Vollsuite-Nachweis gewertet.
  Der unmittelbar zuvor vollständig rückgemeldete fokussierte Lauf bestand
  mit `19 passed in 8.82s`.
- **Schlussfolgerung und nächster Schritt:** Keine Aussage über den
  Gesamtsuitenstatus aus diesem unvollständigen Terminalresultat ableiten;
  für den implementierten Pfad bleibt der fokussierte Synthetiknachweis die
  belastbare Prüfung.

## Diagnose am 2026-08-26 (niedrige GPU-Auslastung des Variable-TCN-Trainings)

- **Fragestellung und Reasoning:** Während des realen Variable-TCN/BiLSTM-
  Trainings lag die beobachtete RTX-5070-Ti-Auslastung nur bei etwa 30–40 %.
  Es sollte read-only geklärt werden, ob Daten-I/O, VRAM-Kapazität oder die
  Ausführungsstruktur von Renderer und Objective begrenzt, bevor ein
  Optimierungshebel gewählt wird.
- **Eingaben/Setup:** Lauf
  `output/training_runs/variable_tcn_bilstm_v2_wandb_20260826`, Dataset v2,
  ausschließlich dessen bereits materialisierte Train-/Validation-Caches,
  `cuda:0`, Batchgröße 8 und W&B online. Der Testsplit wurde nicht geöffnet;
  weder Quellcode noch Trainingsartefakte wurden verändert.
- **Testumfang bzw. Befehle:** Read-only-Snapshots mit `nvidia-smi`,
  `Get-Process`, Runmanifest/`history.json`/W&B-Metadaten, gezielte
  Codeinspektion von `variable_runner.py`, `variable_training.py`,
  `variable_data.py` und den differenzierbaren Renderern sowie eine
  PowerShell-Inventur der 468 Cachemanifeste nach Takt- und Samplelänge.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Während des Laufendes
  meldete `nvidia-smi` 18 % GPU-Auslastung, etwa 2,3–3,0 GiB von 16 GiB VRAM
  und nur 48–77 W von 300 W. Der Python-Prozess hatte in rund 5,3 Minuten
  ungefähr 317 CPU-Sekunden verbraucht, also näherungsweise einen vollen
  CPU-Kern. Der Lauf beendete sich regulär nach Epoche 29; die letzte W&B-
  Session meldet 355,62 s Laufzeit, Best-Epoche 23 und Validation-Loss
  `0,2455985323`. Der Wrapper materialisiert alle Batches vorab im RAM, daher
  ist `DataLoader num_workers` für diesen Lauf kein Epochenengpass. Im Loss
  werden die acht Beispiele jedoch in Python seriell gerendert und bewertet;
  außerdem erzwingen pro Batch zahlreiche einzelne
  `float(value.detach().cpu())`- und Finite-Prüfungen CUDA-Synchronisationen.
  Der Renderer selbst unterstützt bereits echte Batchtensoren. Die 117
  Cachebeispiele je Länge besitzen nur 23/26/31/31 unterschiedliche
  Samplelängen; Padding auf das jeweilige Maximum würde über die vollständige
  Längengruppe nur etwa 9–12 % Längenaufschlag verursachen. Eine erste
  Inventur verwendete irrtümlich den nicht vorhandenen JSON-Pfad
  `arrays.source_audio.shape` und endete mit wiederholten Null-Indexfehlern;
  die korrigierte Inventur über `waveforms.shape` lief erfolgreich.
- **Schlussfolgerung und nächster Schritt:** Die GPU ist primär durch kleine,
  seriell gestartete Arbeiten und Host-/Device-Synchronisationen unterfüttert,
  nicht durch Cache-I/O oder VRAM-Mangel. Priorität haben (1) Loss-Terme auf
  der GPU sammeln und gebündelt übertragen sowie Finite-Prüfungen bündeln,
  danach (2) längenhomogene Audios gepaddet/maskiert stapeln und Renderer plus
  Objective echt batchweise ausführen. Erst anschließend sollten größere
  Batches und BF16-Autocast in kurzen, getrennten Benchmarkläufen gegen die
  FP32-Loss-/Gradientenreferenz geprüft werden. Eine bloße Erhöhung von
  `num_workers` ist für diesen Runner nicht zielführend.

## Testlauf am 2026-08-26 (Cue-Ranker-Pair-Index, fehlerhafter Erstaufruf)

- **Fragestellung und Reasoning:** Der neue Pair-Index-CLI- und Universe-Pfad
  sollte fokussiert gegen die synthetischen Vertrags-, Positiv- und
  Split-Leakage-Tests geprüft werden. Der erste Aufruf setzte `-B` an die
  falsche Stelle und wurde deshalb von pytest als unbekanntes Argument
  zurückgewiesen; der Test wurde nicht gestartet.
- **Eingaben/Setup:** Repository-Workspace, `.venv\Scripts\python.exe`,
  synthetische Fixtures in `tests/test_cue_ranker_universe.py`; keine realen
  Pair-/Audio-/Feature-Artefakte und kein Test-Artefakt wurden geöffnet.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q -B -p no:cacheprovider tests/test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Blockiert vor Testbeginn mit
  `pytest: error: unrecognized arguments: -B` und Exit-Code 1.
- **Schlussfolgerung und nächster Schritt:** Kein Codeergebnis aus diesem
  fehlerhaften Aufruf ableiten. Den identischen fokussierten Lauf mit der
  korrekten Python-Option vor `-m` ausführen.

## Testlauf am 2026-08-26 (Cue-Ranker-Pair-Index, erste fokussierte Suite)

- **Fragestellung und Reasoning:** Nach der Korrektur des Python-Aufrufs wurde
  die synthetische Universe-/Pair-Index-Suite für Positiv-, Negativ-,
  Determinismus- und Testsplit-Leakage-Verhalten ausgeführt.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`,
  `tests/test_cue_ranker_universe.py`; ausschließlich synthetische Pair-
  Manifeste, mit einem absichtlich fehlenden Test-Pair-Pfad; keine realen
  Audio-, Feature- oder Test-Artefakte.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `5 passed, 1 failed` in
  `5,34 s`, Exit-Code 1. Der einzige Fehler lag in der neuen Testfixture:
  deren Hilfsfunktion versuchte beim Erstellen des absichtlich fehlenden
  Test-Pair-Pfads dessen SHA zu lesen. Der Produktionscode öffnete den
  fehlenden Testpfad nicht.
- **Schlussfolgerung und nächster Schritt:** Die Fixture wurde korrigiert,
  sodass der Test-SHA deterministisch synthetisch gesetzt wird; danach wird
  derselbe Lauf wiederholt.

## Testlauf am 2026-08-26 (Cue-Ranker-Pair-Index, CLI-Test-API)

- **Fragestellung und Reasoning:** Die korrigierte Leakage-Fixture sollte den
  offiziellen `build-cue-ranker-pair-index`-Einstieg ausführen.
- **Eingaben/Setup:** Wie im unmittelbar vorherigen Lauf, ausschließlich
  synthetische Root-/Pair-/Split-Map-Daten; der fehlende Test-Pair-Pfad blieb
  absichtlich unmaterialisiert.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `5 passed, 1 failed` in
  `4,47 s`, Exit-Code 1. Der Test traf den neuen CLI-Pfad, aber
  `src.features.__main__.main` akzeptierte noch kein `argv` für den
  programmatischen CLI-Test.
- **Schlussfolgerung und nächster Schritt:** `main(argv=None)` wurde additiv
  ergänzt; der fokussierte Lauf wird erneut ausgeführt.

## Testlauf am 2026-08-26 (Cue-Ranker-Pair-Index, fokussiert bestanden)

- **Fragestellung und Reasoning:** Positiv-, Negativ-, Determinismus- und
  Split-Leakage-Verträge des neuen Pair-Index-/Universe-Pfads sollten nach
  den Fixture- und CLI-Korrekturen vollständig grün sein.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, sechs synthetische Tests in
  `tests/test_cue_ranker_universe.py`; der Test-Pair-Pfad wurde nur als
  fehlende Referenz in der Split-Map geführt und nicht geöffnet.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `6 passed in 4,53 s`,
  Exit-Code 0. Der CLI erzeugte den Pair-Index mit Root-Manifest-SHA und
  Split-Map-Datei-SHA; das Test-Pair wurde vor einem möglichen Öffnen
  ausgesiebt.
- **Schlussfolgerung und nächster Schritt:** Der fokussierte neue Pfad ist
  synthetisch verifiziert. Als Nächstes folgen CLI-/Batch-Regressionen und
  die vollständige relevante Regression ohne große Real-Materialisierung.

## Testlauf am 2026-08-26 (Cue-Ranker-Datenanfang und angrenzende Regression)

- **Fragestellung und Reasoning:** Der neue Pair-Index-/Universe-Pfad durfte
  bestehende Candidate-v2-, Dataset-v2-, Batch- und Multi-Batch-Verträge nicht
  brechen. Die angrenzende synthetische Regression wurde daher gemeinsam mit
  dem fokussierten neuen Satz ausgeführt.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Fixtures der
  fünf Testdateien; keine reale Materialisierung, kein Training und kein
  Zugriff auf Testsplit-Artefakte.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_candidates.py tests/test_variable_dataset.py tests/test_batch_render.py tests/test_multi_batch_render.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `41 passed, 2 warnings in
  33,38 s`, Exit-Code 0. Die beiden bekannten Python-3.14-Deprecation-
  Warnungen betreffen `aifc`/`sunau` in `audioread`.
- **Schlussfolgerung und nächster Schritt:** Candidate-v2/v1-, Dataset-v2-,
  Batch- und Multi-Batch-Pfade bleiben testbar; der Pair-Index-Pfad zeigt keine
  Regression. Es folgt ein CLI-Contract-Audit sowie eine abschließende
  Diff-/Hashprüfung ohne großen Real-Lauf.

## Testlauf am 2026-08-26 (Pair-Index-Hardening-Regression)

- **Fragestellung und Reasoning:** Nach dem zusätzlichen Source-Manifest-
  Binding der Split-Map und der Revalidierung gebundener Root-/Dataset-SHAs
  sollte die gesamte fokussierte Datenanfangs-Regression weiterhin bestehen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Candidate-,
  Dataset-v2-, Batch- und Multi-Batch-Fixtures; keine realen Pair-, Audio-,
  Feature- oder Testartefakte wurden für den Cue-Ranker-Pfad geöffnet.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_candidates.py tests/test_variable_dataset.py tests/test_batch_render.py tests/test_multi_batch_render.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `41 passed, 2 warnings in
  11,87 s`, Exit-Code 0. Die Warnungen sind die bekannten `aifc`-/`sunau`-
  Deprecations aus `audioread` unter Python 3.14.
- **Schlussfolgerung und nächster Schritt:** Das Hardening ist regressionsfrei
  in den angrenzenden Pfaden. Abschließend werden die übrigen Cue-Ranker-
  Vertragsmodule fokussiert geprüft und danach der Arbeitsbaum auditiert.

## Testlauf am 2026-08-26 (Pair-Manifest-Provenienz, Diagnose)

- **Fragestellung und Reasoning:** Nach Ergänzung der Pair-Manifest-Request-
  und Grid-Provenienzprüfung sollte der fokussierte Universe-Satz bestehen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Fixtures in
  `tests/test_cue_ranker_universe.py`; kein reales oder Testsplit-Artefakt.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `2 passed, 4 failed` in
  `4,01 s`, Exit-Code 1. Die neue Grid-Provenienzprüfung verwies zunächst
  aus `_validate_candidate` auf eine dort nicht verfügbare lokale Variable
  `generation` (`NameError`).
- **Schlussfolgerung und nächster Schritt:** Die Prüfung wird mit dem bereits
  verfügbaren Generation-Payload korrekt parametrisiert; anschließend wird
  der fokussierte Satz erneut ausgeführt.

## Testlauf am 2026-08-26 (Pair-Manifest-Provenienz, fokussiert bestanden)

- **Fragestellung und Reasoning:** Die korrigierte Generation-Payload-
  Übergabe sollte die vollständige Pair-Manifest-Request-/Grid-Prüfung ohne
  Regression im Universe-Satz ausführen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, sechs synthetische Tests
  aus `tests/test_cue_ranker_universe.py`; das absichtlich fehlende Test-Pair
  blieb ungeöffnet und unmaterialisiert.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `6 passed in 3,83 s`,
  Exit-Code 0.
- **Schlussfolgerung und nächster Schritt:** Pair-Manifest-SHA, vollständige
  Request-Konfiguration, Candidate-v2-/4/4- und Grid-Provenienz sowie
  Split-Leakage sind fokussiert verifiziert.

## Testlauf am 2026-08-26 (abschließende Cue-Ranker-Datenanfangs-Regression)

- **Fragestellung und Reasoning:** Nach der letzten Provenienzkorrektur
  sollten der neue Pair-Index-/Universe-Pfad, alle vorhandenen Cue-Ranker-
  Stufen und die unveränderten Candidate-/Dataset-v2-/Batch-Pfade gemeinsam
  bestehen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Tests aus den
  Cue-Ranker-, Candidate-, Dataset-v2-, Batch- und Multi-Batch-Testdateien;
  kein großer realer Universe-Lauf, kein Training und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py tests/test_candidates.py tests/test_variable_dataset.py tests/test_batch_render.py tests/test_multi_batch_render.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `67 passed, 2 warnings in
  18,56 s`, Exit-Code 0. Die Warnungen sind die bekannten
  `aifc`-/`sunau`-Deprecations aus `audioread`.
- **Schlussfolgerung und nächster Schritt:** Der implementierte Datenanfang
  ist über die fokussierte Gesamtregression verifiziert; es bleibt nur die
  statische Endkontrolle des Diffs und die Statuspflege.

## Testlauf am 2026-08-26 (additive Batch-Manifest-Provenienz)

- **Fragestellung und Reasoning:** Die zuletzt ergänzten Source-/Target-
  Audio-SHAs im einzelnen Batch-Manifest sollten den Universe-/Pair-Index-
  Vertrag ergänzen, ohne Candidate- oder Batch-Verhalten zu verändern.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Universe- und
  Batch-Fixtures; keine realen Audio-/Feature-/Testartefakte und kein Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_batch_render.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `10 passed, 2 warnings in
  9,22 s`, Exit-Code 0. Die Warnungen sind die bekannten
  `aifc`-/`sunau`-Deprecations aus `audioread`.
- **Schlussfolgerung und nächster Schritt:** Die additive Manifestprovenienz
  ist gezielt regressionsgeprüft. Jetzt folgen statische Diff-/Statuschecks
  und die Aktualisierung des verifizierten Projektstatus.

## Testlauf am 2026-08-26 (abschließende Regression nach Producer-Kompatibilität)

- **Fragestellung und Reasoning:** Die sichere Unterstützung des bestehenden
  Producer-Feldnamens `manifest_path` und einer explizit im Root gebundenen
  Request-Konfiguration sollte den gesamten implementierten Datenanfang
  unverändert grün lassen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, dieselbe fokussierte
  Cue-Ranker-/Candidate-/Dataset-v2-/Batch-/Multi-Batch-Suite; keine reale
  Materialisierung, kein Training und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py tests/test_candidates.py tests/test_variable_dataset.py tests/test_batch_render.py tests/test_multi_batch_render.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `67 passed, 2 warnings in
  16,26 s`, Exit-Code 0. Die Warnungen sind die bekannten
  `aifc`-/`sunau`-Deprecations aus `audioread`.
- **Schlussfolgerung und nächster Schritt:** Der produktive Datenanfang ist
  nach der letzten Änderung vollständig fokussiert regressionsgeprüft.

## Testlauf am 2026-08-26 (SHA-Binding-Endkontrolle)

- **Fragestellung und Reasoning:** Die zusätzliche Prüfung auf vorhandene und
  zueinander passende Dataset-/Source-Manifest- und Split-Map-SHAs sollte
  alle zuvor verifizierten Datenanfangs- und Regressionsverträge erhalten.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, vollständige fokussierte
  synthetische Cue-Ranker-/Candidate-/Dataset-v2-/Batch-/Multi-Batch-Suite;
  kein realer Universe-Großlauf, kein Training und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py tests/test_candidates.py tests/test_variable_dataset.py tests/test_batch_render.py tests/test_multi_batch_render.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `67 passed, 2 warnings in
  15,35 s`, Exit-Code 0. Die Warnungen sind die bekannten
  `aifc`-/`sunau`-Deprecations aus `audioread`.
- **Schlussfolgerung und nächster Schritt:** SHA-Binding und alle fokussierten
  Tests sind final verifiziert. Es wurde kein Output-Artefakt verändert.

## Testlauf am 2026-08-26 (übrige Cue-Ranker-Vertragsmodule)

- **Fragestellung und Reasoning:** Die Änderungen am gemeinsamen Feature-CLI
  und am Batch-Provenienzvertrag sollten die bereits vorhandenen Dataset-,
  Teacher-, Modell-, Runner- und Learned-Integrationstests nicht beeinflussen.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`, synthetische Fixtures in
  den fünf Cue-Ranker-/Integrationstestdateien; kein reales Training, kein
  Universe-Großlauf und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cue_ranker_dataset.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `26 passed, 2 warnings in
  16,55 s`, Exit-Code 0. Die Warnungen sind die bekannten
  `aifc`-/`sunau`-Deprecations aus `audioread`.
- **Schlussfolgerung und nächster Schritt:** Die vorhandenen Cue-Ranker-
  Dataset-/Teacher-/Modell-/Runner- und Inferenzverträge bleiben grün. Es
  folgt nur noch die statische Integritäts- und Diff-Prüfung; ein großer
  realer Universe-Lauf wird nicht gestartet.

## Testlauf am 2026-08-26 (Teacher-Pfad, erste Diagnose)

- **Fragestellung und Reasoning:** Der neue Sealer-, Resolver-, Cache- und
  Resume-Pfad sollte zunächst syntaktisch und gegen die vorhandenen
  Teacher-Fixtures geprüft werden, bevor weitere Negative- und End-to-End-
  Tests ergänzt werden.
- **Eingaben/Setup:** `.venv\Scripts\python.exe`; ausschließlich
  synthetische Universe-/Checkpoint-Fixtures in
  `tests/test_cue_ranker_teacher.py`; kein reales Release, keine Audio- oder
  Testsplit-Materialisierung.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m py_compile src\ml\cue_ranker_teacher.py src\ml\cue_ranker_teacher_resolver.py src\ml\__main__.py; .venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `py_compile` scheiterte
  vor der Prüfung mit `Permission denied` auf einem vorhandenen
  `__pycache__`-Temporärpfad. Der anschließende Testlauf ergab `2 passed,
  1 failed`: Universe-v1 speichert die Splitzugehörigkeit im hashgeprüften
  Shardpfad, aber noch nicht redundant pro Row; die neue Prüfung verlangte
  diese Redundanz zu früh.
- **Schlussfolgerung und nächster Schritt:** Der Teacher bindet den Split nun
  ausschließlich aus dem bereits verifizierten Train-/Validation-Shard und
  lehnt ein etwaig vorhandenes widersprüchliches Row-Feld weiter ab. Die
  Wiederholung erfolgt mit `-B`, damit keine Bytecode-Datei geschrieben wird.

## Testlauf am 2026-08-26 (Teacher-Regression, erster grüner Lauf)

- **Fragestellung und Reasoning:** Nach der sicheren Shard-Split-Bindung
  sollten die bestehenden Teacher-Verträge wieder grün sein.
- **Eingaben/Setup:** Dieselben rein synthetischen Fixtures; kein Testsplit,
  kein reales Audio, kein reales Teacher-Release.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `3 passed in 2,85 s`,
  Exit-Code 0.
- **Schlussfolgerung und nächster Schritt:** Die ursprünglichen Sealer- und
  Label-Verträge bleiben kompatibel. Resume-, Manipulations- und
  Produktions-Guard-Tests werden ergänzt.

## Testlauf am 2026-08-26 (Cue-Ranker-Teacher, Zwischenregression)

- **Fragestellung und Reasoning:** Die neuen Resume-/Cache-Felder durften
  Dataset-Format-3 und den gruppierten Loss nicht verändern.
- **Eingaben/Setup:** Synthetische Cue-Ranker-Teacher-, Dataset- und
  Runner-Fixtures; Train/Validation-only, keine Test-Artefakte.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_runner.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `10 passed in 5,54 s`,
  Exit-Code 0.
- **Schlussfolgerung und nächster Schritt:** Die kompatiblen
  `teacher_status`-Werte und der zusätzliche Produktionsstatus beeinträchtigen
  die Loss-/Dataset-Verträge nicht.

## Testlauf am 2026-08-26 (synthetischer vollständiger Teacher-Score)

- **Fragestellung und Reasoning:** Ein Candidate-v2 musste ohne Mock des
  Controllers vollständig durch `weights_only`-Teacher, Objective v5 und den
  bestehenden Render-Guard laufen; zusätzlich wurden Checkpoint-Manipulation,
  Cache-Key-Trennung, Resume, Guard-Rejection und Alignment-Failure geprüft.
- **Eingaben/Setup:** Erweiterte synthetische Fixtures mit 2/4/6-Takt-
  Candidates und vier samplegleichen Stereo-Waveforms. Kein reales Audio,
  Testsplit oder Teacher-Release.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `8 passed, 4 warnings in
  7,32 s`, Exit-Code 0. Die vier erwarteten Librosa-Warnungen entstehen durch
  die absichtlich sehr kurzen 256-Sample-Synthesewaveforms des Guard-Fixtures
  (`n_fft=2048` beziehungsweise leere Tuningmenge), nicht durch den
  Produktionsresolver.
- **Schlussfolgerung und nächster Schritt:** Der vollständige synthetische
  Teacher-Pfad und alle verlangten Negativ-/Resume-Fälle sind abgedeckt.

## Testlauf am 2026-08-26 (Teacher-CLI-Contract)

- **Fragestellung und Reasoning:** Die neuen CLI-Einstiege mussten sichtbar
  einen expliziten Run, Normalizer, Backend-Provenienz beziehungsweise eine
  Split-Autorität verlangen und keinen versteckten Default anbieten.
- **Eingaben/Setup:** Nur Argumentparser/Help-Ausgabe, keine Ausführung eines
  Sealer- oder Labeljobs und keine Artefaktmaterialisierung.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m src.ml --help; .venv\Scripts\python.exe -B -m src.ml seal-cue-ranker-teacher --help; .venv\Scripts\python.exe -B -m src.ml label-cue-ranker-teacher --help`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 0. Beide Befehle
  sind registriert; der Sealer verlangt `--normalizer` und
  `--backend-provenance`, das Labeling verlangt `--split-map`.
- **Schlussfolgerung und nächster Schritt:** Kein automatischer Runpfad oder
  Testsplit ist über die CLI erreichbar.

## Testlauf am 2026-08-26 (abschließende Teacher-/Alignment-Regression)

- **Fragestellung und Reasoning:** Sealer, Candidate-v2-Resolver, getrennte
  Caches, Guard, Resume und die bestehende lokale Grid-Ausrichtung sollten
  gemeinsam mit den angrenzenden Cue-Ranker-Stufen regressionsfrei sein.
- **Eingaben/Setup:** Rein synthetische Universe-, Teacher-, Dataset-,
  Modell-, Runner- und Variable-Waveform-Fixtures; kein großer realer Lauf,
  kein Training und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_variable_waveform_cache.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `39 passed, 4 warnings in
  9,50 s`, Exit-Code 0. Die Warnungen entsprechen dem dokumentierten kurzen
  synthetischen Render-Guard-Fixture; keine Testdatei, kein Test-Audio und
  kein Testloader wurden vom Produktionspfad geöffnet.
- **Schlussfolgerung und nächster Schritt:** Der Teacher-Implementierungs-
  meilenstein ist synthetisch verifiziert. Ein realer Pilot bleibt erst nach
  explizitem Normalizer-/Backend-/Universe-Release zulässig.

## Testlauf am 2026-08-26 (Teacher-Sealer-CLI, vollständige Synthetik)

- **Fragestellung und Reasoning:** Neben der Help-Prüfung sollte der neue
  Sealer-CLI einen expliziten abgeschlossenen Run, einen trainings-only
  Normalizer und eine Backend-Provenienz tatsächlich zu einem verifizierbaren
  Release binden.
- **Eingaben/Setup:** Synthetischer completed Variable-TCN-Run mit
  manifestiertem Best-Checkpoint sowie kleine Normalizer-/Backend-JSONs in
  `tests/test_cue_ranker_teacher.py`; keine reale Checkpointpublikation.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `9 passed, 4 warnings in
  6,72 s`, Exit-Code 0. Der neue CLI-Test bestätigt den erzeugten
  Normalizer-SHA erneut über `verify_teacher_release()`. Die vier Warnungen
  stammen unverändert vom kurzen synthetischen Guard-Fixture.
- **Schlussfolgerung und nächster Schritt:** Der Sealer-CLI bindet keine
  implizite Modellwahl und schreibt einen testbar verifizierbaren Release.

## Testlauf am 2026-08-26 (Waveform-Cache-Provenienz-Korrektur)

- **Fragestellung und Reasoning:** Der neue unveränderliche
  Candidate-Waveform-Cache muss bei einem zweiten Zugriff dieselbe
  Basisprovenienz prüfen; die detaillierte, tatsächlich angewandte Alignment-
  Provenienz darf diesen Cache-Hit nicht durch eine nachträgliche Key-Änderung
  verhindern.
- **Eingaben/Setup:** Synthetische Teacher-Release-, Candidate- und
  Stereo-Waveform-Fixtures; direkte Prüfung des atomar geschriebenen
  Cue-Ranker-Waveform-Caches sowie der bestehenden Alignment-/Universe-Tests.
  Kein reales Audio, kein Testsplit und keine Release-Publikation.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py tests\test_variable_waveform_cache.py tests\test_cue_ranker_universe.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `26 passed, 4 warnings in
  7,15 s`, Exit-Code 0. Die bekannten vier Librosa-Warnungen stammen von den
  kurzen synthetischen Guard-Waveforms; es gab keine Blockade.
- **Schlussfolgerung und nächster Schritt:** Der Cache trennt
  Release-/Candidate-/Provenienz-Keys, trifft erneut verifizierbar und hält
  die Alignment-Provenienz zusätzlich im gespeicherten Manifest fest.

## Testlauf am 2026-08-26 (finale Cue-Ranker-Teacher-Regression)

- **Fragestellung und Reasoning:** Nach der zusätzlichen SHA-Bindung für
  Modellvertrag, Renderer, Objective und Alignment sowie der Cache-Korrektur
  mussten der vollständige Teacher-Pfad und alle angrenzenden Cue-Ranker-
  Verträge gemeinsam regressionsfrei bleiben.
- **Eingaben/Setup:** Ausschließlich synthetische Universe-, Teacher-,
  Dataset-, Modell-, Runner- und Variable-Waveform-Fixtures. Kein echter
  Teacher-Release, kein großer Labeling-Lauf und keinerlei Test-Artefakt.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_variable_waveform_cache.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `41 passed, 4 warnings in
  9,90 s`, Exit-Code 0. Die vier erwarteten Librosa-Warnungen kommen nur vom
  256-Sample-Guard-Fixture; es gab keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der Produktionspfad ist
  synthetisch vollständig verifiziert. Ein realer Pilot setzt weiterhin die
  explizit freigegebenen Normalizer-, Backend- und Universe-Provenienzen
  voraus.

## Testlauf am 2026-08-26 (Cache-Root-Audit-Regression)

- **Fragestellung und Reasoning:** Ein über die CLI gewählter Waveform-
  Cache-Root muss im Label-/Resume-Vertrag auditierbar sein, ohne die
  bestehenden Teacher-, Dataset- oder Alignment-Verträge zu verändern.
- **Eingaben/Setup:** Dieselben ausschließlich synthetischen Fixtures wie im
  finalen Teacher-Regressionstest; kein reales Audio, kein Testsplit und
  keine Veröffentlichung.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_variable_waveform_cache.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `41 passed, 4 warnings in
  10,02 s`, Exit-Code 0. Die vier bekannten Librosa-Warnungen stammen aus dem
  kurzen synthetischen Guard-Fixture; es gab keine Blockade.
- **Schlussfolgerung und nächster Schritt:** Der tatsächliche Cache-Root ist
  jetzt Teil des atomar geschriebenen Label-Manifests und der Resume-Bindung.

## Testlauf am 2026-08-26 (Produktions-Normalizer-Regression)

- **Fragestellung und Reasoning:** Der Resolver muss die bestehende
  `FeatureNormalizationStats`-Signatur exakt mit dem trainings-only
  Normalizervertrag befüllen, bevor Features oder Audio verarbeitet werden.
- **Eingaben/Setup:** Synthetischer trainings-only Normalizer mit gültigem
  Dateihash und die vollständigen Cue-Ranker-/Variable-Waveform-Fixtures; kein
  reales Audio, Testsplit oder Teacher-Release.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_variable_waveform_cache.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `42 passed, 4 warnings in
  10,26 s`, Exit-Code 0. Die vier bekannten Librosa-Warnungen stammen aus dem
  kurzen synthetischen Guard-Fixture; keine Fehler oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der Resolver übernimmt
  `stats_id`, Spektralfluss- und Onset-Normalisierung mit den richtigen
  benannten Vertragsfeldern.

## Testlauf am 2026-08-26 (Teil-Resume-Budgettests, erste Ausführung)

- **Fragestellung und Reasoning:** Der neue Candidate- und Fehlerbudget-
  Rahmen sollte einen Teil-Lauf nach atomarem Cachewrite abbrechen und danach
  ohne Neubewertung fortsetzen können.
- **Eingaben/Setup:** Erweiterte synthetische Teacher-Fixtures mit drei
  Candidates sowie alle angrenzenden Cue-Ranker-/Waveform-Fixtures; kein
  reales Audio, Testsplit oder Release.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_variable_waveform_cache.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 1: `42 passed, 2
  failed, 4 warnings in 10,60 s`. Ausschließlich die zwei neuen Test-
  Annahmen erwarteten fälschlich die Input-Reihenfolge `good` zuerst; die
  verifizierte Universe-Sortierung liefert deterministisch `failed`, `good`,
  `guard`. Die Budgetimplementierung selbst schrieb den ersten Cacheeintrag
  und brach anschließend wie vorgesehen ab.
- **Schlussfolgerung und nächster Schritt:** Test auf die festgestellte,
  deterministische Candidate-Reihenfolge korrigieren und die vollständige
  Regression wiederholen.

## Testlauf am 2026-08-26 (Teil-Resume-Budgettests, korrigierte Ausführung)

- **Fragestellung und Reasoning:** Nach Bindung der Testannahmen an die
  kanonische Candidate-Reihenfolge musste der kontrollierte Abbruch nach
  atomarem Cachewrite sowie die deterministische Fortsetzung verifiziert
  werden.
- **Eingaben/Setup:** Erweiterte synthetische Teacher-Fixtures mit Candidate-
  und Fehlerbudget, dazu alle angrenzenden Cue-Ranker-/Waveform-Fixtures; kein
  reales Audio, Testsplit oder Teacher-Release.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_variable_waveform_cache.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `44 passed, 4 warnings in
  64,31 s`, Exit-Code 0. Die vier bekannten Librosa-Warnungen stammen aus dem
  kurzen synthetischen Guard-Fixture; es gab keine Blockade.
- **Schlussfolgerung und nächster Schritt:** Fehlerbudget und
  `max_candidates` schreiben candidateweise, brechen kontrolliert ab und
  setzen anhand der verifizierten Cache-Einträge ohne Neubewertung fort.

## Testläufe am 2026-08-26 (Format-3-Featureloader und Ranker-CLI)

- **Fragestellung und Reasoning:** Der zuvor nur injizierbare Dataset-View
  musste durch einen echten, ausschliesslich SHA-gebundenen Featurecache-
  Resolver ersetzt werden. Zu prüfen waren die Teacher-identische
  Normalisierung, alle variablen Längen, Train/Validation ohne Testsplit,
  Cache-/Universe-/Teacher-/Normalizer-Manipulation und die offizielle CLI.
- **Eingaben/Setup:** Ausschliesslich neue synthetische Format-3-Universes,
  Teacher-Label-Shards und vorhandene, künstliche Feature-Protocol-2-Caches;
  CPU, kein CUDA-Lauf, kein Audio- oder Testsplitzugriff.
- **Testumfang bzw. Befehle und Ergebnis:**
  1. `.venv\Scripts\python.exe -m py_compile ...; .venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_cue_ranker_dataset.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py -q`:
     Pycache-Schreibversuch von `py_compile` wurde mit `Permission denied`
     blockiert; die anschliessenden Tests ergaben zunächst `1 failed, 14
     passed` wegen einer alten Minimalfixture ohne die nun zwingenden
     endlichen p99-Normalizerwerte.
  2. Nach Fixture-Korrektur derselbe Pytest-Umfang: `15 passed, 2 warnings`.
  3. `.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_cue_ranker_feature_loader.py -q`:
     `2 passed`.
  4. Erweiterter Loader-/Dataset-/Runner-Umfang: zunächst `1 failed, 12
     passed` wegen eines Test-`argv`, das fälschlich `-m src.ml` innerhalb
     von `sys.argv` nachstellte; nach Korrektur `13 passed`.
  5. Abschliessend `.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_feature_loader.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py -q`:
     `48 passed, 6 warnings in 11.66 s`, Exit-Code 0. Die Warnungen stammen
     ausschliesslich aus bekannten kurzen Librosa-/Audioread-Synthesefällen.
- **Schlussfolgerung und nächster Schritt:** Format 3 löst nun keine
  Tensor-Duplikate ein, sondern verifiziert die Dataset→Universe→Teacher-
  Kette, öffnet nur passende Cachepayloads und extrahiert die 54/16-
  Float32-Inputs identisch zum Teacher. `train-cue-ranker` konstruiert nur
  Train- und Validation-Loader und setzt über den vorhandenen SHA-geprüften
  `weights_only`-Latest-Checkpoint fort. Ein realer Pilot bleibt separat
  freigabepflichtig und wurde nicht gestartet.

## Testlauf am 2026-08-26 (Normalizer-Scope-Vertrag und CLI-Preflight)

- **Fragestellung und Reasoning:** Der maschinelle Nachweis der Train-only-
  Normalisierung sollte nicht nur beim Loader, sondern bereits beim Export
  gelten: jede deklarierte Track-SHA muss exakt dem Train-Universum
  entsprechen, ohne Validation-Leakage. Zusätzlich musste die veröffentlichte
  CLI sichtbar ohne Testsplitoption bleiben.
- **Eingaben/Setup:** Synthetisches Format-3-Universum mit zwei Train- und
  zwei Validation-Track-SHAs sowie künstlichen Featurecaches; CPU-only.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_cue_ranker_dataset.py tests/test_cue_ranker_feature_loader.py tests/test_cue_ranker_runner.py -q; .venv\Scripts\python.exe -m src.ml train-cue-ranker --help`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `14 passed in 5.83 s`,
  Exit-Code 0. Die Hilfe enthält Batchgröße, Epochen, Seed, Device, Resume
  und W&B-Mode, aber keine Testsplitoption; keine Warnungen oder Blockaden.
- **Schlussfolgerung und nächster Schritt:** Der Export verweigert fehlende,
  unvollständige oder nicht exakt traingebundene Normalizer-Tracklisten; der
  Loader weist zusätzlich nachträglich eingeschleuste Validation-SHAs ab.

## Testlauf am 2026-08-26 (abschliessende Format-3-Regression)

- **Fragestellung und Reasoning:** Nach Schliessung des exportseitigen
  Normalizer-Scopes musste die gesamte betroffene Cue-Ranker-Kette gemeinsam
  geprüft werden, einschliesslich der unveränderten Learned-Inferenz.
- **Eingaben/Setup:** Ausschliesslich bestehende und neue synthetische
  Fixtures, CPU; weder reales CUDA-Training noch Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_cue_ranker_universe.py tests/test_cue_ranker_teacher.py tests/test_cue_ranker_dataset.py tests/test_cue_ranker_feature_loader.py tests/test_cue_ranker_model.py tests/test_cue_ranker_runner.py tests/test_learned_cue_ranker_integration.py -q`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `49 passed, 6 warnings in
  11.46 s`, Exit-Code 0. Die sechs bekannten Warnungen stammen aus kurzen
  Librosa-/Audioread-Syntheseinputs; es gab keine Blockade.
- **Schlussfolgerung und nächster Schritt:** Der reale Format-3-
  Dataset-/Trainingspfad ist synthetisch vollständig verifiziert. Ein späterer
  echter Train-/Validation-Lauf benötigt nur freigegebene, entsprechend
  gebundene Artefakte und bleibt vor dem Start separat zu entscheiden.

## Testlauf am 2026-08-26 (frischer Cue-Ranker-Audit, W&B-Fehlerpfad)

- **Fragestellung und Reasoning:** Der W&B-Abschluss ohne explizit übergebene
  Artefaktpfade sollte isoliert mit einer rein synthetischen SDK-Attrappe
  reproduziert werden, bevor ein möglicher Fehler behoben wird.
- **Eingaben/Setup:** Kein Dataset, keine Audio-, Feature-, Teacher- oder
  Testsplit-Artefakte; nur ein Einzeiler mit lokalen Dummy-Klassen und
  `WandbLogger.finish()`.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -c "... WandbLogger(...).finish(...)"`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 1 bereits beim
  Parsen des Einzeilers: `SyntaxError` für eine nicht zulässige
  Klassendefinition hinter einem Semikolon. Der Zielpfad wurde dadurch nicht
  ausgeführt und es wurde kein Projektartefakt geschrieben.
- **Schlussfolgerung und nächster Schritt:** Die Reproduktion wird mit einem
  syntaktisch gültigen, weiterhin rein synthetischen `exec`-Snippet wiederholt;
  erst danach erfolgt gegebenenfalls eine Korrektur mit Regressionstest.

## Testläufe am 2026-08-26 (frischer Cue-Ranker-Audit, reproduzierte Defekte)

- **Fragestellung und Reasoning:** Nach dem Syntaxfehler sollten die beiden
  statischen Verdachtsfälle isoliert nachgewiesen werden: W&B-Abschluss ohne
  übergebene Artefaktpfade und eine fremde Normalizer-Universumsbindung beim
  Format-3-Export.
- **Eingaben/Setup:** Ausschließlich In-Memory-SDK-Dummies beziehungsweise
  synthetische SHA-256-Werte; keine Projekt-Datasets, kein Audio, kein
  Teacher-Release und kein Testsplit.
- **Testumfang bzw. Befehle:**
  1. `.venv\Scripts\python.exe -B -c "... WandbLogger(...).finish(...)")` mit
     synthetischem Run/Artifact-Dummy ohne `artifact_paths`.
  2. `.venv\Scripts\python.exe -B -c "... _normalizer_record(...)")` mit
     unterschiedlichen synthetischen `input_universe_manifest_sha256`-Werten.
- **Ergebnis inklusive Fehlern oder Blockaden:**
  1. Exit-Code 1, reproduzierbar `NameError: name 'config' is not defined` in
     `WandbLogger.finish`; der fehlende W&B-Defaultpfad wäre damit ein
     kontrollierter Trainingsfehler.
  2. Exit-Code 0 mit `MISMATCH_ACCEPTED`: `_normalizer_record()` publizierte
     eine vom aktuellen Universe abweichende Input-SHA und hätte ein erst beim
     Loader unbrauchbares Dataset erzeugen können.
- **Schlussfolgerung und nächster Schritt:** Beide Befunde sind klar
  reproduzierte Defekte. Der W&B-Pfad wird auf die Instanzkonfiguration
  korrigiert; der Dataset-Export verweigert einen fehlenden oder abweichenden
  Input-Universe-SHA. Für beide Korrekturen folgen fokussierte
  Regressionstests, bevor weitere Auditläufe starten.

## Testlauf am 2026-08-26 (frischer Cue-Ranker-Audit, Fix-Regression)

- **Fragestellung und Reasoning:** Die zwei minimalen Korrekturen mussten
  jeweils den reproduzierten Fehler verhindern, ohne die bestehende
  Format-3-Export- oder W&B-Integration zu verändern.
- **Eingaben/Setup:** Nur die vorhandenen synthetischen W&B-Dummies sowie
  Cue-Ranker-Universe-/Teacher-Fixtures; kein reales Training, kein Audio und
  kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_wandb_logging.py tests\test_cue_ranker_dataset.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `8 passed in 2,64 s`,
  Exit-Code 0. Der neue Test belegt den W&B-Abschluss mit instanzgebundenen
  Artefaktpfaden; der neue Exporttest weist die abweichende
  Normalizer-Universums-SHA ab.
- **Schlussfolgerung und nächster Schritt:** Beide Audit-Fixes sind
  regressionsgeprüft. Die Prüfung der verbleibenden Teacher-, Loader-,
  Train-/Resume- und Inferenzgrenzen wird jetzt auf der synthetischen
  Gesamtkette fortgesetzt.

## Testlauf am 2026-08-26 (frischer Cue-Ranker-Audit, Inferenz-Normalizer)

- **Fragestellung und Reasoning:** Der Inferenzloader muss die train-only-
  Normalisierung nicht nur aus dem Datasetmanifest übernehmen, sondern auch
  in der tatsächlich gelesenen Normalizerpayload erzwingen.
- **Eingaben/Setup:** Ausschließlich temporäre synthetische JSON-Datei mit
  absichtlich `fit_scope=all_splits` und ein dazu passender Manifest-Hash;
  kein Modellcheckpoint, kein Audio und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -c "... _load_normalizer(...)")`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 0 mit
  `NORMALIZER_PAYLOAD_SCOPE_ACCEPTED`. Der alte Inferenzpfad akzeptierte die
  widersprüchliche Payload trotz einer deklarativen train-only-Angabe im
  Datasetmanifest.
- **Schlussfolgerung und nächster Schritt:** Dies ist ein dritter
  reproduzierter Defekt an einer Pflichtinvariante. Der Inferenzloader prüft
  nun den effektiven Scope sowie dessen Universe-/Source-SHA-Bindungen;
  ein Regressionstest wird ergänzt.

## Testlauf am 2026-08-26 (frischer Cue-Ranker-Audit, Inferenz-Normalizer-Fix)

- **Fragestellung und Reasoning:** Die Scope-/SHA-Prüfung sollte zusammen mit
  der bestehenden Inferenz-, W&B- und Dataset-Regression laufen.
- **Eingaben/Setup:** Ausschließlich synthetische Testfixtures und lokale
  temporäre Dateien; kein Audio, kein reales Training und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_learned_cue_ranker_integration.py tests\test_wandb_logging.py tests\test_cue_ranker_dataset.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 1: `16 passed, 1
  failed, 2 warnings in 5,54 s`. Der neue Vertragscode lehnte die alte
  Minimalfixture vor ihrem vorgesehenen defekten Checkpoint ab, weil sie die
  Platzhalter-SHAs aus nichthexadezimalem `u`/`s` bildete. Der Codefehler trat
  nicht erneut auf; die Fixture wurde auf gültige, dennoch rein synthetische
  SHA-256-Hexwerte korrigiert.
- **Schlussfolgerung und nächster Schritt:** Die gezielte Regression wird mit
  gültigen Artefaktidentitäten wiederholt. Die zwei Warnungen sind die
  bekannten Audioread-Deprecations aus der bestehenden Rendering-Synthese.

## Testlauf am 2026-08-26 (frischer Cue-Ranker-Audit, Inferenz-Normalizer-Fix wiederholt)

- **Fragestellung und Reasoning:** Mit gültigen synthetischen SHA-256-Werten
  sollte der neue Inferenz-Normalizervertrag den bisherigen
  Checkpoint-Preflight und die bestehenden W&B-/Dataset-Fälle erhalten.
- **Eingaben/Setup:** Nur synthetische Fixtures und temporäre Dateien; kein
  reales Audio, kein Training und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_learned_cue_ranker_integration.py tests\test_wandb_logging.py tests\test_cue_ranker_dataset.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `17 passed, 2 warnings in
  5,86 s`, Exit-Code 0. Der neue Test weist die `all_splits`-Payload ab; der
  defekte Checkpoint wird danach wieder am erwarteten `weights_only`-Load
  abgewiesen. Die Warnungen sind die bekannten Audioread-Deprecations.
- **Schlussfolgerung und nächster Schritt:** Der dritte Audit-Fix ist
  regressionsgeprüft. Es folgen der vollständige synthetische Kettensmoke,
  Teacher-Resume sowie Train-/Resume- und Artefakt-Checks.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, manipulierte Teacher-Cache-Zeile)

- **Fragestellung und Reasoning:** Ein abgebrochener Teacher-Lauf darf beim
  Resume keine nachträglich veränderte Candidate-Cache-Zeile verwenden. Der
  Cache war bisher nur an Kandidat und Release gebunden; deshalb wurde die
  gespeicherte Utility gezielt verändert.
- **Eingaben/Setup:** Vollständig temporäres synthetisches Universe,
  synthetischer abgeschlossener Variable-TCN-Best-Checkpoint und lokaler
  Evaluator. Kein Audio, kein Testsplit, kein echter Teacher-Aufruf.
- **Testumfang bzw. Befehl:** PowerShell-Herestring an
  `.venv\Scripts\python.exe -B -`, der erst labelt, anschließend eine
  `candidate_cache/**/label.json`-Utility auf `999.0` ändert und mit
  `resume=True` fortsetzt.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 1 mit
  `ValueError: teacher_label_shard_immutable_conflict`. Die manipulierte
  Cachezeile wurde zunächst in den Resume-Lauf übernommen und erst beim
  Vergleich mit dem bereits publizierten, unveränderlichen Label-Shard
  entdeckt.
- **Schlussfolgerung und nächster Schritt:** Der Endshard verhindert eine
  stille Veröffentlichung, aber die Resume-Grenze selbst war nicht
  fail-closed. Jede Cachezeile erhält daher eine kanonische Label-SHA sowie
  eine geprüfte Provenance-SHA; ein Regressionstest muss die frühere,
  spezifische Ablehnung beweisen.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, Teacher-Cache-Fix)

- **Fragestellung und Reasoning:** Die Candidate-Cache-SHA und die interne
  Provenance-SHA müssen eine manipulierte Resume-Zeile vor jedem finalen
  Shardvergleich abbrechen lassen und die bestehenden Teacher-Verträge
  erhalten.
- **Eingaben/Setup:** Synthetische Teacher-Releases, Universen und Resolver-
  Fixtures aus `tests/test_cue_ranker_teacher.py`; kein reales Audio, keine
  Datenartefakte und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_teacher.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 0; Pytest meldete
  ausschließlich erfolgreiche Testfortschritte. Der neue Regressionstest
  verändert eine Cache-Utility und erhält nun unmittelbar
  `teacher_label_cache_sha256_mismatch`.
- **Schlussfolgerung und nächster Schritt:** Candidate-Cache-Resumes sind
  nun zeilenweise hashgebunden und fail-closed. Als Nächstes folgt der
  explizite Pair-Index-zu-Inferenz-Smoke mit Offline-W&B und Ranker-Resume.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, E2E-Smoke erster Lauf)

- **Fragestellung und Reasoning:** Der neue synthetische End-to-End-Test soll
  Pair-Index, Universe, Teacher-Labels, Format-3-Export, cache-only Loader,
  Offline-Training/Resume und Learned-Inferenz verbinden.
- **Eingaben/Setup:** Vier rein synthetische Train-/Validation-Track-SHAs,
  temporäre Featurecache-Attrappen und ein synthetischer Teacher-Release;
  keine realen Dateien und kein Testsplit.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_e2e_smoke.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 1, `1 failed in
  4.25 s`: Der E2E-Evaluator hatte die Featureprovenienz, aber nicht die SHA
  des tatsächlich übergebenen Train-only-Normalizers in die Teacherprovenienz
  übernommen. Der Loader brach erwartungsgemäß mit
  `cue_ranker_feature_loader_normalizer_teacher_mismatch` vor Training ab.
- **Schlussfolgerung und nächster Schritt:** Das ist eine unvollständige
  synthetische Fixture, kein Produktionsdefekt: Der echte Resolver bindet
  ohnehin die Release-Normalizer-SHA ein. Die Fixture wird auf dieselbe
  Quell-SHA gebunden; der Lauf wird danach vollständig wiederholt.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, E2E-Smoke zweiter Lauf)

- **Fragestellung und Reasoning:** Nach der korrigierten Normalizerbindung
  sollte die gesamte Kette bis zur Learned-Inferenz abschließen.
- **Eingaben/Setup:** Dieselben ausschließlich temporären synthetischen
  Train-/Validation-Paar-, Cache- und Teacher-Release-Objekte; W&B im
  Offline-Modus. Es gibt keinen Testrecord und keine reale Mediendatei.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_e2e_smoke.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 1, `1 failed in
  27.43 s`: Pair-Index, Universe, Teacher-Labels (einschließlich eines
  Guard-Rejects), Dataset, Offline-Epoche 1 und Resume-Epoche 2 liefen durch.
  Erst die Testhilfsfunktion für die Inferenz übergab einen bereits
  vorhandenen `beat_index` doppelt an `CutPoint`, wodurch `TypeError: got
  multiple values for keyword argument 'beat_index'` entstand. W&B schrieb
  zwei lokale Offline-Runs; die SDK gab zusätzlich eine nicht blockierende
  Zugriffs-Warnung für ihren globalen Debug-Logpfad aus.
- **Schlussfolgerung und nächster Schritt:** Dies ist wiederum nur ein
  Testhilfsfehler nach erfolgreich durchlaufenen Produktionsgrenzen. Die
  doppelte Übergabe wird entfernt, danach erfolgt der vollständige Smoke
  erneut.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, vollständiger E2E-Smoke)

- **Fragestellung und Reasoning:** Die synthetische Freigabekette muss vom
  Pair-Index bis zur geladenen Learned-Inferenz einschließlich des zweiten,
  fortgesetzten Offline-Trainingslaufs deterministisch und SHA-gebunden
  schließen.
- **Eingaben/Setup:** Nur temporäre Train-/Validation-SHAs, Candidate-v2-
  4/4-Grids mit `approximate_grid_policy=reject`, vorbefüllte synthetische
  Featurecache-Artefakte, ein synthetischer abgeschlossener Teacher-Release
  und W&B `offline`; keine Testdatei, kein Testmanifest und kein echtes
  Labeling/Training.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_e2e_smoke.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `1 passed in 12.19 s`,
  Exit-Code 0. Der Test bestätigt Pair-Index → Universe → Teacher-Labels
  (ein `guard_rejected`) → Train-only-Normalizer → Format-3 → cache-only
  Gruppenloader → Offline-Epoche 1 → SHA-geprüftes Resume auf Epoche 2 →
  `weights_only`-geladene Learned-Inferenz. Manifest-, History-, Best- und
  Latest-SHAs wurden im Test maschinell verglichen; die zwei identischen
  Inferenzaufrufe lieferten dieselbe Rangfolge.
- **Schlussfolgerung und nächster Schritt:** Der geforderte kleine
  End-to-End-Smoke ist grün und dauerhaft als Test abgedeckt. Als Nächstes
  werden die vollständigen fokussierten Cue-Ranker-/Render-/W&B-Tests und
  anschließend die gesamte Suite ausgeführt.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, Fokuskommando in vorgegebener Reihenfolge)

- **Fragestellung und Reasoning:** Vor dem breiten Fokus wurde die vom Auftrag
  verlangte Optionenkombination zunächst unverändert verwendet.
- **Eingaben/Setup:** Keine Testfixture wurde initialisiert, da Pytest die
  Kommandozeile vor der Sammlung zurückwies.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q -B -p no:cacheprovider ...` mit den
  Cue-Ranker-, W&B-, Render- und E2E-Testmodulen.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 4:
  `pytest: error: unrecognized arguments: -B`. `-B` ist eine Python-
  Interpreteroption und muss vor `-m pytest` stehen; es wurde kein Test
  ausgeführt und keine Projektartefakte wurden angelegt.
- **Schlussfolgerung und nächster Schritt:** Die semantisch gleiche,
  funktionsfähige Form `.venv\Scripts\python.exe -B -m pytest -q -p
  no:cacheprovider ...` wird für Fokus und Suite verwendet. Der abgewiesene
  vorgegebene Wortlaut bleibt als echte Ausführungsblockade dokumentiert.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, vollständiger Fokus)

- **Fragestellung und Reasoning:** Nach grünem E2E-Smoke müssen alle direkt
  betroffenen Universe-, Teacher-, Dataset-/Loader-, Modell-/Resume-, W&B-
  und Learned-Renderpfade zusammen bestehen, einschließlich des
  deterministischen Render-Backfills.
- **Eingaben/Setup:** Ausschließlich die versionierten synthetischen
  Fixtures; der neue E2E-Smoke verwendet nur temporäre Train-/Validation-
  Artefakte und W&B offline. Kein realer Teacher, kein realer Trainingslauf
  und kein Testsplitzugriff.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_cue_ranker_universe.py tests\test_cue_ranker_teacher.py tests\test_cue_ranker_dataset.py tests\test_cue_ranker_feature_loader.py tests\test_cue_ranker_model.py tests\test_cue_ranker_runner.py tests\test_wandb_logging.py tests\test_learned_cue_ranker_integration.py tests\test_multi_batch_render.py tests\test_cue_ranker_e2e_smoke.py`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `72 passed, 6 warnings in
  27.62 s`, Exit-Code 0. Die vier Librosa-Warnungen sind erwartete kurze
  synthetische Waveforms, die zwei Audioread-Deprecations stammen aus der
  Renderfixture. Keine Warnung betraf Hash-, Split-, Resume- oder
  Backfill-Verträge.
- **Schlussfolgerung und nächster Schritt:** Alle fokussierten
  Pflichtgrenzen sind grün. Anschließend läuft die gesamte Suite in der
  funktional korrekten Interpreteroption-Reihenfolge; die Abweichung vom
  syntaktisch ungültigen vorgegebenen Wortlaut ist oben dokumentiert.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, Gesamtsuite erster Start)

- **Fragestellung und Reasoning:** Nach grünem Fokus wurde die vollständige
  Repositorysuite gestartet, um unbeabsichtigte Fernwirkungen auszuschließen.
- **Eingaben/Setup:** Venv, bytecodefrei und ohne Pytest-Cacheprovider;
  unveränderter Working Tree außer den dokumentierten Audit-Fixes und dem
  synthetischen E2E-Test.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Der externe Testprozess lief
  nach beobachteten erfolgreichen Fortschrittspunkten zu Ende; die
  Terminalbrücke verlor jedoch zwischen zwei Statusabfragen die zugehörige
  Cell-ID und damit Exit-Code sowie Endausgabe. Ein anschließender
  Prozesscheck bestätigte, dass kein Venv-Pythonprozess mehr aktiv war. Dieses
  Ergebnis ist daher nicht als grüne Verifikation wertbar.
- **Schlussfolgerung und nächster Schritt:** Die vollständige Suite wird
  unmittelbar erneut mit längerer, zusammenhängender Ausgabeabfrage gestartet;
  nur deren vollständig beobachtetes Ergebnis wird für das Freigabeurteil
  verwendet.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, Gesamtsuite zweiter Start)

- **Fragestellung und Reasoning:** Die ohne JUnit-Zusatz erneut gestartete
  Gesamtsuite sollte die zuvor nur unvollständig übertragene Endausgabe
  liefern.
- **Eingaben/Setup:** Unveränderter synthetischer Testbestand, Venv,
  Interpreter-`-B` und deaktivierter Cacheprovider.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Nach 40 beobachteten
  Fortschrittspunkten lief der Venv-Pythonprozess innerhalb des nächsten
  30-Sekunden-Fensters aus; die Windows-Terminalbrücke lieferte erneut keine
  Abschlusszeile und keinen verwertbaren Exit-Code zurück.
- **Schlussfolgerung und nächster Schritt:** Auch dieser Lauf ist nicht als
  belastbare grüne Suitewertung verwendbar. Der danach gestartete dritte Lauf
  schreibt deshalb denselben Pytest-Status zusätzlich in ein temporäres
  JUnit-Protokoll.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, vollständige Suite mit JUnit-Nachweis)

- **Fragestellung und Reasoning:** Die Gesamtsuite muss unabhängig von der
  fehlerhaften Langprozess-Ausgabe der Terminalbrücke vollständig und
  maschinell auswertbar sein.
- **Eingaben/Setup:** Unveränderte Venv-Suite, keine Pytest-Caches;
  `C:\Users\max_h\AppData\Local\Temp\beatbridge-cue-ranker-audit-pytest.xml`
  ist ausschließlich ein temporäres JUnit-Testprotokoll außerhalb des
  Repositories.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --junitxml C:\Users\max_h\AppData\Local\Temp\beatbridge-cue-ranker-audit-pytest.xml`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Der nach 45.703 Sekunden
  beendete JUnit-Report enthält `tests=266`, `failures=0`, `errors=0` und
  `skipped=0`; die Maschinenabfrage des XML bestätigte dieselben vier Werte.
  Die Terminalbrücke zeigte nur 49 Fortschrittspunkte und keine
  Abschlusszeile, aber der vollständige Report wurde erst nach regulärem
  Prozessende geschrieben. Es gibt somit keinen Testfehler und keine
  Blockade.
- **Schlussfolgerung und nächster Schritt:** Die komplette Repositorysuite
  ist grün und verifiziert. Der wortgetreue, aber syntaktisch falsche
  Optionsaufbau wird separat noch einmal als vollständiger Befehl protokolliert;
  seine Parserablehnung ändert nicht das grüne Ergebnis der funktional
  korrekten Suite.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, wortgetreues vollständiges Suitekommando)

- **Fragestellung und Reasoning:** Der vom Auftrag genau vorgegebene
  Vollsuite-Befehl wurde zusätzlich wortgetreu ausgeführt, damit die
  Optionsreihenfolge nicht nur aus dem Fokuslauf abgeleitet wird.
- **Eingaben/Setup:** Keine Sammlung oder Fixture-Initialisierung möglich,
  weil Pytest die Interpreteroption bereits beim Parsen zurückweist.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -m pytest -q -B -p no:cacheprovider`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Exit-Code 4 mit
  `pytest: error: unrecognized arguments: -B`; kein Test wurde ausgeführt.
  Der zwingende, komplette Verifikationslauf steht unmittelbar davor mit der
  semantisch identischen, gültigen Schreibweise und JUnit-Nachweis bei 266
  fehlerfreien Tests.
- **Schlussfolgerung und nächster Schritt:** Die Eingabezeile ist als
  Python-/Pytest-Syntax nicht ausführbar. Für alle künftigen Auditläufe muss
  `-B` vor `-m pytest` stehen; die tatsächliche Suitefreigabe basiert auf
  diesem korrekten Interpreteraufruf.

## Testlauf am 2026-08-27 (frischer Cue-Ranker-Audit, finaler vollständiger Suite-Nachweis)

- **Fragestellung und Reasoning:** Nach einer rein kosmetischen Entfernung
  eines unbenutzten Imports im neuen E2E-Test muss der endgültige Working
  Tree nochmals vollständig abgedeckt sein.
- **Eingaben/Setup:** Unveränderte Venv, bytecodefrei, ohne Pytest-
  Cacheprovider. Das JUnit-Protokoll
  `C:\Users\max_h\AppData\Local\Temp\beatbridge-cue-ranker-audit-final-pytest.xml`
  liegt nur temporär außerhalb des Repositories.
- **Testumfang bzw. Befehl:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --junitxml C:\Users\max_h\AppData\Local\Temp\beatbridge-cue-ranker-audit-final-pytest.xml`.
- **Ergebnis inklusive Fehlern oder Blockaden:** Der Prozess beendete sich
  regulär; die maschinelle Auswertung des JUnit-Reports ergibt `tests=266`,
  `failures=0`, `errors=0`, `skipped=0`, `time=48.370 s`. Die
  Terminalvermittlung zeigte während des langen Windows-Laufs nur
  Fortschrittspunkte, aber der vollständige XML-Report bestätigt die
  fehlerfreie Endausführung.
- **Schlussfolgerung und nächster Schritt:** Der finale Stand besteht die
  gesamte Suite. Das Freigabeurteil bleibt wegen fehlender realer,
  ausdrücklich freigegebener Pilotartefakte bedingt; die konkreten
  Voraussetzungen stehen in `STATUS.md`.

## 2026-09-07 – Repository-/Modellübersicht: lesender Artefaktabgleich

- **Fragestellung und Reasoning:** Für die angefragte Funktions-/Modellübersicht
  ältere Smoke-Aussagen mit vorhandenen Runs abgleichen; Architekturpotenzial,
  technische Trainingsbelege und Hörqualität getrennt behandeln.
- **Eingaben/Setup:** Pflichtdokumente, Modell-/Renderer-/Rankingcode,
  Trainingsmanifeste und Historien. Keine Originalaudioänderung, kein Zugriff
  auf Testsplit-Daten; bestehende Nutzerdiffs erhalten.
- **Testumfang/Befehl:** Lesende JSON-Auswertung über
  `.venv\Scripts\python.exe -X utf8 -`; `hashlib.sha256` für `history.json`
  und den manifestierten Best-Checkpoint der Runs
  `variable_tcn_bilstm_waveform_v2_full_20260821` und
  `variable_tcn_bilstm_v2_wandb_20260826`, Vergleich mit
  `manifest.files[key].sha256`.
- **Ergebnis:** 4/4 SHA-Vergleiche stimmen. Manifeststatus jeweils `completed`,
  letzte Epochen 20/29; minimale History-Validation-Losses
  `0.24643995364507038` (Epoche 14) und `0.24559853225946426` (Epoche 23).
  Kein Checkpointload, Training, pytest-Lauf oder Hörtest. Das vorausgehende
  Lesen des ZIP-verpackten Skills scheiterte zunächst bei der Konsolenausgabe
  an cp1252 (`UnicodeEncodeError`); mit `-X utf8` erfolgreich. Anhängen dieses
  Logeintrags mit PowerShell `Add-Content` wurde mit Zugriff verweigert
  abgebrochen; der Eintrag wurde stattdessen mit dem Dateipatchwerkzeug ergänzt.
- **Schlussfolgerung/nächster Schritt:** STATUS und ML_MODEL_CURRENT_STATE
  additiv berichtigt. Vorhandene geblendete Studien bewerten. Die inzwischen
  implementierten Cue-Ranker-CLIs belegen für sich keine reale Rankingqualität.

## 2026-09-09 – LaTeX-Gliederung für die Masterarbeit

- **Fragestellung und Reasoning:** Eine sinnvolle, zum BeatBridge-Projektstand
  passende Kapitelstruktur im vorhandenen Overleaf-Template anlegen, ohne
  unbelegte Ergebnisse oder fertigen Inhalt vorwegzunehmen.
- **Eingaben/Setup:** `overleaf/CGThesis.tex`, `overleaf/meta.tex`, die
  vorhandenen Kapiteldateien sowie `STATUS.md`,
  `Projekt-Gesamtuebersicht.md` und die Agentenanweisungen. Keine Audio- oder
  Python-Dateien verändert.
- **Testumfang/Befehl:** Lesende LaTeX-Strukturprüfung mit PowerShell
  (`Get-ChildItem overleaf -Recurse -File -Include *.tex` und Prüfung der
  referenzierten Kapiteldateien); anschließend Suche nach verfügbaren
  Compilern mit `where.exe pdflatex`, `where.exe xelatex`,
  `where.exe lualatex` und `where.exe tectonic`.
- **Ergebnis:** Alle in `CGThesis.tex` eingebundenen Kapiteldateien sind
  vorhanden. Die Gliederung enthält die Kapitel Introduction, Related Work,
  Methodology, Implementation, Evaluation and Results, Discussion und
  Conclusion sowie einen Appendix. Kein LaTeX-Compiler ist in der Umgebung
  verfügbar, daher konnte kein PDF-Build ausgeführt werden.
- **Schlussfolgerung und nächster Schritt:** Die Arbeitsgliederung ist als
  editierbares Gerüst angelegt. Als Nächstes können Forschungsfragen,
  Methodik und die tatsächlichen Ergebnisse kapitelweise ausgearbeitet und
  anschließend in Overleaf kompiliert werden.

## 2026-09-13 – Repository-/Overleaf-Push-Audit

- **Fragestellung und Reasoning:** Prüfen, ob die auf einem anderen Rechner
  hinzugefügte Overleaf-Arbeit vollständig auf GitHub angekommen ist und sich
  aus einem anderen Checkout reproduzieren lässt.
- **Eingaben/Setup:** Lokaler Branch `main`, Remote `origin` und der nach
  ausdrücklich erlaubtem `git fetch --prune origin` aktualisierte Remote-Ref.
  Bestehende Nutzeränderungen am Notebook und unversionierte IDE-Dateien
  blieben unangetastet.
- **Testumfang bzw. Befehle:** `git status --short --branch`, `git branch -vv`,
  `git rev-list --left-right --count main...origin/main`, `git ls-tree`,
  `git submodule status`, `git cat-file -e`, Prüfung von `.gitmodules`,
  Inventur des lokalen Pfads `overleaf` und Sichtung des einführenden Commits
  `95f7e1d`.
- **Ergebnis inklusive Fehlern oder Blockaden:** `main` und `origin/main` sind
  bei Commit `95f7e1d` synchron (0 voraus, 0 zurück). `overleaf` ist dort nur
  ein Gitlink (Modus `160000`) auf Commit
  `6469dfac57062f654c0d9b4d5b87b6e2f6f9e45d`. Eine `.gitmodules`-Datei und
  damit die Quell-URL fehlen; `git submodule status` bricht entsprechend ab.
  Das referenzierte Commitobjekt ist nicht im Hauptrepo vorhanden, und der
  lokale `overleaf`-Ordner ist leer. Die zuvor protokollierten Dateien
  `CGThesis.tex`, `meta.tex` und Kapiteldateien sind deshalb in diesem
  Checkout nicht verfügbar.
- **Schlussfolgerung und nächster Schritt:** Der Hauptrepo-Push war technisch
  erfolgreich, enthält aber nicht reproduzierbar den Overleaf-Inhalt. Auf dem
  anderen Rechner den verschachtelten Repository-Inhalt entweder als normale
  BeatBridge-Dateien einchecken oder ein echtes Submodule mitsamt
  `.gitmodules` und erreichbarem, separat gepushtem Zielrepository einrichten;
  danach aus einem frischen Checkout gegenprüfen.

## 2026-09-13 – Thesis-Setup-Audit: Bestandsaufnahme, Aufgabenstellung und Toolchain

- **Fragestellung und Reasoning:** Vor inhaltlichem Schreiben den tatsächlichen
  Overleaf-Dateistand, die verbindliche Aufgabenstellung und die lokal verfügbare
  Build-Umgebung prüfen; ältere Statusaussagen nicht als aktuellen Dateinachweis
  behandeln. Bestehende Nutzerdiffs und Originaldateien erhalten.
- **Eingaben/Setup:** Pflichtdokumente, alle zehn Kapitel-/Abstract-/Anhangdateien,
  `CGThesis.tex`, `meta.tex`, `cg.cls`, `bibliography.bib`, relevante Protokolle
  und die unveränderte dreiseitige Aufgabenstellungs-PDF. Lesender
  Vorher-Snapshot unter `/tmp/beatbridge-thesis-setup-audit-20260913/before/`.
- **Testumfang bzw. Befehle:** `git status --short`,
  `git -C overleaf status --short`, `git -C overleaf diff -- CGThesis.tex`,
  `git ls-files --stage .gitmodules overleaf`; Toolinventur per `command -v`
  für `pdftotext pdftoppm pdfinfo latexmk pdflatex xelatex lualatex tectonic biber bibtex node`,
  `pdflatex --version`, `kpsewhich babel.sty`, `kpsewhich ngerman.ldf`,
  `kpsewhich biblatex.sty`, `kpsewhich biber`. PDF-Prüfung:
  `pdfinfo angepasste_aufgabenstellung_masterarbeit.pdf`, danach
  `/usr/bin/pdfinfo angepasste_aufgabenstellung_masterarbeit.pdf`,
  `/usr/bin/pdftotext -layout angepasste_aufgabenstellung_masterarbeit.pdf -`
  und `/usr/bin/pdftoppm -scale-to 1400 -png angepasste_aufgabenstellung_masterarbeit.pdf /tmp/beatbridge-thesis-setup-audit-20260913/assignment`;
  alle drei erzeugten Seiten visuell angesehen.
- **Ergebnis einschließlich Fehlern/Blockaden:** Die Nutzeränderung von `LR`
  auf `MA` war bereits vorhanden und wurde erhalten. Vor dieser Bearbeitung war
  nur Related Work eingebunden; Abstracts und weitere Kapitel enthielten noch
  Template-Material oder nur Überschriften. Die lokale `.gitmodules` ist
  versioniert und der Submodule-Inhalt vorhanden; ältere Leerordner-Aussagen
  treffen auf diesen Stand nicht zu. Keine neue Remote-/Checkout-Prüfung.
  Das zuerst über PATH aufgelöste gebündelte `pdfinfo` scheiterte wegen fehlendem
  `GLIBC_2.38`; dadurch wurde die anschließende `&&`-Kette nicht ausgeführt.
  Die expliziten System-Poppler-Befehle waren erfolgreich. Die Aufgabenstellung
  enthält einen deutschen, aber keinen registrierten englischen Titel; der
  bestehende englische Titel bleibt mit Klärungs-TODO erhalten. PDF-Seite 2
  bestätigt insbesondere 1–4 Takte, GUI/Export, Repräsentations-/Metrikbewertung,
  manuellen Korrekturaufwand und Tanz-Nutzbarkeit als Anforderungen.
  `pdflatex` ist vorhanden (TeX Live 2022/dev/Debian), aber `ngerman.ldf`,
  `biblatex.sty` und Biber wurden nicht gefunden; auch `latexmk` fehlt.
  Der vorgeschriebene Windows-Pythonpfad `.venv/Scripts/python.exe` ist in
  dieser Linux-Umgebung nicht vorhanden. Es wurde kein Python ausgeführt.
- **Schlussfolgerung/nächster Schritt:** Struktur an den tatsächlichen Dateien
  reparieren, empirische Inhalte als TODO belassen und den Buildfehler separat
  protokollieren. Primärliteratur, Registrierung und Prüfungsordnung sind noch
  nicht durch diesen Strukturcheck verifiziert.

## 2026-09-13 – Thesis-Setup-Audit: lokaler LaTeX-Buildversuch

- **Fragestellung und Reasoning:** Die aktivierte vollständige Gliederung mit der
  unveränderten Hochschulklasse kompilieren; ein Quelltextcheck allein belegt
  keine erfolgreiche LaTeX-/Bibliographie-Verarbeitung oder korrekte Seitengestaltung.
- **Eingaben/Setup:** Bearbeitete Overleaf-Quelldateien; Arbeitsverzeichnis
  `/home/max/Documents/BeatBridge/overleaf`; neuer Buildordner einschließlich
  `chapters/` ausschließlich unter `/tmp/beatbridge-thesis-setup-audit-20260913/build/`.
  Der vom PDF-Skill verlangte Artefaktmarker wurde einmal erfolgreich ausgeführt.
- **Testumfang bzw. Befehl:**
  `pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=/tmp/beatbridge-thesis-setup-audit-20260913/build CGThesis.tex`.
- **Ergebnis einschließlich Fehlern/Blockaden:** Exit-Code 1 beim Laden von
  Babel: `Unknown option 'ngerman'`; `ngerman.ldf` fehlt. Kein PDF erzeugt.
  Log: `/tmp/beatbridge-thesis-setup-audit-20260913/build/CGThesis.log`.
  Der Abbruch erfolgt vor Verarbeitung der Kapitel und Bibliographie;
  weitere LaTeX-Fehler sind damit weder nachgewiesen noch ausgeschlossen.
  Biber wurde nicht ausgeführt; zusätzlich fehlt laut Vorprüfung `biblatex.sty`.
- **Schlussfolgerung/nächster Schritt:** Vollständige TeX-Abhängigkeiten
  bereitstellen oder in Overleaf mit `CGThesis.tex` als Hauptdatei bauen.
  `cg.cls` bleibt unverändert; keine Sprach-/Bibliographiepakete wurden entfernt,
  um einen scheinbar erfolgreichen Ersatzbuild zu erzeugen. Nach erfolgreichem
  Build Warnungen und Seiten einschließlich beider Abstracts visuell prüfen.

## 2026-09-13 – Thesis-Setup-Audit: statische Endprüfung und unabhängiger Review

- **Fragestellung und Reasoning:** Aktivierung, Reihenfolge, Referenzintegrität,
  Template-Bereinigung und Erhaltung der bestehenden Literatur-/Nutzerinhalte
  unabhängig von der unvollständigen LaTeX-Installation prüfen.
- **Eingaben/Setup:** Finale LaTeX-Struktur und Vorher-Snapshot. Temporäre
  lesende Node-Prüfung; keine Testsplit-, Checkpoint- oder Audioverarbeitung.
- **Testumfang bzw. Befehle:**
  `/home/max/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node /tmp/beatbridge-thesis-setup-audit-20260913/check_structure.mjs`,
  `git -C overleaf diff --check` und
  `git diff --check -- docs/STATUS.md docs/Bemerkungen.md`.
  SHA-256 des temporären Prüfscripts:
  `e5b4c02c73838c18300f45a7fbdb9ec905d51c3d93675ad40d773c89fc9e6269`.
  Der Strukturcheck entfernt Kommentare, prüft aktive Include-/Inputdateien,
  Kapitelreihenfolge, `MA`/Englisch, lokalen deutschen Sprachwechsel, Anhangmodus,
  einfache Klammer-/Umgebungsbalance, Label-Eindeutigkeit, aktive Referenzen,
  Zitationsfolge/-schlüssel und Template-Reste. Vorher/Nachher-Vergleiche prüfen
  den exakten Titel, Related-Work-Prosa und sämtliche nicht-editoriellen
  Bibliographiefelder. SHA-256-Vergleiche schützen Notebook, Aufgabenstellungs-PDF,
  Schreibpromptdatei und `.gitmodules` gegen Änderungen durch diese Bearbeitung.
  Zusätzlich unabhängiger lesender Strukturreview durch ein anderes Modell mit
  frischem Kontext gemäß Projekt-Skill; keine Tests/Dateiänderungen durch den Reviewer.
- **Ergebnis einschließlich Fehlern/Blockaden:** Node Exit-Code 0, keine
  fehlgeschlagene Prüfung: 10 aktive Includes (2 Abstracts, 7 Hauptkapitel,
  1 Anhang), gewünschte Kapitelreihenfolge, 14 eindeutige aktive Labels,
  0 aktive Querverweise, 43 Zitationsvorkommen mit 38 unterschiedlichen
  Schlüsseln und 38 eindeutigen Bibliographieeinträgen. Alle Zitationen
  auflösbar und gegenüber dem Snapshot unverändert. Alle zehn eingebundenen
  Dateien enthalten konkrete TODOs. Related-Work-Prosa, Titel und nicht-editorielle
  Bibliographiefelder erhalten; vier editorielle Notizen stehen jetzt in Kommentaren.
  Alle vier Schutz-Hashes stimmen. Beide Diff-Whitespace-Prüfungen erfolgreich.
  Nach Ergänzung des Prüfprotokolls und eines reinen Abgabedatum-TODO-Kommentars
  wurden beide genannten `git diff --check`-Prüfungen erneut erfolgreich ausgeführt.
  Der unabhängige Review fand keine umsetzungsrelevanten Strukturfehler.
- **Schlussfolgerung/nächster Schritt:** Die Quelldateien bilden ein konsistentes
  Arbeitsgerüst. Das ersetzt weder TeX/Biber-Kompilation noch Primärquellenprüfung,
  fertige Abstracts oder eine Ergebnisfreigabe. Offene Punkte und Quellen stehen in
  `docs/masterarbeit/THESIS_SETUP_AUDIT.md`. Kein Training, keine Python-/pytest-Suite,
  keine Hörbewertung und kein Commit durch diesen Agenten.

## 2026-09-14 – Thesis-Setup-Reaudit: Aufgabenstellung und Live-Zustand

- **Fragestellung und Reasoning:** Den tatsächlich ausgecheckten Overleaf-Stand
  erneut gegen die Aufgabenstellung prüfen, weil die vorhandene Audit-Dokumentation
  bereits eine reparierte Struktur meldete, der Live-Stand aber weiterhin
  `LR`, deaktivierte Abstracts/Kapitel und Template-Beispiele enthielt.
- **Eingaben/Setup:** `CGThesis.tex`, `meta.tex`, alle Dateien unter
  `overleaf/chapters/`, `bibliography.bib`, `cg.cls`, die Pflichtdokumente,
  relevante Protokolle/Methodikdateien, eine lesende Inventur vorhandener
  Manifest-/History-/Ratingartefakte und die unveränderte dreiseitige
  Aufgabenstellungs-PDF. Keine Audio-, Dataset- oder Checkpointdatei verändert.
- **Testumfang bzw. Befehle:** Zunächst `pdfinfo`, `pdftotext -layout` und
  `pdftoppm` über PATH; anschließend explizit `/usr/bin/pdfinfo`,
  `/usr/bin/pdftotext -layout` und `/usr/bin/pdftoppm -png -r 130`.
  Alle drei gerenderten Seiten wurden visuell geprüft. Zusätzlich
  `git status --short`, `git submodule status` und
  `git -C overleaf status --short`.
- **Ergebnis einschließlich Fehlern/Blockaden:** Der erste Poppler-Aufruf brach
  ab, weil die gebündelte Binary `GLIBC_2.38` verlangt. Die System-Poppler-
  Aufrufe waren erfolgreich: drei A4-Seiten, keine Verschlüsselung oder Formulare,
  vollständige lesbare Darstellung. Die PDF bestätigt den deutschen Titel,
  Masterarbeitsstatus, GUI/Export, Repräsentations- und Metrikevaluation,
  Übergänge von ein bis vier Takten, manuellen Korrekturaufwand und
  Tanz-Nutzbarkeit; sie enthält keinen exakten registrierten englischen Titel.
  Der Overleaf-Submodule-Checkout war sauber und stand auf `6469dfa`, enthielt
  aber den noch nicht reparierten Template-Zustand. Bestehende Diffs in
  `docs/STATUS.md`, `docs/Bemerkungen.md` und das unversionierte Auditdokument
  wurden erhalten und nur auf den nachgewiesenen aktuellen Stand fortgeschrieben.
- **Schlussfolgerung/nächster Schritt:** Den Live-Stand selbst reparieren,
  den englischen Titel bis zur Prüfung des Registrierungsdatensatzes bewahren
  und fehlende Empirie ausschließlich als präzise TODO-Kommentare führen.

## 2026-09-14 – Thesis-Setup-Reaudit: statische Strukturprüfung

- **Fragestellung und Reasoning:** Nach dem Umbau maschinell prüfen, ob beide
  Abstracts, sieben Hauptkapitel und der Anhang aktiv und geordnet sind, ob
  Referenzen/Zitationen auflösbar bleiben und ob Template-Demos entfernt wurden.
- **Eingaben/Setup:** Bearbeitete Overleaf-Quellen und der unveränderte
  Vorher-Snapshot unter
  `/tmp/beatbridge-thesis-setup-audit-20260913/before/`. Der bestehende
  lesende Node-Prüfer wurde wiederverwendet; keine Experimentartefakte wurden
  ausgeführt oder verändert.
- **Testumfang bzw. Befehle:**
  `/home/max/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node /tmp/beatbridge-thesis-setup-audit-20260913/check_structure.mjs`,
  `git -C overleaf diff --check`, Diff-Whitespace-Prüfung der geänderten
  Projektdokumentation sowie `rg` nach den bekannten Template-Texten und
  einem aktiven `LR`-Klassenaufruf.
- **Ergebnis einschließlich Fehlern/Blockaden:** Der erste Strukturcheck
  meldete ausschließlich `bibliography non-editorial fields preserved`,
  weil zunächst auch die vorhandene informative Graph-Cut-`note` entfernt
  worden war. Dieses nicht als Templateplatzhalter belegte Feld wurde
  wiederhergestellt. Die Wiederholung und die abschließende Prüfung bestanden:
  10 aktive Includes, die sieben verlangten Kapitel in richtiger Reihenfolge,
  43 eindeutige Labels, keine aktiven Querverweise, 43 Zitationsvorkommen mit
  38 unterschiedlichen und auflösbaren Schlüsseln, 38 eindeutige
  Bibliographieeinträge sowie mindestens ein Evidenz-TODO in jeder eingebundenen
  Datei. Die Template-Suche und alle Diff-Whitespace-Prüfungen blieben leer.
- **Schlussfolgerung/nächster Schritt:** Die Quellstruktur ist statisch
  konsistent. Das ist kein Ersatz für LaTeX/Biber-Kompilation, visuelle
  PDF-Prüfung, Primärquellenprüfung oder empirische Ergebnisfreigabe.

## 2026-09-14 – Thesis-Setup-Reaudit: lokaler LaTeX-Buildversuch

- **Fragestellung und Reasoning:** Prüfen, ob die vollständige Struktur mit der
  unveränderten Instituts-Klasse lokal kompiliert und damit auch Sprachwechsel,
  Kapitelverarbeitung und Bibliographie technisch validiert werden können.
- **Eingaben/Setup:** Arbeitsverzeichnis `overleaf/`, Ausgabe ausschließlich
  unter `tmp/thesis_setup_audit_20260914/build/`. Der PDF-Artefaktmarker wurde
  unmittelbar vor dem Build genau einmal erfolgreich ausgeführt.
- **Testumfang bzw. Befehl:**
  `pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=/home/max/Documents/BeatBridge/tmp/thesis_setup_audit_20260914/build CGThesis.tex`.
  Vorprüfung per `command -v` und `kpsewhich` für LaTeX-/Bibliographiewerkzeuge
  und `babel.sty`, `ngerman.ldf`, `biblatex.sty`.
- **Ergebnis einschließlich Fehlern/Blockaden:** `pdflatex` ist als TeX Live
  2022/dev/Debian vorhanden, brach aber beim Laden von Babel mit
  `Unknown option 'ngerman'` ab, weil `ngerman.ldf` fehlt. Kein PDF wurde
  erzeugt; Kapitel und Bibliographie wurden nicht erreicht. `latexmk`,
  `biber` und `biblatex.sty` fehlen ebenfalls; nur `bibtex` ist vorhanden,
  obwohl die Klasse Biber verlangt. Der Log liegt unter
  `tmp/thesis_setup_audit_20260914/build/CGThesis.log`.
- **Schlussfolgerung/nächster Schritt:** Vollständige TeX-Abhängigkeiten
  bereitstellen oder in Overleaf mit `CGThesis.tex` als Hauptdokument bauen.
  Danach Biber-Lauf, Referenz-/Warnungsprüfung und visuelle Kontrolle aller
  Seiten einschließlich Titel und beider Abstracts durchführen. Keine
  Klassenabhängigkeit wurde entfernt, um den Build scheinbar erfolgreich zu machen.

## 2026-09-14 – Thesis-Setup-Reaudit: unabhängiger Strukturreview

- **Fragestellung und Reasoning:** Den Mehrdatei-Umbau gemäß Projekt-Skill mit
  frischem Kontext gegen Aufgabenstellung, LaTeX-Struktur und wissenschaftliche
  Evidenzgrenzen kreuzprüfen.
- **Eingaben/Setup:** Read-only-Review durch ein anderes Modell; Pflichtdokumente,
  Aufgabenstellung, aktueller Overleaf-Diff, sämtliche Kapitel und Bibliographie.
  Keine Dateiänderung und kein empirischer Test durch den Reviewer.
- **Testumfang bzw. Befehl:** Manueller Strukturreview von Dokumentklasse,
  Sprachzustand, Abstracts, Kapitelreihenfolge, Titel, Template-Resten, TODOs,
  Labels, Zitationen und Dokumentationskonsistenz.
- **Ergebnis einschließlich Fehlern/Blockaden:** Kein Defekt in der TeX-Struktur.
  Ein Dokumentationswiderspruch wurde gefunden: Der zu Beginn dieses Reaudits
  direkt gelesene Live-Stand enthielt `LR`, während der erhaltene
  Vorher-Snapshot vom 2026-09-13 bereits `MA` enthält und der ältere Logeintrag
  `MA` als erhaltene Nutzeränderung beschreibt. Die Ursache der zwischenzeitlichen
  Abweichung ist nicht belegt. `STATUS.md` und der Auditbericht beschreiben nun
  ausschließlich diese beobachteten Zustände, ohne eine unbelegte Herkunft zu
  behaupten. Zusätzlich wurde der gemeldete Grammatikfehler in `STATUS.md`
  korrigiert. Danach bestand der Node-Strukturcheck erneut mit 10 aktiven
  Includes, 43 eindeutigen Labels, 43 Zitationsvorkommen, 38 auflösbaren
  Bibliographieschlüsseln und ohne Fehler. `git -C overleaf diff --check`
  sowie `git diff --check -- docs/STATUS.md docs/Bemerkungen.md` blieben
  ohne Ausgabe. Die explizite Dateiprüfung bestätigte, dass der fehlgeschlagene
  Build kein `CGThesis.pdf` erzeugt hatte.
- **Schlussfolgerung/nächster Schritt:** Der Reaudit ist nach der
  Dokumentationskorrektur strukturell freigegeben. Vollständige Kompilation,
  visuelle Thesis-Prüfung und Primärquellenaudit bleiben offen.

## 2026-09-16 – Thesis-Blueprint: Aufgabenstellung und Evidenzinventur

- **Fragestellung und Reasoning:** Eine belastbare englische Thesis-Argumentation
  planen, ohne Kapitelprosa zu schreiben und ohne implementierte Pfade,
  Verzeichnisnamen oder ältere Statusaussagen als Ausführungsnachweis zu
  behandeln. Besonders zu trennen waren direkte Control-Optimierung, gelernte
  Controller, Cuepoint-Ranking, fester Vier-Takt-Pfad, variabler
  2/4/6/8-Takt-Pfad, synthetische Tests, Validierungsstudien und historische
  Testnutzung.
- **Eingaben/Setup:** `AGENTS.md`, `.agents/AGENT.md`, vollständig extrahiertes
  `multi-session-project-discipline/SKILL.md`, `docs/STATUS.md`,
  `docs/Projekt-Gesamtuebersicht.md`, relevante Feature-/Dataset-/Control-/
  Ranker-/Rendering-/Hörprotokolle, Modellstands- und GUI-Dokumente,
  relevante Implementierung und Tests, alle LaTeX-Dateien und die unveränderte
  dreiseitige Aufgabenstellungs-PDF. Die PDF wurde mit
  `/usr/bin/pdftotext -layout` extrahiert, mit `/usr/bin/pdftoppm -scale-to 1100
  -png` gerendert und auf allen drei Seiten visuell geprüft. Unfertige
  Antwortschlüssel, Audio, Test-Shards und Tensorpayloads wurden nicht geöffnet.
- **Testumfang bzw. Befehle:** Lesende Inventur per `rg`, `sed`, `jq`, `cat`,
  `git status --short` und `git -C overleaf status --short`. Der temporäre
  `/tmp/beatbridge-blueprint-20260916/check_evidence.sh` prüfte mit `jq` und
  `sha256sum` alle drei lokal vorhandenen Runmanifeste gegen History,
  Best-/Latest-Checkpoint und gebundenes Datasetmanifest sowie die Zähler der
  vollständigen Hörstudien. Checkpoints wurden nur gehasht, nicht geladen.
- **Ergebnis einschließlich Fehlern/Blockaden:** Neun manifestierte Run-Dateien,
  drei Datasetbindungen und drei History-Minimum/Best-/Endepochen-Ketten
  stimmten. Verifiziert wurden der feste MLP-v1-Lauf und zwei historische
  Vocal-MLP-v2-Läufe; die Validation-Proxy-Werte sind ausschließlich
  innerhalb des jeweiligen Laufvertrags interpretierbar. Vier vollständige
  `study_results.json` stimmten mit vollständigen Ratings und Präferenzsummen
  überein. Drei weitere lokale Ratingsätze stehen auf `unrated`. Die später in
  den Dokumenten genannten RoFormer-/Full-Band-/Variable-Runs, Dataset v2 und
  September-Hörsätze fehlen in diesem Checkout; ihre bisherigen Auditbefunde
  wurden als dokumentierte, nicht als frisch verifizierte Primärevidenz
  klassifiziert. Der reale Cue-Ranker bleibt unbelegt; der vorhandene
  End-to-End-Test ist ausdrücklich synthetisch.
- **Schlussfolgerung/nächster Schritt:** Der Blueprint muss aktuelle lokale
  Primärevidenz, frühere Audit-Evidenz und noch erforderliche Versuche sichtbar
  trennen. Vor finalen Ergebnistabellen sind die fehlenden unveränderlichen
  Artefakte wiederherzustellen und erneut zu prüfen. Niedrigere Proxy-Losses
  dürfen nicht als Hörqualität oder Architektur-Rangliste ausgegeben werden.

## 2026-09-16 – Thesis-Blueprint: statische Konsistenz- und Schutzprüfung

- **Fragestellung und Reasoning:** Prüfen, ob der neue Plan alle verlangten
  Bestandteile und die vorhandene LaTeX-Gliederung abdeckt, seine relativen
  Quellenlinks auflösen und die bestehende Thesis-Prosa unverändert bleibt.
- **Eingaben/Setup:**
  `docs/masterarbeit/THESIS_BLUEPRINT.md`, alle Dateien unter
  `overleaf/chapters/` und ein vor der Blueprint-Bearbeitung erzeugtes
  SHA-256-Inventar des gesamten Overleaf-Checkouts. Das temporäre Prüfsystem
  liegt unter `/tmp/beatbridge-blueprint-20260916/`.
- **Testumfang bzw. Befehle:** Zuerst `node
  /tmp/beatbridge-blueprint-20260916/check_blueprint.mjs`; danach wegen
  fehlendem `node` auf PATH explizit
  `/home/max/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
  /tmp/beatbridge-blueprint-20260916/check_blueprint.mjs`. Zusätzlich
  `git diff --check -- docs/masterarbeit/THESIS_BLUEPRINT.md docs/STATUS.md
  docs/Bemerkungen.md`, SHA-256 von Aufgabenstellungs-PDF, `.gitmodules` und
  `docs/masterarbeit/SCHREIBPROMPTS.md` sowie `diff -u` zwischen dem
  Overleaf-Vorher-Inventar und einem neu berechneten Inventar.
- **Ergebnis einschließlich Fehlern/Blockaden:** Der erste Node-Aufruf
  scheiterte mit Exit-Code 127, weil `node` nicht auf PATH liegt. Der erste
  Lauf über den gebündelten Node fand sechs nur in Gross-/Kleinschreibung und
  Benennung abweichende Related-Work-Zeilen im Blueprint. Die Zeilen wurden an
  die tatsächlichen LaTeX-Abschnittstitel angeglichen. Danach bestand der
  Check: genau eine primäre Frage, drei Teilfragen, 31 aufgelöste relative
  Links, Abdeckung aller 47 vorhandenen LaTeX-Abschnitte sowie vorhandene
  Beitrags-, Evidenzmatrix-, Outline-, Negativclaim- und Zitationsgrenzen.
  `git diff --check` blieb leer. Das Overleaf-SHA-Inventar ist bytegenau
  unverändert; auch die drei genannten Schutzdateien wurden nicht bearbeitet.
  Es wurde kein LaTeX-Build gestartet, da ausschließlich ein Markdown-Plan
  angelegt und keine Thesis-Quelle verändert wurde. Kein Python-/pytest-Lauf,
  Training oder Hörtest wurde ausgeführt.
- **Schlussfolgerung/nächster Schritt:** Die Blueprint-Struktur ist statisch
  konsistent und die Thesis-Prosa blieb unverändert. Die in der früheren
  Setup-Prüfung dokumentierte fehlende lokale TeX-Toolchain wird durch diesen
  Markdown-Check weder behoben noch erneut getestet.

## 2026-09-16 – Thesis-Blueprint: unabhängiger Evidenzreview

- **Fragestellung und Reasoning:** Den umfangreichen Plan gemäß
  Multi-Session-Projektdisziplin in frischem Kontext gegen Aufgabenstellung,
  Evidenzklassen, Modellpfade, Hörstatus und Zitationsgrenzen prüfen, bevor er
  als Grundlage für spätere Kapitelprosa dient.
- **Eingaben/Setup:** Read-only-Review durch ein anderes Modell mit
  `THESIS_BLUEPRINT.md`, Pflichtdokumenten, Aufgabenstellung, relevanten
  Protokollen, Quellpfaden und lokal verfügbaren Manifest-/History-/
  Ratingartefakten. Der Reviewer öffnete weder Audio/Test-Shards noch
  unfertige Antwortschlüssel und änderte keine Datei.
- **Testumfang bzw. Befehl:** Semantischer Review von Forschungsfragen,
  Aufgabenstellungsabdeckung, wissenschaftlichen und technischen Beiträgen,
  Claim-to-Evidence-Matrix, allen Kapitelabschnitten, Negativclaims,
  Fixed-vs.-Variable-Trennung, Cue-Ranker-Grenzen, Validation-/Held-out-Sprache,
  lokal fehlenden späteren Artefakten und Quellenverweisen. Der erste
  Reviewversuch wurde vor inhaltlicher Arbeit durch ein Nutzungslimit des
  Review-Agenten beendet. Ein neuer begrenzter Fresh-Context-Review wurde
  anschließend erfolgreich abgeschlossen.
- **Ergebnis einschließlich Fehlern/Blockaden:** Drei konkrete Punkte wurden
  gefunden und korrigiert: (1) P6 bezeichnete irrtümlich H1–H6 insgesamt als
  abgeschlossene Ergebnisdateien, obwohl nur H1–H4 abgeschlossen sind; (2) die
  Aufgabenstellungstabelle führte automatische Tempo-/Beat-/Taktanalyse und
  GUI-Anzeige von Beats, Takten und Segmentgrenzen nicht als eigene Anforderung;
  (3) der Statussatz zum unveränderten registrierten Titel widersprach dem
  offenen Nachweis des exakten englischen Registrierungstitels. Zusätzlich
  wurde die Zuordnung der Repräsentationsbewertung zu SQ1 und der
  Metrikbewertung zu SQ2 explizit gemacht. Der Reviewer fand keine weiteren
  Fehler bei Fragenzahl, Fixed-/Variable-Trennung, Validation-/Held-out-
  Einordnung, synthetischen Ranker-Grenzen, Beitragsmatrix, Dataset-/Run-/
  Ratingzahlen, Zitationsaussagen oder lokalen Quellenpfaden. Nach den
  Korrekturen wurden der Node-Blueprint-Check und der Evidenzcheck erneut
  ausgeführt: weiterhin 1+3 Forschungsfragen, 31 gültige relative Links,
  47 abgedeckte LaTeX-Abschnitte, neun gültige Run-Dateihashes, drei
  Datasetbindungen, drei konsistente Histories und vier konsistente
  abgeschlossene Hörzusammenfassungen. `git diff --check` sowie der erneute
  Overleaf-SHA-Vergleich blieben ohne Ausgabe.
- **Schlussfolgerung/nächster Schritt:** Der korrigierte Blueprint ist als
  evidenzgebundene Planungsgrundlage reviewbar. Die fehlenden Versuche und
  Artefakte bleiben offene Arbeit; der Review wandelt keine dokumentierte oder
  geplante Evidenz in ein Ergebnis um. Vor Thesis-Prosa folgt die fachliche
  Prüfung des Blueprint-Inhalts durch den Nutzer beziehungsweise die Betreuung.

## 2026-09-16 – Related Work: Claim-, Quellen- und Metadatenaudit

- **Fragestellung und Reasoning:** Jeden Absatz des Related-Work-Kapitels auf
  eine durch die zitierte Primärquelle belegte Aussage zurückführen und die
  Positionierung als Vergleich von Problem, Supervision, Output und Evaluation
  formulieren. Dabei mussten Cuepoint-Auswahl, Kompatibilitätsranking,
  Rendering und Control-Lernen getrennt sowie Proxy-Optimierung und
  Perzeptionsnachweis ausdrücklich auseinandergehalten werden.
- **Eingaben/Setup:** Pflichtdokumente und Projekt-Skill, Thesis-Blueprint,
  Feature-, Control-, Ranker- und Render-Metrik-Protokolle, aktueller
  LaTeX-Stand sowie Primärpublikationen beziehungsweise offizielle
  Proceedings-, DOI-, Autoren- und Hochschul-Repositoriumsseiten. Geprüft
  wurden insbesondere die direkten Systeme von Bittner et al., Kim et al.,
  Mosaikbox, DJTransGAN, Robinson und Brown, DJ AI und Hein sowie die
  verwendeten Frontend-, SSL-, Kompatibilitäts- und Evaluationsarbeiten.
- **Testumfang bzw. Befehle:** Zitations-/Bibliographieschlüssel wurden mit
  `rg`, `perl` und `sort -u` inventarisiert. Der Gesamtbuild wurde mit
  `pdflatex -interaction=nonstopmode -halt-on-error
  -output-directory=/tmp/beatbridge_literature_audit CGThesis.tex` versucht.
  Ein isoliertes englisches Testdokument unter
  `/tmp/beatbridge_literature_audit/` wurde mit `pdflatex`, `bibtex` und zwei
  weiteren `pdflatex`-Läufen gebaut. Ein repräsentativer BibLaTeX-Test mit
  `backend=bibtex` wurde zusätzlich gestartet. Abschließend wurden
  Schlüsselgleichheit, Klammer-/Syntaxzustand und Whitespace mit Shell-/Perl-
  Checks sowie `git -C overleaf diff --check` und `git diff --check` geprüft.
- **Ergebnis einschließlich Fehlern/Blockaden:** Das Kapitel wurde auf sieben
  Vergleichsgruppen plus Terminologie und Positionierungssynthese umgebaut.
  23 zitierte Schlüssel besitzen genau 23 Bibliographieeinträge. Das isolierte
  Kapitel ließ sich einschließlich klassischem BibTeX-Lauf zu einem
  neunseitigen Test-PDF bauen; nach der bibliographisch korrekten Einstufung
  der Princeton-Arbeit als BibLaTeX-`@thesis` blieb der abschließende
  BibLaTeX-Lauf lokal blockiert, weil `biblatex.sty` fehlt. Der Gesamtbuild
  scheiterte bereits zuvor an fehlendem `ngerman.ldf`; `latexmk` und Biber sind
  ebenfalls nicht installiert. Es entstand kein Thesis-PDF. Die Fehler sind
  Toolchain-Blockaden und keine durch das Kapitel gemeldeten LaTeX-Syntaxfehler.
  Eine abschließende Link-Stichprobe erkannte außerdem, dass die zunächst
  eingetragene ISMIR-Late-Breaking-Nummer `000036` auf den Spleeter-Abstract
  statt auf die Graph-Cut-Arbeit verwies; der Primärquellenlink wurde auf den
  verifizierten Abstract `000035` korrigiert.
  Kein Python-/pytest-Lauf, Training, Audio-Rendern oder Hörtest wurde
  ausgeführt.
- **Schlussfolgerung/nächster Schritt:** In Overleaf oder einer vollständigen
  TeX-Installation `pdflatex`/Biber/`pdflatex` zweimal ausführen, danach
  undefinierte Zitate, BibLaTeX-Warnungen, Zeilenumbrüche und das sichtbare
  Literaturverzeichnis prüfen. Die zwei erhaltenen TODOs dürfen erst nach dem
  kontrollierten Repräsentationsversuch beziehungsweise einer fixierten
  Perzeptionsauswertung ersetzt werden.

## 2026-09-16 – Englisches Methodology-/System-Design-Kapitel

- **Fragestellung und Reasoning:** Den verifizierten deutschen Methodikentwurf
  sinngemäß in das Overleaf-Kapitel überführen, dabei mathematische und
  methodische Verträge erhalten und jede Aussage nach Evidenzstufe begrenzen.
  Besonders zu prüfen waren Zahlen aus Dataset-/Runmanifesten, die Trennung
  von Fixed- und Variable-Protokoll, synthetischer Cue-Ranker-Verifikation,
  realem Training, Validation-Entwicklung und held-out Evaluation sowie die
  bereits bekannten Toolchain-Blockaden.
- **Eingaben/Setup:** Pflichtdokumente und eingebetteter
  Multi-Session-Projektdisziplin-Skill, deutscher Entwurf, Thesis-Blueprint,
  Setup-Audit, Analysis-/Candidate-/Feature-/Dataset-/Control-/Ranker-/Study-
  Protokolle, aktueller Overleaf-Aufbau und Bibliographie. Lokal vorhanden
  waren zwei Format-1-Datasetmanifeste, drei Format-1-Runmanifeste/-Histories
  und historische Hörartefakte. Die Primärartefakte für Dataset v2, spätere
  RoFormer-/Full-Band-/Variable-Runs und die September-Hörsätze fehlen in
  diesem Checkout; dafür wurden nur die datierten Repository-Audits verwendet.
  Originalaudio, Checkpoints, Manifeste und Hörartefakte wurden nicht geändert.
- **Testumfang bzw. Befehle und Ergebnisse:** Read-only-`jq`-Abgleiche
  bestätigten für die lokalen Datasetmanifeste `45/9/9` und `370/50/60`,
  train-only-Normalisierung und die IDs `f9044dc259b7296c8b28` und
  `52bc9d1cebfd1b82d2ea`. Die lokalen Runmanifeste bestätigten unter anderem
  Parameterzahlen `10.394`/`20.821`, Trainings-Samplerate 11.025 Hz,
  Batchgröße 5, Lernrate `1e-3`, Weight Decay `1e-4`, Gradientengrenze 1,
  Patience 6 und die SHA-gebundene Best-/Latest-/History-Struktur.
  `git -C overleaf diff --check`, ein AWK-Klammercheck, die Prüfung auf
  doppelte Kapitel-Labels und der Abgleich von `lu2024bsroformer` gegen
  `bibliography.bib` bestanden mit Exit-Code 0. Der Gesamtbuild
  `pdflatex -interaction=nonstopmode -halt-on-error
  -output-directory=/tmp/beatbridge-methodology-latex-20260916 CGThesis.tex`
  scheiterte mit Exit-Code 1 vor jeder Kapitelinklusion an fehlendem
  `ngerman.ldf`; es entstand kein Thesis-PDF. Der erste isolierte Kapitelbuild
  erzeugte ein 15-seitiges PDF, meldete aber mehrere Overfull-Boxen und wegen
  des reduzierten Wrappers zunächst undefinierte Referenzen/Zitationen. Nach
  iterativer Umformulierung und einem temporären Bibliographieplatzhalter
  bestanden weitere `pdflatex`-Läufe; der abschließende Lauf erzeugte ein
  16-seitiges PDF mit Exit-Code 0 ohne Warnungen oder Overfull-Boxen. Der
  erste Renderingversuch mit dem gebündelten `pdftoppm` scheiterte an dessen
  nicht verfügbarer GLIBC-2.38-Abhängigkeit. Der Fallback mit Ghostscript
  renderte die Seiten 3 und 11 erfolgreich; Dataset- und Objective-Tabelle
  wurden visuell auf lesbare Spalten, vollständige Werte und Überlauf geprüft.
  Nach der Status- und Logpflege bestanden `git diff --check`,
  `git -C overleaf diff --check` und der erneute Klammercheck mit Exit-Code 0.
  Nach dem abschließenden HT-Demucs-Zitations-TODO bestanden beide Diffchecks,
  der Klammercheck und der erneute Schlüsselabgleich ebenfalls mit Exit-Code 0.
  Die vorgeschriebene Windows-Python-Datei `.venv\\Scripts\\python.exe` ist
  in diesem Linux-Checkout nicht vorhanden; deshalb wurde kein Python-/pytest-
  Lauf gestartet.
- **Ergebnis einschließlich Fehlern/Blockaden:**
  `overleaf/chapters/03_mainPart.tex` enthält nun das englische Kapitel mit
  erhaltenem Kapitel- und allen bisherigen Abschnittslabels. Der Text trennt
  implementierte, technisch verifizierte, real trainierte, evaluierte und
  geplante Arbeit. Format-2-/spätere Runzahlen sind als Audit-only markiert;
  der synthetische Ranker wird nicht als Realergebnis dargestellt; Proxy-Loss
  wird nicht als Perzeptionsnachweis verwendet. Die vorhandene Bibliographie
  wurde nicht verändert. Der Gesamtbuild bleibt ausschließlich an der
  dokumentierten lokalen TeX-Abhängigkeit blockiert; der Kapitelquelltext
  selbst kompiliert isoliert fehlerfrei.
- **Schlussfolgerung/nächster Schritt:** In Overleaf beziehungsweise einer
  vollständigen TeX-Installation den Gesamtbuild mit Biber ausführen und das
  Kapitel im echten Thesis-Layout vollständig visuell prüfen. Vor dem Entfernen
  der LaTeX-TODOs müssen insbesondere Korpusrechte, Format-2-/spätere
  Primärartefakte, Repräsentationsversuch, realer Cue-Ranker, 1-/3-Takt-Fälle,
  gelernte Controller-Hörstudie sowie GUI-, Korrekturaufwands- und
  Tanzevaluation tatsächlich vorliegen. Kein Commit wurde erstellt.

## 2026-09-21 – Evidence-based Implementation-Kapitel

- **Fragestellung und Reasoning:** Den Templateinhalt von
  `overleaf/chapters/04_implementation.tex` durch eine reproduzierbare,
  wissenschaftlich begrenzte Beschreibung der tatsächlich implementierten
  BeatBridge-Pipeline ersetzen. Entscheidend waren die Trennung von
  Feature-Protokoll 1 und 2, festem Full-Band-Renderer und variablem
  Vocal-Renderer sowie implementiertem Code, synthetischer Verifikation,
  realem Training und lediglich geplanter GUI-/End-to-End-Funktionalität.
- **Eingaben/Setup:** Pflichtdokumente und eingebetteter
  Multi-Session-Projektdisziplin-Skill, `STATUS.md`, Exposé, aktuelles
  Methodology-Kapitel, Analysis-/Candidate-/Feature-/Dataset-/Rendering-/ML-/
  Cue-Ranker-/Batch-/GUI-Protokolle, CLI-Dokumentation und die relevanten
  Quellmodule. Primäre lokale Evidenz waren zwei Format-1-Datasetmanifeste,
  drei Format-1-Runmanifeste/-Histories und historische Studienartefakte.
  Format-2-Dataset, spätere Fixed-TCN-/Variable-TCN-Runs und reale
  Cue-Ranker-Artefakte fehlen in diesem Checkout und wurden nicht als frisch
  verifizierte Primärartefakte behandelt.
- **Testumfang bzw. Befehle:** Der erste isolierte Aufruf
  `pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp
  /tmp/beatbridge_impl_check.tex` scheiterte, weil der temporäre Wrapper
  `\cite` zunächst mit `\newcommand` statt `\renewcommand` definierte. Nach
  der Wrapperkorrektur kompilierte das Kapitel. Tabellenbreiten,
  Pseudocodegröße, lange Bezeichner und die Provenienzkette wurden danach
  iterativ korrigiert. Der finale isolierte Doppelaufruf desselben Befehls
  erzeugte ein zehnseitiges PDF ohne LaTeX-Fehler, undefinierte Referenzen
  oder Overfull-Boxen; verblieben sind nur Underfull-Hinweise in schmalen
  Tabellenzellen. `rg` bestätigte neun eindeutige bestehende Kapitel-/
  Abschnittslabels, genau eine Zitation `lu2024bsroformer`, den vorhandenen
  Bibliographieeintrag und vier explizite TODO-Kommentare. Der Gesamtbuild
  `pdflatex -interaction=nonstopmode -halt-on-error CGThesis.tex` scheiterte
  wie dokumentiert vor Kapitelinklusion an fehlendem `ngerman.ldf`; es entstand
  kein Thesis-PDF. Der erste Bildrender-Aufruf über das gebündelte
  `pdftoppm` scheiterte an dessen GLIBC-2.38-Anforderung. `/usr/bin/pdftoppm`
  renderte anschließend Seiten 1, 2, 5 und 6 des isolierten PDFs erfolgreich.
  Architekturabbildung, Statusübersicht, Pseudocode und Controller-/Renderer-
  Tabelle wurden visuell auf Lesbarkeit und Überlauf geprüft. Abschließend
  bestanden `git -C overleaf diff --check` und `git diff --check` mit
  Exit-Code 0. Die beim blockierten Gesamtbuild erzeugte unversionierte
  `overleaf/CGThesis.log` wurde danach wieder entfernt.
- **Ergebnis einschließlich Fehlern/Blockaden:** Das Kapitel beschreibt nun
  Architektur und Datenfluss, Analyse- und Featurecaches, Candidate- und
  Datasetaufbau, optionalen Cue-Ranker, vier Controller-/Rendererpfade,
  Training und Resume, Evaluation, Provenienzkette sowie den aktuellen
  CLI-/Notebook-/HTML-Workflow. Der Variable-TCN-Pfad wird korrekt als
  vocal-aware Objective-v5-Pfad und nicht als Variante des festen
  Drei-Band-EQ-Renderers beschrieben. Der reale Ranker, eine GUI,
  Multi-Track-Assembly und finaler Projekt-Export bleiben ausdrücklich offen.
  Proxy-Loss wird nicht als Perzeptionsnachweis verwendet. Originalaudio,
  Datasets, Checkpoints, Manifeste und Studienartefakte wurden nicht geändert.
- **Schlussfolgerung/nächster Schritt:** Den vollständigen Thesis-Build in
  Overleaf oder einer TeX-Installation mit `ngerman`, BibLaTeX und Biber
  ausführen und das Kapitel im endgültigen Thesis-Layout prüfen. TODOs erst
  nach realem Ranker-Lauf, GUI-/End-to-End-Implementierung, Klärung von
  Korpus- und onTAKT-Rechten sowie Wiederherstellung der fehlenden Format-2-
  und späteren Runartefakte entfernen. Kein Python-/pytest-Lauf, Training,
  Audio-Rendering oder Commit wurde ausgeführt.

## 2026-09-21 – Read-only-Audit des neuen Scantraxx-Ordners

- **Fragestellung und Reasoning:** Ausschließlich den rekursiv neu
  hinzugefügten Ordner `musik\PRIVE Hardstyle Top 1000 of all times - by
  Scantraxx` inventarisieren. Erforderlich waren Audioanzahl/-format,
  exakte SHA-256-Duplikate im Ordner, SHA-Überschneidungen mit dem übrigen
  `musik`-Bestand, Treffer in Analyse-/Feature-/Vocal-Stem-Caches,
  Batchgrößenabschätzung und auffällige Dateien/Metadaten. Da die
  Projektanweisung Rendering, Featureextraktion und Training ausdrücklich
  untersagt, wurden nur Dateisystem-, Hash-, Container-/Tag- und
  CLI-Help-Prüfungen ausgeführt. Originalaudio wurde nicht geöffnet zum
  Dekodieren und nicht geschrieben.
- **Eingaben/Setup:** Repository-Arbeitsbaum am 2026-09-21, `.venv\Scripts\python.exe`
  (Python 3.14.2), FFprobe 8.1 aus dem lokalen PATH. Vorbestehende
  Änderungen `overleaf` (modified) und `prototypes/` (untracked) wurden
  nicht verändert. Zielordner enthielt 399 Dateien: 398 FLAC-Dateien und
  eine 14.430-Byte-Textdatei `Download Report - 21.9.2026, 11:00:12.txt`.
- **Testumfang bzw. Befehle:**
  - `Get-ChildItem musik -Recurse -File` plus Erweiterungs-/Größen- und
    Pfadlängeninventar. Ergebnis: unter `musik` 519 Dateien, davon 517
    Audio-Dateien; außerhalb des Zielordners 119 Audio-Dateien. Der neue
    Ordner umfasst 13.519.656.836 Bytes Audio.
  - SHA-256-Prüfung der 398 Ziel-FLACs mit acht parallelen, gestreamten
    Hash-Läufen über `.venv\Scripts\python.exe` sowie Größen-Vorfilter für
    den Gesamtbestand. Ergebnis: **398 eindeutige SHA-256-Hashes, 0 interne
    Duplikate**. Die einzige gleich große Kandidatenpaarung im Zielordner
    war nicht byteidentisch: `Hit You With That Bang Shit - Adaro.flac`
    (`4ea3bf25c2cf30066e2a719fc1518427ba28f6822c59af448f2dd81b0b971d22`)
    und `Hit you with that bang shit - Radio Edit - Adaro.flac`
    (`06ea7a198b0a21bd5d0b816bbbfe5eb192769f4ca43a16ad927853b68ac4a972`).
  - SHA-Überlappungsprüfung gegen alle übrigen Audio-Dateien unter `musik`.
    Für eine vollständige Duplikatentscheidung wurden alle zwei mehrfach
    vorkommenden Dateigrößen (nur vier Dateien) gehasht; unterschiedliche
    Dateigrößen können keinen gleichen SHA-256 besitzen. Ergebnis:
    **0 Zieldateien mit SHA-Überschneidung**. Die bekannte externe
    Duplikatgruppe `musik\07 - BREATH_LESS.flac` und
    `musik\Deezl - BREATH_LESS.flac` hat SHA-256
    `acc1e30d0698b39b23add02b3806648c74eecc937d7c27a933e33266153c5c99`,
    liegt aber vollständig außerhalb des neuen Ordners.
  - FFprobe-Metadatenprüfung aller 398 FLACs ohne Dekodierung:
    `ffprobe -v error -show_entries ... -of json`. Ergebnis: 398/398
    erfolgreich, jeweils FLAC/16-bit/44.100 Hz/2 Kanäle, Dauer 117,016 bis
    530,924 Sekunden, Gesamtdauer 102.612,283 Sekunden bzw. 28,5034
    Stunden. Jede Datei besitzt einen FLAC-Audiostream und einen
    eingebetteten MJPEG-Coverstream; das ist erwartete Cover-Art und kein
    zweiter hörbarer Audiostream.
  - Tag-/Namensprüfung mit FFprobe, Unicode-/Casefold-Gruppierung und
    Größen-/Pfadlängenprüfung. `title`, `artist` und `album` sind in allen
    398 Dateien vorhanden; Datums- und numerische Track-/Disc-Tags waren
    formal gültig. Optional fehlen `composer` in 223, `publisher` in 2,
    `copyright` in 3 und die vier Disc-/Track-Totalfelder in jeweils 1
    Datei. In allen Dateien existieren sowohl `COMMENT` als auch `comment`
    (zwei unterschiedlich geschriebene Kommentar-Tags); das sollte vor
    einer späteren Metadaten-Normalisierung bewusst entschieden werden.
    Auffällige, aber technisch zulässige Namen sind führendes `#` sowie
    Unicode-Zeichen wie `Alpha²` und das Fullwidth-Zeichen `？` in `Huh？`.
    Es gab keine case-insensitiven oder NFC-normalisierten Dateinamen-
    Duplikate, keine kleinen/0-Byte-Audiodateien und keinen Pfad über 142
    Zeichen. Die Textdatei ist ein Downloader-Fehlerbericht mit 51
    nummerierten Fehlversuchen/fehlenden Downloads, keine Audiodatei.
  - Cacheprüfung ohne Öffnen von NPZ-/Audio-Payloads: JSON-Manifeste und
    64-stellige Cachepfad-SHAs unter `output\pre_analysis*` und
    `output\feature_cache*` wurden gegen alle 398 Ziel-SHAs verglichen;
    zusätzlich wurden Legacy-Analyse-TXT-Dateien auf Zielnamen geprüft.
    Geprüfter Bestand: 118 `analysis.json`, 73 Format-1-Featuremanifeste,
    122 Variable-v2-Featuremanifeste, 64 Demucs-Vocal-Stemmanifeste und 55
    RoFormer-Vocal-Stemmanifeste (zusätzlich 68 Stem-Payloads im separaten
    Variable-v2-Root). Ergebnis: **0 Analyse-, 0 Feature- und 0
    Vocal-Stem-Cachetreffer**; auch 16-stellige Cacheprefixe trafen nicht.
    Legacy-Analyse-TXT-Treffer nach Dateinamen: 0.
  - CLI-Vertragsprüfung: `.venv\Scripts\python.exe -m src.multi_batch_render
    --help`, `.venv\Scripts\python.exe -m src.features --help`,
    `.venv\Scripts\python.exe -m src.ml --help` sowie die Help-Aufrufe der
    relevanten Cache-/Train-Unterbefehle. Ergebnis: Ordner werden von
    `multi_batch_render` rekursiv expandiert; der Befehl dedupliziert per
    SHA-256 und rendert danach. Es gibt keinen offiziellen Analyse-only-
    CLI. Es wurde kein Multi-Batch, keine Analyse für diesen Ordner, keine
    Featureextraktion, kein Vocal-Stem-Lauf, kein Waveformcache, kein
    Rendering und kein Training ausgeführt.
- **Ergebnis einschließlich Fehlern/Blockaden:** Der neue Bestand ist ein
  technisch konsistenter Satz von 398 eindeutigen, stereo 44,1-kHz-
  16-bit-FLACs mit eingebettetem Cover-Art. Es bestehen keine exakten
  Überschneidungen mit dem übrigen `musik`-Audio und keine verwertbaren
  bestehenden Analyse-/Feature-/Vocal-Caches. Die Metadatenrisiken sind
  optional fehlende Felder, doppelte Kommentar-Schreibweisen und einige
  Unicode-/führende-`#`-Namen; die Container-/Audioheader selbst zeigten
  keinen FFprobe-Fehler.
- **Batchumfangsschätzung:** Nach Filterung sei `N` die Zahl der Tracks,
  die BPM-/Grid-Policy und Ausschlüsse passieren. Dann erzeugt
  `multi_batch_render` höchstens `N * min(top-targets, N-1)` Songpaare.
  Bei allen 398 Tracks wären das bei `--top-targets 1` 398 Paare, bei
  Default `--top-targets 3` 1.194 Paare. Mit einem Renderer und
  `--top-transitions 1` beziehungsweise `3` sind das 398 bzw. 1.194 WAVs
  (Default-Targets plus 3 Transitions: 3.582 WAVs). Als grobe Candidate-
  Referenz liefert der bereits dokumentierte 111-Paar-Lauf 1.730.938
  Candidates, also etwa 15.594 pro Paar; daraus folgen grob 6,2 Mio.
  Candidates bei 398 Top-1-Paaren beziehungsweise 18,6 Mio. bei 1.194
  Paaren. Das ist nur eine Ressourcenabschätzung: BPM-/Grid-Ausschlüsse,
  Tracklängen und Fehler können `N` und die tatsächlichen Counts deutlich
  senken. BPM wurde in diesem Audit bewusst nicht analysiert.
- **Konkreter späterer Ausführungsplan; in dieser Session nicht ausgeführt:**
  1. Zuerst ein begrenzter Pilot auf 20 deterministisch sortierten FLACs;
     neuer Analyse- und Outputroot, vier Takte, ein Ziel, eine Transition,
     ein Renderer, strikte Grid-Policy. Das prüft Ressourcen und Failure-
     Klassen, ohne bestehende Artefakte zu überschreiben:

     ```powershell
     $pilotTracks = @(Get-ChildItem -LiteralPath 'musik\PRIVE Hardstyle Top 1000 of all times - by Scantraxx' -File -Filter '*.flac' | Sort-Object FullName | Select-Object -First 20 -ExpandProperty FullName)
     & .venv\Scripts\python.exe -m src.multi_batch_render @pilotTracks `
       --output-dir output\batches\scantraxx_pilot_20260921 `
       --analysis-location output\pre_analysis_scantraxx_pilot_20260921 `
       --analysis-workers 8 --top-targets 1 --top-transitions 1 `
       --renderers equal_power --transition-bars 4 `
       --approximate-grid-policy reject --min-bpm 145 --max-bpm 165 `
       --track-exclusions config\track_exclusions.json
     ```

  2. Nach Prüfung des Pilot-Manifests den vollständigen, noch begrenzten
     Top-1/Top-3-Batch ausführen. `multi_batch_render` akzeptiert den
     Zielordner rekursiv; `--analysis-location` und `--output-dir` sind neu:

     ```powershell
     & .venv\Scripts\python.exe -m src.multi_batch_render `
       'musik\PRIVE Hardstyle Top 1000 of all times - by Scantraxx' `
       --output-dir output\batches\scantraxx_top1_top3_20260921 `
       --analysis-location output\pre_analysis_scantraxx_20260921 `
       --analysis-workers 8 --top-targets 1 --top-transitions 3 `
       --renderers equal_power --transition-bars 4 `
       --approximate-grid-policy reject --min-bpm 145 --max-bpm 165 `
       --track-exclusions config\track_exclusions.json
     ```

  3. Erst wenn das Batch-Manifest fehlerfrei und die BPM-/Grid-Ausschlüsse
     fachlich akzeptiert sind, die darin akzeptierten Songs in einen neuen
     Feature-/Vocal-Cache extrahieren. Das ist der erste ausdrücklich teure
     Feature-/Stem-Schritt und bleibt bis zur Freigabe ungestartet:

     ```powershell
     $batch = Get-Content -Raw output\batches\scantraxx_top1_top3_20260921\manifest.json | ConvertFrom-Json
     foreach ($song in $batch.songs) {
       & .venv\Scripts\python.exe -m src.features cache-track $song `
         --cache-root output\feature_cache_scantraxx_20260921 `
         --analysis-root output\pre_analysis_scantraxx_20260921 `
         --sample-rate 44100 --vocal-backend roformer `
         --vocal-model roformer-model-bs-roformer-sw-by-jarredou
       if ($LASTEXITCODE -ne 0) { throw "cache-track failed: $song" }
     }
     ```

  4. Einen neuen, trackgetrennten Format-1-Datensatz exportieren; der
     Zielordner muss neu sein. Dieser Befehl extrahiert bei Cache-Miss noch
     fehlende Ziel-BPM-/Cue-Varianten und ist daher erst nach Cacheprüfung
     und Ressourcenfreigabe auszuführen:

     ```powershell
     & .venv\Scripts\python.exe -m src.features export-dataset `
       output\batches\scantraxx_top1_top3_20260921\manifest.json `
       output\datasets\scantraxx_feature_protocol_v1_top1_top3_20260921 `
       --cache-root output\feature_cache_scantraxx_20260921 `
       --analysis-root output\pre_analysis_scantraxx_20260921 `
       --top-k-per-pair 3 --transition-bars 4 --split-seed 20260921 `
       --min-bpm 145 --max-bpm 165 --vocal-backend roformer `
       --vocal-model roformer-model-bs-roformer-sw-by-jarredou `
       --track-exclusions config\track_exclusions.json
     ```

  5. Vor jedem ML-Lauf nur die ausdrücklich vorgesehenen Train-/Validation-
     Waveformcaches aufbauen; den Testsplit nicht materialisieren, wenn kein
     unabhängiger Testlauf autorisiert ist:

     ```powershell
     & .venv\Scripts\python.exe -m src.ml cache-vocal-waveforms `
       output\datasets\scantraxx_feature_protocol_v1_top1_top3_20260921 `
       --split train --cache-root output\ml_cache\scantraxx_vocal_bridge_20260921 `
       --training-sample-rate 11025
     & .venv\Scripts\python.exe -m src.ml cache-vocal-waveforms `
       output\datasets\scantraxx_feature_protocol_v1_top1_top3_20260921 `
       --split validation --cache-root output\ml_cache\scantraxx_vocal_bridge_20260921 `
       --training-sample-rate 11025
     ```

  6. Training bleibt ein separater, explizit freizugebender Schritt. Für den
     Format-1-Vocal-Runner wäre der konkrete Einstieg:

     ```powershell
     & .venv\Scripts\python.exe -m src.ml train-vocal `
       output\datasets\scantraxx_feature_protocol_v1_top1_top3_20260921 `
       output\training_runs\scantraxx_vocal_mlp_v2_seed20260921 `
       --cache-root output\ml_cache\scantraxx_vocal_bridge_20260921 `
       --feature-cache-root output\feature_cache_scantraxx_20260921 `
       --device auto --wandb-mode disabled --seed 20260921
     ```

     Der Befehl wurde nicht ausgeführt; vor einem realen Lauf müssen
     Datasetgröße, Speicher-/VRAM-Budget, Track-Split, Cachevollständigkeit
     und ein unabhängiger Auswertungsplan geprüft werden. Variable-v2- oder
     Cue-Ranker-Pfade bleiben bis zur expliziten Veröffentlichung einer
     passenden Split-Autorität und Provenienzkette zurückgestellt.
- **Schlussfolgerung/nächster Schritt:** Der Audit ist abgeschlossen und
  liefert eine belastbare Nullbasis für neue Cachematerialisierung. Als
  nächster Schritt genügt bei Freigabe der 20-Track-Pilot; bis dahin werden
  keine Audiodateien, bestehenden Caches, Manifeste oder Trainingsartefakte
  verändert. Der abschließende `git diff --check -- docs/Bemerkungen.md`
  bestand. Kein Commit wurde erstellt.

## 2026-09-21 — Preflight und Multi-Song-Batch PRIVE Top 1000

- **Fragestellung und Reasoning:** Der neu hinzugefügte Ordner `musik\\PRIVE
  Hardstyle Top 1000 of all times - by Scantraxx` sollte ausschließlich mit
  der bestehenden Multi-Batch-Pipeline verarbeitet werden. Vor dem Lauf waren
  die verpflichtenden Projektdateien `AGENTS.md`, `docs/STATUS.md`,
  `docs/Projekt-Gesamtuebersicht.md`, `.agents/AGENT.md` und
  `.agents/multi-session-project-discipline.skill` gelesen. Der Zielpfad
  `output\\batches\\prive\\_top1000\\_baseline\\_20260921` war neu bzw.
  leer; Original-Audiodateien und bestehende Outputs wurden nicht zum
  Überschreiben freigegeben.
- **Setup und Preflight:** Python wurde ausschließlich über
  `.venv\\Scripts\\python.exe` verwendet. Ausgeführt wurden u. a.:

  ```powershell
  ffmpeg -hide_banner -version
  ffmpeg -hide_banner -filters
  ffmpeg -hide_banner -h filter=rubberband
  rubberband --version
  .\\aufTAKTCl.exe --help
  ```

  FFmpeg 8.1 (`www.gyan.dev`) war vorhanden und mit
  `--enable-librubberband` gebaut; der `rubberband`-Filter war verfügbar.
  Eine eigenständige `rubberband`-CLI war nicht im PATH, wurde für diesen
  Lauf aber nicht benötigt, weil die Pipeline den FFmpeg-Librubberband-Pfad
  nutzt. `aufTAKTCl.exe` war vorhanden (Version `4.2.0+e2277a`, gebaut am
  03.03.2023); `--help` lief bis zur erwarteten Meldung zum fehlenden
  `-inputFile`. Die Binary-Prüfsumme war
  `35F9149CFEF66DF9B7AC7716953F859F2D34AF1BEB2D2DB231062A4A1B523`.
- **Verarbeitung/Befehl:** Der exakt verwendete Pipeline-Befehl war:

  ```powershell
  & .venv\\Scripts\\python.exe -u -m src.multi_batch_render `
    'musik\\PRIVE Hardstyle Top 1000 of all times - by Scantraxx' `
    --output-dir output\\batches\\prive\\_top1000\\_baseline\\_20260921 `
    --ranking-method feature_baseline_v3 `
    --top-targets 1 --top-transitions 1 `
    --renderers equal_power --transition-bars 2 4 `
    --min-bpm 145 --max-bpm 165 `
    --analysis-workers 4 `
    --analysis-location output\\pre_analysis\\prive_top1000_baseline_20260921 `
    --approximate-grid-policy reject `
    --track-exclusions config\\track_exclusions.json
  ```

  Der erste Versuch analysierte alle 398 Titel, scheiterte anschließend aber
  beim Anlegen von `output\\batches\\prive` mit `PermissionError`/WinError 5;
  es wurden keine Batchdateien geschrieben. Der zweite Versuch las danach
  398 vorhandene Analyse-JSONs aus dem separaten Analyse-Root, scheiterte aber
  erneut beim atomaren Root-Manifest-Tempfile mit WinError 5; auch der
  Zielordner blieb leer. Nach einer einmaligen, exakt auf den neuen Zielpfad
  begrenzten Dateischreibfreigabe wurde derselbe Befehl erneut ausgeführt.
  Dieser freigegebene Lauf erreichte das Root-Manifest und lief bei
  Einzelfehlern weiter; Prozess-Exitcode war `1`, weil Fehler aufgezeichnet
  wurden.
- **Ergebnis und Manifestprüfung:** Verifiziert mit
  `.venv\\Scripts\\python.exe` und `manifest.json` unter
  `output\\batches\\prive\\_top1000\\_baseline\\_20260921`:

  - rekursiver Eingang: 398 Audiofiles; Analyse erfolgreich/cachevalidiert:
    398; BPM-Bereich akzeptiert: 321;
  - BPM-ausgeschlossen: 77 (74 unter 145 BPM, 3 über 165 BPM);
    Analysefehler: 0; konfigurierte Ausschlüsse: 0; SHA-Duplikate im
    Zielordner: 0;
  - 321 Sources wurden als `completed` gerankt und erhielten jeweils ein
    ausgewähltes Ziel; 321/321 Pair-Aufrufe scheiterten jedoch vor der
    Candidate-Erzeugung mit demselben Fehler:
    `generate_and_render_batch() got an unexpected keyword argument
    'cue_ranker'`;
  - erfolgreiche Songpaare: 0; erfolgreiche Renderings: 0; Pair-Manifeste
    und WAV-Ausgaben: 0. Im Batch-Root liegt nur `manifest.json` (ca. 98,5
    MB), keine Audiodatei;
  - Candidate-Rejections: nicht bestimmbar/nicht erreicht, weil alle Paare
    vor `generate_transition_candidates` abbrachen; häufigste persistierte
    Pair-Rejection ist daher keine Candidate-Rejection, sondern der genannte
    `TypeError` (321 Fälle);
  - Analyse-Backends: `librosa.beat.beat_track` für Beat-Tempo und
    `zplane_AUFTAKT_aufTAKTCl` für Bar-Metadaten; ein Rendering-Tempo-/Stretch-
    Backend wurde nicht verwendet, weil kein Render- oder
    Transition-Metric-Schritt erreicht wurde;
  - Root-Konfiguration verifiziert: `feature_baseline_v3`, ausschließlich
    `equal_power`, Übergänge `[2, 4]` Takte, `top_targets_per_source=1`,
    `top_transitions_per_pair=1`, BPM `[145, 165]`,
    `analysis_workers=4`, `approximate_grid_policy=reject` und
    `config\\track_exclusions.json`.
- **Zusatzprüfungen:** Die Root-Datei wurde rekursiv auf Pair-Manifeste und
  WAVs geprüft (jeweils 0). Der Fehler wurde gegen den Quellcode abgeglichen:
  `src\\multi_batch_render.py` übergibt in Zeile 193 `cue_ranker=...`,
  während `src\\batch_render.py::generate_and_render_batch` keinen Parameter
  dieses Namens akzeptiert und stattdessen `cue_ranker_run`/verwandte
  Provenienzparameter führt. Es wurden keine Codeänderungen vorgenommen.
  `git status --short` zeigte keine Änderungen unter `musik` oder den
  bestehenden Outputs; es wurden keine Audiodateien verändert. Training,
  zusätzliche Featureextraktion und Vocal-Stem-Extraktion wurden nicht
  ausgeführt.
- **Schlussfolgerung/nächster Schritt:** `docs/STATUS.md` wird nicht
  aktualisiert, weil kein verifizierter Render-Meilenstein vorliegt. Vor
  einem neuen Lauf muss die bestehende API-Inkompatibilität zwischen
  `multi_batch_render.py` und `batch_render.py` projektseitig korrigiert und
  mit einem kleinen neuen Zielpfad getestet werden. Danach kann derselbe
  oben dokumentierte Befehl in einem neuen, nicht überschriebenen Batchpfad
  erneut laufen; die 398 Analyse-JSONs im separaten Analyse-Root können dabei
  wiederverwendet werden. Kein Commit wurde erstellt.

## 2026-09-21 — API-Fix und erfolgreicher PRIVE-Top-1000-Batch

- **Fragestellung und Reasoning:** Der zuvor dokumentierte Batch scheiterte
  in allen 321 Pair-Aufrufen an einer API-Inkompatibilität: `src\\multi_batch_render.py`
  übergab `cue_ranker=...`, obwohl `src\\batch_render.py::generate_and_render_batch`
  diesen Parameter nicht akzeptiert. Für `feature_baseline_v3` wird dieser
  optionale Learned-Ranker nicht benötigt; daher wurde ausschließlich diese
  veraltete Keyword-Übergabe entfernt. Die `cue_ranker_run`- und übrigen
  Provenienzparameter blieben unverändert.
- **Setup und Patchprüfung:** Geändert wurde nur
  `src\\multi_batch_render.py`; `git diff --check -- src/multi_batch_render.py`
  bestand. Zusätzlich wurde
  `.venv\\Scripts\\python.exe -m src.multi_batch_render --help` ausgeführt.
  Der vorherige Fehl-Output blieb erhalten; der neue Lauf verwendete den
  nicht überschreibenden Pfad
  `output\\batches\\prive\\_top1000\\_baseline\\_20260921_fixed`.
- **Verarbeitung/Befehl:** Ausgeführt wurde mit `.venv\\Scripts\\python.exe`:

  ```powershell
  & .venv\\Scripts\\python.exe -u -m src.multi_batch_render `
    'musik\\PRIVE Hardstyle Top 1000 of all times - by Scantraxx' `
    --output-dir output\\batches\\prive\\_top1000\\_baseline\\_20260921_fixed `
    --ranking-method feature_baseline_v3 `
    --top-targets 1 --top-transitions 1 `
    --renderers equal_power --transition-bars 2 4 `
    --min-bpm 145 --max-bpm 165 `
    --analysis-workers 4 `
    --analysis-location output\\pre_analysis\\prive_top1000_baseline_20260921 `
    --approximate-grid-policy reject `
    --track-exclusions config\\track_exclusions.json
  ```

  Der Lauf beendete sich mit Exit-Code `0`. Original-FLACs, der vorherige
  Fehl-Output und bestehende Nutzeränderungen wurden nicht überschrieben.
  Training, zusätzliche Vocal-Stem-Extraktion und ein separater
  Feature-Extraktionslauf wurden nicht ausgeführt.
- **Root-Manifest und Verarbeitungsergebnis:** Geprüft wurde
  `output\\batches\\prive\\_top1000\\_baseline\\_20260921_fixed\\manifest.json`;
  der Root enthielt 321 Pair-Manifeste, 122 WAVs und war 93,86 MiB groß.

  - rekursiver Eingang: 398 Audiodateien; 321 nach BPM-Filter akzeptiert;
    77 ausgeschlossen (74 unter 145 BPM, 3 über 165 BPM);
  - konfigurierte Track-Ausschlüsse: 0; SHA-Duplikate im Zielordner: 0;
    Analysefehler: 0; Cross-Ordner-SHA-Überschneidungen: 0;
  - Sources: 321/321 `completed`; Songpaare: 321/321 `completed`;
    Pair-Fehler: 0; Renderfehler: 0; Übergangsmetrikfehler: 0;
  - erfolgreiche Renderings: 122 Varianten als 122 WAVs, ausschließlich
    `equal_power`; 199 Paare hatten wegen fehlender Kandidaten keine
    Rendering-Variante;
  - Candidate-Rejections: `incompatible_transition_meter` 70.374,
    `target_grid_provenance_rejected` 138, `source_grid_provenance_rejected`
    136 und `invalid_source_grid` 1;
  - tatsächlich verwendete Tempo-/Analyse-Backends: BPM/Beat
    `librosa.beat.beat_track`, Bar-Metadaten `zplane_AUFTAKT_aufTAKTCl`;
    für alle 122 Renderings war der Stretch-/Tempo-Backendstatus
    `not_needed`, da keine Tempoänderung erforderlich war. FFmpeg mit
    librubberband war vorab geprüft, wurde für diese gleich-tempo
    Renderings aber nicht als Stretch-Backend benötigt;
  - Analyse-Cache: 398 Analyse-JSONs im separaten Root vorhanden; vor dem
    Lauf waren keine passenden Feature- oder Vocal-Stem-Cache-Treffer
    vorhanden. Die Baseline-Features wurden im regulären Pair-Verlauf
    verarbeitet.
- **Schlussfolgerung/nächster Schritt:** Der API-Fix ist durch einen
  vollständigen, fehlerfreien Multi-Song-Lauf verifiziert. Für den nächsten
  Lauf empfiehlt sich ein gezielter Kandidaten-/Grid-Audit der 199 Paare ohne
  Kandidat, insbesondere der häufigen `incompatible_transition_meter`-Fälle,
  bevor ein größerer Renderer- oder Learned-Ranker-Lauf gestartet wird. Kein
  Commit wurde erstellt.

## 2026-09-23 — Fehlversuch beim Syntaxcheck der Dataset-v2-Erweiterung

- **Fragestellung und Reasoning:** Früher Syntaxcheck der neuen additiven
  Producer-, Splitgruppen-, Waveformcacheindex- und Trainingsvertragsmodule,
  bevor funktionale Tests ausgeführt werden.
- **Eingaben/Setup:** Repository-Worktree; `.venv\Scripts\python.exe`; vier
  geänderte Pythonmodule, keine Audioeingaben.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -m py_compile src\variable_producer.py src\features\variable_split.py src\ml\variable_waveform_cache.py src\ml\variable_runner.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** Der Lauf endete mit
  Exit-Code 1, bevor der Syntaxcheck abgeschlossen war. Python konnte die
  temporäre Bytecodedatei unter `src\__pycache__` wegen `PermissionError:
  [Errno 13]` nicht anlegen. Es liegt damit kein festgestellter Syntaxfehler,
  sondern eine lokale Schreibblockade des Bytecodecaches vor.
- **Schlussfolgerung und nächster Schritt:** Den identischen Check mit `-B`
  beziehungsweise `PYTHONDONTWRITEBYTECODE=1` wiederholen und anschließend
  die fokussierten synthetischen Regressionstests ausführen.

## 2026-09-23 — Schreibfreier Syntaxcheck der Dataset-v2-Erweiterung

- **Fragestellung und Reasoning:** Nach der Bytecache-Blockade sollte die
  Syntax derselben vier Module ohne Seiteneffekt geprüft werden.
- **Eingaben/Setup:** `.venv\Scripts\python.exe -B`; Quelltexte wurden mit
  `ast.parse` nur gelesen, kein Bytecode geschrieben.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -c "import ast,pathlib; files=['src/variable_producer.py','src/features/variable_split.py','src/ml/variable_waveform_cache.py','src/ml/variable_runner.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('AST syntax OK:', len(files))"
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** Exit-Code 0;
  `AST syntax OK: 4`.
- **Schlussfolgerung und nächster Schritt:** Die Module sind syntaktisch
  gültig; als Nächstes folgen fokussierte synthetische Funktions- und
  Regressionstests.

## 2026-09-23 — Erster fokussierter Regressionstest der Implementierung

- **Fragestellung und Reasoning:** Prüfung des neuen candidate-only Producers,
  der Recording-Group-Splitfortschreibung, des Cacheindexes und des
  TCN/BiLSTM-Vertrags gegen die vorhandenen synthetischen Tests.
- **Eingaben/Setup:** Ausschließlich Pytest-Fixtures in temporären
  Verzeichnissen; keine private Musik, keine Stems und keine Modellgewichte.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_producer.py tests/test_variable_contract_hardening.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** 24 Tests bestanden,
  ein neuer Producer-Test schlug fehl. Die Testhilfsfunktion `_sha` erwartete
  ein `Path`-Objekt, erhielt vom realistischen Producer-Stub aber einen
  Stringpfad; dadurch blieb die Paarliste leer. Der Fehler lag im Testaufbau,
  nicht im Produktivpfad.
- **Schlussfolgerung und nächster Schritt:** `_sha` im Test normalisiert den
  Eingang nun mit `Path(path)`; derselbe fokussierte Lauf wird wiederholt.

## 2026-09-23 — Erfolgreicher fokussierter Regressionstest der Implementierung

- **Fragestellung und Reasoning:** Wiederholung nach Korrektur des
  Testpfadtyps; Ziel war die gemeinsame Prüfung von Producer, Splitgruppen,
  Cacheindex und bestehendem Variable-TCN/BiLSTM-Verhalten.
- **Eingaben/Setup:** Synthetische temporäre Dateien und Tensoren; kein Zugriff
  auf die private Musiksammlung, keine Audio- oder Gewichtsartefakte.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_producer.py tests/test_variable_contract_hardening.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** **25 Tests bestanden in
  7,24 Sekunden**.
- **Schlussfolgerung und nächster Schritt:** Die neuen Kernverträge arbeiten
  synthetisch zusammen. Zusätzlich wird die explizite Aufnahme beider
  Waveformcache-SHAs in den Trainingsvertrag getestet und danach die breitere
  variable Regression ausgeführt.

## 2026-09-23 — Erster breiter Variable-v2-Regressionslauf

- **Fragestellung und Reasoning:** Gemeinsame Regression der neuen Verträge
  mit Feature Protocol 2, Dataset-v2, Variable-ML, Multi-Batch und bestehenden
  Hörstudienexportern.
- **Eingaben/Setup:** Zehn synthetische Testmodule; `.venv`; Bytecode- und
  Pytest-Cache deaktiviert; keine privaten Audiodateien.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_producer.py tests/test_variable_features.py tests/test_variable_dataset.py tests/test_variable_contract_hardening.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py tests/test_variable_ml.py tests/test_multi_batch_render.py tests/test_all_models_control_study.py tests/test_nontrivial_model_examples.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** 60 Tests bestanden,
  ein Assertion-Matcher scheiterte ausschließlich an der Großschreibung von
  `Both` in der erwarteten Fehlermeldung. Die geprüfte Produktivvalidierung
  löste korrekt aus.
- **Schlussfolgerung und nächster Schritt:** Testregex auf `[Bb]oth`
  korrigiert; derselbe breite Lauf wird wiederholt.

## 2026-09-23 — Erfolgreicher breiter Variable-v2-Regressionslauf

- **Fragestellung und Reasoning:** Wiederholung der gemeinsamen Regression
  nach der reinen Testmatcher-Korrektur.
- **Eingaben/Setup:** Zehn synthetische Testmodule; keine privaten Audios,
  Stems, Datasetshards oder Gewichte.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_producer.py tests/test_variable_features.py tests/test_variable_dataset.py tests/test_variable_contract_hardening.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py tests/test_variable_ml.py tests/test_multi_batch_render.py tests/test_all_models_control_study.py tests/test_nontrivial_model_examples.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** **61 Tests bestanden in
  8,93 Sekunden**.
- **Schlussfolgerung und nächster Schritt:** Die additive Implementierung ist
  mit den bestehenden variablen Daten-, Modell- und Studienpfaden kompatibel.
  Es folgt ein expliziter synthetischer Vier-Längen-Smoke mit Resume.

## 2026-09-23 — Synthetischer Vier-Längen-Training-Smoke mit Resume

- **Fragestellung und Reasoning:** Prüfung, dass 2/4/6/8-Takt-Batches gemeinsam
  eine Epoche trainieren, per streng identischem Vertrag auf Epoche 2
  fortgesetzt werden und Cacheindex-/Rootmanifest-SHAs erhalten bleiben.
- **Eingaben/Setup:** Synthetische Feature-/Waveformtensoren für alle vier
  Längen, CPU, 8 kHz und kleiner Test-Lowpass; keine Korpusdaten.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_tcn_bilstm.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** **8 Tests bestanden in
  5,22 Sekunden**, darunter Epoche 1 plus SHA-vertraglich geprüftes Resume auf
  Epoche 2 sowie Model-only-Fine-Tune mit neuem Optimizer.
- **Schlussfolgerung und nächster Schritt:** Der Code-Smoke ist grün. Der
  reale 16/4-Track-Smoke folgt nach der Recording-Group-Prüfung und wird nicht
  durch den synthetischen Test ersetzt.

## 2026-09-23 — Abschlussregression nach Recording-Group- und Status-Hardening

- **Fragestellung und Reasoning:** Nach Aufnahme der Gruppenmitglieder in die
  Splitautorität und fail-closed Producer-Rootstatus sollte die betroffene
  Vertragsmenge erneut geprüft werden.
- **Eingaben/Setup:** Fünf synthetische Testmodule, temporäre Dateien/Tensoren,
  kein Zugriff auf das PRIVE-Audio.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_producer.py tests/test_variable_contract_hardening.py tests/test_variable_dataset.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** **33 Tests bestanden in
  9,06 Sekunden**.
- **Schlussfolgerung und nächster Schritt:** Gruppenbindung, kompakter
  Producer, Pair-SHA-Verifikation, Cacheindex und Vier-Längen-Training bleiben
  grün. Danach wurden die drei neuen/erweiterten CLI-Oberflächen geprüft.

## 2026-09-23 — CLI-Preflight für Producer, Splitfortschreibung und Training

- **Fragestellung und Reasoning:** Sicherstellen, dass die implementierten
  Einstiegspunkte ausführbar und die Fine-Tune-Optionen tatsächlich exponiert
  sind, ohne einen Reallauf zu starten.
- **Eingaben/Setup:** Nur Argumentparser; keine Korpus-, Cache- oder
  Trainingsartefakte.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m src.variable_producer --help
  .venv\Scripts\python.exe -B -m src.variable_split_extension --help
  .venv\Scripts\python.exe -B -m src.ml train-variable-tcn-bilstm --help
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** Alle drei Befehle
  endeten mit Exit-Code 0. Producer und Splitfortschreibung zeigen ihre
  Pflichtpfade; der Trainingsparser zeigt Resume getrennt von
  `--initialize-from-manifest` und `--initialize-from-checkpoint`.
- **Schlussfolgerung und nächster Schritt:** Die Ausführungspfade sind
  erreichbar. Der nächste reale Schritt benötigt die bestätigte
  Recording-Group-Datei.

## 2026-09-23 — Producer-Request-SHA-Abschlusscheck

- **Fragestellung und Reasoning:** Der kompakte Producer bindet nun seine
  vollständige Anfragekonfiguration kanonisch im Root und in jedem
  Pairmanifest; die unmittelbar betroffenen Tests wurden erneut ausgeführt.
- **Eingaben/Setup:** Synthetische Zweitrack-Fixture und Split-Hardening,
  keine realen Audiodaten.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_producer.py tests/test_variable_contract_hardening.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** **8 Tests bestanden in
  2,49 Sekunden**.
- **Schlussfolgerung und nächster Schritt:** Request-SHA, Gruppenbindung und
  fail-closed Status sind verifiziert. Es folgt nur noch der statische
  Diff-/Whitespace-Check; danach folgt der Realkorpuslauf.

## 2026-09-23 — Abschließender Diff-/Whitespace-Check

- **Fragestellung und Reasoning:** Prüfung aller in diesem Auftrag neu
  implementierten oder dokumentierten Pfade auf Patch-Artefakte und
  Whitespacefehler.
- **Eingaben/Setup:** Explizite Liste der Producer-, Split-, Dataset-, Cache-,
  Trainings-, Test- und Dokumentationsdateien; vorbestehende fremde Änderungen
  an `overleaf`, `prototypes/` und `src/multi_batch_render.py` waren nicht Teil
  der Prüfliste.
- **Testumfang bzw. Befehl:** `git diff --check --` mit allen im Auftrag
  bearbeiteten Dateien.
- **Ergebnis einschließlich Fehlern oder Blockaden:** Exit-Code 0; keine
  Whitespacefehler. Git meldete nur erwartete LF/CRLF-Konvertierungshinweise
  für bereits unter Windows geführte Dateien.
- **Schlussfolgerung und nächster Schritt:** Der Implementierungsstand ist
  sauber übergabefähig. Vor der realen Materialisierung bleibt nur die
  Recording-Group-Zuordnung technisch zu bestätigen.

## 2026-09-23 — Unabhängiger Read-only-Audit des variablen PRIVE-Top-3-Batches

- **Fragestellung und Reasoning:** Der vorhandene Multi-Song-Batch
  `output\batches\prive_top1000_variable_top3_20260922` sollte unabhängig
  auf Datenvollständigkeit, Fehlersemantik, BPM-Ausschlüsse, approximative
  Grids, SHA-Duplikate, Candidate-Rejections, Score-Verteilungen,
  Rendererfehler und Tempo-Backend-Provenienz geprüft werden. Zulässig waren
  ausschließlich vorhandene Manifeste und bereits erzeugte Artefakte. Es
  wurde kein Audio neu gerendert, kein Modell trainiert und kein
  Originalaudio geöffnet oder neu gehasht. Damit beziehen sich Aussagen zu
  Source-Audio-SHAs auf die im Root-/Pair-Manifest deklarierte Provenienz.
- **Eingaben/Setup:** Gelesen wurden das 99.689.588-Byte-Root-Manifest, alle
  963 Pair-Manifeste mit zusammen 1.051.087.719 Bytes sowie die einzige
  vorhandene WAV. Python lief ausschließlich über
  `.venv\Scripts\python.exe`; JSON wurde mit der Standardbibliothek,
  Verteilungen mit NumPy und die bestehende WAV mit SoundFile gelesen.
  Vorbestehende Änderungen an `docs/Bemerkungen.md`, `docs/STATUS.md`,
  `src/multi_batch_render.py`, `overleaf` und `prototypes/` wurden erhalten.
- **Testumfang bzw. Befehle:** Zunächst inventarisierten read-only
  `Get-ChildItem -LiteralPath
  output\batches\prive_top1000_variable_top3_20260922 -Recurse -File` und
  fokussierte `.venv\Scripts\python.exe -c "..."`-Sonden Root-/Pair-Schema,
  Failure-Payloads, Candidate-/Score-Struktur und das einzige WAV-Manifest.
  Der anschließende vollständige Python-Audit las alle 963 Pair-Manifeste,
  berechnete deren SHA-256, verglich Referenzen und Zähler, validierte den
  kanonischen Candidate-Request-Hash, Kandidaten-/Score-ID-Mengen,
  Rangsortierung, endliche Werte, Scorebereich, Grid-Provenienz,
  Outputreferenzen und Verteilungen. Eine getrennte SoundFile-/NumPy-Sonde
  prüfte Header, Samplezahl, endliche Werte, Peak und die manifestierten
  Übergangsgrenzen der bestehenden WAV. `pytest`, Pipeline-CLIs, Renderer,
  Feature-/Stem-Extraktion und Trainingsrunner wurden nicht gestartet.
- **Datenvollständigkeit und SHA-Verträge:** Das Root-Manifest hat SHA-256
  `e9c4a1466f6dba7000de2f04a6c2476bd019ae30e28a56679cc38c35f77be989`
  und deklariert 321 Songs/Sources. Es gibt 963 erwartete und 963 vorhandene
  Pair-Verzeichnisse/-Manifeste (`321 * top_targets_per_source=3`), keine
  fehlenden oder verwaisten Pair-Manifeste und keine Zählerabweichung.
  Sämtliche 963 manifestierten Pair-Manifest-SHAs stimmen mit den Dateien;
  Candidate-Request-Payload und -SHA sind Root, Pair-Referenz und Pair-
  Manifest überall identisch. Die 321 Source-Pfade und 321 deklarierten
  Source-Audio-SHAs sind jeweils eindeutig; `duplicate_tracks` ist leer,
  kein ausgewähltes Paar ist ein SHA-Self-Pair und alle Candidate-
  Source-/Target-SHAs stimmen mit der Root-Referenz. Das belegt
  Manifestkonsistenz, nicht eine erneute Hashprüfung der Original-FLACs.
- **BPM-Filter:** Das Manifest bilanziert 398 analysierte Tracks als 321
  akzeptiert plus 77 BPM-Ausschlüsse; Analysefehler, Policy-Ausschlüsse und
  SHA-Duplikate sind jeweils null. Alle 321 akzeptierten manifestierten BPMs
  liegen inklusiv in `[145,165]`: 29 bei 147,656250, 251 bei 151,999081,
  32 bei 156,605114 und 9 bei 161,499023 BPM. Von den 77 Ausschlüssen liegen
  74 unter 145 und 3 über 165 BPM. Auffällig sind 31 Ausschlüsse exakt bei
  74,898098 BPM; im Hardstyle-Korpus ist ein Half-Time-Schätzfehler damit
  plausibel, aus Manifesten allein aber nicht bewiesen. Die BPM-Policy ist
  technisch konsistent, ihre musikalische Recall-Qualität nicht validiert.
- **Approximative Grids und Candidate-Rejections:** Über 1.926 Pair-Seiten
  sind 1.104 Grids `auftakt_matched_to_librosa` mit `fallback_used=false`
  und 822 `fallback_from_detected_beats` mit `fallback_used=true`; für die
  321 Track-SHAs wurde kein widersprüchlicher Grid-Datensatz gefunden. Die
  konfigurierte Policy `approximate_grid_policy=reject` greift sichtbar:
  231 Pair-Manifeste verwerfen die Source- und 235 die Target-Provenienz.
  Weitere 694 Paare enden mit `unsupported_meter` (Variable Candidate
  Protocol 2 verlangt 4/4), drei mit `invalid_source_grid`. Insgesamt haben
  958/963 Paare keine Kandidaten; die Rejection-Einträge sind je Pair
  aggregierte Abbruchgründe und keine Zählung einzelner hypothetischer
  Kandidaten. Nur fünf Paare erzeugen Kandidaten.
- **Candidate- und Score-Prüfung:** Die fünf zulässigen Paare enthalten
  zusammen 303.824 Kandidaten und ebenso viele `feature_baseline_v3`-Scores:
  88.278 für 2, 79.584 für 4, 71.583 für 6 und 64.379 für 8 Takte. Alle
  Candidate-IDs sind global eindeutig, Candidate-/Score-ID-Mengen stimmen,
  Ränge sind lückenlos absteigend sortiert, alle Scores sind endlich und
  liegen in `[0,1]`. Gesamtverteilung: Minimum 0,215710, 5-%-Quantil
  0,359225, Median 0,491583, Mittel 0,499160, 95-%-Quantil 0,637146,
  Maximum 0,893347. Komponentenmittel: Energy 0,824369, Harmonic 0,953022,
  High Power 0,423352, Non-Overlap 0,043309, Tempo 1,0 und Timbre 0,703609.
  Der sehr niedrige mittlere Non-Overlap-Wert zeigt, dass der große
  Candidate-Raum überwiegend schwache Bridge-Geometrien enthält; das
  Top-Ranking funktioniert formal, ist aber keine Hörqualitätsevidenz.
  Die 102.720 Songkompatibilitäts-Scores liegen bei Median 0,909858 und
  Mittel 0,901648; die 963 ausgewählten Top-3-Ziele bei Median 0,969089 und
  Mittel 0,966251. Es gab keine Song- oder Candidate-Rankingfehler.
- **Renderer- und Metrikfehler:** Vier der fünf ausgewählten Top-1-
  Candidates scheitern mit `ValueError`, weil Source- und Target-
  Übergangsfenster unterschiedlich lang sind: `Feel My Fire - Ran-D →
  Imagine - Bass Modulators` 566.272/564.224 Samples (Differenz 2.048),
  `Living For The Moment - Ran-D → Broken - Regain` 279.552/282.624
  (3.072), `Mellow - Showtek → The Words - Psyko Punkz`
  280.576/282.112 (1.536) und `WKND - Edit - Max Enforcer → Imagine -
  Bass Modulators` 141.312/140.800 (512). Das entspricht bei 44,1 kHz etwa
  46,4, 69,7, 34,8 und 11,6 ms. Nur `Keep Me Awake - Radio Edit -
  Atmozfears → Imagine - Bass Modulators` wurde als 8-Takt-Equal-Power-WAV
  erzeugt. Deren Render-Metrik scheitert separat: Das manifestierte
  `transition_end_sample=784724` liegt 35.024 Samples beziehungsweise
  0,7942 s hinter der 749.700 Frames langen Datei. Daher existiert für den
  gesamten Batch kein `rendered_transition_baseline_v1`-Score.
- **Vorhandene WAV:** Die deklarierte Datei existiert, ist nicht verwaist
  und hat SHA-256
  `3a94ab0e6700eb006c2c42fdedddf761484a3ddc6d2da8e438a02fffe5253b5f`.
  Header und Manifest stimmen bei 44.100 Hz, Stereo, 749.700 Frames und
  17,0 s; alle Samples sind endlich. Abweichend von früheren Float32-
  Studienartefakten ist sie PCM-16. Der Peak erreicht exakt -1,0; 1.536
  Samples liegen betragsmäßig bei mindestens 0,999 und 573 Samples exakt
  bei negativem Full Scale. Das ist ein objektiver Pegel-/Clipping-
  Prüfhinweis, beweist ohne Vergleich zum Eingang aber nicht, dass der
  Renderer das Clipping neu erzeugt hat.
- **Fehlersemantik:** Root-`failures` ist leer und alle 321 Sources sowie
  963 Pair-Referenzen tragen `status=completed`, obwohl vier Pair-Manifeste
  Renderfehler und eines einen Transition-Metric-Fehler enthalten. Die
  zugehörigen Root-Pair-Summen `render_failure_count=1` beziehungsweise
  `transition_metric_failure_count=1` sind korrekt; `completed` bedeutet
  hier also abgeschlossene/persistierte Bearbeitung, nicht erfolgreichen
  Render und nicht Fehlerfreiheit. Ein Verbraucher darf weder Root-
  `failures=[]` noch `status=completed` allein als Erfolgsindikator nutzen,
  sondern muss die verschachtelten Fehlerzähler auswerten. Der Prozess-
  Exitcode des historischen Laufs ist nicht als Artefakt vorhanden und kann
  aus diesem Audit nicht behauptet werden.
- **Tempo-Backend-Provenienz:** Alle fünf renderrelevanten Top-Candidates
  deklarieren identische Source-/Target-BPM 151,999081 und
  `tempo_relative_difference=0`. Die einzige erfolgreiche Variante nennt
  deshalb korrekt `tempo_backend=not_needed`; ein Time-Stretch-Backend wurde
  in keinem vorhandenen Audioartefakt ausgeführt. Für die vier vor dem
  Renderabschluss gescheiterten Versuche existiert folgerichtig keine
  ausgeführte Backend-Provenienz. Die Grids nennen einheitlich
  `librosa=0.11.0;aufTAKTCl=sha256:35f9149c...1b523`; dies ist
  Analyse-/Grid-, nicht Time-Stretch-Provenienz.
- **Technische Funktionsfähigkeit versus musikalische Qualität:** Formal
  funktionieren Inventar, SHA-Verkettung, BPM-Filter, Grid-Policy,
  Candidate-v2-Erzeugung für fünf Paare und Feature-Ranking. Als Hörbatch
  ist das Ergebnis nicht freigegeben: Nur 1/963 Paare besitzt Audio, dieses
  Audio hat keinen gültigen Render-Metrikscore und einen Full-Scale-
  Pegelhinweis. Weder die hohen Songkompatibilitätswerte noch der beste
  Candidate-Score 0,893347 belegen musikalische Stimmigkeit, Artefaktfreiheit
  oder Tanz-Nutzbarkeit; es fand in diesem Audit keine Hörbewertung statt.
- **Kleines, konditionales Hörset:** Nach Behebung der Renderer-/Metrikfehler
  wäre ein dreiteiliges Set ohne Track- oder Künstlerwiederholung sinnvoll:
  (1) `Keep Me Awake - Atmozfears → Imagine - Bass Modulators`, 8 Takte,
  Score 0,801610; (2) `Living For The Moment - Ran-D → Broken - Regain`,
  4 Takte, Score 0,893347; (3) `Mellow - Showtek → The Words - Psyko
  Punkz`, 4 Takte, Score 0,854332. Das ist nur eine metadatenbasierte,
  innerhalb des Hardstyle-Batches möglichst wenig redundante Auswahl. Aktuell
  ist allein Nummer 1 als WAV vorhanden und wegen Metrikfehler/Pegelfund nur
  diagnostisch hörbar; Nummer 2 und 3 wurden nicht erzeugt. Es wird keine
  musikalische Qualität behauptet.
- **Schlussfolgerung und nächster Schritt:** Vor einer Hörfreigabe zuerst
  den Variable-Renderervertrag für lokale Gridlängen sowie die Berechnung
  der Render-Metrikgrenzen korrigieren und in einem neuen, nicht
  überschreibenden kleinen Lauf verifizieren. Separat sollte die Häufung
  von Half-Time-BPMs und `unsupported_meter` untersucht werden; die strikte
  Approximate-Grid-Policy sollte nicht still gelockert werden. Dieser Auftrag
  hat bewusst keinen Fix, keinen neuen Render-/Trainingslauf und keinen
  Commit ausgeführt. Der abschließende Befehl
  `git diff --check -- docs/STATUS.md docs/Bemerkungen.md` bestand; Git gab
  nur die bestehende LF/CRLF-Konvertierungswarnung für beide Dateien aus.

## 2026-09-23 — Plan und Vertragsaudit für die PRIVE-Dataset-v2-Erweiterung

- **Fragestellung und Reasoning:** Die 398 lokalen PRIVE-FLACs sollen das
  bestehende variable Trainingskorpus reproduzierbar erweitern, ohne jetzt
  Audio, Stems, Features, Datasetshards, Waveformcaches oder Gewichte zu
  materialisieren und ohne Training. Vor dem Plan wurden Feature Protocol 2,
  Dataset Format 2, Splitautorität, BS-RoFormer-Provenienz,
  Variable-Waveformcache, Variable-TCN/BiLSTM-Runner und die beiden vorhandenen
  PRIVE-Batches gegen Code, Protokolle und lokale Manifeste geprüft.
- **Eingaben/Setup:** Repository am 2026-09-23; `.venv\Scripts\python.exe`;
  read-only Inventur des PRIVE-Ordners und der vorhandenen Dataset-/Cache-/
  Runmanifeste. Vorbestehende Änderungen an `docs/Bemerkungen.md`,
  `docs/STATUS.md`, `src/multi_batch_render.py`, `overleaf` und `prototypes/`
  wurden erhalten.
- **Testumfang bzw. Befehl:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_variable_features.py tests/test_variable_dataset.py tests/test_variable_contract_hardening.py tests/test_variable_waveform_cache.py tests/test_variable_tcn_bilstm.py tests/test_multi_batch_render.py
  ```

- **Ergebnis einschließlich Fehlern oder Blockaden:** **45 Tests bestanden in
  58,12 Sekunden**. Es wurden nur synthetische Pytest-Fixtures und temporäre
  Verzeichnisse verwendet. Feature-v2, homogene Dataset-v2-Shards, gemeinsame
  SHA-Splitautorität, Geometrie-Hardening, lokales Grid-Alignment,
  Cacheintegrität, T=16/32/48/64, explizite Längenkonditionierung,
  Checkpoint/Resume und Multi-Batch-Regression sind grün. Kein Testsplit-
  Audio und kein reales Korpusartefakt wurde geöffnet oder geschrieben.
- **Verifizierte Entscheidungen:** Der bestehende 2/4-Takt-Baseline-Root und
  der fehlerhafte variable Top-3-Root sind keine Datasetquelle. Vor dem
  Vollauf ist ein neuer kompakter, splitbewusster Multi-Song-Produzent mit
  `PartialPreAnalysis`/Merge-v2, Candidate Protocol 2 und ohne Renderer
  erforderlich. Die alten 87 Splitzuweisungen bleiben unverändert; neue
  Audio-SHAs werden gruppenweise ergänzt. Der neue primäre Modelllauf startet
  von Grund auf. Ein optionales Fine-Tuning ist ein separater Initialisierungs-
  lauf und kein Resume. Test-Waveformcache, Testtraining und Testmodellwahl
  bleiben gesperrt.
- **Sackgassen:** Die frühere 87-Paar-Materialisierung erzeugte 6,15 GB JSON
  für 1,92 Millionen Kandidaten; ein erneut unbeschränktes Vollmanifest wird
  deshalb nicht akzeptiert. Der aktuelle Variable-Runvertrag bindet nur das
  Datasetmanifest und noch keinen kanonischen Gesamtindex des Waveformcaches;
  dieser Hash wird vor dem neuen Training Pflicht. Exakte Audio-SHA-Trennung
  allein erkennt außerdem keine Radio-/Album-/Alternate-Version derselben
  Aufnahme, weshalb eine vorgelagerte Recording-Group-Zuordnung geplant ist.
- **Schlussfolgerung und nächster Schritt:** Der vollständige Phasen-,
  Hash-, Speicher-, Laufzeit-, Smoke-, Trainings- und Hörstudienplan steht in
  `docs/PRIVE_DATASET_V2_EXTENSION_PLAN.md`. Vor jeder Materialisierung sind
  zuerst Producervertrag, Split-/Recording-Gruppen und
  der Waveformcacheindex-Vertrag zu schließen. Der abschließende Lauf
  `git diff --check -- docs/PRIVE_DATASET_V2_EXTENSION_PLAN.md docs/STATUS.md
  docs/Bemerkungen.md` bestand mit Exit-Code 0; ausgegeben wurden nur die
  bestehenden LF/CRLF-Hinweise für `STATUS.md` und `Bemerkungen.md`. Kein
  Commit wurde erstellt.

## 2026-09-24 — Reale PRIVE-Korpusinventur und Dataset-v2-Smoke-Lauf

- **Fragestellung und Reasoning:** Nach der ausdrücklichen Freigabe zur
  Materialisierung soll die PRIVE-Sammlung technisch in einen neuen,
  unveränderlichen Dataset-v2-Pfad überführt werden. Unverändert bleiben die
  technischen Schutzregeln: Recording-Gruppen dürfen keine Splits
  überqueren, alte Zuweisungen werden eingefroren und der Testsplit bleibt
  für Producer-Smoke, Training und Modellwahl geschlossen.
- **Statischer Normalisierungscheck:** Ein `.venv\Scripts\python.exe -B -c`
  Check lud `src/variable_corpus_inventory.py`, pars­te die geänderten
  Python-Dateien mit `ast.parse` und prüfte beispielhaft die
  Recording-Group-Normalisierung. `Special Edit` wurde mit der Grundaufnahme
  gruppiert; `A Feeling (Citizen Remix)` normalisierte zu
  `the raiders|a feeling`. Ergebnis: erfolgreich in 29,4 s.
- **Erster realer Inventurlauf (fehlgeschlagen, unverändert bewahrt):**

  ```powershell
  .venv\Scripts\python.exe -B -m src.variable_corpus_inventory `
    --base-producer-manifest output\batch_variable_v2_strict_20260820_selected_top3_run01\manifest.json `
    --base-dataset-manifest output\datasets\variable_v2_strict_20260820_selected_roformer_run01\manifest.json `
    --added-directory "musik\PRIVE Hardstyle Top 1000 of all times - by Scantraxx" `
    --output-dir output\corpora\prive_scantraxx_extension_v2_20260923_run01 `
    --split-seed 20260923
  ```

  Der Lauf stoppte absichtlich mit `ValueError`, weil die Recording-Gruppe
  `recording-a930310ba6b8991716df` bereits in zwei eingefrorenen Splits lag:
  `musik\05 - HELP_LESS.flac` in Train und `HELP_LESS - DEEZL.flac` aus dem
  Q-dance-Korpus in Test. Die Dateien haben verschiedene Audio-SHAs, bilden
  nach Artist/Titel aber dieselbe Aufnahme. Der Teilstand wurde nicht
  überschrieben, sondern nach
  `output/corpora/prive_scantraxx_extension_v2_20260923_run01_failed_recording_conflict01`
  verschoben.
- **Entscheidung aus der Sackgasse:** Bei Konflikten ausschließlich zwischen
  bereits eingefrorenen Altzuweisungen bleibt genau der stärker geschützte
  Split aktiv (`test > validation > train`); die anderen Kopien werden mit
  Pfad, SHA, Gruppe, altem und behaltenem Split explizit im Korpusmanifest
  als `preexisting_recording_group_cross_split_conflict` ausgeschlossen.
  Neue Tracks werden weiterhin gruppenweise zugewiesen, nicht einzeln.
- **Gezielter Regressionstest nach dem Konflikt-Fix:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider `
    tests/test_variable_corpus_inventory.py `
    tests/test_variable_producer.py `
    tests/test_variable_contract_hardening.py
  ```

  Ergebnis: **10 Tests bestanden in 3,72 s**. Nach der zusätzlichen
  Parallelisierung des BPM-/Merge-v2-Preflights wurde derselbe Umfang erneut
  ausgeführt: **10 Tests bestanden in 2,46 s**.
- **Erfolgreicher realer Inventurlauf:** Der obige Inventurbefehl wurde mit
  demselben neuen Zielpfad wiederholt und erfolgreich abgeschlossen. Aktiv
  sind **484 Tracks in 473 Recording-Gruppen**; ein Train-Duplikat der
  eingefrorenen Testaufnahme `HELP_LESS` ist ausgeschlossen. Die versiegelten
  Bindungen lauten: Korpusmanifest
  `46a7f677f008ce9d8296b6b1a80db0fbf6d419cddfbe0886c88b3d7ae297b3a4`,
  Recording-Gruppen
  `9b9d657c5785013d20b06abd252c8d4af1e06889e977a06f3b666effcb2dc0b4`,
  Splitautoritätsdatei
  `1eaf5672428f030ca9807c5ddf3d1e06bf03c06b2792b8a9a21bf564a318d3ee`
  und kanonische Splitabbildung
  `f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
  Die Autorität enthält 343 Train-, 70 Validation- und 72 Test-SHAs; sie
  enthält bewusst auch die ausgeschlossene historische Train-SHA, während
  das aktive Korpus 484 statt 485 Tracks umfasst.
- **Erster Producer-Smoke (abgebrochen):** Ein 20-Track-Smoke mit separatem,
  leerem Merge-v2-Cache wurde nach der ersten abgeschlossenen Analyse
  abgebrochen, weil aufTAKT pro Track ungefähr Echtzeit/2 benötigt und der
  vorhandene Cache dadurch nicht wiederverwendet wurde. Der eine
  Cacheeintrag blieb als diagnostischer Teilstand unter
  `output/pre_analysis/prive_scantraxx_extension_merge_v2_smoke_20260924_run01_aborted_empty_cache01`
  erhalten. Es wurden weder Audio gerendert noch Datasetshards geschrieben.
- **Parallelisierungsentscheidung:** `src.variable_producer` besitzt nun
  `--analysis-workers`; jeder Worker verwendet eine eigene
  `PartialPreAnalysis`-Instanz, während der inhaltsadressierte Cache atomar
  beschrieben wird. Der Producervertrag bindet die Workerzahl in seine
  Request-Konfiguration. Dadurch kann der teure reale Preflight parallel
  laufen, ohne Split-, Candidate- oder Outputsemantik zu ändern.
- **Zweiter Smoke-Subset:** Der versiegelte Subset
  `smoke_corpus_manifest_run02.json` enthält vier Train- und vier
  Validation-Tracks aus dem neuen PRIVE-Ordner, acht verschiedene
  Recording-Gruppen und keinen Testtrack. SHA-256:
  `dc826a8ace66ab6ae0c1183bb7252c4a737a95256efbc0d6c6b4d2309d28fb85`.
  Ein erster Selektionsversuch schrieb nichts, weil der Filter den
  tatsächlichen Quellenwert `prive_scantraxx` zunächst fälschlich als
  `added` erwartete; nach read-only Diagnose wurde ein neuer Run-02-Pfad
  verwendet.
- **Laufender realer Producer-Smoke:**

  ```powershell
  .venv\Scripts\python.exe -B -m src.variable_producer `
    --corpus-manifest output\corpora\prive_scantraxx_extension_v2_20260923_run01\smoke_corpus_manifest_run02.json `
    --output-dir output\producers\prive_scantraxx_extension_variable_v2_smoke_20260924_run02 `
    --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority.json `
    --analysis-location output\pre_analysis `
    --transition-bars 2 4 6 8 --top-targets 1 `
    --top-candidates-per-length 1 --min-bpm 145 --max-bpm 165 `
    --analysis-workers 4
  ```

  Alle acht Analysen wurden ohne Analysefehler beendet; zwei Tracks lagen
  außerhalb des BPM-Fensters. Der Candidate-v2-Lauf für die sechs
  verbleibenden Tracks war beim Schreiben dieses Zwischenstands noch aktiv.

## 2026-09-25 — Dataset-v2-Smoke und Vollauf

- **Fragestellung und Reasoning:** Den freigegebenen Plan mit einem realen,
  reproduzierbaren Dataset-v2-Smoke ausführen und bei bestandenen Split-,
  Grid- und Hash-Gates den Voll-Producer starten. In dieser Fortsetzung wurden
  keine Testbeispiele in den Smoke aufgenommen; die Splitautorität enthält
  weiterhin den unangetasteten geschlossenen Testsplit.
- **Smoke-Producer Run 02:** Run 02 wurde mit vier Audioanalysen ausgeführt.
  BPM-Prüfung schloss `It's Our Moment - Wasted Penguinz` (74,898 BPM) und
  `Mask On My Face - KELTEK` (129,199 BPM) aus. Train produzierte Kandidaten,
  aber beide verbleibenden Validation-Tracks hatten unter dem aktuellen
  4/4-Vertrag keine Kandidaten. Diagnose der Rejections: `unsupported_meter`.
  Der Prozess endete ohne Analysefehler, der Smoke wurde wegen fehlender
  Validation-Beispiele verworfen und der Root unverändert als Diagnoseartefakt
  belassen.
- **Smoke-Producer Run 04:** Ein mit den früheren Candidate-Dateien
  übereinstimmendes Validation-Paar (`Azure - D-Charged` / `Safe & Sound`)
  war unter den aktuellen Analysis-v2-Caches ebenfalls kein gültiges 4/4-Paar.
  Der Run endete technisch, aber mit null Validation-Kandidaten; er wurde
  nicht als Datasetquelle verwendet.
- **Grid-gültiger Validation-Smoke:** Read-only Suche über die abgeschlossenen
  Merge-v2-Caches fand vier aktuelle 4/4-Validation-Grids. Ein direkter
  `generate_transition_candidates`-Check auf `MEDICINE - TOZA` und
  `My History - Galactixx` ergab 9.282 Kandidaten für 2 Takte und keine
  Rejection. Die vier Tracks für Run 05 sind zwei PRIVE-Train-Tracks
  (`Feel My Fire`, `Imagine`) und zwei eingefrorene Basis-Validation-Tracks
  (`MEDICINE`, `My History`), alle mit unterschiedlichen Aufnahmegruppen und
  bereits SHA-verifizierten Analysecaches. Der Smoke-Subset-SHA lautet
  `e91f2964aad10f39f6a249f3e4ef3cb0288e24dedb67e7bc1f14cc0dca69dfb2`.
- **Producer-Smoke Run 05:** Befehl:

  ```powershell
  .venv\Scripts\python.exe -B -m src.variable_producer `
    --corpus-manifest output\corpora\prive_scantraxx_extension_v2_20260923_run01\smoke_corpus_manifest_run05.json `
    --output-dir output\producers\prive_scantraxx_extension_variable_v2_smoke_20260924_run05 `
    --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority.json `
    --analysis-location output\pre_analysis\prive_scantraxx_extension_merge_v2_smoke_20260924_run05 `
    --transition-bars 2 4 6 8 --top-targets 1 `
    --top-candidates-per-length 1 --min-bpm 145 --max-bpm 165 `
    --analysis-workers 4
  ```

  Ergebnis `completed`, keine Fehler, vier splitinterne Paare, je ein Top-
  Candidate für jede Länge und Split. Insgesamt 16 Candidates, acht Train,
  acht Validation; Candidate- und Pair-SHAs wurden geprüft. Producer-Root-SHA:
  `0346b1b1b3fcf5b1fa2db7b77402c511cc21e714cee30e5e29019984c94fd287`.
- **Splitbindung für den Datasetexport:** Der Export verweigerte zunächst
  korrekt die ungebundene Korpusautorität, da sie an das Korpusmanifest statt
  an dieses Producer-Root gebunden war (`Frozen split authority source
  manifest hash differs`). `bind_variable_split_authority` und das CLI
  `src.variable_split_binding` wurden ergänzt. Die Bindung ließ Mapping-SHA
  und sämtliche Zuweisungen unverändert und speicherte Parent-Map- und
  Producer-Root-SHA.
- **Regressionstests zur Splitbindung:** Erster Lauf des erweiterten
  Testumfangs endete mit **1 Fehler / 10 bestanden**: der synthetische Test
  der regulären Splitbildung übergab null Pairgewichte, wodurch der
  Splitter wie spezifiziert keine nichtleeren Example-Splits erzeugen konnte.
  Nach Korrektur der Testfixture und nach Ergänzung des parallelen Source-
  Pfads liefen die Tests jeweils erfolgreich:

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider `
    tests\test_variable_contract_hardening.py `
    tests\test_variable_producer.py `
    tests\test_variable_corpus_inventory.py
  ```

  Ergebnisse: **11 Tests bestanden in 3,50 s**; nach Hinzunahme des
  `source_workers=2`-Producer-Smokes **11 Tests bestanden in 2,54 s**.
- **RoFormer- und Dataset-Smoke:** Der erste Export scheiterte vor Feature-
  Extraktion an CP1252 bei einem Emoji in der Downloadbibliothek. Mit
  `PYTHONIOENCODING=utf-8` erreichte er den Modellabruf, den das eingeschränkte
  Netzwerk zunächst blockierte (drei Verbindungsversuche). Nach erfolgreicher
  Freigabe des nötigen Netzwerkzugriffs lud der Export den
  BS-RoFormer-Checkpoint mit 699.412.152 Bytes in den ignorierten lokalen
  Featurecache. Es wurde kein Gewicht dem Repository hinzugefügt.
  Anschließend endete der Export erfolgreich:

  ```powershell
  .venv\Scripts\python.exe -B -m src.features export-dataset-v2 `
    output\producers\prive_scantraxx_extension_variable_v2_smoke_20260924_run05\manifest.json `
    output\datasets\prive_scantraxx_extension_variable_v2_fp2_roformer_smoke_20260924_run01 `
    --cache-root output\feature_cache_prive_scantraxx_extension_fp2_roformer_smoke_20260924_run01 `
    --analysis-root output\pre_analysis\prive_scantraxx_extension_merge_v2_smoke_20260924_run05 `
    --transition-bars 2 4 6 8 --top-k-per-pair 1 `
    --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority_for_producer_smoke_run05.json `
    --vocal-backend roformer --min-bpm 145 --max-bpm 165
  ```

  Der Versuch `src.features validate-variable-dataset` war kein gültiger
  Befehl (die CLI bietet ihn nicht an). Stattdessen wurden alle 16 Beispiele
  mit `VariableFeatureDatasetCollection` einzeln geladen. Ein erster
  Prüf-Ausdruck erwartete fälschlich, dass auch die Splitzuweisung für Test
  aus dem Manifest fehlt; anschließend wurde die richtige Bedingung geprüft:
  in jedem Shard sind null Testbeispiele und Testshards explizit leer.
  Ergebnis: 2 Train und 2 Validation für jede Länge, 16 erfolgreich
  eingelesene Beispiele, Feature Protocol 2, Datasetmanifest-SHA
  `f687d786c11bd64433a7092d05fe507b9584aaf857916a55f04d1d85b1a3ca32`.
- **BPM-Eligible-Subset für den Vollauf:** Der bereits abgeschlossene
  Baseline-Preflight (87 bestehende Tracks) und der alte PRIVE-Preflight
  (321 akzeptierte von 398 Dateien) wurden anhand ihrer Tracklisten mit dem
  Audio-SHA-Inventar verknüpft. Das neue `eligible_corpus_manifest.json`
  enthält 407 einmalige Audios und bindet beide Elternmanifeste sowie ihre
  BPM-Policy; Splitzahlen: 292/58/57. Manifest-SHA:
  `7bcf4a79db6943d78bf53d60f5adbf273245f31c7378a3aaacf360df6dc95be3`.
  Die abgeleitete Trackauswahl wurde über Pfade aus den alten Manifesten
  erstellt und anschließend mit der aktuellen Korpus-SHA-Liste auf 407
  eindeutige Zeilen abgeglichen. Ungeprüfte Half-Time-Dateien wurden nicht
  ergänzt.
- **Voll-Producer-Sackgasse Run 01:** Der erste Voll-Producer wurde nach
  129 fertigen Merge-v2-Analysemanifests während des Preflights abgebrochen.
  Die Trackliste umfasste zu diesem Zeitpunkt noch alle 484 Audios, sodass
  bekannte BPM-Ausschlüsse unnötig erneut analysiert worden wären. Das
  Producer-Verzeichnis wurde vor dem Ende des BPM-Preflights nicht angelegt;
  die 129 inhaltsadressierten Cacheeinträge bleiben bestehen.
- **Voll-Producer Run 02:** Der laufende Befehl verwendet die gebundene
  407-Track-Eligible-Liste und vier Source-Worker:

  ```powershell
  .venv\Scripts\python.exe -B -m src.variable_producer `
    --corpus-manifest output\corpora\prive_scantraxx_extension_v2_20260923_run01\eligible_corpus_manifest.json `
    --output-dir output\producers\prive_scantraxx_extension_variable_v2_top1x3_20260923_run02 `
    --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority.json `
    --analysis-location output\pre_analysis\prive_scantraxx_extension_merge_v2_20260923_run01 `
    --transition-bars 2 4 6 8 --top-targets 1 `
    --top-candidates-per-length 3 --min-bpm 145 --max-bpm 165 `
    --analysis-workers 8 --source-workers 4
  ```

  Der Run schloss später 407/407 Eligible-Audio-SHA-Analysen ab und begann
  die Paarbildung. Beim Abbruch war ein Pair abgeschlossen und es gab null
  Pairfehler; die Gesamtentscheidung und Korrektur des Testsplit-Gates stehen
  direkt im folgenden Eintrag.

- **Voll-Producer Run 02 -- geschlossener Testsplit-Gatefehler:** Run 02 wurde
  nach abgeschlossener BPM-Voranalyse (407/407 Eligible-Audio-SHAs) und nach
  Beginn der Paarbildung abgebrochen. Der Producer hatte zu diesem Zeitpunkt
  Quellen mit Split test in die Voranalyse einbezogen; ein Pair war
  abgeschlossen, null fehlgeschlagen. Es gab noch keinen Datasetexport und
  kein Training. Das verletzt den geforderten geschlossenen Testsplit. Run 02
  bleibt als unvollständiges Diagnoseartefakt erhalten; seine Analysecaches
  und das partielle Producerroot werden nicht als Dataset verwendet.
- **Korrektur und Regressionstest, 2026-09-25:** src.variable_producer
  schließt nun Testtracks anhand der bereits manifestierten Audio-SHAs aus,
  bevor Audiodateien gehasht, BPM-analysiert oder zur Paarbildung verwendet
  werden. Die ausgeschlossenen Test-SHAs werden nur als Auditmetadaten
  aufgeführt. Falls ein Splitauthority-Testzuweisungen enthält, aber kein
  Korpusmanifest zum Vorfiltern vorliegt, verweigert der Producer den Lauf,
  bevor er Audio inspiziert.
  Ein erster Testbefehl verwies auf die nicht existente Datei
  tests/test_variable_split.py und führte keine Tests aus. Der tatsächliche
  fokussierte Befehl
  .venv\Scripts\python.exe -B -m pytest tests\test_variable_producer.py -q
  bestand mit 3 Tests in 7,62 s. Die neuen Regressionstests belegen, dass
  Testaudio weder gehasht noch analysiert wird und dass der Lauf ohne
  manifestbasierte Vorfilterung vor Audiozugriff abbricht.
  Nächster Schritt: Run 03 mit derselben Eligible-Liste, dem unveränderten
  Splitmapping und neuer Producer-Run-ID ausschließlich aus Train/Validation
  erstellen; danach Testleere und SHAbindungen des Dataset-v2-Exports prüfen.

## 2026-09-25 — Recovery des PRIVE-Produzenten und Dataset-v2-Vollausführung

- **Fragestellung/Reasoning:** Den PRIVE-Trainingsbestand auf dem korrigierten,
  strikt trackgetrennten Run fortsetzen, ohne unvollständige Rootmanifeste zu
  verändern; danach den neuen unveränderlichen 2/4/6/8-Takt-Dataset-v2-Root
  mit Feature Protocol 2 und BS-RoFormer erzeugen und maschinell prüfen.
- **Eingaben/Setup:** Korpusinventar-Manifest-SHA
  `46a7f677f008ce9d8296b6b1a80db0fbf6d419cddfbe0886c88b3d7ae297b3a4`;
  BPM-Eligible-Manifest mit 407 Tracks und Verteilung 292/58/57,
  SHA `7bcf4a79db6943d78bf53d60f5adbf273245f31c7378a3aaacf360df6dc95be3`;
  kanonische Mapping-SHA
  `f01243f227db7fb41c8859de62985b39ba75a71fe9a8f5fe95b40d619c1b4a7a`.
  Der reproduzierbare Split nutzt Audio-SHA und vorab bestätigte
  Recording-Gruppen. Für den Dataset-Export werden nur gleichsplitige
  Train-/Validation-Paare akzeptiert; `test` wird bereits vor Audiozugriff
  ausgeschlossen.
- **Producer-Sackgasse und Recovery:** Korrigierter Run 03 verarbeitete 350
  Train-/Validation-Sources und schrieb alle 350 Pairmanifeste, endete aber
  mit Exit-Code 1, bevor das Rootmanifest seine gesamten Statuszeilen
  aktualisierte (61 von 350 Statuszeilen waren aktualisiert). Das partielle
  Run-03-Root wurde nicht verändert oder als abgeschlossen ausgegeben.
  Recovery Run 04 aggregierte zwar die 350 vorhandenen Pairmanifeste, besaß
  aber null geeignete Validation-Beispiele und wurde nicht verwendet. Recovery
  Run 05 erzeugte einen neuen Root aus Run 03 plus zwei SHA-geprüften,
  splitinternen Validation-Pairmanifesten des bereits geprüften Smoke Run 05.
  Root:
  `output/producers/prive_scantraxx_extension_variable_v2_top1x3_20260923_run05_recovered_from_run03_plus_validation_smoke/manifest.json`;
  SHA-256 `172c3ba41c9a7b807452e443865e63d43d67bcbd2d792be6ca841ed69b2d8a36`.
  Er bindet 350 Source-Zeilen, 352 Pairmanifeste (292 Train / 60 Validation),
  null Pairfehler und 57 ausgeschlossene Testzuweisungen. Von 289
  Source-Ranking-Audits sind die Originalranglisten nicht wiederherstellbar;
  diese Records sind ausdrücklich als nicht wiederhergestellt markiert.
  Pro Taktlänge stehen 36 Train- und 2 Validation-Candidates zur Verfügung.
- **Splitbindung:** Die unveränderte Mapping-SHA wurde an Recovery-Root-SHA
  gebunden; Authoritydatei
  `output/corpora/prive_scantraxx_extension_v2_20260923_run01/split_authority_for_producer_run05_recovered.json`,
  Datei-SHA `bfcb6929bd5c1f7bbfee41c82e5cef868a066dfa13337e712d5d3227265030b9`.
  Ein erster Aufruf verwendete versehentlich einen nicht existierenden
  Producerpfad (fehlendes `_variable`) und schlug vor jeder Änderung fehl;
  der Aufruf mit dem richtigen Recoverypfad bestand. Nach Ergänzung der
  Recovery-Validierung für mehrere Supplement-Roots bestanden
  `.venv\Scripts\python.exe -B -m pytest tests\test_variable_producer.py tests\test_variable_producer_recovery.py -q`
  mit **4 Tests in 2,59 s**.
- **Datasetexport:** Ziel war vor dem Lauf nicht vorhanden:
  `output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run01`.
  Verwendeter Befehl:

  ```powershell
  $env:PYTHONIOENCODING='utf-8'
  .venv\Scripts\python.exe -B -m src.features export-dataset-v2 `
    output\producers\prive_scantraxx_extension_variable_v2_top1x3_20260923_run05_recovered_from_run03_plus_validation_smoke\manifest.json `
    output\datasets\prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run01 `
    --cache-root output\feature_cache_prive_scantraxx_extension_fp2_roformer_20260923_run01 `
    --analysis-root output\pre_analysis\prive_scantraxx_extension_merge_v2_20260923_run01 `
    --transition-bars 2 4 6 8 --top-k-per-pair 3 `
    --split-map output\corpora\prive_scantraxx_extension_v2_20260923_run01\split_authority_for_producer_run05_recovered.json `
    --vocal-backend roformer --min-bpm 145 --max-bpm 165
  ```

  Der erste rund 50-minütige Extraktionslauf befüllte 22 Vocal-Stem- und 23
  Track-Featurecaches, endete aber beim Anlegen des temporären Datasetroots
  mit `PermissionError: [WinError 5]` unter `output\datasets`. Der Root-ACL
  erlaubte Änderungen; die Workspace-Sandbox hatte den konkreten temporären
  Schreibzugriff blockiert. Der Exporter entfernte den unvollständigen Temp-
  Root, der unveränderliche Zielpfad blieb frei. Nach gezielter Freigabe lief
  derselbe Befehl mit Exit-Code 0 durch und schrieb 152 Beispiele. Verteilung
  je Länge (2/4/6/8): **36 Train / 2 Validation / 0 Test**.
- **SHA-/Split-/Loaderaudit:** Read-only Inlineprüfung via
  `@' ... '@ | .venv\Scripts\python.exe -B -` validierte Feature Protocol 2,
  RoFormer, die gebundene Recovery-Root-SHA und Mapping-SHA, die SHA des
  Producerroots, alle 352 Pairmanifeste und alle 24 Sharddateien. Der
  ML-`VariableFeatureDataset` lud alle 12 Längen-/Splitshards und 152 Beispiele;
  Shapes für T=16/32/48/64, Metadata-/Example-ID-Gleichheit, Cachemanifest-
  SHAs und Audio-SHA-Zuordnung jedes Tracks wurden geprüft. Pro Beispiel lagen
  Source und Target im deklarierenden Split; der Testshard war je Länge leer.
  Ergebnis: null Split-Leckage, null Testbeispiele. Dataset-ID
  `6be39995e91c0063a933`, Manifest-SHA-256
  `9d11bae795c098376d46a9a02204a7cb6647f77ffb5ff39f5c80c2da94823562`.
  Der Root enthält 25 Dateien und 1.640.132 Bytes.
- **Cache-/Repositoryprüfung:** Der getrennte RoFormer-/Featurecache enthält
  92 Dateien und 1.433.741.822 Bytes (22 `vocal_stem.npz`, 23
  `track_features.npz`, einschließlich lokaler Modellassets). `git check-ignore`
  bestätigte Datasetmanifest und RoFormer-Checkpoint als von `.gitignore`
  erfasste `output/`-Artefakte. Kein Audio und keine Gewichte wurden dem
  Git-Index hinzugefügt; es wurde kein Commit erstellt.
- **Regressionstest:**

  ```powershell
  .venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider `
    tests\test_variable_producer.py `
    tests\test_variable_producer_recovery.py `
    tests\test_variable_corpus_inventory.py `
    tests\test_variable_dataset.py `
    tests\test_variable_contract_hardening.py `
    tests\test_variable_features.py `
    tests\test_feature_dataset_export.py
  ```

  Ergebnis: **30 passed in 7,83 s**, zwei bestehende `audioread`-
  Deprecation-Warnungen (`aifc`, `sunau` entfernt in Python 3.13).
- **Schlussfolgerung und nächster Schritt:** Der angeforderte unveränderliche
  Dataset-v2-Export ist erstellt und inhaltlich/SHA-seitig geprüft.
  Variable-Waveformcache, Training/Fine-Tuning des
  `variable_tcn_bilstm_transition_control_v1` und unabhängiger Hörvergleich
  gegen Equal Power wurden nicht gestartet und sind außerhalb des hier
  abgeschlossenen Dataset-Schritts offen. Fehler, Cacheartefakte und Dataset
  bleiben durch Recovery-Roots beziehungsweise unveränderliche Pfade
  nachvollziehbar.
- **Dokumentationscheck:** `git diff --check` bestand mit Exit-Code 0; Git
  gab nur die bestehenden LF/CRLF-Hinweise aus. Nach Bereinigung des
  Eingabeinventars fand der gezielte PRIVE-Plan-Suchcheck keine Bewertung der
  Sammlungseignung oder -dokumentation und keine Aussage, Run 03 sei noch in
  Vorbereitung.

## 2026-09-25 — Diagnose der `unsupported_meter`-Rejections in PRIVE

- **Fragestellung/Reasoning:** Klären, ob die leeren PRIVE-Train-Paare wegen
  tatsächlich unbrauchbarer Beatpositionen oder wegen der globalen
  Metrumprüfung von Candidate Protocol 2 abgelehnt wurden.
- **Eingaben/Setup:** Read-only Join der Pairmanifeste für „Meltdown“ → „Life
  That We Dream Of“, „Birds“ → „02 ASCENSION“ und „Inferno“ → „VENGEANCE“ mit
  den Merge-v2-Analysen, adressiert durch Source-/Target-Audio-SHA, unter
  `output/pre_analysis/prive_scantraxx_extension_merge_v2_20260923_run01`.
  Analysevertrag `librosa_auftakt_monotonic_partial_v2`, Samples bei 44.100 Hz.
  Codepfad `src/candidates/variable.py` und Candidate Protocol 2 wurden
  lesend geprüft; keine Audiodatei, kein Cache und kein Dataset wurde erzeugt
  oder verändert.
- **Prüfumfang/Ergebnis:** Der Variable-Candidate-Generator weist das ganze
  Paar sofort ab, falls irgendein Beat-Tupel in Source oder Target
  `beats_in_bar != 4` trägt; die Prüfung läuft vor Provenienz-, Fenster- und
  Kandidatenprüfung. „Meltdown“ hat zwei lokal als 3/4 markierte Inseln bei
  107,62–110,82 s und 143,22–145,22 s; eine read-only Auswertung der
  zusammenhängenden, vollständigen 4/4-Fenster findet 78 vollständige
  4/4-Takte, maximal 34 am Stück. „Birds“ hat in Source eine einzelne
  3-Beat-Insel bei 21,77–22,52 s; Source/Target sind Merge-v2-akzeptiert und
  enthalten 129/128 vollständige 4/4-Takte, maximal 26/60 am Stück.
  „Inferno“ hat mehrere lokal als 3/4 markierte Inseln in Source und Target;
  beide Merge-v2-Analysen sind akzeptiert und enthalten 120/91 vollständige
  4/4-Takte, maximal 47/58 am Stück. In den drei untersuchten Pairmanifesten wurde damit
  `unsupported_meter` als globale Policy-Rejection bestätigt, nicht als
  Nachweis, dass keinerlei beat-synchrone 4/4-Fenster existieren.
  Zusatzbefund: Das Target von „Meltdown“ hat nur Fallback-Provenienz, weil
  seine Merge-Abdeckung 0,858 unter der 0,98-Schwelle liegt; die frühe
  Metrum-Rejection verdeckt diesen separaten Provenienzgrund.
- **Schlussfolgerung und nächster Schritt:** Die sechs Tracks der drei Paare
  besitzen jeweils mindestens einen zusammenhängenden 4/4-Block von 16 oder
  mehr Takten; damit sind strukturelle Pre-/Postfenster bis acht Takte
  vorhanden. Es ist plausibel, daraus Kandidaten zu gewinnen, ohne 3/4-Inseln
  umzudeuten. Ein späterer read-only In-Memory-Smoke fand in „Birds“ →
  „02 ASCENSION“ 10.602/5.841/3.306/1.575 ungerankte Kandidaten für
  2/4/6/8 Takte und in „Inferno“ → „VENGEANCE“ 6.298/3.570/2.184/1.296.
  Das sind keine exportierten Trainingsbeispiele und kein Nachweis
  musikalischer Downbeat-Korrektheit. „Meltdown“ → „Life That We Dream Of“
  bleibt wegen Target-Fallback-Provenienz abgelehnt. Daraufhin wurde der
  Candidate-v2-Metrumfilter geändert: Metrum- und Kontiguitätsbedingungen
  gelten pro Fenster, bestehende Candidate-/Datasetmanifeste bleiben
  unverändert. Für neue Daten ist ein neuer Producer-/Datasetroot nötig;
  SHAs/Splits sind dort erneut zu prüfen.

## 2026-09-25 — Variable Candidate-v2: lokale 4/4-Fenster

- **Fragestellung/Reasoning:** Nicht ganze Tracks wegen lokaler Nicht-4/4-
  Markierungen verwerfen, aber weiterhin ausschließlich Kandidaten mit
  vollständigen, zusammenhängenden 4/4-Fenstern für 2/4/6/8 Takte zulassen.
  `unsupported_meter` soll nur auftreten, wenn kein Kandidat einer
  angeforderten Länge möglich ist und der Metrumausschluss dafür ursächlich
  ist.
- **Eingaben/Setup:** Synthetische Beat-Grid-Fixtures einschließlich
  3/4-only und 4/4-/3/4-/4/4-Mischung; erkannte Grid-Metadaten; `.venv`;
  Änderungen in `src/candidates/variable.py`,
  `tests/test_variable_contract_hardening.py` und
  `docs/CANDIDATE_PROTOCOL.md`.
- **Testumfang/Befehle:**
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_variable_contract_hardening.py tests\test_candidates.py tests\test_partial_merge.py`
  sowie
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_variable_producer.py tests\test_multi_batch_render.py`.
- **Ergebnis:** Erste Gruppe **32 passed in 6,36 s**; zweite Gruppe
  **15 passed in 6,16 s**; keine Fehler oder Warnungen. Mixed-Meter-Fixture
  liefert Kandidaten für 2/4/6/8 Takte an lokalen 4/4-Grenzen. Reine
  3/4-Fixtures liefern `unsupported_meter`; Nicht-4/4-Beatgrenzen werden
  nicht als Candidate-Cutpoints ausgegeben. Source-/Target-Boundary-Limits
  werden nach dem lokalen 4/4-Fensterfilter angewandt, damit Metruminseln
  brauchbare 4/4-Grenzen nicht aus dem Top-N verdrängen. Zusätzlich lief der
  geänderte Generator read-only auf den SHA-gebundenen Analysen dreier echter
  Train-Paare: „Birds“ → „02 ASCENSION“ ergab 10.602/5.841/3.306/1.575,
  „Inferno“ → „VENGEANCE“ 6.298/3.570/2.184/1.296 ungerankte Kandidaten für
  2/4/6/8 Takte; „Meltdown“ → „Life That We Dream Of“ blieb korrekt an
  `target_grid_provenance_rejected` gesperrt. Das waren In-Memory-Ergebnisse,
  keine geschriebenen Pairmanifeste.
- **Abschließender Regressionstest:** Nach Ergänzung einer Regression, die
  einen möglichen kürzeren Übergang trotz nicht möglicher langer Länge
  absichert, wurde die kombinierte Gruppe ausgeführt:
  `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_variable_contract_hardening.py tests\test_candidates.py tests\test_partial_merge.py tests\test_variable_producer.py tests\test_multi_batch_render.py`.
  Der erste kombinierte Lauf bestand mit **48 passed in 5,42 s**; die
  abschließende Wiederholung nach Formatierung bestand mit **48 passed in
  5,57 s**. Beide ohne Fehler oder Warnungen.
- **Schlussfolgerung und nächster Schritt:** Regressionen bestätigen den
  neuen Fensterscope und unveränderte Integration in Producer/Batch. Der
  Realpaar-Smoke bestätigt, dass die lokale Filteränderung Kandidaten
  freigibt, ohne Provenienzfilter zu lockern. Es wurde kein Producerlauf,
  Datasetexport oder Training gestartet; der bisherige
  unveränderliche Datasetroot bleibt unverändert. Für eine aktualisierte
  Stichprobe ist ein neuer Producer- und Datasetroot mit geschlossener
  Testsplitauthorität sowie anschließendem SHA-/Leakage-Audit erforderlich.
# Desktop-GUI-Prototyp, 2026-10-06

- **Fragestellung und Reasoning:** Wie kann das vorhandene BeatBridge-GUI-
  Mockup als Desktop-App nutzbar werden, ohne die produktiven Audio-
  Abhaengigkeiten zu vergroessern oder Mock-Daten als echte Pipeline-Ergebnisse
  auszugeben? Die GUI-Spezifikation laesst Framework und Packaging offen und
  sieht eine gestufte Umsetzung vor.
- **Eingaben/Setup:** Bestehendes Mockup unter `prototypes/gui-mockup/`,
  Spezifikation `docs/GUI_SPECIFICATION.md`, Windows und Repository-
  Pythonumgebung `.venv`.
- **Umfang:** `src.gui_app` startet das lokale Mockup in einem nativen
  pywebview-Fenster. `requirements-gui.txt` haelt pywebview optional. Das
  Fenster bindet weiterhin weder Pipeline noch Manifeste an und verwendet
  keine Netzverbindung. Die Framework-Entscheidung und die Grenze zur
  manifestbasierten Stufe A sind in `GUI_SPECIFICATION.md` festgehalten.
- **Testumfang/Ergebnis:** In dieser Umsetzung wurde kein Testlauf und kein
  manueller App-Durchklick ausgefuehrt. Die Windows-WebView2-Runtime wird fuer
  den Start benoetigt.
- **Schlussfolgerung und naechster Schritt:** Der Desktop-Einstiegspunkt ist
  vorbereitet, der GUI-Prototyp ist damit noch nicht als Laufzeitverhalten
  verifiziert. Als naechstes Abhaengigkeit installieren, App starten und den
  Mockup-Durchklick vornehmen; danach den manifestbasierten Review-MVP gemaess
  Stufe A planen.

## 2026-10-06 — Native Python-Review-GUI

- **Fragestellung/Reasoning:** Der Nutzer praezisiert, dass die GUI nativ in
  Python laufen soll und keine WebView sein soll. Der zuvor erstellte
  pywebview-Launcher wird als Zwischenstand verworfen. PySide6/Qt Widgets
  passt zum bestehenden Python-Backend und erlaubt das Weiterverwenden der
  HTML-Oberflaeche als visuelle Referenz, ohne sie zur Laufzeit zu benoetigen.
- **Eingaben/Setup:** Bestehende `GUI_SPECIFICATION.md`,
  `BATCH_RENDERING_PROTOCOL.md`, `RENDERED_TRANSITION_METRIC_PROTOCOL.md`,
  `output/batches/help_to_breath_ranked/manifest.json` als lokales
  Formatbeispiel, Windows-Repository mit `.venv`.
- **Umfang:** `src.gui_app` startet ein natives Qt-Widgets-Fenster.
  `src/gui/manifest.py` liest Single-Pair-Batchmanifeste read-only und
  adaptiert additive/historische Felder; `main_window.py` zeigt Trackpaare,
  Varianten, Scores, Fehler und Cue-/Rendergrenzen, spielt je eine WAV ab und
  speichert eine Auswahl separat; `waveform.py` berechnet die WAV-Huellkurve
  in einem Worker. Auswahlvertrag: `docs/GUI_SELECTION_PROTOCOL.md`.
  `requirements-gui.txt` fuehrt PySide6 optional. Pipeline-Steuerung,
  Neurendering, Mehrtrack-Sequenz und Endexport bleiben ausserhalb dieses
  Review-MVP.
- **Testumfang/Ergebnis:** Kein Testlauf und kein manueller App-Durchklick in
  dieser Session. PySide6 wurde nicht installiert. Die UI kann daher noch
  nicht als Laufzeit-verifiziert gemeldet werden. Vorhandene Aenderungen in
  nicht GUI-bezogenen Dateien wurden nicht bearbeitet.
- **Schlussfolgerung/naechster Schritt:** Die native UI und der
  manifestgebundene Auswahl-Sidecar sind implementiert. PySide6-Abhaengigkeit
  installieren, ein Paarmanifest oeffnen und Wiedergabe/Wellenform/Sidecar
  manuell pruefen; Reibungspunkte dokumentieren. Danach die GUI um
  Pipeline-Aufgaben und spaeter Mehrtrack-Assembly erweitern.

## 2026-10-06 — Nativer Mehrtrack-Transition-Builder

- **Fragestellung und Reasoning:** Der primaere Ablauf soll mehrere Songs
  aufnehmen, Analyse bei Bedarf erlauben und einen manuellen Uebergang von
  Song A an Cuepoint A zu Song B an Cuepoint B erzeugen. Der Nutzer moechte
  dafuer eine echte native Python-App statt eines Webinterfaces. Die vorhandene
  Pipeline kann ein A/B-Paar mit manuellen Cuepoints rendern; daher wird dieser
  konkrete Durchstich umgesetzt. Der trainierte Learned-Cue-Ranker ist laut
  `ML_MODEL_CURRENT_STATE.md` nicht als Standard fuer reale Hoerqualitaet
  freigegeben; die UI darf die technische Render-Metrik nicht als dessen
  Modellurteil ausgeben.
- **Eingaben/Setup:** Vorhandene native PySide6-Review-GUI, GUI-Spezifikation,
  Pipeline `render_transition`, Trackanalyse `PreAnalysis` und technische
  Renderbewertung `rank_rendered_transitions`; Repository-Pythonumgebung
  `.venv`.
- **Umfang:** `src.gui.transition_builder` stellt eine native Trackbibliothek,
  optionalen Analyseaufruf, zwei Trackselektoren, klickbare Wellenformen und
  Zeit-Cuepoints, Laenge-/Rendererauswahl, asynchrones Rendering, Audioplayer,
  Ergebniswellenform und technische Bewertung bereit. Neu erzeugte WAVs und
  JSON-Provenienz werden unter `output/gui_transitions/` gespeichert. Der
  Launcher `src.gui_app` startet dies standardmaessig; der alte Manifestreview
  bleibt per `--review-manifest` oder Manifestargument erreichbar. Die
  Spezifikation, Statusseite und Startanleitung wurden an den Ablauf angepasst.
- **Testumfang/Ergebnis:** Kein Testlauf und kein manueller App-Durchklick in
  dieser Session; insbesondere sind PySide6-Laufzeit, Audioausgabe, Codec-
  Unterstuetzung und Pipeline-Render aus der GUI noch nicht verifiziert.
- **Schlussfolgerung und naechster Schritt:** Funktionaler nativer
  A/B-Renderdurchstich ist implementiert, aber noch nicht als verwendbar
  abgenommen. Als naechstes PySide6 installieren, mehrere repräsentative
  Dateien laden, Analyse/Wiedergabe/Cuepointwechsel und Render pruefen und
  eventuelle Laufzeitprobleme dokumentieren. Danach Projektpersistenz,
  automatische Kandidatenerzeugung und spaeter Mashup-Assembly priorisieren.

## 2026-10-06 — Mehrtrack-Kanten, ML-Auswahl und Mockup-Abgleich

- **Fragestellung und Reasoning:** Der Analyse-Cache lud im GUI nicht
  verlaesslich, Modellruns liessen sich beim Uebergang nicht waehlen und der
  Ablauf war auf ein A/B-Paar beschraenkt. Zusaetzlich wich die native Ansicht
  sichtbar vom bestehenden DAW-Mockup ab. Cacheidentitaet bleibt SHA- und
  analyseversionsgebunden; der Pfad soll waehlbar sein. Fuer laengere
  Sequenzen braucht jede Nachbarkante eigene Cuepoints, Einstellungen und
  Vorschauergebnisse. Die Ansicht wird an Mockup-Hierarchie, Spurenfarben und
  Inspectorposition angenaehert, ohne vorzugeben, dass die noch fehlenden
  Analyse-/Alternativenpanels bereits integriert sind.
- **Eingaben/Setup:** Vorhandene PySide6-Oberflaeche, Mockup
  `docs/gui-mockups/beatbridge-daw-data-concept-v1.png`,
  `docs/GUI_SPECIFICATION.md`, Analyse-Cache `PreAnalysis`, lokale
  Trainingsmanifeste/Checkpointloader aus den ML-Evaluationen. Repo-Root und
  `.venv` als vorgesehene Laufzeitumgebung.
- **Umfang:** Analyse-Cache nutzt nun einen absoluten Repository-Default oder
  einen in der UI waehlbaren Ordner und meldet Cachetreffer/Neuanalyse. Die
  Sequenz kann Tracks anhaengen, umsortieren und entfernen; benachbarte Kanten
  werden separat bearbeitet. Einfuegen erhaelt Einstellungen und Ergebnisse
  bereits bestehender Kanten. A/B-Waveforms haben Cyan/Korall-Akzente und
  stehen gestapelt neben dem Inspector. Eine App-Leiste bietet Kantenwechsel
  und Wiedergabe der gerenderten Vorschau. Die ML-Liste zeigt abgeschlossene
  lokale Runs der drei im Adapter unterstuetzten Modellfamilien mit Checkpoint;
  die Inferenz bindet an Dataset-SHA/Normalisierung und gespeicherte
  Checkpoint-Provenienz. ML-Vorschauen enthalten Kontext vor/nach dem
  gerenderten Modellfenster, damit die technische Render-Metrik gueltige
  Vor-/Nachlaufdaten erhaelt. UI-Status, Spezifikation und Startanleitung
  wurden entsprechend aktualisiert.
- **Testumfang/Ergebnis:** In dieser Arbeit wurde kein Testlauf und kein
  manueller App-Durchklick ausgefuehrt. Keine Laufzeitbehauptung fuer
  Cachetreffer, Qt-Signale/Layout, Audioausgabe oder die drei ML-Inferenzpfade.
  Die optische Struktur wurde am gespeicherten Mockup-Bild abgeglichen; ein
  pixelgenauer Gleichstand ist nicht umgesetzt. Quelldateien der Audios und
  nicht GUI-bezogene Aenderungen wurden nicht angetastet.
- **Schlussfolgerung und naechster Schritt:** Der Arbeitsstand deckt jetzt den
  gewuenschten Mehrtrack-Ablauf und die Modellwahl konzeptionell ab und lehnt
  sich staerker an das Mockup an. Als naechstes die App mit PySide6 manuell
  starten, mindestens drei Tracks analysieren, A→B und B→C getrennt einstellen,
  Cache erneut laden, Baseline sowie einen lokalen ML-Run rendern und die
  resultierenden Layout-/Laufzeitprobleme nachtragen. Danach erst fehlende
  Mockup-Bereiche wie Analysepanels, Variantenvergleich und Mashup-Export
  integrieren.

## 2026-10-06 — Drag-and-Drop, Cache-Pruefung und Waveform-Zoom

- **Fragestellung und Reasoning:** Tracks sollen ohne Dateidialog aus der
  Bibliothek in eine Mashup-Sequenz eingefuegt, dort per Ziehen sortiert und
  ebenso aus dem Windows-Explorer importiert werden koennen. Beim Import ist
  zuerst ein passender Analyse-Cache zu laden; Cache-Misses sollen klar
  `Nicht analysiert` zeigen, ohne eine moeglicherweise lange Analyse still
  anzustossen. Die Waveform braucht zoom- und verschiebbare Zeitansicht, wobei
  Cuepointklicks weiterhin auf die sichtbare Zeitspanne abgebildet werden.
- **Eingaben/Setup:** Native PySide6-Widgets `transition_builder.py` und
  `waveform.py`, Cachevertrag der `PreAnalysis`-Klasse, Windows-Explorer-URLs,
  vorhandene lineare Mehrtrack-Sequenz. Pythonumgebung `.venv`.
- **Umfang:** Die Bibliothek stellt lokale Audio-URLs fuer Drag-and-Drop
  bereit. Die Sequenz akzeptiert Explorer-Dateien und Bibliothekstracks an der
  Drop-Position; interne Drops ordnen Sequenztracks neu. Umordnen verwirft
  laufende Kantenbindungen, ohne erzeugte Audiodateien zu loeschen. Eine neue
  Cache-only-API von `PreAnalysis` laedt nur gueltige aktuelle/Legacy-Eintraege
  und kehrt bei Cache-Miss ohne Analyse zurueck; die GUI prueft dies asynchron
  und zeigt Cache-Treffer, `Nicht analysiert` oder konkreten Prueffehler an.
  Waveforms zeigen einen hochaufgeloesten Ausschnitt; Mausrad zoomt am
  Zeigeranker, Shift+Mausrad oder Ziehen mit mittlerer Taste verschiebt,
  Doppelklick setzt die Gesamtansicht zurueck. Cuepointklicks verwenden den
  sichtbaren Ausschnitt.
- **Testumfang/Ergebnis:** Keine Tests und kein manueller GUI-Durchklick in
  dieser Arbeit. Drag-and-Drop-Events, Cache-Ladevorgaenge und Zoom/Cuepoint-
  Interaktion sind daher noch nicht zur Laufzeit verifiziert.
- **Schlussfolgerung und naechster Schritt:** Implementierung und Anleitung
  sind aktualisiert. Beim naechsten manuellen Durchklick Explorer-Import,
  Bibliothek→Sequenz, internes Sortieren, gueltigen Cache-Treffer, Cache-Miss,
  Zoom/Pan und Cuepointwahl pruefen; Fehler im Log ergaenzen. Die explizite
  Analyseaktion bleibt fuer Cache-Misses verfuegbar.

## 2026-10-06 — Korrektur: Waveform-Overlay und Explorer-Drop

- **Fragestellung und Reasoning:** Der Nutzer meldet, dass der obere
  Waveform-Bedienhinweis die Audiodarstellung ueberlagert und Explorer-Drops
  nicht ankommen. Der Bedienhinweis gehoert in die Spurueberschrift. Qt-Item-
  Views empfangen native Drops auf ihrem Viewport, daher wird die externe
  Dropannahme explizit dort und zusaetzlich auf der Sequenzflaeche behandelt;
  interne Sequenzbewegungen laufen weiter ueber den Item-View.
- **Eingaben/Setup:** Nutzerfeedback zum laufenden GUI, `WaveformWidget`,
  `SequenceListWidget`, `SequenceDropPanel`; native Qt-/Windows-URL-Mime-Daten.
- **Umfang:** Bei geladener Waveform zeichnet der Painter keinen Hinweistext
  mehr in die Kurve. Zoom-/Pan-Hinweise stehen in der Spurueberschrift.
  Sequenz-Viewport und Sequenzpanel akzeptieren lokale Datei-URLs und den
  internen BeatBridge-Track-Mime-Typ. Externe Drops werden als Kopie an die
  bestehende Import-/Cache-Pruefung uebergeben; interne Moves bleiben
  Umsortierungen.
- **Testumfang/Ergebnis:** Kein Test und kein manueller Windows-GUI-Durchklick
  in dieser Arbeit; der gemeldete Fehler ist daher noch nicht am laufenden
  Explorer bestaetigt behoben.
- **Schlussfolgerung und naechster Schritt:** Der Qt-Drop-Pfad ist expliziter
  und der Text wurde aus der Waveform entfernt. Im naechsten Durchklick jeweils
  eine Datei auf die Sequenzliste und auf den freien Sequenzbereich ziehen,
  dann interne Sortierung pruefen und die Waveform bei mehreren Zoomstufen
  visuell kontrollieren.

## 2026-10-06 — Korrektur: Drops ausserhalb der Sequenz und Waveformdetail

- **Fragestellung und Reasoning:** Rueckmeldung: Explorer-Drops werden nur in
  der Sequenz angenommen und Zoom zeigt einen Balken statt einer lesbaren
  Wellenform. Die Importannahme muss auch die Bibliothek und den uebrigen
  App-Arbeitsbereich umfassen. Die bisherige Min/Max-Huellkurve nutzte nur
  `abs(signal)` und lag dadurch einseitig ueber der Nulllinie; signierte
  Minima/Maxima stellen beide Signalhalbwellen dar.
- **Eingaben/Setup:** Nutzerfeedback zum laufenden Qt-GUI, `ApplicationDropWidget`,
  `TrackLibraryList`, `SequenceDropPanel`, `SequenceListWidget` und
  `_WaveformTask`.
- **Umfang:** Lokale Explorer-Dateien werden jetzt auch auf der gesamten
  App-Arbeitsflaeche und direkt in der Trackbibliothek angenommen; Sequenz-
  und Bibliothekseintrag-Drops bleiben speziell behandelt. Alle Pfade laufen
  durch dieselbe Erweiterungs-/Dateipruefung und Cache-Pruefung. Die
  Waveformaggregation berechnet pro Zeit-Bin signierte Kanalminima und
  -maxima, die um die Nulllinie gezeichnet werden.
- **Testumfang/Ergebnis:** Kein Test und kein manueller Windows-GUI-Durchklick
  ausgefuehrt. Explorer-Propagation ueber Kindwidgets und Darstellung mehrerer
  Audioformate/Zoomstufen sind noch nicht zur Laufzeit verifiziert.
- **Schlussfolgerung und naechster Schritt:** Die Importbereiche und die
  Datenbasis fuer eine beidseitige Waveform sind erweitert. Explorer-Datei auf
  Bibliothek, Sequenz, Waveform und freien Arbeitsbereich ziehen und die
  sichtbare Kurve bei 1x/mehrfach Zoom pruefen; bei weiterem Drop-Verlust die
  konkreten `QDragEnterEvent`-/`QDropEvent`-Empfaenger instrumentieren.

## 2026-10-06 — Waveform-Worker: veralteter Variablenname

- **Fragestellung und Reasoning:** Nutzer meldet beim Oeffnen des Fensters
  `Name levels is not defined`. Die signierte Waveformaggregation hatte
  `levels` durch `frame_minimums`/`frame_maximums` ersetzt, eine Laengenreferenz
  im Bucket-Index aber nicht aktualisiert.
- **Eingaben/Setup:** Nutzerbericht und `_WaveformTask.run()` in
  `src/gui/waveform.py`.
- **Umfang:** Die Bucket-Index-Laenge verwendet nun `len(frame_minimums)`, also
  exakt die Anzahl Frames, fuer die Minima und Maxima berechnet werden.
- **Testumfang/Ergebnis:** Kein Testlauf und kein App-Neustart ausgefuehrt.
  Der berichtete Namensfehler wurde statisch lokalisiert und die Referenz
  angepasst; Waveformdarstellung bleibt zur Laufzeit zu pruefen.
- **Schlussfolgerung und naechster Schritt:** Die `NameError`-Ursache ist im
  Code beseitigt. App erneut starten und Waveform laden; bei weiterem Fehler
  den vollstaendigen Traceback erfassen.

## 2026-10-06 — Waveform-Zoomdarstellung und Trackkopf

- **Fragestellung und Reasoning:** Nutzer meldet, dass beim Hineinzoomen nur
  Balken sichtbar sind und Songname/BPM in die Waveform hineinragen.
  Vereinzelte vertikale Min/Max-Striche wirken bei grober Aufloesung wie ein
  Balkendiagramm. Eine feinere signed Min/Max-Huellkurve mit verbundener,
  gefuellter Ober-/Unterkante bildet die Audioform lesbarer ab. Trackidentitaet
  und BPM gehoeren in die Spur-Kopfzeile, ausserhalb des Plotbereichs.
- **Eingaben/Setup:** Nutzerfeedback; `WaveformWidget.paintEvent`,
  `_WaveformTask.run` und `_build_track_wave_panel`.
- **Umfang:** Die Waveformaggregation erfasst bis zu 160.000 zeitliche Bins
  (begrenzt auf die Anzahl Audiosamples) und uebergibt NumPy-Arrays statt
  Python-Listen. Beim Zeichnen werden Bins passend zur Widgetbreite aggregiert;
  obere und untere Signalgrenze werden als verbundene, leicht gefuellte Form
  gezeichnet. Songdatei und BPM erscheinen in einer einzeiligen Trackkopf-
  Zusammenfassung, Gridprovenienz steht im Tooltip.
- **Testumfang/Ergebnis:** Kein Testlauf und kein GUI-Neustart ausgefuehrt.
  Darstellungsqualitaet und Zeichenlast bei Wiedergabe/Zoom sind noch nicht
  zur Laufzeit geprueft.
- **Schlussfolgerung und naechster Schritt:** Die visuelle Struktur ist
  korrigiert; bei der naechsten manuellen Nutzung die Gesamtansicht und starke
  Zoomstufen vergleichen und auf fluessiges Neuzeichnen achten.

## 2026-10-06 — Waveform nach NumPy-Umstellung leer

- **Fragestellung und Reasoning:** Nutzer meldet, dass die Waveform nach der
  letzten Huellkurven-Aenderung gar nicht mehr gezeichnet wird. Die
  Hintergrundaufgabe liefert jetzt NumPy-Arrays; `paintEvent` und `wheelEvent`
  verwendeten noch Listen-Wahrheitspruefungen, die bei mehrdimensionalen
  Arrays einen `ValueError` ausloesen.
- **Eingaben/Setup:** Nutzerfeedback und alle Referenzen auf `_minimums` in
  `src/gui/waveform.py`.
- **Umfang:** Beide Wahrheitspruefungen nutzen nun explizit `len(...)`; die
  Typannotationen erlauben Arraydaten und leere Listen fuer den Initialzustand.
- **Testumfang/Ergebnis:** Kein Testlauf und kein App-Neustart ausgefuehrt.
  Fehlerursache statisch identifiziert und korrigiert; Rendern bleibt
  laufzeitlich unverifiziert.
- **Schlussfolgerung und naechster Schritt:** Waveform- und Zoompfad koennen
  NumPy-Daten jetzt ohne implizite Array-Wahrheitspruefung verarbeiten. App
  neu starten und Audio laden; bei weiterem Fehler den GUI-Traceback erfassen.

## 2026-10-20 — Redaktioneller Humanize-Durchgang im Overleaf-Entwurf

- **Fragestellung und Reasoning:** Prüfen, ob die englische Thesis-Prosa erkennbare
  formelhafte Wiederholungen enthält, ohne wissenschaftliche Aussagen,
  Einschränkungen oder LaTeX-Verweise zu verändern. Der Durchgang betrifft die
  Kapitel 1 bis 6; Abstract, Conclusion und Appendix enthalten derzeit nur
  TODOs und wurden nicht umformuliert.
- **Eingaben/Setup:** `overleaf/chapters/*.tex`, Humanize-Referenzen und
  `surface_scan.py`; ausgeführt mit `.venv\Scripts\python.exe -X utf8` im
  Repository. Der Scanner liest rohes TeX, sodass Befehle, Tabellen und
  wiederkehrende Fachbegriffe manche Kennzahlen verfälschen können.
- **Testlauf 1 — Ausgangsscan:** `surface_scan.py` zunächst für
  `01_introduction.tex`, danach als Batch für die sechs ausgearbeiteten
  Kapitel. Ergebnis: Introduction 1.791 Wörter, 26 Trikolons, vier parallele
  Satzanfänge; Results 2.083 Wörter, 24 Trikolons, drei parallele Satzanfänge;
  Discussion 2.166 Wörter, 34 Trikolons, drei parallele Satzanfänge. Der
  Scanner meldete Wiederholungen, überwiegend technische Wendungen wie
  Längenangaben und Protokollbegriffe. Schlussfolgerung: Frage-Überschriften,
  nummerierte Beitrags-/Prioritätsformeln und einige doppelte Vorbehalte
  gezielt bearbeiten; technische Listen beibehalten.
- **Testlauf 2 — Nachscan:** Derselbe Batchbefehl nach den Textänderungen
  und erneut nach der abschließenden Faktenprüfung. Final: Introduction
  1.742 Wörter, 25 Trikolons, drei parallele Satzanfänge; Results 2.054
  Wörter, 22 Trikolons, zwei parallele Satzanfänge; Discussion nach der
  letzten Einzelkorrektur 2.118 Wörter, 33 Trikolons, zwei parallele
  Satzanfänge. Die Satzlängen-CV blieb bei
  Introduction 0,448→0,440, Results 0,809→0,827 und Discussion
  0,423→0,412 ungefähr stabil. Die Frage-Überschriften in Results wurden
  als Sachüberschriften formuliert; der Scanner zählt diese TeX-Überschriften
  nicht als rhetorische Fragen. Schlussfolgerung: Der Durchgang reduziert die
  tatsächlich bearbeiteten Muster, ohne die Satzlängen stark zu glätten.
- **Testlauf 2a — Trefferprüfung:** Die JSON-Treffer für wiederholte Phrasen,
  partizipiale Enden und Wortliste wurden je Kapitel ausgegeben. Viele Treffer
  waren TeX-Formeln oder Fachbegriffe (`\ref`-Ziele, Tabellenbefehle,
  Übergangslängen); einzelne Partizipialtreffer waren Satzmitten statt
  Nachträge. In Discussion blieb `Moreover` als entbehrlicher Übergang und
  wurde entfernt. Ein anschließender `--text`-Scan dieses Kapitels meldete
  Wortliste 0,0/1.000 Wörter und Satzlängen-CV 0,412. Schlussfolgerung:
  Scanner-Zahlen nur nach Prüfung der zitierten Stellen als Stilbefund nutzen.
- **Testlauf 3 — Diff und Inhaltsanker:** `git -C overleaf diff --check`
  bestand ohne Whitespace-Fehler. Ein `.venv`-Python-Vergleich der fünf
  geänderten Kapitel mit `HEAD` fand dieselben `\cite`-, `\ref`- und
  `\label`-Befehle sowie dieselben Ziffern-Tokens; alle fünf Dateien hatten
  eine geschlossene Klammerbilanz. Das prüft syntaktische und numerische
  Anker, nicht die vollständige semantische Gleichwertigkeit. Der Diff wurde
  deshalb zusätzlich gelesen; ausgelassene Aussagen zu globalem
  Similarity-Score, explizitem Renderer und artefaktorientiertem Design
  wurden vor dem letzten Check wiederhergestellt.
- **Testlauf 4 — LaTeX-Gesamtbuild:**
  `compile_latex_document(path=overleaf, mainFile=CGThesis.tex)` erreichte
  die Kapitel, scheiterte aber mit `error: program not found` beim
  Bibliographie-Schritt. `CGThesis.tex` verwendet `\addbibresource` und
  `\printbibliography`; der Build meldete zunächst undefinierte Zitate und
  mehrere Overfull-/Underfull-Boxen. `Get-Command` fand lokal weder
  `latexmk`, `biber`, `pdflatex` noch `xelatex`. Schlussfolgerung: Kein
  erfolgreicher Gesamt-PDF-Build nachweisbar; Bibliographie-Programm in der
  Build-Umgebung klären und dann erneut kompilieren.
- **Redaktionelle Beobachtung:** Kapitel 4 bezeichnet die GUI noch als
  geplant und behauptet, es gebe keinen GUI-Code. `src/gui_app.py` und der
  aktuelle `docs/STATUS.md` belegen inzwischen einen nativen GUI-Pfad.
  Dieser sachliche Aktualisierungsbedarf wurde beim reinen Stil-Durchgang
  nicht stillschweigend umgeschrieben; der Implementierungsstand muss vor
  Abgabe separat mit Kapitel 4 abgeglichen werden.
