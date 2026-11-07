"""Real SQLite failures and interruption preserve one V1 creation intent."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from http.client import HTTPException
import unittest
from unittest.mock import patch

from tests import links
from tests import test_core_creation as http


class CoreCreationFailureTests(unittest.TestCase):
    setUp = http.CoreCreationTests.setUp
    start = http.CoreCreationTests.start
    stop = http.CoreCreationTests.stop
    request = http.CoreCreationTests.request
    setup_account = http.CoreCreationTests.setup_account
    create = http.CoreCreationTests.create

    def intent(self, request_id):
        with self.app.read_catalog() as cx:
            return dict(cx.execute('SELECT * FROM creations WHERE id=?', (request_id,)).fetchone())

    def test_creation_rejects_escaped_parent_before_any_outside_file_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary)
            link = self.root / 'organizations'
            try:
                links.directory_link(outside, link)
            except links.LinkUnavailable as error:
                self.skipTest(links.skip_reason(error))
            try:
                status, value, _ = self.request('/api/commands', http.creation())
                self.assertEqual(status, 200)
                self.assertEqual(value['receipt']['status'], 'rejected')
                self.assertEqual(list(outside.iterdir()), [])
                self.assertEqual(self.request('/api/commands', http.creation())[1], value)
            finally:
                # A RED implementation may have registered the escaped test AU;
                # discard only that temporary registration before fixture close.
                with self.app.catalog() as cx:
                    cx.execute('DELETE FROM organizations')
                link.unlink()

    def test_creation_audit_must_still_match_its_original_request(self):
        au_id = self.create()['organization_id']
        intent = self.intent('v1-create')
        database = self.root / intent['folder'] / 'state.sqlite3'
        before = database.read_bytes()
        with closing(sqlite3.connect(database)) as cx, cx:
            cx.execute("UPDATE creation_adoptions SET request_id='unrelated-request',adopted_at='1900-01-01'")
        damaged = database.read_bytes()
        try:
            status, value, _ = self.request('/api/v1/aus/' + au_id)
            self.assertEqual((status, value.get('code')), (409, 'incompatible_state'))
            self.assertEqual(self.request('/api/session')[0], 409)
            with self.assertRaises(ValueError):
                self.app.close()
            self.assertEqual(database.read_bytes(), damaged)
        finally:
            database.write_bytes(before)

    def test_intent_storage_failure_returns_503_without_allocating_or_faking_unknown(self):
        with self.app.catalog() as cx:
            cx.execute("CREATE TRIGGER fail_intent BEFORE INSERT ON creations BEGIN SELECT RAISE(ABORT,'controlled intent failure'); END")
        status, value, _ = self.request('/api/commands', http.creation())
        self.assertEqual((status, value.get('code')), (503, 'storage_unavailable'))
        self.assertEqual(self.request('/api/v1/receipts?id=v1-create')[0], 403)
        self.assertEqual(self.app.organizations(), [])
        self.assertFalse((self.root / 'organizations').exists())

    def test_authentication_catalog_lock_returns_typed_storage_error(self):
        self.assertEqual(self.request('/api/v1/aus/org-missing')[0], 403)
        before = self.app.db.read_bytes()
        with closing(sqlite3.connect(self.app.db)) as cx:
            cx.execute('BEGIN EXCLUSIVE')
            try:
                status, value, _ = self.request('/api/v1/aus/org-missing', timeout=15)
            except (HTTPException, OSError):
                status, value = None, {}
            finally:
                cx.rollback()
        self.assertEqual((status, value.get('code')), (503, 'storage_unavailable'))
        self.assertEqual(self.app.db.read_bytes(), before)
        self.assertEqual(self.request('/api/v1/aus/org-missing')[0], 403)

    def test_directory_failure_keeps_unknown_without_retrying_allocation(self):
        # Exercise an equivalent path spelling, as Windows CI expands short temp names.
        self.root = self.root / '..' / self.root.name
        original = Path.mkdir

        def fail_directory(path, *args, **kwargs):
            if path.parent.resolve() == (self.root / 'organizations').resolve():
                raise OSError('controlled directory failure')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'mkdir', fail_directory):
            status, value, _ = self.request('/api/commands', http.creation())
        self.assertEqual(status, 200)
        self.assertEqual(value['receipt']['status'], 'unknown')
        original_intent = self.intent('v1-create')
        self.stop(); self.start()
        self.assertEqual(self.request('/api/commands', http.creation())[1], value)
        self.assertEqual(self.intent('v1-create'), original_intent)
        self.assertFalse((self.root / original_intent['folder']).exists())

    def test_au_state_charter_and_root_audit_roll_back_in_one_real_transaction(self):
        connect = sqlite3.connect

        class RejectAudit(sqlite3.Connection):
            def execute(self, query, *args):
                result = super().execute(query, *args)
                if query.startswith('CREATE TABLE creation_adoptions'):
                    super().execute("CREATE TRIGGER reject_adoption BEFORE INSERT ON creation_adoptions BEGIN SELECT RAISE(ABORT,'controlled adoption failure'); END")
                return result

        def failing_connection(database, *args, **kwargs):
            if str(database).endswith('state.sqlite3'):
                kwargs['factory'] = RejectAudit
            return connect(database, *args, **kwargs)

        with patch('ai_union.adapters.core_au_store.sqlite3.connect', failing_connection):
            status, value, _ = self.request('/api/commands', http.creation())
        self.assertEqual(status, 200)
        self.assertEqual(value['receipt']['status'], 'unknown')
        intent = self.intent('v1-create')
        database = self.root / intent['folder'] / 'state.sqlite3'
        with closing(sqlite3.connect(database)) as cx:
            self.assertEqual(cx.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])
        before = database.read_bytes()
        self.stop(); self.start()
        self.assertEqual(database.read_bytes(), before)
        self.assertEqual(self.request('/api/commands', http.creation())[1], value)
        self.assertEqual(self.app.organizations(), [])

    def test_interruptions_before_and_after_au_commit_keep_original_id_and_bytes(self):
        for request_id, boundary in (('before-au', 'create'), ('after-au', 'register')):
            request = http.creation(request_id)
            target = self.app.creation.core if boundary == 'create' else self.app.creation.catalog
            with self.subTest(boundary=boundary), patch.object(target, boundary, side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.app.command(self.token, request)
            intent = self.intent(request_id)
            self.assertEqual(json.loads(intent['receipt'])['status'], 'accepted')
            directory = self.root / intent['folder']
            before = {path.name: path.read_bytes() for path in directory.glob('*') if path.is_file()}
            if boundary == 'register':
                with closing(sqlite3.connect(directory / 'state.sqlite3')) as cx:
                    state = json.loads(cx.execute('SELECT data FROM state').fetchone()[0])
                    adoption = cx.execute('SELECT au_id,principal_id,request_id FROM creation_adoptions').fetchone()
                    self.assertEqual(adoption, (state['id'], intent['creator_principal_id'], request_id))
                    self.assertEqual(state['id'], intent['allocated_au_id'])
                    self.assertEqual(cx.execute('SELECT COUNT(*) FROM charters').fetchone()[0], 1)
            self.stop(); self.start()
            receipt = self.request('/api/v1/receipts?id=' + request_id)[1]['receipt']
            self.assertEqual(receipt['status'], 'unknown')
            self.assertEqual(receipt['organization_id'], intent['allocated_au_id'])
            self.assertEqual(self.request('/api/commands', request)[1]['receipt'], receipt)
            self.assertEqual({path.name: path.read_bytes() for path in directory.glob('*') if path.is_file()}, before)
            self.assertEqual(self.app.organizations(), [])


if __name__ == '__main__':
    unittest.main()
