# CLI verwenden

`src/pipeline.py` erzeugt einen einzelnen taktgenauen Übergang zwischen zwei Audiodateien. Die Übergangspunkte werden dabei manuell als Sample-Positionen angegeben und anschließend auf den nächstgelegenen erkannten Downbeat ausgerichtet. Für automatische Kandidaten und den systematischen Export mehrerer Varianten steht zusätzlich `src/batch_render.py` bereit.

## Voraussetzungen

Alle Befehle werden in PowerShell aus dem Projektordner `BeatBridge` ausgeführt.

1. Python-Abhängigkeiten in der vorhandenen virtuellen Umgebung installieren:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. `aufTAKTCl.exe` muss im Projekt-Root liegen. Die aktuell eingecheckte Datei
   ist technisch per SHA-256 identifiziert; ihre konkrete Version, Herkunft
   und Weitergabeberechtigung sind jedoch nicht belegt. Vor Distribution die
   Hinweise in [`EXTERNAL_TOOLS.md`](./EXTERNAL_TOOLS.md) beachten.
3. Für Tempoanpassung sowie MP3-, FLAC- und andere Nicht-WAV-Eingaben muss
   `ffmpeg` über `PATH` aufrufbar und mit `librubberband` kompiliert sein:

   ```powershell
   ffmpeg -version
   ffmpeg -hide_banner -filters | Select-String rubberband
   ```

   Die zweite Ausgabe muss den Audiofilter `rubberband` enthalten.

4. Optional kann zusätzlich das eigenständige Rubber-Band-CLI installiert
   werden. BeatBridge nutzt es automatisch als Fallback, wenn FFmpeg fehlt,
   den Filter nicht enthält oder die Verarbeitung fehlschlägt:

   ```powershell
   rubberband --version
   ```

   Wenn der FFmpeg-Filter funktioniert, ist das separate CLI nicht erforderlich.

5. CLI-Hilfe anzeigen:

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

Alle Renderer passen Song 2 zunächst tonhöhenerhaltend an das BPM von Song 1
an. BeatBridge verwendet dafür zuerst FFmpegs `rubberband`-Filter mit gemeinsam
verarbeitetem Stereo (`channels=together`). Falls dieser Schritt nicht
verfügbar ist oder fehlschlägt, wird automatisch das eigenständige
`rubberband`-CLI mit R3-Engine (`-3`) verwendet. Temporäre Backend-WAVs sind
32-Bit-Float, damit die Tempoanpassung keine zusätzliche PCM16-Quantisierung
verursacht.

Im Batch-Manifest zeigt `rendered_variants[].tempo_backend` den tatsächlich
verwendeten Pfad:

- `ffmpeg_librubberband`
- `rubberband_cli_r3`
- `not_needed` bei praktisch identischem Tempo

Schlagen beide Rubber-Band-Wege fehl, bricht die jeweilige Variante mit einer
Fehlermeldung ab, die beide Ursachen enthält. Es gibt bewusst keinen stillen
Fallback auf den früheren Librosa-Phase-Vocoder. `tempo_fade` bleibt aus
Kompatibilitätsgründen verfügbar, entspricht aber dem linearen
`fade`-Renderer.

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

Standardmäßig durchsucht BeatBridge alle nutzbaren Source- und Target-Grenzen
und erzeugt Bridges mit 2 oder 4 Takten. `feature_baseline_v3` wählt vor dem
Rendering vielversprechende Cutpoints aus. Wegen des größeren Suchraums werden
standardmäßig nur die fünf bestbewerteten Kandidaten mit den gewählten
Renderern exportiert. Anschließend bewertet
`rendered_transition_baseline_v1` jede tatsächlich gerenderte Variante. Das
Manifest enthält deshalb sowohl `candidate_rank`/`candidate_score` als auch
`transition_rank`/`transition_score`; die vollständigen Teilwerte stehen unter
`rendered_transition_ranking`.

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

[`notebooks/listen_batch.ipynb`](../notebooks/listen_batch.ipynb) lädt ein
Batch-Manifest, sortiert neue Batches nach Render-Rang und zeigt Render- sowie
Cutpoint-Score nebeneinander. Bei älteren Manifesten ohne Render-Metrik fällt
es auf den Cutpoint-Rang zurück. Eine Batch-Übersicht visualisiert die
Render-Score-Verteilung und den Vergleich von Cutpoint- zu Render-Score; bei
einem Paar aus einem nachbewerteten Multi-Song-Batch bezieht sie alle dortigen
Varianten ein und hebt das aktuelle Paar hervor. Für
jede gewählte WAV-Datei richtet `play(index)` außerdem die Source- und
Target-Waveform an ihren jeweiligen Cue Points bei `t = 0` aus und zeigt sie
untereinander. Das Zeitfenster kann separat mit
`plot_cue_points(index, seconds_before=..., seconds_after=...)` angepasst
werden. Anschließend erscheinen die vier Metrikkomponenten samt Gesamtscore
direkt vor dem eingebetteten Audio-Player.
`rate(index, 1_bis_5, issues=(...), notes="...")`
speichert Bewertungen atomar als `ratings.json` im Batch-Ordner;
`show_ratings()` zeigt den aktuellen Stand. Für einen anderen Lauf in der
ersten Codezelle nur `BATCH_DIR` ändern und die Zellen von oben nach unten
ausführen.

Alternativ lässt sich eine Bewertung über `python -m src.evaluation.ratings`
speichern. Das vollständige Format und ein Beispiel stehen in
[`RATINGS_PROTOCOL.md`](./RATINGS_PROTOCOL.md). Die Vorab-Auswahl beschreibt
[`RANKING_PROTOCOL.md`](./RANKING_PROTOCOL.md); Komponenten und Grenzen der
Metrik für fertige WAV-Varianten stehen in
[`RENDERED_TRANSITION_METRIC_PROTOCOL.md`](./RENDERED_TRANSITION_METRIC_PROTOCOL.md).

## Multi-Song-Batch

`src.multi_batch_render` behandelt jeden angegebenen Track als Quelle, wählt
pro Quelle die besten Zieltracks und exportiert pro ausgewähltem Paar die
besten Übergänge. Standardmäßig sind das drei Zieltracks, drei Kandidaten je
Songpaar und der `equal_power`-Renderer. Das Wurzel-Manifest verweist auf die
regulären Paar-Manifeste und dokumentiert die vollständige Songauswahl.

```powershell
.venv\Scripts\python.exe -m src.multi_batch_render `
  musik\*.flac `
  --output-dir "output\batches\all_songs_top3_targets_top3_transitions_20260722"
```

Ein Verzeichnisargument wird rekursiv nach `.flac`, `.mp3`, `.ogg` und
`.wav` durchsucht. Exakte Audio-Duplikate werden per SHA-256 nur einmal
verwendet. Ein inklusiver BPM-Bereich kann bereits vor Songranking und
Kandidatengenerierung erzwungen werden:

```powershell
.venv\Scripts\python.exe -m src.multi_batch_render `
  musik `
  --output-dir output\batches\all_music_recursive_bpm145_165_top1_20260805 `
  --top-targets 1 `
  --top-transitions 1 `
  --renderers equal_power `
  --min-bpm 145 `
  --max-bpm 165 `
  --analysis-workers 4
```

Das Root-Manifest dokumentiert Policy-Ausschlüsse, Audio-Duplikate,
BPM-Ausschlüsse, Analysefehler und die Workerzahl getrennt. Die Worker teilen
keine temporären aufTAKT-Dateien.

Das Wurzel-Manifest wird nach jedem Songpaar atomar aktualisiert. Bereits
abgeschlossene Paare bleiben bei einer Unterbrechung nachvollziehbar.
Unabhängige Sources und Paare werden bei Einzelfehlern weiterverarbeitet.
Nach dem finalen Manifest endet die CLI jedoch mit Exit-Code `1`, wenn dort
BPM-Analyse-, Source-, Paar-, Render- oder Render-Metrikfehler dokumentiert
sind. Exit-Code `0` bedeutet einen Lauf ohne aufgezeichnete Fehler;
Policy-/BPM-Ausschlüsse und erkannte Audio-Duplikate sind reguläre Ergebnisse.

### Vorhandenen Multi-Song-Batch nachbewerten

Ein älterer Batch kann mit der Render-Metrik bewertet werden, ohne WAVs oder
historische Manifeste zu verändern:

```powershell
.venv\Scripts\python.exe -m src.evaluation.backfill_transition_metrics `
  "output\batches\all_songs_top3_targets_top3_transitions_20260722"
```

Je Paar und im Wurzelordner entsteht ein separates
`transition_metrics.json`. Das Notebook erkennt diese Sidecars automatisch.

## Differenzierbare Controls auf realen Batch-Beispielen vergleichen

Der folgende Befehl wählt vier unterschiedliche 4-Takt-Paare mit hohen
Render-Scores aus dem Multi-Song-Batch vom 22.07 aus und exportiert pro Paar
eine feste Equal-Power- sowie eine direkt optimierte Variante:

```powershell
.venv\Scripts\python.exe -m src.evaluation.control_probe `
  output\batches\all_songs_top3_targets_top3_transitions_20260722 `
  output\control_comparisons\batch_20260722_top4_4bar_v2_monotone `
  --pair-count 4 `
  --transition-bars 4 `
  --optimization-steps 60
```

Der Zielordner muss neu sein. Bestehende Batch-WAVs und Manifeste werden nur
gelesen. Jeder Paarordner enthält:

```text
01_baseline_equal_power.wav
02_optimized_proxy.wav
```

`manifest.json` dokumentiert Auswahl, Cutpoints, Controls, Proxy-Loss,
historische Render-Metrik und technische WAV-Daten. Beide WAVs eines Paars
haben identischen Kontext und verwenden dieselbe Peak-Absenkung.

Tracks aus `config/track_exclusions.json` werden bei neuen Control-Vergleichen
und Multi-Song-Batches standardmäßig übersprungen und im neuen Batch-Manifest
als Ausschluss dokumentiert. Aktuell betrifft das `14 - STRUGGLING.flac`,
dessen Tempo im realen Hörvergleich nicht zum übrigen Vergleichsset passte.
Historische Batches werden dadurch nicht verändert.

## Blinden A/B-Hörsatz erzeugen und bewerten

```powershell
.venv\Scripts\python.exe -m src.evaluation.blind_control_study `
  output\batches\all_songs_top3_targets_top3_transitions_20260722 `
  output\control_studies\blind_v3_top8_4bar_20260729 `
  --pair-count 8 `
  --transition-bars 4 `
  --optimization-steps 60 `
  --max-track-uses 2 `
  --blind-seed 20260729
```

Jeder Paarordner enthält nur `A.wav` und `B.wav`. `manifest.json` verrät die
Zuordnung nicht. `answer_key.json` darf erst nach der Bewertung geöffnet
werden. Die vorbereitete `ratings.json` speichert pro Variante fünf Kriterien
von 1 bis 5, A/B/Tie-Präferenz, Fehler-Tags und Notizen.

Aktuellen Bewertungsstand anzeigen:

```powershell
.venv\Scripts\python.exe -m src.evaluation.control_study_ratings show `
  output\control_studies\blind_v3_top8_4bar_20260729
```

Erst nach `status = completed` den Antwortschlüssel methodisch zuordnen und
`study_results.json` erzeugen:

```powershell
.venv\Scripts\python.exe -m src.evaluation.analyze_control_study `
  output\control_studies\blind_v3_top8_4bar_20260729
```

Der versionierte Studienvertrag steht in
[`CONTROL_STUDY_PROTOCOL.md`](./CONTROL_STUDY_PROTOCOL.md).

Control-v3 mit begrenzten Kurvenschritten und dem aktuellen
Rubber-Band-Time-Stretch-Backend als neuen blinden Satz rendern:

```powershell
.venv\Scripts\python.exe -m src.evaluation.blind_control_study `
  output\batches\all_songs_top3_targets_top3_transitions_20260722 `
  output\control_studies\blind_v4_control_v3_rubberband_top8_4bar_20260730 `
  --pair-count 8 `
  --transition-bars 4 `
  --optimization-steps 60 `
  --max-track-uses 2 `
  --blind-seed 20260730
```

Der Ordner enthält dieselben acht Songpaare wie der vorherige v2-Hörsatz, aber
vollständig neu gerenderte A/B-Dateien. `manifest.json` nennt pro Paar
`tempo_backend`; `answer_key.json` bleibt bis 8/8 Ratings geschlossen.

Nach vollständiger Bewertung den neuen Satz auswerten:

```powershell
.venv\Scripts\python.exe -m src.evaluation.analyze_control_study `
  output\control_studies\blind_v4_control_v3_rubberband_top8_4bar_20260730
```

## Featurevertrag anzeigen

Das aktive maschinenlesbare Schema für das spätere Feature→Control-Modell
anzeigen:

```powershell
.venv\Scripts\python.exe -m src.features
```

Feature-Protokoll 1 definiert pro Track `(32, 54)` sowie 16 globale Features.
Der vollständige Vertrag steht in
[`FEATURE_PROTOCOL.md`](./FEATURE_PROTOCOL.md).

Deterministische Volltrack-Features berechnen oder aus dem Hash-Cache laden:

```powershell
.venv\Scripts\python.exe -m src.features cache-track `
  "musik\04 - GHOST.flac"
```

Der erste Aufruf schreibt `manifest.json` und `track_features.npz` unter
`output/feature_cache/`. Weitere Aufrufe mit identischem Audio, Beat-Grid,
Sample-Rate, Zieltempo und Extractorvertrag liefern `cache_hit: true`.

Standardmäßig wird dabei `htdemucs` für Vocal-Features verwendet. Der erste
Lauf lädt die offiziellen Gewichte und berechnet einen wiederverwendbaren
Vocal-Stem; spätere Cue Points, Songpaare und Zieltempi desselben Songs nutzen
dieses Stem-Artefakt erneut. Für schnelle technische Tests ohne Modell:

```powershell
.venv\Scripts\python.exe -m src.features cache-track `
  "musik\04 - GHOST.flac" `
  --vocal-backend disabled
```

Modellreferenz, BibTeX und die verifizierte Gewichtsrevision stehen in
[`PRETRAINED_MODELS.md`](./PRETRAINED_MODELS.md) und
[`REFERENCES.bib`](./REFERENCES.bib).

Eine für ein bestimmtes Zieltempo ausgerichtete Trackvariante separat cachen:

```powershell
.venv\Scripts\python.exe -m src.features cache-track `
  "musik\Aversion - Activation [Explicit].flac" `
  --target-bpm 156.60511363636363
```

Der Vocal-Extractor und die globalen Paarfeatures sind implementiert.
Belastbare musikalische Phrasenmerkmale fehlen noch; sie werden mit
`phrase_valid = 0` als nicht verfügbar markiert.

## Feature-Dataset exportieren

Die drei bestgerankten Vier-Takt-Kandidaten je Songpaar als
Feature→Control-Eingaben exportieren:

```powershell
.venv\Scripts\python.exe -m src.features export-dataset `
  output\batches\all_songs_top3_targets_top3_transitions_20260722\manifest.json `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  --top-k-per-pair 3 `
  --transition-bars 4 `
  --split-seed 20260731 `
  --vocal-backend demucs
```

Erweiterter 145–165-BPM-Export mit mehr Cue-Varianz je Paar:

```powershell
.venv\Scripts\python.exe -m src.features export-dataset `
  output\batches\all_music_recursive_bpm145_165_top1_20260805\manifest.json `
  output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 `
  --top-k-per-pair 10 `
  --transition-bars 4 `
  --split-seed 20260805 `
  --min-bpm 145 `
  --max-bpm 165 `
  --vocal-backend demucs
```

Der Export erzeugt `train.npz`, `validation.npz`, `test.npz`,
`examples.jsonl` und `manifest.json`. Splits werden über Audio-SHA statt
Kandidaten gebildet; Source und Target eines exportierten Beispiels liegen
immer im selben Split. Normalisierungsstatistiken stammen ausschließlich aus
Trainings-Tracks. Details: [`DATASET_PROTOCOL.md`](./DATASET_PROTOCOL.md).

## Feature→Control-MLP trainieren

Der Trainingslauf baut fehlende Bridge-Waveform-Caches einmalig auf, misst in
Epoche 0 die Equal-Power-Initialisierung und trainiert anschließend nur auf
`train`. `validation` steuert Best-Checkpoint und Early Stopping; `test` wird
nicht geladen.

```powershell
.venv\Scripts\python.exe -m src.ml train `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\training_runs\time_shared_mlp_v1_objective_v4_seed20260804_20260804 `
  --seed 20260804 `
  --max-epochs 30 `
  --batch-size 5 `
  --patience 6
```

Ein unterbrochener Lauf kann bei identischem Vertrag mit höherem
`--max-epochs` fortgesetzt werden:

```powershell
.venv\Scripts\python.exe -m src.ml train <dataset> <run-ordner> `
  --max-epochs 60 `
  --resume
```

Details zu Checkpoints, Hashes und Reproduzierbarkeit:
[`ML_CONTROL_MODEL_PROTOCOL.md`](./ML_CONTROL_MODEL_PROTOCOL.md).

## Gelerntes MLP blind gegen Equal Power hören

```powershell
.venv\Scripts\python.exe -m src.evaluation.ml_control_study `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\training_runs\time_shared_mlp_v1_objective_v4_seed20260804_20260804 `
  output\control_studies\blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun `
  --split validation `
  --max-examples-per-pair 9 `
  --blind-seed 20260804
```

Der Validation-Split ist ein Entwicklungsvergleich, da er bereits für
Early Stopping verwendet wurde. Während des Hörens nur `A.wav`, `B.wav`,
`README.md` und `ratings.json` verwenden; `answer_key.json` bleibt bis zur
vollständigen Bewertung geschlossen.

## Vocal-Control-Modell v2 prüfen und Waveforms cachen

Modellkonfiguration und Ausgaben anzeigen:

```powershell
.venv\Scripts\python.exe -m src.ml model-info-vocal
```

Die geplante TCN/BiLSTM-Architektur inspizieren:

```powershell
.venv\Scripts\python.exe -m src.ml model-info-tcn-bilstm
```

Die TCN/BiLSTM-Trainingssonde auf dem erweiterten Feature-Datensatz starten:

```powershell
.venv\Scripts\python.exe -m src.ml train-tcn-bilstm `
  output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 `
  output\training_runs\tcn_bilstm_transition_control_v1_full_band_extended_bpm145_165_top10_20260812 `
  --device cuda:0
```

Mix und Demucs-Vocal-Stems für Objective v5 samplegleich cachen:

```powershell
.venv\Scripts\python.exe -m src.ml cache-vocal-waveforms `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  --split train `
  --training-sample-rate 11025
```

Der neue Cache liegt getrennt unter
`output/ml_cache/bridge_waveform_v2_vocal/`. Der bestehende `train`-Befehl
trainiert weiterhin nur Modell v1 mit Objective v4.

Das Vocal-Modell v2 mit Objective v5 trainieren:

```powershell
.venv\Scripts\python.exe -m src.ml train-vocal `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\training_runs\vocal_time_shared_mlp_v2_objective_v5_seed20260805_20260805 `
  --seed 20260805 `
  --max-epochs 30 `
  --batch-size 5 `
  --learning-rate 0.001 `
  --patience 6 `
  --min-delta 0.0001 `
  --training-sample-rate 11025
```

Fehlende Vocal-Waveform-Caches für Train und Validation werden dabei einmalig
aufgebaut; der Testsplit bleibt unangetastet. Resume verwendet den separaten
Befehl und verlangt einen identischen Run-Vertrag:

```powershell
.venv\Scripts\python.exe -m src.ml train-vocal <dataset> <run-ordner> `
  --max-epochs 60 `
  --resume
```

Der reale Lauf auf dem erweiterten Datensatz:

```powershell
.venv\Scripts\python.exe -m src.ml train-vocal `
  output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 `
  output\training_runs\vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805 `
  --seed 20260805 `
  --max-epochs 30 `
  --batch-size 5 `
  --learning-rate 0.001 `
  --patience 6 `
  --min-delta 0.0001 `
  --training-sample-rate 11025
```

Details zu Vertrag, Checkpoints und aktuellem Trainingsstand:
[`VOCAL_CONTROL_MODEL_PROTOCOL.md`](./VOCAL_CONTROL_MODEL_PROTOCOL.md).

## Vocal-reiche Objective-v4/v5-Controls blind vergleichen

```powershell
.venv\Scripts\python.exe -m src.evaluation.vocal_objective_study `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\control_studies\blind_v7_objective_v5_vocal_active6_20260805_rerun `
  --splits train validation `
  --pair-count 6 `
  --optimization-steps 80 `
  --learning-rate 0.06
```

Die Auswahl verlangt Vocal-Aktivität in den tatsächlich gerenderten
Source- und Targetfenstern, begrenzt Trackwiederholungen und schließt
`STRUGGLING` explizit aus. Während der Bewertung nur `A.wav`, `B.wav`,
`README.md` und `ratings.json` verwenden; `answer_key.json` bleibt bis zum
Abschluss geschlossen.

## Analyse-Cache und Ausgaben

Beim ersten Lauf analysiert BeatBridge BPM, Beats und Taktpositionen. Neue
Ergebnisse werden anhand von Audio-SHA und Analysevertrag zwischengespeichert:

```text
output/pre_analysis/v2/<audio-sha256>/<analysis-id>/analysis.json
```

- `analysis.json` enthält Audioidentität, vollständigen Analysevertrag, BPM,
  Beat-/Taktpositionen, Fallbackstatus, Backendidentitäten, Confidence und
  Diskrepanzen zwischen librosa und aufTAKT.
- Die Datei wird atomar geschrieben.
- Gleichnamige Audiodateien kollidieren nicht, weil der vollständige Audiohash
  statt des Track-Stems den Ordner bestimmt.
- Wird Audio, Algorithmus, librosa-Version oder aufTAKT-Binary verändert,
  entsteht ein neuer Cacheeintrag.
- Historische Stem-/Text-Caches bleiben read-only lesbar und werden nicht
  automatisch als aktuelle Analysen klassifiziert.
- Audiodateien im Ordner `musik/` werden ausschließlich gelesen und nicht verändert.

## Häufige Fehler

### `ffmpeg` wurde nicht gefunden

Nicht-WAV-Dateien werden für aufTAKT temporär nach WAV konvertiert. Prüfen, ob `ffmpeg -version` in derselben PowerShell funktioniert.

### Kein Rubber-Band-Backend war erfolgreich

Die Meldung `[Time stretch] No Rubber Band backend succeeded` enthält getrennte
Ursachen für FFmpeg und das eigenständige CLI. Prüfen Sie zuerst:

```powershell
ffmpeg -hide_banner -filters | Select-String rubberband
```

Falls kein `rubberband`-Filter erscheint, muss ein FFmpeg-Build mit
`--enable-librubberband` verwendet oder alternativ das eigenständige
`rubberband`-CLI installiert werden. Mit `rubberband --version` lässt sich der
Fallback prüfen.

### Downbeat-Metadaten fehlen

Fehlt eine belastbare Downbeat-Erkennung, bricht die Analyse nicht deshalb ab:
Sie erzeugt ein explizit als approximativ markiertes 4/4-Raster und schreibt
die Herkunft in den Analyse-Cache. Das ist vom späteren Kandidatenfilter zu
unterscheiden: Die Kandidatengenerierung lehnt approximative oder unbekannte
Raster mit der Default-Policy `reject` ab. Nur
`--approximate-grid-policy allow` erlaubt diesen Fallback für einen bewussten
Batchlauf. Ein Batch ohne andere nutzbare Kandidaten endet dann mit einer
begründeten Rejection im Manifest, nicht mit einem stillen Ersatz-Grid.

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
