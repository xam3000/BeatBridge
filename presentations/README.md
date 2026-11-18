# BeatBridge – Mastervortrag

Die aktuelle PowerPoint steht in `output/BeatBridge_Mastervortrag_20min_20261117.pptx`.
Sie folgt den drei eigenen Vorträgen unter `older_presentations/`: einfache
Thementitel, schwarze native Stichpunkte und Unterpunkte, eine rote
Gliederungsfolie und größere Diagramme. 18 Vortragsfolien einschließlich Titel
und Gliederung, eine Abschlussfolie und drei ausgeblendete Reservefolien.
Das geplante Zeitbudget beträgt 20:00 Minuten. Die erste Fassung vom 16.11.
bleibt in `output/BeatBridge_Mastervortrag_20min.pptx` erhalten.
Die deutschen Sprechernotizen enthalten Erläuterungen, den Zeitplan und
Kapitelverweise zur Thesis. Eine Live-Demo oder externe Audiodatei ist nicht nötig.

Inhalte: Problem und Abgrenzung, Eingaben, Controller–Renderer-Lernmechanismus,
Controls und Proxy, vier Trainingspfade, Datengrundlage, Proxy- und Hörbefunde,
Grenzen und Fazit. Grundlage ist die aktuelle Arbeit unter `overleaf/`.
Tabellen und Kurvendiagramme sind native editierbare PowerPoint-Objekte;
Kurven auf Folien 9/10 sind ausdrücklich didaktische Illustrationen.

`PLAN.md` hält den ursprünglichen Auftrag und Quellenregeln fest.
`STYLE_REVISION_20261117.md` dokumentiert Referenzbeobachtungen und Stilrevision.
`content.mjs` enthält die erste Fassung. `style-content.mjs` übernimmt deren
wissenschaftliche Aussagen und Notizen mit gestrafften Folientexten und
angepassten Layoutverweisen. `build-style.mjs` importiert die erste fertige
PowerPoint und bearbeitet deren Layouts/Objekte. `build.mjs` bleibt der
ursprüngliche Vorlagenbuilder. Die Vorlage und die Thesis werden nicht verändert.
`.build/` enthält lokale Renderbilder und Validierungsberichte und wird ignoriert.

Zum erneuten Bauen den Node-Runtimepfad in `build-style.mjs` an die lokal verfügbare
gebündelte Codex-Runtime anpassen und eine **neue** finale Zieldatei sowie einen
**neuen** Receiptpfad wählen;
die Finalisierung überschreibt keine vorhandene Ausgabe. Python-Prüfungen
verwenden `.venv/Scripts/python.exe`. Aus dem Repositoryverzeichnis ausführen:

```powershell
& '<gebündelte Node-Runtime>/node.exe' presentations/build-style.mjs
```

Die Finalisierung prüft Paket, Layout, Referenzschrift, native Tabellen und
Diagramme sowie erneuten Artifact-Tool-Import. Auf diesem Windows-Workspace
scheitert das Publizieren per Hardlink mit EPERM. Der Builder verwendet nur für
seine konkrete neu angelegte Zieldatei eine exklusive Kopie des bereits
validierten Stagings; die finalen Hashprüfungen bleiben aktiv. Diesen eng
begrenzten Kompatibilitätspfad entfernen, wenn die Runtime Hardlinks unterstützt.
Die Originalvorlage enthält eine nichtfatale eingebettete Lato-Light-Namenswarnung.
Eine native PowerPoint-Laufzeitprüfung und ein tatsächlich gesprochener
Probevortrag wurden nicht durchgeführt.
