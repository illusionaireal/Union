"""Bounded V1 executions keep responsibility, tool receipts and unknown attempts."""
from contextlib import closing
import copy
import json
import sqlite3
import time
from unittest.mock import patch

from ai_union.model_service import ServiceError
from tests.model_access_support import ModelAccessCase


class CoreModelCheckTests(ModelAccessCase):
    def prepare_check(self, calls=6):
        self.saved()
        self.allow_documents()
        self.resource_grant(calls)

    def test_real_document_read_returns_to_second_inference_with_complete_responsibility(self):
        self.prepare_check()
        receipt, request = self.start_check()
        check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "succeeded", check)
        self.assertIn("这是明确选择的真实本地资料", check["output"])
        state = self.read()["au"]
        self.assertEqual(state["members"][check["member_id"]]["principal_id"], self.principal)
        self.assertEqual(state["work"][check["work_id"]]["responsible_binding_id"], check["binding_id"])
        self.assertEqual(state["mandates"][check["mandate_id"]]["work_id"], check["work_id"])
        self.assertEqual(check["agent_definition"]["id"], "core.model_check")
        self.assertEqual(check["agent_definition"]["version"], 1)
        self.assertEqual(check["agent_definition"]["tools"], ["read_document"])
        self.assertEqual(check["purpose"], "connection_check")
        self.assertEqual(len(check["attempts"]), 2)
        self.assertEqual(len(self.provider.requests), 2)
        first, second = self.provider.requests.values()
        self.assertNotIn("明确选择的真实本地资料", json.dumps(first))
        self.assertIn("明确选择的真实本地资料", json.dumps(second, ensure_ascii=False))
        self.assertIn("_native", second["messages"][-2])
        self.assertEqual([a["usage"]["input_tokens"] for a in check["attempts"]], [25, 25])
        self.assertTrue(all(a["usage"]["cost_minor"] is None for a in check["attempts"]))
        self.assertEqual(self.models()["resources"]["reserved_calls"], 2)
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], receipt)
        self.assertEqual(len(self.provider.requests), 2)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], 1)
        self.assertFalse(self.read()["capabilities"]["autonomous_business"])

    def test_explicit_governance_tool_and_two_call_resource_authorization_are_required(self):
        self.saved()
        data = {"connection_id": "connection-a", "expected_revision": 1, "binding_id": None,
                "document_name": "selected.txt", "document_text": "Only selected material"}
        for setup in (None, lambda: self.resource_grant(1), self.allow_documents):
            if setup:
                setup()
            status, value, _ = self.model_command("start_model_check", data)
            self.assertEqual(status, 200, value)
            self.assertEqual(value["receipt"]["status"], "rejected")
            self.assertEqual(self.provider.requests, {})
        self.model_success("grant_model_resources", {"max_calls": 4, "allow_unknown_cost": False, "reason": "No unknown spend"})
        status, value, _ = self.model_command("start_model_check", data)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(self.provider.requests, {})

    def test_revocation_after_inference_preserves_usage_but_never_executes_tool(self):
        self.prepare_check()
        def revoke():
            check = self.models()["checks"][0]
            self.success("revoke_mandate", {"mandate_id": check["mandate_id"], "reason": "Stop this test authority"})
        self.provider.before_result = revoke
        receipt, _ = self.start_check()
        check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "not_adopted", check)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertEqual(check["attempts"][0]["usage"]["input_tokens"], 25)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], 0)
        self.assertEqual(self.read()["au"]["work"][check["work_id"]]["status"], "open")

    def test_remote_grant_revocation_retains_nonzero_usage_without_second_call(self):
        self.prepare_check()
        self.provider.before_result = lambda: setattr(self.provider, "revoked", True)
        receipt, _ = self.start_check()
        check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "not_adopted", check)
        self.assertEqual(check["attempts"][0]["usage"]["output_tokens"], 12)
        self.assertEqual(len(self.provider.requests), 1)

    def test_lost_post_receipt_queries_original_attempts_without_dispatch_replay(self):
        self.prepare_check()
        self.provider.lost_submit = True
        receipt, _ = self.start_check()
        check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "succeeded", check)
        self.assertEqual(len([p for p in self.provider.posts if p[0] == "/v1/requests"]), 2)

    def test_restart_reconciles_second_attempt_and_reuses_the_original_tool_receipt(self):
        self.prepare_check()
        actual = self.provider.request
        def broken_second(rid, au):
            if len(self.provider.requests) == 2:
                raise ServiceError("lost_second_result")
            return actual(rid, au)
        with patch.object(self.provider, "request", side_effect=broken_second):
            receipt, _ = self.start_check()
            unknown = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(unknown["status"], "unknown", unknown)
        original_ids = list(self.provider.requests)
        self.stop(); self.start()
        self.model_success("reconcile_model_check", {"check_id": receipt["check_id"]})
        complete = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(complete["status"], "succeeded", complete)
        self.assertEqual(list(self.provider.requests), original_ids)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], 1)
        self.assertEqual(len(complete["attempts"]), 2)

    def test_concurrent_checks_cannot_spend_the_same_two_call_reservation(self):
        self.prepare_check(calls=2)
        self.provider.result_state = "streaming"
        first, _ = self.start_check()
        deadline = time.monotonic() + 2
        while not self.provider.requests and time.monotonic() < deadline:
            time.sleep(0.01)
        status, value, _ = self.model_command("start_model_check", {"connection_id": "connection-a", "expected_revision": 1,
            "binding_id": None, "document_name": "second.txt", "document_text": "independent"})
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected")
        self.provider.result_state = "completed"
        self.assertEqual(self.wait_for("checks", first["check_id"])["status"], "succeeded")
        self.assertEqual(self.models()["resources"]["reserved_calls"], 2)
