# Rückmeldung zum Umsetzungsstand

Stand: 22. November 2026, Commit `4651e51`. Bezug: [Aktionsplan vom 18.11.](./ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md) und dein [Umsetzungsdokument](../docs/REVIEW_JP_UMSETZUNG.md). Einstieg in alle Review-Dokumente: [README](./README.md).

Ergänzt am 23. November 2026: einführende Erklärungen in 4.1, 4.2 und Befund 1. Korrigiert am selben Tag: In Befund 3 sind die Punkte Download und Seed zurückgenommen, weil deine Durchführungsanleitung sie abdeckt. Alle anderen Befunde und Zahlen sind unverändert. Ebenfalls am 23.11. eingetragen: die Entscheidung der Betreuung zur Paarzahl (Befund 3, Abschnitt 9) und Abschnitt 11. Dazu Abschnitt 12 mit dem Design des Hörversuchs als lokale Web-Anwendung. Außerdem in 4.1 und Abschnitt 8 die Einordnung, was umgesetzt werden muss und was zu benennen reicht.

## 1. Kurzfassung

Die Umsetzung ist in zwei Tagen sehr weit gekommen und sauber belegt: Protokoll, eingefrorenes Evaluationsset, Vergleichsmatrix, Controller-Diagnose mit Seeds, trainierte Fortsetzungsmetrik und fertige Stimuli. Das eingefrorene Protokoll ist besser, als ich es skizziert hatte.

Bevor jemand hört, müssen drei Dinge geklärt sein:

1. Der Vorsprung von MERT gegenüber den klassischen Merkmalen kann ein Artefakt der Kodierung sein.
2. Die Tempo-Angleichung der normalen Pipeline ist zu grob; korrigiert ist sie bisher nur im Renderer des Hörversuchs.
3. Der Hörversuch bleibt nach Entscheidung der Betreuung bei 7 Paaren und ist damit nach dem eigenen Protokoll beschreibend. Vor dem Hören ist der harte Schnitt als Anker gleich auf die Cues zu verteilen.

Alle drei lassen sich jetzt noch billig beheben, weil es noch keine Bewertungen gibt. Den 27.11. halte ich damit für nicht haltbar. Die Reihenfolge steht in Abschnitt 8.

## 2. Wie geprüft wurde

| Marke | Bedeutung |
|---|---|
| **[C]** | von mir selbst im Code gelesen |
| **[C*]** | von einem Hilfsagenten gelesen, die Fundstelle habe ich nachgelesen |
| **[A]** | von einem Hilfsagenten gelesen, von mir nicht nachgeprüft |
| **[B]** | aus deinen versionierten Belegen (CSV, JSON, Berichte), nicht neu gerechnet |
| **[M]** | von mir ausgeführt |

Die Artefakte unter `output/review_jp_20261118/` (Stimuli, Checkpoints, Caches, Einzelränge) liegen nur bei dir. Ich konnte deshalb nichts nachrechnen, was unterhalb der versionierten Tabellen liegt, und nichts anhören.

Tests **[M]**: 399 bestanden, 5 übersprungen (CUDA), 1 Fehlschlag wegen fehlendem PySide6 in meiner Umgebung. Vorher brach die Suite beim Einsammeln ab, weil `psutil` nicht in den Requirements steht (Abschnitt 6).

## 3. Stand je Planschritt

| Planschritt | Paket | Stand | Anmerkung |
|---|---|---|---|
| Entscheidungen | P00 | vom Autor getroffen | Antwort der Betreuung offen (Abschnitt 9) |
| Protokoll und eingefrorenes Set | P01 | erledigt | 22 neue Aufnahmen, 11 Paare, Commit `2a70dc1` **[B]** |
| Vergleichsmatrix | P02 | erledigt | im Ledger, Kapitel 5 abgedeckt **[B]** |
| Training gleich Anwendung | P03 | erledigt | Cue-Skalierung und Vocal-Backend an den Run-Vertrag gebunden **[C*]** |
| Gemeinsamer Renderpfad | P04 | erledigt | mit Lautheitsabgleich **[A]** |
| Equal-Power-Start | P05 | erledigt für neue Läufe | alte Checkpoints bleiben über den Legacy-Vertrag ladbar **[C*]** |
| Controller-Diagnose | P06 | erledigt | Ergebnisse in Abschnitt 4.1 |
| Repräsentationen pro Takt | P07 | erledigt | MERT-v1-95M und 41 klassische Kanäle **[C]** |
| Paare und Negative | P08 | erledigt | 12.999 Trainings- und 2.830 Validation-Abfragen **[B]** |
| Metrik trainieren | P09 | erledigt | drei Stufen, je drei Seeds **[C]** |
| Offline-Prüfung, Ranker | P10 | erledigt | `mert_continuation_v1` im Batch-Render **[C]** |
| Hörversuch | P11 | Material fertig, nicht durchgeführt | 7 Paare, 49 Clips, 3 Player-Pakete **[B]** |
| Auswertung | P12 | fehlt | kein Code vorhanden **[A]** |
| 1 bis 4 Takte | P13 | erledigt für Baselines | ML bleibt bei 4 bzw. 2/4/6/8 Takten **[C*]** |
| Mashup-Export | P14 | fehlt | nicht begonnen **[M]** |
| Thesis, Abschlussprüfung | P15, P16 | fehlt | nicht begonnen |

## 4. Ergebnisse, die stehen

### 4.1 Controller (Forschungsfrage F3)

Ein Controller ist hier das Netz, das für ein bereits gewähltes Cue-Paar die Steuerkurven der Mischung ausgibt (Pegel, EQ, Bass, Gesang). Es wählt keine Stelle und erzeugt kein Audio.

Die Tabelle vergleicht vier Wege zu diesen Kurven:

- **Equal Power:** Standard-Crossfade ohne Netz.
- **Feste Kurve:** eine einzige, auf den Trainingsdaten optimierte Kurvenschar, für jedes Paar gleich.
- **Modell:** der Controller.
- **Direkt:** die Kurven werden für jedes Beispiel einzeln optimiert, ohne Netz.

Entscheidend ist Modell gegen feste Kurve. Nur wenn der Controller sie schlägt, nutzt er seine Eingabe.

Validation-Verlust, niedriger ist besser. Paare gleich gewichtet **[B]**, Stichproben von mir an `p06/controls.csv` und `p06_run02/matrix.csv` bestätigt **[C*]**.

| Pfad | Equal Power | feste Kurve | Modell | direkt | unabhängige Einheiten |
|---|---|---|---|---|---|
| R1 Zwei-Band-MLP | 0,421 | 0,411 | 0,415 | 0,368 | 5 Trackpaare, 2 Gruppen |
| R2 Vocal-MLP | 0,351 | 0,347 | 0,325 | 0,281 | 5 Trackpaare, 2 Gruppen |
| R3 TCN, alter Lauf | 0,411 | 0,307 | 0,321 | 0,191 | 5 Trackpaare, 2 Gruppen |
| R3 TCN, neuer Start (1 Seed) | 0,411 | 0,307 | 0,240 | 0,191 | 5 Trackpaare, 2 Gruppen |
| R4 variabler TCN, 4 Takte | 0,273 | 0,260 | 0,230 | 0,217 | 52 Trackpaare, 12 Gruppen |

Was sich daraus sagen lässt:

- Der alte TCN gibt für alle Beispiele exakt dieselbe Kurve aus (alle zehn Kanäle mit Spannweite null, auf Train und Validation). Das MLP ist schlechter als eine feste Kurve. Für diese beiden Pfade trifft die Kritik aus dem Review zu.
- Vocal-MLP, TCN mit korrektem Start und variabler TCN schlagen die feste Kurve. Meine Vermutung war hier zu pessimistisch.
- Belastbar ist das nur für R4: Dort liegt das Modell in allen 12 unabhängigen Gruppen unter der festen Kurve. Bei R2 und R3 tragen 2 Gruppen das Ergebnis.
- Alles gilt für die Proxy-Verlustfunktion. Der Gewinn stammt überwiegend aus dem Energie-Term mit seiner festen V-Vorlage **[A]**. Ein hörbarer Nutzen ist nicht gezeigt.

Was nicht in die Thesis gehört: „77 % des Optimums" (die direkte Optimierung ist bei endlichem Budget keine Obergrenze), Vergleiche zwischen den Pfaden, eine Ursachenaussage „der Equal-Power-Start macht den TCN eingabeabhängig" (1 Seed, mehrere Änderungen zugleich).

Warum keine Vergleiche zwischen den Pfaden: Die vier Pfade unterscheiden sich gleichzeitig in Renderer, Version der Verlustfunktion und Datensatz (R1 bis R3 auf 5 Trackpaaren, R4 auf 52). Zulässig ist je Pfad der Gewinn gegenüber der festen Kurve.

Der Hörversuch prüft keinen der trainierten Controller. Sein Kurvenfaktor vergleicht Equal Power mit einer direkt optimierten Kurve ohne Netz **[C]** (`docs/masterarbeit/review_jp_20261118/p11/studienprotokoll.md:19`). Ein hörbarer Nutzen der Netze bleibt damit ungeprüft. Die Controller treten in der Thesis als Diagnose auf.

Was für F3 fehlt, falls die Thesis mehr als eine Diagnose behaupten soll **[A]**:

- Audio-Unterschied Modell gegen feste Kurve. Gemessen ist bisher nur Modell gegen Equal Power.
- Nachweis, dass feste Kurve und direkte Optimierung konvergiert sind (Verlauf, mehr Schritte oder Neustarts).
- Mindestens drei Seeds für R3 mit neuem Start.

### 4.2 Fortsetzungsmetrik (Forschungsfrage F2)

Markierte Beispiele für gute Übergänge gibt es nicht. Die Metrik lernt deshalb an einer Rateaufgabe innerhalb einzelner Songs: Sie bekommt ein Stück und soll erkennen, welches Stück im selben Song wirklich folgt. Die richtige Antwort liefert der Song selbst; das ist das Selbstüberwachte.

Training und Anwendung teilen dieselbe Aufteilung:

| Stück | Training, ein Song | Anwendung, zwei Songs |
|---|---|---|
| Abfrage | 4 Takte vor einer Schnittstelle | 4 Takte von Song A vor dem Übergang |
| Lücke | 4 Takte, ausgelassen | der Übergang, in dem A und B gemischt sind |
| Kandidat | 4 Takte danach: die echte Fortsetzung oder ein fremdes Stück | 4 Takte von Song B nach dem Übergang |

Die Fenster habe ich im Code gelesen **[C]** (`src/features/p08_pairs.py:22-23`, `src/ranking/continuation.py:84-98`). Dass der Übergang genau in der Lücke liegt, steht in deinem P08-Bericht **[B]** (`docs/masterarbeit/REVIEW_JP_P08_PAARE_20261119.md:19`).

Ein hoher Wert heißt in der Anwendung: B könnte an dieser Stelle als Fortsetzung von A durchgehen.

Jedes Stück wird vorher in Zahlen beschrieben. Das übernimmt entweder MERT, ein vortrainiertes und hier eingefrorenes Musikmodell, oder ein Satz klassischer, von Hand festgelegter Merkmale. Dahinter sitzt ein kleines Netz, der Kopf, der aus zwei Beschreibungen den Passwert macht. Trainiert wird nur der Kopf. Die Spalten der Tabelle sind drei Ausbaustufen: direkter Vergleich ohne Kopf, ein einfacher Kopf und ein größerer.

Aufgabe: die richtige Fortsetzung unter 9 Kandidaten finden; Zufall wäre 11 % **[B]**. Angegeben ist der Anteil der Abfragen, bei denen sie auf Platz 1 steht (Recall@1).

| | Kosinus ohne Training | bilinear | zwei Türme |
|---|---|---|---|
| klassische Merkmale | 55,8 % | 61,2 % | 68,5 % |
| MERT | 44,5 % | 62,1 % | 85,7 % |

- Training, Verlust und Auswahlregel entsprechen dem Plan **[C]** (`src/ml/p09_train.py`, `src/ml/p08_contrastive.py`). Die Korrektur für falsche Negative ist korrekt umgesetzt.
- Die Rangfolge der Metrik hängt praktisch nicht mit der Regelformel zusammen (mittlere Rangkorrelation −0,03 über 26 Entwicklungspaare) **[B]**. Beide wählen also verschiedene Cues. Das macht den Hörversuch aussagekräftig.
- Die Zahlen sind auf der Validation gewählt und gemessen. Das steht im Bericht, gehört aber auch in jede Tabelle der Thesis.
- Ob 85,7 % gegen 68,5 % ein Unterschied der Repräsentation ist, hängt an Befund 1.

## 5. Drei Befunde vor dem Hörversuch

### Befund 1: Abfrage und Fortsetzung teilen den Encoder-Kontext

**In einfachen Worten.** MERT bekommt das Audio in Blöcken von rund 20 Sekunden und darf beim Beschreiben jedes Moments auf den ganzen Block hören. Abfrage, Lücke und echte Fortsetzung liegen meist im selben Block. Die Beschreibung der Abfrage entsteht also, während MERT die echte Fortsetzung mithört; bei den fremden Stücken ist das nie so. Der Kopf kann damit lernen „diese beiden wurden zusammen verarbeitet“ statt „das passt musikalisch“.

Dass die Beschreibungen danach pro Takt getrennt gespeichert werden, ändert daran nichts. Nötig ist, das Audio vor MERT zu schneiden. Die Regel: Keine Beschreibung darf über die Schnittstelle hinweg hören, im Training wie in der Anwendung.

**Was.** MERT wird über den ganzen Track in Kernen von 20 s mit 2 s Kontext je Seite berechnet (`src/features/p07_mert.py:29-30`, `:47-53`, `:100-133`) **[C]**. MERT ist ein Transformer, bei dem jeder Frame den ganzen Eingabeblock sieht. Abfrage, Lücke und Fortsetzung umfassen 12 Takte, bei 150 bis 160 BPM also 18 bis 19 s (`src/features/p08_pairs.py:22-23`) **[C]**. In den meisten Fällen hat das Abfragefenster die echte Fortsetzung deshalb schon gesehen.

Die falschen Kandidaten stammen aus anderen Tracks oder liegen mehr als 16 Takte entfernt (`src/features/p08_windows.py:99-105`) **[C]**. Sie teilen nie einen Block mit der Abfrage.

**Warum es zählt.**

- Die klassischen Merkmale werden pro Halbbeat lokal berechnet und haben diesen Vorteil nicht. Der Vergleich der Repräsentationen ist damit nicht fair.
- In der Anwendung werden A und B getrennt kodiert (`src/ranking/continuation.py:64-81`) **[C]**. Der Kopf wurde also auf einem Signal trainiert, das es zwischen zwei Songs nicht gibt.
- Die beiden Abkürzungstests schließen das nicht aus. Ihre Gegenbeispiele liegen ebenfalls außerhalb des Blocks. Zusätzlich sind sie so gezogen, dass sie sich strukturell von der richtigen Antwort unterscheiden (mindestens zwei von vier Strukturmerkmalen um eine Standardabweichung, `p08_windows.py:104-105`) **[C]**. Ein Modell, das nur „gleicher Abschnitt" erkennt, besteht sie ebenfalls.

Dein P08-Bericht erwähnt den Chunk-Kontext in einem Satz. Gemessen ist der Effekt nicht. Auch von mir nicht: Das ist eine Ableitung aus dem Code, kein Messwert.

**Was zu tun ist.**

1. Schnelle Schichtung mit vorhandenen Ergebnissen (Minuten): `review_jp/scripts/mert_kontext_check.py`. Das Skript teilt die 2.830 Validation-Abfragen danach, ob eine Kerngrenze Abfrage und Fortsetzung trennt, und berichtet Recall@1 je Schicht für alle 14 Bedingungen. Die klassischen Zeilen sind die Kontrolle. Im Selbsttest läuft es; mit deinen Daten ist es ungetestet.
2. Sauberer Test (unter einer Stunde, nur Inferenz): Für die Validation-Fenster das Audio vor MERT schneiden und jedes Fenster einzeln kodieren. Die Abfrage aus Audio, das an der Schnittstelle endet, die Kandidaten aus Audio, das an ihrem Fensteranfang beginnt. Den vorhandenen Studienkopf darauf auswerten.
   - Vorher im MERT-Paper nachlesen, mit welcher Ausschnittlänge vortrainiert wurde. Nach meiner Erinnerung sind es rund 5 Sekunden; nachgeprüft habe ich das nicht. Ein Vier-Takt-Fenster dauert hier rund 6 Sekunden.
3. Fällt Recall@1 deutlich: Köpfe auf einzeln kodierten Fenstern neu trainieren, nach demselben Protokoll, und im Ranker ebenso kodieren. Das wird eine neue Protokollversion für die Metrik.
4. Eine härtere Kontrolle ergänzen: Gegenbeispiele aus derselben Aufnahme und demselben Abschnittstyp. Das Ergebnis darf nahe am Zufall liegen; es zeigt, was die Metrik unterscheidet und was nicht.

**Fertig, wenn** eine Tabelle Recall@1 für die ursprüngliche und die einzeln kodierte Variante zeigt (MERT Stufen 0 und 2, klassisch Stufe 2) und die Entscheidung über den Studienkopf vor dem erneuten Rendern der Stimuli datiert im Repo steht.

### Befund 2: Die Tempo-Angleichung der Pipeline ist zu grob

**Was.** Die Pipeline streckt B um das Verhältnis der BPM-Felder und lässt die Streckung weg, wenn die Felder gleich sind (`src/pipeline.py:225-227`) **[C]**. Das BPM-Feld ist der globale librosa-Wert (`src/analysis/pre_analysis.py:460`) **[C]**. Er ist auf ganze Analyseschritte gerastert: 16 der 18 akzeptierten neuen Aufnahmen stehen bei exakt 160,71 BPM **[A]**. Benachbarte Rasterwerte liegen knapp 3 % auseinander.

Dein Korrekturbericht belegt die Folge **[B]** (`docs/masterarbeit/review_jp_20261118/p11/korrektur_run02.md`): In 9 von 21 gewählten Cues unterschieden sich die 16-Schlag-Spannen von A und B um mindestens 40 ms, im Extremfall um 160 ms.

**Warum es zählt.**

- 160 ms über vier Takte sind in der Mitte der Überblendung rund 80 ms Versatz zwischen den Kicks. Das ist hörbar.
- Die Korrektur steht nur im Renderer des Hörversuchs (`src/evaluation/p11_alignment.py`, aufgerufen in `src/evaluation/comparison_study.py:100`) **[C]**. Pipeline, GUI, Batch-Render und die Trainingsfenster sind unverändert.
- Betroffen sind damit auch alle bisherigen Render: Trainingsdaten der Controller und die früheren Hörsätze. Der im Hörtest vom 6.11. wegen „Tempoproblem" ausgeschlossene Clip passt dazu.

**Bedenken zur jetzigen Korrektur.**

- Sie streckt jeden einzelnen Schlag von B auf die Länge des entsprechenden Schlags von A, ohne Obergrenze. Im größten Fall ist der Faktor 0,667; 227 von 336 Intervallen werden gestreckt (`docs/masterarbeit/review_jp_20261118/reviews/R_P11_02.md:25`) **[C*]**.
- Damit wird das Zittern der Beat-Erkennung (Raster 10,7 ms) in die Musik hineingestreckt, mit einer Nahtstelle nach jedem Schlag.
- Die Prüfung „höchstens 1 % und 20 ms" kann nicht scheitern, weil die geprüften Marken aus den A-Längen selbst gebaut werden (`p11_alignment.py:74-76`) **[C]**.
- Der harte Schnitt bekommt die Korrektur nicht, die anderen sechs Clips schon. Wie stark sie eingreift, hängt vom Cue ab. Das kann den Vergleich der Cue-Wahlen verfälschen.

**Was zu tun ist.**

1. Tempo aus dem Beat-Raster schätzen statt aus dem BPM-Feld: lineare Regression der Schlagzeiten über ein längeres Fenster um den Cue (zum Beispiel 64 Schläge). Bei EDM mit festem Tempo ist das auf Bruchteile eines Promille genau und mittelt das Rasterzittern heraus.
2. B für die Brücke mit einem einzigen Faktor aus diesem Verhältnis strecken, in `src/bridge.py`, damit Pipeline, GUI, Batch, Training und Hörversuch denselben Weg nehmen.
3. Eine echte Prüfung dahinter: Cue ablehnen, wenn die Schläge nach der Streckung um mehr als eine festgelegte Toleranz vom Regressionsraster abweichen.
4. An Entwicklungsclips anhören: bisherige Pipeline, neue Angleichung und die Streckung pro Schlag im direkten Vergleich.
5. Für die Thesis beziffern, wie viele der bisherigen Trainingsbeispiele und Hörclips einen Spannenfehler über 20 ms hatten.

**Fertig, wenn** die Verteilung der Spannenfehler vor und nach der Änderung als Tabelle vorliegt, die Hörprobe protokolliert ist und der Hörversuch denselben Code benutzt wie die Pipeline.

### Befund 3: Der Hörversuch kann so nichts bestätigen

**Was.**

- 4 der 11 Paare fielen an der Rasterprüfung aus. Dein Protokoll erlaubt unter 10 unabhängigen Paaren nur eine beschreibende Auswertung, ausdrücklich ohne Bestätigung von H1 bis H3 (`docs/EVALUATION_PROTOCOL.md:98`) **[C*]**. Das frische Material würde für ein Ergebnis verbraucht, das von vornherein offen bleiben muss.
- Der Anker ist ungleich verteilt. Der harte Schnitt liegt nur am Regel-Cue **[C]** (`docs/EVALUATION_PROTOCOL.md:74`). Der Regel-Cue ist damit dreimal zu hören, davon einmal in einer absichtlich schlechten Fassung; die beiden anderen Cues je zweimal. Das kann die Bewertung des Regel-Cues in beide Richtungen verschieben und trifft genau den Vergleich H1. Hörende müssen dafür nichts über das Design wissen.
- Zugriff auf Dateien und Reihenfolgen: Der im Repository committete Player hat keine Download-Sperre (`src/evaluation/p11_player.html:22`) **[C*]**, und die Reihenfolgen entstehen aus einem öffentlichen Seed (`src/evaluation/p11_player.py:15`, `:27`) **[C*]**. Deine Durchführungsanleitung schließt beides am betreuten Hörplatz aus (`docs/masterarbeit/review_jp_20261118/p11/durchfuehrung.md:9-13`) **[C]**. Das reicht, solange niemand bewertet, der das Repository kennt. In der ersten Fassung dieser Rückmeldung hatte ich das als Lücke gewertet; das war überzogen. Die geplante Web-Anwendung ersetzt diesen Player; die Anforderungen stehen in Abschnitt 12.
- Der Kurvenfaktor ist schwach: Die direkt optimierte Kurve weicht auf Entwicklungsdaten im Mittel rund 0,7 dB von Equal Power ab **[B]**. H3 ist damit fast sicher erfüllt und sagt wenig.
- Der Auswertungscode (gemischtes Modell, Bootstrap, Kontraste) fehlt **[A]**.

**Entscheidung der Betreuung (23.11.2026).** Es bleibt bei 7 Paaren. Der Versuch soll nicht größer werden: 49 Clips von rund 19 s sind etwa 15 Minuten reine Hörzeit pro Person. Folgen:

- Nach deinem Protokoll ist die Auswertung damit beschreibend; H1 bis H3 werden nicht bestätigt (`docs/EVALUATION_PROTOCOL.md:98`). So gehört es auch in die Thesis.
- Die Schwelle von 10 Paaren nicht nachträglich senken. Rechnerisch wäre eine Bestätigung mit 7 Paaren ohnehin nur möglich, wenn alle 7 in dieselbe Richtung zeigen. Überschlag mit einem einseitigen Vorzeichentest: 7 von 7 ergibt 1/128 ≈ 0,008 und liegt unter der korrigierten Grenze 0,05/3 ≈ 0,017; 6 von 7 ergibt 0,063.
- Das Gewicht der Arbeit liegt damit auf den Offline-Ergebnissen der Metrik. Befund 1 wird dadurch wichtiger.

**Was zu tun ist.** Eine zweite Protokollfassung, bevor jemand hört:

1. Paarzahl: bleibt bei 7 (Entscheidung oben). Im Protokoll Version 2 festhalten, dass die Auswertung beschreibend ist.
2. Optional: die vier Rasterausfälle neu ansehen. Zwei haben 50 % Abdeckung; das spricht für eine Halb- oder Doppeltempo-Uneinigkeit der beiden Erkenner **[A]**. Abschnitt 11 beschreibt ein Vorgehen dafür. Zurückgewonnene Paare dürfen nur dazukommen, wenn die Regel vorher im Protokoll steht.
3. Den harten Schnitt an jeder der drei Stellen rendern. Jede Person hört pro Paar einen davon, rotierend (Abschnitt 12.2). Es bleiben sieben Clips pro Paar.
4. Die Zugriffsprüfung am Hörplatz wie in deiner Durchführungsanleitung vorgesehen durchführen und protokollieren. Mehr ist hier nicht nötig.
5. Hörende, die das Design und das Repository nicht kennen. Autor und Betreuer scheiden als Bewerter aus. Drei Personen sind das Minimum des Protokolls; mehr Personen senken das Rauschen, ersetzen aber keine Paare.
6. Die Auswertung schreiben und an Kunstdaten mit bekanntem Effekt testen, bevor die Zuordnung geöffnet wird.
7. Stimuli erst nach den Entscheidungen zu Befund 1 und 2 neu rendern.
8. Die Web-Anwendung für den Versuch nach Abschnitt 12 bauen.

**Fertig, wenn** Protokoll Version 2 mit Anlass und Datum committet ist, der harte Schnitt gleich verteilt ist und die Auswertung auf Kunstdaten den eingebauten Effekt wiederfindet.

## 6. Kleinere Punkte

| Punkt | Fundstelle | Was tun |
|---|---|---|
| Im neuen TCN-Pfad bewertet die Verlustfunktion die Sinus-Gain-Kurve als Mix-Position. Glattheit, Vocal- und Transienten-Terme rechnen damit auf der falschen Kurve; die Werte sind nicht mit R1 vergleichbar. **[C*]** | `src/control/differentiable.py:435`, `src/ml/control_initialization.py:64-74` | Position getrennt an die Verlustfunktion geben; R3 mit neuem Start danach neu messen |
| Neue Abhängigkeiten fehlen in den Requirements: `psutil`, `transformers` 4.49.0, `pyloudnorm`. Ein frischer Checkout kann die Tests nicht einsammeln. **[M]** | `src/features/p07_extract.py:13` | Requirements ergänzen |
| Sweeps starten weiter im alten Modus, also 9,9 dB unter Equal Power. **[C*]** | `src/ml/__main__.py:838`, `:867`, `:921` | Default auf `equal_power_v1` |
| Ein Fallback-Raster wird nicht mehr wiederverwendet, aber auch nie gespeichert. Jeder Aufruf wiederholt die ganze Analyse. **[C*]** | `src/analysis/pre_analysis.py:251-253`, `:274-275` | Fallback mit eigenem Schlüssel speichern |
| Nach dem Umsortieren in der GUI bleiben alte Cues und Bereiche an der Kante hängen. **[C*]** | `src/gui/transition_builder.py:971-980` | mit dem Mashup-Export beheben |
| `tempo_fade` ist weiter dieselbe Klasse wie `fade`. **[C*]** | `src/pipeline.py:45` | streichen oder als Alias kennzeichnen |
| Manifeste enthalten Windows-Pfade; die GUI findet auf anderen Rechnern keine Modelle. **[A]** | `src/gui/ml_transition.py:36` | Pfade relativ und mit `/` schreiben |
| Die Reviews im Repo heißen „unabhängig", sind aber eigene Agentensitzungen mit der Vorgabe, nichts außerhalb des Plans zu verlangen. Sie haben echte Fehler gefunden. Es sind Konsistenzprüfungen. **[A]** | `docs/masterarbeit/UMSETZUNGSPROMPTS_REVIEW_JP_20261118.md:653` | in der Thesis als Kreuzprüfung bezeichnen, nicht als unabhängiges Review |

## 7. Was aus den Befunden vom 13.11. geworden ist

Nummern aus Abschnitt 6 des [Code-Reviews](./CODE_REVIEW.md).

| Nr. | Befund vom 13.11. | Stand 22.11. |
|---|---|---|
| 1 | TCN startet 9,9 dB unter Equal Power | behoben für neue Läufe; Sweeps noch im alten Modus |
| 2 | Energieziel ist eine feste V-Form | unverändert, in P06 als Grenze gemessen |
| 3 | EQ und Ducking im Full-Band-Pfad ohne Vocal-Signal | unverändert; dazu der neue Punkt in Abschnitt 6, Zeile 1 |
| 4 | GUI skaliert den Ziel-Cue invers | behoben, mit Test |
| 5 | Zwei Verlust-Terme sind linear | unverändert, dokumentiert |
| 6 | Validation hängt an 2 bzw. 5 Tracks | für den alten Datensatz unverändert; R4 hat 12 Gruppen; neues Set eingefroren |
| 7 | Fehlgeschlagene Analyse wird dauerhaft gecacht | teilweise behoben (Abschnitt 6, Zeile 4) |
| 8 | 0,2-s-Schwelle beim Beat-Abgleich | unverändert, dokumentiert |
| 9 | Chroma und Tonart kaum belastbar | unverändert; die Kanäle sind Teil der klassischen Vergleichsbasis |
| 10 | Wächter des Cue-Ranker-Lehrers bewertet ein Kunstsignal | Lehrer eingestellt; der alte Code liegt noch im Repo |
| 11 | ML in der GUI läuft nur auf dem Autorenrechner | offen |
| 12 | `tempo_fade` gleich `fade` | aus der Standardliste entfernt, Alias bleibt |
| 13 | Zustände nach dem Umsortieren in der GUI | offen |
| 14 | Zwei Kanäle heißen anders, als sie rechnen | unverändert |
| 15 | LayerNorm über gemischten Eingangsvektor | unverändert |

Neu seit dem 13.11.: die Tempo-Angleichung (Befund 2). Sie stand im damaligen Hilfsbericht als unsichere Vermutung und fehlte in meiner Fehlerliste.

## 8. Reihenfolge der nächsten Schritte

| Nr. | Schritt | Aufwand | Fertig, wenn |
|---|---|---|---|
| 1 | Befund 1 prüfen, bei Bedarf Köpfe auf einzeln kodierten Fenstern neu trainieren | 1 bis 2 Tage | Vergleichstabelle und datierte Entscheidung zum Studienkopf |
| 2 | Befund 2: Tempo aus dem Beat-Raster, eine Angleichung für alle Pfade | 1 bis 2 Tage | Fehlertabelle vor/nach, Hörprobe an Entwicklungsclips |
| 3 | Protokoll Version 2 (Anker gleich verteilt, Auswertung beschreibend), Web-Anwendung nach Abschnitt 12, Auswertungscode | 1 bis 2 Tage | Abschnitt 5, Befund 3 |
| 4 | Stimuli neu rendern, Kreuzprüfung | 0,5 Tage | technischer Nachweis wie bei run02 |
| 5 | Hörversuch mit mindestens 3 Personen, Auswertung | 2 bis 3 Tage | Rohdaten gesichert, vorab festgelegte Analyse gelaufen |
| 6 | Mashup-Export, GUI-Zustände, parallel zu 5 | 2 bis 3 Tage | drei Songs, gemischte Längen, eine Datei |
| 7 | Pflichtpunkte aus Abschnitt 6 (Einordnung unten) | 1 bis 2 Tage | Tests grün aus frischem Checkout |
| 8 | Thesis und Abschlussprüfung | rund 1 Woche | jede Kernaussage mit Matrixzeile |

Die Schritte 1 bis 3 lassen sich teilweise parallel bearbeiten. Schritt 4 braucht alle drei.

### Was umgesetzt werden muss und was zu benennen reicht

Maßstab: Umgesetzt werden muss, worauf eine Aussage der Thesis ruht oder was ein Ergebnis verfälscht. Bei allem anderen reicht es, die Grenze offen zu benennen und nichts darüber hinaus zu behaupten. Das Benennen kostet keine Genauigkeit, sondern Reichweite: Die Aussagen werden enger, bleiben aber richtig.

| Punkt | Einordnung | Begründung |
|---|---|---|
| MERT einzeln kodieren (Befund 1) | Pflicht | Die Kernaussage „MERT schlägt klassische Merkmale“ ruht darauf. |
| Tempo-Angleichung (Befund 2) | Pflicht | Alle Stimuli hängen daran; tempoangepasste Übergänge sind eine geforderte Funktion. |
| Anker gleich verteilen, Protokoll Version 2, Auswertung vor dem Entblinden (Befund 3) | Pflicht | Nach dem Hören nicht mehr zu beheben. |
| Requirements ergänzen (Abschnitt 6) | Pflicht | Ohne sie läuft nichts aus einem frischen Checkout. Kleiner Aufwand. |
| Mashup-Export samt Zustand nach dem Umsortieren in der GUI | Pflicht | Geforderte Funktion; der Zustandsfehler betrifft den Export nach dem Umsortieren. |
| Sweep-Voreinstellung auf Equal-Power-Start (Abschnitt 6) | Pflicht, sobald ein Sweep läuft | Sonst mischen neue Ergebnisse alte und neue Bedingungen. Eine Zeile. |
| Unterschiede zwischen den Controller-Pfaden | benennen | Keine Aussage über Pfade hinweg; je Pfad nur der Gewinn gegenüber der festen Kurve. |
| Neuer TCN-Lauf: ein Seed, zwei Änderungen, Verlust auf der Gain-Kurve | benennen, als explorativ | Drei Seeds und die korrigierte Verlustfunktion sind nur nötig, wenn die Thesis eine Ursache behaupten will. |
| Feste V-Vorlage, lineare Terme, tote Kanäle, Chroma | benennen | Grenzen des Proxys. Folge: nur Aussagen über den Proxy, keine über hörbare Qualität. |
| Validation von R1 bis R3 auf 2 Gruppen | benennen | Belastbar ist nur R4. |
| F3-Ergänzungen aus 4.1 | nur bei weitergehender Aussage | Für eine Diagnose reicht der jetzige Stand. |
| Controller im Hörversuch | benennen | Der Versuch prüft keine Netze; kein Satz über ihren hörbaren Nutzen. |
| 7 Paare im Hörversuch | benennen | Die Auswertung ist beschreibend. |

Was das Benennen kostet. Diese Aussagen sind dann nicht möglich:

- welche Architektur die beste ist,
- dass ein Controller hörbar besser mischt als eine feste Kurve,
- warum der neue TCN-Lauf besser abschneidet,
- dass die gelernte Stellenwahl im Hörversuch bestätigt ist.

Was bleibt, wenn Befund 1 hält:

- Die gelernte Metrik findet die echte Fortsetzung häufiger als dieselbe Metrik auf klassischen Merkmalen.
- Sie wählt andere Stellen als die Regel.
- Der Hörversuch beschreibt, wie diese Stellen klingen.
- Die Controller gewinnen je Pfad wenig gegenüber einer festen Kurve; der Proxy belohnt überwiegend eine feste Form.

Eine Grenze hat das Benennen: Es reicht nicht, wo eine Zahl als Ergebnis berichtet wird, die von dem ungeklärten Punkt abhängt. Jede berichtete Zahl braucht deshalb ihre Zeile in der Vergleichsmatrix, und Zeilen, die sich in mehr als einem Faktor unterscheiden, werden nicht miteinander verglichen.

## 9. Offene Entscheidung der Betreuung

Deine Frage aus dem Umsetzungsdokument liegt bei der Betreuung:

> Decken Abschnittsauswahl, Mashup und 1 bis 4 Takte zusammen mit F1 bis F3 die Aufgabenstellung ab, wenn die GUI nicht in der Thesis dargestellt wird und Nachweise zu Korrekturaufwand und Tanznutzen entfallen?

Die Antwort wird hier nachgetragen, sobald sie vorliegt.

Bereits entschieden:

- 23.11.2026: Der Hörversuch bleibt bei 7 Paaren und wird nicht vergrößert. Folgen siehe Befund 3.

## 10. Was nicht geprüft werden konnte

- Alles unter `output/review_jp_20261118/`: Stimuli, Zuordnungen, Checkpoints, Caches, Einzelränge.
- Ob der Code vom 22.11. dem entspricht, der am 19.11. die Stimuli erzeugt hat. Der Commit kam nach dem Lauf **[A]**.
- Die Größe der Effekte in Befund 1 und 2. Beide sind aus Code und deinen Belegen abgeleitet, nicht gemessen und nicht gehört.
- Die GUI und alle Windows-Teile, wie beim ersten Review.
- Die Thesis unter `overleaf/`.

## 11. Optionale Anregung der Betreuung: zwei Beat-Tracker mit Entscheidungsregel

Nicht entscheidend für den Abschluss. Festgehalten für den Fall, dass die Rasteranalyse noch überarbeitet wird. Das Vorgehen stammt aus einem anderen Projekt der Betreuung (Erfahrung mit rund 120 Tracks) und ist unten unverändert im Inhalt wiedergegeben. Ich habe es nicht nachgeprüft.

### Unterschied zum jetzigen Stand in BeatBridge

| | BeatBridge jetzt **[C]** | Vorgehen der Betreuung |
|---|---|---|
| Quelle der Schlagzeiten | librosa (`src/analysis/pre_analysis.py:29`, `:460`) | aufTAKT allein |
| Rolle des zweiten Trackers | aufTAKT liefert die Takte (`:30`) | Beat This! ist nur Zeuge für die „1“ |
| Toleranz beim Zuordnen | 0,2 s (`:18`) | 70 ms |
| Wenn die Analyse unsicher ist | 4/4-Ersatzraster aus Schlägen oder BPM (`:84`, `:92`) | kein Raster, lieber keins als ein falsches |
| Abnahme | Schwelle von 98 % Übereinstimmung (`:34`) | Hörprobe durch einen Menschen |

### Was es hier bringen könnte

- Zwei der vier Rasterausfälle im Hörversuch haben 50 % Übereinstimmung **[A]**. Lückentor und Tempoebene aus Vorwissen (Schritte 1 und 2) zielen genau auf diesen Fall. Zählangaben aus Choreografie-Notizen gibt es hier nicht, aber das Tempofenster des Materials reicht: Bei 145 bis 165 BPM liegen obere und untere Grenze unter Faktor 2 auseinander, die Ebene wäre eindeutig.
- Die jetzige Toleranz von 0,2 s ist bei 160 BPM größer als ein halber Schlag (0,19 s). Ein Schlag des einen Erkenners kann damit dem Offbeat des anderen zugeordnet werden. 70 ms schließen das aus.
- Für Befund 2: Die Schlagzeiten stammen jetzt von librosa und liegen auf dessen Analyseraster von 10,7 ms. Ob aufTAKT feiner auflöst, wäre zu messen. Nach Erfahrung der Betreuung trifft aufTAKT den Schlag zuverlässig.

### Was zu beachten wäre

- Beat This! wäre eine neue Abhängigkeit mit eigenen Modellgewichten.
- Eine geänderte Analyse ändert, welche Paare die Rasterprüfung bestehen. Die Ausschlusskriterien sind vorab festgelegt. Eine Änderung gehört deshalb mit Datum und Anlass ins Protokoll, bevor jemand hört.
- Die Schwellen sind nach Angabe der Betreuung empirisch gesetzt, einige nach Sicht der Daten. Für BeatBridge wären sie auf Entwicklungsmaterial zu prüfen, nicht auf den Studienpaaren.

### Das Vorgehen

Offline-Analyse, je Musikstück einmal.

**Tracker**

- A = zplane aufTAKT 4.5 (kommerzielles SDK; NN mit 3 BLSTM-Schichten und statistischem Dekoder, Modus kAutomatic). Liefert Schläge, Zählzeit im Takt und Taktlänge. A ist die einzige Quelle der Schlagzeiten.
- B = Beat This! (CPJKU, Transformer, Checkpoint final0, ohne DBN). Liefert Schläge und Downbeats. B ist nur Zeuge: Es entscheidet die Phase der „1“ und markiert Stellen zum Nachhören, setzt aber nie Schlagzeiten.
- Beide bekommen dieselbe WAV (44,1 kHz Stereo, vorher geprüft: 0 Samples Versatz zur Referenz). Paar-Toleranz überall 70 ms.

**Ablauf je Stück**

1. Lückentor: Liegt ein A-Intervall außerhalb 0,75 bis 1,33 × Median-Intervall, wechselt A die Tempoebene. Dann gilt der Sonderweg in Schritt 5.
2. Tempoebene (×½, ×1, ×2): Sie wird nicht vom Tracker gewählt, sondern aus Vorwissen. Das sind Zählangaben aus Choreografie-Notizen je Abschnitt (zum Beispiel „8x8“ über 29 s) und ein plausibles Tempofenster je Genre (oben/unten < 2, damit eindeutig). Widerspricht beides oder gibt es keine Aussage, lautet das Ergebnis „nicht bestimmbar“ und es gibt kein Raster. Bei ×2 werden Mittelpunkte zwischen A-Schlägen eingesetzt.
3. „1“ aus A: Anker ist die erste A-„1“ vor dem ersten Takt mit ≠ 4 Schlägen; ab dort stur in Vierern zählen. Die Musik ist durchgehend 4/4; A meldet sonst falsche 3/4-Takte und verschiebt die „1“.
4. Abstimmung über die „1“:
   - Einig: ≥ 95 % der A-„1“ haben einen B-Downbeat. Dann gilt die A-Phase.
   - Uneinig, und B hat in der uneinigen Strecke selbst Lücken (B fällt typischerweise ins halbe Tempo). Dann gilt die A-Phase.
   - Uneinig, B ohne Lücken und ≥ 95 % der B-Downbeats auf einer einzigen A-Zählzeit. Dann wird die B-Phase übernommen.
   - Sonst (Phase wechselt oder ist unklar): keine „1“ schreiben, Warnung mit Zeitpunkt.
5. Sonderweg bei Lückentor („Brücke“): A-Intervalle klassifizieren als
   - „voll“ (≈ 1 Periode, beide Enden mit B-Partner, kein schiefer Takt),
   - „halb + B-Mittelpunkt“,
   - „halb + halb“ (beide halb und die Notizen sagen volles Tempo; markiert) oder
   - „unsicher“.

   Strecken von ≥ 8 verlässlichen Intervallen bleiben. Lücken dazwischen werden nur gefüllt, wenn drei Bedingungen gelten: Die Gerade über je 16 echte Schläge beiderseits hat ≤ 10 ms Median und ≤ 25 ms Maximum Restfehler; der Abstand ist ganzzahlig (± 0,15 Schlag; ein halber Schlag ist ein Offbeat und wird verworfen); die Lücke ist ≤ 64 Schläge lang. Bei einem Sprung zwischen den Seiten wählt B die Seite. Sind < 50 % verlässlich, lautet das Ergebnis „nicht bestimmbar“. Eingefüllte Schläge werden im Ergebnis gekennzeichnet.

**Ausgabe**

Schlagzeiten (von A), Index der ersten „1“, Quelle der Phase, Zeugen-Anteile (Schlag- und „1“-Übereinstimmung A↔B) und eine Liste der uneinigen Stellen. Die Anteile sind nur Information, nie ein Urteil: Abgenommen wird erst nach einer Hörprobe (Klick und Akzent auf der „1“) durch einen Menschen.

**Erfahrung (rund 120 Tracks)**

A trifft den Schlag zuverlässig. Fehler sind fast immer die „1“ (Halbtakt-Versatz, falsche 3/4-Takte) oder die Tempoebene. B allein irrt oft ins halbe Tempo; das sieht man an seinen Lücken. Bisher gab es bei den gehörten Tracks keinen Fall „beide einig und falsch“. Die Schwellen sind empirisch gesetzt, einige nach Sicht der Daten.

## 12. Design des Hörversuchs als lokale Web-Anwendung

Für den Hörversuch entsteht eine kleine lokale Web-Anwendung. Sie ist noch nicht committet. Der Player im Repository (`src/evaluation/p11_player.html`) ist nach Auskunft der Betreuung ein anderer Stand und wird hier nicht bewertet. Dieser Abschnitt beschreibt, was die neue Anwendung leisten muss, damit der Versuch als Experiment trägt.

Rahmen: 7 Songpaare, 7 Clips pro Paar, rund 15 Minuten reine Hörzeit pro Person. Nichts in diesem Abschnitt verlängert die Sitzung. Es ist ein Vorschlag; was davon gilt, steht am Ende im Protokoll Version 2.

### 12.1 Grundaufbau

- Jede Person bewertet alle 7 Songpaare. Pro Paar gibt es eine Seite mit 7 Clips, jeder Clip bekommt einen Wert von 0 bis 100 und darf beliebig oft gehört werden.
- Die Bedingungen bleiben wie im Protokoll: drei Übergangsstellen (gelernte Metrik, Regel, Zufall), je zwei Kurven (Equal Power, direkt optimiert), dazu ein harter Schnitt.
- Alle Clips eines Paars stehen nebeneinander. Der direkte Vergleich macht kleine Unterschiede hörbar und hält die Skala stabil.
- Vor dem ersten Paar kommt eine Übungsseite mit Entwicklungsmaterial, die nicht gewertet wird. Dort wird die Lautstärke eingestellt und danach nicht mehr verändert.

### 12.2 Randomisierung

| Ebene | Regel | Zweck |
|---|---|---|
| Reihenfolge der Songpaare | pro Person verschieden, als lateinisches Quadrat (7 × 7), Zeilen der Reihe nach vergeben | jedes Paar kommt gleich oft früh und spät; fängt Ermüdung und Eingewöhnung ab |
| Position der Clips auf der Seite | pro Person und Paar zufällig, mit neutralen Bezeichnungen | die Position verrät nichts über die Bedingung |
| Stelle des harten Schnitts | pro Paar drei harte Schnitte rendern, jede Person hört einen; Zuweisung rotierend über Personen und Paare | keine Stelle ist häufiger zu hören als die anderen |
| Zufalls-Stelle (optional) | pro Paar zwei oder drei Zufalls-Stellen rendern und über die Personen verteilen | der Vergleich mit dem Zufall hängt nicht an sieben einzelnen Ziehungen |

Die Anwendung zieht alles aus einem geheimen Startwert, den nur die Versuchsleitung kennt. Die Zuordnung von neutralem Code zu Bedingung liegt in einer Schlüsseldatei, die der Browser nie bekommt. Die tatsächlich gezeigte Reihenfolge wird mit den Rohdaten gespeichert, in neutralen Codes.

### 12.3 Verblindung

- Hörende erfahren nur die Aufgabe („bewerte die musikalische Qualität des Übergangs“), nichts über die Verfahren und nichts über die Zahl der Bedingungen. Aufgeklärt wird nach der Abgabe.
- Die Oberfläche zeigt keine Wellenform, keine sprechenden Dateinamen und bietet keinen Download. Alle Clips eines Paars sind gleich lang.
- Die Versuchsleitung weist die Bedingungen nicht von Hand zu; das macht die Anwendung. Die Anleitung ist schriftlich und für alle gleich. Während der Sitzung wird nichts kommentiert.
- Wer das Design oder das Repository kennt, bewertet nicht. Das schließt Autor und Betreuung aus.

### 12.4 Störgrößen und Gegenmaßnahmen

| Störgröße | Maßnahme |
|---|---|
| Lautheit | wie bisher angleichen (−23 LUFS, gleiche Cliplänge) |
| Tempo-Angleichung | derselbe Verarbeitungsweg für alle sieben Clips eines Paars, auch für den harten Schnitt (Befund 2) |
| Erwartung der Hörenden | Verblindung nach 12.3 |
| Einfluss der Versuchsleitung | schriftliche Anleitung, kein Kommentar |
| Voreinstellung des Reglers | der Regler startet ohne Wert; eine Bewertung zählt erst nach einer Eingabe |
| Unaufmerksamkeit | „Weiter“ erst, wenn jeder Clip der Seite einmal vollständig gelaufen und bewertet ist |
| Unterschiedliche Nutzung der Skala | beschriftete Skala in fünf gleich breiten Bereichen (schlecht, mäßig, ordentlich, gut, ausgezeichnet, wie in ITU-R BS.1534); ausgewertet werden Unterschiede innerhalb einer Person |
| Wiedergabe | ein Hörplatz, ein Kopfhörer, verlustfreies Audio ohne Pegelbearbeitung im Browser |
| Reihenfolge und Ermüdung | Randomisierung nach 12.2 |

### 12.5 Was die Anwendung mitschreibt

- Bewertung je Clip, Abspielzahl je Clip, Zeit je Seite und jede Änderung nach einem Schritt zurück.
- Zeitstempel, Sitzungskennung, Version der Anwendung und Prüfsummen der gezeigten Clips.
- Die Rohdaten liegen als fortlaufende Datei bei der Anwendung, nicht nur im Browser. Nach dem Abschluss einer Sitzung lässt sie keine Änderung mehr zu.

### 12.6 Was sich nicht beheben lässt

- **Stelle und Inhalt hängen zusammen.** Eine andere Übergangsstelle bedeutet andere Musik davor und danach. Wer den Drop lieber mag als das Intro, bewertet das mit. Die Anleitung kann darauf hinweisen; trennen lässt es sich nicht. Das gehört als Einschränkung in die Thesis.
- **Der harte Schnitt ist kein sicherer Tiefpunkt.** Ein Schnitt auf der Eins kann in Tanzmusik gut klingen. Er dient deshalb nicht dazu, Personen auszuschließen, und wird getrennt beschrieben. So steht es auch in deinem Protokoll (`docs/EVALUATION_PROTOCOL.md:74`).
- **7 Paare.** Die Auswertung bleibt beschreibend (Befund 3).

### 12.7 Zuverlässigkeit ohne Mehrzeit

Die beiden Kurven an derselben Stelle klingen fast gleich (im Mittel rund 0,7 dB Unterschied **[B]**). Der Abstand ihrer Bewertungen je Person zeigt deshalb auch, wie genau jemand bewertet. Er ist zugleich der Kurveneffekt aus H2 und H3; er wird nur beschrieben, und niemand wird deswegen ausgeschlossen.

### 12.8 Ablauf

1. Probelauf mit einer Person an Entwicklungsmaterial, nicht gewertet. Dauer messen.
2. Auswertungsskript an Kunstdaten mit bekanntem Effekt testen und committen, bevor der Schlüssel geöffnet wird.
3. Vor jeder Sitzung kurze Angaben erheben: Erfahrung mit Musik, DJing und Tanz in je drei Stufen, bekannte Hörprobleme. Sie dienen nur der Beschreibung.
4. Sitzungen durchführen. Rohdaten mit Prüfsumme sichern, dann erst entblinden.
5. Personenzahl: mindestens 3 nach Protokoll, besser 6 bis 9. Ein Vielfaches von 3 lässt die Rotation des harten Schnitts aufgehen.

### 12.9 Was ins Protokoll Version 2 gehört

- Rotation des harten Schnitts, lateinisches Quadrat, Skalenbeschriftung und, falls gewählt, mehrere Zufalls-Stellen.
- Keine Ausschlüsse wegen Punktwerten, wie bisher.
- Die beschreibende Auswertung mit 7 Paaren.
- Hören Personen verschiedene harte Schnitte oder Zufalls-Stellen, mittelt die Auswertung je Paar über die Personen. Die sechs gekreuzten Zellen je Person bleiben vollständig.
