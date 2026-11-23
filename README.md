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

Für einen frischen Checkout unter Windows mit Python 3.14:

```powershell
py -3.14 -m venv .venv
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

BeatBridge wählt Cuepoints, rendert Übergänge und exportiert ausgewählte Songabschnitte als zusammenhängende WAV. Ein geprüftes Beispiel verbindet drei Trainingsaufnahmen mit einem Zwei- und einem Drei-Takt-Übergang. Für den geschlossenen Hörversuch sind sieben Songpaare vorgesehen. Den Stand der MERT-Auswahl, der Tempo-Prüfung und der Erhebung führt das Projekt im [Status](docs/STATUS.md). [Bedienung und Entwicklungs-Mashup](docs/masterarbeit/review_jp_20261118/p14/mashup.md)
