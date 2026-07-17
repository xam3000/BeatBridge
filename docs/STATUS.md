# BeatBridge – Stand & Next Steps

_Stand: 2026-07-17_

**Maßgeblicher Kontext: [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) (Exposé).** Diese Datei hält den *technischen Prototyp-Stand der Startphase* (Monat 1 / erste 2–3 Wochen) fest. Ziel, Scope, wissenschaftlicher Beitrag, Related Work, Datenstrategie, Evaluation, 6-Monats-Plan und Risiken stehen im Exposé.

**Forschungsfrage (Exposé):** Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue, nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu **bewerten** und zu **erzeugen** — möglichst ohne explizite Annotationen? Wissenschaftlicher Kern ist die **Übergangsmetrik / das Compatibility-Modell** (Monat 2–3), nicht Pipeline oder GUI.

**Wichtigstes Erfolgskriterium der Startphase (Exposé Abschn. 14):** Nach spätestens drei Wochen sollen *mehrere automatisch erzeugte* Übergänge *hörbar* sein und *systematisch verglichen* werden können.

Kurzfazit Prototyp: schlanke, im Kern lauffähige CLI-Pipeline für einen taktsynchronen Übergang zwischen zwei Songs. Analyse (librosa + aufTAKT) und vier Rendering-Baselines (Hard Cut, linearer Crossfade, Equal-Power-Crossfade und tempoangepasster Crossfade) mit Downbeat-/Bar-Alignment stehen — aber **Cutpoints noch manuell**, also noch nicht „automatisch erzeugt". Der Sprung zu *automatisch + vergleichbar* fehlt noch.

## Aktueller Stand (implementiert)

- **Projektstruktur / API / CLI**: `src/pipeline.py` bietet `render_transition()` als programmatischen Einstieg und argparse als CLI — lädt zwei Songs, analysiert, normalisiert, rendert und exportiert. Struktur `src/analysis/`, `src/cutting/`, `src/tempo/`.
- **Audio-I/O**: Laden über `librosa.load`, Export über `soundfile.write`; intern standardmäßig 44,1 kHz Stereo. Abweichende Sample-Raten werden resampelt, Mono wird auf Stereo erweitert und Beat-Positionen werden mit skaliert.
- **Beat-/Bar-Analyse** (`src/analysis/pre_analysis.py`):
  - librosa `beat_track` für BPM + Beats.
  - aufTAKT (`aufTAKTCl.exe`) für Taktposition; Nicht-WAV wird per ffmpeg konvertiert.
  - Merge beider Quellen zu bar-annotierten Beats (`sample, count_in_bar, beats_in_bar`); Abweichungen werden protokolliert.
  - Analyse-Cache per SHA-256-Hash des Songs (`00_pre_analysis.txt`), Diskrepanzen in `01_missing_beats.txt`.
- **Übergänge**:
  - `src/cutting/simple_cut.py`: Hard Cut, Snap auf den nächstgelegenen Downbeat, Bar-Alignment zwischen beiden Songs.
  - `src/cutting/fade_cut.py`: linearer Crossfade über N Beats (Default 8), Bar-aligned.
  - `src/cutting/equal_power_fade_cut.py`: Equal-Power-Crossfade.
  - `tempo_fade`: tonhöhenerhaltende Anpassung von Song B auf BPM von Song A, danach linearer Crossfade.
- **Tempo** (`src/tempo/`): Resample-basierte Variante (`SimpleTempoAdjust`, verändert Tonhöhe) und reparierter, eingebundener `TimeStretch` (tonhöhenerhaltend).
- **Tests**: `pytest`-Suite mit synthetischen Audiodaten prüft alle vier Renderer, Tempoanpassung, 48→44,1-kHz-Resampling, Mono→Stereo und den Fehlerpfad bei fehlenden Downbeat-Metadaten.
- **Dataset**: 21 Audiodateien liegen im ignorierten Ordner `musik/`; für alle 21 existiert eine gecachte Analyse unter `output/pre_analysis/` (plus ein veralteter zusätzlicher Cache `HELP_LESS`). Kuratierte Track-Notizen, Lizenzstatus und reproduzierbare Dataset-Definition fehlen noch.

### Verifiziert am 2026-07-17 (Codex, nach Rendering-Meilenstein)

- Python-Version der Projektumgebung: **3.14.2**.
- `.venv\Scripts\python.exe -m pytest -q`: **8 Tests bestanden**; zwei nicht blockierende Deprecation-Warnungen aus `audioread` unter Python 3.14.
- `.venv\Scripts\python.exe -m pip check`: keine defekten Abhängigkeiten; `pytest 9.1.1` ist installiert und in `requirements-dev.txt` festgehalten.
- CLI und programmatischer Import laufen; verfügbare Renderer: `simple`, `fade`, `equal_power`, `tempo_fade`.
- `aufTAKTCl.exe` und `tmp/` sind lokal vorhanden. `ffmpeg 8.1` ist über `PATH` auflösbar und wurde mit `ffmpeg -version` erfolgreich ausgeführt. Eine vorherige Prüfung innerhalb der eingeschränkten Codex-Dateisandbox lieferte wegen fehlendem Zugriff auf das WinGet-Paketverzeichnis fälschlich „nicht gefunden“.
- Reales Entwicklungsset gemessen: 20 Tracks mit 44,1 kHz Stereo, ein Track mit 48 kHz Stereo.
- Bereits vorhanden: `output/combined_song.wav` (375,84 s) und `output/cut_song.wav` (214,70 s), beide 44,1 kHz Stereo. Das ist noch kein systematischer Batch-Vergleich.

## Abgleich mit dem geplanten Systemablauf

| Komponente aus dem Exposé | Umsetzungsstand | Nachweis / Lücke |
|---|:--:|---|
| 1. Audioimport & Abschnittsauswahl | 🟡 | Zwei Audiodateien können verarbeitet werden; Abschnittsgrenzen sind manuelle Sample-Cutpoints. Mehrere Songs, Abschnittsobjekte und Reihenfolge-Constraints fehlen. |
| 2. Musikanalyse | 🟡 | BPM, Beats, Downbeats und Taktpositionen sind vorhanden. Phrasen-/Segmentgrenzen, Strukturtypen, Vocal-Aktivität und eine plattformunabhängige Downbeat-Lösung fehlen. |
| 3. Kandidatengenerierung | ❌ | Keine automatische Ableitung oder Filterung möglicher Übergangspunkte. |
| 4. Übergangsmetrik | ❌ | Weder Feature-Baseline noch Embedding-Metrik, Ranking oder Score-Komponenten implementiert. |
| 5. Rendering | ✅ | Alle vier im Exposé verlangten Baseline-Renderer sind implementiert und synthetisch getestet. Erweiterungen wie EQ, Filter oder Stems sind bewusst späterer Scope. |
| 6. Vorschau & Export | 🟡 | WAV-Export per CLI funktioniert. Batch-Export, Visualisierung, Inline-Playback, Auswahlworkflow und GUI fehlen. |

Damit ist die technische Grundlage aus Monat 1 weitgehend vorhanden. Das frühe Erfolgskriterium „automatisch erzeugt und systematisch vergleichbar“ ist noch nicht erfüllt, weil die Komponenten 3 und 6 fehlen. Der wissenschaftliche Kern aus Monat 2–3 (Komponente 4) wurde noch nicht begonnen.

## Fortschritt gegen die Startphase (Exposé Abschn. 13–14)

| Baustein | Status | Kurz |
|---|:--:|---|
| Reproduzierbares Repository | 🟡 | Git, MD-Doku und Requirements-Dateien vorhanden; aufTAKT und ffmpeg funktionieren lokal, sind aber externe Windows-Komponenten und ihre Einrichtung ist noch nicht automatisiert |
| Kleines Entwicklungsset (10–20 Tracks) | 🟡 | 21 lokale Audiodateien + Analyse-Caches vorhanden; Kuratierung, Track-Notizen, Rechte und reproduzierbare Definition fehlen |
| Beat-/Bar-Analyse | ✅ | librosa + aufTAKT-Merge, mit Diskrepanz-Log |
| Mehrere gerenderte Übergänge | 🟡 | Vier Renderer implementiert und synthetisch getestet — Cutpoints aber noch manuell |
| Automatische Kandidaten | ❌ | keine Ableitung aus Bar-/Phrasengrenzen (Exposé Abschn. 5) |
| Systematischer Vergleich / Höranalyse | ❌ | kein Batch-Export, keine Vergleichsoberfläche |
| Erste Baseline-Renderer (4 Stück) | ✅ | Hard Cut, linearer Crossfade, Equal-Power und tempoangepasster Crossfade getestet |
| Einfache Feature-Metrik | ❌ | offen (Monat 2) |
| Erste Embedding-Tests | ❌ | offen (Monat 3) |
| Liste typischer Fehlerfälle | 🟡 | nur punktuell (`Bemerkungen.md`) |
| Entscheidung ML-Fokus | ❌ | offen; Exposé priorisiert vortrainierte Embeddings zuerst |

## Bekannte Bugs / Baustellen

- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als zusätzliche einfache Baseline bewusst behandeln; `tempo_fade` verwendet den tonhöhenerhaltenden `TimeStretch`.
- **Downbeat-Metadaten erforderlich**: Fehlen aufTAKT-/Taktinformationen, bricht Downbeat-Snapping jetzt mit einer konkreten Fehlermeldung ab. Ein belastbarer plattformunabhängiger Fallback fehlt weiterhin.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Kandidatengenerierung).
- **Repo-/Cache-Hygiene**: Die früheren Track-Ordner sind im Arbeitsbaum gelöscht; unter `output/pre_analysis/` bleibt ein zusätzlicher veralteter Cache `HELP_LESS` ohne gleichnamigen aktuellen Audio-Stem.

## GUI-Frage: jetzt oder später? (Entscheidung)

**Empfehlung: noch kein echtes GUI — vom Exposé bestätigt** (GUI ist nur Interaktionsschicht; Risiko 15: „GUI-/Audio-Engineering verdrängt den Forschungsbeitrag"). Erst die Pipeline tragfähig machen und billig „sehen & hören" ermöglichen. Ein ausgebautes GUI lohnt sich erst, wenn Kandidaten + Metrik stehen und es einen Workflow gibt, den es einpackt (gerankte Kandidaten durchblättern, probehören, annehmen/verwerfen) — laut Zeitplan Monat 4.

Billiger Zwischenschritt statt GUI: `matplotlib`-Visualisierung (Waveform/Spektrogramm + (Down)Beats + Übergangsfenster) und ein Jupyter-Notebook (oder dünnes Streamlit/Gradio) mit Inline-Playback (`IPython.display.Audio`).

## Next Steps (priorisiert)

Ziel: das Startphasen-Erfolgskriterium erfüllen — die Schleife **automatische Kandidaten → mehrere rendern → anhören/vergleichen** schließen.

**Abgeschlossen am 2026-07-17:** programmatische Pipeline, Audio-Normalisierung, vier Rendering-Baselines, versionierter Rendering-Vertrag und automatisierte Tests.

1. **Kandidatenvertrag und Einheiten festlegen** — versioniertes, später additiv erweiterbares Kandidatenformat definieren; Beats, Takte und Phrasen eindeutig trennen. Mindestens Songreferenzen, Cutpoints, Übergangslänge, Grid-Metadaten, Filterstatus und Provenienz vorsehen.
2. **Kandidatengenerierung (Exposé Abschn. 5)** — aus Bar-Grenzen: letzte N Takte von A × erste N Takte von B, Längen 1/2/4 Takte; zunächst harte, messbare Filter für Beat-Grid und Tempo-Toleranz. Instabilität und Vocal-Overlap erst filtern, sobald dafür ein belastbares Signal definiert ist. **Kernbaustein, der aus dem manuellen Werkzeug ein automatisches macht.**
3. **Batch-Rendering** — alle Kandidaten × Renderer-Typen × Längen in einen Ordner exportieren, sinnvoll benannt und auf den Kandidaten zurückführbar.
4. **Anhören & Sehen** — Jupyter-Notebook mit Waveform/(Down)Beats-Plot + Inline-Playback; dabei die „Liste typischer Fehlerfälle" (Exposé Abschn. 14) sammeln.
5. **Entwicklungsset kuratieren (Exposé Abschn. 8)** — die vorhandenen 21 Tracks als reproduzierbares Set definieren, Varianz und Duplikate prüfen, Track-Notizen ergänzen und Lizenzfrage klären (parallel, eher Handarbeit).

Danach (nicht jetzt): **Feature-Metrik & Ranking** (Monat 2) auf genau diesen Kandidaten; **vortrainierte Embeddings** vergleichen, eigenes SSL-Fine-Tuning optional (Monat 3; Priorisierung laut Exposé Risiko 15: Pipeline+Baselines+Metrik zuerst).

## Offene Fragen / Entscheidungen (technisch)

- BPM-/Beat-Grid: was ist maßgeblich, wenn librosa und aufTAKT abweichen (HELP_LESS 161 vs. 157)?
- Übergangslänge intern in **Beats** oder **Takten** führen? (CLI erwartet aktuell Beats bei FadeCut.)
- Vocal-Overlap: eigene Vocal-Detektion oder als weiches Penalty in der Metrik? (Exposé: beides denkbar — harter Filter + Score-Penalty.)
- **aufTAKT (Windows-Binary) vs. plattformunabhängiges Downbeat-Tracking** (z. B. madmom) — Reproduzierbarkeit vs. Aufwand.
- Rechte an den Testtracks (HELP_LESS/BREATH_LESS) — eigene Produktion oder lizenzpflichtig? (Exposé Abschn. 8: rechtlich handhabbares Set nötig.)
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?

_Vom Exposé bereits beantwortet: Forschungsfrage, Scope/Abgrenzung, Rolle der GUI, Related-Work-Rahmen, Evaluationsansatz, ML-Priorisierung._
