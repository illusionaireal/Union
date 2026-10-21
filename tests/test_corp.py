import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_union.console import Console
from ai_union.corp import REPO, REQUEST_ID, company_engine, inspect_company, prepare
from ai_union.engine import Rejected
from ai_union.model_api import bind_connection, configure_connection
from ai_union.service import serve


class CorpTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "company"
        self.profile = json.loads((REPO / "examples/ai-union-corp.json").read_text())

    def create(self):
        result = prepare(self.root, self.profile, "test adopter")
        self.assertEqual(result["status"], "succeeded", result)
        return company_engine(self.root)

    def test_preparation_is_idempotent_and_does_not_create_members_or_calls(self):
        engine = self.create()
        result = prepare(self.root, self.profile, "test adopter")
        self.assertEqual(result["organization_id"], engine.state()["id"])
        self.assertEqual(engine.runs(), [])
        self.assertEqual(engine.state()["members"], {})
        self.assertIn("AI-UNION", engine.state()["goal"])
        self.assertEqual(engine.state()["resources"]["max_calls"], 32)

    def test_changed_creation_does_not_overwrite_adopted_profile(self):
        engine = self.create()
        changed = copy.deepcopy(self.profile)
        changed["goal"] = "another goal"
        with self.assertRaises(Rejected):
            prepare(self.root, changed, "test adopter")
        self.assertEqual(engine.state()["goal"], self.profile["goal"])

    def test_status_can_read_while_console_runs_and_never_probes_provider(self):
        engine = self.create()
        app = Console(self.root, fixture=None)
        self.addCleanup(app.close)
        with patch("ai_union.model_api.APIExecutor.chat", side_effect=AssertionError("must not call")):
            result = inspect_company(self.root)
        self.assertFalse(result["can_attempt_bootstrap"])
        self.assertEqual(result["source"], "not_run")
        self.assertIn("model_connection", [b["code"] for b in result["bootstrap_blockers"]])
        self.assertFalse(result["autonomous_operation_verified"])
        self.assertEqual(engine.runs(), [])
        self.assertEqual(app.session_info(app.new_session("board"))["executors"], ["api"])

    def test_unknown_creation_is_not_automatically_recreated(self):
        self.create()
        app = Console(self.root, fixture=None)
        with app.catalog() as cx:
            row = cx.execute("SELECT receipt FROM creations WHERE id=?", (REQUEST_ID,)).fetchone()
            receipt = json.loads(row[0]) | {"status": "unknown"}
            cx.execute("UPDATE creations SET receipt=? WHERE id=?", (json.dumps(receipt), REQUEST_ID))
        app.close()
        with self.assertRaises(Rejected):
            company_engine(self.root)
        self.assertEqual(prepare(self.root, self.profile, "test adopter")["status"], "unknown")

    def test_saved_connection_is_not_tool_verification_and_never_exposes_key(self):
        engine = self.create()
        key = (engine.root / "board.key").read_text()
        config = json.loads((REPO / "examples/model-api.json").read_text())
        configure_connection(engine, key, "primary", config, "test", "private-test-key")
        bind_connection(engine, key, "primary", "test")
        result = inspect_company(self.root)
        self.assertFalse(result["can_attempt_bootstrap"])
        self.assertIn("paused", [b["code"] for b in result["bootstrap_blockers"]])
        engine.set_paused(False)  # Explicit host start, matching Console's start command.
        result = inspect_company(self.root)
        self.assertTrue(result["can_attempt_bootstrap"], result)
        self.assertFalse(result["tool_roundtrip_verified"])
        self.assertNotIn("private-test-key", json.dumps(result))
        self.assertEqual(engine.runs(), [])

    def test_tool_probe_evidence_is_bound_to_real_source_and_connection_revision(self):
        engine = self.create()
        key = (engine.root / "board.key").read_text()
        config = json.loads((REPO / "examples/model-api.json").read_text())
        configure_connection(engine, key, "primary", config, "test", "private-test-key")
        bind_connection(engine, key, "primary", "test")
        metadata = {"connection_id": "primary", "connection_revision": 1, "transport_source": "local_test", "protocol": "test-protocol", "requested_model": "test-model"}
        package = engine.begin_connection_test(metadata)
        engine.finish_connection_test(package["run_id"], {"stage": "tool_roundtrip"}, {})
        self.assertFalse(inspect_company(self.root)["tool_roundtrip_verified"])
        package = engine.begin_connection_test(metadata | {"transport_source": "provider_api"})
        engine.finish_connection_test(package["run_id"], {"stage": "tool_roundtrip"}, {})
        self.assertFalse(inspect_company(self.root)["tool_roundtrip_verified"], "without transport archive a DB label is insufficient")
        folder = engine.root / "executions" / package["run_id"]
        folder.mkdir(parents=True)
        (folder / "result.json").write_text("{}")
        (folder / "receipt.json").write_text(json.dumps(metadata | {"transport_source": "provider_api", "response_id": "synthetic-unit-test-receipt"}))
        self.assertTrue(inspect_company(self.root)["tool_roundtrip_verified"])
        configure_connection(engine, key, "primary", config | {"max_output_tokens": 2000}, "new revision")
        self.assertFalse(inspect_company(self.root)["tool_roundtrip_verified"])

    def test_service_requires_explicit_cost_acceptance_before_watch(self):
        engine = self.create()
        with patch("ai_union.service.watch") as watch:
            with self.assertRaises(Rejected):
                serve(engine, max_steps=1, max_seconds=1, allow_unknown_cost=False)
            watch.assert_not_called()
        self.assertEqual(engine.runs(), [])

    def test_service_stops_at_exact_budget_boundary_without_budget_reset(self):
        engine = self.create()
        with patch("ai_union.service.watch", return_value=[{"action": "decision"}]):
            result = serve(engine, max_steps=1, max_seconds=1, allow_unknown_cost=True)
            self.assertTrue(result["restart_allowed"])
            # Reserve and fail a known local attempt, without any provider call.
            engine.set_paused(False)
            package = engine.begin_decision("fixture")
            engine.fail_run(package["run_id"], "fixture-only test")
            key = (engine.root / "board.key").read_text()
            engine.configure_resources(key, {"max_calls": 1, "timeout_seconds": 30}, "test exact limit")
            result = serve(engine, max_steps=1, max_seconds=1, allow_unknown_cost=True)
            self.assertFalse(result["restart_allowed"])
            self.assertEqual(result["budget"]["calls_reserved"], 1)

    def test_service_unknown_execution_is_never_replayed(self):
        engine = self.create()
        engine.set_paused(False)
        package = engine.begin_decision("api")
        with patch("ai_union.service.HarnessExecutor") as harness, patch("ai_union.service.resolve_connection", return_value={}):
            result = serve(engine, max_steps=2, max_seconds=1, allow_unknown_cost=True)
        harness.return_value.execute.assert_not_called()
        self.assertFalse(result["restart_allowed"])
        self.assertEqual(engine.runs()[0]["id"], package["run_id"])
        self.assertEqual(engine.runs()[0]["status"], "unknown")
        self.assertEqual(len(engine.runs()), 1)

    def test_service_pause_and_failure_are_terminal(self):
        engine = self.create()
        for action in ("paused", "blocked"):
            with patch("ai_union.service.watch", return_value=[{"action": action}]):
                result = serve(engine, max_steps=1, max_seconds=1, allow_unknown_cost=True)
                self.assertFalse(result["restart_allowed"])


if __name__ == "__main__":
    unittest.main()
