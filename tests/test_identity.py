"""Persistent host identities; no remote account or model calls."""
import json
import tempfile
import unittest
import threading
from pathlib import Path
from unittest.mock import patch
from ai_union.console import Console
from ai_union.engine import Rejected


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Console(self.temp.name)
        self.addCleanup(lambda: self.app.close())
        self.host = self.app.new_session('board', platform_admin=True)

    def setup(self):
        return self.app.identity.setup(self.host, 'owner', 'correct-horse-password', True)

    def test_anonymous_observer_and_scoped_board_cannot_claim_owner(self):
        for token in (None, self.app.new_session('observer'), self.app.new_session('board', organizations=[])):
            with self.assertRaises(Rejected):
                self.app.identity.setup(token, 'owner', 'correct-horse-password', True)
        self.assertFalse(self.app.identity.configured())

    def test_restart_preserves_login_and_cookie_scope_but_not_plaintext_secrets(self):
        result = self.setup()
        token = result['token']
        self.assertTrue(self.app.session(token)['platform_admin'])
        self.app.close()
        self.app = Console(self.temp.name)
        self.assertEqual(self.app.session_info(token)['role'], 'board')
        raw = Path(self.app.db).read_bytes()
        for secret in ('correct-horse-password', token, result['recovery_code']):
            self.assertNotIn(secret.encode(), raw)

    def test_password_login_logout_and_admin_flag_never_come_from_client(self):
        self.setup()
        with self.assertRaises(Rejected):
            self.app.identity.login('owner', 'wrong-password', False)
        result = self.app.identity.login('owner', 'correct-horse-password', False)
        self.assertTrue(self.app.session(result['token'])['platform_admin'])
        self.app.identity.logout(result['token'])
        with self.assertRaises(Rejected):
            self.app.session(result['token'])
        with self.assertRaises(Rejected):
            self.setup()

    def test_board_account_cannot_upgrade_itself_to_platform_admin(self):
        host = self.app.new_session('board')
        result = self.app.identity.setup(host, 'owner', 'correct-horse-password', False)
        self.assertFalse(self.app.session(result['token'])['platform_admin'])

    def test_password_change_and_recovery_revoke_all_previous_sessions(self):
        first = self.setup()
        second = self.app.identity.login('owner', 'correct-horse-password', True)
        changed = self.app.identity.change_password(first['token'], 'correct-horse-password', 'a-new-secure-password')
        for token in (first['token'], second['token']):
            with self.assertRaises(Rejected): self.app.session(token)
        recovered = self.app.identity.recover('owner', first['recovery_code'], 'recovered-secure-password')
        with self.assertRaises(Rejected): self.app.session(changed['token'])
        with self.assertRaises(Rejected):
            self.app.identity.recover('owner', first['recovery_code'], 'another-secure-password')
        self.assertEqual(self.app.session(recovered['token'])['actor'], 'account:owner')

    def test_expiration_and_persisted_login_throttle(self):
        first = self.setup()
        with patch('ai_union.identity.time.time', return_value=10**12):
            with self.assertRaises(Rejected): self.app.session(first['token'])
        for _ in range(8):
            with self.assertRaises(Rejected): self.app.identity.login('owner', 'bad-password', False)
        self.app.close(); self.app = Console(self.temp.name)
        with self.assertRaisesRegex(Rejected, '稍后'):
            self.app.identity.login('owner', 'correct-horse-password', False)

    def test_invalid_setup_has_no_partial_account(self):
        with self.assertRaises(Rejected):
            self.app.identity.setup(self.host, 'owner', 'correct-horse-password', 'true')
        self.assertFalse(self.app.identity.configured())

    def test_recovery_code_is_consumed_once_under_concurrency(self):
        first = self.setup()
        barrier, results = threading.Barrier(2), []
        original = self.app.identity._replace
        def delayed(*args, **kwargs):
            barrier.wait(timeout=5)
            return original(*args, **kwargs)
        def recover():
            try: results.append(self.app.identity.recover('owner', first['recovery_code'], 'recovered-secure-password'))
            except Rejected: results.append(None)
        with patch.object(self.app.identity, '_replace', side_effect=delayed):
            threads = [threading.Thread(target=recover) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(10)
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_old_password_cannot_issue_session_after_password_change(self):
        first = self.setup()
        ready, resume, results = threading.Event(), threading.Event(), []
        original = self.app.identity._issue
        def delayed(*args, **kwargs):
            ready.set(); resume.wait(5)
            return original(*args, **kwargs)
        def login():
            try: results.append(self.app.identity.login('owner', 'correct-horse-password', False))
            except Rejected: results.append(None)
        with patch.object(self.app.identity, '_issue', side_effect=delayed):
            thread = threading.Thread(target=login); thread.start()
            self.assertTrue(ready.wait(5))
            self.app.identity.change_password(first['token'], 'correct-horse-password', 'a-new-secure-password')
            resume.set(); thread.join(10)
        self.assertEqual(results, [None])
