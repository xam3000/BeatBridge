# Dataset Format 2 — variable Übergangslängen

_Vertragsversion 2, additive Ergänzung zu `DATASET_PROTOCOL.md`, eingeführt am
2026-08-20._

Der v1-Exporter und vorhandene `train.npz`/`validation.npz`/`test.npz` bleiben
unverändert. Format 2 exportiert mehrere angeforderte Längen in einem neuen,
atomar publizierten Datasetroot:

```text
<dataset-root-v2>/
├── manifest.json
├── lengths/
│   ├── 2bar/{train,validation,test}.npz
│   ├── 4bar/{train,validation,test}.npz
│   ├── 6bar/{train,validation,test}.npz
│   └── 8bar/{train,validation,test}.npz
└── metadata/
    ├── 2bar/{train,validation,test}.jsonl
    ├── 4bar/{train,validation,test}.jsonl
    ├── 6bar/{train,validation,test}.jsonl
    └── 8bar/{train,validation,test}.jsonl
```

## Homogene Shards statt Padding

Jeder Shard enthält ausschließlich eine Länge und damit eine Form:

```text
features_a:       float32 (N, T, 54)
features_b:       float32 (N, T, 54)
global_features:  float32 (N, 16)
length_condition: float32 (N, 1)
example_ids:      unicode (N,)
transition_length_bars: int16 (N,)
sequence_length:  int16 (N,)
```

Es gibt im Basispfad kein künstliches Padding und keine zusätzliche
Zeitachsenmaske. Die bestehenden `audio_valid`, `phrase_valid` und
`vocal_valid`-Kanäle bleiben die semantischen Featuremasken. Ein Loader lädt
genau einen Längen-Shard; gemischte T-Batches werden abgewiesen.

Auch ein leerer Shard wird geschrieben. Sein NPZ hat die führende Dimension
`0` und die korrekte Länge `T`; das Manifest markiert ihn mit `empty: true`,
`count: 0` und einem maschinenlesbaren `empty_reason`. Es werden keine
Beispiele erfunden. Train und Validation müssen für jede tatsächlich
trainierte Länge nichtleer sein.

## Auswahl und Split-Autorität

`export-dataset-v2` akzeptiert `--transition-bars 2 4 6 8`. Die Auswahl erfolgt
mit `top_k_per_pair` **pro Songpaar und pro Länge**. Erst die Union aller
ausgewählten und policybereinigten Records wird genau einmal über Audio-SHA
einer Split-Autorität zugeordnet. Dieselbe `audio_sha256 -> split`-Map wird für
alle Längen verwendet; Cross-Split-Paare werden verworfen, nicht umetikettiert.

Eine eingefrorene Map kann über `--split-map` gelesen und hashgeprüft werden.
Ohne diese Option erzeugt der Export genau eine deterministische Map über die
Union und speichert ihren kanonischen Hash im Manifest. Eine neue oder
unbekannte Trackmenge darf eine neue Map erzeugen, aber niemals je Länge eine
eigene Map.

## Manifest und Reproduzierbarkeit

Das Root-Manifest führt mindestens Dataset-/Exporter-/Feature-/Global-Pair-
Version, angeforderte Längen und `T`, Source- und Paarmanifest-SHAs,
vollständige Track-Zuordnung und deren kanonischen Hash, Split-Policy,
Training-only-Normalisierung, Shape-/Dtype-Verträge, pro-Länge/pro-Split-
Counts, NPZ-/JSONL-Pfade und Datei-SHAs. Beispielmetadaten führen Candidate-
und Pair-Manifest-SHA, Track-SHAs, Cues, BPM, Grid-Provenienz, L/Beats/T,
Längenkondition sowie Featurecache-ID und Cachemanifest-Hash.

Zeitstempel werden im v2-Manifest nicht verwendet. Konfiguration, Eingabe-
Hashes, sortierte JSON-Schlüssel und ein NPZ-Writer mit festem ZIP-Zeitstempel
sind damit reproduzierbar prüfbar. Ein vorhandener Datasetroot wird nicht geöffnet,
überschrieben oder gelöscht.

## CLI

```powershell
.venv\Scripts\python.exe -m src.features export-dataset-v2 `
  output\batches\variable\manifest.json `
  output\datasets\feature_protocol_v2_variable `
  --transition-bars 2 4 6 8 `
  --top-k-per-pair 3 `
  --split-map config\frozen_split_authority.json `
  --vocal-backend disabled
```

Der Befehl erzeugt keinen großen Datensatz von selbst; er exportiert nur die
vom Nutzer angegebene Manifestmenge in einen neuen Zielordner.
## Verifizierte reale Materialisierung (2026-08-21)

Die erste reale Format-2-Materialisierung wurde unter einem neuen Datasetpfad abgeschlossen:

`output/datasets/variable_v2_strict_20260820_selected_roformer_run01`

Der Export verwendete 87 strikt akzeptierte Merge-v2-Track-SHAs, eine gemeinsame
Audio-SHA-Split-Autorität und top-k=3 je Songpaar und Länge. Die nachgelagerte
Auswahlmanifeststufe ist unter `output/batch_variable_v2_strict_20260820_selected_top3_run01`
hashgebunden; die vollständigen Batchmanifeste bleiben die unveränderte Quelle.

Verifizierte Shards:

| Länge | T | Train | Validation | Test |
|---:|---:|---:|---:|---:|
| 2 Takte | 16 | 105 | 12 | 21 |
| 4 Takte | 32 | 105 | 12 | 21 |
| 6 Takte | 48 | 105 | 12 | 21 |
| 8 Takte | 64 | 105 | 12 | 21 |

`DATASET_V2_VALIDATION_OK` bestätigte Shapes, finite Werte, zeitnormalisierte
`transition_position`, eindeutige Example-IDs, Audio-SHA-Split-Isolation,
Manifest-/Dateihashes und RoFormer-Provenienz. Der Datensatz umfasst 552
Beispiele und 53 tatsächlich in exportierten Beispielen verwendete Tracks;
die Split-Autorität selbst enthält alle 87 ausgewählten Tracks. Leere
Längenshards traten in dieser Materialisierung nicht auf.
