# Machine Re-Mix / BeatBridge – Projekt-Gesamtübersicht

> **Auftrag vom 18.–23. November 2026.** F1 untersucht die Übergangsstelle und Mixing-Kurve, F2 die gelernte Fortsetzungsmetrik und F3 die eingabeabhängigen Controller. Die Betreuung hat den geschlossenen Hörversuch auf sieben Paare begrenzt. Die Auswertung ist deskriptiv. Abschnittsauswahl, vollständiger Mashup-Export und Baseline-Übergänge von einem bis vier Takten gehören zum Softwareumfang. Die formale Entscheidung zur übrigen Aufgabenabdeckung steht aus. Die folgenden älteren Scope-Angaben dokumentieren den damaligen Auftrag. [Umsetzungsregister](REVIEW_JP_UMSETZUNG.md) · [Betreuungsrückmeldung](../review_jp/RUECKMELDUNG_20261122.md)

_Quelle: frühere Ausarbeitung (ChatGPT-Diskussion), ins Projekt übernommen am 2026-07-17. Dies ist der maßgebliche Kontext für Ziel, Scope und Zeitplanung der Masterarbeit._

> **Thesis-Scope vom 2026-11-11 (Autorenauftrag):** Für die Überarbeitung unter
> `overleaf/` sind die bestehenden Formalia bestätigt. GUI-Inhalte werden aus
> der Thesis entfernt; GUI-Software bleibt bestehen. Eine große Nutzerstudie
> sowie aktuelle Messungen zu Korrekturaufwand und Tanznutzen sind keine
> Abschlussaufgaben; eine mögliche spätere Studie steht allein in Future Work.
> Zusätzliche Variable-Grid-/Rendererdiagnose, Fresh-Environment-Reproduktion
> und Teilnehmerdatenerhebung sind ebenfalls abgewählt. Dies dokumentiert die
> Entscheidung des Autors, keinen nachgewiesenen Lizenzinhalt und keinen
> Betreuungsbeschluss zur übrigen Aufgabenstellung. Verbleibende wissenschaftliche
> Evidenzlücken bleiben ausdrücklich benannt. Der korrigierte Modellhörtest
> ergibt 19 Fünffach-Gleichstände bei einem ungerankten Ausschluss, keinen
> beobachteten Präferenzvorteil und keinen Äquivalenznachweis. Auftrag und
> Umsetzung: [`masterarbeit/THESIS_REVISION_20261111.md`](./masterarbeit/THESIS_REVISION_20261111.md).
> Entgegenstehende Anforderungen im historischen Exposé unten werden für
> diesen Thesis-Auftrag durch diese Präzisierung ersetzt.

> **Scope-Präzisierung vom 2026-07-29:** Wissenschaftlicher Kern ist das
> selbstüberwachte Lernen zeitabhängiger Mixing-Kurven ohne
> Ground-Truth-Kontrollkurven. Ein differenzierbarer Renderer wendet die
> vorhergesagten Controls auf vier Takte zwischen einem nutzergegebenen
> Drop-Ende A und Drop-Anfang B an; eine eingefrorene Übergangsmetrik liefert
> das Lernsignal. Compatibility- und Render-Metriken bleiben notwendige
> Baselines und Hilfskomponenten, sind aber nicht mehr der alleinige
> Hauptbeitrag. Diese Präzisierung ersetzt entgegenstehende Priorisierungen in
> der früheren Ausarbeitung.

> **Feature-Präzisierung vom 2026-07-30:** Feature-Protokoll 1 verwendet pro
> Track 32 Halbbeat-Schritte über die vier gerenderten Takte, 54 exakt benannte
> Kanäle und 16 globale Merkmale. Ein acht Takte breiter Analysekontext um die
> Cue Points liefert insbesondere 8-Takt-Phrasen- und Vocal-Phrasenmerkmale.
> Die vollständige Definition und Missingness-Regeln stehen in
> `FEATURE_PROTOCOL.md`.

> **Modellprovenienz vom 2026-07-30:** Vortrainierte Analysemodelle sind
> zulässig, sofern Paper, Software-/Modellversion, konkrete Gewichtsrevision
> und Gewichts-Hash gespeichert werden. Der aktive Vocal-Pfad verwendet
> `htdemucs`; Zitiernachweis und BibTeX stehen in `PRETRAINED_MODELS.md` und
> `REFERENCES.bib`. Der wissenschaftliche Eigenbeitrag bleibt das
> selbstüberwachte Lernen der Mixing-Kurven, nicht das erneute Trainieren einer
> Vocal-Separation.

> **Dataset-Präzisierung vom 2026-07-31:** Train, Validation und Test werden
> strikt anhand des Audio-SHA getrennt; Paare über Splitgrenzen werden
> verworfen. Normalisierung wird nur auf Trainings-Tracks gefittet. Das
> versionierte NPZ-/JSONL-Format und die reale 45/9/9-Erstinstanz stehen in
> `DATASET_PROTOCOL.md` beziehungsweise im ignorierten `output/datasets/`.

> **Objective-Präzisierung vom 2026-07-31:** Objective Version 4 verwendet
> zusätzlich gültigkeitsmaskierte Vocal-Overlap-, Vocal-Grenz- und
> Transientenartefakt-Terme aus Feature-Protokoll 1. Die Gewichte wurden nur
> am track-getrennten Validation-Split gewählt; der neue geblendete Hörsatz
> stammt vollständig aus dem unangetasteten Test-Split.

> **Hör-Gate vom 2026-08-04:** Nach vollständiger geblendeter Bewertung
> wurden die neun Testbeispiele entblindet: alle neun Präferenzen gelten der
> Objective-v4-optimierten Kurve gegenüber Equal Power. Der Wertungsgewinn
> liegt ausschließlich bei Sauberkeit; für Vocal-Klarheit besteht noch kein
> Unterschied. Da nur drei Test-Audiohashes mit mehreren Cue-Varianten
> vorliegen, ist dies ein bestandenes Entwicklungs-Gate und kein
> populationsweiter Wirksamkeitsnachweis.

> **ML-Baseline vom 2026-08-04:** Die erste Feature→Control-Baseline ist ein
> kleines zeitgeteiltes MLP mit 10.394 Parametern. Es sagt keine unabhängigen
> Gains, sondern die konstruktiv monotonen Control-v3-Inkremente voraus und
> wird ohne Zielkurven über Renderer und Objective v4 trainiert. Ein
> hashbasierter Bridge-Waveform-Cache verhindert wiederholtes Laden und
> Time-Stretching pro Epoche. Der versionierte Trainingsrunner speichert
> deterministische Train-/Validation-Verläufe, atomare Best-/Latest-
> Checkpoints, Early Stopping und Resume. Im Erstlauf sank der
> Validation-Proxy-Loss gegenüber Equal Power um 3,26 %. Der geblendete
> Neuner-Entwicklungsvergleich des gelernten Modells gegen Equal Power wurde
> qualitativ gehört; es zeigte sich kein klarer Gesamtvorteil und weiterhin
> Vocal-Overlap beziehungsweise unnatürlich leise eingeblendete Vocals. Ein
> neuer externer Modelltestsatz steht weiterhin aus.

> **Vocal-Control-Erweiterung vom 2026-08-05:** Der erste gelernte
> Zwei-Control-Hörvergleich zeigte nur geringe Unterschiede; auffällig
> blieben überlappende und unnatürlich leise eingeblendete Vocals. Als
> additive Version sind deshalb eine eigenständige monotone Vocal-Übergabe,
> getrenntes Source-/Target-Ducking, ein stem-fähiger differenzierbarer
> Renderer und Objective v5 implementiert. Der neue Audibility-Term bestraft
> unnötig leise aktive Vocals. Diese kleine MLP-v2-Sonde ist noch nicht das
> geplante TCN-/BiLSTM-Hauptmodell. Nach dem direkten Objective-v5-Hör-Gate
> wurde sie mit einem separaten versionierten Runner trainiert.

> **Vocal-Hör-Gate vom 2026-08-05:** Sechs Kandidaten wurden anhand der
> tatsächlichen Vocal-Aktivität in beiden vier Takte langen
> Übergangsfenstern ausgewählt und als geblendeter Objective-v4/v5-Vergleich
> gerendert. Beide Varianten verwenden denselben stem-fähigen Renderer und
> gemeinsamen Peak-Gain. Nach vollständiger geblendeter Bewertung gewinnt
> Objective v5 zwei Paare, Objective v4 eines, drei sind Gleichstände. Nur
> die Vocal-Klarheit verbessert sich; drei Paare werden durch gemeinsame
> Time-Stretch-Artefakte begrenzt. Das Gate ist positiv, aber wegen eines
> Raters und sechs Entwicklungsbeispielen kein populationsweiter Nachweis.

> **Vocal-ML-Erstlauf vom 2026-08-05:** Ein eigener versionierter
> `self_supervised_vocal_train_validation_v2`-Runner trainiert Modellformat 2
> jetzt end-to-end über den stem-fähigen Renderer und Objective v5. Er bindet
> alle tatsächlich verwendeten Vocal-Cachemanifeste per SHA-256, hält den
> Testsplit unangetastet und speichert atomare Best-/Latest-Checkpoints sowie
> exaktes Resume. Im realen 45/9-Train-/Validation-Lauf lag die beste
> Validation in Epoche 16; der Gesamt-Proxy-Loss sank um 3,17 %, Vocal-
> Overlap um 26,70 % und Vocal-Audibility um 25,27 %. Da zugleich der alte
> Objective-v4-Anteil um 5,05 % anstieg, entscheidet als nächstes ein
> geblendeter Hörvergleich des gelernten Best-Checkpoints gegen die
> ungelernte Vocal-Baseline.

> **Dataset- und Trainings-Erweiterung vom 2026-08-05:** Der rekursive
> Musikimport umfasst 119 FLAC-Pfade. `STRUGGLING`, ein exaktes
> Audio-Duplikat und sechs Tracks unter 145 BPM wurden vor Ranking und
> Kandidatengenerierung ausgeschlossen; kein Track lag über 165 BPM. Aus 111
> eindeutigen zulässigen Quellen entstand ein fehlerfreier Top-1-Paarbatch.
> Bis zu zehn Vier-Takt-Cues pro Paar ergeben nach strikter Audio-SHA-
> Trennung **370 Train / 50 Validation / 60 Test** über 43/5/7 verwendete
> Trackhashes. Der zweite Vocal-v2-Lauf verbessert den Validation-Proxy-Loss
> bis Epoche 22 um 6,14 %, den alten v4-Anteil um 4,83 %, Energieform um
> 8,79 %, Vocal-Overlap um 44,39 % und Audibility um 10,04 %. Die
> Mid-Phrase-Gain-Änderung steigt jedoch um 204,28 %; deshalb bleibt der
> geblendete Modellhörvergleich das nächste Gate.

## 1. Ausgangslage und Motivation

Ziel der Masterarbeit ist ein System zur KI-gestützten Erstellung musikalischer Übergänge für **Tanz-Mashups**. Bei Tanzperformances werden häufig ausgewählte Abschnitte verschiedener Songs kombiniert (Intros/Outros, Build-ups/Drops, Breaks, Refrains, choreografisch relevante Abschnitte).

Die Schwierigkeit liegt nicht im Aneinanderhängen, sondern darin, einen Übergang zu erzeugen, der rhythmisch, harmonisch, klanglich und dramaturgisch funktioniert. Für Tanz sind stabiler Beat, klare Taktgrenzen und ein vorhersehbarer Energieverlauf besonders wichtig. Manuelles Mashup-Erstellen ist zeitaufwendig und setzt Erfahrung voraus.

## 2. Zentrale Forschungsfrage

**Wie können Self-Supervised Learning und gelernte musikalische Repräsentationen genutzt werden, um kurze, taktgenaue und nutzergesteuerte Übergänge zwischen ausgewählten Songabschnitten automatisch zu bewerten und zu erzeugen?**

Im Mittelpunkt: ob sich übergangsrelevantes Wissen **ohne explizite Annotationen** guter/schlechter Übergänge aus unannotierter Musik lernen lässt. Untersucht wird nicht nur das technische Überblenden, sondern vor allem: welche Übergangspunkte zusammenpassen, wie sich diese Passung messen lässt, welche Transition-Variante für ein Abschnittspaar geeignet ist, und wie Nutzer-Constraints einbezogen werden.

## 3. Geplanter wissenschaftlicher Beitrag

Schwerpunkt: ein **selbstüberwachtes Control-Modell für Mixing-Kurven**. Es
erhält beat-synchrone Merkmale zweier ausgerichteter Songfenster und sagt
zeitabhängige, komplementäre Mixing- und Frequenzübergaben voraus. Ein
separater differenzierbarer Renderer erzeugt daraus Audio; eine eingefrorene
Übergangsmetrik dient ohne annotierte Kontrollkurven als Proxy-Loss.
Compatibility- und Render-Metriken bewerten weiterhin Songabschnitte,
Kandidaten und Ergebnisse und bilden Baselines für das gelernte System.

Mögliche Kriterien: rhythmische Kompatibilität, Tempo-/Beat-Kompatibilität, Takt-/Phrasenstruktur, Energieverlauf, Lautheit, spektrale/klangliche Ähnlichkeit, harmonische Verträglichkeit, Strukturtypen (Build-up/Drop/Outro), Vocal-Überlagerungen, benötigte Stärke von Time-Stretching/Pitch-Anpassung.

Kein Zwang, ein großes Foundation Model neu zu trainieren. Realistisch: zunächst **vortrainierte Musik-Embeddings** verwenden und darauf eine transition-spezifische Metrik entwickeln. Eigenes SSL-Fine-Tuning ist optionale Erweiterung (sofern Daten, Compute, Zeit reichen).

## 4. Abgrenzung des Projekts

Nicht Ziel: vollständiges professionelles DJ-System, autonome Komposition ganzer Stücke, perfekte komplette DJ-Sets, umfangreiche Produktions-DAW, aufwendige GUI.

Abschnittsauswahl darf interaktiv erfolgen; die GUI ist **nur Interaktionsschicht**. Kernbeitrag ist nicht „erzeugt automatisch ein komplettes DJ-Set", sondern: **„bewertet und erzeugt kurze musikalische Übergänge zwischen vorgegebenen Songabschnitten unter Nutzer-Constraints."** Diese Abgrenzung hält das Projekt in 6 Monaten realistisch.

## 5. Geplanter Systemablauf (sechs Komponenten)

1. **Audioimport & Abschnittsauswahl** — Nutzer lädt mehrere Songs, wählt Abschnitte (z. B. Song A: letzter Build-up + Drop; Song B: Intro + erster Refrain; Song C: Break + Outro). Reihenfolge kann harte Vorgabe sein.
2. **Musikanalyse** — pro Song: Tempo, Beats, Downbeats, Takte, Phrasen-/Segmentgrenzen, optional Strukturtypen, optional Vocal-Aktivität/Stems. Beat-/Bar-Grid ist Grundvoraussetzung (kleine Timingfehler → hörbar schlechte Übergänge).
3. **Kandidatengenerierung** — aus Bar-/Segmentgrenzen mögliche Übergangspunkte (z. B. letzte 4 Bar-Grenzen von A × erste 4 von B; Längen 1/2/4 Takte). Harte Filter schließen ungeeignete Kandidaten aus (instabiles Grid, zu große Tempoabweichung, ungünstige Phrasengrenzen, zu starker Vocal-Overlap).
4. **Übergangsmetrik** — verbleibende Kandidaten bewerten & ranken. Score ≈ Rhythmuskompatibilität + harmonische Verträglichkeit + Energie-/Klangkontinuität + Embedding-Kompatibilität − Vocal-Overlap-Penalty − Time-Stretching-Penalty. Erst klassische feature-basierte Baseline, dann vortrainierte Embeddings, ggf. eigenes Modell.
5. **Rendering** — mindestens: harter Schnitt auf Bar-Grenze, linearer Crossfade, Equal-Power-Crossfade, einfacher tempoangepasster Übergang. Erweiterungen: EQ/Filter, Pitch-Shifting, stem-aware Übergänge, Vocal-Reduktion, getrennte Behandlung von Drums/Bass/Vocals/Begleitung.
6. **Vorschau & Export** — GUI: Songs laden, Beats/Takte anzeigen, Abschnitte wählen, Constraints setzen, mehrere Varianten anhören, finalen Track exportieren.

## 6. Nutzer-Constraints

Verbindung automatischer Bewertung mit expliziten Vorgaben: Reihenfolge der Abschnitte, Übergangslänge (1/2/4 Takte), Zieltempo, erlaubter Time-Stretch-Umfang, Beat-/Bar-Alignment, Übergangstyp, gewünschte Strukturkombination, Vermeidung starker Vocal-Überlagerungen, gewünschter Energieverlauf.

**Harte Constraints** dürfen nicht verletzt werden (z. B. Abschnittsreihenfolge, Übergangslänge). **Weiche Constraints** beeinflussen den Score (z. B. harmonische Nähe, geringe Tempoänderung).

## 7. Related Work & Positionierung

- **Auto-DJ / Übergangsauswahl**: Bittner et al. (Playlist-Reihenfolge, Übergangspunkte über beat-synchrone Merkmale); Mosaikbox (regelbasiertes Auto-DJ, Beat-Grid, Segmentierung, Stem-Modifikation); DJTransGAN (Fader-/EQ-Kurven aus realen Mixen); Robinson & Brown (Crossfade-Optimierung im Zeit-Frequenz-Bereich).
- **Self-Supervised Music Representation Learning**: CLMR, BYOL-A, MERT, MusicFM, verwandte Audio-SSL-Verfahren. Erfassen musikalische Eigenschaften, sind aber nicht auf Übergangsqualität optimiert.
- **Mashup-/Stem-Kompatibilität** (methodisch am nächsten): AutoMashUpper, Huang et al. (Stem-Kompatibilität), COCOLA, Stem-JEPA.
- **Beat-/Downbeat-/Strukturanalyse**: Beat-Tracking, Downbeat-/Bar-Erkennung, Struktursegmentierung, Cue-Point-Erkennung — notwendige Infrastruktur, nicht primärer Beitrag.

Die ursprüngliche Related Work (nur Auto-DJ) ließ zentrale Literatur zu SSL, Embeddings, Mashability, Struktursegmentierung und Cue-Point-Erkennung aus.

## 8. Datenstrategie

Zunächst kleines **Debug-/Entwicklungsset (~10–20 Tracks)** mit verschiedenen Fällen: elektronische Musik mit klarem Beat; Pop/Dance mit Vocals; Songs mit Intros/Outros ohne durchgehende Drums; Breaks/Tempowechsel; rhythmisch/harmonisch schwierige Kombinationen.

Für die Evaluation später ein größeres, **rechtlich handhabbares** Set (frei lizenziert / für Forschung nutzbar). Quellen: frei lizenzierte Datensätze, eigene/institutionell nutzbare Musik, künstlich erzeugte Übergangsvarianten, aus Songs abgeleitete positive/negative Segmentpaare, ggf. Stems / Source-Separation.

## 9. Mögliche Self-Supervised-Lernsignale

Ohne große Menge gelabelter Übergänge braucht es Pseudo-Labels / Pretext Tasks: benachbarte Segmente desselben Songs als positive Paare; weit entfernte / rhythmisch verschobene als negative; gleiche Segmente mit künstlichen Tempo-/Beat-/Tonartfehlern; Stems desselben Songs als kompatibel vs. zufällig kombinierte Stems als weniger kompatibel; Original-Übergang vs. bewusst verschlechterte Varianten; kontrastives Lernen auf beat-/bar-synchronen Segmenten.

**Kritische methodische Frage**: Bildet „benachbart im selben Song" wirklich dieselbe Kompatibilität ab wie „geeignet für einen DJ-Übergang zwischen zwei Songs"? Muss geprüft und evaluiert werden.

## 10. Baselines

- **Rendering-Baselines**: harter Schnitt, linearer Crossfade, Equal-Power-Crossfade, tempoangepasster Crossfade.
- **Auswahl-/Scoring-Baselines**: zufälliger bar-synchroner Kandidat, minimale BPM-Differenz, Chroma-Ähnlichkeit, Energie-/Lautheitskontinuität, kombinierte handgefertigte Feature-Metrik, Distanz in vortrainiertem Embedding-Raum.

Zentrale Frage: Produziert die entwickelte Metrik bessere Rankings und hörbar bessere Übergänge als diese einfachen Verfahren?

## 11. Evaluation

- **Technisch/objektiv**: Stabilität von Beat-/Bar-Tracking, Einhaltung der Constraints, BPM-/Taktkonsistenz, benötigte Tempoanpassung, Vocal-Overlap, Time-Stretch-Artefakte, Robustheit über Übergangslängen.
- **Übergangsmetrik**: Ranking guter/schlechter Kandidaten; Vergleich Feature-Metrik vs. Embeddings vs. eigenes Modell; Ablation einzelner Score-Komponenten; Generalisierung auf unbekannte Songs; Korrelation mit menschlichen Bewertungen.
- **Perzeptuell**: Hörer bewerten Smoothness, rhythmische Stabilität, harmonische/klangliche Stimmigkeit, Natürlichkeit, Energieverlauf, Vocal-Clash, Tanz-Eignung, Gesamtpräferenz. Sinnvoll: **paarweise Vergleiche / Rankings** (absolute Werte schlecht vergleichbar).

## 12. Erwartetes Endergebnis

Lauffähiger Prototyp, der mehrere Songs importiert; Tempo/Beats/Takte/Grenzen analysiert; ausgewählte Abschnitte verarbeitet; Übergangspunkte erzeugt; Übergänge mit KI-basierter/kombinierter Metrik bewertet; Constraints berücksichtigt; mehrere Strategien rendert; Vorschau/Vergleich ermöglicht; finalen Track exportiert.

Zusätzlich: systematische Related-Work-Analyse, dokumentierte Baselines, reproduzierbare Evaluationspipeline, kleiner Evaluationskorpus, Ergebnisse einer Hörstudie, kritische Diskussion der Grenzen.

## 13. Zeitplanung (6 Monate)

- **Monat 1 – Grundlagen & Baselines**: Scope/Erfolgskriterien; Literatur strukturieren; Entwicklungsdatensatz; Beat-/Bar-Analyse; erste einfache Übergänge.
- **Monat 2 – Kandidaten & klassische Metrik**: Kandidaten generieren; feature-basierte Metrik; Baseline-Ranking; Fehlerklassen systematisieren.
- **Monat 3 – Embeddings & SSL**: vortrainierte Modelle vergleichen; transition-spezifische Lernsignale; ggf. Fine-Tuning; erste Ablationen.
- **Monat 4 – Constraints & Integration**: harte/weiche Constraints; Rendering verbessern; GUI-Prototyp; Pipeline stabilisieren.
- **Monat 5 – Evaluation**: finaler Evaluationsdatensatz; Baseline-Vergleiche; Hörstudie vorbereiten/durchführen; statistische Auswertung.
- **Monat 6 – Abschluss**: Nachtests/Ablationen; Ergebnisse konsolidieren; Ausarbeitung; Software/Daten dokumentieren; Präsentation/Abgabe.

## 14. Ziel der ersten zwei bis drei Wochen

Noch kein vollständiges ML-System, sondern: technische Basis funktioniert. Am Ende sollten vorliegen: klare Problem-/Scope-Definition; reproduzierbares Repository; kleines Entwicklungsset; funktionierende Beat-/Bar-Analyse; mehrere gerenderte Übergänge; erste Baseline-Verfahren; einfache Feature-Metrik; erste Tests mit vortrainierten Embeddings; Liste typischer Fehlerfälle; Entscheidung über den endgültigen ML-Fokus.

**Wichtigstes frühes Erfolgskriterium: Nach spätestens drei Wochen sollen mehrere automatisch erzeugte Übergänge hörbar sein und systematisch verglichen werden können.**

## 15. Zentrale Risiken & Priorisierung

Risiken: unzuverlässige Downbeat-/Bar-Erkennung; fehlende/ungeeignete Trainingsdaten; allgemeine Audio-Embeddings bilden Übergangsqualität nicht ab; subjektive Qualität schwer objektiv messbar; Source-Separation-Artefakte; **GUI-/Audio-Engineering verdrängt den Forschungsbeitrag**; eigenes SSL-Modell zu ambitioniert für den Zeitraum.

Empfohlene Priorisierung:

1. **Pflichtziel**: robuste Pipeline, Baselines und Übergangsmetrik mit vortrainierten Repräsentationen.
2. **Sinnvolle Erweiterung**: stem-/vocal-aware Constraints.
3. **Ambitionierte Erweiterung**: eigenes transition-spezifisches SSL-Fine-Tuning.

So bleibt die Arbeit auch dann wissenschaftlich vollständig, wenn das eigene SSL-Training nicht den erhofften Mehrwert bringt.
