# P11 · Technischer Nachweis für die Versuchsleitung

**Historischer Stand run01, am 19.11.2026 für die Hörsitzungen verworfen.** Die Tabellen belegen die ursprüngliche Auswahl und den damaligen Export. Für die aktuelle Geometrie, Pegel, Zuordnungen und die Materialübergabe gilt der [Korrekturbericht zu run02](korrektur_run02.md). Das folgende Protokolldatum und die Prüfsumme beziehen sich auf die [gesicherte Originalfassung](studienprotokoll_run01.md).

Die elf vorab festgelegten Paare stammen aus 22 getrennten Recording-Gruppen des P01-Freeze `2a70dc1`. Das [Studienprotokoll](studienprotokoll.md) lag vor der ersten Verarbeitung des Finalmaterials vor. Der SHA-256 lautet `98fe6033a9e225b295a4265b54835b808f8ad633e426bd3e33b9af73bcc0b85a`. Bedienung und Bewertungsexport wurden mit sieben P04-Entwicklungsclips erprobt. Daten aus dieser Bedienprobe zählen ausschließlich als Funktionstest.

## Ausschlüsse vor der Cue-Wahl

Die partielle Rasteranalyse verlangt mindestens 98 % übereinstimmende Beats je Detektor im gemeinsamen Zeitbereich und einen Block aus mindestens acht vollständigen Takten. Bei vier Quellaufnahmen verfehlte die Analyse diese Anforderungen. Das betreffende Paar entfiel jeweils für alle sechs Studienzellen und den Anker. Die Paar-IDs in der Tabelle bezeichnen Einträge der eingefrorenen Population.

| Paar-ID | Übereinstimmung librosa | Übereinstimmung aufTAKT | Längster vollständiger Block |
|---|---:|---:|---:|
| P04 | 100,00 % | 50,00 % | 0 Takte |
| P05 | 78,29 % | 99,51 % | 58 Takte |
| P08 | 99,74 % | 90,24 % | 46 Takte |
| P11 | 50,00 % | 99,65 % | 45 Takte |

Der [lokale Bestand](../../../../output/review_jp_20261118/p11_hoerversuch/run01/inventory.json) verknüpft jeden Ausschluss mit Aufnahme-SHA, Zeitpunkt, Ablehnungsgrund und Prüfsumme der Detektordiagnose. Alle zulässigen Paare stammen aus der ursprünglichen Elferliste. Mit weniger als zehn unabhängigen Paaren gilt für H1–H3 der vorab festgelegte deskriptive Auswertungsweg. Der technische Bestand enthält keine Bewertungen.

## Gerenderte Panels

| Paar-ID | Gemeinsame Cue-IDs | Verschiedene gewählte Cues | PCM24-Clips |
|---|---:|---:|---:|
| P01 | 4.136 | 3 | 7 |
| P02 | 4.686 | 3 | 7 |
| P03 | 4.104 | 3 | 7 |
| P06 | 1.444 | 3 | 7 |
| P07 | 6.148 | 3 | 7 |
| P09 | 4.928 | 3 | 7 |
| P10 | 13.110 | 3 | 7 |
| **Gesamt** | **38.556** | **21** | **49** |

Der technische Audit hat die Selektorwahl und die personenbezogenen Permutationen nachgespielt, alle 49 Stereo-PCM24-Dateien bei 44.100 Hz erneut gemessen und die 147 Teilnehmerkopien anhand ihrer SHA-256 geprüft. Die Clips dauern 18,90–19,17 s. Die größte Abweichung vom Lautheitsziel des jeweiligen Paars beträgt 0,01 LU, der höchste True Peak −12,28 dBTP. Für die Versuchsleitung stehen drei getrennte Sitzungskennungen bereit. [Versionierbarer Prüfnachweis](verified.json)

## Reproduktion und Zugang

In der P07-Laufzeit bindet `src.evaluation.p11_stimuli` den lokalen Encoder und die vier Takte umfassenden Fenster an die P10-Auswahl. Der Regelranker ist `feature_baseline_v3`. Beide Selektoren und die uniforme Zufallswahl greifen auf dieselben Cue-IDs zu. Jedes vollständige Paar enthält in `pool.csv` IDs, native Schnittpunkte und beide Scores. `selection.json` bindet das Ranking an das Modell und die GPU-Laufzeit. Das P04-Panel enthält die sechs Renderbedingungen und den harten Schnitt am Regel-Cue. `stimuli/results.json` dokumentiert Geometrie, Controls, Lautheit und Audiodatei-SHA je Clip. In `secondary.json` stehen die vorab vorgesehenen technischen Vergleichsmetriken für die sechs Zellen.

Im Repositoryroot erzeugt der folgende Aufruf bei Bedarf eine neue technische Reproduktion. Er benötigt die gebundenen Originale, P07-Runtime, nativen CUDA/bf16-Support, lokale Gewichte und die im P04-Vertrag genannten Audiowerkzeuge.

```powershell
$env:PYTHONPATH = (Resolve-Path output/review_jp_20261118/p07/runtime).Path
$env:HF_HUB_OFFLINE = '1'
$replay = 'output/review_jp_20261118/p11_hoerversuch/replay'
.venv\Scripts\python.exe -B -X utf8 -m src.evaluation.p11_stimuli --output $replay --preanalyse-after 0 --workers 6
.venv\Scripts\python.exe -B -X utf8 -m src.evaluation.p11_stimuli --output $replay --record-grid-exclusions
.venv\Scripts\python.exe -B -X utf8 -m src.evaluation.p11_stimuli --output $replay --historical
.venv\Scripts\python.exe -B -X utf8 -m src.evaluation.p11_verify --root $replay
```

Die Zuordnungsschlüssel verbleiben bei der Versuchsleitung. Für den geschlossenen Zugang, den Bewertungsexport und die Sicherung vor Entblindung gilt die [Durchführungsanleitung](durchfuehrung.md). Der nächste geplante Meilenstein ist der unabhängige P11-Review in einer eigenen Sitzung. Anschließend organisiert der Autor die Teilnahme.
