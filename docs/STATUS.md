# BeatBridge – Stand & Next Steps

_Stand: 2026-08-12_

**Rolle dieser Datei:** Einstieg, verifizierter aktueller Stand und priorisierte
nächste Schritte. Der ausführliche chronologische Experimentlog gehört in
[`Bemerkungen.md`](./Bemerkungen.md); die älteren Verifizierungsblöcke hier
bleiben als Übergangsarchiv erhalten und sind keine zusätzlichen To-do-Listen.
**Maßgeblicher Kontext: [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) (Exposé).** Diese Datei hält den *technischen Prototyp-Stand der Startphase* (Monat 1 / erste 2–3 Wochen) fest. Ziel, Scope, wissenschaftlicher Beitrag, Related Work, Datenstrategie, Evaluation, 6-Monats-Plan und Risiken stehen im Exposé.

**Forschungsfrage (präzisiert am 2026-07-29):** Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue, nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu **bewerten** und zu **erzeugen** — möglichst ohne explizite Annotationen? Wissenschaftlicher Kern ist jetzt das **Lernen zeitabhängiger Mixing-Kurven ohne Ground-Truth-Kontrollkurven**; eine eingefrorene Übergangsmetrik liefert über einen differenzierbaren Renderer das Lernsignal. Compatibility- und Render-Metriken bleiben Baselines und Hilfskomponenten.

**Wichtigstes Erfolgskriterium der Startphase (Exposé Abschn. 14):** Nach spätestens drei Wochen sollen *mehrere automatisch erzeugte* Übergänge *hörbar* sein und *systematisch verglichen* werden können.

Kurzfazit Prototyp: Kandidaten können jetzt aus taktsynchronen Downbeats automatisch erzeugt, als Drop-Ende-A→energiearme Bridge→Drop-Anfang-B vorgerankt, ohne Überlappung der High-Power-Abschnitte gerendert und anschließend anhand des tatsächlichen Renderergebnisses erneut bewertet werden. Objective-v4-optimierte Kurven gewannen den zurückgehaltenen Hörsatz 9/9 gegen Equal Power. Volltrack-Features einschließlich vortrainierter Vocal-Separation, persistente Trainings-Waveform-Caches und die erste kleine Feature→Control-MLP-Baseline samt versioniertem Trainingslauf sind implementiert. Der MLP-Hörvergleich zeigte qualitativ nur geringe Unterschiede und weiterhin Vocal-Overlap beziehungsweise unnatürlich leise eingeblendete Vocals. Deshalb wurden ein stem-fähiger Renderer, Vocal-Control-Modell v2 und Objective v5 mit explizitem Audibility-Loss ergänzt. Im gezielt Vocal-reichen Hörsatz gewinnt Objective v5 zwei Paare gegen einen v4-Sieg und drei Gleichstände; nur die Vocal-Klarheit verbessert sich. Nach dem ersten 45/9-Lauf wurde der Musikbestand auf 119 FLAC-Pfade erweitert und reproduzierbar auf 145–165 BPM gefiltert. Der neue SHA-getrennte Datensatz enthält 370/50/60 Train-/Validation-/Testbeispiele. Der zweite Vocal-v2-Lauf erreicht die beste Validation in Epoche 22 und verbessert den Gesamt-Proxy um 6,14 %, nun auch den alten v4- und Energieanteil. Die Mid-Phrase-Gain-Änderung wird jedoch deutlich schlechter. Ein geblendeter Vergleich des Best-Checkpoints gegen die ungelernte Initialisierung liegt jetzt mit fünf vocal-aktiven Paaren ohne Time-Stretch bereit; die Bewertung ist offen. Die lokale RTX 5070 Ti ist inzwischen über PyTorch 2.13.0+cu130 nutzbar; neue Trainings- und Demucs-Läufe wählen CUDA standardmäßig automatisch.

## Aktueller Stand (implementiert)

- **Projektstruktur / API / CLI**: `src/pipeline.py` bietet `render_transition()` sowie `generate_transition_candidates()` als programmatische Einstiege; argparse deckt weiterhin den einzelnen Render-Export ab. Struktur `src/analysis/`, `src/candidates/`, `src/cutting/`, `src/tempo/`.
- **Audio-I/O**: Laden über `librosa.load`, Export über `soundfile.write`; intern standardmäßig 44,1 kHz Stereo. Abweichende Sample-Raten werden resampelt, Mono wird auf Stereo erweitert und Beat-Positionen werden mit skaliert.
- **Beat-/Bar-Analyse** (`src/analysis/pre_analysis.py`):
  - librosa `beat_track` für BPM + Beats.
  - aufTAKT (`aufTAKTCl.exe`) für Taktposition; Nicht-WAV wird per ffmpeg konvertiert.
  - Merge beider Quellen zu bar-annotierten Beats (`sample, count_in_bar, beats_in_bar`); Abweichungen werden protokolliert.
  - Analyse-Cacheformat 2 unter `v2/<audio-sha256>/<analysis-id>/analysis.json`: kollisionsfrei für gleiche Stems, an Audio und vollständigen Analysevertrag gebunden und atomar geschrieben. Die JSON-Datei enthält BPM, Beats, Grid-Provenienz und Diskrepanzdiagnostik; alte Stem-/Text-Caches bleiben read-only lesbar.
  - Fallback: Wenn aufTAKT fehlt, fehlschlägt oder unvollständige Metadaten liefert, werden die Beat-Positionen als approximatives 4/4-Raster annotiert; ohne Beats wird bei gültigem BPM ein gleichmäßiges Raster erzeugt.
  - Analyseformat 1 trennt seit 2026-08-12 Raster und Herkunft: `grid_source`, `fallback_used`, Backend-Version, Confidence, `analysis_id` und Beat-Grid-Hash werden additiv gespeichert. Alt-Caches ohne Sidecar werden als `legacy_cache_unknown` markiert und nicht nachträglich als erkannt klassifiziert. Verträge: `ANALYSIS_PROTOCOL.md`, `EXTERNAL_TOOLS.md`.
- **Übergänge**:
  - `src/cutting/simple_cut.py`: Hard Cut, Snap auf den nächstgelegenen Downbeat, Bar-Alignment zwischen beiden Songs.
  - `src/cutting/fade_cut.py`: linearer Crossfade über N Beats (Default 8), Bar-aligned.
  - `src/cutting/equal_power_fade_cut.py`: Equal-Power-Crossfade.
  - Alle Renderer passen Song B tonhöhenerhaltend auf BPM von Song A an; `tempo_fade` ist ein Kompatibilitätsalias für den linearen Crossfade.
- **Bridge-Rendering Version 2**: Fade-Renderer erhalten Drop A vollständig bis zum Source-Cut, mischen ausschließlich Source-Postroll mit Target-Preroll und beginnen Drop B exakt am Target-Cut. Die beiden High-Power-Abschnitte liegen dadurch außerhalb des überlappenden Fensters.
- **Tempo** (`src/tempo/`): Resample-basierte Variante (`SimpleTempoAdjust`, verändert Tonhöhe) und tonhöhenerhaltender `TimeStretch` über Rubber Band. Primär läuft FFmpegs `rubberband`-Filter mit gemeinsamem Stereo; bei Fehlern folgt das eigenständige Rubber-Band-CLI mit R3-Engine. Der frühere Librosa-Phase-Vocoder ist nicht mehr im Produktionspfad.
- **Tests**: `pytest`-Suite mit synthetischen Audiodaten prüft alle vier Renderer, FFmpeg-Priorität, Rubber-Band-CLI-Fallback, Float32-Zwischenformat, Tempoanpassung, 48→44,1-kHz-Resampling, Mono→Stereo und den Fehlerpfad bei fehlenden Downbeat-Metadaten.
- **Kandidatengenerierung** (`src/candidates/`): versionierter Vertrag `CANDIDATE_PROTOCOL.md` und Generator `bar_grid_v1`. Er kombiniert standardmäßig alle nutzbaren Taktgrenzen beider Songs für 2/4 Takte; nachweislich erkannte Downbeat-Herkunft, vollständige Downbeat-Metadaten, Pre-/Post-Roll auf beiden Seiten, kompatible Beatanzahl in allen vier Fenstern und maximal 15 % Tempoabweichung sind harte Filter. `approximate_grid_policy = reject|allow` ist standardmäßig strikt; neue Kandidaten und Manifeste tragen Source-/Target-Grid-Provenienz.
- **Feature-Ranking** (`src/ranking/`): `feature_baseline_v3` bewertet Drop A, Source-Auslauf, Target-Vorlauf und Drop B getrennt. Je 30 % entfallen auf High Power der Drops und Non-Overlap (Energieabfall nach A, niedrige Transition-Energie, Energieanstieg vor B); Chroma, RMS-Kontinuität, Spektrum und Tempo ergänzen den Score.
- **Featurevertrag, globale Paarfeatures und Datasetexport** (`src/features/`): Feature-Protokoll 1 definiert `features_a/features_b` als `float32 (32, 54)` und 16 globale Merkmale. `extract_track.py` berechnet und cached Volltrackmerkmale, `vocal.py` trennt mit HT Demucs einmal pro Song einen wiederverwendbaren Vocal-Stem, `global_pair.py` erzeugt Tempo-, lokale Key-/Harmonie- und Kontextwerte. `dataset_export.py` wählt gerankte Vier-Takt-Kandidaten, wendet Trainingsausschlüsse an, bildet Audio-SHA-getrennte Splits, fitttet Flux-/Onset-Normalisierung nur auf Trainingsartefakten und exportiert atomar NPZ/JSONL mit vollständiger Provenienz. Phrasenkanäle bleiben mit `phrase_valid = 0` deaktiviert. Verträge: `FEATURE_PROTOCOL.md`, `DATASET_PROTOCOL.md`, `PRETRAINED_MODELS.md`.
- **Metrik für gerenderte Übergänge** (`src/ranking/rendered_transition.py`): `rendered_transition_baseline_v1` bewertet nach dem Rendering das tatsächliche Audio inklusive Time-Stretch und Crossfade. Energieform und Grenzglätte zählen je 30 %, harmonische Kontinuität und rhythmische Stabilität je 20 %. Score, Teilwerte, Messwerte, Rang und isolierte Fehler stehen additiv im Batch-Manifest.
- **Differenzierbarer Control-Prototyp** (`src/control/`): `differentiable_control_v3` rendert vier Takte aus zwei komplementären, konstruktiv monotonen Kurven (`mix_position`, `low_end_position`) mit Equal-Power-Gains und festem FIR-Crossover. Bei 32 Punkten ist jeder Halbbeat-Schritt konstruktiv kleiner als 0,099644; normalisierte Abweichungs- und Krümmungsterme bestrafen abrupte Übergaben. Objective Version 4 ergänzt gültigkeitsmaskierte Vocal-Overlap-, Vocal-Onset/-Offset-Grenz- und Transientenartefakt-Terme aus den gespeicherten Featurefenstern. Frei parametrisierte Kurven können vor einem neuronalen Netz direkt optimiert werden; der Vertrag steht in `DIFFERENTIABLE_CONTROL_PROTOCOL.md`.
- **Reale Control-Vergleiche** (`src/evaluation/control_probe.py`): wählt aus einem nachbewerteten Multi-Song-Batch hoch bewertete 4-Takt-Kandidaten, rekonstruiert Source-Postroll und Target-Preroll, optimiert die zwei Control-Kurven und exportiert pro Paar Baseline/Optimiert mit identischem Kontext, gemeinsamer Peak-Absenkung und versioniertem Manifest. Der aktuelle blinde v3-Control-Satz mit Rubber Band liegt unter `output/control_studies/blind_v4_control_v3_rubberband_top8_4bar_20260730/`; frühere v1/v2-Versuche bleiben unverändert.
- **Blinde Control-Hörstudie** (`src/evaluation/blind_control_study.py`, `control_study_ratings.py`, `analyze_control_study.py`): erzeugt A/B-Dateien ohne Methodenlabel, trennt den unveränderlichen Antwortschlüssel vom öffentlichen Manifest, speichert Ratings atomisch und entblindet erst nach vollständiger Bewertung in ein reproduzierbares `study_results.json`. Vertrag: `CONTROL_STUDY_PROTOCOL.md`.
- **Historische Render-Metrik** (`src/evaluation/backfill_transition_metrics.py`): bewertet vorhandene Multi-Song-Batches ohne Änderung der WAVs oder ursprünglichen Manifeste. Samplegenaue Grenzen werden aus Kandidaten-Beat-Index, Read-only-Analyse-Cache und Tempoanpassung rekonstruiert; atomische `transition_metrics.json`-Sidecars dokumentieren Fortschritt und Ergebnisse.
- **Songpaar-Kompatibilität** (`src/ranking/song_compatibility.py`): `rank_song_targets()` ordnet Target-Songs pro Source-Song vor der Cutpoint-Generierung nach Harmonie, Tempoanpassungsstärke, Klang, Energie und Rhythmus.
- **Batch-Rendering** (`src/batch_render.py`, `src/multi_batch_render.py`): rankt akzeptierte Kandidaten und rendert standardmäßig die Top 5 × ausgewählte Renderer als kurze WAV-Vorschauen. Multi-Batches akzeptieren rekursive Musikordner, deduplizieren identisches Audio per SHA-256, filtern optional inklusive BPM-Grenzen und teilen Volltrack-Kompatibilitätsfeatures über alle Quellen. Mehrere Analyseworker verwenden getrennte temporäre aufTAKT-Dateien. Exporte werden atomar geschrieben; vorhandene Dateien werden ohne explizites `--overwrite` nicht ersetzt. Source-/Paarfehler isolieren unabhängige Arbeit und bleiben im finalen Manifest; jeder dort dokumentierte Analyse-, Render- oder Metrikfehler führt anschließend zu CLI-Exit-Code 1. Seit 2026-07-22 übernehmen alle Renderer Source-/Target-BPM explizit aus dem Kandidatenvertrag und passen Song B konsistent auf Song A an.
- **Hörbewertung und Visualisierung** (`src/evaluation/ratings.py`, `notebooks/listen_batch.ipynb`): das Notebook listet Varianten in Rangfolge, zeigt für den umgebenden Multi-Song-Batch die Render-Score-Verteilung sowie Cutpoint-gegen-Render-Score und hebt das aktuelle Songpaar hervor. Pro Hörprobe werden die Source- und Target-Waveform an ihren jeweiligen Cue Points bei `t = 0` ausgerichtet untereinander sowie Gesamtscore und vier Render-Metrikkomponenten visualisiert. WAVs werden über `IPython.display.Audio` eingebettet. `rate()` speichert eine 1–5-Bewertung mit Fehler-Tags und Notiz atomar in einer getrennten `ratings.json`; dieselbe Funktionalität ist als CLI verfügbar. Der Startpfad verweist auf ein nachbewertetes reales Songpaar.
- **Dataset und Ausschlüsse**: 119 FLAC-Pfade liegen rekursiv im ignorierten Ordner `musik/`. `config/track_exclusions.json` schließt `14 - STRUGGLING.flac` aus neuen Multi-Batches, Control-Vergleichen und Training aus. Der neue Batch entfernt zusätzlich ein byteidentisches BREATH_LESS-Duplikat und sechs Tracks unter 145 BPM; keiner lag über 165 BPM. Der erweiterte SHA-getrennte Datensatz enthält 370/50/60 Beispiele über 43/5/7 verwendete Trackhashes. Der historische 45/9/9-Datensatz und frühere Läufe bleiben unverändert. Kuratierte Track-Notizen und Lizenzstatus fehlen weiterhin.
- **ML-Baseline Version 1** (`src/ml/`): `FeatureControlDataset` verbindet die bestehenden Feature-Splits mit unveränderlichen, hashbasiert gecachten Source-/Target-Bridge-Waveforms. `time_shared_mlp_v1` hat 10.394 Parameter, wird auf alle 31 Halbbeat-Intervalle geteilt angewendet und erzeugt über dieselbe konstruktive Control-v3-Transformation zwei gültige Kurven. Die Nullinitialisierung startet exakt bei Equal Power; `self_supervised_batch_loss` rendert variable Audiolängen ohne Padding einzeln und mittelt Objective v4. `self_supervised_train_validation_v1` ergänzt deterministische Seeds, Equal-Power-Epoche 0, atomare Best-/Latest-Checkpoints mit SHA-256, vollständige Loss-History, Early Stopping und vertragsgeprüftes Resume. Resume und Studienexport prüfen den Manifesthash vor dem eingeschränkten `weights_only`-Laden. Vertrag: `ML_CONTROL_MODEL_PROTOCOL.md`.
- **Vocal-Control-Erweiterung Version 2** (`src/control/`, `src/ml/`): `vocal_time_shared_mlp_v2` hat 20.821 Parameter und erzeugt zusätzlich eine monotone Vocal-Übergabe sowie getrenntes Source-/Target-Ducking. `DifferentiableVocalAwareRenderer` verarbeitet gecachte Demucs-Stems separat vom Zwei-Band-Accompaniment. Objective v5 ersetzt die alten mixgebundenen Vocal-Gewichte durch tatsächlichen Stem-Overlap, einen Audibility-Loss gegen unnötig leise aktive Vocals und eine Strafe für Gain-Änderungen mitten in Phrasen. Der Cache v2 speichert Mix und beide samplegleichen Vocal-Stems. `self_supervised_vocal_train_validation_v2` trainiert diese Kette reproduzierbar mit atomaren Checkpoints, Early Stopping, strengem Vertrags-/Hash-Resume und ohne Zugriff auf den Testsplit; Checkpoint-Loads sind auf `weights_only` beschränkt. Vertrag: `VOCAL_CONTROL_MODEL_PROTOCOL.md`.
- **GPU-Ausführung** (`src/torch_device.py`): `auto` wählt für Training und neue Demucs-Separationen CUDA, wenn verfügbar, andernfalls CPU. Der aufgelöste Trainings-Device wird im unveränderlichen Run-Vertrag gespeichert; explizite Overrides bleiben mit `--device cpu` und `--device cuda:<index>` möglich. `requirements-cuda.txt` fixiert den offiziellen CUDA-13.0-Wheel zusätzlich zum plattformneutralen Basis-Requirement.

### Verifiziert am 2026-08-12 (Codex, Multi-Batch-Exitstatus)

- `src.multi_batch_render` verarbeitet unabhängige Sources und Paare trotz
  Einzelfehlern weiter und schreibt das finale Wurzelmanifest weiterhin
  atomar.
- Danach liefert die CLI Exit-Code `1` für dokumentierte BPM-Analyse-,
  Source-, Paar-, Render- oder Render-Metrikfehler. Exit-Code `0` ist auf
  Läufe ohne aufgezeichnete Fehler beschränkt; reguläre Ausschlüsse und
  Duplikate sind keine Fehler.
- CLI-Tests decken Source-/Paarfehler, BPM-Analysefehler, verschachtelte
  Render-/Metrikfehler und den fehlerfreien Exit-0-Fall ab.
- `.venv\Scripts\python.exe -m pytest -q`: **128 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

### Verifiziert am 2026-08-12 (Codex, sichere Checkpoint-Loads)

- Alle vier Produktionspfade für v1-/v2-Resume und Studienexport verwenden
  `torch.load(..., weights_only=True)`; es gibt keinen verbleibenden
  `weights_only=False`-Aufruf unter `src/`.
- Der v1-Runner prüft nun wie v2 den SHA-256 von `latest.pt` gegen
  `manifest.json`, bevor PyTorch die Datei öffnet. Beide Studienloader prüfen
  den manifestierten Best-Checkpoint ebenfalls vor dem Laden.
- Tests verankern den `weights_only`-Parameter an allen vier Loadpfaden und
  weisen manipulierte v1-/v2-`latest.pt` sowie beide `best.pt` vor dem Laden
  ab.
- Alle sechs vorhandenen manifestierten Checkpoints aus den drei realen
  v1-/v2-Trainingsläufen bestanden ihre SHA-256-Prüfung und ließen sich mit
  `weights_only=True` auf CPU laden.
- `.venv\Scripts\python.exe -m pytest -q`: **123 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

### Verifiziert am 2026-08-12 (Codex, Downbeat-Grid-Provenienz)

- `AnalysisResult` ergänzt die bisherigen BPM-/Beat-Tupel um
  `BeatGridMetadata`; Zweiwert-Unpacking bleibt kompatibel. Direkte
  `RenderResult`-Objekte führen Source-/Target-Provenienz ebenfalls additiv.
- Frische vollständige aufTAKT/librosa-Merges speichern `fallback_used = false`,
  beide Backendidentitäten und eine normierte Match-Confidence. Beat- und
  BPM-Fallbacks speichern `fallback_used = true`, ihre genaue Quelle und
  Confidence `0,0`; Alt-Caches bleiben explizit
  `legacy_cache_unknown` mit `fallback_used = null`.
- Der Default `approximate_grid_policy = reject` weist Fallback und unbekannte
  Herkunft mit getrennten Source-/Target-Rejectioncodes ab. `allow` ist ein
  expliziter Opt-in und entfernt die Provenienz nicht.
- Neue Batchkandidaten tragen `source_grid`/`target_grid`; neue Datasetzeilen
  übernehmen diese Felder. Historische Kandidaten werden als `null` behandelt,
  nicht rückwirkend geraten.
- Volltrack-Featurecaches führen `beat_grid_metadata` im Manifest und im
  Cache-Key, sodass eine geänderte Herkunft keinen alten Cache-Hit erzeugt.
- Cacheformat 2 adressiert Ergebnisse über vollständigen Audio-SHA und einen
  Hash aus Algorithmusversion, librosa-Version/-Parametern,
  aufTAKT-Binary-SHA, Merge- und Fallbackvertrag. `analysis.json` wird atomar
  geschrieben; gleichnamige, inhaltlich verschiedene Dateien besitzen
  getrennte Cachepfade. Legacy-Caches werden nur bei passendem Audiohash
  read-only geladen.
- Die lokale `aufTAKTCl.exe` hat SHA-256
  `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523`
  und keine eingebettete Versions-/Herstellerinformation. Die CLI passt zur
  zplane-AUFTAKT-SDK-Dokumentation; exakte Lieferkette, lokale Lizenz und
  Weitergaberecht sind im Repository nicht belegt. Maschinenlesbarer Stand:
  `config/auftakt_binary_provenance.json`.
- `.venv\Scripts\python.exe -m pytest -q`: **121 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

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

### Verifiziert am 2026-07-31 (Codex, Objective v4 und zurückgehaltener Hörsatz)

- Objective v4 verwendet drei neue differenzierbare Terme:
  gaingewichtetes `vocal_overlap`, onset-/offsetbewusstes `vocal_boundary`
  und `transient_artifact` für Übergabebewegung auf starken
  Onset-/Spectral-Flux-Bins. Ohne beide Featuretensoren sind die neuen Terme
  exakt null; ein nur einseitig vorhandener Tensor wird abgelehnt.
- Die Gewichte `1.0 / 0.30 / 0.08` wurden auf zwei inhaltlich eindeutigen
  Validation-Paaren eingefroren. Der Loss sank dort von `0.2180 → 0.1916`
  und `0.2906 → 0.2740`. Beim vocalreichen zweiten Paar sank
  Vocal-Overlap `0.0168 → 0.0068` und Vocal-Grenze `0.4647 → 0.4078`.
- `src.evaluation.heldout_control_study` rendert Datasetbeispiele direkt mit
  ihren gespeicherten Featurefenstern und dokumentiert Dataset-ID, Split,
  Objective-Version, Controls und Loss-Komponenten. Der Testsplit bleibt
  strikt von Training und Validation getrennt.
- Neuer geblendeter Testsatz:
  `output/control_studies/blind_v5_objective_v4_heldout_test9_4bar_20260731_rerun/`.
  Er enthält alle neun Testbeispiele als 18 Float32-WAVs, 44,1 kHz Stereo,
  paarweise identische Länge und ausschließlich endliche Samples. Drei
  Frontliner-Paare verwenden `ffmpeg_librubberband`, die übrigen sechs
  benötigen keine Tempoanpassung. `STRUGGLING` kommt nicht vor.
- Der Objective-Loss sank in allen neun Testbeispielen (je nach Paar rund
  5,3–19,5 %). Der Satz ist noch geblendet und unbewertet; ein hörbarer
  Vorteil gegenüber Equal Power ist daher ausdrücklich noch nicht belegt.
- Ratings-Format 2 ergänzt `vocal_clarity` sowie `vocal_clash` und
  `cut_lyrics`; alte Format-1-Ratings bleiben lesbar.
- `.venv\Scripts\python.exe -m pytest -q`: **77 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-04 (Nutzerhörtest, Objective v4)

- Der geblendete Testsplit-Hörsatz ist vollständig bewertet und erst danach
  über `src.evaluation.analyze_control_study` entblindet worden. Persistente
  Ergebnisse: `ratings.json` und `study_results.json` im v5-Hörsatz.
- Präferenz: **9/9 für die Objective-v4-optimierten Kurven**, 0 für Equal
  Power, 0 Gleichstände. Das gilt in allen drei gerichteten Paargruppen mit
  jeweils drei unterschiedlichen Cue-Kombinationen.
- Mittel über sechs Kriterien: Equal Power **4,7593**, optimiert **4,9259**.
  Der Unterschied stammt ausschließlich aus `cleanliness`: **4,0 → 5,0** in
  jedem Paar. Energieform, Low-End und Artefaktfreiheit sind jeweils 5,0 für
  beide Methoden; Rhythmik und Vocal-Klarheit jeweils 4,7778 für beide.
- Interpretation: Das direkte Optimierungs-Gate gegen Equal Power ist für
  diesen zurückgehaltenen Satz bestanden. Eine spezifische hörbare
  Verbesserung durch die neuen Vocal-Terme ist damit noch nicht gezeigt;
  acht Paare hatten dort Deckeneffekte, Paar 3 erhielt für beide Methoden
  Vocal-Klarheit 3.
- Statistische Grenze: neun Cue-Beispiele sind wegen Track-/Paarwiederholung
  keine neun unabhängigen Beobachtungen. Der Testsplit enthält drei
  Audio-Hashes; insbesondere teilen die drei Paargruppen Tracks. Das Ergebnis
  ist ein starkes Entwicklungs-Gate, noch kein populationsweiter Nachweis.

### Verifiziert am 2026-08-04 (Codex, ML-Baseline Version 1)

- Bridge-Waveform-Cacheformat 1 speichert pro Beispiel zwei samplegleiche
  Float32-Stereo-Waveforms mit Konfigurations-, Datei- und Array-Hashes. Die
  produktive 44,1-kHz-Ausrichtung einschließlich Time-Stretch wird vor der
  Ablage auf standardmäßig 11.025 Hz heruntergerechnet und nicht pro Epoche
  wiederholt.
- Das PyTorch-Dataset prüft Split-NPZ, `examples.jsonl`, Paarmanifest und bei
  einem Cache-Erstaufbau beide Audio-SHAs. Features werden gestapelt;
  BPM-abhängig lange Waveforms bleiben ungepaddet und werden im Loss einzeln
  gerendert.
- `time_shared_mlp_v1`: 124 Eingänge je Intervall, Hidden-Dimensionen 64/32,
  zwei Inkrement-Logits, **10.394 Parameter**. Vor dem ersten Update sind
  beide Kurven exakt linear; Endpunkte, strenge Monotonie und maximale
  Schrittgröße bleiben konstruktiv garantiert.
- Reale Train-Sonde `example-c0a82769f650d763`: Cache-Erstlauf
  `cache_hit = false`, unmittelbare Wiederholung `true`, Waveformshape
  `(2, 67328)`, Backend `not_needed`. Der initiale self-supervised Loss ist
  `0,303036`; alle vorhandenen Modellgradienten sind endlich.
- Der endgültige unabhängige Modelltest benötigt neue Track-Hashes, weil der
  aktuelle Testsplit bereits für die Objective-v4-Hörstudie verwendet wurde.
- `.venv\Scripts\python.exe -m pytest -q`: **81 Tests bestanden**; zwei
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

### Verifiziert am 2026-08-04 (Codex, erster MLP-Trainingslauf)

- `self_supervised_train_validation_v1` speichert den vollständigen
  Dataset-/Modell-/Renderer-/Objective-/Optimierungsvertrag, atomare
  `best.pt`-/`latest.pt`-Checkpoints samt SHA-256, alle Loss-Komponenten und
  vertragsgeprüftes Resume. Epoche 0 ist die unveränderte Equal-Power-Kurve.
- Reale Instanz:
  `output/training_runs/time_shared_mlp_v1_objective_v4_seed20260804_20260804/`
  auf Dataset `f9044dc259b7296c8b28`, **45 Train / 9 Validation**. Alle 54
  Bridge-Waveform-Caches wurden aufgebaut; der Testsplit wurde nicht geladen.
- Validation-Loss: **0,305959 → 0,295999** in der besten Epoche 8
  (**−3,26 %**). Train-Loss in derselben Epoche: **0,320002 → 0,303996**
  (**−5,00 %**). Nach sechs Epochen ohne weitere Verbesserung stoppte der
  Lauf in Epoche 14.
- Auf Validation weichen die vorhergesagten `mix_position`-Kurven maximal
  0,185 und `low_end_position` maximal 0,038 von linear ab. Die maximale
  Standardabweichung zwischen Beispielen beträgt 0,101 beziehungsweise
  0,023; das Netz gibt damit keine einzelne konstante Kurve aus.
- Manifest-, History-, Best- und Latest-Hashes wurden erneut berechnet und
  stimmen. `best.pt` enthält Epoche 8, `latest.pt` Epoche 14.
- Der Proxy-Loss-Rückgang ist nur ein technischer Lernnachweis, kein
  Hörqualitätsnachweis. Der bestehende Testsplit ist durch das frühere
  Objective-v4-Hör-Gate bereits verbraucht; ein finaler Modellvergleich
  benötigt neue Audio-Hashes.
- `.venv\Scripts\python.exe -m pytest -q`: **84 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-04 (Codex, blinder MLP-Entwicklungsvergleich)

- `src.evaluation.ml_control_study` prüft Dataset-, Paarmanifest- und
  Best-Checkpoint-Hashes, lädt `best.pt` aus Epoche 8 und rendert Equal Power
  sowie die vorhergesagten MLP-Kurven mit identischem Kontext und gemeinsamer
  Peak-Absenkung. Die A/B-Zuordnung steht nur in `answer_key.json`.
- Vollständiger Satz:
  `output/control_studies/blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun/`
  mit **9 Paaren / 18 Float32-WAVs**, 44,1 kHz Stereo. Alle Audio-Hashes
  stimmen; A und B sind je Paar samplegleich, alle Werte endlich, maximaler
  Peak 0,98.
- Der Objective-Loss sinkt in allen neun Paaren; im Mittel
  **0,305959 → 0,295999** (−3,26 %), paarweise rund 0,98–8,00 %. Diese Werte
  sind nur im Antwortschlüssel dokumentiert und werden vor der Bewertung
  nicht zur A/B-Zuordnung offengelegt.
- `ratings.json` verwendet Format 2 und steht auf `unrated`. Der Satz enthält
  alle Validation-Beispiele, darunter sechs Cue-Varianten von
  BREATH_LESS→BREATH_LESS und drei ASCENSION→BREATH_LESS. Wegen Modellwahl
  auf demselben Split ist dies kein unabhängiger Test.
- Ein erster Export mit der üblichen Obergrenze von drei Beispielen pro
  gerichteter Trackkombination bleibt unverändert als 6-Paar-Zwischenartefakt
  unter dem gleichnamigen Ordner ohne `_rerun` erhalten.
- `.venv\Scripts\python.exe -m pytest -q`: **87 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, Vocal-Control v2 und Objective v5)

- `vocal_time_shared_mlp_v2` erzeugt `mix_position`, `low_end_position`,
  `vocal_position`, getrenntes `vocal_duck_a/b` und die resultierenden
  `vocal_gain_a/b`. Mix-, Low-End- und Vocal-Position bleiben konstruktiv
  monoton mit festen Endpunkten; Ducking ist an beiden Enden exakt null.
- Der stem-fähige Renderer bildet pro Track `mix - Demucs-Vocal`, rendert den
  Rest zweibandig und addiert beide Vocal-Stems mit unabhängigen Gains.
- Objective v5 ergänzt `vocal_stem_overlap`, `vocal_audibility` und
  `vocal_mid_phrase_gain_change`. Synthetische Tests bestätigen: unnötiges
  Absenken eines aktiven Einzelvocals erhöht Audibility-Loss; Ducking bei zwei
  aktiven Vocals senkt den Stem-Overlap-Term.
- Vocal-Bridge-Cacheformat 2 enthält vier samplegleiche Float32-Stereoarrays
  und bindet beide Demucs-Artefakt-SHAs in den Cache-Key ein. Reale Sonde
  `example-c0a82769f650d763`: viermal `(2, 67328)` bei 11.025 Hz, erster Lauf
  Miss, direkter Wiederholungslauf Hit.
- Reale Gradientensonde: Objective v5 `0,365197`, davon v4 `0,302488`,
  Audibility `0,125145`, Stem-Overlap `0` und Mid-Phrase-Änderung `0,000684`;
  alle Gradienten endlich.
- Der additive v2-Trainingsrunner wurde anschließend separat implementiert;
  der v1-Vertrag und seine Checkpoints bleiben unverändert. Die Objective-
  Gewichte bleiben wegen der kleinen Hörstichprobe Entwicklungsparameter.
- `.venv\Scripts\python.exe -m pytest -q`: **92 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, Vocal-reicher Objective-v5-Hörsatz)

- Die Auswahl bewertet Vocal-Aktivität in exakt den 32 Halbbeat-Bins des
  Source-Postrolls und Target-Prerolls. Beide Seiten müssen im Mittel
  mindestens `0,15` erreichen; je gerichteter Paarung wird nur ein Cue und
  je Track höchstens zwei Verwendungen zugelassen. `STRUGGLING` kommt nicht
  vor.
- Vollständiger geblendeter Satz:
  `output/control_studies/blind_v7_objective_v5_vocal_active6_20260805_rerun/`
  mit sechs Paaren / zwölf Float32-WAVs bei 44,1 kHz. Die Source-Mittelwerte
  reichen von `0,374` bis `0,894`, Target von `0,491` bis `0,792`; je Paar
  sind 13 bis 32 von 32 Bins gleichzeitig vocal-aktiv über `0,2`.
- Beide A/B-Varianten verwenden denselben Vocal-Renderer, Kontext und
  gemeinsamen Peak-Gain. Verglichen werden Objective-v4-Mix-/Low-End-
  Controls ohne Ducking gegen vollständig optimierte Objective-v5-Controls.
- Der Objective-v5-Loss sank in allen sechs Paaren um rund 6,9–20,1 %.
  Alle WAV-Hashes stimmen, A/B sind je Paar samplegleich, alle Werte endlich
  und der gemeinsame Peak liegt bei höchstens 0,98.
- Nach vollständiger geblendeter Bewertung und anschließender Entblindung:
  Objective v5 **2 Siege**, Objective v4 **1 Sieg**, **3 Gleichstände**.
  Der Mittelwert über fünf Kriterien steigt `4,2333→4,3667`; ausschließlich
  Vocal-Klarheit steigt (`4,3333→5,0`). Sauberkeit, Energie, Low-End und
  Artefaktfreiheit sind identisch.
- Nutzerentscheidung 2026-08-05: `rhythmic_stability` wird aus neuen
  Control-Modell-Ratings entfernt, weil die verglichenen Controls Beat-Grid
  und Time-Stretch nicht beeinflussen. Ratings-Format 3 speichert fünf
  Kriterien; historische Versionen 1/2 bleiben lesbar.
- Paar 2, 3 und 5 verwenden `ffmpeg_librubberband` mit Faktoren 0,9697,
  0,9697 und 0,9706. Der Nutzer hört in beiden Methoden ein schlechtes
  Target; diese drei Gleichstände validieren primär den gemeinsamen
  Time-Stretch-Pfad, nicht die Vocal-Controls.
- Gelernt (2026-08-05, erster Exportversuch): Ein Sandbox-Start von FFmpeg
  scheiterte beim zweiten Paar mit `WinError 5`; der unvollständige Ordner
  ohne `_rerun` blieb unverändert, der freigegebene `_rerun` ist vollständig.
- `.venv\Scripts\python.exe -m pytest -q`: **97 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, erster Vocal-v2-Trainingslauf)

- `self_supervised_vocal_train_validation_v2` bindet Modellformat 2,
  Control-Protokoll 4, Objective v5, Vocal-Cacheformat 2 und `htdemucs` in
  einen unveränderlichen Vertrag. Pfad und SHA-256 aller tatsächlich
  verwendeten Cachemanifeste werden gespeichert. Checkpoints und History
  werden atomar geschrieben; Resume prüft Vertrag und Latest-Checkpoint-Hash.
- Reale Instanz:
  `output/training_runs/vocal_time_shared_mlp_v2_objective_v5_seed20260805_20260805/`
  auf Dataset `f9044dc259b7296c8b28`, **45 Train / 9 Validation**. Train und
  Validation besitzen vollständige Vocal-Waveform-Caches; der Testsplit
  blieb mit **0/9** absichtlich unangetastet.
- Validation-Loss: **0,267815 → 0,259337** in der besten Epoche 16
  (**−3,17 %**). Nach sechs Epochen ohne weitere Verbesserung stoppte der
  Lauf in Epoche 22. Train-Loss bis Epoche 16: **0,243792 → 0,225894**
  (**−7,34 %**).
- Auf Validation sinken `vocal_stem_overlap` um **26,70 %** und
  `vocal_audibility` um **25,27 %**. Gleichzeitig steigen der alte
  `loss_v4` um **5,05 %**, `energy_shape` um 4,21 % und
  `vocal_mid_phrase_gain_change` um 27,78 %. Der Gesamt-Proxygewinn stammt
  damit gezielt aus den neuen Vocal-Termen und muss hörend bestätigt werden.
- Die gelernte Validation-Sonde zeigt vor allem Source-Ducking: Mittelwert
  `0,1452`, Maximum `0,5088`; Target-Ducking bleibt klein (Mittelwert
  `0,0037`, Maximum `0,0092`). Alle Positionen bleiben monoton und alle
  Ducking-Endpunkte liegen numerisch bei null.
- Manifest-, History-, Best- und Latest-Hashes wurden erneut berechnet und
  stimmen. `best.pt` enthält Epoche 16, `latest.pt` Epoche 22.
- `.venv\Scripts\python.exe -m pytest -q`: **100 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, erweiterter 145–165-BPM-Datensatz und Retraining)

- Rekursiver Inventarbestand: **119 FLAC-Pfade**. Vor dem Songranking wurden
  `STRUGGLING` per Policy, ein SHA-identisches Duplikat von BREATH_LESS und
  sechs Tracks unter 145 BPM ausgeschlossen; kein Track lag über 165 BPM.
  Die Grenzen sind inklusiv und stehen in Batch- und Datasetmanifest.
- `output/batches/all_music_recursive_bpm145_165_top1_20260805/` enthält
  **111/111 abgeschlossene Quellen und Paarmanifeste, 0 Fehler**. Die
  Paarmanifeste enthalten 1.730.938 Kandidaten mit BPM 147,656–161,499;
  kein Kandidat liegt außerhalb des Vertrags.
- Dataset `52bc9d1cebfd1b82d2ea` unter
  `output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805/`:
  1.110 ausgewählte Cues vor Splitfilterung, 630 Cross-Split-Verwerfungen,
  **480 Exportbeispiele = 370 Train / 50 Validation / 60 Test**. Verwendete
  Trackhashes: 43/5/7, keine Überschneidung. Alle fünf Dateihashes stimmen.
- Neuer Trainingslauf:
  `output/training_runs/vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805/`.
  Beste Validation in Epoche 22, Early Stopping in Epoche 28. Train-Loss
  **0,307197→0,269025 (−12,43 %)**; Validation
  **0,359040→0,336999 (−6,14 %)**.
- Auf Validation verbessern sich `loss_v4` um **4,83 %**, `energy_shape` um
  **8,79 %**, `vocal_stem_overlap` um **44,39 %** und `vocal_audibility` um
  **10,04 %**. `vocal_mid_phrase_gain_change` steigt dagegen um
  **204,28 %** und bleibt das wichtigste Hör-Risiko.
- Das neue Modell duckt auf den 50 Validation-Beispielen eher Target-Vocals
  (Mittel 0,1689, Maximum 0,7164) als Source-Vocals (Mittel 0,0401, Maximum
  0,5107). Alle Positionen bleiben monoton und Ducking-Endpunkte null.
- Alle 420 Train-/Validation-Cachemanifest-Hashes, History sowie Best-/Latest-
  Checkpoint stimmen. Best enthält Epoche 22, Latest Epoche 28. Für **0/60**
  Testbeispiele wurde ein Vocal-Waveform-Cache erzeugt.
- Gelernt (2026-08-05, erster erweiterter Batchversuch): Das Tool-Timeout
  beendete den Shell-Wrapper, nicht dessen Python-Kindprozess. Mehrfaches
  Fortsetzen auf demselben Ordner erzeugte zwei `FileExistsError`; der
  kollidierte Top-3-Zwischenordner bleibt unverändert. Für den sauberen
  Top-1-Lauf wurde genau ein Prozess in einem neuen Ordner verwendet.
- `.venv\Scripts\python.exe -m pytest -q`: **105 Tests bestanden**; zwei
  bestehende, nicht blockierende Deprecation-Warnungen aus `audioread`.

### Verifiziert am 2026-08-05 (Codex, CUDA-Aktivierung)

- Lokale GPU: **NVIDIA GeForce RTX 5070 Ti**, 16 GB VRAM, Compute Capability
  12.0. NVIDIA-Treiber 610.74 meldet CUDA UMD 13.3.
- Die Projekt-`.venv` verwendet jetzt **PyTorch 2.13.0+cu130** statt des
  CPU-Wheels. `torch.cuda.is_available()` ist wahr; eine reale Tensor- und
  Gradientenprobe lief auf `cuda:0` mit endlichen Gradienten.
- Beide Trainingsrunner lösen den neuen Default `auto` vor Erstellung des
  Run-Vertrags auf `cuda:0` oder `cpu` auf. Ein vollständiger synthetischer
  Train-/Validation-Lauf auf `cuda:0` schrieb den erwarteten CUDA-Vertrag.
- Neue Demucs-Separationen verwenden denselben Auto-Device-Pfad und schreiben
  `compute_device` additiv ins Stemmanifest. Vorhandene gültige Stem-Caches
  bleiben unverändert und werden nicht neu berechnet. Eine reale HT-Demucs-
  Sonde auf einer synthetischen Sekunde Stereo-Audio lief auf `cuda:0`, gab
  vier endliche Stems zurück und belegte maximal rund 793 MiB GPU-Speicher.
- CUDA-Backward-Kernel für lineares Upsampling und adaptives Average-Pooling
  sind in PyTorch 2.13 nicht strikt deterministisch. Sie laufen deshalb unter
  CUDA mit Determinismuswarnung; für bitgenaue Wiederholung bleibt
  `--device cpu` verfügbar. Historische CPU-Runs benötigen beim Resume
  weiterhin ausdrücklich `--device cpu`.
- `.venv\Scripts\python.exe -m pytest -q`: **109 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen. `.venv\Scripts\python.exe -m pip check`:
  keine defekten Abhängigkeiten.

### Verifiziert am 2026-08-06 (Codex, Vocal-v2-Modell-Hörsatz)

- `src.evaluation.vocal_ml_control_study` prüft Runformat, Runnername,
  Modellvertrag, Dataset-ID/-Manifesthash sowie SHA-256 und Epoche des
  Best-Checkpoints. Verglichen werden die ungelernte Vocal-v2-Initialisierung
  und der Best-Checkpoint aus Epoche 22 im identischen stem-fähigen Renderer.
- Die Auswahl arbeitet ausschließlich auf `validation`, verlangt auf beiden
  Seiten mittlere Vocal-Stärke mindestens `0,15`, verwendet höchstens einen
  Cue pro gerichteter Paarung und begrenzt die Tempoanpassung auf `0,5 %`.
  Der aktuelle Split liefert fünf unterschiedliche gerichtete Paarungen;
  tatsächlich benötigen alle **0,0 %** Tempoanpassung (`tempo_backend =
  not_needed`).
- Vollständiger geblendeter, noch unbewerteter Satz:
  `output/control_studies/blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806/`
  mit fünf Paaren / zehn Float32-WAVs bei 44,1 kHz. Source-Vocal-Stärke
  `0,353–0,796`, Target `0,188–0,911`; 7 bis 32 von 32 Bins sind gleichzeitig
  über `0,2` aktiv.
- Alle öffentlichen WAV-Hashes stimmen; A/B sind je Paar samplegleich,
  endlich und haben gemeinsame Peak-Absenkung auf höchstens 0,98.
  `ratings.json` verwendet Format 3 und enthält **0/5 Ratings**; ein
  `study_results.json` existiert noch nicht. `answer_key.json` wurde zur
  Wahrung der Blendung nicht geöffnet.
- Der Objective-v5-Proxy verbessert sich pro Paar nicht einheitlich: zwei
  Paare sinken, drei steigen. Damit darf der Trainingsmittelwert nicht als
  Ersatz für die ausstehende Hörbewertung interpretiert werden.
- `.venv\Scripts\python.exe -m pytest -q`: **111 Tests bestanden**; zwei
  bestehende `audioread`-Deprecation-Warnungen und zwei erwartete
  CUDA-Determinismuswarnungen.

## Abgleich mit dem geplanten Systemablauf

| Komponente aus dem Exposé | Umsetzungsstand | Nachweis / Lücke |
|---|:--:|---|
| 1. Audioimport & Abschnittsauswahl | 🟡 | Zwei Audiodateien können verarbeitet werden; Abschnittsgrenzen sind manuelle Sample-Cutpoints. Mehrere Songs, Abschnittsobjekte und Reihenfolge-Constraints fehlen. |
| 2. Musikanalyse | 🟡 | BPM, Beats, Downbeats, Taktpositionen und HT-Demucs-basierte Vocal-Aktivität sind vorhanden. Phrasen-/Segmentgrenzen, Strukturtypen und eine plattformunabhängige Downbeat-Lösung fehlen. |
| 3. Kandidatengenerierung | 🟡 | Bar-synchrone 2/4-Takt-Kandidaten über beide vollständigen Tracks mit vier vollständigen Drop-/Bridge-Fenstern vorhanden. Phrasen/Struktur und Vocal-Filter fehlen noch. |
| 4. Übergangsmetrik | 🟡 | `feature_baseline_v3` rankt Cutpoints vorab; `rendered_transition_baseline_v1` bewertet Renderergebnisse. Objective v5 enthält stem-basierten Vocal-Overlap und Audibility und gewann sein direktes Hör-Gate knapp 2:1 bei drei Gleichständen. Phrasen, Embeddings und eine gelernte Metrik fehlen. |
| 5. Rendering | ✅ | Hard Cut sowie lineare, Equal-Power-, Zwei-Band- und stem-fähige Vocal-Control-Renderer sind implementiert; Tempoangleichung und Drop-Grenzen sind getestet. |
| 6. Vorschau & Export | 🟡 | Batch-WAV-Export, auditierbares Manifest, Cue-Point-/Metrikvisualisierung und Notebook-Inline-Playback funktionieren. Auswahlworkflow und GUI fehlen. |

Damit ist die technische Grundlage aus Monat 1 weitgehend vorhanden. Das frühe Erfolgskriterium „automatisch erzeugt und systematisch vergleichbar“ ist erfüllt; v1- und Vocal-v2-Training sowie die direkten Objective-Hör-Gates sind abgeschlossen. Der Vocal-v2-Modell-Hörsatz ist gerendert, aber noch unbewertet. Offen sind dessen geblendete Bewertung, weitere Rater und der breitere wissenschaftliche Vergleich aus Monat 2–3.

## Fortschritt gegen die Startphase (Exposé Abschn. 13–14)

| Baustein | Status | Kurz |
|---|:--:|---|
| Reproduzierbares Repository | 🟡 | Git, MD-Doku und Requirements-Dateien vorhanden; aufTAKT und ffmpeg funktionieren lokal, sind aber externe Windows-Komponenten. aufTAKT ist technisch per SHA identifiziert, konkrete Lizenz/Weitergabeberechtigung bleibt ungeklärt. |
| Kleines Entwicklungsset (10–20 Tracks) | 🟡 | Technisch auf 119 lokale FLAC-Pfade beziehungsweise 111 eindeutige BPM-zugelassene Tracks erweitert; Kuratierung, Track-Notizen und Rechte fehlen weiterhin |
| Beat-/Bar-Analyse | ✅ | librosa + aufTAKT-Merge, mit Diskrepanz-Log |
| Mehrere gerenderte Übergänge | 🟡 | Automatischer Batch-Export vorhanden; erster realer 2-Varianten-Lauf HELP_LESS → BREATH_LESS ohne Fehler dokumentiert |
| Automatische Kandidaten | 🟡 | `bar_grid_v1` erzeugt standardmäßig 2/4-Takt-Varianten über alle nutzbaren Downbeats beider Songs; keine Phrasen-/Strukturinformationen |
| Systematischer Vergleich / Höranalyse | 🟡 | Gerankter Batch, Inline-Playback sowie bewertete blinde Control-/Objective-Hörsätze vorhanden; der aktuelle Vocal-v2-Modellhörsatz ist mit 0/5 Ratings noch offen, weitere Rater und ein breiterer Testsatz fehlen |
| Erste Baseline-Renderer (4 Stück) | ✅ | Tempoangepasster Hard Cut, linearer Crossfade, Equal-Power und Kompatibilitätsalias `tempo_fade` getestet |
| Einfache Feature-Metrik | ✅ | `feature_baseline_v3` mit High-Power- und Non-Overlap-Komponente, auditierbaren Messwerten und Top-k-Rendering |
| Render-Audio-Metrik | ✅ | `rendered_transition_baseline_v1` mit vier erklärbaren Komponenten, eigenem Ranking und Fehlerisolation im Batch-Manifest |
| Erste Embedding-Tests | ❌ | offen (Monat 3) |
| Liste typischer Fehlerfälle | 🟡 | fortlaufend in [`Bemerkungen.md`](./Bemerkungen.md), noch nicht vollständig systematisiert |
| Entscheidung ML-Fokus | ✅ | Self-supervised Feature→Control-Lernen ohne Ground-Truth-Kurven; differenzierbarer Renderer und eingefrorenes Objective als Lernpfad |

## Bekannte Bugs / Baustellen

- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als zusätzliche einfache Baseline bewusst behandeln; alle Renderer verwenden den tonhöhenerhaltenden Rubber-Band-`TimeStretch`.
- **Time-Stretch-Hörvalidierung**: Rubber Band wurde im neuen Hörsatz real verwendet, aber Paar 5 klingt laut Nutzer in beiden Methoden schlecht. Noch offen ist die isolierte Diagnose Originalsegment versus gestretchtes Segment versus musikalisch ungeeignetes Target-Fenster.
- **Downbeat-Fallback**: Bei fehlenden Taktinformationen bleibt ein approximatives 4/4-Raster für explizite Experimente verfügbar. Es ist jetzt per Provenienz von erkannten Downbeats unterscheidbar und wird von der Kandidatengenerierung standardmäßig abgelehnt. Historische Artefakte ohne Provenienz bleiben methodisch `unknown`.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Kandidatengenerierung).
- **Repo-/Cache-Hygiene**: Neue Caches sind Audio-SHA-/Analyse-ID-adressiert und kollidieren nicht über Track-Stems. Historische Stem-Caches bleiben unverändert; darunter befindet sich ein zusätzlicher veralteter `HELP_LESS`-Eintrag ohne gleichnamigen aktuellen Audio-Stem.
- **aufTAKT-Lizenz**: Die eingecheckte Binärdatei ist per SHA-256 fixiert, aber ihre exakte Quelle und Weitergabeberechtigung sind nicht belegt. Vor Veröffentlichung klären beziehungsweise Binary aus dem Distributionsartefakt entfernen.

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

**Abgeschlossen am 2026-08-04:** zurückgehaltener Objective-v4-Hörsatz vollständig bewertet und entblindet; optimierte Kurven gewinnen 9/9 gegen Equal Power, mit Vorteil ausschließlich bei Sauberkeit.

**Abgeschlossen am 2026-08-04:** versionierter, reproduzierbarer MLP-Trainingsrunner und erster realer 45/9-Train/Validation-Lauf; beste Validation in Epoche 8, Early Stopping in Epoche 14.

**Abgeschlossen am 2026-08-05:** Vocal-Control-Modell v2, stem-fähiger differenzierbarer Renderer, Objective v5 mit Vocal-Audibility-Loss und Vocal-Bridge-Cacheformat 2 samt realer Gradientensonde.

**Abgeschlossen am 2026-08-05:** sechs gezielt Vocal-reiche Objective-v4/v5-A/B-Paare vollständig bewertet und erst danach entblindet; v5 gewinnt 2:1 bei drei Gleichständen und verbessert ausschließlich Vocal-Klarheit.

**Abgeschlossen am 2026-08-05:** separater versionierter Vocal-v2-Trainingsrunner und erster realer 45/9-Train-/Validation-Lauf; beste Validation in Epoche 16, Early Stopping in Epoche 22.

**Abgeschlossen am 2026-08-05:** rekursiver 145–165-BPM-Datenlauf, fehlerfreier 111-Paar-Batch, erweiterter 370/50/60-Datensatz und Vocal-v2-Retraining; beste Validation in Epoche 22, Early Stopping in Epoche 28.

**Abgeschlossen am 2026-08-06:** geblendeter Vocal-v2-Modell-Hörsatz mit fünf vocal-aktiven, gerichteten Validation-Paaren ohne Time-Stretch; Best-Checkpoint aus Epoche 22 gegen die ungelernte Initialisierung. Der Satz ist weiterhin **0/5 bewertet**, und es gibt noch kein `study_results.json`.

1. **Time-Stretch und Target-Fenster von Paar 5 isolieren** — Original-Targetsegment und Rubber-Band-Variante mit identischem Ausschnitt separat exportieren und hören. So wird unterschieden, ob der schlechte Klang vom Backend, der Tempoänderung oder bereits vom gewählten Aversion-Fenster stammt.
2. **Feature-Protokoll 1 auditieren** — globale Paarfeatures, Datasetexport und track-getrennte Splits sind implementiert. Als Nächstes die Vocal-Scores gegen gehörte Lyrics-/Clash-Fälle prüfen und ein semantisch passendes Phrasenverfahren validieren. Kein stilles 4/4→8-Takt-Fallback; Downbeat-Fallbacks bleiben über `source_grid`/`target_grid` sichtbar.
3. **Objective v5 direkt hörvalidieren** — Gate bestanden: 2 v5-Siege, 1 v4-Sieg, 3 Gleichstände; Vocal-Klarheit `4,3333→5,0`. Für endgültige Gewichte später mit mehr Ratenden und ohne Time-Stretch-dominierte Paare wiederholen.
4. **Gelerntes Vocal-v2-Modell hörvalidieren** — Hörsatz ist gerendert: fünf vocal-aktive gerichtete Paarungen, alle ohne Time-Stretch; aktuell **0/5 Ratings**, noch kein `study_results.json`. Als Nächstes A/B vollständig bewerten, erst danach entblinden und auswerten; dabei starkes Target-Ducking und Mid-Phrase-Pegeländerungen gezielt notieren. Objective-Gewichte oder Architektur erst nach diesem Gate ändern.
5. **Entwicklungsset kuratieren** — die 111 eindeutigen BPM-zugelassenen Tracks als reproduzierbares Set definieren, Varianz prüfen, Track-Notizen ergänzen und Lizenzfrage klären (parallel, eher Handarbeit).

Danach: TCN-/BiLSTM-Hauptmodell und Mid-/High-Controls als neue Modellversion untersuchen sowie vortrainierte Embeddings auf demselben trackgetrennten Evaluationssatz vergleichen.

### Verifiziert am 2026-08-12 (TCN/BiLSTM-Hauptmodell, Architektursonde)

- Eine additive `tcn_bilstm_transition_control_v1`-Architektur ist unter
  `src/ml/model.py` implementiert. Sie verwendet einen für A/B geteilten
  temporalen Conv1d-Encoder `54 → 64 → 128`, die Fusion
  `[A, B, A-B, A*B]` mit `512 → 256`, die Projektion der 16 globalen
  Paarfeatures und einen zweilagigen bidirektionalen LSTM mit
  `input_size=256` und `hidden_size=128`.
- Der Controller gibt pro Halbbeat zehn sigmoid-beschränkte Werte als
  `(B, 32, 10)` aus: Gain A/B, Low-/Mid-/High-EQ A/B, Low-End-Ownership und
  Vocal-Ducking. Der Einstieg ist `python -m src.ml model-info-tcn-bilstm`.
- Die Architektursonde verändert v1/v2-Checkpoints und deren Trainingsrunner
  nicht. Monotonie, komplementäre Gains und die Anbindung an den
  differenzierbaren Renderer bleiben ein eigener nächster Control-/Objective-
  Schritt; ein selbstüberwachter Trainingsrunner für v3 ist noch offen.

## Offene Fragen / Entscheidungen (technisch)

- BPM-/Beat-Grid: was ist maßgeblich, wenn librosa und aufTAKT abweichen (HELP_LESS 161 vs. 157)?
- Übergangslänge: **entschieden am 2026-07-21** — Kandidaten führen sie kanonisch in Takten und leiten die für FadeCut benötigten Beats aus dem analysierten Fenster ab. Offene Folgefrage: Wie sollen spätere Renderer mit wechselndem Metrum umgehen?
- Vocal-Overlap: HT-Demucs-Scores sind verfügbar; offen ist ihre Kalibrierung und ob sie als harter Filter, weiche Metrik-Penalty oder nur als Modelleingang verwendet werden.
- **aufTAKT (Windows-Binary) vs. plattformunabhängiges Downbeat-Tracking** (z. B. madmom) — Reproduzierbarkeit vs. Aufwand.
- Rechte an den Testtracks (HELP_LESS/BREATH_LESS) — eigene Produktion oder lizenzpflichtig? (Exposé Abschn. 8: rechtlich handhabbares Set nötig.)
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?

_Vom Exposé bereits beantwortet: Forschungsfrage, Scope/Abgrenzung, Rolle der GUI, Related-Work-Rahmen, Evaluationsansatz, ML-Priorisierung._
