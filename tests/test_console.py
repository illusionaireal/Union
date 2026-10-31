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
from tests.support import CHARTER, RESOURCES, decision, init, organization

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

    def test_model_configuration_is_versioned_scoped_and_persistent(self):
        original = self.e.state()["version"]
        data = {"model": "test-model-a", "reason": "test configuration only"}
        receipt = self.command("model", data, request_id="model-setting", version=original)
        self.assertEqual(receipt["status"], "succeeded")
        self.assertEqual(self.command("model", data, request_id="model-setting", version=original), receipt)
        self.assertEqual(self.e.state()["version"], original + 1)
        self.assertEqual(snapshot(self.e)["execution_config"]["codex_model"], "test-model-a")
        self.assertEqual(self.e.runs(), [])
        self.assertEqual(self.command("model", data | {"model": "stale-model"}, version=original)["status"], "rejected")
        with self.assertRaises(Rejected):
            self.command("model", data, session=self.observer)
        with self.assertRaises(Rejected):
            self.e.configure_model("not-the-board-key", "test-model-b", "test")
        other = self.command("create", {"name": "other", "goal": "test", "board_name": "test", "charter": CHARTER, "resources": RESOURCES}, org_id=None)
        self.assertIsNone(self.app.observe(self.board, other["organization_id"])["execution_config"]["codex_model"])
        self.app.close()
        self.app = Console(self.app.root, fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.assertEqual(self.app.observe(self.board, self.org)["execution_config"]["codex_model"], "test-model-a")

    def test_model_configuration_rejects_invalid_input_and_running_changes(self):
        for model in (42, [], "--config", "name\nsecret", "x" * 129):
            with self.subTest(model=model):
                self.assertEqual(self.command("model", {"model": model, "reason": "test"})["status"], "rejected")
        with exclusive(self.e):
            self.assertEqual(self.command("model", {"model": "test-model", "reason": "test"})["status"], "rejected")
        self.assertEqual(self.e.state()["version"], 0)
        self.command("model", {"model": "test-model", "reason": "test"})
        self.assertEqual(self.command("model", {"model": "", "reason": "restore CLI default"})["status"], "succeeded")
        self.assertIsNone(snapshot(self.e)["execution_config"]["codex_model"])

    def test_saved_model_and_per_run_override_reach_executor_without_enabling_it(self):
        self.command("model", {"model": "test-model-a", "reason": "test"})
        data = {"executor": "codex", "max_steps": 1, "allow_unknown_cost": True}
        self.assertEqual(self.command("start", data)["status"], "rejected")
        self.app.enable_codex = True
        self.assertEqual(self.command("start", data | {"allow_unknown_cost": False})["status"], "rejected")
        calls = 0
        def double(root, model=None):
            nonlocal calls
            executor = FixtureExecutor(copy.deepcopy(FIXTURE[calls:]))
            calls += 1
            executor.model = model
            return executor
        with patch("ai_union.console.CodexExecutor", side_effect=double) as factory:
            first = None
            for values, model in (({}, "test-model-a"), ({"model": "test-model-b"}, "test-model-b"), ({"model": None}, None)):
                receipt = self.command("start", data | values)
                first = first or receipt
                self.assertEqual(receipt["status"], "accepted")
                self.app.join_jobs()
                self.assertEqual(factory.call_args.kwargs["model"], model)
                self.assertEqual(self.app.receipt(self.board, self.org, receipt["id"])["requested_model"], model)
            self.command("model", {"model": "test-model-c", "reason": "new default after run"})
            replay = self.command("start", data, request_id=first["id"], version=first["base_version"])
            self.assertEqual(replay["requested_model"], "test-model-a")
            self.assertEqual(factory.call_count, 3)
        self.assertEqual(snapshot(self.e)["execution_config"]["codex_model"], "test-model-c")
        self.assertEqual(self.command("start", {"executor": "fixture", "max_steps": 1, "model": "test-model-a"})["status"], "rejected")

    def test_cli_uses_organization_model_unless_explicitly_overridden(self):
        from ai_union.cli import main
        import io
        self.command("model", {"model": "test-model-a", "reason": "CLI defaults"})
        base = ["--root", str(self.e.root), "run", "--executor", "codex", "--max-steps", "1", "--allow-unknown-cost"]
        def no_dispatch(engine, factory, max_steps):
            with exclusive(engine):
                factory()
            return [{"action": "wait"}]
        with patch("ai_union.cli.CodexExecutor") as factory, patch("ai_union.cli.run", side_effect=no_dispatch), patch("sys.stdout", new_callable=io.StringIO):
            factory.return_value.name = "codex"
            for extra, expected in (([], "test-model-a"), (["--model", "test-model-b"], "test-model-b"), (["--model", ""], None)):
                self.assertEqual(main(base + extra), 0)
                self.assertEqual(factory.call_args.kwargs["model"], expected)
        self.assertEqual(self.e.runs(), [])

    def test_cli_run_and_watch_resolve_model_after_acquiring_dispatch_lock(self):
        from ai_union import cli, runner
        import io
        calls = []
        def double(root, model=None):
            with self.assertRaises(Rejected):
                with exclusive(self.e):
                    pass
            executor = FixtureExecutor(copy.deepcopy(FIXTURE[len(calls):]))
            calls.append(model)
            return executor
        for cmd in ("run", "watch"):
            self.command("model", {"model": "old-model", "reason": "initial default"})
            original = getattr(runner, cmd)
            def interleaved(engine, factory, *args):
                self.command("model", {"model": "new-model", "reason": "saved before dispatcher lock"})
                return original(engine, factory, *args)
            argv = ["--root", str(self.e.root), cmd, "--executor", "codex", "--max-steps", "1", "--allow-unknown-cost"]
            if cmd == "watch":
                argv += ["--max-seconds", "1"]
            with patch("ai_union.cli.CodexExecutor", side_effect=double), patch.object(cli, cmd, side_effect=interleaved), patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(cli.main(argv), 0)
        self.assertEqual(calls, ["new-model", "new-model"])

    def test_cli_rechecks_money_cap_after_acquiring_dispatch_lock(self):
        from ai_union import cli, runner
        import io
        for cmd in ("run", "watch"):
            self.command("resources", {"resources": RESOURCES, "reason": "reset test cap"})
            original = getattr(runner, cmd)
            def interleaved(engine, factory, *args):
                with exclusive(self.e):
                    key = (self.e.root / "board.key").read_text(encoding="utf-8").strip()
                    self.e.configure_resources(key, RESOURCES | {"max_cost": 100, "cost_reserve_per_call": 1}, "test cap added before lock")
                return original(engine, factory, *args)
            argv = ["--root", str(self.e.root), cmd, "--executor", "codex", "--max-steps", "1", "--allow-unknown-cost"]
            if cmd == "watch":
                argv += ["--max-seconds", "1"]
            with patch("ai_union.cli.CodexExecutor") as factory, patch.object(cli, cmd, side_effect=interleaved), patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(cli.main(argv), 2)
                factory.assert_not_called()
        self.assertEqual(self.e.runs(), [])

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

    def test_runtime_member_projection_is_readonly_and_does_not_expose_host_details(self):
        organization(self.e)
        before = (self.e.state(), self.e.events(), self.e.runs())
        view = snapshot(self.e)
        self.assertEqual(view["runtime"]["mode"], "unregistered")
        self.assertEqual(view["runtime"]["liveness"], "unknown")
        member = next(item for item in view["member_execution"] if item["member_id"] == "m1")
        self.assertEqual(member["work_state"], "ready")
        self.assertEqual(member["workspace"]["mode"], "virtual_only")
        self.assertNotIn("directory", json.dumps(view))
        self.assertNotIn("container", json.dumps(view))
        self.assertEqual(before, (self.e.state(), self.e.events(), self.e.runs()))

    def test_runtime_member_projection_preserves_waiting_and_unknown_states(self):
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        self.e.fail_run(package["run_id"], "private", unknown=True)
        unknown = snapshot(self.e)
        first = next(item for item in unknown["member_execution"] if item["member_id"] == "m1")
        self.assertEqual(first["work_state"], "blocked")
        self.assertIn("run_requires_reconciliation", first["reason_codes"])
        waiting = next(item for item in unknown["member_execution"] if item["member_id"] == "m2")
        self.assertEqual(waiting["work_state"], "waiting")
        self.assertIn("dependency_pending", waiting["reason_codes"])

    def _retried_member_runs(self):
        organization(self.e)
        first = self.e.begin_work("w1", "fixture")
        self.e.finish_work(first["run_id"], {"status": "blocked", "summary": "Fixture input needed"}, {})
        self.e.apply_decision(decision(self.e, [{"op": "resume_work", "work_id": "w1"}]), "m1", "a1")
        latest = self.e.begin_work("w1", "fixture")
        self.e.finish_work(latest["run_id"], {"status": "delivered", "artifacts": [{"name": "first.txt", "content": "Fixture delivery"}]}, {})
        other = self.e.begin_work("w2", "fixture")
        self.e.finish_work(other["run_id"], {"status": "delivered", "artifacts": [{"name": "dependent.txt", "content": "Fixture dependent delivery"}]}, {})
        return first, latest, other

    def test_runtime_recent_run_uses_latest_persisted_member_run_without_writing(self):
        first, latest, other = self._retried_member_runs()
        before = (self.e.state(), self.e.events(), self.e.runs())
        for engine in (self.e, Engine(self.e.root), self.e):
            view = snapshot(engine)
            members = {item["member_id"]: item for item in view["member_execution"]}
            self.assertEqual(members["m1"]["recent_run"]["id"], latest["run_id"])
            self.assertEqual(members["m1"]["recent_run"]["status"], "delivered")
            self.assertEqual(members["m1"]["recent_run"]["work_id"], "w1")
            self.assertEqual(members["m2"]["recent_run"]["id"], other["run_id"])
            self.assertEqual([r["id"] for r in view["runs"]], [first["run_id"], latest["run_id"], other["run_id"]])
            self.assertEqual(view["budget"]["calls_reserved"], 3)
        self.assertEqual(before, (self.e.state(), self.e.events(), self.e.runs()))

    def test_runtime_idle_session_follows_latest_member_run_without_reading_feedback(self):
        from ai_union.harness import session_tables
        first, latest, other = self._retried_member_runs()
        with self.e.transaction() as cx:
            session_tables(cx)
            for sid, package in (("session-old", first), ("session-latest", latest), ("session-other", other)):
                cx.execute("INSERT INTO agent_sessions(id,task_key,status,last_run_id,feedback,updated_at) VALUES(?,?,'completed',?,?,?)",
                           (sid, sid, package["run_id"], "PRIVATE_SESSION_FEEDBACK", "2026-10-31T00:00:00+00:00"))
        with self.e.read_transaction() as cx:
            before = [dict(row) for row in cx.execute("SELECT * FROM agent_sessions ORDER BY rowid")]
        for engine in (self.e, Engine(self.e.root)):
            view = snapshot(engine)
            members = {item["member_id"]: item for item in view["member_execution"]}
            self.assertIsNone(members["m1"]["current_work_id"])
            self.assertEqual(members["m1"]["session"]["id"], "session-latest")
            self.assertEqual(members["m2"]["session"]["id"], "session-other")
            self.assertNotIn("PRIVATE_SESSION_FEEDBACK", json.dumps(view))
        with self.e.read_transaction() as cx:
            self.assertEqual(before, [dict(row) for row in cx.execute("SELECT * FROM agent_sessions ORDER BY rowid")])

    def test_runtime_recent_member_run_includes_later_decision(self):
        self._retried_member_runs()
        latest = self.e.begin_decision("fixture")
        self.e.finish_decision(latest["run_id"], decision(self.e, []), {})
        view = snapshot(self.e)
        member = next(item for item in view["member_execution"] if item["member_id"] == "m1")
        self.assertEqual(member["recent_run"]["id"], latest["run_id"])
        self.assertIsNone(member["recent_run"]["work_id"])

    def _runtime_member(self, engine, member_id="m1"):
        before = (engine.state(), engine.events(), engine.runs(), engine.paused())
        result = None
        for reader in (engine, Engine(engine.root), engine):
            view = snapshot(reader)
            result = next(item for item in view["member_execution"] if item["member_id"] == member_id)
            self.assertEqual(view["budget"]["calls_reserved"], len(before[2]))
        self.assertEqual(before, (engine.state(), engine.events(), engine.runs(), engine.paused()))
        return result

    def _extra_runtime_work(self, work_id, position_id="p1", dependencies=None):
        return {"op": "create_work", "id": work_id, "title": "Fixture observation work",
                "instruction": "Produce a fixture artifact", "position_id": position_id,
                "dependencies": dependencies or []}

    def test_runtime_unfinished_work_states_are_not_idle(self):
        for status, expected, reason in (("blocked", "blocked", "work_blocked"),
                                         ("failed", "blocked", "work_failed"),
                                         ("host_failed", "blocked", "work_failed"),
                                         ("needs_review", "blocked", "run_requires_reconciliation"),
                                         ("paused", "waiting", "work_paused")):
            with self.subTest(status=status):
                engine = init(Path(self.temp.name) / status)
                organization(engine)
                if status == "paused":
                    engine.apply_decision(decision(engine, [{"op": "pause_work", "work_id": "w1"}]), "m1", "a1")
                else:
                    package = engine.begin_work("w1", "fixture")
                    if status in ("host_failed", "needs_review"):
                        engine.fail_run(package["run_id"], "PRIVATE_FAILURE_DETAIL", unknown=status == "needs_review")
                    else:
                        engine.finish_work(package["run_id"], {"status": status, "summary": "Fixture result"}, {})
                member = self._runtime_member(engine)
                self.assertEqual(member["current_work_id"], "w1")
                self.assertEqual(member["work_state"], expected)
                self.assertIn(reason, member["reason_codes"])
                self.assertNotIn("PRIVATE_FAILURE_DETAIL", json.dumps(snapshot(engine)))

    def test_runtime_selects_ready_work_ahead_of_earlier_dependency_wait(self):
        organization(self.e)
        self.e.apply_decision(decision(self.e, [{"op": "cancel_work", "work_id": "w1"},
            self._extra_runtime_work("a-waiting", dependencies=["w2"]),
            self._extra_runtime_work("z-ready")]), "m1", "a1")
        member = self._runtime_member(self.e)
        self.assertEqual(self.e.ready_work(), ["z-ready"])
        self.assertEqual((member["current_work_id"], member["work_state"], member["reason_codes"]), ("z-ready", "ready", []))

    def test_runtime_ready_work_is_not_hidden_by_settled_failure(self):
        organization(self.e)
        self.e.apply_decision(decision(self.e, [self._extra_runtime_work("ready")]), "m1", "a1")
        package = self.e.begin_work("w1", "fixture")
        self.e.finish_work(package["run_id"], {"status": "blocked", "summary": "Fixture blocked"}, {})
        member = self._runtime_member(self.e)
        self.assertEqual((member["current_work_id"], member["work_state"]), ("ready", "ready"))

    def test_runtime_unknown_work_precedes_ready_and_never_replays(self):
        from ai_union.runner import step
        organization(self.e)
        self.e.apply_decision(decision(self.e, [self._extra_runtime_work("ready")]), "m1", "a1")
        package = self.e.begin_work("w1", "fixture")
        self.e.fail_run(package["run_id"], "Fixture unknown", unknown=True)
        before = (self.e.state(), self.e.events(), self.e.runs())
        member = self._runtime_member(self.e)
        self.assertEqual((member["current_work_id"], member["work_state"]), ("w1", "blocked"))
        self.assertIn("run_requires_reconciliation", member["reason_codes"])
        self.assertEqual(step(self.e, FixtureExecutor(copy.deepcopy(FIXTURE)))["action"], "blocked")
        self.assertEqual(before, (self.e.state(), self.e.events(), self.e.runs()))
        self.assertEqual(self.command("reconcile", {"run_id": package["run_id"], "resolution": "abandon", "reason": "Fixture receipt checked"})["status"], "succeeded")
        self.assertEqual(self._runtime_member(self.e)["work_state"], "ready")

    def test_runtime_other_members_unknown_blocks_ready_but_preserves_dependency_wait(self):
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        self.e.fail_run(package["run_id"], "Fixture unknown", unknown=True)
        waiting = self._runtime_member(self.e, "m2")
        self.assertEqual((waiting["work_state"], waiting["reason_codes"]), ("waiting", ["dependency_pending"]))
        self.e.apply_decision(decision(self.e, [self._extra_runtime_work("other-ready", "p2")]), "m1", "a1")
        member = self._runtime_member(self.e, "m2")
        self.assertEqual((member["current_work_id"], member["work_state"]), ("other-ready", "blocked"))
        self.assertIn("run_requires_reconciliation", member["reason_codes"])

    def test_runtime_unknown_decision_has_no_work_reference_and_blocks_dispatch(self):
        organization(self.e)
        self.e.apply_decision(decision(self.e, [self._extra_runtime_work("other-ready", "p2")]), "m1", "a1")
        package = self.e.begin_decision("fixture")
        self.e.fail_run(package["run_id"], "Fixture decision unknown", unknown=True)
        member = self._runtime_member(self.e)
        self.assertEqual(member["work_state"], "blocked")
        self.assertIsNone(member["current_work_id"])
        self.assertIn("run_requires_reconciliation", member["reason_codes"])
        other = self._runtime_member(self.e, "m2")
        self.assertEqual((other["current_work_id"], other["work_state"]), ("other-ready", "blocked"))

    def test_runtime_running_requires_current_host_evidence_and_blocks_other_ready(self):
        organization(self.e)
        self.e.apply_decision(decision(self.e, [self._extra_runtime_work("other-ready", "p2")]), "m1", "a1")
        with exclusive(self.e), activity(self.e):
            self.e.begin_work("w1", "fixture")
            member = self._runtime_member(self.e)
            self.assertEqual((member["current_work_id"], member["work_state"]), ("w1", "executing"))
            other = self._runtime_member(self.e, "m2")
            self.assertEqual((other["work_state"], other["reason_codes"]), ("waiting", ["dispatch_busy"]))
        member = self._runtime_member(self.e)
        self.assertEqual((member["work_state"], member["reason_codes"]), ("blocked", ["activity_unconfirmed"]))
        other = self._runtime_member(self.e, "m2")
        self.assertEqual((other["work_state"], other["reason_codes"]), ("blocked", ["activity_unconfirmed"]))

    def test_runtime_pause_budget_resume_and_terminal_work_recompute_without_calls(self):
        organization(self.e)
        self.assertEqual(self.command("pause", {})["status"], "succeeded")
        self.assertEqual(self._runtime_member(self.e)["reason_codes"], ["dispatch_paused"])
        self.e.set_paused(False)
        package = self.e.begin_work("w1", "fixture")
        self.e.finish_work(package["run_id"], {"status": "blocked", "summary": "Fixture input needed"}, {})
        self.e.apply_decision(decision(self.e, [{"op": "resume_work", "work_id": "w1"}]), "m1", "a1")
        self.assertEqual(self.command("resources", {"resources": RESOURCES | {"max_calls": 1}, "reason": "Fixture exhausted allowance"})["status"], "succeeded")
        member = self._runtime_member(self.e)
        self.assertEqual((member["work_state"], member["reason_codes"]), ("blocked", ["budget_limited"]))
        self.assertEqual(self.command("resources", {"resources": RESOURCES, "reason": "Fixture restore original allowance"})["status"], "succeeded")
        self.e.apply_decision(decision(self.e, [{"op": "pause_work", "work_id": "w1"}]), "m1", "a1")
        self.assertEqual(self._runtime_member(self.e)["reason_codes"], ["work_paused"])
        self.e.apply_decision(decision(self.e, [{"op": "resume_work", "work_id": "w1"}]), "m1", "a1")
        self.assertEqual(self._runtime_member(self.e)["work_state"], "ready")
        self.e.apply_decision(decision(self.e, [{"op": "cancel_work", "work_id": "w1"}]), "m1", "a1")
        member = self._runtime_member(self.e)
        self.assertEqual((member["current_work_id"], member["work_state"], member["reason_codes"]), (None, "idle", []))

    def test_runtime_needs_review_after_revocation_precedes_confirmed_activity(self):
        organization(self.e)
        with exclusive(self.e), activity(self.e):
            package = self.e.begin_work("w1", "fixture")
            self.e.apply_decision(decision(self.e, [{"op": "update_position", "position_id": "p1",
                "title": "Fixture responsibility", "mandate": "Coordinate fixture work",
                "permissions": CHARTER["allowed_operations"]}]), "m1", "a1")
            member = self._runtime_member(self.e)
            self.assertEqual(self.e.state()["work"]["w1"]["status"], "needs_review")
            self.assertEqual((member["current_work_id"], member["work_state"], member["reason_codes"]),
                             ("w1", "blocked", ["work_needs_review"]))
            self.assertEqual(member["recent_run"]["id"], package["run_id"])
            self.assertEqual(member["recent_run"]["status"], "running")

    def test_runtime_handoff_does_not_give_new_owner_the_old_members_session(self):
        from ai_union.harness import session_tables
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        with self.e.transaction() as cx:
            session_tables(cx)
            cx.execute("INSERT INTO agent_sessions(id,task_key,status,last_run_id,feedback,updated_at) VALUES(?,?,'paused',?,?,?)",
                       ("old-owner-session", "fixture-task", package["run_id"], "PRIVATE_HANDOFF_FEEDBACK", "2026-10-31T00:00:00+00:00"))
        self.e.apply_decision(decision(self.e, [{"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a3"}]), "m1", "a1")
        member = self._runtime_member(self.e, "m2")
        self.assertEqual((member["current_work_id"], member["work_state"]), ("w1", "blocked"))
        self.assertIn("work_needs_review", member["reason_codes"])
        self.assertIsNone(member["recent_run"])
        self.assertEqual(member["session"], {"id": None, "updated_at": None, "has_checkpoint": False, "resume_state": "not_available"})
        self.assertEqual(self._runtime_member(self.e)["session"]["id"], "old-owner-session")
        self.assertNotIn("PRIVATE_HANDOFF_FEEDBACK", json.dumps(snapshot(self.e)))

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
