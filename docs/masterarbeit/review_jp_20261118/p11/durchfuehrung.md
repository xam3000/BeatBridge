# P11 · Anleitung für die geschlossene Hörsitzung

**Freigabestand 19.11.2026.** Run01 ist als Hörmaterial verworfen. Vor der ersten Sitzung benötigt run02 den eigenen technischen Review und den Nutzercommit für Studienprotokoll, Anleitung und die Prüfsummen der privaten Zuordnungen. Die Schlüssel selbst verwahrt die Versuchsleitung lokal. Im ersten Review wurden die zwei damaligen Schlüsselversionen zum technischen Vergleich gelesen. Zu diesem Zeitpunkt lagen keine Bewertungen vor.

## Versuchsleitung

Vor Beginn das lokale Bestandsmanifest und den unabhängigen Meilensteinreview prüfen. Ausschlüsse, tatsächlich verfügbare Paare und gegebenenfalls die deskriptive Auswertung nach dem [Studienprotokoll](studienprotokoll.md) dokumentieren. Personen einzeln den vorbereiteten Pseudonymen VP01, VP02 und VP03 zuweisen. Personenliste und Zuordnungsschlüssel bleiben bei der Versuchsleitung.

Pro Person ausschließlich den Inhalt ihres Ordners `player` auf einem geschlossenen Hörplatz bereitstellen. Das Teilnehmerkonto darf weder das Repository noch den übergeordneten Studienordner mit den Schlüsseln lesen. Lokale Audiowiedergabe mit Kopfhörern prüfen und eine angenehme Lautstärke mit separatem Entwicklungsmaterial einstellen. Den Zugang organisiert der Autor. Audiodateien dürfen nicht weitergegeben oder veröffentlicht werden.

Nach Freigabe ausschließlich `output/review_jp_20261118/p11_hoerversuch/run02/blind/VP01/player/` beziehungsweise den entsprechenden Ordner für VP02 oder VP03 auf den geschlossenen Hörplatz kopieren. Der jeweilige Schlüssel liegt eine Ebene darüber. `run02/verified.json` nennt die Sitzungskennung für jede Person. Bei Rückgabe die Kennung des Exports mit dieser Liste abgleichen. Sie ist der SHA-256 des privaten, nach Schlüsseln sortierten JSON-Mappings (Python `json.dumps(mapping, sort_keys=True).encode()`). Der frühere Zwischenstand `run01/sessions` wird außerhalb des Studienordners im Archiv der Versuchsleitung `output/review_jp_20261118/p11_archiv_run01_sessions/` aufbewahrt. Vor Übergabe kontrolliert die Versuchsleitung die tatsächlichen Leserechte des Teilnehmerkontos.

Die Versuchsleitung betreut den Hörplatz während der Sitzung. Sie öffnet den Player selbst und stellt für Hörende nur dessen Bedienoberfläche bereit. Die gemeinsam verwendeten Vor- und Nachläufe eines Cues können bei einer Dateianalyse auch dann die Dreiergruppe am Regel-Cue erkennbar machen, wenn alle sieben WAVs gleich lang sind. Deshalb vor jeder Sitzung prüfen und protokollieren, dass über den eingerichteten Hörplatz weder Ordneransicht noch WAV-Download, Entwicklerwerkzeuge oder externe Audioanalyse zur Verfügung stehen. Der JSON-Export für die Antworten muss funktionieren. Wenn diese Trennung am vorgesehenen Platz nicht eingerichtet werden kann, bleibt die Sitzung aus. Akustische Ähnlichkeiten zwischen Bedingungen gehören zum gepaarten Design.

## Hörende

Öffnen Sie `index.html` in Chrome. Sie hören für jedes Songpaar sieben kurze Übergänge. Bewerten Sie die musikalische Gesamtqualität jedes Übergangs auf einer Skala von 0 (sehr schlecht) bis 100 (sehr gut). Spielen Sie die Ausschnitte eines Paars so oft und in der Reihenfolge ab, wie Sie es für Ihren Vergleich benötigen. Derselbe Wert ist für mehrere Clips möglich. Kommentare sind freiwillig. Planen Sie ungefähr 30 bis 40 Minuten ein.

Mit „Weiter“ gelangen Sie nach den sieben Bewertungen zum nächsten Paar. „Zurück“ führt zur vorherigen Seite. Lassen Sie Browserprofil und Dateipfad während der Sitzung gleich, damit Ihre Eingaben lokal erhalten bleiben. Nach der letzten Seite „Bewertungen exportieren“ wählen und die JSON-Datei der Versuchsleitung übergeben.

## Abschluss und P12-Übergabe

Die Versuchsleitung sichert jeden abgeschlossenen Originalexport unverändert mit Eingangszeit und Dateihash. Vor dem Öffnen der Zuordnung Pseudonym, Sitzungskennung, Abschlusszeit, Anzahlen, anonyme IDs, Wertebereich und Duplikate prüfen. Technische Vorfälle getrennt festhalten. Erst nach Abschluss der Datenerhebung und dieser Prüfung die Zuordnung öffnen. Die Personenordner enthalten unterschiedliche feste Permutationen. Jede finale Sitzung verwendet einen separat verwahrten Schlüssel. Testexporte aus dem Entwicklungspilot führen den Split `development`. In P12 gehören ausschließlich echte, abgeschlossene Exporte mit Split `final`.
