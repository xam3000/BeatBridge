# BeatBridge – Stand & Next Steps

_Stand: 2026-07-17_

Schlanke, im Kern lauffähige CLI-Pipeline für **einen taktsynchronen Übergang zwischen zwei Songs**. Analyse (librosa + aufTAKT) und zwei Übergangstypen (Hard Cut, linearer Crossfade) mit Downbeat-/Bar-Alignment stehen. Automatische Kandidatenfindung, Filter, Übergangsmetrik, Evaluation und Visualisierung fehlen noch. Grob: **Actionplan-Schritte 2–4 großteils erledigt, 5–7 offen.**

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

## Fortschritt gegen den Actionplan

| Schritt | Thema | Status | Kurz |
|---|---|:--:|---|
| 1 | Scope & Erfolgskriterien | 🟡 | 2-Song-Fall + manuelle Cutpoints da; 1/2/4-Takt-Länge nur teilweise, Tempo-Vergleich & Vocal-Constraint offen |
| 2 | Technische Basis | ✅ | Git, MD-Files, CLI, Struktur, Audio-I/O, Analyse, Baseline-Übergänge stehen. Board fehlt, Metrik-/Eval-Modul fehlt |
| 3 | Dataset für Tests | 🟡 | 2 Testsongs vorhanden; strukturierte Pro-Track-Notizen fehlen noch |
| 4 | Beattracking | 🟡 | aufTAKT + librosa-Vergleich läuft; **Visualisierung fehlt**, Fehlerkatalog nur punktuell |
| 5 | Übergangskandidaten | ❌ | Cutpoints noch manuell; keine automatische Ableitung aus Bar-/Phrasengrenzen, keine Filter |
| 6 | Baseline-Renderer | 🟡 | Hard Cut ✓, linearer Crossfade ✓; Equal-Power & tempoangepasst fehlen, kein Batch-Export, keine systematische Höranalyse |
| 7 | Feature-Metrik & Ranking | ❌ | komplett offen (BPM-Diff, Chroma, Energie, Spektrum, Vocal-/Stretch-Penalty, Ranking) |

## Bekannte Bugs / Baustellen

- **Tempo-Anbindung tot & fehlerhaft**
  - `pipline.py → adjust_tempo()` referenziert `self.adjusted_song1` (nie gesetzt → `NameError`); die Methode wird im Ablauf nie aufgerufen.
  - `time_stretch.py → adjust_tempo_to_bpm()` greift auf `self.target_bpm` zu (nie im `__init__` gesetzt → Crash); Signatur weicht von `SimpleTempoAdjust` ab.
  - Alias `SimpleTempoAdjust = TimeStretch` am Dateiende ist irreführend.
- **Tonhöhe**: `SimpleTempoAdjust` (Resample) verändert die Tonhöhe — als Baseline ok, aber bewusst behandeln; die gewollte tonhöhen-erhaltende Variante (`TimeStretch`) ist die kaputte.
- **Downbeat-Fallback**: ohne aufTAKT-Daten (z. B. Nicht-WAV ohne ffmpeg) sind Beats reine Ints ohne Taktinfo → `is_downbeat` immer `False` → `snap_to_down_beat` fällt still auf „alle Beats" zurück.
- **BPM-Divergenz** (dokumentiert in `Bemerkungen.md`): librosa vs. aufTAKT (HELP_LESS: 161 vs. 157) — Grid-Wahl noch ungeklärt.
- **Phrasenlänge**: Raster 4 Beats, Phrasen aber meist 8 — relevant für plausible Übergangspositionen (Schritt 5).
- **Repo-Hygiene**: im Ordner `05 - HELP_LESS` liegt zusätzlich eine Kopie der `07 - BREATH_LESS.flac` (vermutlich versehentlich).
- **Tippfehler**: `pipline.py` (statt `pipeline.py`) — kosmetisch.

## GUI-Frage: jetzt oder später? (Entscheidung)

**Empfehlung: noch kein echtes GUI.** Erst die Pipeline tragfähig machen und billig „sehen & hören" ermöglichen. Ein ausgebautes GUI lohnt sich erst, wenn Schritt 5–7 stehen und es einen Workflow gibt, den es einpackt (durch gerankte Kandidaten blättern, probehören, annehmen/verwerfen).

Begründung:

- Der Kern ist noch nicht als Bibliothek nutzbar (nur CLI mit manuellen Sample-Cutpoints), und der Tempo-Pfad ist kaputt. Ein GUI auf dieser API bedeutet doppelte Arbeit.
- „Sehen & hören" ist Schritt 4 (Visualisierung) und fehlt komplett — der größte Hebel ist `matplotlib`, kein GUI.
- In 2–3 Wochen ist ein ausgebautes GUI ein Zeitfresser, der den eigentlichen Beitrag (Metrik/Evaluation, Schritt 7) nicht voranbringt.

**Empfohlene Reihenfolge (statt GUI zuerst):**

1. Pipeline als aufrufbare Funktion (zwei Dateien + Parameter → Audio + Beats) und Tempo-Pfad reparieren.
2. `matplotlib`-Visualisierung: Waveform/Spektrogramm + (Down)Beats + mögliche Übergangsfenster.
3. Jupyter-Notebook (oder dünnes Streamlit/Gradio), das beides zusammenbringt: Plots inline, Audio inline (`IPython.display.Audio`), Parameter tweaken und neu rendern.
4. Echtes GUI erst nach Schritt 5–7, wenn gerankte Kandidaten zum Durchblättern/Probehören da sind.

## Next Steps (priorisiert)

1. **Tempo-Pfad reparieren & einbinden** — `target_bpm` sauber durchreichen, toten `adjust_tempo()`-Zweig fixen, Tempo-Anpassung optional vor den Cut hängen. Damit wird der „tempoangepasste Übergang" aus Schritt 6 überhaupt testbar.
2. **Equal-Power-Crossfade** ergänzen (neben dem linearen) — kleiner Schritt, direkt vergleichbar.
3. **Automatische Kandidatenpunkte (Schritt 5)** — aus Bar-/Phrasengrenzen (4- und 8-Beat-Phrasen) Cutpoints ableiten statt manueller CLI-Eingabe; erste Filter: nur auf Beat-Grid, Tempo-Toleranz, instabile Analysebereiche ausschließen.
4. **Batch-Export** — für mehrere Songpaare × Übergangstypen × Längen (1/2/4 Takte) Beispiele rendern, um systematisch zu hören.
5. **Visualisierung (Schritt 4)** — Waveform/Spektrogramm mit (Down)Beats und Übergangsfenstern, um Tracking-Fehler schnell zu sehen.
6. **Feature-Metrik (Schritt 7)** — mit BPM-Diff + Beat/Bar-Alignment + Chroma-Ähnlichkeit + Energieverlauf starten, Kandidaten ranken, Ranking gegen Höreindruck prüfen.
7. **Dataset-Notizen (Schritt 3)** — pro Track: geschätztes Tempo, Beat-Qualität, Vocals, Abschnitte, Auffälligkeiten.

## Offene Fragen / Entscheidungen

- Welches BPM-/Beat-Grid ist maßgeblich, wenn librosa und aufTAKT abweichen?
- Übergangslänge intern in **Beats** oder **Takten** führen? (CLI erwartet aktuell Beats bei FadeCut, Plan spricht von 1/2/4 Takten.)
- Vocal-Overlap-Vermeidung: eigene Vocal-Detektion nötig oder als späteres Penalty in der Metrik?
- Board/Task-Übersicht (Trello o. ä.) — ja/nein?
