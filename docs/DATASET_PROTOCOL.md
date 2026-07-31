# Feature-Dataset-Protokoll

_Datasetformat 1, eingeführt am 2026-07-31._

Dieses Protokoll definiert den reproduzierbaren Export der Eingaben für das
spätere Feature→Control-Modell. Es erzeugt noch keine Zielkurven: Das geplante
Training bleibt selbstüberwacht und erhält sein Signal erst aus
differenzierbarem Renderer und eingefrorenem Objective.

## 1. Auswahl der Beispiele

Quelle ist ein reguläres Batch-`manifest.json` oder das Root-Manifest eines
Multi-Song-Batches. Pro abgeschlossenem Songpaar werden standardmäßig die drei
bestgerankten Kandidaten mit exakt vier Takten ausgewählt.

Die Filterreihenfolge ist:

1. `transition_length_bars == 4`, passend zu Feature- und Control-Protokoll,
2. aufsteigender Rang aus `candidate_ranking`,
3. höchstens `top_k_per_pair` unterschiedliche Kandidaten,
4. Ausschlüsse mit Scope `training`, insbesondere `STRUGGLING`,
5. Verwerfen von Paaren, deren Tracks verschiedenen Splits zugeordnet sind.

Bereits gerenderte Varianten sind nicht die Auswahlquelle. Historische
Top-Renderings können zwei Takte lang sein, während unter den nachfolgenden
Rankingplätzen geeignete Vier-Takt-Kandidaten liegen.

## 2. Track-getrennte Splits

Die Splitidentität ist der SHA-256-Hash der unveränderten Audiodatei, nicht
Pfad, Kandidat oder Source-/Target-Rolle. Ein Track liegt dadurch exakt in
einem der Splits:

```text
train / validation / test
```

Standardverhältnis ist `0,70 / 0,15 / 0,15`, Seed `20260731`. Eine
deterministische, seed-basierte Suche verteilt die Tracks so, dass alle
aktiven Splits Beispiele enthalten, die Beispielanteile möglichst nahe am
Zielverhältnis liegen und danach möglichst viele ausgewählte Paare erhalten
bleiben. Diese Suche ändert keine Kandidatenbewertung.

Nur Paare, deren Source- und Target-Hash demselben Split angehören, werden
exportiert. Kreuzende Paare werden nicht umetikettiert, sondern verworfen und
im Manifest gezählt. Damit kann derselbe Song auch über umgekehrte Rollen oder
tempoangepasste Varianten nicht zwischen Train, Validation und Test leaken.

## 3. Normalisierung

`spectral_flux` und `onset_strength` werden mit dem 99. Perzentil von
`log1p(raw_value)` normalisiert. Diese beiden Statistiken werden
ausschließlich aus den Volltrack-Artefakten der im **Trainingssplit**
verwendeten Tracks und Tempo-Varianten bestimmt. Validation und Test
verwenden danach unverändert dieselben Werte.

Das Datasetmanifest speichert Werte, `stats_id` und
`fit_scope = training_tracks_only`.

## 4. Globale Paarfeatures

Jedes Beispiel enthält die 16 Werte aus Feature-Protokoll 1:

- normalisierte Original-BPM beider Tracks,
- signierte und absolute Tempoabweichung sowie binäre Stretch-Maske,
- lokale Tonika als Sin/Cos, Modus und Confidence für A/B,
- lokale harmonische Kompatibilität,
- Kontextabdeckung von vier Takten vor und vier Takten nach beiden Cues.

`global_pair_v1` schätzt Tonika und Dur/Moll deterministisch aus den lokalen
32-Schritt-Chromaprofilen mit den Krumhansl-Schmuckler-Profilen. Die
Confidence ist der begrenzte Abstand der zwei besten Templates und deshalb
eine versionierte Heuristik, keine kalibrierte Wahrscheinlichkeit. Bei
fehlender tonaler Evidenz sind Tonika/Modus/Confidence null und harmonische
Kompatibilität neutral `0,5`.

## 5. Dateiformat

Ein vollständiger Export enthält:

```text
<dataset>/
├── manifest.json
├── examples.jsonl
├── train.npz
├── validation.npz
└── test.npz
```

Jede Splitdatei enthält:

```text
example_ids:     unicode  (N,)
features_a:      float32  (N, 32, 54)
features_b:      float32  (N, 32, 54)
global_features: float32  (N, 16)
```

Auch leere Splits besitzen vertragsgültige Arrays mit führender Dimension
null. `examples.jsonl` ordnet jede Tensorzeile Kandidat, Split, Tracks,
Audio-Hashes, Original-/Aligned-Cues, BPM, Quellmanifest und Featurecaches zu.

`manifest.json` enthält mindestens:

- Dataset-, Feature-, Global-Extractor- und Splitversion,
- Quellmanifest- und Paarmanifest-Hashes,
- vollständiges maschinenlesbares Featureschema,
- Auswahl-/Ausschluss-/Cross-Split-Zähler,
- Track→Split-Zuordnung,
- Trainingsnormalisierung,
- Dateinamen, Shapes indirekt über den Vertrag und SHA-256 aller Dateien.

Der Zielordner muss neu sein. Der Export wird in einem temporären
Geschwisterordner aufgebaut und erst nach vollständigem Erfolg atomar an den
Zielpfad verschoben. Batchmanifeste, Audio und vorhandene Featurecaches werden
nicht verändert.

## 6. CLI

```powershell
.venv\Scripts\python.exe -m src.features export-dataset `
  output\batches\all_songs_top3_targets_top3_transitions_20260722\manifest.json `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  --top-k-per-pair 3 `
  --transition-bars 4 `
  --split-seed 20260731 `
  --vocal-backend demucs
```

Ein technischer Ein-Split-Smoke-Test darf `--train-ratio 1
--validation-ratio 0 --test-ratio 0` verwenden. Solch ein Export prüft das
Dateiformat, ersetzt aber ausdrücklich nicht den track-getrennten
Train/Validation/Test-Datensatz.
