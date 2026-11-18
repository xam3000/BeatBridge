# Einschätzung: Novelty, Gehalt und nächste Schritte

Stand: 18. November 2026, Commit `56b982a`. Grundlage sind [`CODE_REVIEW.md`](./CODE_REVIEW.md), die dort beschriebenen Messungen, die Kapitel 1 und 2 der Thesis unter `overleaf/chapters/` und drei eigene Literaturrecherchen. Diese Übersicht ersetzt die Reihenfolge in Abschnitt 7 des Reviews.

## 1. Kurzantwort

**Novelty heute: gering.** Die beanspruchte Lücke ist ein Controller, der ohne Referenzkurven über einen differenzierbaren Renderer und eine feste Proxy-Verlustfunktion lernt. Sie ist formal korrekt abgegrenzt, aber schmal. Die Messungen untergraben sie zudem: Im Full-Band-Pfad erreicht eine einzige feste Kurve ohne Netz 99,9 % dessen, was pro Beispiel erreichbar ist. Das gelernte, eingabeabhängige Verhalten trägt also kaum etwas bei.

**Gehalt heute: hoch in der Technik, gering in der Erkenntnis.** Die Pipeline läuft, ist reproduzierbar und vorbildlich dokumentiert. Das wissenschaftliche Ergebnis ist ein Nullresultat: Die Modelle senken den Proxy-Verlust um 3 bis 6 %, und Hörende hören keinen Unterschied zu Equal Power (19 von 19 Gleichständen). Dieses Nullresultat ist noch nicht als solches aufgearbeitet.

**Die Forschungsfrage der Aufgabenstellung ist unbeantwortet.** Es gibt keine selbstüberwachte Repräsentation und keine gegen Hörurteile geprüfte Metrik.

**Das Material reicht für eine interessante Arbeit.** Dazu müsste man das Nullresultat zur Diagnose machen, die selbstüberwachte Metrik für die Wahl der Übergangspunkte nachliefern und beides in einem einzigen sauber geplanten Hörversuch prüfen. Das ist in vier Wochen machbar (Abschnitt 4).

## 2. Was ist drin: Novelty und Gehalt je Baustein

| Baustein | Nächste Vorarbeit | Novelty | Gehalt heute | Belastbarkeit |
|---|---|---|---|---|
| Analyse, Kandidaten, Paar-Render | Standard-MIR; AutoMashUpper (2014), Mosaikbox (2024) | gering | hoch: läuft, 291 Tests grün, volle Provenienz | technisch hoch; Beat-Erkennung nie gegen eine bekannte Wahrheit geprüft |
| Regel-Ranking `feature_baseline_v3` | AutoMashUpper | gering | mittel | Gewichte von Hand, nie geeicht |
| Controller über differenzierbaren Renderer und Proxy-Verlust | DJTransGAN (2022, lernt aus echten DJ-Mixen), Steinmetz (2021), Hein (2025) | mittel als Formulierung | gering: 3 bis 6 % Proxy-Gewinn, unter 1,5 dB Pegelunterschied, im Hörtest nicht unterscheidbar | Validation auf 2 bis 5 Tracks, je ein Seed |
| Vocal-Renderer mit Stems | Mosaikbox (regelbasiert mit Stems) | gering bis mittel | der einzige Term, den ein Modell sichtbar gelernt hat (`vocal_audibility`) | nicht isoliert gehört |
| Variable Längen 2, 4, 6, 8 Takte | – | gering | unklar: keine Epoche 0, deckt 1 bis 4 Takte nicht ab | – |
| Gelernter Cue-Ranker | Huang (2021), Zehren (2022), Argüello (2024) | gering | null: nur synthetische Daten, Labels zirkulär aus dem Proxy-Verlust | – |
| Hörversuche P2 und P5 | – | – | P5 ist ein informatives Nullresultat; P2 zeigt 9 von 9 Präferenzen für direkt optimierte Kurven | gering: ein Rater, wenige Trackpaare |
| Provenienz und Verträge | – | keine wissenschaftliche Novelty | sehr gut; im Kapitel zur Reproduzierbarkeit erwähnenswert | – |

Die Lücke, die die Thesis beansprucht (`overleaf/chapters/02_relatedWork.tex:64`): Keine Quelle verbinde ein festes, vom Nutzer gewähltes Cue-Paar mit einem zeitabhängigen, interpretierbaren Controller, der über einen getrennten differenzierbaren Renderer und eine feste Proxy-Verlustfunktion trainiert wird, ohne Referenzkurven und ohne Qualitätslabels.

Diese Aussage stimmt. Eine Kommission würde aber fragen: „Warum dann nicht einfach die eine optimierte Kurve nehmen?" Darauf gibt es heute keine Antwort. Die Proxy-Verlustfunktion ist im Kern ein regelbasierter Mixer, als Loss formuliert. Ihr Optimum hängt kaum von der Musik ab.

## 3. Wenn die Arbeit heute präsentiert würde

**Was sich vertreten lässt:**

1. Eine reproduzierbare Pipeline von der Analyse bis zum gerenderten Übergang, mit einem differenzierbaren Controller-Framework.
2. Label-freie Optimierung gegen eine Proxy-Verlustfunktion funktioniert technisch: Der Verlust fällt innerhalb jedes Laufs.
3. Sie bringt keinen hörbaren Vorteil: 19 von 19 Gleichständen gegen Equal Power, ehrlich berichtet.
4. Die Gründe lassen sich messen. Die Kurvenparametrisierung erlaubt höchstens ±0,29 Abweichung von der Rampe. Das Energieziel ist eine feste V-Form. Das Optimum ist weitgehend eingabeunabhängig. Die Modelle erreichen 25 bis 44 % dessen, was direkte Optimierung pro Beispiel schafft.

Punkt 4 steht heute nicht in der Thesis. Ohne ihn lautet die Geschichte „wir haben X gebaut, es hilft nicht hörbar", ohne „warum".

**Wo die Kommission angreifen würde:**

| Angriffspunkt | Gewicht |
|---|---|
| Der Titel verspricht Self-Supervised Learning. Gelernt oder genutzt wird keine selbstüberwachte Repräsentation; „self-supervised" heißt im Code nur „ohne Labels gegen eine handgebaute Funktion optimiert". | hoch |
| Die „Metrik" wurde nie gegen ein Hörurteil geprüft, weder Regel-Ranking noch Proxy-Verlust. | hoch |
| Die Evidenz ist dünn: ein Rater, fünf Trackpaare im Hörtest, Validation auf 2 bis 5 Tracks, je ein Seed. | hoch |
| Kernfunktionen fehlen: Mashup-Export, Abschnittsauswahl, 1- und 3-Takt-Übergänge. | mittel; hängt von der Entscheidung zum Umfang ab |
| Der Autor hat GUI, Korrekturaufwand und Nutzerstudie aus der Arbeit genommen, ohne dokumentierte Entscheidung der Betreuung. | mittel |
| Der Startpunkt des TCN ist als Equal Power etikettiert, liegt aber 9,9 dB darunter. | mittel; leicht zu beheben |

Gesamturteil: Heute ist das eine gut gebaute Ingenieursarbeit mit einem unaufgearbeiteten Nullresultat, die ihre eigene Forschungsfrage nicht beantwortet.

## 4. Was konkret passieren müsste

**Zentrale Frage, die die Arbeit interessant macht:**

> Entscheidet bei einem kurzen EDM-Übergang eher das *Wo* (die Wahl der Übergangspunkte) oder das *Wie* (die Form der Mixing-Kurven)? Und wählt eine selbstüberwacht gelernte Metrik das *Wo* besser als Regeln?

Diese Frage verbindet den Titel (SSL plus Metrik) mit der vorhandenen Controller-Arbeit (das *Wie*) und erklärt das Nullresultat. Jeder Ausgang ist berichtenswert.

| Nr. | Schritt | Art | Aufwand | Was dabei herauskommt |
|---|---|---|---|---|
| 1 | Geschichte und Umfang festlegen: obige Leitfrage; was aus der Aufgabenstellung Pflicht bleibt (Mashup-Export, 1 bis 4 Takte); ob ein kleiner Hörversuch mit 3 bis 5 Personen unter die Lizenz fällt. | Entscheidung der Betreuung | 0,5 Tage | Klare Abgabedefinition statt einseitiger Streichungen |
| 2 | Nullresultat zur Diagnose machen: Review-Skripte auf die September-Läufe R1 bis R4 anwenden. Für jeden Pfad vier Bedingungen berichten: Equal Power, eine feste Kurve, Modell, direkte Optimierung. Dazu der Vertauschungstest. | Experiment | 1 bis 2 Tage | Ein Kapitel „Warum der Controller wenig lernt". Ein allgemeiner Befund über Proxy-Verluste: Die Vorlage dominiert, und zwischen Modell und Optimum klafft eine Lücke. |
| 3 | Selbstüberwachte Übergangsmetrik bauen. Eingefrorene MERT- oder MusicFM-Embeddings pro Takt, darauf ein kleiner Kopf, kontrastiv trainiert. Positives Paar: der Takt vor und der Takt nach einem Downbeat desselben Songs. Negative Paare: beatgenau ausgerichtete Takte anderer Songs mit ähnlichem Tempo und ähnlicher Tonart. Diese harten Negative sind nötig, sonst lernt das Modell nur „gleiche Produktion". | Codeänderung plus Experiment | 6 bis 8 Tage | Die SSL-Komponente des Titels. Erste Prüfung: Findet die Metrik die echte Fortsetzung unter harten Negativen wieder, im Vergleich zu `feature_baseline_v3`? |
| 4 | Ein Hörversuch, der beide Fragen zugleich beantwortet. Design: Cue-Wahl (SSL-Top-1, Regel-Top-1, Zufall) mal Kurve (Equal Power, direkt optimiert). 10 bis 12 Trackpaare aus Tracks, die nie in Training, Validation oder einem Hörtest waren. Bewertung je Stimulus auf einer Skala, harter Schnitt als Anker. Hypothesen vorab schriftlich festhalten. | Experiment | 3 bis 4 Tage | Der Effekt der Cue-Wahl gegen den Effekt der Kurve. Dazu die Korrelation jeder Metrik (Proxy-Verlust, Regel-Ranking, gerenderte Metrik, SSL-Metrik) mit den Urteilen. Das beantwortet die „Aussagekraft der Metrik" aus der Aufgabenstellung direkt. |
| 5 | Pflichtteile und Etiketten: Mashup-Export als Verkettung der Sequenz; 1 und 3 Takte im Baseline-Renderer; „self-supervised" in der Thesis auf die Metrik beziehen, den Controller „label-freie Proxy-Optimierung" nennen; TCN-Startpunkt korrigieren oder umbenennen. | Codeänderung | 2 bis 3 Tage | Prototyp erfüllt die Aufgabenstellung formal; keine angreifbaren Etiketten |
| 6 | Optional, mit hohem Risiko und der höchsten Novelty: die SSL-Metrik als differenzierbaren Kritiker statt der V-Vorlage ins Controller-Training einbauen. Gegenstück zu DJTransGAN, aber ohne echte DJ-Mixe. | Codeänderung plus Experiment | 4 bis 6 Tage | Nur angehen, wenn 3 und 4 vor Woche 3 stehen. Risiken: Der Controller nutzt Schwächen des Kritikers aus; MERT auf gerendertem Audio ist rechenintensiv. |

**Zu den möglichen Ausgängen von Schritt 4:**

- Ist der Effekt der Cue-Wahl deutlich größer als der der Kurve, ist das eine klare, verwertbare Aussage für automatische DJ-Systeme.
- Schlägt die SSL-Metrik die Regeln, passt der Kernbeitrag zum Titel.
- Scheitert sie, bleibt ein sauber gemessenes Ergebnis mit Diagnose.
- Ein Hinweis, dass die Kurve bei direkter Optimierung hörbar werden kann, liegt schon vor: In P2 bevorzugte der einzige Rater die direkt optimierte Kurve 9 von 9 Mal, und die Sauberkeit stieg in jedem Paar einheitlich von 4 auf 5 (`docs/STATUS.md:1290-1297`). Diese Gleichförmigkeit sollte mit mehr Hörenden geprüft werden. Deshalb steht die direkte Optimierung im Design, nicht das trainierte Modell.

**Zeitplan, rund 17 bis 20 Arbeitstage:**

| Woche | Inhalt |
|---|---|
| 1 | Schritte 1 und 2, Beginn von Schritt 3 |
| 2 | Schritt 3 |
| 3 | Schritt 4 (Stimuli bauen, Versuch durchführen) und Schritt 5 |
| 4 | Auswertung und Schreiben; Schritt 6 nur bei Vorsprung |

**Was eingestellt werden sollte:** weitere Controller-Architekturen und Sweeps, die Längen 6 und 8, der Lehrer des Cue-Rankers (zirkulär) und weitere Provenienz-Werkzeuge. Dort ist kein Erkenntnisgewinn mehr zu erwarten, der den Aufwand rechtfertigt.

## 5. Novelty der vorgeschlagenen Richtung

Die Idee in Schritt 3 ist nicht völlig neu:

- Fedorishin et al. (2024) trainieren mit „Split-and-Contrast" eine Repräsentation, in der benachbarte Abschnitte desselben Audiosignals ähnlich sind. Damit finden und erzeugen sie Übergänge, allerdings für Film und Video, nicht für Musik-Mixe. Die Arbeit fehlt bisher im Related Work der Thesis und muss dort hinein.
- Contrastive Predictive Coding (van den Oord et al. 2018) nutzt dasselbe Prinzip allgemein: Vorhersage der Zukunft im Embedding-Raum. Diese Angabe stammt aus meinem Wissen, ich habe sie nicht nachgeschlagen.
- Die bereits zitierten Arbeiten zu Kompatibilität (Huang 2021, COCOLA, Stem-JEPA) lernen das gleichzeitige Zusammenpassen von Stems eines Songs, nicht die zeitliche Fortsetzung über einen Schnitt zwischen zwei Songs. DJ AI (2025) nutzt MERT, aber für die Auswahl kompatibler Tracks über Tonart-Regeln und für generierte Übergänge, nicht als gelernte Cue-Metrik.

Neu wäre die Kombination: richtungsabhängig, beat-synchron, für Cue-Paare zwischen zwei Songs, mit harten Negativen gegen die Abkürzung „gleiche Produktion" und gegen Hörurteile validiert. Für eine Masterarbeit ist das eine angemessene, vertretbare Novelty. Für eine Konferenz würde sie erst mit Schritt 6 oder einer größeren Hörstudie reichen.

## Quellen

Bereits in `overleaf/chapters/02_relatedWork.tex` zitiert: `chen2022djtransgan`, `kinay2025djai`, `huang2021stemcompat`, `ciranni2025cocola`, `riou2024stemjepa`, `davies2014automashupper`, `sowula2024mosaikbox`, `zehren2022cuepoints`, `arguello2024cuedetr`, `hein2025supervised`, `steinmetz2021mixingconsole`.

Neu recherchiert (18.11.2026):

- [Fedorishin et al., Audio Match Cutting, arXiv 2408.10998](https://arxiv.org/abs/2408.10998)
- [Chen et al., Automatic DJ Transitions with Differentiable Audio Effects and GANs, arXiv 2110.06525](https://arxiv.org/abs/2110.06525)
- [Argüello et al., Cue Point Estimation using Object Detection, arXiv 2407.06823](https://arxiv.org/abs/2407.06823)
- [DJ AI, Sabancı University 2025](https://research.sabanciuniv.edu/52373/1/AI_DJ_AM2025.pdf)
- [Hein, A Supervised Learning Framework for Generating DJ Transitions, Princeton 2025](https://theses-dissertations.princeton.edu/entities/publication/86237923-6f8a-4172-a6e7-d639e97d38d1)

Eine Suche nach einer Arbeit, die eine selbstüberwachte Fortsetzungsmetrik für DJ-Cue-Paare oder einen gelernten Kritiker für differenzierbares DJ-Mixing seit 2025 beschreibt, fand nichts. Das ist ein Hinweis auf eine Lücke, kein Beweis. Vor dem Festschreiben sollte jemand die Proceedings von ISMIR und ICASSP 2025/2026 gezielt durchsehen.
