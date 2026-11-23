# Tempo-Angleichung am Cue

Stand 23.11.2026. Die normale Pipeline, GUI, Paar- und Mehrfachbatches, neu exportierte Trainings-Waveforms sowie der neue Studienmodus verwenden dieselbe Angleichung. Jede Überblendung übernimmt die gesamte gemessene Brückendauer von A. B endet am Zielcue. [Rückmeldung, Befund 2](../../review_jp/RUECKMELDUNG_20261122.md) · [Rendervertrag](../RENDERING_PROTOCOL.md)

## Messung und Entscheidung am Cue

Für jede Aufnahme schätzt eine lineare Regression mit freiem Achsenabschnitt die mittlere Schlagdauer in Samples. Das Fenster umfasst bis zu 64 beobachtete Schläge um den Cue. Am Trackrand verschiebt sich das Fenster, bei kürzeren Tracks stehen weniger Schläge zur Verfügung. Der Tempofaktor für B ist das Verhältnis der Schlagdauern B/A. Die Pipeline verarbeitet B mit diesem einen Faktor und verwendet für den zugehörigen Vocal-Stem denselben Faktor. Gleiche globale BPM-Felder können unterschiedliche lokale Schlagdauern verbergen. [Regression](../../src/tempo/cue_alignment.py) · [Brückenextraktion](../../src/bridge.py)

Die Prüfung arbeitet in der Zeitachse des ausgegebenen Audios. Über sämtliche Schlaggrenzen der Brücke dürfen die gemessenen A- und B-Marken höchstens 20 ms von ihrer jeweiligen Regressionsgeraden abweichen. Außerdem dürfen sich korrespondierende A- und B-Marken höchstens um 20 ms unterscheiden, wenn der B-Cue auf das Ende der A-Brücke gelegt wird. Die Grenze wurde vor der Auswertung der historischen P11-Pools festgelegt. Ein verrutschter innerer Beat kann damit auch bei gleicher Gesamtdauer zum Ausschluss führen. GUI-Vorschläge und neue Batches filtern vor Ranking und Top-K. Neu exportierte Trainingssets weisen ausgeschlossene Beispiele aus. Frühere Datensätze und Studienpanels behalten ihren historischen Waveformvertrag.

## Spannenfehler auf archivierten Beatmarken

Der Spannenfehler ist der Betrag der Differenz zwischen A-Auslauf und skaliertem B-Vorlauf über dieselbe Zahl von Schlägen. Die Tabelle verwendet die archivierten Featuregrids der genannten Cues. „Alt“ verwendet den Faktor aus den globalen BPM-Feldern, „neu“ die lokale Regression über genau dieselben Cues vor der Zulassungsprüfung. Die letzten zwei Spalten erfassen nur die zugelassenen Cues. Median und 95. Perzentil stehen in Millisekunden. [Maschinenlesbare Werte einschließlich Maxima](review_jp_20261118/tempo/spannenfehler.json) · [Auswertung](../../src/evaluation/cue_tempo_audit.py)

Die 394 verschiedenen Train-/Validation-Featurecaches von D1 bis D4 enthalten 329 Einträge mit dokumentiertem Detektor `auftakt_matched_to_librosa_partial_v2`. Bei den übrigen 65 älteren Caches fehlt das Herkunftsfeld. Für diese Einträge belegen die Werte die gespeicherten Zeitmarken, ihre ursprüngliche Detektorherkunft bleibt offen.

| Bestand | Cues | >20 ms alt | >20 ms neu | Median alt / neu | P95 alt / neu | Zugelassen | P95 zugelassen |
|---|---:|---:|---:|---:|---:|---:|---:|
| D1 Train | 45 | 44 | 31 | 92,9 / 40,6 | 243,1 / 157,6 | 4 | 18,8 |
| D1 Validation | 9 | 7 | 7 | 46,4 / 71,3 | 116,1 / 124,9 | 0 | – |
| D2 Train | 370 | 240 | 254 | 46,4 / 43,0 | 192,1 / 161,1 | 12 | 9,4 |
| D2 Validation | 50 | 42 | 33 | 81,3 / 27,6 | 168,9 / 114,9 | 1 | 3,9 |
| D3 Train | 420 | 259 | 283 | 46,4 / 48,0 | 197,4 / 176,1 | 19 | 14,3 |
| D3 Validation | 48 | 25 | 26 | 23,2 / 27,7 | 173,0 / 132,3 | 1 | 18,6 |
| D4 Train | 2.649 | 1.572 | 1.491 | 23,2 / 25,0 | 215,9 / 167,2 | 217 | 14,3 |
| D4 Validation | 636 | 334 | 349 | 23,2 / 24,1 | 246,7 / 165,5 | 70 | 13,9 |
| November-Hörsatz, Teilmenge von D2 Validation | 20 | 19 | 11 | 81,3 / 22,3 | 186,3 / 112,8 | 0 | – |
| P04-Entwicklungspanel | 3 | 0 | 3 | 0,0 / 46,2 | 10,4 / 52,6 | 0 | – |
| P11 run01, ausgewählte Cues | 21 | 11 | 13 | 20,7 / 35,2 | 181,3 / 97,5 | 1 | 12,6 |

Die Regression senkt beispielsweise bei D4 Train das 95. Perzentil von 216 auf 167 ms. Bei D2 Train überschreiten mit der Regression sogar mehr Cues die 20-ms-Grenze. Von den 2.649 D4-Trainingsbeispielen bestehen 217 die vollständige Prüfung. Ein neuer Controllerlauf bräuchte daher einen neu exportierten, ausreichend großen Trainingsbestand. Die Schätzung verwendet Tracker-Marken. Hörbarer Kickversatz, Klangqualität und zusätzliche lokale Korrekturen früherer variabler Cache- oder Studienrenderer wurden hier nicht akustisch vermessen. Der November-Hörsatz umfasst mehrere Renderbedingungen pro Cue. Seine 20 Cues sind bereits in D2 Validation enthalten.

Im historischen P11-Kandidatenpool verbleiben nach der reinen Geometrieprüfung 151/4.136 (P01), 46/4.686 (P02), 1.078/4.104 (P03), 13/1.444 (P06), 343/6.148 (P07), 1.012/4.928 (P09) und 1.127/13.110 (P10). Weitere Studienbedingungen wie Vor-/Nachlauf und Merkmalsverfügbarkeit können diese Zahlen verringern. Der Audit las ausschließlich die archivierten Marken und wählte keine neuen finalen Cues aus.

## Hörvergleich auf Entwicklungspaaren

Je Paar liegen drei Equal-Power-Überblendungen desselben Cues mit gleichem Vorlauf und gleicher Gesamtdauer vor. Der Vergleich verwendet die historische globale Anpassung, die einmalige lokale Anpassung und die schlagweise Korrektur des früheren Studienrenders. Bei dev01 betrug der ursprüngliche Spannenfehler 21,1 ms, bei dev05 33,1 ms. Die sechs nachgemessenen PCM24-Dateien erreichen −23,01 bis −23,00 LUFS und höchstens −12,18 dBTP. Pro Paar sind die Tracks disjunkt zum jeweils anderen Paar. [Dateinamen, SHA-256 und Einzelpegel](review_jp_20261118/tempo/entwicklungsclips.json)

| Paar | Globale BPM | Lokale Regression | Schlagweise Korrektur |
|---|---|---|---|
| dev01 | [WAV](../../output/review_jp_20261118/cue_tempo/entwicklungsclips_run01/dev01-global_bpm_v1.wav) | [WAV](../../output/review_jp_20261118/cue_tempo/entwicklungsclips_run01/dev01-cue_grid_regression_v3.wav) | [WAV](../../output/review_jp_20261118/cue_tempo/entwicklungsclips_run01/dev01-beatwise_run02.wav) |
| dev05 | [WAV](../../output/review_jp_20261118/cue_tempo/entwicklungsclips_run01/dev05-global_bpm_v1.wav) | [WAV](../../output/review_jp_20261118/cue_tempo/entwicklungsclips_run01/dev05-cue_grid_regression_v3.wav) | [WAV](../../output/review_jp_20261118/cue_tempo/entwicklungsclips_run01/dev05-beatwise_run02.wav) |

Die persönliche Hörprobe steht aus. Für beide Cues werden hörbare Doppelanschläge, Nahtstellen der Streckung, ein eventueller Vorzug und die jeweilige Stelle im Clip protokolliert. Die sechs WAVs liegen lokal unter `output/`. Ein frisches Ziel erlaubt ihre Wiederherstellung.

```powershell
.venv\Scripts\python.exe -m src.evaluation.cue_tempo_audit output/tempo_audit_neu.json
.venv\Scripts\python.exe -m src.evaluation.cue_tempo_listening output/tempo_hoerprobe_neu
```
