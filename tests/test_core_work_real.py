"""Bounded real acceptance for S03: one work, at most two calls, synthetic material.

Skipped unless the host provides both its private modeld configuration and an
explicit opt-in, so a normal test run never spends real money. The limits here are
the ones the user authorised: at most 2 calls and at most 1024 output tokens per
call, with synthetic materials only.
"""
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from ai_union.work_transport import modeld_factory
from tests.model_access_support import ModelAccessCase

CONFIG = os.environ.get("UNION_MODELD_CONFIG")
OPTOUT = os.environ.get("UNION_REAL_ACCEPTANCE") != "1"


@unittest.skipIf(not CONFIG or OPTOUT, "real acceptance needs UNION_MODELD_CONFIG and UNION_REAL_ACCEPTANCE=1")
class RealBoundedAcceptanceTests(ModelAccessCase):
    def connection(self):
        state = self.read()["au"]
        default = state["model_access"]["default_connection_id"]
        return dict(state["model_access"]["connections"][default])

    def test_one_work_uses_at_most_two_calls_and_reports_usage_without_cost(self):
        connection = self.connection()
        connection["max_output_tokens"] = min(int(connection.get("max_output_tokens") or 1024), 1024)
        self.app.work.transport = None
        self.app.work.transport_factory = lambda au_id, state_connection: modeld_factory(CONFIG)(
            au_id, connection)
        self.prepare()

        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_text(
            "# 合成资料\n\n这是一个用于有界验收的合成文档，不含任何真实业务数据。\n", encoding="utf-8")
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")

        data = {"work_id": "work-real", "title": "合成概览", "member_name": "资料整理 Agent",
                "goal": "阅读合成资料并写三行概览", "member_id": "m-real", "binding_id": "b-real",
                "mandate_id": "ma-real", "definition_id": "d-real", "connection_id": connection["id"],
                "expected_revision": connection["revision"], "materials_root": "project-docs",
                "max_calls": 2, "tools": ["read_document", "list_documents"], "reason": "有界真实验收"}
        status, value, _ = self.request("/api/v1/work/commands",
                                        {"id": str(uuid.uuid4()), "organization_id": self.au_id,
                                         "base_version": self.read()["au"]["version"],
                                         "kind": "start_work", "data": data})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        status, started, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": self.au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "start_attempt", "data": {"work_id": "work-real"}})
        self.assertEqual(started["receipt"]["status"], "succeeded", started)

        status, looped, _ = self.request("/api/v1/work/commands",
                                         {"id": str(uuid.uuid4()), "organization_id": self.au_id,
                                          "base_version": self.read()["au"]["version"],
                                          "kind": "run_loop", "data": {"work_id": "work-real"}})
        self.assertEqual(status, 200, looped)
        card = self.request("/api/v1/work?organization_id=" + self.au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        used = work["budget"]["used"]
        self.assertLessEqual(used, 2, work["budget"])
        self.assertLessEqual(work["usage"]["output_tokens"], 2 * 1024, work["usage"])
        self.assertEqual(work["cost_status"], "unknown")
        self.assertTrue(work["steps"] or work["results"], work)
        print("real acceptance:", json.dumps({"turns_used": used, "usage": work["usage"],
                                              "cost_status": work["cost_status"],
                                              "tool_calls": len(work["tool_calls"]),
                                              "results": len(work["results"])}, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
