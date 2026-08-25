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
