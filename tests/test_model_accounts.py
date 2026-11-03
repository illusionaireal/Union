"""Account adoption is platform-only; controlled backend, zero model calls."""
import copy
import tempfile
import unittest
from unittest.mock import patch
from ai_union.console import Console
from ai_union.engine import Rejected
from ai_union.model_accounts import ModelAccounts
from ai_union.model_service import ServiceError
from ai_union.model_api import list_connections
from tests.support import CHARTER, RESOURCES


class Backend:
    def __init__(self): self.grants={}; self.posts=0; self.lose=False
    def call(self, method, path, body=None, **kwargs):
        if method == 'POST' and path == '/v1/grants':
            self.posts += 1
            self.grants[body['id']] = copy.deepcopy(body) | {'revision':1,'revoked_at':None}
            if self.lose: raise ServiceError('lost_receipt')
            return self.grants[body['id']]
        if method == 'GET' and path.startswith('/v1/grants/'):
            return self.grants[path.rsplit('/',1)[1]]
        raise AssertionError('Unexpected call')


class ModelAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.app=Console(self.temp.name); self.addCleanup(self.app.close)
        self.admin=self.app.new_session('board',platform_admin=True)
        self.backend=Backend(); self.subject=ModelAccounts(self.app,self.backend)
        stub=patch('ai_union.model_service.ModelServiceClient',return_value=self.backend)
        stub.start(); self.addCleanup(stub.stop)
        result=self.app.command(self.admin,{'id':'create-au','kind':'create','organization_id':None,'base_version':None,
            'data':{'name':'Controlled AU','goal':'test','board_name':'board','charter':CHARTER,'resources':RESOURCES}})
        self.org=result['organization_id']; self.engine=self.app.engine(self.admin,self.org)
        self.command={'id':'adopt-a','action':'adopt','organization_id':self.org,'account_ref':'account-a',
          'model':'model-a','connection_id':'go','name':'Controlled Go','bind_default':True,'reason':'controlled adoption'}

    def test_platform_only_and_replay_does_not_duplicate_grant_or_connection(self):
        for token in [self.app.new_session('board'),self.app.new_session('observer'),self.app.new_session('board',organizations=[self.org])]:
            with self.assertRaises(Rejected): self.subject.command(token,self.command)
        self.assertEqual(self.backend.posts,0)
        receipt=self.subject.command(self.admin,self.command)
        self.assertEqual(receipt['status'],'succeeded',receipt)
        self.assertEqual(self.subject.command(self.admin,self.command),receipt)
        self.assertEqual(self.backend.posts,1)
        self.assertEqual(list_connections(self.engine)[0]['revision'],1)
        self.assertEqual(self.engine.state()['execution_config']['api_connection_id'],'go')
        with self.assertRaises(Rejected): self.subject.command(self.admin,self.command|{'model':'different'})

    def test_lost_grant_receipt_requires_explicit_lookup_and_never_reposts(self):
        self.backend.lose=True
        receipt=self.subject.command(self.admin,self.command)
        self.assertEqual(receipt['status'],'unknown')
        self.assertEqual(list_connections(self.engine),[])
        self.subject.command(self.admin,self.command)
        self.assertEqual(self.backend.posts,1)
        completed=self.subject.command(self.admin,{'id':'finish-a','action':'finish_adoption','target_id':'adopt-a'})
        self.assertEqual(completed['status'],'succeeded',completed)
        self.assertEqual(self.backend.posts,1)
        self.assertEqual(list_connections(self.engine)[0]['revision'],1)
        self.subject.command(self.admin,{'id':'finish-again','action':'finish_adoption','target_id':'adopt-a'})
        self.assertEqual(list_connections(self.engine)[0]['revision'],1)
        self.assertEqual(self.subject.receipt(self.admin,'adopt-a')['status'],'succeeded')

    def test_wrong_au_grant_does_not_save_or_bind(self):
        self.backend.lose=True
        self.subject.command(self.admin,self.command)
        self.backend.grants['adopt-a']['au_id']='another-au'
        receipt=self.subject.command(self.admin,{'id':'finish-a','action':'finish_adoption','target_id':'adopt-a'})
        self.assertEqual(receipt['status'],'unknown')
        self.assertEqual(list_connections(self.engine),[])
        self.assertNotIn('api_connection_id',self.engine.state().get('execution_config',{}))

    def test_connection_and_default_roll_back_together(self):
        with patch('ai_union.model_accounts.bind_connection',side_effect=Rejected('controlled failure')):
            receipt=self.subject.command(self.admin,self.command)
        self.assertEqual(receipt['status'],'unknown')
        self.assertEqual(list_connections(self.engine),[])
        receipt=self.subject.command(self.admin,{'id':'finish-a','action':'finish_adoption','target_id':'adopt-a'})
        self.assertEqual(receipt['status'],'succeeded',receipt)
