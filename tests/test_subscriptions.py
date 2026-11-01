import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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


class NativeBackend:
    def __init__(self): self.calls=[];self.status='pending';self.bad_url=False
    def call(self, method, path, data=None, timeout=4):
        self.calls.append((method,path,data))
        if path == '/api/integration':
            return {'data':[{'id':'opencode','connections':[{'secret':'PRIVATE_SENTINEL'}]}]}
        if method == 'GET': return {'data':{'status':self.status}}
        go='/opencode/' in path
        return {'data':{'attemptID':'con_abc123','mode':'auto','url':('https://evil.example/' if self.bad_url else
            'https://opencode.ai/console/auth/device?user_code=ABCD1234' if go else
            'https://auth.openai.com/api/accounts/authorize?state=TESTSTATE&redirect_uri=http%3A%2F%2F127.0.0.1%3A49152%2Fauth%2Fcallback'),
            'instructions':'Enter code: ABCD1234' if go else 'Complete authorization in browser.'}}


class NativeSubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=Console(self.temp.name);self.addCleanup(self.app.close)
        self.native=NativeBackend();self.backend=Backend()
        self.subject=Subscriptions(self.app,self.backend,self.native)
        self.admin=self.app.new_session('board',platform_admin=True)
        self.other=self.app.new_session('board',platform_admin=True)
        self.thread=patch('ai_union.subscriptions.threading.Thread');self.thread.start();self.addCleanup(self.thread.stop)

    def begin(self, action='authorize_chatgpt', id='native-1'):
        return self.subject.command(self.admin,{'id':id,'action':action})

    def callback(self, **changes):
        value={'id':'cb-1','action':'complete_chatgpt','target_id':'native-1',
               'callback_url':'http://127.0.0.1:49152/auth/callback?code=PRIVATE_SENTINEL&state=TESTSTATE&client_id=issued-client'}
        value.update(changes);return value

    def test_go_browser_account_uses_native_device_without_key_or_model(self):
        result=self.begin('authorize_go')
        self.assertEqual(result['status'],'authorizing');self.assertIn('ABCD1234',result['instructions'])
        self.assertEqual(self.native.calls[0],('POST','/api/integration/opencode/connect/oauth',{'methodID':'device'}))
        self.assertEqual(self.backend.calls,[])
        with self.assertRaises(Rejected): self.subject.command(self.admin,{'id':'second','action':'save_go','api_key':'key'})
        self.assertNotIn('url',self.subject.receipt(self.other,'native-1'))
        public=self.subject.status(self.admin);self.assertTrue(public['providers'][0]['connected'])
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(public))

    def test_chatgpt_browser_does_not_require_device_code_and_scopes_callback(self):
        result=self.begin();self.assertTrue(result['needs_callback'])
        self.assertEqual(self.native.calls[0][2],{'methodID':'chatgpt-token-sharing'})
        public=self.subject.receipt(self.other,'native-1');self.assertNotIn('url',public);self.assertNotIn('needs_callback',public)
        with self.assertRaises(Rejected):self.subject.command(self.other,self.callback())
        receipt=self.subject.command(self.admin,self.callback())
        self.assertFalse(receipt['needs_callback']);self.assertEqual(self.subject.command(self.admin,self.callback()),receipt)
        self.assertNotIn(b'PRIVATE_SENTINEL',Path(self.app.db).read_bytes())
        with self.assertRaises(Rejected):self.subject.command(self.admin,self.callback(id='cb-new'))

    def test_callback_rejects_ssrf_duplicate_state_mismatch_and_wrong_destination(self):
        self.begin()
        for url in ['http://evil.example/auth/callback?code=x&state=TESTSTATE',
                    'http://127.0.0.1:49153/auth/callback?code=x&state=TESTSTATE',
                    'http://127.0.0.1:49152/other?code=x&state=TESTSTATE',
                    'http://127.0.0.1:49152/auth/callback?code=x&state=BAD',
                    'http://127.0.0.1:49152/auth/callback?code=x&state=TESTSTATE&state=TESTSTATE',
                    'http://127.0.0.1:49152/auth/callback?code=x&state=TESTSTATE&redirect_uri=http://evil',
                    'http://user@127.0.0.1:49152/auth/callback?code=x&state=TESTSTATE',
                    'http://127.0.0.1:49152/auth/callback?code=x&state=TESTSTATE#secret']:
            with self.subTest(url=url),self.assertRaises((Rejected,ValueError)):
                self.subject.command(self.admin,self.callback(callback_url=url))
        self.assertEqual(len(self.native.calls),1)

    def test_callback_after_native_restart_or_terminal_never_relays(self):
        self.begin();self.native.status='complete'
        with self.assertRaises(Rejected):self.subject.command(self.admin,self.callback())
        self.native.call=lambda *a,**k: (_ for _ in ()).throw(OSError('PRIVATE_SENTINEL'))
        with self.assertRaises(OSError):self.subject.command(self.admin,self.callback())
        with self.app.read_catalog() as cx:self.assertEqual(cx.execute('SELECT count(*) FROM subscription_callbacks').fetchone()[0],0)

    def test_restart_strips_stale_links_and_does_not_replay(self):
        self.begin();before=len(self.native.calls);Subscriptions(self.app,self.backend,self.native)
        result=self.subject.receipt(self.admin,'native-1')
        self.assertEqual(result['status'],'unknown');self.assertNotIn('url',result);self.assertNotIn('needs_callback',result)
        self.assertEqual(len(self.native.calls),before)

    def test_terminal_poll_and_bad_native_url_are_redacted(self):
        receipt=self.begin('authorize_go');self.native.status='complete'
        self.subject._poll_native('native-1',receipt,{'provider':'opencode','attempt':'con_abc123'})
        self.assertEqual(self.subject.receipt(self.admin,'native-1')['status'],'succeeded')
        self.native.bad_url=True
        result=self.begin('authorize_chatgpt','bad-native')
        self.assertEqual(result['status'],'unknown');self.assertNotIn('url',result)

    def test_callback_relay_has_no_basic_no_redirect_and_failure_is_unknown(self):
        self.begin();self.subject.command(self.admin,self.callback())
        with patch('ai_union.subscriptions.urllib.request.build_opener') as build:
            build.return_value.open.side_effect=OSError('PRIVATE_SENTINEL')
            self.subject._relay_callback('native-1','http://127.0.0.1:49152/auth/callback?code=private')
            arg=build.return_value.open.call_args.args[0]
            self.assertIsInstance(arg,str)
            self.assertFalse(build.call_args.args[0].proxies)
            self.assertIsNone(build.call_args.args[1].redirect_request())
        receipt=self.subject.receipt(self.admin,'native-1');self.assertEqual(receipt['status'],'unknown')
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(receipt));self.assertNotIn('url',receipt)

    def test_exact_native_terminal_resolves_transport_unknown_without_replaying_callback(self):
        for status,expected in [('complete','succeeded'),('failed','failed'),('expired','failed')]:
            request_id='terminal-'+status;receipt=self.begin('authorize_chatgpt',request_id)
            receipt.update(status='unknown');self.subject._save(request_id,receipt)
            before=len(self.native.calls);self.native.status=status
            self.subject._poll_native(request_id,receipt,{'provider':'openai','attempt':'con_abc123'})
            result=self.subject.receipt(self.admin,request_id)
            self.assertEqual(result['status'],expected);self.assertEqual(result['previous_status'],'unknown')
            self.assertEqual(result['reconciliation_source'],'native_attempt')
            self.assertEqual([c[0] for c in self.native.calls[before:]],['GET'])
