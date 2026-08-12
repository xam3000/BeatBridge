# Vortrainierte Modelle und Zitiernachweis

_Stand: 2026-07-30._

Diese Datei hält fest, welche vortrainierten Modelle BeatBridge verwendet,
welche Gewichte tatsächlich ausgeführt wurden und welche Publikation in der
Masterarbeit zitiert werden soll. Kopierbare BibTeX-Einträge stehen in
[`REFERENCES.bib`](./REFERENCES.bib).

## Aktiv: BS-RoFormer für Vocal-Features

BeatBridge verwendet standardmäßig BS-RoFormer über das inference-only Paket
`bs-roformer-infer==0.1.1`. Das Modell wird beim ersten Bedarf automatisch in
`output/.../model_artifacts/roformer_models/` geladen und per SHA-256 im
Vocal-Stem-Manifest identifiziert. Der aktive Default ist
`roformer-model-bs-roformer-sw-by-jarredou`; er liefert einen Vocal-Stem, der
für Featureextraktion und den stem-fähigen Renderer weiterverwendet wird.

Zu zitieren:

- Wei-Tsung Lu, Ju-Chiang Wang, Qiuqiang Kong und Yun-Ning Hung:
  *Music Source Separation with Band-Split RoPE Transformer*, ICASSP 2024,
  DOI `10.1109/ICASSP48485.2024.10446843`.
- Paper: <https://arxiv.org/abs/2309.02612>
- Inferenzpaket: <https://github.com/openmirlab/bs-roformer-infer>
- Modell-Assets: <https://huggingface.co/jarredou/BS-ROFO-SW-Fixed>

Der exakte Checkpoint- und Config-Hash wird erst beim ersten lokalen Lauf
bekannt und im Manifest gespeichert; die Gewichtsbytes werden nicht in Git
eingecheckt. `demucs` bleibt als explizites Vergleichsbackend verfügbar.

## Vergleichsbackend: HT Demucs für Vocal-Features

BeatBridge kann `htdemucs` aus Demucs `4.1.0` explizit anfordern, um pro Song einmalig
einen Vocal-Stem zu erzeugen. Daraus werden anschließend beat-synchrone
Vocal-Aktivität, Prominenz, Onset, Offset, Phrasenfortschritt und eine
Margin-Confidence abgeleitet. Es wird kein Demucs-Modell nachtrainiert.

Zu zitieren:

- Simon Rouard, Francisco Massa und Alexandre Défossez:
  *Hybrid Transformers for Music Source Separation*, ICASSP 2023,
  DOI `10.1109/ICASSP49357.2023.10096956`.
- Offizielles Paper: <https://arxiv.org/abs/2211.08553>
- Offizielle Software: <https://github.com/adefossez/demucs>
- Verwendete Modellkarte: <https://huggingface.co/adefossez/HTDemucs>

Die am 2026-07-30 geprüfte lokale Gewichtsrevision lautet:

```text
Hugging-Face-Repository: adefossez/HTDemucs
Revision: bf35a81b663819a8255c8fefee17f9d812b786b5
Datei: 955717e8.safetensors
SHA-256: d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd
Größe: 84.025.440 Bytes
```

Diese Werte sind nicht nur Dokumentation: Jeder Vocal-Stem und jeder davon
abhängige Featurecache speichert Modellname, Demucs-Version, Hub-Revision,
Gewichts-Hashes, Paper-Metadaten und den Hash des erzeugten Stems im
`manifest.json`. Damit bleibt auch bei einer später geänderten Remote-Version
nachvollziehbar, welche Gewichte einen Datensatz erzeugt haben.

Wichtig für die Interpretation: Demucs liefert einen geschätzten Vocal-Stem,
aber keine kalibrierte Vocal-Wahrscheinlichkeit und keine
Unsicherheitsschätzung. Die sechs BeatBridge-Kanäle sind daher deterministische
Scores aus Stem-/Mix-Energie und Aktivitätsverlauf. `vocal_confidence` ist eine
Margin-Confidence dieses Scores, keine vom Demucs-Paper behauptete
Modellkonfidenz.

## Kandidat, derzeit nicht aktiv: All-In-One

Für musikalische Abschnittsgrenzen wurde geprüft:

- Taejun Kim und Juhan Nam:
  *All-In-One Metrical And Functional Structure Analysis With Neighborhood
  Attentions on Demixed Audio*, WASPAA 2023,
  DOI `10.1109/WASPAA58266.2023.10248148`.
- Paper: <https://arxiv.org/abs/2307.16425>
- Offizielle Software: <https://github.com/mir-aidj/all-in-one>

Das Modell sagt Beats, Downbeats sowie funktionale Abschnittsgrenzen und
-labels voraus. Es ist noch **nicht** Bestandteil des aktiven
Featureextractors:

1. Die offizielle Windows-Installation verlangt einen lokalen NATTEN-Build;
   die dokumentierten Python-Klassifikatoren enden bei Python 3.11, während
   BeatBridge Python 3.14 verwendet.
2. Funktionale Abschnittsgrenzen wie Verse/Chorus sind nicht automatisch
   gleichbedeutend mit den im Featurevertrag gemeinten 8-Takt-Phrasengrenzen.

Bis Backend und Semantik separat validiert sind, bleiben die vier
musikalischen Phrasenkanäle null und `phrase_valid = 0`. Der BibTeX-Eintrag ist
bereits hinterlegt, falls das Modell in einem späteren Experiment verwendet
wird; eine bloße Prüfung ohne Verwendung muss in der Arbeit nicht als
eingesetztes Verfahren dargestellt werden.
