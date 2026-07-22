# CLI verwenden

`src/pipeline.py` erzeugt einen einzelnen taktgenauen Übergang zwischen zwei Audiodateien. Die Übergangspunkte werden dabei manuell als Sample-Positionen angegeben und anschließend auf den nächstgelegenen erkannten Downbeat ausgerichtet. Für automatische Kandidaten und den systematischen Export mehrerer Varianten steht zusätzlich `src/batch_render.py` bereit.

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
| `CUTPOINT1` | Ende von Drop A / Beginn des Source-Auslaufs, angegeben in Samples auf dem Ziel-Sample-Raster |
| `CUTPOINT2` | Ende des Target-Vorlaufs / Beginn von Drop B, angegeben in Samples auf dem Ziel-Sample-Raster |
| `RENDERER` | `simple`, `fade`, `equal_power` oder `tempo_fade` |

Die wichtigsten Optionen:

| Option | Standard | Bedeutung |
|---|---:|---|
| `--fade-beats N` | `8` | Länge der Bridge in Beats zwischen Source- und Target-Cutpoint |
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

`fade` erhält Drop A bis `CUTPOINT1`, blendet danach den Source-Auslauf mit dem Target-Vorlauf vor `CUTPOINT2` und startet dort Drop B. Der folgende Aufruf verwendet acht Beats:

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 fade --fade-beats 8 -o "output\help_to_breath_linear.wav"
```

### Equal-Power-Crossfade

`equal_power` verwendet dieselbe Drop-Bridge mit Sinus-/Cosinus-Hüllkurven. Dadurch bleibt die kombinierte quadratische Verstärkung über den Fade konstant.

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 equal_power --fade-beats 8 -o "output\help_to_breath_equal_power.wav"
```

### Tempoangleichung

Alle Renderer passen Song 2 zunächst tonhöhenerhaltend an das BPM von Song 1 an. `tempo_fade` bleibt aus Kompatibilitätsgründen verfügbar, entspricht aber dem linearen `fade`-Renderer.

```powershell
.venv\Scripts\python.exe src\pipeline.py "musik\05 - HELP_LESS.flac" "musik\07 - BREATH_LESS.flac" 2646000 1323000 tempo_fade --fade-beats 8 -o "output\help_to_breath_tempo.wav"
```

## Automatische Kandidaten als Batch rendern

Der Batch-Befehl erzeugt zuerst taktbasierte Kandidaten und exportiert danach jede akzeptierte Kombination aus Kandidat und Renderer. Cutpoints müssen dabei **nicht** manuell angegeben werden.

```powershell
.venv\Scripts\python.exe -m src.batch_render `
  "musik\05 - HELP_LESS.flac" `
  "musik\07 - BREATH_LESS.flac" `
  --output-dir "output\batches\help_to_breath"
```

Standardmäßig durchsucht BeatBridge alle nutzbaren Source- und Target-Grenzen und erzeugt Bridges mit 2 oder 4 Takten. `feature_baseline_v3` bevorzugt ein natürliches Drop-Ende in A, energiearme Übergangsfenster und einen Drop-Anfang in B. Wegen des größeren Suchraums werden standardmäßig nur die fünf bestbewerteten Kandidaten mit den gewählten Renderern exportiert. Der Zielordner enthält WAV-Dateien unter `rendered\` und ein `manifest.json` mit allen Kandidaten, Scores und Messwerten.

Jede WAV ist standardmäßig eine kurze Vorschau: fünf Sekunden vor und zwölf Sekunden nach dem Source-Cutpoint. `--preview-before-seconds` und `--preview-after-seconds` passen den Kontext an.

Ein kleinerer, schnellerer Vergleichslauf mit nur Equal-Power-Fades und zwei Taktlängen:

```powershell
.venv\Scripts\python.exe -m src.batch_render `
  "musik\05 - HELP_LESS.flac" `
  "musik\07 - BREATH_LESS.flac" `
  --output-dir "output\batches\help_to_breath_equal_power" `
  --renderers equal_power `
  --transition-bars 2 4 `
  --top-k 5
```

Wichtige Batch-Optionen:

| Option | Standard | Bedeutung |
|---|---:|---|
| `--output-dir ORDNER` | – | Erforderlicher Zielordner für Manifest und WAV-Dateien |
| `--renderers ...` | alle vier Baselines | Eine oder mehrere Renderer-Varianten |
| `--transition-bars ...` | `2 4` | Kandidatenlängen in Takten |
| `--source-boundaries N` | alle | Optionales Limit auf die letzten N nutzbaren Source-Grenzen |
| `--target-boundaries N` | alle | Optionales Limit auf die ersten N nutzbaren Zielgrenzen; ohne Option wird der ganze Song B durchsucht |
| `--max-tempo-difference X` | `0.15` | Maximale symmetrische relative BPM-Differenz (`0.15` = 15 %) |
| `--top-k N` | `5` | Rendert nur die N bestbewerteten Kandidaten; alle Scores bleiben im Manifest |
| `--overwrite` | aus | Erlaubt ausschließlich auf expliziten Wunsch das Ersetzen gleichnamiger Exportdateien |

Ein vorhandener Export wird standardmäßig nicht überschrieben. Für einen weiteren Versuch deshalb einen neuen Ordner wählen; `--overwrite` nur bewusst einsetzen. Der ausführliche Exportvertrag steht in [`BATCH_RENDERING_PROTOCOL.md`](./BATCH_RENDERING_PROTOCOL.md).

## Batch im Notebook anhören

[`notebooks/listen_batch.ipynb`](../notebooks/listen_batch.ipynb) lädt ein Batch-Manifest, sortiert die Varianten nach Feature-Rang und zeigt für jede gewählte WAV-Datei einen eingebetteten Audio-Player. `rate(index, 1_bis_5, issues=(...), notes="...")` speichert Bewertungen atomar als `ratings.json` im Batch-Ordner; `show_ratings()` zeigt den aktuellen Stand. Das Notebook startet mit dem ersten realen Lauf `output/batches/help_to_breath_first`. Für einen anderen Lauf in der ersten Codezelle nur `BATCH_DIR` ändern und die Zellen von oben nach unten ausführen.

Alternativ lässt sich eine Bewertung über `python -m src.evaluation.ratings` speichern. Das vollständige Format und ein Beispiel stehen in [`RATINGS_PROTOCOL.md`](./RATINGS_PROTOCOL.md); Score-Komponenten und Grenzen der Baseline beschreibt [`RANKING_PROTOCOL.md`](./RANKING_PROTOCOL.md).

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

### Der Batch erzeugt keine WAV-Dateien

Prüfen Sie zuerst `manifest.json` im angegebenen Zielordner. Unter `candidate_generation.rejections` steht, welcher harte Filter die Kandidaten verhindert hat, etwa fehlende Downbeat-Metadaten, zu wenig Pre-Roll oder eine zu große BPM-Differenz. Der Befehl beendet sich in diesem Fall mit Exit-Code `2` und erzeugt bewusst keine stillen Ersatz-Cutpoints.

## Tests ausführen

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Der programmatische Python-Vertrag hinter der CLI steht in [`RENDERING_PROTOCOL.md`](./RENDERING_PROTOCOL.md).
