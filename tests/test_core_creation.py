"""V1 creation/reopen through the real HTTP, identity and persistence boundaries."""
from contextlib import closing
import copy
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from ai_union.console import Console
from ai_union.server import Server
from tests.support import CHARTER, RESOURCES


def creation(request_id="v1-create", **changes):
    data = {"name": "Prepared AU", "goal": "Preserve an explicit objective", "board_name": "Owner display",
            "charter": copy.deepcopy(CHARTER), "resources": copy.deepcopy(RESOURCES)}
    data.update(changes)
    return {"id": request_id, "organization_id": None, "base_version": None, "kind": "create_v1", "data": data}


class CoreCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = None
        self.server = None
        self.start()
        self.addCleanup(self.stop)
        self.token = self.setup_account()

    def start(self):
        self.app = Console(self.root)
        self.server = Server(self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.thread.join(5)
            self.server.server_close()
            self.server = None
        if self.app and not self.app.closed:
            self.app.close()

    def request(self, path, body=None, token="current", timeout=5):
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=timeout)
        headers = {"Origin": self.server.origin, "Content-Type": "application/json"}
        actual = getattr(self, "token", None) if token == "current" else token
        if actual:
            headers["Cookie"] = self.server.cookie_name + "=" + actual
        try:
            client.request("POST" if body is not None else "GET", path,
                           json.dumps(body) if body is not None else None, headers)
            response = client.getresponse()
            return response.status, json.loads(response.read()), response.getheader("Set-Cookie")
        finally:
            client.close()

    def setup_account(self):
        status, _, cookie = self.request("/api/auth/setup", {"username": "owner", "password": "correct-horse-password", "remember": True}, token=None)
        self.assertEqual(status, 200)
        return cookie.split("=", 1)[1].split(";", 1)[0]

    def create(self, request=None):
        status, result, _ = self.request("/api/commands", request or creation())
        self.assertEqual(status, 200, result)
        self.assertEqual(result["receipt"]["status"], "succeeded", result)
        return result["receipt"]

    def test_core_account_creates_prepared_au_and_reopens_same_identity_after_restart(self):
        request = creation()
        receipt = self.create(request)
        au_id = receipt["organization_id"]
        status, value, _ = self.request("/api/v1/aus/" + au_id)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["protocol"], "core.au.v1")
        au = value["au"]
        principal = self.app.session(self.token)["principal_id"]
        self.assertEqual(au["governance_root"], {"creator_principal_id": principal, "governor_principal_id": principal})
        self.assertEqual((au["id"], au["version"], au["charter_version"], au["policy_version"]), (au_id, 0, 1, 0))
        self.assertEqual((au["runtime_profile"], au["schema_version"], au["autonomy_state"], au["resource_state"]), ("core_v1", 1, "inactive", "planned"))
        self.assertEqual(au["charter"], CHARTER)
        self.assertEqual(au["resources"], RESOURCES)
        self.assertEqual(value["capabilities"], {"read": True, "autonomous_business": False, "charter_enforcement": "not_activated"})
        self.assertEqual(self.request("/api/v1/receipts?id=v1-create")[1]["receipt"], receipt)
        self.assertEqual(self.request("/api/receipts?id=v1-create")[0], 409)
        with self.app.read_catalog() as cx:
            item = dict(cx.execute("SELECT * FROM organizations WHERE id=?", (au_id,)).fetchone())
        self.assertEqual(item["profile"], "core_v1")
        self.assertFalse((self.root / item["folder"] / "board.key").exists())
        self.stop()
        self.start()
        self.assertEqual(self.request("/api/v1/aus/" + au_id)[1], value)
        listed = self.request("/api/session")[1]["organizations"]
        self.assertIn({"id": au_id, "name": au["name"], "profile": "core_v1"}, listed)
        self.assertEqual(self.request("/api/commands", request)[1]["receipt"], receipt)

    def test_host_ticket_and_platform_admin_do_not_substitute_for_core_principal(self):
        for token in (None, self.app.new_session("board"), self.app.new_session("board", platform_admin=True)):
            with self.subTest(token_kind="anonymous" if token is None else "host"):
                status, value, _ = self.request("/api/commands", creation(), token)
                self.assertEqual(status, 401 if token is None else 403)
                self.assertEqual(value.get("code"), "not_authenticated" if token is None else "not_authorized")
        with self.app.read_catalog() as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM creations").fetchone()[0], 0)

    def test_invalid_new_requests_do_not_allocate_an_intent_or_directory(self):
        for index, changes in enumerate(({"governor_principal_id": "forged"}, {"runtime_profile": "legacy_v0"},
                                         {"active": True}, {"company": {}}, {"controller_ref": {}},
                                         {"name": " "}, {"resources": {"max_calls": True, "timeout_seconds": 180}})):
            with self.subTest(changes=changes):
                status, value, _ = self.request("/api/commands", creation("invalid-" + str(index), **changes))
                self.assertEqual(status, 400, value)
                self.assertEqual(value["code"], "invalid_request")
        with self.app.read_catalog() as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM creations").fetchone()[0], 0)
        self.assertFalse((self.root / "organizations").exists())

    def test_same_principal_replays_original_payload_without_new_validation(self):
        request = creation()
        receipt = self.create(request)
        with patch("ai_union.domain.creation.validate_creation", side_effect=AssertionError("stored request must not be revalidated")):
            self.assertEqual(self.request("/api/commands", request)[1]["receipt"], receipt)
        changed = copy.deepcopy(request)
        changed["data"]["goal"] = "different goal"
        status, value, _ = self.request("/api/commands", changed)
        self.assertEqual((status, value["code"]), (409, "id_conflict"))
        with self.app.read_catalog() as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM organizations").fetchone()[0], 1)

    def test_same_name_owner_reset_cannot_take_old_au_or_creation_receipt(self):
        receipt = self.create()
        au_id = receipt["organization_id"]
        original_principal = self.app.session(self.token)["principal_id"]
        self.stop()
        from scripts.reset_owner import reset
        reset(self.root, confirm=True)
        self.start()
        self.token = self.setup_account()
        self.assertNotEqual(self.app.session(self.token)["principal_id"], original_principal)
        self.assertEqual(self.request("/api/session")[1]["organizations"], [])
        replies = []
        for path in ("/api/v1/aus/" + au_id, "/api/v1/aus/org-missing", "/api/v1/receipts?id=v1-create", "/api/v1/receipts?id=absent"):
            status, value, _ = self.request(path)
            self.assertEqual((status, value["code"]), (403, "not_authorized"))
            self.assertNotIn(original_principal, json.dumps(value))
            replies.append(value)
        self.assertTrue(all(value == replies[0] for value in replies))
        for request in (creation(), creation(goal="changed across principal")):
            status, value, _ = self.request("/api/commands", request)
            self.assertEqual((status, value["code"]), (403, "not_authorized"))
        self.assertEqual(self.request("/api/receipts?id=v1-create")[0], 409)

    def test_failed_registration_keeps_allocated_id_and_original_unknown_query(self):
        with self.app.catalog() as cx:
            cx.execute("CREATE TRIGGER fail_core_registration BEFORE INSERT ON organizations BEGIN SELECT RAISE(ABORT, 'controlled register failure'); END")
        status, value, _ = self.request("/api/commands", creation())
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "unknown")
        with self.app.read_catalog() as cx:
            intent = dict(cx.execute("SELECT * FROM creations WHERE id='v1-create'").fetchone())
        self.assertEqual(receipt["organization_id"], intent["allocated_au_id"])
        database = self.root / intent["folder"] / "state.sqlite3"
        with closing(sqlite3.connect(database)) as cx:
            self.assertEqual(json.loads(cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0])["id"], intent["allocated_au_id"])
        self.assertEqual(self.request("/api/v1/receipts?id=v1-create")[1]["receipt"], receipt)
        self.assertEqual(self.request("/api/v1/aus/" + intent["allocated_au_id"])[0], 403)
        self.stop()
        self.start()
        with patch("ai_union.adapters.core_au_store.CoreAUStore.create", side_effect=AssertionError("unknown must not create again")):
            self.assertEqual(self.request("/api/commands", creation())[1]["receipt"], receipt)
        self.assertEqual(self.request("/api/session")[1]["organizations"], [])


if __name__ == "__main__":
    unittest.main()
