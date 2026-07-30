# BeatBridge-Dokumentation

Dieser Ordner ist das dauerhafte Projektgedächtnis. Verifizierte Erkenntnisse, Entscheidungen und offene Punkte werden hier festgehalten und nicht nur in Chat-Verläufen.

## Dokumentrollen

| Datei | Rolle | Pflege |
|---|---|---|
| [`STATUS.md`](./STATUS.md) | Einstieg, verifizierter Stand und priorisierte nächste Schritte | Bei Meilensteinen und relevanten Standänderungen aktualisieren |
| [`Projekt-Gesamtuebersicht.md`](./Projekt-Gesamtuebersicht.md) | Maßgeblicher Forschungsrahmen, Scope und Zeitplanung | Nur bei bewussten Projektentscheidungen ändern |
| [`CLI.md`](./CLI.md) | Installation, Kommandozeilen-Aufrufe, Renderer und Fehlerbehebung | Bei Änderungen an CLI-Argumenten oder Laufzeitvoraussetzungen aktualisieren |
| [`RENDERING_PROTOCOL.md`](./RENDERING_PROTOCOL.md) | Versionierter Vertrag der programmatischen Rendering-Pipeline | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`CANDIDATE_PROTOCOL.md`](./CANDIDATE_PROTOCOL.md) | Versionierter Vertrag für automatische Übergangskandidaten | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`BATCH_RENDERING_PROTOCOL.md`](./BATCH_RENDERING_PROTOCOL.md) | Versionierter Vertrag für Batch-Exporte und Manifeste | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`RENDERED_TRANSITION_METRIC_PROTOCOL.md`](./RENDERED_TRANSITION_METRIC_PROTOCOL.md) | Versionierte Baseline-Metrik für bereits gerenderte Übergänge | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`DIFFERENTIABLE_CONTROL_PROTOCOL.md`](./DIFFERENTIABLE_CONTROL_PROTOCOL.md) | Versionierter Vertrag für lernbare Mixing-Controls, differenzierbaren Renderer und Proxy-Objective | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`FEATURE_PROTOCOL.md`](./FEATURE_PROTOCOL.md) | Versionierter Tensor-, Geometrie-, Vocal-/Phrasen- und Normalisierungsvertrag für das Feature→Control-Modell | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`PRETRAINED_MODELS.md`](./PRETRAINED_MODELS.md) | Eingesetzte vortrainierte Modelle, Gewichtsrevisionen, Grenzen und Zitierhinweise | Bei Änderungen an Modell, Gewichten oder Backend aktualisieren |
| [`REFERENCES.bib`](./REFERENCES.bib) | Direkt übernehmbare BibTeX-Einträge für die Masterarbeit | Mit tatsächlich eingesetzten oder explizit geprüften wissenschaftlichen Backends abgleichen |
| [`CONTROL_STUDY_PROTOCOL.md`](./CONTROL_STUDY_PROTOCOL.md) | Versionierter Vertrag für blinde A/B-Control-Vergleiche, Antwortschlüssel und Ratings-Sidecar | Nur additiv ändern; inkompatible Änderungen benötigen eine neue Version |
| [`Bemerkungen.md`](./Bemerkungen.md) | Laufende Beobachtungen, Entscheidungen und gelernte Lektionen | Neue Einträge mit Datum und Begründung ergänzen; bestehende Einträge nicht löschen |
| [`../config/track_exclusions.json`](../config/track_exclusions.json) | Versionierte, maschinell angewendete Ausschlüsse aus neuen Batches, Vergleichen und Trainingsdaten | Nur mit Track-Hash, Datum und begründetem Nutzer-/Datenurteil ergänzen |

Projektweite Arbeitsregeln stehen in [`../AGENTS.md`](../AGENTS.md). Die kompakte Bedienungs- und Projektübersicht bleibt in [`../README.md`](../README.md).
