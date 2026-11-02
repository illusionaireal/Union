import copy
import json
import unittest
from ai_union.engine import Rejected
from ai_union.model_api import list_connections
from ai_union.model_portability import export_connections, import_connections
from tests import test_model_api as api_tests


class PortabilityTests(unittest.TestCase):
    setUp = api_tests.ModelAPITests.setUp
    command = api_tests.ModelAPITests.command
    configure = api_tests.ModelAPITests.configure

    def test_export_has_no_secret_or_host_credential_reference(self):
        self.configure()
        bundle=export_connections(self.e)
        self.assertNotIn(api_tests.SECRET,json.dumps(bundle))
        self.assertEqual(set(bundle['connections'][0]), {'id','config'})

    def test_conflict_rolls_back_whole_import_and_rename_preserves_old_key(self):
        self.configure(); bundle=export_connections(self.e)
        new=copy.deepcopy(bundle['connections'][0]); new['id']='new'
        bundle['connections'].insert(0,new)
        key=(self.e.root/'board.key').read_text(encoding='utf-8').strip()
        with self.assertRaises(Rejected): import_connections(self.e,key,bundle,'reject','test import')
        self.assertEqual([c['id'] for c in list_connections(self.e)],['primary'])
        result=import_connections(self.e,key,bundle,'rename','test import')
        self.assertEqual(result[1]['id'],'primary-import-1')
        connections={c['id']:c for c in list_connections(self.e)}
        self.assertTrue(connections['primary']['has_api_key'])
        self.assertFalse(connections['primary-import-1']['has_api_key'])
        self.assertIsNone(self.e.state().get('execution_config',{}).get('api_connection_id'))

    def test_import_rejects_secrets_before_command_storage(self):
        bundle={'version':1,'connections':[{'id':'new','config':dict(self.config, api_key_env='HOST_SECRET')} ]}
        with self.assertRaises(Rejected):
            self.command('api_import',{'bundle':bundle,'mode':'reject','reason':'test import'})
        self.assertNotIn(b'HOST_SECRET',self.e.db.read_bytes())

    def test_import_command_is_idempotent_and_replace_clears_key(self):
        self.configure(); bundle=export_connections(self.e)
        receipt=self.command('api_import',{'bundle':bundle,'mode':'replace','reason':'test import'},request_id='import-once')
        self.assertEqual(receipt['status'],'succeeded')
        self.assertFalse(list_connections(self.e)[0]['has_api_key'])
        version=self.e.state()['version']
        again=self.command('api_import',{'bundle':bundle,'mode':'replace','reason':'test import'},request_id='import-once',version=receipt['base_version'])
        self.assertEqual(again,receipt); self.assertEqual(self.e.state()['version'],version)
