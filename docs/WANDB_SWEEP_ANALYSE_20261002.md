# Analyse des TCN/BiLSTM-Sweeps vom 2026-10-02

## Datengrundlage und Verifikation

Quelle: `wandb_export_2026-10-02T09_20_57.391+02_00.csv`, Snapshot vom
2026-10-02, 09:20:57 MESZ. SHA-256:
`aa342d7813fcca2a5bdfc4cbb87445bc4d0b7970025ef7b597f125c7267a431e`.
92 Zeilen, 329 Spalten, ausschließlich Sweep `nqntmdi0` und das feste
`tcn_bilstm_transition_control_v1`. Dies ist keine Auswertung des Vocal-MLP
oder des variablen TCN-Modells.

Alle 91 Runs mit Metriken verwenden Dataset `52bc9d1cebfd1b82d2ea`
(370 Train-/50 Validation-Beispiele), Datasetmanifest-SHA
`4708a8fa983354903759a934f48d36b6450510809773dda2a12f9408821886b7`,
Objective v4, `differentiable_full_band_transition_v1` und Seed `20260930`.
Die beiden exportierten Best-Loss-Felder stimmen in allen 91 Zeilen überein.
Alle 91 lokalen History-Dateien sind vorhanden, ihre Manifest-SHAs stimmen,
und ihr minimaler Validation-Loss stimmt mit dem Export innerhalb 1e-10 überein.
Keine Audio-/Testdaten wurden geöffnet und kein Training gestartet.

Die CSV enthält Summary-Metriken, keine vollständigen Kurven. Die zusätzliche
Kurven- und Best-Epochen-Auswertung basiert auf den lokalen Histories unter
`output/training_runs/wandb_sweeps/tcn_bilstm_transition_control_v1/nqntmdi0/`.
`validation/loss` und die einzelnen exportierten Loss-Komponenten stammen
aus der letzten geloggten Epoche. Sie dürfen nicht als Komponenten des
Best-Loss interpretiert werden. Die Komponenten unten wurden explizit aus
der jeweils besten History-Epoche entnommen.

## Umfang und Ranking

| Zustand | Runs | Median Best-Loss | Minimum | Maximum |
|---|---:|---:|---:|---:|
| finished/completed, alle 150 Epochen | 35 | 0,316314 | 0,261587 | 0,319606 |
| killed, 52–69 Epochen | 56 | 0,320390 | 0,293404 | 0,324889 |
| running, noch ohne Metriken | 1 | – | – | – |

Die Summe exportierter Run-Laufzeiten beträgt 23,145 Stunden. Das ist eine
Summe von Run-Runtimes, keine GPU-Zeitmessung und keine belastbare Messung
der gesamten Sweep-Wandzeit. Der Median der besten Epoche abgeschlossener
Runs beträgt 71 (Spanne 28–149).

| Run | Best-Loss | Best-Epoche | Basis-LR | Batch | Dropout | Kernel | Dilation | Weight Decay | Clip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| vlfwfn7a | 0,261587 | 77 | 0,0002698791 | 3 | 0,1 | 5 | 4 | 0,00001 | 2 |
| fxhhidgi | 0,261624 | 81 | 0,0004795509 | 7 | 0 | 5 | 4 | 0,0001 | 0,5 |
| sifded82 | 0,262754 | 97 | 0,0010704191 | 7 | 0 | 3 | 4 | 0,0001 | 2 |
| 5tvxznt0 | 0,264914 | 85 | 0,0005286518 | 3 | 0 | 5 | 2 | 0,00001 | 0,5 |
| brql6who | 0,293181 | 96 | 0,0003550019 | 5 | 0,1 | 5 | 1 | 0,0001 | 2 |

Die Top 4 bilden einen deutlich besseren Loss-Bereich. Der beste Run liegt
17,30 % unter dem Median der abgeschlossenen Runs. Diese Bezugsgröße ist
die Sweep-Verteilung, keine Equal-Power-Baseline oder unabhängige Evaluation.
Die ersten beiden Runs unterscheiden sich nur um 0,0000363 beziehungsweise
0,01386 % relativ zum besten Loss. Ohne Wiederholungen mit mehreren Seeds
ist dies kein belastbarer Nachweis einer besseren Konfiguration.

## Hyperparameter: explorative Muster

Bayessche adaptive Auswahl, unterschiedliche Trainingsbudgets und
Hyperband-Selektion verhindern eine kausale Interpretation von Gruppenmedians.
Auch nur abgeschlossene Runs sind eine vorselektierte Stichprobe.

| Parameterwert | Runs mit Metriken | Davon finished | Best-Loss < 0,30 |
|---|---:|---:|---:|
| Dropout 0 | 24 | 11 | 3 |
| Dropout 0,1 | 31 | 10 | 3 |
| Dropout 0,2 | 36 | 14 | 0 |
| Kernel 3 | 29 | 10 | 2 |
| Kernel 5 | 35 | 11 | 4 |
| Kernel 7 | 27 | 14 | 0 |
| Dilation 1 | 37 | 15 | 1 |
| Dilation 2 | 29 | 8 | 2 |
| Dilation 4 | 25 | 12 | 3 |
| Weight Decay 0,00001 | 22 | 7 | 2 |
| Weight Decay 0,0001 | 37 | 20 | 4 |
| Weight Decay 0,0003 | 32 | 8 | 0 |
| Clip 0,5 | 35 | 13 | 3 |
| Clip 1 | 27 | 15 | 0 |
| Clip 2 | 29 | 7 | 3 |

Für einen gezielten Folgevergleich sind Kernel 3/5, Dilation 2/4,
Dropout 0/0,1, Weight Decay 1e-5/1e-4 und Clip 0,5/2 plausible Kandidaten.
Die beiden Spitzenruns teilen Kernel 5 und Dilation 4. Batch 3 und 7 sind
beide unter den Top 4. Die Top-4-Lernraten reichen von 2,70e-4 bis 1,07e-3.
Ein einzelnes LR-Optimum lässt sich daraus nicht ableiten.
Diese Vorschläge sind aus dem Export abgeleitete Versuchshypothesen,
keine bereits beschlossene Änderung des Suchraums.

## Wo entsteht der Loss-Gewinn?

Vergleich der gewichteten Beiträge an der besten Epoche des Spitzenruns
mit `1w51w9t6` als transparent gewähltem Run aus dem typischen Loss-Bereich.
Dieser einzelne Referenzrun ist kein gemittelter Gruppenvergleich.

| Gewichteter Beitrag | vlfwfn7a, Epoche 77 | 1w51w9t6, Epoche 71 |
|---|---:|---:|
| Energy shape | 0,067340 | 0,121417 |
| Vocal boundary | 0,102229 | 0,103642 |
| Transient artifact | 0,074582 | 0,074838 |
| Vocal overlap | 0,012827 | 0,013946 |
| Control smoothness | 0,003769 | 0,001322 |
| Control curvature | 0,000605 | 0,000173 |
| Gesamtloss | 0,261587 | 0,315410 |

Die Energiekomponente sinkt um rund 44,5 % und erklärt nahezu den gesamten
Netto-Loss-Gewinn dieses Vergleichs. Glattheits- und Krümmungsstrafen steigen.
Der Transientenbeitrag bleibt nahezu unverändert. Das Modell erzielt also
hier vor allem einen günstigeren Energieverlauf unter dem Proxy-Objective.
Ein allgemeiner hörbarer Qualitätsgewinn oder natürlichere Vocals folgt
daraus nicht. Beim besten Run machen Vocal-Grenzen und Transienten zusammen
rund 67,6 % des verbleibenden Loss aus.

## Pruning und Training bis zur letzten Epoche

56/91 Runs mit Metriken (61,5 %) wurden beendet, alle zwischen Epoche 52
und 69. Das Muster passt zur dokumentierten Hyperband-Konfiguration mit
Prüfung ab 50 geloggten Epochen. Der CSV-Status `killed` allein beweist
jedoch weder Hyperband-Pruning noch einen manuellen Abbruch pro Run.
Die lokalen Manifeste dieser 56 Runs stehen weiterhin auf `running`;
das ist ein Statuspflegeproblem und kein Beleg für 56 aktive Trainings.

`sifded82` lag bis Epoche 50 bestenfalls bei 0,317780 und fiel erst später
auf 0,262754 (beste Epoche 97). Auch `fxhhidgi` stand bis Epoche 50 erst bei
0,310609 und erreichte später 0,261624. Damit ist nachgewiesen, dass frühe
Scores gute spätere Ergebnisse noch nicht zuverlässig unterscheiden.
`xdmd5cma` wurde nach 57 Epochen bei 0,293404 beendet, obwohl es im gesamten
Export Platz 6 erreicht. Diesen Kandidaten sollte ein kontrollierter
Folgeversuch mit vollem Budget prüfen; sein hypothetischer 150-Epochen-Loss
ist unbekannt. Eine Pruning-Änderung ist durch diesen Snapshot allein noch
nicht festgelegt.

Die letzte Epoche ist teilweise deutlich schlechter als die beste:
`dbo2krx3` 0,311375 → 0,348542 und `1t6tmnsr` 0,317522 → 0,346766.
Das ist mit Überanpassung oder instabiler Optimierung vereinbar, aber ohne
zusätzliche Diagnose kein eindeutiger Ursachennachweis. Auswahl und
Inferenz sollten auf der besten Validation-Epoche beruhen.

Alle 91 geprüften Runmanifeste referenzieren keine Best-Checkpoints.
Die erfolgreichen Sweep-Konfigurationen müssen mit aktivierter
Checkpoint-Speicherung erneut trainiert werden, bevor sie hörbar evaluiert
werden können. Das Export-Ranking allein stellt kein nutzbares Modell bereit.

## Nächste Experimente

1. `vlfwfn7a` und `fxhhidgi` mit mehreren Seeds und identischem vollen Budget
   nachtrainieren, Best-Checkpoints speichern und Mittelwert/Streuung melden.
2. `xdmd5cma` mit vollem Budget prüfen und frühe Scores gegen finale Scores
   auswerten, bevor das Hyperband-Gate angepasst wird.
3. Die gewählten Best-Checkpoints auf gleichen Validation-Stimuli geblendet
   gegen die bestehende Referenz hören. Energie, Vocal-Klarheit und
   Natürlichkeit getrennt bewerten. Testsplit bleibt bis zum eingefrorenen
   Evaluations-Gate geschlossen.

Reproduzierbare Auswertung:
`.venv\Scripts\python.exe -X utf8 scripts/analyze_wandb_export_20261002.py`.
Maschinenlesbare Ergebnisse und visuell geprüfte Grafik liegen unter
`output/analysis/wandb_sweep_20261002/`. Die Grafik beschränkt die Kurvenachse
auf Loss 0,25–0,36 und Epochen 1–150; die hohe Initialisierung ist abgeschnitten.
