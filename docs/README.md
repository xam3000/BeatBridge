# BeatBridge-Dokumentation

Dieser Ordner ist das dauerhafte Projektgedächtnis. Verifizierte Erkenntnisse,
Entscheidungen und offene Punkte werden hier festgehalten und nicht nur in
Chat-Verläufen. `STATUS.md` ist der kurze Einstieg mit aktuellem Stand und
priorisierten nächsten Schritten; `Bemerkungen.md` ist die fortlaufende
Chronik aus Beobachtungen, Entscheidungen und gelernten Lektionen.

## Dokumentrollen

| Datei | Rolle | Pflege |
|---|---|---|
| [`STATUS.md`](./STATUS.md) | Einstieg, verifizierter Stand und priorisierte nächste Schritte | Bei Meilensteinen und relevanten Standänderungen aktualisieren |
| [`LISTENING_STUDY_ANALYSE_20261106.md`](./LISTENING_STUDY_ANALYSE_20261106.md) | Auswertung des korrigierten 20er-Modellhörtests: 19 Fünffach-Gleichstände, ein bestätigter Ausschluss; JSON-Ergebnisse und Reproduktionsskript verlinkt | Datierten Befund erhalten; Folgeauswertungen separat dokumentieren |
| [`PIPELINE_UEBERSICHT.md`](./PIPELINE_UEBERSICHT.md) | Grafische Gesamtpipeline, Controller-/Rendererzuordnung, Evidenzgrenzen und Quellen (Stand 27.10.2026) | Bei belegten Änderungen an Datenfluss oder Ausführungsstand aktualisieren |
| [`figures/flowcharts/README.md`](./figures/flowcharts/README.md) | Elf farbige Thesis-SVGs: Gesamtpipeline und Komponenten, englische Captions, Quellen und Generator (28.10.2026) | Bei belegten Pipelineänderungen oder gewünschter Layoutänderung aktualisieren |
| [`figures/flowcharts/METRICS_README.md`](./figures/flowcharts/METRICS_README.md) | Zwölf zusätzliche Metrik-SVGs (12–23): Berechnung, Defaultgewichte, Interpretation, Captions und Quellen (29.10.2026) | Bei belegten Metrikänderungen aktualisieren; Run-Konfigurationen bleiben maßgeblich |
| [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) | Maßgeblicher Forschungsrahmen, Scope und Zeitplanung | Nur bei bewussten Projektentscheidungen ändern |
| [`GUI_SPECIFICATION.md`](./GUI_SPECIFICATION.md) | Implementierbares Zielbild für Paar-Editor, Datenvisualisierung, Vergleich und gestufte GUI-Umsetzung | Bei bewussten UX-/GUI-Entscheidungen aktualisieren; keine Pipelineverträge duplizieren |
| [`CLI.md`](./CLI.md) | Installation, Kommandozeilen-Aufrufe, Renderer und Fehlerbehebung | Bei Änderungen an CLI-Argumenten oder Laufzeitvoraussetzungen aktualisieren |
| [`RENDERING_PROTOCOL.md`](./RENDERING_PROTOCOL.md) | Versionierter Vertrag der programmatischen Rendering-Pipeline | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`CANDIDATE_PROTOCOL.md`](./CANDIDATE_PROTOCOL.md) | Versionierter Vertrag für automatische Übergangskandidaten | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`RANKING_PROTOCOL.md`](./RANKING_PROTOCOL.md) | Versionierter Vertrag für Cutpoint-/Feature-Ranking und Vorab-Auswahl | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`RATINGS_PROTOCOL.md`](./RATINGS_PROTOCOL.md) | Versionierter Vertrag für menschliche Ratings und Fehler-Tags | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`SONG_COMPATIBILITY_PROTOCOL.md`](./SONG_COMPATIBILITY_PROTOCOL.md) | Versionierter Vertrag für das Songpaar-Kompatibilitätsranking | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`BATCH_RENDERING_PROTOCOL.md`](./BATCH_RENDERING_PROTOCOL.md) | Versionierter Vertrag für Batch-Exporte und Manifeste | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`RENDERED_TRANSITION_METRIC_PROTOCOL.md`](./RENDERED_TRANSITION_METRIC_PROTOCOL.md) | Versionierte Baseline-Metrik für bereits gerenderte Übergänge | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`DIFFERENTIABLE_CONTROL_PROTOCOL.md`](./DIFFERENTIABLE_CONTROL_PROTOCOL.md) | Versionierter Vertrag für lernbare Mixing-Controls, differenzierbaren Renderer und Proxy-Objective | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`FEATURE_PROTOCOL.md`](./FEATURE_PROTOCOL.md) | Versionierter Tensor-, Geometrie-, Vocal-/Phrasen- und Normalisierungsvertrag für das Feature→Control-Modell | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`DATASET_PROTOCOL.md`](./DATASET_PROTOCOL.md) | Versionierter Exportvertrag für globale Paarfeatures, NPZ-Dateien, Trainingsnormalisierung und track-getrennte Splits | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`ML_CONTROL_MODEL_PROTOCOL.md`](./ML_CONTROL_MODEL_PROTOCOL.md) | Versionierter Vertrag für Bridge-Waveform-Cache, PyTorch-Dataset, kleine Feature→Control-MLP-Baseline und Self-Supervised-Loss | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`VOCAL_CONTROL_MODEL_PROTOCOL.md`](./VOCAL_CONTROL_MODEL_PROTOCOL.md) | Additiver Vertrag für Vocal-Control-Modell v2, stem-fähigen Renderer, Objective v5 und Vocal-Bridge-Cacheformat 2 | Nur additiv ändern; vorhandene v1/v4-Artefakte bleiben unverändert |
| [`PRETRAINED_MODELS.md`](./PRETRAINED_MODELS.md) | Eingesetzte vortrainierte Modelle, Gewichtsrevisionen, Grenzen und Zitierhinweise | Bei Änderungen an Modell, Gewichten oder Backend aktualisieren |
| [`REFERENCES.bib`](./REFERENCES.bib) | Direkt übernehmbare BibTeX-Einträge für die Masterarbeit | Mit tatsächlich eingesetzten oder explizit geprüften wissenschaftlichen Backends abgleichen |
| [`CONTROL_STUDY_PROTOCOL.md`](./CONTROL_STUDY_PROTOCOL.md) | Versionierter Vertrag für blinde A/B-Control-Vergleiche, Antwortschlüssel und Ratings-Sidecar | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`Bemerkungen.md`](./Bemerkungen.md) | Laufende Beobachtungen, Entscheidungen und gelernte Lektionen | Neue Einträge mit Datum und Begründung ergänzen; bestehende Einträge nicht löschen |
| [`../config/track_exclusions.json`](../config/track_exclusions.json) | Versionierte, maschinell angewendete Ausschlüsse aus neuen Batches, Vergleichen und Trainingsdaten | Nur mit Track-Hash, Datum und begründetem Nutzer-/Datenurteil ergänzen |

Projektweite Arbeitsregeln stehen in [`../AGENTS.md`](../AGENTS.md). Die kompakte Bedienungs- und Projektübersicht bleibt in [`../README.md`](../README.md).
