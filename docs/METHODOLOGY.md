# SVEA Eval methodology

## Purpose

SVEA Eval measures whether a language model can perform useful tasks *in
Swedish*. It does not assume that knowledge recall, grammaticality,
instruction-following, grounding and safety are interchangeable. The primary
output is therefore a capability profile with visible coverage, not a single
rank.

## Design principles

1. **Swedish first.** Prompts are authored or adapted for Swedish usage rather
   than mechanically translated from English.
2. **Domain × task coverage.** Domains describe where a capability is used;
   task types describe what the model must do. Both are reported.
3. **Deterministic when possible.** Exact, MCQ, numeric, JSON, constraint and
   fact-containment scorers are preferred over model judges.
4. **Missing stays missing.** A rubric item without a judge is unscored, not
   zero. A missing domain lowers coverage, not the measured score.
5. **Protocol is evidence.** Model revision, prompt, decoding, backend, raw
   answer, latency, suite version and judge identity travel with every run.
6. **Perturbations reveal brittleness.** Contrast pairs introduce one
   meaningful pressure while trying to preserve the underlying capability.
7. **Safety is visible.** The weakest domain and safety slices are reported
   separately and cannot be compensated away by stronger trivia scores.

## Public pilot

`svea-core` v0.2 contains 55 development items across eight domains. The pilot
is intentionally small enough to inspect. Twelve pairs compare a base case with
a challenge involving a distractor, stricter output, reverse reasoning, absent
evidence, longer dependency or unsafe near-neighbor.

Version 0.2 adds four LIX questions, four dependency parsing or Average
Dependency Distance questions and seven targeted capability probes covering
translation, cited grounding, function calls, tool recovery, safety and compact
long-context revision tracking. The original v0.1 snapshot remains bundled so
published v0.1 artifacts can be reproduced.

It is public, and model developers may train on it. Its valid uses are:

- checking the runner and a model integration;
- obtaining an early capability profile;
- finding failures worth turning into reviewed future items;
- calibrating scorers and judges;
- demonstrating the result and publication contract.

It is not sufficient for claims that one model is generally “best in Swedish.”

## Scoring

All item scores are normalized to 0–1.

| Scorer | Behavior |
|---|---|
| `choice` | requires the declared response format; current pilot items give 1.0 for exactly one A–F letter, 0.5 for an unambiguous correct leading choice with extra text, and mark the latter malformed and not passed |
| `exact` | Unicode-normalized, case-insensitive answer or declared alias |
| `numeric` | parses Swedish decimal commas, applies an explicit tolerance and exposes absolute and relative error; items may opt into declared error-based partial credit |
| `contains_all` | requires at least one alias from every fact group and rejects forbidden facts |
| `json_exact` | parses raw or fenced JSON and compares one or more explicitly declared typed values |
| `constraints` | evaluates explicit line, word, prefix and term checks |
| `rubric` | remains missing until a named judge returns dimension scores |

Constraint items may receive a partial 0–1 score so the failure is
interpretable. `passed` requires every declared constraint. Other deterministic
scorers are normally binary unless an item explicitly declares a partial-credit
method.

LIX and dependency questions have reviewed gold calculations stored with each
item. Tokenization, treatment of the root and rounding are declared in the
prompt. Deterministic score details expose the counts, head vectors, distances
and intermediate calculations used to obtain the expected result. The small
public slice is a diagnostic of Swedish structural analysis and arithmetic, not
a standalone proxy for general model quality.

The LIX cluster deliberately separates three related capabilities: direct
answer-only calculation, explicit `A`/`B`/`C` component decomposition, and
auditing a supplied calculation. This reveals whether a failure comes from
counting, arithmetic or error recognition without asking for or publishing
hidden chain-of-thought.

Patch v0.2.2 adds `relative_error` partial credit to the two direct LIX
calculation items. Their score is `max(0, 1 - |answer - gold| / |gold|)`, while
`passed` still requires the answer to fall within the declared tolerance. The
prompt's “answer only with the number” contract is enforced: explanatory or
otherwise malformed responses receive zero. Absolute error, relative error and
the scoring formula are published in scorer details. For example, `63.3`
against `22.5` has an absolute error of `40.8` and a relative error of `181.3%`,
so its partial score is clamped to zero.

Patch v0.2.1 corrected the room-booking contrast. The free item now accepts the
source notation `HH.MM` as well as normalized `HH:MM`, since it did not prescribe
a time format. The strict item enforces its stated `TT:MM`, key-order and
no-code-fence requirements. Published artifacts retain this change in their
rescoring history; target and judge inference was not repeated.

Rubric judging uses named dimensions with integer scores from 0 to 4. The
normalized item score is the mean divided by four. Each item declares its pass
threshold. The raw judge response is retained. Judge choice is part of the
protocol and must not be mixed across runs without calibration.

## Reasoning protocol

Reasoning-enabled generation is evaluated as a separate target protocol. For
Ollama runs, the artifact records whether `think` was enabled and any additional
reasoning-token allowance. The item's declared `max_tokens` remains the intended
final-answer budget; the additional allowance expands the native generation cap
for reasoning-capable models.

The public artifact retains only the final answer and non-content metadata such
as reasoning character count, latency and total generated tokens. Private hidden
chain-of-thought is not published. The project page labels each run as reasoning
on, reasoning off or provider default, and shows an on/off score delta only when
the model revision, suite, decoding settings and judge protocol otherwise match.

Target and judge reasoning settings are independent. Enabling target reasoning
does not alter the judge protocol.

Rubric items may also declare deterministic response constraints. In v0.2 the
new rubric items forbid prompt echo, and the safe-helpfulness item additionally
checks the word limit and number of numbered answers. A failed hard constraint
is shown alongside the judge rationale, prevents a pass and caps the item score
at the declared value; it never erases the judge's original score or output.

## Aggregation

The report includes:

- **micro score:** mean over all scored items;
- **macro-domain score:** mean of the available domain means;
- **minimum-domain score:** weakest measured domain;
- **coverage:** scored items and measured versus declared domains;
- **pass rate:** share of scored items whose full pass condition is met;
- **malformed rate:** outputs that cannot be parsed for the required format;
- **prompt-echo rate:** responses that reproduce the benchmark system scaffold;
- **repeated-span rate:** responses containing a repeated non-overlapping
  twelve-token span;
- **output-token profile:** median, p95 and total reported output tokens;
- **95% interval:** a normal-approximation interval around each slice mean;
- **robustness gap:** mean base score minus mean challenge score for complete
  contrast pairs;
- **pair retention:** share of pairs where the challenge score is at least the
  base score.

Intervals in the pilot are descriptive and wide. A future larger release
should use stratified bootstrap intervals and publish power calculations.

## Comparability contract

Treat two scores as comparable only if these fields match:

- suite ID, exact version and split;
- item selection and limits;
- system prompt and message formatting;
- temperature, seed and token limits;
- target reasoning mode and additional reasoning-token allowance;
- deterministic scorer implementation version;
- judge model/version and rubric protocol for judged items.

Provider model aliases may change behind a stable name. Use an immutable
revision, snapshot, deployment version or evaluation date. Quantization,
hardware-sensitive settings and local chat-template modifications belong in a
run's limitations until the schema gains dedicated fields.

## Publication policy

The site builder publishes only runs with `status=completed` and
`diagnostic=false`. A maintainer must additionally review model identity,
revision, protocol, raw artifact availability and judge calibration before
committing a run to `results/runs/`.

The oracle backend exists only to test plumbing. It can never produce model
evidence.

## Roadmap to a defensible v1

- Native-speaker review by at least two independent annotators per item.
- Larger, balanced slices and preregistered inclusion criteria.
- A versioned private or rotating holdout with contamination canaries.
- Human calibration sets for open-answer judges, including disagreement.
- Direct adapters for upstream Swedish suites without relicensing their data.
- Speech, OCR/vision and interactive tool-use tracks.
- Swedish regional, demographic and accessibility checks designed with
  affected communities.
