"""Stable core principals on real temporary account/catalog databases."""
import json
import tempfile
import unittest
import uuid

from ai_union.console import Console
from ai_union.engine import Rejected


class CoreIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Console(self.temp.name)
        self.addCleanup(lambda: self.app.close())

    def test_account_principal_survives_login_password_recovery_and_restart(self):
        first = self.app.identity.setup(None, "owner", "correct-horse-password", True)
        principal = self.app.session(first["token"]).get("principal_id")
        self.assertIsInstance(principal, str, "authenticated accounts need a stable core principal")
        self.assertEqual(str(uuid.UUID(principal)), principal)
        with self.app.read_catalog() as cx:
            account = dict(cx.execute("SELECT * FROM owner_account").fetchone())
            session = json.loads(cx.execute("SELECT data FROM login_sessions").fetchone()[0])
        self.assertEqual(account["principal_id"], principal)
        self.assertEqual(session["principal_id"], principal)
        self.assertNotIn("principal_id", self.app.session(self.app.new_session("board", platform_admin=True)))

        logged_in = self.app.identity.login("owner", "correct-horse-password", True)
        changed = self.app.identity.change_password(logged_in["token"], "correct-horse-password", "a-new-secure-password")
        recovered = self.app.identity.recover("owner", first["recovery_code"], "recovered-secure-password")
        for token in (first["token"], logged_in["token"], changed["token"]):
            with self.assertRaises(Rejected):
                self.app.session(token)
        self.assertEqual(self.app.session(recovered["token"])["principal_id"], principal)
        self.app.close()
        self.app = Console(self.temp.name)
        self.assertEqual(self.app.session(recovered["token"])["principal_id"], principal)

    def test_session_without_current_account_principal_is_not_authenticated(self):
        first = self.app.identity.setup(None, "owner", "correct-horse-password", True)
        with self.app.catalog() as cx:
            original = cx.execute("SELECT data FROM login_sessions").fetchone()[0]
            stale = json.loads(original)
            stale.pop("principal_id")
            cx.execute("UPDATE login_sessions SET data=?", (json.dumps(stale),))
        with self.assertRaises(Rejected):
            self.app.session(first["token"])
        with self.app.catalog() as cx:
            cx.execute("UPDATE login_sessions SET data=?", (original,))
            cx.execute("UPDATE owner_account SET principal_id=?", (str(uuid.uuid4()),))
        with self.assertRaises(Rejected):
            self.app.session(first["token"])


if __name__ == "__main__":
    unittest.main()
