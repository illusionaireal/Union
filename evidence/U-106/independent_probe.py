"""Independent HTTP/SQLite review; explicit transport double, zero real calls."""
import copy
import hashlib
import sqlite3
from unittest.mock import patch

from tests.model_access_support import ModelAccessCase
from tests import test_core_work as support


class ResultBoundaryReview(ModelAccessCase):
    for _name in ('adopt_default', 'work_command', 'work', 'works', 'allow_listing',
                  'work_with_listing', 'prepare_materials', 'start_attempt', 'with_transport',
                  'run_loop', 'second_work'):
        locals()[_name] = getattr(support.CoreWorkTests, _name)

    def setUp(self):
        super().setUp()
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        self.channel = self.with_transport(
            {'content': None, 'tool_calls': [{'id': 'review-read', 'type': 'function',
                'function': {'name': 'read_document', 'arguments': '{"path":"nested/a.md"}'}}]},
            {'content': '# Independent bounded result\nSource: nested/a.md\n', 'tool_calls': []},
        )
        status, value, _ = self.run_loop()
        self.assertEqual((status, value['receipt']['status']), (200, 'succeeded'))
        self.item = self.works()['works'][0]
        self.result = self.item['results'][0]
        self.target = {'work_id': self.item['id'], 'result_id': self.result['id']}
        self.assertEqual(len(self.channel.calls), 2)
        self.assertEqual(self.provider.requests, {})

    def action(self, kind, **kwargs):
        return self.work_command(self.au_id, kind, self.target, **kwargs)

    def success_action(self, kind):
        status, value, request = self.action(kind)
        self.assertEqual((status, value['receipt']['status']), (200, 'succeeded'), value)
        return value['receipt'], request

    def lookup(self, request, token='current'):
        return self.request('/api/v1/governance/receipts?organization_id=' + self.au_id
                            + '&id=' + request['id'], token=token)

    def download(self, token='current'):
        return self.request('/api/v1/work/results?organization_id=' + self.au_id
                            + '&id=' + self.result['id'], token=token)

    def test_adopt_deliver_restart_preserves_original_identity_digest_and_sources(self):
        adopted, adopt_request = self.success_action('adopt_result')
        self.assertEqual(adopted['result']['sha256'], self.result['sha256'])
        self.stop(); self.start()
        self.assertEqual(self.lookup(adopt_request)[1]['receipt'], adopted)
        delivered, deliver_request = self.success_action('deliver_work')
        self.stop(); self.start()
        self.assertEqual(self.lookup(deliver_request)[1]['receipt'], delivered)
        self.assertEqual(delivered['work']['result_id'], self.result['id'])
        self.assertEqual(delivered['work']['work_id'], self.item['id'])
        status, body, _ = self.download()
        self.assertEqual(status, 200)
        self.assertEqual(hashlib.sha256(body['content'].encode()).hexdigest(), self.result['sha256'])
        self.assertEqual(body['result']['sources'], self.result['sources'])
        self.assertEqual(body['result']['adopted_by_principal_id'], self.principal)
        self.assertEqual(self.works()['works'][0]['status'], 'delivered')
        self.assertEqual(len(self.channel.calls), 2)

    def test_disabled_model_does_not_remove_existing_result_governance(self):
        connection = self.models()['connections'][0]
        self.model_success('set_connection', {'connection_id': connection['id'],
            'expected_revision': connection['revision'], 'enabled': False, 'make_default': False})
        self.assertFalse(self.works()['access']['can_start'])
        self.success_action('adopt_result')
        self.success_action('deliver_work')
        self.assertEqual(len(self.channel.calls), 2)
        self.assertEqual(self.provider.requests, {})

    def test_governance_projection_does_not_depend_on_default_model(self):
        connection = self.models()['connections'][0]
        self.model_success('set_connection', {'connection_id': connection['id'],
            'expected_revision': connection['revision'], 'enabled': False, 'make_default': False})
        access = self.works()['access']
        self.assertFalse(access['can_start'])
        self.assertIs(access.get('can_manage_results'), True)

    def test_download_rejects_a_mismatched_work_scope(self):
        self.second_work()
        status, body, _ = self.request('/api/v1/work/results?organization_id=' + self.au_id
            + '&id=' + self.result['id'] + '&work_id=work-second')
        self.assertIn(status, (400, 403), body)
        self.assertNotIn('content', body)

    def test_scoped_download_returns_the_original_work_identity(self):
        status, body, _ = self.request('/api/v1/work/results?organization_id=' + self.au_id
            + '&id=' + self.result['id'] + '&work_id=' + self.item['id'])
        self.assertEqual(status, 200)
        self.assertEqual(body.get('work_id'), self.item['id'])
        self.assertEqual(body['result']['id'], self.result['id'])

    def test_foreign_principal_cannot_read_or_mutate_original_result(self):
        token, _ = self.participant('independent-outsider')
        before = self.read()['au']
        for kind in ('adopt_result', 'deliver_work'):
            status, _, _ = self.action(kind, token=token, version=before['version'])
            self.assertEqual(status, 403)
        self.assertEqual(self.download(token)[0], 403)
        self.assertEqual(self.read()['au'], before)
        _, request = self.success_action('adopt_result')
        self.assertEqual(self.lookup(request, token)[0], 403)

    def test_stale_and_cross_work_commands_preserve_result_and_original_request(self):
        _, _, _ = self.second_work()
        before = self.read()['au']
        status, stale, _ = self.action('adopt_result', version=before['version']-1)
        self.assertEqual((status, stale['receipt']['status']), (200, 'rejected'))
        status, wrong, _ = self.work_command(self.au_id, 'adopt_result',
            dict(self.target, work_id='work-second'))
        self.assertEqual((status, wrong['receipt']['status']), (200, 'rejected'))
        self.assertEqual(self.read()['au'], before)
        adopted, request = self.success_action('adopt_result')
        wrong_request = copy.deepcopy(request)
        wrong_request['data']['work_id'] = 'work-second'
        self.assertEqual(self.request('/api/v1/work/commands', wrong_request)[0], 409)
        self.assertEqual(self.lookup(request)[1]['receipt'], adopted)

    def test_storage_failure_rolls_back_adoption_and_receipt_together(self):
        before = self.read()['au']
        with patch.object(self.app.work.store, 'save', side_effect=sqlite3.OperationalError('review commit failure')):
            status, _, request = self.action('adopt_result')
        self.assertGreaterEqual(status, 400)
        self.assertEqual(self.read()['au'], before)
        self.assertEqual(self.lookup(request)[0], 403)

    def test_candidate_does_not_close_an_attempt_with_an_unresolved_reservation(self):
        self.second_work(materials_root='independent-docs', work_id='work-unresolved')
        self.start_attempt('work-unresolved')
        status, reserved, _ = self.work_command(self.au_id, 'reserve_step', {'work_id': 'work-unresolved'})
        self.assertEqual((status, reserved['receipt']['status']), (200, 'succeeded'))
        self.with_transport({'content': 'Separate candidate with one unresolved reservation', 'tool_calls': []})
        status, response, _ = self.run_loop('work-unresolved')
        self.assertEqual((status, response['receipt']['status']), (200, 'succeeded'))
        pending = next(w for w in self.works()['works'] if w['id'] == 'work-unresolved')
        self.assertEqual(pending['budget']['reserved'], 1)
        self.assertEqual(pending['attempts'][0]['status'], 'running')
        target = {'work_id': pending['id'], 'result_id': pending['results'][0]['id']}
        self.assertEqual(self.work_command(self.au_id, 'adopt_result', target)[1]['receipt']['status'], 'succeeded')
        self.assertEqual(self.work_command(self.au_id, 'deliver_work', target)[1]['receipt']['status'], 'rejected')

    def test_manual_candidate_cannot_borrow_a_finished_loops_evidence_to_close_its_attempt(self):
        item = self.works()['works'][0]
        data = {'work_id': item['id'], 'result_id': 'review-manual-result', 'title': 'Manual review material',
                'content': 'A manual candidate referencing the completed loop', 'sources': self.result['sources']}
        status, value, _ = self.work_command(self.au_id, 'submit_result', data)
        self.assertEqual((status, value['receipt']['status']), (200, 'succeeded'))
        target = {'work_id': item['id'], 'result_id': 'review-manual-result'}
        status, value, _ = self.work_command(self.au_id, 'adopt_result', target)
        self.assertEqual((status, value['receipt']['status']), (200, 'succeeded'))
        self.assertEqual(self.works()['works'][0]['attempts'][0]['status'], 'running')
        self.assertEqual(self.work_command(self.au_id, 'deliver_work', target)[1]['receipt']['status'], 'rejected')

    def test_losing_governance_revokes_content_but_preserves_original_receipt(self):
        adopted, original = self.success_action('adopt_result')
        successor = self.participant('independent-successor')
        self.success('nominate_governor', {'principal_id': successor[1], 'reason': 'Review handover'})
        self.success('accept_governance', {'reason': 'Accept review responsibility'}, token=successor[0])
        self.assertEqual(self.download()[0], 403)
        version = self.read(successor[0])['au']['version']
        self.assertEqual(self.action('deliver_work', version=version)[0], 403)
        self.assertEqual(self.lookup(original)[1]['receipt'], adopted)
        self.assertEqual(self.lookup(original, successor[0])[0], 403)
