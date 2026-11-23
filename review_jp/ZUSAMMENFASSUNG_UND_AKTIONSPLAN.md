# BeatBridge: Kritikpunkte und Aktionsplan

> **Status: Der Plan gilt weiter (Stand 18.11.2026, Commit `56b982a`).** Die Kritikpunkte in Abschnitt 2 und die Tabellen in Abschnitt 3 beschreiben den Stand vor der Umsetzung. Was davon erledigt ist und was sich an der Reihenfolge ändert, steht in der [Rückmeldung vom 22.11.](./RUECKMELDUNG_20261122.md). Den Umsetzungsstand führt der Autor in [`docs/REVIEW_JP_UMSETZUNG.md`](../docs/REVIEW_JP_UMSETZUNG.md). Einstieg in alle Review-Dokumente: [README](./README.md).

Stand: 18. November 2026, Commit `56b982a`.

Dieses Dokument fasst [`CODE_REVIEW.md`](./CODE_REVIEW.md), [`EINSCHAETZUNG.md`](./EINSCHAETZUNG.md) und die anschließende Besprechung zusammen. Wo es von den beiden früheren Dokumenten abweicht, gilt dieses. Belege mit Fundstellen und Messwerten stehen im Code-Review; hier stehen nur die tragenden Zahlen.

---

## 1. Das Wichtigste in fünf Sätzen

1. Die Arbeit hat eine solide, sehr gut dokumentierte technische Basis. Ihr wissenschaftlicher Kern, ein gelernter Controller für Überblendkurven, liefert aber keinen hörbaren Effekt, und warum, ist nicht aufgearbeitet.
2. Das Hörbare entscheidet vermutlich die vorgelagerte Auswahl der Übergangspunkte. Die trifft heute eine handgewichtete, nie geprüfte Regelformel.
3. Die Aufgabenstellung verlangt eine selbstüberwacht gelernte Repräsentation und eine geprüfte Übergangsmetrik. Beides fehlt.
4. Ergebnisse aus verschiedenen Pfaden (Datensätze, Renderer, Verlustfunktionen, Abtastraten, Optimierer) werden nebeneinandergestellt, obwohl sie sich in mehreren Faktoren zugleich unterscheiden.
5. Der Plan: das Lernen in die Auswahlstufe verlegen (selbstüberwachte Fortsetzungsmetrik auf MERT), den Controller als Diagnose behandeln und beides in einem einzigen vorab festgelegten Evaluationsprotokoll prüfen.

---

## 2. Kritikpunkte

### 2.1 Blocker: gefährden die Abnahme oder die Erfüllung der Aufgabenstellung

| Nr. | Kritikpunkt | Beleg | Aufgelöst durch |
|---|---|---|---|
| B1 | **Self-Supervised Learning fehlt.** Der Titel verspricht es. Im Code wird keine selbstüberwachte Repräsentation gelernt oder genutzt. „Self-supervised" bezeichnet dort nur das Minimieren einer handgebauten Verlustfunktion ohne Labels. | `src/ml/training.py:1`; Suche nach MERT, MusicFM, CLAP und wav2vec ohne Treffer | Phase 2 |
| B2 | **Die Übergangsmetrik ist nie validiert.** Ausgewählt wird mit einer Regelformel mit Gewichten von Hand (`src/ranking/feature_baseline.py:21-26`). Weder sie noch der Proxy-Verlust wurde je gegen Hörurteile geprüft. Die geforderte „Aussagekraft der Metrik" ist unbeantwortet. | Code-Review 3.3 und 4.6 | Phasen 2 und 3 |
| B3 | **Der gelernte Teil wirkt nicht hörbar, und es ist nicht erklärt, warum.** Die Modelle senken den Proxy-Verlust um 3 bis 6 % und ändern den Pegelverlauf im Median um unter 1,5 dB. Im Hörtest lagen sie 19 von 19 Mal gleichauf mit Equal Power. Im Full-Band-Pfad erreicht eine einzige feste Kurve ohne Netz 99,9 % des möglichen Gewinns. | Code-Review 4.1 bis 4.3 | Phase 1.4 |
| B4 | **Der Umfang wurde einseitig gekürzt, Kernfunktionen fehlen.** Der Autor hat am 11.11. GUI, Korrekturaufwand und Nutzerstudie aus der Thesis genommen, ohne dokumentierte Entscheidung der Betreuung. Es gibt keinen Mashup-Export, keine 1- und 3-Takt-Übergänge im ML-Pfad und keine Auswahl von Abschnitten. | `docs/masterarbeit/AUFTRAG_THESIS_UEBERARBEITUNG_20261111.md`; Code-Review 3.10 | Phasen 0 und 4 |

### 2.2 Große Nachfragen: lösbar, müssen aber beantwortet sein

| Nr. | Kritikpunkt | Kern |
|---|---|---|
| N1 | Dünne Evidenzbasis | ein Rater; fünf Trackpaare im Hörtest; Validation auf 2 bzw. 5 Tracks; je ein Seed. Die Beispiele sind stark abhängig: bis zu 60 Beispiele pro Track, einzelne Cues bis zu 19-mal wiederverwendet. |
| N2 | Fehlende Vergleichbarkeit | Die Pfade unterscheiden sich in Datensatz, Feature-Protokoll, Vocal-Backend, Renderer, Verlustfunktion, Optimierer und Startpunkt zugleich (Abschnitt 3). |
| N3 | Konstruktion der Verlustfunktion | Das Energieziel ist eine feste V-Form mit −6 dB. Drei Terme sind praktisch immer null (`boundary`, `clipping`, `monotonicity`). `transient_artifact` ist eine Konstante. Zwei Terme sind linear und finden ihr Optimum immer an der Schranke. Die Kurven dürfen höchstens ±0,29 von der Rampe abweichen. |
| N4 | Eingabemerkmale | 13 der 54 Kanäle sind für alle Beispiele identisch, im größeren Datensatz zusätzlich 5 der 16 globalen. Chroma und Tonart sind kaum belastbar (Tonart-Konfidenz im Mittel 0,08 bis 0,17). Das Netz sieht nur die 4 überlagerten Takte, nicht den Kontext davor und danach. |
| N5 | Zirkularität | Der Lehrer des Cue-Rankers ist die Verlustfunktion, mit der auch der Controller trainiert wird. Regel-Ranking, Render-Metrik und Verlustfunktion kodieren alle drei dieselbe Annahme einer 6-dB-Senke und sind damit keine unabhängigen Prüfungen voneinander. |
| N6 | Exponierte Testdaten | Der Test-Split von D1 wurde im Hörtest P2 während der Entwicklung gehört (laut Ledger). Für eine unabhängige Schlussauswertung ist er verbraucht. |
| N7 | Abweichung zwischen Training und Anwendung | Die GUI skaliert den Ziel-Cue für die ML-Merkmale invers (`src/gui/ml_transition.py:146`). Sie speist Vocal-Modelle immer mit RoFormer-Merkmalen (`:127`); die lokalen Vocal-Läufe sind mit Demucs trainiert. Der Cue-Ranker läuft bei der Anwendung standardmäßig ohne Vocals, beim Training mit. |
| N8 | Reproduzierbarkeit außerhalb des Autorenrechners | aufTAKT läuft nur unter Windows. Ein Fehlschlag wird stillschweigend als 4/4-Raster gecacht. Die Run-Manifeste enthalten Windows-Pfade, die ML-Einbindung der GUI findet deshalb anderswo keine Modelle. |

Kleinere Fehler (zum Beispiel `tempo_fade` identisch mit `fade`, veraltete Cues nach dem Umsortieren) stehen in Abschnitt 6 des Code-Reviews.

---

## 3. Vergleichbarkeit: wo heute Dinge durcheinandergehen

### 3.1 Die vier Controller-Pfade unterscheiden sich in fast allem

| | MLP v1 | Vocal-MLP v2 | TCN/BiLSTM fest | TCN/BiLSTM variabel |
|---|---|---|---|---|
| Datensatz (Sept.-Lauf) | D2 | D2 | D2 | D4 |
| Feature-Protokoll | 1 | 1 | 1 | 2 |
| Vocal-Backend der Merkmale | Demucs | Demucs | Demucs | RoFormer |
| Renderer | Zwei-Band | Vocal (Stems) | Full-Band, 10 Regler | Vocal (Stems) |
| Verlustfunktion | v4 | v5 | v4 | v5, zeitnormiert |
| Längen | 4 Takte | 4 Takte | 4 Takte | 2, 4, 6, 8 Takte |
| Optimierer-Plan | konstante Lernrate, Patience 6 | Plateau-Scheduler, Patience 6 | Warm-up und Plateau, Patience 30 | Warm-up und Plateau, Patience 30 |
| Startpunkt | exakt Equal Power | fast Equal Power (1,3 % Ducking) | 9,9 dB unter Equal Power | keine Epoche 0 protokolliert |

Fundstellen: `src/ml/runner.py:64-125`, `src/ml/vocal_runner.py:59-78`, `src/ml/variable_runner.py:57-120`, `:196-233`, Manifeste unter `output/`, `docs/RESULTS_EVIDENCE_LEDGER.md` (R1 bis R4). Für D2 ist das Vocal-Backend aus dem lokalen Manifest gelesen, für D4 aus dem Ledger.

**Folgen:**
- Rohe Verlustwerte zwischen den Spalten sind nicht vergleichbar. Das sagt der Ledger selbst (R5).
- Ein „Architekturvergleich" MLP gegen TCN ist zugleich ein Vergleich von Renderer, Optimierer und Startpunkt.
- Der Satz „der TCN verbessert sich um 83 %" misst überwiegend das Zurücklernen der normalen Lautstärke.

### 3.2 Training und Auswertung laufen unter verschiedenen Bedingungen

- Trainiert wird bei 11 025 Hz mit Filterkern 127. Der Hörtest P5 rendert alles bei 44,1 kHz mit Kern 511 (`src/evaluation/four_model_listening_study.py:436-443`). Das ist begründet, aber die Kurven wurden unter einer anderen Renderkonfiguration optimiert, als sie gehört werden.
- Die Hörstimuli bekommen eine gemeinsame Spitzenpegel-Verstärkung (`:235-238`), aber keinen Lautheitsabgleich. Lautere Varianten werden in Hörtests systematisch bevorzugt; das ist weder kontrolliert noch berichtet.
- In P5 wird das variable Modell auf Cues aus dem Validation-Set von Format 1 bewertet, also außerhalb seiner eigenen Domäne (Ledger P5).

### 3.3 Drei „Metriken", eine Annahme

| Metrik | Wo die 6-dB-Senke steckt |
|---|---|
| Regel-Ranking `feature_baseline_v3` | `drop_boundary_contrast_db = 6.0` (`src/ranking/feature_baseline.py:30`) |
| Render-Metrik `rendered_transition_baseline_v1` | `desired_energy_contrast_db = 6.0` (`src/ranking/rendered_transition.py:22`) |
| Verlustfunktion v4 und v5 | `valley_depth_db = 6.0` (`src/control/differentiable.py:93`) |

Wenn eine davon die andere „bestätigt", ist das keine unabhängige Evidenz.

### 3.4 Gut, und darauf lässt sich aufbauen

Die Provenienz ist vorbildlich: Jede Zahl lässt sich über Manifeste und Hashes einem Artefakt zuordnen, und der Ledger trennt bereits vergleichbare von nicht vergleichbaren Werten. Es fehlt nicht an Nachvollziehbarkeit, sondern an kontrollierten Vergleichen.

---

## 4. Grundsätze für alles Weitere

Diese zehn Regeln gelten für jedes Experiment ab jetzt. Sie gehören in ein Protokoll im Repo (Schritt 1.1).

| Nr. | Grundsatz | Konkret |
|---|---|---|
| G1 | Ein Vergleich ändert genau einen Faktor. | Alles andere wird festgehalten und in der Ergebnistabelle ausgewiesen. Unterscheiden sich zwei Bedingungen in mehr als einem Faktor, heißt das „explorativ", nicht „Vergleich". |
| G2 | Ein eingefrorenes Evaluationsset. | Recording-Gruppen, die nie in Training, Validation, Hörtest oder Entwicklung vorkamen. Die Liste mit Hashes wird festgeschrieben, bevor ein Experiment läuft. Alte Test-Splits gelten als verbraucht. |
| G3 | Ein Auswertungspfad. | Ein Skript rendert alle Bedingungen mit derselben Konfiguration (Abtastrate, Filterkerne, Länge, Kontext) und gleicht die Lautheit an (LUFS). Es schreibt eine Ergebnistabelle. Keine Studie baut ihren eigenen Renderpfad. |
| G4 | Gepaarte Baselines in jedem Pfad. | Equal Power, eine feste optimierte Kurve und die direkte Optimierung pro Beispiel, unter identischem Renderer und identischer Verlustfunktion. Pfadübergreifend werden nur relative Größen verglichen: Gewinn gegenüber Equal Power und Anteil des direkt erreichbaren Gewinns. |
| G5 | Die Analyseeinheit ist das Trackpaar. | Konfidenzintervalle per Bootstrap über Trackpaare, nicht über Beispiele. Hauptkonfigurationen mit mindestens drei Seeds; keine Aussage aus einem einzelnen Seed. |
| G6 | Qualität misst nur das Hörurteil. | Keine Metrik wird durch eine andere Metrik mit denselben Annahmen „validiert". |
| G7 | Vorab festlegen. | Hypothesen, primäre Kennzahl, Ausschlussregeln und Auswertungsmethode stehen datiert im Repo, bevor ausgewertet wird. Nachträgliche Ausschlüsse nur nach vorab festgelegter Regel. |
| G8 | Training gleich Anwendung. | Der Code prüft per Assertion, dass Vocal-Backend, Normalisierung und Tempo-Skalierung bei der Anwendung dem Run-Vertrag entsprechen. |
| G9 | Eine Vergleichsmatrix. | Jede Zahl in der Thesis hat eine Zeile mit Datensatz-ID, Feature-Protokoll, Vocal-Backend, Renderer samt Konfiguration, Version der Verlustfunktion, Abtastrate, Seed und Checkpoint-Regel. Der vorhandene Ledger wird dazu erweitert. |
| G10 | Weniger Pfade. | Was die Forschungsfrage nicht beantwortet, wird eingefroren und nur noch als Diagnose oder Ausblick berichtet (Abschnitt 6). |

---

## 5. Aktionsplan

Leitfrage, um die herum die Arbeit gebaut wird:

> Entscheidet bei einem kurzen EDM-Übergang eher das *Wo* (die Wahl der Übergangspunkte) oder das *Wie* (die Form der Mixing-Kurven)? Und wählt eine selbstüberwacht gelernte Metrik das *Wo* besser als Regeln und als klassische Merkmale?

Gesamtaufwand rund 18 bis 21 Arbeitstage. Jeder Schritt hat ein Kriterium, wann er fertig ist.

### Phase 0: Entscheidungen der Betreuung (0,5 Tage)

| Nr. | Entscheidung | Empfehlung |
|---|---|---|
| E1 | Leitfrage wie oben | annehmen |
| E2 | Pflichtteile aus der Aufgabenstellung | Mashup-Export und 1 bis 4 Takte bleiben Pflicht. Über die GUI bewusst entscheiden und die Entscheidung dokumentieren. |
| E3 | Hörversuch mit mindestens drei Hörenden: lizenzrechtlich zulässig? | klären; davon hängt Phase 3 ab |
| E4 | Gebrauch von „self-supervised" | nur noch für die Metrik; den Controller als „label-freie Optimierung gegen eine Proxy-Verlustfunktion" bezeichnen |
| E5 | Metrik nur für die Fortsetzung oder auch für die Überlagerung | zuerst nur Fortsetzung; Überlagerung als Ausblick |

**Fertig, wenn:** die Entscheidungen datiert in `docs/` stehen.

### Phase 1: Fundament für Vergleichbarkeit und Diagnose (Woche 1, rund 4 Tage)

**1.1 Evaluationsprotokoll** (1 Tag)
- `docs/EVALUATION_PROTOCOL.md` mit den Grundsätzen G1 bis G9 in konkreter Form.
- Eingefrorenes Evaluationsset: 10 bis 12 Trackpaare aus rund 20 bis 24 nie benutzten Tracks, nach Recording-Gruppen getrennt. Die Hashes werden festgeschrieben.

*Fertig, wenn:* das Protokoll und die Hash-Liste committet sind, bevor ein Experiment aus Phase 2 oder 3 läuft.

**1.2 Vergleichsmatrix** (0,5 Tage)
- Den Ledger um die Spalten aus G9 erweitern.
- Jede bisherige Zahl der Thesis einordnen: „kontrollierter Vergleich", „innerhalb eines Laufs" oder „explorativ".

*Fertig, wenn:* keine Zahl in Kapitel 5 ohne Matrixzeile ist.

**1.3 Einheitlicher Auswertungspfad und Fehler, die Ergebnisse verfälschen** (1,5 Tage)
- Ein Render- und Auswertungsskript für alle Bedingungen: gleiche Konfiguration, Lautheitsabgleich, eine Ergebnistabelle.
- Assertions für Training gleich Anwendung (G8).
- Beheben:
  - inverse Cue-Skalierung in der GUI (`src/gui/ml_transition.py:146`);
  - Vocal-Backend der GUI aus dem Run-Vertrag lesen statt fest RoFormer (`:127`);
  - Fallback-Cache von aufTAKT (`src/analysis/pre_analysis.py:279`, `:560`).
- Je ein fachlicher Test:
  - Zwei-Band-Renderer mit linearer Rampe gleich `EqualPowerFadeCut`;
  - Startpunkt jedes Controllers gleich Equal Power.

*Fertig, wenn:* die Tests grün sind und das Skript eine Equal-Power-Bedingung bitgleich zweimal reproduziert.

**1.4 Diagnose des Controllers** (1 bis 1,5 Tage)
- Die Review-Skripte (`review_jp/scripts/`) auf R1 bis R4 anwenden. Für jeden Pfad die vier Bedingungen aus G4, dazu den Vertauschungstest und den Audio-Unterschied.
- MLP v1 und Vocal-MLP v2 mit drei Seeds neu trainieren. Das dauert jeweils Minuten.
- Den TCN einmal mit echtem Equal-Power-Start neu trainieren, um zu zeigen, wie viel Gewinn übrig bleibt.

*Fertig, wenn:* es eine Tabelle „Equal Power, feste Kurve, Modell, direkt" für alle Pfade mit Streuung über Seeds gibt, dazu einen Kapitelentwurf „Warum der Controller wenig lernt".

### Phase 2: Selbstüberwachte Fortsetzungsmetrik (Woche 2, 6 bis 8 Tage)

**2.1 Repräsentationen pro Takt** (1 Tag)
- **MERT:** eingefroren, Originalaudio (nicht gestreckt) bei 24 kHz mono, alle Schichten, pro Takt über das vorhandene Beat-Raster gemittelt.
- **Klassisch:** die 41 lebenden der 54 Kanäle, Mittel und Streuung über die 8 Halbbeats eines Takts, auf Train-Daten standardisiert. Die Track-Caches enthalten den ganzen Track bereits.
- **Augmentierung:** zwei bis drei Fassungen pro Track vorberechnen, die nur Produktionsmerkmale ändern (EQ, Pegel, leichter Hall). Die Tonhöhe bleibt unverändert, weil die harmonische Fortsetzung gelernt werden soll.

**2.2 Paare und Negativbeispiele** (1 Tag)

Die Geometrie bildet den Übergang nach: B ab T steht dort, wo in A der Takt S+L stünde. Daher:

- **Positive Paare:** die k Takte vor einem Downbeat d und die k Takte ab d+L, aus demselben Song.
- **Negative Paare:**
  - andere Tracks im selben Batch;
  - andere Tracks mit höchstens 5 % Tempounterschied (harte Negative);
  - derselbe Song, ein Abschnitt mit deutlich anderem Charakter und mehr als 16 Takten Abstand. Das bestraft die Abkürzung „gleiche Aufnahme". Wegen möglicher falscher Negative, denn EDM ist repetitiv, wird der Verlust abgesichert (Debiased Contrastive Learning).
- **Split** nach Recording-Gruppen. L zunächst 4 Takte, später als Eingabe für 1 bis 4 Takte.

**2.3 Architektur, als Kapazitätsleiter** (2 bis 3 Tage)

| Stufe | Score | Parameter |
|---|---|---|
| 0 | Kosinus der rohen Embeddings, ohne Training | 0 |
| 1 | bilinear mit niedrigem Rang, wie bei CPC | ca. 0,1 Mio. |
| 2 | zwei Türme („Ende von A", „Anfang von B"), je eine versteckte Schicht, Ausgabe 128, lernbare Gewichtung der MERT-Schichten | ca. 0,5 Mio. |
| 3 | Kreuz-Encoder auf [a, b, a−b, a·b], nur falls Stufe 2 nicht reicht | ca. 0,5 Mio. |

- Verlust: InfoNCE.
- Dieselbe Leiter, dasselbe Budget und dieselben Seeds für MERT und die klassischen Merkmale. Das ist der kontrollierte Repräsentationsvergleich, den die Aufgabenstellung verlangt.
- Checkpoint-Auswahl über Recall@1 auf Validation, nicht über den Verlust.

**2.4 Offline-Auswertung** (1 Tag)
- Wiederfinden der echten Fortsetzung unter harten Negativen (Recall@1, MRR) auf Validation-Tracks.
- **Abkürzungstest:** Hält das Modell Intro und Drop desselben Songs für eine passende Fortsetzung, hat es die Identität der Aufnahme gelernt.
- Übereinstimmung mit `feature_baseline_v3` auf Top-1 und im Rangkorrelationsmaß. Die Fälle, in denen beide widersprechen, anhören (eine Stunde).

**2.5 Entscheidungspunkt.** In den Hörversuch geht nur eine Metrik, die den Abkürzungstest besteht. Besteht keine, werden erst die Negativbeispiele nachgeschärft. Reicht die Zeit nicht, geht die Null-Variante (Stufe 0) in den Hörversuch.

**2.6 Einbau.** Als neuer Ranker unter `src/ranking/`, über den vorhandenen Schalter `ranking_method` (`src/batch_render.py:138`).

*Fertig, wenn:* eine Tabelle der Offline-Kennzahlen für Stufe 0 bis 2 mal zwei Repräsentationen mal drei Seeds vorliegt, der Abkürzungstest dokumentiert ist und der Ranker im Batch-Render läuft.

### Phase 3: Ein Hörversuch für beide Fragen (Woche 3, 3 bis 4 Tage)

**Design:**

| Element | Festlegung |
|---|---|
| Material | 10 bis 12 Trackpaare aus dem eingefrorenen Evaluationsset |
| Faktor Cue-Wahl | SSL-Metrik Top-1, Regel-Ranking Top-1, Zufall unter den gefilterten Kandidaten |
| Faktor Kurve | Equal Power, direkt optimiert (Verlustfunktion v4, Zwei-Band) |
| Anker | harter Schnitt am Cue |
| Stimuli | 7 je Paar, rund 20 s, blind, zufällige Reihenfolge, Lautheit angeglichen |
| Bewertung | Skala 0 bis 100 je Stimulus nach MUSHRA-Art, dazu ein optionaler Kommentar |
| Dauer | rund 30 bis 40 Minuten je Person; mindestens drei Hörende, falls E3 das erlaubt |

**Hypothesen, vorab im Repo festgehalten:**
- **H1:** Cues der SSL-Metrik werden besser bewertet als Cues der Regelformel.
- **H2:** Der Effekt der Cue-Wahl ist größer als der Effekt der Kurve.
- **H3:** Die direkt optimierte Kurve wird nicht schlechter bewertet als Equal Power. Das wiederholt P2 sauber.
- **Sekundär:** Korrelation jeder Metrik (Proxy-Verlust, Regelformel, Render-Metrik, SSL-Metrik) mit den Urteilen, innerhalb jedes Trackpaars. Das beantwortet die „Aussagekraft der Metrik" aus der Aufgabenstellung direkt.

**Auswertung:**
- Gemischtes Modell: Bewertung ~ Cue × Kurve, mit zufälligen Effekten für Trackpaar und Person.
- Konfidenzintervalle per Bootstrap über Trackpaare.
- Ausschlussregeln vorab festgelegt.

*Fertig, wenn:* Rohdaten, Auswertungsskript und Ergebnistabelle im Repo sind und die vorab festgelegte Analyse unverändert gelaufen ist.

### Phase 4: Pflichtteile (parallel zu Phase 3, 2 bis 3 Tage)

- Mashup-Export: eine Sequenz aus mehreren Abschnitten zu einer Audiodatei verketten, mit konsistenter Tempobehandlung über alle Kanten.
- 1 und 3 Takte im Baseline-Renderer, in der Kandidatenerzeugung und in der GUI.
- `tempo_fade` entweder als echte Variante bauen oder streichen.
- Optional: Beat-Erkennung auf Beat This! umstellen. Damit wäre die Pipeline plattformunabhängig und das Windows-Programm aufTAKT überflüssig.

*Fertig, wenn:* ein Mashup aus mindestens drei Songs mit gemischten Übergangslängen (1 bis 4 Takte) als eine Datei exportiert wird.

### Phase 5: Schreiben (Woche 4)

- **Forschungsfragen neu zuschneiden:**
  - F1 Wo gegen Wie (Phase 3);
  - F2 SSL-Metrik gegen Regeln und klassische Merkmale (Phasen 2 und 3);
  - F3 Warum der Proxy-trainierte Controller wenig lernt (Phase 1.4).
- **Related Work ergänzen:** Fedorishin et al. 2024 (Audio Match Cutting), CPC, Debiased Contrastive Learning, MARBLE und SUPERB.
- **Beiträge** nur aus Ergebnissen, die eine Matrixzeile haben (G9).

### Optional: Phase 6, nur bei Vorsprung nach Woche 3

Die SSL-Metrik als differenzierbaren Kritiker statt der V-Vorlage ins Controller-Training einbauen. Das ist die höchste Novelty: ein Gegenstück zu DJTransGAN ohne echte DJ-Mixe. Es ist aber auch das höchste Risiko: Der Controller kann Schwächen des Kritikers ausnutzen, und MERT auf gerendertem Audio ist teuer.

---

## 6. Was eingestellt wird

| Was | Status künftig |
|---|---|
| weitere Controller-Architekturen und Hyperparameter-Sweeps | nur noch als Diagnose aus Phase 1.4 berichtet |
| variable Längen 6 und 8 Takte | Ausblick; außerhalb der Aufgabenstellung |
| Lehrer des Cue-Rankers (Labels aus der Verlustfunktion) | eingestellt; zirkulär |
| Metrik für die Überlagerung (Stem-Ansatz) | Ausblick, falls E5 nicht anders entscheidet |
| weitere Provenienz-Werkzeuge | reicht; der Aufwand geht in kontrollierte Vergleiche |

---

## 7. Risiken und Ausweichpfade

| Risiko | Ausweichpfad |
|---|---|
| Die SSL-Metrik ist nicht besser als die Regelformel. | Ebenfalls ein Ergebnis. Mit Phase 3 sauber gemessen, beantwortet es F2 negativ und bleibt berichtbar. |
| Die Abkürzung „gleiche Aufnahme" lässt sich nicht beseitigen. | Null-Variante (roher MERT-Kosinus) und klassische Merkmale als Bedingungen verwenden; die Abkürzung als Befund berichten. |
| Nur eine hörende Person ist zulässig (E3). | Mehr Trackpaare statt mehr Personen. Die Hypothesen trotzdem vorab festlegen und das Ergebnis als explorativ kennzeichnen. |
| Die Zeit reicht nicht. | In dieser Reihenfolge streichen: Phase 6, Beat This!, Kapazitätsstufe 3, Seeds für den TCN. Nicht streichen: Phasen 1.1, 1.4, 2.4 und 3. |

---

## 8. Zeitplan

| Woche | Inhalt | Ergebnis am Wochenende |
|---|---|---|
| 1 | Phase 0, Phase 1 | Protokoll und Evaluationsset festgeschrieben, Vergleichsmatrix, Diagnose-Tabelle |
| 2 | Phase 2 | Offline-Kennzahlen, Abkürzungstest, Ranker integriert |
| 3 | Phase 3, Phase 4 | Hörversuch durchgeführt, Mashup-Export, 1 bis 4 Takte |
| 4 | Phase 5 (Phase 6 nur bei Vorsprung) | Kapitel 3 bis 7 überarbeitet |
