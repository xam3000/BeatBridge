# P14 · Sequenzexport am 23. November 2026

Der Entwicklungsexport verbindet „Meltdown“ von Devin Wild, „Inferno“ von Vertile und „Rise Of The Celestials“ von Coone. Alle drei Originale stammen aus verschiedenen Recording-Gruppen im P07-Trainingssplit. Zwei vollständige Renderläufe ergaben dieselbe 65,324 Sekunden lange Stereo-WAV und dasselbe Manifest. [Entwicklungsplan](development_plan.json) · [WAV](../../../../output/review_jp_20261118/p14_mashup/run01/mashup.wav) · [Kantenmanifest](../../../../output/review_jp_20261118/p14_mashup/run01/manifest.json)

## Bedienung

In der BeatBridge-GUI die Songs zur Sequenz hinzufügen. **Songabschnitt …** legt Anfang und Ende für den ausgewählten Song in Originalsekunden fest. Voreingestellt ist die gesamte Aufnahme. Für jeden Paarübergang beide Cuepoints setzen, Länge und Baseline wählen. Die gezogenen Bereiche in den Wellenformen dienen weiterhin der Cue-Suche. Der Export akzeptiert Hard Cut, linearen Fade und Equal Power. Trainierte Controller sind in der Paarvorschau verfügbar.

**Mashup exportieren …** schreibt WAV und Manifest zusammen in einen neuen Unterordner des gewählten Ziels. Die Ausgabe beginnt am Abschnittsanfang des ersten Songs. An jedem Ausgangscue beginnt die Brücke. Am Ende der Brücke setzt der Folgesong an seinem Eingangscue ein. Der letzte Abschnitt läuft bis zu seinem eingestellten Ende. Die Abschnitte müssen alle tatsächlich verwendeten Solopassagen und Überblendungen enthalten. Überlappende Ein- und Ausgangscues eines mittleren Songs führen zu einer Fehlermeldung.

Beim Umsortieren folgen die Abschnitte ihrem Song. Für weiterhin benachbarte Paare bleiben Cues, Suchbereiche, Renderer und Vorschau erhalten. Neu entstandene Kanten beginnen ohne Cuepoints.

## Tempo und Ausgabedauer

Die Cue-Zeiten beziehen sich auf das Original. Die GUI und der CLI-Export rasten auf den Downbeat ein. Die erste Spur gibt das Anfangstempo vor. An jeder weiteren Kante bestimmt die Regression über bis zu 64 Schläge das Verhältnis des lokalen Tempos von B zum bereits angepassten A. Das gemeinsame 20-ms-Kriterium prüft die beobachteten Beatpositionen vor dem Mix. Jeder Folgesong wird höchstens einmal aus seinen Originalsamples mit Rubber Band gestreckt. Für den Fade liefert A die Zahl der Samples zwischen Ausgangscue und Übergangsende. In B endet das gleich lange Fenster am skalierten Eingangscue. Bei Hard Cut beträgt die Überlappung null Samples. Ein gemeinsamer Pegelfaktor schützt die PCM24-Ausgabe vor Übersteuerung.

| Material der WAV | Anfang, inklusiv | Ende, exklusiv | Samples |
|---|---:|---:|---:|
| Meltdown | 0 | 1.112.144 | 1.112.144 |
| Meltdown → Inferno, zwei Takte Equal Power | 1.112.144 | 1.253.456 | 141.312 |
| Inferno | 1.253.456 | 1.464.544 | 211.088 |
| Inferno → Rise Of The Celestials, drei Takte linear | 1.464.544 | 1.676.178 | 211.634 |
| Rise Of The Celestials | 1.676.178 | 2.880.776 | 1.204.598 |

Bei 44.100 Hz ergeben sich 2.880.776 Stereo-Frames. Die BPM-Felder der drei Aufnahmen lauten 152,00, 161,50 und 156,61. Aus den örtlichen Schlagabständen ergeben sich die Tempofaktoren 0,938679 für „Inferno“ und 0,968924 für „Rise Of The Celestials“. Der größte gemessene Versatz gegenüberliegender Beats beträgt 10,56 bzw. 16,49 ms. Der einmalige Pegelfaktor ist 0,672347. WAV-SHA-256 `a0cae38158276b50a2dbd56c3c57885401f24517039d207adac5d76b0b937b65`.

## Reproduktion

Aus dem Repository einen neuen Ausgabeordner angeben. Der Entwicklungsplan bindet die Originale über SHA-256. Die Proben verwenden den vorhandenen v2-Analysecache.

```powershell
.venv\Scripts\python.exe -B -X utf8 -m src.mashup docs/masterarbeit/review_jp_20261118/p14/development_plan.json output/review_jp_20261118/p14_mashup/replay02 --partial-grid --analysis-cache output/pre_analysis/prive_scantraxx_extension_merge_v2_20260923_run01
```

Die gezielten Tests prüfen alle vier Baselinelängen, Hard Cut, gemischte Sampleraten, drei unterschiedliche Tempi, Originalschutz, zu kurze Abschnitte und den Export über den GUI-Button. Der Offscreen-Test bedient auch die Sequenz nach dem Umsortieren. Der manuelle Durchklick und das menschliche Anhören der Entwicklungs-WAV stehen aus. [Testjournal](../../../Bemerkungen.md)
