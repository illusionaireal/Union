"""U-101: a standard-library HTTP client against a separate, unmodified Core process.

No Core/test helper imports, launch tickets, SQLite access or model requests.
Run: python -m unittest tests.test_public_core_client -v
"""
import copy
import http.client
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest


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


class PublicCoreClientTests(unittest.TestCase):
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

    def start(self):
        # Do not pass a real host model/service configuration into the temporary Core.
        env = {key: value for key, value in os.environ.items() if not key.startswith("UNION_")}
        env.update(PYTHONPATH=str(REPO), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
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


if __name__ == "__main__":
    unittest.main()
