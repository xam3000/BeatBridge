# BeatBridge thesis setup audit

Date: 2026-09-14. Scope: LaTeX structure and evidence boundaries before
substantive writing. This is an editable outline, not a completed thesis or
a new experimental evaluation.

## Sources and audit boundaries

- `overleaf/CGThesis.tex`, `meta.tex`, `cg.cls`, every file in `chapters/`,
  `bibliography.bib` and the supplied template's `README.txt`.
- `angepasste_aufgabenstellung_masterarbeit.pdf`: all three pages extracted
  and visually inspected. Page 1 supplies the German title, aim and research
  question; page 2 specifies one-to-four-bar transitions, representation and
  metric evaluation, GUI interaction, export, manual correction effort and
  dance-performance usefulness; page 3 defines the non-goals.
- `AGENTS.md`, `.agents/AGENT.md`, the packaged multi-session discipline skill,
  `docs/STATUS.md`, `docs/Projekt-Gesamtuebersicht.md`,
  `docs/ML_MODEL_CURRENT_STATE.md` and relevant entries in `docs/Bemerkungen.md`.
- `docs/CONTROL_STUDY_PROTOCOL.md`, `docs/CUE_RANKER_MODEL_PROTOCOL.md`,
  `docs/TCN_BILSTM_CONTROL_MODEL_PROTOCOL.md`, `docs/DATASET_PROTOCOL_V2.md`,
  `docs/VARIABLE_WAVEFORM_CACHE_PROTOCOL.md`, `docs/GUI_SPECIFICATION.md`, and
  the relevant sections of `docs/masterarbeit/methodik.tex`.

The protocols define methods; the status documents report prior verification.
Neither is treated here as a fresh audit of training or listening artifacts.
No audio, checkpoint, dataset shard or blinded answer key was opened. No
numeric experimental result was transferred into the thesis. A later results
chapter must first bind each claim to an immutable manifest/history/rating
artifact and verify that artifact.

## Findings and implemented decisions

| Finding before this audit | Resolution / remaining condition |
|---|---|
| Only Related Work was enabled; both abstracts and the other six chapters were commented out. | Enabled both abstracts, all seven chapters and a supplementary appendix. |
| At the start of the 2026-09-14 re-audit, the live Overleaf checkout selected `LR`, which renders the document as a literature report. The retained 2026-09-13 snapshot already contains `MA`, so the intervening state change is not explained by the available evidence. | Changed the live file to `MA, twosided`. `cg.cls` maps `MA` to Master Thesis and selects English by default. No class rewrite. |
| Both abstracts contained template instructions. | Replaced them with explicit draft placeholders and evidence-dependent TODOs. German text is locally wrapped in Babel's `otherlanguage` environment. |
| Introduction and Implementation contained sample figures, equations and unrelated source listings; the main chapter contained template guidance. | Replaced examples with a project-specific section outline and TODO comments. Results, Discussion and Conclusion now have distinct roles. |
| Related Work already contained substantive prose and citations. | Retained that prose and every citation. Expanded the chapter title, reserved a terminology section and flagged the pending primary-source/positioning audit. |
| Author metadata included the literal `Optional affiliation`. | Cleared that optional field; preserved all personal names, contacts and examiner details. Empty study-programme field retains the class default, with a verification TODO. |
| Bibliography printed editorial requests and key-history notes. | Moved four such notes to comments; unresolved verification remains explicit. All entry keys and scholarly metadata are retained. |
| Historical status entries say the Overleaf folder is empty or a complete outline already exists. | Current files were inspected directly. The local submodule and a tracked `.gitmodules` URL are present. No remote availability or fresh-checkout reproducibility is claimed; earlier log entries are retained as historical records. |

The exact title remains **BeatBridge: Using Self-Supervised Learning for
DJ-Style Transitions**. The assignment instead gives **KI-gestützte
Generierung musikalischer Übergänge für Tanz-Mashups mittels Self-Supervised
Learning**. It contains no exact registered English equivalent. `meta.tex`
therefore records the discrepancy for confirmation against the registration
record; no translation or new title has been substituted.

The supplied German abstract template states that an English thesis needs
both a German and an English abstract. Both are included. Current examination
regulations, abstract length limits, final programme wording and submission
date still require confirmation; the template is not proof of current
examination rules.

## Chapter structure and responsibility

| Chapter | Purpose and section coverage |
|---|---|
| 1. Introduction | Problem and motivation; main question and sub-questions; approach and intended contributions; scope/non-goals; roadmap. |
| 2. Background and Related Work | Terminology and conceptual foundations; existing literature on sequencing, front ends, representations, compatibility, controls and evaluation; research positioning. |
| 3. Methodology and System Design | Research design; corpus/split rules; analysis/alignment; representations; candidate ranking; controllers; renderers/objectives; training/baselines; evaluation design. |
| 4. Implementation | Actual software/data flow; caches and provenance; dataset/training mechanisms; ranker and renderer integration; current workflow versus planned GUI/export; reproduction environment. |
| 5. Experimental Setup and Results | Evidence inventory and comparison conditions; corpus/run configuration; technical validity; controller/proxy outcomes; representation/metric/ranker evaluation; perception; manual effort and dance usefulness; failures. |
| 6. Discussion and Limitations | Answers and interpretation; proxy/perception relationship; representation/ranker/controller limits; threats to validity; assignment coverage; evidence-based priorities. |
| 7. Conclusion and Future Work | Supported answer to the main question, achieved scientific/engineering contributions, principal limitation and focused next steps. |
| Appendix | Protocol/artifact index, actual evaluation materials and supplementary results/reproduction commands. |

Chapter 3 defines the scientific method, Chapter 4 explains its realisation,
and Chapter 5 supplies actual settings and evidence. This separation avoids
turning intended experiments or implemented code paths into results.

## Evidence-dependent TODOs

- **Scope and research questions:** reconcile the assignment's representation
  and metric emphasis with the documented controller-focused decision. Obtain
  supervisor agreement for any reduced deliverable; do not infer it from an
  implementation gap.
- **Lengths:** explicitly audit one- and three-bar support and evaluation.
  Six- and eight-bar studies are extensions, not evidence of one-to-four-bar
  coverage.
- **Representations and ranking:** retain space for real embedding and
  metric-validity studies. The documented synthetic ranker checks are not
  evidence of real-data training or musical ranking quality.
- **Protocol families:** keep fixed four-bar and variable-length paths
  separate. The fixed full-band renderer and variable vocal renderer do not
  become equivalent because diagnostic output dimensions match. Do not rank
  architectures by losses from incompatible objectives, data or renderers.
- **Corpus and external tools:** verify origin, permitted research/use and
  redistribution, corpus statistics and external-tool provenance. Local
  availability establishes no permission.
- **Perception:** verify completed ratings and analysis before reporting
  outcomes. Prepared audio is not a completed listening study. Document actual
  raters, consent, recruitment, listening conditions, split, dependence among
  cue/track/pair observations and any statistical procedure performed.
- **Held-out evaluation:** distinguish validation development and historical
  test reuse from a final independent test. No new test material was accessed.
- **User workflow:** GUI design, multi-track section selection, final mashup
  export, manual correction effort and dance usefulness require implementation
  and study evidence before being described as achieved.
- **Final prose:** write abstracts and conclusion only from stable, verified
  results/discussion. Literature novelty and performance claims remain subject
  to primary-source verification.

## Citations and labels

No citation was added or removed. The bibliography metadata was inspected for
structural/editorial issues, not independently verified against publications.
In particular, the existing uncertainty for `sowula2024mosaikbox` (title and
first author's given name) remains a TODO. The publication-version/year notes
for `rouard2023htdemucs`, `steinmetz2021mixingconsole` and `delgado2022peaq`
remain in comments for primary-source review. The preprint/conference note in
`robinson2023graphcuts` also warrants checking. Other existing records and
claim support must be checked during the dedicated literature audit; key
resolution alone does not verify a source or its claim.

The substantive labels `sec:related_work` and `ch:main` remain unchanged.
Five template-only figure/listing labels and their demo-only references were
retired together; their names are retained in source comments. New chapter
and section labels are unique. The German methodology draft and its separate
bibliography are not included automatically: importing it requires an English
revision, evidence reconciliation and explicit citation-key resolution.

## Verification

Detailed commands, failures and outcomes are recorded in `docs/Bemerkungen.md`
under the 2026-09-14 thesis-setup re-audit entries. The retained pre-edit
snapshot is under `/tmp/beatbridge-thesis-setup-audit-20260913/`; the current
build attempt is confined to `tmp/thesis_setup_audit_20260914/`.
Static source checks do not replace compilation or visual review of the
resulting thesis. No experiment, Python test suite or perceptual test is part
of this structural audit. No commit is created.

Static verification passed: ten active includes, seven chapters in order,
43 unique active labels, no active cross-references, 43 citation occurrences
resolving to 38 unchanged bibliography keys, no active template demos, and
balanced braces/environments under the limited source checker. The exact title,
existing Related Work prose, non-editorial bibliography fields and four
protected-file hashes match the pre-edit snapshot. Both Git whitespace checks
passed. An independent read-only structural review found no TeX-structure
defect after its documentation-consistency finding was corrected.

The local `pdflatex` attempt failed while loading Babel because
`ngerman.ldf` is missing. No thesis PDF was produced, and the chapters were not
processed. `biblatex.sty` and Biber are also unavailable. A successful complete
build and visual review remain outstanding; no template dependencies were
removed to bypass this limitation. The assignment PDF itself was successfully
read and rendered using system Poppler after the bundled `pdfinfo` failed
because it requires `GLIBC_2.38`.

For a complete TeX installation, select `overleaf/CGThesis.tex` as the main
document in Overleaf, or run `latexmk -pdf -interaction=nonstopmode
-halt-on-error CGThesis.tex` from `overleaf/`. This latter command is guidance,
not an executed successful build. Check unresolved references/citations,
overfull boxes, title-page layout and the German/English abstracts afterward.
