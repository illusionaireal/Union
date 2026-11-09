"""U108: Core HTTP/SQLite to an actual loopback modeld journal double; no inference."""
import copy
import json
import threading
import time
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit
from unittest.mock import patch

from ai_union.model_service import ModelServiceClient as RealClient
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work_http import WorkHttpChainTests
from tests.test_work_transport_http import ModeldDouble


class WorkEventsTests(WorkHttpChainTests):
    def setUp(self):
        super().setUp()
        self.remote_state = 'completed'
        self.remote_authorized = True
        self.fault = None
        self.raw_events = None
        self.grant_hook = None
        self.gets = []

        def get(handler):
            parts = urlsplit(handler.path)
            self.gets.append(handler.path)
            if parts.path.startswith('/v1/grants/'):
                value = self.provider.call('GET', handler.path)
                if self.grant_hook:
                    hook, self.grant_hook = self.grant_hook, None
                    hook()
                return handler._send(200, value)
            request_id = parts.path.split('/')[3]
            au_id = parse_qs(parts.query)['au_id'][0]
            if parts.path.endswith('/events'):
                after = int(parse_qs(parts.query)['after'][0])
                values = self.raw_events if self.raw_events is not None else [
                    self.event(request_id, 1, 'text_delta', {'text': '原工作部分正文'}),
                    self.event(request_id, 2, 'native_event', {'text': 'private-native-canary'}),
                    self.event(request_id, 3, 'tool_call_complete', {'name': 'read_document', 'arguments': 'private-args-canary'}),
                ]
                malformed = any(type(e['seq']) is not int or not 0 < e['seq'] <= 9007199254740991 for e in values)
                return handler._send(200, {'events': values if malformed else [e for e in values if e['seq'] > after][:500], 'state': self.remote_state})
            return handler._send(200, {
                'id': 'wrong-id' if self.fault == 'id' else request_id,
                'au_id': 'other-au' if self.fault == 'au' else au_id,
                'state': self.remote_state, 'action_authorized': self.remote_authorized,
                'result': {'message': {'role': 'assistant', 'content': '结果'},
                           'usage': {'input_tokens': 5, 'output_tokens': 2}},
            })

        self.patch_get = patch.object(ModeldDouble, 'do_GET', get)
        self.patch_get.start()
        self.addCleanup(self.patch_get.stop)
        self.app.models.backend = lambda: RealClient(str(self.config))
        self.app.work.transport_factory = lambda au, connection: ModeldWorkTransport(
            RealClient(str(self.config)), au, connection, poll_seconds=.02, timeout_seconds=10)

    @staticmethod
    def event(request_id, seq, kind, payload):
        return {'request_id': request_id, 'seq': seq, 'type': kind, 'payload': payload}

    def seeded(self):
        self.prepare_work()
        status, value, _ = self.run_step()
        self.assertEqual((status, value['receipt']['status']), (200, 'succeeded'), value)
        self.step = self.request('/api/v1/work?organization_id=' + self.au_id)[1]['works'][0]['steps'][0]

    def observe(self, after=0, **changes):
        params = {'organization_id': self.au_id, 'work_id': 'work-http',
                  'step_ref': self.step['step_ref'], 'after': str(after)}
        token = changes.pop('token', 'current')
        params.update(changes)
        return self.request('/api/v1/work/events?' + urlencode(params), token=token)

    def model_posts(self):
        return [x for x in ModeldDouble.seen if x[:2] == ('POST', '/v1/requests')]

    def test_original_projection_is_private_read_only_and_survives_restart(self):
        self.seeded()
        before, posts = self.dump(), len(self.model_posts())
        status, value, _ = self.observe()
        self.assertEqual(status, 200, value)
        self.assertEqual(value['protocol'], 'core.work-events.v1')
        for key in ('step_ref', 'attempt_id', 'model_request_id', 'command_id'):
            self.assertEqual(value[key], self.step[key])
        self.assertEqual(value['events'], [{'seq': 1, 'type': 'text_delta', 'text': '原工作部分正文'},
                                         {'seq': 3, 'type': 'tool_call_complete', 'name': 'read_document'}])
        self.assertNotIn('private-', json.dumps(value))
        self.assertEqual(value['cursor'], 3)
        self.assertEqual(self.observe(3)[1]['events'], [])
        self.stop(); self.start()
        self.app.models.backend = lambda: RealClient(str(self.config))
        self.assertEqual(self.observe()[1]['events'], value['events'])
        self.assertEqual((self.dump(), len(self.model_posts())), (before, posts))

    def test_read_authority_grant_and_original_scope_fail_closed(self):
        self.seeded()
        outsider, _ = self.participant('work-events-outsider')
        self.assertEqual(self.observe(token=outsider)[0], 403)
        self.assertEqual(self.observe(work_id='other-work')[0], 403)
        self.assertEqual(self.observe(step_ref='other-step')[0], 403)
        for cursor in (-1, 'bad', '1.2', '9007199254740992'):
            self.assertEqual(self.observe(cursor)[0], 400)
        self.provider.revoked = True
        self.assertEqual(self.observe()[0], 403)
        self.provider.revoked = False
        self.provider.grant_revision += 1
        self.assertEqual(self.observe()[0], 403)
        self.provider.grant_revision -= 1
        self.remote_authorized = False
        self.assertEqual(self.observe()[0], 403)

    def test_local_role_is_rechecked_after_remote_grant_get(self):
        self.seeded()
        token, principal = self.participant('work-events-successor')
        self.success('nominate_governor', {'principal_id': principal, 'reason': 'handover'})
        self.grant_hook = lambda: self.success('accept_governance', {'reason': 'accept'}, token=token)
        self.assertEqual(self.observe()[0], 403)

    def test_remote_identity_and_event_conflicts_are_not_partial_success(self):
        self.seeded()
        for fault in ('id', 'au'):
            self.fault = fault
            self.assertEqual(self.observe()[0], 409)
        self.fault = None
        event = self.event(self.step['model_request_id'], 1, 'text_delta', {'text': 'one'})
        self.raw_events = [event, copy.deepcopy(event)]
        self.assertEqual(len(self.observe()[1]['events']), 1)
        self.raw_events.append(event | {'payload': {'text': 'conflicting'}})
        self.assertEqual(self.observe()[0], 409)
        self.raw_events = [event | {'request_id': 'other-model-request'}]
        self.assertEqual(self.observe()[0], 409)

    def test_pages_advance_over_private_events_and_do_not_reexecute(self):
        self.seeded()
        request_id = self.step['model_request_id']
        self.raw_events = [self.event(request_id, i, 'native_event', {'secret': 'canary'}) for i in range(1, 501)]
        self.raw_events.append(self.event(request_id, 501, 'text_delta', {'text': 'tail'}))
        posts = len(self.model_posts())
        status, first, _ = self.observe()
        self.assertEqual(status, 200, first)
        self.assertEqual((first['cursor'], first['has_more'], first['events']), (500, True, []))
        tail = self.observe(500)[1]
        self.assertEqual((tail['cursor'], tail['has_more'], tail['events'][0]['text']), (501, False, 'tail'))
        self.assertEqual(len(self.model_posts()), posts)

    def test_output_while_original_command_is_pending_keeps_reservation(self):
        self.prepare_work()
        self.remote_state = 'streaming'
        outcome = []
        worker = threading.Thread(target=lambda: outcome.append(self.run_step()))
        worker.start()
        try:
            for _ in range(150):
                card = self.request('/api/v1/work?organization_id=' + self.au_id)[1]['works'][0]
                if card['steps']:
                    break
                time.sleep(.02)
            self.step = card['steps'][0]
            before = self.dump()
            status, value, _ = self.observe()
            self.assertEqual(status, 200, value)
            self.assertEqual(value['events'][0]['text'], '原工作部分正文')
            self.assertEqual(self.dump(), before)
            self.assertEqual(card['budget']['reserved'], 1)
            self.assertEqual(len(self.model_posts()), 1)
        finally:
            self.remote_state = 'interrupted'
            worker.join(15)
        self.assertFalse(worker.is_alive())
        current = self.request('/api/v1/work?organization_id=' + self.au_id)[1]['works'][0]
        self.assertEqual(current['steps'][0]['status'], 'unknown')
        self.assertEqual(current['budget']['reserved'], 1)
        self.remote_authorized = False
        self.assertEqual(self.observe()[0], 403)

    def test_connection_disable_during_read_hides_text_and_does_not_settle(self):
        self.seeded()
        self.grant_hook = lambda: self.model_success('set_connection', {
            'connection_id': 'connection-a', 'expected_revision': 1, 'enabled': False, 'make_default': False})
        self.assertEqual(self.observe()[0], 403)
        card = self.request('/api/v1/work?organization_id=' + self.au_id)[1]['works'][0]
        self.assertFalse(card['steps'][0]['can_observe'])
        self.assertEqual(card['budget']['used'], 1)

    def test_text_bound_is_explicit_and_malformed_sequences_fail_closed(self):
        self.seeded()
        request_id = self.step['model_request_id']
        self.raw_events = [self.event(request_id, 1, 'text_delta', {'text': 'x' * 70000})]
        status, value, _ = self.observe()
        self.assertEqual(status, 200, value)
        self.assertTrue(value['truncated'])
        self.assertEqual(len(value['events'][0]['text']), 65536)
        for seq in (True, -1, '2', 9007199254740992):
            self.raw_events = [self.event(request_id, seq, 'text_delta', {'text': 'private'})]
            self.assertEqual(self.observe()[0], 409)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkEventsTests(name) for name in WorkEventsTests.__dict__ if name.startswith('test_'))
