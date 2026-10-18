from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.normalize_video import normalize


class NormalizationTests(unittest.TestCase):
    def test_existing_paths_are_never_overwritten_and_failed_encodes_are_cleaned_up(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input.webm", Path(directory) / "copy.mp4"
            source.write_bytes(b"original")
            with self.assertRaises(ValueError):
                normalize(source, source)
            output.write_bytes(b"keep")
            with self.assertRaises(ValueError):
                normalize(source, output)
            output.unlink()
            with patch("tools.normalize_video.subprocess.Popen") as popen:
                popen.return_value.wait.return_value = 1
                with self.assertRaises(RuntimeError):
                    normalize(source, output)
            self.assertEqual(source.read_bytes(), b"original")
            self.assertEqual(list(Path(directory).iterdir()), [source])

    def test_competing_output_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input.webm", Path(directory) / "copy.mp4"
            source.write_bytes(b"original")
            def complete():
                output.write_bytes(b"other writer")
                return 0
            with patch("tools.normalize_video.subprocess.Popen") as popen:
                popen.return_value.wait.side_effect = complete
                with self.assertRaises(FileExistsError):
                    normalize(source, output)
            self.assertEqual(output.read_bytes(), b"other writer")
            self.assertEqual(len(list(Path(directory).iterdir())), 2)
