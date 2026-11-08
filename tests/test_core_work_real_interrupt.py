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
from ai_union.work_transport import modeld_factory
from tests.test_core_work_real import MAX_OUTPUT, MODEL, RealChannelCase

CONFIG = os.environ.get("UNION_MODELD_CONFIG")
SKIP = (not CONFIG) or os.environ.get("UNION_REAL_INTERRUPT_ACCEPTANCE") != "1"


def reconciliation_problems(work, request_id, lookup):
    """Assess the product's actual original-request lookup, not a guessed outcome."""
    steps = [step for step in work.get("steps", []) if step.get("model_request_id") == request_id]
    if len(steps) != 1 or not lookup.get("called"):
        return ["没有唯一原请求或没有实际原请求核对"]
    step = steps[0]
    usage = lookup.get("usage")
    budget = work.get("budget", {})
    if usage is None:
        return [] if step.get("status") in ("unknown", "reserved") and budget.get("reserved") == 1 and budget.get("used") == 0 else ["未确认请求的预约被释放"]
    known = {k: v for k, v in usage.items() if k in ("input_tokens", "output_tokens") and type(v) is int and v >= 0}
    return [] if step.get("status") == "used" and step.get("usage") == known and budget.get("used") == 1 and budget.get("reserved") == 0 else ["已确认完成的原请求未保留实际用量"]


@unittest.skipIf(SKIP, "real interruption needs UNION_MODELD_CONFIG and UNION_REAL_INTERRUPT_ACCEPTANCE=1 (up to one call)")
class RealInterruptTests(RealChannelCase):
    def wait_for_request_id(self, au_id, deadline=25):
        """Read the durable request id the product persisted before dispatching."""
        started = time.monotonic()
        while time.monotonic() - started < deadline:
            status, card, _ = self.request("/api/v1/work?organization_id=" + au_id)
            if status != 200 or card.get("organization_id") != au_id:
                return None, None
            for work in card["works"]:
                if work["id"] != self.target_command["data"]["work_id"]:
                    continue
                for step in work.get("steps") or []:
                    if (step.get("model_request_id") and step.get("command_id") == self.target_command["id"]
                            and step.get("attempt_id") == self.target_attempt):
                        return step["model_request_id"], step["step_ref"]
            time.sleep(0.02)
        return None, None

    def cancel_when_dispatched(self, client, au_id, observed):
        request_id, step_ref = self.wait_for_request_id(au_id)
        if request_id is None:
            return
        observed["request_id"], observed["step_ref"] = request_id, step_ref
        deadline = time.monotonic() + 25
        observed["remote_cancellation_confirmed"] = False
        try:
            while time.monotonic() < deadline:
                remote = client.call("GET", "/v1/requests/" + request_id + "?au_id=" + au_id)
                if remote.get("id") != request_id or remote.get("au_id") != au_id:
                    observed["lookup_error"] = "scope_mismatch"
                    return
                observed["state"] = remote.get("state")
                if remote.get("state") in ("completed", "failed", "interrupted"):
                    observed["interrupted"] = (remote["state"] == "interrupted" and observed.get("cancel_requested") is True)
                    return
                if not observed.get("cancel_requested"):
                    events = client.events(request_id, au_id, 0).get("events", [])
                    output = any(e.get("request_id") == request_id and type(e.get("seq")) is int and e["seq"] > 0
                                 and e.get("type") in ("text_delta", "tool_call_complete") for e in events)
                    if remote.get("state") == "streaming" and output:
                        observed["provider_output_observed"] = True
                        reply = client.call("POST", "/v1/requests/" + request_id + "/cancel?au_id=" + au_id, {})
                        if (reply.get("id") != request_id or reply.get("au_id") != au_id
                                or reply.get("cancel_requested") is not True or reply.get("state") == "completed"):
                            observed["cancel_error"] = "unconfirmed_or_completed"
                            return
                        observed["cancel_requested"] = True
                time.sleep(0.02)
        except Exception as error:  # Failure cannot prove cancellation; never publish private error text.
            observed["lookup_error"] = type(error).__name__

    def prepare_work(self, au_id, connection):
        directory = Path(self.root) / "synthetic-materials"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "brief.md").write_text("# 合成资料\n\n中断验收用合成文档。\n", encoding="utf-8")
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False),
            encoding="utf-8")
        data = {"work_id": "work-real", "title": "合成概览", "member_name": "资料整理 Agent",
                "goal": "先 read_document 读取 brief.md，然后逐行输出 1 到 600 的编号清单（每行只写数字），最后写三行概览", "member_id": "m-real", "binding_id": "b-real",
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
        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = next(item for item in card["works"] if item["id"] == "work-real")
        self.target_attempt = next(item["id"] for item in work["attempts"] if item["status"] == "running")

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
        self.target_command = {"id": str(uuid.uuid4()), "organization_id": au_id,
                               "base_version": self.read()["au"]["version"],
                               "kind": "run_step", "data": {"work_id": "work-real"}}

        def canceller():
            try:
                self.cancel_when_dispatched(ModelServiceClient(CONFIG), au_id, observed)
            finally:
                done.set()

        worker = threading.Thread(target=canceller, daemon=True)
        worker.start()
        status, stepped, _ = self.request("/api/v1/work/commands", self.target_command)
        self.assertTrue(done.wait(55), "cancellation observer did not finish")
        worker.join()
        print("interrupt observed:", json.dumps(observed, ensure_ascii=False))
        self.assertTrue(observed.get("request_id"), "the product must persist the original request id before dispatch")
        self.assertTrue(observed.get("provider_output_observed"), "no scoped provider output before cancellation")
        self.assertTrue(observed.get("cancel_requested"), "modeld did not acknowledge the original cancellation")
        self.assertTrue(observed.get("interrupted"), "completion race or missing terminal observation is not interruption")

        card = self.request("/api/v1/work?organization_id=" + au_id)[1]
        work = [item for item in card["works"] if item["id"] == "work-real"][0]
        self.assertEqual(work["budget"]["used"], 0, work["budget"])
        self.assertEqual(work["budget"]["reserved"], 1, work["budget"])
        self.assertEqual([step["status"] for step in work["steps"]], ["unknown"], work["steps"])

        lookup = {}
        factory = modeld_factory(CONFIG)

        def observing_factory(organization_id, connection):
            channel = factory(organization_id, connection)
            original_lookup = channel.lookup
            def observe(original_id):
                self.assertEqual(original_id, observed["request_id"])
                lookup["called"] = True
                try:
                    lookup["usage"] = original_lookup(original_id)
                    return lookup["usage"]
                except Exception:
                    lookup["usage"] = None
                    raise
            channel.lookup = observe
            return channel

        self.app.work.transport_factory = observing_factory
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
        self.assertEqual(reconciliation_problems(work, observed["request_id"], lookup), [])
        self.assertEqual(work["results"], [], "reconciliation may account for usage but cannot adopt recovered content")
        original_steps = work["steps"]
        self.stop()
        self.start()
        # An immutable original receipt is returned before transport construction.
        def no_dispatch(*args):
            raise AssertionError("reopening the original command attempted to construct another channel")
        self.app.work.transport_factory = no_dispatch
        replay_status, replay, _ = self.request("/api/v1/work/commands", self.target_command)
        self.assertEqual(replay_status, 200)
        self.assertEqual(replay, stepped)
        reopened = next(item for item in self.request("/api/v1/work?organization_id=" + au_id)[1]["works"] if item["id"] == "work-real")
        self.assertEqual(reopened["steps"], original_steps)


if __name__ == "__main__":
    unittest.main()
