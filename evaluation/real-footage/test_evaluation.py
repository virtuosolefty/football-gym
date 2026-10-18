import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("field_evaluate", Path(__file__).with_name("evaluate.py"))
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class MatchingTests(unittest.TestCase):
    def test_contacts_match_once_within_tolerance(self):
        self.assertEqual(evaluate.matched_events([1.30, 1.35, 2.03], [1.38, 2.02]), 2)

    def test_absent_or_distant_predictions_are_not_matches(self):
        self.assertEqual(evaluate.matched_events([], [1.38]), 0)
        self.assertEqual(evaluate.matched_events([.5, 3], [1.38, 2.02]), 0)


if __name__ == "__main__":
    unittest.main()
