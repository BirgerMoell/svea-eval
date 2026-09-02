import json
import tempfile
import unittest
from pathlib import Path

from svea_eval.backends import GenerationConfig, OracleBackend
from svea_eval.data import load_suite
from svea_eval.runner import run_evaluation


class RunnerTests(unittest.TestCase):
    def test_oracle_run_is_resumable_and_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata, items = load_suite()
            output = Path(directory) / "oracle.json"
            first = run_evaluation(
                suite_metadata=metadata,
                items=items,
                backend=OracleBackend(),
                output=output,
                config=GenerationConfig(),
                limit=4,
            )
            second = run_evaluation(
                suite_metadata=metadata,
                items=items,
                backend=OracleBackend(),
                output=output,
                config=GenerationConfig(),
                limit=4,
            )
            self.assertEqual(first["status"], "completed")
            self.assertTrue(first["diagnostic"])
            self.assertEqual(first["summary"]["overall"]["score"], 1.0)
            self.assertEqual(second["summary"]["counts"]["scheduled"], 4)
            self.assertEqual(len(output.with_suffix(".samples.jsonl").read_text().splitlines()), 4)
            self.assertEqual(json.loads(output.read_text())["model"]["backend"], "oracle-diagnostic")

    def test_oracle_judge_completes_rubric_items(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata, items = load_suite()
            rubric_item = [item for item in items if item.scoring["type"] == "rubric"][0]
            run = run_evaluation(
                suite_metadata=metadata,
                items=[rubric_item],
                backend=OracleBackend(),
                judge_backend=OracleBackend(),
                judge_revision="oracle-rev",
                output=Path(directory) / "judged.json",
                config=GenerationConfig(),
            )
            self.assertEqual(run["status"], "completed")
            self.assertEqual(run["samples"][0]["score"], 1.0)
            self.assertEqual(run["samples"][0]["judgment"]["model"], "svea/oracle-diagnostic")
            self.assertEqual(run["judge"]["revision"], "oracle-rev")

    def test_resume_rejects_changed_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata, items = load_suite()
            output = Path(directory) / "changed.json"
            run_evaluation(
                suite_metadata=metadata,
                items=items,
                backend=OracleBackend(),
                output=output,
                config=GenerationConfig(system_prompt="Första protokollet"),
                limit=1,
            )
            with self.assertRaisesRegex(ValueError, "resume manifest differs"):
                run_evaluation(
                    suite_metadata=metadata,
                    items=items,
                    backend=OracleBackend(),
                    output=output,
                    config=GenerationConfig(system_prompt="Ändrat protokoll"),
                    limit=1,
                )
