import copy
import json
import tempfile
import unittest
from pathlib import Path
from ai_union.au_contract import describe_au_v1, configure_descriptor
from ai_union.engine import Rejected
from tests.support import init, organization
from tests import test_console

class AUContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.e=init(Path(self.temp.name));organization(self.e)

    def test_legacy_projection_is_readonly_and_does_not_grant_host_actor_internal_powers(self):
        before=self.e.state();data=describe_au_v1(self.e)
        self.assertEqual(data['supported_operations'],[])
        self.assertEqual(data['governance']['authority_source'],'legacy_board')
        self.assertEqual(data['governance']['controller_ref']['principal_id'],'legacy-board:'+before['id'])
        self.assertEqual(data['member_refs']['m1'],{'au_id':before['id'],'member_id':'m1'})
        self.assertNotIn('board_hash',json.dumps(data));self.assertEqual(before,self.e.state())
        member=describe_au_v1(self.e,actor='m1',assignment_id='a1')
        self.assertIn('create_work',member['supported_operations'])
        with self.assertRaises(Rejected):describe_au_v1(self.e,actor='m2',assignment_id='a2')

    def test_descriptor_is_metadata_with_version_and_actual_board_validation(self):
        v=self.e.state()['version'];ref={'principal_id':'external-org:ops','display_name':'Company sponsor'}
        with self.assertRaises(Rejected):configure_descriptor(self.e,'bad-key',ref,'reason',v)
        configure_descriptor(self.e,'test-key',ref,'reason',v)
        data=describe_au_v1(self.e)
        self.assertEqual(data['governance']['controller_ref'],ref)
        self.assertEqual(data['governance']['authority_source'],'legacy_board')
        with self.assertRaises(Rejected):configure_descriptor(self.e,'test-key',ref,'reason',v)
        self.assertNotIn('controller_ref',self.e.charter())
        with self.assertRaises(Rejected):configure_descriptor(self.e,'test-key',ref|{'authority_source':'sso'},'x',self.e.state()['version'])

    def test_projection_rejects_bootstrap_actor_with_forged_assignment(self):
        other=init(Path(self.temp.name)/'bootstrap-org')
        self.assertEqual(describe_au_v1(other)['supported_operations'],[])
        with self.assertRaises(Rejected):describe_au_v1(other,actor='bootstrap',assignment_id='fake-assignment')
        with self.assertRaises(Rejected):describe_au_v1(self.e,actor='bootstrap',assignment_id='a1')

    def test_descriptor_cannot_store_credential_or_invalid_type(self):
        for ref in ({'principal_id':'test-key','display_name':'name'}, {'principal_id':42,'display_name':'name'}, {'principal_id':'x','display_name':''}):
            with self.assertRaises(Rejected):configure_descriptor(self.e,'test-key',ref,'x',self.e.state()['version'])

class ContractConsoleTests(unittest.TestCase):
    setUp=test_console.ConsoleTests.setUp
    command=test_console.ConsoleTests.command

    def test_same_creation_contract_and_replay_preserve_descriptor(self):
        from tests.support import CHARTER,RESOURCES
        data={'name':'Internal AU','goal':'company task','board_name':'sponsor','charter':CHARTER,'resources':RESOURCES,'controller_ref':{'principal_id':'external-org:ops','display_name':'Ops'}}
        r=self.command('create',data,org_id=None,request_id='internal-create')
        self.assertEqual(r['status'],'succeeded',r)
        r2=self.command('create',data,org_id=None,request_id='internal-create');self.assertEqual(r,r2)
        engine=self.app.engine(self.board,r['organization_id'])
        self.assertEqual(describe_au_v1(engine)['governance']['controller_ref'],data['controller_ref'])
        self.assertEqual(self.app.observe(self.observer,r['organization_id'])['au_contract']['supported_operations'],[])
        isolated=self.app.new_session('observer',organizations=[])
        with self.assertRaises(Rejected):self.app.observe(isolated,r['organization_id'])

    def test_existing_descriptor_command_is_scoped_and_idempotent(self):
        data={'controller_ref':{'principal_id':'external-org:ops','display_name':'Ops'},'reason':'business context'}
        before=self.e.state()['version']
        with self.assertRaises(Rejected):self.command('controller_descriptor',data,session=self.observer)
        r=self.command('controller_descriptor',data,request_id='descriptor-change',version=before)
        self.assertEqual(r['status'],'succeeded',r)
        again=self.command('controller_descriptor',data,request_id='descriptor-change',version=before)
        self.assertEqual(r,again)
        self.assertEqual(self.e.state()['version'],before+1)

    def test_rejected_descriptor_does_not_log_board_credential(self):
        key=(self.e.root/'board.key').read_text().strip()
        with self.assertRaises(Rejected):
            self.command('controller_descriptor',{'controller_ref':{'principal_id':'external-org:ops','display_name':key},'reason':'context'},request_id='secret-descriptor')
        with self.e.read_transaction() as cx:
            rows=[r[0] for r in cx.execute('SELECT payload FROM commands')]
            rows += [r[0] for r in cx.execute('SELECT data FROM events')]
            rows += [r[0] for r in cx.execute("SELECT value FROM meta WHERE key='au_descriptor_v1'")]
        self.assertFalse(any(key in value for value in rows))
