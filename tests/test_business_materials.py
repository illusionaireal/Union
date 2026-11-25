"""U120: ordinary core users import and authorize one business text for a Work."""
import copy
import hashlib
import json
import uuid
import sqlite3
from unittest.mock import patch
from contextlib import closing

from tests.model_access_support import ModelAccessCase
from tests import test_core_work as work_support

work_data = work_support.work_data


class BusinessMaterialsTests(ModelAccessCase):
    adopt_default = work_support.CoreWorkTests.adopt_default
    work_command = work_support.CoreWorkTests.work_command
    work = work_support.CoreWorkTests.work
    works = work_support.CoreWorkTests.works
    start_attempt = work_support.CoreWorkTests.start_attempt
    work_step = work_support.CoreWorkTests.work_step
    second_au = work_support.CoreWorkTests.second_au

    def material(self, content='项目由三个模块组成。\n', name='研究资料.md', **changes):
        data = {'material_id': 'material-' + uuid.uuid4().hex, 'name': name,
                'content': content, 'source': 'paste', 'reason': '授权本组织工作只读这份资料'}
        data.update(changes)
        status, value, request = self.work_command(self.au_id, 'import_material', data)
        return status, value, request

    def imported(self):
        status, value, request = self.material()
        self.assertEqual(status, 200, value)
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        return value['receipt']['material'], request

    def catalog(self):
        status, value, _ = self.request('/api/v1/work/materials?organization_id=' + self.au_id)
        self.assertEqual(status, 200, value)
        return value

    def test_import_catalog_and_original_receipt_preserve_one_private_body(self):
        before = self.read()['au']['version']
        material, request = self.imported()
        self.assertEqual(material['version'], 1)
        self.assertEqual(material['scope'], 'au_read_only')
        self.assertEqual(material['sha256'], hashlib.sha256(request['data']['content'].encode()).hexdigest())
        self.assertTrue(material['read_allowed'])
        public = self.catalog()
        self.assertEqual(public['protocol'], 'core.materials.v1')
        self.assertEqual(public['materials'], [material])
        self.assertEqual(public['version'], before + 1)
        self.assertNotIn(request['data']['content'], json.dumps(public, ensure_ascii=False))
        status, replay, _ = self.request('/api/v1/work/commands', request)
        self.assertEqual(status, 200, replay)
        self.assertEqual(replay['receipt'], self.request('/api/v1/governance/receipts?organization_id=' + self.au_id + '&id=' + request['id'])[1]['receipt'])
        self.assertEqual(self.catalog()['version'], before + 1)
        changed = copy.deepcopy(request)
        changed['data']['content'] += '不同正文'
        self.assertEqual(self.request('/api/v1/work/commands', changed)[0], 409)

    def test_same_work_reads_selected_version_without_host_configuration(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        material, _ = self.imported()
        status, value, _ = self.work(data=work_data(materials_root=material['id'], material_version=1))
        self.assertEqual(status, 200, value)
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.start_attempt()
        status, value, _ = self.work_command(self.au_id, 'invoke_tool', {
            'work_id': 'work-overview', 'tool': 'read_document', 'arguments': {'path': material['name']}})
        self.assertEqual(status, 200, value)
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.assertNotIn('text', value['receipt']['result'])
        self.assertEqual(value['receipt']['result']['sha256'], material['sha256'])
        self.assertEqual(value['receipt']['result']['bytes'], material['bytes'])
        self.assertEqual(value['receipt']['tool_call']['material_id'], material['id'])
        self.assertEqual(value['receipt']['tool_call']['material_version'], 1)

    def test_imported_tool_receipt_never_persists_or_replays_private_body(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        material, imported = self.imported()
        _, value, _ = self.work(data=work_data(materials_root=material['id'], material_version=1))
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.start_attempt()
        _, read, request = self.work_command(self.au_id, 'invoke_tool', {
            'work_id': 'work-overview', 'tool': 'read_document', 'arguments': {'path': material['name']}})
        self.assertEqual(read['receipt']['status'], 'succeeded', read)
        with closing(sqlite3.connect(self.database())) as cx:
            receipt = cx.execute('SELECT receipt FROM governance_commands WHERE id=?', (request['id'],)).fetchone()[0]
            self.assertNotIn('text', json.loads(receipt)['result'])
        _, revoked, _ = self.work_command(self.au_id, 'revoke_material', {
            'material_id': material['id'], 'expected_version': 1, 'reason': '停止后续披露'})
        self.assertEqual(revoked['receipt']['status'], 'succeeded', revoked)
        for status, response, _ in (
            self.request('/api/v1/governance/receipts?organization_id=' + self.au_id + '&id=' + request['id']),
            self.request('/api/v1/work/commands', request),
        ):
            self.assertEqual(status, 200, response)
            self.assertNotIn('text', response['receipt']['result'])
            self.assertEqual(response['receipt'], read['receipt'])
        self.assertEqual(len(self.works()['works'][0]['tool_calls']), 1)

    def test_revoke_rejects_later_read_and_keeps_original_work_and_body(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        material, _ = self.imported()
        status, value, _ = self.work(data=work_data(materials_root=material['id'], material_version=1))
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.start_attempt()
        status, revoked, _ = self.work_command(self.au_id, 'revoke_material', {
            'material_id': material['id'], 'expected_version': 1, 'reason': '停止后续读取'})
        self.assertEqual(revoked['receipt']['status'], 'succeeded', revoked)
        self.assertEqual(revoked['receipt']['material']['version'], 2)
        self.assertFalse(self.catalog()['materials'][0]['read_allowed'])
        status, refused, _ = self.work_command(self.au_id, 'invoke_tool', {
            'work_id': 'work-overview', 'tool': 'read_document', 'arguments': {'path': material['name']}})
        self.assertEqual(refused['receipt']['status'], 'rejected', refused)
        self.assertEqual(len(self.works()['works']), 1)

    def test_controlled_model_tool_roundtrip_carries_the_imported_body_and_source(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        material, _ = self.imported()
        status, value, _ = self.work(data=work_data(materials_root=material['id'], material_version=1))
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.start_attempt()
        transport = work_support.FakeTransport([
            {'content': None, 'tool_calls': [{'id': 'read-import', 'type': 'function', 'function': {
                'name': 'read_document', 'arguments': json.dumps({'path': material['name']})}}]},
            {'content': '确认为三个模块', 'tool_calls': []},
        ])
        self.app.work.transport = transport
        for _ in range(2):
            status, result, _ = self.work_step()
            self.assertEqual(status, 200, result)
            self.assertEqual(result['receipt']['status'], 'succeeded', result)
        output = json.loads(transport.calls[1]['messages'][-1]['content'])
        self.assertEqual(output['content'], '项目由三个模块组成。\n')
        self.assertEqual(output['sha256'], material['sha256'])
        work = self.works()['works'][0]
        self.assertEqual(work['tool_calls'][0]['material_id'], material['id'])
        self.assertIn(work['tool_calls'][0]['step_ref'], work['results'][0]['sources'])

    def test_unsubmitted_discovery_is_read_only_and_private_body_is_not_audit_payload(self):
        before = self.dump()
        self.assertEqual(self.catalog()['materials'], [])
        self.assertEqual(self.dump(), before)
        item, request = self.imported()
        with closing(sqlite3.connect(self.database())) as cx:
            payload, receipt = cx.execute('SELECT payload,receipt FROM governance_commands WHERE id=?', (request['id'],)).fetchone()
            self.assertNotIn(request['data']['content'], payload)
            self.assertNotIn(request['data']['content'], receipt)
            self.assertEqual(json.loads(payload)['data']['content_sha256'], item['sha256'])
            snapshot = cx.execute('SELECT snapshot FROM governance_events ORDER BY version DESC LIMIT 1').fetchone()[0]
            self.assertNotIn(request['data']['content'], snapshot)

    def test_limits_and_bad_names_reject_without_creating_content_or_authority(self):
        before = self.dump()
        for content, name in [('a' * 65537, 'large.txt'), ('a\x00b', 'binary.txt'), ('', 'empty.txt'),
                              ('a', '../secret.txt'), ('a', 'image.png')]:
            status, value, _ = self.material(content, name)
            self.assertEqual(status, 400, value)
        self.assertEqual(self.dump(), before)

    def test_storage_failure_rolls_back_body_and_metadata_and_original_id_is_recoverable(self):
        from ai_union.adapters.governance_store import GovernanceStore
        before = self.dump()
        with patch.object(GovernanceStore, 'save', side_effect=sqlite3.OperationalError('controlled write failure')):
            status, value, request = self.material()
        self.assertEqual(status, 503, value)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.request('/api/v1/governance/receipts?organization_id=' + self.au_id + '&id=' + request['id'])[0], 403)

    def test_other_au_and_principal_cannot_take_the_imported_reference(self):
        item, request = self.imported()
        outsider, _ = self.participant('outsider')
        self.assertEqual(self.request('/api/v1/work/materials?organization_id=' + self.au_id, token=outsider)[0], 403)
        self.assertEqual(self.request('/api/v1/work/commands', request, token=outsider)[0], 403)
        other = self.second_au()
        status, value, _ = self.work_command(other, 'revoke_material', {
            'material_id': item['id'], 'expected_version': 1, 'reason': '不能跨组织撤销'})
        self.assertEqual(value['receipt']['status'], 'rejected', value)
        self.assertTrue(self.catalog()['materials'][0]['read_allowed'])

    def test_revocation_during_completed_model_call_keeps_usage_without_adopting_body(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        item, _ = self.imported()
        _, value, _ = self.work(data=work_data(materials_root=item['id'], material_version=1))
        self.assertEqual(value['receipt']['status'], 'succeeded', value)
        self.start_attempt()
        owner = self

        class RevokingTransport:
            def chat(self, package, messages, tools):
                _, revoked, _ = owner.work_command(owner.au_id, 'revoke_material', {
                    'material_id': item['id'], 'expected_version': 1, 'reason': '正在调用时撤权'})
                owner.assertEqual(revoked['receipt']['status'], 'succeeded', revoked)
                return {'content': '不得采用的正文', 'tool_calls': []}, {'input_tokens': 9, 'output_tokens': 2}

        self.app.work.transport = RevokingTransport()
        _, result, _ = self.work_step()
        self.assertEqual(result['receipt']['status'], 'rejected', result)
        work = self.works()['works'][0]
        self.assertEqual(work['steps'][0]['status'], 'used')
        self.assertEqual(work['steps'][0]['usage'], {'input_tokens': 9, 'output_tokens': 2})
        self.assertEqual(work['results'], [])
