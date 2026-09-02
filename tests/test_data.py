import unittest

from svea_eval.data import load_suite, validate_suite


class DataTests(unittest.TestCase):
    def test_bundled_suite_is_valid_and_has_declared_coverage(self):
        metadata, items = load_suite()

        self.assertEqual(validate_suite(metadata=metadata, items=items), [])
        self.assertEqual(metadata["version"], "0.2.2")
        self.assertEqual(len(items), 55)
        self.assertEqual(len({item.domain for item in items}), 8)
        self.assertEqual(len({item.task_type for item in items}), 7)
        self.assertEqual(len({item.pair_id for item in items if item.pair_id}), 12)
        self.assertEqual(
            {domain: len([item for item in items if item.domain == domain]) for domain in metadata["domains"]},
            {
                "swedish_language": 10,
                "civics_public": 5,
                "work_life": 5,
                "health_literacy": 5,
                "stem_reasoning": 9,
                "culture_society": 5,
                "grounding_safety": 8,
                "digital_agency": 8,
            },
        )

    def test_every_item_has_open_provenance_and_review_state(self):
        _, items = load_suite()

        self.assertTrue(all(item.source.url.startswith("https://") for item in items))
        self.assertTrue(all(item.source.license for item in items))
        self.assertTrue(all(item.review_status == "author_reviewed" for item in items))
