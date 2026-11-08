"""Bounded real acceptance for S03: one work, at most two calls, synthetic material.

Skipped unless the host provides both its private modeld configuration and an
explicit bounded-test opt-in, so an ordinary test run never spends real tokens.
Defaults cap this test at two calls and 1024 output tokens per call with synthetic
material. They do not authorize a new run. The separate interruption opt-in adds
up to one call; enabling both can consume three calls in total.
"""
import copy
import hashlib
import json
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from ai_union.model_service import ModelServiceClient
from ai_union.work_transport import ModeldWorkTransport, modeld_factory
from tests.model_access_support import ModelAccessCase

CONFIG = os.environ.get("UNION_MODELD_CONFIG")
MODEL = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
MAX_OUTPUT = min(int(os.environ.get("UNION_REAL_MAX_OUTPUT", "1024")), 1024)
SKIP = (not CONFIG) or os.environ.get("UNION_REAL_BOUNDED_ACCEPTANCE") != "1"



def acceptance_problems(work, receipt, max_output):
    """Reject acceptance evidence that does not prove a real exchange (review finding on #22)."""
    problems = []
    if receipt.get("status") != "succeeded":
        problems.append("回执不是成功状态")
    if int(receipt.get("turns") or 0) < 1:
        problems.append("没有任何模型回合")
    used = int((work.get("budget") or {}).get("used") or 0)
    if used < 1:
        problems.append("没有发生任何模型调用")
    usage = work.get("usage") or {}
    if int(usage.get("input_tokens") or 0) <= 0 or int(usage.get("output_tokens") or 0) <= 0:
        problems.append("用量为 0，不能证明真实交换")
    if int(usage.get("output_tokens") or 0) > max_output * max(used, 1):
        problems.append("输出 tokens 超过授权上限")
    if (work.get("cost_status") or "") != "unknown":
        problems.append("费用必须如实记为 unknown")
    calls = work.get("tool_calls") or []
    reads = [call for call in calls if call.get("tool") == "read_document"]
    if not reads:
        problems.append("只列目录不算读取：必须有一次 read_document 证明模型真的读了资料正文")
    if any(not call.get("sha256") or not call.get("bytes") for call in reads):
        problems.append("读取资料的调用缺少摘要")
    if not (work.get("results") or []):
        problems.append("没有产出任何成果")
    if used != 2 or receipt.get("turns") != 2 or receipt.get("result") is not True:
        problems.append("需要读取后第二次模型调用及候选成果，不能以单回合摘要验收")
    if work.get("budget", {}).get("max_calls") != 2 or work.get("budget", {}).get("reserved") != 0:
        problems.append("调用预算不是已结算的两次有界调用")
    evidence = work.get("_acceptance") or {}
    observed = evidence.get("calls") or []
    steps = work.get("steps") or []
    ids = [item.get("run_id") for item in observed]
    if (len(observed) != 2 or len(set(ids)) != 2 or not all(ids)
            or ids != [step.get("model_request_id") for step in steps]
            or any(step.get("status") != "used" for step in steps)):
        problems.append("缺少两次原持久请求与实际模型调用的对应证据")
    total = {"input_tokens": 0, "output_tokens": 0}
    for index, call in enumerate(observed):
        measured = call.get("usage") or {}
        if (any(type(measured.get(key)) is not int or measured[key] < 0 for key in total)
                or measured.get("output_tokens", 0) > max_output):
            problems.append("逐次用量未知或超过单次输出上限")
            continue
        for key in total:
            total[key] += measured[key]
        if index >= len(steps) or steps[index].get("usage") != {key: measured[key] for key in total}:
            problems.append("原步进与观察到的模型用量不一致")
    if total != usage:
        problems.append("逐次用量与汇总用量不一致")
    document = evidence.get("document")
    raw = document.encode("utf-8") if isinstance(document, str) else b""
    digest = hashlib.sha256(raw).hexdigest()
    matching_reads = [call for call in reads if call.get("sha256") == digest
                      and call.get("bytes") == len(raw) and call.get("arguments", {}).get("path") == "brief.md"]
    messages = observed[1].get("messages", []) if len(observed) == 2 else []
    paired = set()
    delivered = False
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                try:
                    arguments = json.loads(function.get("arguments", "null"))
                except (ValueError, TypeError):
                    continue
                if function.get("name") == "read_document" and arguments == {"path": "brief.md"}:
                    paired.add(call.get("id"))
        if message.get("role") == "tool" and message.get("tool_call_id") in paired:
            try:
                value = json.loads(message.get("content", "null"))
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and all(value.get(k) == v for k, v in {
                    "path": "brief.md", "content": document, "sha256": digest, "bytes": len(raw)}.items()):
                delivered = True
    if not raw or not matching_reads or not delivered:
        problems.append("未证明授权资料正文及匹配工具回执进入下一轮模型")
    downloads = evidence.get("downloads") or []
    for result in work.get("results") or []:
        downloaded = next((item for item in downloads if item.get("result", {}).get("id") == result.get("id")), {})
        body = downloaded.get("content")
        nonce = evidence.get("nonce")
        if (not isinstance(body, str) or not body or not nonce or nonce not in body
                or downloaded.get("organization_id") != evidence.get("organization_id")
                or downloaded.get("result") != result
                or result.get("sha256") != hashlib.sha256(body.encode()).hexdigest()
                or result.get("bytes") != len(body.encode())
                or not any(call.get("step_ref") in result.get("sources", []) for call in matching_reads)):
            problems.append("成果下载正文、资料校验码、摘要、来源或范围不一致")
    return problems


class RealChannelCase(ModelAccessCase):
    """Host wiring shared by the gated real tests; never carries its own test methods."""
    def setUp(self):
        super().setUp()
        # the shared fixture replaces ModelServiceClient with a double; a real run must not use it
        try:
            self.provider_patch.stop()
        except RuntimeError:
            pass

    def allow_reading(self):
        charter = copy.deepcopy(self.read()["au"]["charter"])
        for tool in ("read_document", "list_documents"):
            if tool not in charter["allowed_tools"]:
                charter["allowed_tools"].append(tool)
        self.success("amend_charter", {"charter": charter,
                                       "reason": "Authorize bounded read-only listing for the acceptance work"})

    def grant(self, au_id):
        client = ModelServiceClient(CONFIG)
        accounts = client.call("GET", "/v1/accounts", admin=True).get("accounts") or []
        self.assertTrue(accounts, "宿主 modeld 没有可用账号；请先完成设备授权")
        account = os.environ.get("UNION_REAL_ACCOUNT")
        if not account:
            self.skipTest("需要 UNION_REAL_ACCOUNT 明确指定账号；不得默认第一个账号")
        selected = next((item for item in accounts if (item.get("id") or item.get("account_ref")) == account), None)
        if selected is None:
            self.skipTest("UNION_REAL_ACCOUNT 不在 modeld 的可用账号列表内")
        self.assertEqual(selected.get("provider"), "opencode-go", "本验收只能使用明确选中的 OpenCode Go 账号")
        grant_id = "grant-" + uuid.uuid4().hex[:12]
        created = client.call("POST", "/v1/grants", {"id": grant_id, "au_id": au_id, "account_ref": account,
                                                     "model_ids": [MODEL]}, admin=True)
        return created["id"], created["revision"]

    def connection(self, grant_ref, grant_revision):
        return {"connection_id": "connection-a", "expected_revision": 0, "name": "Go acceptance",
                "profile": "modeld_grant", "model": MODEL, "max_output_tokens": MAX_OUTPUT,
                "grant_ref": grant_ref, "grant_revision": grant_revision}


@unittest.skipIf(SKIP, "real acceptance needs UNION_MODELD_CONFIG and UNION_REAL_BOUNDED_ACCEPTANCE=1 (up to two calls)")
class RealBoundedAcceptanceTests(RealChannelCase):
    def test_one_work_uses_at_most_two_calls_and_reports_usage_without_cost(self):
        au_id = self.prepare()
        grant_ref, grant_revision = self.grant(au_id)
        receipt, _request = self.model_success("save_connection", self.connection(grant_ref, grant_revision))
        self.wait_operation(receipt["operation_id"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                              "enabled": True, "make_default": True})
        self.allow_reading()

        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        nonce = "public-" + uuid.uuid4().hex
        document = "# 合成资料\n\n合成公开测试资料；请在三行概览里保留资料校验码：" + nonce + "\n"
        (directory / "brief.md").write_bytes(document.encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")

        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")
        data = {"work_id": "work-real", "title": "合成概览", "member_name": "资料整理 Agent",
                "goal": "先 read_document 读取 brief.md，然后用三行中文概览作为最终回答，保留资料校验码，不要再调用工具", "member_id": "m-real", "binding_id": "b-real",
                "mandate_id": "ma-real", "definition_id": "d-real", "connection_id": "connection-a",
                "expected_revision": connection["revision"], "materials_root": "project-docs", "max_calls": 2,
                "tools": ["read_document", "list_documents"], "reason": "有界真实验收"}
        status, value, _ = self.request("/api/v1/work/commands",
                                        {"id": str(uuid.uuid4()), "organization_id": au_id,
                                         "base_version": self.read()["au"]["version"],
                                         "kind": "start_work", "data": data})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        status, started, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "start_attempt", "data": {"work_id": "work-real"}})
        self.assertEqual(started["receipt"]["status"], "succeeded", started)

        observed = []
        original_chat = ModeldWorkTransport.chat

        def observe_chat(channel, package, messages, tools):
            item = {"run_id": package["run_id"], "messages": copy.deepcopy(messages)}
            observed.append(item)
            answer, usage = original_chat(channel, package, messages, tools)
            item["usage"] = copy.deepcopy(usage)
            return answer, usage

        self.app.work.transport_factory = modeld_factory(CONFIG)
        self.enterContext(patch.object(ModeldWorkTransport, "chat", observe_chat))
        status, looped, _ = self.request("/api/v1/work/commands",
                                         {"id": str(uuid.uuid4()), "organization_id": au_id,
                                          "base_version": self.read()["au"]["version"],
                                          "kind": "run_loop", "data": {"work_id": "work-real"}})
        self.assertEqual(status, 200, looped)
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        downloads = []
        for result in work["results"]:
            code, downloaded, _ = self.request("/api/v1/work/results?organization_id=" + au_id + "&id=" + result["id"])
            self.assertEqual(code, 200, "candidate download failed")
            downloads.append(downloaded)
        work["_acceptance"] = {"calls": observed, "document": document, "nonce": nonce,
                               "organization_id": au_id, "downloads": downloads}
        used = work["budget"]["used"]
        problems = acceptance_problems(work, looped["receipt"], MAX_OUTPUT)
        print("acceptance summary:", json.dumps({
            "receipt": {k: looped["receipt"].get(k) for k in ("status", "message", "turns", "tool_calls", "result", "usage")},
            "budget": work["budget"], "usage": work["usage"],
            "tool_calls": [call.get("tool") for call in work["tool_calls"]],
            "results": len(work["results"]), "problems": problems}, ensure_ascii=False))
        self.assertEqual(problems, [], "acceptance evidence must prove a real exchange")
        self.assertLessEqual(used, 2, work["budget"])
        print("real acceptance:", json.dumps({
            "model": MODEL, "receipt": {key: looped["receipt"].get(key) for key in
                                        ("status", "message", "turns", "tool_calls", "result", "usage", "cost_status")},
            "budget": work["budget"], "usage": work["usage"], "cost_status": work["cost_status"],
            "tool_calls": [{"tool": call["tool"], "sha256": call.get("sha256"), "bytes": call.get("bytes")}
                           for call in work["tool_calls"]],
            "results": [{"id": item["id"], "status": item["status"]} for item in work["results"]],
        }, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
