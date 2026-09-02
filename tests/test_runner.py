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
            self.assertEqual(run["samples"][0]["generation_metadata"], {})
            self.assertEqual(run["samples"][0]["judgment"]["generation_metadata"], {})
            self.assertEqual(run["protocol"]["judge_temperature"], 0.0)
            self.assertEqual(run["protocol"]["judge_seed"], 17)

    def test_item_prefix_selects_the_version_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata, items = load_suite()
            run = run_evaluation(
                suite_metadata=metadata,
                items=items,
                backend=OracleBackend(),
                judge_backend=OracleBackend(),
                output=Path(directory) / "extension.json",
                config=GenerationConfig(),
                item_prefixes=("svea-v02-",),
            )
            self.assertEqual(run["status"], "completed")
            self.assertTrue(run["diagnostic"])
            self.assertEqual(run["summary"]["counts"]["scheduled"], 15)
            self.assertEqual(run["protocol"]["item_prefix_filter"], ["svea-v02-"])

    def test_resume_rescores_preserved_judgment(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata, items = load_suite()
            rubric_item = next(item for item in items if item.id == "svea-v01-work-004")
            output = Path(directory) / "rescored.json"
            run_evaluation(
                suite_metadata=metadata,
                items=[rubric_item],
                backend=OracleBackend(),
                judge_backend=OracleBackend(),
                output=output,
                config=GenerationConfig(),
            )
            sidecar = output.with_suffix(".samples.jsonl")
            sample = json.loads(sidecar.read_text())
            sample.update(
                {
                    "score": None,
                    "passed": None,
                    "parsed": None,
                    "score_details": {},
                    "scoring_error": "invalid judge response",
                }
            )
            sample["judgment"]["response"] = (
                '{"scores":{"täckning":3,"trohet":4,"koncision":4},'
                '"reason":"Täckningen har en mindre brist."}'
            )
            sidecar.write_text(json.dumps(sample, ensure_ascii=False) + "\n")

            resumed = run_evaluation(
                suite_metadata=metadata,
                items=[rubric_item],
                backend=OracleBackend(),
                judge_backend=OracleBackend(),
                output=output,
                config=GenerationConfig(),
            )

            self.assertEqual(resumed["status"], "completed")
            self.assertAlmostEqual(resumed["samples"][0]["score"], 11 / 12)
            self.assertEqual(len(sidecar.read_text().splitlines()), 2)

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
