# P11 · Geschlossener Hörversuch

**Festgelegt am 19. November 2026 vor Finalanalyse, Stimuluswahl, Render und Ratings.** Es gelten die Abschnitte „Hörversuch F1/F2“ und „Kontraste, Abhängigkeiten und Ausfälle“ des [P01-Protokolls](../../../EVALUATION_PROTOCOL.md) in Commit `2a70dc1`, einschließlich aller Schwellen, Ausschlüsse und Ausweichanalysen. Die elf gerichteten Paare enthalten 22 Recording-Gruppen. Der Autor organisiert den geschlossenen Zugang für mindestens drei Personen. Die Entwicklungsnotizen bleiben separat.

## Stimuli und Zuteilung

Den vollständigen Pool aus detektierten, durchgängigen Vier-Takt-Cues in 4/4 mit 5 s A-Kontext vor S, 8 s ausgerichtetem B-Kontext nach T und höchstens 15 % Tempoabweichung relativ zu A verwenden. SSL-Top-1 (MERT-Stufe 2, Seed 20260926, Epoche 22, CUDA/bf16), Regel-Top-1 und eine uniforme Zufallswahl auf denselben IDs. Gleichstand nach Kandidaten-ID. Zufallswahl aus der sortierten Liste mit Seed aus 20261119 und Paar-ID. Zusammentreffende Cues behalten alle Methodenlabels. Audiohashes und Koinzidenzen berichten.

P04 rendert je Cue Equal Power (E) und die direkt optimierte Zwei-Band-Kurve (D, Objective v4, 80 Adam-Schritte). Der siebte Clip ist der harte Schnitt am Regel-Cue nach der allein von A gespielten Brücke. Stereo, 44.100 Hz, 511 FIR-Taps, 180 Hz, 32 Stützstellen. Über den ganzen Clip −23 LUFS anstreben, bei Bedarf alle sieben gemeinsam bis höchstens −1 dBTP absenken. PCM24 nachmessen, Toleranzen 0,2 LU und 0,01 dBTP. Technische Ausschlüsse vor Ratings mit ID, Zeitpunkt und Grund dokumentieren. Identischer technischer Retry erlaubt. Keine Ersetzung ausgeschlossener Paare oder Umwahl nach Klang.

Pro Person Paarreihenfolge und Clippositionen aus 20261120, pseudonymer Personen-ID und Paar-ID permutieren. Musikalische Gesamtqualität des Übergangs je Clip von 0 bis 100 bewerten, Kommentar freiwillig. Die Versuchsleitung verwahrt den Zuordnungsschlüssel und sichert die Rohbewertungen vor Entblindung. Bedienprobe auf Entwicklungsclips.

## Hypothesen und Auswertung

Sechs Zellen je vollständigem Personen-Paar-Panel. Über Personen innerhalb eines Paars mitteln, dann Paare gleich gewichten. H1 ist der mittlere SSL-minus-Regel-Unterschied über E/D, Schwelle 0. H2 vergleicht den Betrag des Effekts Mittel(SSL, Regel) minus Zufall über E/D mit dem Betrag von D minus E über alle drei Selektoren. Gerichtete Effekte berichten und die Betragsdifferenz in jeder Ziehung neu bilden, Schwelle 0. H3 prüft D minus E gegen −5 Skalenpunkte. Fünf Punkte sind der vorab akzeptierte mittlere Nachteil (ein Zwanzigstel der Skala), ohne Annahme einer gemessenen Wahrnehmungsschwelle.

10.000 gepaarte Bootstrapziehungen, Seed 20261121, mit allen Personen und Zellen jedes gezogenen Paars. Bei überlappenden Gruppen ganze Zusammenhangskomponenten ziehen und über deren Kanten mitteln. Zweiseitige 95-%-Perzentilintervalle und einseitige untere Grenzen beim Quantil 0,05/3 berichten. Jede bestätigende Aussage verlangt das strikte Überschreiten der jeweiligen Schwelle. Ergänzend das Modell `Bewertung ~ Cue * Kurve + (1|Trackpaar) + (1|Person)`, Zellmittel, Interaktion und Leave-one-person-out-Kontraste berichten.

Fehlende, ungültige und doppelte Werte vor Entblindung prüfen. Unvollständige Sechserpanels und widersprüchliche Duplikate ausschließen, fehlender Anker betrifft nur dessen Beschreibung. Keine Imputation. Unter zehn unabhängigen Paarkomponenten, unter drei Personen oder bei singulärem bzw. nicht konvergiertem Modell gilt der deskriptive Ausweichpfad. Ab zwei Komponenten sind deskriptive Bootstrapintervalle möglich. Sekundär je Paar Spearman-ρ über die sechs Zellmittel für −Proxy, Regel-, Render- und SSL-Score, mittlere Ränge bei Gleichstand, Nenner bei konstanten Vektoren. Anker separat.
