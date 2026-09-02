import tempfile
import unittest
from pathlib import Path

from svea_eval.backends import GenerationConfig, OracleBackend
from svea_eval.data import load_suite
from svea_eval.merge import merge_extension_runs
from svea_eval.runner import run_evaluation


class MergeExtensionTests(unittest.TestCase):
    def test_strict_merge_preserves_base_and_completes_current_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            base_metadata, base_items = load_suite(
                Path("src/svea_eval/resources/suites/svea-core-v0.1")
            )
            current_metadata, current_items = load_suite()
            backend = OracleBackend()
            config = GenerationConfig(seed=42)
            base = run_evaluation(
                suite_metadata=base_metadata,
                items=base_items,
                backend=backend,
                judge_backend=backend,
                output=Path(directory) / "base.json",
                config=config,
            )
            extension = run_evaluation(
                suite_metadata=current_metadata,
                items=current_items,
                backend=backend,
                judge_backend=backend,
                output=Path(directory) / "extension.json",
                config=config,
                item_prefixes=("svea-v02-",),
            )

            merged = merge_extension_runs(
                base_run=base,
                extension_run=extension,
                base_metadata=base_metadata,
                base_items=base_items,
                current_metadata=current_metadata,
                current_items=current_items,
            )

            self.assertEqual(merged["status"], "completed")
            self.assertFalse(merged["diagnostic"])
            self.assertEqual(merged["suite"]["version"], "0.2.2")
            self.assertEqual(merged["summary"]["counts"]["scored"], 55)
            self.assertEqual(
                merged["samples"][0]["response"], base["samples"][0]["response"]
            )
            self.assertTrue(merged["extension_history"][0]["target_protocol_equivalent"])

    def test_merge_rejects_a_target_protocol_change(self):
        base_metadata, base_items = load_suite(
            Path("src/svea_eval/resources/suites/svea-core-v0.1")
        )
        current_metadata, current_items = load_suite()
        base = {
            "status": "completed",
            "suite": {"id": "svea-core", "version": "0.1.3"},
            "model": {"id": "model", "revision": "rev", "backend": "ollama"},
            "judge": {"id": "judge", "revision": "rev", "backend": "ollama"},
            "protocol": {"temperature": 0.0, "seed": 42, "system_prompt": "a", "backend_settings": {}},
            "samples": [{"item_id": item.id} for item in base_items],
        }
        extension = {
            **base,
            "suite": {"id": "svea-core", "version": "0.2.2"},
            "protocol": {**base["protocol"], "temperature": 0.2},
            "samples": [
                {"item_id": item.id}
                for item in current_items
                if item.id not in {base_item.id for base_item in base_items}
            ],
        }
        with self.assertRaisesRegex(ValueError, "temperature"):
            merge_extension_runs(
                base_run=base,
                extension_run=extension,
                base_metadata=base_metadata,
                base_items=base_items,
                current_metadata=current_metadata,
                current_items=current_items,
            )


if __name__ == "__main__":
    unittest.main()
