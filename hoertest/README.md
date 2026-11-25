# Hörtest auf der Institutswebseite

[Kurzanleitung: auf einem Server starten](SERVERSTART.md)

Neben jedem Clip stehen sieben Zahlen zur Auswahl. 1 bedeutet „schlecht“, 7 „ausgezeichnet“. Der Einstieg fragt getrennt nach eigener Musikpraxis, Erfahrung mit dem Mischen von Übergängen und Hörhäufigkeit elektronischer Tanzmusik. Die Angaben beschreiben die Stichprobe. Mit der Timeline lässt sich frei spulen. Die Timeline und die normale Wiedergabe beginnen bei 0:00, ebenso „Neu starten“ und „Erneut hören“. Eine bewusst vor dem Start gewählte Spulposition wird beibehalten; Fortsetzen setzt an der Pausenposition an. Neue Sitzungen können weitergehen, sobald jedes Übergangsfenster tatsächlich abgespielt und jeder Clip bewertet wurde. Der restliche Clip muss dafür nicht zu Ende laufen. Übersprungene Lücken zählen nicht, gehörte Teilstücke bleiben bei Wiederaufnahme erhalten. Die zwei kurzen Übungsclips werden vollständig gehört. Bereits begonnene Sitzungen behalten ihre gespeicherten Fragen und Hörregeln. Unter jedem Songpaar steht weiterhin ein automatisch gespeichertes optionales Kommentarfeld. [Durchführung](DURCHFUEHRUNG_20261125.md) · [Bewertung](BEWERTUNG_20261125.md)

**Bedienpräzisierung vom 25.11.2026:** Auf erneuten Autorenwunsch ersetzt der Start bei 0:00 die frühere automatische Positionierung am Fensteranfang. Diese Präzisierung gilt für die aktuelle Oberfläche auch beim Wiederöffnen einer Sitzung. Der per Prüfsumme gebundene Durchführungsnachtrag bleibt als damalige Fassung unverändert; Fenstergrenzen, erforderliche Hörabdeckung, gespeicherte Antworten und Berechnung der Auswertung ändern sich nicht.

Alle Eingeladenen öffnen denselben Link. Mit „Neue Sitzung starten“ erzeugt die Anwendung einen zufälligen Sitzungscode und teilt die Ausschnitte zu. Die Reihenfolge gilt für die gesamte Sitzung. Nach einer Unterbrechung führt „Begonnene Sitzung fortsetzen“ im selben Browser zum gespeicherten Stand. Ein neuer Start mischt erneut. Die beiden technisch notwendigen Cookies gelten sieben Tage ab dem Start. An einem gemeinsam genutzten Rechner erhält jede Person ein eigenes Browserprofil. Für einen Durchgang am Stück genügt auch ein privates Fenster. Vor dem nächsten Durchgang alle privaten Fenster der vorigen Person schließen.

## Run03 mit rotierendem harten Schnitt

**Aktuelles Transportarchiv:** `output/beatbridge_hoertest_daten_20261125.zip` ergänzt den Git-Code. Es enthält das vollständige `output/run03_rotation/`, die 14 Run03-Render-Metadaten sowie Prüfbelege. Die Datenbankkopie wurde mit SQLite-Backup erstellt und enthält sechs Sitzungen/192 Ereignisse. Das Archiv hat 309.358.961 Byte und SHA-256 `105028d0c8e36e9d681c1d89a5331e219ec8e91b7e9ebdc710c8d55a755f0d2b`. Alle Nutzdateien sind im beiliegenden Manifest mit Prüfsummen aufgeführt. In einen freien Ordner entpacken, dann die `output/`-Struktur in den passenden Git-Checkout übernehmen; eine vorhandene Antwortdatenbank nicht überschreiben. Die weitere Startanleitung liegt im Archiv. Für dieses bereits ergänzte Paket ist kein `prepare-windows` nötig. Das ältere `run03_rotation.zip` enthält den Fensterindex noch nicht.

**Vorhandenes Paket einmal ergänzen.** Für neue Sitzungen benötigt es `listening_windows.json`. Auf dem Rechner mit den ursprünglichen Renderdaten den folgenden Befehl ausführen. Er ergänzt nur den neutralen Fensterindex und verändert weder Audiodateien noch Studienschlüssel oder Antworten. Anschließend den Index zusammen mit dem aktualisierten Anwendungsordner auf den Server übertragen und nach einer Codeänderung den Dienst neu starten. Wird nur der fehlende Index ergänzt, liest der bereits aktualisierte Player ihn beim nächsten Sitzungsstart ohne Neustart. Fehlen die Renderdaten, lässt sich kein verlässlicher Index aus dem Medienpaket allein ableiten. Für die einmalige Ergänzung genügen je `results.json` und `protocol.json` aus den sieben unten genannten `stimuli`-Ordnern. Render-WAVs müssen dafür nicht erneut übertragen werden; im laufenden Betrieb werden die Renderordner nicht benötigt.

**Lokaler Stand vom 25.11.2026:** Das Paket `output/run03_rotation/` auf Port 8767 ist bereits ergänzt. Die 14 nachgereichten JSON-Dateien liegen unter `output/run03_paar_json/output/review_jp_20261118/p11_hoerversuch/run03/`. Alle 65 Indexeinträge und der Sitzungsstart auf einer Datenbankkopie sind geprüft. Für einen erneuten Transfer den gesamten ergänzten Paketordner einschließlich `listening_windows.json` verwenden; das ältere `output/run03_rotation.zip` enthält den Index noch nicht.

```powershell
$render = 'output/review_jp_20261118/p11_hoerversuch/run03'
$panels = 'P01','P02','P03','P06','P07','P09','P10' | ForEach-Object { Join-Path $render "$_/stimuli" }
.venv\Scripts\python.exe -m src.evaluation.p11_web prepare-windows output/institut_hoertest/run03_rotation --panels $panels
```

Für eine bestehende Selbsttestkopie denselben Befehl mit deren Datenordner ausführen. Neue `prepare`-Aufrufe erzeugen den Index automatisch. Begonnene ältere Sitzungen bleiben auch ohne neuen Index fortsetzbar; der Start einer neuen Sitzung meldet einen fehlenden Index ausdrücklich. Der Index gehört bei Sicherung, Übertragung und Versiegelung zum Datenpaket.

Der Server enthält alle 63 Run03-Master und zwei separate Übungsclips. Je Sitzung hören die Teilnehmenden 49 Wertungsclips. Pro Songpaar sind das sechs reguläre Übergänge und einer der drei harten Schnitte. In jedem vollständigen Dreierblock gestarteter Sitzungen kommt jeder harte Schnitt je Paar einmal vor.

Das private Paket für die Erhebung liegt unter `output/institut_hoertest/run03_rotation/`. Eine lokale Vorschau startet mit folgendem Befehl auf einem freien Port. Zum Ausprobieren mit Sitzung eine Kopie des Pakets verwenden.

```powershell
.venv\Scripts\python.exe -m hoertest output/institut_hoertest/run03_rotation --port 8767
```

Um das Paket auf dem Auswertungsrechner neu anzulegen, diesen Import mit einem freien Zielverzeichnis ausführen. Ein bestehendes Paket behält seine Sitzungen.

```powershell
$render = 'output/review_jp_20261118/p11_hoerversuch/run03'
$panels = 'P01','P02','P03','P06','P07','P09','P10' | ForEach-Object { Join-Path $render "$_/stimuli" }
.venv\Scripts\python.exe -m src.evaluation.p11_web prepare output/institut_hoertest/run03_rotation --institute --split final --panels $panels --practice output/review_jp_20261118/p11_hoerversuch/pilot02
```

Die Pakete `run02_49/` und `run03_49/` mit festen Regel-Ankern sind archiviert. Für die Erhebung gilt die [Webdurchführung mit Rotation](PROTOKOLL.md).

## Kurzer technischer Pilot

Im BeatBridge-Projektverzeichnis unter Windows lässt sich ein Pilot mit zwei Übungsclips und einem Entwicklungspaar vorbereiten. Der erste Befehl benötigt die vorhandenen Entwicklungsaufnahmen sowie einen neuen Zielordner. Zum erneuten Öffnen eines vorbereiteten Piloten genügt der zweite Befehl.

```powershell
.venv\Scripts\python.exe -m src.evaluation.p11_web prepare output/institut_hoertest/pilot01 --institute --split development --panels output/review_jp_20261118/p11_hoerversuch/pilot_v2/masters --practice output/review_jp_20261118/p11_hoerversuch/pilot02
.venv\Scripts\python.exe -m hoertest output/institut_hoertest/pilot01
```

Der kurze Pilot ist unter [127.0.0.1:8765/hoertest/](http://127.0.0.1:8765/hoertest/) erreichbar. Mit Strg+C endet der im Terminal gestartete Vorschauprozess.

## Auf dem Institutsserver einrichten

Nach einer Aktualisierung des Ordners `hoertest/` den laufenden Vorschau- oder WSGI-Prozess neu starten. Er lädt die Startseite und den Player beim Start.

1. Den Git-Ordner `hoertest/` auf den Anwendungsserver kopieren, beispielsweise nach `/srv/beatbridge/app/hoertest/`. Die Webanwendung braucht Python ab 3.11 mit SQLite und einen WSGI-Server. Für den Betrieb werden weder das übrige BeatBridge-Projekt noch GPU, ML-Pakete oder externe Webdienste benötigt.
2. Für die Erhebung den privaten Ordner `run03_rotation/` separat übertragen, beispielsweise nach `/srv/beatbridge/daten/run03_rotation/`. Darin liegen die geprüften WAV-Ausschnitte unter `media/`, der verdeckte Zuordnungsschlüssel und die Antwortdatenbank. Das Dienstkonto braucht Leserechte für Clips und Schlüssel sowie Schreibrechte für die Datenbank und ihr Verzeichnis. Diesen Ordner außerhalb des öffentlichen Webverzeichnisses halten. Technische Proben und Erhebung erhalten getrennte Datenverzeichnisse.
3. Die Anwendung hinter dem HTTPS-Zugang der eingeladenen Gruppe betreiben. Der Gruppenschutz muss die gesamte Unterseite einschließlich der Audioanfragen umfassen. Wer den gemeinsamen Link erreichen kann, kann selbst eine Sitzung starten. Die Versuchsleitung legt Kontakt, Zugangsweg und Aufbewahrung der Daten mit dem Institut fest. Server- und Proxyprotokolle können IP-Adressen und Sitzungspfade enthalten.
4. Auf der Institutswebseite einen normalen Link auf die Startseite setzen. Bei rein statischem Webspace kann die Seite auf einen geschützten WSGI-Dienst des Instituts verweisen. Die Antworten werden zentral im Datenverzeichnis dieses Dienstes gespeichert.

Beispiel für einen Linux-Dienst mit Gunicorn in einer eigenen Python-Umgebung. Die Adresse durch die tatsächliche URL ersetzen und den Kontakt angeben.

```sh
cd /srv/beatbridge/app
export BEATBRIDGE_STUDY_DATA=/srv/beatbridge/daten/run03_rotation
export BEATBRIDGE_STUDY_URL=https://institut.example/hoertest/
export BEATBRIDGE_STUDY_CONTACT='Versuchsleitung · Kontaktadresse des Instituts'
gunicorn --workers 2 --bind 127.0.0.1:8765 'hoertest.app:create_app()'
```

Gunicorn lässt sich in der Serverumgebung mit `python -m pip install gunicorn` installieren. Der Reverse Proxy reicht den vollständigen öffentlichen Pfad und den ursprünglichen Host an die Anwendung weiter. Bei nginx kann der standortspezifisch geschützte `location /hoertest/`-Block dafür `proxy_set_header Host $http_host;` und `proxy_pass http://127.0.0.1:8765;` verwenden. Ein vorgeschalteter Cache muss für sämtliche Hörtestrouten deaktiviert sein. Die Linkadresse entspricht genau `BEATBRIDGE_STUDY_URL`. [Gunicorn-Dokumentation](https://gunicorn.org/run/)

## Pilot und Auswertung

Für den Pilot läuft `pilot01` getrennt von der Erhebung hinter demselben HTTPS-Gruppenschutz. Eine außenstehende Person nutzt ihn am eigenen Gerät, unterbricht einmal im selben Browser und schließt den Test ab. Im [Prüfjournal](../docs/Bemerkungen.md) Datum, tatsächliche Gesamt- und Paarseitenzeit, Ladezeit je Clip, Verständnisprobleme und bestätigte Abgabe festhalten. Die eine Pilot-Paarseite misst einen Teil der für sieben Paare veranschlagten 30–40 Minuten. Die Pilotperson nimmt an der Erhebung nicht teil.

Vor der ersten Einladung prüft die Versuchsleitung außerhalb der Gruppe die Startseite und eine gültige Audioadresse auf verweigerten Zugriff. Sie bestätigt mit dem Institut Datenpfade, Zugriffsrechte, Sicherung und Aufbewahrungsfrist. Für eine konsistente Sicherung den Dienst anhalten und das private Datenverzeichnis vollständig kopieren oder die SQLite-Backup-Funktion verwenden. Die Sicherung getrennt und geschützt ablegen und die Wiederherstellung prüfen. Im Journal stehen die Ergebnisse sowie der feste Endtermin mit Uhrzeit. Bis zum Termin werden keine Wertungen ausgewertet. Die persönliche Tempo-Hörprobe, die technische Hörkontrolle aller 63 Master und der Nutzercommit des freigegebenen Stands gehen der Einladung voraus. [Einladungstext](EINLADUNG.md) · [Prüfjournal](../docs/Bemerkungen.md)

Zum vorab festgelegten Endtermin den Zugang schließen und den Dienst anhalten. Das vollständige private Datenverzeichnis auf den Auswertungsrechner kopieren. Beim Versiegeln den bereits vor der Einladung dokumentierten Termin einschließlich UTC-Offset angeben. Die Originale enthalten auch eventuelle verspätete Abgaben. P12 weist diese aus und berücksichtigt für die Wertung ausschließlich fristgerecht abgeschlossene Sitzungen. Eine Abgabe genau zum Endtermin zählt. Für den finalen Rücklauf unter Windows:

```powershell
$stichtag = Read-Host 'Vorab festgelegter Endtermin (ISO 8601, mit UTC-Offset)'
.venv\Scripts\python.exe -m src.evaluation.p11_web seal output/institut_hoertest/ruecklauf output/institut_hoertest/originale --deadline $stichtag
.venv\Scripts\python.exe -m src.evaluation.p12_descriptive output/institut_hoertest/originale output/institut_hoertest/ruecklauf/study_key.json output/institut_hoertest/auswertung.json --split final
```

Für Pilotdaten gilt `--split development`. Die Auswertung der Erhebung weist die gestarteten, abgeschlossenen und unvollständigen Sitzungen, die tatsächlich besetzten Paarpositionen und die Schnittanker je Paar aus. Die Hörortangabe erlaubt eine zusätzliche deskriptive Auswertung. Ein Code bezeichnet eine Sitzung. Die Zahl verschiedener Personen lässt sich daraus allein nicht bestimmen. [Durchführung mit Rotation](PROTOKOLL.md) · [Methodenreview zur Weboberfläche](../docs/masterarbeit/review_jp_20261118/reviews/HOERTEST_INSTITUT.md)
