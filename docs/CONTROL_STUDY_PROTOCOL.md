# Blinder Control-A/B-Hörvergleich

_Vertragsversion: 1, eingeführt am 2026-07-29._

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

Alle vier JSON-Formate starten mit `format_version = 1`.

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

Für A und B werden jeweils ganzzahlige Werte von 1 bis 5 gespeichert:

- `cleanliness`,
- `energy_shape`,
- `low_end_handover`,
- `rhythmic_stability`,
- `artifact_freedom`.

Zusätzlich werden `preferred = A | B | tie`, optionale Fehler-Tags und eine
freie Notiz erfasst. Nach jeder Bewertung wird `ratings.json` atomisch
ersetzt. `status = completed` gilt erst, wenn alle Paare bewertet sind.

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
