# BeatBridge: Schreibprompts fuer die Masterarbeit

Stand: 2026-09-13

Diese Prompts sind fuer Codex-Sessions im Root des BeatBridge-Repositories
gedacht. Die Arbeitsanweisungen sind auf Englisch formuliert, weil auch der
Zieltext auf Englisch entsteht. Pro Session sollte nur ein Prompt bearbeitet
werden. Vor jeder Session muessen die im Repository geltenden Agentenregeln
gelesen werden.

## Modellwahl

| Aufgabe | Modell | Reasoning | Begruendung |
|---|---|---:|---|
| Gliederung, Forschungsargument, kritische Synthese | `gpt-6-astra` | `xhigh` | Hoher Bedarf an fachlicher Abgrenzung und konsistenter Argumentation |
| Evidenzbasierter Kapitelentwurf | `gpt-6-astra` | `high` | Sehr gute Dokument- und Repository-Synthese |
| Ergebnis- und Diskussionskapitel | `gpt-6-astra` | `xhigh` | Hohe Gefahr von Scheinkausalitaet oder ueberzogenen Aussagen |
| Literatur- und Zitationsaudit | `gpt-6-astra` | `xhigh` | Quellen muessen gegen konkrete Aussagen geprueft werden |
| Normale Ueberarbeitung eines bereits korrekten Kapitels | `gpt-5.6-sol` | `high` | Gutes Verhaeltnis aus Qualitaet und Aufwand |
| Reine Sprachglaettung, LaTeX-Hygiene, Wiederholungen | `gpt-5.6-terra` | `medium` | Mechanischere Aufgabe mit geringerem Schlussfolgerungsbedarf |

Empfohlener Standard: `gpt-6-astra` mit `high`. `xhigh` sollte gezielt fuer
Forschungsfrage, Ergebnisinterpretation, Diskussion und Abschlussaudit
verwendet werden. Ein hoeheres Reasoning-Level ersetzt keine fehlenden Daten,
Quellen oder menschlichen Bewertungen.

## Gemeinsamer Qualitaetsvertrag

Der folgende Block kann vor jeden Einzelprompt gesetzt werden:

```text
You are working on the BeatBridge master's thesis. The thesis must be written
in clear, precise scientific English at the level of a competent master's
student in computer science. Prefer direct and natural academic prose over
ornate, promotional, or formulaic language.

Before editing anything, read and follow AGENTS.md,
.agents/multi-session-project-discipline.skill, .agents/AGENT.md,
docs/STATUS.md, docs/Projekt-Gesamtuebersicht.md, and the relevant protocol,
experiment, and LaTeX files. Treat repository documentation and immutable run
artifacts as evidence. Do not treat folder names, planned experiments, old
status statements, or code paths as proof that an experiment was completed.

Scientific integrity rules:
- Never invent measurements, participants, citations, implementation details,
  statistical tests, software versions, or experimental outcomes.
- Clearly distinguish implemented, technically verified, trained, evaluated,
  and merely planned work.
- Distinguish synthetic smoke tests, validation-set development studies, and
  held-out evaluations.
- Do not claim that a proxy loss proves perceptual quality.
- Do not compare raw validation losses across incompatible datasets,
  objectives, renderers, sample rates, or feature protocols as if they formed
  a fair architecture ranking.
- Preserve all explicit TODOs whose evidence is still missing. Rewrite them as
  concise LaTeX comments or clearly marked placeholders instead of guessing.
- Every externally verifiable factual claim must have a suitable citation.
  Use only real bibliography keys already verified in bibliography.bib, or
  add a source only after verifying its primary publication metadata.
- Paraphrase sources; do not copy distinctive wording.
- Keep terminology consistent: track A/source/outgoing track, track B/target/
  incoming track, cue point, transition window, controller, renderer, proxy
  objective, candidate ranker, and perceptual evaluation.
- Preserve valid LaTeX and existing labels, citations, and cross-references.
- Do not modify original audio, experiment artifacts, checkpoints, manifests,
  or unrelated user changes.

Writing style:
- Use explicit topic sentences and logical paragraph transitions.
- Keep claims proportional to the evidence.
- Avoid phrases such as "groundbreaking", "revolutionary", "obviously",
  "it is worth noting", "in today's rapidly evolving landscape", and vague
  claims such as "significantly better" unless supported by the stated test.
- Use first-person plural only if it is consistent with the university's
  style; otherwise prefer "this thesis" or an active description of the
  method. Avoid excessive passive voice.
- Define abbreviations on first use and do not redefine them later.

At the end, report:
1. files changed;
2. claims added and their evidence sources;
3. unresolved placeholders or missing evidence;
4. citations added, removed, or still requiring verification;
5. the exact verification performed, including LaTeX compilation if run.
Do not commit.
```

## Prompt 0: LaTeX- und Gliederungs-Audit

Modell: `gpt-6-astra`  
Reasoning: `xhigh`

```text
Audit the current Overleaf thesis setup before substantive writing. Inspect
overleaf/CGThesis.tex, overleaf/meta.tex, every file in overleaf/chapters/,
overleaf/bibliography.bib, the official thesis assignment PDF, and the current
project documentation.

Produce and implement a defensible thesis structure for an English-language
master's thesis on BeatBridge. Check in particular whether the document class
selects a master's thesis rather than a literature report, whether both the
required German and English abstracts are included, whether all intended
chapters are enabled, and whether placeholder template material remains.

Use a chapter structure that separates:
1. Introduction and research questions;
2. Background and Related Work;
3. Methodology/System Design;
4. Implementation;
5. Experimental Setup and Results;
6. Discussion and Limitations;
7. Conclusion and Future Work.

Do not fill missing empirical content. Insert precise TODO comments where a
section depends on unfinished experiments, a supervisor decision, corpus
rights, participant information, or final statistics. Preserve the official
registered title unless the assignment proves another exact title. Compile
the thesis if the required local toolchain is available, and document the
test according to AGENTS.md.
```

## Prompt 1: Forschungsfrage, Contributions und Kapitelplan

Modell: `gpt-6-astra`  
Reasoning: `xhigh`

```text
Derive a rigorous thesis argument from the official assignment and the
verified state of the BeatBridge repository. Do not draft full chapters yet.

Create an English thesis blueprint that contains:
- one primary research question and at most three focused sub-questions;
- a precise problem statement;
- the scientific scope and explicit non-goals;
- a contribution list that separates scientific contributions from software
  engineering contributions;
- a claim-to-evidence matrix mapping every intended contribution to existing
  or still-required experiments and artifacts;
- a section-by-section outline with the purpose and central claim of each
  section;
- a list of claims that the current evidence does not yet support.

The central scientific thread should reflect the actual project: learning
time-dependent and interpretable mixing controls without ground-truth control
curves, using a differentiable renderer and a fixed proxy objective, with cue
point selection treated as a separate upstream problem. Account explicitly
for the current limits of the real cue-ranker evidence, the validation-based
listening comparisons, dataset constraints, and the distinction between the
fixed four-bar and variable-length model paths.

Write the blueprint to docs/masterarbeit/ as a reviewable planning document.
Do not change thesis prose until the blueprint has been checked for consistency
against the repository evidence.
```

## Prompt 2: Introduction schreiben

Modell: `gpt-6-astra`  
Reasoning: `high`

```text
Write the Introduction chapter in overleaf/chapters/01_introduction.tex based
on the approved thesis blueprint, the official assignment, and verified
repository documentation. Remove all template examples.

The chapter should move from the practical problem to the research gap and
then to the thesis response. Include:
- motivation for short, musically coherent, user-constrained DJ transitions;
- why cue-point selection and transition rendering are related but distinct;
- why supervised target control curves are difficult to obtain;
- the research question and sub-questions;
- the proposed high-level approach;
- precise contributions, each worded no more strongly than the evidence;
- scope and non-goals;
- a short thesis roadmap.

Do not turn the introduction into a literature survey or implementation
manual. Cite only the few works needed to establish the problem and research
gap. Aim for approximately 4--6 thesis pages, but prioritize argumentative
completeness over a fixed length. Mark any contribution that still depends on
unfinished evaluation as provisional in a LaTeX TODO comment rather than
presenting it as achieved.
```

## Prompt 3: Related Work kritisch ueberarbeiten

Modell: `gpt-6-astra`  
Reasoning: `xhigh`

```text
Perform a claim-level literature and positioning audit of
overleaf/chapters/02_relatedWork.tex and overleaf/bibliography.bib.

For every paragraph, verify that the cited primary source supports the actual
claim. Prefer papers and official project documentation over secondary
summaries. Check bibliographic metadata and remove or soften claims that cannot
be verified. Do not add references merely to make the bibliography longer.

Reorganize the chapter around a comparison rather than a catalogue:
- automatic DJ sequencing, cue-point selection, and transition systems;
- learned DJ controls and differentiable audio processing;
- beat/downbeat, structural, harmonic, and vocal front ends;
- self-supervised music representations;
- compatibility and mashability learning;
- transition evaluation;
- the precise research gap addressed by BeatBridge.

For each group, explain what problem prior work solves, what supervision it
uses, what it outputs, how it is evaluated, and why it does or does not answer
the BeatBridge research question. End with a compact positioning synthesis.
Avoid repeatedly ending paragraphs with generic statements such as "this is
relevant to the present thesis." Use explicit technical comparisons instead.

Return a citation audit table in the session summary listing every added or
materially changed claim and its supporting source. Keep the thesis prose in
scientific English and valid LaTeX.
```

## Prompt 4: Methodology/System Design ins Englische ueberfuehren

Modell: `gpt-6-astra`  
Reasoning: `high`

```text
Turn the verified German methodology draft in
docs/masterarbeit/methodik.tex into a coherent English Methodology and System
Design chapter in the appropriate Overleaf chapter file. Translate for meaning
and scientific clarity, not sentence by sentence.

Preserve the mathematical definitions, protocol boundaries, dataset split
rules, and methodological caveats. Cover:
- research design;
- data basis and SHA-based split isolation;
- beat/downbeat analysis and alignment;
- beat-synchronous section representation;
- candidate generation and hard versus soft constraints;
- cue-point baselines and learned ranker;
- fixed and variable-length control models;
- differentiable rendering and proxy objectives;
- rendering baselines;
- training and checkpoint selection;
- objective and perceptual evaluation design;
- reproducibility and known methodological limitations.

Reconcile every numeric statement with current manifests or authoritative
documentation. If two documents disagree, investigate the underlying artifact
and retain a TODO if the conflict cannot be resolved. Do not present synthetic
ranker validation as a real-data result. Do not imply that all planned
ablations or final listening studies have occurred. Keep implementation-level
details out of this chapter when they do not affect reproducibility or the
scientific method.
```

## Prompt 5: Implementation schreiben

Modell: `gpt-6-astra`  
Reasoning: `high`

```text
Replace the template content in overleaf/chapters/04_implementation.tex with
an evidence-based description of the BeatBridge implementation.

Inspect the actual source tree and protocol documents before writing. Explain
the architecture and data flow at a level that enables an informed reader to
understand and reproduce the system without turning the chapter into a file-by-
file inventory. Cover the major modules for analysis, feature extraction,
candidate generation, dataset construction, model training, differentiable
rendering, evaluation, artifact provenance, and the current user workflow.

Use concise pseudocode, equations, tables, or architecture figures only when
they clarify a non-trivial process. Do not paste production source code unless
a short excerpt is essential. Clearly label components that are implemented
but only synthetically verified, components used in real training, and planned
GUI or end-to-end functionality that does not yet exist. Mention concrete
software versions only when verified from locked environment files or run
artifacts. Preserve the distinction among feature protocol 1, feature protocol
2, the fixed full-band renderer, and the variable vocal renderer.
```

## Prompt 6: Results ausschliesslich aus Evidenz schreiben

Modell: `gpt-6-astra`  
Reasoning: `xhigh`

```text
Write overleaf/chapters/05_results.tex using only completed and verifiable
BeatBridge experiments. Build an evidence ledger before drafting: for every
number, identify the exact manifest, history file, analysis output, listening-
study result, or documented verification that supports it.

Organize results by research question rather than chronology. Separate:
- technical validity and constraint compliance;
- dataset and candidate statistics;
- training behavior within each compatible model/protocol family;
- objective/proxy outcomes;
- cue-ranking outcomes, explicitly separating synthetic tests from real-data
  experiments;
- perceptual or preference results, with sample size and data split stated;
- failure cases and negative results.

Use tables and figures where they reduce repetition. State which comparisons
are fair and which are not. Do not rank architectures by losses produced under
different objectives, datasets, sample rates, or renderers. Do not describe an
unevaluated listening set as a study result. Report exploratory one-rater or
validation-set findings as exploratory. Never use "significant" unless a
specified statistical significance test was actually run. Add explicit TODOs
for the final held-out evaluation and unresolved listening studies rather than
filling gaps with expectations.
```

## Prompt 7: Discussion und Limitations schreiben

Modell: `gpt-6-astra`  
Reasoning: `xhigh`

```text
Write overleaf/chapters/06_discussion.tex after reading the completed Results
chapter and its evidence ledger. Interpret the findings in relation to each
research question and to the most relevant prior work.

The chapter must distinguish observation, interpretation, and speculation.
Discuss:
- what the evidence suggests about self-supervised control learning without
  target control curves;
- whether proxy-objective improvements aligned with perceived quality;
- the role and limitations of vocal-aware controls;
- what can and cannot be concluded about cue-point ranking;
- fixed versus variable transition lengths without forcing an invalid direct
  comparison;
- dependency on beat/downbeat quality, source separation, time stretching,
  sample rate, corpus composition, and hand-designed proxy terms;
- internal, construct, external, and conclusion validity;
- likely failure modes and practical implications for a human-in-the-loop
  workflow.

Explain negative or inconclusive results rather than hiding them. Do not make
causal claims from observational comparisons. Do not generalize beyond the
tempo range, track set, participant pool, transition types, or evaluation
protocol actually used. End with concrete future-work priorities that follow
from observed limitations, not a generic list of fashionable methods.
```

## Prompt 8: Conclusion schreiben

Modell: `gpt-6-astra`  
Reasoning: `high`

```text
Write overleaf/chapters/07_conclusion.tex as a concise answer to the thesis
research questions. Base it only on the final Results and Discussion chapters.

Restate the problem and approach briefly, summarize the strongest supported
findings, identify the main scientific and engineering contributions, and
state the most important limitation. Do not introduce new experiments,
citations, terminology, or numerical results. Avoid repeating the abstract
word for word. End with a restrained outlook describing the next research step
that would most directly close the current evidence gap. Aim for roughly two
to three pages unless the university guidelines require otherwise.
```

## Prompt 9: Englischen und deutschen Abstract schreiben

Modell: `gpt-6-astra`  
Reasoning: `high`

```text
Write the final English abstract in
overleaf/chapters/00_abstractEnglish.tex and the required German summary in
overleaf/chapters/00_abstract.tex. Remove all template text.

Read the final Introduction, Methodology, Results, Discussion, and Conclusion
first. Each abstract must be self-contained and cover motivation, research
problem, method, data/evaluation scope, principal results, and the supported
conclusion. Include only the most decision-relevant quantitative result or two
and always provide the necessary context. Do not cite literature unless the
university explicitly requires citations in abstracts. Do not introduce
acronyms that are used only once. Keep the English and German versions
semantically equivalent rather than mechanically literal. Respect the word or
page limit in the examination regulations; if no limit can be verified, flag
that fact before choosing a length.
```

## Prompt 10: Wissenschaftliches Englisch sprachlich ueberarbeiten

Modell: `gpt-5.6-terra`  
Reasoning: `medium`

```text
Perform a language-only edit of the specified thesis chapter. Preserve all
technical meaning, numbers, citations, LaTeX commands, labels, equations,
tables, and the strength of every claim. Do not add new scientific content.

Improve the text to clear scientific English at master's-student level:
- remove awkward literal translations from German;
- shorten overlong sentences;
- replace vague pronouns and unclear antecedents;
- improve paragraph cohesion and topic sentences;
- reduce unnecessary passive voice and nominalizations;
- remove repetition, filler, promotional language, and generic AI-style prose;
- enforce consistent tense: present for the thesis/method and established
  knowledge, past for completed experimental procedures and observations;
- enforce consistent terminology and abbreviation use.

Return a short list of passages whose meaning is ambiguous or whose claims
appear unsupported, but do not silently repair them by inventing an
interpretation. Compile the document if the local toolchain is available.
```

## Prompt 11: Finaler wissenschaftlicher Konsistenz-Audit

Modell: `gpt-6-astra`  
Reasoning: `xhigh`

```text
Conduct a final adversarial audit of the complete thesis. Assume that a strict
reviewer will check every contribution and numerical claim.

Check:
- consistency among title, abstract, research questions, contributions,
  methods, results, discussion, and conclusion;
- whether every research question is answered and every claimed contribution
  has evidence;
- leakage between training, validation, and test data;
- accidental presentation of validation development as held-out evaluation;
- synthetic-versus-real experiment labeling;
- fair comparison conditions across model and renderer variants;
- use of "self-supervised", "teacher", "ground truth", "baseline",
  "significant", "generalization", and "real-time";
- agreement of all dataset sizes, epoch counts, best epochs, metric values,
  transition lengths, sample rates, and model descriptions with the immutable
  artifacts;
- citation coverage and bibliography metadata;
- unresolved TODOs, template text, duplicated labels, broken references,
  missing figures/tables, and LaTeX warnings;
- privacy, corpus-rights, participant-consent, and reproducibility statements.

First produce a severity-ranked audit with blockers, major issues, and minor
issues. Then fix only issues that are unambiguous and supported by repository
evidence. Leave explicit TODOs for anything requiring new experiments,
supervisor input, participant information, legal clarification, or an
interpretive choice. Compile from a clean LaTeX state if possible and document
the exact command and outcome. Do not commit.
```

## Empfohlene Reihenfolge

1. Prompt 0: LaTeX-/Struktur-Audit
2. Prompt 1: Forschungsargument und Claim-Evidence-Matrix
3. Prompt 3: Related-Work-Audit
4. Prompt 4: Methodology/System Design
5. Prompt 5: Implementation
6. Fehlende Experimente und Bewertungen abschliessen
7. Prompt 6: Results
8. Prompt 7: Discussion
9. Prompt 2 nochmals gegen den finalen Stand pruefen
10. Prompt 8: Conclusion
11. Prompt 9: Abstracts
12. Prompt 10 kapitelweise, anschliessend Prompt 11 global

Results, Discussion, Conclusion und Abstract sollten erst nach dem Einfrieren
der final berichteten Experimente geschrieben werden. Introduction, Related
Work, Methodology und Implementation koennen vorher belastbar entwickelt
werden, sofern offene Evidenz sichtbar markiert bleibt.
