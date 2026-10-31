"""One read-only dispatch description; real scheduling retains its own guards."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_union.activity import activity
from ai_union.engine import Engine
from ai_union.observation import snapshot
from ai_union.runner import exclusive, step
from tests.support import RESOURCES, init, organization


class NoCallExecutor:
    name = "fixture"

    def execute(self, package):
        raise AssertionError("Unknown/paused observations must not dispatch")


class DispatchObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(Path(self.temp.name) / "org")
        organization(self.e)

    def persisted(self):
        with self.e.read_transaction() as cx:
            tables = [tuple(r) for r in cx.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
        return self.e.state(), self.e.events(), self.e.runs(), self.e.paused(), tables

    def observe(self, expected):
        before = self.persisted()
        result = None
        with patch.object(Engine, "recover", side_effect=AssertionError("Reading must not recover")):
            for reader in (self.e, Engine(self.e.root), self.e):
                result = snapshot(reader)
                self.assertEqual(result["dispatch_state"], expected)
                self.assertEqual(result["runtime"]["dispatch_state"], expected)
                self.assertEqual(result["runtime"]["mode"], "unregistered")
                self.assertEqual(result["budget"]["calls_reserved"], len(before[2]))
        self.assertEqual(before, self.persisted())
        return result

    def test_unknown_precedes_pause_intent_without_recovery_or_replay(self):
        package = self.e.begin_work("w1", "fixture")
        self.e.fail_run(package["run_id"], "Fixture unknown", unknown=True)
        for paused in (False, True):
            self.e.set_paused(paused)
            view = self.observe("needs_review")
            self.assertEqual(view["next_step"], "blocked")
            self.assertEqual(view["execution_state"], "unknown")
            before = self.persisted()
            self.assertEqual(step(self.e, NoCallExecutor())["action"], "paused" if paused else "blocked")
            self.assertEqual(before, self.persisted())

    def test_paused_host_without_a_run_does_not_claim_quiescence(self):
        self.e.set_paused(True)
        self.observe("paused")
        with exclusive(self.e), activity(self.e):
            view = self.observe("pause_requested")
            self.assertEqual(view["execution_state"], "idle")
            self.assertIsNone(view["runtime"]["active_run_id"])
            self.assertEqual(view["budget"]["calls_reserved"], 0)
        self.observe("paused")

    def test_persisted_running_keeps_pause_request_after_owner_loss(self):
        with exclusive(self.e), activity(self.e):
            package = self.e.begin_work("w1", "fixture")
            self.e.set_paused(True)
            self.assertEqual(self.observe("pause_requested")["runtime"]["active_run_id"], package["run_id"])
        view = self.observe("pause_requested")
        self.assertEqual(view["execution_state"], "unconfirmed")
        self.assertEqual(view["runs"][0]["status"], "running")
        with exclusive(self.e), activity(self.e):
            view = self.observe("pause_requested")
            self.assertEqual(view["runtime"]["liveness"], "confirmed")
            self.assertIsNone(view["runtime"]["active_run_id"])
            self.assertFalse(view["runs"][0]["host_confirmed"])

    def test_enabled_does_not_promise_work_or_budget_eligibility(self):
        self.observe("enabled")
        with exclusive(self.e), activity(self.e):
            self.observe("enabled")
            package = self.e.begin_work("w1", "fixture")
            self.observe("enabled")
            self.e.fail_run(package["run_id"], "Fixture settled failure")
        self.e.configure_resources("test-key", RESOURCES | {"max_calls": 1}, "Fixture exhausted allowance")
        view = self.observe("enabled")
        self.assertIsNotNone(view["budget"]["blocked_reason"])
        self.assertEqual(view["next_step"], "blocked")
