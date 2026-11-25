# Hörtest auf einem Server starten

Für einen Linux-Server mit Python ab 3.11, SQLite und einem HTTPS-Reverse-Proxy.
Die Beispiele verwenden `/srv/beatbridge` als Projektordner.

## 1. Code und Daten bereitstellen

- Den aktuellen Git-Stand nach `/srv/beatbridge` übernehmen.
- `beatbridge_hoertest_daten_20261125.zip` in einen freien Ordner entpacken und dessen `output/`-Struktur in den Projektordner übernehmen. Vorhandene Antwortdatenbanken nicht überschreiben.
- Unter `/srv/beatbridge/output/run03_rotation/` müssen `study_key.json`, `listening_windows.json`, `responses.sqlite` und `media/` liegen. Das Dienstkonto benötigt Leserechte sowie Schreibrechte auf Datenbank und Datenordner.
- Das Archiv enthält bereits gespeicherte Sitzungen. Es ist keine leere Datenbank für eine neue Erhebung. Die Render-Metadaten werden für den laufenden Player nicht benötigt.

## 2. Serverumgebung einrichten

```sh
cd /srv/beatbridge
python3 -m venv .venv-server
.venv-server/bin/python -m pip install gunicorn
```

Der Player benötigt keine GPU oder ML-Pakete.

## 3. Starten

Domain und Kontakt durch die tatsächlichen Angaben ersetzen:

```sh
cd /srv/beatbridge
export BEATBRIDGE_STUDY_DATA=/srv/beatbridge/output/run03_rotation
export BEATBRIDGE_STUDY_URL=https://institut.example/hoertest/
export BEATBRIDGE_STUDY_CONTACT='Name und Kontakt der Versuchsleitung'
.venv-server/bin/gunicorn --workers 2 --bind 127.0.0.1:8765 'hoertest.app:create_app()'
```

Der Befehl läuft im Vordergrund. Für den Dauerbetrieb denselben Startbefehl
mit Arbeitsverzeichnis und den drei Umgebungsvariablen als Dienst, etwa
unter systemd, einrichten. Nach einem Codeupdate den Dienst neu starten.

## 4. HTTPS-Zugang verbinden und prüfen

Der Reverse Proxy leitet `/hoertest/` an `http://127.0.0.1:8765` weiter.
Er muss den vollständigen Pfad und den ursprünglichen `Host` erhalten.
Die öffentliche Adresse muss genau `BEATBRIDGE_STUDY_URL` entsprechen.
Gruppenschutz für alle Hörtestrouten einschließlich Audio aktivieren und
Caching deaktivieren. Den Datenordner nicht als statisches Webverzeichnis freigeben.

Danach die öffentliche URL öffnen und mit einer separaten Kopie der Daten
den Einstieg, Audiowiedergabe, Speicherung und Wiederaufnahme prüfen.
Das ergänzte Datenpaket benötigt weder einen Neurender noch `prepare-windows`.

Weitere Angaben zu Proxy, Pilot, Sicherung und Auswertung:
[Betriebsanleitung](README.md#auf-dem-institutsserver-einrichten).
