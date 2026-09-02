# Contributing to SVEA Eval

Contributions are welcome from Swedish speakers, domain experts, researchers
and model engineers. The most valuable work now is reviewer-checked task data,
judge calibration and reproducible model runs.

## Add an item

Each JSONL item must provide:

- a stable ID, suite version and split;
- domain, capability and task type;
- an unambiguous prompt and answer instruction;
- a deterministic gold answer or explicit rubric;
- source kind, direct URL, license note and access date;
- review status and relevant tags;
- a contrast-pair ID and variant when applicable.

Before submitting, answer these questions in the pull request:

1. Was the Swedish written or reviewed by a native speaker?
2. Is the answer stable, unambiguous and supported by the linked source?
3. Can the task be scored deterministically? If not, why is a judge needed?
4. Does the item contain copyrighted text, personal data or a secret test?
5. What model failure does the item distinguish from nearby items?

Do not inflate a suite by making superficial paraphrases. A contrast variant
must introduce a named behavioral pressure and preserve the capability being
tested.

## Add a result

Run the complete versioned suite with an immutable model revision where
possible. Open-generation items require a pinned judge and a documented judge
calibration. Keep the raw run outside `docs/`; commit the reviewed run to
`results/runs/`, then rebuild the public data:

```bash
svea build-site --results results/runs --docs docs
```

The site builder refuses to publish partial and diagnostic artifacts. A human
reviewer must still verify that the run used a comparable protocol and that its
model identity is accurate.

## Checks

```bash
PYTHONPATH=src python3 -m svea_eval validate
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m svea_eval build-site
python3 -m compileall -q src
```

## Licensing

Code contributions are Apache-2.0. By contributing original task content to
the bundled SVEA datasets, you agree to release that task content under
CC0-1.0. External source terms still apply; do not submit content you lack the
right to redistribute.
