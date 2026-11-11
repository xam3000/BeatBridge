# BeatBridge GUI-Spezifikation

_Konzeptversion 1, beschlossen am 2026-09-10. Diese Spezifikation beschreibt
das implementierbare Zielbild; sie ist noch kein Nachweis einer fertigen GUI._

Visuelle Referenz:
[`gui-mockups/beatbridge-daw-data-concept-v1.png`](./gui-mockups/beatbridge-daw-data-concept-v1.png)

## 1. Zweck und Produktgrenze

Die BeatBridge-GUI ist eine Interaktions- und Erklaerschicht fuer die vorhandene
Analyse-, Kandidaten-, Ranking- und Rendering-Pipeline. Sie hilft Nutzenden,

1. beliebig viele Tracks zu importieren und Songabschnitte zu einer
   Mashup-Sequenz anzuordnen,
2. je zwei benachbarte Abschnitte als Quelle A und Ziel B zu bearbeiten,
3. zulaessige Uebergangskandidaten zu erzeugen oder zu laden,
4. Kandidaten und Renderverfahren vergleichend anzuhoeren,
5. die wichtigsten Gruende fuer ein Ranking nachzuvollziehen und
6. jeden Paaruebergang zu uebernehmen und die gesamte Sequenz zu exportieren.

Die GUI ist ausdruecklich keine vollstaendige DAW. Nicht Teil des ersten
Umfangs sind freie Mehrspurproduktion, Plug-in-Hosting, Piano-Roll,
Sample-Editing, komplexe Automation, Recording oder ein grosser Mixer.

## 2. Verbindliche Gestaltungsprinzipien

- **Musik zuerst:** Timeline, Cuepoints, Wiedergabe und Variantenvergleich
  haben visuell Vorrang vor Forschungs- und Provenienzdetails.
- **Eine Zeitautoritaet:** Die Position des Audio-Transportes ist die einzige
  veraenderliche Zeitautoritaet. Playhead, Charts und Zeittext sind nur
  Projektionen dieses Zustands.
- **Backend-Artefakte sind die Datenautoritaet:** Kandidaten, Scores,
  Rendergrenzen, Fehler und Provenienz werden aus den versionierten
  BeatBridge-Manifests gelesen. Die GUI berechnet keine konkurrierenden
  fachlichen Werte.
- **Keine erfundenen Werte:** Fehlt eine Metrik, zeigt die GUI `Nicht
  verfuegbar` und nach Moeglichkeit den Grund. Ein fehlender Wert wird nie als
  Null interpretiert.
- **Harte und weiche Kriterien bleiben unterscheidbar:** Harte Constraints
  koennen Kandidaten ausschliessen. Weiche Kriterien beeinflussen nur Ranking
  oder Empfehlung.
- **Automatik bleibt korrigierbar:** Nutzende koennen Cuepoints, Laenge und
  Methode waehlen sowie andere Kandidaten anhoeren. Die Empfehlung ist kein
  Zwang.
- **Keine stillen Guards:** Eine nicht moegliche Aktion erklaert konkret,
  welche Analyse, Auswahl oder Datei fehlt.
- **Originale bleiben unveraendert:** Importierte Audiodateien werden nur
  gelesen. Vorschauen, Entscheidungen und Exporte sind neue Artefakte.
- **Wissenschaftliche Ehrlichkeit:** Modellscore, technische Metrik und
  menschliches Urteil werden sprachlich und visuell nicht gleichgesetzt.

## 3. Primaerer Nutzerworkflow

```text
Tracks importieren oder vorhandenen Batch oeffnen
  -> mehrere Songabschnitte in der Mashup-Sequenz anordnen
  -> Analysezustand aller verwendeten Tracks pruefen
  -> eine Kante zwischen zwei benachbarten Abschnitten auswaehlen
  -> dieses Paar als Track A und Track B im Paar-Editor oeffnen
  -> Abschnitt/Cuepoints und Constraints setzen
  -> Kandidaten erzeugen und ranken
  -> Top-Varianten rendern
  -> Varianten synchron anhoeren und erklaerende Daten ansehen
  -> Variante uebernehmen oder Auswahl korrigieren
  -> fuer weitere benachbarte Abschnitte wiederholen
  -> gesamte Mashup-Sequenz pruefen und exportieren
```

Ein Projekt darf **beliebig viele Tracks und Abschnittsinstanzen** enthalten.
Der Paar-Editor bearbeitet gleichzeitig immer genau **einen gerichteten
Uebergang A -> B** zwischen zwei benachbarten Abschnittsinstanzen. Bei einer
Sequenz `A -> B -> C -> D` existieren deshalb drei unabhaengige Uebergangskanten:
`A -> B`, `B -> C` und `C -> D`. Ein einzelner Uebergang mischt niemals drei
Tracks gleichzeitig.

Ein Track darf mehrfach in einer Sequenz vorkommen und dabei verschiedene
Abschnitte oder Cuepoints verwenden. Deshalb werden Sequenzeintraege ueber
stabile Abschnittsinstanz-IDs identifiziert und nicht allein ueber Trackname
oder Audio-SHA.

## 4. Fensteraufbau

Zielgroesse ist ein Desktopfenster ab 1440 x 900 Pixeln. Unter 1280 Pixeln
Breite darf der rechte Inspector eingeklappt werden; die Timeline darf nicht
unter 720 Pixel nutzbare Breite fallen.

| Bereich | Lage | Richtwert | Aufgabe |
|---|---|---:|---|
| Kopf- und Transportleiste | oben | 56-64 px | Projekt, Transport, Zeit, Audiozustand, Export |
| Bibliothek | links | 240-280 px | Tracks importieren, suchen und A/B zuweisen |
| Mashup-Sequenz | unter Kopfzeile | 72-104 px | mehrere Abschnitte anordnen und Paaruebergaenge waehlen |
| Paar-Timeline | Mitte oben | flexibel, mindestens 360 px hoch | Waveforms, Taktgrid, Cuepoints, Uebergang |
| Uebergangs-Inspector | rechts | 280-320 px | Constraints, Methode und konkrete Auswahl |
| Analyse-/Vergleichsbereich | Mitte unten | 280-360 px | Erklaerung, Varianten, A/B-Vergleich |
| Statusleiste | unten | 24-32 px | Arbeitsstatus, Warnungen, Provenienz-Kurzinfo |

Die Paar-Timeline ist im Bearbeitungsmodus die dominante Flaeche. Die
Mashup-Sequenz bleibt als kompakter Kontext sichtbar und markiert den aktuell
bearbeiteten Paaruebergang. Bibliothek, Inspector und Analysebereich sind
ein-/ausklappbar; Transportleiste und Sequenzkontext nicht.

## 5. Komponenten

### 5.1 Kopf- und Transportleiste

Pflichtelemente:

- BeatBridge-Name und aktueller Projekt-/Sitzungsname,
- Zurueck/Wiederholen nur fuer GUI-Auswahlaktionen,
- zum Anfang der Vorschau springen,
- Wiedergabe/Pause,
- optional Transition-Loop,
- aktuelle Zeit und Gesamtdauer der geladenen Vorschau,
- Takt-/Beat-Snap, Zoom und Fit-to-Transition,
- Audioausgabe mit erkennbarem Fehlerzustand,
- Export-Aktion.

Die Leertaste steuert Wiedergabe/Pause. Wenn ein Texteingabefeld fokussiert
ist, darf sie keine Wiedergabe ausloesen.

### 5.2 Trackbibliothek

Jeder Trackeintrag zeigt, sofern vorhanden:

- Dateiname oder Anzeigename,
- Dauer,
- BPM,
- Tonart,
- Analysezustand,
- optional Artwork,
- Anzahl und Positionen der Verwendungen in der Mashup-Sequenz,
- fuer das aktuell gewaehlte Paar optional die temporaere Rolle `A` oder `B`.

Analysezustaende sind mindestens `nicht analysiert`, `Analyse laeuft`,
`analysiert`, `Warnung` und `fehlgeschlagen`. Warnung und Fehler oeffnen eine
Detailansicht mit maschinenlesbarem Code und nutzerlesbarer Erklaerung.

Interaktionen:

- Import ueber Dateidialog oder Drag-and-drop,
- Klick selektiert einen Track,
- Aktion `Zur Sequenz hinzufuegen`, optional mit Abschnittsauswahl,
- Drag-and-drop eines Tracks an eine Position der Mashup-Sequenz,
- `Als A verwenden` und `Als B verwenden` sind nur im freien Paarvergleich
  verfuegbar; in einer Sequenz ergeben sich A und B aus den benachbarten
  Abschnittsinstanzen,
- das Oeffnen eines anderen Paares fragt nur dann nach, wenn eine ungespeicherte
  Uebergangsauswahl verloren ginge,
- Tauschen von A und B ist eine sichtbare Aktion; es ist keine rein visuelle
  Spiegelung, sondern aendert im freien Vergleich die Richtung. Innerhalb der
  Sequenz wird stattdessen die Reihenfolge der Abschnittsinstanzen geaendert.

### 5.3 Mashup-Sequenz

Die Sequenzleiste stellt alle verwendeten Abschnittsinstanzen horizontal dar.
Sie ist keine dritte Audiospur im Paar-Editor, sondern die uebergeordnete
Struktur des Projekts.

```text
[Abschnitt 1: Track A] --(Uebergang 1)--> [Abschnitt 2: Track B]
                       --(Uebergang 2)--> [Abschnitt 3: Track C]
                       --(Uebergang 3)--> [Abschnitt 4: Track D]
```

Visuell wird dies als lineare Kette von Abschnittskarten mit jeweils einer
anklickbaren Uebergangskante zwischen zwei Karten umgesetzt. Eine korrekte
lineare Darstellung lautet beispielsweise:

```text
[Track A / Abschnitt 1] -> [Track B / Abschnitt 2] -> [Track C / Abschnitt 3]
           Uebergang 1              Uebergang 2
```

Eine Abschnittskarte zeigt Trackname, Abschnittsname oder Zeitbereich, Dauer
und Analysezustand. Eine Uebergangskante zeigt ihren Status:

- `offen`: noch keine Variante uebernommen,
- `in Bearbeitung`: aktuell im Paar-Editor,
- `bereit`: gueltige Variante uebernommen,
- `veraltet`: Track, Abschnitt oder Constraint wurde danach geaendert,
- `Warnung` oder `fehlgeschlagen`.

Interaktionen:

- Tracks oder bestehende Abschnitte an einer beliebigen Position einfuegen,
- Abschnittsinstanzen per Drag-and-drop umordnen,
- Abschnitt duplizieren oder aus der Sequenz entfernen,
- Kante anklicken, um genau deren linke Instanz als A und rechte Instanz als B
  im Paar-Editor zu laden,
- zur vorherigen oder naechsten offenen Kante springen.

Umordnen, Einfuegen oder Entfernen kann Paarbeziehungen aendern. Bereits
gerenderte Uebergaenge werden dabei nicht geloescht, aber von der aktiven
Sequenz geloest oder als veraltet markiert. Die GUI darf niemals eine alte
Variante stillschweigend einer neuen Kante zuordnen.

### 5.4 Paar-Timeline

Die Timeline enthaelt genau zwei synchron dargestellte Spuren:

- `A - <Trackname>` als ausgehender Track,
- `B - <Trackname>` als eingehender Track.

Pflichtdarstellung:

- Waveform je Track,
- gemeinsame Zeit- und Taktachse,
- Beats als feine und Downbeats/Taktgrenzen als staerkere Linien,
- Cue-Marker `A OUT` und `B IN`,
- farblich hervorgehobenes Uebergangsfenster,
- Playhead,
- resultierende Gain-/Control-Kurven, wenn sie fuer die Variante vorliegen,
- Warnhinweis bei approximativem oder unsicherem Grid.

Die gemeinsame Bildschirmachse bildet die bereits ausgerichtete
Uebergangsvorschau ab. Absolute Quellzeiten beider Tracks stehen zusaetzlich
in Cuepoint-Tooltips und im Inspector; sie duerfen nicht aus der visuellen
Ueberlagerung zurueckgerechnet werden.

Cue-Marker rasten standardmaessig auf gueltige Downbeats. Freies
Sample-Dragging ist nicht Teil des MVP. Das Verschieben eines Markers waehlt
einen vorhandenen Kandidaten oder fordert eine neue Kandidatengenerierung an;
es veraendert nie heimlich ein bestehendes Kandidatenmanifest.

In der nativen Transition-Builder-GUI gilt eine direkte Mausgeste getrennt
davon: Ein einfacher Klick auf eine Waveform setzt einen manuellen Cuepoint;
Ziehen markiert einen Suchbereich. Die Bereiche werden je gerichteter
Sequenzkante gespeichert. „Beste Cuepoints in Bereichen suchen“ begrenzt die
bar-ausgerichtete Kandidatengenerierung auf die Downbeats innerhalb beider
Bereiche und bewertet die Kandidaten mit `feature_baseline_v3`. Bei mehr als
400 Treffern wird die deterministische Kandidatenfolge gleichmäßig abgetastet,
um Volltrackauswahlen speicherschonend zu bewerten. Der Kandidat mit dem
höchsten Score setzt die beiden Cuepoints des aktiven Übergangs und wird vom
anschließenden Rendern verwendet. Der gelernte Cue-Ranker bleibt bis zu einer
Evaluation mit realen Tracks von der automatischen Auswahl ausgeschlossen;
die Feature-Baseline ist eine nachvollziehbare Heuristik und keine
Hörqualitätsgarantie. Die UI erlaubt approximative/Fallback-Grids, damit die
Suche auf importierten Audiodateien unmittelbar nutzbar ist.

### 5.5 Uebergangs-Inspector

Der Inspector trennt drei Gruppen.

**Auswahl**

- Source-Cuepoint und Target-Cuepoint mit Takt- und absoluter Zeitangabe,
- Uebergangslaenge in Takten,
- Zieltempo beziehungsweise Tempoautoritaet,
- Render-/Control-Methode.

**Harte Constraints**

- maximal erlaubte relative Tempoabweichung,
- Grid-Policy,
- zulaessige Uebergangslaengen,
- erforderlicher vollstaendiger Pre-/Postroll,
- optional Vocal-Overlap-Ausschluss, sobald ein entsprechender harter
  Backendvertrag existiert.

**Weiche Praeferenzen**

- Energieverlauf,
- Harmoniegewicht,
- Vocal-Praeferenz,
- bevorzugte Strukturkombination, sobald Segmentdaten belastbar vorliegen.

Auswahllisten werden aus Backend-Faehigkeiten gespeist und nicht im Frontend
fest verdrahtet. Der aktuell validierte Candidate-v2-Pfad bietet 2, 4, 6 und
8 Takte. 1- und 3-Takt-Faelle bleiben verborgen oder klar als nicht
unterstuetzt markiert, bis ein entsprechender Vertrag implementiert ist.

### 5.6 Analysebereich: `Warum dieser Uebergang?`

Der Bereich besitzt drei Tabs.

#### Analyse

Zeitbezogene Daten teilen sich die x-Achse der Transition:

- Energie/RMS von A und B,
- Vocal-Aktivitaet von A und B,
- harmonischer Verlauf oder Tonartkontext,
- optional Beat-/Onset-Stabilitaet,
- sichtbar markierter Beginn und Ende des Uebergangs.

Daneben steht eine Scoreaufschluesselung. Die UI zeigt nur tatsaechlich
gelieferte Komponenten. Fuer `rendered_transition_baseline_v1` sind dies
insbesondere Energieform, Grenzglaette, harmonische Kontinuitaet und
rhythmische Stabilitaet. Vocal- und Stretch-Werte werden nur gezeigt, wenn das
gewaehlte Artefakt sie explizit liefert.

Jeder Wert traegt einen Typ:

- `Technische Messung`,
- `Feature-Baseline`,
- `Modellscore`,
- `menschliche Bewertung`.

Tooltips erklaeren Einheit, Richtung (`hoeher ist besser` oder `niedriger ist
besser`) und Datenquelle. Scores unterschiedlicher Methoden duerfen nicht
ohne dokumentierte Normalisierung auf derselben Skala als gleichartig
dargestellt werden.

#### Alternativen

Mindestens die drei bestplatzierten erfolgreich gerenderten Varianten werden
als Karten dargestellt. Eine Karte enthaelt:

- Rang und Score samt Scoretyp,
- Candidate-ID in der Detailansicht,
- A-/B-Cuepoints,
- Uebergangslaenge,
- Methode/Renderer,
- Zieltempo und Stretch-Anforderung,
- Warnungen oder Partial-Status,
- Aktion `Anhoeren`,
- Aktion `Auswaehlen`.

Ein Kandidat und eine gerenderte Variante sind unterschiedliche Objekte. Hat
ein Kandidat mehrere Renderer, erscheinen diese entweder als Untervarianten
derselben Karte oder als getrennte Vergleichskarten mit gemeinsamer
Candidate-ID.

#### Details

Die Detailansicht macht auditierbar:

- verwendete Manifest- und Protokollversionen,
- Analyse-/Grid-Provenienz,
- Rankingmethode,
- Renderer/Modell und Checkpointbezug,
- Audio- und Artefaktpfade,
- dokumentierte Rejections, Backfills und Failures.

Diese Informationen sind fuer Forschung und Diagnose wichtig, bleiben aber
aus dem primaeren Musikworkflow herausgehalten.

### 5.7 Baseline-/Modellvergleich

Der Vergleichsschalter hat die Zustaende `Baseline` und `Modell`. Er darf nur
Varianten vergleichen, die fachlich vergleichbar sind, insbesondere dasselbe
Songpaar und denselben vorgesehenen Vergleichskontext.

Beim Umschalten bleiben erhalten:

- Playheadposition relativ zum Uebergangsfenster,
- Loopzustand,
- Lautstaerke,
- Zoom und sichtbare Zeitspanne.

Beim Umschalten wechseln:

- Audiodatei,
- Control-Kurven,
- methodenspezifische Scores und Provenienz.

Die UI bezeichnet einen Modellscore nicht als objektive Qualitaet. Fuer
geblendete Studien kann statt Methodenname nur `A`/`B`/`C`/`D` erscheinen;
die Entblindung darf nicht aus einem geschuetzten Antwortschluessel in den
normalen Reviewzustand durchsickern.

### 5.8 Primaere Aktionen

- `Varianten vergleichen` oeffnet den Vergleichsmodus und startet nicht
  automatisch die Wiedergabe.
- `Uebergang uebernehmen` speichert eine Auswahlreferenz auf Candidate und
  gerenderte Variante an der aktuell gewaehlten Sequenzkante; die Quelldateien
  und Manifeste bleiben unveraendert.
- `Export` ist im Paar-MVP ein Export der gewaehlten Vorschau oder eines neu
  gerenderten vollstaendigen Uebergangs. Ein kompletter Mashup-Export ist nur
  moeglich, wenn jede benoetigte Kante der Sequenz eine gueltige uebernommene
  Variante besitzt.

## 6. Zustandsmodell

| Zustand | Sichtbares Verhalten | Erlaubte Hauptaktion |
|---|---|---|
| `empty` | Importhinweis, leere Timeline | Tracks importieren/Batch oeffnen |
| `tracks_loaded` | Metadaten, Analyse noch offen | Analyse starten |
| `sequence_editing` | mehrere Abschnittsinstanzen, offene Kanten sichtbar | Reihenfolge/Abschnitte bearbeiten |
| `analyzing` | Fortschritt je Track, abbrechbar | Status ansehen |
| `pair_ready` | A/B-Timeline und gueltige Gridinformation | Kandidaten erzeugen |
| `generating_candidates` | Fortschritt und Filterzaehler | Status ansehen/abbrechen |
| `candidates_ready` | Rangliste; noch nicht jede Variante hoerbar | Varianten rendern |
| `rendering` | Fortschritt pro Variante; Teilfehler sichtbar | fertige Varianten anhoeren |
| `review_ready` | Audiovergleich und Analysen aktiv | Variante auswaehlen |
| `selection_dirty` | lokale Auswahl noch nicht uebernommen | uebernehmen/verwerfen |
| `selection_accepted` | gewaehlte Variante markiert | exportieren/naechstes Paar |
| `sequence_ready` | jede benoetigte Kante besitzt eine gueltige Auswahl | Mashup pruefen/exportieren |
| `exporting` | Fortschritt und Zielpfad | Status ansehen |
| `partial_failure` | nutzbare Ergebnisse plus Fehlerliste | weiterarbeiten/Details |
| `blocked` | konkrete fehlende Voraussetzung | angebotene Behebung |

Langlaufende Schritte liefern Fortschritt und sind abbrechbar. Ein Abbruch
darf fertige, verifizierte Artefakte nicht entfernen. Nach Neustart darf die
GUI vorhandene atomisch abgeschlossene Manifeste wieder oeffnen; temporaere
Dateien gelten nicht als fertige Ergebnisse.

## 7. Datenbindung an vorhandene BeatBridge-Artefakte

| GUI-Inhalt | Primaere Quelle |
|---|---|
| Trackpfade und Audio-SHAs | Candidate-/Batchmanifest |
| BPM, Beat-, Downbeat- und Taktpositionen | Analyseartefakt und `source_grid`/`target_grid` |
| Candidate-ID, Cuepoints, Laenge | `candidate_generation.candidates` |
| harte Ablehnungen | `candidate_generation.rejections` |
| Feature-Rang und Komponenten | `candidate_ranking` |
| Learned-Cue-Auswahl | `cue_ranking` und `selection_candidate_ids` |
| gerenderte Variante und WAV | `rendered_variants` |
| Rendergrenzen | `transition_start_sample`, `transition_end_sample` |
| Render-Score und Komponenten | `rendered_transition_ranking` oder Sidecar |
| Renderer-/Tempo-Backend | gerenderte Variante und Rendering-Provenienz |
| Fehler/Backfill | `failures`, Preflight- und Backfillfelder |
| menschliche Bewertungen | Ratings-Sidecar nach `RATINGS_PROTOCOL.md` |

Die Implementierung benoetigt eine Adapter-/View-Model-Schicht zwischen
versionierten Manifests und UI. Diese Schicht muss alte additive Formate lesen
koennen und Felder mit `vorhanden`, `nicht vorhanden` oder `ungueltig`
klassifizieren. UI-Komponenten lesen nicht direkt und unabhaengig dieselbe
JSON-Datei.

## 8. Minimaler View-Model-Vertrag

Die spaetere technische Implementierung soll mindestens folgende fachliche
Objekte bereitstellen; konkrete Programmiersprache und Klassenstruktur sind
nicht Teil dieser Spezifikation.

| Objekt | Erforderlicher Inhalt |
|---|---|
| `ProjectView` | Projektname, beliebig viele Tracks, Mashup-Sequenz, aktives Paar |
| `TrackView` | stabile ID/SHA, Anzeigename, Pfad, Dauer, BPM, Tonart, Analysestatus |
| `SectionView` | stabile Instanz-ID, Track-ID, Abschnittsgrenzen, Anzeigename, Position |
| `SequenceView` | geordnete Section-IDs und die daraus entstehenden Transition-Edges |
| `TransitionEdgeView` | stabile Kanten-ID, linke/rechte Section-ID, Status, Auswahlreferenz |
| `PairView` | aktive Kanten-ID, Source-/Target-Section, Gridstatus, Constraints, Arbeitsstatus |
| `CandidateView` | Candidate-ID, Cuepoints, Taktlaenge, Tempo, Rankingaussagen, Rejections |
| `VariantView` | stabile Varianten-ID, Candidate-ID, Methode, WAV, Rendergrenzen, Scores, Fehler |
| `TimeSeriesView` | Semantik, Einheit, Zeitbasis, Werte, Missingness, Quelle |
| `SelectionView` | gewaehlte Variante, Auswahlzeitpunkt, optionale Nutzernotiz |
| `CapabilityView` | vom Backend unterstuetzte Laengen, Methoden und optionale Datenfelder |

Stabile IDs duerfen nicht aus Listenpositionen oder sichtbaren Dateinamen
gebildet werden. Candidate-ID, Audio-SHA und manifestierte Variantenbeziehung
sind massgeblich.

## 9. Wiedergabe und Synchronisation

- Es spielt hoechstens eine Variante gleichzeitig.
- Variantenwechsel stoppt oder wechselt samplegenau auf denselben relativen
  Zeitpunkt; welche Strategie verwendet wird, muss einheitlich sein.
- Loopgrenzen entsprechen standardmaessig den manifestierten Rendergrenzen,
  koennen aber auf die ganze Vorschau erweitert werden.
- Die Darstellung unterscheidet Preview-Kontext und eigentliches
  Uebergangsfenster.
- Lautstaerke ist ein Abhoerparameter und veraendert weder WAV noch Score.
- Peak-Normalisierung oder Lautheitsunterschiede werden aus den Artefakten
  uebernommen, nicht spontan im Player versteckt korrigiert.
- Eine nicht ladbare Audiodatei markiert nur die betroffene Variante als
  fehlerhaft; andere Varianten bleiben benutzbar.

## 10. Fehler- und Warnkonzept

Fehler werden auf der kleinsten sinnvollen Ebene gezeigt:

- Trackfehler am Bibliothekseintrag,
- Grid-/Cueproblem an der betroffenen Spur,
- Kandidaten-Rejection im Alternativen-/Detailtab,
- Renderfehler an der Variantenkarte,
- Audioausgabefehler in der Transportleiste,
- Exportfehler am Exportvorgang.

Jede Meldung enthaelt:

1. was nicht funktioniert hat,
2. ob andere Ergebnisse weiter nutzbar sind,
3. eine konkrete naechste Aktion und
4. in den Details Fehlercode, Schritt und Artefaktbezug.

Normale Policy-Ausschluesse sind keine roten Systemfehler. Unsichere oder
approximative Grids sind gelbe Warnungen, sofern der gewaehlte Backendvertrag
ihre Verwendung ueberhaupt erlaubt.

## 11. Speicherung und Provenienz

Die GUI speichert Projekte/Entscheidungen additiv in einem eigenen,
versionierten Projektformat. Vor dessen Implementierung ist ein eigener
Protokollentscheid erforderlich. Mindestens zu speichern sind:

- Referenzen und SHAs der Audioquellen,
- Pfade und SHAs der gelesenen Manifeste,
- geordnete Abschnittsinstanzen mit stabilen IDs und Trackreferenzen,
- fuer jedes benachbarte Instanzpaar eine gerichtete Uebergangskante,
- aktives gerichtetes Paar,
- Constraints je Uebergangskante,
- ausgewaehlte Candidate- und Varianten-ID je Uebergangskante,
- UI-relevante Nutzernotizen,
- Zeitstempel und Formatversion.

Nicht in das Projektformat dupliziert werden grosse Audioarrays,
Analysefeatures oder Modellgewichte. Pfade allein reichen fuer auditierbare
Auswahl nicht aus; bei Wiedereroeffnung werden die gespeicherten Hashbeziehungen
geprueft.

## 12. Visuelles System

- Hintergrund: dunkles Anthrazit statt reines Schwarz.
- Track A: Cyan/Tuerkis.
- Track B: Koralle/Magenta.
- Uebergang/Selektion: Violett als kontrollierte Mischung beider Trackfarben.
- Erfolg: Gruen ausschliesslich fuer bestaetigten Zustand.
- Warnung: Amber; Fehler: Rot.
- Text und Status duerfen nie nur ueber Farbe vermittelt werden.
- Mindestschriftgroesse fuer Bedieninhalte: 13 px bei 100-%-Skalierung.
- Zielkontrast: WCAG 2.1 AA fuer normalen Text und Bedienelemente.
- Fokusrahmen sind immer sichtbar; alle Primaeraktionen sind per Tastatur
  erreichbar.
- Animationen sind kurz und abschaltbar; Waveform und Playhead duerfen keine
  dauerhafte GPU-intensive Dekoration enthalten.

Das Bildmockup ist eine Stil- und Hierarchiereferenz. Fantasienamen,
Beispielwerte, Coverbilder und einzelne Beschriftungen darin sind keine
fachliche Datenquelle.

## 13. Tastaturgrundbelegung

| Taste | Aktion |
|---|---|
| `Leertaste` | Wiedergabe/Pause |
| `L` | Transition-Loop an/aus |
| `Pos1` | Beginn der Vorschau |
| `Pfeil links/rechts` | Playhead schrittweise bewegen |
| `Shift` + Pfeil | vorherige/naechste gueltige Taktgrenze |
| `1`, `2`, `3` | Vergleichsvariante fokussieren |
| `Enter` | fokussierte Variante anhoeren/auswaehlen, kontextabhaengig |
| `Ctrl+Z` / `Ctrl+Shift+Z` | lokale Auswahl zurueck/wiederholen |

Vor Implementierung muessen Konflikte mit dem gewaehlt GUI-Framework und
Screenreadern geprueft werden.

## 14. Umsetzungsstufen

### Stufe A: Manueller Paar-Transition-Builder

Ziel ist ein frueh nutzbarer nativer Durchstich in die vorhandene
Analyse-/Render-Pipeline:

- mehrere Audiodateien in eine temporaere Trackbibliothek laden,
- Audiodateien aus dem Windows-Explorer direkt in eine Sequenzkante/Position
  ziehen und Bibliothekseintraege per Drag-and-Drop zur Sequenz hinzufuegen,
- Sequenzabschnitte innerhalb der Sequenz per Drag-and-Drop umsortieren,
- Tracks bei Bedarf analysieren und BPM/Gridstatus anzeigen,
- mehrere Tracks in eine lineare Sequenz aufnehmen und benachbarte gerichtete
  Kanten A→B, B→C usw. einzeln bearbeiten,
- Cuepoints auf den Trackwellenformen setzen oder als Zeit eingeben,
- Uebergangslaenge und vorhandenen Renderer waehlen; abgeschlossene lokale
  Runs unterstuetzter ML-Control-Modelle koennen alternativ zur Baseline
  ausgewaehlt werden,
- eine Vorschau mit der bestehenden Pipeline rendern, abspielen und technisch
  bewerten,
- Ergebnis und Quellen-SHAs als neue Artefakte speichern, ohne Originale zu
  ueberschreiben,
- Cachebasis auswaehlen und Cachetreffer sichtbar melden.

Beim Import wird zuerst ein gueltiger Cacheeintrag gesucht und geladen. Ein
Cache-Miss startet keine implizite Analyse; der Track wird als `Nicht
analysiert` markiert und kann explizit analysiert werden. Die Wellenform bietet
Mausrad-Zoom um die Zeigerposition, horizontales Verschieben per
Shift+Mausrad oder Ziehen mit der mittleren Maustaste und Doppelklick fuer die
Gesamtansicht.

Der aktuelle Durchstich haelt Sequenz und Kantenstatus nur fuer die laufende
Sitzung; er speichert noch kein wiedereroeffnbares Mehrtrackprojekt und erzeugt
keine automatische Kandidatenauswahl. Modellkontrollen sind experimentell und
vier Takte lang; die Render-Metrik bleibt eine technische Bewertung des
gerenderten Audios, keine gelernte oder menschliche Qualitaetsbewertung. Ein
optional manifestbasierter Review-MVP bleibt fuer vorhandene Batchartefakte
verfuegbar. Die native Qt-Oberflaeche folgt der Mockup-Hierarchie, bildet aber
noch nicht alle Mockup-Analysepanels, Alternativenkarten, Audioeinstellungen
oder Exportfunktionen ab.

### Stufe B: Interaktiver Paar-Editor

- beliebig viele Tracks importieren und Analyse anstossen,
- mehrere Abschnittsinstanzen zu einer Sequenz anordnen,
- eine Sequenzkante als aktives A/B-Paar oeffnen,
- Backend-Faehigkeiten und Constraints laden,
- Kandidatengenerierung und Ranking starten,
- Cuepoints auf gueltige Downbeats setzen,
- Top-Varianten rendern,
- Auswahl als neues Projektartefakt speichern.

### Stufe C: Mashup-Assembly

- Sequenzreihenfolge und Abschnittsgrenzen pruefen,
- Status aller gerichteten Paaruebergaenge anzeigen,
- jeden Uebergang einzeln und die gesamte Sequenz am Stueck vorhoeren,
- End-to-End-Render und Export mit vollstaendiger Provenienz.

Fuer `N` Abschnittsinstanzen einer linearen Sequenz erwartet die GUI genau
`N - 1` Paaruebergaenge. Der Export-Preflight blockiert, wenn eine dieser
Kanten offen, veraltet oder fehlgeschlagen ist, und benennt die betroffenen
Kanten konkret.

### Stufe D: Evaluationsmodus

- geblendete Vergleichsstudien,
- Rating- und Fehler-Tags,
- Export gemaess Ratings-/Control-Study-Protokollen,
- keine vorzeitige Entblindung.

## 15. Abnahmekriterien fuer Stufe A

Stufe A gilt erst als umgesetzt, wenn alle folgenden Punkte erfuellt sind:

1. Mindestens drei unterschiedliche Audiodateien lassen sich gleichzeitig
   laden und als Song A/B waehlen.
2. Cuepoints koennen per Wellenformklick und Zeitfeld gesetzt werden;
   Trackwechsel uebernehmen keine alten Cuepoints.
3. Trackanalyse laeuft ausserhalb des UI-Threads und zeigt BPM/Gridstatus oder
   den konkreten Fehler.
4. Der manuelle Render nutzt die ausgewaehlten Tracks, Cuepoints, Taktlaenge
   und Renderer der vorhandenen Pipeline.
5. Das Ergebnis laesst sich abspielen; Rendergrenzen werden in der
   Ergebniswellenform markiert.
6. Render-Metrik, Provenienz und Fehler sind als technische Baseline benannt
   und werden nicht als menschliche Hoerqualitaet dargestellt.
7. Vorschau und Sidecar werden neu geschrieben; Quelldateien bleiben
   unveraendert.
8. Ein manueller Durchklick dokumentiert Reibungspunkte; ein spaeterer
   automatisierter UI-Test ersetzt diesen Durchklick nicht.

Der optionale manifestbasierte Review-Modus besitzt eigene
Abnahmekriterien aus dem urspruenglichen Review-MVP.

## 16. Zusaetzliche Abnahmekriterien fuer Mehrtrack-Projekte

1. Ein Projekt kann mindestens drei unterschiedliche Tracks gleichzeitig
   enthalten und in eine Sequenz einfuegen.
2. Ein Track kann mehrfach als unterschiedliche Abschnittsinstanz verwendet
   werden.
3. Bei drei Abschnittsinstanzen entstehen genau zwei gerichtete
   Uebergangskanten.
4. Der Paar-Editor zeigt trotz Mehrtrack-Projekt immer nur die zwei Spuren der
   ausgewaehlten Kante.
5. Wechsel zwischen Kanten erhaelt die unabhaengigen Constraints und
   Variantenentscheidungen jeder Kante.
6. Umordnen einer Abschnittsinstanz markiert nicht mehr passende
   Uebergangsauswahlen als veraltet und ordnet sie nicht automatisch neu zu.
7. Ein gesamter Mashup-Export ist erst moeglich, wenn alle `N - 1` Kanten eine
   gueltige Auswahl besitzen.
8. Kein einzelner Rendereraufruf und keine Variantenkarte repraesentiert mehr
   als zwei Tracks gleichzeitig.

## 17. Noch zu entscheidende Implementierungsfragen

Die Implementierungsfragen werden vor dem jeweiligen Bauabschnitt datiert
entschieden. Beschlossene Entscheidungen:

- **Native Python-GUI, 2026-10-06:** Die produktive Desktop-Oberflaeche wird
  mit PySide6/Qt Widgets umgesetzt. Das HTML-Mockup bleibt visuelle Referenz,
  ist aber nicht Laufzeitbestandteil der nativen GUI. Ein zuvor angelegter
  pywebview-Launcher war ein Zwischenstand und wurde auf Nutzerwunsch ersetzt.
  Der native Einstieg ist `src.gui_app`; GUI-Abhaengigkeiten bleiben optional.
  Der primaere Einstieg ist der manuelle Paar-Transition-Builder aus Stufe A.
  Ein manifestbasierter Review-MVP bleibt als optionaler Modus erhalten und
  speichert Auswahlen gemaess [`GUI_SELECTION_PROTOCOL.md`](./GUI_SELECTION_PROTOCOL.md).

Weiter offen:

- Packaging als installierbare/distributable Anwendung,
- Audio-Engine und Strategie fuer samplegenauen Variantenwechsel,
- Ort und Versionierung des Mehrtrack-GUI-Projektformats,
- welche Codec-Kombination fuer Wellenform, Wiedergabe und Rendering auf den
  Zielplattformen verbindlich unterstuetzt wird,
- genaue Herkunft der Waveform-Pyramiden fuer schnelles Zoomen,
- ob Tonartdarstellung als Camelot, klassische Tonart oder beides erfolgt,
- welche Scorekomponenten ueber unterschiedliche Methoden hinweg gemeinsam
  skaliert werden duerfen,
- wie 1- und 3-Takt-Uebergaenge nach ihrer Pipelinefreigabe einsortiert werden,
- Barrierefreiheitspruefung des finalen Frameworks,
- Grenzen zwischen Paar-Vorschau und spaeterem Voll-Mashup-Render,
- Semantik ueberlappender oder nichtlinear verzweigter Sequenzen; Version 1
  setzt bewusst eine lineare Reihenfolge voraus.

Diese Entscheidungen muessen vor dem jeweiligen Bauabschnitt datiert und mit
Begruendung in der Projektdokumentation festgehalten werden.
