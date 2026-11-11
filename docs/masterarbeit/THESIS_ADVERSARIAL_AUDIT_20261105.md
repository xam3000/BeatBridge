# Adversarial thesis audit — 5 November 2026

This is a submission-readiness audit, not an experimental result. The thesis is
**not ready for submission**. The findings below were recorded before thesis
edits. Subsequent repairs and remaining limitations are listed separately.
Existing user changes were present in both the main repository and `overleaf`;
they are not attributed to this audit. No commit is authorised.

## Blockers

1. **The argument has no completed beginning or ending.** Both abstract files
   contain only headings and TODO comments; `07_conclusion.tex` has no conclusion
   or future-work prose. The registered English title is unconfirmed in
   `meta.tex`, as are the submission date and programme wording. The title's
   self-supervision wording is broader than the implemented fixed-proxy control
   learning unless that narrower meaning is retained. The thesis must not imply
   an evaluated self-supervised representation learner. Abstracts and conclusion
   require an author/supervisor decision on the final claim and scope; this audit
   does not invent that decision.
2. **Several research obligations lack experimental answers.** SQ1 has evidence
   of within-protocol optimisation, but no matched feature/control ablations.
   SQ2 has small, one-rater direct-control development results, but no completed
   trained-controller perceptual evaluation. SQ3 has multi-length training but
   no matched duration comparison or length-specific perceptual result. There
   is no controlled representation experiment, real-data learned-ranker result,
   one-/three-bar evaluation, manual-correction experiment, or dance-usefulness
   result. These are completion work or require a documented scope decision,
   not optional claims that can be filled in from code.
3. **The checked histories do not establish a globally untouched final test
   population.** Original-file SHA splits
   are consistent within the four checked dataset instances; 4,227 train and
   validation metadata rows agree with their assignments. Assignments differ
   between instances: D1's three assigned test hashes become D2 training hashes;
   D2 and D4 also move hashes between train, validation, and reserved test roles.
   This is not evidence of within-run optimisation leakage, but prevents a
   global untouched-test claim. The shared twenty-cue export is v1 validation,
   yet eight cues use both tracks reserved as test by D4's variable split
   authority, seven include a D4 training-assigned track, and five use tracks
   outside that authority. Thus, the export itself exposed reserved variable
   test material even though the variable training audit records `test_reads=0`.
   Materialisation does not establish human listening, use in model selection,
   or within-run optimisation leakage. Actual listening and selection exposure
   must be recorded before a final held-out claim; the planned independent
   study calls for a new exposure-controlled track set and frozen protocol.
   The report does not open test NPZ/audio or unfinished
   answer keys.
4. **Governance and final production checks are incomplete.** Corpus provenance,
   research-use and redistribution permissions, onTAKT supply chain/licence,
   participant recruitment/consent/privacy decisions, and exact reproduction
   environment remain explicitly unresolved. Their absence does not establish
   either permission or a legal violation. The appendix's protocol index and
   actual evaluation materials are empty. No full LaTeX build has yet been
   verified in this audit; tool availability and the clean-build outcome are
   recorded below. No participant identities or restricted audio should be
   copied into the public appendix as a substitute for a governance decision.

## Major issues

1. **Wrong Objective-v4 preference count.** Results Table
   `tab:results-listening` says nine ties. The completed primary
   `blind_v5_objective_v4_heldout_test9_4bar_20260731_rerun/study_results.json`
   records nine preferences for directly optimised controls, zero baseline
   preferences and zero ties (SHA-256
   `ab71a3b9a8a00b0588ee7e139d7407bd49ab83f7a159da0a10dfc46f0a0728ff`).
   Discussion and the evidence ledger already report the latter. This supports
   a count correction, not a population-level superiority claim.
2. **Suppressed Results content breaks references and hides limitations.**
   `sec:results-user-evaluation` and `sec:results-failures` are referenced from
   Discussion but commented out. The technical-constraint section is also
   commented out, leaving “fourteen validation cache failures noted above”
   without its explanation. Restore the supported status/failure paragraphs
   and labels while retaining evidence TODOs.
3. **Methods and Implementation describe an obsolete checkout.** They say
   format-2 and later fixed/variable run artefacts are absent; all four dataset
   manifests and September run roots are now local. All 51 checked train/
   validation payload/metadata and run-file digests match. The fixed-TCN and
   variable run contracts support their described renderers. Update the
   evidence boundary, dataset table, and training settings without treating a
   successful audit as a fresh training or listening experiment.
4. **Shared-stimulus exposure is mislabelled.** “Out-of-domain” alone misses the
   mixture of training exposure, reserved-test exposure and absent-map tracks.
   D4 exports no test examples but still reserves test tracks in its authority.
   Equal cues, context and common peak gain do not make this a common split or
   architecture benchmark. The variable output is rendered at 11,025 Hz and
   resampled to 44,100 Hz in that export; the other paths retain different
   renderer semantics. Label all these conditions explicitly.
5. **Training settings are overstated as universal.** The 370/50 fixed September
   runs use the stated learning rate, batch size five, patience six and
   `min_delta=1e-4`. Variable training uses length-homogeneous batches and
   `min_delta=0`; its first logged point is trained epoch one. The vocal declared
   checkpoint (epoch 34, 0.324909533560276) differs legitimately from the smaller
   logged value at epoch 38 (0.3248401999473572) because of the improvement
   threshold. Describe these separately.
6. **Citation coverage is incomplete.** HT-Demucs is used and named but its
   primary publication is absent from the active bibliography; the methodology
   leaves an explicit citation TODO. Librosa, onTAKT and Rubber Band are named
   without authoritative source citations in the technical chapters. A
   resolving citation key is not proof of publication metadata or claim support.
   Independent primary-source cross-review is in progress; only verified
   additions or corrections will be applied.
7. **An earlier completed, mixed/negative study is omitted.** The thesis says
   three completed direct-control comparisons have analysis files, while four
   are local. The earliest control-v2 study records three preferences for
   directly optimised controls, four for equal power and one tie. Include this
   superseded comparison with its own protocol label; it must not be pooled
   with the revised control-v3 or later objective studies.

## Minor issues and bounded negative findings

- Forty source TODO markers remain before repairs. Some are necessary missing
  evidence; a subset are obsolete recovery requests. The exact inventory,
  source hashes and locations are in `audit_20261105_before.json`.
- The static scan finds two undefined references, no duplicate labels or
  bibliography keys, no unresolved citation keys, no missing included file or
  externally referenced graphic, and no mismatched environments. It is not a
  TeX parser and cannot certify compilation, layout, bibliography formatting,
  or the absence of underfull/overfull boxes.
- The only implemented figure in the active thesis is the in-document data-flow
  schematic. The repository's other diagrams are not missing figure files
  unless the thesis actually references them. There are no empirical result
  plots establishing additional outcomes.
- “Self-supervised” is locally defined as fixed-proxy learning without target
  curves/human quality labels; it does not establish learned music
  representations. “Teacher” denotes the optional frozen controller/proxy
  pseudo-labelling path, verified only synthetically. “Ground truth” is not
  assigned to estimated stems or heuristic grids. The thesis avoids claiming
  statistical significance, architecture superiority or causal real-time
  operation. Preserve these boundaries.
- The raw validation losses are correctly separated by objective, renderer,
  dataset and feature protocol. A first-to-best reduction is not necessarily
  improvement over a matched unlearned baseline, especially for the fixed TCN's
  initialisation and the variable run's trained first point.
- The local beat-analysis executable is `aufTAKTCl.exe`, not “onTAKT”.
  `docs/EXTERNAL_TOOLS.md` and `config/auftakt_binary_provenance.json` identify
  its bytes but expressly leave exact supply chain and usage permission open.
  A related AUFTAKT SDK manual does not prove this binary's version or licence.
- Acronyms MLP, TCN/BiLSTM and BS-RoFormer are redefined after their first use;
  retain the first definitions and remove later redefinitions.
- Means on the recorded ordinal scales remain descriptive. Repeated cues,
  reversed pairs, shared tracks and one rater per completed study do not provide
  independent population samples. No new significance test is warranted here.

## Primary numerical evidence and verification scope

The script `audit_thesis.py` records dataset manifest digests, 51 file-hash
comparisons, four run contracts and histories, four completed-study summaries,
rating status, both batch totals, split cross-tabs and static TeX checks in the
before/after JSON reports. It reads only metadata and hashes for existing
artefacts. It does not train, render, score held-out audio, open test tensors,
or unblind unfinished studies. Format-1 combined metadata includes test row
records; those rows are skipped without further inspection. Test-only JSONL
files are not opened. No dataset, checkpoint, study manifest or rating is edited.

Validated dataset counts: 45/9/9 and 370/50/60 for format 1;
105/12/21 per length for strict format 2; D4 has 663/159/0 for lengths 2/4/6
and 660/159/0 for length 8. The variable training audit narrows 636 exported
validation examples to 622 accepted examples and reports 2,649 train examples,
14 cache exclusions and zero training-run test reads. Fixed batch totals are
321 pairs, 2,746,846 candidates and 122 renders; variable batch totals are 963
pairs, 303,824 candidates, five candidate-bearing pairs, one render, four
render failures and one metric failure. Completion flags alone prove none of
these stronger success conditions.

## Repair disposition and final verification

Superseded by the final audit of 6 November 2026
(`THESIS_ADVERSARIAL_AUDIT_20261106.md`). That report records the supported
repairs, the bibliography corrections, the static checks, the unavailable
LaTeX toolchain, and the blockers that remain. This earlier audit is retained
unchanged as the initial finding set.
