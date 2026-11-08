"""Deployment watch must preserve work across failed reads and concurrent runs."""
import importlib.util
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import tempfile
import unittest
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch

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

    def collection_fixture(self, failed_source=None):
        env = self.root / "board.env"
        env.write_text("UNION_KANBAN_URL=https://board.example.invalid\nUNION_KANBAN_KEY=fixture-secret\n")
        config = {"env_file": str(env), "github_repository": "example/union", "ssh_port": 222,
                  "ssh_target": "fixture-host", "health_command": "fixture-health"}
        calls = []

        def request(request, **kwargs):
            url = request.full_url
            source = "board" if "board.example.invalid" in url else "github"
            calls.append(source)
            if source == failed_source:
                raise TimeoutError("fixture-secret must not enter diagnostics")
            if "/messages?" in url:
                result = {"latest_id": 7, "messages": []}
            elif source == "board":
                result = {"revision": 7, "tasks": []}
            elif "/pulls?" in url:
                result = []
            else:
                result = {"workflow_runs": []}
            return io.StringIO(json.dumps(result))

        def command(args, **kwargs):
            if args[0] == "git":
                return SimpleNamespace(returncode=0, stdout="password=fixture-secret\n")
            calls.append("nas")
            if failed_source == "nas":
                raise TimeoutError("fixture-secret must not enter diagnostics")
            return SimpleNamespace(returncode=0, stdout="running false 0")

        self.enterContext(patch.object(watch.urllib.request, "build_opener",
                                       return_value=SimpleNamespace(open=request)))
        self.enterContext(patch.object(watch, "run_command", side_effect=command))
        return config, calls

    def test_board_failure_still_records_github_and_nas_without_advancing_cursor(self):
        first = watch.poll(self.root, lambda: {"revision": 2})
        config, calls = self.collection_fixture("board")
        failed = watch.poll(self.root, lambda: watch.collect(config))
        self.assertIn("github", calls)
        self.assertIn("nas", calls)
        self.assertEqual(failed["status"], "failed")
        for key in ("snapshot", "last_success", "fingerprint", "pending"):
            self.assertEqual(failed[key], first[key])
        self.assertEqual(failed["observations"]["board"]["error"], "TimeoutError")
        self.assertEqual(failed["observations"]["nas"]["data"]["nas"]["health"], "running false 0")
        self.assertEqual(failed["observations"]["github"]["status"], "ok")
        self.assertNotIn("fixture-secret", (self.root / "status.json").read_text())

    def test_github_failure_keeps_board_and_nas_observations(self):
        config, calls = self.collection_fixture("github")
        failed = watch.poll(self.root, lambda: watch.collect(config))
        self.assertIn("nas", calls)
        self.assertEqual(failed["observations"]["board"]["data"]["board_revision"], 7)
        self.assertEqual(failed["observations"]["nas"]["status"], "ok")
        self.assertNotIn("last_success", failed)

    def test_recovery_clears_partial_diagnostics_and_unchanged_snapshot_is_stable(self):
        config, _ = self.collection_fixture("nas")
        failed = watch.poll(self.root, lambda: watch.collect(config))
        self.assertEqual(failed["observations"]["nas"]["error"], "TimeoutError")
        config, _ = self.collection_fixture()
        recovered = watch.poll(self.root, lambda: watch.collect(config))
        self.assertEqual(recovered["status"], "ok")
        self.assertNotIn("observations", recovered)
        watch.acknowledge(self.root, recovered["fingerprint"])
        unchanged = watch.poll(self.root, lambda: watch.collect(config))
        self.assertFalse(unchanged["pending"])

    def test_no_proxy_configuration_allows_actual_http_reads(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                value = {"latest_id": 1, "messages": []} if "messages" in self.path else {"revision": 1, "tasks": []}
                body = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = self.enterContext(HTTPServer(("127.0.0.1", 0), Handler))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        env = self.root / "loopback.env"
        env.write_text(f"UNION_KANBAN_URL=http://127.0.0.1:{server.server_port}\nUNION_KANBAN_KEY=fixture\n")
        # Other probes deliberately cannot start; this test only performs loopback HTTP.
        with patch.object(watch, "run_command", side_effect=OSError("unavailable fixture")), \
                patch.object(watch.urllib.request, "proxy_bypass", return_value=False):
            state = watch.poll(self.root, lambda: watch.collect({"env_file": str(env)}))
        self.assertEqual(state["observations"]["board"]["status"], "ok")
        self.assertEqual(state["observations"]["board"]["data"]["board_revision"], 1)

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

    def agent_config(self):
        prompt = self.root / "prompt.txt"
        prompt.write_text("Handle authorized deployment work; inspect original outcomes before retrying.")
        return {"state_dir": str(self.root), "agent_enabled": True, "codex": "codex",
                "repository": str(self.root), "prompt_file": str(prompt)}

    def successful_exec(self, calls):
        def run(args, **kwargs):
            calls.append((args, kwargs))
            if "login" in args:
                return SimpleNamespace(returncode=1)
            Path(args[args.index("-o") + 1]).write_text(json.dumps({"status": "handled", "summary": "checked"}))
            return SimpleNamespace(returncode=0)
        return run

    def test_configured_provider_runs_without_a_separate_cli_login(self):
        state = watch.poll(self.root, lambda: {"revision": 1})
        calls = []
        status = watch.run_agent(self.agent_config(), state, run=self.successful_exec(calls))
        self.assertEqual(status, "handled")
        self.assertEqual(len(calls), 1)
        self.assertIn("exec", calls[0][0])
        self.assertFalse(watch.read_json(self.root / "status.json")["pending"])

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
        self.assertEqual(len(calls), 1)
        self.assertTrue(watch.read_json(self.root / "status.json")["pending"])

    def partial(self, revision=1, all_failed=False):
        def read():
            raise watch.PartialCollectionError({
                "board": {"status": "failed", "at": watch.now(), "error": "TimeoutError"},
                "github": ({"status": "failed", "at": watch.now(), "error": "TimeoutError"} if all_failed else
                           {"status": "ok", "at": watch.now(), "data": {"revision": revision}}),
            })
        return watch.poll(self.root, read)

    def test_partial_success_runs_once_without_consuming_complete_pending(self):
        complete = watch.poll(self.root, lambda: {"revision": 7})
        calls = []
        config = self.agent_config()
        self.assertEqual(watch.run_agent(config, self.partial(), run=self.successful_exec(calls)), "handled")
        actual = watch.read_json(self.root / "status.json")
        for key in ("last_success", "fingerprint", "pending", "snapshot"):
            self.assertEqual(actual[key], complete[key])
        self.assertIn("partial", calls[0][1]["input"])
        self.assertEqual(watch.run_agent(config, self.partial(), run=self.successful_exec(calls)), "idle")
        self.assertEqual(len(calls), 1, "timestamp-only changes do not start another agent")
        self.assertEqual(watch.run_agent(config, self.partial(2), run=self.successful_exec(calls)), "handled")
        self.assertEqual(len(calls), 2)

    def test_partial_acknowledgment_cannot_consume_a_newer_partial_observation(self):
        config = self.agent_config()
        calls = []
        execute = self.successful_exec(calls)

        def newer_during_execution(args, **kwargs):
            self.partial(2)
            return execute(args, **kwargs)

        self.assertEqual(watch.run_agent(config, self.partial(1), run=newer_during_execution), "handled")
        self.assertEqual(watch.run_agent(config, self.partial(2), run=execute), "handled")
        self.assertEqual(len(calls), 2)

    def test_all_failed_or_stale_observations_do_not_start_an_agent(self):
        config = self.agent_config()
        calls = []
        run = self.successful_exec(calls)
        self.assertEqual(watch.run_agent(config, self.partial(all_failed=True), run=run), "idle")
        self.partial()

        def fail():
            raise RuntimeError("collection could not start")

        stale = watch.poll(self.root, fail)
        self.assertEqual(watch.run_agent(config, stale, run=run), "idle")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
