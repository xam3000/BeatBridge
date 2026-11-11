# Wie die BeatBridge-Metriken funktionieren

**Stand: 29.10.2026.** Die zwölf neuen SVGs ergänzen die
[Pipelineabbildungen 01–11](./README.md). Die Beschriftungen und
Caption-Vorschläge sind passend zur Thesis auf Englisch. Alle Formeln wurden
gegen die aktuelle Implementierung gelesen. Die Zahlen in Gewichten und
Toleranzen sind **Code-Defaults**; die gespeicherte Konfiguration eines
konkreten Runs ist für dessen Ergebnisse maßgeblich. Es wurden keine neuen
Musik-/Modellergebnisse erhoben.

## 12 — Wo welche Metrik eingesetzt wird

[12-metric-roles.svg](./12-metric-roles.svg)

**Caption:** Distinct roles of the evaluation quantities in BeatBridge.
Whole-song and cue-window scores support selection, the rendered-audio metric
evaluates an exported variant, and fixed proxy losses train the controller.
Human listening ratings provide a separate form of evidence. Technical scores
are maximised, training losses are minimised, and neither is a calibrated
probability of perceptual quality.

Die drei Baseline-Scores liegen in `[0,1]`. Ein hoher Wert bedeutet, dass
die jeweilige technische Heuristik erfüllt ist, nicht „90 % guter Übergang“.
Die Objectives sind gewichtete Loss-Summen ohne obere Eins-Grenze. Ihre
Beträge lassen sich nicht über unterschiedliche Renderer-/Dataset-/Objective-
Verträge hinweg als Modellrangliste verwenden.

## 13 — Songpaar-Kompatibilität

[13-song-compatibility-metric.svg](./13-song-compatibility-metric.svg)

**Caption:** Whole-track compatibility score used to preselect target songs.
Five similarity components are combined with fixed default weights. Tempo and
RMS differences receive clipped linear scores; spectral-centroid distance is
mapped exponentially. Chroma and normalised onset-strength profiles are
compared using cosine similarity. This score does not select exact cue points.

**Quelle:** [song_compatibility.py](../../../src/ranking/song_compatibility.py),
[Vertrag](../../SONG_COMPATIBILITY_PROTOCOL.md).

Der Gesamtscore ist `0.35 H + 0.25 T + 0.15 K + 0.15 E + 0.10 R`.
`H` ist der geklippte Chroma-Kosinus. Der Tempoabstand ist symmetrisch:
`abs(BPM_A-BPM_B)/max(BPM_A,BPM_B)`; bei 15 % wird sein Teilscore null.
Die Energiedifferenz verwendet RMS-dB, keine LUFS-Messung. Die beiden
Spektralschwerpunkte werden vor dem Oktavabstand jeweils um **20 Hz**
verschoben; anschließend wird `exp(-distance)` gebildet.
Der Rhythmusvergleich interpoliert die Onset-Verläufe auf 32 Punkte über den
Track; er ist kein Vergleich erkannter Beatpositionen. Ohne verwertbare
Chroma-/Onsetvektoren ist der entsprechende Kosinuswert neutral `0.5`.

## 14 — Cuepoint-Ranking

[14-cue-ranking-metric.svg](./14-cue-ranking-metric.svg)

**Caption:** Feature-based ranking of accepted cue candidates before
rendering. High power and non-overlap contribute 60 percent of the default
score; harmonic, energy, timbre and tempo similarities contribute the
remainder. Drop-window features and transition-window features have distinct
roles. Renderer-dependent artefacts cannot be evaluated at this stage.

**Quelle:** [_score_candidate](../../../src/ranking/feature_baseline.py),
[Rankingvertrag](../../RANKING_PROTOCOL.md).

`S_cue = 0.30 HP + 0.30 NO + 0.18 H + 0.10 E + 0.05 K + 0.07 T`.
Chroma, Energie und Klang beziehen sich auf **A vor Cue A** und **B nach
Cue B**. Die Übergangsfenster **A nach Cue A** und **B vor Cue B** gehen in
Non-Overlap ein. Die Fensterdauer wird in dieser Baseline aus Beatanzahl und
BPM angenähert, nicht aus der exakten lokalen Gridfensterdauer übernommen.
Die Baseline enthält weder eine Vocal-Clash-Messung noch einen Phrase-/Lyrics-
Detektor. Gleichstände werden deterministisch über die Candidate-ID gelöst.

## 15 — High Power und Non-Overlap im Detail

[15-cue-energy-and-non-overlap.svg](./15-cue-energy-and-non-overlap.svg)

**Caption:** Computation of the high-power and non-overlap components from
four unrendered windows. Window RMS values are located in their own track's
energy distribution. The weakest drop percentile determines high power;
non-overlap combines quiet transition windows with the weaker of the source
energy fall and target energy rise. These quantities describe cue geometry,
not the rendered waveform.

**Quelle:** [feature_baseline.py](../../../src/ranking/feature_baseline.py),
insbesondere `_relative_power_percentile` und `_score_candidate`.

Für ein Fenster mit RMS-Pegel `r` ist `p = mean(track_frame_RMS_dB <= r)`.
Die Trackverteilung basiert auf RMS-Frames mit 2.048 Samples und Hop 512.
Ist der robuste Dynamikbereich `p90-p10 < 3 dB`, wird das Perzentil neutral
auf `0.5` gesetzt. Dadurch werden stärker komprimierte Tracks nicht durch
instabile Perzentile bevorzugt.

Mit `clip01(x)=clip(x,0,1)` gilt:

- `HP = min(p_A_before, p_B_after)`.
- `fall_A = RMS_A_before - RMS_A_after`,
  `rise_B = RMS_B_after - RMS_B_before`, jeweils in dB.
- `d_A = clip01(fall_A/6)`, `d_B = clip01(rise_B/6)`.
- `q = 1 - max(p_A_after,p_B_before)`.
- `NO = sqrt(q * min(d_A,d_B))`.

High Power ist also relativ zum einzelnen Track. Der Non-Overlap-Score
verlangt beide Grenzen und beide ruhigen Übergangsfenster. Er ist kein
Nachweis, dass der Renderer später tatsächlich keine High-Power-Anteile mischt.

## 16 — Technische Metrik des gerenderten Audios

[16-render-audio-metric.svg](./16-render-audio-metric.svg)

**Caption:** Technical score of an actual rendered transition. The weighted
components measure energy contrast around the whole bridge, smoothness at
actual render boundaries, chroma continuity at both ends, and onset
periodicity at the expected tempo. All components are computed on the
rendered audio, including the effects of time stretching and mixing.

**Quelle:** [rendered_transition.py](../../../src/ranking/rendered_transition.py),
[Vertrag](../../RENDERED_TRANSITION_METRIC_PROTOCOL.md).

`S_render = 0.30 Energy + 0.30 Boundary + 0.20 Harmony + 0.20 Rhythm`.
Das Stereoergebnis wird für diese Baseline zu Mono gemittelt. Pre- und
Postkontext sind jeweils höchstens eine erwartete Übergangslänge lang.
Energie wird über den **ganzen** Bridgeblock gemessen:
`sqrt(clip01((pre_dB-bridge_dB)/6) * clip01((post_dB-bridge_dB)/6))`.
Das ist keine zeitaufgelöste Sollkurvenabweichung wie im Trainingsobjective.

Die Harmoniekomponente mittelt den Chroma-Kosinus zwischen Prekontext und
erster Bridgehälfte sowie zwischen zweiter Bridgehälfte und Postkontext.
Fehlende tonale Evidenz ergibt neutral `0.5`.
Beim Hard Cut sind Start und Ende identisch: Es gibt eine tatsächliche
Grenze, einen besonderen nachfolgenden Analyseblock und einen direkten
Pre-/Post-Chromavergleich. Die in der Grafik gezeigte Zwei-Hälften-Form gilt
für eine ausgedehnte Bridge.

## 17 — Grenzglätte und rhythmische Stabilität

[17-boundary-and-rhythm-mechanisms.svg](./17-boundary-and-rhythm-mechanisms.svg)

**Caption:** Mechanisms behind two rendered-audio score components.
Boundary smoothness combines an RMS-continuity score with a sample-jump
score relative to local signal differences. Rhythmic stability computes
onset-envelope correlation at one expected beat lag. The correlation is
mapped from [-1,1] to [0,1]; degenerate onset evidence receives a neutral score.

**Quelle:** `_boundary_smoothness`, `_rhythmic_stability` in
[rendered_transition.py](../../../src/ranking/rendered_transition.py).

Default: RMS-Fenster je 0,10 s links/rechts der Grenze, Click-Kontext je
0,25 s davor/danach. `R = exp(-abs(delta_RMS_dB)/12)`.
`J` ist der Sample-Sprung an der Grenze relativ zum 99. Perzentil der
absoluten Sampledifferenzen im lokalen Kontext. `C = exp(-max(0,J-1))`;
der Grenzscore ist `sqrt(R*C)`, der Komponentenscore dessen Mittel über die
Grenzen. Ist der lokale Referenzsprung praktisch null, verwendet der Code
`J=0` für ebenfalls null und sonst `J=10`.

Für Rhythmik wird die Onset-Hüllkurve mittelwertbereinigt. Der Lag ist bei
Hop 512 `max(1,round(60*sr/(BPM*512)))`. Verglichen werden die beiden um
diesen Lag versetzten Teilvektoren. Es gibt keine Suche nach dem maximalen
Autokorrelationspeak und keinen Test, ob ein Downbeat korrekt erkannt wurde.
Stille, zu kurze oder konstante Onset-Evidenz wird neutral `0.5` bewertet.

## 18 — Trainingsloss für Energie und Grenzen

[18-objective-energy-and-boundaries.svg](./18-objective-energy-and-boundaries.svg)

**Caption:** Energy-shape and endpoint losses in the differentiable training
objective. A piecewise-linear target in RMS decibels joins the source start
level to a valley and then to the target end level. The loss measures
normalised squared deviations at frame level and at both endpoints.
The plotted levels are illustrative, not measured experiment results.

**Quelle:** `_frame_rms_db`, `_u_shaped_energy_target` und
`DifferentiableTransitionObjective.forward` in
[differentiable.py](../../../src/control/differentiable.py).

Die Leistungswerte werden über Stereokanäle gemittelt und mit adaptivem
Average-Pooling in T Frames aufgeteilt. Daraus entsteht ein RMS-dB-Verlauf;
es wird nicht erst das Stereo-Audiosignal zu Mono addiert.
Startwert ist der erste Source-Frame, Endwert der letzte Target-Frame.
Die theoretische Talsohle liegt `6 dB` unter dem kleineren Endpunktwert.
Die mathematische Zielkurve ist stückweise linear, also V-förmig in dB.
Bei geradem T muss kein Frame exakt in der Talmitte liegen.

`L_energy = mean(((rendered_dB-target_dB)/12)^2)` mit Gewicht `1.0`.
`L_boundary` ist das Mittel der quadrierten Endpointdifferenzen, jeweils
durch `6 dB` normalisiert, mit Gewicht `0.5`. Dieser Boundary-Loss ist
kein Sample-Click-Detektor. Die im Diagramm verwendeten Pegel -6/-3 dBFS
und der gezeichnete gerenderte Verlauf sind synthetische Lehrbeispiele.

## 19 — Control-Regularisierung und Clipping

[19-control-and-clipping-losses.svg](./19-control-and-clipping-losses.svg)

**Caption:** Control regularisers and clipping penalty in the proxy objective.
Mix and low-end handover increments are regularised relative to a uniform
step; curvature penalises changes of increments, and monotonicity penalises
negative increments. A separate sample-domain term penalises excursions
beyond full scale. These are training penalties rather than bounded quality scores.

**Quelle:** [DifferentiableTransitionObjective.forward](../../../src/control/differentiable.py).

Mit `u=1/(T-1)` ist die sogenannte Smoothness hier ausdrücklich eine
Abweichung von **gleichmäßigen Inkrementen**, kein beliebiger Audio-
Glättebegriff. Gewichte: Smoothness `0.02`, Curvature `0.05`, Monotonicity
`0.1`, Clipping `2.0`. Die Controlterme beziehen sich auf Mix- und
Low-End-Position, nicht automatisch auf sämtliche EQ- oder Vocal-Ausgänge.
Bei konstruktiv monotonen Kurven kann die Monotonicity-Strafe null sein.
`relu(abs(y)-1)^2` ist eine weiche Overshoot-Strafe; die Berechnung selbst
führt kein hartes Clipping des Audios aus.

## 20 — Featurekonditionierte Terme von Objective v4

[20-objective-v4-conditioned-terms.svg](./20-objective-v4-conditioned-terms.svg)

**Caption:** Feature-conditioned Objective-v4 terms. Vocal overlap is
weighted by estimated activity and equal-power mix gains. Vocal-boundary
costs condition handover speed on entry/exit cues, and a transient proxy
conditions handover motion on onset and spectral-flux features. Validity
masks control which evidence contributes.

**Quelle:** `_conditioned_objective_terms`, `_vocal_strength` in
[differentiable.py](../../../src/control/differentiable.py).

Die Vocal-Grundstärke ist
`activity * prominence * (0.5 + 0.5*confidence)`.
Für die v4-Vocalterme erhalten beide Seiten zusätzlich die gemeinsame
Maske `vocal_valid_A * vocal_valid_B`. Overlap ist das Mittel von
`s_A*s_B*(gain_A*gain_B)^2`; die Gains folgen der Mix-Position über
Equal-Power-Cos/Sin. Der Boundaryterm kombiniert die normierte Mix-
Übergaberate mit Source-Cutkosten und Target-Entrykosten. Source-Cutkosten
verwenden `1-offset`, Targetkosten zusätzlich `(1-onset)` und
`0.25+0.75*phrase_progress`. Der Transiententerm verwendet gemittelte
Intervallwichtigkeit aus `max(flux,onset)` beider Seiten, die gemeinsame
Audio-Gültigkeit und `mix_rate + 0.5*low_rate`.

Defaultgewichte sind `1.0 / 0.30 / 0.08`. Fehlen beide Featuretensoren,
sind die drei Terme exakt null; nur ein fehlender Tensor wird als Fehler
abgelehnt. Die gültigkeitsbezogene `conditioning_valid_fraction` ist eine
Diagnose und kein zusätzlich gewichteter Loss.

## 21 — Stem-basierte Vocal-Losses von Objective v5

[21-objective-v5-vocal-losses.svg](./21-objective-v5-vocal-losses.svg)

**Caption:** Stem-aware vocal penalties in Objective v5. Estimated vocal
strengths are weighted by the relative RMS activity of the separated stems.
Overlap discourages two strong audible vocals, audibility discourages
unnecessary attenuation, and the phrase-conditioned gain-change term
discourages changes inside active vocal phrases. Default v5 disables the two
feature-vocal penalties inherited from v4.

**Quelle:** `VocalAwareTransitionObjective.forward`,
`_normalised_stem_strength` in [differentiable.py](../../../src/control/differentiable.py),
[variabler Objectiveadapter](../../../src/control/variable_differentiable.py).

Hier sind `s_A/s_B` die Vocal-Grundstärken mit jeweils eigener Validitätsmaske
und eigener Stem-RMS-Gewichtung. Stem-RMS wird pro Beispiel am maximalen
Frame-RMS normalisiert; praktisch inaktive Stems erhalten null. Die
tatsächlichen Vocal-Gains `g_A/g_B` enthalten Vocal-Übergabe und Ducking.

Overlap-Gewicht `1.0` multipliziert
`mean(s_A*s_B*(g_A*g_B)^2)`.
Audibility-Gewicht `0.5` multipliziert
`mean(s_A*(1-0.75*s_B)*(1-g_A)^2 + s_B*(1-0.75*s_A)*(1-g_B)^2)`.
Ein allein aktiver Vocal wird dadurch stärker vor unnötiger Absenkung
geschützt; ein aktiver Gegenvocal reduziert dieses Gewicht, hebt es aber
nicht vollständig auf. Mid-Phrase-Gewicht `0.2` multipliziert die mit
`s_A*(1-offset_A)` bzw. `s_B*(1-onset_B)` gewichteten quadrierten
Gain-Inkremente; `mid` bedeutet Mittelwert benachbarter Featurebins.

Die v5-Basiskonfiguration setzt v4-`vocal_overlap_weight` und
`vocal_boundary_weight` auf **null**. Deshalb bedeutet der gespeicherte
Key `loss_v4` den Basisklassenteil unter der verwendeten v5-Konfiguration,
nicht automatisch einen unveränderten Standard-v4-Loss. Der Transiententerm
bleibt erhalten. Der variable Adapter setzt die Framezahl auf das tatsächliche
T und verwendet die vorhandenen Mittelwertreduktionen; er dividiert nicht
pauschal noch einmal den gesamten Loss durch T. Daraus folgt keine garantierte
numerische Vergleichbarkeit aller unterschiedlichen Trainingsverträge.

## 22 — Experimentelle Cue-Ranker-Metriken

[22-experimental-ranker-metrics.svg](./22-experimental-ranker-metrics.svg)

**Caption:** Evaluation of a cue ranker against a frozen teacher on identical
candidate groups. The synthetic example distinguishes exact top-1 agreement,
top-k set overlap and teacher-ordinal NDCG. Score correlation and selected
teacher utility are reported separately. Teacher agreement is not evidence
of perceptual transition quality.

**Quelle:** `_metric_bucket`, `_ordinal_gains`, `_pearson` in
[cue_ranker_runner.py](../../../src/ml/cue_ranker_runner.py).

Top-1 prüft die exakte erste Candidate-ID; Top-k ist der Schnitt der beiden
Top-k-Mengen geteilt durch `min(k,group_size)`. Für NDCG verwendet dieser
Code **ordinale Gains N,N-1,...,1**, keine Exponential-Gains aus rohen
Teacherutilities. Position i zählt ab 1, Discount ist `log2(i+1)`.
Gleichstände werden über Candidate-ID sortiert. Das Beispiel A/B/C/D gegen
B/A/D/C ist erfunden und explizit als Illustration markiert:
Top-1 `0`, Top-2 `1`, NDCG@2 rund `0.937`.

Gruppen mit weniger als zwei Kandidaten werden ausgeschlossen. Gruppenmetriken
werden gemittelt, global und je Länge; Pearson wird auf den endlichen
Score-/Utility-Paaren der gültigen Gruppen gepoolt. Bei konstanten Scores ist
die Korrelation `None`, nicht null. Guard-Rejections dienen als negative
Anker unterhalb gültiger Teacherutilities, technische Teacherfehler werden
nicht als normale Labels behandelt. Der reale Cue-Ranker-Qualitätsnachweis
bleibt unetabliert; die Grafik zeigt keine neue Realmessung.

## 23 — Menschliche Bewertung und Zusammenfassung

[23-human-rating-summary.svg](./23-human-rating-summary.svg)

**Caption:** Descriptive summaries of a completed blinded listening study.
The answer key maps public labels to methods. Preferences are summarised as
method wins and ties, while criterion scores yield per-method summaries and
paired candidate-minus-reference differences. These summaries preserve the
study's sampling and rater limitations.

**Quelle:** [analyze_control_study.py](../../../src/evaluation/analyze_control_study.py),
[Ratingformat](../../../src/evaluation/control_study_ratings.py).

Eine Entblindung ist nur nach vollständig bewerteten Paaren zulässig.
Präferenzraten schließen Gleichstände aus: Methodensiege geteilt durch
Anzahl entscheidender Urteile. Sind alle Urteile Gleichstände, ist diese
Rate `None`. Kriterien werden getrennt mit Anzahl, Summe, Mittelwert,
Minimum und Maximum zusammengefasst; „Overall“ poolt alle Kriterienwerte.
Delta ist **Kandidat minus Referenz**. Die fünf aktuellen Kriterien sind
Sauberkeit, Energieform, Low-End-Übergabe, Vocal-Klarheit und Artefaktfreiheit.
Historische Formate enthalten zusätzlich Rhythmik. Eine 5 bedeutet hier,
dass kein entsprechendes Problem aufgefallen ist, nicht musikalische
Perfektion. Ordinale Ratingmittel sind deskriptive Zusammenfassungen,
keine Signifikanztests; wiederverwendete Cue-/Trackpaare sind nicht unabhängig.

## Wiedererzeugen und prüfen

```powershell
.venv\Scripts\python.exe -X utf8 docs/figures/flowcharts/generate_metric_figures.py --preview-dir output/metric_figure_previews_20261029
```

Der [Metrikgenerator](./generate_metric_figures.py) verwendet die Zeichen-
und Layoutprüfungen des [Basisgenerators](./generate_flowcharts.py).
Er schreibt nur die neuen SVGs 12–23; die vorhandenen Pipeline-SVGs bleiben
unverändert. Das Energiebeispiel wird mit Matplotlib als Vektorplot erzeugt.
Die SVGs besitzen editierbaren Text und dieselbe 160-mm-Nennbreite wie die
erste Serie. PNGs/Kontaktbogen dienen ausschließlich der Sichtprüfung.

Synthetische Rechnungen wurden zusätzlich gegen Produktionshelfer geprüft:
Defaultgewichte, Songscore, lokale High-Power-/Non-Overlap-Berechnung,
Grenzglätte, neutrale Rhythmik, Energiezielkurve, Validitätsmasken,
Stemstärke, NDCG/Top-k und deskriptive Ratingsummary. Es wurden dabei keine
Audiodateien, Dataset-NPZs, Antwortschlüssel, echten Ratings oder Gewichte
gelesen und keine neuen Qualitätsresultate beansprucht. Der Ablauf steht in
[Bemerkungen.md](../../Bemerkungen.md).
