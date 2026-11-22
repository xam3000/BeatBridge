# Einordnung des Reviews unter `review_jp/`

Stand: 18. November 2026. Geprüfter Checkout: `b40a60a`.
Auftrag: Review und Verbesserungsvorschläge sichten und mit dem aktuellen
Projekt- und Thesisstand abgleichen. Die folgenden Prioritäten sind Empfehlungen;
sie beschließen keinen neuen Forschungsumfang.

## Grundlage und Prüftiefe

Gelesen wurden die vier Reviewdokumente
[`CODE_REVIEW.md`](../../review_jp/CODE_REVIEW.md),
[`EINSCHAETZUNG.md`](../../review_jp/EINSCHAETZUNG.md),
[`TESTLAEUFE.md`](../../review_jp/TESTLAEUFE.md) und
[`ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md`](../../review_jp/ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md).
Der Aktionsplan vom 18. November hat innerhalb dieser Reviewserie Vorrang.
Er wurde gegen den Autorenauftrag vom 11. November, die aktuelle Einleitung
und Diskussion, den Evidence Ledger und ausgewählte Code- und Ergebnisstellen
geprüft. Der Code unter `src/` und die Tests unterscheiden sich laut Git-Diff
nicht vom Reviewstand `56b982a`; `overleaf/` verweist auf eine neuere Revision.

Eine neue kleine Prüfung bestätigte die TCN-Initialisierung mit synthetischen
Eingaben und rechnete die Prozentangaben aus vorhandenen Review-JSONs nach.
Die Audioanalysen, Optimierungen und die fremde Testsuite wurden nicht erneut
ausgeführt. Die 291 bestandenen Tests sind ein historischer macOS-Befund des
Reviewers. Neuheit, Literaturvollständigkeit und Aufwandsschätzungen wurden
nicht extern verifiziert. Testdetails stehen in [`Bemerkungen.md`](../Bemerkungen.md).

## Tragende Befunde

| Thema | Einordnung für den aktuellen Stand |
|---|---|
| TCN-Startpunkt | Im aktuellen Modell bestätigt: sechs EQ-Kanäle und Ducking starten bei 0,5; die Hauptgains sind linear. Der Full-Band-Renderer dämpft dadurch auch die Randbereiche. Das ist keine Equal-Power-Audiobaseline. Die rund −9,86 dB stammen aus den neun Audiofällen des externen Reviews, nicht aus einer neuen Messung. |
| Feste Energievorlage | Im Code bestätigt: Das Energieziel verwendet Anfangs-/Endpegel und eine konfigurierte Senke von 6 dB. Damit wird eine vorgegebene Energiedramaturgie belohnt. Ein niedrigerer Loss allein validiert diese musikalische Annahme nicht. |
| Eingabeabhängigkeit | Die Reviewmessungen zeigen Unterschiede zwischen Modellkurven und unterschiedliche Ergebnisse beim Vertauschen. Eine pauschale Aussage, alle Modelle gäben immer dieselbe Kurve aus, wird dadurch gerade nicht gestützt. Die Messungen der drei trainierten Modelle betreffen August-Läufe. |
| Fehlende Baselines | Eine auf Training optimierte feste Kurve und direkte Optimierung pro Beispiel sind nützliche Ergänzungen. Sie helfen, Nutzen durch Anpassung an die Eingabe von einer allgemein günstigeren Kurvenform zu unterscheiden. |
| Repräsentation und Metrik | Die Lücken bleiben bestehen: kein kontrollierter Vergleich mit selbstüberwachten Repräsentationen und keine unabhängige perzeptuelle Validierung der Cue-Metrik. Der synthetisch geprüfte Cue-Ranker belegt bisher Ausführbarkeit und Lehrerübereinstimmung. |
| Anwendung | Die inversen Tempoverhältnisse im GUI- und Datasetpfad sowie das fest gewählte RoFormer-Backend für Vocal-MLP sind im Code nachvollziehbar. Das sind konkrete Kandidaten für Softwarekorrekturen; die GUI-Szenarien wurden hier nicht ausgeführt. |
| Vergleichbarkeit | Gemeinsame Cues machen unterschiedliche Trainings-, Renderer- und Objectiveverträge nicht zu einem isolierten Architekturvergleich. Diese Grenze ist bereits ausdrücklich in Ledger und Thesis dokumentiert. |

## Aussagen, die enger formuliert werden müssen

### Die 99,9 Prozent sind kein Befund über alle berichteten Modelle

`b1_b2_tcn_fresh_init.json` enthält `run=fresh_init_only`, den top3-Datensatz
vom 31. Juli und neun Validationbeispiele. Der trainierte September-TCN fehlt
in dieser Reviewmessung. Die Werte sind:

| Referenz/Bedingung | Validation-Loss |
|---|---:|
| Frisch initialisierter Full-Band-TCN | 1,962874 |
| Equal Power im Zwei-Band-Renderer | 0,305959 |
| Auf Training optimierte feste Full-Band-Kurvenschar | 0,242856 |
| Direkte Full-Band-Optimierung pro Beispiel | 0,241128 |

Die 99,8996 % sind `(Start − feste Kurve) / (Start − direkt)` und verwenden
den stark gedämpften Start als Referenz. Mit dem vorhandenen Zwei-Band-
Equal-Power-Wert als rechnerischer Referenz ergeben sich 97,3337 %; auch das
ersetzt keine eigens abgesicherte Full-Band-Equal-Power-Bedingung.
Die fast gleichen Losswerte der beiden optimierten Bedingungen sind ein
wichtiger lokaler Befund. Sie beweisen weder globale Eingabeunabhängigkeit
noch, dass der tatsächlich berichtete September-TCN überflüssig ist.
Auch die direkte Optimierung mit begrenzter Schrittzahl ist ein beobachteter
Referenzwert, kein Nachweis des globalen Optimums.

### Konstante Kanäle haben verschiedene Rollen

Der Featureaudit bezeichnet auch `transition_position` und Beat-/Barphasen
als tot, weil sie zwischen ausgerichteten Beispielen identisch sind.
`transition_position` hat jedoch 32 verschiedene Werte innerhalb eines Fensters.
Solche Kanäle können die Zeitposition kodieren, gerade für das zeitgeteilte
MLP. Davon sind nicht implementierte Phrasenkanäle und konstante
Gültigkeitsflags zu unterscheiden. Ein pauschales Entfernen aller 13 Kanäle
ist durch den Audit nicht begründet; eine Ablation müsste ihre jeweilige
Funktion prüfen und bestehende Featureverträge erhalten.

### Gleichstände erklären ihre Ursache nicht

P5 bedeutet: Ein Rater hat bei 19 bewerteten Cues keinen Präferenzvorteil
angegeben. Es bedeutet weder Unhörbarkeit noch Gleichwertigkeit. Kleine
Frame-Pegelunterschiede und Differenzsignalpegel liefern keine allgemeine
Hörschwelle und erklären das Ergebnis nicht kausal. Die Reviewaussage
„unter 1 dB an der Hörschwelle“ sollte deshalb nicht in die Thesis übernommen
werden. Ebenso sind ein fast nuller Strafterm und ein mathematisch konstanter
Term verschieden: Ein Boundary- oder Clippingterm kann einen Schutz gegen
Verletzungen darstellen, auch wenn die untersuchten Fälle ihn kaum aktivieren.

### Die aktuelle Thesis behandelt bereits mehrere Kritikpunkte

Einleitung und Diskussion unterscheiden Optimierung und Hören, benennen den
TCN-Start als untrainiertes Netz, das fehlende variable Epoche-0-Protokoll,
ungleiche Modellverträge, exponierte Daten und die offenen Aufgabenstellungs-
anteile. Das Nullresultat ist also bereits diskutiert. Neu und wertvoll wäre
eine quantitativ geprüfte Mechanismendiagnose mit festen Kurven und
Vertauschungstests. Die Reviewformulierung „nicht aufgearbeitet“ ist dafür
zu pauschal. Die fehlenden Vergleichsexperimente sind durch ihre ehrliche
Benennung allerdings noch nicht erledigt.

## Empfohlene Reihenfolge

1. **Controllerbefund absichern.** Zuerst die Reviewdiagnostik auf die für
   die Thesis maßgeblichen September-Läufe R1–R4 übertragen. Die vier Runordner
   sind hier vorhanden; Vollständigkeit und Kompatibilität ihrer Artefakte
   sind vor einem Lauf zu prüfen. Gleiche Caches, Renderer, Objectives und
   Auswertungsparameter je Pfad; Bedingungen: explizites Equal Power,
   train-optimierte feste Kurve, Modell und direkte Optimierung, ergänzt um
   Vertauschung und Audioabweichungen. Keine alten Artefakte überschreiben.
   Das wäre eine neue Diagnose, noch kein neuer unabhängiger Qualitätstest.
2. **Die Arbeit aus dieser Diagnose verbessern.** Eine kompakte
   Vergleichsmatrix ergänzen, den TCN-Start quantitativ erklären und
   Optimierungsspielraum von tatsächlich gelernter Anpassung unterscheiden.
   Neue Aussagen erst nach geprüften Resultaten in Kapitel 5/6 und Vortrag
   übernehmen. Historische Initialisierungsdaten nicht nachträglich umetikettieren,
   ohne die Herkunft klar zu erhalten.
3. **Softwarefehler getrennt beheben.** Cue-Skalierung und Vocal-Backendvertrag
   mit gezielten fachlichen Regressionen korrigieren. Fallback-Cache und
   Sequenzzustände anschließend separat prüfen. Diese Verbesserungen sind
   nützlich, ersetzen aber keine Evidenz für Controller- oder Metrikqualität.
4. **Über den größeren Forschungsumfang entscheiden.** Die vorgeschlagene
   selbstüberwachte Fortsetzungsmetrik wäre eine neue Forschungsrichtung mit
   Repräsentationsvergleich, eigener Datenerzeugung und Hörvalidierung.
   Zuerst eine kleine Offline-Machbarkeitsprüfung und ein klares Erfolgskriterium
   planen, bevor eine ganze Architekturleiter umgesetzt wird. Gute Fortsetzungs-
   retrieval-Werte innerhalb eines Songs belegen noch keine gute Übergangswahl
   zwischen Songs. Aufnahmeidentität und repetitive EDM-Passagen sind zentrale
   mögliche Abkürzungen. Ein neuer Hörversuch wäre ein zusätzlicher Auftrag.

## Bewertung des Vierwochenplans

Die Richtung „Cue-Wahl gegen Kurvenform“ ist eine prüfbare Hypothese. Dass die
Cue-Wahl den größeren hörbaren Effekt hat, ist bisher nicht gemessen.
Der Plan bündelt neue Daten, Embeddings, mehrere Modelle und Seeds, erneutes
Controllertraining, eine Hörstudie, Exportfunktionen und eine Thesisrevision.
18–21 Tage sind daher eine unbestätigte Schätzung, keine belastbare Zusage.

Vor neuen abschließenden Experimenten sind Hypothesen, Ausschlüsse, gemeinsame
Renderbedingungen und eine wirklich neue Evaluationpopulation festzulegen.
Auch Trackpaare können gemeinsame Tracks enthalten; ein Bootstrap über Paare
allein löst diese Abhängigkeit nicht automatisch. Lautheitsabgleich muss zum
Bewertungsziel passen und dokumentiert sein, besonders bei einer Methode,
deren Effekt gerade in einer veränderten Energiekurve liegt. Eine gerichtete
Nichtunterlegenheitshypothese braucht eine vorab begründete Marge und passende
Auswertung; ein nicht signifikanter Unterschied reicht dafür nicht.

Der Autorenauftrag vom 11. November nimmt GUI-Inhalte und eine große neue
Nutzerstudie aus der aktuellen Thesisarbeit. Der Review kann diese Entscheidung
nicht ändern. Ob und welche weiteren offiziellen Aufgabenanteile abzudecken
sind, bleibt als Scopefrage offen; eine Betreuungsentscheidung ist weiterhin
nicht dokumentiert. Ein neuer MERT-Pfad, GUI-Erweiterungen, Mashup-Export oder
eine zusätzliche Studie wurden mit dieser Sichtung weder begonnen noch beschlossen.
