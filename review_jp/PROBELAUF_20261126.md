# Notiz zum Probelauf auf dem Institutsserver

Notiz vom 26. November 2026. Stand des Codes: Commit `598d46a`. Die Notiz ergänzt die [Rückmeldung vom 25.11.](./RUECKMELDUNG_20261125.md) und ersetzt sie nicht; deren Abschnitt 9 bleibt die Checkliste vor der ersten Einladung. Einstieg in alle Review-Dokumente: [README](./README.md).

## 1. Kurzfassung

Deine Hörtest-Anwendung läuft auf dem Institutsserver. Zwei Personen haben den Test im Probe-Ordner vollständig durchlaufen. Die Daten sind vollständig, und dein Auswertungsweg läuft darauf ohne Fehler.

Aus dem Probelauf folgen vier Punkte:

1. **Zählraster.** Die zweite Person bemängelt in drei von vier Kommentaren das Zählraster, unter anderem Einsätze auf der 5 statt auf der 1. Im Code ist jeder Taktanfang eine mögliche Stelle; ein Raster über acht Schläge habe ich nicht gefunden. Dazu brauche ich deine Stellungnahme (Abschnitt 4).
2. **Übereinstimmung.** Die beiden Personen werten denselben Clip im Schnitt 2 Punkte verschieden. Das Ziel von 6 bis 9 Sitzungen aus der Rückmeldung vom 25.11. ist damit knapp (Abschnitt 5).
3. **Harter Schnitt.** Er ist bei beiden kein Tiefpunkt. Die Thesis kann ihn nicht als schlechte Referenz voraussetzen (Abschnitt 5).
4. **Anwendung.** Vier kleinere Beobachtungen, keine davon hält den Start auf (Abschnitt 6).

Ob die gelernte Stelle oder die optimierte Kurve besser klingt, lässt sich aus zwei Personen nicht ablesen. An Hypothesen und Auswertung ändert der Probelauf nichts.

Marken wie in der Rückmeldung: **[C]** von mir selbst im Code gelesen, **[M]** von mir ausgeführt oder an den Probedaten gemessen. Angehört habe ich nichts.

## 2. Was gelaufen ist

- **Code.** `hoertest/` aus `598d46a`, unverändert. Die Dateien auf dem Server sind mit dem Git-Stand verglichen **[M]**.
- **Start.** Apache mit mod_wsgi statt Gunicorn aus `hoertest/SERVERSTART.md`. Eine eigene Startdatei setzt `BEATBRIDGE_STUDY_DATA` und `BEATBRIDGE_STUDY_URL` und ruft `create_app()` auf. An deinem Code war dafür keine Änderung nötig.
- **Daten.** Dein Paket vom 25.11. mit Schlüssel, Fensterdatei und 65 Clips, unverändert. Die mitgelieferte Antwortdatenbank mit deinen Testsitzungen wird nicht verwendet. Wir haben leere Datenbanken mit dem Schema aus `src/evaluation/p11_session.py:216-224` angelegt.
- **Ordner.** Es gibt einen Ordner für Probeläufe und einen für die Erhebung. Der Ordner der Erhebung ist leer und bleibt es bis zur ersten Einladung.
- **Zugriff.** Ohne Anmeldung antworten Startseite, Sitzungsadresse und Audio-Adresse mit 401 **[M]**.

Abweichung von deinem Plan: Der Probelauf lief mit dem endgültigen Material (`split = final`) und nicht mit `pilot01` aus Entwicklungsmaterial (`hoertest/README.md:79`). Das hat drei Folgen:

- Die Probedaten wertest du mit `--split final` aus, nicht mit `--split development` (`hoertest/README.md:91`).
- Beide Personen kennen die Clips und nehmen an der Erhebung nicht teil.
- Person A ist die Betreuung. Sie kennt das Design, die Zuordnung der Clips kannte sie beim Hören nicht. Person B ist außenstehend, hörte am eigenen Gerät außerhalb des Instituts, hört wöchentlich EDM und hat unter einem Jahr DJ-Erfahrung.

Den Abzug der Probe-Datenbank bekommst du getrennt. Er gehört nicht ins Repository. Seine SHA-256 beginnt mit `1bd2ad48`. Einzelne Wertungen und die Zuordnung stehen deshalb auch nicht in dieser Notiz.

## 3. Was funktioniert **[M]**

- **Sitzungen.** Drei Starts: zwei vollständig, einer nach 15 Sekunden auf der Übungsseite abgebrochen.
- **Vollständigkeit.** Je 51 von 51 Wertungen im Bereich 1 bis 7, Ereignisse zeitlich geordnet, `integrity_check` ohne Befund.
- **Zuordnung.** `layout()` ergibt bei allen drei Sitzungen den gespeicherten `key_hash`.
- **Versiegeln.** `p11_web seal` meldet zwei abgeschlossene Sitzungen, führt die abgebrochene als unvollständig und findet keine Auffälligkeit.
- **Auswertung.** `p12_descriptive --split final` läuft durch: 14 von 14 Seiten gültig, keine Ausschlüsse. Die Kontraste sind gleich meinen von Hand gerechneten.
- **Dauer.** Person A brauchte ohne Pause rund 21 Minuten, Person B 35 Minuten. Die angekündigten 30 bis 40 Minuten (`hoertest/EINLADUNG.md:5`) passen für sorgfältiges Hören. Eine Paarseite dauerte im Median 3,0 und 4,3 Minuten.
- **Wiedergabe.** Vom Ereignis `arm` bis zum Ereignis `play` vergingen im Median 0,1 bis 0,2 Sekunden, einmal 2,2 Sekunden.

Die einzelnen Läufe stehen in den [Testläufen](./TESTLAEUFE.md), Nr. 21 bis 29.

Aus Schritt 3 der Rückmeldung vom 25.11. bleibt offen: Verständnisprobleme sind noch nicht erfragt, und das Unterbrechen und Fortsetzen im selben Browser wurde nicht gezielt geprüft.

## 4. Zählraster

Person B hat vier Kommentare geschrieben, sinngemäß:

| Paar | Kommentar |
|---|---|
| P02 | Lied 1 endet nicht auf dem Schlag, auf dem Lied 2 beginnt. Geschnitten wird mitten im Drop oder Buildup. |
| P07 | Das Zählraster ist nicht eingehalten. |
| P01 | Wo das Zählraster stimmt, beginnen die meisten Übergänge auf der 5 und nicht auf der 1. |
| P10 | Das Zählraster passt besser. Lied 2 setzt aber zu laut ein, der Übergang wirkt überladen. |

Was der Code dazu sagt **[C]**:

- Mögliche Stellen sind alle Schläge mit `count_in_bar == 1`, also jeder Taktanfang (`src/candidates/generation.py:322`, `:325-333`).
- Der gelernte Ranker verlangt Taktanfänge im 4/4-Takt (`src/ranking/learned_cue_ranker.py:363-366`).
- aufTAKT liefert je Schlag die Zeit, die Zählzeit im Takt und die Schläge je Takt (`src/analysis/pre_analysis.py:513-514`).
- Ein Raster über acht Schläge habe ich unter `src/` nicht gefunden. Gesucht habe ich nach `phrase`, `eight`, `achter`, `8-count` und nach Resten des Taktindex.

Ein Taktanfang ist beim Tanzen die 1 oder die 5 eines Achters. Wenn keine Bedingung den Achter berücksichtigt, folgen Einsätze auf der 5 aus der Konstruktion. Die Arbeit handelt von Tanz-Mashups, deshalb wiegt der Punkt schwerer als ein Geschmacksurteil. Er stützt sich bisher auf eine Person und auf meine Lesart des Codes.

Was ich dazu brauche:

1. Stimmt die Lesart, oder gibt es eine Bedingung auf den Achter, die ich übersehen habe?
2. Zähl für die 21 Stellen des Hörtests (7 Paare mal 3 Stellen) aus, auf welcher Zählzeit des Achters Lied 1 endet und Lied 2 beginnt.
3. Hör die Clips von P02 und P07 mit Mitzählen an: Sind die Schläge beider Lieder gegeneinander versetzt? Das gehört zur Tempo-Hörprobe (Schritt 2 der Rückmeldung vom 25.11.). Wenn sie gemacht ist, nenn bitte das Protokoll.
4. Ändere am Material nichts, bevor das besprochen ist. Es gibt zwei Wege: Stellen auf die 1 des Achters beschränken, dann mit neuem Rendern, neuem Paket und neuem Probelauf. Oder die Erhebung so lassen und die Grenze in der Thesis benennen. Das entscheidet die Betreuung.

## 5. Was die Wertungen zeigen und was nicht

Kontraste aus deiner Auswertung, in Punkten der Skala von 1 bis 7 **[M]**:

| Kontrast | Person A | Person B | beide | `descriptive_95` |
|---|---|---|---|---|
| `ssl_minus_rule` | +0,71 | +0,86 | +0,79 | −0,21 bis +1,93 |
| `top_minus_random` | 0,00 | +0,57 | +0,29 | −0,50 bis +1,02 |
| `direct_minus_equal` | −0,38 | +0,81 | +0,21 | −0,10 bis +0,52 |

- **Stelle.** Die gelernte Stelle liegt bei beiden vor der Regel. Je Songpaar reicht `ssl_minus_rule` aber von −1,25 bis +3,5. Ob das an den Paaren liegt oder am Rauschen zweier Personen, lässt sich noch nicht trennen.
- **Mischweise.** Die beiden urteilen gegensätzlich: Person A wertet Equal Power höher, Person B die optimierte Kurve.
- **Übereinstimmung.** Über die 42 gleichen regulären Clips korrelieren die Wertungen mit +0,14. Der mittlere Abstand je Clip beträgt 2,0 Punkte. Die beste Stelle ist in 3 von 7 Paaren dieselbe.
- **Harter Schnitt.** Person A wertet ihn im Mittel mit 4,43 gegen 4,14 für die regulären Übergänge, Person B mit 3,29 gegen 3,17. Unter dem harten Schnitt desselben Paars liegen 21 und 17 der 42 regulären Clips. Jede Person hört je Paar nur einen der drei Schnitte.

Daraus folgt:

1. **Zahl der Sitzungen.** Bei `direct_minus_equal` liegen die beiden Personen 1,2 Punkte auseinander. Bleibt die Streuung zwischen Personen so, liegt der Standardfehler des Mittels bei 9 Personen bei etwa 0,3 Punkten. Unterschiede unter etwa einem halben Punkt wären dann nicht zu sichern. Das ist aus zwei Personen nur eine grobe Größenordnung. Nenn bitte, wie viele Personen du realistisch erreichst; ob das Ziel aus Punkt C der Rückmeldung vom 25.11. steigt, entscheidet die Betreuung. Reihenfolge und harter Schnitt sind erst nach 21 Sitzungen vollständig ausgeglichen (Blöcke von 7 und von 3).
2. **Harter Schnitt.** Setz ihn in der Thesis nicht als untere Referenz voraus. Dein Ankerbericht (`src/evaluation/p12_descriptive.py:154-165`) zeigt, wie er abschneidet. Bestätigt die Erhebung das Bild, ist das ein Ergebnis und kein Störfall.
3. **Nullergebnis.** Es ist möglich, dass die Erhebung keinen Unterschied zeigt. Das ist in Ordnung, wenn die Thesis es so benennt.

## 6. Beobachtungen an der Anwendung

| Nr. | Beobachtung | Fundstelle **[C]** | Mein Vorschlag |
|---|---|---|---|
| 1 | Ein abgebrochener Start belegt einen Platz der Rotation. Der Platz ist die Zahl der vorhandenen Sitzungen und wird beim Absenden der Startseite vergeben. Im Probelauf betraf das einen von drei Starts. | `hoertest/session.py:151`, `:177-178`; `hoertest/app.py:182` | Nicht ändern. Die Auswertung weist die besetzten Positionen aus. In der Thesis nennen. Im Ordner der Erhebung keine Testsitzung starten. |
| 2 | Wie lange jemand hört, wird nur aufgezeichnet, bis das Pflichtfenster gehört ist. Ob der Clip bis zum Ende lief, zeigt allein das Ereignis `ended`. Bei Person A liefen 8 von 49 Clips bis zum Ende, bei Person B 32. | `hoertest/player.html:94` | Benennen. Für Aussagen zur Hördauer `ended` verwenden, nicht `listened`. |
| 3 | Die Seitenzeit zählt Pausen mit. Bei Person A stehen 811 Sekunden auf der letzten Seite, darin 11 Minuten Pause. | `hoertest/session.py:282-284` | Dauern als Median berichten oder Pausen aus den Ereignissen herausrechnen. |
| 4 | Das Kommentarfeld wird 500 ms nach jeder Eingabe gespeichert, jedes Mal mit altem und neuem Text. Bei Person B sind das 69 Einträge für vier Kommentare. Auch wieder gelöschter Text bleibt im Ereignisprotokoll. | `hoertest/player.html:202`; `hoertest/session.py:269-270` | In der Auswertung nur den Endstand verwenden. Prüfen, ob die Zwischenstände in den versiegelten Originalen stehen müssen. |

Zur abgebrochenen Sitzung: Der Übungsclip wurde in 15 Sekunden dreimal gestartet, danach kam nichts mehr. Das kann ein Wiedergabeproblem gewesen sein. Die Betreuung fragt nach, wer das war und auf welchem Gerät.

## 7. Was ich von dir brauche

1. Die Stellungnahme zum Zählraster (Abschnitt 4, Punkte 1 bis 3).
2. Den Stand der Tempo-Hörprobe.
3. Die Zahl der Personen, die du realistisch erreichst.
4. Zu jeder Beobachtung in Abschnitt 6 einen Satz: ändern oder benennen.
5. Die Bestätigung, dass `598d46a` der Stand für die Erhebung ist. Änderungen an `hoertest/` vor der Erhebung bitte nur nach Absprache, weil wir neue Stände selbst auf den Server spielen.

## 8. Grenzen dieser Notiz

- Es sind zwei Personen, eine davon die Betreuung.
- Die Kommentare stammen von einer Person. Ich habe keinen Clip angehört.
- Die Zahlen stammen aus Probedaten und gehen nicht in die Erhebung ein.
