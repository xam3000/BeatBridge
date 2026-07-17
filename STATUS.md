# BeatBridge – Stand & Next Steps

_Stand: 2026-07-17_

**Maßgeblicher Kontext: [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) (Exposé).** Diese Datei hält den *technischen Prototyp-Stand der Startphase* (Monat 1 / erste 2–3 Wochen) fest. Ziel, Scope, wissenschaftlicher Beitrag, Related Work, Datenstrategie, Evaluation, 6-Monats-Plan und Risiken stehen im Exposé.

**Forschungsfrage (Exposé):** Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue, nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu **bewerten** und zu **erzeugen** — möglichst ohne explizite Annotationen? Wissenschaftlicher Kern ist die **Übergangsmetrik / das Compatibility-Modell** (Monat 2–3), nicht Pipeline oder GUI.

**Wichtigstes Erfolgskriterium der Startphase (Exposé Abschn. 14):** Nach spätestens drei Wochen sollen *mehrere automatisch erzeugte* Übergänge *hörbar* sein und *systematisch verglichen* werden können.

Kurzfazit Prototyp: schlanke, im Kern lauffähige CLI-Pipeline für einen taktsynchronen Übergang zwischen zwei Songs. Analyse (librosa + aufTAKT) und zwei Übergangstypen (Hard Cut, linearer Crossfade) mit Downbeat-/Bar-Alignment stehen — aber **Cutpoints noch manuell**, also noch nicht „automatisch erzeugt". Der Sprung zu *automatisch + vergleichbar* fehlt noch.

## Aktueller Stand (implementiert)

- **Projektstruktur / CLI**: `src/pipline.py` als Einstieg (argparse) — lädt zwei Songs, analysiert, schneidet, exportiert. Struktur `analysis/`, `cutting/`, `tempo/`.
- **Audio-I/O**: Laden über `librosa.load`, Export über `soundfile.write`.
- **Beat-/Bar-Analyse** (`analysis/pre_analysis.py`):
  - librosa `beat_track` für BPM + Beats.
  - aufTAKT (`aufTAKTCl.exe`) für Taktposition; Nicht-WAV wird per ffmpeg konvertiert.
  - Merge beider Quellen zu bar-annotierten Beats (`sample, count_in_bar, beats_in_bar`); Abweichungen werden protokolliert.
  - Analyse-Cache per SHA-256-Hash des Songs (`00_pre_analysis.txt`), Diskrepanzen in `01_missing_beats.txt`.
- **Übergänge**:
  - `cutting/simple_cut.py`: Hard Cut, Snap auf Downbeat, Bar-Alignment zwischen beiden Songs.
  - `cutting/fade_cut.py`: linearer Crossfade über N Beats (Default 8), Bar-aligned.
- **Tempo** (`tempo/`): Resample-basiert (`SimpleTempoAdjust`, verändert Tonhöhe) und Time-Stretch (`TimeStretch`, tonhöhen-erhaltend) — **vorhanden, aber nicht eingebunden und teils fehlerhaft** (siehe Bugs).
- **Dataset**: zwei Testsongs (`05 - HELP_LESS`, `07 - BREATH_LESS`) als FLAC inkl. gecachter Analyse.

## Fortschritt gegen die Startphase (Exposé Abschn. 13–14)

| Baustein | Status | Kurz |
|---|:--:|---|
| Reproduzierbares Repository | 🟡 | Git + MD-Doku vorhanden; `requirements.txt`/`pyproject` fehlt, aufTAKT ist Windows-Binary |
| Kleines Entwicklungsset (10–20 Tracks) | ❌ | erst 2 Testsongs |
| Beat-/Bar-Analyse | ✅ | librosa + aufTAKT-Merge, mit Diskrepanz-Log |
| Mehrere gerenderte Übergänge | 🟡 | Hard Cut + linearer Crossfade — aber **manuell**, nicht automatisch |
| Automatische Kandidaten | ❌ | keine Ableitung aus Bar-/Phrasengrenzen (Exposé Abschn. 5) |
| Systematischer Vergleich / Höranalyse | ❌ | kein Batch-Export, keine Vergleichsoberfläche |
| Erste Baseline-Renderer (4 Stück) | 🟡 | 2 von 4 (Equal-Power & tempoangepasst fehlen) |
| Einfache Feature-Metrik | ❌ | offen (Monat 2) |
| Erste Embedding-Tests | ❌ | offen (Monat 3) |
| Liste typischer Fehlerfälle | 🟡 | nur punktuell (`Bemerkungen.md`) |
| Entscheidung ML-Fokus | ❌ | offen; Exposé priorisiert vortrainierte Embeddings zuerst |

## Bekannte Bugs / Baustellen

- **Tempo-Anbindung tot & fehlerhaft**
  - `pipline.py → adjust_tempo()` referenziert `self.adjusted_song1` (nie gesetzt → `NameError`); die Methode wird im Ablauf nie aufgerufen.
  - `time_stretch.py → adjust_tempo_to_bpm()` greift auf `self.target_bpm` zu (nie im `__init__` gesetzt → Crash); Signatur weicht von `SimpleTempoAdjust` ab.
  - Alias `SimpleTempoAdjust = TimeStretch` am Dateiende ist irreführend.
- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als Baseline ok, aber bewusst behandeln; die gewollte tonhöhen-erhaltende Variante (`TimeStretch`) ist die kaputte.
- **Downbeat-Fallback**: ohne aufTAKT-Daten (z. B. Nicht-WAV ohne ffmpeg) sind Beats reine Ints ohne Taktinfo → `is_downbeat` immer `False` → `snap_to_down_beat` fällt still auf „alle Beats" zurück.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Kandidatengenerierung).
- **Repo-Hygiene**: im Ordner `05 - HELP_LESS` liegt zusätzlich eine Kopie der `07 - BREATH_LESS.flac` (vermutlich versehentlich).
- **Tippfehler**: `pipline.py` (statt `pipeline.py`) — kosmetisch.

## GUI-Frage: jetzt oder später? (Entscheidung)

**Empfehlung: noch kein echtes GUI — vom Exposé bestätigt** (GUI ist nur Interaktionsschicht; Risiko 15: „GUI-/Audio-Engineering verdrängt den Forschungsbeitrag"). Erst die Pipeline tragfähig machen und billig „sehen & hören" ermöglichen. Ein ausgebautes GUI lohnt sich erst, wenn Kandidaten + Metrik stehen und es einen Workflow gibt, den es einpackt (gerankte Kandidaten durchblättern, probehören, annehmen/verwerfen) — laut Zeitplan Monat 4.

Billiger Zwischenschritt statt GUI: `matplotlib`-Visualisierung (Waveform/Spektrogramm + (Down)Beats + Übergangsfenster) und ein Jupyter-Notebook (oder dünnes Streamlit/Gradio) mit Inline-Playback (`IPython.display.Audio`).

## Next Steps (priorisiert)

Ziel: das Startphasen-Erfolgskriterium erfüllen — die Schleife **automatische Kandidaten → mehrere rendern → anhören/vergleichen** schließen.

1. **Pipeline aufrufbar machen + 4 Rendering-Baselines vervollständigen** — Pipeline als Funktion (zwei Dateien + Parameter → Audio + Beats), damit sie in einer Schleife läuft; Tempo-Pfad reparieren (siehe Bugs) und **Equal-Power-Crossfade** ergänzen, sodass alle vier Baselines (Hard Cut, linearer/Equal-Power-Crossfade, tempoangepasst) existieren.
2. **Kandidatengenerierung (Exposé Abschn. 5)** — aus Bar-Grenzen: letzte N Takte von A × erste N Takte von B, Längen 1/2/4 Takte; harte Filter (nur auf Beat-Grid, Tempo-Toleranz, instabile Bereiche ausschließen, optional Vocal-Overlap). **Kernbaustein, der aus dem manuellen Werkzeug ein automatisches macht.**
3. **Batch-Rendering** — alle Kandidaten × Renderer-Typen × Längen in einen Ordner exportieren, sinnvoll benannt.
4. **Anhören & Sehen** — Jupyter-Notebook mit Waveform/(Down)Beats-Plot + Inline-Playback; dabei die „Liste typischer Fehlerfälle" (Exposé Abschn. 14) sammeln.
5. **Entwicklungsset erweitern (Exposé Abschn. 8)** — von 2 auf 10–20 Tracks mit Varianz; Lizenzfrage klären (parallel, eher Handarbeit).

Danach (nicht jetzt): **Feature-Metrik & Ranking** (Monat 2) auf genau diesen Kandidaten; **vortrainierte Embeddings** vergleichen, eigenes SSL-Fine-Tuning optional (Monat 3; Priorisierung laut Exposé Risiko 15: Pipeline+Baselines+Metrik zuerst).

## Offene Fragen / Entscheidungen (technisch)

- BPM-/Beat-Grid: was ist maßgeblich, wenn librosa und aufTAKT abweichen (HELP_LESS 161 vs. 157)?
- Übergangslänge intern in **Beats** oder **Takten** führen? (CLI erwartet aktuell Beats bei FadeCut.)
- Vocal-Overlap: eigene Vocal-Detektion oder als weiches Penalty in der Metrik? (Exposé: beides denkbar — harter Filter + Score-Penalty.)
- **aufTAKT (Windows-Binary) vs. plattformunabhängiges Downbeat-Tracking** (z. B. madmom) — Reproduzierbarkeit vs. Aufwand.
- Rechte an den Testtracks (HELP_LESS/BREATH_LESS) — eigene Produktion oder lizenzpflichtig? (Exposé Abschn. 8: rechtlich handhabbares Set nötig.)
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?

_Vom Exposé bereits beantwortet: Forschungsfrage, Scope/Abgrenzung, Rolle der GUI, Related-Work-Rahmen, Evaluationsansatz, ML-Priorisierung._
