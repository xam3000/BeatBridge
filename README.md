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
PyTorch. Training und neue Demucs-Separationen wählen standardmäßig
`cuda:0`, wenn CUDA verfügbar ist, und fallen sonst auf CPU zurück. Für einen
bewussten CPU-Lauf kann bei den Trainingsbefehlen `--device cpu` angegeben
werden.

Die programmatischen Verträge für Rendering, Kandidaten, Batch-Exporte und die
Metrik für gerenderte Varianten stehen unter [`docs/`](./docs/README.md).

## Projektstand

Die technische Basis ist vorhanden: Beat-/Bar-Analyse, Audio-Normalisierung,
vier Übergangs-Renderer, automatische bar-synchrone Kandidaten, Cutpoint-Ranking,
eine Baseline-Metrik für gerenderte Varianten, Batch-Export und ein
Notebook-Hörvergleich.

Der nächste Meilenstein ist die Validierung der beiden Rankings gegen
menschliche Hörurteile. Der verbindliche, priorisierte Arbeitsstand wird
ausschließlich in [`docs/STATUS.md`](./docs/STATUS.md) gepflegt, damit keine
parallelen Aktionspläne auseinanderlaufen.
