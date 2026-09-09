# Cue-Ranker Dataset Format 3

_Vertragsversion 3, eingeführt am 2026-08-25. Additiv zu Dataset v1/v2._

Format 3 ist ein leichter, gruppierter Kandidatenindex für Cue-Ranking. Es
ersetzt weder die v1- noch die v2-Exporter, deren Top-K-Auswahl und Artefakte
unverändert bleiben.

## Sealed Split und Pair-Index

Ein Cue-Ranker-Export beginnt bei einem SHA-geprüften `pair_index.json`. Der
Index enthält ausschließlich Paare, deren beide Audio-SHAs im selben Split
`train` oder `validation` liegen. Test-SHAs dürfen nur in der externen
Split-Map als Abweisungsmenge vorkommen. Testpfade, Test-Pair-Manifeste und
Testcounts werden nicht gelesen oder geschrieben. Fehlt ein solcher Index,
ist `sealed_test_pair_index_required` ein harter Fehler; es gibt keinen
Legacy-Discovery-Fallback.

Der Pair-Index bindet Pair-Manifestpfad und -SHA, geordnete Audio-SHAs,
Candidate-Generator- und Request-Hash sowie Split-Map-SHA. Vor dem Öffnen
eines Pair-Manifests werden genau diese Angaben gegen den Index geprüft.

Der offizielle Einstieg ist:

```powershell
.venv\Scripts\python.exe -m src.features build-cue-ranker-pair-index <split-authorized-batch-manifest> <pair-index.json> --split-map <split-map.json>
```

Der Batch-Producer schreibt dafür je abgeschlossenem Paar vorab die
vollständige Provenienz in sein Root-Manifest: geordnete Source-/Target-
Audio-SHAs, Pair-Manifest-SHA, Candidate-Generator sowie die vollständige
Candidate-Request-Konfiguration und deren SHA. Der Builder liest nur dieses
Root-Manifest und die Split-Autorität. Historische Roots ohne diese Angaben
werden mit `sealed_test_pair_index_required` beziehungsweise einer
Provenienzfehlermeldung abgelehnt; es gibt keinen nachträglichen Discovery-
oder Pair-Manifest-Fallback. Optional bindet der Index zusätzlich einen
Dataset-Manifestpfad und dessen SHA.

## Universum und Gruppen

Alle akzeptierten v2-Candidates (`bar_grid_v2_length_specific`) einer
zulässigen Gruppe werden indexiert. Der Pfad verwendet niemals das
`top_k_per_pair`-Verfahren. Er akzeptiert nur `approximate_grid_policy=reject`,
Format 2, 4/4-Cues, `filter_status=accepted` und zwei nicht-Fallback-Grid-
Provenienzen mit SHA-256-Gridhash.

`group_id` ist nichtzirkulär:

```text
sha256("cue_ranker_group_v1" | source_sha | target_sha | generator |
       request_hash | sha256(canonical full member identities))
```

Die volle Member-Identität enthält Generator, beide Audio-SHAs, vollständige
Cues, Länge/Beats und beide Grid-Hashes. Gleiche `candidate_id` bei
unterschiedlicher voller Identität ist `candidate_id_collision`.

Der universelle Index speichert Candidate-, Cue-, Grid-, Audio- und
Pair-Manifest-Provenienz samt SHA-256 sowie einen historischen
`feature_baseline_v3`-Score ausschließlich als Baseline/Stratifizierungswert;
er ist kein Teacher-Target.

## Sampling und Ragged Gruppen

Die Teacher-Auswahl ist pro Gruppe deterministisch. Die Slotzahl ist
`min(512, max(128, ceil(16 * sqrt(n))))`. Baseline-Quantile
`[0,.1),[.1,.4),[.4,.7),[.7,.9),[.9,1]` erhalten 10/20/30/25/15 Prozent;
unscored erhält bis zu fünf Prozent. Leere Strata und Rundungsreste werden
kanonisch auf nichtleere Strata verteilt. Innerhalb eines Stratums entscheidet
die kleinste Priorität `sha256(seed|group_id|stratum|candidate_id)`.

Jede gelabelte Row speichert `stratum`, Stratumgröße, Quote, Seed und
`p_inclusion=q_h/n_h`. Der Wert muss in `(0,1]` liegen. Hard Negatives werden
als deterministische Anker aus dem untersten Baseline-Quantil markiert, aber
in v1 nicht kandidatenspezifisch nachgemint: ein listweiser Schritt verwendet
später stets alle gelabelten Mitglieder einer Gruppe.

`*-ragged-groups.npz` enthält `group_ids`, `group_offsets` und
`member_row_ids`; dadurch sind unterschiedliche Gruppen- und Längengrößen
ohne Padding darstellbar.

## Layout

```text
<root>/
  manifest.json
  groups/{train,validation}.jsonl
  index/{train,validation}-candidates-00000.npz
  index/{train,validation}-ragged-groups.npz
  teacher/{train,validation}-labels-00000.npz
  normalization/train_only_stats.json
```

NPZ-Candidatezeilen tragen serialisierte, kanonische Metadaten und keine
Feature- oder Waveformtensoren. Teacher-Labels werden in einem separaten,
SHA-gebundenen Schritt ergänzt. `failed` ist technisch fehlgeschlagen und
weder positives noch negatives Qualitätslabel; `guard_rejected` ist ein
dokumentierter negativer Anker. Der Datasetmanifest enthält nur
`test: {"state":"sealed_not_materialized"}`.

## Produktionspfad und Resume (verifiziert am 2026-08-26)

Der produktive Offline-Pfad besitzt zwei additive CLI-Einstiege:

```powershell
.venv\Scripts\python.exe -m src.ml seal-cue-ranker-teacher <completed-variable-tcn-run> <teacher-release.json> `
  --normalizer <training-only-normalizer.json> `
  --backend-provenance <rubberband-backend-provenance.json>

.venv\Scripts\python.exe -m src.ml label-cue-ranker-teacher <universe-root> <teacher-release.json> <label-root> `
  --split-map <split-authority.json> --resume
```

Der Sealer akzeptiert ausschließlich den manifestierten `best_checkpoint`
eines abgeschlossenen `variable_tcn_bilstm_transition_control_v1`-Runs. Er
bindet Checkpoint- und Runmanifest-SHA, State-dict-Schema, Modellvertrag,
Renderer, Objective-v5, Guard-Konfiguration, train-only Normalizer,
`local_grid_target_to_source_v1`, Backend-Provenienz, Code-SHAs und Umgebung.
Jeder Load prüft diese Kette vor `torch.load(..., weights_only=True)`; ein
anderer Run wird nie automatisch gewählt.

Der Resolver nimmt nur die SHA-geprüften Train-/Validation-Shards entgegen,
bindet Candidate-SHA und `analysis_id` an die Analysis, erzeugt Feature-v2-
Fenster und Globalfeatures mit den vorhandenen Extraktoren und verwendet nur
`align_variable_waveform_windows()` für die vier Waveforms. Es gibt keine
neue Crop-, Padding-, Resampling- oder Grid-Fallbacksemantik.

`output/ml_cache/cue_ranker_teacher_waveform_v1/` ist ein eigener,
unveränderlicher Cache. Sein Key enthält Candidate-Identität,
Teacher-Release-SHA, Feature-Payload-/Manifest-, Grid-, Audio- und Stem-SHAs,
lokale Source-Geometrie, Alignment, Normalizer, Renderer, Objective und
Backend. Der Labelroot führt darüber hinaus einen atomaren Ergebniscache je
Candidate. Ein Resume akzeptiert nur exakt gebundene Treffer und wiederholt
keine verifizierte Bewertung.

`teacher_status=scored|guard_rejected|failed` bleibt für den bestehenden
Ranker-Loss bestehen. Das zusätzliche operative Feld
`label_status=success|guard_rejected|technical_failure` macht den
Produktionsstatus eindeutig. `guard_rejected` bleibt ein relativer negativer
Anker; `failed` bleibt aus Loss und Qualitätsmetriken ausgeschlossen.
Konfigurierbare Candidate-/Failure-Limits stehen im Labelmanifest. Ein Fehler
wird gecacht und blockiert andere Gruppen nicht; ein explizites Budget beendet
den Lauf fortsetzbar.

## Reales Featureloading und Ranker-Training (verifiziert am 2026-08-26)

`CueRankerGroupedDataset` darf für Format 3 keine eingebetteten Tensoren als
Produktionsersatz verwenden. Sein Standardloader verifiziert zuerst
Dataset-, Universe- und Teacher-Label-Manifest/Shard-SHAs sowie die identische
Candidate-Identität. Danach sucht er ausschliesslich einen bestehenden
Feature-Protocol-2-Cache, dessen Payload- und Manifest-SHA mit der
Teacher-Provenienz übereinstimmen. Er erzeugt mit
`extract_variable_track_window()` und
`build_variable_global_pair_features()` dieselben normalisierten Inputs wie
der Teacher. Fehlende Caches, nicht-endliche Werte, andere Dtypes,
Geometrien ausser 16/32/48/64 oder abweichende Normalizer/Teacher-SHAs sind
harte Fehler. Er baut keinen Cache, öffnet kein Pair-Manifest und besitzt
keinen Testsplitpfad.

Der Export kopiert einen unabhängigen, train-only Normalizer mit `stats_id`,
den beiden endlichen p99-Statistiken, `input_universe_manifest_sha256`,
Train-Track-SHAs und der SHA-Referenz der Eingabedatei. Validation verwendet
ihn unverändert. Der offizielle Trainingsaufruf ist:

```powershell
.venv\Scripts\python.exe -m src.ml train-cue-ranker <dataset-v3-root> <run-root> --feature-cache-root <feature-cache-root> --batch-size 1 --max-epochs 1 --seed 20260825 --device cpu --wandb-mode disabled
```

Er erzeugt ausschliesslich Train- und Validation-Loader. `--resume` setzt
nur nach der bestehenden SHA-Prüfung von Manifest, History, Best und Latest
mit `torch.load(..., weights_only=True)` fort; es gibt keine Testsplitoption.
