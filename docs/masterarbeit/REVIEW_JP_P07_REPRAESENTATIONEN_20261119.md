# P07 · Taktmerkmale für die Fortsetzungsmetrik

Stand 19. November 2026. Die beiden Repräsentationen verwenden dieselben
vollständigen, erkannten 4/4-Takte aus dem Originaltempo. Abtast- und
Taktgrenzen sind im Cache in Samples bei 24 kHz angegeben.

## Ergebnis und Ressourcen

Der vollständige Export enthält 762 Ansichten und 104.131 Taktzeilen
je Repräsentationsfamilie. Die 236 Trainingsoriginale aus 230
Recording-Gruppen liefern 32.308 Takte, ebenso jede der beiden
Trainingsfassungen. Die 54 Validation-Originale aus 53 Gruppen liefern
7.207 Takte. Der Audit prüfte jede Ansicht gegen das Quellraster und
zählte 98–142 MERT-Frames pro Takt. Er bestätigte die Hashes der
Originale und Cachedateien, die Gruppentrennung sowie die Mittelwerte
und Skalen der Trainingsoriginale. [Cachemanifest](../../output/review_jp_20261118/p07/full/manifest.json) ·
[Maschinenlesbarer Prüfnachweis](P07_VERIFIED_20261119.json)

| Messung | CUDA-Smoke | Gesamtextraktion |
|---|---:|---:|
| Zeit einschließlich Modellladen | 29,01 s | 37 min 20 s |
| CUDA allokiert, Spitze | 1,07 GiB | 4,84 GiB |
| CUDA reserviert, Spitze | 1,47 GiB | 8,48 GiB |
| Prozess-Working-Set, Spitze | 2,26 GiB | 4,76 GiB |
| Ausgabe | 52,06 MiB | 15,39 GiB |

Im Gesamtlauf kamen 19 neue Vocal-Stems hinzu. Deren lokaler
RoFormer-Checkpoint und die Konfiguration liegen zusammen mit den
Stems, WAVs und Repräsentationen in der gemessenen Ausgabe. Der
MERT-Snapshot liegt separat im selben P07-Ausgabeordner und enthält
das 377,6-MB-Gewicht. Der CUDA-Smoke traf beim erneuten Start alle
drei Ansichten im Cache.

## Bestand und Split

Der Freeze-Commit `2a70dc185bbcf62806d5d426783e03f347c01dd6` bindet das
Evaluationsprotokoll, elf Paare aus 22 Evaluationsgruppen und ihren
Expositionskatalog. Der P07-Einstieg verifiziert die Git-Blobs gegen den
Freeze-Nachweis. Er bindet die September-Splitautorität und deren
BPM-geeignete Liste von 407 Dateien über SHA-256. Die Recording-Gruppen
stammen aus dem eingefrorenen P01-Katalog. Historische Testzuweisungen
sperren die ganze Gruppe. Gruppen mit mehreren September-Zuweisungen,
die P01-Gruppen und das neue Lieferverzeichnis sind ebenfalls gesperrt.
Alle Prüfungen liegen vor dem Öffnen der Originale und vor Feature-Cache-Zugriffen.

68 Zuordnungen entfallen durch die historischen Testgruppen, darunter
ein September-Splitkonflikt. Von den übrigen 281 Train- und 58
Validation-Dateien haben 236 beziehungsweise 54 einen akzeptierten
September-Merge-v2. Die übrigen 49 weisen ein Fallback-Raster auf.
Der Export prüft zusätzlich, dass im Audiobereich vollständige Takte
vorliegen. Die Ausschlussliste im Exportmanifest führt Dateihashes,
Gruppen, Split und Grund. Validation enthält gemäß P01 ausschließlich
Originale. Jede Trainingsfassung erbt Dateihash, Gruppe, Split und Raster
des Originals.

## MERT

Verwendet wird **m-a-p/MERT-v1-95M** mit 12 Transformerlagen, Breite 768
und 75 Hz Merkmalsrate. Die 330M-Variante hätte 24 Lagen mit Breite
1024 und höhere Rechen- sowie Cachekosten. Die Entscheidung für 95M
berücksichtigt alle Zustände und drei Trainingsansichten je Aufnahme auf
einer RTX 5070 Ti mit 16 GB VRAM und rund 64 GiB RAM. Die Modellkarte
nennt CC BY-NC 4.0. Die Gewichte kommen im lokalen, nichtkommerziellen
Thesis-Experiment zum Einsatz. [Modellkarte der gebundenen Revision](https://huggingface.co/m-a-p/MERT-v1-95M/blob/12af15fef9d0ac838c3f475bfbbf26d2060dd4f5/README.md) · [Lizenz](https://creativecommons.org/licenses/by-nc/4.0/) · [Li et al., MERT](https://arxiv.org/abs/2306.00107)

| Bindung | Wert |
|---|---|
| Hub-Revision | `12af15fef9d0ac838c3f475bfbbf26d2060dd4f5` |
| Benutzte Datei | `pytorch_model.bin`, 377.552.987 B |
| SHA-256 der Gewichte | `a2b8b747f72c06e0595aeae41ae5473f4364938c6b39b2c58be38c48e6bd3fcd` |
| Software | Transformers 4.49.0, PyTorch 2.13.0+cu130 |
| Inferenz | Eval-Modus, deaktivierte Gradienten, CUDA BF16-Autocast, FP32-Taktmittel |

Der Loader prüft zusätzlich die Bytes der Modellkarte, Konfiguration,
Vorverarbeitung und der beiden offiziellen Python-Module. Er lädt den
State Dict strikt und mit `weights_only=True`. [Hashliste und Loader](../../src/features/p07_mert.py) · [Offizielle Gewichtsdatei](https://huggingface.co/m-a-p/MERT-v1-95M/blob/12af15fef9d0ac838c3f475bfbbf26d2060dd4f5/pytorch_model.bin)

Der Extraktor mittelt die Originalkanäle zu Mono und resampelt mit
SoXR HQ auf 24 kHz. Die Wandlung erhält Dauer und Tonhöhe.
Das Modell sieht Kerne von 20 Sekunden mit bis zu zwei Sekunden Kontext
auf jeder Seite. Die offiziellen Modellparameter normalisieren jeden
Eingabechunk auf Mittelwert null und Einheitsvarianz. Das schwächt die
Wirkung eines reinen Gain-Faktors im MERT-Zweig. Jeder Zeitframe gehört
über sein Zentrum genau einem Kern. Ausgehend vom Chunksample null hat
das Konvolutionsfrontend 320 Samples Schrittweite und 400 Samples
Rezeptivfeld. Dadurch liegt sein erstes Zentrum bei Sample 199,5.
Pro Takt gehen die Frames in `[Downbeat, nächster Downbeat)` gleich
gewichtet ein. Die Modellachse enthält Zustand 0 am Encodereingang und
zwölf Ausgaben der Transformerlagen. Die Werte hängen vom lokalen
Chunkkontext ab.

## Klassische Merkmale und Produktionsfassungen

Ein Takt beginnt an einem erkannten Downbeat und endet am nächsten.
Die erkannten Beatpositionen werden einzeln auf 24-kHz-Samples gerundet.
Die gerundete Mitte zwischen je zwei Beats teilt sie in acht Halbbeats.
Die Folge muss `1,2,3,4,1` entsprechen. Beatabstände über dem 1,5-Fachen
des Medianabstands unterbrechen gültige Takte. Die bestehenden
Halbbeat-Deskriptoren laufen auf derselben Zeitbasis wie MERT. Ein Vergleich
mit den berechneten Halbbeatgrenzen bricht bei einer Abweichung ab.

Die feste Kanalfolge ist `CHANNELS` in [p07_audio.py](../../src/features/p07_audio.py).
Sie entspricht den bisherigen Indizes 9–24 und 26–50.

| Kanäle | Reihenfolge innerhalb der Gruppe |
|---|---|
| Pegel und Bandspektrum (9) | `rms_dbfs`, `rms_db_relative`, `loudness_slope`, `low_energy_ratio`, `mid_energy_ratio`, `high_energy_ratio`, `local_energy_percentile`, `crest_factor`, `silence_probability` |
| Spektrum und Rhythmus (7) | `spectral_centroid`, `spectral_bandwidth`, `spectral_rolloff`, `spectral_flatness`, `spectral_flux`, `onset_strength`, `kick_prominence` |
| Harmonik (19) | `chroma_00` bis `chroma_11`, `tonnetz_0` bis `tonnetz_5`, `harmonic_ratio` |
| Vocals (6) | `vocal_activity`, `vocal_prominence`, `vocal_onset_probability`, `vocal_offset_probability`, `vocal_phrase_progress`, `vocal_confidence` |

Die übrigen Indizes des 54-Kanal-Vertrags enthalten Positions- und
Phrasenkoordinaten, Confidence und Gültigkeitsfelder. Die in alten
Fenstern beobachtete Gleichheit der Positionskanäle lässt ihre
Funktion für den zeitabhängigen Controller offen. Der 54-Kanal-Vertrag
bleibt in Kraft. Der beobachtungsarme Audiokanal `silence_probability`
ist im Planumfang enthalten.

Je Kanal werden Mittelwert und Populationsstandardabweichung über
acht Halbbeats gespeichert. In den 82 Spalten stehen alle Mittel
vor allen Streuungen. Flux und Onset gehen mit ihren Rohwerten ein.
Der z-Scaler schätzt Mittel und Streuung jeder Spalte aus den gültigen Takten der
Trainingsoriginale. Er nutzt eine Eins für Skalen unter 1e−8 und
transformiert mit denselben Parametern die Trainingsfassungen und
Validation. Die Vocal-Kanäle stammen aus dem Original-RoFormer-Stem
mit demselben EQ, Raumfilter und Gain wie der jeweilige Mix. Der
RoFormer-Vertrag bindet Gewichts- und YAML-Hash. Historische Stems
werden nach Identitäts- und Hashprüfung wiederverwendet. Fehlende Stems
werden mit derselben Datei und Konfiguration erzeugt.

| Trainingsfassung | Peak-EQ in Hz / Q / dB | Pegel | Raumanteil und Seed |
|---|---|---|---|
| Original | — | 0 dB | — |
| `warm_room` | 220 / 0,8 / +2,0 und 4.200 / 0,9 / −2,5 | −3 dB | 0,065 · 20261119 |
| `bright_room` | 260 / 0,8 / −2,2 und 3.600 / 0,9 / +2,5 | −5 dB | 0,090 · 20261120 |

Der Raumimpuls hat einen direkten Tap bei Sample null und 48
abklingende Reflexionen zwischen 12 und 150 ms. Die Reflexionen haben
reproduzierbare Vorzeichen und eine auf den Raumanteil skalierte
L2-Norm. Die exponentielle Abklingkonstante beträgt 40 ms. Die
Ausgabe hat dieselbe Länge wie das Original. Über einem Spitzenwert
von 0,999 wird der Gain für Mix und Stem gemeinsam weiter abgesenkt.
Beide Fassungen liegen als Mono-WAV Float32 bei 24 kHz vor.

## Reproduktion und Anschluss an P08

Vom Repositoryroot aus. Das Downloadziel enthält nur unveröffentlichte
lokale Artefakte. P07 lädt beim Extrahieren keine Modelle nach.

```powershell
$p07 = 'output/review_jp_20261118/p07'
$env:HF_HUB_DISABLE_IMPLICIT_TOKEN = '1'
.venv/Scripts/hf.exe download m-a-p/MERT-v1-95M README.md config.json preprocessor_config.json configuration_MERT.py modeling_MERT.py pytorch_model.bin --revision 12af15fef9d0ac838c3f475bfbbf26d2060dd4f5 --local-dir "$p07/model"
.venv/Scripts/python.exe -m pip install --no-deps --target "$p07/runtime" transformers==4.49.0 tokenizers==0.21.4 huggingface-hub==0.36.2 regex==2026.11.19
$env:PYTHONPATH = (Resolve-Path "$p07/runtime").Path
.venv/Scripts/python.exe -B -X utf8 -m src.features.p07_extract --smoke --output "$p07/smoke"
.venv/Scripts/python.exe -B -X utf8 -m src.features.p07_extract
.venv/Scripts/python.exe -B -X utf8 -m src.features.p07_verify
```

Die atomare `entry.json` kennzeichnet abgeschlossene Ansichten. Beim
erneuten Aufruf prüft der Export Konfiguration und Dateihashes. Jede
Ansicht bindet Quellhash, Raster, Modell, Software, Produktionsparameter
und Vocal-Artefakt. Der Scaler wird nach Abschluss des Laufs aus dem
Indexbestand gefittet. Die standardisierten Dateien stehen unter
`standardized/<scaler_id>/`.

P08 startet mit `full/manifest.json`. Die Ansichten verweisen auf ihre
`entry.json`, das benachbarte `bars.npz` und das standardisierte
klassische Array. `mert` ist Float32 in der Ordnung
`[Takt, Zustand, Dimension]`. `bar_boundaries_24k` enthält die neun
Halbbeatgrenzen pro Zeile. `bar_start_beat_index` verweist in das
ursprüngliche Analyse-Raster. Benachbarte Zeilen können durch ausgelassene
Takte getrennt sein. Für zusammenhängende Fenster müssen End- und
Startsample aufeinanderfolgender Zeilen übereinstimmen.

Der [Testjournal-Eintrag](../Bemerkungen.md) enthält Laufzeiten,
Speicherspitzen und den Stand der technischen Prüfungen.
