"""Deployment watch must preserve work across failed reads and concurrent runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

MODULE = Path(__file__).resolve().parents[1] / "ops/automation/ops_watch.py"
spec = importlib.util.spec_from_file_location("ops_watch", MODULE)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class OpsWatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_unchanged_snapshot_after_ack_needs_no_agent(self):
        first = watch.poll(self.root, lambda: {"revision": 1})
        self.assertTrue(first["pending"])
        watch.acknowledge(self.root, first["fingerprint"])
        second = watch.poll(self.root, lambda: {"revision": 1})
        self.assertFalse(second["pending"])
        self.assertEqual(second["fingerprint"], first["fingerprint"])

    def test_failed_read_keeps_success_and_unhandled_signal(self):
        first = watch.poll(self.root, lambda: {"revision": 2})
        def fail():
            raise RuntimeError("secret must not enter diagnostics")
        failed = watch.poll(self.root, fail)
        self.assertEqual(failed["last_success"], first["last_success"])
        self.assertEqual(failed["fingerprint"], first["fingerprint"])
        self.assertTrue(failed["pending"])
        self.assertEqual(failed["error"], "RuntimeError")
        self.assertNotIn("secret", (self.root / "status.json").read_text())

    def test_ack_of_old_snapshot_does_not_consume_new_input(self):
        first = watch.poll(self.root, lambda: {"message": 1})
        newer = watch.poll(self.root, lambda: {"message": 2})
        watch.acknowledge(self.root, first["fingerprint"])
        self.assertTrue(watch.poll(self.root, lambda: {"message": 2})["pending"])
        watch.acknowledge(self.root, newer["fingerprint"])
        self.assertFalse(watch.poll(self.root, lambda: {"message": 2})["pending"])

    def test_lock_excludes_second_worker_and_releases_after_failure(self):
        with self.assertRaisesRegex(RuntimeError, "failed worker"):
            with watch.lock(self.root / "agent.lock") as held:
                self.assertTrue(held)
                with watch.lock(self.root / "agent.lock") as second:
                    self.assertFalse(second)
                raise RuntimeError("failed worker")
        with watch.lock(self.root / "agent.lock") as held:
            self.assertTrue(held)

    def test_health_change_queues_new_work(self):
        good = watch.poll(self.root, lambda: {"health": "running"})
        watch.acknowledge(self.root, good["fingerprint"])
        self.assertTrue(watch.poll(self.root, lambda: {"health": "exited"})["pending"])

    def test_missing_login_does_not_clear_pending_work(self):
        state = watch.poll(self.root, lambda: {"revision": 1})
        calls = []
        def logged_out(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=1)
        status = watch.run_agent({"state_dir": str(self.root), "agent_enabled": True,
                                  "codex": "codex"}, state, run=logged_out)
        self.assertEqual(status, "login_required")
        self.assertEqual(calls, [["codex", "login", "status"]])
        self.assertTrue(watch.read_json(self.root / "status.json")["pending"])

    def test_failed_agent_keeps_pending_for_original_result_reconciliation(self):
        state = watch.poll(self.root, lambda: {"revision": 1})
        prompt = self.root / "prompt.txt"
        prompt.write_text("Check original deployment result before retrying.")
        calls = []
        def failed_exec(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0 if "login" in args else 1)
        status = watch.run_agent({"state_dir": str(self.root), "agent_enabled": True,
            "codex": "codex", "repository": str(self.root), "prompt_file": str(prompt)},
            state, run=failed_exec)
        self.assertEqual(status, "follow_up")
        self.assertEqual(len(calls), 2)
        self.assertTrue(watch.read_json(self.root / "status.json")["pending"])


if __name__ == "__main__":
    unittest.main()
