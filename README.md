# BeatBridge

## Dokumentation

Der aktuelle, verifizierte Projektstand und die weitere Dokumentation liegen unter [`docs/`](./docs/README.md).

- [Status und nächste Schritte](./docs/STATUS.md)
- [Projekt-Gesamtübersicht und Forschungsrahmen](./docs/Projekt-Gesamtuebersicht.md)
- [CLI verwenden](./docs/CLI.md)
- [Laufende Bemerkungen](./docs/Bemerkungen.md)

## Entwicklungsumgebung

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Der programmatische Rendering-Vertrag ist in [`docs/RENDERING_PROTOCOL.md`](./docs/RENDERING_PROTOCOL.md) beschrieben.

## Projektstand

Die technische Rendering-Basis ist vorhanden: Beat-/Bar-Analyse, Audio-Normalisierung, vier Übergangs-Renderer, CLI und automatisierte Tests. Übergangspunkte müssen noch manuell angegeben werden; automatische Kandidaten, Ranking und Hörvergleich fehlen.

Der nächste Meilenstein ist die Schleife **Kandidaten erzeugen → Varianten batchweise rendern → anhören und vergleichen**. Der verbindliche, priorisierte Arbeitsstand wird ausschließlich in [`docs/STATUS.md`](./docs/STATUS.md) gepflegt, damit keine parallelen Aktionspläne auseinanderlaufen.
