"""Bounded immutable requirement metadata on the original Work, no execution authority."""
import copy
import hashlib
import re
import time

from . import governance, work
from .creation import text, valid_principal
from ..errors import CoreError, require

MAX_BYTES = 65536
MAX_ITEMS = 100
MAX_TOTAL_BYTES = 8 * 1024 * 1024
STATUSES = ('received', 'attached', 'observed', 'consumed')
SCOPE_FIELDS = {'member_id', 'binding_id', 'binding_version', 'definition_id', 'definition_version',
                'mandate_id', 'mandate_version', 'charter_version', 'policy_version'}
HASH = re.compile('[a-f0-9]{64}\\Z')


def validate_scope(value):
    governance.exact(value, SCOPE_FIELDS, '输入来源')
    for key, item in value.items():
        require(work.reference(item) if key.endswith('_id') else type(item) is int and item >= 1,
                '输入来源身份或版本无效')


def validate_owner(value):
    from .work_recovery import validate
    require(isinstance(value, dict), '输入执行所有者依据无效')
    validate({'execution_owner': value})


def validate_input(data):
    governance.exact(data, {'work_id', 'input_id', 'content', 'reason'})
    require(work.reference(data['work_id']) and work.reference(data['input_id']), '工作或输入引用无效')
    text(data['reason'], '输入依据', 10000)
    require(isinstance(data['content'], str) and data['content'].strip() and '\x00' not in data['content'],
            '输入必须是非空 UTF-8 文本')
    require(len(data['content'].encode('utf-8')) <= MAX_BYTES, '输入超过 64 KiB 上限')


def scope(state, item):
    records = work.records(state)
    binding = records['bindings'][item['responsible_binding_id']]
    definition = records['definitions'][item['definition_id']]
    mandate = records['mandates'][item['mandate_id']]
    return {'member_id': binding['member_id'], 'binding_id': binding['id'], 'binding_version': binding['version'],
            'definition_id': definition['id'], 'definition_version': definition['version'],
            'mandate_id': mandate['id'], 'mandate_version': mandate['version'],
            'charter_version': state['charter_version'], 'policy_version': state['policy_version']}


def can_append(state, principal):
    return (state['schema_version'] in governance.SUPPORTED_SCHEMAS
            and governance.current(state) == principal and governance.effective_status(state, time.time()) != 'exited')


def can_read(state, principal):
    return governance.current(state) == principal


def append(state, data, principal):
    item = work.records(state)['works'].get(data['work_id'])
    require(item is not None, '工作不存在或不属于此 AU')
    raw = data['content'].encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    inputs = item.get('inputs', [])
    previous = next((value for value in inputs if value['id'] == data['input_id']), None)
    if previous is not None:
        if previous['actor_principal_id'] != principal:
            raise CoreError('id_conflict', '输入引用属于原主体，不能冒用')
        if previous['sha256'] != digest:
            raise CoreError('id_conflict', '输入引用已用于不同正文')
        return copy.deepcopy(previous), False
    require(item['status'] in work.OPEN, '工作已结束，不能隐式重开或补充输入')
    require(len(inputs) < MAX_ITEMS, '该工作输入已达 100 条上限；历史不能删除')
    require(sum(value['bytes'] for value in inputs) + len(raw) <= MAX_TOTAL_BYTES, '该工作输入正文超过 8 MiB 上限')
    value = {'id': data['input_id'], 'seq': len(inputs) + 1, 'sha256': digest, 'bytes': len(raw),
             'source_kind': 'requirement', 'actor_principal_id': principal, 'received_at': work._stamp(),
             'reason': data['reason'], 'source_scope': scope(state, item), 'status': 'received', 'attachments': []}
    item.setdefault('inputs', []).append(value)
    item['input_seq'] = value['seq']
    item.setdefault('input_cursor', 0)
    state['schema_version'] = max(state['schema_version'], 6)
    return copy.deepcopy(value), True


def projection(item):
    inputs = copy.deepcopy(item.get('inputs', []))
    summary = {status: sum(value['status'] == status for value in inputs) for status in STATUSES}
    summary['pending'] = sum(value['status'] != 'consumed' for value in inputs)
    return {'inputs': inputs, 'input_seq': item.get('input_seq', 0), 'input_cursor': item.get('input_cursor', 0),
            'input_summary': summary}


def validate_state(item):
    inputs = item.get('inputs', [])
    require(isinstance(inputs, list) and len(inputs) <= MAX_ITEMS, '输入记录无效')
    require(type(item.get('input_seq', 0)) is int and item.get('input_seq', 0) == len(inputs)
            and type(item.get('input_cursor', 0)) is int,
            '输入顺序或采用游标无效')
    require(0 <= item.get('input_cursor', 0) <= len(inputs), '输入采用游标无效')
    seen = set()
    for seq, value in enumerate(inputs, 1):
        require(isinstance(value, dict) and work.reference(value.get('id')) and value['id'] not in seen
                and value.get('seq') == seq and value.get('status') in STATUSES
                and value.get('source_kind') == 'requirement' and isinstance(value.get('source_scope'), dict)
                and isinstance(value.get('attachments'), list), '输入身份或来源不一致')
        require(isinstance(value.get('sha256'), str) and HASH.fullmatch(value['sha256'])
                and type(value.get('bytes')) is int and 0 < value['bytes'] <= MAX_BYTES, '输入正文摘要无效')
        require(valid_principal(value.get('actor_principal_id')) and isinstance(value.get('received_at'), str)
                and isinstance(value.get('reason'), str) and 0 < len(value['reason']) <= 10000,
                '输入主体或接收依据无效')
        validate_scope(value['source_scope'])
        attachments = value['attachments']
        require(value['status'] == 'received' or attachments, '输入状态缺少原请求关联')
        steps_seen = set()
        for attachment in attachments:
            require(isinstance(attachment, dict), '原输入关联无效')
            step = next((step for step in item.get('steps', [])
                         if step['step_ref'] == attachment.get('step_ref')), None)
            require(step is not None and step['step_ref'] not in steps_seen
                    and value['id'] in step.get('input_refs', [])
                    and attachment.get('model_request_id') == step.get('model_request_id')
                    and attachment.get('request_sha256') == step.get('request_sha256')
                    and isinstance(attachment.get('attached_at'), str), '输入与原请求或预约关联不一致')
            validate_owner(attachment.get('execution_owner'))
            steps_seen.add(step['step_ref'])
        if value['status'] in ('observed', 'consumed'):
            basis = next((attachment for attachment in attachments
                          if attachment['step_ref'] == value.get('observed_step_ref')), None)
            require(basis is not None and isinstance(basis.get('observed_at'), str), '输入缺少原模型观察依据')
        if value['status'] == 'consumed':
            basis = next((attachment for attachment in attachments
                          if attachment['step_ref'] == value.get('consumed_step_ref')), None)
            adopted = next((step for step in item.get('steps', [])
                            if step['step_ref'] == value.get('consumed_step_ref')), None)
            require(basis is not None and isinstance(basis.get('consumed_at'), str)
                    and adopted is not None and adopted['status'] == 'used'
                    and adopted.get('dispatch_phase') == 'adopted' and adopted.get('context_sha256'),
                    '输入缺少原步骤成功采用和上下文依据')
            validate_scope(basis.get('adopted_scope'))
            validate_owner(basis.get('adopted_owner'))
        require(seq > item.get('input_cursor', 0) or value['status'] == 'consumed', '游标跨过未采用输入')
        seen.add(value['id'])
    require(sum(value['bytes'] for value in inputs) <= MAX_TOTAL_BYTES, '输入正文总量无效')
    prefix = 0
    for value in inputs:
        if value['status'] != 'consumed':
            break
        prefix = value['seq']
    require(item.get('input_cursor', 0) == prefix, '输入游标未匹配连续成功采用的前缀')
