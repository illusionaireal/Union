"""U-121 durable bounded work acceptance and original execution through Core HTTP."""
import hashlib
import json
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from ai_union.adapters.core_au_store import CoreAUStore
from ai_union.adapters.work_execution_store import wire_digest
from ai_union.application.model_access import ModelAccessService
from ai_union.console import Console
from ai_union.model_service import ServiceError
from ai_union.work_transport import ModeldWorkTransport

from tests import test_business_materials as material_support
from tests import test_core_work as work_support
from scripts import release_package as release
from tests.model_access_support import ModelAccessCase
from tests.test_core_creation import creation


class WorkIntentTests(ModelAccessCase):
    adopt_default = work_support.CoreWorkTests.adopt_default
    works = work_support.CoreWorkTests.works
    material = material_support.BusinessMaterialsTests.material
    imported = material_support.BusinessMaterialsTests.imported

    def work_command(self, au_id, kind, data, *, request_id=None, **kwargs):
        if kind == 'start_work_intent' and request_id is None:
            scope = hashlib.sha256(au_id.encode('utf-8')).hexdigest()[:24]
            request_id = f'intent-{scope}-{uuid.uuid4().hex}'
        return work_support.CoreWorkTests.work_command(self, au_id, kind, data, request_id=request_id, **kwargs)

    def prepare_intent(self, mode='automatic_text', **changes):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        material, _ = self.imported()
        return work_support.work_data(materials_root=material['id'], material_version=material['version'],
                                      constraints='只使用指定资料', delivery_mode=mode, **changes)

    def test_single_submission_accepts_original_attempt_and_recovers_original_receipt(self):
        data = self.prepare_intent()
        self.app.work.transport = work_support.FakeTransport([])
        with patch('ai_union.application.work_intent.wake'):
            status, response, request = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(status, 200, response)
        receipt = response['receipt']
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual((receipt['intent_id'], receipt['work_id'], receipt['delivery_mode']),
                         (request['id'], data['work_id'], data['delivery_mode']))
        card = self.works()['works'][0]
        self.assertEqual(card['intent']['attempt_id'], receipt['attempt_id'])
        self.assertEqual(card['attempts'][0]['id'], receipt['attempt_id'])
        status, replay, _ = self.request('/api/v1/work/commands', request)
        self.assertEqual((status, replay['receipt']), (200, receipt))
        self.assertEqual(len(self.works()['works'][0]['attempts']), 1)


    def channel(self):
        self.provider.request = self.result
        self.app.work.transport = ModeldWorkTransport(
            self.provider, self.au_id, self.read()['au']['model_access']['connections']['connection-a'])

    def result(self, request_id, au_id):
        body = self.provider.requests.get(request_id)
        if body is None:
            raise ServiceError('not_found', 404)
        if self.provider.before_result:
            callback, self.provider.before_result = self.provider.before_result, None
            callback()
        has_source = any(message['role'] == 'tool' for message in body['messages'])
        if has_source:
            message = {'content': '资料概要：项目由三个模块组成。', 'tool_calls': []}
        else:
            message = {'content': '', 'tool_calls': [{'id': 'read-import', 'type': 'function', 'function': {
                'name': 'read_document', 'arguments': json.dumps({'path': '研究资料.md'})}}]}
        return {'id': request_id, 'au_id': au_id, 'state': 'completed', 'request_digest': wire_digest(body),
                'action_authorized': not self.provider.revoked,
                'result': {'message': message, 'usage': {'input_tokens': 5, 'output_tokens': 3}}}

    def wait_intent(self, status):
        until = time.monotonic() + 5
        while time.monotonic() < until:
            card = self.works()['works'][0]
            if card['intent']['status'] == status:
                return card
            time.sleep(.025)
        self.fail((card['intent'], card['steps']))

    def test_worker_delivers_same_attempt_after_original_session_logout(self):
        data = self.prepare_intent()
        self.channel()
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def held():
            entered.set()
            self.assertTrue(release.wait(5))
        self.provider.before_result = held
        status, response, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(status, 200, response)
        receipt = response['receipt']
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertTrue(entered.wait(2), 'acceptance must wake the original attempt')
        original_token = self.token
        self.app.identity.logout(original_token)
        self.token = self.app.identity.login('owner', 'correct-horse-password')['token']
        release.set()
        card = self.wait_intent('delivered')
        self.assertEqual(card['status'], 'delivered')
        self.assertEqual(card['attempts'][0]['id'], receipt['attempt_id'])
        self.assertEqual(len([path for path, _ in self.provider.posts if path == '/v1/requests']), 2)
        self.assertEqual(card['budget']['used'], 2)
        self.assertIn(data['constraints'], self.model_posts()[0]['messages'][1]['content'])

    def test_review_requires_exact_original_candidate_before_delivery(self):
        data = self.prepare_intent('governor_review')
        self.channel()
        status, response, request = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual((status, response['receipt']['status']), (200, 'succeeded'), response)
        card = self.wait_intent('awaiting_decision')
        self.assertNotEqual(card['status'], 'delivered')
        decision = {key: value for key, value in card['intent']['decision'].items() if key != 'authorized_principal_id'}
        decision.update(work_id=card['id'], intent_id=request['id'], reason='采用已验证的原文本成果')
        status, response, _ = self.work_command(self.au_id, 'decide_work_intent', decision | {'sha256': '0' * 64})
        self.assertEqual((status, response['receipt']['status']), (200, 'rejected'), response)
        status, response, command = self.work_command(self.au_id, 'decide_work_intent', decision)
        self.assertEqual((status, response['receipt']['status']), (200, 'succeeded'), response)
        card = self.wait_intent('delivered')
        self.assertEqual(card['delivered_result_id'], decision['result_id'])
        status, replay, _ = self.request('/api/v1/work/commands', command)
        self.assertEqual((status, replay['receipt']), (200, response['receipt']))


    def test_revoked_remote_grant_refuses_before_accepting_original_work(self):
        data = self.prepare_intent()
        self.channel()
        self.provider.revoked = True
        status, response, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual((status, response['receipt']['status']), (200, 'rejected'), response)
        self.assertEqual(self.works()['works'], [])
        self.assertEqual(self.model_posts(), [])

    def model_posts(self):
        return [body for path, body in self.provider.posts if path == '/v1/requests']

    def test_two_independent_intents_survive_each_others_versioned_progress(self):
        data = self.prepare_intent()
        self.channel()
        other, _ = self.imported()
        second = data | {'materials_root': other['id'], 'material_version': other['version'],
            'work_id': 'work-other', 'member_id': 'member-other', 'binding_id': 'binding-other',
            'mandate_id': 'mandate-other', 'definition_id': 'definition-other'}
        held, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def held_once():
            held.set()
            release.wait(5)
        self.provider.before_result = held_once
        _, first, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(first['receipt']['status'], 'succeeded', first)
        self.assertTrue(held.wait(2))
        _, later, _ = self.work_command(self.au_id, 'start_work_intent', second)
        self.assertEqual(later['receipt']['status'], 'succeeded', later)
        release.set()
        until = time.monotonic() + 5
        while time.monotonic() < until:
            cards = self.works()['works']
            if all(card['intent']['status'] == 'delivered' for card in cards):
                break
            time.sleep(.025)
        self.assertEqual([card['intent']['status'] for card in cards], ['delivered', 'delivered'], cards)
        self.assertEqual(len(self.model_posts()), 4)


    def test_failed_acceptance_rolls_back_work_attempt_receipt_and_schema(self):
        data = self.prepare_intent()
        self.channel()
        before = self.dump()
        save = self.app.work.store.save
        def fail_after_write(cx, state, charter, command, *args, **kwargs):
            save(cx, state, charter, command, *args, **kwargs)
            if command['kind'] == 'start_work_intent':
                raise OSError('controlled acceptance commit failure')
        with patch.object(self.app.work.store, 'save', side_effect=fail_after_write):
            status, response, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual((status, response['code']), (503, 'storage_unavailable'))
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.model_posts(), [])

    def test_scope_and_manual_commands_cannot_change_managed_attempt(self):
        data = self.prepare_intent()
        self.channel()
        with patch('ai_union.application.work_intent.wake'):
            status, response, request = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual((status, response['receipt']['status']), (200, 'succeeded'), response)
        card = self.works()['works'][0]
        status, response, _ = self.request('/api/v1/work/commands', request | {
            'data': data | {'constraints': 'different'}})
        self.assertEqual((status, response['code']), (409, 'id_conflict'))
        outsider, _ = self.participant('outsider-intent')
        status, response, _ = self.request('/api/v1/work/commands', request, token=outsider)
        self.assertEqual((status, response['code']), (403, 'not_authorized'))
        other = self.create(creation('u121-cross-au'))['organization_id']
        status, response, _ = self.request('/api/v1/work/commands', request | {'organization_id': other})
        self.assertEqual((status, response['code']), (403, 'not_authorized'))
        status, response, _ = self.request('/api/v1/work/commands', request | {'id': str(uuid.uuid4())})
        self.assertEqual((status, response['code']), (400, 'invalid_request'))
        for kind, details in (
                ('reserve_step', {}), ('run_loop', {}), ('run_step', {}),
                ('recover_work', {'attempt_id': card['attempts'][0]['id'], 'reason': '手工越权尝试'}),
                ('finish_attempt', {'attempt_id': card['attempts'][0]['id'], 'outcome': 'stopped',
                                    'reason': '手工越权尝试'}),
                ('adopt_result', {'result_id': 'result-fake'})):
            status, response, _ = self.work_command(self.au_id, kind, {'work_id': card['id']} | details)
            self.assertNotEqual(response.get('receipt', {}).get('status'), 'succeeded', (kind, status, response))
        self.assertEqual(self.works()['works'][0], card)
        self.assertEqual(self.model_posts(), [])

    def test_stop_preserves_admitted_call_accounting_and_denies_new_actions(self):
        data = self.prepare_intent()
        self.channel()
        held, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def hold_first():
            held.set()
            release.wait(5)
        self.provider.before_result = hold_first
        _, accepted, request = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded')
        self.assertTrue(held.wait(2))
        status, response, _ = self.work_command(self.au_id, 'stop_work_intent', {
            'work_id': data['work_id'], 'intent_id': request['id'], 'reason': '已结束这次原意图'})
        self.assertEqual((status, response['receipt']['status']), (200, 'succeeded'), response)
        card = self.wait_intent('stopped')
        self.assertEqual(card['budget']['reserved'], 1)
        release.set()
        until = time.monotonic() + 5
        while time.monotonic() < until:
            card = self.works()['works'][0]
            if card['status'] == 'stopped':
                break
            time.sleep(.025)
        self.assertEqual(card['status'], 'stopped', card)
        self.assertEqual(card['budget']['used'], 1)
        self.assertEqual(card['steps'][0]['usage'], {'input_tokens': 5, 'output_tokens': 3})
        self.assertEqual(card['results'], [])
        self.assertEqual(len(self.model_posts()), 1)

    def test_404_unknown_restarts_with_same_attempt_epoch_and_no_repost(self):
        data = self.prepare_intent()
        self.channel()
        self.provider.lost_submit = True
        lookup_ids = []
        def missing(request_id, au_id):
            lookup_ids.append((request_id, au_id))
            raise ServiceError('not_found', 404)
        self.provider.request = missing
        _, accepted, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded')
        waiting = self.wait_intent('waiting_unknown')
        original = waiting['steps'][0]
        self.app.join_jobs()
        self.assertEqual(len(lookup_ids), 3, lookup_ids)
        self.stop()
        with patch.object(Console, '_work_channel_factory',
                          return_value=lambda au_id, config: ModeldWorkTransport(self.provider, au_id, config)):
            self.start()
        self.app.join_jobs()
        card = self.wait_intent('waiting_unknown')
        self.assertEqual(card['steps'][0], original)
        self.assertEqual(card['attempts'][0]['id'], accepted['receipt']['attempt_id'])
        self.assertEqual(card['attempts'][0]['execution_owner']['epoch'], 2)
        self.assertEqual(lookup_ids, [(original['model_request_id'], self.au_id)] * 6)
        self.assertEqual(len(self.model_posts()), 1)
        self.assertEqual(card['budget']['reserved'], 1)
        self.assertEqual(card['results'], [])
        self.provider.lost_submit = False
        self.provider.request = self.result
        _, appended, _ = self.work_command(self.au_id, 'append_work_input', {
            'work_id': data['work_id'], 'input_id': 'resume-input', 'content': '确认原始资料',
            'reason': '原模型服务再次可查询后补充输入'})
        self.assertEqual(appended['receipt']['status'], 'succeeded', appended)
        delivered = self.wait_intent('delivered')
        self.assertEqual([step['model_request_id'] for step in delivered['steps']][0], original['model_request_id'])
        self.assertEqual(delivered['attempts'][0]['execution_owner']['epoch'], 2)
        self.assertEqual([body['id'] for body in self.model_posts()].count(original['model_request_id']), 1)
        self.assertEqual(delivered['input_cursor'], 1)

    def test_posted_text_candidate_cannot_swallow_a_late_input(self):
        data = self.prepare_intent()
        self.channel()
        held, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def hold_second(request_id, au_id):
            if len(self.model_posts()) == 2 and not held.is_set():
                held.set()
                release.wait(5)
            return self.result(request_id, au_id)
        self.provider.request = hold_second
        _, accepted, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded')
        self.assertTrue(held.wait(2))
        _, response, _ = self.work_command(self.au_id, 'append_work_input', {
            'work_id': data['work_id'], 'input_id': 'late-input', 'content': '末尾加入新的校验文本',
            'reason': '原文本提交期间新增要求'})
        self.assertEqual(response['receipt']['status'], 'succeeded', response)
        release.set()
        card = self.wait_intent('delivered')
        self.assertEqual(len(self.model_posts()), 3)
        self.assertEqual([result['status'] for result in card['results']], ['candidate', 'adopted'])
        self.assertEqual([result['input_cursor'] for result in card['results']], [0, 1])
        self.assertEqual(card['results'][1]['id'], card['delivered_result_id'])

    def test_older_install_refuses_real_intent_under_miswritten_schema_marker(self):
        data = self.prepare_intent()
        self.channel()
        save = self.app.work.store.save
        def mark_old(cx, state, charter, command, *args, **kwargs):
            if command['kind'] == 'start_work_intent':
                state['schema_version'] = 6
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, 'save', side_effect=mark_old), patch(
                'ai_union.application.work_intent.wake'):
            _, accepted, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded')
        self.assertEqual(self.read()['au']['schema_version'], 6)
        manifest = {'core_schemas': {'auth': 2, 'catalog': 1}, 'core_au_schemas': list(range(1, 7))}
        before = self.dump()
        with self.assertRaisesRegex(release.ReleaseError, 'durable work intent'):
            release.check_core_schemas(manifest, {'console_state': self.root})
        release.check_core_schemas(manifest | {'core_au_schemas': list(range(1, 8))}, {'console_state': self.root})
        self.assertEqual(self.dump(), before)


    def test_account_principal_revocation_keeps_model_usage_without_tools_or_result(self):
        data = self.prepare_intent()
        self.channel()
        held, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def hold_result():
            held.set()
            release.wait(5)
        self.provider.before_result = hold_result
        _, accepted, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded', accepted)
        self.assertTrue(held.wait(2))
        with self.app.catalog() as accounts:
            accounts.execute("UPDATE owner_account SET principal_id=? WHERE principal_id=?",
                             ('085fe768-e3e2-4609-96e9-54479cbd0724', self.principal))
        release.set()
        self.app.join_jobs()
        directory, original = self.app.governance.locate(self.au_id)
        state = CoreAUStore().read(directory, self.au_id, creation=original)['au']
        card = state['work_runtime']['works'][data['work_id']]
        self.assertEqual(card['intent']['status'], 'blocked')
        self.assertEqual(card['steps'][0]['status'], 'used')
        self.assertEqual(card['steps'][0]['usage'], {'input_tokens': 5, 'output_tokens': 3})
        self.assertFalse(card.get('tool_calls'))
        self.assertFalse(card.get('results'))
        self.assertEqual(len(self.model_posts()), 1)

    def test_managed_intent_uses_approved_fourth_turn_within_same_budget(self):
        data = self.prepare_intent()
        self.channel()
        def extend_tools(request_id, au_id):
            result = self.result(request_id, au_id)
            if len(self.model_posts()) < 4:
                result['result']['message'] = {'content': '', 'tool_calls': [{
                    'id': 'read-' + request_id, 'type': 'function', 'function': {
                        'name': 'read_document', 'arguments': json.dumps({'path': '研究资料.md'})}}]}
            return result
        self.provider.request = extend_tools
        _, accepted, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded', accepted)
        delivered = self.wait_intent('delivered')
        self.assertEqual(len(self.model_posts()), 4)
        self.assertEqual(delivered['budget'], {'max_calls': 4, 'used': 4, 'reserved': 0})
        self.assertEqual({step['attempt_id'] for step in delivered['steps']}, {accepted['receipt']['attempt_id']})


    def test_corrupt_unrelated_au_storage_does_not_block_healthy_work_acceptance(self):
        data = self.prepare_intent()
        self.channel()
        other = self.create(creation('u121-corrupt-other-au'))['organization_id']
        other_directory, _ = self.app.governance.locate(other)
        other_database = other_directory / 'state.sqlite3'
        original = other_database.read_bytes()
        self.addCleanup(other_database.write_bytes, original)
        other_database.write_bytes(b'controlled corrupt sqlite data')
        with patch('ai_union.application.work_intent.wake'):
            status, response, request = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(status, 200, response)
        self.assertEqual(response['receipt']['status'], 'succeeded', response)
        self.assertEqual(self.works()['works'][0]['intent']['id'], request['id'])


    def test_startup_intent_scan_skips_an_au_that_fails_after_earlier_checks(self):
        data = self.prepare_intent()
        self.channel()
        other = self.create(creation('u121-startup-other-au'))['organization_id']
        directory, _ = self.app.governance.locate(other)
        database = directory / 'state.sqlite3'
        original = database.read_bytes()
        self.addCleanup(database.write_bytes, original)
        with patch('ai_union.application.work_intent.wake'):
            _, accepted, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual(accepted['receipt']['status'], 'succeeded')
        self.stop()
        prior_recovery = ModelAccessService.recover

        def corrupt_after_model_scan(models):
            prior_recovery(models)
            database.write_bytes(b'controlled corrupt sqlite data')

        with patch.object(ModelAccessService, 'recover', corrupt_after_model_scan), patch.object(
                Console, '_work_channel_factory',
                return_value=lambda au_id, config: ModeldWorkTransport(self.provider, au_id, config)), self.assertLogs(
                    'ai_union.application.work_intent', 'WARNING') as warnings:
            self.start()
        self.assertNotIn(str(database), '\n'.join(warnings.output))
        card = self.wait_intent('delivered')
        self.assertEqual(card['attempts'][0]['id'], accepted['receipt']['attempt_id'])

    def test_managed_intent_rejects_legacy_mutable_host_folder(self):
        data = self.prepare_intent()
        self.channel()
        work_support.CoreWorkTests.prepare_materials(self)
        data.pop('material_version')
        data['materials_root'] = 'project-docs'
        with patch('ai_union.application.work_intent.wake'):
            status, response, _ = self.work_command(self.au_id, 'start_work_intent', data)
        self.assertEqual((status, response['receipt']['status']), (200, 'rejected'), response)
        self.assertIn('业务资料版本', response['receipt']['message'])
        self.assertEqual(self.works()['works'], [])
        old_data = {key: val for key, val in data.items() if key not in ('constraints', 'delivery_mode')}
        status, response, _ = self.work_command(self.au_id, 'start_work', old_data)
        self.assertEqual((status, response['receipt']['status']), (200, 'succeeded'), response)
