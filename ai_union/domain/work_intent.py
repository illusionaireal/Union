"""Durable approval and public Work intent state."""
import copy
import hashlib
import re

from . import work
from .creation import text, valid_principal
from .work_inputs import HASH, validate_scope
from ..engine import identifier
from ..errors import CoreError, require

SCHEMA = 7
MODES = ('automatic_text', 'governor_review')
STATUSES = ('accepted', 'running', 'waiting_unknown', 'awaiting_decision', 'blocked',
            'delivered', 'stopped')
KINDS = ('start_work_intent', 'decide_work_intent', 'stop_work_intent')
CANDIDATE_FIELDS = {'result_id', 'result_seq', 'sha256', 'input_cursor'}
PUBLIC_FIELDS = ('id', 'status', 'delivery_mode', 'authorized_principal_id', 'attempt_id', 'reason')

START_ID = re.compile(r'intent-([a-f0-9]{24})-[a-f0-9]{32}')


def validate_start_id(au_id, request_id):
    matched = START_ID.fullmatch(request_id)
    if not matched:
        raise CoreError('invalid_request', '工作意图请求标识格式无效')
    scope = hashlib.sha256(au_id.encode('utf-8')).hexdigest()[:24]
    if matched.group(1) != scope:
        raise CoreError('not_authorized')


def start_data(data):
    return {key: value for key, value in data.items() if key not in ('constraints', 'delivery_mode')}


def validate_input(kind, data):
    from . import governance
    if kind == 'start_work_intent':
        work.validate_input('start_work', start_data(data))
        require(data.get('delivery_mode') in MODES, '交付方式必须是自动文本交付或治理者审查')
        constraints = data.get('constraints')
        require(isinstance(constraints, str) and len(constraints) <= 4096 and '\x00' not in constraints,
                '工作约束必须是至多 4096 字符的文本，可留空')
        constraints.encode('utf-8')
        return
    fields = {'work_id', 'intent_id', 'reason'}
    if kind == 'decide_work_intent':
        fields |= CANDIDATE_FIELDS
    governance.exact(data, fields)
    require(work.reference(data['work_id']), '工作引用无效')
    identifier(data['intent_id'])
    text(data['reason'], '决定依据', 10000)
    if kind == 'decide_work_intent':
        validate_candidate({key: data[key] for key in CANDIDATE_FIELDS})


def validate_candidate(value):
    require(work.reference(value['result_id']) and type(value['result_seq']) is int and value['result_seq'] >= 1
            and isinstance(value['sha256'], str) and HASH.fullmatch(value['sha256'])
            and type(value['input_cursor']) is int and value['input_cursor'] >= 0, '原候选引用或输入游标无效')


def projection(intent):
    value = {key: intent[key] for key in PUBLIC_FIELDS}
    if intent.get('decision') is not None:
        value['decision'] = copy.deepcopy(intent['decision'])
    return value


def validate_state(item):
    if 'intent' not in item:
        return
    intent = item['intent']
    require(isinstance(intent, dict), '持久工作批准无效')
    identifier(intent.get('id'))
    require(intent['id'] == item['request_id'] and intent.get('status') in STATUSES
            and intent.get('delivery_mode') in MODES and valid_principal(intent.get('authorized_principal_id'))
            and intent['authorized_principal_id'] == item['authorized_by_principal_id']
            and isinstance(intent.get('reason'), str)
            and isinstance(intent.get('constraints'), str) and len(intent['constraints']) <= 4096
            and isinstance(intent.get('approval'), dict)
            and type(intent.get('checked_version')) is int and intent['checked_version'] >= 1,
            '持久工作批准无效')
    approval = intent['approval']
    require(set(approval) == {'responsibility', 'connection', 'materials_binding', 'max_calls'}
            and isinstance(approval['connection'], dict)
            and isinstance(approval['materials_binding'], str) and HASH.fullmatch(approval['materials_binding'])
            and approval['max_calls'] == item['max_calls'], '持久工作批准的资料、模型或次数无效')
    validate_scope(approval['responsibility'])
    attempts = item.get('attempts') or []
    require(len(attempts) == 1 and attempts[0]['id'] == intent.get('attempt_id')
            and attempts[0]['owner_principal_id'] == intent['authorized_principal_id'],
            '持久工作必须保留一个原执行尝试')
    require((intent['status'] == 'delivered') == (item['status'] == 'delivered'),
            '工作意图交付状态与原工作不一致')
    decision = intent.get('decision')
    if decision:
        require(intent['status'] in ('awaiting_decision', 'delivered') and intent['delivery_mode'] == 'governor_review'
                and decision.get('authorized_principal_id') == intent['authorized_principal_id'],
                '原候选决定主体或工作阶段无效')
        validate_candidate(decision)
        require(any(result['id'] == decision['result_id'] and result['seq'] == decision['result_seq']
                    and result['sha256'] == decision['sha256'] and result['attempt_id'] == intent['attempt_id']
                    and result.get('input_cursor', 0) == decision['input_cursor'] for result in item.get('results', [])),
                '待决定候选缺少原成果依据')
    else:
        require(intent['status'] != 'awaiting_decision', '工作审查缺少可行动的原候选')
