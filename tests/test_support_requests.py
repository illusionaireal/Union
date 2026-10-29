import copy
import tempfile
import unittest
from pathlib import Path
from ai_union.support_requests import respond
from ai_union.agent_protocol import tools_for, compile_tool
from ai_union.engine import Engine, Rejected
from tests import test_console
from tests.support import CHARTER,RESOURCES,organization,decision

class SupportRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        c=copy.deepcopy(CHARTER);c['allowed_operations'].append('request_support')
        self.e=Engine.create(Path(self.temp.name),'au','goal',c,RESOURCES,'sponsor','test-key');organization(self.e)

    def enable(self):
        s=self.e.state();p=s['positions']['p1']
        self.e.apply_decision(decision(self.e,[{'op':'update_position','position_id':'p1','title':p['title'],'mandate':p['mandate'],'permissions':p['permissions']+['request_support']}]),'m1','a1')

    def raise_request(self):
        self.enable();p=self.e.begin_decision('fixture')
        result=compile_tool(p,'request_support',{'kind':'tool','need':'Read-only knowledge access','reason':'Need source information'})
        self.e.finish_decision(p['run_id'],result,{})
        return next(iter(self.e.state()['support_requests']))

    def test_capability_is_opt_in_and_cannot_grant_actual_tools(self):
        p=self.e.begin_decision('fixture')
        self.assertNotIn('request_support',{t['function']['name'] for t in tools_for(p)})
        self.e.fail_run(p['run_id'],'no request')
        key=self.raise_request();r=self.e.state()['support_requests'][key]
        self.assertEqual(r['status'],'pending');self.assertEqual(r['raised_by'],'m1')
        before=copy.deepcopy(self.e.charter());resources=copy.deepcopy(self.e.state()['resources'])
        respond(self.e,'test-key',key,'accepted_for_action','Will inspect integration',self.e.state()['version'])
        self.assertEqual(self.e.charter(),before);self.assertEqual(self.e.state()['resources'],resources)
        self.assertEqual(self.e.state()['support_requests'][key]['status'],'accepted_for_action')

    def test_responses_require_actual_board_and_version_and_persist(self):
        key=self.raise_request();v=self.e.state()['version']
        with self.assertRaises(Rejected):respond(self.e,'wrong',key,'declined','reason',v)
        respond(self.e,'test-key',key,'needs_information','Specify data scope',v)
        with self.assertRaises(Rejected):respond(self.e,'test-key',key,'declined','reason',v)
        restored=Engine(self.e.root)
        self.assertEqual(restored.state()['support_requests'][key]['status'],'needs_information')
        p=self.e.begin_work('w1','fixture')
        self.assertNotIn('support_requests',p['context'])

    def test_bootstrap_cannot_raise_request_or_supply_forged_source(self):
        from ai_union.support_requests import propose
        operation={'op':'request_support','id':'request-1','kind':'tool','need':'source','reason':'purpose'}
        with self.assertRaises(Rejected):propose({},operation,'bootstrap',None,[])
        self.enable();p=self.e.begin_decision('fixture')
        with self.assertRaises(ValueError):compile_tool(p,'request_support',{'kind':'tool','need':'x','reason':'y','raised_by':'someone-else'})


class SupportConsoleTests(unittest.TestCase):
    setUp=test_console.ConsoleTests.setUp
    command=test_console.ConsoleTests.command

    def test_console_response_scope_replay_and_no_implicit_grant(self):
        charter=self.e.charter();charter['allowed_operations'].append('request_support')
        self.command('amend',{'charter':charter,'reason':'fixture request'})
        organization(self.e)
        p1=self.e.state()['positions']['p1']
        self.e.apply_decision(decision(self.e,[{'op':'update_position','position_id':'p1','title':p1['title'],'mandate':p1['mandate'],'permissions':p1['permissions']+['request_support']}]),'m1','a1')
        p=self.e.begin_decision('fixture')
        self.e.finish_decision(p['run_id'],compile_tool(p,'request_support',{'kind':'resources','need':'More calls','reason':'Need evaluation'}),{})
        key=next(iter(self.e.state()['support_requests']))
        data={'request_id':key,'status':'accepted_for_action','reason':'Will review resource request'}
        with self.assertRaises(Rejected):self.command('respond_request',data,session=self.observer)
        limited=self.app.new_session('board',organizations=[])
        with self.assertRaises(Rejected):self.command('respond_request',data,session=limited)
        before=copy.deepcopy(self.e.state()['resources']);v=self.e.state()['version']
        r=self.command('respond_request',data,request_id='response-1',version=v)
        self.assertEqual(r['status'],'succeeded',r)
        self.assertEqual(self.command('respond_request',data,request_id='response-1',version=v),r)
        self.assertEqual(before,self.e.state()['resources'])

    def test_response_rejects_board_key_before_command_persistence(self):
        key=(self.e.root/'board.key').read_text().strip()
        with self.assertRaises(Rejected):self.command('respond_request',{'request_id':'request-id','status':'declined','reason':key},request_id='secret-response')
        with self.e.read_transaction() as cx:
            rows=[r[0] for r in cx.execute('SELECT payload FROM commands')]
            rows += [r[0] for r in cx.execute('SELECT data FROM events')]
        self.assertFalse(any(key in value for value in rows))
