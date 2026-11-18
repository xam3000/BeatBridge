# Testläufe des Code-Reviews vom 13. November 2026

`AGENTS.md` verlangt, jeden Testlauf in `docs/Bemerkungen.md` einzutragen. Das Review durfte keine vorhandenen Dateien ändern. Die Läufe stehen deshalb hier, im selben Raster (Fragestellung, Setup, Befehl, Ergebnis, Schlussfolgerung).

Umgebung für alle Läufe: macOS, CPU, Python 3.14.6, eigene venv unter `review_jp/.venv` (installiert aus `requirements.txt` und `requirements-dev.txt`: torch 2.13.0, numpy 2.4.6, librosa 0.11.0). Start jeweils aus dem Repo-Root mit `PYTHONDONTWRITEBYTECODE=1`. Kein Training, kein Sweep, kein W&B-Aufruf, kein Download von Modellgewichten. Test-Split und `answer_key.json` wurden nicht geöffnet.

| Nr. | Fragestellung | Befehl | Ergebnis | Schlussfolgerung |
|---|---|---|---|---|
| 1 | Läuft die Testsuite auf dem Mac? (Commit `7918338`) | `python -m pytest -q -p no:cacheprovider --basetemp=review_jp/logs/pytest_tmp`, mit `WANDB_MODE=disabled`, `QT_QPA_PLATFORM=offscreen` | 289 bestanden, 1 übersprungen, 34 s. `git status` vorher und nachher identisch. Protokoll: `logs/pytest_q_7918338.log` | Tests sind plattformneutral, weil aufTAKT, FFmpeg und CUDA durch Attrappen ersetzt sind. |
| 2 | Dasselbe nach dem Pull auf `56b982a` | wie Nr. 1 | 291 bestanden, 1 übersprungen, 21 s. Protokoll: `logs/pytest_q_56b982a.log` | Der Pull bricht nichts. |
| 3 | B3/B4: Welche Feature-Kanäle sind tot, wie abhängig sind die Beispiele? | `python review_jp/scripts/b3_b4_feature_and_dependency_audit.py` | 13 von 54 Sequenzkanälen für alle Beispiele identisch; Validation aus 2 bzw. 5 Tracks. Rohdaten: `results/b3_b4_feature_and_dependency_audit.json`, `logs/b3_b4.log` | Verdacht 3 bestätigt. |
| 4 | B1/B2 für den lokalen MLP-v1-Lauf | `python review_jp/scripts/b1_b2_model_response_and_loss.py mlp_v1_top3` | Validation 0,30596 (Equal Power) → 0,29600 (Modell); Abgleich mit `history.json` auf sieben Stellen. Rohdaten: `results/b1_b2_mlp_v1_top3.json` | Netz reagiert auf das Trackpaar, Gewinn 3,3 %. |
| 5 | B1/B2 für den Vocal-v2-Lauf auf top3 | wie Nr. 4 mit `vocal_v2_top3` | 0,26781 → 0,25934; 73 % des Gewinns bleiben mit vertauschten Eingaben. Rohdaten: `results/b1_b2_vocal_v2_top3.json` | Gewinn überwiegend eingabeunabhängig. |
| 6 | B1/B2 für den Vocal-v2-Lauf auf top10 | wie Nr. 4 mit `vocal_v2_top10` | 0,35904 → 0,33700; 32 % des Gewinns bleiben mit vertauschten Eingaben. Rohdaten: `results/b1_b2_vocal_v2_top10.json` | Netz reagiert, 89 % des Gewinns aus dem Energie-Term. |
| 7 | Startpunkt und eingabeunabhängiges Optimum im Full-Band-Pfad | wie Nr. 4 mit `tcn_fresh_init`, danach `python review_jp/scripts/b2c_tcn_plot.py` | Frisch initialisiert 1,9629; eine feste Kurvenschar 0,2429; direkt pro Beispiel 0,2411. Rohdaten: `results/b1_b2_tcn_fresh_init.json` | Feste Kurve holt 99,9 % des möglichen Gewinns. |
| 8 | Ist der differenzierbare Renderer bei Equal-Power-Controls gleich dem `EqualPowerFadeCut`? | `python review_jp/scripts/b5_renderer_equivalence.py` | Zwei-Band: max. Abweichung 2,4·10⁻⁷. Full-Band bei frischem TCN: −9,9 dB. Rohdaten: `results/b5_renderer_equivalence.json` | Zwei-Band-Start ist Equal Power, TCN-Start nicht. |
| 9 | Wie stark unterscheidet sich das Modell-Audio von Equal Power? | `python review_jp/scripts/b2b_audio_difference.py` | Differenzsignal im Median −17 bis −19 dB; größte Frame-Pegelabweichung im Median 0,7 bis 1,4 dB. Rohdaten: `results/b2b_audio_difference.json` | Unterschiede an der Hörschwelle. |
| 10 | Läuft das Skript für das variable Modell? | `python review_jp/scripts/student_variable_model_check.py --selftest` | Läuft mit Zufallsdaten durch. Keine Aussage über das Modell; die Selbsttest-Ausgaben wurden wieder gelöscht. | Skript ist für den Studenten bereit, mit echten Daten ungetestet. |

Abgebrochene oder fehlerhafte Anläufe:

- Nr. 4 brach beim ersten Versuch im Plot ab (falsche Array-Form für die Referenzlinie). Behoben, danach erneut vollständig gelaufen.
- Nr. 8 brach beim ersten Versuch mit einem Importfehler ab (`EqualPowerFadeCut` liegt in `src/cutting/equal_power_fade_cut.py`). Behoben.

Laufzeiten: Nr. 4 rund 50 s, Nr. 5 rund 70 s, Nr. 7 rund 100 s, Nr. 6 rund 8 min (2500 Renderings für den Vertauschungstest).

Aufräumen: `review_jp/.venv` belegt rund 1 GB und kann gelöscht werden. `.gitignore` des Repos schließt `.venv/` und `__pycache__/` bereits aus; `review_jp/` selbst ist nicht ignoriert und nicht committet.
