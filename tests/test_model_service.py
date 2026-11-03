"""Controlled service contracts; no external account/model calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_union.engine import Engine, Rejected
from ai_union.executor import ExecutionFailure
from ai_union.model_accounts import ModelAccounts
from ai_union.model_api import configure_connection, resolve_connection
from ai_union.model_service import ModelServiceTransport, ServiceError, validate_service_config
from ai_union.model_portability import export_connections, validate_bundle
from tests.support import CHARTER, RESOURCES


class Service:
    def __init__(self, au):
        self.grant = {'id':'grant-a','au_id':au,'account_ref':'account-a','revision':1,'revoked_at':None,'model_ids':['model-a']}
        self.posts = 0
        self.lost = False
        self.state = 'completed'
        self.body = None

    def call(self, method, path, body=None, **kwargs):
        if path.startswith('/v1/grants/'): return copy.deepcopy(self.grant)
        if method == 'POST' and path == '/v1/requests':
            self.posts += 1; self.body = body
            if self.lost: raise ServiceError('lost_receipt')
            return {}
        return {}

    def request(self, rid, au):
        return {'id':rid,'au_id':au,'state':self.state,'result':{
            'message':{'role':'assistant','content':'controlled test','_native':{'message':{'role':'assistant','content':[{'type':'reasoning','text':'test','signature':'signature-test'}]}}},
            'usage':{'input_tokens':10,'output_tokens':5}}}

    def events(self, rid, au, after):
        return {'events':[{'request_id':rid,'seq':1,'type':'text_delta','payload':{'text':'controlled test'}}] if after == 0 else []}


class ModelServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.key = 'controlled-board-key'
        self.engine = Engine.create(Path(self.temp.name) / 'au','Controlled AU','test',CHARTER,RESOURCES,'board',self.key)
        self.service = Service(self.engine.state()['id'])
        self.mock = patch('ai_union.model_service.ModelServiceClient', return_value=self.service)
        self.mock.start(); self.addCleanup(self.mock.stop)
        self.config = ModelAccounts.config({'id':'grant-a','name':'Go test','model':'model-a'})
        configure_connection(self.engine,self.key,'go',self.config,'controlled adoption',api_key='')
        self.connection = resolve_connection(self.engine,'go')
        self.transport = ModelServiceTransport(self.engine.root,self.connection,client=self.service)

    def test_lost_acceptance_queries_same_id_and_preserves_native_checkpoint(self):
        self.service.lost = True
        package = self.engine.begin_connection_test(self.transport.metadata)
        message,usage = self.transport.chat(package,[{'role':'user','content':'test'}],[])
        self.assertEqual(self.service.posts,1)
        self.assertEqual(message['_native']['message']['content'][0]['signature'],'signature-test')
        self.assertIsNone(usage['cost_minor'])
        self.assertEqual(usage['cost_basis'],'subscription')
        self.assertEqual(self.service.body['deadlines']['task_ms'],RESOURCES['timeout_seconds']*1000)
        with self.assertRaises(Rejected): self.transport.chat(package,[{'role':'user','content':'test'}],[])
        self.assertEqual(self.service.posts,1)

    def test_interrupted_is_unknown_and_cannot_supply_executable_message(self):
        self.service.state = 'interrupted'
        package = self.engine.begin_connection_test(self.transport.metadata)
        with self.assertRaises(ExecutionFailure) as failure: self.transport.chat(package,[{'role':'user','content':'test'}],[])
        self.assertTrue(failure.exception.unknown)
        self.assertEqual(self.service.posts,1)

    def test_conflicting_request_is_unknown_and_never_adopts_a_different_payload(self):
        package = self.engine.begin_connection_test(self.transport.metadata)
        with patch.object(self.service,'call',side_effect=ServiceError('conflict',409)), patch.object(self.service,'request') as lookup:
            with self.assertRaises(ExecutionFailure) as failure: self.transport.chat(package,[{'role':'user','content':'test'}],[])
        self.assertTrue(failure.exception.unknown)
        lookup.assert_not_called()

    def test_explicit_pre_dispatch_rejection_does_not_claim_unknown_provider_execution(self):
        package = self.engine.begin_connection_test(self.transport.metadata)
        with patch.object(self.service,'call',side_effect=ServiceError('not_granted',403)):
            with self.assertRaises(ExecutionFailure) as failure: self.transport.chat(package,[{'role':'user','content':'test'}],[])
        self.assertFalse(failure.exception.unknown)

    def test_grant_cannot_cross_au_or_enter_portable_bundle(self):
        self.service.grant['au_id'] = 'other-au'
        with self.assertRaises(Rejected): configure_connection(self.engine,self.key,'wrong',self.config,'test')
        exported = export_connections(self.engine)
        self.assertIsNone(exported['connections'][0]['config']['grant_ref'])
        self.assertFalse(exported['connections'][0]['config']['enabled'])
        validate_bundle(exported)
        exported['connections'][0]['config'] = self.config
        with self.assertRaises(Rejected): validate_bundle(exported)

    def test_connection_change_prevents_dispatch_and_unknown_fields_are_rejected(self):
        package = self.engine.begin_connection_test(self.transport.metadata)
        configure_connection(self.engine,self.key,'go',{**self.config,'enabled':False},'disable')
        with self.assertRaises(Rejected): self.transport.chat(package,[{'role':'user','content':'test'}],[])
        self.assertEqual(self.service.posts,0)
        with self.assertRaises(Rejected): validate_service_config({**self.config,'api_key':'must-not-accept'})
