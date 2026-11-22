# P11 · Korrekturlauf nach R_P11_01

**Stand 19. November 2026.** Der [unabhängige Review](../reviews/R_P11_01.md) betrifft run01. Dieser Lauf ist als Stimulusquelle für die Erhebung verworfen. Die ursprünglichen Tabellen über Kandidaten, Modellwahl und Rasterausschlüsse sowie die Messwerte der damaligen Dateien bleiben historische Nachweise. Für run02 gelten der [datierte Nachtrag](studienprotokoll.md) und die [aktuelle Durchführungsanleitung](durchfuehrung.md).

| Befund | Prüfung und Entscheidung |
|---|---|
| F-1 · lokale Takte | Der Producer kürzte auf die kleinere der beiden Fensterspannen. In neun von 21 gewählten Cues lagen die Spannen mindestens 40 ms auseinander. P09/Regel endete 7.056 Samples bzw. 160 ms zu früh in A. Auf Autorenentscheidung erhält jedes feste B-Fenster die 17 Grenzen des vollständigen A-Fensters. |
| F-2 · Dateilänge | In allen sieben ursprünglichen Panels verriet die Dreiergruppe gleicher Größe die Zugehörigkeit zur Regel inklusive Anker. Die Größe allein unterschied die drei Mitglieder dieser Gruppe untereinander nicht. Auf Autorenentscheidung kürzt run02 den B-Nachlauf auf die Dauer der kürzesten Zelle und misst danach die fertigen Dateien. |
| F-3 · zweiter Player | Alle drei alten Schlüssel waren identisch zur jeweiligen run01-Hauptfassung. Im alten Sitzungsobjekt fehlte die Kennung. Alle drei Zwischenpakete liegen jetzt außerhalb des Studienordners im [historischen Ablageort](../../../../output/review_jp_20261118/p11_archiv_run01_sessions/). |
| F-4 · Rasterkriterium | Der datierte Nachtrag benennt 98 % gemeinsame Abdeckung je Detektor und acht zusammenhängende vollständige Takte. Die Aussage, diese Schwellen seien erst am 18. November in einer unversionierten Analysefassung festgehalten worden, ist durch `git show d476124:docs/ANALYSIS_PROTOCOL.md` widerlegt. Sie standen am 21. August im Repository. |
| F-5 · Versionierung | Der P01-Freeze ist versioniert. Für die ursprüngliche P11-Fassung existieren die lokale Zeitfolge und der in run01 gespeicherte Hash. Ein nachträglicher Commit kann diese Vorgeschichte dokumentieren. Vor Teilnahme muss der Autor die gesicherte Erstfassung, den Nachtrag, die Anleitung und die Bindung der neuen Zuordnungsschlüssel committen. |
| F-6 · Lautheit | Vier separat generierte Stereosignale bei 44.100 Hz verglichen FFmpeg mit pyloudnorm 0.1.1, Filter DeMan. Größte Differenz 0,0595 LU, für das Signal mit Pegelwechsel und Gate 0,0424 LU. Das prüft den Produktionsmesser an bekannten Signalen. Die Lautheitsangaben für die finalen Clips sind FFmpeg-Messungen. [Referenzimplementierung und Lizenz](https://pypi.org/project/pyloudnorm/0.1.1/) |

## Herkunft der Rasterabweichung

Alle 18 akzeptierten Aufnahmen mit Analyse-Cache haben nativ 48.000 Hz. In allen 18 Caches stimmt das globale librosa-BPM-Feld mit dem aus dem Median aller gespeicherten Schlagabstände berechneten Tempo überein. Bei P06 entsprechen 17.920 native Samples genau 160,71 BPM. Die im Review genannten 147,6 BPM entstehen durch Einsetzen der Renderabtastrate von 44.100 Hz. Die gemeldete Unstimmigkeit innerhalb dieses Receipts ist widerlegt.

Die kombinierte Analyse übernimmt die Samplepositionen von librosa und Taktzählung und Metrum von aufTAKT. In allen 18 Caches liegen die nativen Zeitpunkte auf dem 512-Sample-Raster. Bei 48 kHz entspricht das rund 10,67 ms oder 470,4 Samples im Render. Der globale Median garantiert für die 16 Intervalle eines einzelnen Cues weder gleiche lokale Mediane noch gleiche Spannen. Die technische Ursache der verkürzten A-Brücke ist somit belegt. Die genaue Lage der musikalischen Schläge innerhalb der Detektorauflösung wurde nicht gehörseitig bestimmt. [Implementierung der Zuordnung](../../../../src/analysis/pre_analysis.py) · [historische Nachrechnung](../../../../output/review_jp_20261118/p11_hoerversuch/run02/review_check.json)

## Rendervertrag für run02

Die Kandidatenpools, Cue-IDs, vier Rasterausschlüsse und die auf Halbbeats normierten R1-Merkmalsfenster stammen aus run01. Sie behalten ihre Zuordnung zum jeweiligen Beatindex. In jedem gewählten Cue verwendet P04 das vollständige A-Fenster. Nach der globalen Tempoanpassung gleicht Rubber Band lokal nur B-Intervalle unterschiedlicher Länge an. Die ersten und letzten 10 ms jedes Beats stammen samplegetreu aus B. Je 20 ms Überblendung verbinden sie mit dem tonhöhenerhaltend gestreckten Inneren. Das tatsächliche lokal angepasste B-Signal liegt als internes Float-WAV vor. Das Prüfschema bindet alle 16 Intervallgrenzen und deren Originalsamples an den Export. Equal Power und die 80 direkten Adam-Schritte verwenden dieselbe neue Brücke. Die technische Prüfung bezieht sich auf das detektierte Raster. Hörwirkung und Qualitätspräferenzen bleiben Gegenstand der Erhebung.

Der Eintrag `context_seconds` des P04-Profils bezeichnet die nominellen fünf und acht Sekunden. Die tatsächlich beibehaltene Zahl der B-Samples steht je Clip in `suffix_frames`. Sechs Zellen und der Anker eines Paars werden erst nach dem Zuschnitt gemeinsam normalisiert. Der Audit prüft die Framezahlen, identische Dateigrößen, die Pegel und die Zuordnungen in allen drei anonymen Paketen. Die vollständige Zuordnung bleibt lokal bei der Versuchsleitung.

Zum erneuten Rendern im Repositoryroot den lokalen P07-Runtime-Pfad als `PYTHONPATH` setzen. Mit Projekt-Python `-B -X utf8 -m src.evaluation.p11_stimuli --revise-from output/review_jp_20261118/p11_hoerversuch/run01 --output <neuer_Pfad>` ausführen, anschließend `-m src.evaluation.p11_verify --root <neuer_Pfad>`. Die Teilnehmerpakete des abgeschlossenen Laufs befinden sich ausschließlich unter `run02/blind/VP01/player` und entsprechend für VP02 und VP03.

## Technisches Ergebnis

Alle 21 gewählten Cues der sieben zulässigen Paare bestanden die beiden lokalen Kriterien. In den gespeicherten B-Brücken entsprechen die Intervallgrenzen dem A-Raster samplegenau. Bei P09/Regel enthält die korrigierte Brücke 271.891 Samples, vorher 264.835. Die vier ursprünglichen Rasterausschlüsse gelten weiter. Bei sieben unabhängigen Paaren bleibt die Erhebung deskriptiv.

| Paar | Stereo-Frames je Clip | Bytes je WAV, alle sieben Zellen |
|---|---:|---:|
| P01 | 837.665 | 5.026.034 |
| P02 | 833.431 | 5.000.630 |
| P03 | 838.135 | 5.028.854 |
| P06 | 835.783 | 5.014.742 |
| P07 | 845.192 | 5.071.196 |
| P09 | 837.665 | 5.026.034 |
| P10 | 837.665 | 5.026.034 |

Die 49 Clips dauern 18,899–19,165 s. Vom B-Nachlauf bleiben 345.274–352.800 Samples (7,829–8,000 s). Der größte Abstand zum Lautheitsziel beträgt 0,02 LU, der höchste True Peak −12,16 dBTP. Die drei neu gebundenen Sitzungsschlüssel unterscheiden sich von allen Schlüsseln des verworfenen Laufs. Der Audit bestätigte 147 Teilnehmerkopien. Der Nutzercommit benötigt die hier dokumentierten Bindungen, den datierten Nachtrag, die historische Protokollfassung und die Durchführung. [Prüfnachweis und Schlüsselbindungen](run02_verified.json) · [Unabhängige Messreferenz und historische Geometrie](run02_review_check.json)
