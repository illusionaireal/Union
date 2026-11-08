"""One-off real exit for #22-B: read body -> candidate -> adopt -> download -> deliver -> reopen.

Runs against the integration head with the host's real modeld. Kept out of the PR32 driver
scope: this is evidence tooling for the card owner.
"""
import json
import hashlib
import os
import unittest
import uuid
from pathlib import Path

from ai_union.model_service import ModelServiceClient
from tests.model_access_support import ModelAccessCase

CONFIG = os.environ["UNION_MODELD_CONFIG"]
MODEL = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
ACCOUNT = os.environ["UNION_REAL_ACCOUNT"]
TEXT = "# 合成资料\n\n本资料只用于有界验收：项目代号 UNION-BOUNDED-7319，试点城市为杭州。\n"
DIGEST = hashlib.sha256(TEXT.encode()).hexdigest()


class Exit22B(ModelAccessCase):
    def test_exit_22b(self):
        au_id = self.prepare()
        self.provider_patch.stop()
        client = ModelServiceClient(CONFIG)
        grant = client.call("POST", "/v1/grants",
                            {"id": "grant-" + uuid.uuid4().hex[:12], "au_id": au_id,
                             "account_ref": ACCOUNT, "model_ids": [MODEL]}, admin=True)
        receipt, _ = self.model_success("save_connection", {
            "connection_id": "connection-a", "expected_revision": 0, "name": "22B 验收",
            "profile": "modeld_grant", "model": MODEL, "max_output_tokens": 1024,
            "grant_ref": grant["id"], "grant_revision": grant["revision"]})
        self.wait_operation(receipt["operation_id"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                              "enabled": True, "make_default": True})
        import copy
        charter = copy.deepcopy(self.read()["au"]["charter"])
        for tool in ("read_document", "list_documents"):
            if tool not in charter["allowed_tools"]:
                charter["allowed_tools"].append(tool)
        self.success("amend_charter", {"charter": charter, "reason": "允许有界验收读取登记资料"})

        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_bytes(TEXT.encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")
        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")

        data = {"work_id": "work-exit", "title": "22B 真实出口", "member_name": "资料整理 Agent",
                "goal": "第一步必须 read_document('brief.md') 读取正文；第二步用最终回答写三行概览，"
                        "不要再调用任何工具，也不要先列目录",
                "member_id": "m-exit", "binding_id": "b-exit", "mandate_id": "ma-exit",
                "definition_id": "d-exit", "connection_id": "connection-a",
                "expected_revision": connection["revision"], "materials_root": "project-docs",
                "max_calls": 3, "tools": ["read_document"], "reason": "22-B 真实有界出口"}
        status, created, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "start_work", "data": data})
        self.assertEqual(created["receipt"]["status"], "succeeded", created)
        status, started, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "start_attempt", "data": {"work_id": "work-exit"}})
        self.assertEqual(started["receipt"]["status"], "succeeded", started)
        status, looped, _ = self.request("/api/v1/work/commands",
                                         {"id": str(uuid.uuid4()), "organization_id": au_id,
                                          "base_version": self.read()["au"]["version"],
                                          "kind": "run_loop", "data": {"work_id": "work-exit"}})
        loop_receipt = looped.get("receipt", looped)
        work = [item for item in self.request("/api/v1/work?organization_id=" + au_id)[1]["works"]
                if item["id"] == "work-exit"][0]
        summary = {"loop": {key: loop_receipt.get(key) for key in
                            ("status", "message", "turns", "tool_calls", "result", "usage")},
                   "budget": work["budget"], "usage": work["usage"],
                   "reads": [{"sha256": call.get("sha256"), "bytes": call.get("bytes")}
                             for call in work["tool_calls"] if call["tool"] == "read_document"],
                   "document_sha256": DIGEST,
                   "results": [{"id": item["id"], "status": item["status"]} for item in work["results"]]}
        self.assertEqual(loop_receipt.get("status"), "succeeded", loop_receipt)
        self.assertTrue(work["results"], "需要候选成果")
        self.assertTrue(any(call.get("sha256") == DIGEST for call in work["tool_calls"]),
                        "读取摘要必须等于合成资料摘要")
        self.assertGreaterEqual(work["usage"]["input_tokens"], 1, work["usage"])

        result = next(item for item in work["results"] if item["status"] == "candidate")
        status, adopted, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "adopt_result",
                                           "data": {"work_id": "work-exit", "result_id": result["id"]}})
        self.assertEqual(adopted["receipt"]["status"], "succeeded", adopted)
        code, downloaded, _ = self.request("/api/v1/work/results?organization_id=" + au_id + "&id=" + result["id"])
        self.assertEqual(code, 200, downloaded)
        attempt = self.read()["au"]  # touch state so version is fresh
        work_read = [item for item in self.request("/api/v1/work?organization_id=" + au_id)[1]["works"]
                     if item["id"] == "work-exit"][0]
        running = next((item for item in work_read["attempts"] if item["status"] == "running"), None)
        if running is not None:
            status, closed, _ = self.request("/api/v1/work/commands",
                                             {"id": str(uuid.uuid4()), "organization_id": au_id,
                                              "base_version": self.read()["au"]["version"],
                                              "kind": "finish_attempt",
                                              "data": {"work_id": "work-exit", "attempt_id": running["id"],
                                                       "outcome": "delivered", "reason": "本轮只读资料已产出并采用候选成果"}})
            self.assertEqual(closed["receipt"]["status"], "succeeded", closed)
        status, delivered, _ = self.request("/api/v1/work/commands",
                                            {"id": str(uuid.uuid4()), "organization_id": au_id,
                                             "base_version": self.read()["au"]["version"],
                                             "kind": "deliver_work",
                                             "data": {"work_id": "work-exit", "result_id": result["id"]}})
        self.assertEqual(delivered["receipt"]["status"], "succeeded", delivered)
        summary["download"] = {"bytes": len(downloaded.get("content") or ""),
                               "sha256_matches": downloaded.get("sha256") == DIGEST}
        summary["deliver"] = {key: delivered["receipt"].get(key) for key in ("status", "message")}

        self.stop()
        self.start()
        reopened = [item for item in self.request("/api/v1/work?organization_id=" + au_id)[1]["works"]
                    if item["id"] == "work-exit"][0]
        summary["reopen"] = {"status": reopened["status"],
                             "results": [{"id": item["id"], "status": item["status"]}
                                         for item in reopened["results"]],
                             "steps": [step["status"] for step in reopened["steps"]]}
        self.assertEqual(reopened["status"], "delivered", reopened)
        self.assertEqual([item["status"] for item in reopened["results"]], ["adopted"], reopened)
        print("EXIT22B:", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
