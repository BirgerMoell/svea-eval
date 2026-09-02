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

`svea-core` v0.1 contains 40 development items: five in each of eight domains.
The pilot is intentionally small enough to inspect. Eight pairs compare a base
case with a challenge involving a distractor, stricter output, reverse
reasoning or absent evidence.

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
| `numeric` | parses Swedish decimal commas and applies an explicit tolerance |
| `contains_all` | requires at least one alias from every fact group and rejects forbidden facts |
| `json_exact` | parses raw or fenced JSON and compares one or more explicitly declared typed values |
| `constraints` | evaluates explicit line, word, prefix and term checks |
| `rubric` | remains missing until a named judge returns dimension scores |

Constraint items may receive a partial 0–1 score so the failure is
interpretable. `passed` requires every declared constraint. Other deterministic
scorers are normally binary.

Rubric judging uses named dimensions with integer scores from 0 to 4. The
normalized item score is the mean divided by four. Each item declares its pass
threshold. The raw judge response is retained. Judge choice is part of the
protocol and must not be mixed across runs without calibration.

## Aggregation

The report includes:

- **micro score:** mean over all scored items;
- **macro-domain score:** mean of the available domain means;
- **minimum-domain score:** weakest measured domain;
- **coverage:** scored items and measured versus declared domains;
- **pass rate:** share of scored items whose full pass condition is met;
- **malformed rate:** outputs that cannot be parsed for the required format;
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
