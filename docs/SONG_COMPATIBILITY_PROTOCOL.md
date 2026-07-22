# Songpaar-Kompatibilitätsprotokoll

_Vertragsversion: 1, eingeführt am 2026-07-22._

`rank_song_targets()` ist der Auswahl-Schritt **vor** der Cutpoint-Generierung. Für einen Source-Song ordnet er mehrere Target-Songs nach ihrer allgemeinen Eignung für einen Übergang. Die am besten bewerteten Paare werden anschließend mit `generate_transition_candidates()` und `feature_baseline_v3` feiner nach Cutpoints bewertet.

## Einstiegspunkt

```python
from src.ranking.song_compatibility import rank_song_targets

result = rank_song_targets(
    "musik/source.wav",
    ["musik/target_a.wav", "musik/target_b.wav"],
)
```

Jeder Score enthält die folgenden transparenten Komponenten:

| Komponente | Gewicht | Bedeutung |
|---|---:|---|
| `harmonic` | 0,35 | Ähnlichkeit der globalen Chroma-Profile |
| `tempo` | 0,25 | Geringe notwendige Tempoanpassung; ab 15 % Differenz ist der Teilscore 0 |
| `timbre` | 0,15 | Ähnlichkeit der mittleren Spektralschwerpunkte |
| `energy` | 0,15 | Ähnlichkeit der durchschnittlichen RMS-Lautheit |
| `rhythm` | 0,10 | Ähnlichkeit der normalisierten Onset-Verläufe |

Das Ergebnis ist ein Vorfilter, keine Qualitätsgarantie: Es bewertet ganze Songs, nicht einzelne Songabschnitte. Kandidatengenerierung und Cutpoint-Ranking bleiben für die endgültige Auswahl erforderlich.

## CLI

```powershell
.venv\Scripts\python.exe -m src.ranking.song_compatibility `
  "musik\05 - HELP_LESS.flac" `
  "musik\07 - BREATH_LESS.flac" "musik\08 - TARGET.flac"
```

Die Ausgabe ist nach Score absteigend geordnet. Fehler einzelner Target-Songs werden gemeldet, ohne die übrigen Rankings abzubrechen.
