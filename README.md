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

Actionplan 2–3 Wochen

* Gucken was geht
* Einfach, lauffähige Audio-Pipeline
    * Songs laden,
    * Tempo, Beats und Takte analysieren,
    * Songabschnitte taktsynchron verbinden,
    * einfache Übergänge rendern,
    * erste Ergebnisse anhören und typische Fehler identifizieren.

## 1. Scope und Erfolgskriterien festlegen

* Was machen was funktioniert:
    * mehrere Songs importieren,
    * Abschnitte manuell oder halbautomatisch auswählen,
    * Beat- und Bar-Analyse durchführen,
    * Übergänge von 1, 2 und 4 Takten erzeugen,
    * Hard Cuts, Crossfades und einfache tempoangepasste Übergänge vergleichen,
    * Ergebnis als Audiodatei exportieren.
* Gucken welche User-Constraints Sinn machen
    * Übergangslänge,
    * Zieltempo,
    * Takt-/Bar-Alignment,
    * Übergangstyp,
    * optional Vermeidung starker Vocal-Überlagerungen.
## 2. Technische Basis aufbauen
* Git-Repo
* MD-Files für wo sind wir und was sind die Next Steps
    * Vielleicht noch Trello Board oder sowas für Task-Übersicht
* Eine einfache Projektstruktur für Audioanalyse, Übergangsgenerierung, Metriken und Evaluation anlegen.
* Kommandozeilen-Tool, GUI später.
* Erste Funktionen:
    * Audio laden,
    * Audio exportieren,
    * Beats/BPM analysieren,
    * einfache Übergänge rendern.
## 3. Dataset für Tests
* Erstemal mit ein paar Testsongs starten.
* Zu jedem Track kurze Notizen aufschreiben:
    * geschätztes Tempo,
    * Qualität der Beat-Erkennung,
    * Vocals,
    * mögliche Abschnitte,
    * auffällige Probleme.
## 4. Beattracking
* Hast du noch Auftakt rumfliegen?
* visualisieren
    * IWaveform oder Spektrogramm,
    * (Down)Beats,
    * mögliche Übergangsfenster.
* Typische Fehler sammeln
    * falsches Tempo,
    * verschobener Downbeat,
    * Komische Beats in Breaks,
    * Komische Taktgrenzen,
    * Probleme bei Intros oder Tempoänderungen.
## 5. Erste Test-Übergangskandidaten erzeugen
* Übergänge zunächst nur an musikalisch plausiblen Positionen erlauben.
* Kandidatenpunkte aus Bar- und Phrasengrenzen ableiten.
* Übergangslängen auf 1, 2 und 4 Takte begrenzen.
* Einfache Filter definieren:
    * keine Übergänge außerhalb des Beat-Grids,
    * keine zu großen Tempoabweichungen,
    * keine offensichtlich instabilen Analysebereiche,
    * optional keine starken Vocal-Überlagerungen.
## 6. Baseline-Renderer implementieren
* Mehrere einfache Übergangsstrategien umsetzen:
    * harter Schnitt auf Bar-Grenze,
    * linearer Crossfade, Equal-Power-Crossfade,
    * einfacher tempoangepasster Crossfade.
* Für mehrere Songpaare und Übergangslängen Audio-Beispiele exportieren.
* Erste Höranalyse durchführen und typische Qualitätsprobleme sammeln:
    * rhythmisch unsauber,
    * harmonisch schief,
    * Energie bricht ab,
    * Vocals kollidieren,
    * Crossfade klingt matschig,
    * Timestretching erzeugt Mist.
## 7. Erste Feature-basierte Übergangsmetrik angucken
* zB
    * BPM-Differenz,
    * Beat-/Bar-Alignment,
    * Chroma-Ähnlichkeit,
    * Energie-/Loudness-Verlauf,
    * spektrale Ähnlichkeit,
    * Vocal-Overlap-Penalty,
    * Time-Stretching-Penalty.
* Diese Metrik verwenden, um Übergangskandidaten zu ranken.
* Gucken, ob die besten Kandidaten auch beim Anhören gut wirken.
