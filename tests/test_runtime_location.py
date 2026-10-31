"""Deployment descriptions and actual host evidence are separate fixture facts."""
import json
import tempfile
import unittest
from pathlib import Path

from ai_union.activity import activity
from ai_union.engine import Engine
from ai_union.observation import snapshot
from ai_union.runner import exclusive
from tests.support import init, organization


class RuntimeLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(Path(self.temp.name) / "org")
        organization(self.e)

    def persisted(self):
        with self.e.read_transaction() as cx:
            tables = [tuple(r) for r in cx.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
        return self.e.state(), self.e.events(), self.e.runs(), self.e.paused(), tables

    def observe(self, liveness="unknown", active=None, dispatch="enabled"):
        before = self.persisted()
        result = None
        for reader in (self.e, Engine(self.e.root), self.e):
            result = snapshot(reader)
            runtime = result["runtime"]
            self.assertEqual(runtime, {"runtime_id": None, "name": "部署位置未登记", "mode": "unregistered",
                "instance_id": None, "observed_at": None, "liveness": liveness,
                "dispatch_state": dispatch, "active_run_id": active, "capabilities": []})
            self.assertEqual(result["budget"]["calls_reserved"], len(before[2]))
            self.assertNotIn(str(self.e.root), json.dumps(result))
            self.assertNotIn('"pid"', json.dumps(result))
        self.assertEqual(before, self.persisted())
        return result

    def test_legacy_unregistered_reads_do_not_create_runtime_registration(self):
        view = self.observe()
        self.assertEqual(view["member_execution"][0]["work_state"], "ready")
        self.assertEqual(len(view["organization"]["members"]), 2)
        self.e.set_paused(True)
        self.observe(dispatch="paused")

    def test_confirmed_work_and_loss_of_activity_do_not_infer_deployment(self):
        with exclusive(self.e), activity(self.e):
            self.observe(liveness="confirmed")  # Host alive, but no active run yet.
            package = self.e.begin_work("w1", "fixture")
            view = self.observe(liveness="confirmed", active=package["run_id"])
            member = next(m for m in view["member_execution"] if m["member_id"] == "m1")
            self.assertEqual(member["work_state"], "executing")
            self.e.set_paused(True)
            self.observe(liveness="confirmed", active=package["run_id"], dispatch="pause_requested")
        view = self.observe(dispatch="pause_requested")
        self.assertEqual(view["runs"][0]["status"], "running")
        self.assertEqual(view["runs"][0]["display_status"], "unconfirmed")
        member = next(m for m in view["member_execution"] if m["member_id"] == "m1")
        self.assertEqual((member["work_state"], member["reason_codes"]), ("blocked", ["activity_unconfirmed"]))

    def test_new_host_activity_does_not_confirm_a_previous_owners_run(self):
        self.e.begin_work("w1", "fixture")
        with exclusive(self.e), activity(self.e):
            view = self.observe(liveness="confirmed")
            self.assertFalse(view["runs"][0]["host_confirmed"])
            self.assertEqual(view["runs"][0]["display_status"], "unconfirmed")

    def test_unknown_dispatch_is_not_erased_by_unregistered_description(self):
        package = self.e.begin_work("w1", "fixture")
        self.e.fail_run(package["run_id"], "Fixture unknown result", unknown=True)
        for paused in (False, True):
            self.e.set_paused(paused)
            view = self.observe(dispatch="needs_review")
            self.assertEqual(view["runs"][0]["status"], "unknown")
            member = next(m for m in view["member_execution"] if m["member_id"] == "m1")
            self.assertEqual(member["work_state"], "blocked")
            self.assertIn("run_requires_reconciliation", member["reason_codes"])
