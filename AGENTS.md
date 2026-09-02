# SVEA Eval agent guide

SVEA Eval is a Swedish-first LLM capability benchmark. Keep the following
contracts intact when changing it:

- Treat `src/svea_eval/resources/suites/` as the canonical bundled suite data.
- Every item needs explicit provenance, license, scoring, domain, capability,
  task type, and public development status.
- Preserve raw model output and exact run protocol in result artifacts.
- Never turn missing or unjudged evidence into zero.
- Never present diagnostic, oracle, partial, or protocol-mismatched runs as
  leaderboard evidence.
- Keep the dependency-free core working on Python 3.11+.
- API keys are read only from named environment variables and are never saved.
- Use `python3 -m svea_eval validate`, `python3 -m pytest`, and
  `python3 -m svea_eval build-site` before publishing.

The public pilot suite is a development instrument, not a hidden test set.
Contributions should add reviewer metadata and contamination notes rather than
claiming an unreviewed prompt is production-grade evidence.
