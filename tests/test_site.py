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
                "judge": None,
                "suite": {"id": "svea-core", "version": "0.1.0"},
                "finished_at": "2026-09-02T00:00:00+00:00",
                "summary": {
                    "overall": {"score": 0.5},
                    "counts": {"scheduled": 40, "scored": 40},
                },
                "limitations": [],
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
            bundle = (root / "docs/data/site-data.js").read_text()
            self.assertTrue(bundle.startswith("window.SVEA_SITE_DATA = "))
            self.assertIn('"run_id":"run-1"', bundle)
