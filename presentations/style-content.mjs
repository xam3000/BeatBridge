import {slides as original} from './content.mjs';

// Same research evidence and speaker notes; shorter copy in the author's
// established topic-title / bullet-list presentation style.
export const styledSlides=original.map((s,i)=>({...structuredClone(s),originalIndex:i}));
const set=(i,values)=>Object.assign(styledSlides[i],values);
set(1,{title:'Motivation',seconds:60,bullets:[
 'Ausgewählte Songabschnitte für Tanz-Mashups verbinden',
 'Reihenfolge und wichtige Einsätze stehen bereits fest',
 'Übergang soll den Puls und die gewünschte Energie erhalten'
]});
set(2,{title:'Cuepoints und Controller',bullets:[
 'Cuepoints: Wo wird übergeleitet?',
 {text:'Zeitfenster auf Taktgrenzen festlegen',level:1},
 {text:'Tempo, verfügbaren Kontext und Kompatibilität prüfen',level:1},
 'Controller: Wie wird übergeleitet?',
 {text:'Lautstärke, Bass und Vocals während des Übergangs steuern',level:1},
 {text:'Untersuchung für ein fest gewähltes Cuepoint-Paar',level:1}
]});
set(3,{title:'Forschungsfrage',bullets:[
 'Interpretierbare Mixing-Controls ohne Zielkurven lernen',
 'Keine Referenzübergänge für das gewählte Paar voraussetzen',
 'Verwandte Arbeiten',
 {text:'Differenzierbares Mixing mit Referenzmix',level:1},
 {text:'DJTransGAN lernt aus realen DJ-Übergängen',level:1},
 'BeatBridge verwendet ein festes Proxy-Objective als Lernsignal',
 {text:'Selbstüberwachung der Controls, kein Vortraining von Musik-Embeddings',level:1}
]});
set(4,{title:'Methode – Überblick',bullets:[
 'Beat- und Taktraster analysieren, zulässige Cuepoints auswählen',
 'Merkmale und tempoausgerichtete Audiosignale vorbereiten',
 'Controller erzeugt zeitabhängige Mixing-Controls',
 'Renderer wendet die Controls auf die Audiosignale an',
 'Training',
 {text:'Proxy bewertet den Übergang und liefert Gradienten',level:1},
 'Anwendung',
 {text:'Ein Vorwärtsdurchlauf sagt die Controls voraus',level:1}
]});
set(5,{title:'Methode – Eingaben',bullets:[
 'Beat-synchrone Merkmale für beide Tracks',
 {text:'Timing: Beat- und Taktposition',level:1},
 {text:'Energie und Klang: Pegel, Frequenzanteile und Transienten',level:1},
 {text:'Harmonik und geschätzte Gesangsaktivität',level:1},
 '54 Merkmale je Zeitpunkt und 16 globale Paarmerkmale',
 'Fester Pfad mit vier Takten',
 {text:'Zwei Schritte pro Beat ergeben 32 Zeitpunkte je Track',level:1},
 {text:'Fehlende Analysen werden explizit markiert',level:1}
]});
set(6,{title:'Methode – Lernen durch den Renderer',bullets:[
 'Controller sagt Controls voraus',
 'Fester Renderer erzeugt den Übergang',
 'Proxy-Objective bewertet das Ergebnis',
 'Gradienten fließen zum Controller zurück',
 'Gemeinsame Netzgewichte über Beispiele lernen',
 'Keine Zielkurven erforderlich'
]});
set(7,{title:'Methode – Mixing-Controls',bullets:[
 'Getrennte Übergabe von Gesamtmix, Bass und Vocals',
 'Je nach Pfad zusätzliche EQ- und Ducking-Controls',
 'Beschränkte Werte und glatte Verläufe gegen abrupte Änderungen'
]});
set(8,{title:'Methode – Proxy-Objective',bullets:[
 'Energieform',
 {text:'Kontrollierte Senke im Übergang',level:1},
 'Signal und Controls',
 {text:'Stetige Grenzen und wenig Clipping',level:1},
 {text:'Glatte Änderungen der Controls',level:1},
 'Vocals',
 {text:'Überlagerung begrenzen',level:1},
 {text:'Aktive Stimmen hörbar halten',level:1}
],caveats:['Gestaltetes Trainingsziel, keine validierte perzeptuelle Qualitätsmetrik']});
set(9,{title:'Methode – Controller',caveats:[
 'Daten, Renderer und Objectives unterscheiden sich zwischen den Pfaden',
 'Kein isolierter Vergleich der Netzarchitekturen'
]});
set(10,{title:'Experimente – Daten',bullets:[
 'Aufteilung nach Hash der Originalaudiodatei je Datensatz',
 'Normalisierung ausschließlich auf Trainingsdaten fitten'
],caveats:[
 'Zahlen zählen Übergangsbeispiele, keine unabhängigen Tracks',
 'Keine gemeinsame, global unexponierte finale Testpopulation'
]});
set(11,{title:'Ergebnisse – Training',caveats:[
 'Validierungs-Proxy-Loss sinkt in allen vier Läufen',
 'Loss nur innerhalb einer Zeile vergleichen',
 {text:'Beim variablen Controller ist der erste Messpunkt bereits trainiert',level:1}
]});
set(12,{title:'Experimente – Hörvergleich',bullets:[
 'Equal Power und die vier gelernten Controller',
 '20 Vier-Takt-Cues mit identischen Cuepoints je Beispiel',
 {text:'Anonyme, zufällig vergebene Labels und gemeinsame Peak-Skalierung',level:1},
 'Ein Rater vergibt Plätze, Gleichstände sind erlaubt',
 '19 Beispiele bewertet, eines wegen Tempoeindruck ausgeschlossen',
 'Explorativer Vergleich',
 {text:'Gemeinsame Stimuli, aber unterschiedliche Modell- und Rendering-Protokolle',level:1}
]});
set(13,{title:'Ergebnisse – Hörvergleich',caveats:[
 'Ein Rater, 19 bewertete Cues und ein unbewerteter Ausschluss',
 'Kein beobachteter Präferenzvorteil gegenüber Equal Power',
 'Kein Nachweis von Gleichwertigkeit oder hoher absoluter Qualität'
]});
set(14,{title:'Ergebnisse – Direkte Optimierung',bullets:[
 'Direkte Control-Optimierung',
 {text:'Eine eigene Kurve pro Beispiel anpassen',level:1},
 {text:'Historischer v4-Hörtest: 9 von 9 gegenüber Equal Power bevorzugt',level:1},
 {text:'Ein Rater und nur drei wiederverwendete Audiohashes',level:1},
 'Gelernter Controller',
 {text:'Gemeinsame Netzparameter über Beispiele lernen',level:1},
 {text:'Korrigierter Modellhörtest ergibt ausschließlich Gleichstände',level:1},
 'Unterschiedliche Studienprotokolle erklären noch keine Ursache'
]});
set(15,{title:'Grenzen und weitere Arbeit',bullets:[
 'Modelle unter gleichen Daten, Renderern und Baselines vergleichen',
 'Neue Tracks und unabhängige Rater für weitere Hörvergleiche',
 'Proxy-Komponenten, Controls und Merkmale mit Ablationen untersuchen',
 'Vortrainierte Musikrepräsentationen kontrolliert vergleichen',
 'Variable Übergangslänge',
 {text:'2 / 4 / 6 / 8 Takte trainiert, kein Daueroptimum gezeigt',level:1},
 {text:'1 / 3 Takte bleiben ungeprüft',level:1},
 'Gelernter Cue-Ranker bisher nur synthetisch geprüft'
]});
set(16,{title:'Fazit',bullets:[
 'Interpretierbare Controls über einen differenzierbaren Renderer lernen',
 'Lernen ohne Zielkurven und ohne Referenzübergänge möglich',
 'Vier reale Läufe verbessern ihren Validierungs-Proxy-Loss',
 'Kein Präferenzvorteil im korrigierten Hörvergleich beobachtet',
 'Eine allgemeine perzeptuelle Verbesserung bleibt offen'
]});
set(17,{title:'Vielen Dank für die Aufmerksamkeit',subtitle:'Fragen?'});
set(18,{title:'Reserve – Trainingsprotokolle',caveats:[
 'Vocal-MLP: Manifest wählt 0,324910, History-Minimum ist 0,324840',
 'Checkpoint-Auswahl verwendet eine Mindestverbesserungsschwelle'
]});
set(19,{title:'Reserve – Vocal-Objective',caveats:[
 'Eigene Protokolle für Vocal-MLP und variablen TCN',
 'Variable Form normalisiert zeitabhängige Terme nach Übergangslänge'
]});
set(20,{title:'Reserve – Cuepoint-Auswahl',bullets:[
 'Merkmalsbasierte Auswahl',
 {text:'Taktgrenzen, vollständigen Kontext und Tempo prüfen',level:1},
 {text:'Energie, Harmonik und Timbre gewichten',level:1},
 {text:'Realer Batch: 122 gerenderte Auswahlen',level:1},
 'Experimenteller gelernter Ranker',
 {text:'Kandidaten relativ innerhalb eines Trackpaars ordnen',level:1},
 {text:'Pseudo-Labels eines eingefrorenen Teachers',level:1},
 {text:'Nur synthetische Ende-zu-Ende-Prüfung, keine reale Qualitätsaussage',level:1}
]});
styledSlides[1].notes=styledSlides[1].notes.replace('Die Kurven rechts','Die Kurven unten');
styledSlides[2].notes=styledSlides[2].notes
 .replace('Auf der linken Seite werden mögliche Zeitfenster gebildet','Für die Cuepoint-Auswahl werden mögliche Zeitfenster gebildet')
 .replace('Auf der rechten Seite stehen die Controls','Beim Controller stehen die Controls')
 .replace('die rechte Seite bei festgehaltenen Cuepoints','den Controller bei festgehaltenen Cuepoints');
styledSlides.splice(1,0,{
 type:'agenda',title:'Gliederung',seconds:30,bullets:[
 'Motivation', 'Forschungsfrage', 'Methode', 'Experimente', 'Ergebnisse', 'Grenzen und Fazit'
 ],notes:'Zuerst erläutere ich den Anwendungsfall und die Forschungsfrage. Danach zeige ich, wie BeatBridge Übergänge über einen Controller und einen differenzierbaren Renderer lernt. Anschließend folgen die Trainings- und Hörbefunde sowie die Grenzen und das Fazit.',
 source:'Gliederung des Vortrags; Thesis Kap. 1–7'
});
