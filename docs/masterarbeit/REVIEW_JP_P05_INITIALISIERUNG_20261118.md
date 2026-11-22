# P05 · Equal-Power-Start der Controller

Am 18. November 2026 lieferten alle fünf frisch initialisierten Controller auf ihren Entwicklungsfenstern samplegleich die passende Equal-Power-Brücke aus P04. Bei allen fünf änderte ein Schritt entlang des Gradienten des Trainings-Objectives das Audio. Die Messung erfolgte auf der CPU bei ursprünglichem Gain, vor jeder Hörstimulus-Normalisierung. Sie belegt den Startzustand und die Trainierbarkeit. Der Nutzen gelernter Kurven über mehrere Epochen ist Gegenstand von P06.

## Vertrag für Gewichte und Controls

Neue reguläre Trainingsläufe verwenden `model.config.control_initialization = "equal_power_v1"`. Fehlt das Feld in einem gespeicherten Vertrag, verwenden die Loader `legacy`. Der CLI-Schalter `--control-initialization legacy` reproduziert den alten Start. Ein leerer persistenter Tensor im neuen State-Dict bindet den Vertrag an die Gewichte. Striktes Laden erkennt damit eine Verwechslung in beiden Richtungen. Es kommen keine trainierbaren Parameter hinzu. Die bisherigen Sweep-YAMLs ohne das Feld beschreiben ihre ursprünglichen Legacy-Experimente.

| Controller | Physische Controls bei E0 |
|---|---|
| R1 · Time-shared MLP | Lineare Position für Mix und Tiefton. Der vorhandene Zwei-Band-Renderer erzeugt die Equal-Power-Gains. Das entspricht bereits dem bisherigen Start. |
| R2 · Vocal-MLP | Lineare Position für Mix, Tiefton und Vocals. Ducking beider Stems ist überall null. |
| R3 · Fester TCN/BiLSTM | Mixposition zuerst auf Samples interpolieren, dann Cosinus/Sinus für A/B bilden. Tieftonposition linear, alle sechs Band-EQs auf eins, Ducking null. Der Legacy-Rendererpfad interpoliert weiterhin die Gain-Stützstellen. |
| R4 · Variabler TCN/BiLSTM und variable MLP-Baseline | Dieselben fünf physischen Stem-Controls wie R2 mit der Stützstellenzahl der gewählten Taktlänge. Ein Adapter verwendet die bestehenden variablen Modelle. Der per Quelltext-SHA gebundene September-Teacher behält seine Implementierung. |

Die bestehenden monotonen Positionsköpfe haben bei gleichen Inkrementen eine lineare Rampe. Ein neutraler EQ liegt am oberen Rand seines Wertebereichs, neutrales Ducking am unteren. Für die Absenkung verwendet der neue Vertrag `a(z) = tanh(|z|)`. Am Knick bei null wählt Autograd durch den expliziten rechten Zweig die einseitige Ableitung +1. Beide Logitvorzeichen können die Neutralstellung verlassen. Beim festen TCN gilt für EQ `1 − a(z)` und für Ducking `a(z)`. Die Vocal-Köpfe zentrieren das Logit um den initialen Bias und behalten Maximalabsenkung und Positionsfenster bei. Die Tests prüfen die Ableitung am Knick und an beiden Flanken sowie die tatsächlich bewegten Hilfscontrols nach dem ersten Schritt.

Bei einem frischen variablen Lauf misst der Runner vor dem ersten Optimiererschritt Train und Validation samt Losskomponenten je Taktlänge. Diese E0 erscheint einmal in Historie und gegebenenfalls W&B. Bei aktivierter Checkpointsicherung erlaubt `latest.pt` das Fortsetzen direkt nach E0. Der erste für `best.pt` berücksichtigte Trainingsstand ist weiterhin E1. Bei Gewichtsübernahme bezeichnet `checkpoint_initialization` den tatsächlich gemessenen Start. R4 vom September beginnt in seiner historischen Tabelle weiterhin mit der bereits trainierten E1.

## Entwicklungsprobe

Die fünf Vorwärts- und Rückwärtsprüfungen nutzen das erste native Trainingsbeispiel des jeweiligen P04-Smokes, vier Takte, Seed 20260926 und einen SGD-Schritt mit Lernrate 0,01. Bei den ersten drei Pfaden ist das Fenster `example-d4ee00b2a98cbc2a`, bei den beiden variablen Modellen `variable-example-af9687e3a58057cf`. Die Maximalabweichungen sind absolute Differenzen von Float32-Waveform-Samples.

| Modell | Max. Abweichung E0 zu Equal Power | L2-Norm des Lossgradienten | Max. Audioänderung nach einem Schritt |
|---|---:|---:|---:|
| R1 MLP | 0 | 0,0020102 | 4,17 × 10⁻⁷ |
| R2 Vocal-MLP | 0 | 0,0085070 | 3,09 × 10⁻⁵ |
| R3 fester TCN | 0 | 0,288335 | 0,0059482 |
| R4 variabler TCN | 0 | 0,088788 | 0,0004913 |
| Variable MLP-Baseline | 0 | 0,053285 | 0,0001883 |

Zusätzlich prüft der Smoke auf je einem archivierten Validierungsfenster die vier September-Best-Checkpoints. Alle vier reproduzieren die P04-Modellzeile mit identischen Controls, Rohproxy-Komponenten und SHA-256 des gerenderten Audios. Die synthetischen Stereotests decken 2, 4, 6 und 8 Takte für beide variablen Modelle ab. Die Startprüfung vergleicht die gesamte Gainkurve mit der Referenz, ihre Endpunkte und die konstante Summe der quadrierten Gains. [Messwerte und Hashes](review_jp_20261118/p05/entwicklungsprobe.json) · [Testprotokoll](../Bemerkungen.md)

Erneuter Aufruf aus dem Projektstamm mit einem freien Ausgabeordner:

```powershell
.venv\Scripts\python.exe -m src.evaluation.check_control_initialization --p04-reference output/review_jp_20261118/p04_render/run02 --output output/review_jp_20261118/p05_initialisierung/run04
```

## Übergabe an P06

Die sieben Konfigurationen binden D2 über den Manifest-SHA. R1 und R2 erhalten jeweils die drei vorab gewählten Seeds 20260926, 20260927 und 20260928. R3 erhält für den deskriptiven Vergleich denselben Seed 20260926 wie sein Septemberlauf. Die Budgets betragen 30/100/30 Epochen für R1/R2/R3, Patience jeweils 6. Alle drei verwenden wie die September-Checkpoints AdamW bei konstanter Lernrate 0,001. Die Option `--constant-learning-rate` wählt diese Variante beim festen TCN. R4 geht mit dem September-Best-Checkpoint in die Diagnose. [Benannte Konfigurationen](review_jp_20261118/p05/p06_configs.json) · [P04-Aufrufe für die gepaarten E/F/M/D-Bedingungen](REVIEW_JP_P04_RENDER_20261118.md)

Der folgende Aufruf startet erst im Arbeitspaket P06 einen ausgewählten Lauf. Für jede Wiederholung ist der jeweilige vollständige Name aus der JSON-Datei einzusetzen.

```powershell
$plan = Get-Content -Raw docs/masterarbeit/review_jp_20261118/p05/p06_configs.json | ConvertFrom-Json
$run = $plan.runs | Where-Object name -eq 'R3_equal_power_v1_seed20260926'
$profile = $plan.profiles.($run.profile)
$runArgs = @($profile.command, $plan.dataset, (Join-Path $plan.output_root $run.name), '--seed', $run.seed) + $plan.common_args + $profile.args
.venv\Scripts\python.exe -m src.ml @runArgs
```
