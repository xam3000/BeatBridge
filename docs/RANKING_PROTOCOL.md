# Ranking-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21._

Dieses Dokument beschreibt die erste transparente Auswahl-Baseline zwischen Kandidatengenerierung und Rendering. Änderungen an Version 1 erfolgen nur additiv; inkompatible Änderungen benötigen eine neue `format_version`.

## `feature_baseline_v1`

Für jeden akzeptierten Kandidaten werden die beiden Audiofenster unmittelbar **vor** den Cutpoints analysiert. Die Fensterlänge entspricht näherungsweise der Übergangslänge in Beats bei der jeweiligen Track-BPM. Der Score liegt zwischen 0 und 1 und setzt sich zusammen aus:

| Komponente | Gewicht | Bedeutung |
|---|---:|---|
| `harmonic` | 0,35 | Kosinusähnlichkeit der gemittelten Chroma-Profile |
| `energy` | 0,30 | Ähnlichkeit der RMS-Pegel; bei 24 dB Differenz erreicht die Komponente 0 |
| `timbre` | 0,20 | Ähnlichkeit der mittleren spektralen Schwerpunkte |
| `tempo` | 0,15 | Lineare Abwertung der relativen BPM-Differenz bis 15 % |

Der Gesamtscore ist die gewichtete Summe. Gleichstände werden deterministisch über die `candidate_id` aufgelöst. Neben dem Gesamtscore bleiben Einzelkomponenten und Rohmessungen im Manifest erhalten.

## Manifest-Feld `candidate_ranking`

Das bestehende Batch-Manifest Version 1 wird additiv um `candidate_ranking` ergänzt:

- `ranker`: aktuell `feature_baseline_v1`,
- `config`: verwendete Gewichte und Skalierungsparameter,
- `scores`: Kandidaten-ID, Rang, Gesamtscore, Einzelkomponenten und Messwerte,
- `failures`: pro nicht bewertbarem Kandidaten Fehlertyp und Meldung.

`render_selection` hält zusätzlich fest, ob alle Kandidaten oder nur `top_k` gerendert wurden. Ein Rankingfehler bricht die Bewertung der übrigen Kandidaten nicht ab. Ohne `--top-k` werden auch nicht bewertbare akzeptierte Kandidaten nach den erfolgreich gerankten Kandidaten gerendert.

## Bewusste Grenzen

- Der Score ist keine kalibrierte Qualitätswahrscheinlichkeit und kein gelerntes Modell.
- Phrasenposition, Strukturtyp und Vocal-Overlap werden noch nicht gemessen.
- Das Ranking bewertet Cutpoint und Übergangsfenster, nicht den Renderer. Unterschiede zwischen Hard Cut, linearem Fade und Equal-Power-Fade werden über menschliche Bewertungen erfasst.
- Die Chroma-Ähnlichkeit ist eine einfache Harmonie-Baseline und berücksichtigt keine musikalisch differenzierte Tonartrelation.
- Die Fensterlänge wird aus BPM und Beatanzahl angenähert; sie verwendet noch nicht die exakten Beat-Grenzen aus der Analyse.

Damit ist die Baseline vor allem ein überprüfbarer Vergleichspunkt für spätere Feature-, Embedding- und lernbasierte Metriken.
