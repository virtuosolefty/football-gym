import math
import tempfile
import unittest

from football import domain
from football.knowledge import DRILLS
from football.store import Store


def player(**changes):
    return domain.profile({"name": "Test Player", "age_band": "18+", "position": "Midfielder", "goal": "wall",
                           "equipment": ["ball", "wall", "markers", "cones"], "minutes": 20, "consent": True, **changes})


def attempt(protocol="wall", **changes):
    return {"protocol": protocol, "metrics": {"attempts": 24, "successes": 20, "weak_foot": 6},
            "conditions": {"distance": 3, "width": 1, "surface": "Grass", "duration": 30},
            "quality": {"visible": True, "fixed_camera": True, "setup_valid": True}, "notes": "", **changes}


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.store.set("profile", player())

    def test_invalid_numbers_and_non_integral_counts(self):
        for invalid in [True, math.nan, math.inf, -1, "5", 1.5]:
            with self.subTest(value=invalid), self.assertRaises(domain.ValidationError):
                self.store.add_attempt(attempt(metrics={"attempts": 24, "successes": invalid, "weak_foot": 6}))

    def test_successes_and_weak_foot_cannot_exceed_attempts(self):
        for field in ["successes", "weak_foot"]:
            m = {"attempts": 24, "successes": 20, "weak_foot": 6, field: 25}
            with self.assertRaises(domain.ValidationError):
                self.store.add_attempt(attempt(metrics=m))

    def test_consent_and_guardian_permissions(self):
        for changes in [{"consent": False}, {"age_band": "16–17", "guardian": False}, {"age_band": "Under 16"}]:
            with self.assertRaises(domain.ValidationError):
                player(**changes)
        self.assertTrue(player(age_band="16–17", guardian=True)["guardian"])

    def test_protocol_duration_and_standard_attempt_count(self):
        with self.assertRaises(domain.ValidationError):
            self.store.add_attempt(attempt(conditions={"distance": 3, "width": 1, "surface": "Grass", "duration": 60}))
        with self.assertRaises(domain.ValidationError):
            self.store.add_attempt(attempt("touch", metrics={"attempts": 19, "successes": 18}, conditions={"distance": 3, "width": 1, "surface": "Grass", "duration": 60}))

    def test_invalid_quality_and_missed_cones_are_unmeasurable(self):
        self.store.add_attempt(attempt(quality={"visible": False, "fixed_camera": True, "setup_valid": True}))
        self.store.add_attempt(attempt("slalom", metrics={"seconds": 12, "missed": 1}, conditions={"distance": 2, "width": 1, "surface": "Turf", "duration": 60}))
        self.assertTrue(all(a["status"] == "UNMEASURABLE" and a["value"] is None for a in self.store.attempts()))
        self.assertTrue(all(p["latest"] is None for p in domain.passport(self.store.attempts())))

    def test_comparison_does_not_mix_conditions(self):
        self.store.add_attempt(attempt(metrics={"attempts": 20, "successes": 10, "weak_foot": 4}))
        changed = {"distance": 5, "width": 1, "surface": "Grass", "duration": 30}
        self.store.add_attempt(attempt(metrics={"attempts": 20, "successes": 18, "weak_foot": 5}, conditions=changed))
        p = next(p for p in domain.passport(self.store.attempts()) if p["protocol"] == "wall")
        self.assertIsNone(p["delta"])
        self.store.add_attempt(attempt(metrics={"attempts": 20, "successes": 20, "weak_foot": 8}, conditions=changed))
        p = next(p for p in domain.passport(self.store.attempts()) if p["protocol"] == "wall")
        self.assertEqual(p["delta"], 10)
        self.assertEqual(p["comparable_count"], 2)

    def test_review_preserves_original_and_logs_each_correction(self):
        saved = self.store.add_attempt(attempt())
        for successes in [18, 19]:
            self.store.review({"attempt_id": saved["id"], "coach": "Reviewer", "note": "Count verified at the clip.",
                               "metrics": {"attempts": 24, "successes": successes, "weak_foot": 6}})
        assessed = self.store.attempts()[0]
        self.assertEqual(assessed["original_metrics"]["successes"], 20)
        self.assertEqual(assessed["metrics"]["successes"], 19)
        self.assertEqual(self.store.events("attempt")[0]["metrics"]["successes"], 20)
        self.assertEqual(len(self.store.events("review")), 2)
        self.assertIn("Coach-reviewed", assessed["confidence"])

    def test_review_cannot_turn_bad_setup_into_measurement(self):
        a = self.store.add_attempt(attempt(quality={"visible": True, "fixed_camera": False, "setup_valid": True}))
        self.store.review({"attempt_id": a["id"], "coach": "Reviewer", "note": "Camera moved.", "metrics": None})
        self.assertIsNone(self.store.attempts()[0]["value"])

    def test_equipment_filter_and_goal_priority(self):
        p = player(equipment=["ball"])
        result = domain.plan(p, [], [], "Ready")
        self.assertTrue(result["assignments"])
        self.assertTrue(all(a["protocol"] == "juggling" for a in result["assignments"]))
        result = domain.plan(player(), [], [], "Ready")
        self.assertEqual(result["assignments"][0]["protocol"], "wall")
        self.assertLessEqual(result["minutes"], 20)

    def test_readiness_and_recent_effort_reduce_load(self):
        ready = domain.plan(player(), [], [], "Ready")
        tired = domain.plan(player(), [], [], "Tired")
        hard = domain.plan(player(), [], [{"protocol": "wall", "effort": 5, "completed": True}], "Ready")
        self.assertLess(tired["minutes"], ready["minutes"])
        self.assertEqual(tired["minutes"], hard["minutes"])
        self.assertEqual(domain.plan(player(), [], [], "Rest")["assignments"], [])

    def test_progression_requires_reviewed_retests_and_comfortable_sessions(self):
        for i in range(2):
            a = self.store.add_attempt(attempt(metrics={"attempts": 20, "successes": 18, "weak_foot": 10}))
            self.store.review({"attempt_id": a["id"], "coach": "Reviewer", "note": "Verified."})
        completions = [{"protocol": "wall", "effort": 2, "completed": True}] * 2
        result = domain.plan(player(), self.store.attempts(), completions, "Ready")
        d = next(d for d in DRILLS if d["id"] == result["assignments"][0]["drill_id"])
        self.assertEqual(d["difficulty"], 2)
        result = domain.plan(player(), self.store.attempts(), [], "Ready")
        d = next(d for d in DRILLS if d["id"] == result["assignments"][0]["drill_id"])
        self.assertEqual(d["difficulty"], 1)

    def test_feedback_cannot_be_duplicated(self):
        p = self.store.generate_plan({"readiness": "Ready"})
        data = {"assignment_id": p["assignments"][0]["id"], "completed": True, "effort": 2}
        self.store.complete(data)
        with self.assertRaises(domain.ValidationError):
            self.store.complete(data)

    def test_explicit_practice_focus_respects_equipment_rest_budget_and_standard_scores(self):
        from football.knowledge import DRILL
        for identity in ("touch-directional", "wall-weaker-foot"):
            plan = self.store.generate_plan({"readiness": "Ready", "focus_drill_id": identity})
            self.assertEqual(plan["assignments"][0]["drill_id"], identity)
            self.assertEqual(plan["focus_drill_id"], identity)
            self.assertEqual(DRILL[identity]["version"], "practice-1")
            self.store.complete({"assignment_id": plan["assignments"][0]["id"], "completed": True, "effort": 2, "note": "Left gate: 3/5; right gate: 4/5"})
            self.assertEqual(self.store.attempts(), [])
        tired = self.store.generate_plan({"readiness": "Tired", "focus_drill_id": "touch-directional"})
        self.assertLessEqual(tired["minutes"], self.store.player()["minutes"]*.6)
        rest = self.store.generate_plan({"readiness": "Rest", "focus_drill_id": "touch-directional"})
        self.assertEqual(rest["assignments"], [])
        for identity in ("not-a-drill", "wall-5", [], True):
            with self.assertRaises(domain.ValidationError):
                self.store.generate_plan({"readiness": "Ready", "focus_drill_id": identity})
        limited = {**self.store.player(), "equipment": ["ball"]}
        with self.assertRaises(domain.ValidationError):
            domain.plan(limited, [], [], "Ready", "touch-directional")
        automatic = domain.plan(self.store.player(), [], [], "Ready")
        self.assertFalse(any(DRILL[a["drill_id"]].get("practice_only") for a in automatic["assignments"]))

    def test_persistence_and_erasure(self):
        self.store.add_attempt(attempt())
        self.assertEqual(len(Store(self.tmp.name).attempts()), 1)
        self.store.erase()
        self.assertIsNone(self.store.get("profile"))
        self.assertEqual(self.store.events(), [])

    def test_knowledge_review_is_versioned_and_requires_confirmation(self):
        with self.assertRaises(domain.ValidationError):
            self.store.approve_drill({"drill_id": "wall-1", "reviewer": "Coach", "note": "Reviewed."})
        result = self.store.approve_drill({"drill_id": "wall-1", "reviewer": "Coach", "note": "Reviewed.", "qualified": True})
        self.assertEqual(result["version"], "starter-1")


if __name__ == "__main__":
    unittest.main()
