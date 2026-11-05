"""Real legacy entrypoints reject core V1 while legacy controls remain usable."""
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

from ai_union.engine import Rejected, encoded
from ai_union.model_accounts import ModelAccounts
from tests import test_core_creation as http, test_model_accounts as models
from tests.test_core_isolation import files
from tests.support import CHARTER, RESOURCES


class CoreEntrypointTests(unittest.TestCase):
    setUp = http.CoreCreationTests.setUp
    start = http.CoreCreationTests.start
    stop = http.CoreCreationTests.stop
    request = http.CoreCreationTests.request
    setup_account = http.CoreCreationTests.setup_account
    create = http.CoreCreationTests.create

    def prepared(self):
        receipt = self.create()
        au_id = receipt['organization_id']
        with self.app.read_catalog() as cx:
            folder = cx.execute('SELECT folder FROM organizations WHERE id=?', (au_id,)).fetchone()[0]
        return au_id, self.root / folder

    def test_cli_and_workspace_reject_before_reading_secrets_or_running_anything(self):
        _, directory = self.prepared()
        before = files(directory)
        for module, args in (
                ('ai_union', ['status']),
                ('ai_union', ['run', '--executor', 'fixture', '--fixture', 'must-not-read', '--max-steps', '1']),
                ('ai_union', ['amend', '--charter', 'must-not-read', '--board-key-file', 'must-not-read', '--reason', 'test']),
                ('ai_union', ['api-test', '--board-key-file', 'must-not-read']),
                ('ai_union', ['api-configure', '--connection-id', 'test', '--config', 'must-not-read', '--board-key-file', 'must-not-read', '--reason', 'test']),
                ('ai_union.workspace', ['status']),
                ('ai_union.workspace', ['configure', '--config', 'must-not-read', '--board-key-file', 'must-not-read', '--reason', 'test'])):
            with self.subTest(module=module, command=args[0]):
                result = subprocess.run([sys.executable, '-B', '-m', module, '--root', str(directory), *args],
                                        capture_output=True, text=True, encoding='utf-8', timeout=20)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('准备态', json.loads(result.stderr)['error'])
                self.assertEqual(files(directory), before)

    def test_old_http_commands_and_reads_cannot_write_or_dispatch_prepared_au(self):
        au_id, directory = self.prepared()
        before = files(directory)
        commands = {'start': {'executor': 'fixture', 'max_steps': 1}, 'pause': {},
                    'event': {'event_id': 'e', 'kind': 'opinion', 'content': 'text', 'source': 'fixture', 'simulated': True},
                    'amend': {'charter': CHARTER, 'reason': 'test'},
                    'resources': {'resources': RESOURCES, 'reason': 'test'},
                    'model': {'model': 'fixture', 'reason': 'test'},
                    'api_test': {'connection_id': 'test'},
                    'api_connection': {'connection_id': 'test', 'config': {}, 'reason': 'test'},
                    'api_binding': {'connection_id': 'test', 'reason': 'test'}}
        with patch.object(self.app, 'executor_factory', side_effect=AssertionError('must not dispatch')):
            for kind, data in commands.items():
                with self.subTest(kind=kind):
                    status, value, _ = self.request('/api/commands', {'id': 'denied-' + kind, 'kind': kind,
                        'organization_id': au_id, 'base_version': 0, 'data': data})
                    self.assertEqual((status, value.get('code')), (409, 'unsupported_capability'), value)
                    self.assertEqual(files(directory), before)
        for endpoint in ('snapshot', 'model-connections', 'model-export', 'model-costs'):
            status, value, _ = self.request('/api/' + endpoint + '?organization_id=' + au_id)
            self.assertEqual((status, value.get('code')), (409, 'unsupported_capability'), value)
        self.assertEqual(self.app.jobs, [])
        self.assertEqual(files(directory), before)

    def test_model_account_adoption_rejects_before_external_grant_and_catalog_receipt(self):
        au_id, directory = self.prepared()
        before = files(directory)
        backend = models.Backend()
        subject = ModelAccounts(self.app, backend)
        admin = self.app.new_session('board', platform_admin=True)
        with self.assertRaises(Rejected):
            subject.command(admin, {'id': 'forbidden-adoption', 'action': 'adopt', 'organization_id': au_id,
                'account_ref': 'controlled', 'model': 'controlled', 'connection_id': 'go', 'name': 'test',
                'bind_default': True, 'reason': 'test'})
        self.assertEqual(backend.posts, 0)
        with self.app.read_catalog() as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_account_commands WHERE id='forbidden-adoption'").fetchone()[0], 0)
        self.assertEqual(files(directory), before)

    def test_mixed_profiles_list_restart_and_close_preserve_v1_and_legacy_behavior(self):
        au_id, directory = self.prepared()
        legacy = self.create(http.creation('legacy') | {'kind': 'create'})['organization_id']
        engine = self.app.engine(self.token, legacy)
        engine.set_paused(False)
        version = engine.state()['version']
        status, result, _ = self.request('/api/commands', {'id': 'legacy-event', 'kind': 'event', 'organization_id': legacy,
            'base_version': version, 'data': {'event_id': 'event', 'kind': 'opinion', 'content': 'legacy remains usable',
                                            'source': 'controlled', 'simulated': True}})
        self.assertEqual((status, result['receipt']['status']), (200, 'succeeded'))
        before = files(directory)
        self.assertEqual({item['id'] for item in self.request('/api/session')[1]['organizations']}, {au_id, legacy})
        host = self.app.new_session('board', platform_admin=True)
        self.assertEqual([item['id'] for item in self.request('/api/session', token=host)[1]['organizations']], [legacy])
        self.stop(); self.start()
        self.assertEqual(self.request('/api/v1/aus/' + au_id)[0], 200)
        self.assertTrue(self.app.engine(self.token, legacy).paused())
        self.assertTrue(any(event['id'] == 'event' for event in self.app.engine(self.token, legacy).events()))
        self.assertEqual(files(directory), before)

    def test_wrong_v1_mapping_is_rejected_without_exposing_or_mutating_other_au(self):
        au_id, directory = self.prepared()
        second = self.create(http.creation('second', name='Private other AU'))['organization_id']
        with self.app.read_catalog() as cx:
            folder = cx.execute('SELECT folder FROM organizations WHERE id=?', (second,)).fetchone()[0]
        before = files(self.root / 'organizations')
        with self.app.catalog() as cx:
            cx.execute('UPDATE organizations SET folder=? WHERE id=?', (folder, au_id))
        try:
            status, value, _ = self.request('/api/v1/aus/' + au_id)
            self.assertEqual((status, value.get('code')), (409, 'incompatible_state'))
            self.assertNotIn('Private other AU', str(value))
            with self.assertRaises(Rejected):
                self.app.close()
            self.assertEqual(files(self.root / 'organizations'), before)
        finally:
            with self.app.catalog() as cx:
                cx.execute('UPDATE organizations SET folder=? WHERE id=?', (str(directory.relative_to(self.root)), au_id))


if __name__ == '__main__':
    unittest.main()
