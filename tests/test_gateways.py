"""Real local HTTP and durable registry checks; no supplier calls or credentials."""
import copy
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from ai_union.console import Console
from ai_union.engine import Rejected
from ai_union.gateways import probe
from ai_union.model_api import list_connections, resolve_connection
from tests.support import CHARTER, RESOURCES
from tests import test_http


class StatusHandler(BaseHTTPRequestHandler):
    payload = {"success": True, "data": {"version": "v1.0.0-rc.47", "private": "not-exported"}}
    code = 200
    requests = []
    slow = False
    def do_GET(self):
        type(self).requests.append((self.path, dict(self.headers)))
        self.send_response(type(self).code)
        self.send_header('Location', '/redirect-target')
        self.end_headers()
        if type(self).slow:
            try:
                for _ in range(30):
                    self.wfile.write(b' '); self.wfile.flush(); time.sleep(.25)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        body = json.dumps(type(self).payload).encode()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def log_message(self, *args):
        pass


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.app = Console(Path(self.temp.name) / 'console'); self.addCleanup(self.app.close)
        self.admin = self.app.new_session('board', platform_admin=True)
        self.board = self.app.new_session('board')
        self.observer = self.app.new_session('observer')
        self.seq = 0
        self.config = dict(name='Test New API', service_url='http://127.0.0.1:12345',
                           api_base_url='http://127.0.0.1:12345/v1', admin_url='http://127.0.0.1:12345', mode='external')

    def command(self, kind='save', revision=0, request_id=None, data=None, token=None):
        self.seq += 1
        return self.app.gateways.command(token or self.admin, dict(id=request_id or f'gateway-request-{self.seq}',
            gateway_id='gateway-test', base_revision=revision, kind=kind,
            data=data if data is not None else {'config': self.config} if kind == 'save' else {}))

    def create(self, token=None):
        self.seq += 1
        r = self.app.command(token or self.board, dict(id=f'create-{self.seq}', organization_id=None,
            base_version=None, kind='create', data=dict(name='Company', goal='test', board_name='test', charter=CHARTER, resources=RESOURCES)))
        return r['organization_id']

    def serve(self):
        StatusHandler.requests = []; StatusHandler.code = 200
        StatusHandler.slow = False
        StatusHandler.payload = {'success': True, 'data': {'version': 'v1.0.0-rc.47', 'private': 'not-exported'}}
        server = ThreadingHTTPServer(('127.0.0.1', 0), StatusHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(thread.join); self.addCleanup(server.shutdown)
        self.config['service_url'] = f'http://127.0.0.1:{server.server_port}/prefix'
        return server

    def test_platform_scope_tickets_and_public_organization_directory(self):
        self.command()
        for token in (self.board, self.observer, self.app.new_session('board', organizations=[])):
            with self.assertRaises(Rejected): self.app.gateways.list(token)
            with self.assertRaises(Rejected): self.command(token=token)
            with self.assertRaises(Rejected): self.app.gateways.receipt(token, 'gateway-request-1')
        with self.assertRaises(Rejected): self.app.new_session('observer', platform_admin=True)
        with self.assertRaises(Rejected): self.app.new_session('board', organizations=[], platform_admin=True)
        launched = self.app.exchange(self.app.ticket('board', platform_admin=True))
        self.assertTrue(self.app.session_info(launched)['platform_admin'])
        self.assertFalse(self.app.session_info(self.app.exchange(self.app.ticket('board')))['platform_admin'])
        oid = self.create()
        before = self.app.engine(self.board, oid).state()
        self.assertEqual(len(self.app.gateways.list(self.board, oid)['gateways']), 1)
        self.assertEqual(before, self.app.engine(self.board, oid).state())
        self.assertNotIn('receipts', self.app.gateways.list(self.board, oid))
        self.assertEqual(set(self.app.gateways.list(self.board, oid)['gateways'][0]), {'id','revision','config'})
        self.assertEqual(set(self.app.gateways.list(self.board, oid)['gateways'][0]['config']), {'name','api_base_url'})
        with self.assertRaises(Rejected): self.app.gateways.list(self.app.new_session('board', organizations=[]), oid)
        with self.assertRaises(Rejected): self.app.gateways.list(self.observer, oid)

    def test_versions_idempotency_archive_and_restart(self):
        first = self.command(request_id='stable')
        self.assertEqual(first, self.command(request_id='stable'))
        with self.assertRaises(Rejected): self.command(request_id='stable', revision=1)
        self.assertEqual(self.command(revision=0)['status'], 'rejected')
        self.assertEqual(self.command(revision=1)['status'], 'succeeded')
        self.assertEqual(self.command('archive', revision=2)['status'], 'succeeded')
        self.assertEqual(self.app.gateways.list(self.admin)['gateways'], [])
        self.assertEqual(self.command(revision=3)['status'], 'rejected')
        self.app.close()
        self.app = Console(Path(self.temp.name) / 'console'); self.addCleanup(self.app.close)
        admin = self.app.new_session('board', platform_admin=True)
        self.assertEqual(self.app.gateways.receipt(admin, 'stable'), first)
        self.assertEqual(self.app.gateways.list(admin)['gateways'], [])

    def test_target_validation_and_no_unsupported_operation(self):
        for url in ('file:///etc/passwd', 'https://user:pass@example.com', 'https://example.com/?secret=x',
                    'https://example.com/#token', 'http://example.com', 'https://example.com:99999', 'javascript:alert(1)'):
            with self.subTest(url=url), self.assertRaises(Rejected):
                self.command(data={'config': self.config | {'service_url': url}})
        with self.assertRaises(Rejected): self.command('restart')
        with self.assertRaises(Rejected): self.command(data={'config': self.config, 'api_key': 'never-save'})
        self.assertNotIn('never-save', self.app.db.read_bytes().decode(errors='ignore'))

    def test_actual_status_http_version_no_credentials_and_readonly_refresh(self):
        self.serve(); self.command()
        for _ in range(3): self.app.gateways.list(self.admin)
        self.assertEqual(StatusHandler.requests, [])
        self.command('probe', revision=1); self.app.join_jobs()
        record = self.app.gateways.list(self.admin)['gateways'][0]
        self.assertEqual(record['health'], 'healthy'); self.assertEqual(record['version'], 'v1.0.0-rc.47')
        self.assertEqual(record['deployment_state'], 'unknown'); self.assertTrue(record['checked_at'])
        self.assertNotIn('not-exported', json.dumps(record))
        path, headers = StatusHandler.requests[0]
        self.assertEqual(path, '/prefix/api/status')
        self.assertNotIn('Authorization', headers); self.assertNotIn('Cookie', headers)
        StatusHandler.payload = {'success': True, 'data': {}}
        self.command('probe', revision=1); self.app.join_jobs()
        self.assertIsNone(self.app.gateways.list(self.admin)['gateways'][0]['version'])
        StatusHandler.code = 302
        self.command('probe', revision=1); self.app.join_jobs()
        self.assertEqual(len(StatusHandler.requests), 3)
        record = self.app.gateways.list(self.admin)['gateways'][0]
        self.assertEqual(record['health'], 'unavailable'); self.assertEqual(record['deployment_state'], 'unknown')

    def test_response_limits_invalid_payload_and_offline(self):
        self.serve()
        for payload in ([], {'success': False, 'data': {}}, {'success': True, 'data': 'bad'}, {'big': 'x' * 70000}):
            StatusHandler.payload = payload
            self.assertEqual(probe(self.config)['health'], 'unavailable')
        self.config['service_url'] = 'http://127.0.0.1:1'
        self.assertEqual(probe(self.config)['health'], 'unavailable')

    def test_stale_probe_cannot_overwrite_changed_endpoint_and_one_inflight(self):
        self.command()
        entered, release = threading.Event(), threading.Event()
        def hold(config):
            entered.set(); release.wait(3)
            return dict(health='healthy', version='old', message='old')
        with patch('ai_union.gateways.probe', hold):
            accepted = self.command('probe', revision=1, request_id='probe-original')
            self.assertTrue(entered.wait(1))
            self.assertEqual(self.command('probe', revision=1, request_id='probe-original'), accepted)
            self.assertEqual(self.command('probe', revision=1)['status'], 'rejected')
            self.config['service_url'] = 'https://replacement.example'
            self.command(revision=1)
            release.set(); self.app.join_jobs()
        record = self.app.gateways.list(self.admin)['gateways'][0]
        self.assertEqual(record['health'], 'unknown'); self.assertIsNone(record['version'])
        self.assertIn('未应用', self.app.gateways.receipt(self.admin, accepted['id'])['message'])

    def test_slow_drip_is_terminated_by_total_deadline(self):
        self.serve(); StatusHandler.slow = True
        start = time.monotonic()
        self.assertEqual(probe(self.config)['health'], 'unavailable')
        self.assertLess(time.monotonic() - start, 6)

    def test_restart_marks_accepted_unknown_and_does_not_replay(self):
        self.command()
        with self.app.catalog() as cx:
            cx.execute('INSERT INTO gateway_commands VALUES(?,?,?)', ('interrupted', 'digest', json.dumps(dict(id='interrupted',gateway_id='gateway-test',kind='probe',status='accepted'))))
        self.app.close(); self.app = Console(Path(self.temp.name) / 'console'); self.addCleanup(self.app.close)
        admin = self.app.new_session('board', platform_admin=True)
        self.assertEqual(self.app.gateways.receipt(admin, 'interrupted')['status'], 'unknown')
        self.assertEqual(self.app.jobs, [])

    def test_au_connection_snapshot_key_isolation_and_explicit_migration(self):
        self.command(); oid = self.create(); other = self.create(); e = self.app.engine(self.board, oid)
        config = dict(name='AU New API',base_url=self.config['api_base_url'],model='test-model',response_format='agent',
                      token_limit_field='max_tokens',max_output_tokens=100,timeout_seconds=5,enabled=True)
        def connect(config, ref, key=None):
            self.seq += 1
            return self.app.command(self.board, dict(id=f'connect-{self.seq}', organization_id=oid, base_version=e.state()['version'],kind='api_connection',
                data=dict(connection_id='primary',config=config,reason='test',gateway_ref=ref,**({'api_key': key} if key else {}))))
        ref = dict(id='gateway-test', revision=1)
        self.assertEqual(connect(config, ref, 'private-au-sentinel')['status'], 'succeeded')
        self.assertEqual(list_connections(e)[0]['gateway_ref'], ref)
        self.assertNotIn('private-au-sentinel', json.dumps(self.app.model_connections(self.board, oid)))
        self.assertEqual(self.app.model_connections(self.board, other)['connections'], [])
        self.config['api_base_url'] = 'https://new.example/v1'; self.command(revision=1)
        self.assertEqual(resolve_connection(e, 'primary')['config']['base_url'], config['base_url'])
        self.assertEqual(connect(config, ref)['status'], 'rejected')
        changed = config | {'base_url': self.config['api_base_url']}
        self.assertEqual(connect(changed, dict(id='gateway-test',revision=2))['status'], 'rejected')
        self.assertEqual(connect(changed, dict(id='gateway-test',revision=2), 'replacement-key')['status'], 'succeeded')
        self.command('archive', revision=2)
        self.assertEqual(resolve_connection(e, 'primary')['api_key'], 'replacement-key')


class GatewayHTTPTests(unittest.TestCase):
    setUp = test_http.HTTPTests.setUp
    request = test_http.HTTPTests.request
    create = test_http.HTTPTests.create
    # Reuse transport harness without duplicating inherited test cases.
    def test_gateway_transport_platform_scope_and_spa(self):
        self.assertEqual(self.request('GET','/api/gateways')[0],403)
        self.board = self.app.new_session('board',platform_admin=True)
        self.cookie = self.server.cookie_name + '=' + self.board
        self.assertEqual(self.request('GET','/api/gateways')[0],200)
        request = dict(id='http-gateway',gateway_id='gateway-test',base_revision=0,kind='save',data={'config':dict(name='HTTP test',service_url='http://127.0.0.1:1',api_base_url='http://127.0.0.1:1/v1',admin_url='http://127.0.0.1:1',mode='external')})
        self.assertEqual(self.request('POST','/api/gateway-commands',request,headers={'Origin':'http://evil.example'})[0],403)
        self.assertEqual(self.request('POST','/api/gateway-commands',request)[1]['receipt']['status'],'succeeded')
        self.assertEqual(self.request('GET','/api/gateway-receipts?id=http-gateway')[1]['receipt']['id'],'http-gateway')
        oid = self.create()
        self.cookie = self.server.cookie_name + '=' + self.app.new_session('board',organizations=[oid])
        self.assertEqual(self.request('GET','/api/gateways')[0],403)
        self.assertEqual(self.request('GET','/api/gateways?organization_id='+oid)[0],200)
        self.assertEqual(self.request('POST','/api/gateway-commands',request)[0],403)
