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

    def test_contacts_maximize_matches_before_minimizing_error_and_ignore_order(self):
        self.labels["contacts"] = [{"time": .3, "foot": "left"}, {"time": .5, "foot": "right"}]
        self.run["candidates"] = [{"time": .4, "side": "right"}, {"time": .16, "side": "left"}]
        result = evaluate(self.labels, self.run)
        self.assertEqual(len(result["contact_matches"]), 2)
        self.assertEqual(result["contact_recall"], 1)
        self.assertEqual(result["contact_precision"], 1)
        self.assertEqual(result["contact_mean_absolute_error_seconds"], .12)
        self.assertEqual(result["contact_side_accuracy"], 1)
        self.labels["contacts"].reverse()
        self.assertEqual(evaluate(self.labels, self.run)["contact_matches"], result["contact_matches"])

    def test_nearest_timing_tiebreak_and_unknown_side_abstention(self):
        self.run["candidates"] = [{"time": .4, "side": "left"}, {"time": .51, "side": "unknown"}]
        result = evaluate(self.labels, self.run)
        self.assertEqual(result["contact_matches"][0]["proposal"], .51)
        self.assertEqual(result["contact_precision"], .5)
        self.assertEqual(result["contact_side_coverage"], 0)
        self.assertIsNone(result["contact_side_accuracy"])

    def test_malformed_detections_and_duplicate_timestamps_are_refused(self):
        for changes in ({"found": "false"}, {"x": float("nan")}, {"score": 1.1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                evaluate(self.labels, {**self.run, "samples": [{**self.run["samples"][1], **changes}]})
        with self.assertRaises(ValueError):
            evaluate(self.labels, {**self.run, "samples": self.run["samples"] * 2})
        with self.assertRaises(ValueError):
            evaluate(self.labels, {**self.run, "candidates": [{"time": .5}, {"time": .5}]})

    def test_reviewed_empty_contacts_and_empty_proposals_have_no_fake_recall(self):
        self.labels["contacts"] = []
        self.run["candidates"] = []
        result = evaluate(self.labels, self.run)
        self.assertIsNone(result["contact_recall"])
        self.assertIsNone(result["contact_precision"])
        self.assertEqual(result["missed_contacts"], 0)

    def test_body_contacts_are_matched_but_not_scored_as_left_or_right_foot(self):
        self.labels["contacts"][0]["foot"] = "body"
        self.run["candidates"] = [{"time": .5, "side": "left"}]
        result = evaluate(self.labels, self.run)
        self.assertEqual(result["contact_recall"], 1)
        self.assertIsNone(result["contact_side_accuracy"])
        self.assertIsNone(result["contact_side_coverage"])

    def test_near_duplicate_samples_cannot_reuse_a_label(self):
        self.run["samples"] = [{"time": 0, "found": False}, {"time": .001, "found": False}]
        with self.assertRaises(ValueError):
            evaluate(self.labels, self.run)
