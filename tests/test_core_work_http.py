"""End-to-end: the HTTP API drives a real loopback modeld double through run_step."""
import json
import tempfile
import uuid
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from ai_union.model_service import ModelServiceClient
from ai_union.work_transport import ModeldWorkTransport
from tests.model_access_support import ModelAccessCase
from tests.test_work_transport_http import ModeldDouble

CONNECTION = {"id": "connection-a", "revision": 2, "grant_ref": "grant-a", "grant_revision": 3,
              "model": "model-a", "max_output_tokens": 1024, "task_ms": 30000}


def work_data(**changes):
    data = {"work_id": "work-http", "title": "项目概览", "member_name": "资料整理 Agent",
            "goal": "阅读授权资料写一份概览", "member_id": "m-http", "binding_id": "b-http",
            "mandate_id": "ma-http", "definition_id": "d-http", "connection_id": "connection-a",
            "expected_revision": 1, "materials_root": "project-docs", "max_calls": 2,
            "tools": ["read_document"], "reason": "端到端验证"}
    data.update(changes)
    return data


class WorkHttpChainTests(ModelAccessCase):
    def setUp(self):
        super().setUp()
        ModeldDouble.seen = []
        ModeldDouble.state = "completed"
        ModeldDouble.post_status = 202
        self.double = ThreadingHTTPServer(("127.0.0.1", 0), ModeldDouble)
        self.double_thread = threading.Thread(target=self.double.serve_forever, daemon=True)
        self.double_thread.start()
        self.tokens = tempfile.TemporaryDirectory()
        root = Path(self.tokens.name)
        (root / "admin.token").write_text("a" * 40, encoding="utf-8")
        (root / "worker.token").write_text("b" * 40, encoding="utf-8")
        self.config = root / "modeld.json"
        self.config.write_text(json.dumps({
            "origin": "http://127.0.0.1:%d" % self.double.server_address[1],
            "admin_token_file": "admin.token", "worker_token_file": "worker.token"}), encoding="utf-8")
        for private_file in (self.config, root / "admin.token", root / "worker.token"):
            private_file.chmod(0o600)
        self.app.work.transport_factory = self.channel

    def tearDown(self):
        self.double.shutdown()
        self.double_thread.join(timeout=5)
        self.double.server_close()
        self.tokens.cleanup()
        super().tearDown()

    def channel(self, au_id, connection):
        return ModeldWorkTransport(ModelServiceClient(str(self.config)), au_id, CONNECTION,
                                   sleep=lambda _: None, timeout_seconds=10)

    def adopt_default(self):
        return self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                                     "enabled": True, "make_default": True})

    def work_command(self, au_id, kind, data):
        request = {"id": str(uuid.uuid4()), "organization_id": au_id,
                   "base_version": self.read()["au"]["version"], "kind": kind, "data": data}
        return self.request("/api/v1/work/commands", request)

    def prepare_work(self):
        self.prepare()
        self.saved()
        self.adopt_default()
        self.allow_documents()
        directory = Path(self.root) / "authorized-docs"
        (directory / "nested").mkdir(parents=True, exist_ok=True)
        (directory / "nested" / "a.md").write_bytes("a 正文\n".encode("utf-8"))
        (Path(self.root) / "document-roots.json").write_text(
            json.dumps({"version": 1, "roots": {"project-docs": str(directory)}}, ensure_ascii=False), encoding="utf-8")
        status, value, _ = self.work_command(self.au_id, "start_work", work_data())
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        status, started, _ = self.work_command(self.au_id, "start_attempt", {"work_id": "work-http"})
        self.assertEqual(started["receipt"]["status"], "succeeded", started)

    def run_step(self):
        return self.work_command(self.au_id, "run_step", {"work_id": "work-http"})

    def test_a_step_over_real_http_executes_the_tool_and_files_a_candidate_result(self):
        self.prepare_work()
        ModeldDouble.result = {"message": {"role": "assistant", "content": None,
                                           "tool_calls": [{"id": "c1", "type": "function",
                                                           "function": {"name": "read_document",
                                                                        "arguments": "{\"path\": \"nested/a.md\"}"}}]},
                               "usage": {"input_tokens": 5, "output_tokens": 2}}
        ModeldDouble.state = "completed"
        status, value, _ = self.run_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["tool_calls"], 1)
        card = [w for w in self.request("/api/v1/work?organization_id=" + self.au_id)[1]["works"]
                if w["id"] == "work-http"][0]
        self.assertEqual([c["tool"] for c in card["tool_calls"]], ["read_document"])
        self.assertEqual(card["steps"][0]["status"], "used")
        self.assertEqual(card["steps"][0]["usage"], {"input_tokens": 5, "output_tokens": 2})
        self.assertEqual(card["steps"][0]["cost_status"], "unknown")

        ModeldDouble.result = {"message": {"role": "assistant", "content": "# 概览\n"}, "usage": {}}
        status, value, _ = self.run_step()
        self.assertEqual(value["receipt"]["result"], True, value)
        card = [w for w in self.request("/api/v1/work?organization_id=" + self.au_id)[1]["works"]
                if w["id"] == "work-http"][0]
        self.assertEqual(len(card["results"]), 1)
        self.assertEqual(card["results"][0]["status"], "candidate")
        self.assertTrue(any(entry[0] == "POST" and entry[1] == "/v1/requests" for entry in ModeldDouble.seen))


if __name__ == "__main__":
    unittest.main()
