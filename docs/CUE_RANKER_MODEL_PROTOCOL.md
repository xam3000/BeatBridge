# Cue-Ranker Teacher Contract v1

_Eingefrorener Teachervertrag für Dataset Format 3, eingeführt 2026-08-25._

Diese Datei definiert nur die Offline-Labelstufe, kein Ranking-Modell und
keine Inferenzintegration. Ein Release bindet den SHA-256 des
Control-Runmanifests und `best.pt`, den State-dict-Schemahash,
`variable_tcn_bilstm_transition_control_v1`, Objective v5,
`DifferentiableVocalAwareRenderer`, `local_grid_target_to_source_v1`,
Normalizer, Grid-, Audio-, Stem-Payload- und Backend-Provenienz. Es wird
`weights_only=True` und `eval()` verwendet; der Job führt keine
Optimizer-Schritte aus.

`teacher_release.json` wird vor jedem Label-Load SHA-geprüft. CPU ist
bitgenaue Referenz; ein GPU-Release bindet Device, CUDA/cuDNN,
Python/PyTorch/NumPy, deterministische Flags und explizite Toleranz. Eine
Abweichung ist ein neuer Release und kein Resume.

Ein technisch gültiger Score ist `teacher_utility = -total_loss_v5`.
Zusätzlich muss der eingefrorene Render-Guard
`rendered_transition_baseline_v1` mindestens `0.50` erreichen.
Nichtendliche Inputs/Controls, Hash-/Alignment-/Rendererfehler erhalten
`teacher_status=failed` mit kanonischem Fehlercode. Ein Guard-Fehler oder
Score unterhalb der Schwelle erhält `teacher_status=guard_rejected`; beides
bleibt auditierbar und blockiert keine andere Gruppe.

## Train-/Validation-Auswertung (v1, 2026-08-25)

Der Ranker trainiert ausschließlich gegen die eingefrorenen Format-3-
`teacher_utility`-Labels. Pro Epoche schreibt `history.json` für Train und
Validation den gruppierten IPW-Listwise-Ranking-Loss sowie Metriken auf exakt
demselben loss-zulässigen Snapshot. Technische `failed`-Labels gehen weder in
Loss noch Qualitätsmetriken ein; `guard_rejected` bleibt als negativer
Teacher-Anker erhalten.

Validation berichtet deterministisch für Ranker, gleichverteilte gültige
Zufallsauswahl, `feature_baseline_v3`, BPM-only, Harmonie-only und den nicht
deploybaren Teacher-Oracle: Top-1-Agreement, Top-K-Overlap-Agreement, NDCG,
Top-1-Teacher-Utility und die Pearson-Korrelation der Ranker-Scores mit der
Teacher-Utility. Alle Werte erscheinen zusätzlich getrennt für 2/4/6/8
Takte; weniger als zwei loss-zulässige Kandidaten ergeben sichtbar `null`
statt einer Imputation. Tie-break ist überall `candidate_id`.

Diese Größen sind ausschließlich Teacher-Agreement. Sie sind ausdrücklich
**kein Nachweis hörbarer Übergangsqualität**; dafür bleibt eine getrennte,
unabhängige Renderer-/Hörstudie erforderlich. Der Runner nutzt keine
Candidate-IDs, Audio-SHAs, Rohsamplepositionen oder lokalen Audio-Pfade als
Modelleingabe und sendet keinerlei lokale Pfade an externe Dienste.
