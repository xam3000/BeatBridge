# Beat-synchroner Featurevertrag

_Vertragsversion 1, eingeführt am 2026-07-30._

Dieser Vertrag definiert die Eingaben eines späteren
Feature→Control-Modells. Die kanonische, maschinenlesbare Reihenfolge steht in
`src/features/contract.py`. Änderungen an Namen, Reihenfolge, Bedeutung,
Normalisierung oder Geometrie benötigen eine neue Vertragsversion.

Der Vertrag definiert noch kein trainiertes Feature→Control-Modell.

Seit 2026-07-30 implementiert `src/features/extract_track.py` die
deterministischen Timing-, Energie-, Spektral-/Rhythmus- und Harmonikgruppen
als wiederverwendbaren Volltrack-Cache. Seit Extractor-Version 2 kann der
vortrainierte `htdemucs`-Vocal-Backend aktiviert werden. Die musikalischen
Phrasenkanäle bleiben explizit ungültig, bis ein semantisch passendes und
technisch reproduzierbares Backend validiert ist. Modell- und
Zitierprovenienz: [`PRETRAINED_MODELS.md`](./PRETRAINED_MODELS.md).

## 1. Tensorvertrag

Ein Beispiel enthält:

```text
features_a:      float32 (32, 54)
features_b:      float32 (32, 54)
global_features: float32 (16,)
```

Im Batch kommt eine führende Dimension hinzu. Alle Werte sind endlich; `NaN`
und implizite Ersatzwerte sind verboten. Fehlende Analysen werden mit null
gefüllt und durch die zugehörige Gültigkeitsmaske markiert.

`54` und `16` ergeben sich aus den unten definierten skalaren Kanälen. Sie
sind keine vorab gewählten Zielgrößen.

## 2. Musikalische Geometrie

Die gerenderte Bridge umfasst vier 4/4-Takte:

```text
4 Takte × 4 Beats × 2 Schritte pro Beat = 32 Halbbeat-Schritte
```

Die Cue Points bedeuten weiterhin:

- Source-Cue: Ende Drop A / Beginn Source-Postroll,
- Target-Cue: Ende Target-Preroll / Beginn Drop B.

Die modellierten Sequenzen sind chronologisch auf dieselbe Bridge ausgerichtet:

```text
features_a[i] = Source A nach dem Source-Cue, Halbbeat i
features_b[i] = Target B vor dem Target-Cue, Halbbeat i
```

`features_a[0]` und `features_b[0]` liegen somit am Anfang der Bridge;
`features_a[31]` und `features_b[31]` unmittelbar vor deren Ende.

Der Extractor muss je Track acht Takte Kontext untersuchen:

```text
vier Takte vor dem Cue + vier Takte nach dem Cue
```

Nur die 32 Bridge-Schritte werden an das Modell übergeben. Der zusätzliche
Kontext dient zur Bestimmung von Vocal-Phrasen, 8-Takt-Phrasenposition,
Lautheitsdifferenzen und Ableitungen an den Cue-Grenzen. Fehlender Randkontext
steht in `context_coverage_a/b`.

Track B wird vor der lokalen Featureextraktion mit demselben versionierten
Time-Stretch-Backend und derselben BPM-Geometrie ausgerichtet, die auch der
Renderer verwendet. Original-BPM und Tempoänderung bleiben in den globalen
Features erhalten.

## 3. Zeitabhängige Features pro Track

Die Kanalreihenfolge ist stabil und gruppiert:

| Gruppe | Anzahl | Kanäle |
|---|---:|---|
| Timing | 9 | `transition_position`, Beat- und Taktphase als Sin/Cos, 8-Takt-Phrasenphase als Sin/Cos, Distanz zur Phrasengrenze, Phrasen-Confidence |
| Energie | 9 | absolutes und trackrelatives RMS, Lautheitsslope, Low/Mid/High-Energieanteil, Energieperzentil, Crest-Faktor, Silence Probability |
| Spektrum/Rhythmus | 8 | Centroid, Bandwidth, Rolloff, Flatness, Flux, Onset Strength, Kick Prominence, Beat-Pulse-Confidence |
| Harmonik | 19 | 12 L1-normalisierte Chroma-Kanäle (`00 = C`), 6 Tonnetz-Koordinaten, Harmonic Ratio |
| Vocals | 6 | Activity, Prominence, Onset, Offset, Phrase Progress, Confidence |
| Gültigkeit | 3 | `audio_valid`, `phrase_valid`, `vocal_valid` |
| **Gesamt** | **54** | |

Exakte Kanalnamen, Indizes, Wertebereiche, Normalisierungsformeln und
Kurzbeschreibungen liefert:

```python
from src.features import FEATURE_DEFINITIONS, feature_index
```

### 3.1 Timing

`transition_position` verwendet die Halbbeat-Mitte `(i + 0.5) / 32`.
Periodische Positionen werden als Sinus und Kosinus kodiert, damit am
Takt-/Phrasenwechsel kein künstlicher großer Sprung entsteht.

Die Phrasenphase bezieht sich auf eine erkannte 8-Takt-Phrase und nicht auf
`bar_index modulo 8`. Ist keine belastbare Phrase bekannt:

```text
phrase_phase_sin = 0
phrase_phase_cos = 0
distance_to_phrase_boundary = 0
phrase_confidence = 0
phrase_valid = 0
```

Ein approximatives 4/4-Beat-Raster darf deshalb nicht still eine angeblich
erkannte 8-Takt-Phrase erzeugen.

### 3.2 Energie und Frequenzbänder

Frequenzbänder sind:

```text
low:   f < 180 Hz
mid:   180 Hz <= f < 4 kHz
high:  f >= 4 kHz
```

Die drei Energieanteile verwenden dieselbe Spektralleistung und summieren sich
bei `audio_valid = 1` bis auf numerische Toleranz zu eins. Absolute Energie
bleibt über `rms_dbfs` erhalten; `rms_db_relative` und das Perzentil reduzieren
Mastering-Abhängigkeit.

`loudness_slope`, `spectral_flux` und Vocal-Onset/-Offset dürfen für den ersten
Bridge-Schritt auf den vorhergehenden Kontext zugreifen. Dadurch bleiben
Änderungen direkt am Cue sichtbar.

### 3.3 Harmonik

Die Chroma-Reihenfolge ist:

```text
C, C#, D, D#, E, F, F#, G, G#, A, A#, B
```

Bei fehlender tonaler Evidenz werden Chroma, Tonnetz und `harmonic_ratio` null
gesetzt; `audio_valid` bleibt davon unabhängig. Key-Confidence wird global
geführt.

## 4. Vocal-Featuregruppe

Vocal-Merkmale sind für Version 1 explizit Teil des Inputs:

| Kanal | Bedeutung |
|---|---|
| `vocal_activity` | begrenzter Aktivitätsscore dafür, dass im Halbbeat Gesang aktiv ist |
| `vocal_prominence` | Stärke der Vocal-Komponente relativ zum Gesamtmix |
| `vocal_onset_probability` | aus dem Aktivitätsanstieg abgeleiteter Onset-Score |
| `vocal_offset_probability` | aus dem Aktivitätsabfall abgeleiteter Offset-Score |
| `vocal_phrase_progress` | Fortschritt innerhalb einer erkannten Vocal-Phrase |
| `vocal_confidence` | Margin-Confidence des abgeleiteten Aktivitätsscores |

Eine reine Activity-Maske reicht nicht: Die Hörtests zeigten unterbrochene
Lyrics und Vocal-Clashes. Onset, Offset und Phrase Progress sollen
unterscheiden, ob ein Gesangsteil sicher beendet ist oder durch den Cue
zerschnitten wird.

Das Produkt `vocal_activity_a * vocal_activity_b` ist ein erklärbares
Vocal-Overlap-Signal. Es muss nicht als zusätzlicher Eingangskanal gespeichert
werden, weil die Pairwise-Fusion es aus beiden Sequenzen bilden kann.

Ist kein gültiger Vocal-Extractor verfügbar, werden alle sechs Vocal-Kanäle
null und `vocal_valid = 0`. Solche Beispiele sind für technische Smoke-Tests
zulässig, aber nicht für den finalen Training-/Evaluationssatz des
Vocal-Experiments.

Der aktive Backend `demucs_energy_activity_v1` verwendet den von
`htdemucs` geschätzten Vocal-Stem. Pro Halbbeat werden Vocal- und Mix-RMS
verglichen; ein absolutes und relatives Energiegate erzeugt den
Aktivitätsscore. Onset/Offset sind gerichtete Differenzen des geglätteten
Scores, Phrase Progress läuft innerhalb zusammenhängender aktiver Regionen.
Diese Größen liegen in `[0, 1]`, sind aber noch nicht gegen annotierte
Vocal-Wahrscheinlichkeiten kalibriert. Entsprechend dürfen sie in der Arbeit
nicht als native Demucs-Outputs oder als kalibrierte Wahrscheinlichkeiten
bezeichnet werden.

## 5. Globale Features

Der globale Vektor enthält 16 skalare Werte:

```text
bpm_a
bpm_b
tempo_ratio_b_over_a
tempo_change_abs
tempo_adjustment_required
key_tonic_a_sin
key_tonic_a_cos
key_tonic_b_sin
key_tonic_b_cos
key_mode_a
key_mode_b
key_confidence_a
key_confidence_b
harmonic_compatibility
context_coverage_a
context_coverage_b
```

Der Time-Stretch-Backendname ist Provenienz, kein numerischer Modellinput. Das
Modell erhält stattdessen Richtung und Betrag der Tempoänderung. Experimente
mit verschiedenen Backends benötigen getrennte Dataset-/Renderer-Versionen.

Die globalen Werte werden durch `global_pair_v1` berechnet. Tonika und Modus
stammen aus den lokalen 32-Schritt-Chromaprofilen und
Krumhansl-Schmuckler-Templates; die Confidence ist der begrenzte Abstand der
beiden besten Templates. `harmonic_compatibility` ist die Cosinusähnlichkeit
der lokalen Chromaprofile und bei fehlender Evidenz neutral `0,5`.
`context_coverage_a/b` zählt die tatsächlich vorhandenen Halbbeat-Bins relativ
zu den angeforderten vier Takten vor plus vier Takten nach dem Cue.

## 6. Normalisierung und Datenlecks

- Physikalisch begrenzte Größen verwenden die im Schema definierten festen
  Transformationen.
- `spectral_flux` und `onset_strength` verwenden ausschließlich das
  99. Perzentil des **Trainingssplits**. Die Statistik wird danach eingefroren
  und unverändert auf Validation und Test angewendet.
- Trackrelative Statistiken dürfen den vollständigen einzelnen Track
  verwenden, aber keine anderen Tracks oder Hörbewertungen.
- Splits erfolgen trackweise: Kein Track darf über verschiedene Rollen oder
  Paarungen in mehr als einem von Train, Validation und Test vorkommen.
- Alle Normalisierungsstatistiken werden mit Namen, Wert, Split-Hash und
  Extractor-Version im Dataset-Manifest gespeichert.

## 7. Erforderliche Provenienz

Jedes gespeicherte Featurebeispiel muss mindestens dokumentieren:

```text
feature_protocol_version
source/target path und SHA-256
Source-/Target-Cue auf dem 44,1-kHz-Raster
Source-/Target-BPM
Beat-/Bar-Analyseversion
Time-Stretch-Backend und Rendering-Protokoll
Extractor-ID und Version je Featuregruppe
Normalisierungsmanifest und Split-ID
features_a/features_b/global_features Shape und dtype
Gültigkeits- und Context-Coverage-Werte
```

Eine Änderung am Vocal-, Phrasen-, Beat-, Spektral- oder Time-Stretch-Backend
erzeugt einen neuen Datasetlauf. Bestehende Featureartefakte werden nicht
stillschweigend überschrieben.

## 8. Validierung

```python
from src.features import (
    validate_feature_array,
    validate_global_feature_array,
)

validate_feature_array(features_a)
validate_feature_array(features_b)
validate_global_feature_array(global_features)
```

Die Validatoren prüfen Dimension, Gleitkomma-Datentyp, endliche Werte und
kanalspezifische Wertebereiche. Semantische Prüfungen des späteren Extractors
müssen zusätzlich unter anderem Bandanteilssumme, Cue-Ausrichtung,
Phrasenmasken und reproduzierbare Hashes testen.

## 9. Volltrack-Featurecache

Teure Audiofeatures werden nicht pro Songpaar oder Cue Point neu berechnet.
Ein Cacheeintrag repräsentiert einen vollständigen Track auf seinem
Halbbeat-Raster:

```text
output/feature_cache/
└── feature_protocol_v1/
    └── <source-sha-prefix>/
        └── <config-hash>/
            ├── manifest.json
            └── track_features.npz
```

Der Konfigurationshash umfasst mindestens:

```text
Audio-SHA-256
Feature-Protokoll
Extractor-Version
Rendering-Protokoll
Sample-Rate
Original- und ausgerichtete BPM
Hash des ausgerichteten Beat-Grids
Beat-Grid-Provenienz (`grid_source`, `fallback_used`, Backend-Version, Confidence)
Time-Stretch-Policy
Vocal-Backend, Modellname und Vocal-Stem-Hash
```

Eine andere Audiodatei, ein anderes Grid, eine andere Grid-Herkunft, eine
andere Ziel-BPM oder eine Extractor-/Protokolländerung erzeugt deshalb einen
neuen Eintrag. Vorhandene Caches werden nicht überschrieben. Das Manifestfeld
`beat_grid_metadata` folgt `ANALYSIS_PROTOCOL.md`; historische Herkunft wird
nicht aus den Rasterkoordinaten geraten.

`track_features.npz` enthält:

- normalisierte, bereits begrenzte Basiskanäle für alle vollständigen
  Halbbeat-Bins,
- Samplegrenzen jedes Bins,
- rohe `spectral_flux`- und `onset_strength`-Werte.

Die beiden unbeschränkten Rohkanäle werden bewusst erst beim Ausschneiden
eines Modellfensters mit dem eingefrorenen 99. Perzentil des Trainingssplits
normalisiert. Das Audio muss dafür nicht erneut analysiert werden.

Source- und Target-Fenster werden aus demselben Artefakt geschnitten:

```python
source = artifact.model_window(
    source_cue,
    role="source",
    normalization=train_stats,
)
target = artifact.model_window(
    target_cue,
    role="target",
    normalization=train_stats,
)
```

Bei `role="source"` beginnen die 32 Schritte am Cue; bei `role="target"` enden
sie am Cue. Cue Points müssen auf einer gespeicherten Halbbeat-Grenze liegen.

Track B mit einer anderen Ziel-BPM erhält einen getrennten Cacheeintrag der
tatsächlich mit dem Renderer-Backend tempoangepassten Volltrack-Waveform.
Wiederholte Verwendungen mit derselben Ziel-BPM nutzen diesen Eintrag erneut.

Der teure Demucs-Lauf liegt eine Ebene darüber als song- und modellabhängiges
Artefakt:

```text
output/feature_cache/model_artifacts/demucs_vocal_v1/
└── <source-sha-prefix>/<config-hash>/
    ├── manifest.json
    └── vocal_stem.npz
```

Der Stem wird deshalb auch dann nicht neu berechnet, wenn derselbe Song mit
anderen Cue Points oder mehreren Ziel-BPMs verwendet wird. Eine
tempoangepasste Zielvariante stretcht Mix und gecachten Vocal-Stem mit
derselben Renderer-Policy. Das Stem-Manifest enthält die exakte
Hugging-Face-Revision und SHA-256-Hashes der verwendeten Gewichtsdateien.

## 10. Noch nicht Teil von Version 1

- Section-Type-Klassen wie Drop, Break oder Build-up,
- gelernte Audio-Embeddings,
- Lyrics-/Phonem-Inhalte,
- Mid-/High-EQ- oder Vocal-Ducking-Outputs,
- automatische Auswahl besserer Cue Points.

Diese Erweiterungen sind additiv nur möglich, solange Shape und Bedeutung der
Version-1-Kanäle unverändert bleiben; andernfalls benötigen sie
Feature-Protokoll 2.

Der konkrete NPZ-/JSONL-Export sowie die strikt track-getrennte
Train/Validation/Test-Regel stehen in
[`DATASET_PROTOCOL.md`](./DATASET_PROTOCOL.md).
