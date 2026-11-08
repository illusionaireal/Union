"""Interrupt a real modeld request and prove the product keeps an unknown reservation.

Reviewer guidance on #22 (comment on the card): the driver must look up the durable
original request id, and a manual reconcile may never release a reservation — only a
confirmed completion becomes used; lookup failure, 404 or interruption stays unknown.
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
    def wait_for_request_id(self, au_id, deadline=25):
        """Read the durable request id the product persisted before dispatching."""
        started = time.monotonic()
        while time.monotonic() - started < deadline:
            card = self.request("/api/v1/work?organization_id=" + au_id)[1]
            for work in card["works"]:
                for step in work.get("steps") or []:
                    if step.get("model_request_id"):
                        return step["model_request_id"], step["step_ref"]
            time.sleep(0.1)
        return None, None

    def cancel_when_dispatched(self, client, au_id, observed):
        request_id, step_ref = self.wait_for_request_id(au_id)
        if request_id is None:
            return
        observed["request_id"], observed["step_ref"] = request_id, step_ref
        try:
            client.call("GET", "/v1/requests/" + request_id + "?au_id=" + au_id, admin=False)
        except Exception as error:  # noqa: BLE001 - a lookup failure is not a cancellation
            observed["lookup_error"] = type(error).__name__
            return
        observed["observed"] = True
        client.call("POST", "/v1/requests/" + request_id + "/cancel?au_id=" + au_id, {}, admin=True)
        observed["cancelled"] = True

    def prepare_work(self, au_id, connection):
        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_text("# 合成资料\n\n中断验收用合成文档。\n", encoding="utf-8")
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")
        data = {"work_id": "work-real", "title": "合成概览", "member_name": "资料整理 Agent",
                "goal": "阅读合成资料并写三行概览", "member_id": "m-real", "binding_id": "b-real",
                "mandate_id": "ma-real", "definition_id": "d-real", "connection_id": connection["id"],
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

    def test_an_interrupted_call_stays_unknown_and_a_manual_reconcile_cannot_release_it(self):
        au_id = self.prepare()
        grant_ref, grant_revision = self.grant(au_id)
        receipt, _request = self.model_success("save_connection", self.connection(grant_ref, grant_revision))
        self.wait_operation(receipt["operation_id"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                              "enabled": True, "make_default": True})
        self.allow_reading()
        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")
        self.prepare_work(au_id, connection)

        observed = {}
        done = threading.Event()

        def canceller():
            self.cancel_when_dispatched(ModelServiceClient(CONFIG), au_id, observed)
            done.set()

        threading.Thread(target=canceller, daemon=True).start()
        status, stepped, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "run_step", "data": {"work_id": "work-real"}})
        done.wait(30)
        self.assertTrue(observed.get("request_id"), "the product must persist the original request id before dispatch")
        self.assertTrue(observed.get("observed"), "modeld never confirmed the durable request: " + str(observed))
        self.assertTrue(observed.get("cancelled"), "the cancel was never sent")

        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        self.assertEqual(work["budget"]["used"], 0, work["budget"])
        self.assertEqual(work["budget"]["reserved"], 1, work["budget"])
        self.assertEqual([step["status"] for step in work["steps"]], ["unknown"], work["steps"])

        status, reconciled, _ = self.request("/api/v1/work/commands",
                                             {"id": str(uuid.uuid4()), "organization_id": au_id,
                                              "base_version": self.read()["au"]["version"],
                                              "kind": "reconcile_step",
                                              "data": {"work_id": "work-real",
                                                       "step_id": observed["step_ref"],
                                                       "status": "released",
                                                       "reason": "尝试手工释放"}})
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        print("interrupt:", json.dumps({
            "request_id": observed["request_id"], "receipt": {k: reconciled.get("receipt", reconciled).get(k)
                                                              for k in ("status", "message")},
            "budget": work["budget"], "steps": [step["status"] for step in work["steps"]],
        }, ensure_ascii=False))
        self.assertEqual(work["budget"]["reserved"], 1, "a manual reconcile may not release the reservation")
        self.assertEqual([step["status"] for step in work["steps"]], ["unknown"], work["steps"])


if __name__ == "__main__":
    unittest.main()
