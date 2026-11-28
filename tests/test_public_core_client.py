"""U-101/U-102: a standard-library client against a separate, unmodified Core process.

No Core/test helper imports, launch tickets, SQLite access or model requests.
Run: python -m unittest tests.test_public_core_client -v
"""
import copy
import http.client
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from urllib.parse import urlencode


REPO = Path(__file__).resolve().parents[1]
PASSWORD = "u101-synthetic-account-password"


def creation(request_id):
    return {
        "id": request_id, "organization_id": None, "base_version": None,
        "kind": "create_v1", "data": {
            "name": "Public client AU", "goal": "Prepare an independently readable AU",
            "board_name": "Shared display name is not authority",
            "charter": {
                "text": "Synthetic local preparation only; no autonomous business or external actions.",
                "allowed_operations": [], "allowed_tools": [],
                "reserved_matters": ["resources", "charter", "dissolution"],
                "board_can_amend": True,
            },
            "resources": {"max_calls": 1, "timeout_seconds": 30},
        },
    }


class HttpClient:
    def __init__(self, port):
        self.port = port
        self.origin = f"http://127.0.0.1:{port}"
        self.cookie = None
        self.requests = []

    def request(self, path, body=None, *, headers=None, discard_response=False):
        method = "GET" if body is None else "POST"
        sent = {"Content-Type": "application/json", "Origin": self.origin}
        if self.cookie:
            sent["Cookie"] = self.cookie
        sent.update(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        self.requests.append((method, path))
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, sent)
            response = conn.getresponse()
            if discard_response:
                # The server has answered, but this client deliberately retains no receipt.
                # Recover by GET using the request id; never silently retry this POST.
                return None
            payload = json.loads(response.read())
            cookie = SimpleCookie()
            cookie.load(response.getheader("Set-Cookie") or "")
            if cookie:
                self.cookie = "; ".join(f"{key}={value.value}" for key, value in cookie.items())
            return response.status, payload
        finally:
            conn.close()


class PublicCoreHost(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="union-u101-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.process = None
        self.output = None
        self.addCleanup(self.stop)
        self.start()
        self.owner = HttpClient(self.port)
        self.owner_session = self.authenticate(self.owner, "setup", "owner")

    def host_environment(self):
        return {}

    def process_environment(self):
        # Do not pass a real host model/service configuration into the temporary Core.
        return {key: value for key, value in os.environ.items() if not key.startswith("UNION_")}

    def start(self):
        env = self.process_environment()
        env.update(PYTHONPATH=str(REPO), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        env.update(self.host_environment())
        log = self.root / "startup.log"
        self.output = log.open("wb")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "ai_union.server", "--root", str(self.root / "core"),
             "--port", "0", "--disable-api"],
            cwd=REPO, env=env, stdin=subprocess.DEVNULL, stdout=self.output,
            stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            self.assertIsNone(self.process.poll(), "temporary Core exited before readiness")
            match = re.search(r"http://127\.0\.0\.1:(\d+)", log.read_text(encoding="utf-8", errors="replace"))
            if match:
                self.port = int(match[1])
                self.assertEqual(HttpClient(self.port).request("/api/auth/status")[0], 200)
                return
            time.sleep(0.025)
        self.fail("temporary Core did not become ready within 30 seconds")

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
            self.process.wait(timeout=15)
            self.process = None
        if self.output is not None:
            self.output.close()
            self.output = None

    def authenticate(self, client, action, username):
        status, result = client.request("/api/auth/" + action,
                                        {"username": username, "password": PASSWORD, "remember": True})
        self.assertEqual(status, 200)
        self.assertEqual(result["session"]["core_protocol"], "core.au.v1")
        return result["session"]

    def get(self, client, path):
        status, result = client.request(path)
        self.assertEqual(status, 200, result)
        return result

    def create(self, client, request):
        status, result = client.request("/api/commands", request)
        self.assertEqual(status, 200, result)
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "succeeded", result)
        return receipt

    def listed(self, client):
        return self.get(client, "/api/session")["organizations"]

    def assert_error(self, result, status, code):
        self.assertEqual(result[0], status, result)
        self.assertEqual(result[1]["code"], code)
        self.assertEqual(set(result[1]), {"error", "code"})


class PublicCoreClientTests(PublicCoreHost):
    def test_prepared_creation_protocol_versions_and_public_audit_link(self):
        request = creation("public-create")
        receipt = self.create(self.owner, request)
        au_id = receipt["organization_id"]
        view = self.get(self.owner, "/api/v1/aus/" + au_id)
        au = view["au"]
        self.assertEqual(view["protocol"], "core.au.v1")
        self.assertEqual((au["id"], au["runtime_profile"], au["schema_version"]), (au_id, "core_v1", 1))
        self.assertEqual((au["version"], au["charter_version"], au["policy_version"]), (0, 1, 0))
        self.assertEqual((au["autonomy_state"], au["resource_state"]), ("inactive", "planned"))
        self.assertEqual(au["charter"], request["data"]["charter"])
        self.assertEqual(au["resources"], request["data"]["resources"])
        self.assertEqual(au["governance_root"], {
            "creator_principal_id": self.owner_session["principal_id"],
            "governor_principal_id": self.owner_session["principal_id"],
        })
        self.assertFalse(view["capabilities"]["autonomous_business"])
        self.assertEqual(view["capabilities"]["charter_enforcement"], "not_activated")
        self.assertEqual((receipt["id"], receipt["kind"], receipt["base_version"], receipt["actor"]),
                         (request["id"], "create_v1", None, "account:owner"))
        self.assertTrue(receipt["created_at"])
        self.assertEqual(self.get(self.owner, "/api/v1/receipts?id=public-create")["receipt"], receipt)
        self.assertEqual(self.listed(self.owner), [{"id": au_id, "name": au["name"], "profile": "core_v1"}])
        public = json.dumps({"view": view, "receipt": receipt})
        for private in (PASSWORD, self.owner.cookie.split("=", 1)[1], json.dumps(str(self.root))[1:-1]):
            self.assertNotIn(private, public)
        for private_key in ("password", "recovery_code", "token", "board_key", "folder", "database"):
            self.assertNotIn('"' + private_key + '"', public)

    def test_ordinary_account_creates_own_au_but_cannot_read_or_replay_another(self):
        request = creation("owned-create")
        receipt = self.create(self.owner, request)
        other = HttpClient(self.port)
        session = self.authenticate(other, "register", "participant")
        self.assertEqual(session["role"], "core")
        self.assertFalse(session["platform_admin"])
        self.assertNotEqual(session["principal_id"], self.owner_session["principal_id"])
        self.assertEqual(self.listed(other), [])
        denials = []
        for path in ("/api/v1/aus/" + receipt["organization_id"], "/api/v1/aus/absent-au",
                     "/api/v1/receipts?id=owned-create", "/api/v1/receipts?id=absent-request"):
            result = other.request(path)
            self.assert_error(result, 403, "not_authorized")
            denials.append(result[1])
        self.assertTrue(all(value == denials[0] for value in denials))
        self.assertNotIn(self.owner_session["principal_id"], json.dumps(denials))
        self.assert_error(other.request("/api/commands", request), 403, "not_authorized")
        changed = copy.deepcopy(request)
        changed["data"]["goal"] = "Try to take over a different principal's request"
        self.assert_error(other.request("/api/commands", changed), 403, "not_authorized")
        own = self.create(other, creation("participant-create"))
        self.assertNotEqual(own["organization_id"], receipt["organization_id"])
        view = self.get(other, "/api/v1/aus/" + own["organization_id"])
        self.assertEqual(view["au"]["governance_root"]["creator_principal_id"], session["principal_id"])
        self.assertEqual(len(self.listed(self.owner)), 1)
        self.assertEqual(len(self.listed(other)), 1)
        self.assertEqual(self.get(self.owner, "/api/v1/receipts?id=owned-create")["receipt"], receipt)

    def test_same_principal_new_session_replay_and_conflict_preserve_original(self):
        request = creation("replay-create")
        receipt = self.create(self.owner, request)
        before = self.get(self.owner, "/api/v1/aus/" + receipt["organization_id"])
        second = HttpClient(self.port)
        session = self.authenticate(second, "login", "owner")
        self.assertEqual(session["principal_id"], self.owner_session["principal_id"])
        self.assertNotEqual(second.cookie, self.owner.cookie)
        self.assertEqual(self.create(second, request), receipt)
        changed = copy.deepcopy(request)
        changed["data"]["goal"] = "Changed intent under the same request id"
        self.assert_error(second.request("/api/commands", changed), 409, "id_conflict")
        self.assertEqual(self.get(second, "/api/v1/aus/" + receipt["organization_id"]), before)
        self.assertEqual(self.get(second, "/api/v1/receipts?id=replay-create")["receipt"], receipt)
        self.assertEqual(len(self.listed(second)), 1)

    def test_invalid_identity_version_and_types_do_not_consume_request_id(self):
        changes = [
            {"data": {"governor_principal_id": self.owner_session["principal_id"]}},
            {"data": {"runtime_profile": "legacy_v0"}}, {"data": {"active": True}},
            {"data": {"resources": {"max_calls": True, "timeout_seconds": 30}}},
            {"base_version": 0}, {"organization_id": "forged-existing-au"},
        ]
        for index, patch in enumerate(changes):
            with self.subTest(patch=patch):
                request = creation("invalid-" + str(index))
                invalid = copy.deepcopy(request)
                invalid.update({key: value for key, value in patch.items() if key != "data"})
                invalid["data"].update(patch.get("data", {}))
                before = self.listed(self.owner)
                self.assert_error(self.owner.request("/api/commands", invalid), 400, "invalid_request")
                self.assertEqual(self.listed(self.owner), before)
                self.assert_error(self.owner.request("/api/v1/receipts?id=" + request["id"]), 403, "not_authorized")
                self.create(self.owner, request)
                self.assertEqual(len(self.listed(self.owner)), len(before) + 1)

    def test_anonymous_and_cross_origin_requests_cannot_create(self):
        anonymous = HttpClient(self.port)
        request = creation("authenticated-only")
        self.assert_error(anonymous.request("/api/commands", request), 401, "not_authenticated")
        for path in ("/api/v1/aus/absent-au", "/api/v1/receipts?id=authenticated-only"):
            self.assert_error(anonymous.request(path), 401, "not_authenticated")
        for headers in ({"Origin": "https://untrusted.invalid"}, {"Host": "untrusted.invalid"},
                        {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.owner.request("/api/commands", request, headers=headers)[0], 403)
        self.assertEqual(self.listed(self.owner), [])
        self.assert_error(self.owner.request("/api/v1/receipts?id=authenticated-only"), 403, "not_authorized")
        self.create(self.owner, request)
        self.assertEqual(len(self.listed(self.owner)), 1)

    def test_discarded_response_is_recovered_by_original_id_without_second_post(self):
        request = creation("discarded-response")
        self.assertIsNone(self.owner.request("/api/commands", request, discard_response=True))
        receipt = self.get(self.owner, "/api/v1/receipts?id=discarded-response")["receipt"]
        self.assertEqual((receipt["id"], receipt["status"]), (request["id"], "succeeded"))
        au = self.get(self.owner, "/api/v1/aus/" + receipt["organization_id"])["au"]
        self.assertEqual(au["goal"], request["data"]["goal"])
        self.assertEqual(len(self.listed(self.owner)), 1)
        self.assertEqual(self.owner.requests.count(("POST", "/api/commands")), 1)

    def test_restart_and_normal_login_preserve_principal_au_versions_and_receipt(self):
        request = creation("restart-create")
        receipt = self.create(self.owner, request)
        view = self.get(self.owner, "/api/v1/aus/" + receipt["organization_id"])
        listed = self.listed(self.owner)
        principal = self.owner_session["principal_id"]
        self.stop()
        self.start()
        reopened = HttpClient(self.port)
        self.assertEqual(self.authenticate(reopened, "login", "owner")["principal_id"], principal)
        self.assertEqual(self.get(reopened, "/api/v1/aus/" + receipt["organization_id"]), view)
        self.assertEqual(self.get(reopened, "/api/v1/receipts?id=restart-create")["receipt"], receipt)
        self.assertEqual(self.listed(reopened), listed)
        self.assertEqual(self.create(reopened, request), receipt)
        self.assertEqual(self.listed(reopened), listed)


class PublicWorkClientHost(PublicCoreHost):
    """U-102: public work commands; modeld is an explicit grant-only HTTP double."""

    first_claim_platform_admin = True

    def setUp(self):
        self.grants = {}
        self.model_requests = []
        case = self

        class GrantOnly(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def answer(self, code, body):
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                case.model_requests.append(("GET", self.path))
                if self.headers.get("Authorization") != "Bearer " + "a" * 40:
                    return self.answer(403, {"error": "not_authorized"})
                grant = case.grants.get(self.path)
                return self.answer(200, grant) if grant else self.answer(404, {"error": "not_found"})

            def do_POST(self):
                # No inference is implemented. Unexpected dispatch must fail the test.
                case.model_requests.append(("POST", self.path))
                self.answer(403, {"error": "inference_disabled"})

        self.modeld = ThreadingHTTPServer(("127.0.0.1", 0), GrantOnly)
        self.model_thread = threading.Thread(target=self.modeld.serve_forever, daemon=True)
        self.model_thread.start()
        self.addCleanup(self.stop_modeld)
        super().setUp()
        self.client = HttpClient(self.port)
        self.session = self.authenticate(self.client, "register", "governor")
        self.assertFalse(self.session["platform_admin"])
        self.assertIs(self.owner_session["platform_admin"], self.first_claim_platform_admin)
        self.prepare_work_au()

    def stop_modeld(self):
        self.modeld.shutdown()
        self.model_thread.join(timeout=5)
        self.modeld.server_close()
        self.assertFalse(self.model_thread.is_alive())
        self.assertTrue(self.model_requests, "The real Core must have verified the configured grant")
        self.assertTrue(all(method == "GET" and path.startswith("/v1/grants/")
                            for method, path in self.model_requests), self.model_requests)

    def host_environment(self):
        config = self.root / "synthetic-modeld.json"
        config.write_text(json.dumps({
            "origin": "http://127.0.0.1:%d" % self.modeld.server_port,
            "admin_token_file": "synthetic-admin.token", "worker_token_file": "synthetic-worker.token",
        }), encoding="utf-8")
        config.chmod(0o600)
        for role, char in (("admin", "a"), ("worker", "w")):
            path = self.root / ("synthetic-" + role + ".token")
            path.write_text(char * 40, encoding="ascii")
            path.chmod(0o600)
        env = {"UNION_MODELD_CONFIG": str(config)}
        if self.first_claim_platform_admin:
            env["UNION_FIRST_CLAIM_PLATFORM_ADMIN"] = "1"
        return env

    def view(self):
        return self.get(self.client, "/api/v1/aus/" + self.au_id)

    def works(self):
        return self.get(self.client, "/api/v1/work?" + urlencode({"organization_id": self.au_id}))

    def receipt_path(self, request_id):
        return "/api/v1/governance/receipts?" + urlencode({"organization_id": self.au_id, "id": request_id})

    def command(self, family, kind, data, request_id):
        request = {"id": request_id, "organization_id": self.au_id,
                   "base_version": self.view()["au"]["version"], "kind": kind, "data": data}
        status, value = self.client.request("/api/v1/" + family + "/commands", request)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        return value["receipt"]

    def prepare_work_au(self):
        request = creation("work-au")
        request["data"]["charter"].update(allowed_operations=["create_work"], allowed_tools=["produce_artifact"])
        request["data"]["resources"]["max_calls"] = 4
        self.creation_receipt = self.create(self.client, request)
        self.au_id = self.creation_receipt["organization_id"]
        self.command("governance", "adopt_governance", {"config": {
            "profile": "local_governance.v1", "final_decision_principal_id": self.session["principal_id"],
            "reserved_matters": ["charter", "goal", "resources", "appointments", "mandates", "dissolution"],
            "unavailability": {"mode": "exit_after_timeout", "timeout_seconds": 3600},
        }, "reason": "Synthetic public command acceptance only"}, "governance-adopt")
        self.command("governance", "activate_governance", {"reason": "Internal controlled records only"}, "governance-activate")
        self.grants["/v1/grants/grant-public"] = {
            "id": "grant-public", "au_id": self.au_id, "revision": 1,
            "revoked_at": None, "model_ids": ["synthetic-model"],
        }
        saved = self.command("models", "save_connection", {
            "connection_id": "connection-public", "expected_revision": 0, "name": "Grant-only double",
            "profile": "modeld_grant", "model": "synthetic-model", "max_output_tokens": 128,
            "grant_ref": "grant-public", "grant_revision": 1,
        }, "connection-save")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            models = self.get(self.client, "/api/v1/models?organization_id=" + self.au_id)
            op = next(item for item in models["operations"] if item["id"] == saved["operation_id"])
            if op["status"] not in ("queued", "running", "saving"):
                self.assertEqual(op["status"], "succeeded", op)
                break
            time.sleep(0.01)
        else:
            self.fail("Synthetic grant preparation did not finish within 15 seconds")
        self.command("models", "set_connection", {"connection_id": "connection-public", "expected_revision": 1,
                     "enabled": True, "make_default": True}, "connection-adopt")

    def work_request(self, request_id="register-work", suffix="one"):
        return {"id": request_id, "organization_id": self.au_id,
                "base_version": self.view()["au"]["version"], "kind": "start_work", "data": {
                    "work_id": "work-" + suffix, "title": "Public command work", "goal": "Prepare a bounded result",
                    "member_name": "Synthetic responsible AI", "member_id": "member-" + suffix,
                    "binding_id": "binding-" + suffix, "mandate_id": "mandate-" + suffix,
                    "definition_id": "definition-" + suffix, "connection_id": "connection-public",
                    "expected_revision": 1, "materials_root": None, "max_calls": 1,
                    "tools": ["produce_artifact"], "reason": "Explicit controlled work registration",
                }}

    def submit(self, request, expected="succeeded", client=None):
        status, value = (client or self.client).request("/api/v1/work/commands", request)
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], expected, receipt)
        for key in ("id", "organization_id", "base_version", "kind"):
            self.assertEqual(receipt[key], request[key])
        self.assertEqual(receipt["actor_principal_id"], self.session["principal_id"])
        self.assertTrue(receipt["created_at"])
        self.assertEqual(self.get(client or self.client, self.receipt_path(request["id"]))["receipt"], receipt)
        return receipt

class PublicWorkClientTests(PublicWorkClientHost):
    def test_public_work_registration_binds_responsibility_without_dispatch(self):
        request = self.work_request()
        receipt = self.submit(request)
        view = self.works()
        self.assertEqual(view["protocol"], "core.work.v1")
        self.assertEqual(view["version"], request["base_version"] + 1)
        self.assertEqual(receipt["version"], view["version"])
        self.assertEqual(receipt["work_id"], "work-one")
        self.assertEqual(len(view["works"]), 1)
        work = view["works"][0]
        self.assertEqual((work["id"], work["status"], work["max_calls"]), ("work-one", "pending", 1))
        self.assertEqual(work["responsible"], {"member_id": "member-one", "name": "Synthetic responsible AI",
                         "binding_id": "binding-one", "duty": "Public command work"})
        self.assertEqual(work["definition"], {"id": "definition-one", "version": 1,
                         "connection_id": "connection-public", "model": "synthetic-model", "tools": ["produce_artifact"]})
        self.assertEqual(work["mandate"], {"id": "mandate-one", "version": 1, "actions": ["produce_artifact"], "active": True})
        for key in ("attempts", "steps", "results"):
            self.assertEqual(work[key], [])
        self.assertEqual(view["cost_status"], "unknown")
        self.assertFalse(view["capabilities"]["autonomous_business"])
        public = json.dumps({"receipt": receipt, "view": view})
        for private in (PASSWORD, self.client.cookie.split("=", 1)[1], "a" * 40, "w" * 40,
                        json.dumps(str(self.root))[1:-1]):
            self.assertNotIn(private, public)

    def test_platform_admin_cannot_read_submit_or_replay_another_au(self):
        request = self.work_request()
        original = self.submit(request)
        before = self.works()
        paths = ["/api/v1/work?organization_id=" + self.au_id,
                 self.receipt_path(request["id"]), self.receipt_path("unknown-request")]
        for path in paths:
            self.assert_error(self.owner.request(path), 403, "not_authorized")
        for data in (request, self.work_request("admin-attempt", "two")):
            self.assert_error(self.owner.request("/api/v1/work/commands", data), 403, "not_authorized")
        self.assertEqual(self.works(), before)
        self.assertEqual(self.get(self.client, self.receipt_path(request["id"]))["receipt"], original)

    def test_new_session_replay_is_idempotent_and_changed_payload_conflicts(self):
        request = self.work_request()
        original = self.submit(request)
        before = self.works()
        second = HttpClient(self.port)
        self.assertEqual(self.authenticate(second, "login", "governor")["principal_id"], self.session["principal_id"])
        self.assertEqual(self.submit(request, client=second), original)
        changed = copy.deepcopy(request)
        changed["data"]["goal"] = "Different intent under the same ID"
        self.assert_error(second.request("/api/v1/work/commands", changed), 409, "id_conflict")
        self.assertEqual(self.works(), before)

    def test_stale_versions_return_queryable_rejections_without_work_mutation(self):
        before = self.works()
        for key in ("au", "connection"):
            request = self.work_request("stale-" + key)
            if key == "au":
                request["base_version"] -= 1
            else:
                request["data"]["expected_revision"] = 2
            receipt = self.submit(request, "rejected")
            self.assertEqual(receipt["effect"], "none")
            self.assertEqual(receipt["version"], before["version"])
            self.assertEqual(self.works(), before)
        self.submit(self.work_request("current-versions"))

    def test_disabled_connection_and_exited_governance_refuse_new_work(self):
        self.command("models", "set_connection", {"connection_id": "connection-public", "expected_revision": 1,
                     "enabled": False, "make_default": False}, "connection-disable")
        before = self.works()
        models = self.get(self.client, "/api/v1/models?organization_id=" + self.au_id)
        revision = models["connections"][0]["revision"]
        disabled = self.work_request("disabled-connection")
        disabled["data"]["expected_revision"] = revision
        self.submit(disabled, "rejected")
        self.assertEqual(self.works(), before)
        self.command("models", "set_connection", {"connection_id": "connection-public", "expected_revision": revision,
                     "enabled": True, "make_default": True}, "connection-enable")
        request = self.work_request("enabled-connection")
        request["data"]["expected_revision"] = self.get(self.client, "/api/v1/models?organization_id=" + self.au_id)["connections"][0]["revision"]
        self.submit(request)
        self.command("governance", "exit_governance", {"reason": "End synthetic governance authority"}, "governance-exit")
        before = self.works()
        exited = self.work_request("exited-governance", "two")
        exited["data"]["expected_revision"] = request["data"]["expected_revision"]
        self.submit(exited, "rejected")
        self.assertEqual(self.works(), before)

    def test_discarded_work_response_recovers_by_get_and_survives_restart(self):
        request = self.work_request()
        posts = self.client.requests.count(("POST", "/api/v1/work/commands"))
        self.assertIsNone(self.client.request("/api/v1/work/commands", request, discard_response=True))
        receipt = self.get(self.client, self.receipt_path(request["id"]))["receipt"]
        self.assertEqual((receipt["id"], receipt["status"], receipt["work_id"]), (request["id"], "succeeded", "work-one"))
        before = self.works()
        self.assertEqual(len(before["works"]), 1)
        self.assertEqual(self.client.requests.count(("POST", "/api/v1/work/commands")), posts + 1)
        self.stop()
        self.start()
        self.client = HttpClient(self.port)
        self.assertEqual(self.authenticate(self.client, "login", "governor")["principal_id"], self.session["principal_id"])
        self.assertEqual(self.get(self.client, self.receipt_path(request["id"]))["receipt"], receipt)
        self.assertEqual(self.works(), before)
        self.assertFalse(any(method == "POST" and path == "/api/v1/work/commands" for method, path in self.client.requests))

    def test_invalid_and_cross_origin_commands_do_not_consume_the_request_id(self):
        request = self.work_request()
        self.assert_error(HttpClient(self.port).request("/api/v1/work/commands", request), 401, "not_authenticated")
        self.assertEqual(self.client.request("/api/v1/work/commands", request, headers={"Origin": "https://untrusted.invalid"})[0], 403)
        for change in ({"max_calls": True}, {"actor_principal_id": self.owner_session["principal_id"]}):
            invalid = copy.deepcopy(request)
            invalid["data"].update(change)
            self.assert_error(self.client.request("/api/v1/work/commands", invalid), 400, "invalid_request")
        self.assertEqual(self.works()["works"], [])
        self.assert_error(self.client.request(self.receipt_path(request["id"])), 403, "not_authorized")
        self.submit(request)


class StandaloneCoreTests(PublicWorkClientHost):
    """U-104: one public workflow under a fresh host and Core account boundary."""

    first_claim_platform_admin = False

    def process_environment(self):
        env = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR") if name in os.environ}
        home = self.root / "profile"
        home.mkdir(exist_ok=True)
        env.update({name: str(home) for name in (
            "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME",
            "XDG_DATA_HOME", "XDG_CACHE_HOME", "TEMP", "TMP", "TMPDIR",
        )})
        return env

    def test_core_account_creates_reads_and_registers_work_without_private_platform(self):
        before = self.view()
        self.assertEqual(self.listed(self.client), [
            {"id": self.au_id, "name": before["au"]["name"], "profile": "core_v1"},
        ])
        self.assertEqual(before["protocol"], "core.au.v1")
        self.assertEqual(before["au"]["schema_version"], 3)
        self.assertEqual(before["au"]["governance_root"]["creator_principal_id"], self.session["principal_id"])
        creation_path = "/api/v1/receipts?id=" + self.creation_receipt["id"]
        self.assertEqual(self.get(self.client, creation_path)["receipt"], self.creation_receipt)

        stale = self.work_request("stale-state")
        stale["base_version"] -= 1
        rejection = self.submit(stale, "rejected")
        self.assertEqual(rejection["effect"], "none")
        self.assertEqual(self.works()["works"], [])

        request = self.work_request()
        self.assertIsNone(self.client.request("/api/v1/work/commands", request, discard_response=True))
        path = self.receipt_path(request["id"])
        receipt = self.get(self.client, path)["receipt"]
        self.assertEqual((receipt["id"], receipt["organization_id"], receipt["status"]),
                         (request["id"], self.au_id, "succeeded"))
        self.assertEqual(receipt["actor_principal_id"], self.session["principal_id"])
        work_view = self.works()
        self.assertEqual(work_view["protocol"], "core.work.v1")
        self.assertEqual(work_view["organization_id"], self.au_id)
        self.assertEqual(receipt["version"], before["au"]["version"] + 1)
        self.assertEqual(work_view["version"], receipt["version"])
        self.assertEqual(len(work_view["works"]), 1)
        work = work_view["works"][0]
        self.assertEqual((work["id"], work["status"]), (receipt["work_id"], "pending"))
        self.assertEqual(work["responsible"]["binding_id"], request["data"]["binding_id"])
        self.assertEqual((work["definition"]["id"], work["definition"]["version"]),
                         (request["data"]["definition_id"], 1))
        for key in ("attempts", "steps", "results"):
            self.assertEqual(work[key], [])
        self.assertEqual(self.client.requests.count(("POST", "/api/v1/work/commands")), 2)

        other = HttpClient(self.port)
        other_session = self.authenticate(other, "register", "other")
        self.assertFalse(other_session["platform_admin"])
        for endpoint in ("/api/v1/aus/" + self.au_id, creation_path,
                         "/api/v1/work?organization_id=" + self.au_id, path):
            self.assert_error(other.request(endpoint), 403, "not_authorized")

        self.stop()
        self.start()
        self.client = HttpClient(self.port)
        reopened = self.authenticate(self.client, "login", "governor")
        self.assertFalse(reopened["platform_admin"])
        self.assertEqual(reopened["principal_id"], self.session["principal_id"])
        self.assertEqual(self.get(self.client, creation_path)["receipt"], self.creation_receipt)
        self.assertEqual(self.get(self.client, path)["receipt"], receipt)
        self.assertEqual(self.get(self.client, self.receipt_path(stale["id"]))["receipt"], rejection)
        self.assertEqual(self.view()["au"]["schema_version"], before["au"]["schema_version"])
        self.assertEqual(self.view()["au"]["version"], receipt["version"])
        self.assertEqual(self.works(), work_view)
        self.assertNotIn(("POST", "/api/v1/work/commands"), self.client.requests)


if __name__ == "__main__":
    unittest.main()
