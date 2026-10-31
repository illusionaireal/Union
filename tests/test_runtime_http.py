"""Actual loopback HTTP observation boundaries; fixtures are not AU operation."""
import copy
import hashlib
import json
import sqlite3
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.sqlite import SqliteSaver

from ai_union import workspace
from ai_union.activity import activity
from ai_union.harness import session_tables
from ai_union.runner import exclusive
from tests import test_http
from tests.support import CHARTER, RESOURCES, decision, organization


class RuntimeHTTPTests(unittest.TestCase):
    request = test_http.HTTPTests.request

    def setUp(self):
        test_http.HTTPTests.setUp(self)
        self.engines, self.ids, self.private, self.configs = {}, {}, [], {}
        for name in ("a", "b"):
            charter = copy.deepcopy(CHARTER)
            charter["allowed_tools"].append(workspace.TOOL)
            request = {"id": "create-" + name, "organization_id": None, "base_version": None, "kind": "create",
                       "data": {"name": "Public fixture AU " + name, "goal": "Fixture observation " + name,
                                "board_name": "Fixture host", "charter": charter, "resources": RESOURCES}}
            status, response, _ = self.request("POST", "/api/commands", request)
            self.assertEqual(status, 200)
            self.ids[name] = response["receipt"]["organization_id"]
            self.engines[name] = self.app.engine(self.board, self.ids[name])
            self.private.append(str(self.engines[name].root))
            organization(self.engines[name])

    def get(self, name, token="default", extra=None):
        query = {"organization_id": self.ids[name]} | (extra or {})
        token = self.board if token == "default" else token
        headers = {"Cookie": self.server.cookie_name + "=" + token} if token is not None else {}
        return self.request("GET", "/api/snapshot?" + urlencode(query), headers=headers, cookie=False)

    def digest(self):
        result = []
        for engine in self.engines.values():
            with engine.read_transaction() as cx:
                tables = [tuple(r) for r in cx.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
                data = [(name, [tuple(r) for r in cx.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]) for name, _ in tables]
            folder = engine.root / "harness"
            files = {p.name: None if p.name.endswith("-shm") else hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in folder.iterdir() if p.is_file()} if folder.is_dir() else {}
            result.append((hashlib.sha256(repr((tables, data)).encode()).hexdigest(), folder.exists(), files))
        return result

    def guards(self):
        stack = ExitStack()
        for target in ("ai_union.engine.Engine.recover", "ai_union.runner.step", "ai_union.console.step",
                       "ai_union.model_api.APIExecutor.chat", "ai_union.harness.HarnessExecutor.execute",
                       "ai_union.workspace.run_container"):
            stack.enter_context(patch(target, side_effect=AssertionError("GET invoked execution or recovery")))
        stack.enter_context(patch.object(SqliteSaver, "setup", side_effect=AssertionError("GET initialized SDK")))
        stack.enter_context(patch.object(SqliteSaver, "get_tuple", side_effect=AssertionError("GET read checkpoint bodies")))
        return stack

    def read_stable(self, name="a", token="default", extra=None):
        before, last, sequence = self.digest(), None, -1
        with self.guards():
            for _ in range(3):
                status, view, headers = self.get(name, token, extra)
                self.assertEqual(status, 200)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(view["organization"]["id"], self.ids[name])
                self.assertEqual(view["organization"]["name"], "Public fixture AU " + name)
                self.assertEqual(view["dispatch_state"], view["runtime"]["dispatch_state"])
                self.assertEqual(view["runtime"]["mode"], "unregistered")
                self.assertGreater(view["snapshot_sequence"], sequence)
                sequence, last = view["snapshot_sequence"], view
                public = json.dumps(view)
                for value in self.private:
                    self.assertNotIn(value, public)
        self.assertEqual(before, self.digest())
        return last

    def private_fixture(self, name, *, checkpoint=False, unknown=True, wal=True):
        engine = self.engines[name]
        key = (engine.root / "board.key").read_text().strip()
        secret = "PRIVATE_API_KEY_" + name
        request = {"id": "connection-" + name, "organization_id": self.ids[name],
                   "base_version": engine.state()["version"], "kind": "api_connection",
                   "data": {"connection_id": "fixture-model", "api_key": secret, "reason": "Fixture only",
                            "config": {"name": "Fixture connection", "base_url": "https://provider.invalid/v1",
                                       "model": "fixture-model", "token_limit_field": "max_tokens",
                                       "max_output_tokens": 100, "timeout_seconds": 3, "enabled": True}}}
        status, response, _ = self.request("POST", "/api/commands", request)
        self.assertEqual(status, 200)
        self.assertEqual(response["receipt"]["status"], "succeeded")
        position = engine.state()["positions"]["p1"]
        engine.apply_decision(decision(engine, [{"op": "update_position", "position_id": "p1", "title": position["title"],
            "mandate": position["mandate"], "permissions": position["permissions"] + [workspace.TOOL]}]), "m1", "a1")
        directory = Path(self.temp.name) / ("PRIVATE_WORKSPACE_" + name)
        directory.mkdir()
        config = {"directory": str(directory), "image": "sha256:" + name * 64, "timeout_seconds": 30, "enabled": True}
        workspace.configure(engine, key, config, "Fixture host binding")
        self.configs[name] = config
        package = engine.begin_work("w1", "fixture")
        failure = "PRIVATE_HOST_FAILURE_" + name
        if unknown:
            engine.fail_run(package["run_id"], failure, unknown=True)
        else:
            engine.finish_work(package["run_id"], {"status": "blocked", "summary": "Fixture waiting"}, {})
        feedback = "PRIVATE_FEEDBACK_" + name
        with engine.transaction() as cx:
            session_tables(cx)
            cx.execute("INSERT INTO agent_sessions(id,task_key,status,last_run_id,feedback,updated_at) VALUES(?,?,?,?,?,?)",
                       ("shared-session-id", "fixture-task", "unknown" if unknown else "paused", package["run_id"], feedback, "2026-10-31T00:00:00Z"))
        body, metadata = "PRIVATE_CHECKPOINT_BODY_" + name, "PRIVATE_CHECKPOINT_METADATA_" + name
        if checkpoint:
            folder = engine.root / "harness"
            folder.mkdir()
            cx = sqlite3.connect(folder / "checkpoints.sqlite3")
            self.addCleanup(cx.close)  # Keep writer open; WAL observation stays unknown.
            value = empty_checkpoint()
            value["channel_values"] = {"private": body}
            SqliteSaver(cx).put({"configurable": {"thread_id": "shared-session-id", "checkpoint_ns": ""}}, value,
                               {"source": "input", "step": -1, "parents": {}, "private": metadata}, {})
            if not wal:
                self.assertEqual(cx.execute("PRAGMA journal_mode=DELETE").fetchone()[0], "delete")
        self.private.extend((key, secret, str(directory), config["image"], failure, feedback, body, metadata, str(engine.root)))

    def test_http_session_roles_and_actual_au_scope(self):
        for role in ("board", "observer"):
            global_token = self.app.new_session(role)
            limited = self.app.new_session(role, organizations=[self.ids["a"]])
            for name in ("a", "b"):
                self.read_stable(name, global_token)
            self.read_stable("a", limited)
            before = self.digest()
            self.assertEqual(self.get("b", limited)[0], 403)
            status, info, _ = self.request("GET", "/api/session", headers={"Cookie": self.server.cookie_name + "=" + limited}, cookie=False)
            self.assertEqual(status, 200)
            self.assertEqual([r["id"] for r in info["organizations"]], [self.ids["a"]])
            self.assertEqual(before, self.digest())
        expired = self.app.new_session("observer", organizations=[self.ids["a"]])
        self.app.sessions[expired]["expires"] = 0
        for token in (None, "forged-test-cookie", expired):
            self.assertEqual(self.get("a", token)[0], 401)

    def test_same_member_session_ids_and_whole_response_privacy(self):
        self.private_fixture("a", checkpoint=True, wal=False)  # Present DELETE store is still unknown.
        self.private_fixture("b", checkpoint=False)
        for role in ("board", "observer"):
            token = self.app.new_session(role)
            first, second = self.read_stable("a", token), self.read_stable("b", token)
            for view in (first, second):
                self.assertEqual(set(view["organization"]["members"]), {"m1", "m2"})
                self.assertEqual(view["member_execution"][0]["session"]["id"], "shared-session-id")
                self.assertEqual(view["member_execution"][0]["recent_run"]["id"], view["runs"][0]["id"])
                self.assertEqual(view["member_execution"][0]["session"]["resume_state"], "requires_reconciliation")
                self.assertTrue(view["receipts"])
            self.assertIsNone(first["member_execution"][0]["session"]["has_checkpoint"])
            self.assertFalse(second["member_execution"][0]["session"]["has_checkpoint"])
            self.assertNotEqual(first["runs"][0]["id"], second["runs"][0]["id"])

    def test_forged_observation_parameters_and_runtime_commands_do_not_expand_scope(self):
        limited = self.app.new_session("observer", organizations=[self.ids["a"]])
        session_before = self.app.session(limited)
        extra = {"role": "board", "organizations": self.ids["b"], "member_id": "m1", "runtime_manage": "true",
                 "root": str(self.engines["b"].root), "path": str(self.engines["b"].root)}
        self.read_stable("a", limited, extra)
        before = self.digest()
        self.assertEqual(self.get("b", limited, extra)[0], 403)
        command = {"id": "forged-runtime", "organization_id": self.ids["a"],
                   "base_version": self.engines["a"].state()["version"], "kind": "runtime_start", "data": {"runtime_manage": True}}
        self.assertEqual(self.request("POST", "/api/commands", command)[0], 409)
        self.assertEqual(self.request("POST", "/api/runtime-commands", command)[0], 404)
        self.assertEqual(self.request("POST", "/api/commands", command,
            headers={"Cookie": self.server.cookie_name + "=" + limited}, cookie=False)[0], 403)
        self.assertEqual(before, self.digest())
        self.assertEqual(session_before, self.app.session(limited))

    def test_http_state_chain_and_budget_do_not_execute_on_get(self):
        engine = self.engines["a"]
        token = self.app.new_session("observer", organizations=[self.ids["a"]])
        initial = self.read_stable(token=token)
        self.assertEqual([m["work_state"] for m in initial["member_execution"]], ["ready", "waiting"])
        engine.set_paused(True)
        self.assertEqual(self.read_stable(token=token)["dispatch_state"], "paused")
        engine.set_paused(False)
        with exclusive(engine), activity(engine):
            package = engine.begin_work("w1", "fixture")
            view = self.read_stable(token=token)
            self.assertEqual(view["runtime"]["active_run_id"], package["run_id"])
            self.assertEqual(view["member_execution"][0]["work_state"], "executing")
        view = self.read_stable(token=token)
        self.assertEqual(view["runs"][0]["display_status"], "unconfirmed")
        self.assertEqual(view["member_execution"][0]["reason_codes"], ["activity_unconfirmed"])
        engine.fail_run(package["run_id"], "Fixture unknown", unknown=True)
        self.assertEqual(self.read_stable(token=token)["dispatch_state"], "needs_review")
        other = self.engines["b"]
        work = other.begin_work("w1", "fixture")
        other.finish_work(work["run_id"], {"status": "delivered", "artifacts": [{"name": "fixture.txt", "content": "Fixture delivery"}]}, {})
        other.configure_resources((other.root / "board.key").read_text().strip(), RESOURCES | {"max_calls": 1}, "Fixture cap")
        view = self.read_stable("b")
        self.assertEqual([m["work_state"] for m in view["member_execution"]], ["idle", "blocked"])
        self.assertEqual(view["member_execution"][1]["reason_codes"], ["budget_limited"])

    def test_http_current_authority_changes_do_not_resume_historical_checkpoint(self):
        self.private_fixture("a", checkpoint=True, unknown=False)
        engine = self.engines["a"]
        key = (engine.root / "board.key").read_text().strip()
        token = self.app.new_session("observer", organizations=[self.ids["a"]])
        view = self.read_stable(token=token)
        self.assertTrue(view["member_execution"][0]["workspace"]["available"])
        self.assertEqual(view["member_execution"][0]["session"]["resume_state"], "unknown")
        workspace.disable(engine, key, "Fixture revocation")
        self.assertEqual(self.read_stable(token=token)["member_execution"][0]["workspace"]["reason_codes"], ["workspace_disabled"])
        workspace.configure(engine, key, self.configs["a"], "Fixture rebind")
        charter = engine.charter()
        charter["allowed_tools"].remove(workspace.TOOL)
        engine.amend(key, charter, "Fixture charter revocation")
        view = self.read_stable(token=token)
        self.assertEqual(view["member_execution"][0]["workspace"]["reason_codes"], ["workspace_not_authorized"])
        self.assertIsNone(view["member_execution"][0]["session"]["has_checkpoint"])
        engine.apply_decision(decision(engine, [{"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a3"}]), "m1", "a1")
        view = self.read_stable(token=token)
        self.assertIsNone(view["member_execution"][1]["session"]["id"])
        self.assertFalse(view["member_execution"][1]["session"]["has_checkpoint"])

    def test_http_legacy_unconfigured_read_does_not_create_observation_tables(self):
        before = self.digest()
        for name in ("a", "b"):
            view = self.read_stable(name)
            self.assertTrue(all(m["workspace"]["mode"] == "virtual_only" for m in view["member_execution"]))
            self.assertTrue(all(m["session"]["id"] is None for m in view["member_execution"]))
            with self.engines[name].read_transaction() as cx:
                tables = {r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertNotIn("agent_sessions", tables)
                self.assertNotIn("workspace_grant", tables)
        self.assertEqual(before, self.digest())
