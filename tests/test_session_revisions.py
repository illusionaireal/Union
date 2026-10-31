"""Actual SDK/checkpoints with loopback model replies; no live provider or Docker."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from langgraph.checkpoint.sqlite import SqliteSaver

from ai_union import workspace
from ai_union.engine import Engine, Rejected
from ai_union.harness import HarnessExecutor
from ai_union.model_api import resolve_connection
from ai_union.runner import run
from tests import test_harness, test_workspace_harness
from tests.support import decision
from tests.test_agent_conversation import tool


class SessionRevisionTests(unittest.TestCase):
    setUp = test_harness.HarnessTests.setUp
    command = test_harness.HarnessTests.command
    configure = test_harness.HarnessTests.configure
    bind = test_harness.HarnessTests.bind
    replies = test_harness.HarnessTests.replies
    executor = test_harness.HarnessTests.executor
    ready = test_workspace_harness.WorkspaceHarnessTests.ready

    def fresh(self):
        return HarnessExecutor(self.e, resolve_connection(self.e))

    def row(self, sid):
        with self.e.read_transaction() as cx:
            return dict(cx.execute("SELECT * FROM agent_sessions WHERE id=?", (sid,)).fetchone())

    def session_rows(self):
        with self.e.read_transaction() as cx:
            return [tuple(r) for r in cx.execute("SELECT * FROM agent_sessions ORDER BY id")]

    def checkpoint(self, sid):
        with sqlite3.connect(self.e.root / "harness" / "checkpoints.sqlite3") as cx:
            value = SqliteSaver(cx).get_tuple({"configurable": {"thread_id": sid, "checkpoint_ns": ""}})
            self.assertIsNotNone(value)
            # Latest checkpoints can contain only a delta; persisted history
            # includes the messages/files that the graph reconstructs on resume.
            return list(SqliteSaver(cx).list({"configurable": {"thread_id": sid, "checkpoint_ns": ""}}))

    def history(self, sid):
        row = self.row(sid)
        with sqlite3.connect(self.e.root / "harness" / "checkpoints.sqlite3") as cx:
            checkpoints = cx.execute("SELECT * FROM checkpoints WHERE thread_id=? ORDER BY checkpoint_ns,checkpoint_id", (sid,)).fetchall()
            writes = cx.execute("SELECT * FROM writes WHERE thread_id=? ORDER BY checkpoint_ns,checkpoint_id,task_id,idx", (sid,)).fetchall()
        run_ids = {row["last_run_id"]} | {r["run_id"] for r in workspace.receipts(self.e)}
        previous_runs = [r for r in self.e.runs() if r["id"] in run_ids]
        return row, previous_runs, checkpoints, writes

    def seed(self):
        executor, directory = self.ready()
        self.canary = "PRIVATE_OLD_SESSION_DRAFT"
        self.replies(tool(workspace.TOOL, {"command": "fixture command"}))
        with patch.object(workspace, "run_container", return_value={"exit_code": 0, "output": "Container double only"}) as sandbox:
            self.assertEqual(run(self.e, executor, 1)[0]["action"], "progress")
        sandbox.assert_called_once()
        self.assertEqual(len(workspace.receipts(self.e)), 1)
        self.old_receipts = workspace.receipts(self.e)
        self.replies(tool("write_file", {"file_path": "/private-draft.md", "content": self.canary}))
        self.assertEqual(run(self.e, executor, 1)[0]["action"], "progress")
        sid = executor.session_id
        self.assertEqual(self.row(sid)["status"], "paused")
        self.assertEqual(self.e.runs()[-1]["status"], "continued")
        self.assertIn(self.canary, json.dumps(self.checkpoint(sid), default=str))
        self.e = Engine(self.e.root)  # Resume against persisted state, not the old graph.
        return sid, directory

    def binding(self):
        work = next(w for w in self.e.state()["work"].values() if w["status"] == "pending" and not w["dependencies"])
        state = self.e.state()
        return {"work": work["id"], "work_version": work["version"], "member": work["member_id"],
                "assignment": work["assignment_id"], "charter": state["charter_version"], "policy": state["policy_version"],
                "connection": resolve_connection(self.e)["revision"], "workspace": workspace.binding(self.e)["revision"]}

    def changed_session(self, sid, old_history):
        calls = self.e.status()["budget"]["calls_reserved"]
        requests = len(self.provider.requests)
        receipts = workspace.receipts(self.e)
        executor = self.fresh()
        self.replies({"role": "assistant", "content": "Fixture delivery under current binding."})
        with patch.object(workspace, "run_container", side_effect=AssertionError("No container authorized by this test")):
            result = run(self.e, executor, 1)
        self.assertEqual(result[0]["action"], "work", result)
        self.assertNotEqual(executor.session_id, sid)
        self.assertNotEqual(self.row(executor.session_id)["task_key"], old_history[0]["task_key"])
        self.assertEqual(self.row(executor.session_id)["status"], "completed")
        self.assertNotIn(self.canary, json.dumps(self.provider.requests[-1]["body"]))
        self.assertNotIn(self.canary, json.dumps(self.checkpoint(executor.session_id), default=str))
        self.assertEqual(self.history(sid), old_history)
        self.assertEqual(workspace.receipts(self.e), receipts)
        self.assertEqual(self.e.status()["budget"]["calls_reserved"], calls + 1)
        self.assertEqual(len(self.provider.requests), requests + 1)
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)
        return executor

    def test_unchanged_binding_resumes_actual_sdk_thread_and_private_draft(self):
        sid, _ = self.seed()
        before = self.binding()
        executor = self.fresh()
        self.replies(tool("read_file", {"file_path": "/private-draft.md"}))
        result = run(self.e, executor, 1)
        self.assertEqual(result[0]["action"], "progress", result)
        self.assertEqual(executor.session_id, sid)
        self.assertEqual(self.binding(), before)
        self.assertIn(self.canary, json.dumps(self.provider.requests[-1]["body"]))
        self.assertIn(self.canary, json.dumps(self.checkpoint(sid), default=str))

    def test_connection_revision_starts_new_sdk_thread_and_preserves_history(self):
        sid, _ = self.seed()
        before, history = self.binding(), self.history(sid)
        self.assertEqual(self.configure()["status"], "succeeded")
        self.assertEqual(self.binding(), before | {"connection": before["connection"] + 1})
        executor = self.changed_session(sid, history)
        self.assertEqual(executor.metadata["connection_revision"], before["connection"] + 1)

    def test_workspace_revision_starts_new_sdk_thread_and_preserves_history(self):
        sid, _ = self.seed()
        before, history = self.binding(), self.history(sid)
        grant = workspace.binding(self.e)
        workspace.configure(self.e, (self.e.root / "board.key").read_text(), grant["config"], "Fixture revision only")
        self.assertEqual(self.binding(), before | {"workspace": before["workspace"] + 1})
        self.changed_session(sid, history)

    def test_formal_handoff_starts_new_sdk_thread_without_previous_members_draft(self):
        sid, _ = self.seed()
        before, history = self.binding(), self.history(sid)
        work = self.e.state()["work"][before["work"]]
        member = next(m for m in self.e.state()["members"] if m != before["member"])
        self.e.apply_decision(decision(self.e, [{"op": "handoff", "position_id": work["position_id"],
            "member_id": member, "assignment_id": "fixture-handoff"}]), before["member"], before["assignment"])
        self.assertEqual(self.binding(), before | {"member": member, "assignment": "fixture-handoff", "work_version": before["work_version"] + 1})
        self.assertFalse(self.e.state()["assignments"][before["assignment"]]["active"])
        self.changed_session(sid, history)
        self.assertEqual(self.e.runs()[-1]["package"]["member_id"], member)

    def test_disabled_connection_rejected_by_fresh_locked_factory_without_consumption(self):
        sid, _ = self.seed()
        self.assertEqual(self.configure(self.config | {"enabled": False})["status"], "succeeded")
        history = self.history(sid)
        before = self.e.runs(), self.e.status()["budget"], len(self.provider.requests), self.session_rows()
        with self.assertRaises(Rejected):
            run(self.e, self.fresh, 1)
        self.assertEqual((self.e.runs(), self.e.status()["budget"], len(self.provider.requests), self.session_rows()), before)
        self.assertEqual(self.history(sid), history)

    def test_disabled_workspace_not_offered_and_forged_sdk_call_never_runs_container(self):
        sid, _ = self.seed()
        history = self.history(sid)
        workspace.disable(self.e, (self.e.root / "board.key").read_text(), "Fixture host revocation")
        calls, requests = self.e.status()["budget"]["calls_reserved"], len(self.provider.requests)
        self.replies(tool(workspace.TOOL, {"command": "must not execute"}))
        with patch.object(workspace, "run_container") as sandbox:
            result = run(self.e, self.fresh, 1)
        sandbox.assert_not_called()
        self.assertEqual(result[0]["action"], "blocked", result)
        self.assertEqual(result[0]["failure"]["code"], "api_tool_arguments")
        offered = {t["function"]["name"] for t in self.provider.requests[-1]["body"]["tools"]}
        self.assertNotIn(workspace.TOOL, offered)
        self.assertEqual(workspace.receipts(self.e), self.old_receipts)
        self.assertEqual(self.e.state()["artifacts"], {})
        self.assertEqual(self.history(sid), history)
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)

        self.assertEqual(self.e.status()["budget"]["calls_reserved"], calls + 1)
        self.assertEqual(len(self.provider.requests), requests + 1)

    def test_inflight_position_revocation_rechecked_before_sdk_workspace_tool(self):
        sid, _ = self.seed()
        history, before = self.history(sid), self.binding()
        calls, requests = self.e.status()["budget"]["calls_reserved"], len(self.provider.requests)
        self.replies(tool(workspace.TOOL, {"command": "must not execute after revocation"}))
        reply = self.provider.override

        def revoke(package):
            state = self.e.state()
            position = state["positions"][state["work"][before["work"]]["position_id"]]
            self.e.apply_decision(decision(self.e, [{"op": "update_position", "position_id": position["id"],
                "title": position["title"], "mandate": position["mandate"],
                "permissions": [p for p in position["permissions"] if p != workspace.TOOL]}]), before["member"], before["assignment"])
            return reply(package)

        self.provider.override = revoke
        executor = self.fresh()
        with patch.object(workspace, "run_container") as sandbox:
            result = run(self.e, executor, 1)
        sandbox.assert_not_called()
        self.assertEqual(result[0]["action"], "blocked", result)
        self.assertEqual(result[0]["failure"]["code"], "api_tool_arguments")
        self.assertIn(workspace.TOOL, {t["function"]["name"] for t in self.provider.requests[-1]["body"]["tools"]})
        self.assertEqual(workspace.receipts(self.e), self.old_receipts)
        self.assertEqual(self.e.state()["artifacts"], {})
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)
        self.assertEqual(self.e.runs()[-1]["status"], "continued")
        self.assertEqual(self.row(sid)["task_key"], history[0]["task_key"])
        self.assertIn("章程或岗位未授权工作区工具", "\n".join(executor.tool_errors))
        self.assertEqual(self.e.status()["budget"]["calls_reserved"], calls + 1)
        self.assertEqual(len(self.provider.requests), requests + 1)
