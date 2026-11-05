"""Independent core identities never inherit host or AU authority."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid

from ai_union.console import Console
from ai_union.errors import Rejected
from ai_union import identity_schema
from tests import test_core_creation as core_http
from tests.test_core_creation import creation
from tests.test_identity_upgrade import legacy_catalog, dump, OLD_PAYLOAD, OLD_RECEIPT


class CoreParticipantTests(unittest.TestCase):
    setUp = core_http.CoreCreationTests.setUp
    start = core_http.CoreCreationTests.start
    stop = core_http.CoreCreationTests.stop
    request = core_http.CoreCreationTests.request
    setup_account = core_http.CoreCreationTests.setup_account
    create = core_http.CoreCreationTests.create

    def register(self, username="participant"):
        status, value, cookie = self.request("/api/auth/register", {
            "username": username, "password": "participant-safe-password", "remember": True}, token=None)
        self.assertEqual(status, 200, value)
        return cookie.split("=", 1)[1].split(";", 1)[0], value

    def test_registration_gives_stable_core_identity_without_host_or_existing_au_rights(self):
        owner_au = self.create()["organization_id"]
        token, result = self.register()
        session = self.app.session(token)
        self.assertEqual((session["role"], session["organizations"], session["platform_admin"]), ("core", [], False))
        self.assertNotEqual(session["principal_id"], self.app.session(self.token)["principal_id"])
        self.assertEqual(result["session"]["organizations"], [])
        self.assertEqual(self.request("/api/v1/aus/" + owner_au, token=token)[0], 403)
        legacy = creation("cannot-create-legacy") | {"kind": "create"}
        self.assertEqual(self.request("/api/commands", legacy, token)[0], 403)
        self.assertEqual(self.request("/api/model-service", token=token)[0], 403)
        status, own, _ = self.request("/api/commands", creation("participant-au"), token)
        self.assertEqual(status, 200, own)
        self.assertEqual(own["receipt"]["status"], "succeeded")
        self.stop()
        self.start()
        status, value, cookie = self.request("/api/auth/login", {
            "username": "participant", "password": "participant-safe-password", "remember": True}, token=None)
        self.assertEqual(status, 200, value)
        again = cookie.split("=", 1)[1].split(";", 1)[0]
        self.assertEqual(self.app.session(again)["principal_id"], session["principal_id"])
        self.assertEqual([o["id"] for o in value["session"]["organizations"]], [own["receipt"]["organization_id"]])

    def test_reset_owner_preserves_participant_credentials_and_never_transfers_au_authority(self):
        original = self.create()["organization_id"]
        token, _ = self.register()
        principal = self.app.session(token)["principal_id"]
        self.stop()
        from scripts.reset_owner import reset
        reset(self.root, confirm=True)
        self.start()
        self.token = self.setup_account()
        self.assertEqual(self.request("/api/v1/aus/" + original)[0], 403)
        status, value, cookie = self.request("/api/auth/login", {
            "username": "participant", "password": "participant-safe-password", "remember": False}, token=None)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["session"]["principal_id"], principal)
        participant = cookie.split("=", 1)[1].split(";", 1)[0]
        self.assertEqual(self.request("/api/v1/aus/" + original, token=participant)[0], 403)

    def test_registration_cannot_choose_privilege_or_reuse_an_existing_name(self):
        self.register()
        for data in ({"username": "owner", "password": "participant-safe-password", "remember": False},
                     {"username": "new-user", "password": "participant-safe-password", "remember": False, "account_kind": "owner"}):
            status, _, _ = self.request("/api/auth/register", data, token=None)
            self.assertNotEqual(status, 200)
        with self.app.read_catalog() as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM owner_account").fetchone()[0], 2)

    def test_other_account_login_cannot_clear_target_account_failure_throttle(self):
        self.register()
        bad_owner = {"username": "owner", "password": "incorrect-password", "remember": False}
        good_other = {"username": "participant", "password": "participant-safe-password", "remember": False}
        for _ in range(7):
            self.assertEqual(self.request("/api/auth/login", bad_owner, token=None)[0], 401)
        self.assertEqual(self.request("/api/auth/login", good_other, token=None)[0], 200)
        self.assertEqual(self.request("/api/auth/login", bad_owner, token=None)[0], 401)
        good_owner = bad_owner | {"password": "correct-horse-password"}
        status, value, _ = self.request("/api/auth/login", good_owner, token=None)
        self.assertEqual(status, 401, "An unrelated successful login must not reset the owner's failed-attempt limit")
        self.assertIn("尝试过多", value["error"])
        self.assertEqual(self.request("/api/auth/login", good_other, token=None)[0], 200)

    def test_successful_login_clears_only_its_own_failed_attempts(self):
        self.register()
        bad = {"username": "participant", "password": "incorrect-password", "remember": False}
        for _ in range(7):
            self.assertEqual(self.request("/api/auth/login", bad, token=None)[0], 401)
        good = bad | {"password": "participant-safe-password"}
        self.assertEqual(self.request("/api/auth/login", good, token=None)[0], 200)
        self.assertEqual(self.request("/api/auth/login", bad, token=None)[0], 401)
        self.assertEqual(self.request("/api/auth/login", good, token=None)[0], 200)


def schema_one(root):
    database = legacy_catalog(root)
    principal = str(uuid.uuid4())
    with closing(sqlite3.connect(database)) as cx, cx:
        cx.execute("ALTER TABLE owner_account ADD COLUMN principal_id TEXT")
        cx.execute("UPDATE owner_account SET principal_id=?", (principal,))
        cx.execute("CREATE UNIQUE INDEX core_owner_principal ON owner_account(principal_id)")
        cx.execute("ALTER TABLE organizations ADD COLUMN profile TEXT NOT NULL DEFAULT 'legacy_v0'")
        cx.execute("ALTER TABLE creations ADD COLUMN profile TEXT NOT NULL DEFAULT 'legacy_v0'")
        cx.execute("ALTER TABLE creations ADD COLUMN creator_principal_id TEXT")
        cx.execute("ALTER TABLE creations ADD COLUMN allocated_au_id TEXT")
        cx.execute("CREATE TABLE core_schema(id INTEGER PRIMARY KEY CHECK(id=1), auth_version INTEGER NOT NULL, catalog_version INTEGER NOT NULL, write_revision INTEGER NOT NULL, upgrade_receipt TEXT)")
        cx.execute("INSERT INTO core_schema VALUES(1,1,1,0,NULL)")
    return database, principal


class ParticipantUpgradeTests(unittest.TestCase):
    def test_schema_one_requires_explicit_upgrade_and_preserves_principal_and_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database, principal = schema_one(root)
            original = database.read_bytes()
            original_dump = dump(database)
            rejected = None
            try:
                app = Console(root)
            except Rejected as error:
                rejected = error
            else:
                app.close()
            self.assertIsNotNone(rejected, "S01 identities require explicit schema 2 upgrade before writes")
            self.assertEqual(database.read_bytes(), original)
            receipt = identity_schema.upgrade(root, services_stopped=True)
            self.assertEqual(receipt["schema"], {"auth": 2, "catalog": 1})
            self.assertEqual(receipt["from_schema"], {"auth": 1, "catalog": 1})
            with closing(sqlite3.connect(database)) as cx:
                self.assertEqual(cx.execute("SELECT principal_id,account_kind FROM owner_account").fetchone(), (principal, "owner"))
                self.assertEqual(cx.execute("SELECT payload,receipt FROM creations").fetchone(), (OLD_PAYLOAD, OLD_RECEIPT))
                self.assertEqual(cx.execute("SELECT COUNT(*) FROM login_sessions").fetchone()[0], 0)
            upgraded = dump(database)
            identity_schema.upgrade(root, services_stopped=True)
            self.assertEqual(dump(database), upgraded)
            rolled = identity_schema.upgrade(root, services_stopped=True, rollback=True)
            self.assertEqual(rolled["schema"], {"auth": 1, "catalog": 1})
            self.assertEqual(dump(database), original_dump)

    def test_failed_schema_one_upgrade_does_not_lose_the_original_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database, _ = schema_one(root)
            with closing(sqlite3.connect(database)) as cx, cx:
                cx.execute("CREATE TRIGGER fail_upgrade BEFORE DELETE ON login_sessions BEGIN SELECT RAISE(ABORT, 'controlled upgrade failure'); END")
            original = dump(database)
            with self.assertRaises(sqlite3.DatabaseError):
                identity_schema.upgrade(root, services_stopped=True)
            self.assertEqual(dump(database), original)


if __name__ == "__main__":
    unittest.main()
