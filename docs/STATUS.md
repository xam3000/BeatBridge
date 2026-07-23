# BeatBridge – Stand & Next Steps

_Stand: 2026-07-23_

**Maßgeblicher Kontext: [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) (Exposé).** Diese Datei hält den *technischen Prototyp-Stand der Startphase* (Monat 1 / erste 2–3 Wochen) fest. Ziel, Scope, wissenschaftlicher Beitrag, Related Work, Datenstrategie, Evaluation, 6-Monats-Plan und Risiken stehen im Exposé.

**Forschungsfrage (Exposé):** Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue, nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu **bewerten** und zu **erzeugen** — möglichst ohne explizite Annotationen? Wissenschaftlicher Kern ist die **Übergangsmetrik / das Compatibility-Modell** (Monat 2–3), nicht Pipeline oder GUI.

**Wichtigstes Erfolgskriterium der Startphase (Exposé Abschn. 14):** Nach spätestens drei Wochen sollen *mehrere automatisch erzeugte* Übergänge *hörbar* sein und *systematisch verglichen* werden können.

Kurzfazit Prototyp: Kandidaten können jetzt aus taktsynchronen Downbeats automatisch erzeugt, als Drop-Ende-A→energiearme Bridge→Drop-Anfang-B gerankt, ohne Überlappung der High-Power-Abschnitte gerendert und im Notebook angehört sowie bewertet werden. Ein realer Drop-Bridge-Lauf für HELP_LESS → BREATH_LESS liegt vor; menschliche Urteile, Phrasen-/Vocal-Merkmale und gelernte Metriken fehlen noch.

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
- **Tempo** (`src/tempo/`): Resample-basierte Variante (`SimpleTempoAdjust`, verändert Tonhöhe) und reparierter, eingebundener `TimeStretch` (tonhöhenerhaltend).
- **Tests**: `pytest`-Suite mit synthetischen Audiodaten prüft alle vier Renderer, Tempoanpassung, 48→44,1-kHz-Resampling, Mono→Stereo und den Fehlerpfad bei fehlenden Downbeat-Metadaten.
- **Kandidatengenerierung** (`src/candidates/`): versionierter Vertrag `CANDIDATE_PROTOCOL.md` und Generator `bar_grid_v1`. Er kombiniert standardmäßig alle nutzbaren Taktgrenzen beider Songs für 2/4 Takte; vollständige Downbeat-Metadaten, Pre-/Post-Roll auf beiden Seiten, kompatible Beatanzahl in allen vier Fenstern und maximal 15 % Tempoabweichung sind harte Filter.
- **Feature-Ranking** (`src/ranking/`): `feature_baseline_v3` bewertet Drop A, Source-Auslauf, Target-Vorlauf und Drop B getrennt. Je 30 % entfallen auf High Power der Drops und Non-Overlap (Energieabfall nach A, niedrige Transition-Energie, Energieanstieg vor B); Chroma, RMS-Kontinuität, Spektrum und Tempo ergänzen den Score.
- **Songpaar-Kompatibilität** (`src/ranking/song_compatibility.py`): `rank_song_targets()` ordnet Target-Songs pro Source-Song vor der Cutpoint-Generierung nach Harmonie, Tempoanpassungsstärke, Klang, Energie und Rhythmus.
- **Batch-Rendering** (`src/batch_render.py`): rankt akzeptierte Kandidaten und rendert standardmäßig die Top 5 × ausgewählte Renderer als kurze WAV-Vorschauen (5 s vor, 12 s nach Source-Cutpoint). Exporte werden atomar geschrieben; vorhandene Dateien werden ohne explizites `--overwrite` nicht ersetzt. Gescheiterte Einzelvarianten sowie Generator- und Ranking-Rejections bleiben im Manifest sichtbar. Seit 2026-07-22 übernehmen alle Renderer die Source-/Target-BPM explizit aus dem Kandidatenvertrag und passen Song B konsistent auf Song A an.
- **Hörbewertung** (`src/evaluation/ratings.py`, `notebooks/listen_batch.ipynb`): das Notebook listet Varianten in Rangfolge und bettet WAVs über `IPython.display.Audio` ein. `rate()` speichert eine 1–5-Bewertung mit Fehler-Tags und Notiz atomar in einer getrennten `ratings.json`; dieselbe Funktionalität ist als CLI verfügbar. Der Startpfad verweist auf den realen Ranking-Lauf.
- **Dataset**: 21 Audiodateien liegen im ignorierten Ordner `musik/`; für alle 21 existiert eine gecachte Analyse unter `output/pre_analysis/` (plus ein veralteter zusätzlicher Cache `HELP_LESS`). Kuratierte Track-Notizen, Lizenzstatus und reproduzierbare Dataset-Definition fehlen noch.

### Verifiziert am 2026-07-22 (Codex, nach Ranking-/Hörbewertungs-Meilenstein)

- Multi-Song-Batch: `output/batches/all_songs_top3_targets_top3_transitions_20260722/`; für alle 20 aktuellen Tracks wurden die drei global kompatibelsten Zieltracks ausgewählt und pro Songpaar bis zu drei Equal-Power-Übergänge gerendert. Ergebnis: 60 abgeschlossene Paar-Manifeste, 165 WAV-Vorschauen, keine Runner- oder Renderfehler. `src.multi_batch_render` schreibt das Auswahl- und Fortschrittsmanifest nach jedem Songpaar atomar fort; Wildcards wie `musik\*.flac` werden auf Windows intern aufgelöst.
- Python-Version der Projektumgebung: **3.14.2**.
- `.venv\Scripts\python.exe -m pytest -q`: **32 Tests bestanden**; zwei nicht blockierende Deprecation-Warnungen aus `audioread` unter Python 3.14.
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
| 4. Übergangsmetrik | 🟡 | `feature_baseline_v3` rankt Drop-Ende, energiearme Non-Overlap-Bridge und Drop-Anfang anhand relativer Energie plus Compatibility-Merkmalen. Phrasen, Vocals, Embeddings und menschliche Evaluation fehlen. |
| 5. Rendering | ✅ | Hard Cut sowie lineare und Equal-Power-Bridge-Renderer sind implementiert und gleichen das Tempo immer an; ein Test garantiert, dass Drop A/B außerhalb des Mischfensters bleiben. |
| 6. Vorschau & Export | 🟡 | Batch-WAV-Export, auditierbares Manifest und Notebook-Inline-Playback funktionieren. Visualisierung, Auswahlworkflow und GUI fehlen. |

Damit ist die technische Grundlage aus Monat 1 weitgehend vorhanden. Das frühe Erfolgskriterium „automatisch erzeugt und systematisch vergleichbar“ ist auf Artefakt-Ebene erfüllt; der menschliche Hörvergleich und der wissenschaftliche Kern aus Monat 2–3 (Komponente 4) stehen noch aus.

## Fortschritt gegen die Startphase (Exposé Abschn. 13–14)

| Baustein | Status | Kurz |
|---|:--:|---|
| Reproduzierbares Repository | 🟡 | Git, MD-Doku und Requirements-Dateien vorhanden; aufTAKT und ffmpeg funktionieren lokal, sind aber externe Windows-Komponenten und ihre Einrichtung ist noch nicht automatisiert |
| Kleines Entwicklungsset (10–20 Tracks) | 🟡 | 21 lokale Audiodateien + Analyse-Caches vorhanden; Kuratierung, Track-Notizen, Rechte und reproduzierbare Definition fehlen |
| Beat-/Bar-Analyse | ✅ | librosa + aufTAKT-Merge, mit Diskrepanz-Log |
| Mehrere gerenderte Übergänge | 🟡 | Automatischer Batch-Export vorhanden; erster realer 2-Varianten-Lauf HELP_LESS → BREATH_LESS ohne Fehler dokumentiert |
| Automatische Kandidaten | 🟡 | `bar_grid_v1` erzeugt standardmäßig 2/4-Takt-Varianten über alle nutzbaren Downbeats beider Songs; keine Phrasen-/Strukturinformationen |
| Systematischer Vergleich / Höranalyse | 🟡 | Gerankter Batch, Inline-Playback und persistente 1–5-Bewertung mit Fehler-Tags vorhanden; tatsächliche menschliche Urteile fehlen |
| Erste Baseline-Renderer (4 Stück) | ✅ | Tempoangepasster Hard Cut, linearer Crossfade, Equal-Power und Kompatibilitätsalias `tempo_fade` getestet |
| Einfache Feature-Metrik | ✅ | `feature_baseline_v3` mit High-Power- und Non-Overlap-Komponente, auditierbaren Messwerten und Top-k-Rendering |
| Erste Embedding-Tests | ❌ | offen (Monat 3) |
| Liste typischer Fehlerfälle | 🟡 | nur punktuell (`Bemerkungen.md`) |
| Entscheidung ML-Fokus | ❌ | offen; Exposé priorisiert vortrainierte Embeddings zuerst |

## Bekannte Bugs / Baustellen

- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als zusätzliche einfache Baseline bewusst behandeln; alle Renderer verwenden den tonhöhenerhaltenden `TimeStretch`.
- **Downbeat-Fallback**: Bei fehlenden Taktinformationen wird ein approximatives 4/4-Raster aus den Beat-Positionen (oder BPM) erzeugt. Es hält die Pipeline lauffähig, ist aber keine verlässliche Downbeat-Erkennung und sollte im Hörvergleich geprüft werden.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Kandidatengenerierung).
- **Repo-/Cache-Hygiene**: Die früheren Track-Ordner sind im Arbeitsbaum gelöscht; unter `output/pre_analysis/` bleibt ein zusätzlicher veralteter Cache `HELP_LESS` ohne gleichnamigen aktuellen Audio-Stem.

## GUI-Frage: jetzt oder später? (Entscheidung)

**Empfehlung: noch kein echtes GUI — vom Exposé bestätigt** (GUI ist nur Interaktionsschicht; Risiko 15: „GUI-/Audio-Engineering verdrängt den Forschungsbeitrag"). Erst die Pipeline tragfähig machen und billig „sehen & hören" ermöglichen. Ein ausgebautes GUI lohnt sich erst, wenn Kandidaten + Metrik stehen und es einen Workflow gibt, den es einpackt (gerankte Kandidaten durchblättern, probehören, annehmen/verwerfen) — laut Zeitplan Monat 4.

Billiger Zwischenschritt statt GUI: `matplotlib`-Visualisierung (Waveform/Spektrogramm + (Down)Beats + Übergangsfenster) und ein Jupyter-Notebook (oder dünnes Streamlit/Gradio) mit Inline-Playback (`IPython.display.Audio`).

## Next Steps (priorisiert)

Ziel: das Startphasen-Erfolgskriterium erfüllen — die Schleife **automatische Kandidaten → mehrere rendern → anhören/vergleichen** schließen.

**Abgeschlossen am 2026-07-17:** programmatische Pipeline, Audio-Normalisierung, vier Rendering-Baselines, versionierter Rendering-Vertrag und automatisierte Tests.

1. **Drop-Bridge-Hörvergleich durchführen** — die drei Varianten aus `help_to_breath_drop_bridge` im Notebook anhören und über `rate()` bewerten: Bleibt Drop A vollständig, wirkt die 4-Takt-Bridge energieärmer, und startet Drop B klar ohne High-Power-Überlappung? Danach zwei kontrastierende Trackpaare exportieren. Als nächste Notebook-Erweiterung die vier Analysefenster und den Energieverlauf plotten.
2. **Entwicklungsset kuratieren (Exposé Abschn. 8)** — die vorhandenen 21 Tracks als reproduzierbares Set definieren, Varianz und Duplikate prüfen, Track-Notizen ergänzen und Lizenzfrage klären (parallel, eher Handarbeit).
3. **Feature-Metrik evaluieren und erweitern** — menschliche Bewertungen gegen Score/Rang vergleichen, Gewichte nicht anhand eines Einzelbeispiels überoptimieren und als Nächstes Phrasen- sowie Vocal-Informationen ergänzen; danach vortrainierte Embeddings vergleichen.

Danach: die **Feature-Metrik** auf mehreren bewerteten Trackpaaren validieren; **vortrainierte Embeddings** vergleichen, eigenes SSL-Fine-Tuning optional (Monat 3; Priorisierung laut Exposé Risiko 15: Pipeline+Baselines+Metrik zuerst).

## Offene Fragen / Entscheidungen (technisch)

- BPM-/Beat-Grid: was ist maßgeblich, wenn librosa und aufTAKT abweichen (HELP_LESS 161 vs. 157)?
- Übergangslänge: **entschieden am 2026-07-21** — Kandidaten führen sie kanonisch in Takten und leiten die für FadeCut benötigten Beats aus dem analysierten Fenster ab. Offene Folgefrage: Wie sollen spätere Renderer mit wechselndem Metrum umgehen?
- Vocal-Overlap: eigene Vocal-Detektion oder als weiches Penalty in der Metrik? (Exposé: beides denkbar — harter Filter + Score-Penalty.)
- **aufTAKT (Windows-Binary) vs. plattformunabhängiges Downbeat-Tracking** (z. B. madmom) — Reproduzierbarkeit vs. Aufwand.
- Rechte an den Testtracks (HELP_LESS/BREATH_LESS) — eigene Produktion oder lizenzpflichtig? (Exposé Abschn. 8: rechtlich handhabbares Set nötig.)
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?

_Vom Exposé bereits beantwortet: Forschungsfrage, Scope/Abgrenzung, Rolle der GUI, Related-Work-Rahmen, Evaluationsansatz, ML-Priorisierung._
