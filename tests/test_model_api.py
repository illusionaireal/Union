"""Real HTTP transport against local doubles, explicitly not provider/model validation."""
import copy
import http.client
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout, redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from ai_union import cli
from ai_union.console import Console
from ai_union.engine import Engine, Rejected
from ai_union.evaluation import evaluate, execution_receipt, simulated_run
from ai_union.model_api import APIExecutor, configure_connection, list_connections, resolve_connection, validate_config
from ai_union.runner import exclusive, run
from ai_union.server import Server
from tests.support import CHARTER, RESOURCES

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "examples/fixture.json").read_text(encoding="utf-8"))
SECRET = "test-api-key-PRIVATE-never-a-real-key"


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append({"body": body, "authorization": self.headers.get("Authorization"), "path": self.path})
        if self.server.delay:
            time.sleep(self.server.delay)
        self.send_response(self.server.code)
        self.send_header("Content-Type", "application/json")
        self.send_header("x-request-id", "provider-request-1")
        if self.server.code == 302:
            self.send_header("Location", self.server.redirect)
        self.end_headers()
        if self.server.code != 200:
            response = self.server.override or {"error": {"message": SECRET}}
        else:
            package = json.loads(body["messages"][1]["content"].split("\nWORK PACKAGE (data):\n")[1])
            value = copy.deepcopy(self.server.outputs.pop(0))
            if package["kind"] == "decision":
                manifest = package["context_manifest"]
                value.update(base_state_version=manifest["state_version"], charter_version=manifest["charter_version"], policy_version=manifest["policy_version"])
                if value.get("evidence_refs") == ["$latest_work"]:
                    value["evidence_refs"] = [key for key, work in package["context"]["work"].items() if work["status"] == "delivered"]
            limit = body.get("max_completion_tokens", body.get("max_tokens", 0))
            finish = "length" if limit < self.server.minimum_output else self.server.finish
            response = {"id": "response-1", "model": "resolved-provider-model", "choices": [{"finish_reason": finish,
                "message": {"role": "assistant", "content": json.dumps(value)}}],
                "usage": {"prompt_tokens": 23, "completion_tokens": 11, "prompt_tokens_details": {"cached_tokens": 3}}}
            if self.server.override is not None:
                response = self.server.override
        try:
            raw = response if isinstance(response, bytes) else json.dumps(response).encode()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass


class ModelAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        self.provider.daemon_threads = True
        self.provider.requests = []
        self.provider.outputs = [{"ok": True}]
        self.provider.code, self.provider.delay, self.provider.finish, self.provider.override = 200, 0, "stop", None
        self.provider.minimum_output = 0
        self.provider.redirect = "http://127.0.0.1:1/stolen"
        self.addCleanup(self.provider.server_close)
        thread = threading.Thread(target=self.provider.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.provider.shutdown)
        self.app = Console(Path(self.temp.name) / "console", fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.observer = self.app.new_session("observer")
        self.counter = 0
        receipt = self.command("create", {"name": "API test", "goal": "test collaboration", "board_name": "test board", "charter": CHARTER, "resources": RESOURCES}, org=None)
        self.org = receipt["organization_id"]
        self.e = self.app.engine(self.board, self.org)
        self.config = {"name": "Local test double", "base_url": f"http://127.0.0.1:{self.provider.server_port}/v1",
                       "model": "test-model", "response_format": "json_schema", "token_limit_field": "max_completion_tokens",
                       "max_output_tokens": 4096, "timeout_seconds": 3, "enabled": True}

    def command(self, kind, data, org="current", request_id=None, version=None, token=None):
        self.counter += 1
        oid = getattr(self, "org", None) if org == "current" else org
        if version is None and oid:
            version = self.e.state()["version"]
        return self.app.command(token or self.board, {"id": request_id or f"api-command-{self.counter}", "kind": kind,
                    "organization_id": oid, "base_version": version, "data": data})

    def configure(self, config=None, **extra):
        return self.command("api_connection", {"connection_id": "primary", "config": config or self.config,
                                                "api_key": SECRET, "reason": "test configuration"} | extra)

    def bind(self):
        return self.command("api_binding", {"connection_id": "primary", "reason": "test binding"})

    def probe(self, **data):
        receipt = self.command("api_test", {"connection_id": "primary", "allow_unknown_cost": True} | data)
        self.app.join_jobs()
        return self.app.receipt(self.board, self.org, receipt["id"])

    def test_secret_stays_in_private_table_and_never_in_command_or_metadata(self):
        receipt = self.configure()
        self.assertEqual(receipt["status"], "succeeded")
        self.assertTrue(receipt["connection"]["has_api_key"])
        self.bind()
        with self.e.read_transaction() as cx:
            self.assertEqual(cx.execute("SELECT api_key FROM model_connections").fetchone()[0], SECRET)
            public = [r[0] for r in cx.execute("SELECT payload FROM commands")]
        public += [json.dumps(self.e.state()), json.dumps(self.e.events()), json.dumps(self.app.observe(self.board, self.org)),
                   json.dumps(self.app.model_connections(self.board, self.org)), json.dumps(receipt), json.dumps(self.e.context())]
        self.assertNotIn(SECRET, "\n".join(public))
        result = self.probe()
        self.assertEqual(result["status"], "succeeded")
        self.assertNotIn(SECRET, json.dumps(result))
        for path in (self.e.root / "executions").rglob("*.json"):
            self.assertNotIn(SECRET, path.read_text())
        self.assertEqual(self.provider.requests[0]["authorization"], "Bearer " + SECRET)
        self.assertNotIn(SECRET, json.dumps(self.provider.requests[0]["body"]))

    def test_configuration_is_transactional_versioned_idempotent_and_bound(self):
        version = self.e.state()["version"]
        data = {"connection_id": "primary", "config": self.config, "api_key": SECRET, "reason": "test"}
        a = self.command("api_connection", data, request_id="save-key", version=version)
        self.assertEqual(a, self.command("api_connection", data, request_id="save-key", version=version))
        with self.assertRaises(Rejected):
            self.command("api_connection", data | {"api_key": "changed"}, request_id="save-key", version=version)
        self.assertEqual(self.command("api_connection", data, version=version)["status"], "rejected")
        self.bind()
        self.command("model", {"model": "codex-default", "reason": "test preserve binding"})
        self.assertEqual(self.e.state()["execution_config"]["api_connection_id"], "primary")
        self.assertEqual(resolve_connection(self.e)["revision"], 1)
        self.command("api_connection", {"connection_id": "primary", "config": self.config | {"model": "new-model"}, "reason": "keep key"})
        self.assertEqual(resolve_connection(self.e)["revision"], 2)
        self.app.close()
        self.app = Console(self.app.root, fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.assertEqual(resolve_connection(self.e)["config"]["model"], "new-model")
        self.assertEqual(list_connections(self.e)[0]["revision"], 2)
        self.assertFalse(self.provider.requests)

    def test_observer_scope_board_key_and_running_changes_are_rejected(self):
        with self.assertRaises(Rejected):
            self.configure_with_token(self.observer)
        with self.assertRaises(Rejected):
            self.app.model_connections(self.observer, self.org)
        with self.assertRaises(Rejected):
            self.app.model_connections(self.app.new_session("board", organizations=[]), self.org)
        with self.assertRaises(Rejected):
            configure_connection(self.e, "wrong-key", "primary", self.config, "test", SECRET)
        with exclusive(self.e):
            self.assertEqual(self.configure()["status"], "rejected")
        self.assertEqual(self.e.state()["version"], 0)

    def configure_with_token(self, token):
        return self.command("api_connection", {"connection_id": "primary", "config": self.config, "api_key": SECRET, "reason": "test"}, token=token)

    def test_connection_config_rolls_back_with_failed_command(self):
        original = self.app._execute
        def fail(e, request):
            original(e, request)
            raise Rejected("injected rollback")
        with patch.object(self.app, "_execute", fail):
            self.assertEqual(self.configure()["status"], "rejected")
        self.assertEqual(list_connections(self.e), [])
        self.assertEqual(self.e.state()["version"], 0)

    def test_rejected_configuration_never_persists_accidentally_pasted_key(self):
        self.assertEqual(self.configure(reason="accidental pasted key " + SECRET)["status"], "rejected")
        with self.e.read_transaction() as cx:
            for row in cx.execute("SELECT payload,receipt FROM commands"):
                self.assertNotIn(SECRET, row[0] + row[1])
        self.assertNotIn(SECRET, json.dumps(self.e.events()))
        with self.assertRaises(Rejected):
            self.command("api_connection", {"connection_id": "primary", "config": self.config, "api_key": SECRET, "reason": "test"}, request_id=SECRET)

    def test_binding_and_key_rotation_cannot_publish_any_saved_key(self):
        self.configure()
        with self.assertRaises(Rejected):
            self.command("api_binding", {"connection_id": "primary", "reason": "paste " + SECRET})
        key = (self.e.root / "board.key").read_text()
        from ai_union.model_api import bind_connection
        with self.assertRaises(Rejected):
            bind_connection(self.e, key, "primary", "paste " + SECRET)
        self.configure(api_key="replacement-test-key")
        for secret in (SECRET, "replacement-test-key"):
            with self.subTest(secret=secret), self.assertRaises(Rejected):
                self.command("api_binding", {"connection_id": "primary", "reason": "paste " + secret})
            with self.assertRaises(Rejected):
                configure_connection(self.e, key, "primary", self.config, "paste " + secret, "")
        public = json.dumps(self.e.events()) + json.dumps(self.app.observe(self.observer, self.org))
        with self.e.read_transaction() as cx:
            public += "".join(row[0] + row[1] for row in cx.execute("SELECT payload,receipt FROM commands"))
        self.assertNotIn(SECRET, public)
        self.assertNotIn("replacement-test-key", public)

    def test_escaped_provider_credential_is_rejected_after_json_decoding(self):
        self.configure()
        self.provider.override = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"ok": True}), "ignored": SECRET}}]}).replace(SECRET, "".join("\\u%04x" % ord(c) for c in SECRET)).encode()
        self.assertEqual(self.probe()["status"], "failed")
        self.assertNotIn(SECRET, json.dumps(self.e.runs()) + json.dumps(self.e.events()))
        for path in (self.e.root / "executions").rglob("*.json"):
            self.assertNotIn(SECRET, path.read_text())

    def test_malformed_choice_and_message_are_failed_not_unknown(self):
        self.configure()
        for choices in ([7], [{"finish_reason": "stop", "message": 7}], [{"finish_reason": "stop", "message": {"content": "{\"ok\":true,\"ok\":false}"}}]):
            self.provider.outputs = [{"ok": True}]
            self.provider.override = {"choices": choices, "usage": {"prompt_tokens": 2, "completion_tokens": 3}}
            self.assertEqual(self.probe()["status"], "failed")
        self.assertEqual([r["status"] for r in self.e.runs()], ["failed"] * 3)
        self.assertTrue(all(r["usage"]["output_tokens"] == 3 for r in self.e.runs()))

    def test_response_capacity_is_bounded_and_does_not_store_body(self):
        self.configure()
        self.provider.override = b"x" * 1000001
        self.assertEqual(self.probe()["status"], "failed")
        self.assertEqual(len(self.provider.requests), 1)
        self.assertFalse((self.e.root / "executions" / self.e.runs()[0]["id"] / "result.json").exists())

    def test_invalid_config_and_endpoint_change_cannot_leak_saved_key(self):
        for change in ({"base_url": "http://example.com/v1"}, {"base_url": "https://user:pass@example.com/v1"},
                       {"base_url": "https://example.com/v1?key=secret"}, {"max_output_tokens": True},
                       {"timeout_seconds": 0}, {"response_format": "text"}, {"token_limit_field": "wrong"}):
            with self.subTest(change=change), self.assertRaises(Rejected):
                validate_config(self.config | change)
        self.configure()
        data = {"connection_id": "primary", "config": self.config | {"base_url": "https://different.example/v1"}, "reason": "different endpoint"}
        self.assertEqual(self.command("api_connection", data)["status"], "rejected")
        self.assertEqual(self.command("api_connection", data | {"api_key": ""})["status"], "succeeded")
        self.assertFalse(list_connections(self.e)[0]["has_api_key"])
        self.assertEqual(self.probe()["status"], "rejected")
        self.assertFalse(self.provider.requests)

    def test_connection_probe_preserves_pause_and_events_but_consumes_one_call(self):
        self.configure()
        self.command("pause", {})
        before = self.e.state()
        events = self.e.events(True)
        self.assertEqual(self.probe()["status"], "succeeded")
        self.assertTrue(self.e.paused())
        self.assertEqual(self.e.state()["members"], before["members"])
        self.assertEqual(self.e.events(True), events)
        self.assertEqual(len(self.e.runs()), 1)
        self.assertEqual(self.e.runs()[0]["kind"], "connection_test")
        usage = self.e.usage()[0]["usage"]
        self.assertEqual(usage["input_tokens"], 23)
        self.assertEqual(usage["output_tokens"], 11)
        self.assertEqual(usage["cached_input_tokens"], 3)
        self.assertIsNone(usage["cost"])
        self.assertEqual(usage["actual_model"], "resolved-provider-model")
        self.assertFalse(evaluate(self.e)["checks"]["real_executor_only"])

    def test_probe_requires_cost_acceptance_and_budget_and_is_not_replayed(self):
        self.configure()
        self.assertEqual(self.probe(allow_unknown_cost=False)["status"], "rejected")
        receipt = self.command("api_test", {"connection_id": "primary", "allow_unknown_cost": True}, request_id="one-probe")
        self.app.join_jobs()
        repeated = self.command("api_test", {"connection_id": "primary", "allow_unknown_cost": True}, request_id="one-probe", version=receipt["base_version"])
        self.assertEqual(repeated["status"], "succeeded")
        self.assertEqual(len(self.provider.requests), 1)
        self.command("resources", {"resources": RESOURCES | {"max_calls": 1}, "reason": "cap test"})
        self.assertEqual(self.probe()["status"], "rejected")
        self.assertEqual(len(self.provider.requests), 1)

    def test_api_request_format_and_explicit_compatibility_mode(self):
        self.configure(self.config | {"response_format": "json_object", "token_limit_field": "max_tokens"})
        self.assertEqual(self.probe()["status"], "succeeded")
        request = self.provider.requests[0]
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertEqual(request["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(request["body"]["max_tokens"], self.config["max_output_tokens"])
        self.assertNotIn("tools", request["body"])

    def test_whole_http_loop_is_persistent_and_explicitly_simulated(self):
        self.configure()
        self.bind()
        self.provider.outputs = copy.deepcopy(FIXTURE)
        receipt = self.command("start", {"executor": "api", "max_steps": 8, "allow_unknown_cost": True})
        self.app.join_jobs()
        receipt = self.app.receipt(self.board, self.org, receipt["id"])
        self.assertEqual(receipt["status"], "succeeded")
        report = evaluate(Engine(self.e.root))
        self.assertTrue(report["mechanism_scenario_passed"])
        self.assertEqual(report["status"], "simulated")
        self.assertFalse(report["real_agent_verified"])
        self.assertEqual(len(self.provider.requests), 6)
        self.assertEqual(len(self.e.state()["artifacts"]), 3)
        self.assertEqual(self.app.observe(self.board, self.org)["source"], "fixture")
        self.assertEqual(self.e.runs()[0]["package"]["execution"]["connection_revision"], 1)

    def test_authentication_error_and_redirect_never_retry_or_persist_provider_body(self):
        self.configure()
        for code in (401, 429, 302):
            self.provider.code = code
            self.assertEqual(self.probe()["status"], "failed")
        self.assertEqual(len(self.provider.requests), 3)
        self.assertNotIn(SECRET, json.dumps(self.e.events()) + json.dumps(self.e.runs()))
        self.assertEqual([r["status"] for r in self.e.runs()], ["failed"] * 3)

    def test_provider_error_is_unknown_blocks_further_calls_and_retains_reservation(self):
        self.configure()
        self.provider.code = 503
        self.assertEqual(self.probe()["status"], "unknown")
        self.assertEqual(self.e.runs()[0]["status"], "unknown")
        self.assertEqual(self.probe()["status"], "rejected")
        self.assertEqual(len(self.provider.requests), 1)
        self.assertEqual(self.e.status()["budget"]["calls_reserved"], 1)

    def test_whole_request_deadline_preserves_unknown_without_retry(self):
        self.configure(self.config | {"timeout_seconds": 1})
        self.provider.delay = 2
        start = time.monotonic()
        self.assertEqual(self.probe()["status"], "unknown")
        self.assertLess(time.monotonic() - start, 1.8)
        time.sleep(0.1)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertFalse((self.e.root / "executions" / self.e.runs()[0]["id"] / "result.json").exists())

    def test_invalid_truncated_and_tool_results_keep_usage_and_do_not_form_organization(self):
        self.configure()
        for override, finish in ((None, "length"), ({"choices": [{"finish_reason": "stop", "message": {"content": "{}", "tool_calls": [{"id": "bad"}]}}]}, "stop"), (b"not json", "stop")):
            self.provider.outputs = [{"ok": True}]
            self.provider.override, self.provider.finish = override, finish
            self.assertEqual(self.probe()["status"], "failed")
        self.assertEqual(self.e.runs()[0]["usage"]["output_tokens"], 11)
        self.assertEqual(self.e.state()["members"], {})

    def test_configuration_version_is_fixed_for_job_and_updates_are_locked(self):
        self.configure()
        self.bind()
        self.provider.delay = 0.2
        self.provider.outputs = copy.deepcopy(FIXTURE)
        receipt = self.command("start", {"executor": "api", "max_steps": 1, "allow_unknown_cost": True})
        self.assertEqual(receipt["execution"]["connection_revision"], 1)
        self.assertEqual(self.configure(self.config | {"model": "new-model"})["status"], "rejected")
        self.app.join_jobs()
        self.assertEqual(self.provider.requests[0]["body"]["model"], "test-model")
        self.assertEqual(self.configure(self.config | {"model": "new-model"})["status"], "succeeded")
        self.assertEqual(self.e.runs()[0]["usage"]["connection_revision"], 1)

    def test_http_contract_uses_session_origin_and_redacted_connection_response(self):
        server = Server(self.app)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        def request(method, path, body=None, token=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=4)
            connection.request(method, path, body=json.dumps(body) if body else None,
                               headers={"Origin": server.origin, "Content-Type": "application/json", "Cookie": server.cookie_name + "=" + (token or self.board)})
            response = connection.getresponse()
            status, value = response.status, json.loads(response.read())
            connection.close()
            return status, value
        body = {"id": "save-http-key", "kind": "api_connection", "organization_id": self.org, "base_version": 0,
                "data": {"connection_id": "primary", "config": self.config, "api_key": SECRET, "reason": "HTTP configuration"}}
        status, result = request("POST", "/api/commands", body)
        self.assertEqual(status, 200)
        self.assertEqual(result["receipt"]["status"], "succeeded")
        status, result = request("GET", "/api/model-connections?organization_id=" + self.org)
        self.assertEqual(status, 200)
        self.assertTrue(result["connections"][0]["has_api_key"])
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(request("GET", "/api/model-connections?organization_id=" + self.org, token=self.observer)[0], 403)

    def test_cli_config_bind_probe_and_api_run_share_the_same_store(self):
        root = self.e.root
        config_file = Path(self.temp.name) / "config.json"
        config_file.write_text(json.dumps(self.config))
        key_file = root / "board.key"
        def call(arguments):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(["--root", str(root)] + arguments)
            self.assertNotIn(SECRET, out.getvalue() + err.getvalue())
            return code, json.loads(out.getvalue() or err.getvalue())
        with patch.dict(os.environ, {"UNION_TEST_API_KEY": SECRET}):
            self.assertEqual(call(["api-configure", "--connection-id", "primary", "--config", str(config_file), "--api-key-env", "UNION_TEST_API_KEY", "--board-key-file", str(key_file), "--reason", "test"])[0], 0)
        self.assertEqual(call(["api-bind", "--connection-id", "primary", "--board-key-file", str(key_file), "--reason", "test"])[0], 0)
        self.assertEqual(call(["api-test", "--board-key-file", str(key_file), "--allow-unknown-cost"])[0], 0)
        self.provider.outputs = copy.deepcopy(FIXTURE)
        code, result = call(["run", "--executor", "api", "--max-steps", "8", "--allow-unknown-cost"])
        self.assertEqual(code, 0)
        self.assertTrue(result["simulated"])
        self.assertEqual(call(["api-list"])[1]["connections"][0]["id"], "primary")
        self.assertTrue(evaluate(self.e)["mechanism_scenario_passed"])
        self.assertEqual(len(self.e.runs()), 7)

    def test_disabled_api_and_money_hard_cap_reject_before_http(self):
        self.configure()
        self.app.enable_api = False
        self.assertEqual(self.probe()["status"], "rejected")
        self.app.enable_api = True
        self.e.configure_resources((self.e.root / "board.key").read_text(), RESOURCES | {"max_cost": 100, "cost_reserve_per_call": 1}, "test")
        self.assertEqual(self.probe()["status"], "rejected")
        self.assertFalse(self.provider.requests)

    def test_provider_receipt_classification_accepts_api_and_checks_version(self):
        # Synthetic receipt contract only; this is not an actual provider run.
        metadata = {"connection_id": "primary", "connection_revision": 2, "protocol": "openai_chat_completions",
                    "requested_model": "test-model", "transport_source": "provider_api"}
        folder = self.e.root / "executions" / "receipt-contract"
        folder.mkdir(parents=True)
        (folder / "result.json").write_text("{}")
        receipt_path = folder / "receipt.json"
        receipt_path.write_text(json.dumps(metadata | {"response_id": "provider-response"}))
        record = {"id": "receipt-contract", "executor": "api", "status": "delivered", "usage": {}, "package": {"execution": metadata}}
        self.assertFalse(simulated_run(record))
        self.assertTrue(execution_receipt(self.e, record))
        receipt_path.write_text(json.dumps(metadata | {"connection_revision": 1, "response_id": "provider-response"}))
        self.assertFalse(execution_receipt(self.e, record))
        self.assertTrue(simulated_run(record | {"package": {"execution": metadata | {"transport_source": "local_test"}}}))

    def test_rejected_api_parameter_is_actionable_without_exposing_provider_body(self):
        self.configure()
        self.bind()
        self.provider.code = 400
        self.provider.override = {"error": {"param": "response_format", "message": "unsupported " + SECRET}}
        result = self.probe()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure"]["code"], "api_request_rejected")
        self.assertEqual(result["failure"]["parameter"], "response_format")
        self.assertIn("JSON Object", result["failure"]["recovery"])
        view = self.app.observe(self.board, self.org)
        self.assertEqual(view["runs"][-1]["failure"], result["failure"])
        self.assertNotIn(SECRET, json.dumps([result, view]))
        self.assertEqual(len(self.provider.requests), 1)  # No automatic retry or fallback.

    def test_truncated_output_reports_cause_and_retains_usage(self):
        self.configure()
        self.bind()
        self.provider.finish = "length"
        result = self.probe()
        self.assertEqual(result["failure"]["code"], "api_output_truncated")
        self.assertIn("输出", result["failure"]["recovery"])
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 11)
        self.assertEqual(len(self.provider.requests), 1)

    def test_connection_probe_honors_configured_output_budget_for_reasoning_models(self):
        self.configure()
        self.bind()
        self.provider.minimum_output = 1024
        result = self.probe()
        self.assertEqual(result["status"], "succeeded", result)
        self.assertEqual(self.provider.requests[-1]["body"]["max_completion_tokens"], self.config["max_output_tokens"])
        self.assertEqual(len(self.provider.requests), 1)

    def test_bootstrap_validation_failure_is_visible_in_run_and_start_receipt(self):
        self.configure()
        self.bind()
        self.provider.outputs = [{"issue": "test", "rationale": "test", "expected_effect": "test", "evidence_refs": [], "operations": []}]
        receipt = self.command("start", {"executor": "api", "max_steps": 2, "allow_unknown_cost": True})
        self.app.join_jobs()
        receipt = self.app.receipt(self.board, self.org, receipt["id"])
        view = self.app.observe(self.board, self.org)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(receipt["failure"]["code"], "runtime_validation")
        self.assertIn("至少两名", receipt["failure"]["rule"])
        self.assertEqual(view["runs"][-1]["failure"], receipt["failure"])
        self.assertTrue(any("至少两名" in reason for reason in view["blocked_reasons"]))
        self.assertEqual(len(self.provider.requests), 1)
