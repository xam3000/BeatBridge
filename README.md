# BeatBridge

## Dokumentation

Der aktuelle, verifizierte Projektstand und die weitere Dokumentation liegen unter [`docs/`](./docs/README.md).

- [Status und nächste Schritte](./docs/STATUS.md)
- [Projekt-Gesamtübersicht und Forschungsrahmen](./docs/Projekt-Gesamtuebersicht.md)
- [CLI verwenden](./docs/CLI.md)
- [Kandidatenvertrag](./docs/CANDIDATE_PROTOCOL.md)
- [Batch-Rendering](./docs/BATCH_RENDERING_PROTOCOL.md)
- [Metrik für gerenderte Übergänge](./docs/RENDERED_TRANSITION_METRIC_PROTOCOL.md)
- [Batch anhören (Notebook)](./notebooks/listen_batch.ipynb)
- [Laufende Bemerkungen](./docs/Bemerkungen.md)

## Entwicklungsumgebung

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-cuda.txt
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

`requirements-cuda.txt` installiert unter Windows den CUDA-13.0-Build von
PyTorch. Training und neue BS-RoFormer-Separationen wählen standardmäßig
`cuda:0`, wenn CUDA verfügbar ist, und fallen sonst auf CPU zurück. Für einen
bewussten CPU-Lauf kann bei den Trainingsbefehlen `--device cpu` angegeben
werden.

Die programmatischen Verträge für Rendering, Kandidaten, Batch-Exporte und die
Metrik für gerenderte Varianten stehen unter [`docs/`](./docs/README.md).

## Projektstand

Die technische Basis ist vorhanden: Beat-/Bar-Analyse, Audio-Normalisierung,
vier Übergangs-Renderer, automatische bar-synchrone Kandidaten, Cutpoint- und
Render-Ranking, Batch-Export sowie blinde Hörstudien. Das Vocal-v2-Training und
mehrere Objective-/Control-Hörsätze sind abgeschlossen; der aktuelle
Vocal-v2-Modellhörsatz ist jedoch noch unbewertet (0/5 Ratings, noch keine
`study_results.json`).

Der nächste Arbeitsblock ist deshalb die geblendete Bewertung dieses
Vocal-v2-Satzes, ergänzt um die isolierte Time-Stretch-/Target-Fenster-Diagnose
und die weitere Kuratierung des Entwicklungssets. Der verbindliche,
priorisierte Arbeitsstand wird ausschließlich in
[`docs/STATUS.md`](./docs/STATUS.md) gepflegt.
