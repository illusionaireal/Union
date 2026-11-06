"""S02 failures retain original work, safe diagnostics and observed usage."""
from contextlib import closing
import http.client
import json
import sqlite3
import threading
from unittest.mock import patch

from ai_union.model_service import ServiceError
from tests.model_access_support import ModelAccessCase


class CoreModelDiagnosticsTests(ModelAccessCase):
    def ready(self):
        self.saved()
        self.allow_documents()
        self.resource_grant(6)

    def test_worker_start_failure_keeps_receipt_and_can_reconcile_original_work(self):
        self.ready()
        actual_start = threading.Thread.start

        def fail_worker(thread):
            target = getattr(thread, "_target", None)
            if getattr(target, "__qualname__", "").startswith("ModelAccessService.spawn."):
                raise RuntimeError("synthetic worker startup failure")
            return actual_start(thread)

        receipt = None
        try:
            with patch("ai_union.application.model_access.threading.Thread.start", new=fail_worker):
                receipt, request = self.start_check()
        except http.client.RemoteDisconnected:
            # Allow fixture teardown after exposing the missing HTTP recovery behavior.
            self.app.jobs[:] = [thread for thread in self.app.jobs if thread.ident is not None]
        self.assertIsNotNone(receipt, "A durable command receipt must survive worker startup failure")
        original = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(original["status"], "unknown")
        self.assertEqual(original.get("diagnostic", {}).get("code"), "worker_start_failed")
        self.assertNotIn((self.au_id, original["id"]), self.app.models.running)
        self.assertEqual(self.provider.requests, {})
        self.assertTrue(all(thread.ident is not None for thread in self.app.jobs))
        self.model_success("reconcile_model_check", {"check_id": original["id"]})
        resumed = self.wait_for("checks", original["id"])
        self.assertEqual(resumed["status"], "succeeded", resumed)
        self.assertEqual(resumed["work_id"], original["work_id"])
        self.assertEqual(len(self.provider.requests), 2)
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], receipt)
        self.assertEqual(len(self.provider.requests), 2)

    def test_decoded_key_cannot_be_saved_in_public_connection_fields(self):
        secret = 'private-"quoted"-\\key'
        data = {"connection_id": "connection-a", "expected_revision": 0,
                "name": "visible " + secret, "profile": "openai_compatible",
                "model": "model-a", "max_output_tokens": 256,
                "base_url": "https://model.example.invalid/v1", "api_key": secret}
        status, _, _ = self.model_command("save_connection", data)
        self.assertEqual(status, 400)
        self.assertEqual(self.provider.posts, [])
        self.assertEqual(self.models()["connections"], [])
        self.assertNotIn(secret, json.dumps(self.read()["au"], ensure_ascii=False))

    def test_interrupted_event_usage_survives_restart_without_dispatch_or_double_count(self):
        self.ready()
        original_request = self.provider.request
        calls = []

        def interrupted(request_id, au_id):
            value = original_request(request_id, au_id)
            return value | {"state": "interrupted", "result": None,
                            "action_authorized": False, "error": "provider_result_unconfirmed"}

        def events(request_id, au_id, after=0):
            calls.append(after)
            items = [
                {"request_id": request_id, "seq": 1, "type": "usage", "created_at": "2026-11-06",
                 "payload": {"input_tokens": 37, "output_tokens": 5, "modeld_usage": {"cost": 0.04}}},
                {"request_id": request_id, "seq": 2, "type": "usage", "created_at": "2026-11-06",
                 "payload": {"input_tokens": 37, "output_tokens": 9, "cost_minor": 4, "currency": "USD"}},
                {"request_id": request_id, "seq": 3, "type": "native_event", "created_at": "2026-11-06",
                 "payload": {"type": "raw", "data": "private-native-canary"}},
            ]
            return {"events": [item for item in items if item["seq"] > after], "state": "interrupted"}

        with patch.object(self.provider, "request", side_effect=interrupted), patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            first = self.wait_for("checks", receipt["check_id"])
            self.assertEqual(first["status"], "unknown", first)
            usage = first["attempts"][0]["usage"]
            self.assertEqual((usage["input_tokens"], usage["output_tokens"]), (37, 9))
            self.assertEqual((usage["cost_minor"], usage["currency"]), (4, "USD"))
            self.assertEqual(usage.get("basis"), "events")
            self.assertEqual(usage.get("observed_through_seq"), 3)
            self.assertNotIn("private-native-canary", json.dumps(self.models()))
            self.stop(); self.start()
            self.model_success("reconcile_model_check", {"check_id": first["id"]})
            resumed = self.wait_for("checks", first["id"])
        self.assertEqual(resumed["attempts"][0]["usage"], usage)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertIn(3, calls)
        with closing(sqlite3.connect(self.database())) as cx:
            stored = json.loads(cx.execute("SELECT result FROM model_attempts").fetchone()[0])
        self.assertEqual([event["seq"] for event in stored["events"]], [1, 2, 3])

    def test_final_usage_takes_precedence_over_cumulative_stream_usage(self):
        self.ready()

        def events(request_id, au_id, after=0):
            item = {"request_id": request_id, "seq": 1, "type": "usage", "created_at": "2026-11-06",
                    "payload": {"input_tokens": 24, "output_tokens": 10}}
            return {"events": [item] if after < 1 else [], "state": "completed"}

        with patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            complete = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(complete["status"], "succeeded", complete)
        for attempt in complete["attempts"]:
            self.assertEqual((attempt["usage"]["input_tokens"], attempt["usage"]["output_tokens"]), (25, 12))
            self.assertEqual(attempt["usage"].get("basis"), "result")
        self.assertEqual(len(self.provider.requests), 2)

    def test_provider_failure_has_safe_actionable_diagnostic_and_retains_usage(self):
        self.ready()
        original = self.provider.request

        def refused(request_id, au_id):
            return original(request_id, au_id) | {"state": "failed", "error": "provider_authentication_failed"}

        with patch.object(self.provider, "request", side_effect=refused):
            receipt, _ = self.start_check()
            failed = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(failed.get("diagnostic", {}).get("code"), "provider_authentication_failed")
        self.assertIn("密钥", failed["message"])
        self.assertTrue(failed["diagnostic"]["next_step"])
        self.assertEqual(failed["attempts"][0]["usage"]["input_tokens"], 25)
        self.assertEqual(len(self.provider.requests), 1)

    def test_unrecognized_remote_error_is_not_exposed_in_public_diagnostics(self):
        self.ready()
        original = self.provider.request

        def refused(request_id, au_id):
            return original(request_id, au_id) | {"state": "failed", "error": 'provider said private-key-"canary"'}

        with patch.object(self.provider, "request", side_effect=refused):
            receipt, _ = self.start_check()
            failed = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(failed.get("diagnostic", {}).get("code"), "provider_result_unconfirmed")
        self.assertNotIn("private-key", json.dumps(self.models()))

    def test_service_authentication_failure_does_not_claim_provider_key_is_wrong(self):
        data = {"connection_id": "connection-a", "expected_revision": 0, "name": "Connection",
                "profile": "openai_compatible", "model": "model-a", "max_output_tokens": 256,
                "base_url": "https://model.example.invalid/v1", "api_key": "controlled-key"}
        actual = self.provider.call

        def fail_auth(method, path, body=None, **kwargs):
            if path == "/v1/api-connections":
                raise ServiceError("model_service_rejected", 401)
            return actual(method, path, body, **kwargs)

        with patch.object(self.provider, "call", side_effect=fail_auth):
            receipt, _ = self.model_success("save_connection", data)
            operation = self.wait_operation(receipt["operation_id"])
        self.assertEqual(operation.get("diagnostic", {}).get("code"), "model_service_authentication_failed")
        self.assertEqual(operation["status"], "rejected")
        self.assertEqual(self.provider.requests, {})
