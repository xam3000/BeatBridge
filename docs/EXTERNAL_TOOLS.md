# Externe Binärwerkzeuge

_Stand: 2026-08-12._

Diese Datei dokumentiert lokale Binärwerkzeuge, deren Herkunft und Lizenz
nicht über den Python-Paketmanager reproduziert werden. Eine funktionale
Zuordnung ersetzt keinen Herkunfts- oder Lizenznachweis.

## `aufTAKTCl.exe`

Lokale, am 2026-08-12 gemessene Identität:

| Feld | Wert |
|---|---|
| Pfad im Repository | `aufTAKTCl.exe` |
| SHA-256 | `35f9149cfef66df9b7ac7716953f859f2d37d34af1beb2d2db231062a4a1b523` |
| Größe | `7.195.648` Bytes |
| PE-Dateiversion | nicht vorhanden |
| PE-Produktversion | nicht vorhanden |
| Hersteller-/Copyrightfeld | nicht vorhanden |
| Erster Git-Nachweis | Commit `85369de81ae63b3737b7211e81001887845ecd8b`, 2026-06-17 |

Die Aufrufsyntax `aufTAKTCl -i … -r …` und das Ausgabeformat entsprechen dem
Command-Line-Beispiel der offiziellen
[zplane-AUFTAKT-v4-Dokumentation](https://licensing.zplane.de/uploads/SDK/AUFTAKT/V4/manual/AUFTAKT_v4_sdk_documentation.pdf).
Das stützt die Zuordnung zur Produktfamilie, beweist aber weder eine konkrete
SDK-Version noch die Lieferkette dieser exakten Datei. Auch der erste
auffindbare Git-Commit nennt als Nachricht nur `added analysis` und enthält
keinen Herkunfts- oder Lizenzbeleg.

Die offizielle [zplane-Lizenzseite](https://licensing.zplane.de/licensing)
führt AUFTAKT als lizenzpflichtiges SDK. Insbesondere wird die akademische
Lizenz dort als nicht zur Distribution berechtigend beschrieben. Im
Repository liegt derzeit kein Lizenzvertrag, Herkunftsnachweis oder sonstiger
Beleg für die Weitergabe dieser Binärdatei. Deshalb gilt:

- exakte Quelle: **unbekannt**,
- konkrete AUFTAKT-Version: **unbekannt**,
- lokale Nutzungsberechtigung: **nicht im Repository belegt**,
- Weitergabeberechtigung: **nicht belegt; nicht annehmen**.

Der maschinenlesbare Spiegel steht in
`config/auftakt_binary_provenance.json`. Der Analyse-Cache verwendet nicht
eine geratene Versionsnummer, sondern den vollständigen Binary-SHA-256 als
technische Backendidentität. Vor einer Veröffentlichung oder Weitergabe des
Repositories muss die Lizenzlage geklärt und die Binärdatei gegebenenfalls
aus dem verteilten Artefakt entfernt werden.
