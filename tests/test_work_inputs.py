"""U093 durable requirements on original Work; HTTP/SQLite, controlled models only."""
import copy
import hashlib
import json
import uuid
import unittest
from unittest.mock import patch

from tests.test_work_dispatch import WorkDispatchTests, CallbackTransport
from tests.test_core_work import FakeTransport
from tests.test_work_recovery import WorkRecoveryTests, RecoveryClient


class WorkInputTests(WorkDispatchTests):
    def append(self, content='追加要求：保留原责任与引用', input_id=None, **kwargs):
        return self.work_command(self.au_id, 'append_work_input', {
            'work_id': 'work-overview', 'input_id': input_id or 'input-' + uuid.uuid4().hex,
            'content': content, 'reason': '用户补充原工作要求'}, **kwargs)

    def test_held_original_request_accepts_input_without_changing_its_wire(self):
        request = self.arrange()
        seen = []
        def held(package):
            before = copy.deepcopy(self.card()['steps'][0])
            status, value, command = self.append()
            seen.append((status, value, before, copy.deepcopy(self.card()['steps'][0])))
        self.app.work.transport = CallbackTransport(held)
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], 200, seen[0][1])
        self.assertEqual(seen[0][1]['receipt']['status'], 'succeeded', seen[0][1])
        self.assertEqual(seen[0][2], seen[0][3])
        item = self.works()['works'][0]['inputs'][0]
        self.assertEqual(item['status'], 'received')
        self.assertEqual(self.card()['input_cursor'], 0)
        self.assertNotIn('追加要求', json.dumps(seen[0][1], ensure_ascii=False))

    def test_next_turn_attaches_in_order_and_consumes_with_private_context_once(self):
        self.arrange()
        _, first, _ = self.append('第一项要求')
        _, second, _ = self.append('第二项要求')
        channel = FakeTransport([{'content': '完整答复', 'tool_calls': []}, {'content': '后续答复', 'tool_calls': []}])
        self.app.work.transport = channel
        first_turn = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(first_turn['status'], 'succeeded', first_turn)
        messages = channel.calls[0]['messages']
        self.assertEqual([message['content'] for message in messages[-2:]], ['第一项要求', '第二项要求'])
        card = self.card()
        self.assertEqual(card.get('input_cursor'), 2)
        self.assertEqual([value['status'] for value in card['inputs']], ['consumed', 'consumed'])
        self.assertEqual(card['results'][0]['input_cursor'], 2)
        self.assertEqual(card['steps'][0]['input_refs'], [first['receipt']['input']['id'], second['receipt']['input']['id']])
        self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(sum(m.get('content') == '第一项要求' for m in channel.calls[1]['messages']), 1)
        self.assertEqual(sum(m.get('content') == '第二项要求' for m in channel.calls[1]['messages']), 1)
        self.assertEqual(len(self.card()['inputs'][0]['attachments']), 1)
        self.assertEqual(self.state()['schema_version'], 6)

    def test_input_body_read_is_scoped_and_command_audit_contains_only_digest(self):
        self.arrange()
        _, value, request = self.append('私有正文', input_id='input-stable')
        receipt = value['receipt']
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        query = '/api/v1/work/inputs?organization_id=' + self.au_id + '&work_id=work-overview&id=input-stable'
        status, body, _ = self.request(query)
        self.assertEqual(status, 200, body)
        self.assertEqual(body['content'], '私有正文')
        self.assertEqual(body['input']['sha256'], hashlib.sha256('私有正文'.encode()).hexdigest())
        with self.app.work.store.transaction(self.directory) as cx:
            payload = cx.execute('SELECT payload FROM governance_commands WHERE id=?', (request['id'],)).fetchone()[0]
            audit = cx.execute('SELECT snapshot FROM governance_events ORDER BY version DESC LIMIT 1').fetchone()[0]
        self.assertNotIn('私有正文', payload + audit)
        self.assertEqual(json.loads(payload)['data']['content_sha256'], body['input']['sha256'])
        status, _, _ = self.request(query.replace('work-overview', 'work-other'))
        self.assertEqual(status, 400)

    def test_tool_only_turn_cannot_change_earlier_result_input_provenance(self):
        request = self.arrange()
        request['id'] = 'abc123def456-original'
        self.app.work.transport = CallbackTransport()
        self.assertTrue(self.app.work.run_step(self.token, request)['result'])
        original = copy.deepcopy(self.card()['results'][0])
        self.append()
        later = self.request_value() | {'id': 'abc123def456-later'}
        self.app.work.transport = CallbackTransport(message={'content': None, 'tool_calls': [{
            'id': 'listing', 'type': 'function', 'function': {'name': 'list_documents', 'arguments': '{}'}}]})
        receipt = self.app.work.run_step(self.token, later)
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertFalse(receipt['result'])
        self.assertEqual(self.card()['input_cursor'], 1)
        self.assertEqual(self.card()['results'], [original])

    def test_loop_never_imports_receipt_from_standalone_child_id_collision(self):
        request = self.arrange() | {'id': 'unrelated-loop-t1'}
        self.app.work.transport = channel = CallbackTransport()
        self.assertTrue(self.app.work.run_step(self.token, request)['result'])
        loop = self.request_value() | {'id': 'unrelated-loop', 'kind': 'run_loop'}
        receipt = self.app.work.run_loop(self.token, loop)
        self.assertEqual(receipt['status'], 'rejected', receipt)
        self.assertFalse(receipt['result'])
        self.assertEqual(receipt['turns'], 0)
        self.assertEqual(len(channel.calls), 1)

    def test_same_input_id_is_immutable_and_original_command_replay_survives_restart(self):
        self.arrange()
        _, value, request = self.append('保留正文', input_id='input-stable')
        original = value['receipt']
        self.assertEqual(original['status'], 'succeeded', original)
        _, duplicate, _ = self.append('保留正文', input_id='input-stable')
        self.assertEqual(duplicate['receipt']['input'], original['input'])
        self.assertEqual(self.card()['input_seq'], 1)
        status, conflict, _ = self.append('不同正文', input_id='input-stable')
        self.assertEqual(status, 409, conflict)
        self.stop(); self.start()
        status, repeated, _ = self.request('/api/v1/work/commands', request)
        self.assertEqual(status, 200, repeated)
        self.assertEqual(repeated['receipt'], original)

    def test_append_accepts_no_model_budget_and_stale_host_but_public_version_is_strict(self):
        self.arrange()
        self.app.work.transport = CallbackTransport()
        for _ in range(4):
            self.app.work.run_step(self.token, self.request_value())
        self.stop(); self.start()
        _, value, request = self.append()
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.assertEqual(self.works()['access']['can_append_input'], True)
        _, stale, _ = self.append(version=request['base_version'])
        self.assertEqual(stale['receipt']['status'], 'rejected', stale)

    def test_snapshot_and_attachment_rollback_if_reservation_save_fails(self):
        self.arrange()
        self.append()
        self.app.work.transport = CallbackTransport()
        original = self.app.work.store.save
        def fail(cx, state, charter, command, *args, **kwargs):
            if command['kind'] == 'work_dispatch_prepared':
                raise RuntimeError('controlled reservation commit failure')
            return original(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, 'save', side_effect=fail):
            with self.assertRaises(RuntimeError):
                self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(self.card().get('steps', []), [])
        self.assertEqual(self.card()['inputs'][0]['attachments'], [])
        self.assertEqual(self.card()['inputs'][0]['status'], 'received')

    def test_observation_survives_failed_adoption_without_consumption_or_context(self):
        self.arrange()
        self.append()
        self.app.work.transport = CallbackTransport()
        save = self.app.work.store.save
        def fail(cx, state, charter, command, *args, **kwargs):
            if command['kind'] == 'work_dispatch_adopted':
                raise KeyboardInterrupt('controlled adoption commit loss')
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, 'save', side_effect=fail):
            with self.assertRaises(KeyboardInterrupt):
                self.app.work.run_step(self.token, self.request_value())
        card = self.card()
        self.assertEqual(card['inputs'][0]['status'], 'observed')
        self.assertEqual(card['input_cursor'], 0)
        self.assertNotIn('context_sha256', card['steps'][0])
        self.assertEqual(card.get('results', []), [])

    def test_over_limit_adopted_context_keeps_observation_without_consuming_input(self):
        self.arrange()
        self.append('x' * 300)
        self.app.work.transport = CallbackTransport(message={'content': 'y' * 300, 'tool_calls': []})
        with patch('ai_union.adapters.work_context_store.MAX_CONTEXT_BYTES', 500):
            receipt = self.app.work.run_step(self.token, self.request_value())
        card = self.card()
        self.assertEqual(receipt['model_outcome'], 'not_adoptable', receipt)
        self.assertEqual(card['inputs'][0]['status'], 'observed')
        self.assertEqual(card['input_cursor'], 0)
        self.assertNotIn('context_sha256', card['steps'][0])
        self.assertEqual(card['steps'][0]['usage'], {'input_tokens': 11, 'output_tokens': 4})
        self.assertEqual(card.get('results', []), [])

    def test_adoption_budget_includes_system_and_goal_of_the_next_turn(self):
        self.arrange()
        from ai_union.adapters.core_au_store import encoded
        from ai_union.domain import work
        state = self.state()
        prefix = work.step_plan(state, state['charter'], 'work-overview', instance=self.app.instance)['messages']
        input_message = {'role': 'user', 'content': 'x' * 300}
        reply = {'role': 'assistant', 'content': 'y' * 300, 'tool_calls': []}
        limit = max(len(encoded(prefix + [input_message]).encode()), len(encoded([input_message, reply]).encode())) + 1
        self.assertGreater(len(encoded(prefix + [input_message, reply]).encode()), limit)
        self.append(input_message['content'])
        self.app.work.transport = CallbackTransport(message={'content': reply['content'], 'tool_calls': []})
        with patch('ai_union.adapters.work_context_store.MAX_CONTEXT_BYTES', limit), \
                patch('ai_union.application.work_inputs.MAX_CONTEXT_BYTES', limit):
            receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt.get('model_outcome'), 'not_adoptable', receipt)
        self.assertEqual(self.card()['input_cursor'], 0)
        self.assertEqual(self.card()['inputs'][0]['status'], 'observed')

    def test_loop_next_child_includes_input_accepted_during_transport_construction(self):
        self.arrange()
        from tests.test_work_context import tool_call
        channel = FakeTransport([tool_call('list_documents', {}), {'content': '响应新增要求', 'tool_calls': []}])
        factories = []
        def factory(au_id, connection):
            factories.append(1)
            if len(factories) == 2:
                self.append('在下一预约前到达的要求')
            return channel
        self.app.work.transport = None
        self.app.work.transport_factory = factory
        request = self.request_value()
        request['kind'] = 'run_loop'
        result = self.app.work.run_loop(self.token, request)
        self.assertEqual(result['status'], 'succeeded', result)
        self.assertEqual(result['turns'], 2, result)
        self.assertEqual(channel.calls[1]['messages'][-1]['content'], '在下一预约前到达的要求')
        self.assertEqual(self.card()['input_cursor'], 1)

    def test_append_to_another_work_does_not_stop_the_original_loop(self):
        self.arrange()
        from tests.test_core_work import work_data
        from tests.test_work_context import tool_call
        status, value, _ = self.work(data=work_data(work_id='work-other', member_id='member-other',
            binding_id='binding-other', mandate_id='mandate-other', definition_id='definition-other'))
        self.assertEqual(status, 200, value)
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        channel = FakeTransport([tool_call('list_documents', {}), {'content': '原工作继续', 'tool_calls': []}])
        factory_calls = 0
        def factory(au_id, connection):
            nonlocal factory_calls
            factory_calls += 1
            if factory_calls == 2:
                status, value, _ = self.work_command(self.au_id, 'append_work_input', {
                    'work_id': 'work-other', 'input_id': 'input-other', 'content': '另一工作私有要求', 'reason': '只附入所属工作'})
                self.assertEqual(status, 200, value)
                self.assertEqual(value['receipt']['status'], 'succeeded', value)
            return channel
        self.app.work.transport_factory = factory
        receipt = self.app.work.run_loop(self.token, self.request_value() | {'kind': 'run_loop'})
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(receipt['turns'], 2)
        self.assertNotIn('另一工作私有要求', json.dumps(channel.calls, ensure_ascii=False))
        other = self.state()['work_runtime']['works']['work-other']
        self.assertEqual(other['inputs'][0]['status'], 'received')

    def test_pending_input_prevents_automatic_attempt_close_and_delivery(self):
        self.arrange()
        self.app.work.transport = CallbackTransport(lambda _: self.append('最后一步派发后的要求'))
        request = self.request_value()
        request['kind'] = 'run_loop'
        self.app.work.run_loop(self.token, request)
        result = self.card()['results'][0]
        _, adopted, _ = self.work_command(self.au_id, 'adopt_result', {
            'work_id': 'work-overview', 'result_id': result['id']})
        self.assertEqual(adopted['receipt']['status'], 'succeeded', adopted)
        self.assertEqual(self.card()['attempts'][0]['status'], 'running')
        self.work_command(self.au_id, 'finish_attempt', {'work_id': 'work-overview', 'attempt_id': self.attempt_id,
            'outcome': 'stopped', 'reason': '明确停止，保留未处理输入'})
        _, delivered, _ = self.work_command(self.au_id, 'deliver_work', {
            'work_id': 'work-overview', 'result_id': result['id']})
        self.assertEqual(delivered['receipt']['status'], 'rejected', delivered)

    def test_disabled_model_does_not_deny_input_or_schema_six_reconciliation(self):
        self.arrange()
        self.append()
        _, value, _ = self.model_command('set_connection', {'connection_id': 'connection-a',
            'expected_revision': 1, 'enabled': False, 'make_default': False})
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        _, value, _ = self.append('模型停用期间新要求')
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.assertEqual(self.works()['access']['can_append_input'], True)
        self.assertEqual(self.state()['schema_version'], 6)

    def test_old_installer_refuses_input_features_even_under_wrong_low_marker(self):
        self.arrange()
        from scripts import release_package as release
        save = self.app.work.store.save
        def low_marker(cx, state, charter, command, *args, **kwargs):
            if command['kind'] == 'append_work_input':
                state['schema_version'] = 5
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, 'save', side_effect=low_marker):
            self.append()
        before = self.dump()
        manifest = {'core_schemas': {'auth': 2, 'catalog': 1}, 'core_au_schemas': [1, 2, 3, 4, 5]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(manifest, {'console_state': self.root})
        release.check_core_schemas(manifest | {'core_au_schemas': [1, 2, 3, 4, 5, 6]}, {'console_state': self.root})
        self.assertEqual(before, self.dump())

    def test_old_installer_refuses_private_input_feature_with_missing_metadata(self):
        self.arrange()
        from scripts import release_package as release
        save = self.app.work.store.save
        def old_projection(cx, state, charter, command, *args, **kwargs):
            if command['kind'] == 'append_work_input':
                state['schema_version'] = 5
                target = state['work_runtime']['works']['work-overview']
                for name in ('inputs', 'input_seq', 'input_cursor'):
                    target.pop(name, None)
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, 'save', side_effect=old_projection):
            self.append()
        manifest = {'core_schemas': {'auth': 2, 'catalog': 1}, 'core_au_schemas': [1, 2, 3, 4, 5]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(manifest, {'console_state': self.root})

    def test_old_installer_detects_user_input_retained_only_in_private_turn(self):
        self.arrange()
        from ai_union.adapters.work_context_store import WorkContextStore
        from scripts import release_package as release
        self.app.work.transport = CallbackTransport()
        save = WorkContextStore.save
        def retain_private_input(cx, step, scope, messages, sources, binding):
            save(cx, step, scope, [{'role': 'user', 'content': '仅保留在旧投影的私有上下文'}] + messages,
                 sources, binding)
        with patch.object(WorkContextStore, 'save', side_effect=retain_private_input):
            receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(self.state()['schema_version'], 5)
        manifest = {'core_schemas': {'auth': 2, 'catalog': 1}, 'core_au_schemas': [1, 2, 3, 4, 5]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(manifest, {'console_state': self.root})

    def test_old_installer_cannot_resume_new_parent_without_child_binding(self):
        self.arrange()
        from scripts import release_package as release
        request = self.request_value() | {'kind': 'run_loop'}
        with patch.object(self.app.work, 'drive_loop', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.app.work.run_loop(self.token, request)
        self.assertEqual(self.state()['schema_version'], 5)
        self.assertTrue(self.card()['loops'][0]['bind_children'])
        manifest = {'core_schemas': {'auth': 2, 'catalog': 1}, 'core_au_schemas': [1, 2, 3, 4, 5]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(manifest, {'console_state': self.root})

    def test_input_limits_unicode_tamper_and_reads_never_write_or_truncate(self):
        self.arrange()
        before = self.dump()
        self.works()
        self.assertEqual(before, self.dump())
        for text in ('', '\x00x', '\ud800', '汉' * 21846):
            status, value, _ = self.append(text)
            self.assertEqual(status, 400, value)
        self.assertEqual(self.card().get('inputs', []), [])
        _, value, _ = self.append('x' * 65536, input_id='input-boundary')
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        from ai_union.domain import work_inputs
        with patch.object(work_inputs, 'MAX_ITEMS', 1):
            _, value, _ = self.append('第二条')
            self.assertEqual(value['receipt']['status'], 'rejected', value)
        with self.app.work.store.transaction(self.directory) as cx:
            cx.execute('UPDATE work_input_bodies SET content=? WHERE input_id=?', ('tampered', 'input-boundary'))
        query = '/api/v1/work/inputs?organization_id=' + self.au_id + '&work_id=work-overview&id=input-boundary'
        before = self.dump()
        status, value, _ = self.request(query)
        self.assertEqual(status, 409, value)
        self.assertEqual(before, self.dump())
        self.app.work.transport = channel = CallbackTransport()
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'rejected', receipt)
        self.assertEqual(channel.calls, [])

    def test_authority_handover_never_changes_input_actor_or_consumes_old_source(self):
        self.arrange()
        _, value, request = self.append('治理交接前要求', input_id='input-stable')
        original = copy.deepcopy(value['receipt']['input'])
        token, principal = self.participant('input-successor')
        self.success('nominate_governor', {'principal_id': principal, 'reason': '明确交接'})
        self.success('accept_governance', {'reason': '接受原责任'}, token=token)
        status, value, _ = self.append('旧治理主体不能补充', version=self.state()['version'])
        self.assertEqual(status, 403, value)
        status, value, _ = self.append('治理交接前要求', input_id='input-stable', token=token)
        self.assertEqual(status, 409, value)
        self.assertEqual(self.card()['inputs'][0], original)

    def test_public_step_version_is_strict_when_input_arrives_during_factory(self):
        self.arrange()
        channel = CallbackTransport()
        def factory(*args):
            self.append('公开命令之后的新输入')
            return channel
        self.app.work.transport = None
        self.app.work.transport_factory = factory
        from ai_union.errors import Rejected
        with self.assertRaises(Rejected):
            self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(channel.calls, [])

    def test_synthetic_context_limit_refuses_without_attachment_or_dispatch(self):
        self.arrange()
        self.append('上下文上限内不能截断的新要求')
        self.app.work.transport = channel = CallbackTransport()
        with patch('ai_union.application.work_inputs.MAX_CONTEXT_BYTES', 20):
            receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'rejected', receipt)
        self.assertEqual(self.card()['inputs'][0]['attachments'], [])
        self.assertEqual(channel.calls, [])

    def test_context_selects_complete_fitting_prefix_and_keeps_later_input_pending(self):
        self.arrange()
        _, first, _ = self.append('甲' * 100)
        _, second, _ = self.append('乙' * 100)
        from ai_union.domain import work
        from ai_union.adapters.core_au_store import encoded
        base = work.step_plan(self.state(), self.state()['charter'], 'work-overview', self.app.instance)
        limit = len(encoded(base['messages'] + [{'role': 'user', 'content': '甲' * 100}]).encode())
        self.app.work.transport = channel = FakeTransport([{'content': '响应第一项', 'tool_calls': []}])
        with patch('ai_union.application.work_inputs.MAX_CONTEXT_BYTES', limit):
            receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(channel.calls[0]['messages'][-1]['content'], '甲' * 100)
        self.assertEqual(self.card()['input_cursor'], 1)
        self.assertEqual([value['status'] for value in self.card()['inputs']], ['consumed', 'received'])
        self.assertEqual(self.card()['steps'][0]['input_refs'], [first['receipt']['input']['id']])
        self.assertEqual(self.card()['inputs'][1]['id'], second['receipt']['input']['id'])

    def test_actual_execution_snapshot_selects_fitting_prefix_without_raising_limit(self):
        self.arrange()
        self.append('第一项' * 100)
        self.append('第二项' * 100)
        self.app.work.transport = channel = FakeTransport([{'content': '有限快照成果', 'tool_calls': []}])
        with patch('ai_union.adapters.work_execution_store.MAX_EXECUTION_BYTES', 5000):
            from ai_union.errors import Rejected
            try:
                receipt = self.app.work.run_step(self.token, self.request_value())
            except Rejected as error:
                self.fail('可容纳原输入前缀不应因完整快照大小全拒绝：' + str(error))
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(channel.calls[0]['messages'][-1]['content'], '第一项' * 100)
        self.assertEqual(self.card()['input_cursor'], 1)
        self.assertEqual(self.card()['inputs'][1]['status'], 'received')
        with self.app.work.store.transaction(self.directory) as cx:
            payload = cx.execute('SELECT payload FROM work_execution_requests').fetchone()[0]
        self.assertLessEqual(len(payload.encode()), 5000)

    def test_current_governor_can_read_history_when_intake_has_exited(self):
        self.arrange()
        self.append('历史输入正文', input_id='input-history')
        self.success('exit_governance', {'reason': '明确退出治理，保留可读历史'})
        access = self.works()['access']
        self.assertFalse(access['can_append_input'])
        self.assertTrue(access.get('can_read_inputs'))
        query = '/api/v1/work/inputs?organization_id=' + self.au_id + '&work_id=work-overview&id=input-history'
        status, value, _ = self.request(query)
        self.assertEqual(status, 200, value)
        self.assertEqual(value['content'], '历史输入正文')
        token, _ = self.participant('input-history-outsider')
        status, _, _ = self.request(query, token=token)
        self.assertEqual(status, 403)

    def test_effective_timeout_exit_refuses_intake_and_preserves_history_read(self):
        self.arrange()
        self.append('超时前已经收存')
        self.assertEqual(self.state()['governance']['unavailability']['mode'], 'exit_after_timeout')
        with patch('time.time', return_value=self.state()['governance']['valid_until'] + 1):
            access = self.works()['access']
            self.assertFalse(access['can_append_input'])
            self.assertTrue(access['can_read_inputs'])
            status, _, _ = self.append('退出后的输入')
            self.assertIn(status, (400, 403))
        self.assertEqual(self.card()['input_seq'], 1)

    def test_legacy_loop_without_execution_snapshot_can_resume_original_first_child(self):
        self.arrange()
        from ai_union.application import work_dispatch as dispatch
        request = self.request_value() | {'kind': 'run_loop'}
        state = self.state()
        with self.app.work.store.transaction(self.directory) as cx:
            charter = state.pop('charter')
            work = state['work_runtime']['works']['work-overview']
            work.setdefault('loops', []).append({'command_id': request['id'], 'command_sha256': dispatch.request_digest(request),
                'principal_id': state['governance']['current_principal_id'], 'turn_cap': 1,
                'first_version': state['version'] + 1})
            dispatch.event(self.app.work.store, cx, state, charter, request,
                           state['governance']['current_principal_id'], 'loop_prepared')
        self.app.work.transport = channel = CallbackTransport()
        receipt = self.app.work.run_loop(self.token, request)
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(receipt['turns'], 1)
        self.assertEqual(len(channel.calls), 1)

    def test_first_input_that_cannot_fit_snapshot_refuses_before_any_reservation(self):
        self.arrange()
        self.append('无法容纳的首项' * 100)
        self.app.work.transport = channel = CallbackTransport()
        from ai_union.errors import Rejected
        with patch('ai_union.adapters.work_execution_store.MAX_EXECUTION_BYTES', 1000):
            with self.assertRaises(Rejected):
                self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(channel.calls, [])
        self.assertEqual(self.card().get('steps', []), [])
        self.assertEqual(self.card()['inputs'][0]['status'], 'received')
        self.assertEqual(self.card()['input_cursor'], 0)

    def test_first_input_body_and_schema_adoption_rollback_together(self):
        self.arrange()
        from ai_union.adapters.work_input_store import WorkInputStore
        save = WorkInputStore.save
        def fail(*args):
            save(*args)
            raise RuntimeError('controlled loss after body insertion')
        with patch.object(WorkInputStore, 'save', side_effect=fail):
            with self.assertRaises(RuntimeError):
                self.app.work.command(self.token, {'id': str(uuid.uuid4()), 'organization_id': self.au_id,
                    'base_version': self.state()['version'], 'kind': 'append_work_input', 'data': {
                    'work_id': 'work-overview', 'input_id': 'input-first', 'content': '事务中的输入', 'reason': '可靠收存'}})
        self.assertEqual(self.card().get('inputs', []), [])
        self.assertEqual(self.state()['schema_version'], 3)
        with self.app.work.store.transaction(self.directory) as cx:
            self.assertIsNone(cx.execute("SELECT 1 FROM sqlite_master WHERE name='work_input_bodies'").fetchone())

    def test_consumed_metadata_without_original_adoption_basis_is_rejected(self):
        self.arrange()
        self.append()
        from ai_union.domain.work_inputs import validate_state
        from ai_union.errors import Rejected
        target = copy.deepcopy(self.card())
        target['inputs'][0]['status'] = 'consumed'
        target['input_cursor'] = 1
        with self.assertRaises(Rejected):
            validate_state(target)

    def test_expired_governance_receives_but_cannot_attach_input(self):
        self.arrange()
        _, value, _ = self.append()
        self.assertEqual(value['receipt']['status'], 'succeeded')
        with patch('ai_union.domain.governance.effective_status', return_value='unavailable'):
            _, value, _ = self.append('治理暂不可执行时收存')
            self.assertEqual(value['receipt']['status'], 'succeeded', value)
            self.app.work.transport = channel = CallbackTransport()
            receipt = self.app.work.run_step(self.token, self.request_value())
            self.assertEqual(receipt['status'], 'rejected', receipt)
            self.assertEqual(channel.calls, [])

    def test_changed_source_scope_and_closed_attempt_never_consume_input(self):
        self.arrange()
        self.append()
        charter = copy.deepcopy(self.state()['charter'])
        self.success('amend_charter', {'charter': charter, 'reason': '有效来源版本变化需核对'})
        self.app.work.transport = channel = CallbackTransport()
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'rejected', receipt)
        self.assertEqual(channel.calls, [])
        self.assertEqual(self.card()['input_cursor'], 0)
        self.assertEqual(self.card()['inputs'][0]['status'], 'received')

    def test_close_during_observation_keeps_input_pending_and_no_context(self):
        self.arrange()
        self.append()
        service = self.app.work
        self.app.work.transport = CallbackTransport(lambda _: self.app.close())
        receipt = service.run_step(self.token, self.request_value())
        self.assertEqual(receipt['model_outcome'], 'unknown', receipt)
        self.assertEqual(self.card()['inputs'][0]['status'], 'observed')
        self.assertEqual(self.card()['input_cursor'], 0)
        self.assertNotIn('context_sha256', self.card()['steps'][0])

    def test_refused_original_can_reattach_without_losing_attachment_history(self):
        self.arrange()
        self.append()
        from ai_union.errors import Rejected
        def refuse(_):
            raise Rejected('受控明确拒绝，未执行')
        self.app.work.transport = CallbackTransport(refuse)
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['model_outcome'], 'refused', receipt)
        self.app.work.transport = CallbackTransport()
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(len(self.card()['inputs'][0]['attachments']), 2)
        self.assertEqual(self.card()['input_cursor'], 1)


class WorkInputRecoveryTests(WorkRecoveryTests):
    append = WorkInputTests.append

    def test_usage_only_reconciliation_cannot_discard_original_input_adoption(self):
        request = self.arrange()
        self.append('等待原请求采用的输入')
        request['base_version'] = self.state()['version']
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, request)
        self.stop(); self.start(); self.wire(client)
        step = self.card()['steps'][0]
        _, probe, _ = self.work_command(self.au_id, 'reconcile_step',
            {'work_id': 'work-overview', 'step_id': step['step_ref'], 'status': 'used', 'reason': '原请求用量核对'})
        self.assertEqual(probe['receipt']['status'], 'rejected', probe)
        self.assertIn(self.card()['steps'][0]['status'], ('reserved', 'unknown'))
        _, recovered, _ = self.recover()
        self.assertEqual(recovered['receipt']['status'], 'succeeded', recovered)
        self.assertEqual(self.card()['input_cursor'], 1)
        self.assertEqual(len(client.posts), 1)

    def test_unknown_original_recovers_input_and_context_exactly_once(self):
        self.arrange()
        self.append('未知原请求中的要求')
        request = self.request_value()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, request)
        self.assertEqual(len(self.card()['inputs'][0]['attachments']), 1)
        original = copy.deepcopy(self.card()['inputs'][0]['attachments'][0])
        self.assertEqual(self.card()['inputs'][0]['status'], 'attached')
        self.stop(); self.start()
        self.wire(client)
        _, value, _ = self.recover()
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.assertEqual(self.card()['input_cursor'], 1)
        self.assertEqual(self.card()['inputs'][0]['status'], 'consumed')
        self.assertEqual(self.card()['inputs'][0]['attachments'][0]['step_ref'], original['step_ref'])
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(sum(m.get('content') == '未知原请求中的要求' for m in client.posts[0]['messages']), 1)

    def test_false_remote_authority_retains_observed_pending_input(self):
        self.arrange()
        self.append()
        client = self.wire()
        client.authorized = False
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['model_outcome'], 'not_adoptable', receipt)
        self.assertEqual(self.card()['inputs'][0]['status'], 'observed')
        self.assertEqual(self.card()['input_cursor'], 0)

    def test_unknown_404_keeps_attachment_and_never_reposts(self):
        self.arrange()
        self.append()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, self.request_value())
        client.requests.clear()
        self.stop(); self.start()
        self.wire(client)
        self.recover()
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(self.card()['input_cursor'], 0)
        self.assertEqual(self.card()['inputs'][0]['status'], 'attached')
        self.assertIn(self.card()['steps'][0]['status'], ('reserved', 'unknown'))

    def test_recovered_tool_turn_keeps_user_and_tool_pairing_in_next_original_turn(self):
        self.arrange()
        self.append('原工具轮次输入')
        from tests.test_work_context import tool_call
        client = self.wire()
        client.crash_post = True
        request = self.request_value()
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, request)
        lookup = client.request
        def tools(request_id, au_id):
            value = lookup(request_id, au_id)
            value['result']['message'] = tool_call('list_documents', {})
            return value
        client.request = tools
        self.stop(); self.start()
        self.wire(client)
        self.recover()
        self.app.work.transport = channel = FakeTransport([{'content': '完整成果', 'tool_calls': []}])
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        messages = channel.calls[0]['messages']
        self.assertEqual(sum(m.get('content') == '原工具轮次输入' for m in messages), 1)
        call = next(m for m in messages if m['role'] == 'assistant')['tool_calls'][0]
        tool = next(m for m in messages if m['role'] == 'tool')
        self.assertEqual(tool['tool_call_id'], call['id'])

    def test_modeld_prefix_seals_exact_original_wire_and_preserves_pending(self):
        self.arrange()
        self.append('A' * 1000)
        self.append('B' * 1000)
        client = self.wire()
        with patch('ai_union.adapters.work_execution_store.MAX_EXECUTION_BYTES', 10000):
            receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt['status'], 'succeeded', receipt)
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(client.posts[0]['messages'][-1]['content'], 'A' * 1000)
        self.assertEqual(self.card()['inputs'][1]['status'], 'received')
        self.assertEqual(self.card()['input_cursor'], 1)
        from ai_union.adapters.work_execution_store import WorkExecutionStore, wire_digest
        step = self.card()['steps'][0]
        with self.app.work.store.transaction(self.directory) as cx:
            snapshot = WorkExecutionStore.load_request(cx, step)
            payload = cx.execute('SELECT payload FROM work_execution_requests').fetchone()[0]
        self.assertLessEqual(len(payload.encode()), 10000)
        self.assertEqual(snapshot['wire_body'], client.posts[0])
        self.assertEqual(wire_digest(snapshot['wire_body']), self.card()['steps'][0]['request_sha256'])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(cls(name) for cls in (WorkInputTests, WorkInputRecoveryTests)
                              for name in cls.__dict__ if name.startswith('test_'))
