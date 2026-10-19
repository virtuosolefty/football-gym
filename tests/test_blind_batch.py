import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.prepare_blind_batch import prepare


class BlindBatchTests(unittest.TestCase):
    def test_tasks_are_unlabelled_bound_to_unchanged_video_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "source.mp4"
            video.write_bytes(b"test-video")
            case = {"file": "source.mp4", "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "start": 1, "end": 2,
                    "collection": "test", "source": "fixture", "license": "test", "focus": "secret predicted contacts", "seed": {"x": .5}}
            output = root / "batch"
            rows = prepare([case], root, output)
            task = json.loads((output / "annotator/review-001.task.json").read_text())
            self.assertEqual(set(task), {"format", "clip", "conditions"})
            self.assertNotIn("secret", str(task))
            self.assertEqual((output / "annotator/review-001.mp4").read_bytes(), video.read_bytes())
            self.assertFalse(rows[0]["independent_labels_received"])
            with self.assertRaises(ValueError):
                prepare([case], root, output)
            with self.assertRaises(ValueError):
                prepare([{**case, "sha256": "0"*64}], root, root / "bad")
            self.assertFalse((root / "bad").exists())
            for changes in ({"file": "../escape.mp4"}, {"start": True}, {"end": float("nan")}):
                with self.assertRaises(ValueError):
                    prepare([{**case, **changes}], root, root / "invalid")
