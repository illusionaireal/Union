"""Interrupt a real modeld request and prove the product keeps an unknown reservation.

Gated like the bounded acceptance: skipped unless the host provides its private modeld
configuration and the explicit opt-in. One call at most, synthetic material only.
"""
import json
import os
import threading
import time
import unittest
import uuid
from pathlib import Path

from ai_union.model_service import ModelServiceClient
from tests.test_core_work_real import MAX_OUTPUT, MODEL, RealChannelCase

CONFIG = os.environ.get("UNION_MODELD_CONFIG")
SKIP = (not CONFIG) or os.environ.get("UNION_REAL_ACCEPTANCE") != "1"


@unittest.skipIf(SKIP, "real interruption needs UNION_MODELD_CONFIG and UNION_REAL_ACCEPTANCE=1")
class RealInterruptTests(RealChannelCase):
    def request_id(self):
        return "work-real-s1"

    def cancel_when_dispatched(self, client, au_id, observed):
        """Cancel only after modeld confirms the original request exists."""
        for _ in range(100):
            try:
                client.call("GET", "/v1/requests/" + self.request_id() + "?au_id=" + au_id, admin=False)
            except Exception:  # noqa: BLE001 - not created yet
                time.sleep(0.1)
                continue
            observed["observed"] = True
            client.call("POST", "/v1/requests/" + self.request_id() + "/cancel?au_id=" + au_id, {}, admin=True)
            observed["cancelled"] = True
            return

    def test_an_interrupted_call_keeps_an_unknown_reservation_until_reconciled(self):
        au_id = self.prepare()
        grant_ref, grant_revision = self.grant(au_id)
        receipt, _request = self.model_success("save_connection", self.connection(grant_ref, grant_revision))
        self.wait_operation(receipt["operation_id"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                              "enabled": True, "make_default": True})
        self.allow_reading()
        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_text("# 合成资料\n\n中断验收用合成文档。\n", encoding="utf-8")
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")
        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")
        data = {"work_id": "work-real", "title": "合成概览", "member_name": "资料整理 Agent",
                "goal": "阅读合成资料并写三行概览", "member_id": "m-real", "binding_id": "b-real",
                "mandate_id": "ma-real", "definition_id": "d-real", "connection_id": "connection-a",
                "expected_revision": connection["revision"], "materials_root": "project-docs",
                "max_calls": 1, "tools": ["read_document", "list_documents"], "reason": "中断验收"}
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

        observed = {"observed": False, "cancelled": False}
        done = threading.Event()

        def canceller():
            client = ModelServiceClient(CONFIG)
            self.cancel_when_dispatched(client, au_id, observed)
            done.set()

        threading.Thread(target=canceller, daemon=True).start()
        status, stepped, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "run_step", "data": {"work_id": "work-real"}})
        done.wait(20)
        self.assertTrue(observed["observed"], "modeld never confirmed the original request; a lookup failure is not a cancellation")
        self.assertTrue(observed["cancelled"], "the cancel was never actually sent")
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        print("interrupt:", json.dumps({"receipt": {k: stepped["receipt"].get(k) for k in
                                                    ("status", "model_outcome", "message", "step")},
                                        "budget": work["budget"],
                                        "steps": [{"status": step["status"], "reason": step.get("reason")}
                                                  for step in work["steps"]],
                                        "usage": work["usage"]}, ensure_ascii=False))
        self.assertEqual(work["budget"]["used"], 0, work["budget"])
        self.assertEqual(work["budget"]["reserved"], 1, work["budget"])
        self.assertEqual([step["status"] for step in work["steps"]], ["unknown"], work["steps"])

        step_id = work["steps"][0]["step_ref"]
        status, reconciled, _ = self.request("/api/v1/work/commands",
                                             {"id": str(uuid.uuid4()), "organization_id": au_id,
                                              "base_version": self.read()["au"]["version"],
                                              "kind": "reconcile_step",
                                              "data": {"work_id": "work-real", "step_id": step_id,
                                                       "status": "released", "reason": "已中断，核对后释放"}})
        self.assertEqual(reconciled["receipt"]["status"], "succeeded", reconciled)
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        self.assertEqual(work["budget"]["reserved"], 0, work["budget"])
        self.assertEqual([step["status"] for step in work["steps"]], ["released"], work["steps"])


if __name__ == "__main__":
    unittest.main()
