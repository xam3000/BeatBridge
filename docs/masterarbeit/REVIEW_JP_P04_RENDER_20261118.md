# P04 · Gemeinsames Rendering für Diagnose und Hörstimuli

Stand 18.11.2026. P06 und P11 verwenden `python -m src.evaluation.render_comparison`. Ein Aufruf bindet Renderer, Objective, Samplebasis und Gainverfahren an einen Vergleich. Das Ergebnis besteht aus `results.json` (Tabelle) und `protocol.json` (Vertrag). Der Studienmodus schreibt zusätzlich die sieben nachgemessenen WAV-Dateien eines Paars. [CLI](../../src/evaluation/render_comparison.py) · [Gemeinsame Auswertung](../../src/evaluation/comparison.py)

## Diagnose für P06

| Profil | Audio und Fenster | Renderer und Proxy | Controls |
|---|---|---|---|
| R1 | D2, historische Format-1-Brücke, vier Takte | Zwei-Band, v4 | Mix- und Bassposition |
| R2 | D2, gebundene Mix-/Stem-Caches, vier Takte | Vocal, v5 | Mix-, Bass-, Vocalposition, Ducking A/B. D2-Features auf Demucs-Basis, September-Wellenformen mit RoFormer-Stems |
| R3 | D2, dieselbe Brückenextraktion wie R1 | Full-Band, v4, Vocal-Ducking über das Mittenband | Hauptgains A/B, sechs EQs, Bass-Ownership und Ducking |
| R4 | D4, lokale Grid-Ausrichtung und zugelassene Beispiele des versiegelten Cacheindex | Vocal, zeitnormiertes v5 | Drei Positionen und zwei Vocal-Duckings aus dem variablen Modelladapter. Eigene Auswertung und feste Kurve je Länge |

Alle vier verarbeiten Stereo-Float32 mit 11.025 Hz, FIR 127 und Trennung bei 180 Hz, bei R3 zusätzlich 3.500 Hz. Der Diagnose-Proxy verwendet die vollständige native Brücke bei Einheitsgain ohne Vor-/Nachlauf. Ein Takt liefert acht Halbbeat-Stützstellen und acht Objective-Fenster. Der Adapter prüft Best-Checkpoint und Datasetmanifest gegen den gewählten Run. R2 liest die dort einzeln gebundenen Waveform-Manifeste, R4 prüft die Digests von Cache-Root und Index sowie die verwendeten Einträge. Je Fenster stehen Samplegrenzen und Cachebezug in der Tabelle. Bei den historischen R1–R3-Einträgen beziehen sich die gespeicherten Extraktionskoordinaten auf 44.100 Hz. `bridge_samples` zählt die tatsächlich ausgewerteten Samples bei 11.025 Hz. [Native Adapter](../../src/evaluation/comparison_native.py)

E rendert Equal Power mit neutralem EQ und Ducking. F minimiert den mittleren Train-Paarloss. Bei mehreren Cues eines gerichteten SHA-Paars erhält jeder Cue denselben Anteil am Gewicht dieses Paars. Adam akkumuliert die Gradienten vor jedem Update über das Trainingsmaterial. F bleibt danach für alle Validationbeispiele gleich. M verwendet die Controls des Best-Checkpoints. D startet für jeden Cue neu und minimiert dessen eigenen Proxy. F/D verwenden dieselbe Parametrisierung, Equal-Power-Start, Inkrementschranke 0,6, Lernrate 0,06 und regulär 80 Updates. Berichtet wird der erreichte letzte Schritt.

Bei R2/R4 werden die beiden Ducking-Anteile nach jedem Update auf [0, 1] projiziert und mit dem vertraglichen Maximum und dem Vocal-Positionsfenster multipliziert. Bei R3 erhalten F/D je eine Haupt- und Bassposition sowie sechs EQs und ein Ducking in [0, 1]. Die Hauptposition wird vor Sinus/Cosinus auf Sampleauflösung interpoliert. So erreicht E auch zwischen den Stützstellen Equal Power. M übergibt dem gleichen Full-Band-Renderer die zehn nativen Stützstellenkanäle des historischen TCN. Diese Gainparametrisierungen sind bei der Deutung von D als Vergleichswert relevant. P05 behandelt den Start der lernenden Netze separat.

**Aufruf für die vollständige P06-Auswertung eines Profils** (im Repository-Root, frisches Ausgabeziel).

```powershell
.venv\Scripts\python.exe -m src.evaluation.render_comparison diagnose R1 --output output/review_jp_20261118/p06_controller/run01/R1_legacy
```

`R2`, `R3` oder `R4 --bars 4` wählen die anderen Verträge. R4 akzeptiert die historischen Längen 2/4/6/8 jeweils einzeln. Für einen weiteren kompatiblen Lauf `--run <Runverzeichnis>` mit eigenem Ziel angeben. Neue Modellformate aus P05 benötigen den zugehörigen expliziten Modelladapter. Standardmäßig umfasst F alle zugelassenen Trainbeispiele und die Tabelle alle zugelassenen Validationbeispiele der gewählten Länge. Der kleine reproduzierbare Entwicklungsaufruf lautet zum Beispiel

```powershell
.venv\Scripts\python.exe -m src.evaluation.render_comparison diagnose R1 --limit 1 --steps 2 --output output/review_jp_20261118/p04_render/replay/R1
```

## Panel für P11

Das Eingabe-JSON enthält den Pfad und SHA-256 des gemeinsamen Paarmanifests, eine Kandidaten-ID je Selektor (`ssl`, `rule`, `random`), die beiden FP1-Trackfeature-Verzeichnisse und den Split `development` bzw. `final`. Pfade gelten ab Repository-Root. Das vollständige [Entwicklungspanel](review_jp_20261118/p04/dev_panel.json) ist zugleich ein Eingabebeispiel. P11 setzt dort die einmalig aus seinem gemeinsamen gültigen Pool bestimmten IDs ein. Mehrfach ausgewählte Cues bleiben unter jedem Selektornamen erhalten. Ein finales Panel erfordert 80 Updates.

```powershell
.venv\Scripts\python.exe -m src.evaluation.render_comparison study docs/masterarbeit/review_jp_20261118/p04/dev_panel.json --analysis-root output/pre_analysis_variable_v2_strict_20260820_retry01 --merge-algorithm librosa_auftakt_monotonic_partial_v2 --steps 2 --output output/review_jp_20261118/p04_render/replay/panel
```

Für P11 das vorbereitete Panel und den zugehörigen Analyse-Root einsetzen, ein eigenes Ziel angeben und `--steps` beim Standard 80 belassen. Die Auswahl, spätere Verblindung und Zuordnung für den Player gehören zu P11. Die technischen Dateien hier enthalten die Methodenzuordnung.

Der Studienpfad lädt das Paar einmal, passt B bei Bedarf per Rubber Band an A an und verwendet für jeden ausgewählten Cue dieselbe Brückenextraktion wie der Bestandsrenderer. Er prüft Original-SHAs, Tempoabweichung, erkannte Grids, lokale 4/4-Fenster, Feature-Gridhashes, Vocalvertrag und R1-Normalisierung. Der Übergang verwendet 16 Beats ab S in A und vor T in B. Die gemeinsame Dauer ergibt sich aus dem kürzeren der beiden vollständigen Beatfenster. Pro Cue bleiben die letzten Samples vor T und die ersten ab S erhalten. Die Tabelle führt beide Beatfolgen, die ausgerichteten Samplegrenzen und den Target-Samplefaktor. [Brückenextraktion](../../src/bridge.py)

Für alle sechs E/D-Zellen laufen Rendering, Objective v4 und D-Optimierung bei 44.100 Hz Stereo-Float32, FIR 511, 180 Hz und 32 Stützstellen. Jeder Clip hat 5 s A vor S und 8 s B ab T. Beim Anker am Regel-Cue spielt A während der gesamten Brücke allein, danach folgt B ab T. Zu kurze Kontexte, abweichende Koordinaten und ungültige Pegel führen zu einem Fehler für das ganze Panel. Die Veröffentlichung des Zielverzeichnisses erfolgt nach Abschluss der Prüfung.

**Lautheitsmessung und Interpretation.** FFmpeg misst gegatete integrierte LUFS und True Peak über den gesamten Stereo-Clip einschließlich beider Kontexte. Der `loudnorm`-Eingangsmesser verwendet 192 kHz für True Peak (4,35-fache Rate). Der erste konstante Gain pro Clip beträgt −23 LUFS minus Roh-LUFS. Aus dem höchsten vorläufigen True Peak aller sieben Clips folgt bei Überschreitung von −1 dBTP eine gemeinsame zusätzliche Absenkung. Es gibt keinen Limiter. Die Nachmessung liest das exportierte Stereo-PCM24-WAV und prüft ±0,2 LU um das erreichte Paarziel und höchstens −0,99 dBTP einschließlich Quantisierungstoleranz. [Implementierung](../../src/evaluation/comparison_study.py) · [FFmpeg-Messverfahren](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)

Die Wiedergabeangleichung gleicht absolute Lautheitsunterschiede der ganzen Clips aus. Ein konstanter Gain erhält den relativen Energieverlauf innerhalb eines Clips. Der Clippingterm kann deutlich sinken. Energie- und Randterme reagieren beim Mitskalieren beider Referenzen weitgehend pegelinvariant, mit kleinen Differenzen durch numerische Untergrenzen und PCM24-Quantisierung. Der rohe Brückenproxy bleibt die Bezugsgröße für die Controllerdiagnose.

## Tabelle und Entwicklungsnachweis

Eine Zeile entspricht einer Bedingung an einem Cue. Alle Zeilen führen Profil, Split, gerichtetes SHA-Paar, Beispiel/Cue, Geometrie, Bedingung, Selektor, Controls, Brückenlänge, Float32-Audiohash und SHA des vollständigen Protokolls. `proxy_raw` enthält die Komponenten vor Gain. `proxy_playback` verwendet dieselben Controls, die nachgelesene PCM24-Brücke und beide Referenzen mit dem tatsächlich angewandten Gesamtgain. `loudness` enthält Roh-/Final-LUFS und dBTP, beide Gains und das erreichte Paarziel. Diagnosezeilen führen leere Wiedergabefelder. Beim harten Anker sind beide Controls-Proxys undefiniert. WAV-Dateiname und Datei-SHA erlauben den Abgleich nach einem Wiederholungsexport.

Die abgenommenen lokalen Ergebnisse stehen unter `output/review_jp_20261118/p04_render/run02/`, mit je einer Tabelle in `R1`, `R2`, `R3`, `R4` und `panel`. Je Diagnoseprofil wurden ein Train- und ein Validationbeispiel mit zwei Adam-Updates verarbeitet. Alle 55 gespeicherten M-Komponenten (11/15/11/18) stimmen exakt mit den ursprünglichen Trainings-Lossfunktionen am selben Beispiel überein. Zwei unabhängige Entwicklungsaufrufe lieferten dieselben rohen Audiohashes und sieben byteidentische PCM24-Dateien.

Das technische Panel „Cosmic Frequency“ → „Stuck In The Middle“ verwendet drei Cues eines D2-Trainpaars mit passenden Feature- und nachgewiesenen Beatrastern. Der kürzere Clip dauert 19,07 s, der längere 19,08 s. Gemessener Bereich −23,03 bis −22,99 LUFS, höchster True Peak −15,50 dBTP, zusätzliche Paarabsenkung 0 dB. Ein synthetischer Impulsfall prüft die aktive Paarabsenkung. Die drei Selektorbezeichnungen in diesem Smoke sind Platzhalter. Es wurden keine Hörurteile erhoben. [Testjournal](../Bemerkungen.md)
