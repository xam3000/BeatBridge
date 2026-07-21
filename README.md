# BeatBridge

## Dokumentation

Der aktuelle, verifizierte Projektstand und die weitere Dokumentation liegen unter [`docs/`](./docs/README.md).

- [Status und nächste Schritte](./docs/STATUS.md)
- [Projekt-Gesamtübersicht und Forschungsrahmen](./docs/Projekt-Gesamtuebersicht.md)
- [CLI verwenden](./docs/CLI.md)
- [Kandidatenvertrag](./docs/CANDIDATE_PROTOCOL.md)
- [Batch-Rendering](./docs/BATCH_RENDERING_PROTOCOL.md)
- [Laufende Bemerkungen](./docs/Bemerkungen.md)

## Entwicklungsumgebung

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Die programmatischen Verträge für Rendering, Kandidaten und Batch-Exporte stehen in [`docs/RENDERING_PROTOCOL.md`](./docs/RENDERING_PROTOCOL.md), [`docs/CANDIDATE_PROTOCOL.md`](./docs/CANDIDATE_PROTOCOL.md) und [`docs/BATCH_RENDERING_PROTOCOL.md`](./docs/BATCH_RENDERING_PROTOCOL.md).

## Projektstand

Die technische Basis ist vorhanden: Beat-/Bar-Analyse, Audio-Normalisierung, vier Übergangs-Renderer, automatische bar-synchrone Kandidaten und Batch-Export mit auditierbarem JSON-Manifest. Ranking und eine Hörvergleichsoberfläche fehlen noch.

Der nächste Meilenstein ist die Schleife **Kandidaten erzeugen → Varianten batchweise rendern → anhören und vergleichen**. Der verbindliche, priorisierte Arbeitsstand wird ausschließlich in [`docs/STATUS.md`](./docs/STATUS.md) gepflegt, damit keine parallelen Aktionspläne auseinanderlaufen.
