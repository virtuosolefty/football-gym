import unittest

from tools.evaluate_tracks import evaluate


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.labels = {"format": "football-evaluation-1", "clip": {"id": "clip", "sha256": "abc", "width": 640, "height": 360, "start": 0, "end": 1},
                       "annotator": {"id": "coach", "role": "coach", "independent": True}, "conditions": ["indoor"],
                       "frames": [{"time": 0, "status": "visible", "x": .5, "y": .5, "radius": 10},
                                  {"time": .1, "status": "absent"}, {"time": .2, "status": "occluded"}],
                       "contacts_reviewed": True, "contacts": [{"time": .5, "kind": "contact", "foot": "left"}]}
        self.run = {"start": 0, "end": 1, "width": 640, "height": 360, "media_sha256": "abc", "samples": [
            {"time": 0, "found": True, "x": .5, "y": .5, "score": .8},
            {"time": .1, "found": True, "x": .5, "y": .5, "score": .66},
            {"time": .2, "found": True, "x": .5, "y": .5}, {"time": .3, "found": False}],
            "candidates": [{"time": .55}, {"time": .6}]}

    def test_wrong_object_and_incomplete_labels_are_not_coverage_success(self):
        result = evaluate(self.labels, self.run)
        self.assertEqual(result["counts"], {"correct": 1, "wrong": 1, "missed_visible": 0, "correct_absent": 0, "occluded": 1, "unlabelled": 1})
        self.assertEqual(result["correct_detection_precision"], .5)
        self.assertEqual(len(result["contact_matches"]), 1)
        self.assertEqual(result["false_contact_proposals"], 1)

    def test_unreviewed_contacts_are_not_silently_scored_as_negative_ground_truth(self):
        self.labels.pop("contacts_reviewed")
        result = evaluate(self.labels, self.run)
        self.assertFalse(result["contact_labels_complete"])
        self.assertIsNone(result["false_contact_proposals"])
        self.assertIsNone(result["missed_contacts"])

    def test_independence_hashes_and_windows_are_required(self):
        self.labels["annotator"]["independent"] = False
        with self.assertRaises(ValueError):
            evaluate(self.labels, self.run)
        self.assertFalse(evaluate(self.labels, self.run, allow_implementer=True)["independent_self_declared"])
        self.labels["annotator"]["independent"] = True
        with self.assertRaises(ValueError):
            evaluate(self.labels, {**self.run, "media_sha256": "different"})
        with self.assertRaises(ValueError):
            evaluate(self.labels, {**self.run, "start": .1})
