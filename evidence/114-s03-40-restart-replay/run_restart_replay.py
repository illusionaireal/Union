"""Prepared (not yet run) real evidence for #40: restart, replay the same command, count dispatches.

Per the #99 pre-review, #40 needs: real output events, AU/request identity, and a restart
followed by an original-request lookup/replay that proves no additional dispatch happens.
This script performs exactly that against the host modeld; run it only after the card owner
authorises a new real execution.
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
SKIP = not os.environ.get("UNION_REAL_RESTART_ACCEPTANCE") == "1"


@unittest.skipIf(SKIP, "需要 UNION_REAL_RESTART_ACCEPTANCE=1 的明确授权才会真的发起调用")
class RestartReplay40(ModelAccessCase):
    def step_of(self, au_id, command_id, deadline=30):
        started = time.monotonic()
        while time.monotonic() - started < deadline:
            card = self.request("/api/v1/work?organization_id=" + au_id)[1]
            for work in card["works"]:
                for step in work.get("steps") or []:
                    if step.get("command_id") == command_id:
                        return step
            time.sleep(0.02)
        return None

    def test_restart_replay_keeps_one_dispatch_and_keeps_the_reservation(self):
        au_id = self.prepare()
        self.provider_patch.stop()
        client = ModelServiceClient(CONFIG)
        grant = client.call("POST", "/v1/grants",
                            {"id": "grant-" + uuid.uuid4().hex[:12], "au_id": au_id,
                             "account_ref": ACCOUNT, "model_ids": [MODEL]}, admin=True)
        receipt, _ = self.model_success("save_connection", {
            "connection_id": "connection-a", "expected_revision": 0, "name": "#40 重启重放",
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
        self.success("amend_charter", {"charter": charter, "reason": "#40 允许资料读取"})
        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_bytes("# 合成资料\n\n#40 重启重放用合成正文。\n".encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")
        models_state = self.request("/api/v1/models?organization_id=" + au_id)[1]
        connection = next(item for item in models_state["connections"] if item["id"] == "connection-a")
        data = {"work_id": "work-40", "title": "#40 重启重放", "member_name": "资料整理 Agent",
                "goal": "逐行输出 1 到 500 的数字，每行一个，最后写三行概览",
                "member_id": "m-40", "binding_id": "b-40", "mandate_id": "ma-40",
                "definition_id": "d-40", "connection_id": "connection-a",
                "expected_revision": connection["revision"], "materials_root": "project-docs",
                "max_calls": 1, "tools": ["read_document"], "reason": "#40 真实重启重放"}
        self.request("/api/v1/work/commands", {"id": str(uuid.uuid4()), "organization_id": au_id,
                                               "base_version": self.read()["au"]["version"],
                                               "kind": "start_work", "data": data})
        self.request("/api/v1/work/commands", {"id": str(uuid.uuid4()), "organization_id": au_id,
                                               "base_version": self.read()["au"]["version"],
                                               "kind": "start_attempt", "data": {"work_id": "work-40"}})

        original = {"id": str(uuid.uuid4()), "organization_id": au_id,
                    "base_version": self.read()["au"]["version"], "kind": "run_step",
                    "data": {"work_id": "work-40"}}
        observed = {}

        def canceller():
            step = self.step_of(au_id, original["id"])
            if step is None:
                return
            request_id = step.get("model_request_id")
            observed["request_id"] = request_id
            for _ in range(400):
                remote = client.call("GET", "/v1/requests/" + request_id + "?au_id=" + au_id)
                if remote.get("state") == "streaming":
                    reply = client.call("POST", "/v1/requests/" + request_id + "/cancel?au_id=" + au_id, {})
                    observed["cancel_reply"] = {"state": reply.get("state"),
                                                "cancel_requested": reply.get("cancel_requested")}
                    break
                if remote.get("state") in ("completed", "failed", "interrupted"):
                    observed["finished_before_cancel"] = remote.get("state")
                    break
                time.sleep(0.02)
            for _ in range(300):
                remote = client.call("GET", "/v1/requests/" + request_id + "?au_id=" + au_id)
                if remote.get("state") in ("completed", "failed", "interrupted"):
                    observed["final"] = {"state": remote.get("state"),
                                         "au_id": remote.get("au_id"),
                                         "cancel_requested": remote.get("cancel_requested")}
                    break
                time.sleep(0.02)

        threading.Thread(target=canceller, daemon=True).start()
        status, first, _ = self.request("/api/v1/work/commands", original)
        first_receipt = first.get("receipt", first)
        work = [item for item in self.request("/api/v1/work?organization_id=" + au_id)[1]["works"]
                if item["id"] == "work-40"][0]
        observed["before_restart"] = {"steps": len(work["steps"]),
                                       "budget": work["budget"],
                                       "model_request_id": work["steps"][0].get("model_request_id")}

        self.stop()
        self.start()
        status, replayed, _ = self.request("/api/v1/work/commands", original)
        replay_receipt = replayed.get("receipt", replayed)
        work = [item for item in self.request("/api/v1/work?organization_id=" + au_id)[1]["works"]
                if item["id"] == "work-40"][0]
        observed["after_replay"] = {"steps": len(work["steps"]),
                                     "steps_status": [step["status"] for step in work["steps"]],
                                     "budget": work["budget"],
                                     "model_request_id": work["steps"][0].get("model_request_id")}
        print("RESTART40:", json.dumps({
            "observed": observed,
            "first_receipt": {key: first_receipt.get(key) for key in
                              ("status", "model_outcome", "message", "step")},
            "replay_receipt": {key: replay_receipt.get(key) for key in
                               ("status", "model_outcome", "message", "step")},
        }, ensure_ascii=False))

        self.assertEqual(observed["after_replay"]["steps"], 1, "重放不得产生新步进/新派发")
        self.assertEqual(observed["after_replay"]["steps_status"], ["unknown"], observed)
        self.assertEqual(observed["after_replay"]["budget"]["reserved"], 1, observed)
        self.assertEqual(observed["after_replay"]["model_request_id"],
                         observed["before_restart"]["model_request_id"], "原请求身份必须不变")


if __name__ == "__main__":
    unittest.main()
