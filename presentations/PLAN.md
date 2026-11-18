# BeatBridge – Abschlussvortrag

Stand: 16.11.2026. Auftrag: deutsche PowerPoint in der bereitgestellten ICG-Vorlage, ungefähr 20 Minuten, Forschungspublikum Computergrafik mit ML-Kenntnissen. Der Vortrag muss zusammen mit der fertigen Thesis ohne Repositorywissen verständlich sein.

## Quellen und Gestaltung

Inhaltliche Autorität sind die aktuellen Kapitel unter `overleaf/`, insbesondere Einleitung, Methodik, Ergebnisse, Diskussion und Fazit. Repositorydokumentation dient nur zur Quellenprüfung. Keine neuen Trainings-, Audio- oder Qualitätsexperimente. Originalvorlage, Thesis und Nutzerdaten bleiben unverändert.

Vorlage: `icg_slide_template.pptx`, 960 × 540 px, Lato Light, ICG-/TU-Logos, graue Inhaltsfolien und rote Akzente. Vorlage importieren und Folien kopieren; keine Neugestaltung. Inhalte und Ergebnistabellen bleiben editierbar. Didaktische Kurvengrafiken sind ausdrücklich als Illustration gekennzeichnet.

## Erzählbogen und Zeitbudget

1. Titel (0:25)
2. Übergänge für Tanz-Mashups (1:10)
3. Cuepoints und Mixing-Controls (1:00)
4. Forschungsfrage und Einordnung (1:10)
5. BeatBridge im Überblick (1:10)
6. Beat-synchrone Eingaben (1:05)
7. Lernen durch den Renderer (1:40)
8. Interpretierbare Mixing-Controls (1:15)
9. Das Proxy-Objective (1:30)
10. Vier Controllerpfade (1:00)
11. Daten und Evaluation (1:15)
12. Proxy-Loss im Training (1:20)
13. Aufbau des Hörvergleichs (1:00)
14. Ergebnis des Hörvergleichs (1:20)
15. Direkte Optimierung und Lernen (1:00)
16. Grenzen und nächste Forschungsschritte (1:20)
17. Fazit (1:00)
18. Fragen (ohne Vortragszeit)

Gesamt: 19:40 Minuten als Richtwert; kurze Pausen ergeben ungefähr 20 Minuten. Notizen enthalten sprechbare Erläuterungen und Quellen. Keine erforderliche Live-Demo oder externe Audiodatei.

Drei ausgeblendete Reservefolien: präzise Trainingsprotokolle; Proxy-Komponenten und Vocal-Controls; Cue-Ranking und Evidenzgrenzen.

## Tragende Aussagen und Grenzen

- Selbstüberwachung meint Control-Lernen ohne Referenzkurven/Referenzübergänge, kein Representation Pretraining.
- Vier reale Läufe zeigen sinkenden Validation-Proxy-Loss innerhalb verschiedener Protokolle. Kein Architektur-Ranking und kein kausaler Ablationsbefund.
- Korrigierter Modellhörvergleich: ein Rater, 19 bewertete Beispiele mit fünf gleichen Plätzen, ein unbewerteter Ausschluss. Pro Modell gegen Equal Power 0/19/0. Keine beobachtete Präferenzverbesserung, kein Äquivalenz- oder absoluter Qualitätsnachweis.
- Daten-, Renderer- und Objective-Unterschiede sowie wiederholte Tracks und fehlende globale unabhängige Testpopulation bleiben sichtbar.
- Direkte Control-Optimierung ist von gelerntem Controller strikt getrennt.
- Variable 2/4/6/8 Takte: Training belegt, Dauerpräferenz nicht belegt. 1/3 Takte ungeprüft.
- Gelernter Cue-Ranker nur synthetisch geprüft; keine reale Qualitätsaussage.

## Prüfung

Alle Folien rendern und einzeln sichten; Vergleich mit allen fünf Vorlagenfolien. Paket-/Layoutprüfung, vollständige Notizen und Zeitbudget, Zahl-zu-Thesis-Abgleich. Testläufe und Werkzeugblockaden in `docs/Bemerkungen.md`; erreichten Stand in `docs/STATUS.md` festhalten. Keine Commits.
