import copy
import json
import tempfile
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from ai_union.engine import Engine, Rejected
from ai_union.executor import FixtureExecutor, ExecutionFailure
from ai_union.runner import run, exclusive
from ai_union.activity import activity
from ai_union.observation import snapshot, artifact
from ai_union.console import Console
from tests.support import CHARTER, RESOURCES, init, organization

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "examples/fixture.json").read_text(encoding="utf-8"))


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Console(Path(self.temp.name) / "console", fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.observer = self.app.new_session("observer")
        self.counter = 0
        result = self.command("create", {"name": "test", "goal": "test collaboration", "board_name": "test adopter",
                              "charter": CHARTER, "resources": RESOURCES}, org_id=None)
        self.org = result["organization_id"]
        self.e = self.app.engine(self.board, self.org)

    def command(self, kind, data, org_id="current", session=None, request_id=None, version=None):
        oid = getattr(self, "org", None) if org_id == "current" else org_id
        self.counter += 1
        if version is None and oid:
            version = self.app.engine(self.board, oid).state()["version"]
        return self.app.command(session or self.board, {"id": request_id or f"request-{self.counter}",
            "organization_id": oid, "base_version": version, "kind": kind, "data": data})

    def test_observer_and_scope_are_enforced_on_direct_commands(self):
        with self.assertRaises(Rejected):
            self.command("event", {"kind": "opinion", "source": "test", "simulated": True, "content": "x"}, session=self.observer)
        isolated = self.app.new_session("observer", organizations=[])
        with self.assertRaises(Rejected):
            self.app.engine(isolated, self.org)
        with self.assertRaises(Rejected):
            self.app.engine(self.board, "../state.sqlite3")
        limited_board = self.app.new_session("board", organizations=[])
        self.command("create", {}, org_id=None, request_id="rejected-create")
        with self.assertRaises(Rejected):
            self.app.receipt(limited_board, None, "rejected-create")

    def test_creation_is_durable_and_does_not_overwrite(self):
        data = {"name": "another", "goal": "goal", "board_name": "test", "charter": CHARTER, "resources": RESOURCES}
        first = self.command("create", data, org_id=None, request_id="create-again")
        second = self.command("create", data, org_id=None, request_id="create-again")
        self.assertEqual(first, second)
        self.assertNotEqual(first["organization_id"], self.org)
        with self.assertRaises(Rejected):
            self.command("create", data | {"name": "different"}, org_id=None, request_id="create-again")

    def test_event_idempotency_includes_payload_and_does_not_change_version(self):
        data = {"event_id": "external-1", "kind": "external_feedback", "content": "test", "source": "fixture", "simulated": True}
        version = self.e.state()["version"]
        a = self.command("event", data, request_id="event-1", version=version)
        b = self.command("event", data, request_id="event-1", version=version)
        self.assertEqual(a, b)
        self.assertEqual(self.e.state()["version"], version)
        self.assertEqual(len([e for e in self.e.events() if e["id"] == "external-1"]), 1)
        with self.assertRaises(Rejected):
            self.command("event", data | {"content": "different"}, request_id="event-1", version=version)
        rejected = self.command("event", data | {"simulated": "false"})
        self.assertEqual(rejected["status"], "rejected")

    def test_versions_and_resources_preserve_usage_and_rejections(self):
        self.e.begin_decision("fixture")
        old = self.e.state()["version"]
        self.e.recover()
        rejected = self.command("resources", {"resources": RESOURCES, "reason": "test"}, version=old)
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(len(self.e.runs()), 1)
        good = self.command("resources", {"resources": RESOURCES | {"max_calls": 15}, "reason": "test"})
        self.assertEqual(good["status"], "succeeded")
        self.assertEqual(snapshot(self.e)["budget"]["calls_reserved"], 1)

    def test_amendment_obeys_old_rules(self):
        self.assertEqual(self.command("amend", {"charter": CHARTER | {"board_can_amend": False}, "reason": "test"})["status"], "succeeded")
        self.assertEqual(self.command("amend", {"charter": CHARTER, "reason": "test"})["status"], "rejected")
        self.assertEqual(self.e.state()["charter_version"], 2)

    def test_slow_execution_pause_is_durable_and_stops_next_dispatch(self):
        entered, release = threading.Event(), threading.Event()
        class Slow(FixtureExecutor):
            def execute(inner, package):
                entered.set()
                release.wait(5)
                return super().execute(package)
        self.app.executor_factory = lambda e, data: Slow(copy.deepcopy(FIXTURE))
        started = self.command("start", {"executor": "fixture", "max_steps": 8})
        self.addCleanup(release.set)
        self.assertTrue(entered.wait(3))
        observed = snapshot(self.e)
        self.assertEqual(observed["execution_state"], "running")
        self.assertNotIn("需要核对", " ".join(observed["blocked_reasons"]))
        self.assertEqual(self.command("resources", {"resources": RESOURCES, "reason": "test"})["status"], "rejected")
        self.assertEqual(self.command("pause", {})["status"], "succeeded")
        self.assertEqual(snapshot(self.e)["dispatch_state"], "pause_requested")
        release.set()
        self.app.join_jobs()
        self.assertEqual(len(self.e.runs()), 1)
        self.assertEqual(snapshot(Engine(self.e.root))["dispatch_state"], "paused")
        self.assertEqual(run(self.e, FixtureExecutor([]), 1)[0]["action"], "paused")
        self.assertEqual(self.app.receipt(self.board, self.org, started["id"])["status"], "succeeded")

    def test_thread_start_failure_is_durable_and_does_not_dispatch_or_leak_lock(self):
        data = {"executor": "fixture", "max_steps": 1}
        version = self.e.state()["version"]
        with patch("ai_union.console.threading.Thread.start", side_effect=RuntimeError("private host error")):
            receipt = self.command("start", data, request_id="failed-start", version=version)
        self.assertEqual(receipt["status"], "rejected")
        self.assertNotIn("private host error", json.dumps(receipt))
        self.assertEqual(self.e.runs(), [])
        self.assertEqual(snapshot(self.e)["dispatch_state"], "paused")
        self.assertEqual(self.app.jobs, [])
        with exclusive(self.e):
            pass  # The failed start must release the dispatcher lock.
        self.app.close()
        self.app = Console(self.app.root, fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.assertEqual(self.app.receipt(self.board, self.org, "failed-start"), receipt)
        self.assertEqual(self.command("start", data, request_id="failed-start", version=version), receipt)
        self.assertEqual(self.e.runs(), [])
        self.assertEqual(self.command("start", data)["status"], "accepted")
        self.app.join_jobs()
        self.assertEqual(len(self.e.runs()), 1)

    def test_unknown_keeps_reservation_and_requires_explicit_reconciliation(self):
        class Unknown:
            name = "fixture"
            def execute(inner, package):
                raise ExecutionFailure("private executor error", unknown=True)
        self.app.executor_factory = lambda e, data: Unknown()
        self.command("start", {"executor": "fixture", "max_steps": 2})
        self.app.join_jobs()
        self.assertEqual(snapshot(self.e)["execution_state"], "unknown")
        rid = self.e.runs()[0]["id"]
        self.assertEqual(self.command("start", {"executor": "fixture", "max_steps": 1})["status"], "rejected")
        self.assertEqual(self.command("reconcile", {"run_id": rid, "resolution": "abandon", "reason": "checked test receipt"})["status"], "succeeded")
        self.assertEqual(len(self.e.runs()), 1)

    def test_unconfirmed_running_is_not_alive_and_cannot_be_reconciled(self):
        rid = self.e.begin_decision("fixture")["run_id"]
        self.assertEqual(snapshot(self.e)["execution_state"], "unconfirmed")
        with exclusive(self.e), activity(self.e):
            self.assertEqual(snapshot(self.e)["execution_state"], "unconfirmed")
        self.assertEqual(self.command("reconcile", {"run_id": rid, "resolution": "abandon", "reason": "test"})["status"], "rejected")

    def test_snapshot_is_readonly_consistent_and_excludes_private_logs(self):
        run(self.e, FixtureExecutor(copy.deepcopy(FIXTURE)), 8)
        before = (self.e.state(), self.e.events(), self.e.runs())
        for _ in range(3):
            view = snapshot(self.e)
            self.assertEqual(view["budget"]["calls_reserved"], len(view["runs"]))
            for a in view["organization"]["artifacts"].values():
                self.assertTrue(artifact(self.e, a["id"])["content"])
            self.assertNotIn('"package"', json.dumps(view))
            self.assertNotIn('"path"', json.dumps(view))
            self.assertNotIn("board_hash", json.dumps(view))
        self.assertEqual(before, (self.e.state(), self.e.events(), self.e.runs()))
        a = next(iter(self.e.state()["artifacts"].values()))
        (self.e.root / a["path"]).write_text("tampered", encoding="utf-8")
        with self.assertRaises(Rejected):
            artifact(self.e, a["id"])
        (self.e.root / a["path"]).unlink()
        with self.assertRaises(Rejected):
            artifact(self.e, a["id"])

    def test_same_version_snapshots_include_new_events_and_reservations(self):
        a = snapshot(self.e)
        self.e.add_event("added", "opinion", {"source": "test", "simulated": True})
        self.e.begin_decision("fixture")
        b = snapshot(self.e)
        self.assertEqual(a["organization"]["version"], b["organization"]["version"])
        self.assertEqual(b["pending_events"], a["pending_events"] + 1)
        self.assertEqual(b["budget"]["calls_reserved"], a["budget"]["calls_reserved"] + 1)

    def test_private_failure_summary_stays_private_after_reconciliation_and_restart(self):
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        self.e.fail_run(package["run_id"], "PRIVATE_EXECUTOR_LOG_SECRET", unknown=True)
        # Also cover an existing database written before the safe-summary change.
        with self.e.transaction() as cx:
            state = self.e._state(cx)
            state["work"]["w1"]["summary"] = "PRIVATE_EXECUTOR_LOG_SECRET"
            self.e._save(cx, state)
        self.command("reconcile", {"run_id": package["run_id"], "resolution": "confirmed_not_executed", "reason": "checked test receipt"})
        self.assertNotIn("PRIVATE_EXECUTOR_LOG_SECRET", json.dumps(snapshot(self.e)))
        self.e.begin_work("w1", "fixture")
        self.assertNotIn("PRIVATE_EXECUTOR_LOG_SECRET", json.dumps(snapshot(self.e)))

    def test_parallel_duplicate_command_commits_one_event(self):
        version = self.e.state()["version"]
        request = {"id": "concurrent", "organization_id": self.org, "base_version": version, "kind": "event",
                   "data": {"event_id": "same-receipt", "kind": "opinion", "content": "test", "source": "test", "simulated": True}}
        with ThreadPoolExecutor(max_workers=8) as pool:
            receipts = list(pool.map(lambda _: self.app.command(self.board, request), range(16)))
        self.assertTrue(all(r == receipts[0] for r in receipts))
        self.assertEqual(len([e for e in self.e.events() if e["id"] == "same-receipt"]), 1)

    def test_creation_storage_failure_is_unknown_and_not_replayed(self):
        data = {"name": "interrupted", "goal": "goal", "board_name": "test", "charter": CHARTER, "resources": RESOURCES}
        original = Engine.create
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("private storage diagnostic")
        with patch.object(Engine, "create", side_effect=interrupted) as create:
            result = self.command("create", data, org_id=None, request_id="interrupted-create")
            repeated = self.command("create", data, org_id=None, request_id="interrupted-create")
        self.assertEqual(create.call_count, 1)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result, repeated)
        self.assertNotIn("private storage diagnostic", json.dumps(result))

    def test_creation_registration_failure_keeps_unknown_receipt_queryable(self):
        original = self.app.catalog
        calls = 0
        @contextmanager
        def fail_registration():
            nonlocal calls
            calls += 1
            with original() as cx:
                yield cx
                if calls == 2:
                    raise sqlite3.OperationalError("injected registration failure")
        data = {"name": "unregistered", "goal": "test", "board_name": "test", "charter": CHARTER, "resources": RESOURCES}
        with patch.object(self.app, "catalog", fail_registration):
            result = self.command("create", data, org_id=None, request_id="registration-failed")
        self.assertEqual(result["status"], "unknown")
        self.assertIsNotNone(result["organization_id"])
        self.assertEqual(self.app.receipt(self.board, None, result["id"]), result)
        self.assertEqual(self.command("create", data, org_id=None, request_id="registration-failed"), result)
        self.assertEqual(len(self.app.organizations()), 1)

    def test_failure_after_internal_write_rolls_back_state_but_records_rejection(self):
        execute = self.app._execute
        def injected(e, request):
            execute(e, request)
            raise Rejected("test injected rollback")
        with patch.object(self.app, "_execute", injected):
            result = self.command("event", {"event_id": "rollback", "kind": "opinion", "content": "test", "source": "test", "simulated": True})
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(any(e["id"] == "rollback" for e in self.e.events()))
        self.assertEqual(self.app.receipt(self.board, self.org, result["id"]), result)

    def test_pause_between_selection_and_reservation_prevents_call(self):
        begin = self.e.begin_decision
        def pause_first(executor):
            self.e.set_paused(True)
            return begin(executor)
        with patch.object(self.e, "begin_decision", pause_first):
            run(self.e, FixtureExecutor(copy.deepcopy(FIXTURE)), 1)
        self.assertEqual(self.e.runs(), [])

    def test_concurrent_read_snapshots_are_internally_consistent(self):
        def write():
            run(self.e, FixtureExecutor(copy.deepcopy(FIXTURE)), 8)
        thread = threading.Thread(target=write)
        thread.start()
        while thread.is_alive():
            view = snapshot(self.e)
            self.assertEqual(view["budget"]["calls_reserved"], len(view["runs"]))
            runs = {r["id"]: r for r in view["runs"]}
            for a in view["organization"]["artifacts"].values():
                self.assertEqual(runs[a["run_id"]]["status"], "delivered")
                self.assertIn(a["id"], view["organization"]["work"][a["work_id"]]["artifact_ids"])
        thread.join()

    def test_job_restart_never_replays_a_running_execution(self):
        self.e.begin_decision("fixture")
        self.app.close()
        self.app = Console(self.app.root, fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.assertEqual(snapshot(self.e)["execution_state"], "unconfirmed")
        result = self.command("start", {"executor": "fixture", "max_steps": 1})
        self.app.join_jobs()
        self.assertEqual(self.app.receipt(self.board, self.org, result["id"])["status"], "blocked")
        self.assertEqual(len(self.e.runs()), 1)
        self.assertEqual(snapshot(self.e)["execution_state"], "unknown")
