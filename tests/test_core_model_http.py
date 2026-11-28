"""Actual core HTTP -> modeld -> pinned SDK -> loopback provider integration."""
from contextlib import closing
import hashlib
import http.client
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from uuid import uuid4
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit

from ai_union.model_service import ModelServiceClient, ServiceError
from tests.governance_support import GovernanceCase
from tests.model_access_support import ModelAccessCase
from tests import test_core_work as work_fixtures


@unittest.skipUnless(os.environ.get("UNION_BUN"), "Set UNION_BUN to the pinned Bun for the actual SDK integration")
class CoreModelHTTPTests(GovernanceCase):
    models = ModelAccessCase.models
    model_command = ModelAccessCase.model_command
    model_success = ModelAccessCase.model_success
    allow_documents = ModelAccessCase.allow_documents
    resource_grant = ModelAccessCase.resource_grant
    work_command = work_fixtures.CoreWorkTests.work_command
    works = work_fixtures.CoreWorkTests.works
    prepare_materials = work_fixtures.CoreWorkTests.prepare_materials
    start_attempt = work_fixtures.CoreWorkTests.start_attempt

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="union-core-model-http-")
        self.addCleanup(temporary.cleanup)
        self.private = Path(temporary.name)
        self.secret = "controlled-core-http-api-credential"
        for filename, value in (("admin.token", "controlled-admin-".ljust(48, "a")),
                                ("worker.token", "controlled-worker-".ljust(48, "w")), ("api.token", self.secret)):
            target = self.private / filename
            target.write_text(value, encoding="utf-8")
            target.chmod(0o600)
        stderr = (self.private / "host.log").open("w", encoding="utf-8")
        self.addCleanup(stderr.close)
        host = Path(__file__).resolve().parents[1] / "services/modeld/test/fixtures/core-modeld-host.ts"
        self.host = subprocess.Popen([os.environ["UNION_BUN"], str(host)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=stderr, text=True, encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.addCleanup(self.stop_host)
        self.host.stdin.write(json.dumps({"directory": str(self.private), "admin_token_file": "admin.token",
            "worker_token_file": "worker.token", "api_key_file": "api.token"}))
        self.host.stdin.close()
        ready = queue.Queue()
        threading.Thread(target=lambda: ready.put(self.host.stdout.readline()), daemon=True).start()
        self.provider = json.loads(ready.get(timeout=30))
        self.assertTrue(self.provider["ready"])
        config = self.private / "client.json"
        config.write_text(json.dumps({"origin": self.provider["modeld_url"], "admin_token_file": "admin.token",
            "worker_token_file": "worker.token"}), encoding="utf-8")
        config.chmod(0o600)
        environment = patch.dict(os.environ, {"UNION_MODELD_CONFIG": str(config)})
        environment.start()
        self.addCleanup(environment.stop)
        self.prepare()
        self.activate()

    def stop_host(self):
        if self.host.poll() is None:
            self.host.terminate()
            try:
                self.host.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.host.kill()
                self.host.wait(timeout=5)
        self.host.stdout.close()

    def wait_for(self, table, key):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            value = next(v for v in self.models()[table] if v["id"] == key)
            if value["status"] not in ("queued", "saving", "running"):
                return value
            time.sleep(0.05)
        self.fail("Actual SDK operation did not settle within the bounded test window")

    def stats(self):
        parts = urlsplit(self.provider["stats_url"])
        self.assertEqual(parts.hostname, "127.0.0.1")
        with closing(http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)) as connection:
            connection.request("GET", parts.path)
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            return json.loads(response.read())

    def test_core_save_and_two_stage_tool_exchange_use_actual_modeld_sdk_contract(self):
        saved, _ = self.model_success("save_connection", {"connection_id": "api-http", "expected_revision": 0,
            "name": "Controlled SDK connection", "profile": "openai_compatible", "model": self.provider["model_id"],
            "max_output_tokens": 64, "base_url": self.provider["provider_base_url"], "api_key": self.secret}, request_id="save-http-api")
        self.assertEqual(self.wait_for("operations", saved["operation_id"])["status"], "succeeded")
        self.assertEqual(self.stats()["inference_posts"], 0)
        self.allow_documents()
        self.resource_grant(2)
        original_call = ModelServiceClient.call

        def lose_submit_receipt(client, method, path, body=None, **kwargs):
            result = original_call(client, method, path, body, **kwargs)
            if method == "POST" and path == "/v1/requests":
                raise ServiceError("controlled_loss_after_actual_http_acceptance")
            return result

        with patch.object(ModelServiceClient, "call", lose_submit_receipt):
            receipt, request = self.model_success("start_model_check", {"connection_id": "api-http", "expected_revision": 1,
                "binding_id": None, "document_name": "selected.txt", "document_text": "Only this explicitly selected material is readable."})
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "succeeded", check)
        self.assertIn("explicitly selected material", check["output"])
        stats = self.stats()
        self.assertEqual(stats["real_model_calls"], 0)
        self.assertEqual(stats["inference_posts"], 2)
        first, second = [call["body"] for call in stats["calls"]]
        self.assertEqual(first["tools"][0]["function"]["name"], "read_document")
        tool = next(m for m in second["messages"] if m["role"] == "tool")
        material = json.loads(tool["content"])
        self.assertIn(material["challenge"], check["output"])
        native = next(m for m in second["messages"] if m["role"] == "assistant")
        self.assertEqual(native["tool_calls"][0]["extra_content"]["google"]["thought_signature"], "controlled-core-native-signature")
        self.assertTrue(all(call["session"].startswith(self.au_id + ":") for call in stats["calls"]))
        self.assertEqual([attempt["usage"]["input_tokens"] for attempt in check["attempts"]], [18, 18])
        self.assertTrue(all(attempt["usage"]["cost_minor"] is None for attempt in check["attempts"]))
        self.assertNotIn(self.secret, self.dump())
        self.assertNotIn(self.secret, json.dumps(self.models()))
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], receipt)
        self.model_success("set_connection", {"connection_id": "api-http", "expected_revision": 1, "enabled": True, "make_default": True})
        self.stop(); self.start()
        self.assertTrue(self.models()["connections"][0]["is_default"])
        self.assertEqual(self.models()["checks"][0]["output"], check["output"])
        self.assertEqual(self.stats()["inference_posts"], 2)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], 1)


    def provider_control(self, action):
        parts = urlsplit(self.provider["stats_url"])
        self.assertEqual(parts.hostname, "127.0.0.1")
        with closing(http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)) as connection:
            connection.request("POST", "/__probe/" + action, b"")
            response = connection.getresponse()
            self.assertEqual(response.status, 200, response.read())

    def wait_for_value(self, read, predicate, reason):
        deadline = time.monotonic() + 10
        while True:
            value = read()
            if predicate(value):
                return value
            self.assertLess(time.monotonic(), deadline, reason)
            time.sleep(0.05)

    def setup_responses_work(self):
        self.stop()
        self.start()
        saved, _ = self.model_success("save_connection", {"connection_id": "connection-a",
            "expected_revision": 0, "name": "Controlled Responses connection", "profile": "openai_responses",
            "model": "gpt-6-astra", "max_output_tokens": 64,
            "base_url": self.provider["provider_base_url"], "api_key": self.secret})
        self.assertEqual(self.wait_for("operations", saved["operation_id"])["status"], "succeeded")
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
            "enabled": True, "make_default": True})
        self.allow_documents()
        self.resource_grant(4)

    def test_responses_recovers_original_native_turn_and_attaches_input_to_next_request(self):
        self.setup_responses_work()
        self.prepare_materials()
        work_id = "work-overview"

        def work(kind, **data):
            status, body, _ = self.work_command(self.au_id, kind, {"work_id": work_id, **data})
            self.assertEqual(status, 200, body)
            return body["receipt"]

        def current():
            return self.works()["works"][0]

        status, value, _ = self.work_command(self.au_id, "start_work", work_fixtures.work_data(work_id=work_id))
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        attempt = self.start_attempt()
        submissions = []
        real_call = ModelServiceClient.call

        def lose_first_submit_receipt(client, method, path, body=None, **kwargs):
            result = real_call(client, method, path, body, **kwargs)
            if method == "POST" and path == "/v1/requests":
                submissions.append(body)
                if len(submissions) == 1:
                    raise ServiceError("controlled_loss_after_actual_http_acceptance")
            return result

        self.provider_control("hold")
        requirement = "追加要求：带上本次续接标记-73951"
        with patch.object(ModelServiceClient, "call", lose_first_submit_receipt):
            unknown = work("run_step")
            self.assertEqual(unknown["model_outcome"], "unknown", unknown)
            original = current()["steps"][0]
            before = self.wait_for_value(self.stats, lambda stats: stats["inference_posts"] > 0,
                                         "Responses provider did not receive original POST")
            self.assertEqual(before["inference_posts"], 1)
            added = work("append_work_input", input_id="input-responses-required", content=requirement,
                         reason="User adds a bounded requirement during the original Responses request")
            self.assertEqual(added["status"], "succeeded", added)
            self.assertEqual(current()["inputs"][0]["status"], "received")
            self.assertEqual(current()["input_cursor"], 0)
            self.assertEqual(current()["steps"][0], original)
            self.assertEqual(self.stats(), before)
            self.assertNotIn(requirement, json.dumps(before, ensure_ascii=False))
            self.stop()
            self.start()
            self.assertEqual(current()["inputs"][0]["id"], "input-responses-required")
            self.assertEqual(current()["responsible"]["member_id"], "member-ai-overview")
            self.assertEqual(current()["definition"]["version"], 1)
            self.provider_control("release")
            modeld = ModelServiceClient(os.environ["UNION_MODELD_CONFIG"])
            deadline = time.monotonic() + 10
            while True:
                remote = modeld.request(original["model_request_id"], self.au_id)
                if remote["state"] == "completed":
                    break
                self.assertNotIn(remote["state"], ("failed", "interrupted"), remote)
                self.assertLess(time.monotonic(), deadline, "Original Responses request did not settle")
                time.sleep(0.05)
            recovered = work("recover_work", attempt_id=attempt, reason="Recover by original modeld request")
            self.assertEqual(recovered["status"], "succeeded", recovered)
            first = current()["steps"][0]
            for key in ("step_ref", "attempt_id", "model_request_id", "request_sha256"):
                self.assertEqual(first[key], original[key])
            self.assertEqual(remote["request_digest"], first["request_sha256"])
            self.assertEqual(first["status"], "used")
            self.assertEqual(len(current()["tool_calls"]), 1)
            self.assertEqual(current()["input_cursor"], 0)
            self.assertEqual(len(submissions), 1)
            self.assertEqual(self.stats()["inference_posts"], 1)
            continued = work("run_step")
            self.assertEqual(continued["status"], "succeeded", continued)

        stats = self.stats()
        self.assertEqual(stats["real_model_calls"], 0)
        self.assertEqual(stats["inference_posts"], 2)
        self.assertEqual(len(submissions), 2)
        self.assertEqual(submissions[0]["id"], original["model_request_id"])
        self.assertNotEqual(submissions[0]["id"], submissions[1]["id"])
        body = stats["calls"][1]["body"]
        self.assertFalse(body["store"])
        self.assertNotIn("previous_response_id", body)
        inputs = body["input"]
        reasoning = next(item for item in inputs if item.get("type") == "reasoning")
        native_call = next(item for item in inputs if item.get("type") == "function_call")
        output = next(item for item in inputs if item.get("type") == "function_call_output")
        self.assertEqual(reasoning["encrypted_content"], "controlled-work-encrypted-reasoning")
        self.assertEqual(native_call["call_id"], "controlled-work-call")
        self.assertEqual(output["call_id"], native_call["call_id"])
        self.assertEqual(json.loads(output["output"])["content"], "# 概览\n")
        user_inputs = [part["text"] for item in inputs if item.get("role") == "user"
                       for part in item["content"] if part["type"] == "input_text"]
        self.assertEqual(user_inputs.count(requirement), 1)
        card = current()
        self.assertEqual([item["id"] for item in card["attempts"]], [attempt])
        self.assertEqual(len(card["inputs"][0]["attachments"]), 1)
        self.assertEqual(card["inputs"][0]["status"], "consumed")
        self.assertEqual(card["input_cursor"], 1)
        result, = card["results"]
        status, body, _ = self.request("/api/v1/work/results?" + urlencode({
            "organization_id": self.au_id, "work_id": work_id, "id": result["id"]}))
        self.assertEqual(status, 200, body)
        self.assertIn(requirement, body["content"])
        self.assertIn("概览", body["content"])
        self.assertEqual(result["input_cursor"], 1)
        self.assertEqual([item["usage"]["input_tokens"] for item in card["steps"]], [17, 41])
        claim = self.models()["capabilities"]["profile_scope"]["openai_responses"]["capabilities"]["long_job_new_input"]
        self.assertEqual(claim["status"], "controlled", claim)
        self.assertIn("下一", claim["note"])
        self.assertIn("不支持", claim["note"])


    def test_responses_automatic_work_delivers_append_with_the_original_attempt(self):
        self.setup_responses_work()
        material = "受控资料：原始收入编号 8041"
        work_id = "work-overview"
        requirement = "追加要求：同时列出校验编号 5821"

        def work(kind, data, **kwargs):
            status, body, _ = self.work_command(self.au_id, kind, data, **kwargs)
            self.assertEqual(status, 200, body)
            self.assertEqual(body["receipt"]["status"], "succeeded", body)
            return body["receipt"]

        def current():
            return self.works()["works"][0]

        material_id = "material-" + uuid4().hex
        work("import_material", {"material_id": material_id, "name": "overview.md",
            "content": material, "source": "paste", "reason": "Select synthetic material for the work"})
        scope = hashlib.sha256(self.au_id.encode("utf-8")).hexdigest()[:24]
        self.provider_control("hold")
        try:
            accepted = work("start_work_intent", work_fixtures.work_data(work_id=work_id,
                materials_root=material_id, material_version=1, constraints="Only read the selected material",
                delivery_mode="automatic_text"), request_id=f"intent-{scope}-{uuid4().hex}")
            before = self.wait_for_value(self.stats, lambda stats: stats["inference_posts"] > 0,
                                         "Automatic work did not submit the first Responses request")
            original = current()["steps"][0]
            self.assertEqual(before["inference_posts"], 1)
            self.assertEqual(original["attempt_id"], accepted["attempt_id"])
            work("append_work_input", {"work_id": work_id, "input_id": "input-responses-automatic",
                "content": requirement, "reason": "Append while the first request is running"})
            self.assertEqual(current()["inputs"][0]["status"], "received")
            self.assertEqual(self.stats(), before)
        finally:
            self.provider_control("release")
        delivered = self.wait_for_value(current, lambda card: card["status"] == "delivered",
                                        "Automatic Responses work did not adopt and deliver its result")
        stats = self.stats()
        self.assertEqual(stats["inference_posts"], 2)
        self.assertEqual(stats["real_model_calls"], 0)
        self.assertNotIn(requirement, json.dumps(stats["calls"][0]["body"], ensure_ascii=False))
        next_input = stats["calls"][1]["body"]["input"]
        self.assertTrue(any(item.get("role") == "user" and
            any(part.get("text") == requirement for part in item["content"]) for item in next_input))
        self.assertEqual([item["id"] for item in delivered["attempts"]], [accepted["attempt_id"]])
        self.assertEqual(delivered["steps"][0]["model_request_id"], original["model_request_id"])
        self.assertEqual(delivered["intent"]["id"], accepted["intent_id"])
        self.assertEqual(delivered["input_cursor"], 1)
        self.assertEqual(len(delivered["inputs"][0]["attachments"]), 1)
        status, result, _ = self.request("/api/v1/work/results?" + urlencode({
            "organization_id": self.au_id, "work_id": work_id, "id": delivered["delivered_result_id"]}))
        self.assertEqual(status, 200, result)
        self.assertIn(requirement, result["content"])
        self.assertIn(material, result["content"])


if __name__ == "__main__":
    unittest.main()
