"""Behavioral tests with HTTP doubles. No live model or provider claims."""
import copy
import json
import unittest

from ai_union.agent_protocol import compile_tool, tools_for
from ai_union.engine import Rejected, instant, now
from ai_union.model_api import APIExecutor, resolve_connection
from ai_union.runner import run
from tests import test_model_api
from tests.test_model_api import SECRET


PLAN = {
    "strategy": "先整理资料，再由另一成员完成交付。",
    "members": [
        {"name": "林策", "role": "资料与协调", "mandate": "安排工作并整理资料"},
        {"name": "江墨", "role": "内容交付", "mandate": "根据资料撰写成稿"},
    ],
    "coordinator": "林策",
    # Deliberately reversed: people should not have to topologically sort a plan.
    "tasks": [
        {"title": "撰写成稿", "instruction": "根据资料完成正文", "owner": "江墨", "dependencies": ["整理资料"]},
        {"title": "整理资料", "instruction": "交付可用资料", "owner": "林策"},
    ],
}


def tool(name, arguments):
    return {"role": "assistant", "content": "我会先安排分工，然后开始工作。", "tool_calls": [
        {"id": "call-1", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}]}


class AgentConversationTests(unittest.TestCase):
    setUp = test_model_api.ModelAPITests.setUp
    command = test_model_api.ModelAPITests.command
    configure = test_model_api.ModelAPITests.configure
    bind = test_model_api.ModelAPITests.bind
    probe = test_model_api.ModelAPITests.probe

    def replies(self, *messages):
        queue = iter(messages)
        self.provider.outputs = [{"ok": True}] * len(messages)
        def response(_package):
            message = next(queue)
            return {"id": "local-conversation", "model": "local-double", "choices": [
                {"finish_reason": "tool_calls" if message.get("tool_calls") else "stop", "message": message}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10}}
        self.provider.override = response

    def executor(self):
        self.configure()
        self.bind()
        return APIExecutor(self.e.root, resolve_connection(self.e))

    def test_probe_is_plain_chat_even_for_saved_legacy_schema_connection(self):
        self.configure()
        self.replies({"role": "assistant", "content": "你好，连接正常。"})
        self.assertEqual(self.probe()["status"], "succeeded")
        body = self.provider.requests[0]["body"]
        self.assertNotIn("response_format", body)
        self.assertNotIn("tools", body)
        self.assertNotIn("schema", json.dumps(body).lower())

    def test_init_and_two_members_deliver_plain_markdown_without_schema(self):
        executor = self.executor()
        source = "# 资料\n这里是另一位成员需要使用的原始资料。"
        final = "# 正文\n根据资料完成的正文，不需要 JSON 包装。"
        self.replies(tool("initialize_organization", PLAN),
                     {"role": "assistant", "content": source}, {"role": "assistant", "content": final})
        actions = run(self.e, executor, 3)
        self.assertEqual([a["action"] for a in actions], ["decision", "work", "work"], actions)
        state = self.e.state()
        self.assertEqual(len(state["members"]), 2)
        self.assertEqual(len({w["member_id"] for w in state["work"].values()}), 2)
        contents = [self.e._read_artifact(a) for a in state["artifacts"].values()]
        self.assertCountEqual(contents, [source, final])
        context = json.loads(self.provider.requests[2]["body"]["messages"][1]["content"].split("\nWORK PACKAGE (data):\n")[1])["context"]
        self.assertIn(source, [a["content"] for a in context["artifacts"]])
        self.assertTrue(all("path" not in a for a in context["artifacts"]))
        self.assertTrue(all("path" in a for a in state["artifacts"].values()))
        for request in self.provider.requests:
            self.assertNotIn("response_format", request["body"])
            self.assertNotIn("context_manifest", json.dumps(request["body"]))
        self.assertEqual(self.e.status()["budget"]["calls_reserved"], 3)

    def test_host_owns_versions_and_rejects_stale_plan_without_partial_organization(self):
        package = self.e.begin_decision("api")
        result = compile_tool(package, "initialize_organization", PLAN)
        self.assertEqual(result["base_state_version"], package["context_manifest"]["state_version"])
        self.e.configure_resources((self.e.root / "board.key").read_text(), {"max_calls": 15, "timeout_seconds": 30}, "changed while thinking")
        with self.assertRaises(Rejected):
            self.e.finish_decision(package["run_id"], result, {})
        self.assertEqual(self.e.state()["members"], {})

    def followup_package(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN),
                     {"role": "assistant", "content": "供另一成员使用的资料正文。"},
                     {"role": "assistant", "content": "首次成稿。"})
        run(self.e, executor, 3)
        return executor, self.e.begin_decision("api")

    def test_named_followup_commits_real_cross_member_artifact_dependency(self):
        executor, package = self.followup_package()
        context = package["context"]
        owner = PLAN["members"][1]["name"]
        member = next(m for m in context["members"].values() if m["name"] == owner)
        source = next(w for w in context["work"].values() if w["member_id"] != member["id"])
        artifact = source["artifact_ids"][0]
        proposal = compile_tool(package, "schedule_work", {"owner": owner, "title": "根据资料完成后续成稿", "instruction": "使用已有资料交付完整正文", "dependencies": [artifact]})
        by_id = compile_tool(package, "schedule_work", {"owner": member["id"], "title": "根据资料完成后续成稿", "instruction": "使用已有资料交付完整正文", "dependencies": [artifact]})
        self.assertEqual(proposal, by_id)
        self.e.finish_decision(package["run_id"], proposal, {})
        created = self.e.state()["work"][package["run_id"] + "-w0"]
        self.assertEqual(created["member_id"], member["id"])
        self.assertEqual(created["dependencies"], [source["id"]])
        self.assertIn(source["id"], proposal["evidence_refs"])
        self.replies({"role": "assistant", "content": "依据前人成果完成后续正文。"})
        self.assertEqual(run(self.e, executor, 1)[0]["action"], "work")
        supplied = json.loads(self.provider.requests[-1]["body"]["messages"][1]["content"].split("\nWORK PACKAGE (data):\n")[1])["context"]
        self.assertIn(artifact, [a["id"] for a in supplied["artifacts"]])
        self.assertIn("供另一成员使用的资料正文。", [a["content"] for a in supplied["artifacts"]])
        self.assertTrue(all("path" not in a for a in supplied["artifacts"]))

    def test_named_followup_rejects_unknown_ambiguous_and_duplicate_references(self):
        _, package = self.followup_package()
        baseline = self.e.state()
        valid = {"owner": PLAN["members"][0]["name"], "title": "新任务", "instruction": "交付正文"}
        for args in [valid | {"owner": "不存在"}, valid | {"dependencies": ["不存在"]}, valid | {"title": PLAN["tasks"][0]["title"]}]:
            with self.subTest(args=args), self.assertRaises(Rejected):
                compile_tool(package, "schedule_work", args)
        ambiguous = copy.deepcopy(package)
        ambiguous["context"]["members"]["duplicate"] = {"id": "duplicate", "name": valid["owner"]}
        with self.assertRaises(Rejected):
            compile_tool(ambiguous, "schedule_work", valid)
        self.assertEqual(self.e.state(), baseline)

    def test_natural_tools_preserve_host_identity_and_current_permission_checks(self):
        _, package = self.followup_package()
        valid = {"owner": PLAN["members"][0]["name"], "title": "新任务", "instruction": "交付正文"}
        for field, value in [("actor", "board"), ("position_id", "spoof"), ("id", "spoof"), ("base_state_version", 999)]:
            with self.subTest(field=field), self.assertRaises((Rejected, ValueError)):
                compile_tool(package, "schedule_work", valid | {field: value})
        revoked = copy.deepcopy(package)
        revoked["context"]["charter"]["allowed_operations"] = [op for op in revoked["context"]["charter"]["allowed_operations"] if op not in ("create_work", "wait")]
        offered = {t["function"]["name"] for t in tools_for(revoked)}
        self.assertNotIn("schedule_work", offered)
        self.assertNotIn("wait_for_event", offered)
        with self.assertRaises(Rejected):
            compile_tool(revoked, "schedule_work", valid)
        proposal = compile_tool(package, "schedule_work", valid)
        key = (self.e.root / "board.key").read_text()
        self.e.amend(key, revoked["context"]["charter"], "撤销在途安排工作权限")
        with self.assertRaises(Rejected):
            self.e.finish_decision(package["run_id"], proposal, {})
        self.assertEqual(len(self.e.state()["work"]), 2)

    def test_relative_wait_uses_host_time_and_idle_does_not_call_model(self):
        executor, package = self.followup_package()
        for seconds in (0, -1, 86401, True):
            with self.subTest(seconds=seconds), self.assertRaises((Rejected, ValueError)):
                compile_tool(package, "wait_for_event", {"reason": "等待反馈", "review_after_seconds": seconds})
        before = instant(now())
        proposal = compile_tool(package, "wait_for_event", {"reason": "等待反馈", "review_after_seconds": 60})
        self.assertGreater(instant(proposal["operations"][0]["until"]), before)
        self.e.finish_decision(package["run_id"], proposal, {})
        calls = len(self.provider.requests)
        self.assertEqual(run(self.e, executor, 1)[0]["action"], "wait")
        self.assertEqual(len(self.provider.requests), calls)

    def test_tool_proposal_cannot_supply_authority_or_versions(self):
        package = self.e.begin_decision("api")
        for key, value in (("actor", "board"), ("base_state_version", 900), ("permissions", ["shell"])):
            with self.subTest(key=key), self.assertRaises((Rejected, ValueError)):
                compile_tool(package, "initialize_organization", PLAN | {key: value})
        with self.assertRaises((Rejected, ValueError)):
            compile_tool(package, "run_shell", {"command": "echo unauthorized"})
        self.assertEqual(self.e.state()["members"], {})

    def test_duplicate_names_and_dependency_cycles_are_rejected_before_commit(self):
        package = self.e.begin_decision("api")
        bad_names = copy.deepcopy(PLAN)
        bad_names["members"][1]["name"] = "林策"
        cycle = copy.deepcopy(PLAN)
        cycle["tasks"][1]["dependencies"] = ["撰写成稿"]
        for plan in (bad_names, cycle, PLAN | {"coordinator": "不存在"}):
            with self.assertRaises((Rejected, ValueError)):
                compile_tool(package, "initialize_organization", plan)
        self.assertEqual(self.e.state()["members"], {})

    def test_plain_planning_reply_gets_one_bounded_followup_and_receipt_per_call(self):
        executor = self.executor()
        self.replies({"role": "assistant", "content": "先安排资料和写作两个职责。"}, tool("initialize_organization", PLAN))
        actions = run(self.e, executor, 2)
        self.assertEqual([a["action"] for a in actions], ["correction", "decision"], actions)
        self.assertEqual(len(self.provider.requests), 2)
        self.assertEqual(len(self.e.usage()), 2)
        messages = self.provider.requests[1]["body"]["messages"]
        self.assertTrue(any(m["role"] == "assistant" and "两个职责" in (m.get("content") or "") for m in messages))
        self.assertEqual(self.e.state()["phase"], "active")

    def test_invalid_tool_gets_specific_feedback_and_can_be_corrected(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN | {"coordinator": "不存在"}), tool("initialize_organization", PLAN))
        actions = run(self.e, executor, 2)
        self.assertEqual(actions[-1]["action"], "decision", actions)
        messages = self.provider.requests[1]["body"]["messages"]
        self.assertTrue(any(m["role"] == "tool" and "负责人" in m["content"] for m in messages))
        self.assertEqual(len(self.e.state()["members"]), 2)

    def test_bad_proposal_cannot_loop_or_exceed_authorized_steps(self):
        for steps, expected in ((1, 1), (8, 2)):
            # Each subcase needs a separate organization/reservation history.
            with self.subTest(steps=steps):
                executor = self.executor()
                self.replies(*[{"role": "assistant", "content": "我稍后再安排。"}] * expected)
                before = len(self.provider.requests)
                actions = run(self.e, executor, steps)
                self.assertEqual(len(self.provider.requests) - before, expected)
                self.assertEqual(actions[-1]["action"], "blocked", actions)

    def test_full_endpoint_is_normalized_and_not_appended_twice(self):
        self.configure(self.config | {"base_url": self.config["base_url"] + "/chat/completions"})
        self.replies({"role": "assistant", "content": "OK"})
        self.assertEqual(self.probe()["status"], "succeeded")
        self.assertEqual(self.provider.requests[0]["path"], "/v1/chat/completions")

    def test_work_can_report_blocked_without_fabricating_an_artifact(self):
        executor = self.executor()
        self.replies(tool("initialize_organization", PLAN), tool("report_blocked", {"reason": "缺少用户要求的原始资料"}))
        run(self.e, executor, 2)
        self.assertEqual(len(self.e.state()["artifacts"]), 0)
        blocked = [w for w in self.e.state()["work"].values() if w["status"] == "blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertIn("缺少", blocked[0]["summary"])

    def test_console_does_not_report_uncommitted_plan_as_success_when_step_budget_ends(self):
        self.executor()
        self.replies({"role": "assistant", "content": "我将安排两名成员。"})
        started = self.command("start", {"executor": "api", "max_steps": 1, "allow_unknown_cost": True})
        self.app.join_jobs()
        receipt = self.app.receipt(self.board, self.org, started["id"])
        self.assertEqual(receipt["status"], "blocked", receipt)
        self.assertEqual(self.e.state()["phase"], "bootstrap")
        self.assertEqual(self.e.state()["members"], {})
        self.assertEqual(len(self.provider.requests), 1)

    def test_escaped_secret_inside_tool_arguments_cannot_enter_state_or_feedback(self):
        executor = self.executor()
        message = tool("initialize_organization", PLAN | {"strategy": SECRET})
        message["tool_calls"][0]["function"]["arguments"] = message["tool_calls"][0]["function"]["arguments"].replace(SECRET, "".join("\\u%04x" % ord(c) for c in SECRET))
        self.replies(message)
        actions = run(self.e, executor, 8)
        self.assertEqual(actions[-1]["failure"]["code"], "api_secret_response", actions)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertFalse(executor.correction)
        self.assertNotIn(SECRET, json.dumps([self.e.state(), self.e.runs(), self.app.observe(self.board, self.org)]))
        self.assertEqual(self.e.runs()[0]["usage"]["output_tokens"], 10)
        for path in (self.e.root / "executions").rglob("*.json"):
            self.assertNotIn(SECRET, path.read_text())

    def test_malformed_arguments_get_fixed_feedback_without_replaying_unchecked_text(self):
        executor = self.executor()
        bad = tool("initialize_organization", PLAN)
        invalid = '{"members": "unchecked text'
        bad["tool_calls"][0]["function"]["arguments"] = invalid
        self.replies(bad, tool("initialize_organization", PLAN))
        actions = run(self.e, executor, 2)
        self.assertEqual(actions[-1]["action"], "decision", actions)
        self.assertEqual(len(self.provider.requests), 2)
        self.assertEqual(len(self.e.usage()), 2)
        self.assertNotIn("unchecked text", json.dumps(self.provider.requests[1]["body"]))
        self.assertIn("完整 JSON", self.provider.requests[1]["body"]["messages"][-1]["content"])


if __name__ == "__main__":
    unittest.main()
