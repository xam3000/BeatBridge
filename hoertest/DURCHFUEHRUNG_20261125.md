# Nachtrag: Erfahrungsfragen und Übergangsfenster vom 25. November 2026

Diese Fassung gilt für neu gestartete Sitzungen nach Übernahme des Nachtrags. Sie ersetzt für diese Sitzungen die Erfahrungsfragen und die Regel „Anspielen genügt“ aus dem früheren Bediennachtrag. Bereits begonnene Sitzungen behalten ihre gespeicherte Fassung. Originalaudio, Zuteilung und numerische Kontraste bleiben gleich.

## Erfahrung und Hörsituation

Die drei getrennten Angaben beschreiben die Stichprobe; sie definieren keine Experten-/Laiengruppen und werden nicht zu einem Kompetenzwert addiert:

- Eigene Musikpraxis: insgesamt mindestens einmal pro Woche Instrument, Gesang oder Produktion eigener Musik, einschließlich selbst beigebracht. Antworten: nie bzw. nur seltener, unter einem Jahr, ein bis fünf Jahre, mehr als fünf Jahre, keine Angabe. Längere Pausen nicht mitzählen.
- Eigene DJ-Praxis: insgesamt mindestens einmal pro Monat selbst Übergänge zwischen Songs mischen, etwa mit DJ-Software oder beim Auflegen. Dieselben Zeitkategorien; Üben zu Hause zählt, längere Pausen nicht.
- Genrevertrautheit: Häufigkeit des Hörens elektronischer Tanzmusik in den letzten zwölf Monaten. Antworten: nie, seltener als monatlich, mindestens monatlich aber seltener als wöchentlich, mindestens wöchentlich, keine Angabe.

Bekannte Einschränkungen beim Hören: nein, ja, keine Angabe. Im Institutsplayer zusätzlich Hörort: Institut oder anderer Hörplatz. Die Zeitgrenzen sind pragmatische Beschreibungen und keine validierten Kompetenzstufen. Profilversion 2 und die Prüfsumme dieses Nachtrags werden gespeichert; alte Profile werden nicht umgedeutet.

## Skala und Hörregel

Alle aktuellen Teilnehmertexte verwenden 1 = schlecht und 7 = ausgezeichnet. Die gewählten ganzen Zahlen und ihre Auswertung bleiben auf der Siebenerskala. Gleiche Werte sind zulässig, anfangs ist kein Wert ausgewählt.

Das Pflichtfenster umfasst die gesamte Übergangsspanne aller Varianten des jeweiligen Songpaars sowie zwei Sekunden Kontext davor und danach, begrenzt auf das vorhandene Audio. Grundlage sind die gerenderten Brückenlängen und der fünfsekündige A-Vorlauf. Der harte Schnitt liegt am Ende seiner A-Brücke und ist eingeschlossen. Alle Varianten eines Paars einschließlich der Schnittanker zeigen dasselbe Fenster; seine Grenzen geben keinen Selektor und keine Kurve preis. Die zwei kurzen Entwicklungsübungen werden vollständig gehört.

Ein separater neutraler Index `listening_windows.json` bindet Fenstergrenzen in Samples bei 44.100 Hz an die Audio-SHA-256, Framezahlen und den kanonischen Digest des unveränderten Studienschlüssels. Er wird beim Vorbereiten aus den Render-Metadaten erzeugt. Bei älteren Paketen wird er separat ergänzt; Übergangspositionen werden nicht aus der Gesamtdauer geschätzt. Neue Sitzungen speichern seine SHA-256 und die ihnen zugeteilten Fenster. Die Originalversiegelung enthält den Index ebenfalls.

Die Timeline bleibt frei bedienbar. „Übergang hören“ beginnt am Fensteranfang. Pausen, Wiederholungen und das Anhören in mehreren aneinander anschließenden Abschnitten sind zulässig. Übersprungene Lücken zählen nicht. Der Browser meldet seine tatsächlichen `HTMLMediaElement.played`-Intervalle, der Server vereinigt sie und prüft ihre Grenzen und ihren Zuwachs gegen die seit dem Wiedergabestart vergangene Zeit. Ausschließlich an den beiden äußeren Fenstergrenzen gilt eine Toleranz von 25 ms für die Browser-Zeitauflösung. Weiter setzt bei jeder Variante sowohl die Fensterabdeckung als auch eine Bewertung voraus; das übrige Clipende ist keine Voraussetzung. Bei der Abgabe gelten dieselben Regeln.

Die Aufzeichnung belegt technisch abgespielte Medienzeit. Sie kann Aufmerksamkeit, hörbare Lautstärke oder das Tragen der Kopfhörer nicht nachweisen. Die bisherigen Zähler für Starts und erreichte Clipenden bleiben getrennt erhalten. Hörintervalle und Profilangaben werden neutral gespeichert. Kommentare bleiben optional und gehen nicht in die numerischen Kontraste ein.

Vor dem Start bestätigt der Server die Vorbereitung der Wiedergabe. Erst danach darf der Browser Audio abspielen; ein tatsächliches `playing`-Ereignis wird separat gezählt. Damit verfälschen wartende Speicheranfragen beim Clipwechsel die Zeitprüfung nicht. Die Intervalle werden während des Hörens ungefähr sekündlich und bei Pause, Spulen oder Clipwechsel zusätzlich gespeichert.

## Durchführung vor der Einladung

Fragen, Skalenanker, Anleitung und Hörregel sollen im externen Pilot mit Entwicklungsmaterial gemeinsam geprüft werden. Für die Erhebung wird danach eine gemeinsame Fassung verwendet. Der Endtermin wird vor der ersten Einladung festgelegt. Unterschiedliche Durchführungsfassungen werden im Auswertungsbericht ausdrücklich ausgewiesen; ihre gemeinsame Auswertung ist keine automatische Gleichsetzung der Messbedingungen.
