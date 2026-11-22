# P03 · Inferenzvertrag und wiederholbare Analyse

Stand 18. November 2026. Ursachenbefund und einzelne Prüfläufe stehen im
[Testprotokoll](../Bemerkungen.md).

## Tempo und Cue-Position

Der manuelle GUI-ML-Pfad snappt A und B im jeweiligen Originalraster auf
den gewählten Downbeat. Die ungestreckten Cue-Samples werden bei der
Abtastrate des Feature-Protokolls bestimmt. Für das auf A-Tempo gebrachte
Featurefenster von B gilt
`round(B_original_sample * BPM_B / BPM_A)`. Bei schnellerem Zieltempo
liegt das Fenster früher, bei langsamerem später. Die Berechnung liegt
in `src/tempo/coordinates.py` und wird von beiden Dataset-Exportern und dem
GUI-Adapter verwendet. Der Waveform-Renderer erhält weiterhin den
ungestreckten Kandidaten-Cue und führt seine eigene Rasterausrichtung im
bestehenden Bridge-Pfad durch.

Der Adapter verwendet pro Render und Track dasselbe Analyseergebnis für
Downbeat-Snap, Featurefenster und Bridge. Dadurch kann ein Retry das
Raster während eines Renders nicht wechseln. Der GUI-Export hält die
verwendeten BPM, Feature-Cue-Samples und die Grid-Provenienz fest.

## Feste Modellverträge

`src/ml/inference_contract.py` prüft Dataset-ID, Manifest-SHA-256,
Feature-Protokoll, globale Merkmale, Geometrie, Kanalreihenfolge und
Trainingsnormalisierung. Backend und Modell der Featureextraktion kommen
aus dem Dataset. Ein Vocal-MLP liest den separaten Stem-Vertrag aus dem
Run und den gebundenen Waveform-Manifesten. Widersprüchliche oder fehlende
Angaben führen zu einer Meldung mit Vertragsfeld und Wert. Die bestehenden
Checkpoint-Loader instanziieren das deklarierte Modell und prüfen
Run-ID, Epoche und Checkpoint-Hash.

R1 und R3 verwenden Demucs/`htdemucs` für Features. R2 verwendet dasselbe
Feature-Backend und BS-RoFormer für die Stems des Renderers. Die geprüften
August-Vocal-Runs verwenden Demucs für beide Eingaben. Deren Waveform-
Manifeste v2 mit `htdemucs` stammen aus dem damaligen Demucs-Pfad vor
Einführung des Backendfelds und bleiben lesbar. Der GUI-Preview rendert
bei 44,1 kHz. Filtergrenzen kommen aus dem Run, die Fensterlänge wird
auf die Preview-Abtastrate umgerechnet (bei R1–R3 von 127 auf 511 Taps).
R4 bleibt ein separater variabler Feature-/Rendervertrag.

## Historische Artefakte

- Ältere GUI-Previews mit unterschiedlichen BPM können Controls aus
  dem falschen Zielfenster enthalten. Gleiche BPM umgehen diesen
  Koordinatenfehler. Vocal-MLP-Previews können unabhängig davon die
  falschen Feature-Backends oder Renderer-Stems verwendet haben.
  Falls solche Previews erneut als Beleg gebraucht werden, müssen sie am
  korrigierten Pfad unter einem neuen Artefaktpfad gerendert werden.
- Die Dataset-Exporter hatten die richtige Skalierungsrichtung. Der
  gemeinsame Helfer erhält die bestehende Rundungsreihenfolge. Die
  Trainingsinputs, Datasets, Checkpoints, Objectives und gespeicherten
  Ergebnisse wurden beim Fix nicht neu erzeugt.
- Ein historischer Analyse-Fallback behält Pfad und Inhalt. Ein
  Analyseaufruf versucht aufTAKT erneut. Sobald ein erkannter Grid-Eintrag
  vorliegt, unterscheidet sich die Grid-Provenienz, auch wenn die
  Beat-Samples zufällig identisch sind. Dadurch erhalten neu extrahierte
  Track-Features einen eigenen Cache-Key. Bereits exportierte
  Datasetbeispiele und ihre Provenienz behalten ihren historischen Stand.
  Details stehen im [Analysevertrag](../ANALYSIS_PROTOCOL.md).
- Der historische P5-Hörsatz nutzte für R1–R3 die gespeicherten D2-Features
  und für R4 den separaten Variable-Eingabepfad. Der inverse GUI-Cue war
  dort nicht beteiligt. Das Protokoll und die Werte des historischen
  Vergleichs bleiben für genau diese Renderbedingungen erhalten.

## Übergabe an P04

Für feste Controller stehen Vertragsprüfung und Checkpoint-Loader bereit.
Für Geometrie und Stems kann P04 auf die bestehenden
`extract_aligned_bridge`-/`extract_aligned_vocal_bridge`-Pfade zurückgreifen.
P04 soll je Vergleich einen expliziten gemeinsamen Rendervertrag für
Equal Power, feste Kurve, gelernte Controls und direkte Optimierung binden.
Trainings- und Preview-Abtastrate sind unterschiedliche Angaben.
Variabler R4-Vertrag, Lautheitsabgleich, reproduzierbares Equal Power
und der reale Entwicklungslauf gehören zu P04. Der Status der
Voraussetzungen steht im [Umsetzungsplan](../REVIEW_JP_UMSETZUNG.md).
