# Beobachtungen, Entscheidungen und Gelerntes

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
