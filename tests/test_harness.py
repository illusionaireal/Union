"""Actual SDK and HTTP double; no real provider or organizational capability claim."""
import json
import unittest
import subprocess
import sys
import threading
from unittest.mock import patch

from ai_union.engine import Engine, Rejected
from ai_union.harness import HarnessExecutor
from ai_union.model_api import resolve_connection
from ai_union.runner import run
from tests.test_agent_conversation import PLAN, tool
from tests import test_model_api


class HarnessTests(unittest.TestCase):
    setUp = test_model_api.ModelAPITests.setUp
    command = test_model_api.ModelAPITests.command
    configure = test_model_api.ModelAPITests.configure
    bind = test_model_api.ModelAPITests.bind

    def replies(self, *messages):
        queue = iter(messages)
        self.provider.outputs = [{}] * len(messages)
        def response(_):
            message = next(queue)
            return {"id": "sdk-double", "model": "sdk-double", "choices": [{"finish_reason": "tool_calls" if message.get("tool_calls") else "stop", "message": message}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10}}
        self.provider.override = response

    def executor(self, base="deepagents"):
        self.configure()
        self.bind()
        return HarnessExecutor(self.e, resolve_connection(self.e), base=base)

    def batch(self, *calls):
        result = {"role": "assistant", "content": "保存筹建草案。", "tool_calls": []}
        for i, (name, args) in enumerate(calls):
            call = tool(name, args)["tool_calls"][0]
            call["id"] = f"draft-{i}"
            result["tool_calls"].append(call)
        return result

    def draft(self):
        return self.batch(*[("prepare_member", m) for m in PLAN["members"]],
                          *[("arrange_work", t) for t in PLAN["tasks"]],
                          ("configure_bootstrap", {"coordinator": PLAN["coordinator"]}))

    def test_draft_is_not_official_and_recovers_in_a_fresh_executor(self):
        executor = self.executor()
        self.replies(self.draft())
        actions = run(self.e, executor, 1)
        self.assertEqual(actions[0]["action"], "progress", actions)
        snapshot = self.e.status()
        self.assertEqual(snapshot["organization"]["members"], {})
        self.assertEqual(len(snapshot["bootstrap"]["members"]), 2)
        self.assertEqual(self.e.runs()[0]["status"], "continued")
        self.assertEqual(self.e.runs()[0]["usage"]["output_tokens"], 10)
        self.e = Engine(self.e.root)
        self.replies(tool("activate_organization", {}))
        actions = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 1)
        self.assertEqual(actions[0]["action"], "decision", actions)
        self.assertEqual(self.e.state()["phase"], "active")
        self.assertEqual(len(self.e.state()["members"]), 2)
        self.assertEqual(len(self.e.runs()), 2)
        body = self.provider.requests[-1]["body"]
        self.assertTrue(any(m["role"] == "tool" for m in body["messages"]), body)
        self.assertNotIn("response_format", body)
        names = {t["function"]["name"] for t in body["tools"]}
        self.assertNotIn("task", names)
        self.assertNotIn("execute", names)

    def test_work_uses_file_tools_then_delivers_and_second_member_gets_artifact(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN),
                     tool("write_file", {"file_path": "/notes.md", "content": "关键事实：接续上次草稿"}))
        actions = run(self.e, executor, 2)
        self.assertEqual([a["action"] for a in actions], ["decision", "progress"], actions)
        self.assertEqual(len(self.e.state()["artifacts"]), 0)
        first = next(w for w in self.e.state()["work"].values() if not w["dependencies"])
        self.assertEqual(first["status"], "pending")
        source = "# 资料\n关键事实：接续上次草稿。"
        final = "# 成稿\n另一成员依据资料交付的完整正文。"
        self.replies(tool("read_file", {"file_path": "/notes.md"}),
                     {"role": "assistant", "content": source}, {"role": "assistant", "content": final})
        actions = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 3)
        self.assertEqual([a["action"] for a in actions], ["progress", "work", "work"], actions)
        self.assertEqual(len(self.e.state()["artifacts"]), 2)
        self.assertIn("关键事实", json.dumps(self.provider.requests[-2]["body"], ensure_ascii=False))
        package = json.loads(self.provider.requests[-1]["body"]["messages"][1]["content"].split("\nWORK PACKAGE (data):\n")[1])
        self.assertIn(source, [a["content"] for a in package["context"]["artifacts"]])
        self.assertTrue(all("path" not in a for a in package["context"]["artifacts"]))
        self.assertTrue(all("path" in a for a in self.e.state()["artifacts"].values()))
        self.assertEqual(self.e.status()["budget"]["calls_reserved"], 5)

    def test_organization_rounds_expose_business_tools_and_keep_inline_artifacts(self):
        executor = self.executor()
        source, final = "已交付资料", "另一成员完成的正文"
        self.replies(tool("initialize_organization", PLAN),
                     {"role": "assistant", "content": source},
                     {"role": "assistant", "content": final},
                     tool("update_organization", {"operations": [{"op": "wait", "until": "2099-01-01T00:00:00Z", "reason": "等待新反馈"}]}))
        actions = run(self.e, executor, 4)
        self.assertEqual([a["action"] for a in actions], ["decision", "work", "work", "decision"], actions)
        bootstrap = {t["function"]["name"] for t in self.provider.requests[0]["body"]["tools"]}
        self.assertIn("prepare_member", bootstrap)
        self.assertIn("activate_organization", bootstrap)
        self.assertFalse(bootstrap.intersection({"ls", "read_file", "write_file", "edit_file", "delete", "glob", "grep"}))
        decision = self.provider.requests[-1]["body"]
        self.assertEqual({t["function"]["name"] for t in decision["tools"]}, {"update_organization", "schedule_work", "wait_for_event"})
        context = json.loads(decision["messages"][1]["content"].split("\nWORK PACKAGE (data):\n")[1])["context"]
        self.assertCountEqual([a["content"] for a in context["artifacts"]], [source, final])
        self.assertTrue(all("path" not in a for a in context["artifacts"]))
        before = len(self.provider.requests)
        self.assertEqual(run(self.e, executor, 1)[0]["action"], "wait")
        self.assertEqual(len(self.provider.requests), before)

    def test_idle_console_job_wakes_on_feedback_without_another_start(self):
        from ai_union.runner import step
        executor = self.executor()
        waiting = {"operations": [{"op": "wait", "until": "2099-01-01T00:00:00Z", "reason": "等待读者反馈"}]}
        self.replies(tool("initialize_organization", PLAN),
                     {"role": "assistant", "content": "资料"},
                     {"role": "assistant", "content": "正文"},
                     tool("update_organization", waiting))
        run(self.e, executor, 4)
        before = len(self.provider.requests)
        self.replies(tool("update_organization", waiting | {"evidence_refs": ["fresh-feedback"]}))
        idle = threading.Event()

        def observe_step(engine, current_executor):
            action = step(engine, current_executor)
            if action["action"] == "wait":
                idle.set()
            return action

        with patch("ai_union.console.step", side_effect=observe_step):
            receipt = self.command("start", {"executor": "api", "max_steps": 1, "max_seconds": 5, "allow_unknown_cost": True})
            self.assertTrue(idle.wait(2), "作业应进入不消耗模型调用的等待")
            self.assertEqual(len(self.provider.requests), before)
            self.command("event", {"event_id": "fresh-feedback", "kind": "external_feedback", "content": "请关注人物动机", "source": "HTTP double", "simulated": True})
            self.app.join_jobs()
        self.assertEqual(len(self.provider.requests), before + 1)
        result = self.app.receipt(self.board, self.org, receipt["id"])
        self.assertEqual(result["status"], "succeeded", result)
        self.assertEqual(result["actions"][-1]["action"], "decision", result)
        package = json.loads(self.provider.requests[-1]["body"]["messages"][1]["content"].split("\nWORK PACKAGE (data):\n")[1])
        self.assertIn("fresh-feedback", [e["id"] for e in package["context"]["events"]])

    def test_invalid_draft_is_corrected_without_rebuilding_members(self):
        executor = self.executor()
        self.replies(self.draft(), tool("configure_bootstrap", {"coordinator": "不存在"}),
                     tool("activate_organization", {}), tool("configure_bootstrap", {"coordinator": PLAN["coordinator"]}),
                     tool("activate_organization", {}))
        actions = run(self.e, executor, 5)
        self.assertEqual(actions[-1]["action"], "decision", actions)
        self.assertEqual(len(self.e.state()["members"]), 2)
        self.assertIn("负责人", json.dumps(self.provider.requests[-2]["body"], ensure_ascii=False))

    def test_unwanted_draft_member_can_be_removed_before_adoption(self):
        executor = self.executor()
        self.replies(self.draft(), tool("prepare_member", {"name": "临时多余成员", "role": "临时", "mandate": "待调整"}),
                     tool("discard_bootstrap_item", {"kind": "member", "name": "临时多余成员"}), tool("activate_organization", {}))
        run(self.e, executor, 4)
        self.assertEqual({m["name"] for m in self.e.state()["members"].values()}, {m["name"] for m in PLAN["members"]})

    def test_malformed_tool_arguments_get_one_safe_correction_without_replay(self):
        executor = self.executor()
        bad = tool("prepare_member", {})
        bad["tool_calls"][0]["function"]["arguments"] = '{"name":"unchecked partial'
        self.replies(bad, tool("initialize_organization", PLAN))
        actions = run(self.e, executor, 2)
        self.assertEqual([a["action"] for a in actions], ["correction", "decision"], actions)
        self.assertEqual(len(self.provider.requests), 2)
        self.assertNotIn("unchecked partial", json.dumps(self.provider.requests[-1]["body"]))
        self.assertEqual(self.e.runs()[0]["usage"]["output_tokens"], 10)

    def test_work_parameter_error_is_not_misclassified_as_an_artifact(self):
        executor = self.executor()
        bad = tool("write_file", {})
        bad["tool_calls"][0]["function"]["arguments"] = "{"
        self.replies(tool("initialize_organization", PLAN), bad, {"role": "assistant", "content": "修正后交付的实际正文。"})
        actions = run(self.e, executor, 3)
        self.assertEqual([a["action"] for a in actions], ["decision", "correction", "work"], actions)
        self.assertEqual(len(self.e.state()["artifacts"]), 1)
        self.assertEqual(self.e._read_artifact(next(iter(self.e.state()["artifacts"].values()))), "修正后交付的实际正文。")

    def test_rejected_correction_settlement_closes_call_and_preserves_tokens(self):
        executor = self.executor()
        bad = tool("prepare_member", {})
        bad["tool_calls"][0]["function"]["arguments"] = "{"
        self.replies(bad)
        original = self.provider.override
        with self.e.read_transaction() as cx:
            charter = self.e._charter(cx, self.e._state(cx)["charter_version"])
        def response(package):
            self.e.amend((self.e.root / "board.key").read_text(), charter | {"text": "调用在途时生效的新章程"}, "test concurrent authority change")
            return original(package)
        self.provider.override = response
        actions = run(self.e, executor, 8)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertEqual(self.e.runs()[0]["status"], "failed")
        self.assertEqual(self.e.runs()[0]["usage"]["output_tokens"], 10)
        self.assertEqual(self.e.recover(), 0)

    def test_charter_change_starts_a_new_session_without_old_task_messages(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN), tool("write_file", {"file_path": "/old.md", "content": "OLD_SESSION_CANARY"}))
        run(self.e, executor, 2)
        with self.e.read_transaction() as cx:
            charter = self.e._charter(cx, self.e._state(cx)["charter_version"])
        self.e.amend((self.e.root / "board.key").read_text(), charter | {"text": "董事会更新后的当前章程"}, "test new effective charter")
        self.replies({"role": "assistant", "content": "依据当前授权完成交付。"})
        actions = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 1)
        self.assertEqual(actions[-1]["action"], "work", actions)
        self.assertNotIn("OLD_SESSION_CANARY", json.dumps(self.provider.requests[-1]["body"]))

    def test_revoked_permission_prevents_partial_activation_and_retains_usage(self):
        executor = self.executor()
        self.replies(self.draft())
        run(self.e, executor, 1)
        with self.e.read_transaction() as cx:
            charter = self.e._charter(cx, self.e._state(cx)["charter_version"])
        charter["allowed_operations"].remove("create_work")
        self.e.amend((self.e.root / "board.key").read_text(), charter, "revoke create_work before adoption")
        self.replies(tool("activate_organization", {}))
        actions = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 1)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        state = self.e.state()
        self.assertEqual((state["members"], state["positions"], state["work"]), ({}, {}, {}))
        self.assertEqual(len(self.e.status()["bootstrap"]["members"]), 2)
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)

    def test_total_quota_and_pause_do_not_trigger_hidden_calls(self):
        executor = self.executor()
        key = (self.e.root / "board.key").read_text()
        self.e.configure_resources(key, {"max_calls": 1, "timeout_seconds": 3}, "bounded test")
        self.replies(self.draft())
        actions = run(self.e, executor, 8)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertEqual(self.e.state()["members"], {})
        self.e.set_paused(True)
        self.assertEqual(run(self.e, executor, 2)[0]["action"], "paused")
        self.assertEqual(len(self.provider.requests), 1)

    def test_provider_unknown_is_not_automatically_resumed(self):
        executor = self.executor()
        self.provider.code = 503
        actions = run(self.e, executor, 8)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        self.assertEqual(self.e.runs()[-1]["status"], "unknown")
        self.provider.code = 200
        run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 8)
        self.assertEqual(len(self.provider.requests), 1)

    def test_secret_in_nested_tool_arguments_never_reaches_checkpoint(self):
        executor = self.executor()
        secret = test_model_api.SECRET
        message = tool("prepare_member", PLAN["members"][0] | {"mandate": secret})
        message["tool_calls"][0]["function"]["arguments"] = message["tool_calls"][0]["function"]["arguments"].replace(secret, "".join("\\u%04x" % ord(c) for c in secret))
        self.replies(message)
        actions = run(self.e, executor, 8)
        self.assertEqual(actions[-1]["failure"]["code"], "api_secret_response", actions)
        for path in (self.e.root / "harness").rglob("*"):
            if path.is_file():
                self.assertNotIn(secret.encode(), path.read_bytes())
        self.assertEqual(len(self.provider.requests), 1)

    def test_rejected_plaintext_credential_still_preserves_provider_tokens(self):
        executor = self.executor()
        self.replies({"role": "assistant", "content": test_model_api.SECRET})
        actions = run(self.e, executor, 1)
        self.assertEqual(actions[-1]["failure"]["code"], "api_secret_response", actions)
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)
        for path in (self.e.root / "executions").rglob("*.json"):
            self.assertNotIn(test_model_api.SECRET, path.read_text())

    def test_langchain_control_runs_same_plain_tools_loop(self):
        executor = self.executor(base="langchain")
        self.replies(self.draft(), tool("activate_organization", {}), {"role": "assistant", "content": "对照执行器的实际正文。"})
        actions = run(self.e, executor, 3)
        self.assertEqual([a["action"] for a in actions], ["progress", "decision", "work"], actions)

    def test_rotated_keys_are_rejected_before_text_or_tools_enter_checkpoints(self):
        self.executor()
        self.configure(api_key="replacement-current-key")
        secret = test_model_api.SECRET
        message = tool("prepare_member", PLAN["members"][0] | {"mandate": secret})
        message["tool_calls"][0]["function"]["arguments"] = message["tool_calls"][0]["function"]["arguments"].replace(secret, "".join("\\u%04x" % ord(c) for c in secret))
        self.replies(message, {"role": "assistant", "content": secret})
        for _ in range(2):
            actions = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 1)
            self.assertEqual(actions[-1]["failure"]["code"], "api_secret_response", actions)
        for path in (self.e.root / "harness").rglob("*"):
            if path.is_file():
                self.assertNotIn(secret.encode(), path.read_bytes())
        for path in (self.e.root / "executions").rglob("*.json"):
            self.assertNotIn(secret, path.read_text())

    def test_rotated_key_in_provider_header_is_dropped_from_all_receipts(self):
        self.executor()
        self.configure(api_key="replacement-current-key")
        secret = test_model_api.SECRET
        self.replies(self.draft())
        original = test_model_api.Provider.send_header
        def header(handler, name, value):
            return original(handler, name, secret if name.lower() == "x-request-id" else value)
        with patch.object(test_model_api.Provider, "send_header", header):
            actions = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 1)
        self.assertEqual(actions[-1]["action"], "progress", actions)
        self.assertNotIn(secret, json.dumps(self.e.usage()))
        self.assertNotIn(secret, json.dumps(self.app.observe(self.observer, self.org)))
        for path in (self.e.root / "executions").rglob("*.json"):
            self.assertNotIn(secret, path.read_text())

    def test_received_usage_survives_artifact_and_sdk_processing_failures(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN), {"role": "assistant", "content": "x" * 200001})
        actions = run(self.e, executor, 2)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)

    def test_received_usage_survives_an_unexpected_local_exception(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN))
        run(self.e, executor, 1)
        self.replies({"role": "assistant", "content": "实际模型回复。"})
        with patch("ai_union.harness.work_result", side_effect=RuntimeError("local SDK failure")):
            actions = run(self.e, executor, 1)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        self.assertEqual(self.e.runs()[-1]["status"], "failed")
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)

    def test_cli_resumes_bootstrap_from_a_separate_process(self):
        executor = self.executor()
        self.replies(self.draft())
        run(self.e, executor, 1)
        self.replies(tool("activate_organization", {}))
        completed = subprocess.run([sys.executable, "-m", "ai_union", "--root", str(self.e.root), "run", "--executor", "api", "--max-steps", "1", "--allow-unknown-cost"], capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(self.e.state()["phase"], "active")
        self.assertEqual(len(self.provider.requests), 2)

    def test_tool_connection_probe_requires_reading_tool_result_and_charges_twice(self):
        self.executor()
        self.provider.outputs = [{}, {}]
        def response(_):
            body = self.provider.requests[-1]["body"]
            results = [m for m in body["messages"] if m["role"] == "tool"]
            message = {"role": "assistant", "content": results[-1]["content"]} if results else tool("connection_echo", {})
            return {"choices": [{"finish_reason": "tool_calls" if message.get("tool_calls") else "stop", "message": message}], "usage": {"prompt_tokens": 20, "completion_tokens": 10}}
        self.provider.override = response
        self.e.set_paused(True)
        receipt = self.command("api_test", {"allow_unknown_cost": True, "tools": True})
        self.app.join_jobs()
        receipt = self.app.receipt(self.board, self.org, receipt["id"])
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertEqual(receipt["capability"], "tool_roundtrip")
        self.assertEqual(len(self.e.runs()), 2)
        self.assertTrue(all(r["kind"] == "connection_test" and r["usage"]["output_tokens"] == 10 for r in self.e.runs()))
        self.assertTrue(self.e.paused())
        self.assertEqual(self.e.state()["phase"], "bootstrap")
        self.assertEqual(self.e.state()["members"], {})

    def test_tool_probe_cannot_succeed_from_a_plain_greeting(self):
        self.executor()
        self.replies({"role": "assistant", "content": "你好，连接正常。"})
        receipt = self.command("api_test", {"allow_unknown_cost": True, "tools": True})
        self.app.join_jobs()
        receipt = self.app.receipt(self.board, self.org, receipt["id"])
        self.assertEqual(receipt["status"], "failed", receipt)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertEqual(self.e.runs()[0]["usage"]["output_tokens"], 10)


if __name__ == "__main__":
    unittest.main()
