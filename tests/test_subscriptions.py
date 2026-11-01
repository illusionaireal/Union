import json
from pathlib import Path
import tempfile
import unittest
from ai_union.console import Console
from ai_union.engine import Rejected
from ai_union.subscriptions import Subscriptions


class Backend:
    def __init__(self): self.calls=[]; self.fail=False
    def call(self, method, path, data=None, timeout=4):
        self.calls.append((method,path,data))
        if self.fail: raise OSError('PRIVATE_SENTINEL key=secret')
        if path=='/provider': return {'connected':[], 'all':[{'apiKey':'PRIVATE_SENTINEL'}]}
        if path=='/provider/auth': return {'openai':[{'type':'oauth','label':'ChatGPT (headless)'}]}
        if path.endswith('/authorize'): return {'url':'https://auth.openai.com/codex/device','instructions':'Enter TEST-CODE'}
        return True


class SubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.app=Console(self.temp.name); self.addCleanup(self.app.close)
        self.backend=Backend(); self.subject=Subscriptions(self.app,self.backend)
        self.admin=self.app.new_session('board',platform_admin=True)

    def test_platform_permission_required_and_no_backend_for_denied(self):
        for token in [self.app.new_session('board'),self.app.new_session('observer'),self.app.new_session('board',organizations=[])]:
            with self.assertRaises(Rejected): self.subject.status(token)
            with self.assertRaises(Rejected): self.subject.command(token,{'id':'test-1','action':'authorize_chatgpt'})
        self.assertEqual(self.backend.calls,[])

    def test_go_save_idempotent_and_secret_not_in_receipt_or_database(self):
        request={'id':'go-1','action':'save_go','api_key':'PRIVATE_SENTINEL'}
        result=self.subject.command(self.admin,request)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(self.subject.command(self.admin,request),result)
        self.assertEqual(len(self.backend.calls),1)
        with self.assertRaises(Rejected): self.subject.command(self.admin,dict(request,api_key='another'))
        self.assertNotIn(b'PRIVATE_SENTINEL',Path(self.app.db).read_bytes())
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result))

    def test_unknown_is_not_replayed_and_provider_error_is_not_reflected(self):
        self.backend.fail=True
        request={'id':'unknown-1','action':'save_go','api_key':'PRIVATE_SENTINEL'}
        result=self.subject.command(self.admin,request)
        self.assertEqual(result['status'],'unknown')
        self.subject.command(self.admin,request)
        self.assertEqual(len(self.backend.calls),1)
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(self.subject.receipt(self.admin,'unknown-1')))

    def test_status_projects_only_public_fields(self):
        result=self.subject.status(self.admin)
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result))
        self.assertEqual([p['id'] for p in result['providers']],['opencode-go','openai'])

    def test_callback_is_bound_to_session_and_uses_fixed_provider(self):
        import unittest.mock
        with unittest.mock.patch('ai_union.subscriptions.threading.Thread'):
            result=self.subject.command(self.admin,{'id':'auth-1','action':'authorize_chatgpt'})
        self.assertEqual(result['status'],'authorizing')
        public=self.subject.receipt(self.app.new_session('board',platform_admin=True),'auth-1')
        self.assertNotIn('url',public);self.assertNotIn('instructions',public)
        with self.assertRaises(Rejected): self.subject.command(self.admin,{'id':'auth-2','action':'authorize_chatgpt'})
        self.subject._complete('auth-1',0,result)
        self.assertEqual(self.subject.receipt(self.admin,'auth-1')['status'],'succeeded')

    def test_restart_retains_unknown_and_does_not_reauthorize(self):
        import unittest.mock
        with unittest.mock.patch('ai_union.subscriptions.threading.Thread'):
            self.subject.command(self.admin,{'id':'restart-1','action':'authorize_chatgpt'})
        before=len(self.backend.calls)
        Subscriptions(self.app,self.backend)
        self.assertEqual(self.subject.receipt(self.admin,'restart-1')['status'],'unknown')
        self.assertEqual(len(self.backend.calls),before)

    def test_host_fields_and_bad_authorization_url_are_rejected(self):
        with self.assertRaises(Rejected): self.subject.command(self.admin,{'id':'bad-1','action':'authorize_chatgpt','url':'http://evil'})
        original=self.backend.call
        self.backend.call=lambda method,path,data=None,timeout=4: {'url':'https://evil.example/','instructions':'secret'} if path.endswith('/authorize') else original(method,path,data,timeout)
        result=self.subject.command(self.admin,{'id':'bad-2','action':'authorize_chatgpt'})
        self.assertEqual(result['status'],'unknown'); self.assertNotIn('url',result)

    def test_unknown_blocks_new_identity_and_explicit_reconciliation_does_not_replay(self):
        self.backend.fail=True
        self.subject.command(self.admin,{'id':'first','action':'save_go','api_key':'test-key'})
        with self.assertRaises(Rejected): self.subject.command(self.admin,{'id':'second','action':'save_go','api_key':'test-key'})
        before=len(self.backend.calls)
        with self.assertRaises(Rejected): self.subject.command(self.admin,{'id':'rec-1','action':'reconcile','target_id':'first','confirmed_ended':False})
        receipt=self.subject.command(self.app.new_session('board',platform_admin=True),{'id':'rec-2','action':'reconcile','target_id':'first','confirmed_ended':True})
        self.assertEqual(receipt['previous_status'],'unknown');self.assertEqual(receipt['status'],'reconciled')
        self.assertEqual(len(self.backend.calls),before)

    def test_auth_catalog_is_private_and_live_callback_cannot_be_reconciled(self):
        import os
        if os.name!='nt': self.assertEqual(Path(self.app.db).stat().st_mode & 0o777,0o600)
        self.backend.fail=True
        self.subject.command(self.admin,{'id':'live','action':'save_go','api_key':'test-key'})
        self.subject.active.add('live')
        with self.assertRaises(Rejected): self.subject.command(self.admin,{'id':'rec-live','action':'reconcile','target_id':'live','confirmed_ended':True})

    def test_reconcile_identity_cannot_be_reused_for_different_target(self):
        self.backend.fail=True
        self.subject.command(self.admin,{'id':'original','action':'save_go','api_key':'test-key'})
        command={'id':'stable-reconcile','action':'reconcile','target_id':'original','confirmed_ended':True}
        result=self.subject.command(self.admin,command)
        self.assertEqual(self.subject.command(self.admin,command),result)
        self.assertNotIn('reconciled_by',result)
        with self.assertRaises(Rejected): self.subject.command(self.admin,dict(command,target_id='different'))

    def test_http_endpoint_enforces_origin_role_and_cookie_without_exposing_key(self):
        import http.client,threading
        from ai_union.server import Server
        server=Server(self.app);server.subscriptions=self.subject
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def stop(): server.shutdown();server.server_close();thread.join()
        self.addCleanup(stop)
        def call(token,origin):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
            conn.request('POST','/api/subscription-commands',json.dumps({'id':'http-go','action':'save_go','api_key':'PRIVATE_SENTINEL'}),{'Origin':origin,'Content-Type':'application/json','Cookie':server.cookie_name+'='+token})
            result=conn.getresponse();status=result.status;body=result.read().decode();conn.close();return status,body
        self.assertEqual(call(self.admin,'https://evil.example')[0],403)
        self.assertEqual(call(self.app.new_session('board'),server.origin)[0],403)
        self.assertEqual(self.backend.calls,[])
        status,body=call(self.admin,server.origin);self.assertEqual(status,200)
        self.assertNotIn('PRIVATE_SENTINEL',body);self.assertEqual(len(self.backend.calls),1)
