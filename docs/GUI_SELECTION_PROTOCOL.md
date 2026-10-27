# GUI-Auswahl-Sidecar

_Vertragsversion: 1, eingefuehrt am 2026-10-06._

Die native Batch-Review-GUI schreibt Nutzerauswahlen getrennt vom
Batchmanifest und den gerenderten WAV-Dateien. Fuer
`<batch>/manifest.json` lautet der Pfad `<batch>/manifest.selections.json`.
Die Sidecar-Datei beschreibt genau eine aktuell gespeicherte Variante dieses
Paar-Batches. Sie wird beim erneuten Oeffnen nur angewendet, wenn die SHA-256
des unveraenderten Manifests uebereinstimmt.

```json
{
  "format_version": 1,
  "manifest_sha256": "<sha256 des rohen manifest.json>",
  "saved_at_utc": "2026-10-06T12:00:00+00:00",
  "selected_variant": {
    "variant_key": "<candidate-id>|<renderer>|<relativer WAV-Pfad>",
    "candidate_id": "candidate-...",
    "renderer": "equal_power",
    "output_file": "rendered\\0001__candidate-...__equal_power.wav"
  }
}
```

`variant_key` ist die Kombination der manifestierten Candidate-ID, Renderer-
Kennung und des relativen WAV-Pfades; Listenpositionen werden nicht als
Identitaet verwendet. Ein geaendertes oder nicht mehr passendes Manifest
laesst die gespeicherte Auswahl ungueltig erscheinen und wird nicht automatisch
zugeordnet. Der Schreibvorgang erstellt eine temporaere Datei im selben
Verzeichnis und ersetzt anschliessend atomar die Sidecar-Datei. Audio und
Batchmanifest werden nie veraendert.

Version 1 speichert keine gesamte Mehrtrack-Sequenz, Constraints,
Nutzernotizen oder mehrere Kanten. Diese gehoeren spaeter in ein getrenntes,
versioniertes Projektformat.
