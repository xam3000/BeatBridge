# Batch-Rendering-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21._

Das Batch-Rendering ist die stabile Grenze zwischen Kandidatengenerierung und dem späteren Hörvergleich. Es rendert ausschließlich akzeptierte `TransitionCandidate`-Einträge und schreibt pro Lauf WAV-Dateien sowie ein vollständiges JSON-Manifest.

**Baselinefenster ab 19.11.2026.** Mit `BaselineCandidateGenerationConfig` oder im Paarbatch mit `--baseline-bars 1 2 3 4` prüft der Generator jede Länge einzeln. Jede vorgeschlagene Grenze braucht auf beiden Seiten die gewünschte Anzahl vollständiger, zusammenhängender 4/4-Takte. Das Manifest kennzeichnet die Kandidaten mit `baseline_bar_grid_v3` und Format 3. Beim Fade beginnt A am Source-Cue, B endet am Target-Cue. Die Überlagerung dauert so lange wie das kürzere der beiden tempoangepassten Fenster. Der harte Schnitt hat null Überlagerung. Für den historischen Candidate-v2-Export gilt dessen eigener Vertrag mit gleichen Fensterlängen. Feste Controller verwenden weiterhin vier Takte.

## Ausgabe-Struktur

Beim MERT-Batch beziehen sich `candidate_rank` und `candidate_score` auf die Regelbewertung im gemeinsamen, von unvollständigen MERT-Fenstern bereinigten Pool. `selection_rank` und `selection_score` stammen vom Studienkopf. Auf dev01 sind alle 144 generierten Cues zulässig. Ab P10 run02 protokolliert `cue_ranking.provenance.encoder_runtime` CUDA-Gerät, GPU, bf16-Autocast, Pooling- und Kopfpfad. Ohne native CUDA-bf16-Unterstützung bricht die Studieninferenz ab.

Der F2-Auswertungsvertrag für P10 verwendet für Recall@1 und MRR jede Quellaufnahme (eindeutiger Datei-SHA) als Einheit und für die Kontrollquoten jede Recording-Gruppe. Das zusätzliche Gruppenmittel für Recall steht im P10-Bericht. Maßgeblich für die Auswahl ist die spezifische F2-Regel im eingefrorenen P01-Protokoll.

Für den Vier-Takt-Studienkopf wählt der Paarbatch `--ranking-method mert_continuation_v1` und verwendet standardmäßig den lokal bestätigten partiellen aufTAKT-Analysevertrag. Die MERT-Laufzeit aus P07 muss im Pythonpfad liegen. Die Inferenz lädt die [P10-Auswahl](masterarbeit/review_jp_20261118/p10/selection.json), prüft Modellrevision und Gewichts-SHA und extrahiert je Original die 24-kHz-Taktzustände. Die vier Takte vor S und die vier Takte ab T werden getrennt kodiert. Die Score-Reihenfolge ist absteigend, bei Gleichstand entscheidet die Kandidaten-ID. Regel und MERT erhalten die gemeinsam gültigen Cues. Das Manifest enthält die Regel in `candidate_ranking`, MERT samt Herkunft und Fensterausschlüssen in `cue_ranking` und die verwendete Methode sowie den MERT-Rang an jedem gerenderten Eintrag. Im Mehrsongbatch sind zusätzlich `--transition-bars 4` erforderlich. [Vollständiger CLI-Aufruf und echter Render](masterarbeit/REVIEW_JP_P10_RANKING_20261119.md#batch-render-und-reproduktion)

```text
output/batches/help_to_breath/
├── manifest.json
├── ratings.json                 # optional, nach menschlicher Bewertung
└── rendered/
    ├── 0001__candidate-…__simple.wav
    ├── 0001__candidate-…__fade.wav
    └── …
```

Der Nummernpräfix folgt der deterministischen Kandidatenreihenfolge. Der Dateiname enthält zusätzlich Kandidaten-ID und Renderer, sodass jede WAV-Datei ohne Kontext dem Manifest zugeordnet werden kann.

## `manifest.json`

Das Manifest hat `format_version = 1` und enthält:

| Feld | Bedeutung |
|---|---|
| `renderers` | In diesem Lauf angeforderte Renderer |
| `render_protocol_version` | Semantik der gerenderten Audiodateien; aktuell Version 5 mit Bridge-Crossfade, Rubber-Band-Tempoanpassung und kurzer Vorschau |
| `ranking_method` | Auswahlmethode; ohne explizite Auswahl `feature_baseline_v3` |
| `candidate_generation` | Vollständiges Ergebnis nach `CANDIDATE_PROTOCOL.md`, einschließlich abgelehnter Kandidaten |
| `candidate_ranking` | Feature-Ränge, Einzelkomponenten, Messwerte und Rankingfehler nach `RANKING_PROTOCOL.md` |
| `cue_ranking` | Additives Format 1 für `learned_cue_ranker_v1`, einschließlich Checkpoint-/Run-/Dataset-/Teacher-SHAs, Candidate-Scores, Auswahl-IDs und Preflight/Backfill |
| `rendered_transition_ranking` | Rangfolge der tatsächlich gerenderten Varianten samt Teilwerten und Fehlern nach `RENDERED_TRANSITION_METRIC_PROTOCOL.md` |
| `render_selection` | Gerenderte Kandidaten-IDs und optionales `top_k` |
| `render_preview` | Vorschau-Kontext in Sekunden vor/nach dem Source-Cutpoint |
| `rendered_variants` | Erfolgreiche Exporte: Kandidaten-ID, Renderer, relativer Dateipfad, Sample-Rate, Sample-Anzahl, Rendergrenzen, tatsächlich verwendetes `tempo_backend` sowie beide Ranking-Ergebnisse |
| `failures` | Pro fehlgeschlagener Variante Fehlertyp, Meldung, Kandidaten-ID und Renderer |

`rendered_variants` enthält additiv `candidate_rank`/`candidate_score` für die
Bewertung vor dem Rendering und `transition_rank`/`transition_score` für die
Bewertung des fertigen Audios. Die tatsächlichen Grenzen im WAV stehen als
`transition_start_sample` und `transition_end_sample` daneben. Ein Lauf ohne
akzeptierte Kandidaten erzeugt trotzdem ein Manifest. So bleiben harte
Filterentscheidungen nachvollziehbar. Einzelne fehlgeschlagene Render- oder
Metrikvarianten brechen die übrigen unabhängigen Exporte nicht ab, werden aber
sichtbar im Manifest erfasst und führen in der CLI zu Exit-Code `1`.

Bei `learned_cue_ranker_v1` bleibt `candidate_ranking` semantisch die
historische `feature_baseline_v3`. Die Learned-Auswahl steht ausschließlich in
`cue_ranking.selection_candidate_ids`; `selection_rank`, `selection_score` und
`selection_method` werden additiv pro gerenderter Variante geführt. Harte
Candidate-Filter werden vor der Learned-Inferenz geprüft und können vom Modell
nicht umgangen werden.

Für die gelernte Auswahl werden nach Modellscore geordnete Kandidaten so lange
versucht, bis `top_k` Kandidaten mindestens eine angeforderte Renderervariante
erfolgreich exportiert haben. Schlägt für einen Kandidaten jeder angeforderte
Renderer fehl, wird er als `render_failed` übersprungen und der nächste Score
deterministisch als Backfill versucht. Das Feld
`cue_ranking.renderability_preflight` dokumentiert dafür `rendered`,
`render_failed`, `not_attempted_after_top_k` und `score_failed`; `backfill`
enthält die versuchten und übersprungenen IDs sowie einen sichtbaren
Partial-Status. Der historische `feature_baseline_v3`-Pfad behält seine feste
Top-K-Auswahl ohne dieses Learned-Backfill.

Für `src.multi_batch_render` gilt dieselbe Prozesssemantik additiv auf der
Wurzelebene: Alle unabhängigen Sources und Paare werden soweit möglich
weiterverarbeitet und das Wurzelmanifest wird final atomar geschrieben.
Danach liefert die CLI Exit-Code `1`, sobald das Manifest mindestens einen
BPM-Analyse-, Source-, Paar-, Render- oder Render-Metrikfehler dokumentiert.
Exit-Code `0` bedeutet damit, dass der Lauf keine Fehler aufgezeichnet hat;
reguläre Policy-/BPM-Ausschlüsse und SHA-Duplikate gelten nicht als Fehler.

## Schreib- und Überschreiberegeln

- Audio und Manifest werden zuerst in einer temporären Datei geschrieben und anschließend atomar an ihren Zielpfad verschoben.
- Bestehende Dateien werden standardmäßig **nicht** überschrieben. Der Lauf bricht vor dem ersten Export mit einer konkreten Fehlermeldung ab.
- Nur die explizite CLI-Option `--overwrite` beziehungsweise der API-Parameter `overwrite=True` erlaubt das Ersetzen gleichnamiger Exportdateien.
- Quelldateien bleiben unverändert; sie werden ausschließlich gelesen.

## Programmatische API

```python
from src.batch_render import generate_and_render_batch

result = generate_and_render_batch(
    "musik/song_a.wav",
    "musik/song_b.wav",
    "output/batches/song_a_to_song_b",
    renderers=("simple", "fade", "equal_power"),
)
print(result.manifest_path)
```

Die Funktion verwendet Kandidatengenerierung, Feature-Ranking, Rendering und
danach `rendered_transition_baseline_v1` auf dem vollständigen Renderergebnis
im Speicher. Für jeden Renderer werden die im Kandidaten gespeicherten BPM
verwendet und Song B tonhöhenerhaltend auf Song A angepasst. Standardmäßig
enthält jede WAV fünf Sekunden vor und zwölf Sekunden nach dem Source-Cutpoint;
die Werte stehen auditierbar im Manifest und sind über die API beziehungsweise
CLI konfigurierbar. Standardmäßig werden nur die fünf bestbewerteten Kandidaten
gerendert; das Manifest enthält weiterhin alle erzeugten Kandidaten und Scores.
`top_k=None` rendert über die programmatische API alle Kandidaten. Für
fortlaufende Experimente sollte jeder Lauf einen neuen Ausgabepfad erhalten.

Seit Rendering-Protokoll 5 verwendet die Tempoanpassung zuerst FFmpeg mit
`librubberband` und fällt bei einem Fehler auf das eigenständige
`rubberband`-CLI mit R3-Engine zurück. Der tatsächlich genutzte Pfad steht pro
Variante als `tempo_backend` im Manifest. Historische Manifeste vor Version 5
besitzen dieses additive Feld nicht.

## Additive Candidate-v2-Batches

Ein Batch mit `bar_grid_v2_length_specific` verwendet additiv
`format_version = 2` und `render_protocol_version = 6`. Jede gerenderte
Variante speichert neben Candidate-ID und Rendergrenzen auch
`transition_length_bars` sowie die daraus abgeleitete
`transition_length_beats`. Bestehende v1-Batchroots werden nicht umgeschrieben;
die Ausgabeprüfung verlangt weiterhin einen neuen Zielordner oder ein
explizites Überschreibflag.

## Additive Multi-Song-Variable-Längen

`src.multi_batch_render.generate_multi_song_batch()` akzeptiert additiv
`transition_lengths_bars=(2, 4)`. Die API und CLI validieren das angeforderte
Set über den zentralen Candidate-v2-Längenvertrag; zulässig sind ausschließlich
`2`, `4`, `6` und `8`. Das Root-Manifest speichert die sortierte Liste unter
`transition_lengths_bars`.

Der unveränderte Aufruf ohne Option verwendet weiterhin den v1-
`CandidateGenerationConfig`-Pfad mit genau `(2, 4)`. Wird mindestens eine
6- oder 8-Takt-Länge angefordert, verwendet jedes unabhängige Paar additiv
`VariableCandidateGenerationConfig` und erzeugt ein Candidate-v2-
Paarmanifest. Die Längenprüfung findet pro Länge und pro Boundary statt;
fehlender langer Kontext verwirft daher keine gültigen kürzeren Kandidaten.
Bestehende Multi-Batch-Roots werden nicht aktualisiert oder überschrieben.
