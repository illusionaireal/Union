"""Actual core HTTP -> modeld -> pinned SDK -> loopback provider integration."""
from contextlib import closing
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
from unittest.mock import patch
from urllib.parse import urlsplit

from ai_union.model_service import ModelServiceClient, ServiceError
from tests.governance_support import GovernanceCase
from tests.model_access_support import ModelAccessCase


@unittest.skipUnless(os.environ.get("UNION_BUN"), "Set UNION_BUN to the pinned Bun for the actual SDK integration")
class CoreModelHTTPTests(GovernanceCase):
    models = ModelAccessCase.models
    model_command = ModelAccessCase.model_command
    model_success = ModelAccessCase.model_success
    allow_documents = ModelAccessCase.allow_documents
    resource_grant = ModelAccessCase.resource_grant

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


if __name__ == "__main__":
    unittest.main()
