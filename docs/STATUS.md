# BeatBridge – Stand & Next Steps

_Stand: 2026-07-30_

**Maßgeblicher Kontext: [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) (Exposé).** Diese Datei hält den *technischen Prototyp-Stand der Startphase* (Monat 1 / erste 2–3 Wochen) fest. Ziel, Scope, wissenschaftlicher Beitrag, Related Work, Datenstrategie, Evaluation, 6-Monats-Plan und Risiken stehen im Exposé.

**Forschungsfrage (präzisiert am 2026-07-29):** Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue, nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu **bewerten** und zu **erzeugen** — möglichst ohne explizite Annotationen? Wissenschaftlicher Kern ist jetzt das **Lernen zeitabhängiger Mixing-Kurven ohne Ground-Truth-Kontrollkurven**; eine eingefrorene Übergangsmetrik liefert über einen differenzierbaren Renderer das Lernsignal. Compatibility- und Render-Metriken bleiben Baselines und Hilfskomponenten.

**Wichtigstes Erfolgskriterium der Startphase (Exposé Abschn. 14):** Nach spätestens drei Wochen sollen *mehrere automatisch erzeugte* Übergänge *hörbar* sein und *systematisch verglichen* werden können.

Kurzfazit Prototyp: Kandidaten können jetzt aus taktsynchronen Downbeats automatisch erzeugt, als Drop-Ende-A→energiearme Bridge→Drop-Anfang-B vorgerankt, ohne Überlappung der High-Power-Abschnitte gerendert und anschließend anhand des tatsächlichen Renderergebnisses erneut bewertet werden. Ein vollständig bewerteter blinder Hörsatz vergleicht monotone proxy-optimierte Kurven mit Equal Power. Volltrack-Features einschließlich vortrainierter Vocal-Separation sind implementiert; Feature→Control-Modell, belastbare musikalische Phrasenmerkmale und gelernte Metriken fehlen noch.

## Aktueller Stand (implementiert)

- **Projektstruktur / API / CLI**: `src/pipeline.py` bietet `render_transition()` sowie `generate_transition_candidates()` als programmatische Einstiege; argparse deckt weiterhin den einzelnen Render-Export ab. Struktur `src/analysis/`, `src/candidates/`, `src/cutting/`, `src/tempo/`.
- **Audio-I/O**: Laden über `librosa.load`, Export über `soundfile.write`; intern standardmäßig 44,1 kHz Stereo. Abweichende Sample-Raten werden resampelt, Mono wird auf Stereo erweitert und Beat-Positionen werden mit skaliert.
- **Beat-/Bar-Analyse** (`src/analysis/pre_analysis.py`):
  - librosa `beat_track` für BPM + Beats.
  - aufTAKT (`aufTAKTCl.exe`) für Taktposition; Nicht-WAV wird per ffmpeg konvertiert.
  - Merge beider Quellen zu bar-annotierten Beats (`sample, count_in_bar, beats_in_bar`); Abweichungen werden protokolliert.
  - Analyse-Cache per SHA-256-Hash des Songs (`00_pre_analysis.txt`), Diskrepanzen in `01_missing_beats.txt`.
  - Fallback: Wenn aufTAKT fehlt, fehlschlägt oder unvollständige Metadaten liefert, werden die Beat-Positionen als approximatives 4/4-Raster annotiert; ohne Beats wird bei gültigem BPM ein gleichmäßiges Raster erzeugt.
- **Übergänge**:
  - `src/cutting/simple_cut.py`: Hard Cut, Snap auf den nächstgelegenen Downbeat, Bar-Alignment zwischen beiden Songs.
  - `src/cutting/fade_cut.py`: linearer Crossfade über N Beats (Default 8), Bar-aligned.
  - `src/cutting/equal_power_fade_cut.py`: Equal-Power-Crossfade.
  - Alle Renderer passen Song B tonhöhenerhaltend auf BPM von Song A an; `tempo_fade` ist ein Kompatibilitätsalias für den linearen Crossfade.
- **Bridge-Rendering Version 2**: Fade-Renderer erhalten Drop A vollständig bis zum Source-Cut, mischen ausschließlich Source-Postroll mit Target-Preroll und beginnen Drop B exakt am Target-Cut. Die beiden High-Power-Abschnitte liegen dadurch außerhalb des überlappenden Fensters.
- **Tempo** (`src/tempo/`): Resample-basierte Variante (`SimpleTempoAdjust`, verändert Tonhöhe) und tonhöhenerhaltender `TimeStretch` über Rubber Band. Primär läuft FFmpegs `rubberband`-Filter mit gemeinsamem Stereo; bei Fehlern folgt das eigenständige Rubber-Band-CLI mit R3-Engine. Der frühere Librosa-Phase-Vocoder ist nicht mehr im Produktionspfad.
- **Tests**: `pytest`-Suite mit synthetischen Audiodaten prüft alle vier Renderer, FFmpeg-Priorität, Rubber-Band-CLI-Fallback, Float32-Zwischenformat, Tempoanpassung, 48→44,1-kHz-Resampling, Mono→Stereo und den Fehlerpfad bei fehlenden Downbeat-Metadaten.
- **Kandidatengenerierung** (`src/candidates/`): versionierter Vertrag `CANDIDATE_PROTOCOL.md` und Generator `bar_grid_v1`. Er kombiniert standardmäßig alle nutzbaren Taktgrenzen beider Songs für 2/4 Takte; vollständige Downbeat-Metadaten, Pre-/Post-Roll auf beiden Seiten, kompatible Beatanzahl in allen vier Fenstern und maximal 15 % Tempoabweichung sind harte Filter.
- **Feature-Ranking** (`src/ranking/`): `feature_baseline_v3` bewertet Drop A, Source-Auslauf, Target-Vorlauf und Drop B getrennt. Je 30 % entfallen auf High Power der Drops und Non-Overlap (Energieabfall nach A, niedrige Transition-Energie, Energieanstieg vor B); Chroma, RMS-Kontinuität, Spektrum und Tempo ergänzen den Score.
- **Featurevertrag, globale Paarfeatures und Datasetexport** (`src/features/`): Feature-Protokoll 1 definiert `features_a/features_b` als `float32 (32, 54)` und 16 globale Merkmale. `extract_track.py` berechnet und cached Volltrackmerkmale, `vocal.py` trennt mit HT Demucs einmal pro Song einen wiederverwendbaren Vocal-Stem, `global_pair.py` erzeugt Tempo-, lokale Key-/Harmonie- und Kontextwerte. `dataset_export.py` wählt gerankte Vier-Takt-Kandidaten, wendet Trainingsausschlüsse an, bildet Audio-SHA-getrennte Splits, fitttet Flux-/Onset-Normalisierung nur auf Trainingsartefakten und exportiert atomar NPZ/JSONL mit vollständiger Provenienz. Phrasenkanäle bleiben mit `phrase_valid = 0` deaktiviert. Verträge: `FEATURE_PROTOCOL.md`, `DATASET_PROTOCOL.md`, `PRETRAINED_MODELS.md`.
- **Metrik für gerenderte Übergänge** (`src/ranking/rendered_transition.py`): `rendered_transition_baseline_v1` bewertet nach dem Rendering das tatsächliche Audio inklusive Time-Stretch und Crossfade. Energieform und Grenzglätte zählen je 30 %, harmonische Kontinuität und rhythmische Stabilität je 20 %. Score, Teilwerte, Messwerte, Rang und isolierte Fehler stehen additiv im Batch-Manifest.
- **Differenzierbarer Control-Prototyp** (`src/control/`): `differentiable_control_v3` rendert vier Takte aus zwei komplementären, konstruktiv monotonen Kurven (`mix_position`, `low_end_position`) mit Equal-Power-Gains und festem FIR-Crossover. Bei 32 Punkten ist jeder Halbbeat-Schritt konstruktiv kleiner als 0,099644; normalisierte Abweichungs- und Krümmungsterme bestrafen abrupte Übergaben. Frei parametrisierte Kurven können vor einem neuronalen Netz direkt optimiert werden; der Vertrag steht in `DIFFERENTIABLE_CONTROL_PROTOCOL.md`.
- **Reale Control-Vergleiche** (`src/evaluation/control_probe.py`): wählt aus einem nachbewerteten Multi-Song-Batch hoch bewertete 4-Takt-Kandidaten, rekonstruiert Source-Postroll und Target-Preroll, optimiert die zwei Control-Kurven und exportiert pro Paar Baseline/Optimiert mit identischem Kontext, gemeinsamer Peak-Absenkung und versioniertem Manifest. Der aktuelle blinde v3-Control-Satz mit Rubber Band liegt unter `output/control_studies/blind_v4_control_v3_rubberband_top8_4bar_20260730/`; frühere v1/v2-Versuche bleiben unverändert.
- **Blinde Control-Hörstudie** (`src/evaluation/blind_control_study.py`, `control_study_ratings.py`, `analyze_control_study.py`): erzeugt A/B-Dateien ohne Methodenlabel, trennt den unveränderlichen Antwortschlüssel vom öffentlichen Manifest, speichert Ratings atomisch und entblindet erst nach vollständiger Bewertung in ein reproduzierbares `study_results.json`. Vertrag: `CONTROL_STUDY_PROTOCOL.md`.
- **Historische Render-Metrik** (`src/evaluation/backfill_transition_metrics.py`): bewertet vorhandene Multi-Song-Batches ohne Änderung der WAVs oder ursprünglichen Manifeste. Samplegenaue Grenzen werden aus Kandidaten-Beat-Index, Read-only-Analyse-Cache und Tempoanpassung rekonstruiert; atomische `transition_metrics.json`-Sidecars dokumentieren Fortschritt und Ergebnisse.
- **Songpaar-Kompatibilität** (`src/ranking/song_compatibility.py`): `rank_song_targets()` ordnet Target-Songs pro Source-Song vor der Cutpoint-Generierung nach Harmonie, Tempoanpassungsstärke, Klang, Energie und Rhythmus.
- **Batch-Rendering** (`src/batch_render.py`): rankt akzeptierte Kandidaten und rendert standardmäßig die Top 5 × ausgewählte Renderer als kurze WAV-Vorschauen (5 s vor, 12 s nach Source-Cutpoint). Exporte werden atomar geschrieben; vorhandene Dateien werden ohne explizites `--overwrite` nicht ersetzt. Gescheiterte Einzelvarianten sowie Generator- und Ranking-Rejections bleiben im Manifest sichtbar. Seit 2026-07-22 übernehmen alle Renderer die Source-/Target-BPM explizit aus dem Kandidatenvertrag und passen Song B konsistent auf Song A an.
- **Hörbewertung und Visualisierung** (`src/evaluation/ratings.py`, `notebooks/listen_batch.ipynb`): das Notebook listet Varianten in Rangfolge, zeigt für den umgebenden Multi-Song-Batch die Render-Score-Verteilung sowie Cutpoint-gegen-Render-Score und hebt das aktuelle Songpaar hervor. Pro Hörprobe werden die Source- und Target-Waveform an ihren jeweiligen Cue Points bei `t = 0` ausgerichtet untereinander sowie Gesamtscore und vier Render-Metrikkomponenten visualisiert. WAVs werden über `IPython.display.Audio` eingebettet. `rate()` speichert eine 1–5-Bewertung mit Fehler-Tags und Notiz atomar in einer getrennten `ratings.json`; dieselbe Funktionalität ist als CLI verfügbar. Der Startpfad verweist auf ein nachbewertetes reales Songpaar.
- **Dataset und Ausschlüsse**: 21 Audiodateien liegen im ignorierten Ordner `musik/`; für alle 21 existiert eine gecachte Analyse unter `output/pre_analysis/` (plus ein veralteter zusätzlicher Cache `HELP_LESS`). `config/track_exclusions.json` schließt `14 - STRUGGLING.flac` per Pfad und SHA-256 aus neuen Multi-Batches, Control-Vergleichen und Training aus; historische Artefakte bleiben unverändert. Ein reproduzierbarer Feature-Datensatz mit 45/9/9 Beispielen liegt unter `output/datasets/feature_protocol_v1_top3_4bar_track_split_20260731/`. Kuratierte Track-Notizen und Lizenzstatus fehlen weiterhin.

### Verifiziert am 2026-07-30 (Codex, Feature-Protokoll 1)

- Kanonische Modellinputs: pro Track **32 Halbbeat-Schritte × 54 skalare
  Features**, dazu **16 globale Features**. Die Dimensionen entstehen aus
  stabil benannten Gruppen und nicht aus einer vorgegebenen 64er-Zielgröße.
- Die Vocal-Gruppe enthält `vocal_activity`, `vocal_prominence`,
  `vocal_onset_probability`, `vocal_offset_probability`,
  `vocal_phrase_progress` und `vocal_confidence`; `vocal_valid` trennt
  fehlende Analyse von tatsächlich inaktivem Gesang.
- Phrasenmerkmale beziehen sich auf erkannte 8-Takt-Phrasen. Ein
  `bar_index modulo 8`-Fallback ist ausdrücklich nicht als gültige
  Phrasenerkennung erlaubt.
- Target-Features werden auf genau der tempoangepassten Waveform berechnet,
  die der Renderer verwendet. Richtung und Betrag der Tempoänderung sind
  globale Inputs; der Backendname bleibt Dataset-Provenienz.
- Shape, dtype, endliche Werte, Wertebereiche und binäre Masken werden durch
  `src.features` validiert. Vocal-/Phrasen-Extractor und Datasetexport sind
  noch offen.
- `.venv\Scripts\python.exe -m pytest -q`: **59 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Volltrack-Featurecache v1)

- Hashbasierte Cacheeinträge enthalten Volltrack-Basiskanäle,
  Halbbeat-Samplegrenzen und rohe Flux-/Onset-Kanäle. Audioänderung,
  Beat-Grid, Ziel-BPM, Sample-Rate oder Protokoll-/Extractor-Version ändern
  den Cache-Key.
- Source-Postroll und Target-Preroll werden als `(32, 54)` aus einem
  Volltrack-Artefakt geschnitten. Erst dabei werden
  `transition_position`, Flux und Onset mit Trainingssplit-Statistiken
  vervollständigt und gegen Feature-Protokoll 1 validiert.
- Reale Sonde `GHOST`: **990 Halbbeat-Bins × 54 Kanäle**; erster Lauf
  `cache_hit = false`, unmittelbar wiederholter Lauf `cache_hit = true` auf
  demselben Artefakt. Kein Time-Stretch war nötig.
- Vocal und Phrase stehen im Cachemanifest auf `not_implemented`;
  `vocal_valid = phrase_valid = 0` verhindert eine Verwechslung mit
  tatsächlich inaktiven Signalen.
- Aus dem realen GHOST-Cache wurden ohne Neuberechnung gültige Source- und
  Target-Fenster mit Shape `(32, 54)` und ausschließlich endlichen Werten
  geschnitten.
- `.venv\Scripts\python.exe -m pytest -q`: **65 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, HT-Demucs-Vocalcache v1)

- Demucs `4.1.0` läuft mit der vorhandenen Python-3.14-/Torch-2.13-CPU-Umgebung.
  Verwendet wurde `htdemucs` aus `adefossez/HTDemucs`, Revision
  `bf35a81b663819a8255c8fefee17f9d812b786b5`; der SHA-256 der
  `955717e8.safetensors`-Gewichte ist
  `d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd`.
- Reale Sonde `GHOST`: Der erste Lauf erzeugte einen persistenten Vocal-Stem
  und ein neues Featureartefakt mit **990 × 54** Werten. Der
  Vocal-Aktivitätsscore reicht von rund `1,87e-7` bis `0,9971`;
  `vocal_valid` ist in allen vollständigen Bins eins.
- Der unmittelbar wiederholte CLI-Lauf verwendete das vorhandene
  Featureartefakt mit `cache_hit = true`; weder Separation noch
  Volltrack-Features wurden erneut berechnet.
- Das Manifest enthält Demucs-Version, Modellname, Hub-Revision,
  Gewichtsdatei-Hashes, Vocal-Stem-Hash und die zitierfähigen Paper-Metadaten.
  BibTeX: `docs/REFERENCES.bib`.
- `.venv\Scripts\python.exe -m pytest -q`: **67 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-31 (Codex, globale Features und Datasetformat 1)

- `global_pair_v1` erzeugt alle **16** Vertragswerte: fünf Tempowerte,
  lokale Tonika/Modus/Confidence für A und B, harmonische Kompatibilität und
  Abdeckung des acht Takte breiten Cue-Kontexts. Fehlende tonale Evidenz ist
  explizit Confidence null und Kompatibilität neutral `0,5`.
- Aus 60 historischen Paarmanifesten wurden 165 gerankte Vier-Takt-Beispiele
  ausgewählt. Die Trainingspolicy entfernte neun Beispiele mit `STRUGGLING`;
  die strikt track-getrennte Zuordnung verwarf weitere 93 kreuzende Paare.
- Finaler Datensatz: `dataset_id = f9044dc259b7296c8b28`, **63 eindeutige
  Beispiele** in **45 Train / 9 Validation / 9 Test**. Die Trackzuordnung ist
  12/2/3 über 17 vorkommende erlaubte Audio-Hashes; `TIME_LESS` ist zwar dem
  Trainingssplit zugeordnet, kommt nach Cross-Split-Filterung aber in keinem
  exportierten Beispiel vor.
- Shapes sind Train `(45,32,54)/(45,32,54)/(45,16)`, Validation und Test je
  `(9,32,54)/(9,32,54)/(9,16)`. Alle Werte sind endlich, alle exportierten
  Source-/Targetfenster haben `vocal_valid = 1`, 63 Example-IDs sind eindeutig
  und kein Audio-Hash liegt in mehreren Splits.
- Flux-/Onset-Statistiken wurden ausschließlich aus verwendeten
  Trainingsartefakten gefittet (`stats_id = train-d361f7da6414a9e6`). Die
  SHA-256-Werte aller fünf Datasetdateien wurden gegen das Manifest geprüft.
- `.venv\Scripts\python.exe -m pytest -q`: **72 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Control-/Objective-v3 und neuer Hörsatz)

- Control-Protokoll 3 beschränkt die Inkrement-Logits konstruktiv auf
  `0.6 · tanh(logit)`. Für 32 Kontrollpunkte beträgt die theoretische
  Obergrenze eines Kurvenschritts **0,0996431**; Endpunkte 0/1 und strenge
  Monotonie bleiben erhalten.
- Das Objective bewertet die Abweichung vom gleichmäßigen Inkrement und die
  Änderung aufeinanderfolgender Inkremente nun skalenunabhängig. Equal Power
  hat für beide neuen Formterme den Wert null.
- `output/control_studies/blind_v4_control_v3_rubberband_top8_4bar_20260730/`
  enthält dieselben acht gerichteten Songpaare wie der bewertete v2-Satz,
  vollständig neu als **16 Float32-WAVs**, 44,1 kHz Stereo, paarweise gleiche
  Länge, endliche Samples und ohne Exportfehler.
- `FALLING → Aversion` und `FALLING → HELP_LESS` wurden über
  `ffmpeg_librubberband` tempoangepasst. Die sechs BPM-identischen Paare
  dokumentieren `not_needed`; `STRUGGLING` kommt nicht vor.
- Der öffentliche Satz enthält keine Methodenabbildung, `ratings.json` steht
  nach der Hörbewertung auf **8/8**. Erst danach wurde `answer_key.json`
  geöffnet und `study_results.json` erzeugt. Da dieselben acht früheren
  Urteile v3 mitmotiviert haben, ist dieser Satz ein kontrollierter
  Vorher-/Nachher-Vergleich, kein unabhängiger Testsatz.
- Ergebnis: **8 Gleichstände**, keine Präferenz für Baseline oder Optimiert.
  Beide Methoden erreichen denselben Gesamtmittelwert **4,45** und identische
  Kriterienmittel: Sauberkeit 4,25; Energieform 4,50; Low-End 4,625;
  Rhythmik 4,50; Artefaktfreiheit 4,375. Der Proxy-Loss sank je Paar trotzdem
  um 2,39–36,43 %, ohne einen erkennbaren Methodenunterschied zu erzeugen.
- Gemeinsame Fehler beider Methoden: unterbrochene Lyrics, zurückkehrende
  Source-Melodie, Vocal-Clash und ein schlecht klingendes Target in Paar 5.
  Dort wurde Aversion per `ffmpeg_librubberband` von 161,499 auf 156,605 BPM
  verlangsamt (−3,03 % Tempo); beide A/B-Varianten verwenden dieselbe
  gestretchte Waveform.
- `.venv\Scripts\python.exe -m pytest -q`: **54 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Rubber-Band-Time-Stretch)

- Der installierte FFmpeg-8.1-Build stellt den Filter `rubberband` bereit; die
  verfügbaren Optionen einschließlich `channels=together` wurden über
  `ffmpeg -hide_banner -h filter=rubberband` verifiziert.
- Eine reale Prozesssonde verarbeitete synthetisches 44,1-kHz-Stereo-Audio
  über `ffmpeg_librubberband` bei Faktor 1,1 zu exakt 80.182 Samples,
  Float32, endlichen Werten und zwei Kanälen.
- Das eigenständige `rubberband`-CLI ist lokal derzeit nicht installiert.
  Priorität, R3-Aufruf, inverses Zeitverhältnis und Fallback wurden deshalb
  mit isolierten Prozessdoubles getestet; ein fehlendes zweites Backend
  erscheint mit beiden Schrittursachen statt als stiller Librosa-Fallback.
- Rendering-Protokoll 5 und neue Batch-Manifeste führen
  `tempo_backend`; historische Version-4-Artefakte bleiben unverändert.
- `.venv\Scripts\python.exe -m pytest -q`: **52 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-30 (Codex, Auswertung blinder v3-Hörsatz)

- `ratings.json` enthält **8/8** vollständige Urteile einer Person. Erst danach wurde `answer_key.json` geöffnet und `study_results.json` erzeugt.
- Präferenzen: **Equal-Power-Baseline 4, optimierte Proxy-Kurve 3, Gleichstand 1**. Ohne Gleichstand entspricht das 57,1 % zu 42,9 %.
- Gesamtmittel über fünf Kriterien: Baseline **4,325**, Optimiert **4,250**. Optimiert minus Baseline: Sauberkeit 0,000, Energieform −0,125, Low-End-Übergabe 0,000, rhythmische Stabilität 0,000, Artefaktfreiheit −0,250.
- Interpretation: v2 liegt hörend nahe an der starken Baseline und der eindeutige v1-Fehler ist behoben, aber eine konsistente Verbesserung durch das aktuelle Proxy-Objective ist nicht belegt. Die Notizen markieren insbesondere abrupte Melodie-/Gain-Übergaben, Vocal-Timing, Time-Stretch-Artefakte und eine nicht erfasste 8/4-Phrasengrenze.
- Einschränkung: ein Rater, acht gezielt ausgewählte Paare, keine unabhängige Zufallsstichprobe; eine 5 bedeutet „kein negativer Punkt aufgefallen“, nicht Perfektion.
- `.venv\Scripts\python.exe -m pytest -q`: **49 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten.

### Verifiziert am 2026-07-29 (Codex, blinder v3-Hörsatz)

- `output/control_studies/blind_v3_top8_4bar_20260729/` enthält **8 unterschiedliche gerichtete Paare / 16 WAVs**, ausschließlich `A.wav`/`B.wav`, 44,1 kHz Stereo, paarweise identische Dauer, endliche Samples und keine Exportfehler.
- `STRUGGLING` kommt nicht vor; kein Track wird häufiger als zweimal verwendet. Das öffentliche `manifest.json` enthält keine Methodenabbildung. `answer_key.json` liegt separat; `ratings.json` war zum Exportzeitpunkt mit **0/8** Bewertungen initialisiert und wurde später vollständig ausgefüllt.
- `.venv\Scripts\python.exe -m pytest -q`: **46 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten.

### Verifiziert am 2026-07-29 (Codex, monotone Controls v2)

- Das menschliche Urteil für v1 war in allen vier Paaren eindeutig zugunsten der Baseline: Song A kam kurz vor dem Ende erneut zurück. Die gespeicherten v1-Kurven bestätigten 4–12 rückwärts laufende Mix-Schritte pro Paar und einen maximalen Einzelschritt von −0,468.
- Control-Protokoll 2 parametrisiert nur noch positive, per Softmax auf Summe 1 normierte Inkremente. Alle acht v2-Kurven (`mix_position` und `low_end_position` über vier Paare) haben **0 rückwärts laufende Schritte**, beginnen exakt bei 0 und enden exakt bei 1.
- Unter `output/control_comparisons/batch_20260722_top4_4bar_v2_monotone/` liegen acht neue WAVs, 44,1 kHz Stereo, paarweise identische Länge, endliche Samples und keine Exportfehler. Der Proxy-Loss sank weiterhin um 19,6 %, 72,9 %, 55,0 % und 57,4 %.
- Nutzerurteil: v2 klingt bereits besser; `STRUGGLING → ASCENSION` ist wegen des Tempo-Ausreißers kein gültiger Metrikvergleich und wird künftig ausgeschlossen. Eine erneute read-only Auswahl ersetzt das Paar durch `Frontliner - Tell Me → FALLING`.
- `.venv\Scripts\python.exe -m pytest -q`: **43 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. Ausschluss greift verifiziert in den Scopes `multi_batch`, `control_probe` und `training`.

### Verifiziert am 2026-07-29 (Codex, reale Control-Vergleiche)

- Vier unterschiedliche hoch bewertete 4-Takt-Paare aus dem Batch vom 22.07 wurden verarbeitet: `GHOST → REBIRTH`, `LESS_IS_MORE → HELP_LESS`, `STRUGGLING → ASCENSION` und `Aversion → The Sky`.
- **8/8 WAVs**, 44,1 kHz Stereo, paarweise identische Länge, endliche Samples, keine Exportfehler. Der Proxy-Loss sank um 24,1 %, 97,2 %, 60,7 % und 69,6 %.
- Die historische Render-Metrik bevorzugte Optimiert bei zwei Paaren und Baseline bei zwei Paaren; die Differenzen waren klein. Das menschliche Hörurteil verwarf Optimiert jedoch in allen vier Paaren wegen rückwärts laufender Übergaben. Dieser v1-Lauf ist damit ein dokumentierter Fehlschlag und Motivator für Protokoll 2.
- `.venv\Scripts\python.exe -m pytest -q`: **40 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`. `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten.

### Verifiziert am 2026-07-29 (Codex, differenzierbare Controls)

- PyTorch 2.13.0 CPU ist unter Python 3.14.2 installiert und in `requirements.txt` festgehalten.
- Die synthetische Direktoptimierung senkte den Proxy-Loss in 40 Schritten von 0,2191 auf 0,1049 (**−52,1 %**). Das belegt einen funktionierenden Gradientenpfad, noch keine hörbare Qualität.
- `.venv\Scripts\python.exe -m pytest -q`: **39 Tests bestanden**; zwei bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-07-29 (Codex, Cue-Point-Waveforms)

- `notebooks/listen_batch.ipynb` wurde mit dem realen, nachbewerteten Paar `05_HELP_LESS → 07_BREATH_LESS` vollständig headless ausgeführt. `play(index)` erzeugt für Source A und Target B zwei übereinanderliegende Waveform-Plots mit gemeinsamer relativer Zeitachse, markiert beide Cue Points bei `t = 0` und zeigt danach weiterhin Metrikkomponenten und Audio-Player. Die Bildausgabe wurde stichprobenartig visuell geprüft.

### Verifiziert am 2026-07-27 (Codex, Metrikvisualisierung)

- `notebooks/listen_batch.ipynb` wurde mit dem realen, nachbewerteten Paar `05_HELP_LESS → 07_BREATH_LESS` vollständig headless ausgeführt. Die Übersicht aggregiert alle 165 bewerteten Varianten des umgebenden Multi-Song-Batches; Komponentenbalken und Audio-Player wurden ohne Fehler erzeugt. Beispielbewertungen werden beim Ausführen nicht automatisch gespeichert.
- Matplotlib 3.11.1 ist für Python 3.14 in `requirements.txt` festgehalten.

### Verifiziert am 2026-07-23 (Codex, nach Render-Metrik-Meilenstein)

- Multi-Song-Batch: `output/batches/all_songs_top3_targets_top3_transitions_20260722/`; für alle 20 aktuellen Tracks wurden die drei global kompatibelsten Zieltracks ausgewählt und pro Songpaar bis zu drei Equal-Power-Übergänge gerendert. Ergebnis: 60 abgeschlossene Paar-Manifeste, 165 WAV-Vorschauen, keine Runner- oder Renderfehler. `src.multi_batch_render` schreibt das Auswahl- und Fortschrittsmanifest nach jedem Songpaar atomar fort; Wildcards wie `musik\*.flac` werden auf Windows intern aufgelöst.
- Derselbe Multi-Song-Batch wurde am 2026-07-23 vollständig mit `rendered_transition_baseline_v1` nachbewertet: **165/165 Varianten aus 60/60 Paaren, 0 Fehler**. Scorebereich 0,569–0,943, Mittelwert 0,857, Median 0,883. Komponentenmittel: Energieform 0,817, Grenzglätte 0,900, harmonische Kontinuität 0,961, rhythmische Stabilität 0,749. Ergebnisse liegen als unveränderliche Sidecar-Auswertung unter `transition_metrics.json`.
- Python-Version der Projektumgebung: **3.14.2**.
- `.venv\Scripts\python.exe -m pytest -q`: **35 Tests bestanden**; zwei nicht blockierende Deprecation-Warnungen aus `audioread` unter Python 3.14.
- Synthetische Kontrolle: Die Render-Metrik bevorzugt eine glatte Bridge mit abgesenkter Energie gegenüber einem gleichförmig lauten Übergangsfenster; eine fehlerhafte Variante blockiert die übrigen Scores nicht. Reale Hörvalidierung und Gewichtsabstimmung stehen bewusst noch aus.
- Read-only-Stichprobe auf dem vorhandenen Equal-Power-Rang-1 aus `help_to_breath_drop_bridge`: Gesamtscore 0,807; Energieform 0,516, Grenzglätte 0,929, harmonische Kontinuität 0,968 und rhythmische Stabilität 0,902; keine Metrikfehler. Das ist nur ein technischer Plausibilitätscheck, noch kein Qualitätsnachweis.
- `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten; `pytest 9.1.1` ist installiert und in `requirements-dev.txt` festgehalten.
- CLI und programmatischer Import laufen; verfügbare Renderer: `simple`, `fade`, `equal_power`, `tempo_fade`; alle gleichen dabei das Tempo an.
- `generate_transition_candidates()` erzeugt Kandidaten auf demselben normalisierten 44,1-kHz-Sample-Raster wie die Renderer; ein Integrationstest deckt 48→44,1-kHz-Cutpoint-Skalierung ab.
- Batch-Export testet WAV-Dateien, Manifest-Inhalt, Renderer-/Kandidaten-Rückverfolgbarkeit und den Schutz vor unbeabsichtigtem Überschreiben.
- Erster realer Batch: `output/batches/help_to_breath_first/`, Songpaar `05 - HELP_LESS.flac` → `07 - BREATH_LESS.flac`; ein 2-Takt-Kandidat (`candidate-6a5d9f74efd4ad1f`, beide 161,499 BPM) wurde als linearer und Equal-Power-Crossfade exportiert. Zwei 44,1-kHz-Stereo-WAVs à 63.102.084 Bytes, keine Rejections und keine Renderfehler.
- Erster realer Ranking-Lauf: `output/batches/help_to_breath_ranked/`; 48 Kandidaten aus 4×4 Taktgrenzen und 1/2/4 Takten wurden bewertet, die Top 3 als Equal-Power-WAV exportiert. Rang 1 ist `candidate-33640deded712342` mit Score 0,845; keine Ranking- oder Renderfehler. Noch keine menschlichen Bewertungen.
- High-Power-Ranking-Lauf: `output/batches/help_to_breath_high_power/`; 736 Kandidaten aus den letzten vier Source-Grenzen, allen nutzbaren Target-Grenzen und 2/4 Takten wurden bewertet, die globalen Top 3 als Equal-Power-WAV exportiert. Rang 1 (`candidate-a39b3732c9444fb6`, Score 0,927) verbindet Source-Takt 112 mit Target-Takt 65 bei 91,60 s; Source/Target liegen bei −5,33/−5,47 dB statt Target-Intro bei ungefähr −16 dB. Da die globalen Top 3 alle 2 Takte verwenden, exportiert `output/batches/help_to_breath_high_power_4bar/` zusätzlich den besten 4-Takt-Kandidaten (`candidate-966e75d1a240fc27`, Score 0,919, Target-Takt 63). Keine Ranking- oder Renderfehler; menschliche Hörbewertung offen.
- Drop-Bridge-Lauf: `output/batches/help_to_breath_drop_bridge/`; 14.196 kompatible Kandidaten aus allen nutzbaren Grenzen wurden mit `feature_baseline_v3` bewertet, die Top 3 als Equal-Power-Bridge nach Rendering-Protokoll 2 exportiert. Rang 1 (`candidate-5f8a2a500211a427`, Score 0,751) verbindet Source-Takt 50 (74,47 s) über 4 Takte mit Target-Takt 109 (157,52 s): nach Drop A fällt RMS um 3,36 dB auf −9,02 dB, vor Drop B liegt der Vorlauf bei −13,11 dB und der Anstieg beträgt 6,54 dB. Keine Ranking- oder Renderfehler; Hörurteil offen.
- Multi-Paar-Batch: `output/batches/all_music_adjacent_equal_power_20260721/`; 18 aufeinanderfolgende gerichtete Paare aus 19 Tracks wurden verarbeitet, `Deezl - BREATH_LESS.flac` wurde ausgeschlossen. Sechs Paare lieferten jeweils die Top 5 als Equal-Power-WAVs (30 WAVs insgesamt), zwölf Paare hatten wegen der harten Kandidatenfilter keine akzeptierten Kandidaten. Alle 18 Manifeste wurden geschrieben; es gab keine Renderfehler.
- `aufTAKTCl.exe` und `tmp/` sind lokal vorhanden. `ffmpeg 8.1` ist über `PATH` auflösbar und wurde mit `ffmpeg -version` erfolgreich ausgeführt. Eine vorherige Prüfung innerhalb der eingeschränkten Codex-Dateisandbox lieferte wegen fehlendem Zugriff auf das WinGet-Paketverzeichnis fälschlich „nicht gefunden“.
- Reales Entwicklungsset gemessen: 20 Tracks mit 44,1 kHz Stereo, ein Track mit 48 kHz Stereo.
- Bereits vorhanden: `output/combined_song.wav` (375,84 s) und `output/cut_song.wav` (214,70 s), beide 44,1 kHz Stereo. Das ist noch kein systematischer Batch-Vergleich.

## Abgleich mit dem geplanten Systemablauf

| Komponente aus dem Exposé | Umsetzungsstand | Nachweis / Lücke |
|---|:--:|---|
| 1. Audioimport & Abschnittsauswahl | 🟡 | Zwei Audiodateien können verarbeitet werden; Abschnittsgrenzen sind manuelle Sample-Cutpoints. Mehrere Songs, Abschnittsobjekte und Reihenfolge-Constraints fehlen. |
| 2. Musikanalyse | 🟡 | BPM, Beats, Downbeats und Taktpositionen sind vorhanden. Phrasen-/Segmentgrenzen, Strukturtypen, Vocal-Aktivität und eine plattformunabhängige Downbeat-Lösung fehlen. |
| 3. Kandidatengenerierung | 🟡 | Bar-synchrone 2/4-Takt-Kandidaten über beide vollständigen Tracks mit vier vollständigen Drop-/Bridge-Fenstern vorhanden. Phrasen/Struktur und Vocal-Filter fehlen noch. |
| 4. Übergangsmetrik | 🟡 | `feature_baseline_v3` rankt Cutpoints vorab; `rendered_transition_baseline_v1` bewertet danach das tatsächliche Renderergebnis. Phrasen, Vocals, Embeddings und menschliche Evaluation fehlen. |
| 5. Rendering | ✅ | Hard Cut sowie lineare und Equal-Power-Bridge-Renderer sind implementiert und gleichen das Tempo immer an; ein Test garantiert, dass Drop A/B außerhalb des Mischfensters bleiben. |
| 6. Vorschau & Export | 🟡 | Batch-WAV-Export, auditierbares Manifest, Cue-Point-/Metrikvisualisierung und Notebook-Inline-Playback funktionieren. Auswahlworkflow und GUI fehlen. |

Damit ist die technische Grundlage aus Monat 1 weitgehend vorhanden. Das frühe Erfolgskriterium „automatisch erzeugt und systematisch vergleichbar“ ist einschließlich eines ersten blinden Hörvergleichs erfüllt; Feature→Control-Training, weitere Rater und der breitere wissenschaftliche Vergleich aus Monat 2–3 stehen noch aus.

## Fortschritt gegen die Startphase (Exposé Abschn. 13–14)

| Baustein | Status | Kurz |
|---|:--:|---|
| Reproduzierbares Repository | 🟡 | Git, MD-Doku und Requirements-Dateien vorhanden; aufTAKT und ffmpeg funktionieren lokal, sind aber externe Windows-Komponenten und ihre Einrichtung ist noch nicht automatisiert |
| Kleines Entwicklungsset (10–20 Tracks) | 🟡 | 21 lokale Audiodateien + Analyse-Caches vorhanden; Kuratierung, Track-Notizen, Rechte und reproduzierbare Definition fehlen |
| Beat-/Bar-Analyse | ✅ | librosa + aufTAKT-Merge, mit Diskrepanz-Log |
| Mehrere gerenderte Übergänge | 🟡 | Automatischer Batch-Export vorhanden; erster realer 2-Varianten-Lauf HELP_LESS → BREATH_LESS ohne Fehler dokumentiert |
| Automatische Kandidaten | 🟡 | `bar_grid_v1` erzeugt standardmäßig 2/4-Takt-Varianten über alle nutzbaren Downbeats beider Songs; keine Phrasen-/Strukturinformationen |
| Systematischer Vergleich / Höranalyse | 🟡 | Gerankter Batch, Inline-Playback und ein vollständig bewerteter blinder 8-Paar-Hörsatz vorhanden; weitere Rater und ein breiterer Testsatz fehlen |
| Erste Baseline-Renderer (4 Stück) | ✅ | Tempoangepasster Hard Cut, linearer Crossfade, Equal-Power und Kompatibilitätsalias `tempo_fade` getestet |
| Einfache Feature-Metrik | ✅ | `feature_baseline_v3` mit High-Power- und Non-Overlap-Komponente, auditierbaren Messwerten und Top-k-Rendering |
| Render-Audio-Metrik | ✅ | `rendered_transition_baseline_v1` mit vier erklärbaren Komponenten, eigenem Ranking und Fehlerisolation im Batch-Manifest |
| Erste Embedding-Tests | ❌ | offen (Monat 3) |
| Liste typischer Fehlerfälle | 🟡 | nur punktuell (`Bemerkungen.md`) |
| Entscheidung ML-Fokus | ✅ | Self-supervised Feature→Control-Lernen ohne Ground-Truth-Kurven; differenzierbarer Renderer und eingefrorenes Objective als Lernpfad |

## Bekannte Bugs / Baustellen

- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als zusätzliche einfache Baseline bewusst behandeln; alle Renderer verwenden den tonhöhenerhaltenden Rubber-Band-`TimeStretch`.
- **Time-Stretch-Hörvalidierung**: Rubber Band wurde im neuen Hörsatz real verwendet, aber Paar 5 klingt laut Nutzer in beiden Methoden schlecht. Noch offen ist die isolierte Diagnose Originalsegment versus gestretchtes Segment versus musikalisch ungeeignetes Target-Fenster.
- **Downbeat-Fallback**: Bei fehlenden Taktinformationen wird ein approximatives 4/4-Raster aus den Beat-Positionen (oder BPM) erzeugt. Es hält die Pipeline lauffähig, ist aber keine verlässliche Downbeat-Erkennung und sollte im Hörvergleich geprüft werden.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Kandidatengenerierung).
- **Repo-/Cache-Hygiene**: Die früheren Track-Ordner sind im Arbeitsbaum gelöscht; unter `output/pre_analysis/` bleibt ein zusätzlicher veralteter Cache `HELP_LESS` ohne gleichnamigen aktuellen Audio-Stem.

## GUI-Frage: jetzt oder später? (Entscheidung)

**Empfehlung: noch kein echtes GUI — vom Exposé bestätigt** (GUI ist nur Interaktionsschicht; Risiko 15: „GUI-/Audio-Engineering verdrängt den Forschungsbeitrag"). Erst die Pipeline tragfähig machen und billig „sehen & hören" ermöglichen. Ein ausgebautes GUI lohnt sich erst, wenn Kandidaten + Metrik stehen und es einen Workflow gibt, den es einpackt (gerankte Kandidaten durchblättern, probehören, annehmen/verwerfen) — laut Zeitplan Monat 4.

Billiger Zwischenschritt statt GUI: `matplotlib`-Visualisierung (Waveform/Spektrogramm + (Down)Beats + Übergangsfenster) und ein Jupyter-Notebook (oder dünnes Streamlit/Gradio) mit Inline-Playback (`IPython.display.Audio`).

## Next Steps (priorisiert)

Ziel: den neuen Lernkern zuerst als messbare Schleife
**Controls → differenzierbar rendern → Objective → optimieren → anhören**
auf realem Audio validieren.

**Abgeschlossen am 2026-07-17:** programmatische Pipeline, Audio-Normalisierung, vier Rendering-Baselines, versionierter Rendering-Vertrag und automatisierte Tests.

**Abgeschlossen am 2026-07-29:** versionierter differenzierbarer Zwei-Control-Renderer, direkte Kurvenoptimierung sowie acht reale Baseline/Optimiert-WAVs aus vier unterschiedlichen 4-Takt-Paaren mit vollständiger Provenienz.

**Abgeschlossen am 2026-07-30:** acht geblendete v3-Paare vollständig bewertet und erst danach entblindet; v2 liegt nahe an Equal Power, zeigt aber noch keinen konsistenten Vorteil.

**Abgeschlossen am 2026-07-30:** Control-/Objective-v3 begrenzt lokale Kurvensprünge konstruktiv; alle acht Vergleichspaare wurden mit Rendering-Protokoll 5 neu gerendert.

**Abgeschlossen am 2026-07-31:** alle 16 globalen Paarfeatures, atomarer Feature-Datasetexport und SHA-basierte track-getrennte Train/Validation/Test-Splits; realer 45/9/9-Datensatz mit gültigen Demucs-Vocals.

1. **Time-Stretch und Target-Fenster von Paar 5 isolieren** — Original-Targetsegment und Rubber-Band-Variante mit identischem Ausschnitt separat exportieren und hören. So wird unterschieden, ob der schlechte Klang vom Backend, der Tempoänderung oder bereits vom gewählten Aversion-Fenster stammt.
2. **Feature-Protokoll 1 auditieren** — globale Paarfeatures, Datasetexport und track-getrennte Splits sind implementiert. Als Nächstes die Vocal-Scores gegen gehörte Lyrics-/Clash-Fälle prüfen und ein semantisch passendes Phrasenverfahren validieren. Kein stilles 4/4→8-Takt-Fallback.
3. **Direktoptimierung anschließend auf zurückgehaltenen Paaren validieren** — die bekannten acht Urteile nicht als finalen Testsatz verwenden. Equal Power bleibt die starke Referenz; der Gate ist eine wiederholbare hörbare Verbesserung und nicht nur ein niedrigerer Proxy-Loss.
4. **Erst nach bestandenem Hör-Gate MLP-Baseline bauen** — Feature-Protokoll 1, trackweise Train/Validation/Test-Trennung und zunächst ein kleines Feature→Control-MLP verwenden. TCN/BiLSTM erst nach erfolgreicher MLP-Sonde.
5. **Entwicklungsset kuratieren** — die vorhandenen 21 Tracks als reproduzierbares Set definieren, Varianz und Duplikate prüfen, Track-Notizen ergänzen und Lizenzfrage klären (parallel, eher Handarbeit).

Danach: Objective um harmonische/rhythmische Terme erweitern, Mid-/High- und Vocal-Controls additiv einführen und vortrainierte Embeddings auf demselben trackgetrennten Evaluationssatz vergleichen.

## Offene Fragen / Entscheidungen (technisch)

- BPM-/Beat-Grid: was ist maßgeblich, wenn librosa und aufTAKT abweichen (HELP_LESS 161 vs. 157)?
- Übergangslänge: **entschieden am 2026-07-21** — Kandidaten führen sie kanonisch in Takten und leiten die für FadeCut benötigten Beats aus dem analysierten Fenster ab. Offene Folgefrage: Wie sollen spätere Renderer mit wechselndem Metrum umgehen?
- Vocal-Overlap: HT-Demucs-Scores sind verfügbar; offen ist ihre Kalibrierung und ob sie als harter Filter, weiche Metrik-Penalty oder nur als Modelleingang verwendet werden.
- **aufTAKT (Windows-Binary) vs. plattformunabhängiges Downbeat-Tracking** (z. B. madmom) — Reproduzierbarkeit vs. Aufwand.
- Rechte an den Testtracks (HELP_LESS/BREATH_LESS) — eigene Produktion oder lizenzpflichtig? (Exposé Abschn. 8: rechtlich handhabbares Set nötig.)
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?

_Vom Exposé bereits beantwortet: Forschungsfrage, Scope/Abgrenzung, Rolle der GUI, Related-Work-Rahmen, Evaluationsansatz, ML-Priorisierung._
