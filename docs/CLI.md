# CLI verwenden

Die BeatBridge-CLI erzeugt einen taktgenauen Übergang zwischen zwei Audiodateien. Die Übergangspunkte werden aktuell noch manuell als Sample-Positionen angegeben und anschließend auf den nächstgelegenen erkannten Downbeat ausgerichtet.

## Voraussetzungen

Alle Befehle werden in PowerShell aus dem Projektordner `BeatBridge` ausgeführt.

1. Python-Abhängigkeiten in der vorhandenen virtuellen Umgebung installieren:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. `aufTAKTCl.exe` muss im Projekt-Root liegen. Das ist im aktuellen Repository bereits der Fall.
3. Für MP3-, FLAC- und andere Nicht-WAV-Eingaben muss `ffmpeg` über `PATH` aufrufbar sein:

   ```powershell
   ffmpeg -version
   ```

4. CLI-Hilfe anzeigen:

   ```powershell
   .venv\Scripts\python.exe src\pipeline.py --help
   ```

## Aufruf

```text
pipeline.py SONG1 SONG2 CUTPOINT1 CUTPOINT2 RENDERER [OPTIONEN]
```

| Argument | Bedeutung |
|---|---|
| `SONG1` | Erster Song; der Teil vor dem Übergang bleibt erhalten |
| `SONG2` | Zweiter Song; der Teil nach dem Übergang bleibt erhalten |
| `CUTPOINT1` | Ungefährer Übergangspunkt in Song 1, angegeben in Samples auf dem Ziel-Sample-Raster |
| `CUTPOINT2` | Ungefährer Übergangspunkt in Song 2, angegeben in Samples auf dem Ziel-Sample-Raster |
| `RENDERER` | `simple`, `fade`, `equal_power` oder `tempo_fade` |

Die wichtigsten Optionen:

| Option | Standard | Bedeutung |
|---|---:|---|
| `--fade-beats N` | `8` | Länge eines Crossfades in Beats; der Fade endet aktuell am Cutpoint |
| `--target-sample-rate HZ` | `44100` | Internes Sample-Raster und Sample-Rate der Ausgabe |
| `-o DATEI`, `--output DATEI` | `output/cut_song.wav` | Zielpfad der gerenderten WAV-Datei |

## Cutpoints berechnen

Cutpoints werden derzeit nicht in Sekunden, sondern in Samples angegeben:

```text
cutpoint = zeit_in_sekunden × target_sample_rate
```

Beim Standardwert von 44.100 Hz gilt beispielsweise:

| Zeit | Cutpoint |
|---:|---:|
| 30 Sekunden | `1323000` |
| 60 Sekunden | `2646000` |
| 90 Sekunden | `3969000` |

Die Werte müssen nicht exakt auf einem Beat liegen. BeatBridge sucht den Downbeat mit dem geringsten Sample-Abstand; dieser kann vor oder nach dem angegebenen Cutpoint liegen. Auch bei einer 48-kHz-Eingangsdatei beziehen sich Cutpoints standardmäßig auf das normalisierte 44,1-kHz-Raster. Wird `--target-sample-rate 48000` verwendet, muss entsprechend mit 48.000 multipliziert werden.

## Renderer

### Hard Cut

`simple` schneidet Song 1 am ausgerichteten Downbeat ab und setzt Song 2 an seinem ausgerichteten Downbeat fort.

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 simple -o "output\help_to_breath_simple.wav"
```

### Linearer Crossfade

`fade` blendet Song 1 linear aus und Song 2 linear ein. Der folgende Aufruf verwendet acht Beats:

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 fade --fade-beats 8 -o "output\help_to_breath_linear.wav"
```

### Equal-Power-Crossfade

`equal_power` verwendet Sinus-/Cosinus-Hüllkurven. Dadurch bleibt die kombinierte quadratische Verstärkung über den Fade konstant.

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 equal_power --fade-beats 8 -o "output\help_to_breath_equal_power.wav"
```

### Tempoangepasster Crossfade

`tempo_fade` passt Song 2 zunächst tonhöhenerhaltend an das BPM von Song 1 an und rendert danach einen linearen Crossfade. Die Berechnung dauert länger als bei den anderen Renderern.

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 tempo_fade --fade-beats 8 -o "output\help_to_breath_tempo.wav"
```

## Analyse-Cache und Ausgaben

Beim ersten Lauf analysiert BeatBridge BPM, Beats und Taktpositionen. Ergebnisse werden anhand des Datei-Hashes zwischengespeichert:

```text
output/pre_analysis/05 - HELP_LESS/00_pre_analysis.txt
output/pre_analysis/05 - HELP_LESS/01_missing_beats.txt
```

- `00_pre_analysis.txt` enthält Datei-Hash, BPM und Beat-/Taktpositionen.
- `01_missing_beats.txt` dokumentiert Abweichungen zwischen librosa und aufTAKT.
- Wird die Quelldatei verändert, passt der gespeicherte Hash nicht mehr und die Analyse wird neu ausgeführt.
- Audiodateien im Ordner `musik/` werden ausschließlich gelesen und nicht verändert.

## Häufige Fehler

### `ffmpeg` wurde nicht gefunden

Nicht-WAV-Dateien werden für aufTAKT temporär nach WAV konvertiert. Prüfen, ob `ffmpeg -version` in derselben PowerShell funktioniert.

### Downbeat-Metadaten fehlen

BeatBridge bricht mit `Downbeat snapping requires beat frames with count_in_bar metadata` ab, wenn keine Taktinformationen verfügbar sind. In diesem Fall zuerst die aufTAKT-/ffmpeg-Ausführung prüfen. Es gibt bewusst keinen stillen Fallback auf beliebige Beats.

### Ausgabedatei klingt zu früh oder zu spät geschnitten

Die angegebenen Cutpoints sind nur Ausgangspunkte für die Suche nach dem nächsten Downbeat. Prüfen, ob der berechnete Sample-Wert zur gewünschten Zeit und zur gewählten `--target-sample-rate` gehört. Abweichende librosa-/aufTAKT-Raster werden unter `output/pre_analysis/` protokolliert.

### Übergänge automatisch auswählen

Das unterstützt die CLI noch nicht. Automatische Kandidatengenerierung aus Takt- und Phrasengrenzen ist der nächste geplante Entwicklungsschritt. Aktuell müssen beide Cutpoints angegeben werden.

## Tests ausführen

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Der programmatische Python-Vertrag hinter der CLI steht in [`RENDERING_PROTOCOL.md`](./RENDERING_PROTOCOL.md).
