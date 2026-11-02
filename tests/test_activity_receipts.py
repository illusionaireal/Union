"""Local locks/Engine/Runner with controlled clocks and fixture receipts, not VPS."""
import json
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ai_union.activity as activity_module
from ai_union.engine import Engine, Rejected
from ai_union.locking import held
from ai_union.observation import snapshot
from ai_union.runner import exclusive, run, step
from tests.support import init, organization


class FrozenRenewalEvent(threading.Event):
    def wait(self, timeout=None):
        # Keep the real heartbeat thread asleep until activity's real cleanup.
        return super().wait()


class ActivityReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(Path(self.temp.name) / "org")
        organization(self.e)
        self.old_result = {"status": "delivered", "artifacts": [{"name": "old.txt", "content": "Old fixture receipt"}]}
        self.usage = {"input_tokens": 12, "output_tokens": 4}

    @contextmanager
    def owner(self):
        clock = SimpleNamespace(value=1000.0)
        proxy = SimpleNamespace(Event=FrozenRenewalEvent, Thread=threading.Thread)
        with patch.object(activity_module, "time", SimpleNamespace(time=lambda: clock.value)), \
             patch.object(activity_module, "threading", proxy), exclusive(self.e), activity_module.activity(self.e):
            yield clock

    def persisted(self):
        with self.e.read_transaction() as cx:
            tables = [(r[0], r[1]) for r in cx.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows = [(name, sql, [tuple(r) for r in cx.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]) for name, sql in tables]
        assets = sorted((p.name, p.read_bytes()) for p in (self.e.root / "assets").iterdir() if p.is_file())
        return rows, assets

    def observe(self, package, confirmed):
        before = self.persisted()
        with patch.object(Engine, "recover", side_effect=AssertionError("Observation must not recover")):
            for engine in (self.e, Engine(self.e.root), self.e):
                view = snapshot(engine)
                record = next(r for r in view["runs"] if r["id"] == package["run_id"])
                self.assertEqual(record["status"], "running")
                self.assertEqual(record["host_confirmed"], confirmed)
                self.assertEqual(record["display_status"], "running" if confirmed else "unconfirmed")
                self.assertEqual(view["runtime"]["liveness"], "confirmed" if confirmed else "unknown")
                self.assertEqual(view["runtime"]["active_run_id"], package["run_id"] if confirmed else None)
                self.assertEqual(view["execution_state"], "running" if confirmed else "unconfirmed")
                member = next(m for m in view["member_execution"] if m["member_id"] == "m1")
                self.assertEqual(member["work_state"], "executing" if confirmed else "blocked")
                if not confirmed:
                    self.assertEqual(member["reason_codes"], ["activity_unconfirmed"])
                self.assertEqual(view["dispatch_state"], "pause_requested" if engine.paused() else "enabled")
                self.assertEqual(view["runtime"]["dispatch_state"], view["dispatch_state"])
        self.assertEqual(before, self.persisted())
        return view

    def forbidden(self):
        return SimpleNamespace(name="fixture", execute=Mock(side_effect=AssertionError("Must not dispatch")))

    def interrupted(self):
        with self.owner():
            package = self.e.begin_work("w1", "fixture")
        self.assertTrue(package["host_owner"])
        new = Engine(self.e.root)
        executor = self.forbidden()

        def factory():
            view = snapshot(new)  # Actual runner has acquired its lock and new owner.
            self.assertEqual(view["runtime"]["liveness"], "confirmed")
            self.assertIsNone(view["runtime"]["active_run_id"])
            self.assertFalse(view["runs"][0]["host_confirmed"])
            self.assertNotEqual(new._local.host_owner, package["host_owner"])
            return executor

        result = run(new, factory, 1)  # Real startup recover, then real step.
        self.assertEqual(result[0]["action"], "blocked", result)
        executor.execute.assert_not_called()
        self.assertEqual(new.runs()[0]["status"], "unknown")
        self.assertEqual(new.state()["work"]["w1"]["status"], "needs_review")
        self.assertEqual(new.status()["dispatch_state"], "needs_review")
        self.assertEqual(new.status()["budget"]["calls_reserved"], 1)
        self.assertEqual(new.state()["artifacts"], {})
        return package, new

    def reject_old_receipts(self, package):
        before = self.persisted()
        with self.assertRaises(Rejected):
            self.e.finish_work(package["run_id"], self.old_result, self.usage)
        with self.assertRaises(Rejected):
            self.e.finish_progress(package["run_id"], self.usage)
        self.e.fail_run(package["run_id"], "Late fixture failure must not replace settled state", usage=self.usage)
        self.assertEqual(before, self.persisted())

    def test_direct_ttl_boundary_keeps_original_owner_lock_and_never_dispatches(self):
        with self.owner() as clock:
            package = self.e.begin_work("w1", "fixture")
            path = self.e.root / "runner.activity.json"
            heartbeat = path.read_bytes()
            self.assertEqual(json.loads(heartbeat)["owner"], package["host_owner"])
            self.assertEqual(json.loads(heartbeat)["heartbeat"], 1000)
            for age, confirmed in ((0, True), (5, True), (5.001, False), (-0.001, False)):
                with self.subTest(age=age):
                    clock.value = 1000 + age
                    self.observe(package, confirmed)
                    self.assertTrue(held(self.e.root / "runner.lock"))
                    self.assertEqual(path.read_bytes(), heartbeat)
            clock.value = 1005.001
            executor = self.forbidden()
            factory = Mock(return_value=executor)
            with self.assertRaises(Rejected):
                run(Engine(self.e.root), factory, 1)
            factory.assert_not_called()
            executor.execute.assert_not_called()
            before = self.persisted()
            self.assertEqual(step(self.e, executor)["action"], "blocked")
            self.assertEqual(before, self.persisted())
            self.e.set_paused(True)
            self.observe(package, False)
            self.assertEqual(self.e.status()["budget"]["calls_reserved"], 1)

    def test_expired_heartbeat_does_not_cancel_a_still_valid_original_receipt(self):
        with self.owner() as clock:
            package = self.e.begin_work("w1", "fixture")
            clock.value = 1006
            self.observe(package, False)
            self.e.finish_work(package["run_id"], self.old_result, self.usage)
            view = snapshot(self.e)
            self.assertEqual(view["runs"][0]["status"], "delivered")
            self.assertEqual(view["runs"][0]["usage"], self.usage | {"cost": None, "cost_status": "unknown", "cost_basis":"unknown", "cost_minor":None,"currency":None,"billing_revision":None})
            self.assertEqual(view["runtime"]["liveness"], "unknown")
            self.assertIsNone(view["runtime"]["active_run_id"])
            self.assertEqual(len(self.e.state()["artifacts"]), 1)
            self.assertEqual(view["budget"]["calls_reserved"], 1)

    def test_actual_runner_startup_recovers_unknown_and_rejects_late_old_receipts(self):
        package, _ = self.interrupted()
        self.reject_old_receipts(package)

    def test_reconciled_old_receipt_cannot_complete_the_new_owners_run(self):
        old, new = self.interrupted()
        self.e.reconcile("test-key", old["run_id"], "confirmed_not_executed",
                         "Fixture only reserved a run; no external executor was called")
        history = self.e.runs()[0]
        new_result = {"status": "delivered", "artifacts": [{"name": "new.txt", "content": "New fixture receipt"}]}
        case = self

        class NewExecutor:
            name = "fixture"

            def execute(self, package):
                case.assertTrue(package["host_owner"])
                case.assertNotEqual(package["host_owner"], old["host_owner"])
                case.assertNotEqual(package["run_id"], old["run_id"])
                view = snapshot(new)
                case.assertEqual(view["runtime"]["active_run_id"], package["run_id"])
                case.assertEqual(view["runtime"]["liveness"], "confirmed")
                case.assertEqual([r["host_confirmed"] for r in view["runs"]], [False, True])
                case.reject_old_receipts(old)
                case.assertEqual(new.runs()[0], history)
                return new_result, {"input_tokens": 3, "output_tokens": 2}

        result = run(new, NewExecutor(), 1)
        self.assertEqual(result[0]["action"], "work", result)
        records = new.runs()
        self.assertEqual(records[0], history)
        self.assertEqual([r["status"] for r in records], ["reconciled", "delivered"])
        self.assertEqual(records[1]["result"], new_result)
        self.assertEqual(records[1]["usage"], {"input_tokens": 3, "output_tokens": 2, "cost": None, "cost_status": "unknown", "cost_basis":"unknown", "cost_minor":None,"currency":None,"billing_revision":None})
        self.assertEqual([a["name"] for a in new.state()["artifacts"].values()], ["new.txt"])
        self.assertEqual(new.status()["budget"]["calls_reserved"], 2)
