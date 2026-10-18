import json
import tempfile
import unittest
from unittest.mock import patch

from football import ai, domain
from football.store import Store
from test_domain import player, attempt


class AITests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(tmp.name)
        self.store.set("profile", player())
        self.store.add_attempt(attempt())

    @patch("football.ai.ollama", side_effect=AssertionError("Offline must not use network"))
    def test_offline_coach_works_without_network(self, mock):
        result = ai.answer(self.store, {"question": "How can I improve passing?", "provider": "offline"})
        self.assertTrue(result["drill_ids"])
        self.assertEqual(result["provider"], "Offline rules")
        retest = ai.answer(self.store, {"question": "How should I retest?", "provider": "offline"})
        self.assertIn("matching valid attempts", retest["explanation"])
        mock.assert_not_called()

    def test_cloud_models_and_unconfirmed_local_mode_rejected(self):
        for data in [{"model": "gemma4:cloud", "local_only_confirmed": True}, {"model": "gemma4:e4b", "local_only_confirmed": False}]:
            with self.assertRaises(domain.ValidationError):
                ai.answer(self.store, {"question": "Help", "provider": "ollama", **data})

    @patch("football.ai.ollama")
    def test_local_adapter_sends_minimal_evidence_and_validates_drills(self, mock):
        mock.side_effect = [{}, {"message": {"content": json.dumps({"explanation": "Try a steady rhythm.", "drill_ids": ["wall-1"]})}, "prompt_eval_count": 50, "eval_count": 15}]
        result = ai.answer(self.store, {"question": "Passing", "provider": "ollama", "model": "gemma4:e4b", "local_only_confirmed": True})
        sent = mock.call_args.args[1]
        self.assertNotIn("Test Player", json.dumps(sent))
        self.assertNotIn("media_id", json.dumps(sent))
        self.assertFalse(sent["stream"])
        self.assertEqual(result["tokens"]["output"], 15)
        self.assertEqual(len(self.store.events("chat")), 1)

    @patch("football.ai.ollama")
    def test_cloud_backed_alias_rejected_before_prompt(self, mock):
        mock.return_value = {"remote_model": "gemma4:cloud"}
        with self.assertRaises(domain.ValidationError):
            ai.answer(self.store, {"question": "Help", "provider": "ollama", "model": "gemma4:e4b", "local_only_confirmed": True})
        self.assertEqual(mock.call_count, 1)

    @patch("football.ai.ollama")
    def test_invalid_generated_guidance_and_runtime_failure(self, mock):
        for response in [OSError("offline"), {}, {"message": {"content": "not json"}}, {"message": {"content": "[]"}}, {"message": {"content": '{"explanation":"Invented","drill_ids":["fake"]}'}}]:
            mock.side_effect = [{}, response]
            with self.assertRaises(domain.ValidationError):
                ai.answer(self.store, {"question": "Help", "provider": "ollama", "model": "gemma4:e4b", "local_only_confirmed": True})
        self.assertEqual(self.store.events("chat"), [])


if __name__ == "__main__":
    unittest.main()
