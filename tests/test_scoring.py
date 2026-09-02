from dataclasses import replace
import unittest

from svea_eval.data import load_suite
from svea_eval.scoring import score_item, score_judgment


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, items = load_suite()
        cls.items = {item.id: item for item in items}

    def test_choice_accepts_labeled_answer(self):
        score = score_item(item=self.items["svea-v01-lang-001-clean"], response="Svaret är A.")
        self.assertEqual(score.value, 1.0)
        self.assertEqual(score.parsed, "A")

    def test_choice_marks_unparseable_output(self):
        score = score_item(item=self.items["svea-v01-lang-001-clean"], response="Jag är osäker.")
        self.assertEqual(score.value, 0.0)
        self.assertTrue(score.details["malformed"])

    def test_numeric_understands_swedish_decimal_comma(self):
        item = replace(self.items["svea-v01-stem-002"], gold={"value": 0.75})
        self.assertTrue(score_item(item=item, response="0,75").passed)

    def test_json_accepts_code_fence_but_not_extra_keys(self):
        item = self.items["svea-v01-ground-003"]
        valid = '```json\n{"station":"Norr-7","saknade_dygn":2,"arsmedelvarde":null}\n```'
        extra = '{"station":"Norr-7","saknade_dygn":2,"arsmedelvarde":null,"gissning":4}'
        self.assertTrue(score_item(item=item, response=valid).passed)
        self.assertFalse(score_item(item=item, response=extra).passed)

    def test_contains_all_rejects_forbidden_stale_fact(self):
        item = self.items["svea-v01-work-001-distractor"]
        score = score_item(item=item, response="Amir på onsdag, inte måndag.")
        self.assertFalse(score.passed)
        self.assertEqual(score.details["forbidden_hits"], ["måndag"])

    def test_constraint_score_exposes_each_check(self):
        item = self.items["svea-v01-digital-003"]
        score = score_item(item=item, response="STATUS: KLAR\nNÄSTA: Skicka rapporten nu.")
        self.assertTrue(score.passed)
        self.assertTrue(all(score.details["checks"].values()))

    def test_rubric_judgment_is_normalized(self):
        item = self.items["svea-v01-health-004"]
        judgment = (
            '{"scores":{"sakerhet":4,"tydlighet":3,"avgransning":4},'
            '"reason":"Säkert."}'
        )
        score = score_judgment(item=item, judgment=judgment)
        self.assertAlmostEqual(score.value, 11 / 12)
        self.assertTrue(score.passed)
