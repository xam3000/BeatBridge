# Auftrag: Overleaf-Arbeit überarbeiten

Stand: 11. November 2026. Diese Datei richtet sich an den Agenten, der die
Masterarbeit unter `overleaf/` weiterbearbeitet. Sie ergänzt die
Repository-Anweisungen und hält die Entscheidungen des Autors zu den beim
Thesis-Scan gefundenen Aufgaben fest.

## Arbeitsauftrag

Lies vor Beginn die in `AGENTS.md` genannten Projektunterlagen und die
Multi-Session-Disziplin. Prüfe den aktuellen Arbeitsbaum und erhalte vorhandene
Änderungen. Verschaffe dir anhand der LaTeX-Quellen und der Belege einen eigenen
aktuellen Überblick; der Scan vom 11. November 2026 ist eine Momentaufnahme.
Bearbeite die Arbeit inhaltlich und redaktionell so weit wie die vorhandenen
Belege es erlauben. Erfinde keine Ergebnisse, Quellen, Versuchsbedingungen,
Genehmigungen oder formalen Entscheidungen. Führe keine Experimente allein
deshalb durch, weil ein alter Kommentar sie fordert. Dokumentiere jeden
ausgeführten Testlauf in `docs/Bemerkungen.md` nach den Repository-Regeln.
Der Autor erstellt Commits selbst.

## Verbindliche Entscheidungen des Autors

1. **Formalia:** Zu Punkt 1 des Scans („Titelblatt und Formalia“) hat der Autor
   bestätigt: „passt alles“. Die bestehenden Angaben gelten damit als
   akzeptiert. Entferne die zugehörigen TODO-Kommentare, ohne Titel,
   Studiengang oder Datum eigenmächtig umzusetzen oder neu zu interpretieren.
2. **GUI:** Die GUI ist kein Hauptteil der Arbeit und soll vollständig aus der
   Arbeit herausgenommen werden. Entferne GUI-bezogene Abschnitte, Aussagen,
   TODOs und darauf bezogene Querverweise aus der Thesis. Prüfe dabei auch
   Einleitung, Methodik, Implementierung, Ergebnisse, Diskussion und Roadmap.
   Technische Aussagen zur wissenschaftlichen Pipeline bleiben erhalten,
   soweit sie nicht von der GUI abhängen. Ändere oder entferne keine
   GUI-Software aufgrund dieses Auftrags.
3. **Nutzerstudie:** Eine große User Study wird wegen der aktuellen Lizenz
   nicht durchgeführt. Erwähne eine mögliche spätere Nutzerstudie nur unter
   Future Work; behaupte nicht, dass sie durchgeführt oder beschlossen wurde.
   Entferne Anforderungen an eine aktuelle Untersuchung von Korrekturaufwand
   und Nutzen für Tanzaufführungen sowie den entsprechenden leeren
   Ergebnisabschnitt. Bestehende, tatsächlich durchgeführte kleine Hörtests
   und ihre Grenzen bleiben als solche erhalten. Prüfe die Lizenzlage, bevor
   du eine konkrete juristische Aussage formulierst; die Angabe des Autors
   ist die Entscheidung für den Projektscope, kein eigener Rechtsnachweis.
4. **Punkt 13 des Scans:** Eine zusätzliche Diagnose und Reevaluation der
   Variable-Grid- und Rendererfehler wird nicht benötigt. Entferne den
   entsprechenden Arbeitsauftrag aus der Thesis. Bereits belegte negative
   Ergebnisse dürfen sachlich und mit ihren Grenzen stehen bleiben.
5. **Punkt 14 des Scans:** Eine ergänzende Reproduktions- und
   Teilnehmerdaten-Aufgabe wird nicht benötigt. Entferne die entsprechenden
   TODOs und fordere keine neue Fresh-Environment-Reproduktion, zusätzliche
   Installationsanleitung oder neue Teilnehmerdatenerhebung. Vorhandene,
   belegte Angaben dürfen bleiben; fehlende Rechte oder Nachweise dürfen nicht
   als geklärt dargestellt werden.

## Weitere offene Arbeit

Die übrigen Punkte des Scans sind durch die obigen Entscheidungen nicht
automatisch erledigt. Gehe sie anhand der aktuellen Dateien durch:

- Schreibe die deutsche und englische Zusammenfassung sowie Kapitel 7 anhand
  der endgültigen, belegten Ergebnisse und Grenzen. Fülle den Anhang mit
  tatsächlich verfügbaren, geeigneten Materialien oder passe seine Struktur
  nachvollziehbar an.
- Gleiche Forschungsfragen, Baselines und Beiträge mit der vorhandenen Evidenz
  ab. Dokumentiere fehlende Vergleiche und offene Anforderungen ehrlich;
  stelle ausstehende Entscheidungen der Betreuung nicht als getroffen dar.
- Prüfe die Aufgaben zu Repräsentationsvergleich, Korpusbeschreibung,
  Datenexposition, `aufTAKTCl`, Cue-Ranker sowie Ein- und Dreitaktübergängen.
  Unbelegte Resultate dürfen nicht ergänzt werden. Verbleibende Lücken und
  Entscheidungen im Abschlussbericht konkret benennen.
- Aktualisiere das Hörtest-Ergebnis anhand von
  `docs/LISTENING_STUDY_ANALYSE_20261106.md`: 19 bewertete Beispiele mit
  Fünffach-Gleichstand, Beispiel 11 wegen des Tempoproblems ohne Ranking
  ausgeschlossen. Den früheren Export nicht verwenden. Keine Gleichwertigkeit
  oder allgemeine Qualitätsaussage aus dem Ergebnis ableiten.
- Prüfe weitere Hörtest-TODOs auf Aktualität. Eine große neue Nutzerstudie ist
  gemäß Entscheidung oben kein Abschlusskriterium. Bestehende Grenzen der
  vorhandenen Hörbefunde bleiben erkennbar.

## Abschluss und Prüfung

Prüfe nach Änderungen insbesondere aktive und auskommentierte TODOs,
Kapitelstruktur, Referenzen, Literaturverweise und Widersprüche zwischen
Einleitung, Ergebnissen, Diskussion und Fazit. Baue die Thesis, sofern ein
geeigneter Compiler verfügbar ist; melde andernfalls ausdrücklich, dass eine
statische Prüfung keinen Build und keine visuelle Kontrolle ersetzt. Halte
Änderungen und belegte Entscheidungen in der Projektdokumentation fest. Berichte
dem Autor, was umgesetzt wurde, welche Lücken bleiben und welche Prüfungen
ausgeführt wurden. Original-Audio und Daten bleiben unverändert.
