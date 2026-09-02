import json
import tempfile
import unittest
from pathlib import Path

from svea_eval.site import build_site_data


class SiteTests(unittest.TestCase):
    def test_site_builder_excludes_diagnostic_and_partial_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            results.mkdir()
            base = {
                "run_id": "run-1",
                "status": "completed",
                "diagnostic": False,
                "model": {"id": "model", "revision": "abc", "backend": "openai-compatible"},
                "judge": {
                    "id": "judge-model",
                    "revision": "judge-rev",
                    "backend": "openai-compatible",
                },
                "suite": {"id": "svea-core", "version": "0.1.1"},
                "protocol": {"temperature": 0},
                "finished_at": "2026-09-02T00:00:00+00:00",
                "summary": {
                    "overall": {"score": 0.5},
                    "counts": {"scheduled": 40, "scored": 40},
                },
                "samples": [
                    {
                        "item_id": "svea-v01-lang-001-clean",
                        "response": "A",
                        "score": 1.0,
                        "passed": True,
                        "scorer": "choice",
                        "parsed": "A",
                        "score_details": {"expected": "A"},
                        "scoring_error": None,
                        "latency_ms": 2.0,
                        "input_tokens": 10,
                        "output_tokens": 1,
                        "finish_reason": "stop",
                        "judgment": None,
                        "error": None,
                    }
                ],
                "limitations": [],
                "rescoring_history": [
                    {
                        "source_suite_version": "0.1.0",
                        "target_suite_version": "0.1.1",
                        "reason": "Reviewed correction.",
                    }
                ],
            }
            (results / "publish.json").write_text(json.dumps(base))
            (results / "diagnostic.json").write_text(
                json.dumps({**base, "run_id": "run-2", "diagnostic": True})
            )
            (results / "partial.json").write_text(
                json.dumps({**base, "run_id": "run-3", "status": "partial"})
            )
            built = build_site_data(docs_dir=root / "docs", results_dir=results)
            payload = json.loads((root / "docs/data/results.json").read_text())
            self.assertEqual(built["runs"], 1)
            self.assertEqual([run["run_id"] for run in payload["runs"]], ["run-1"])
            self.assertEqual(payload["runs"][0]["judge"]["id"], "judge-model")
            self.assertEqual(
                payload["runs"][0]["items"][0]["item"]["id"],
                "svea-v01-lang-001-clean",
            )
            self.assertEqual(payload["runs"][0]["items"][0]["sample"]["response"], "A")
            self.assertIsNone(payload["runs"][0]["items"][0]["item"]["rubric"])
            self.assertEqual(
                payload["runs"][0]["rescoring_history"][0]["target_suite_version"],
                "0.1.1",
            )
            bundle = (root / "docs/data/site-data.js").read_text()
            self.assertTrue(bundle.startswith("window.SVEA_SITE_DATA = "))
            self.assertIn('"run_id":"run-1"', bundle)
