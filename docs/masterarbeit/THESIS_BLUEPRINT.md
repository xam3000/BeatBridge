# BeatBridge thesis blueprint

**Date:** 2026-09-16. **Status:** planning document for review; no chapter prose is authorised by this document. The existing title metadata and LaTeX sources are preserved; the exact registered English title remains to be verified. [A3]

## 1. Argument and research questions

The proposed argument is that a controller can learn time-dependent mixing controls from beat-synchronous features without ground-truth control curves, because a differentiable renderer connects those controls to a fixed proxy objective. The repository supports a bounded feasibility claim and an analysis of proxy limitations. It does not yet establish that trained controllers produce perceptually better transitions or reduce the work of preparing dance mashups. Cue point selection remains a separate upstream problem. These distinctions follow the controller-focused project decision, the implemented training paths, and the evidence inventory below. [A2, P1, P2, P3, R1–R3, H1–H6]

**Primary research question:** To what extent can time-dependent, interpretable mixing controls be learned without ground-truth control curves through a differentiable renderer and a fixed proxy objective, and what evidence supports their usefulness for short transitions between selected song sections?

1. **SQ1 — Learning and control:** For fixed cue points and a specified rendering protocol, can a feature-conditioned controller improve the proxy objective over a matched unlearned baseline while maintaining its control constraints, and which input features and control mechanisms contribute to that behaviour?
2. **SQ2 — Perceptual validity:** Under matched comparison conditions, do improvements in the proxy objective correspond to listener preference and the rated properties of the rendered transition, and where do they fail to correspond?
3. **SQ3 — Transition length:** How does the separate length-conditioned controller behave across its supported two-, four-, six-, and eight-bar settings, assessed within that path against a compatible baseline?

SQ1 is partly answerable from the existing real training runs; causal feature/control attribution still needs ablations. SQ2 has exploratory evidence for direct curve optimisation, but no completed local formal rating set for a learned controller. SQ3 has documented real training and technical checks, whose primary artifacts are absent from this checkout; perceptual evaluation remains outstanding. Six and eight bars are extension conditions, not substitutes for the assignment's one-to-four-bar requirement. No question presupposes a positive result. [R1–R6, H1–H6, A1]

The assignment's representation evaluation is operationalised under SQ1 as a controlled comparison or ablation of input representations within one otherwise matched control path. Its transition-metric evaluation is operationalised under SQ2 as a test of whether the fixed proxy and related scores agree with perceptual judgements under declared conditions. These mappings do not assert that either experiment has already been completed. [A1, P1, P4, P5, P7]

### Precise problem statement

Given an ordered pair of selected sections from **track A** (the source or outgoing track) and **track B** (the target or incoming track), a pair of **cue points**, a transition length, and admissible analysis/alignment data, determine how to transfer the audible contribution from A to B over a **transition window**. In the implemented bridge convention, the source window begins at cue A and contains its postroll; the target window ends at cue B and contains its preroll. The retained section of A precedes the window, and the retained section of B follows it. This convention specifies coordinates; it does not establish that the cues coincide with semantically detected drops. [P1, P4]

For candidate `c`, let `X_A`, `X_B`, and `g` be its feature sequences and global pair features, and let `w_c` contain the aligned mix waveforms and, where applicable, estimated vocal stems. The **controller** predicts controls `u_c = f_theta(X_A, X_B, g; L)`; the separate **renderer** produces `y_c = R_p(w_c, u_c)`. The intended training formulation is:

```text
minimise over theta: mean over training examples c of
                    J_p(R_p(w_c, f_theta(X_A, X_B, g; L)), w_c, X_A, X_B)
```

Here `p` identifies one compatible feature, control, alignment, renderer, sample-rate, and objective contract. Length `L` is an explicit condition only in the variable path. The **proxy objective** `J_p` and renderer are fixed during a run; the controller parameters are learned. Objective versions changed during development, so “fixed” does not mean one unchanged objective across the whole project. Direct per-example optimisation adjusts `u_c` itself and must be reported separately from learning a reusable controller. The input waveforms enter the renderer/objective, not the controller. [P1–P3; `src/ml/training.py`, `src/ml/variable_training.py`]

“Interpretable” means that the output variables have explicit mixing meanings, such as mix position, low-end handover, equalisation, and vocal ducking. It is not an evaluated claim that users understand or prefer these controls. “Self-supervised” is used operationally for training without target control curves or human quality labels, using a designed audio/control loss. This is not evidence of a pretrained self-supervised music embedding or an independently learned perceptual metric. [P1–P3, P4]

The **candidate ranker** acts before this conditional control problem: it scores admissible cue-point candidates and chooses which window to render. Its frozen teacher also uses a controller, renderer, and proxy objective. Consequently, agreement with that teacher measures reproduction of the teacher's preferences, not independent musical quality. **Perceptual evaluation** means recorded human judgements of rendered audio under a specified study protocol. [P5, P6]

## 2. Assignment alignment, scope, and non-goals

The official assignment is the scope authority. The July controller-focused decision supplies the scientific emphasis but does not prove that the supervisor waived the assignment's representation, interaction, or evaluation requirements. A narrower final deliverable requires a recorded scope decision. [A1, A2, A3]

| Assignment requirement | Position in this argument | Current boundary / completion requirement |
|---|---|---|
| Learn or use self-supervised audio representations; assess their quality | SQ1, Sections 2.4, 3.4, and 5.5 | Named handcrafted features and pretrained separation support the present controls. They are not evidence of evaluated self-supervised embeddings. A controlled representation experiment and source audit remain required, or an explicit scope amendment. [P4, A3] |
| Develop and assess a transition metric | SQ2, Sections 3.5–3.8 and 5.5–5.6 | Separate candidate feature score, rendered-audio score, training proxy, and teacher utility. Small direct-optimisation listening studies supply limited feedback; no general validity or real learned-ranker superiority follows. [P1, P5–P7, H1–H4] |
| Automatically generate and compare short transitions | SQ1–SQ3 | Fixed four-bar controllers are the core. The variable path covers 2/4/6/8 bars. One-/three-bar learned control and evaluated end-to-end coverage remain missing. Generic positive-length baseline APIs and a historical one-bar candidate example do not close that gap. [P1–P4, P7, A2] |
| Hard cuts, crossfades, and tempo-adjusted transitions | Baselines and engineering context | Implemented baseline paths can provide controls for comparison; each experiment must identify the actual renderer used. `tempo_fade` is a linear-fade alias, not a fourth independent scientific strategy. [P7] |
| Automatically analyse tempo, beats, and bars; display beats, bars, and segment boundaries | Upstream infrastructure and required engineering contribution E3 | Backend tempo/beat/bar analysis and provenance exist, subject to documented grid limits. A validated segment-boundary path and the GUI display are not demonstrated. The final workflow must expose the available analyses and mark missing boundaries rather than infer them. [A1, P4, P7, P8] |
| Multiple songs, GUI selection of sections, preview, final mashup audio export | Required engineering contribution E3 | Batch previews and study interfaces are partial infrastructure. The graphical user interface (GUI), section workflow, sequence assembly, and final export remain a specification, not a demonstrated complete user workflow. [P8, A3] |
| Evaluate correction effort and usefulness for dance performances | Sections 3.8, 5.7, and 6.5 | Still required: implemented workflow, example mashups, task definitions, appropriate users, recorded corrections/time, and actual dance-use judgements. Listening cleanliness alone does not answer either requirement. [A1, P8] |

### Scientific scope

The primary experimental object is one directed transition under fixed cues, with separate analysis of selection when ranker evidence becomes available. The core case is a four-bar window in 4/4. The variable path is a separate protocol family with explicit length conditioning. The target population of any current empirical statement is limited to the selected local examples and their inclusion rules; a broad genre, tempo, or dancer population is not established. [P1–P5, D1–D3]

The control variables, proxy terms, constraints, and renderer are jointly part of the method. Comparing different complete paths can answer a system-comparison question after matching stimuli and playback conditions; it cannot isolate architecture. Architecture claims require holding features, data, splits, renderer, objective, alignment, training budget, and selection rules constant. Proxy losses from incompatible paths must remain in separate tables. [P1–P4, R1–R6]

Explicit non-goals are autonomous composition of whole pieces, a professional DJ system, unrestricted multitrack production, arbitrary metres, causal real-time performance, and training a new source separator or foundation model. These limits do not remove the minimal GUI, final mashup export, representation assessment, or user evaluation required by the assignment. The offline controller formulation uses a complete transition window; no latency claim is proposed. [A1, A2, P3, P8]

## 3. Evidence inventory and its limits

### Evidence rules and source index

**V** means the specified local primary files were inspected in this audit; the exact verification is stated below. **D** means a dated repository audit reports the result, but the primary artifacts were unavailable locally. **I** means code/protocol inspected: implementation is supported, execution is not established by that inspection. **P** means proposed work with no result. These are evidence classes, not a single progress scale: implementation, technical verification, real training, proxy evaluation, and perceptual evaluation are separate states.

Repository identifiers in square brackets are internal evidence references, not bibliography keys. Paths are relative to the repository root unless linked otherwise. No external literature claim is introduced as established by this planning document.

| ID | Source inspected and role |
|---|---|
| A1 | [Official assignment, all three pages](../../angepasste_aufgabenstellung_masterarbeit.pdf): problem, deliverables, evaluations, and non-goals. |
| A2 | [Project overview](../Projekt-Gesamtuebersicht.md), especially the dated scope clarification; [STATUS](../STATUS.md), interpreted chronologically rather than as uniformly current. |
| A3 | [Thesis setup audit](THESIS_SETUP_AUDIT.md); [LaTeX main file](../../overleaf/CGThesis.tex), all chapter files, [bibliography](../../overleaf/bibliography.bib), and [German methodology draft](methodik.tex). These describe writing state, not experimental proof. |
| P1 | [Differentiable control protocol](../DIFFERENTIABLE_CONTROL_PROTOCOL.md), [ML baseline protocol](../ML_CONTROL_MODEL_PROTOCOL.md), [training implementation](../../src/ml/training.py). |
| P2 | [Vocal control protocol](../VOCAL_CONTROL_MODEL_PROTOCOL.md), [vocal runner](../../src/ml/vocal_runner.py). |
| P3 | [TCN/BiLSTM protocol](../TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md), [model state](../ML_MODEL_CURRENT_STATE.md), [variable loss path](../../src/ml/variable_training.py), [variable waveform contract](../VARIABLE_WAVEFORM_CACHE_PROTOCOL.md). |
| P4 | [Feature v1](../FEATURE_PROTOCOL.md), [feature v2](../FEATURE_PROTOCOL_V2.md), [dataset v1](../DATASET_PROTOCOL.md), [dataset v2](../DATASET_PROTOCOL_V2.md). |
| P5 | [Ranker dataset/production contract](../CUE_RANKER_DATASET_PROTOCOL_V3.md), [teacher/model contract](../CUE_RANKER_MODEL_PROTOCOL.md), [synthetic end-to-end test source](../../tests/test_cue_ranker_e2e_smoke.py), and 2026-08-26/27 audits in A2/[experiment log](../Bemerkungen.md). |
| P6 | [Control study protocol](../CONTROL_STUDY_PROTOCOL.md), public study manifests and ratings; completed result files for H1–H4; incomplete local ratings for H5; and the documented but locally absent pending studies H6. |
| P7 | [Candidate protocol](../CANDIDATE_PROTOCOL.md), [ranking protocol](../RANKING_PROTOCOL.md), [rendered metric protocol](../RENDERED_TRANSITION_METRIC_PROTOCOL.md), [rendering protocol](../RENDERING_PROTOCOL.md). |
| P8 | [GUI specification](../GUI_SPECIFICATION.md), explicitly a design; A1 and A3 identify the outstanding workflow/evaluation requirements. |

### Datasets and dependence

| ID / class | Dataset and evidence | Interpretation |
|---|---|---|
| D1 / V metadata | `output/datasets/feature_protocol_v1_top3_4bar_track_split_20260731/manifest.json`; ID `f9044dc259b7296c8b28`; 45 train / 9 validation / 9 test examples | Manifest read; its hash matches R1/R2. Dataset payloads were not reopened. Historical test listening is H3; these tracks are not a fresh final controller test. |
| D2 / V metadata | `output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805/manifest.json`; ID `52bc9d1cebfd1b82d2ea`; 370/50/60 examples | Manifest read and hash matches R3. It records 1,110 selected candidates, 630 cross-split rejections, and train-only normalisation. Prior audit reports 43/5/7 used track hashes. Counts are not independent sample sizes. |
| D3 / D | `output/datasets/variable_v2_strict_20260820_selected_roformer_run01/manifest.json`; ID `2a9679f687c50696692b`; P4 and 2026-08-21 audit | Reported 105 train / 12 validation / 21 test per length; 552 examples overall. Split authority covers 87 tracks, with 53 used in exported examples. Primary dataset absent locally; no fresh tensor/split audit. |

The documented expanded inventory has 119 FLAC paths and 111 unique BPM-eligible sources after a policy exclusion, one duplicate, and six tracks below 145 beats per minute (BPM). The selected corpus therefore reflects a narrow tempo filter, top-ranked pair/cue selection, and local availability. The strict variable export additionally rejects unreliable grids, changing the population relative to D2. These inventory figures are dated audit reports, not a fresh corpus census. Rights, distribution permissions, and representative genre/artist coverage remain unresolved. [A2, P4, D2, D3]

Audio-file SHA-256 separation prevents reuse of an identical hashed file across splits under the recorded policy. It does not by itself establish independence of different encodings, edits, remixes, or recordings of the same musical work. Repeated cues, reversed pairs, shared tracks, and multiple lengths create dependence. A final exposure ledger must reconcile splits across dataset versions and studies, including whether any supposedly new test tracks have already influenced development. [P4; proposed validity requirement]

Do not claim that the entire project's test data were never touched. D1 test audio was used in H3. The August documentation reports D2 test vocal-cache materialisation even though training excluded it. D3 test feature shards were exported, while its subsequent waveform/training audit reports only train/validation access. The separate cue-ranker contract forbids materialising test examples in that path. These are different stages and different claims. This audit read existing v1 root metadata and historical completed study results, but opened no test shard or test audio. [A2, P4, P5]

### Controller families and real training

The abbreviations below are multilayer perceptron (MLP), temporal convolutional network (TCN), bidirectional long short-term memory network (BiLSTM), and equalisation (EQ).

| Path | Scientific treatment | Evidence state |
|---|---|---|
| Fixed `time_shared_mlp_v1` | Feature v1: 32 × 54 per track, 16 globals; two monotone position curves; two-band renderer; objective v4 | Implemented; real training and validation proxy evaluation locally verified in R1. |
| Fixed `vocal_time_shared_mlp_v2` | Same feature geometry; mix/low-end/vocal positions and separate vocal ducking; estimated stems; vocal-aware renderer; objective v5 | R2/R3 locally verified with historical Demucs contract. Later RoFormer run is documented, not locally reverified (R4). |
| Fixed `tcn_bilstm_transition_control_v1` | Feature v1; ten controls used by a low/mid/high-band renderer; objective v4; generic training applies vocal ducking to a mid-band proxy without stems | Implementation inspected; real Full-Band training reported by prior audit (R5). Not an established architecture winner. |
| Variable `variable_tcn_bilstm_transition_control_v1` | Feature/dataset v2; `T=8L`, `L ∈ {2,4,6,8}`, separate `L/8` condition; local-grid waveform contract; vocal-aware renderer and time-normalised objective v5 | Implementation inspected; real completed runs reported in R6. The ten diagnostic channels do not make this the fixed Full-Band EQ path. |
| Variable `variable_time_shared_mlp_v1` | Compatible small vocal-aware variable baseline for a future within-path architecture comparison | Implemented; no real run identified in the inspected local inventory or cited model-state audit. Training/comparison remains P. |

The locally inspected R1–R3 contracts use 11,025 Hz training waveforms. The fixed study exports use 44.1 kHz; the separately documented variable study uses 11,025 Hz and transition-window-only audio. Output sample rate and context must be explicit in every comparison. No inference of full-band perceptual performance from low-rate training loss is licensed. [R1–R3, H5–H6, P3]

| ID / class | Exact run under `output/training_runs/` | Supported observation |
|---|---|---|
| R1 / V | `time_shared_mlp_v1_objective_v4_seed20260804_20260804/` | `early_stopped`; best epoch 8, last 14; validation proxy 0.305959 → 0.295999 relative to its equal-power initialisation. |
| R2 / V | `vocal_time_shared_mlp_v2_objective_v5_seed20260805_20260805/` | `early_stopped`; best 16, last 22; 0.267815 → 0.259337 relative to its vocal-model initialisation. |
| R3 / V | `vocal_time_shared_mlp_v2_extended_bpm145_165_top10_seed20260805_20260805/` | `early_stopped`; best 22, last 28; 0.359040 → 0.336999. Component trade-offs require reporting alongside this aggregate. |
| R4 / D | `vocal_roformer_extended_bpm145_165_top10_seed20260812/` | Prior audit reports best epoch 21, last 27. Restore manifest/history/checkpoints before a final numerical table; infer neither seed nor software version from the directory name. |
| R5 / D | `tcn_bilstm_transition_control_v1_full_band_extended_bpm145_165_top10_20260812/` | Prior audit reports best epoch 14, last 20. Earlier architecture-probe and later Full-Band runs are distinct experiments. |
| R6 / D | `variable_tcn_bilstm_waveform_v2_full_20260821/` and `variable_tcn_bilstm_v2_wandb_20260826/` | September 7 audit reports completed runs ending at epochs 20/29, minimum history validation at 14/23, and matching history/best-checkpoint hashes. This supersedes the historical two-epoch-only description, but is not a fresh local verification or a 100-epoch run. |

For each V run, `manifest.json` and `history.json` were read; history, best, and latest checkpoint bytes matched the manifest hashes; history minimum, selected epoch, and final epoch agreed; and the dataset-manifest binding matched. Checkpoints were not deserialised, and predictions/training were not rerun. The table supplies within-run evidence, not a ranking between rows. R4–R6 artifacts must be restored read-only for final results verification. [Verification record in Section 9]

### Listening evidence

All following paths are under `output/control_studies/`. A completed public audio export is not a completed perceptual evaluation.

| ID / class | Study and inspected files | Permitted claim and limit |
|---|---|---|
| H1 / V | `blind_v3_top8_4bar_20260729/`: ratings and results | One rating set, one rater, eight selected pairs: baseline 4, directly optimised 3, tie 1. Exploratory development evidence. |
| H2 / V | `blind_v4_control_v3_rubberband_top8_4bar_20260730/`: ratings and results | One rater, eight ties; prior protocol identifies reused development pairs. No observed preference difference in this set. Reduced proxy loss reported in A2 must be joined to its optimisation records before quantitative proxy/perception analysis. |
| H3 / V | `blind_v5_objective_v4_heldout_test9_4bar_20260731_rerun/`: public manifest, ratings, results | One rater preferred directly optimised curves in 9/9 cue examples; the recorded criterion difference is cleanliness. This was a held-out objective-development gate at that time, not evidence for a trained controller. P6 reports three audio hashes and repeated pair/cue observations; no nine-independent-trial or population claim. |
| H4 / V | `blind_v7_objective_v5_vocal_active6_20260805_rerun/`: ratings and results | Direct v5 control optimisation wins 2, v4 controls 1, ties 3; one rater. Vocal clarity differs in the saved summaries. Both use a vocal renderer, but control capacity and objective change together: this is not an isolated objective-term ablation. Time-stretch concerns are recorded listener observations, not an isolated causal backend experiment. |
| H5 / V | `blind_v6_mlp_v1_best_vs_equal_power_validation9_20260804_rerun/` and `blind_v8_vocal_mlp_v2_best_vs_initial_validation5_20260806/`: public manifests and ratings | Locally 0/9 and 0/5 rated; no completed results found. Both use validation data already involved in model selection. Informal impressions in A2 remain qualitative development notes. The earlier v6 folder without `_rerun` has six unrated examples despite its name. |
| H6 / D | `blind_all_models_validation_20260904/`; `blind_variable_tcn_lengths_20260904/` | September audit reports five fixed-path validation pairs × four methods at 44.1 kHz, and one variable validation pair per 2/4/6/8 bars × two methods at 11,025 Hz. Reported exports are technically checked; evaluations are pending. Neither root is present locally. Restore public manifests/ratings and verify current status before use. |

H1–H4 result counts were checked against completed rating counts, but no new listening, method-assignment reconstruction, or waveform validation was performed. Unrated answer keys were not opened. Existing rating scales also changed between studies; their overall criterion means must not be pooled as if they were one endpoint. [P6]

### Real cue-ranker evidence

The ranker implementation contains a grouped, teacher-labelled train/validation pipeline, synthetic end-to-end tests, checkpoint/resume checks, and optional learned inference. The August 27 audit reports synthetic verification; it does not report real teacher labelling or real ranker training. Later completed variable-controller runs do not establish that a complete teacher release or real ranker dataset was subsequently produced. The current local inventory supplies no such primary release/run evidence. [P5, A2, P3]

Before a real ranker claim, obtain the test-excluding pair index and full candidate universe, split authority, completed teacher best-checkpoint release, matching train-only normaliser, verified analysis/feature/vocal/waveform caches, and fixed backend provenance. Then produce immutable label, training, and evaluation artifacts. The contract's stratified labelled subset and inclusion probabilities must remain visible; results on it are not automatically results over every candidate. Guard rejections are negative anchors, whereas technical failures are excluded from quality labels. Agreement metrics, including normalised discounted cumulative gain (NDCG), must be accompanied by usable-group counts and failure coverage. Human evaluation with a fixed downstream controller/renderer is needed to test the value of cue selection. [P5]

## 4. Contributions and claim-to-evidence matrix

### Intended scientific contributions

- **S1 — Constrained control learning:** A formulation and implementation of learning feature-conditioned, time-dependent mixing controls through a fixed differentiable renderer/proxy without target curves. Current achievement: bounded real-data training feasibility. This is a project contribution, not a verified claim of being the first such method. [P1–P4, R1–R3]
- **S2 — Empirical analysis of the proxy's usefulness and limits:** A protocol-aware account of proxy changes, control behaviour, and human judgements, including null outcomes and component trade-offs. Current achievement: exploratory direct-optimisation findings and controller validation measurements. A positive learned-controller perceptual result and causal representation/control attribution remain open. [H1–H6, R1–R3]
- **S3 — Explicitly conditioned variable-length extension:** A separate formulation and assessment of control learning across the supported lengths with local-grid alignment. Current achievement: inspected implementation and prior documented real training. Generalisation to unseen lengths, one-/three-bar coverage, and perceptual benefit are not established. [P3, P4, R6]

### Intended software engineering contributions

- **E1 — Auditable experimental pipeline:** Versioned analysis, features, datasets, waveform caches, rendering, training/resume, and blinded-study artifacts. This supports traceability of results; artifact hashes alone do not prove scientific validity or fresh-machine reproducibility. [P1–P7, R1–R3]
- **E2 — Separate candidate-ranker infrastructure:** A teacher-release, grouped-data, training, and inference path that preserves the controller/selection boundary. Current achievement: implementation and historically documented synthetic verification, not a real evaluated ranker. [P5]
- **E3 — User-constrained mashup workflow:** The assignment's minimal GUI, section selection, preview, correction, and complete export workflow. Current achievement: specification and partial batch/review infrastructure only. This is an intended contribution requiring completion, not an accomplished result. [A1, P8]

Every contribution must retain the following evidence boundary when promoted into chapter prose.

| Contribution / intended claim | Existing evidence | Still-required experiment or artifact | Acceptance boundary |
|---|---|---|---|
| S1: control curves can be learned without target curves under explicit constraints | P1–P4 and inspected loss calls; R1–R3 manifest/history/checkpoint hashes | For final empirical reporting: checkpoint inference audit on declared examples, exported curves/constraint diagnostics, exact baseline definitions, and per-example/component measurements; repeat seeds before a stability claim | Supported now: the recorded runs reduced their validation proxy. Do not infer generalisation, universal constraints across all control channels, or perceived quality. |
| S2: the proxy supports useful development but has measurable limits | H1–H4 completed exploratory ratings; R1–R3 histories; H5 incomplete ratings; H6 reported prepared studies | Complete development ratings; predefine a fresh held-out learned-controller comparison with matched cues/audio; collect participants/conditions; report effects and uncertainty with track/pair/rater dependence. Retrain feature/control ablations under one contract; add a verified self-supervised representation comparison for the assignment | The direction of any final preference effect remains open. Direct optimisation is not learned-controller evidence; a null result remains reportable. |
| S3: length conditioning operates within a separate coherent variable protocol | P3/P4 code/contracts; D3/R6 prior audits | Restore and verify D3/R6/H6; train the compatible variable MLP if an architecture comparison is intended; per-length baseline, proxy, controls, failures, and listening outcomes; separately implement/evaluate 1/3 bars for assignment coverage | 2/4/6/8 are supported conditions in the contract. Observed training lengths do not establish unseen-length generalisation. Do not compare v1/v2 raw losses as architecture scores. |
| E1: results can be traced to inputs and processing contracts | Nine local run-file hash checks and three dataset bindings; P1–P7; study counts | Restore later artifacts; portable reproduction manifest, dependency/model/backend identities, rights decisions, and a clean-environment reproduction where claimed | Claim audited provenance for specified artifacts, not universal reproducibility, bitwise CUDA determinism, or redistribution permission. |
| E2: ranker stages are implemented separately from control generation | P5 code and synthetic test source; historical synthetic audit | Real release/universe/normaliser/caches; real train/validation labels and run; baselines on identical labelled groups; independent cue-choice listening with a common downstream renderer | Technical readiness is distinct from real training, teacher agreement, and perceptual usefulness. No learned ranker advantage is currently supported. |
| E3: users can assemble and correct a mashup with the prototype | A1, P8 design; current batch/study infrastructure documented in A2/A3 | Working GUI/section/sequence/export artifacts and acceptance checks; matched user tasks with a manual baseline, correction/time records and quality safeguards; dance-use study materials and results | Until completed, report a design and a requirement gap. Neither a mockup nor WAV previews demonstrate reduced effort or dance usefulness. |

### Evaluation sequence implied by the argument

1. **Freeze the comparison contract.** For each study, identify data/exposure history, cues, features, stems, alignment, renderer, objective, sample rate, context, normalisation, baseline, and checkpoint rule. Keep the fixed and variable studies separate. [P1–P6]
2. **Establish technical feasibility and within-path learning.** Use manifested real histories and curve checks, with synthetic tests serving only implementation verification. A direct optimiser is a comparator under a declared budget, not a guaranteed upper bound or target-curve provider. [P1, R1–R3; proposed comparison rule]
3. **Complete development comparisons, then freeze final choices.** H5/H6 can guide development; they cannot become independent held-out evidence by changing their name. Record the choice before exposing any final test outcomes. [P6]
4. **Conduct a fresh held-out controller evaluation.** Define independent track/work identity and prior exposure, recruitment, experience, consent, listening setup, primary preference endpoint, secondary criteria, order balancing, exclusions, effect estimates, uncertainty procedure, and handling of ties/multiplicity in advance. No participant count or significance test is asserted here. This plan does not start a study or unseal data. [A3, P6; proposed completion work]
5. **Assess representations and cue selection separately.** Match the controller contract for representation ablations; hold the controller and renderer fixed when comparing candidate rankers. A teacher-agreement study can characterise distillation but cannot validate the teacher itself. [P5; proposed experiments]
6. **Close the user-workflow requirement.** Evaluate complete example mashups, correction effort, and dance usefulness after the minimal workflow exists. Treat these outcomes separately from short-window preference. [A1, P8]

## 5. Section-by-section thesis outline

The outline follows the existing seven-chapter LaTeX structure. “Central claim” below means the planned role or a conditional result to establish; it is not permission to write an unsupported finding. Existing labels, citations, and evidence TODOs should be retained during subsequent drafting. [A3]

### Front matter

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| German and English abstracts | Summarise the final problem, method, strongest result, and limitation | Write last from the final S1–S3 evidence; do not promise a quality advantage or completed GUI. |

### 1. Introduction

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 1.1 Problem and Motivation | Introduce the assignment's short-transition task | The project targets selected sections for dance mashups; actual effort/quality benefits require evaluation. A1. |
| 1.2 Research Questions | State the primary question and SQ1–SQ3 | Conditional control, perception, and length are distinct tests; upstream selection is separately scoped. Section 1 above. |
| 1.3 Approach and Intended Contributions | Present the controller–renderer–proxy chain | S1–S3 and E1–E3 have different achievement levels; use the final matrix. |
| 1.4 Scope and Non-Goals | State assumptions and assignment gaps | Four-bar core, separate variable extension, explicit pending representation/GUI/1–3-bar/user evidence. A1–A3. |
| 1.5 Thesis Structure | Explain the argument's progression | Method defines the experiment, implementation realises it, results supply evidence, discussion limits the answer. |

### 2. Background and Related Work

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 2.1 Terminology and Conceptual Foundations | Define the listed terms and required signal-processing concepts | Separate cue selection, control prediction, rendering, proxy evaluation, and perception; source general facts from verified publications. |
| 2.2 Direct work on sequencing, mixing, and transition rendering | Compare the closest prior tasks and supervision | Position this formulation by input, output, supervision, and evaluation, not by unsupported novelty. Primary-source audit required. |
| 2.3 MIR front-end analysis for transition candidates | Explain analysis dependencies | Grid, section, and cue estimation are upstream inputs whose correctness is not guaranteed by control learning. P4/P7 plus verified literature. |
| 2.4 Self-supervised audio and music representation learning | Distinguish representation learning from the present loss-driven controls | A proposed embedding experiment is distinct from the currently used engineered features and estimated stems. A1/P4; literature/evaluation TODO. |
| 2.5 Compatibility and mashability as learned objectives | Define the relationship between scoring tasks | Candidate compatibility, proxy utility, and output preference are different constructs; no universal equivalence claimed. P5/P7; sources pending. |
| 2.6 Stem separation, differentiable DSP, and controllable generation | Position interpretable controls and enabling models | Separation is supporting technology; the thesis learns controls through a fixed renderer. P1–P3; source/version audit pending. |
| 2.7 Transition evaluation and research gap | Derive comparison axes from verified work | The defensible project question is whether this particular proxy-trained controller is useful; “first” or “unexplored” needs separate literature evidence. |

### 3. Methodology and System Design

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 3.1 Research Design and Evidence Boundaries | Define experimental stages and units | Synthetic tests, real training, validation development, and held-out evaluation answer different questions. R/H inventory. |
| 3.2 Problem Formulation and System Overview | Formalise cues/windows, controls, rendering, and loss | The controller is trained conditionally on an already selected candidate; candidate ranking is upstream. P1/P5. |
| 3.3 Corpus, Data Governance, and Splits | Specify inclusion and isolation | SHA-based splitting and train-only normalisation are necessary recorded rules; work identity, exposure, rights, and dependence still need audit. D1–D3. |
| 3.4 Audio Analysis, Alignment, and Representations | Define inputs and missingness | Feature semantics and local-grid alignment are explicit; unavailable phrase channels and uncalibrated vocal heuristics are not semantic ground truth. P3/P4. |
| 3.5 Candidate Generation and Ranking | Specify admissibility, baseline, and optional ranker | A learned score approximates a frozen teacher on a labelled subset; real effectiveness is pending. P5/P7. |
| 3.6 Transition Controllers, Renderers, and Proxy Objective | Define each complete method family | Fixed two-band, fixed vocal, fixed Full-Band, and variable vocal paths have distinct contracts. P1–P3. |
| 3.7 Baselines and Training Procedure | Define fair comparisons and checkpoint choice | Use manifest-defined initialisations, equal power, and budgeted direct optimisation; no cross-protocol loss league table. R1–R6. |
| 3.8 Evaluation Design | Operationalise proxy, perception, representation, ranking, and user outcomes | Predefine the missing studies and dependence-aware analysis; no invented participants/tests. Section 4 and A1. |
| 3.9 Reproducibility and Artifact Provenance | Define the evidence chain | Trace an outcome through study/run, checkpoint, dataset, features, audio identity, and backend contract. E1. |

### 4. Implementation

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 4.1 Software Architecture and Data Flow | Map method stages to actual modules | APIs encode stage boundaries; available entry points do not prove completed runs. Code/P1–P7. |
| 4.2 Analysis, Caches, and Provenance | Explain cached inputs and rejection behaviour | Reuse is conditional on matching provenance; missing data are not silently fabricated. P3–P5. |
| 4.3 Candidate Generation and Ranker Integration | Describe the default and optional selection paths | Feature ranking remains distinct from the optional synthetic-verified learned path. P5/P7. |
| 4.4 Controllers and Rendering Pipeline | Explain output-to-audio mappings | Ten-channel output shapes do not imply identical renderer semantics. P2/P3 and inspected loss calls. |
| 4.5 Training, Inference, and Experiment Tracking | Explain selection, resume, and artifacts | Local run contracts/history/checkpoint binding are authoritative; filenames and dashboards are insufficient. R1–R6/E1. |
| 4.6 Interaction Workflow and Export | Document actual user operations | Distinguish existing batch/review functions from planned section editing and final sequence export. E3; replace TODOs only after verification. |
| 4.7 Reproduction Environment | State exact requirements and platform limits | Use recorded versions, weights, binaries, and commands; rights and fresh-environment reproduction remain conditions. E1. |

### 5. Experimental Setup and Results

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 5.1 Evidence Inventory and Comparison Conditions | Establish what was actually run | A claim has a primary artifact and an explicit V/D boundary; recover D artifacts before final numerical reporting. |
| 5.2 Corpus and Run Configuration | Report selected populations and settings | Example, pair, track, and rater counts are distinct; separate D1–D3 and protocol families. |
| 5.3 Technical Validity and Constraint Compliance | Report technical checks | Finite outputs, constraints, cache/hash checks, and synthetic integration establish technical properties only; 1/3-bar evidence pending. |
| 5.4 Controller and Proxy-Objective Results | Answer the measurable part of SQ1 and SQ3 | R1–R3 show within-run decreases; report components and failure cases. R4–R6 need artifact recovery; causal ablations pending. |
| 5.5 Representation, Metric, and Candidate-Ranking Results | Report assignment-facing component experiments | No real learned-ranker or embedding-quality result currently supported; retain placeholders rather than synthetic substitutes. |
| 5.6 Perceptual Evaluation | Answer SQ2 at the justified level | H1–H4 are small direct-optimisation studies; learned-controller development/final outcomes remain pending. |
| 5.7 Manual Correction Effort and Dance Usefulness | Address user-facing assignment outcomes | No supported result yet. Report completed tasks and quality/effort outcomes only after E3 and its study. |
| 5.8 Failures and Negative Results | Report limits without selective presentation | Preserve early control failures, ties, proxy trade-offs, alignment failures, and incomplete ratings with exact provenance. |

### 6. Discussion and Limitations

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 6.1 Answers to the Research Questions | Give bounded answers in question order | Feasibility, perception, and length conclusions must not exceed Chapter 5. |
| 6.2 Proxy Objectives and Perceptual Quality | Interpret agreement and disagreement | A lower designed loss is not a perceptual-quality certificate; explain supported mismatches. S2. |
| 6.3 Representations, Ranking, and Transition Control | Separate component effects | Whole-path differences cannot identify architecture or cue-selection causes. Matrix and matched experiments. |
| 6.4 Threats to Validity | Assess construct, internal, external, and statistical limits | Address selection, dependence, test exposure, narrow tempo/corpus, missing semantic labels, renderer/stem/alignment differences, and rater sampling. |
| 6.5 Scope Coverage and System Limitations | Audit assignment fulfilment explicitly | Missing 1/3 bars, representations, GUI/export, effort, and dance evidence remain requirements or documented scope decisions. A1. |
| 6.6 Legal, Ethical, and Reproducibility Constraints | State documented permissions and practical limits | Local access and hashes do not establish reuse rights, participant consent, or portable reproduction. E1/E3. |

### 7. Conclusion and Future Work

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| 7.1 Conclusion | State the strongest supported answer and contributions | At present: conditional control-learning feasibility with unresolved perceptual/user benefit; revise only from verified final results. |
| 7.2 Future Work | Prioritise work implied by observed limits | Distinguish required assignment completion from optional broader lengths, datasets, or model families. |

### Appendix

| Section | Purpose | Central claim / evidence condition |
|---|---|---|
| A.1 Protocol and Artifact Index | Make reported claims traceable | Include exact paths, hashes, contracts, and access limitations. |
| A.2 Evaluation Materials | Preserve actual study procedures | Include only final used questionnaires, instructions, consent and ordering rules; protect unfinished study answer keys. |
| A.3 Supplementary Results and Reproduction Commands | Support bounded reproducibility | Preserve secondary results and failures; label synthetic, validation, and held-out artifacts distinctly. |

## 6. Claims not currently supported

The final thesis must not currently claim:

- A trained BeatBridge controller is perceptually superior to equal power, direct optimisation, or other controllers in an independent evaluation. H5 is unrated; H6 is documented as pending. H3 concerns direct optimisation.
- A lower proxy loss proves musical quality, naturalness, vocal intelligibility, or dance usefulness; a universal perceptual metric has been learned; or objective v5's individual terms caused H4's outcome. P1/P2/H1–H4 support narrower statements.
- The fixed TCN/BiLSTM is better than the MLPs, or the variable model is better than the fixed model, from their raw validation losses. Data, objective, renderer, alignment, and evaluation audio differ. P1–P4/R1–R6.
- A real cue ranker was trained/evaluated, outperformed the feature baseline on real music, or selected better cues for listeners. P5 supplies implementation/synthetic evidence only; teacher agreement would remain an intermediate endpoint.
- The project evaluated self-supervised embeddings, learned a general music representation, or established representation transfer. P4 contains engineered feature contracts, not such an experiment.
- One-to-four-bar learned transition generation is completely implemented and evaluated; training at 2/4/6/8 bars establishes generalisation to 1/3 or unseen lengths; or a 100-epoch variable run occurred. P3/P4/R6 do not support these claims.
- Nine cue judgements are nine independent track-pair trials, one rater represents a listener population, or any statistically significant advantage was demonstrated. H1–H4 are descriptive exploratory records.
- All test data stayed untouched, all splits are independent musical works, or validation listening is held-out evaluation. D1–D3/P4/P6 require the stage-specific exposure distinctions above.
- Correct grid provenance proves musically correct downbeats; missing phrase channels encode recognised structure; vocal activity scores are calibrated probabilities or recognised lyrics. P4/P7 do not supply annotated ground truth.
- The GUI and full mashup workflow are complete, manual correction is reduced, or the output has demonstrated dance-performance usefulness. A1/P8 define missing deliverables.
- The corpus is representative or freely redistributable; all external binaries/models have verified distribution permission; or the full pipeline has been reproduced on this Linux checkout. A2/A3 and the local availability audit leave these open.
- The method is the first, generally state of the art, or addresses an unstudied gap. The existing related-work prose is not a completed primary-source or novelty audit. A3.

## 7. Unresolved placeholders and citation policy

Keep explicit placeholders for: supervisor agreement on assignment coverage; the representation experiment; real ranker release/training/evaluation; 1/3-bar support; recovery of R4–R6/D3/H6; completed learned-controller ratings; fresh held-out set/exposure ledger; final study participants, conditions, sample-size rationale and statistical plan; input/control ablations; rights/tool provenance; validated segment boundaries and GUI display of beats/bars/boundaries; GUI assembly/export; and correction-effort/dance-use results. The exact registered English title also remains a separate A3 TODO. No existing LaTeX TODO is resolved merely by this blueprint.

The blueprint cites the assignment, contracts, implementation, and run/study records for project-specific assertions. No bibliography entry or LaTeX citation was added or removed, and no publication metadata was independently verified in this task. Before drafting external factual claims, audit the primary publication and its match to the existing key in `overleaf/bibliography.bib`. A resolving key alone is not verification.

Known verification items retained from A3 are `sowula2024mosaikbox` (title/author), `rouard2023htdemucs`, `steinmetz2021mixingconsole`, and `delgado2022peaq` (publication form/year), plus the version note in `robinson2023graphcuts`. All other substantive literature claims also need source checking. The German draft's `rouard2023hybrid` and `lu2024bsroformer` must not be copied into the Overleaf manuscript without key reconciliation and publication verification; neither is a key in its current bibliography. Preserve the current related-work prose for the later authorised revision, but do not inherit its representation-centred novelty conclusion as an established result.

## 8. Consistency gates before chapter drafting

- The primary question and three sub-questions remain conditional and correspond to S1–S3.
- Every contribution has an existing evidence source, a stated achievement level, and explicit completion conditions.
- Assignment gaps remain visible; planned contributions are not described as delivered.
- Current local evidence is separated from dated reports whose primary artifacts are missing here.
- Fixed four-bar and variable-length contracts remain separate, including their renderers and listening sample rates.
- Direct optimisation, learned controls, and candidate ranking remain separate experimental interventions.
- Existing thesis labels, citations, prose, and evidence TODOs remain unchanged.
- Independent consistency review and the exact verification record are completed before this plan is used for drafting. User review of this blueprint and outstanding scope decisions remain separate from an evidence-consistency check.

## 9. Verification record

The official three-page PDF was text-extracted and visually inspected. Required repository instructions, relevant contracts, run metadata, completed/incomplete study records, code paths, and LaTeX scaffolding were read. The local artifact check passed for nine run-file hashes, three dataset-manifest bindings, three history/best/final-epoch consistency checks, and four completed-study count checks; seven rating files were inventoried. No waveform samples, dataset payloads, or blinded answer keys were opened; checkpoints were only hashed.

Verification commands, limitations, and review findings are recorded in [Bemerkungen](../Bemerkungen.md), under 2026-09-16. The static document/source-preservation check passed. A fresh-context read-only review found and prompted correction of the H1–H6 source-index wording, the missing assignment row for analysis/display, and the ambiguous title-status sentence; it reported no remaining defect in the questions, path separation, evidence matrix, counts, citation boundaries, or source links. No training, Python/pytest run, new perceptual evaluation, bibliography audit, or LaTeX compilation was performed. The required Windows Python path is absent on this checkout; the metadata audit used Bash, `jq`, and `sha256sum`. This Markdown-only task does not repair or retest the earlier LaTeX dependency failure. No commit is created.
