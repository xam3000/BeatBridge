# Thesis-Überarbeitung vom 11. November 2026

Grundlage ist der Autorenauftrag
[`AUFTRAG_THESIS_UEBERARBEITUNG_20261111.md`](./AUFTRAG_THESIS_UEBERARBEITUNG_20261111.md).
Dieser Bericht ergänzt die historischen Audits; deren damalige offenen Punkte
sind keine neue Scope-Entscheidung.

## Vorgehen und Grenzen

1. Aktuellen LaTeX-Stand und Evidenz lesen; vorhandene Änderungen erhalten.
2. Bestätigte Formalia unverändert lassen, zugehörige TODOs entfernen.
3. GUI-Inhalte vollständig aus der Thesis nehmen; keine GUI-Software ändern.
   Den wissenschaftlichen CLI-/Artefaktworkflow erhalten. Aktuelle
   Korrekturaufwands-/Tanznutzen-Studie und leeren Ergebnisabschnitt entfernen.
4. Forschungsfragen auf innerhalb der Protokolle beobachtetes Lernen,
   explorative Hörbefunde und deskriptive Längenevidenz zuschneiden.
   Fehlende Baselines und nicht beantwortete Aufgabenstellungsanteile benennen,
   ohne eine formale Betreuungsentscheidung zu behaupten.
5. Ausschließlich die Hörtestauswertung vom 6. November übernehmen:
   19 Fünffach-Gleichstände; Beispiel 11 ohne Ranking ausgeschlossen;
   keine Äquivalenz-/absolute Qualitätsaussage. Andere Hörsätze getrennt halten.
6. Abstracts, Fazit und Anhang aus belegten Ergebnissen schreiben. Anhang mit
   Protokoll-/Artefaktindex und tatsächlich vorhandenen Bewertungsinformationen
   statt leeren Fragebogen-/Consent-/Reproduktionsversprechen füllen.
7. Abgewählte Diagnose-, Reproduktions- und Teilnehmerdatenaufträge entfernen;
   offene Rechte, Korpusdeskription und aufTAKT-Herkunft nicht als geklärt ausgeben.
8. Statische Prüfung, Compilerprüfung und unabhängiger Kreuzreview; alle
   ausgeführten Tests in `docs/Bemerkungen.md` dokumentieren. Kein Training,
   keine neuen Hör-/Audioexperimente, keine Originaldatenänderung, kein Commit.

Die vorhandene Multi-Session-Disziplin verlangt einen frischen Kreuzreview.
Der Review arbeitet lesend; die Umsetzung bleibt in einer Hand.

## Umgesetzt

- Beide Zusammenfassungen, Kapitel 7 und Anhang aus belegtem Material
  ausgearbeitet. Future Work ist in Kapitel 7 zusammengeführt; dort allein
  steht die mögliche spätere große Nutzerstudie als Option.
- GUI-Inhalte, GUI-Verweise, leeren Korrekturaufwands-/Tanznutzen-Abschnitt
  sowie abgewählte Diagnose-, Reproduktions- und Teilnehmerdaten-TODOs aus
  der Thesis entfernt. Kein GUI-Code geändert.
- Titel, Studiengang, Datumskonfiguration und alle anderen aktiven Formalia
  unverändert; nur die zugehörigen TODO-Kommentare entfernt.
- Die drei Teilfragen auf den beobachteten Within-run-Lernverlauf,
  explorative Hörbefunde und deskriptive Längenevidenz bezogen. Der Text
  behauptet ausdrücklich keine formale Änderung der Aufgabenstellung und
  keinen Betreuungsbeschluss.
- Den abgeschlossenen korrigierten Hörtest in Methodik, Ergebnissen,
  Diskussion, Fazit und Abstracts integriert: 19 Fünffach-Gleichstände,
  0/19/0 gegen Equal Power je gelerntem Modell, Beispiel 11 ohne Ranking
  ausgeschlossen, keine absoluten Kriterienscores und keine Äquivalenzaussage.
  Der alte September-Satz bleibt ausgeschlossen; andere tatsächlich
  unbewertete Entwicklungssets werden getrennt benannt.
- Datenexposition bis zum tatsächlichen Hören am 6. November fortgeschrieben.
  Die 8/7/5-Zählung betrifft die vollständige 20-Cue-Auswahl; das Training-
  `test_reads=0` wird weiterhin nur für den Trainingsaufruf interpretiert.
- Korpusbeschreibung auf bekannte Inventar-/Filter-/Splitzahlen begrenzt;
  fehlende Deskription und Rechte als Grenzen im Fließtext benannt.
  `aufTAKTCl` über vorhandene SHA-/Provenienzdatei dokumentiert, ohne eine
  exakte Quelle, Version oder Lizenz zu behaupten. Keine konkrete neue
  juristische Aussage formuliert; der Lizenzhinweis des Autors wird allein
  als Scope-Entscheidung behandelt.
- Anhang mit existierenden Protokollen, Dataset-/Runpfaden, Bewertungsvertrag,
  Eingangs-Hashes, Exposure- und Fehlerinventar gefüllt. Keine erfundenen
  Einwilligungsunterlagen oder noch nicht ausgeführten Reproduktionsbefehle.
- Historische LaTeX-TODOs durch aktuelle Aussagen und explizite Grenzen
  ersetzt: null verbleibende TODO-Marker bedeutet keine vollständig
  beantwortete Aufgabenstellung.

## Verbleibende wissenschaftliche und formale Lücken

1. Keine protokollgleichen ungelernten Baselines für festen TCN und Variable;
   kein realer Lauf der kompatiblen Variable-MLP-Baseline; keine retrainierten
   Feature-/Control-Ablationen. Ein erster protokollierter Zustand ist nicht
   automatisch Equal Power (Variable beginnt bei trainierter Epoche 1).
2. Kein kontrollierter Vergleich handgefertigter Merkmale und vortrainierter
   SSL-Repräsentationen; kein unabhängiger perzeptueller Nachweis für Proxy-
   oder Rankingmetrik.
3. Gelernter Cue-Ranker nur synthetisch verifiziert; kein belegtes reales
   Teacher-Labeling/Rankertraining und kein gematchter Cue-Auswahlvergleich.
4. Ein-/Dreitakt-Lern- und Hörfälle fehlen; 2/4/6/8 Takte sind kein Ersatz.
   Keine isolierte Qualitätswirkung der Längenkonditionierung belegt.
5. Keine globale unangetastete Testpopulation. Der vorhandene korrigierte
   Modellhörtest ist ein abhängiger Ein-Rater-Entwicklungsvergleich mit
   inkompatiblen Verträgen, begrenzter Verblindung und ausschließlich Ties.
6. Herkunft/Rechte, Genre-/Dauer-/Tempoverteilung sind nicht für alle Korpora
   vollständig belegt. Exakte aufTAKT-Lieferkette, Version und lokale Lizenz
   bleiben offen; vorhandene Runverträge ersetzen keine vollständige
   historische Softwareumgebung. Es wird keine neue Reproduktions- oder
   Teilnehmerdatenerhebung als Abschlussaufgabe gefordert.
7. Semantische Phrasen-/Segmentgrenzen und vollständige Mehrtrack-Assembly
   sind nicht als Ergebnis belegt. Eine formale Betreuungsentscheidung zur
   Abdeckung verbleibender Aufgabenstellungsanteile liegt nicht vor.
8. Der Gesamtbuild ist erfolgreich; eine visuelle PDF-Seitenkontrolle ist in
   dieser Session nicht erfolgt. Build-Erfolg garantiert keine Layoutqualität.

GUI-Abnahme, große Nutzerstudie, zusätzliche Variable-Grid-/Rendererdiagnose,
Fresh-Environment-Reproduktion und zusätzliche Teilnehmerdaten sind gemäß
Autorenauftrag **keine aktuellen Abschlussaufgaben**.

## Prüfungen

- Integrierter Compiler: Gesamtprojekt `overleaf/CGThesis.tex` erfolgreich
  kompiliert; Terminal-TeX ist dafür nicht erforderlich.
- `audit_thesis.py`: 51 Datei-Hashes ohne Abweichung, keine Dataset-
  Zuordnungsfehler, keine undefinierten Referenzen, doppelten Labels,
  fehlenden/ungenutzten Literaturkeys, fehlenden Inputs/Grafiken oder
  Environmentfehler; 26 verwendete Literaturkeys, null TODOs.
- `verify_thesis_revision_20261111.py`: 18 Revisionsinvarianten bestanden,
  einschließlich aktiver Formalia, Formeln/Listings/Literatur, existierender
  Anhangpfade und vorhandener Hörtest-Eingangsdaten. Keine Audios neu geöffnet.
- Unabhängiger lesender Plan- und Quellenreview in frischem Kontext gemäß
  Multi-Session-Disziplin: veraltete Vocal-Modell-Aussage und statisches
  Tabellenbreitenproblem gefunden und behoben. Kein neuer Experimentauftrag.
- Ein erster Diff-Check fand eine zusätzliche Leerzeile am Dateiende von
  Kapitel 5; korrigiert. Abschließende Ergebnisse siehe Testprotokoll.

Details aller Testläufe und ihrer Grenzen stehen in
[`../Bemerkungen.md`](../Bemerkungen.md). Vorher-Snapshot lokal unter
`output/thesis_revision_20261111/`; dauerhafte Prüfergebnisse unter
`docs/masterarbeit/audit_20261111_revision*.json` und
`revision_invariants_20261111.json`. Keine Experimente, kein Training, keine
Original-Audio-/Datenänderungen und kein Commit.
