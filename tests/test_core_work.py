"""S03.1: one goal becomes an answerable AI work under effective local governance."""
import copy
import hashlib
import os
import tempfile
import json
import uuid
from pathlib import Path

from ai_union.errors import Rejected
from tests.model_access_support import ModelAccessCase
from tests.test_core_creation import creation


def work_data(**changes):
    data = {"work_id": "work-overview", "title": "项目概览", "member_name": "资料整理 Agent",
            "goal": "阅读我授权的资料目录，写一份带文件引用的项目概览",
            "member_id": "member-ai-overview", "binding_id": "binding-ai-overview",
            "mandate_id": "mandate-ai-overview", "definition_id": "definition-ai-overview",
            "connection_id": "connection-a", "expected_revision": 1,
            "materials_root": "project-docs", "max_calls": 4, "tools": ["read_document"],
            "reason": "用户要求以授权资料形成第一份可阅读成果"}
    data.update(changes)
    return data


class FakeTransport:
    """Stands in for the host model channel; records what it was asked to run."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, package, messages, tools):
        self.calls.append({"package": package, "messages": messages, "tools": tools})
        answer = self.responses.pop(0)
        return answer if isinstance(answer, tuple) else (answer, {})


class CoreWorkTests(ModelAccessCase):
    def adopt_default(self):
        return self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                                     "enabled": True, "make_default": True})

    def work_command(self, au_id, kind, data, *, token="current", version=None, request_id=None):
        if version is None:
            version = self.request("/api/v1/aus/" + au_id, token=token)[1]["au"]["version"]
        request = {"id": request_id or str(uuid.uuid4()), "organization_id": au_id,
                   "base_version": version, "kind": kind, "data": copy.deepcopy(data)}
        status, value, _ = self.request("/api/v1/work/commands", request, token)
        return status, value, request

    def work(self, au_id=None, data=None, **kwargs):
        return self.work_command(au_id or self.au_id, "start_work", data or work_data(), **kwargs)

    def works(self, au_id=None, token="current"):
        status, value, _ = self.request("/api/v1/work?organization_id=" + (au_id or self.au_id), token=token)
        self.assertEqual(status, 200, value)
        return value

    def second_au(self, request_id="v1-create-second"):
        receipt = self.create(creation(request_id))
        return receipt["organization_id"]

    def test_start_work_binds_ai_member_definition_binding_work_and_mandate_in_one_command(self):
        self.saved()
        default = self.adopt_default()[0]
        before = self.read()["au"]["version"]
        status, value, request = self.work()
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "rejected", receipt)
        self.assertIn("章程", receipt["message"])
        self.assertEqual(self.read()["au"]["version"], before)

        self.allow_documents()
        before = self.read()["au"]["version"]
        status, value, request = self.work()
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertEqual(receipt["work_id"], "work-overview")
        self.assertEqual(receipt["version"], before + 1)
        self.assertEqual(self.read()["au"]["version"], before + 1)

        card = self.works()
        self.assertEqual(card["protocol"], "core.work.v1")
        self.assertTrue(card["access"]["can_start"])
        self.assertEqual(len(card["works"]), 1)
        work = card["works"][0]
        self.assertEqual((work["id"], work["status"], work["max_calls"], work["materials_root"]),
                         ("work-overview", "pending", 4, "project-docs"))
        self.assertEqual(work["responsible"], {"member_id": "member-ai-overview", "name": "资料整理 Agent",
                                              "binding_id": "binding-ai-overview", "duty": "项目概览"})
        self.assertEqual(work["definition"], {"id": "definition-ai-overview", "version": 1,
                                              "connection_id": "connection-a", "model": "model-a",
                                              "tools": ["read_document"]})
        self.assertEqual(work["mandate"], {"id": "mandate-ai-overview", "version": 1, "actions": ["read_document"], "active": True})
        self.assertEqual(card["capabilities"]["execution"], "not_started")

        replay_status, replay, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(replay_status, 200, replay)
        self.assertEqual(replay["receipt"], receipt)
        self.assertEqual(len(self.works()["works"]), 1)
        self.assertEqual(self.read()["au"]["version"], before + 1)
        connection = next(item for item in self.models()["connections"] if item["id"] == "connection-a")
        self.assertTrue(connection["is_default"])

        state = self.read()["au"]
        self.assertNotIn("/", str(state.get("work_runtime", {}).get("works", {})), "host paths never enter AU state")

    def test_start_work_requires_effective_governance_and_the_current_governor(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        token, _ = self.participant("outsider")
        status, value, _ = self.work(token=token, version=self.read()["au"]["version"])
        self.assertEqual(status, 403, value)
        self.assertEqual(value.get("code"), "not_authorized")

        other = self.second_au()
        before = self.request("/api/v1/aus/" + other)[1]["au"]["version"]
        status, value, _ = self.work(au_id=other)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("治理", value["receipt"]["message"])
        self.assertEqual(value["receipt"]["version"], before)
        self.assertEqual(self.request("/api/v1/aus/" + other)[1]["au"]["version"], before)
        self.assertEqual(self.works(au_id=other)["works"], [])

    def test_start_work_refuses_unadopted_model_unbounded_calls_paths_and_duplicate_ids(self):
        unknown = self.work(au_id=self.second_au())
        self.assertEqual(unknown[1]["receipt"]["status"], "rejected", unknown[1])

        self.saved()
        self.adopt_default()
        self.allow_documents()
        status, value, _ = self.work(data=work_data(max_calls=13))
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("剩余", value["receipt"]["message"])

        for materials_root in ("/etc/passwd", "C:\\docs", "..\\secrets", "a/b"):
            status, value, _ = self.work(data=work_data(materials_root=materials_root))
            self.assertEqual(value["receipt"]["status"], "rejected", value)
            self.assertIn("资料目录", value["receipt"]["message"])

        status, value, _ = self.work(data=work_data(tools=["workspace_execute"]))
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("工具", value["receipt"]["message"])

        status, value, _ = self.work(data=work_data(connection_id="connection-missing"))
        self.assertEqual(value["receipt"]["status"], "rejected", value)

        status, succeeded, _ = self.work()
        self.assertEqual(status, 200, succeeded)
        self.assertEqual(succeeded["receipt"]["status"], "succeeded", succeeded)
        status, duplicate, _ = self.work()
        self.assertEqual(duplicate["receipt"]["status"], "rejected", duplicate)
        self.assertIn("已存在", duplicate["receipt"]["message"])
        self.assertEqual(len(self.works()["works"]), 1)

    def test_start_work_requires_a_materials_root_when_read_document_is_granted(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        status, value, _ = self.work(data=work_data(materials_root=None))
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("资料目录", value["receipt"]["message"])
        self.assertEqual(self.works()["works"], [])

        artifact = work_data(tools=["produce_artifact"], materials_root=None, work_id="work-artifact",
                             member_id="member-ai-artifact", binding_id="binding-ai-artifact",
                             mandate_id="mandate-ai-artifact", definition_id="definition-ai-artifact")
        status, value, _ = self.work(data=artifact)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(len(self.works()["works"]), 1)

    def test_work_projection_reports_whether_the_host_registered_materials_are_available(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        status, value, _ = self.work()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.works()["works"][0]["materials"],
                         {"reference": "project-docs", "available": False, "documents": 0})

        directory = Path(self.root) / "authorized-docs"
        directory.mkdir()
        (directory / "overview.md").write_bytes("概览\n".encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False), encoding="utf-8")
        materials = self.works()["works"][0]["materials"]
        self.assertEqual((materials["reference"], materials["available"], materials["documents"]),
                         ("project-docs", True, 1))

    def allow_listing(self):
        charter = copy.deepcopy(self.read()["au"]["charter"])
        for tool in ("read_document", "list_documents"):
            if tool not in charter["allowed_tools"]:
                charter["allowed_tools"].append(tool)
        self.success("amend_charter", {"charter": charter,
                                       "reason": "Authorize bounded read-only listing and reading of the registered root"})

    def prepare_materials(self):
        directory = Path(self.root) / "authorized-docs"
        (directory / "nested").mkdir(parents=True, exist_ok=True)
        (directory / "overview.md").write_bytes("# 概览\n".encode("utf-8"))
        (directory / "nested" / "a.md").write_bytes("a 正文\n".encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False), encoding="utf-8")
        return directory

    def work_with_listing(self):
        self.saved()
        self.adopt_default()
        self.allow_listing()
        status, value, _ = self.work(data=work_data(tools=["list_documents", "read_document"]))
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        return value["receipt"]["work_id"]

    def invoke(self, data, **kwargs):
        return self.work_command(self.au_id, "invoke_tool", data, **kwargs)

    def start_attempt(self, work_id="work-overview"):
        status, value, _ = self.work_command(self.au_id, "start_attempt", {"work_id": work_id})
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        return value["receipt"]["attempt"]["id"]

    def test_invoke_tool_records_durable_receipts_for_authorized_documents(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["result"]["documents"], ["nested/a.md", "overview.md"])

        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "read_document",
                                        "arguments": {"path": "nested/a.md"}})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        digest = hashlib.sha256("a 正文\n".encode("utf-8")).hexdigest()
        self.assertEqual(value["receipt"]["result"]["text"], "a 正文\n")
        self.assertEqual(value["receipt"]["result"]["sha256"], digest)

        calls = self.works()["works"][0]["tool_calls"]
        self.assertEqual([(call["tool"], call["step_ref"]) for call in calls],
                         [("list_documents", "work-overview#1"), ("read_document", "work-overview#2")])
        self.assertEqual(calls[1]["sha256"], digest)
        self.assertEqual(calls[1]["bytes"], len("a 正文\n".encode("utf-8")))
        self.assertNotIn(str(Path(self.root)), json.dumps(calls), "host paths never enter AU state")

    def test_invoke_tool_replays_receipts_and_refuses_unscoped_requests(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        status, first, request = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(first["receipt"]["status"], "succeeded", first)
        replay_status, replay, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(replay_status, 200, replay)
        self.assertEqual(replay["receipt"], first["receipt"])
        recorded = len(self.works()["works"][0]["tool_calls"])

        for arguments in ({"path": "../outside/secret.txt"}, {"path": "C:\\Windows\\win.ini"},
                          {"path": "nested"}, {"path": "absent.md"}):
            status, value, _ = self.invoke({"work_id": "work-overview", "tool": "read_document",
                                            "arguments": arguments})
            self.assertEqual(status, 200, value)
            self.assertEqual(value["receipt"]["status"], "rejected", value)

        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "read_document",
                                        "arguments": {"path": ""}})
        self.assertEqual(status, 400, value)
        self.assertEqual(value.get("code"), "invalid_request")

        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "produce_artifact", "arguments": {}})
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("授权", value["receipt"]["message"])

        (Path(self.root) / "document-roots.json").unlink()
        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(len(self.works()["works"][0]["tool_calls"]), recorded)

    def test_tool_calls_require_a_running_execution_attempt(self):
        self.work_with_listing()
        self.prepare_materials()
        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("执行", value["receipt"]["message"])

        attempt_id = self.start_attempt()
        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["tool_call"]["attempt_id"], attempt_id)
        self.assertEqual(self.works()["works"][0]["attempts"][0]["status"], "running")

        status, again, _ = self.work_command(self.au_id, "start_attempt", {"work_id": "work-overview"})
        self.assertEqual(again["receipt"]["status"], "rejected", again)
        self.assertIn("执行", again["receipt"]["message"])

        status, closed, _ = self.work_command(self.au_id, "finish_attempt",
                                              {"work_id": "work-overview", "attempt_id": attempt_id,
                                               "outcome": "delivered", "reason": "本轮只读资料已产出候选"})
        self.assertEqual(closed["receipt"]["status"], "succeeded", closed)
        card = self.works()["works"][0]
        self.assertEqual([(a["id"], a["status"], a["outcome"]) for a in card["attempts"]],
                         [(attempt_id, "closed", "delivered")])
        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("执行", value["receipt"]["message"])

    def test_unknown_attempt_blocks_further_execution_until_it_is_resolved(self):
        self.work_with_listing()
        self.prepare_materials()
        attempt_id = self.start_attempt()
        status, value, _ = self.work_command(self.au_id, "finish_attempt",
                                             {"work_id": "work-overview", "attempt_id": attempt_id,
                                              "outcome": "unknown", "reason": "宿主未取得供应商回执"})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.works()["works"][0]["attempts"][0]["status"], "unknown")

        status, blocked, _ = self.work_command(self.au_id, "start_attempt", {"work_id": "work-overview"})
        self.assertEqual(blocked["receipt"]["status"], "rejected", blocked)
        self.assertIn("未知", blocked["receipt"]["message"])
        status, call, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(call["receipt"]["status"], "rejected", call)
        self.assertIn("未知", call["receipt"]["message"])

        status, resolved, _ = self.work_command(self.au_id, "finish_attempt",
                                                {"work_id": "work-overview", "attempt_id": attempt_id,
                                                 "outcome": "failed", "reason": "核对后确认该次未产生结果"})
        self.assertEqual(resolved["receipt"]["status"], "succeeded", resolved)
        self.assertEqual(self.works()["works"][0]["attempts"][0]["outcome"], "failed")
        self.start_attempt()

    def reserve(self, work_id="work-overview", **kwargs):
        return self.work_command(self.au_id, "reserve_step", {"work_id": work_id}, **kwargs)

    def settle(self, work_id, step_id, status, reason="本轮步进已结算"):
        return self.work_command(self.au_id, "settle_step",
                                 {"work_id": work_id, "step_id": step_id, "status": status, "reason": reason})

    def test_reserve_step_counts_one_call_per_execution_with_purpose_and_attempt(self):
        self.work_with_listing()
        attempt_id = self.start_attempt()
        status, value, _ = self.reserve()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        step = value["receipt"]["step"]
        self.assertEqual((step["step_ref"], step["status"], step["attempt_id"], step["purpose"]),
                         ("work-overview#s1", "reserved", attempt_id, "work_step"))

        card = self.works()["works"][0]
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 1, "used": 0})
        self.assertEqual([(item["step_ref"], item["status"]) for item in card["steps"]],
                         [("work-overview#s1", "reserved")])

        status, value, _ = self.settle("work-overview", "work-overview#s1", "used")
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.works()["works"][0]["budget"], {"max_calls": 4, "reserved": 0, "used": 1})

        status, released, _ = self.reserve()
        self.assertEqual(released["receipt"]["status"], "succeeded", released)
        status, value, _ = self.settle("work-overview", "work-overview#s2", "released")
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.works()["works"][0]["budget"], {"max_calls": 4, "reserved": 0, "used": 1})

    def test_reserve_step_requires_a_running_attempt_and_respects_the_call_cap(self):
        self.work_with_listing()
        status, value, _ = self.reserve()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("执行", value["receipt"]["message"])

        self.start_attempt()
        for _ in range(4):
            status, value, _ = self.reserve()
            self.assertEqual(value["receipt"]["status"], "succeeded", value)
        status, value, _ = self.reserve()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("调用", value["receipt"]["message"])

        status, value, _ = self.settle("work-overview", "work-overview#s4", "unknown", "供应商未回执")
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        card = self.works()["works"][0]
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 4, "used": 0})
        self.assertEqual(card["steps"][-1]["status"], "unknown")
        status, value, _ = self.settle("work-overview", "work-overview#s4", "used")
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("已经结算", value["receipt"]["message"])

    def submit(self, work_id="work-overview", result_id="result-overview", **kwargs):
        data = {"work_id": work_id, "result_id": result_id, "title": "项目概览（第一版）",
                "content": "# 概览\n- 依据 nested/a.md\n", "sources": ["work-overview#1"]}
        data.update(kwargs)
        return self.work_command(self.au_id, "submit_result", data)

    def adopt(self, work_id="work-overview", result_id="result-overview"):
        return self.work_command(self.au_id, "adopt_result", {"work_id": work_id, "result_id": result_id})

    def test_submit_result_records_digest_and_sources_without_publishing_content(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        status, value, _ = self.invoke({"work_id": "work-overview", "tool": "read_document",
                                        "arguments": {"path": "nested/a.md"}})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)

        status, value, _ = self.submit(sources=["work-overview#1"])
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        digest = hashlib.sha256("# 概览\n- 依据 nested/a.md\n".encode("utf-8")).hexdigest()
        self.assertEqual(value["receipt"]["result"]["sha256"], digest)

        card = self.works()["works"][0]
        self.assertEqual([(r["id"], r["status"], r["sha256"]) for r in card["results"]],
                         [("result-overview", "candidate", digest)])
        self.assertNotIn("# 概览", json.dumps(card), "content stays out of the read projection")

        status, again, _ = self.adopt()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(again["receipt"]["status"], "succeeded", again)
        adopted = self.works()["works"][0]["results"][0]
        self.assertEqual((adopted["status"], bool(adopted["adopted_at"])), ("adopted", True))
        status, twice, _ = self.adopt()
        self.assertEqual(twice["receipt"]["status"], "rejected", twice)
        self.assertIn("已经采用", twice["receipt"]["message"])

    def test_submit_result_requires_an_attempt_and_valid_sources(self):
        self.work_with_listing()
        status, value, _ = self.submit()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("执行", value["receipt"]["message"])

        self.start_attempt()
        for sources in (["work-overview#9"], ["other-work#1"], ["work-overview#1", "work-overview#1"]):
            status, value, _ = self.submit(result_id="result-bad", sources=sources)
            self.assertEqual(value["receipt"]["status"], "rejected", value)
        status, value, _ = self.submit(result_id="result-flat", sources=[], content="")
        self.assertEqual(status, 400, value)

        status, value, _ = self.reserve()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        status, value, _ = self.submit(sources=["work-overview#s1"])
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        status, duplicate, _ = self.submit(sources=["work-overview#s1"])
        self.assertEqual(duplicate["receipt"]["status"], "rejected", duplicate)
        self.assertIn("已存在", duplicate["receipt"]["message"])

    def result_content(self, result_id="result-overview", au_id=None, token="current"):
        query = "/api/v1/work/results?organization_id=" + (au_id or self.au_id) + "&id=" + result_id
        return self.request(query, token=token)

    def test_result_content_is_readable_and_digest_verified(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.reserve()
        self.submit(sources=["work-overview#s1"])
        digest = hashlib.sha256("# 概览\n- 依据 nested/a.md\n".encode("utf-8")).hexdigest()

        status, value, _ = self.result_content()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["protocol"], "core.work.v1")
        self.assertEqual(value["content"], "# 概览\n- 依据 nested/a.md\n")
        self.assertEqual(value["result"]["sha256"], digest)
        self.assertEqual(value["result"]["sources"], ["work-overview#s1"])
        self.assertEqual(value["result"]["status"], "candidate")

        status, value, _ = self.result_content("result-absent")
        self.assertEqual(status, 400, value)
        self.assertNotIn("content", value)

        other = self.second_au()
        status, value, _ = self.result_content(au_id=other)
        self.assertIn(status, (400, 403), value)
        self.assertNotIn("content", value)

    def second_work(self, materials_root="project-docs", work_id="work-second"):
        data = work_data(tools=["list_documents"], materials_root=materials_root, work_id=work_id,
                         member_id=work_id + "-member", binding_id=work_id + "-binding",
                         mandate_id=work_id + "-mandate", definition_id=work_id + "-definition")
        return self.work(data=data)

    def test_shared_materials_root_allows_only_one_open_execution_at_a_time(self):
        self.work_with_listing()
        self.second_work()
        self.start_attempt("work-overview")

        status, blocked, _ = self.work_command(self.au_id, "start_attempt", {"work_id": "work-second"})
        self.assertEqual(blocked["receipt"]["status"], "rejected", blocked)
        self.assertIn("资料目录", blocked["receipt"]["message"])

        status, closed, _ = self.work_command(self.au_id, "finish_attempt",
                                              {"work_id": "work-overview", "attempt_id": "work-overview#a1",
                                               "outcome": "delivered", "reason": "本轮完成"})
        self.assertEqual(closed["receipt"]["status"], "succeeded", closed)
        status, allowed, _ = self.work_command(self.au_id, "start_attempt", {"work_id": "work-second"})
        self.assertEqual(allowed["receipt"]["status"], "succeeded", allowed)

        self.second_work(materials_root="other-docs", work_id="work-third")
        status, independent, _ = self.work_command(self.au_id, "start_attempt", {"work_id": "work-third"})
        self.assertEqual(independent["receipt"]["status"], "succeeded", independent)

    def deliver(self, work_id="work-overview", result_id="result-overview"):
        return self.work_command(self.au_id, "deliver_work", {"work_id": work_id, "result_id": result_id})

    def test_work_completes_only_with_an_adopted_result_and_then_stops_accepting_actions(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.reserve()
        self.submit(sources=["work-overview#s1"])

        status, blocked, _ = self.deliver()
        self.assertEqual(blocked["receipt"]["status"], "rejected", blocked)
        self.assertIn("采用", blocked["receipt"]["message"])
        self.assertEqual(self.works()["works"][0]["status"], "pending")

        self.adopt()
        status, midway, _ = self.deliver()
        self.assertEqual(midway["receipt"]["status"], "rejected", midway)
        self.assertIn("执行", midway["receipt"]["message"])

        self.work_command(self.au_id, "finish_attempt", {"work_id": "work-overview",
                                                         "attempt_id": "work-overview#a1",
                                                         "outcome": "delivered", "reason": "成果已采用"})
        status, done, _ = self.deliver()
        self.assertEqual(status, 200, done)
        self.assertEqual(done["receipt"]["status"], "succeeded", done)
        card = self.works()["works"][0]
        self.assertEqual(card["status"], "delivered")
        self.assertTrue(card["delivered_at"])

        status, twice, _ = self.deliver()
        self.assertEqual(twice["receipt"]["status"], "rejected", twice)
        self.assertIn("已经完成", twice["receipt"]["message"])
        status, after, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
        self.assertEqual(after["receipt"]["status"], "rejected", after)

    def test_an_attempt_records_its_host_instance_and_reads_as_stale_after_a_restart(self):
        self.work_with_listing()
        attempt_id = self.start_attempt()
        card = self.works()["works"][0]
        recorded = card["attempts"][0]
        self.assertEqual(recorded["host_instance"], self.app.instance)
        self.assertIs(recorded["stale"], False)

        previous = self.app.instance
        self.app.instance = "service-restarted"
        try:
            card = self.works()["works"][0]
            restarted = card["attempts"][0]
            self.assertEqual(restarted["id"], attempt_id)
            self.assertEqual(restarted["host_instance"], previous)
            self.assertIs(restarted["stale"], True, "an attempt from a previous service instance is stale")
            status, value, _ = self.invoke({"work_id": "work-overview", "tool": "list_documents", "arguments": {}})
            self.assertEqual(value["receipt"]["status"], "rejected", value)
            self.assertIn("实例", value["receipt"]["message"])
            status, reserved, _ = self.reserve()
            self.assertEqual(reserved["receipt"]["status"], "rejected", reserved)
        finally:
            self.app.instance = previous

        self.work_command(self.au_id, "finish_attempt",
                          {"work_id": "work-overview", "attempt_id": attempt_id, "outcome": "unknown",
                           "reason": "服务重启后核对：该次执行没有结果"})
        card = self.works()["works"][0]
        self.assertEqual(card["attempts"][0]["status"], "unknown")
        self.assertIs(card["attempts"][0]["stale"], False, "a settled attempt is no longer stale")

    def test_each_attempt_reports_how_much_it_already_produced(self):
        self.work_with_listing()
        self.prepare_materials()
        first = self.start_attempt()
        self.reserve()
        self.invoke({"work_id": "work-overview", "tool": "read_document", "arguments": {"path": "nested/a.md"}})
        attempt = self.works()["works"][0]["attempts"][0]
        self.assertEqual((attempt["steps"], attempt["tool_calls"]), (1, 1))

        self.work_command(self.au_id, "finish_attempt",
                          {"work_id": "work-overview", "attempt_id": first, "outcome": "failed",
                           "reason": "服务重启后核对：该次执行没有产生可交付结果"})
        second = self.start_attempt()
        self.assertNotEqual(first, second)
        card = self.works()["works"][0]
        old, current = card["attempts"][0], card["attempts"][1]
        self.assertEqual((old["steps"], old["tool_calls"]), (1, 1), "a settled attempt keeps its own counts")
        self.assertEqual((current["steps"], current["tool_calls"]), (0, 0))

    def with_transport(self, *responses):
        self.app.work.transport = FakeTransport(list(responses))
        return self.app.work.transport

    def work_step(self, work_id="work-overview"):
        return self.work_command(self.au_id, "run_step", {"work_id": work_id})

    def test_run_step_executes_the_tool_the_model_asks_for_and_records_a_receipt(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        transport = self.with_transport(
            {"content": None, "tool_calls": [{"id": "call-1", "type": "function",
             "function": {"name": "read_document", "arguments": "{\"path\": \"nested/a.md\"}"}}]},
            {},
        )

        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["tool_calls"], 1)
        self.assertEqual(transport.calls[0]["package"]["work_id"], "work-overview")
        self.assertTrue(any(tool["function"]["name"] == "read_document" for tool in transport.calls[0]["tools"]))

        card = self.works()["works"][0]
        self.assertEqual([c["tool"] for c in card["tool_calls"]], ["read_document"])
        self.assertEqual(card["tool_calls"][0]["sha256"],
                         hashlib.sha256("a 正文\n".encode("utf-8")).hexdigest())
        self.assertEqual(card["steps"][0]["status"], "used")
        self.assertEqual(card["steps"][0]["purpose"], "work_step")

    def test_run_step_stores_a_candidate_result_when_the_model_answers(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.with_transport({"content": "# 概览\n- 依据 nested/a.md\n", "tool_calls": []}, {})

        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["tool_calls"], 0)
        card = self.works()["works"][0]
        self.assertEqual(len(card["results"]), 1)
        self.assertEqual(card["results"][0]["status"], "candidate")
        self.assertEqual(card["results"][0]["sha256"],
                         hashlib.sha256("# 概览\n- 依据 nested/a.md\n".encode("utf-8")).hexdigest())
        self.assertEqual(card["steps"][0]["status"], "used")

    def test_run_step_requires_a_configured_host_transport(self):
        self.work_with_listing()
        self.start_attempt()
        self.app.work.transport = None
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("通道", value["receipt"]["message"])

    def run_loop(self, work_id="work-overview"):
        return self.work_command(self.au_id, "run_loop", {"work_id": work_id})

    def test_run_loop_keeps_calling_the_model_until_it_answers(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.with_transport(
            {"content": None, "tool_calls": [{"id": "c1", "type": "function",
             "function": {"name": "read_document", "arguments": "{\"path\": \"nested/a.md\"}"}}]},
            {"content": "# 概览\n- 依据 nested/a.md\n", "tool_calls": []},
        )

        status, value, _ = self.run_loop()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["turns"], 2)
        self.assertIs(value["receipt"]["result"], True)
        card = self.works()["works"][0]
        self.assertEqual([step["status"] for step in card["steps"]], ["used", "used"])
        self.assertEqual(len(card["tool_calls"]), 1)
        self.assertEqual(len(card["results"]), 1)

    def test_run_loop_stops_at_the_turn_cap_when_the_model_never_answers(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        call = {"content": None, "tool_calls": [{"id": "c1", "type": "function",
                "function": {"name": "list_documents", "arguments": "{}"}}]}
        self.with_transport(call, call, call)

        status, value, request = self.run_loop()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["turns"], 3)
        self.assertIs(value["receipt"]["result"], False)
        card = self.works()["works"][0]
        self.assertEqual(len(card["steps"]), 3)
        self.assertEqual(len(card["results"]), 0)
        replay_status, again, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(replay_status, 200, again)
        self.assertEqual(again["receipt"], value["receipt"], "the same loop request returns its original receipt")

    def test_run_loop_requires_the_host_transport(self):
        self.work_with_listing()
        self.start_attempt()
        self.app.work.transport = None
        status, value, _ = self.run_loop()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("通道", value["receipt"]["message"])

    def test_run_step_records_model_usage_and_keeps_cost_unknown(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.with_transport(({"content": "# 概览\n", "tool_calls": []},
                             {"input_tokens": 12, "output_tokens": 5}))

        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        card = self.works()["works"][0]
        step = card["steps"][0]
        self.assertEqual(step["usage"], {"input_tokens": 12, "output_tokens": 5})
        self.assertEqual(step["cost_status"], "unknown", "an unverified call never records a definite cost")

    def test_run_loop_accumulates_usage_across_turns(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        call = ({"content": None, "tool_calls": [{"id": "c1", "type": "function",
                 "function": {"name": "list_documents", "arguments": "{}"}}]}, {"input_tokens": 10, "output_tokens": 2})
        answer = ({"content": "# 概览\n", "tool_calls": []}, {"input_tokens": 20, "output_tokens": 8})
        self.with_transport(call, answer)

        status, value, _ = self.run_loop()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["usage"], {"input_tokens": 30, "output_tokens": 10})
        self.assertEqual(value["receipt"]["cost_status"], "unknown")

    def failing_transport(self, error=TimeoutError("provider did not answer")):
        class Failing:
            def chat(self, package, messages, tools):
                raise error
        self.app.work.transport = Failing()
        return self.app.work.transport

    def test_a_channel_failure_keeps_a_reserved_step_and_reports_unknown(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.failing_transport()

        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["model_outcome"], "unknown")
        self.assertIn("核对", value["receipt"]["message"])

        card = self.works()["works"][0]
        self.assertEqual([(s["status"], s["cost_status"]) for s in card["steps"]], [("unknown", "unknown")])
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 1, "used": 0},
                         "an unconfirmed call keeps its reservation")

        reconciled = self.work_command(self.au_id, "reconcile_step",
                                       {"work_id": "work-overview", "step_id": card["steps"][0]["step_ref"],
                                        "status": "released", "reason": "宿主确认供应商未收到请求"})
        self.assertEqual(reconciled[1]["receipt"]["status"], "succeeded", reconciled[1])
        card = self.works()["works"][0]
        self.assertEqual(card["steps"][0]["status"], "released")
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 0, "used": 0})

    def test_run_loop_stops_when_a_turn_leaves_the_model_outcome_unknown(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.failing_transport()

        status, value, _ = self.run_loop()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "unknown", value)
        self.assertEqual(value["receipt"]["model_outcome"], "unknown")
        self.assertEqual(value["receipt"]["turns"], 0)
        card = self.works()["works"][0]
        self.assertEqual([s["status"] for s in card["steps"]], ["unknown"], "no second call after an unknown turn")
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 1, "used": 0})

    def test_run_loop_cap_follows_the_remaining_call_budget(self):
        self.work_with_listing()
        self.prepare_materials()
        self.work_command(self.au_id, "start_work", work_data(
            work_id="work-tight", member_id="m-tight", binding_id="b-tight", mandate_id="ma-tight",
            definition_id="d-tight", materials_root="project-docs", max_calls=2))
        self.start_attempt("work-tight")
        call = {"content": None, "tool_calls": [{"id": "c1", "type": "function",
                "function": {"name": "list_documents", "arguments": "{}"}}]}
        self.with_transport(call, call, call)

        status, value, _ = self.run_loop("work-tight")
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["turns"], 2, "the loop never exceeds the work call budget")
        card = [w for w in self.works()["works"] if w["id"] == "work-tight"][0]
        self.assertEqual(len(card["steps"]), 2)

    def test_a_definite_channel_refusal_creates_no_step_fact(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()

        class Refusing:
            def chat(self, package, messages, tools):
                raise Rejected("模型服务拒绝本次请求")

        self.app.work.transport = Refusing()
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("拒绝", value["receipt"]["message"])
        card = self.works()["works"][0]
        self.assertEqual(card["steps"], [], "a refusal leaves no reserved step behind")
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 0, "used": 0})

    def test_the_host_can_wire_the_channel_through_a_factory(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.app.work.transport = None
        seen = {}

        def factory(au_id, connection):
            seen["au_id"] = au_id
            seen["connection"] = connection
            return FakeTransport([({"content": "# 概览\n", "tool_calls": []}, {"input_tokens": 7, "output_tokens": 3})])

        self.app.work.transport_factory = factory
        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(seen["au_id"], self.au_id)
        self.assertEqual(seen["connection"]["id"], "connection-a")
        self.assertEqual(seen["connection"]["model"], "model-a")
        self.assertEqual(self.works()["works"][0]["steps"][0]["usage"], {"input_tokens": 7, "output_tokens": 3})

    def test_a_factory_that_cannot_build_the_channel_refuses_without_a_step(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.app.work.transport = None

        def factory(au_id, connection):
            raise Rejected("模型服务宿主配置尚未就绪")

        self.app.work.transport_factory = factory
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("就绪", value["receipt"]["message"])
        self.assertEqual(self.works()["works"][0]["steps"], [])

    def test_no_channel_and_no_factory_still_refuses(self):
        self.work_with_listing()
        self.start_attempt()
        self.app.work.transport = None
        self.app.work.transport_factory = None
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("通道", value["receipt"]["message"])

    def test_the_console_wires_the_channel_only_when_the_host_names_its_configuration(self):
        from unittest.mock import patch
        from ai_union.console import Console

        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("UNION_MODELD_CONFIG", None)
                plain = Console(Path(temporary) / "plain", fixture=None, enable_api=False)
                try:
                    self.assertIsNone(plain.work.transport_factory,
                                      "an unconfigured host never invents a model channel")
                finally:
                    plain.close()
            with patch.dict(os.environ, {"UNION_MODELD_CONFIG": str(Path(temporary) / "modeld.json")}):
                wired = Console(Path(temporary) / "wired", fixture=None, enable_api=False)
                try:
                    self.assertTrue(callable(wired.work.transport_factory))
                finally:
                    wired.close()
