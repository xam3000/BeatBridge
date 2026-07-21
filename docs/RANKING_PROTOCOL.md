# Ranking-Protokoll

_Vertragsversion: 1, eingeführt am 2026-07-21._

Dieses Dokument beschreibt die transparenten Auswahl-Baselines zwischen Kandidatengenerierung und Rendering. Änderungen an Version 1 erfolgen nur additiv; inkompatible Änderungen benötigen eine neue `format_version`.

## `feature_baseline_v3` (aktuell)

Version 3 ergänzt die explizite **Drop-Bridge ohne High-Power-Überlappung**. Neben dem High-Power-Paar werden zwei getrennte Übergangsfenster analysiert:

- Source-High-Power: unmittelbar vor dem Source-Cut,
- Source-Auslauf: unmittelbar nach dem Source-Cut,
- Target-Vorlauf: unmittelbar vor dem Target-Cut,
- Target-High-Power: unmittelbar nach dem Target-Cut.

`non_overlap` kombiniert drei Bedingungen: Energieabfall von Drop A zum Source-Auslauf, Energieanstieg vom Target-Vorlauf zu Drop B und niedrige relative Energie beider Übergangsfenster. Für einen vollen Grenzscore sind standardmäßig 6 dB Abfall beziehungsweise Anstieg nötig.

| Komponente | Gewicht | Bedeutung |
|---|---:|---|
| `high_power` | 0,30 | Drop A und Drop B liegen im oberen Energiebereich ihrer Tracks |
| `non_overlap` | 0,30 | Energie fällt nach A ab, bleibt im Übergang niedrig und steigt vor B an |
| `harmonic` | 0,18 | Chroma-Kompatibilität der beiden Drops |
| `energy` | 0,10 | RMS-Kontinuität zwischen den Drops |
| `timbre` | 0,05 | Spektrale Ähnlichkeit der Drops |
| `tempo` | 0,07 | Tempo-Kompatibilität |

Die Messwerte enthalten unter anderem `source_drop_fall_db`, `target_drop_rise_db`, beide Transition-RMS-Werte und die relativen Energie-Perzentile aller vier Fenster.

## `feature_baseline_v2` (historisch)

Version 2 modelliert explizit den gewünschten Ablauf **High Power A → 2-/4-Takt-Übergang → High Power B**:

- Source-Merkmale stammen aus dem Fenster unmittelbar **vor** dem Source-Cutpoint.
- Target-Merkmale stammen aus dem gleich langen Fenster unmittelbar **nach** dem Target-Cutpoint.
- Das Fenster vor dem Target-Cutpoint ist der eigentliche Fade-/Übergangsbereich; sein RMS-Pegel wird als Diagnosewert gespeichert.
- `high_power` ist das Minimum der beiden relativen Energie-Perzentile. Jedes Fenster wird gegen die Energieverteilung seines eigenen Tracks eingeordnet; unterschiedliche Mastering-Lautheiten werden dadurch nicht direkt gleichgesetzt.

| Komponente | Gewicht | Bedeutung |
|---|---:|---|
| `high_power` | 0,40 | Beide angrenzenden Abschnitte sollen im oberen Energiebereich ihres Tracks liegen |
| `harmonic` | 0,25 | Kosinusähnlichkeit der Chroma-Profile der High-Power-Abschnitte |
| `energy` | 0,15 | RMS-Kontinuität zwischen den High-Power-Abschnitten |
| `timbre` | 0,10 | Ähnlichkeit ihrer spektralen Schwerpunkte |
| `tempo` | 0,10 | Lineare Abwertung der relativen BPM-Differenz bis 15 % |

Wiederholte Fenstermerkmale werden pro Lauf gecacht, weil der erweiterte Ziel-Suchraum viele Kandidaten erzeugt. Für Tracks mit weniger als 3 dB robuster Energiedynamik ist das relative Energie-Perzentil nicht aussagekräftig und wird neutral mit 0,5 bewertet.

## `feature_baseline_v1` (historisch)

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

- `ranker`: aktuell `feature_baseline_v3`,
- `config`: verwendete Gewichte und Skalierungsparameter,
- `scores`: Kandidaten-ID, Rang, Gesamtscore, Einzelkomponenten und Messwerte,
- `failures`: pro nicht bewertbarem Kandidaten Fehlertyp und Meldung.

`render_selection` hält zusätzlich fest, ob alle Kandidaten oder nur `top_k` gerendert wurden. Ein Rankingfehler bricht die Bewertung der übrigen Kandidaten nicht ab. Standardmäßig werden wegen des großen Ziel-Suchraums nur die Top 5 gerendert. Mit der programmatischen API kann `top_k=None` weiterhin alle Kandidaten rendern.

## Bewusste Grenzen

- Der Score ist keine kalibrierte Qualitätswahrscheinlichkeit und kein gelerntes Modell.
- Phrasenposition, Strukturtyp und Vocal-Overlap werden noch nicht gemessen.
- Das Ranking bewertet Cutpoint und Übergangsfenster, nicht den Renderer. Unterschiede zwischen Hard Cut, linearem Fade und Equal-Power-Fade werden über menschliche Bewertungen erfasst.
- Die Chroma-Ähnlichkeit ist eine einfache Harmonie-Baseline und berücksichtigt keine musikalisch differenzierte Tonartrelation.
- Die Fensterlänge wird aus BPM und Beatanzahl angenähert; sie verwendet noch nicht die exakten Beat-Grenzen aus der Analyse.

Damit ist die Baseline vor allem ein überprüfbarer Vergleichspunkt für spätere Feature-, Embedding- und lernbasierte Metriken.
