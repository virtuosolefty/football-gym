import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_corpus import audit, CONDITIONS


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "review.md").write_text("Synthetic test fixture, not real review evidence.")
        self.manifest = {"format": "football-corpus-1", "clips": []}

    def clip(self, name, split):
        labels = {"format": "football-evaluation-1", "clip": {"id": name, "sha256": hashlib.sha256(name.encode()).hexdigest(),
                  "width": 640, "height": 360, "start": 0, "end": 30},
                  "annotator": {"id": "test-coach", "role": "coach", "independent": True},
                  "conditions": list(CONDITIONS), "contacts_reviewed": True, "contacts": [],
                  "frames": [{"time": i/10, "status": "visible", "x": .5, "y": .5, "radius": 10} for i in range(300)]}
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(labels), encoding="utf-8")
        entry = {"id": name, "labels": path.name, "split": split, "source_id": name, "player_ids": [name], "alignment_reviewed": True,
                 "blind_review": {"reviewer": "test-reviewer", "record": "review.md", "labels_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
        self.manifest["clips"].append(entry)
        return entry, labels, path

    def test_empty_and_diagnostic_only_corpora_are_not_ready(self):
        self.assertFalse(audit(self.manifest, self.root)["ready_for_calibration_and_validation"])
        entry, labels, path = self.clip("public", "diagnostic")
        labels["annotator"]["independent"] = False
        path.write_text(json.dumps(labels))
        result = audit(self.manifest, self.root)
        self.assertFalse(result["clips"][0]["eligible"])
        self.assertEqual(result["coverage"]["calibration"]["night"], 0)

    def test_complete_disjoint_corpus_and_source_player_hash_leakage(self):
        for split in ("calibration", "held-out"):
            for i in range(3):
                self.clip(f"{split}-{i}", split)
        self.assertTrue(audit(self.manifest, self.root)["ready_for_calibration_and_validation"])
        self.manifest["clips"][-1]["player_ids"] = ["calibration-0"]
        self.manifest["clips"][-1]["source_id"] = "calibration-0"
        result = audit(self.manifest, self.root)
        self.assertFalse(result["ready_for_calibration_and_validation"])
        self.assertTrue(any("player_id" in s for s in result["blockers"]))
        self.assertTrue(any("source_id" in s for s in result["blockers"]))
        last = self.root / "held-out-2.json"
        labels = json.loads(last.read_text())
        labels["clip"]["sha256"] = hashlib.sha256(b"calibration-0").hexdigest()
        last.write_text(json.dumps(labels))
        self.assertTrue(any("sha256" in s for s in audit(self.manifest, self.root)["blockers"]))

    def test_partial_short_changed_labels_and_missing_review_are_ineligible(self):
        entry, labels, path = self.clip("partial", "calibration")
        labels["clip"]["end"] = 1
        labels["frames"] = labels["frames"][:5]
        labels["contacts_reviewed"] = False
        path.write_text(json.dumps(labels))
        result = audit(self.manifest, self.root)
        issues = result["clips"][0]["issues"]
        for phrase in ("hash", "Incomplete", "shorter", "Contacts"):
            self.assertTrue(any(phrase in s for s in issues), issues)
        entry["blind_review"] = {}
        self.assertTrue(any("blind" in s for s in audit(self.manifest, self.root)["clips"][0]["issues"]))

    def test_duplicate_ids_and_evidence_path_escape_are_rejected(self):
        entry, _, _ = self.clip("same", "diagnostic")
        self.manifest["clips"].append(entry)
        with self.assertRaises(ValueError):
            audit(self.manifest, self.root)
        self.manifest["clips"].pop()
        entry["labels"] = "../outside.json"
        with self.assertRaises(ValueError):
            audit(self.manifest, self.root)
