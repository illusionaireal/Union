"""Explicit versioned upgrades of real old catalog databases; no live data."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from ai_union.console import Console
from ai_union.engine import Rejected
from ai_union.identity import fingerprint, password_hash
from ai_union.locking import file_lock

REPO = Path(__file__).resolve().parents[1]
OLD_TOKEN = "old-session-token-for-controlled-upgrade"
OLD_PAYLOAD = '{ "data": {"b":2,"a":1}, "id":"old-request" }'
OLD_RECEIPT = '{ "id":"old-request", "status":"accepted", "organization_id":null }'


def legacy_catalog(root, *, account=True):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    database = root / "console.sqlite3"
    with closing(sqlite3.connect(database)) as cx, cx:
        cx.executescript("""
            CREATE TABLE organizations(id TEXT PRIMARY KEY, folder TEXT NOT NULL);
            CREATE TABLE creations(id TEXT PRIMARY KEY, payload TEXT NOT NULL, receipt TEXT NOT NULL, folder TEXT NOT NULL);
            CREATE TABLE owner_account(username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL, recovery_hash TEXT NOT NULL, platform_admin INTEGER NOT NULL);
            CREATE TABLE login_sessions(digest TEXT PRIMARY KEY, username TEXT NOT NULL, data TEXT NOT NULL, expires REAL NOT NULL, deadline REAL NOT NULL);
            CREATE TABLE login_limit(id INTEGER PRIMARY KEY, failures INTEGER NOT NULL, until REAL NOT NULL);
        """)
        if account:
            salt = "01" * 16
            cx.execute("INSERT INTO owner_account VALUES(?,?,?,?,?)", ("owner", salt, password_hash("correct-horse-password", salt), fingerprint("recovery-for-test"), 0))
            data = {"role": "board", "organizations": None, "platform_admin": False, "actor": "account:owner", "account": "owner", "remember": True, "view_id": "old-view"}
            cx.execute("INSERT INTO login_sessions VALUES(?,?,?,?,?)", (fingerprint(OLD_TOKEN), "owner", json.dumps(data), time.time() + 86400, time.time() + 86400))
        cx.execute("INSERT INTO creations VALUES(?,?,?,?)", ("old-request", OLD_PAYLOAD, OLD_RECEIPT, "organizations/old-request"))
    return database


def dump(database):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as cx:
        return "\n".join(cx.iterdump())


class IdentityUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = legacy_catalog(self.root)

    def upgrade(self, *extra, stopped=True):
        args = [sys.executable, "-B", str(REPO / "scripts/upgrade_core_identity.py"), "--root", str(self.root), *extra]
        if stopped:
            args.append("--services-stopped")
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=15)

    def test_old_schema_rejects_start_before_catalog_or_recovery_writes(self):
        before = self.db.read_bytes()
        rejected = None
        try:
            app = Console(self.root)
        except Rejected as error:
            rejected = error
        else:
            app.close()
        self.assertIsNotNone(rejected, "old catalog must require explicit upgrade before startup writes")
        self.assertIn("upgrade_core_identity.py", str(rejected))
        self.assertEqual(self.db.read_bytes(), before)
        with file_lock(self.root / "console.lock"):
            pass

    def test_upgrade_is_idempotent_preserves_intent_bytes_and_revokes_old_sessions(self):
        before = dump(self.db)
        result = self.upgrade()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        backup = self.root / receipt["backup"]
        self.assertEqual(dump(backup), before)
        with closing(sqlite3.connect(self.db)) as cx:
            principal = cx.execute("SELECT principal_id FROM owner_account").fetchone()[0]
            self.assertTrue(principal)
            self.assertEqual(cx.execute("SELECT payload,receipt,profile,creator_principal_id,allocated_au_id FROM creations").fetchone(),
                             (OLD_PAYLOAD, OLD_RECEIPT, "legacy_v0", None, None))
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM login_sessions").fetchone()[0], 0)
        upgraded = dump(self.db)
        again = self.upgrade()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(dump(self.db), upgraded)
        app = Console(self.root)
        try:
            with self.assertRaises(Rejected):
                app.session(OLD_TOKEN)
            login = app.identity.login("owner", "correct-horse-password", True)
            self.assertEqual(app.session(login["token"])["principal_id"], principal)
            from tests.support import CHARTER, RESOURCES
            created = app.command(login["token"], {"id": "legacy-after-upgrade", "organization_id": None,
                "base_version": None, "kind": "create", "data": {"name": "legacy", "goal": "same old contract",
                "board_name": "owner", "charter": CHARTER, "resources": RESOURCES}})
            self.assertEqual(created["status"], "succeeded")
        finally:
            app.close()

    def test_upgrade_requires_stopped_services_and_holds_the_actual_console_lock(self):
        before = self.db.read_bytes()
        self.assertNotEqual(self.upgrade(stopped=False).returncode, 0)
        with file_lock(self.root / "console.lock"):
            self.assertNotEqual(self.upgrade().returncode, 0)
        self.assertEqual(self.db.read_bytes(), before)

    def test_failed_upgrade_rolls_back_schema_and_original_rows(self):
        with closing(sqlite3.connect(self.db)) as cx, cx:
            cx.execute("CREATE TRIGGER fail_upgrade BEFORE UPDATE ON owner_account BEGIN SELECT RAISE(ABORT, 'controlled migration failure'); END")
        before = dump(self.db)
        result = self.upgrade()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(dump(self.db), before)
        with closing(sqlite3.connect(self.db)) as cx, cx:
            cx.execute("DROP TRIGGER fail_upgrade")
        self.assertEqual(self.upgrade().returncode, 0)

    def test_pristine_upgrade_can_roll_back_but_new_facts_cannot_be_erased(self):
        before = dump(self.db)
        result = self.upgrade()
        self.assertEqual(result.returncode, 0, result.stderr)
        rollback = self.upgrade("--rollback")
        self.assertEqual(rollback.returncode, 0, rollback.stderr)
        self.assertEqual(dump(self.db), before)
        self.assertEqual(self.upgrade().returncode, 0)
        app = Console(self.root)
        try:
            app.identity.login("owner", "correct-horse-password", True)
        finally:
            app.close()
        latest = dump(self.db)
        refused = self.upgrade("--rollback")
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(dump(self.db), latest)

    def test_receipt_path_conflict_rejects_before_migrating_old_catalog(self):
        (self.root / "core-identity-upgrade.json").mkdir()
        before = dump(self.db)
        self.assertEqual(self.upgrade().returncode, 1)
        self.assertEqual(dump(self.db), before)

    def test_incomplete_current_marker_rejects_before_any_service_writes(self):
        for damage in ("ALTER TABLE core_schema RENAME COLUMN upgrade_receipt TO lost_receipt",
                       "UPDATE core_schema SET write_revision=-1"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                app = Console(root)
                app.close()
                database = root / "console.sqlite3"
                with closing(sqlite3.connect(database)) as cx, cx:
                    cx.execute(damage)
                before = database.read_bytes()
                rejected = None
                try:
                    app = Console(root)
                except Rejected as error:
                    rejected = error
                else:
                    app.close()
                self.assertIsNotNone(rejected, "incomplete current marker must reject before startup writes")
                self.assertEqual(database.read_bytes(), before)
                with file_lock(root / "console.lock"):
                    pass

    def test_committed_upgrade_can_recover_receipt_after_projection_write_failure(self):
        from ai_union import identity_schema
        with patch.object(identity_schema, "_write_receipt", side_effect=OSError("controlled receipt interruption")):
            with self.assertRaises((OSError, Rejected)):
                identity_schema.upgrade(self.root, services_stopped=True)
        self.assertEqual(identity_schema.versions(self.db), {"auth": 1, "catalog": 1})
        committed = dump(self.db)
        result = self.upgrade()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertIsInstance(receipt.get("backup"), str, "committed upgrade must retain original recovery evidence")
        self.assertTrue((self.root / "core-identity-upgrade.json").is_file())
        self.assertEqual(dump(self.db), committed)
        self.assertEqual(self.upgrade("--rollback").returncode, 0)


if __name__ == "__main__":
    unittest.main()
