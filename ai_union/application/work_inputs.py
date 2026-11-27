"""Low-impact input acceptance and private scoped reads through the sole AU writer."""
import copy
import hashlib

from ..adapters.core_au_store import CoreAUStore, encoded
from ..adapters.work_input_store import WorkInputStore
from ..adapters.work_context_store import MAX_CONTEXT_BYTES
from ..domain import governance, work, work_inputs as rules
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require


def command(service, token, incoming):
    principal = service.app.creation.principal(service.app.session(token))
    request = copy.deepcopy(incoming)
    try:
        governance.exact(request, {'id', 'organization_id', 'base_version', 'kind', 'data'})
        identifier(request['id'])
        identifier(request['organization_id'])
        require(type(request['base_version']) is int and request['base_version'] >= 0, '须提供当前 AU 版本')
        rules.validate_input(request['data'])
    except (Rejected, TypeError, ValueError, KeyError, UnicodeError) as error:
        raise CoreError('invalid_request', str(error)) from error
    stored = copy.deepcopy(request)
    content = stored['data'].pop('content')
    stored['data']['content_sha256'] = hashlib.sha256(content.encode('utf-8')).hexdigest()
    with service.app.mutex, service.app.catalog() as accounts:
        require(service.app.identity.principal_in(accounts, token) == principal, '登录主体已变化')
        directory, intent = service.app.governance.locate(request['organization_id'])
        with service.store.transaction(directory) as cx:
            state = CoreAUStore.read_in(cx, request['organization_id'], creation=intent)['au']
            previous = service.store.existing(cx, stored, principal)
            if previous is not None:
                return previous
            work.authorize(state, principal)
            if not rules.can_append(state, principal):
                raise CoreError('not_authorized', '当前主体不能收存此组织输入')
            service.store.ensure_commands(cx)
            local = copy.deepcopy(state)
            charter = local.pop('charter')
            receipt = {key: request[key] for key in ('id', 'organization_id', 'base_version', 'kind')} | {
                'actor_principal_id': principal, 'created_at': now(), 'status': 'succeeded', 'effect': 'applied',
                'work_id': request['data']['work_id']}
            changed = False
            cx.execute('SAVEPOINT input_command')
            try:
                require(request['base_version'] == local['version'], 'AU 版本已变化；请核对原输入')
                item, changed = rules.append(local, request['data'], principal)
                if changed:
                    WorkInputStore.save(cx, local['id'], request['data']['work_id'], item, content)
                    local['version'] += 1
                else:
                    WorkInputStore.load(cx, local['id'], request['data']['work_id'], item)
                receipt.update(input=item, message='输入已收存；后续原步骤采用另行记录',
                               effect='applied' if changed else 'none')
            except CoreError:
                raise
            except Rejected as error:
                cx.execute('ROLLBACK TO input_command')
                local = copy.deepcopy(state)
                local.pop('charter')
                changed = False
                receipt.update(status='rejected', effect='none', message=str(error))
            cx.execute('RELEASE input_command')
            receipt['version'] = local['version']
            service.store.save(cx, local, charter, stored, receipt, local['policy_version'], changed=changed)
            return receipt


def read(service, token, au_id, work_id, input_id):
    try:
        identifier(au_id)
        require(work.reference(work_id) and work.reference(input_id), '工作或输入引用无效')
    except (Rejected, TypeError) as error:
        raise CoreError('invalid_request', str(error)) from error
    principal = service.app.creation.principal(service.app.session(token))
    with service.app.mutex, service.app.catalog() as accounts:
        require(service.app.identity.principal_in(accounts, token) == principal, '登录主体已变化')
        directory, intent = service.app.governance.locate(au_id)
        with service.store.transaction(directory) as cx:
            state = CoreAUStore.read_in(cx, au_id, creation=intent)['au']
            work.authorize(state, principal)
            target = work.records(state)['works'].get(work_id)
            item = next((item for item in (target or {}).get('inputs', []) if item['id'] == input_id), None)
            if item is None:
                raise CoreError('invalid_request', '输入不存在或不属于此 AU/Work')
            content = WorkInputStore.load(cx, au_id, work_id, item)
            return {'protocol': 'core.work-input.v1', 'organization_id': au_id, 'work_id': work_id,
                    'input': copy.deepcopy(item), 'content': content}


def select(cx, state, target, plan):
    """Select a legal contiguous pending prefix before its original reservation."""
    refs, messages = [], []
    current_scope = rules.scope(state, target)
    for item in target.get('inputs', []):
        if item['status'] == 'consumed':
            continue
        require(item['source_scope'] == current_scope, '原输入来源版本已变化；保留待核对，不能隐式改来源')
        if item['attachments']:
            last = item['attachments'][-1]
            previous = next((s for s in target.get('steps', []) if s['step_ref'] == last['step_ref']), None)
            require(previous is not None and previous['status'] == 'released',
                    '原输入已附入未明确未执行的请求；保留原关联，不能附入另一请求')
        content = WorkInputStore.load(cx, state['id'], target['id'], item)
        candidate = messages + [{'role': 'user', 'content': content}]
        if len(encoded(plan['messages'] + candidate).encode('utf-8')) > MAX_CONTEXT_BYTES:
            require(refs, '首项输入不能容纳于 4 MiB 上下文；保留原输入，不截断')
            break
        refs.append(item['id'])
        messages.append({'role': 'user', 'content': content})
    require(len(encoded(plan['messages'] + messages).encode('utf-8')) <= MAX_CONTEXT_BYTES,
            '合成模型上下文超过 4 MiB 上限；原输入保留，不截断')
    plan['input_refs'] = refs
    plan['input_messages'] = messages
    plan['input_source_scope'] = current_scope
    plan['messages'].extend(messages)


def fit_request(plan, step, request, transport):
    """Whole-input prefix sized by the same actual wire/snapshot encoder as save."""
    from ..adapters import work_execution_store as snapshots
    while True:
        wire = transport.body(plan['package'], plan['messages'], plan['tools']) if hasattr(transport, 'body') else None
        _, _, wire_bytes, snapshot_bytes = snapshots.WorkExecutionStore.request_snapshot(step, request, plan, wire)
        if wire_bytes <= snapshots.MAX_EXECUTION_BYTES and snapshot_bytes <= snapshots.MAX_EXECUTION_BYTES:
            return wire
        require(len(plan.get('input_refs', [])) > 1,
                '首项输入或原上下文不能容纳于模型 wire/执行快照上限；保留原输入，不截断')
        plan['input_refs'].pop()
        plan['input_messages'].pop()
        plan['messages'].pop()


def attach(state, plan, step):
    target = work.records(state)['works'][plan['work_id']]
    step['input_refs'] = list(plan.get('input_refs', []))
    for input_id in step['input_refs']:
        item = next(value for value in target['inputs'] if value['id'] == input_id)
        item['attachments'].append({'step_ref': step['step_ref'], 'model_request_id': step['model_request_id'],
                                    'request_sha256': step['request_sha256'], 'attached_at': now(),
                                    'execution_owner': copy.deepcopy(plan['execution_owner'])})
        item['status'] = 'attached'


def validate_attachment(cx, state, target, step, plan):
    refs = plan.get('input_refs', [])
    require(refs == step.get('input_refs', []), '原输入快照与预约关联不一致')
    require(len(refs) == len(plan.get('input_messages', [])), '原输入消息快照不完整')
    for input_id, message in zip(refs, plan.get('input_messages', [])):
        item = next((value for value in target.get('inputs', []) if value['id'] == input_id), None)
        require(item is not None and item['status'] != 'consumed'
                and item['source_scope'] == rules.scope(state, target), '原输入来源或采用状态已变化；保留待核对')
        attached = next((a for a in item['attachments'] if a['step_ref'] == step['step_ref']), None)
        require(attached is not None and attached['model_request_id'] == step['model_request_id']
                and attached['request_sha256'] == step['request_sha256'], '原输入与原模型请求关联不一致')
        require(message == {'role': 'user', 'content': WorkInputStore.load(cx, state['id'], target['id'], item)},
                '原输入消息快照与不可变正文不一致')


def observe(state, step):
    target = work.records(state)['works'][step['context_scope']['work_id']]
    for input_id in step.get('input_refs', []):
        item = next(value for value in target['inputs'] if value['id'] == input_id)
        attached = next(a for a in item['attachments'] if a['step_ref'] == step['step_ref'])
        attached['observed_at'] = now()
        if item['status'] != 'consumed':
            item['status'] = 'observed'
            item['observed_step_ref'] = step['step_ref']


def consume(state, target, step, expected_owner, result=None):
    for input_id in step.get('input_refs', []):
        item = next(value for value in target['inputs'] if value['id'] == input_id)
        attached = next(a for a in item['attachments'] if a['step_ref'] == step['step_ref'])
        attached.update(consumed_at=now(), adopted_scope=rules.scope(state, target),
                        adopted_owner=copy.deepcopy(expected_owner))
        item.update(status='consumed', consumed_step_ref=step['step_ref'])
    cursor = 0
    for item in target.get('inputs', []):
        if item['status'] != 'consumed':
            break
        cursor = item['seq']
    if target.get('inputs'):
        target['input_cursor'] = cursor
    step['input_cursor'] = cursor
    if result is not None:
        result.update(input_cursor=cursor, input_refs=list(step.get('input_refs', [])),
                      input_step_ref=step['step_ref'])
