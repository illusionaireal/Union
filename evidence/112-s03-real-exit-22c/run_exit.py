"""One-off real exit for #22-C: interrupt a live request, keep it unknown, and prove no manual release.

Evidence tooling for the card owner; it does not modify the PR32 driver scope.
"""
import json
import os
import threading
import time
import unittest
import uuid
from pathlib import Path

from ai_union.model_service import ModelServiceClient
from tests.model_access_support import ModelAccessCase

CONFIG = os.environ["UNION_MODELD_CONFIG"]
MODEL = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
ACCOUNT = os.environ["UNION_REAL_ACCOUNT"]


class Exit22C(ModelAccessCase):
    def request_id_for(self, au_id, command_id, deadline=30):
        started = time.monotonic()
        while time.monotonic() - started < deadline:
            card = self.request("/api/v1/work?organization_id=" + au_id)[1]
            for work in card["works"]:
                for step in work.get("steps") or []:
                    if step.get("model_request_id") and step.get("command_id") == command_id:
                        return step["model_request_id"], step["step_ref"], step.get("status")
            time.sleep(0.02)
        return None, None, None

    def test_exit_22c(self):
        au_id = self.prepare()
        self.provider_patch.stop()
        client = ModelServiceClient(CONFIG)
        grant = client.call("POST", "/v1/grants",
                            {"id": "grant-" + uuid.uuid4().hex[:12], "au_id": au_id,
                             "account_ref": ACCOUNT, "model_ids": [MODEL]}, admin=True)
        receipt, _ = self.model_success("save_connection", {
            "connection_id": "connection-a", "expected_revision": 0, "name": "22C 验收",
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
        self.success("amend_charter", {"charter": charter, "reason": "允许有界取证的资料读取"})
        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_bytes("# 合成资料\n\n用于中断取证的合成正文。\n".encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")
        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")
        data = {"work_id": "work-cancel", "title": "22C 中断取证", "member_name": "资料整理 Agent",
                "goal": "逐行输出从 1 到 600 的数字，每行只写一个数字，不要省略，不要提前结束",
                "member_id": "m-c", "binding_id": "b-c", "mandate_id": "ma-c", "definition_id": "d-c",
                "connection_id": "connection-a", "expected_revision": connection["revision"],
                "materials_root": "project-docs", "max_calls": 1, "tools": ["read_document"],
                "reason": "22-C 真实中断出口"}
        status, created, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "start_work", "data": data})
        self.assertEqual(created["receipt"]["status"], "succeeded", created)
        status, started, _ = self.request("/api/v1/work/commands",
                                          {"id": str(uuid.uuid4()), "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "start_attempt", "data": {"work_id": "work-cancel"}})
        self.assertEqual(started["receipt"]["status"], "succeeded", started)

        command_id = str(uuid.uuid4())
        observed = {}
        done = threading.Event()

        def canceller():
            request_id, step_ref, _ = self.request_id_for(au_id, command_id)
            if request_id is None:
                done.set()
                return
            observed.update(request_id=request_id, step_ref=step_ref)
            for _ in range(200):
                remote = client.call("GET", "/v1/requests/" + request_id + "?au_id=" + au_id)
                observed.setdefault("states", []).append(remote.get("state"))
                if remote.get("state") == "streaming":
                    reply = client.call("POST", "/v1/requests/" + request_id + "/cancel?au_id=" + au_id, {})
                    observed["cancel_reply"] = {"state": reply.get("state"),
                                                 "cancel_requested": reply.get("cancel_requested")}
                    observed["cancel_sent"] = True
                    break
                if remote.get("state") in ("completed", "failed", "interrupted"):
                    observed["finished_before_cancel"] = remote.get("state")
                    break
                time.sleep(0.02)
            for _ in range(300):
                remote = client.call("GET", "/v1/requests/" + request_id + "?au_id=" + au_id)
                if remote.get("state") in ("completed", "failed", "interrupted"):
                    observed["final"] = {"state": remote.get("state"),
                                         "cancel_requested": remote.get("cancel_requested")}
                    break
                time.sleep(0.02)
            done.set()

        threading.Thread(target=canceller, daemon=True).start()
        status, stepped, _ = self.request("/api/v1/work/commands",
                                          {"id": command_id, "organization_id": au_id,
                                           "base_version": self.read()["au"]["version"],
                                           "kind": "run_step", "data": {"work_id": "work-cancel"}})
        done.wait(60)
        step_receipt = stepped.get("receipt", stepped)
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-cancel"][0]
        summary = {"observed": observed, "receipt": {key: step_receipt.get(key) for key in
                                                     ("status", "model_outcome", "message", "step")},
                   "budget": work["budget"], "steps": [step["status"] for step in work["steps"]]}

        status, reconciled, _ = self.request("/api/v1/work/commands",
                                             {"id": str(uuid.uuid4()), "organization_id": au_id,
                                              "base_version": self.read()["au"]["version"],
                                              "kind": "reconcile_step",
                                              "data": {"work_id": "work-cancel",
                                                       "step_id": work["steps"][0]["step_ref"],
                                                       "status": "used",
                                                       "reason": "核对原请求（若未确认则不记账）"}})
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-cancel"][0]
        summary["reconcile"] = {"receipt": {key: reconciled.get("receipt", reconciled).get(key)
                                            for key in ("status", "message")},
                                "budget": work["budget"], "steps": [step["status"] for step in work["steps"]]}
        print("EXIT22C:", json.dumps(summary, ensure_ascii=False))

        self.assertTrue(observed.get("cancel_sent"), "取消必须真的发出: " + str(observed))
        self.assertEqual(observed.get("final", {}).get("state"), "interrupted", observed)
        self.assertEqual(step_receipt.get("model_outcome"), "unknown", step_receipt)
        self.assertEqual(work["budget"]["reserved"], 1, "未确认原请求时预约必须保留")


if __name__ == "__main__":
    unittest.main()
