import math
import tempfile
import unittest

from football import domain, video
from football.store import Store
from test_domain import player


def run_data(media_id="0" * 32, **changes):
    samples = [{"time": round(i / 10, 2), "found": True, "x": .5, "y": .4 + .15 * math.cos(i / 10 * 2 * math.pi)} for i in range(300)]
    return {"media_id": media_id, "protocol": "juggling", "duration": 30.1, "start": 0, "end": 30,
            "width": 640, "height": 360, "samples": samples, **changes}


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.store.set("profile", player())
        self.media = self.store.append("media", {"filename": "fixture.webm", "name": "fixture", "size": 4, "mime": "video/webm"})
        (self.store.media / "fixture.webm").write_bytes(b'\x1a\x45\xdf\xa3')

    def create(self, **changes):
        return self.store.add_analysis(run_data(self.media["id"], **changes))

    def annotate(self, run, events, **changes):
        return self.store.annotate_video({"analysis_id": run["id"], "events": events, "confirmed": True, "reviewer": "QA", **changes})

    def assessment(self, run, annotation):
        return self.store.assessment_from_video({"analysis_id": run["id"], "annotation_id": annotation["id"],
            "conditions": {"distance": 3, "width": 1, "surface": "Grass", "duration": 30},
            "quality": {"visible": True, "fixed_camera": True, "setup_valid": True}, "notes": "Video reviewed.",
            "metrics": {"contacts": 999}})

    def test_track_turns_are_proposals_and_never_scores(self):
        run = self.create()
        self.assertEqual(run["report"]["status"], "SUSPECT")
        self.assertEqual(run["report"]["coverage"], 1)
        self.assertGreater(len(run["candidates"]), 20)
        self.assertEqual(self.store.attempts(), [])

    def test_coverage_gaps_and_resolution_gate_proposals(self):
        for changes in [{"samples": []}, {"width": 160, "height": 90}, {"samples": [{"time": 0, "found": True, "x": .5, "y": .5}, {"time": 29.9, "found": True, "x": .5, "y": .5}]}]:
            with self.subTest(changes=changes):
                result = video.analysis(run_data(**changes))
                self.assertEqual(result["report"]["status"], "UNMEASURABLE")
                self.assertEqual(result["candidates"], [])
        data = run_data()
        for sample in data["samples"][100:120]:
            sample.update(found=False, x=None, y=None)
        result = video.analysis(data)
        self.assertGreater(result["report"]["coverage"], .85)
        self.assertEqual(result["report"]["status"], "UNMEASURABLE")

    def test_invalid_frame_data_and_missing_media(self):
        cases = [{"duration": math.nan}, {"end": 60}, {"width": True}, {"samples": [{"time": 0, "found": True, "x": 2, "y": .5}]},
                 {"samples": [{"time": 1, "found": False}, {"time": .5, "found": False}]}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(domain.ValidationError):
                video.analysis(run_data(**changes))
        with self.assertRaises(domain.ValidationError):
            self.store.add_analysis(run_data())

    def test_tracker_configuration_is_preserved_and_validated(self):
        seed = {"x": .5, "y": .775, "radius": 8, "colour": [237, 207, 50]}
        run = self.create(seed=seed)
        self.assertEqual(run["configuration"]["seed"], seed)
        with self.assertRaises(domain.ValidationError):
            self.create(seed={**seed, "colour": [256, 0, 0]})

    def test_detector_runs_record_engine_model_and_confidence(self):
        detector = {"model": "yolox_nano", "size": 416, "score_threshold": .2}
        samples = [{"time": round(i / 10, 2), "found": True, "x": .5, "y": .4 + .15 * math.cos(i / 10 * 2 * math.pi), "score": .8} for i in range(300)]
        run = self.create(method="detector", detector=detector, samples=samples)
        self.assertEqual(run["version"], "detector-ball-4")
        self.assertEqual(run["configuration"]["method"], "detector")
        self.assertEqual(run["configuration"]["detector"], detector)
        self.assertEqual(run["samples"][0]["score"], .8)
        self.assertEqual(run["report"]["status"], "SUSPECT")
        colour = self.create()
        self.assertEqual(colour["configuration"]["method"], "colour")
        self.assertNotIn("score", colour["samples"][0])

    def test_detector_seed_needs_no_colour_but_colour_runs_do(self):
        detector = {"model": "yolox_nano", "size": 416, "score_threshold": .2}
        seed = {"x": .5, "y": .5, "radius": 8, "time": 0}
        run = self.create(method="detector", detector=detector, seed=seed)
        self.assertEqual(run["configuration"]["seed"], seed)
        with self.assertRaises(domain.ValidationError):
            self.create(seed=seed)

    def test_detector_configuration_and_scores_are_validated(self):
        detector = {"model": "yolox_nano", "size": 416, "score_threshold": .2}
        bad = [{"method": "magic"}, {"method": "detector"}, {"method": "detector", "detector": {**detector, "size": 5}},
               {"method": "detector", "detector": {**detector, "score_threshold": 2}}, {"method": "detector", "detector": {"size": 416}},
               {"method": "detector", "detector": detector, "samples": [{"time": 0, "found": True, "x": .5, "y": .5, "score": 1.5}]}]
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(domain.ValidationError):
                video.analysis(run_data(**changes))

    def test_seed_frame_time_is_preserved_and_must_lie_inside_the_window(self):
        seed = {"x": .5, "y": .775, "radius": 8, "colour": [237, 207, 50], "time": 12.5}
        run = self.create(seed=seed)
        self.assertEqual(run["configuration"]["seed"], seed)
        self.assertEqual(run["version"], "contrast-ball-4")
        for time in (-1, 31, math.nan):
            with self.subTest(time=time), self.assertRaises(domain.ValidationError):
                self.create(seed={**seed, "time": time})
        with self.assertRaises(domain.ValidationError):
            self.create(start=13, seed=seed)

    def test_review_confirmation_event_types_and_time_bounds(self):
        run = self.create()
        for events, changes in [([{"time": 1, "kind": "contact"}], {"confirmed": False}),
                                ([{"time": 31, "kind": "contact"}], {}), ([{"time": 1, "kind": "pass"}], {}),
                                ([{"time": 1, "kind": "contact"}] * 2, {}), ([{"time": 1, "kind": "contact", "foot": "left"}], {})]:
            with self.assertRaises(domain.ValidationError):
                self.annotate(run, events, **changes)

    def test_juggling_best_run_and_original_events_are_preserved(self):
        run = self.create()
        events = [{"time": t, "kind": "contact"} for t in [1, 2, 3]] + [{"time": 4, "kind": "drop"}, {"time": 5, "kind": "contact"}]
        labels = self.annotate(run, events)
        saved = self.assessment(run, labels)
        self.assertEqual(saved["metrics"]["contacts"], 3)  # Submitted 999 is deliberately ignored.
        self.assertEqual(self.store.attempts()[0]["confidence"], "Video-annotated · self-reviewed")
        self.assertEqual(self.store.attempts()[0]["feedback"][0]["times"], [4])
        with self.assertRaises(domain.ValidationError):
            self.assessment(run, labels)
        next_labels = self.annotate(run, [{"time": 1, "kind": "contact"}])
        with self.assertRaises(domain.ValidationError):
            self.assessment(run, labels)  # A stale timeline cannot silently create another assessment.
        self.assertEqual(len(self.store.events("video_annotation")), 2)
        self.assertEqual(self.store.attempts()[0]["feedback"][0]["times"], [4])
        self.assertEqual(self.store.analyses()[0]["annotation"]["id"], next_labels["id"])

    def test_short_window_can_be_reviewed_but_cannot_create_assessment(self):
        run = self.create(duration=4, end=3, samples=[])
        labels = self.annotate(run, [{"time": 1, "kind": "contact"}])
        with self.assertRaises(domain.ValidationError):
            self.assessment(run, labels)

    def test_pass_metrics_foot_usage_and_cues_link_to_labelled_evidence(self):
        run = self.create(protocol="wall")
        events = [{"time": i + 1, "kind": "pass", "success": i < 7, "foot": "weak" if i == 0 else "strong"} for i in range(10)]
        labels = self.annotate(run, events)
        assessed = self.assessment(run, labels)
        self.assertEqual(assessed["metrics"], {"attempts": 10, "successes": 7, "weak_foot": 1})
        feedback = self.store.attempts()[0]["feedback"]
        self.assertEqual(len(feedback), 2)
        self.assertEqual(feedback[0]["times"], [8, 9, 10])
        self.assertEqual(feedback[1]["drill_id"], "wall-3")
        self.assertEqual(self.store.events("analysis")[0]["candidates"], [])

    def test_unknown_feet_and_twenty_outcome_protocols(self):
        with self.assertRaises(domain.ValidationError):
            video.measurements("wall", [{"kind": "pass", "success": True, "foot": "unknown"}])
        with self.assertRaises(domain.ValidationError):
            video.measurements("gates", [{"kind": "pass", "success": True}] * 19)
        self.assertEqual(video.measurements("touch", [{"kind": "pass", "success": True}] * 20)["successes"], 20)

    def test_slalom_timing_uses_timestamps_and_flags_missed_cones(self):
        events = [{"time": 2, "kind": "start"}, {"time": 4, "kind": "miss"}, {"time": 12.5, "kind": "finish"}]
        self.assertEqual(video.measurements("slalom", events), {"seconds": 10.5, "missed": 1})
        for invalid in [events[:2], events + [{"time": 1, "kind": "start"}], [{"time": 5, "kind": "start"}, {"time": 4, "kind": "finish"}]]:
            with self.assertRaises(domain.ValidationError):
                video.measurements("slalom", invalid)

    def test_video_events_export_and_delete_with_existing_data(self):
        run = self.create()
        self.annotate(run, [{"time": 1, "kind": "contact"}])
        exported = self.store.export()
        self.assertIn("video_annotation", [e["kind"] for e in exported["events"]])
        self.store.erase()
        self.assertEqual(self.store.analyses(), [])
        self.assertEqual(list(self.store.media.iterdir()), [])

    def test_correctness_gate_cannot_pass_on_coverage_without_limits(self):
        run = self.create()
        self.assertEqual(run["report"]["coverage"], 1)
        self.assertEqual(run["report"]["status"], "SUSPECT")
        self.assertFalse(run["report"]["quality"]["configured"])
        self.assertIsNone(run["report"]["quality"]["metrics"]["min_score"])

    def test_quality_limits_flag_low_confidence_motion_and_stationary_decoys(self):
        limits = {"min_score": .6, "max_speed": 2, "max_stationary_seconds": .5}
        data = run_data()
        for sample in data["samples"]:
            sample["score"] = .8
        good = video.analysis({**data, "quality_limits": limits})
        self.assertEqual(good["report"]["status"], "REVIEW_REQUIRED")
        self.assertFalse(good["report"]["quality"]["validated"])
        for issue in ("score", "jump", "still", "missing_score"):
            samples = [dict(s) for s in data["samples"]]
            if issue == "score":
                samples[100]["score"] = .4
            elif issue == "jump":
                samples[100]["x"] = .9
            elif issue == "missing_score":
                samples[100].pop("score")
            else:
                for sample in samples:
                    sample["y"] = .5
            result = video.analysis({**data, "samples": samples, "quality_limits": limits})
            self.assertEqual(result["report"]["coverage"], 1)
            self.assertEqual(result["report"]["status"], "SUSPECT", issue)
            self.assertTrue(result["report"]["quality"]["reasons"])
            self.assertEqual(result["candidates"], [])
        for invalid in ({"unknown": 1}, {"min_score": 2}, {"max_speed": math.nan}, [], {"min_score": True}):
            with self.subTest(invalid=invalid), self.assertRaises(domain.ValidationError):
                video.analysis({**data, "quality_limits": invalid})

    def test_gap_turns_remain_uncertain_and_never_bridge_reseed_segments(self):
        samples = [{"time": i / 10, "found": y is not None, "x": .5 if y is not None else None, "y": y}
                   for i, y in enumerate([.1, .2, .35, None, .35, .2, .1, .05])]
        proposals = video.candidates(samples)
        self.assertTrue(proposals)
        self.assertTrue(proposals[0]["uncertain"])
        self.assertEqual(proposals[0]["evidence"], "trajectory_gap")
        for i, sample in enumerate(samples):
            sample["segment"] = 0 if i < 4 else 1
        self.assertEqual(video.candidates(samples), [])
        for sample in samples[2:6]:
            sample.update(found=False, x=None, y=None)
        self.assertEqual(video.candidates(samples), [])

    def test_reseed_provenance_is_saved_and_segments_require_confirmation(self):
        samples = run_data()["samples"]
        for sample in samples[100:]:
            sample["segment"] = 1
        reseeds = [{"time": 10, "x": .5, "y": .55, "radius": 8, "segment": 1}]
        run = self.create(samples=samples, reseeds=reseeds)
        self.assertEqual(run["configuration"]["reseeds"], reseeds)
        self.assertEqual(run["samples"][100]["segment"], 1)
        with self.assertRaises(domain.ValidationError):
            self.create(samples=samples)
        with self.assertRaises(domain.ValidationError):
            self.create(reseeds=reseeds * 2)

    def test_turn_near_window_boundary_is_uncertain_with_only_one_following_detection(self):
        samples = [{"time": i / 10, "found": True, "x": .5, "y": y} for i, y in enumerate([.1, .15, .2, .4, .2])]
        proposals = video.candidates(samples)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["time"], .3)
        self.assertTrue(proposals[0]["uncertain"])
        self.assertEqual(proposals[0]["evidence"], "trajectory_boundary")

    def test_quality_measures_motion_across_a_short_gap(self):
        samples = [{"time": 0, "found": True, "x": .1, "y": .5, "score": .9},
                   {"time": .1, "found": False}, {"time": .2, "found": True, "x": .9, "y": .5, "score": .9}]
        result = video.track_quality(samples, 640, 360, {"min_score": .5, "max_speed": 2, "max_stationary_seconds": 1})
        self.assertEqual(result["metrics"]["max_speed"], 4)
        self.assertEqual(result["status"], "SUSPECT")

    def test_pose_support_preserves_anatomical_side_without_guessing_stronger_foot(self):
        samples = [{"time": i/10, "found": True, "x": .5, "y": y, "radius": .02}
                   for i, y in enumerate([.1, .2, .4, .2, .1])]
        foot = [[.5, .42, .9], [.49, .43, .9], [.53, .43, .9]]
        samples[2]["pose"] = video.pose_sample({"status": "single", "left": foot})
        proposal = video.candidates(samples)[0]
        self.assertEqual((proposal["side"], proposal["foot"], proposal["pose_support"]), ("left", "unknown", "near_foot"))
        self.assertTrue(proposal["uncertain"])
        self.assertEqual(len(video.candidates(samples, require_pose=True)), 1)
        samples[2]["pose"]["right"] = foot
        self.assertEqual(video.candidates(samples)[0]["pose_support"], "ambiguous")
        self.assertEqual(video.candidates(samples, require_pose=True), [])
        samples[2]["pose"] = {"status": "multiple"}
        self.assertEqual(video.candidates(samples)[0]["side"], "unknown")
        samples[2]["pose"] = {"status": "single", "left": [[.5, .42, .2]]*3}
        self.assertEqual(video.candidates(samples)[0]["side"], "unknown")

    def test_pose_evidence_requires_valid_landmarks_and_model_provenance(self):
        data = run_data()
        data["samples"][0]["pose"] = {"status": "absent"}
        with self.assertRaises(domain.ValidationError):
            video.analysis(data)
        result = video.analysis({**data, "pose_model": video.POSE_MODEL})
        self.assertEqual(result["configuration"]["pose_model"], video.POSE_MODEL)
        for bad in ({"status": "multiple", "left": [[.5, .5, .9]]*3},
                    {"status": "single", "left": [[.5, .5, math.nan]]*3}, {"status": "single", "left": []}):
            with self.subTest(bad=bad), self.assertRaises(domain.ValidationError):
                video.pose_sample(bad)
        run = self.create()
        annotation = self.annotate(run, [{"time": 1, "kind": "contact", "side": "right"}])
        self.assertEqual(annotation["events"][0]["side"], "right")
        self.assertEqual(annotation["events"][0]["foot"], "unknown")



if __name__ == "__main__":
    unittest.main()
