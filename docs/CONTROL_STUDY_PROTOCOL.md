# Blinder Control-A/B-Hörvergleich

_Artefakt-Vertragsversion: 1, eingeführt am 2026-07-29. Ratings-Version 2
mit Vocal-Kriterium: 2026-07-31. Ratings-Version 3 ohne Rhythmik als
Control-Modell-Kriterium: 2026-08-05._

Dieses Dokument beschreibt Auswahl, Artefakte und Bewertungen der ersten
blinden Hörvalidierung für `differentiable_control_v2`. Änderungen an Version 1
erfolgen nur additiv; inkompatible Änderungen benötigen eine neue Version.

Der zweite Hörsatz
`blind_v4_control_v3_rubberband_top8_4bar_20260730` verwendet dieselben acht
gerichteten Songpaare, Control-Protokoll 3 und Rendering-Protokoll 5. Alle
Audios wurden neu erzeugt; bei notwendiger Tempoanpassung wird Rubber Band
verwendet und das konkrete Backend im öffentlichen Manifest dokumentiert.
Die abgeschlossene Bewertung ergab acht Gleichstände und identische
Kriterienwerte für beide Methoden. `study_results.json` dokumentiert dieses
Ergebnis nach der Entblindung.

Der dritte Hörsatz
`blind_v5_objective_v4_heldout_test9_4bar_20260731_rerun` stammt aus dem
Audio-SHA-getrennten Testsplit und verwendet Objective Version 4. Seine neun
Ratings wurden am 2026-08-04 vollständig geblendet gespeichert und erst dann
entblindet. Ergebnis: **9/9 Präferenzen für optimiert**, 0 für Equal Power,
0 Gleichstände. Optimiert steigt im Sechs-Kriterien-Mittel von 4,7593 auf
4,9259. Der Vorteil liegt ausschließlich bei `cleanliness` (4,0 auf 5,0);
`vocal_clarity` ist mit 4,7778 identisch. Wegen drei Cue-Varianten pro
gerichteter Paargruppe und nur drei Test-Audiohashes sind die neun Urteile
nicht als unabhängige Stichprobe zu behandeln.

Der vierte Hörsatz
`blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun`
vergleicht den besten Checkpoint von `time_shared_mlp_v1` geblendet gegen
Equal Power. Er umfasst alle neun Validation-Beispiele. Da derselbe Split
für Early Stopping und Modellwahl verwendet wurde, ist dies ausdrücklich ein
Entwicklungs-Gate und kein unabhängiger Generalisierungsnachweis. Sechs der
neun Beispiele sind verschiedene Cues derselben gerichteten
BREATH_LESS→BREATH_LESS-Kombination; die übrigen drei sind
ASCENSION→BREATH_LESS. Die Ratings sind noch offen.

Der fünfte Hörsatz
`blind_v7_objective_v5_vocal_active6_20260805_rerun` vergleicht
Objective-v4-Controls ohne Vocal-Ducking mit vollständig optimierten
Objective-v5-Controls im selben stem-fähigen Renderer. Alle sechs Paare
besitzen auf beiden Übergangsseiten gemessene Vocal-Aktivität. Nach der
vollständigen geblendeten Bewertung gewinnt Objective v5 zwei Paare,
Objective v4 eines; drei sind Gleichstände. Der Fünf-Kriterien-Mittelwert
steigt von 4,2333 auf 4,3667. Ausschließlich `vocal_clarity` unterscheidet
sich (4,3333 auf 5,0). Paar 2, 3 und 5 werden bei beiden Methoden durch
hörbare Rubber-Band-Time-Stretch-Artefakte begrenzt.

Der sechste Hörsatz
`blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806` vergleicht den
Best-Checkpoint aus Epoche 22 des erweiterten `vocal_time_shared_mlp_v2`-
Laufs geblendet gegen seine ungelernte Initialisierung. Er enthält fünf
vocal-aktive, unterschiedliche gerichtete Paarungen aus dem Validation-Split.
Alle liegen bei exakt gleicher Source-/Target-BPM und verwenden deshalb kein
Time-Stretch. Damit prüft der Satz gezielt die gelernten Mix-, Low-End-,
Vocal- und Ducking-Kurven. Die Ratings sind noch offen; der Satz ist ein
Entwicklungs-Gate auf dem Modellwahl-Split, kein unabhängiger
Generalisierungsnachweis.

## Zweck

Vor dem Training eines Feature→Control-Modells wird geprüft, ob direkt gegen
das Proxy-Objective optimierte monotone Kurven hörbar mindestens so gut sind
wie eine feste Equal-Power-Baseline. Der Blindvergleich verhindert, dass die
Methodenbezeichnung das Urteil beeinflusst.

## Auswahl

- nur vier Takte,
- vorhandener `rendered_transition_baseline_v1`-Score absteigend,
- jedes gerichtete Songpaar höchstens einmal,
- jeder Track höchstens zweimal,
- Ausschlüsse aus `config/track_exclusions.json`; insbesondere kein
  `STRUGGLING`.

Der Objective-v4-Hörsatz verwendet stattdessen den zuvor eingefrorenen,
Audio-SHA-getrennten Dataset-Testsplit. Alle neun Testbeispiele werden
exportiert; mehrere Cue-Kombinationen desselben gerichteten Songpaars sind
bewusst keine unabhängigen Beobachtungen. Validation diente ausschließlich
zur Gewichtswahl, der bekannte frühere Acht-Paar-Satz wird nicht als Test
wiederverwendet.

## Artefakte

```text
study/
├── manifest.json
├── answer_key.json
├── ratings.json
├── study_results.json
├── README.md
└── <pair>/
    ├── A.wav
    └── B.wav
```

Manifest und Antwortschlüssel starten mit `format_version = 1`. Neue Ratings
verwenden `format_version = 3`; vorhandene Version-1/2-Ratings bleiben les-
und auswertbar. Ergebnisse verwenden Version 2, damit beliebige zwei
Methodennamen als Referenz und Kandidat ausgewertet werden können.

- `manifest.json` ist der öffentliche, geblendete Vertrag. Er enthält Tracks,
  Paarindex, vier Takte und technische Metadaten der Dateien A/B, aber keine
  Methodenabbildung oder Proxy-Scores.
- `answer_key.json` enthält A/B→Baseline/Optimiert sowie die vollständigen
  Controls, Loss-Komponenten und historische Render-Metrik. Diese Datei wird
  erst nach abgeschlossener Bewertung geöffnet.
- `ratings.json` ist ein getrenntes, atomisch geschriebenes Sidecar und darf
  iterativ verändert werden. Audio, öffentliches Manifest und Antwortschlüssel
  bleiben unverändert.
- `study_results.json` wird erst aus einem vollständig bewerteten Satz
  erzeugt. Es entblindet die Methoden, enthält Präferenzzahlen,
  Kriterienmittelwerte, paarweise Differenzen und die methodenzugeordneten
  Einzelurteile.

## Bewertung

Für A und B werden in Ratings-Version 3 jeweils ganzzahlige Werte von 1 bis
5 gespeichert:

- `cleanliness`,
- `energy_shape`,
- `low_end_handover`,
- `vocal_clarity`,
- `artifact_freedom`.

`rhythmic_stability` wurde am 2026-08-05 aus neuen Control-Modell-Ratings
entfernt: Die verglichenen Kurven verändern weder Beat-Grid noch
Time-Stretch-Backend. Rhythmik bleibt ein technisches Kandidaten-/Renderer-
Kriterium. Historische Ratings-Versionen 1/2 behalten den Wert unverändert.

Zusätzlich werden `preferred = A | B | tie`, optionale Fehler-Tags und eine
freie Notiz erfasst. Nach jeder Bewertung wird `ratings.json` atomisch
ersetzt. `status = completed` gilt erst, wenn alle Paare bewertet sind.
Ratings-Version 2 ergänzt außerdem die Fehler-Tags `vocal_clash` und
`cut_lyrics`.

## Reproduzierbarer Export

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

Der Zielordner muss neu sein. Historische Batch-Artefakte werden ausschließlich
gelesen.

Objective v4 aus dem track-getrennten Testsplit wird so exportiert:

```powershell
.venv\Scripts\python.exe -m src.evaluation.heldout_control_study `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\control_studies\blind_v5_objective_v4_heldout_test9_4bar_20260731 `
  --split test `
  --max-examples-per-pair 3 `
  --optimization-steps 80 `
  --learning-rate 0.06 `
  --blind-seed 20260731
```

Der beste Feature→Control-Checkpoint wird so gegen Equal Power exportiert:

```powershell
.venv\Scripts\python.exe -m src.evaluation.ml_control_study `
  output\datasets\feature_protocol_v1_top3_4bar_track_split_20260731 `
  output\training_runs\time_shared_mlp_v1_objective_v4_seed20260804_20260804 `
  output\control_studies\blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun `
  --split validation `
  --max-examples-per-pair 9 `
  --blind-seed 20260804
```

Der Export prüft Datasetdateien, Paarmanifest und Best-Checkpoint gegen ihre
SHA-256-Werte. `answer_key.json` enthält zusätzlich Run-ID, Checkpoint-Epoche,
Modellkonfiguration, vorhergesagte Controls und Objective-Komponenten. Im
öffentlichen Manifest erscheinen weder die Methodenabbildung noch die
Proxy-Losswerte.

Der beste Vocal-v2-Checkpoint wird so gegen seine ungelernte Initialisierung
exportiert:

```powershell
.venv\Scripts\python.exe -m src.evaluation.vocal_ml_control_study `
  output\datasets\feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805 `
  output\training_runs\vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805 `
  output\control_studies\blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806 `
  --split validation `
  --pair-count 5 `
  --max-track-uses 3 `
  --maximum-tempo-adjustment-fraction 0.005 `
  --blind-seed 20260806
```

Dieser Export verlangt auf beiden Seiten mittlere Vocal-Stärke mindestens
`0,15`, höchstens einen Cue pro gerichteter Paarung und höchstens `0,5 %`
Tempoanpassung. Er prüft zusätzlich Run-/Modellvertrag, Dataset-ID und
-Manifesthash sowie Best-Checkpoint-Epoche und -SHA-256. Der öffentliche
Vertrag enthält Vocal-/Tempodaten, aber weder A/B-Zuordnung noch Proxy-Loss.

## Ergebnis anzeigen

```powershell
.venv\Scripts\python.exe -m src.evaluation.control_study_ratings show `
  output\control_studies\blind_v3_top8_4bar_20260729
```

Der Antwortschlüssel wird erst ausgewertet, wenn `rated_count = pair_count`
gilt.

Danach wird die Studie reproduzierbar entblindet und ausgewertet:

```powershell
.venv\Scripts\python.exe -m src.evaluation.analyze_control_study `
  output\control_studies\blind_v3_top8_4bar_20260729
```

Die Auswertung ersetzt `study_results.json` atomisch. Sie verändert weder
Ratings noch Audio, Manifest oder Antwortschlüssel.
