import unittest

from svea_eval.data import load_suite
from svea_eval.rescore import rescore_run


class RescoreTests(unittest.TestCase):
    def test_rescore_reuses_response_and_records_version_change(self):
        metadata, items = load_suite()
        response = '{"ordernummer":4821,"antal":6,"leveransdatum":"2027-11-05"}'
        run = {
            "status": "completed",
            "suite": {"id": "svea-core", "version": "0.1.0"},
            "samples": [
                {
                    "item_id": "svea-v01-work-002",
                    "response": response,
                    "score": 0.0,
                    "passed": False,
                    "scorer": "json_exact",
                    "parsed": {
                        "ordernummer": 4821,
                        "antal": 6,
                        "leveransdatum": "2027-11-05",
                    },
                    "score_details": {},
                    "scoring_error": None,
                    "latency_ms": 1.0,
                    "error": None,
                }
            ],
        }

        updated = rescore_run(
            run=run,
            suite_metadata=metadata,
            items=items,
            reason="Accept the underspecified identifier representation.",
        )

        self.assertEqual(updated["suite"]["version"], "0.1.3")
        self.assertEqual(updated["samples"][0]["response"], response)
        self.assertEqual(updated["samples"][0]["score"], 1.0)
        self.assertTrue(updated["samples"][0]["passed"])
        provenance = updated["rescoring_history"][0]
        self.assertEqual(provenance["source_suite_version"], "0.1.0")
        self.assertEqual(provenance["target_suite_version"], "0.1.3")
        self.assertTrue(provenance["model_responses_reused"])
        self.assertEqual(provenance["changes"][0]["item_id"], "svea-v01-work-002")
