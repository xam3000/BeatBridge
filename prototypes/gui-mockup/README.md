# BeatBridge GUI-Mockup

Dieser Ordner enthält das frühere interaktive GUI-Mockup auf Basis von
[`../../docs/GUI_SPECIFICATION.md`](../../docs/GUI_SPECIFICATION.md). Es bleibt
als visuelle Referenz erhalten. Die native Python-Desktop-App wird aus dem
Repository-Root gestartet und nutzt jetzt den manuellen Mehrtrack-
Transition-Builder.

## Native Desktop-App

Einmalig die optionale PySide6-Abhängigkeit installieren und die App aus dem
Repository-Root starten. Optional kann ein Batchmanifest als Startargument
übergeben werden:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.venv\Scripts\python.exe -m src.gui_app
```

Die Oberfläche wird mit Qt Widgets nativ aus Python aufgebaut und orientiert
sich an der Mockup-Hierarchie: Bibliothek links, App-Leiste/Transport oben,
Songsequenz darunter, cyanfarbene A- und korallfarbene B-Wellenformspuren,
Übergangs-Inspector rechts und Vorschau/Bewertung unten. Lade mehrere
Audiodateien, füge sie der Sequenz hinzu und wähle eine Kante A→B, B→C usw.
Cuepoints lassen sich per Wellenformklick oder Zeitfeld einstellen. Für jede
Kante sind Cuepoints, Länge, Renderer/Modellwahl und Ergebnis getrennt.
Audiodateien können aus dem Windows-Explorer auf die Sequenz, die Bibliothek
oder andere freie Bereiche des App-Fensters gezogen werden. Bibliothekstracks
lassen sich in die Sequenz ziehen; Sequenzeinträge können intern umsortiert
werden.
Beim Import wird der Analyse-Cache im Hintergrund geprüft: gültige Treffer
werden geladen, Cache-Misses als „Nicht analysiert“ angezeigt. Die Wellenform
lässt sich mit dem Mausrad zoomen, mit Shift+Mausrad oder mittlerer Maustaste
verschieben und per Doppelklick auf die Gesamtansicht zurücksetzen.
Die Bedienhinweise stehen oberhalb der Waveform und verdecken das Signal
nicht. Analyse-Cache-Pfad ist auswählbar; Treffer werden beim Analysieren gemeldet.
Abgeschlossene unterstützte lokale ML-Runs können für vier Takte ausgewählt
werden. Render und JSON-Provenienz landen neu unter `output/gui_transitions/`;
Quelldateien werden nicht verändert. Die angezeigte Bewertung ist eine
technische Render-Metrik, keine Modell- oder Hörqualitätsgarantie.

Der fruehere manifestbasierte Varianten-Review ist weiterhin verfuegbar:

```powershell
.venv\Scripts\python.exe -m src.gui_app --review-manifest
.venv\Scripts\python.exe -m src.gui_app output\batches\help_to_breath_ranked\manifest.json
```

Die Anwendung ist in der Entwicklungsphase; der manuelle Durchklick und die
Laufzeitverifikation stehen noch aus.

## Mockup im Browser öffnen

`index.html` kann weiterhin direkt im Browser geöffnet werden. Alternativ
kann aus dem Repository ein lokaler statischer Server gestartet werden:

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
