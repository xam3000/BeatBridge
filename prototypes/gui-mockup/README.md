# BeatBridge GUI-Mockup

Dieser Ordner enthält einen eigenständigen interaktiven Browser-Prototypen auf
Basis von [`../../docs/GUI_SPECIFICATION.md`](../../docs/GUI_SPECIFICATION.md).
Er ist absichtlich nicht mit der produktiven BeatBridge-Pipeline verbunden.

## Start

`index.html` kann direkt im Browser geöffnet werden. Alternativ kann aus dem
Repository ein lokaler statischer Server gestartet werden:

```powershell
.venv\Scripts\python.exe -m http.server 8765 --directory prototypes\gui-mockup
```

Danach ist der Prototyp unter `http://localhost:8765/` erreichbar.

## Dateigrenzen

- `index.html`: semantische Anwendungsstruktur und statische UI-Elemente
- `styles.css`: eigenständiges dunkles BeatBridge-Designsystem und Layout
- `mock-data.js`: isolierte Projekt-, Track-, Abschnitts-, Kanten- und
  Variantendaten
- `app.js`: View-State, Rendering und lokale Interaktionen

Die spätere Integration soll `mock-data.js` durch einen Adapter auf die
versionierten BeatBridge-Manifeste und Backend-Fähigkeiten ersetzen. Der
Paar-Editor selbst arbeitet weiterhin mit genau einer `TransitionEdgeView` und
den beiden zugehörigen `SectionView`-Objekten.

## Demonstrierte Interaktionen

- zwischen gerichteten Paarübergängen der Mehrtrack-Sequenz wechseln,
- weitere gemockte Trackabschnitte zur Sequenz hinzufügen,
- Sequenzabschnitte umordnen und dadurch veraltete Kanten sichtbar machen,
- simulierte Wiedergabe, Loop, Playhead und synchronisierte Analyseanzeige,
- Übergangslänge, Zieltempo, Renderer und Präferenzen pro Kante ändern,
- Baseline-/Modellscore umschalten,
- Varianten anhören, auswählen und an einer Sequenzkante übernehmen,
- Export-Preflight über alle `N - 1` Paarübergänge auslösen.

Der Prototyp erzeugt weder Audio noch Projektdateien. Alle angezeigten
Messwerte, Zeitreihen und Provenienzangaben sind klar gekennzeichnete Mock-Daten.
