"""Bounded real acceptance for S03: one work, at most two calls, synthetic material.

Skipped unless the host provides both its private modeld configuration and an
explicit opt-in, so an ordinary test run never spends real money or tokens. The
limits are the ones the user authorised: at most 2 calls and at most 1024 output
tokens per call, with synthetic materials only.
"""
import copy
import json
import os
import unittest
import uuid
from pathlib import Path

from ai_union.model_service import ModelServiceClient
from ai_union.work_transport import modeld_factory
from tests.model_access_support import ModelAccessCase

CONFIG = os.environ.get("UNION_MODELD_CONFIG")
MODEL = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
MAX_OUTPUT = min(int(os.environ.get("UNION_REAL_MAX_OUTPUT", "1024")), 1024)
SKIP = (not CONFIG) or os.environ.get("UNION_REAL_ACCEPTANCE") != "1"


@unittest.skipIf(SKIP, "real acceptance needs UNION_MODELD_CONFIG and UNION_REAL_ACCEPTANCE=1")
class RealBoundedAcceptanceTests(ModelAccessCase):
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
        account = (os.environ.get("UNION_REAL_ACCOUNT")
                   or (accounts[0].get("id") or accounts[0].get("account_ref")))
        grant_id = "grant-" + uuid.uuid4().hex[:12]
        created = client.call("POST", "/v1/grants", {"id": grant_id, "au_id": au_id, "account_ref": account,
                                                     "model_ids": [MODEL]}, admin=True)
        return created["id"], created["revision"]

    def connection(self, grant_ref, grant_revision):
        return {"connection_id": "connection-a", "expected_revision": 0, "name": "Go acceptance",
                "profile": "modeld_grant", "model": MODEL, "max_output_tokens": MAX_OUTPUT,
                "grant_ref": grant_ref, "grant_revision": grant_revision}

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
        (directory / "brief.md").write_text(
            "# 合成资料\n\n这是一个用于有界验收的合成文档，不含任何真实业务数据。\n", encoding="utf-8")
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")

        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")
        data = {"work_id": "work-real", "title": "合成概览", "member_name": "资料整理 Agent",
                "goal": "阅读合成资料并写三行概览", "member_id": "m-real", "binding_id": "b-real",
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

        status, looped, _ = self.request("/api/v1/work/commands",
                                         {"id": str(uuid.uuid4()), "organization_id": au_id,
                                          "base_version": self.read()["au"]["version"],
                                          "kind": "run_loop", "data": {"work_id": "work-real"}})
        self.assertEqual(status, 200, looped)
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        used = work["budget"]["used"]
        self.assertLessEqual(used, 2, work["budget"])
        self.assertLessEqual(work["usage"]["output_tokens"], 2 * MAX_OUTPUT, work["usage"])
        self.assertEqual(work["cost_status"], "unknown")
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
