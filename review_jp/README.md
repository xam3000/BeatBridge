# Review-Dokumente zu BeatBridge

Dieser Ordner enthält die Unterlagen des Betreuer-Reviews: Befunde, Plan, Rückmeldungen, Prüfskripte und deren Ergebnisse. Diese Seite ist der Einstieg und wird bei jeder neuen Rückmeldung aktualisiert.

Letzte Aktualisierung: 22. November 2026, Commit `4651e51`.

## Was jetzt gilt

| Frage | Dokument |
|---|---|
| Wo stehen wir, und was ist als Nächstes zu tun? | [RUECKMELDUNG_20261122.md](./RUECKMELDUNG_20261122.md) |
| Was ist der Plan, und warum? | [ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md](./ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md) |
| Wie weit ist die Umsetzung im Einzelnen? | [`docs/REVIEW_JP_UMSETZUNG.md`](../docs/REVIEW_JP_UMSETZUNG.md), geführt vom Autor |

Wer neu einsteigt, liest zuerst die Rückmeldung, dann den Aktionsplan. Die beiden älteren Dokumente braucht man nur für Belege und Herleitung.

## Alle Dokumente

| Datum | Datei | Bezugs-Commit | Inhalt | Status |
|---|---|---|---|---|
| 13.11.2026 | [CODE_REVIEW.md](./CODE_REVIEW.md) | `56b982a` | Code-Review mit Datenfluss, Messungen, Fehlerliste | Momentaufnahme. Stand jedes Befunds in der Rückmeldung, Abschnitt 7. |
| 18.11.2026 | [EINSCHAETZUNG.md](./EINSCHAETZUNG.md) | `56b982a` | Novelty, Gehalt, Angriffspunkte | Momentaufnahme. Abschnitt 4 durch den Aktionsplan abgelöst. |
| 18.11.2026 | [ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md](./ZUSAMMENFASSUNG_UND_AKTIONSPLAN.md) | `56b982a` | Kritikpunkte, zehn Grundsätze, Plan in Phasen | Gilt. Reihenfolge durch die Rückmeldung angepasst. |
| 22.11.2026 | [RUECKMELDUNG_20261122.md](./RUECKMELDUNG_20261122.md) | `4651e51` | Umsetzungsstand, drei Befunde vor dem Hörversuch, nächste Schritte | Aktuell. Am 23.11. ergänzt: Erklärungen, Entscheidung zur Paarzahl, Abschnitt 11 zu den Beat-Trackern, Abschnitt 12 zum Design des Hörversuchs, Einordnung Pflicht oder Benennen in Abschnitt 8. |
| laufend | [TESTLAEUFE.md](./TESTLAEUFE.md) | je Lauf | Protokoll aller im Review ausgeführten Läufe | Wird fortgeschrieben. |

## Ordner

### `scripts/`

Alle Skripte starten aus dem Repo-Root und schreiben nur nach `review_jp/`.

| Skript | Wozu | Braucht | Status |
|---|---|---|---|
| `mert_kontext_check.py` | Schichtet die Validation-Ergebnisse der Metrik nach geteiltem MERT-Kontext (Rückmeldung, Befund 1) | P07-, P08- und P09-Artefakte unter `output/review_jp_20261118/` | Neu am 22.11. Selbsttest bestanden, mit echten Daten ungetestet. |
| `common.py` | Gemeinsame Helfer und Pfade der geprüften Läufe (`RUNS`) | – | Vom Autor am 19.11. an den neuen Modellvertrag angepasst. |
| `b1_b2_model_response_and_loss.py` | Kurven, Verlust-Zerlegung, Vertauschungstest für feste Controller | Checkpoints, Datensatz, Waveform-Cache | Stand 13.11. Für die September-Läufe durch `src/evaluation/controller_*.py` des Autors ergänzt. |
| `b2b_audio_difference.py` | Audio-Unterschied Modell gegen Equal Power | wie oben | Stand 13.11. |
| `b2c_tcn_plot.py` | Übersichtsplot zum Full-Band-Pfad | Ergebnisse von `b1_b2…` | Stand 13.11. |
| `b3_b4_feature_and_dependency_audit.py` | Tote Kanäle und Abhängigkeit der Beispiele | Datensatz | Stand 13.11. |
| `b5_renderer_equivalence.py` | Zwei-Band-Renderer gegen `EqualPowerFadeCut`, Startpunkt des alten TCN | Datensatz, Waveform-Cache | Vom Autor am 19.11. auf den Legacy-Start festgelegt. |
| `student_variable_model_check.py` | Dieselben Fragen für das variable Modell | Datensatz-Format 2, variabler Cache | Abgelöst: Der Autor hat das variable Modell in seiner Controller-Diagnose selbst ausgewertet. |

### `results/`, `plots/`, `logs/`

- `results/`: Rohdaten der Messungen vom 13.11. auf den Checkpoints vom August. Der Ledger des Autors verweist auf diese Dateien. Das Ergebnis von `mert_kontext_check.py` landet ebenfalls hier.
- `plots/`: Abbildungen zum Code-Review. Die beiden Energieplots für die Vocal-Läufe sind im Bericht nicht eingebunden.
- `logs/`: Protokolle der Läufe aus `TESTLAEUFE.md`, die pytest-Protokolle tragen den Commit im Namen.

`review_jp/.venv` ist die Python-Umgebung des Reviews. Sie ist nicht versioniert und kann gelöscht werden.

## Regeln für diesen Ordner

1. Datierte Dokumente sind Momentaufnahmen und werden inhaltlich nicht umgeschrieben. Jedes trägt oben eine Statuszeile, die sagt, was noch gilt und wo der aktuelle Stand steht.
2. Eine neue Rückmeldung bekommt eine eigene Datei `RUECKMELDUNG_<Datum>.md`. Dabei werden diese Seite und die Statuszeile der vorigen Rückmeldung angepasst.
3. Dateien werden nicht verschoben oder umbenannt. Ledger, Umsetzungsdokument und Prompts des Autors unter `docs/` verweisen auf diese Pfade.
4. Der Umsetzungsstand wird nicht hier geführt, sondern vom Autor in `docs/REVIEW_JP_UMSETZUNG.md`. Entscheidungen der Betreuung werden in der jeweils aktuellen Rückmeldung nachgetragen.
