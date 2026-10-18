from pathlib import Path
import tempfile
import unittest

from sdlc.bootstrap import bootstrap


class SdlcTests(unittest.TestCase):
    def test_runtime_is_separate_reproducible_and_does_not_copy_private_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / "source", root / "runtime"
            for folder in ("src/stages", "public", "test", "data"):
                (source / folder).mkdir(parents=True)
            (source / "data/private.json").write_text("private")
            for name in ("package.json", "package-lock.json", "README.md"):
                (source / name).write_text("{}")
            runner = "const url = `http://localhost:${port}`; if (res.status < 500) return true;"
            (source / "src/appRunner.js").write_text(runner)
            (source / "src/stages/build.js").write_text("const prefixes = ['node', 'npm', 'npx'];")
            bootstrap(source, target)
            self.assertEqual((source / "src/appRunner.js").read_text(), runner)
            self.assertFalse((target / "data").exists())
            self.assertIn("127.0.0.1", (target / "src/appRunner.js").read_text())
            self.assertIn("res.status >= 200 && res.status < 300", (target / "src/appRunner.js").read_text())
            self.assertIn("'python'", (target / "src/stages/build.js").read_text())
            self.assertTrue((target / "source-provenance.json").exists())
            with self.assertRaises(ValueError):
                bootstrap(source, target)
            with self.assertRaises(ValueError):
                bootstrap(source, source / "nested")

    def test_unknown_upstream_is_refused_before_copying(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "source", Path(temp) / "runtime"
            source.mkdir()
            with self.assertRaises(ValueError):
                bootstrap(source, target)
            self.assertFalse(target.exists())
