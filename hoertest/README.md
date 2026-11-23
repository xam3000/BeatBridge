# Hörtest auf der Institutswebseite

Alle Eingeladenen öffnen denselben Link. Mit „Neue Sitzung starten“ erzeugt die Anwendung einen zufälligen Sitzungscode und teilt die Ausschnitte zu. Die Reihenfolge gilt für die gesamte Sitzung. Nach einer Unterbrechung führt „Begonnene Sitzung fortsetzen“ im selben Browser zum gespeicherten Stand. Ein neuer Start mischt erneut. Die beiden technisch notwendigen Cookies gelten sieben Tage ab dem Start. An einem gemeinsam genutzten Rechner erhält jede Person ein eigenes Browserprofil. Für einen Durchgang am Stück genügt auch ein privates Fenster. Vor dem nächsten Durchgang alle privaten Fenster der vorigen Person schließen.

## Hörtest mit allen 49 Aufnahmen

Für die Erhebung werden dieselben sieben Songpaare wie in Run02 mit der aktuellen Pipeline gerendert. Alle hören dieselben 49 Bewertungsclips in wechselnder Reihenfolge. Dazu kommen zwei Übungsclips aus dem Entwicklungsmaterial. Pro Paar werden sechs reguläre Übergänge und der harte Schnitt am Regel-Cue verwendet. Die zwei weiteren harten Schnitte pro Paar verbleiben im Renderarchiv.

Das private Paket für die Erhebung liegt unter `output/institut_hoertest/run03_49/`. Aus dem BeatBridge-Projektverzeichnis startet dieser Befehl die [lokale Fassung mit allen 49 Aufnahmen](http://127.0.0.1:8766/hoertest/).

```powershell
.venv\Scripts\python.exe -m hoertest output/institut_hoertest/run03_49 --port 8766
```

Um das Paket auf dem Auswertungsrechner neu anzulegen, diesen Import mit einem freien Zielverzeichnis ausführen. Ein bestehendes Paket behält seine Sitzungen.

```powershell
$render = 'output/review_jp_20261118/p11_hoerversuch/run03'
$panels = 'P01','P02','P03','P06','P07','P09','P10' | ForEach-Object { Join-Path $render "$_/stimuli" }
.venv\Scripts\python.exe -m src.evaluation.p11_web prepare output/institut_hoertest/run03_49 --institute --fixed-rule-anchors --split final --panels $panels --practice output/review_jp_20261118/p11_hoerversuch/pilot02
```

Die frühere Fassung liegt separat unter `output/institut_hoertest/run02_49/`. Der Unterbefehl `prepare-run02` stellt sie aus den archivierten Aufnahmen wieder her. [Durchführung mit aktuellem Material und festen Ankern](PROTOKOLL_FESTE_ANKER.md)

## Kurzer technischer Pilot

Im BeatBridge-Projektverzeichnis unter Windows lässt sich ein Pilot mit zwei Übungsclips und einem Entwicklungspaar vorbereiten. Der erste Befehl benötigt die vorhandenen Entwicklungsaufnahmen sowie einen neuen Zielordner. Zum erneuten Öffnen eines vorbereiteten Piloten genügt der zweite Befehl.

```powershell
.venv\Scripts\python.exe -m src.evaluation.p11_web prepare output/institut_hoertest/pilot01 --institute --split development --panels output/review_jp_20261118/p11_hoerversuch/pilot_v2/masters --practice output/review_jp_20261118/p11_hoerversuch/pilot02
.venv\Scripts\python.exe -m hoertest output/institut_hoertest/pilot01
```

Der kurze Pilot ist unter [127.0.0.1:8765/hoertest/](http://127.0.0.1:8765/hoertest/) erreichbar. Mit Strg+C endet der im Terminal gestartete Vorschauprozess.

## Auf dem Institutsserver einrichten

1. Den Git-Ordner `hoertest/` auf den Anwendungsserver kopieren, beispielsweise nach `/srv/beatbridge/app/hoertest/`. Die Webanwendung braucht Python ab 3.11 mit SQLite und einen WSGI-Server. Für den Betrieb werden weder das übrige BeatBridge-Projekt noch GPU, ML-Pakete oder externe Webdienste benötigt.
2. Für die Erhebung den privaten Ordner `run03_49/` separat übertragen, beispielsweise nach `/srv/beatbridge/daten/run03_49/`. Darin liegen die geprüften WAV-Ausschnitte unter `media/`, der verdeckte Zuordnungsschlüssel und die Antwortdatenbank. Das Dienstkonto braucht Leserechte für Clips und Schlüssel sowie Schreibrechte für die Datenbank und ihr Verzeichnis. Diesen Ordner außerhalb des öffentlichen Webverzeichnisses halten. Technische Proben und Erhebung erhalten getrennte Datenverzeichnisse.
3. Die Anwendung hinter dem HTTPS-Zugang der eingeladenen Gruppe betreiben. Der Gruppenschutz muss die gesamte Unterseite einschließlich der Audioanfragen umfassen. Wer den gemeinsamen Link erreichen kann, kann selbst eine Sitzung starten. Die Versuchsleitung legt Kontakt, Zugangsweg und Aufbewahrung der Daten mit dem Institut fest. Server- und Proxyprotokolle können IP-Adressen und Sitzungspfade enthalten.
4. Auf der Institutswebseite einen normalen Link auf die Startseite setzen. Bei rein statischem Webspace kann die Seite auf einen geschützten WSGI-Dienst des Instituts verweisen. Die Antworten werden zentral im Datenverzeichnis dieses Dienstes gespeichert.

Beispiel für einen Linux-Dienst mit Gunicorn in einer eigenen Python-Umgebung. Die Adresse durch die tatsächliche URL ersetzen und den Kontakt angeben.

```sh
cd /srv/beatbridge/app
export BEATBRIDGE_STUDY_DATA=/srv/beatbridge/daten/run03_49
export BEATBRIDGE_STUDY_URL=https://institut.example/hoertest/
export BEATBRIDGE_STUDY_CONTACT='Versuchsleitung · Kontaktadresse des Instituts'
gunicorn --workers 2 --bind 127.0.0.1:8765 'hoertest.app:create_app()'
```

Gunicorn lässt sich in der Serverumgebung mit `python -m pip install gunicorn` installieren. Der Reverse Proxy reicht den vollständigen öffentlichen Pfad und den ursprünglichen Host an die Anwendung weiter. Bei nginx kann der standortspezifisch geschützte `location /hoertest/`-Block dafür `proxy_set_header Host $http_host;` und `proxy_pass http://127.0.0.1:8765;` verwenden. Ein vorgeschalteter Cache muss für sämtliche Hörtestrouten deaktiviert sein. Die Linkadresse entspricht genau `BEATBRIDGE_STUDY_URL`. [Gunicorn-Dokumentation](https://gunicorn.org/run/)

## Pilot und Auswertung

Vor der ersten Einladung einen vollständigen Pilotdurchgang mit Entwicklungsmaterial über den vorgesehenen Institutszugang durchführen. Eine außenstehende Person prüft am eigenen Hörplatz, ob sie Aufgabe, Wiederholung, Bewertung, Fortsetzen und Abgabe versteht. Für sieben Paare sind rund 30–40 Minuten eingeplant. Der Pilot dient auch dazu, diese Zeit und das Laden der Ausschnitte über die tatsächliche Verbindung zu prüfen.

Nach der Erhebung den Dienst stoppen und das vollständige private Datenverzeichnis auf den Auswertungsrechner zurückkopieren. Dort die abgeschlossenen Sitzungen in einem neuen Verzeichnis versiegeln. Beispiel für eine finale Erhebung unter Windows:

```powershell
.venv\Scripts\python.exe -m src.evaluation.p11_web seal output/institut_hoertest/ruecklauf output/institut_hoertest/originale
.venv\Scripts\python.exe -m src.evaluation.p12_descriptive output/institut_hoertest/originale output/institut_hoertest/ruecklauf/study_key.json output/institut_hoertest/auswertung.json --split final
```

Für die Pilotdaten gilt `--split development`. Die Auswertung des aktuellen Satzes trägt die Materialkennung `cue_grid_regression_v3_fixed_rule`. Sie zählt gestartete, abgeschlossene und unvollständige Sitzungen, die tatsächlich besetzten Paarpositionen und die Schnittanker je Paar. Ein Code steht für eine Sitzung. Die Zahl verschiedener Personen lässt sich daraus allein nicht bestimmen. [Durchführung mit festen Ankern](PROTOKOLL_FESTE_ANKER.md) · [Methodenreview zur Weboberfläche](../docs/masterarbeit/review_jp_20261118/reviews/HOERTEST_INSTITUT.md)
