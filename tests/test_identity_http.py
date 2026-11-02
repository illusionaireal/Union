import http.client
import json
import tempfile
import threading
import unittest
from ai_union.console import Console
from ai_union.server import Server


class IdentityHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.app=Console(self.temp.name); self.addCleanup(self.app.close)
        self.server=Server(self.app); self.addCleanup(self.server.server_close)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.addCleanup(self.thread.join); self.addCleanup(self.server.shutdown)

    def request(self, path, body=None, token=None, origin=None):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=4)
        headers={'Origin':origin or self.server.origin,'Content-Type':'application/json'}
        if token: headers['Cookie']=self.server.cookie_name+'='+token
        client.request('POST' if body is not None else 'GET', path, json.dumps(body) if body is not None else None, headers)
        response=client.getresponse(); result=(response.status,json.loads(response.read()),response.getheader('Set-Cookie'))
        client.close(); return result

    def test_anonymous_first_claim_and_cross_origin_rejections(self):
        data={'username':'owner','password':'correct-horse-password','remember':True}
        self.assertEqual(self.request('/api/auth/setup',data,origin='https://other.example')[0],403)
        self.assertTrue(self.request('/api/auth/status')[1]['can_setup'])
        status,result,cookie=self.request('/api/auth/setup',data)
        self.assertEqual(status,200);self.assertIn('HttpOnly',cookie);self.assertTrue(self.app.identity.configured())
        self.assertFalse(self.request('/api/auth/status')[1]['can_setup'])
        self.assertEqual(self.request('/api/auth/setup',{'username':'second','password':'correct-horse-password','remember':False})[0],401)
        self.assertEqual(self.request('/api/auth/login',data,origin='https://other.example')[0],403)
        token=cookie.split('=',1)[1].split(';')[0]
        self.assertTrue(self.request('/api/auth/status',token=token)[1]['authenticated'])

    def test_account_setup_login_cookie_and_logout(self):
        host=self.app.new_session('board',platform_admin=True)
        data={'username':'owner','password':'correct-horse-password','remember':True}
        status,result,cookie=self.request('/api/auth/setup',data,host)
        self.assertEqual(status,200); self.assertIn('HttpOnly',cookie);self.assertIn('Max-Age=2592000',cookie)
        self.assertNotIn('token',result)
        self.assertEqual(self.request('/api/session',token=host)[0],401)
        token=cookie.split('=',1)[1].split(';')[0]
        self.assertTrue(self.request('/api/auth/status',token=token)[1]['authenticated'])
        self.assertEqual(self.request('/api/auth/logout',{},token)[0],200)
        self.assertEqual(self.request('/api/session',token=token)[0],401)
        data['platform_admin']=True
        self.assertEqual(self.request('/api/auth/login',data)[0],401)
