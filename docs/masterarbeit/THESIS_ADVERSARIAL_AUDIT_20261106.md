# Final adversarial thesis audit — 6 November 2026

This is a submission-readiness audit of the complete thesis, not an experimental
result. The audit reads `overleaf/CGThesis.tex`, `overleaf/meta.tex`, all active
chapter files, `overleaf/bibliography.bib`, the repository protocols, the
evidence ledger, and the immutable dataset, run, batch, sweep, and study
artefacts. It does not open test tensors, test-only JSONL files, audio, or blind
answer keys.

## Verdict

The thesis is **not ready for submission**. Its experimental core is traceable:
the numerical claims in the Results chapter agree with the local manifests,
histories, checkpoints, study results, and batch manifests, and all 51 checked
file hashes match. The remaining blockers are missing end matter (both abstracts
and the conclusion), unconfirmed administrative fields, research obligations
without evidence, a test-population and exposure problem, and unresolved
governance and reproduction items.

This audit repairs only discrepancies that the repository evidence settles
unambiguously. Every missing experiment, supervisor decision, participant
detail, legal clarification, or interpretive choice remains an explicit TODO.
No commit was made.

## Evidence base

- `docs/masterarbeit/audit_thesis.py` was run before and after the repairs:
  `.venv\Scripts\python.exe -X utf8 -B docs\masterarbeit\audit_thesis.py --report <path>`.
- The final report checks 51 dataset/run file hashes, four dataset manifests,
  four September run manifests, four completed study results, two batch
  manifests, the fixed-TCN sweep snapshot, the shared twenty-cue exposure, and
  the static LaTeX structure. It reports 0 hash failures, 0 dataset row
  assignment errors, 0 undefined references, 0 duplicate labels, 0 missing
  citations, 0 duplicate bibliography keys, 0 unused bibliography keys, 0
  missing includes or graphics, and 0 mismatched environments.
- All DOI-bearing bibliography entries were resolved against Crossref or
  DataCite. Four DOIs resolved to unrelated records and were corrected; two
  missing DOIs and two missing page ranges were added after verification.
- No local TeX engine or bibliography tool is installed; no WSL distribution or
  Docker image is available. A local LaTeX build could therefore not be run.
  The static checks above do not certify compilation, layout, or bibliography
  formatting.

## Blockers

1. **Both abstracts are empty.** `00_abstract.tex` and
   `00_abstractEnglish.tex` contain only headings and TODO comments. The thesis
   has no abstract in either required language.
2. **The conclusion is empty.** `07_conclusion.tex` has headings and TODO
   comments but no supported answer to the primary research question and no
   prioritised future work. Chapter 6 already contains a Future Work section,
   so the final structure also needs an authorial decision to avoid duplication.
3. **Administrative fields are unconfirmed.** The English title in `meta.tex`
   is a translation of the German assignment title and is marked TODO. The
   submission date (`CGThesis.tex`) and the official programme wording
   (`\studyProgram{}`) are also unconfirmed. The title's "Self-Supervised
   Learning" wording is broader than the implemented fixed-proxy control
   learning unless the narrow definition in Chapter 1 is accepted; that is a
   registration/supervisor decision.
4. **Several research obligations have no experimental answer.** SQ1 has
   within-protocol optimisation evidence but no feature/control ablations and,
   for the fixed TCN and variable paths, no matched unlearned baseline. SQ2 has
   one-rater direct-control development studies but no completed
   trained-controller perceptual evaluation. SQ3 has multi-length training but
   no compatible variable-baseline run and no length-specific perceptual
   comparison. There is no controlled representation experiment, no real-data
   learned-ranker result, no one- or three-bar evaluation, no manual-correction
   experiment, and no dance-usefulness result.
5. **No globally untouched final test population is established.** Within each
   dataset instance, train/validation/test assignments are consistent, but the
   four instances move audio hashes between roles. D1's three test hashes become
   training hashes in D2; D2 and D4 also move hashes between train, validation,
   and reserved test. The shared twenty-cue export is labelled validation for
   the fixed models, yet eight cues use only tracks reserved as test by the
   variable authority, seven include a variable-training track, and five use
   only tracks outside that authority. The export materialises reserved test
   material even though the variable training audit records `test_reads=0`.
   Materialisation is not proof of listening or model-selection use, but it
   prevents a global untouched-test claim. A new exposure-controlled track set
   and frozen protocol are still required.
6. **Governance and legal statements are incomplete.** Corpus provenance,
   research-use and redistribution permissions, the `aufTAKTCl` supply chain
   and licence, participant recruitment/consent/privacy decisions, and the
   exact reproduction environment remain unresolved. Their absence does not
   establish a violation, but the thesis cannot claim that these conditions are
   satisfied. The appendix's protocol index and evaluation materials are empty.
7. **The reproduction record is incomplete.** Run manifests bind datasets,
   models, renderers, objectives, seeds, and devices, but the reported runs do
   not carry the exact resolved software versions and invocation details that a
   fresh-system reproduction would need. A fresh-environment reproduction has
   not been performed.
8. **No local LaTeX build was possible.** The available environment has no
   `pdflatex`, `latexmk`, `xelatex`, `lualatex`, `tectonic`, `bibtex`, or
   `biber`; `wsl` has no installed distribution and Docker is unavailable.
   Compilation, page layout, overfull/underfull boxes, and bibliography
   formatting therefore remain unverified in this checkout.

## Research-question and contribution coverage

| Item | Evidence in the repository | Audit verdict |
|---|---|---|
| SQ1, optimisation | Four real runs with hash-bound histories and checkpoints; within-run proxy reductions | Partly answered. The matched-unlearned-baseline clause is available only for the MLP initialisation. |
| SQ1, feature/control attribution | No retrained ablations | Unanswered. |
| SQ2, perceptual validity | Four one-rater direct-control studies; no trained-controller listening study | Unanswered for the learned controllers. The direct-control results are exploratory. |
| SQ3, transition length | Variable run across 2/4/6/8 bars with equal-length weighting | Descriptive only. No compatible variable-baseline run and no length-specific listening result. |
| Controller--renderer--proxy formulation | Four real runs, run contracts, synthetic gradient checks | Supported as optimisation feasibility, not as perceptual quality. |
| Auditable pipeline | Dataset, run, batch, sweep, and study manifests with matching hashes | Supported as a technical/reproducibility contribution. |
| Feature-based candidate path | 321-pair and 963-pair real batches | Supported as execution and candidate yield, not as ranking accuracy. |
| Learned candidate ranker | Synthetic end-to-end tests only | Not empirically supported on real candidate groups. |
| Representation comparison | None | Not supported. |
| One- and three-bar transitions | None | Not supported. |
| Manual correction and dance usefulness | None | Not supported. |
| Graphical workflow | Native prototype source only; no acceptance run or measured task | Not established. |

## Major issues

1. **Four bibliography DOIs resolved to unrelated records.** The entries for
   Korzeniowski and Widmer, Kim et al., Huang et al., and Spijkervet and
   Burgoyne pointed to different publications. Korzeniowski's page range was
   also wrong. Rouard et al. and McFee et al. lacked page ranges; Rouard et al.
   also lacked a DOI; Bittner et al. lacked a DOI. All are corrected in
   `bibliography.bib` after Crossref/DataCite verification.
2. **The Results chapter described a deprecated shared-stimulus export.** The
   text still treated the 30 September 2026 twenty-cue export and its
   11,025-Hz-to-44,100-Hz variable resampling as the current comparison. The
   user retired that export on 5 November 2026 because the resampling removed
   high-frequency content and biased the comparison. The official replacement
   is the 5 November 2026 renderfix export, which renders every candidate
   directly at 44,100 Hz. The text now states this, notes that three
   browser-side rankings of the deprecated export were never exported, and
   keeps the exploratory/out-of-domain qualification.
3. **The shared-stimulus exposure count was ambiguous.** "Five use tracks
   outside that authority" could be read as five cues with any outside track.
   The artefacts show 8 cues with only reserved-test tracks, 7 with a
   variable-training track, and 5 with only outside-authority tracks. The text
   now says "the remaining five use only tracks outside that authority".
4. **The dataset table presented a derived aggregate as an instance.** The row
   "Format 2, all lengths, 420/48/84" is the sum of four per-length shards, not
   a separate manifest. It was removed; the per-length rows and the text's 552
   total remain.
5. **The sweep-checkpoint statement was inaccurate.** The local sweep
   manifests contain null checkpoint entries and no checkpoint files, rather
   than no reference at all. The text now says that the manifests retain no
   best-checkpoint files and that the entries are empty.
6. **The baseline clauses of SQ1 and SQ3 were not answered.** Only the MLP
   initialisation is close to equal power; the fixed TCN/BiLSTM starts from an
   untrained network, and the variable controller starts logging at an already
   trained epoch. Neither provides a matched unlearned baseline. The compatible
   variable MLP baseline has no real run.
   The Discussion now states both limitations, and Chapter 1 carries a TODO to
   reconcile the question wording with the evidence. No new run was invented.
7. **The title's "Self-Supervised Learning" wording needs a scope decision.**
   The body defines self-supervision narrowly as training without target
   curves or human quality labels and explicitly denies that the current
   features are a self-supervised representation learner. The title and the
   assignment use the broader term. This is defensible only if the registration
   record accepts the narrow usage; otherwise the title overclaims.
8. **Chapter 6 and Chapter 7 both plan a "Future Work" section.** The current
   Chapter 6 section is substantive, while Chapter 7 is empty. The final
   conclusion should either absorb that material or cross-reference it, which
   is an authorial structural choice.

## Minor issues

- "Teacher" was used in Chapter 3 before it was defined; the first use now
  identifies the frozen controller as the teacher.
- The mid-band vocal-ducking proxy was cross-referenced to the limitations
  section; it now points to the controller/renderer section that describes it.
- "Described in the repository status" was not a thesis-internal reference; it
  now points to the implementation section.
- The vocal-study sentence said all other criterion means were equal while the
  overall mean also changed. It now says the individual criterion means were
  equal and the overall mean differs only through vocal clarity.
- The list of secondary ratings omitted rhythmic stability, which the completed
  studies actually rated; it is now included.
- Sample-rate notation mixes "44,100 Hz" and "44.1 kHz". Both are correct and
  the meaning is unambiguous, but a final copy-edit pass may standardise it.
- Prose uses "completed run" for runs whose manifest status is
  `early_stopped`; this means "finished", not the manifest status. The Results
  chapter states the actual stop epochs, so the meaning is recoverable.
- The appendix comments use "artifacts" while the thesis prose uses
  "artefacts"; this is confined to comments.
- The Results chapter now distinguishes exported/analysed ratings from
  browser-side rankings; the deprecated export's three browser rankings are
  explicitly excluded.

## Repairs applied

| File | Repair |
|---|---|
| `overleaf/bibliography.bib` | Corrected the Korzeniowski/Widmer DOI and pages; corrected the Kim et al., Huang et al., and Spijkervet/Burgoyne DOIs; added verified DOIs for Bittner et al. and Rouard et al.; added verified page ranges for Rouard et al. and McFee et al. |
| `overleaf/chapters/01_introduction.tex` | Added a TODO recording that SQ1's matched-unlearned-baseline clause is not available for the fixed TCN and variable paths. |
| `overleaf/chapters/03_mainPart.tex` | Removed the derived aggregate dataset row; made the exposure counts unambiguous; defined "teacher" at first use; added rhythmic stability to the secondary ratings; corrected the claim about which run roots carry an input/output audit. |
| `overleaf/chapters/05_results.tex` | Corrected the sweep-checkpoint wording; clarified the vocal-study overall mean; replaced the deprecated twenty-cue description with the renderfix/deprecation record and excluded browser rankings; corrected the best-checkpoint wording in the failure section. |
| `overleaf/chapters/06_discussion.tex` | Added the SQ1 baseline limitation and the SQ3 missing-baseline limitation; corrected the mid-band cross-reference; replaced the repository-status reference with a section reference; fixed a grammar error. |
| `docs/masterarbeit/THESIS_ADVERSARIAL_AUDIT_20261105.md` | Marked the earlier audit as superseded by this final audit. |
| `docs/masterarbeit/audit_20261106*.json` | Read-only evidence reports for the before/after checks. |

## Verification performed

### Thesis structure and citations

Final `audit_thesis.py` report (`docs/masterarbeit/audit_20261106_final.json`):

- 51 file hash checks, 0 failures.
- 4 dataset manifests, 0 train/validation row assignment errors.
- 0 undefined references, 0 duplicate labels.
- 0 missing citation keys, 0 duplicate bibliography keys, 0 unused keys.
- 26 distinct citation keys and 26 bibliography entries.
- 0 missing includes or graphics, 0 mismatched environments.
- 41 TODO markers (40 before the repairs plus the new SQ1 baseline TODO).

### Numerical claims

The following were re-read from the artefacts and agree with the thesis:

- Dataset counts: 45/9/9, 370/50/60, 105/12/21 per length, 663/159/0 for
  lengths 2/4/6, 660/159/0 for length 8; 480 expanded examples, 111 track
  assignments, 1,110 selected before exclusions, 630 cross-split discards,
  552 strict examples, 3,285 PRIVE examples.
- Runs: fixed MLP 0.421035 -> 0.415208 at epoch 1, stopped at 7; vocal MLP
  0.350723 -> 0.324910 at epoch 34, stopped at 40, history minimum 0.324840 at
  epoch 38; fixed TCN 1.938312 -> 0.320778 at epoch 18, stopped at 24;
  variable 0.252060 -> 0.227169 at epoch 34, completed at 40; parameter counts
  10,394, 20,821, and 1,013,226.
- Batches: 321 pairs, 2,746,846 candidates, 122 rendered, 0 failures; 963
  pairs, 303,824 candidates, 5 candidate-bearing pairs, 1 render, 4 render
  failures, 1 metric failure.
- Studies: 3/4/1, 0/0/8, 9/0/0, and 2/1/3 preferences; cleanliness 4.0 -> 5.0
  with vocal clarity 4.778 in both; vocal clarity 4.333 -> 5.0 with equal
  individual criterion means.
- Sweep: 92 rows, 35 completed at 150 epochs, 56 stopped earlier, one without
  metrics; best 0.261587 at epoch 77 and next 0.261624.
- Shared twenty-cue exposure: 8 reserved-test, 7 training, 5 outside-only; all
  twenty cues reuse five track pairs.

### Bibliography metadata

- Crossref/DataCite resolution confirmed the corrected DOIs for
  `korzeniowski2017endtoendkey`, `huang2021stemcompat`, `kim2020djmixanalysis`,
  `spijkervet2021clmr`, `rouard2023hybrid`, `bittner2017playlist`,
  `mcfee2015librosa`, and the previously verified DOIs.
- The four corrected DOIs now resolve to the intended titles and page ranges.
- The ISMIR 2024 page ranges for Argüello et al., Sowula and Knees, Foscarin
  et al., and Riou et al. were confirmed against the ISMIR 2024 proceedings.
- The remaining entries without DOIs are ICLR papers, a thesis, an unrefereed
  demonstration, and a software page; their existing identifiers are retained.

### LaTeX build

No build was run because no engine is installed. The exact checks were:

- `Get-Command pdflatex,latexmk,tectonic,xelatex,lualatex,bibtex,biber`
  returned nothing.
- `Get-ChildItem` over the usual TeX Live/MiKTeX locations found no
  installation.
- `wsl -e sh -lc "command -v pdflatex; ..."` reported that no WSL distribution
  is installed.
- `Get-Command docker` returned nothing.

The static checks cannot certify a successful compile, page layout, or
bibliography formatting.

## Remaining placeholders and missing evidence

The 41 TODO markers fall into these groups:

- **End matter:** both abstracts, the conclusion, and the appendix's protocol
  index, evaluation materials, and reproduction commands.
- **Administrative:** exact English title, submission date, programme wording,
  and the supervisor/registration scope decision for the assignment's
  representation, metric, one-to-four-bar, interaction, and user-evaluation
  requirements.
- **Experiments:** SQ1 feature/control ablations and per-path matched
  baselines; SQ2 trained-controller perceptual study; SQ3 compatible
  variable-baseline and length-specific comparisons; representation
  experiment; real-data teacher labelling and ranker training; one- and
  three-bar cases; manual-correction and dance-usefulness tasks.
- **Governance:** corpus origin and rights, `aufTAKTCl` provenance and licence,
  participant recruitment/consent/privacy, and the exact reproduction
  environment.

## Recommendation

Do not submit until the blockers are resolved. The immediate sequence is:
(1) confirm the title, date, and programme with the examination office;
(2) write the abstracts and conclusion only after the final claim and scope are
fixed; (3) complete the trained-controller listening study on a new
exposure-controlled track set; (4) add the missing baseline and ablation runs or
narrow the research questions accordingly; (5) finalise the legal/consent and
reproduction statements; and (6) run a clean LaTeX build with the institute's
compiler and inspect the PDF.
