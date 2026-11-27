"""Application of one bounded approval through the existing Work transaction."""
import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass

from ..adapters import documents
from ..adapters.core_au_store import CoreAUStore
from ..adapters.work_context_store import WorkContextStore
from ..adapters.work_execution_store import WorkExecutionStore
from ..domain import work as rules, work_inputs, work_intent as intents, work_recovery as ownership
from ..errors import Rejected, require
from ..model_service import ServiceError
from . import work_dispatch as dispatch
from .work_events import connection_scope

LOG = logging.getLogger(__name__)
ACTIONABLE = frozenset(('accepted', 'running', 'waiting_unknown'))


@dataclass(frozen=True)
class Approval:
    """Process-local reference to the persisted authority, scoped to one original epoch."""
    au_id: str
    work_id: str
    intent_id: str
    attempt_id: str
    principal: str
    owner: dict


def approval_scope(service, cx, state, work):
    records = rules.records(state)
    definition = records['definitions'][work['definition_id']]
    binding = records['bindings'][work['responsible_binding_id']]
    mandate = records['mandates'][work['mandate_id']]
    member = records['members'][binding['member_id']]
    require(binding['active'] and mandate['active'] and mandate['work_id'] == work['id']
            and mandate['work_version'] == work['version'] and mandate['binding_id'] == binding['id']
            and mandate['definition_id'] == member['definition_id'] == definition['id']
            and mandate['definition_version'] == member['definition_version'] == definition['version']
            and work['definition_version'] == definition['version']
            and set(definition['tools']) <= set(mandate['actions']),
            '工作责任、成员定义或有效授权已变化')
    connection = rules.connection(state, definition['connection_id'], definition['connection_revision'])
    source = documents.WorkDocuments(service.app.root, state, work, cx)
    return {'responsibility': work_inputs.scope(state, work), 'connection': connection_scope(connection),
            'materials_binding': source.binding, 'max_calls': work['max_calls']}


def accept(service, cx, state, charter, request, principal, grant):
    data = request['data']
    require('material_version' in data, '持久工作意图须明确绑定当前业务资料版本')
    require(service.transport is not None or service.transport_factory is not None,
            '宿主尚未配置模型执行通道；工作意图未接受')
    identities = rules.apply(state, charter, 'start_work', intents.start_data(data), principal, request['id'])
    work = rules.records(state)['works'][data['work_id']]
    attempt = rules.start_attempt(state, data, principal, instance=service.app.instance)
    attempt['execution_owner'] = {'instance': service.app.instance, 'epoch': 1}
    plan = rules.step_plan(state, charter, work['id'], service.app.instance)
    require(set(tool['function']['name'] for tool in plan['tools']) == set(data['tools']),
            '该工作只能批准当前支持的只读资料工具')
    scope = approval_scope(service, cx, state, work)
    require(grant == scope['connection'], '无法确认当前模型服务授权；工作意图未接受')
    work['intent'] = {'id': request['id'], 'status': 'accepted', 'delivery_mode': data['delivery_mode'],
                      'authorized_principal_id': principal, 'attempt_id': attempt['id'],
                      'reason': '工作意图已持久接受，等待原执行推动', 'constraints': data['constraints'],
                      'checked_version': state['version'] + 1,
                      'approval': scope}
    state['schema_version'] = intents.SCHEMA
    return identities | {'intent_id': request['id'], 'attempt_id': attempt['id'],
                         'delivery_mode': data['delivery_mode'],
                         'message': '已接受有限工作意图和原执行尝试；模型执行与成果另行核对'}


def require_unmanaged(work):
    require('intent' not in work, '此工作由原持久意图管理；请使用意图入口或查看原执行')


def authorize(service, cx, accounts, state, work_id, approval):
    work = rules.records(state)['works'].get(work_id, {})
    intent = work.get('intent') or {}
    require(isinstance(approval, Approval) and approval.au_id == state['id'] and approval.work_id == work_id
            and approval.intent_id == intent.get('id') and approval.attempt_id == intent.get('attempt_id')
            and approval.principal == intent.get('authorized_principal_id'),
            '当前原工作批准不存在或作用域已变化')
    require(intent['status'] in ACTIONABLE, '原工作批准已关闭、待决定或需要重新核对')
    require(accounts.execute('SELECT 1 FROM owner_account WHERE principal_id=?', (approval.principal,)).fetchone(),
            '原批准的核心账户已失效；保留原执行与用量')
    rules.authorize(state, approval.principal)
    rules.effective(state, {row[0] for row in accounts.execute('SELECT principal_id FROM owner_account')})
    service.require_host()
    attempt = rules.active_attempt(work, service.app.instance)
    require(attempt['id'] == approval.attempt_id, '原执行尝试已变化')
    ownership.assert_owner(attempt, approval.owner)
    require(approval_scope(service, cx, state, work) == intent['approval'],
            '原工作资料、模型、章程、责任或资源版本已变化')
    require(compatible_since(cx, state, work),
            'AU 有原批准范围外的变化；只允许已验证的低影响输入')
    return approval.principal


def compatible_since(cx, state, work):
    # Only verify ongoing changes in other approved, independently reserved work.
    works = rules.records(state)['works']

    def independent(command):
        target = works.get(command['data'].get('work_id'))
        if target is None or target['id'] == work['id'] or 'intent' not in target:
            return False
        if command['kind'] == 'start_work_intent':
            return target['intent']['id'] == command['id']
        if command['kind'] in ('decide_work_intent', 'stop_work_intent'):
            return target['intent']['id'] == command['data'].get('intent_id')
        if command['kind'].startswith('work_dispatch_intent_'):
            return target['intent']['id'] == command['data'].get('command_id')
        return (command['kind'].startswith('work_dispatch_')
                and any(step.get('command_id') == command['data'].get('command_id')
                        and step.get('command_sha256') == command['data'].get('command_sha256')
                        for step in target.get('steps', [])))

    return dispatch.compatible_since(cx, state, work['intent']['checked_version'], allow_additional=independent)


def track_dispatch(cx, state, work, before):
    intent = work['intent']
    if intent['checked_version'] == before or compatible_since(cx, state, work):
        intent['checked_version'] = state['version']


def pending_steps(work):
    return [step for step in work.get('steps', []) if step['status'] in ('reserved', 'unknown')]


def set_status(intent, status, reason, *, decision=None):
    intent.update(status=status, reason=reason)
    if decision is None:
        intent.pop('decision', None)
    else:
        intent['decision'] = decision


def candidate_data(result):
    return {'result_id': result['id'], 'result_seq': result['seq'], 'sha256': result['sha256'],
            'input_cursor': result.get('input_cursor', 0)}


def candidate_step(work, result):
    last = work['steps'][-1]
    require(last['status'] == 'used' and last.get('dispatch_phase') == 'adopted'
            and result['attempt_id'] == last['attempt_id'] == work['intent']['attempt_id']
            and result['id'] == 'result-' + last['command_id'].replace('-', '')[:12],
            '原候选与最后采用的工作步进不一致')
    return last


def ready_candidate(work, result):
    require(work.get('results') and work['results'][-1] == result and result['status'] == 'candidate',
            '原候选成果已经变化')
    require(not pending_steps(work), '原模型请求仍未解决；保留预约')
    require(result.get('input_cursor', 0) == work.get('input_seq', 0)
            and not any(item['status'] != 'consumed' for item in work.get('inputs', [])),
            '该候选尚未覆盖全部原输入；不能交付')
    candidate_step(work, result)
    known = {item['step_ref'] for item in work.get('tool_calls', []) + work.get('steps', [])
             if item['attempt_id'] == result['attempt_id']}
    require(set(result['sources']) <= known, '原候选的依赖来源已变化')


def deliver(state, work, result, principal, reason, *, decision=None):
    ready_candidate(work, result)
    intent = work['intent']
    data = {'work_id': work['id'], 'result_id': result['id']}
    rules.adopt_result(state, data, principal)
    rules.finish_attempt(state, {'work_id': work['id'], 'attempt_id': intent['attempt_id'],
                                 'outcome': 'delivered', 'reason': reason})
    rules.deliver_work(state, data, principal)
    set_status(intent, 'delivered', '已交付原工作文本成果', decision=decision)


def candidate_produced(state, work_id, principal):
    work = rules.records(state)['works'][work_id]
    intent = work['intent']
    result = work['results'][-1]
    if result.get('input_cursor', 0) != work.get('input_seq', 0):
        set_status(intent, 'running', '原候选保留；有待纳入的后到输入')
    elif intent['delivery_mode'] == 'automatic_text':
        deliver(state, work, result, principal, '按原工作意图自动采用并交付有界文本成果')
    else:
        ready_candidate(work, result)
        set_status(intent, 'awaiting_decision', '原文本候选等待当前治理者决定',
                   decision=candidate_data(result) | {'authorized_principal_id': principal})


def matched_work(state, data):
    work = rules.records(state)['works'].get(data['work_id'], {})
    require((work.get('intent') or {}).get('id') == data['intent_id'], '原工作意图不存在或不属于此工作')
    return work


def decision_result(work, data):
    intent = work['intent']
    require(intent['status'] == 'awaiting_decision', '该意图当前没有可采用的原候选决定')
    require(all(intent['decision'][key] == data[key] for key in intents.CANDIDATE_FIELDS),
            '原候选、摘要或输入游标已变化')
    result = work['results'][-1]
    ready_candidate(work, result)
    return result


def command_grant(service, token, request, principal):
    # Resolve remote authority outside the writer locks and bind the checked scope.
    starting = request['kind'] == 'start_work_intent'
    directory, creation = service.app.governance.locate(request['organization_id'])
    with service.app.mutex, service.app.catalog() as accounts, service.store.transaction(directory) as cx:
        require(service.app.identity.principal_in(accounts, token) == principal, '登录主体已变化')
        state = CoreAUStore.read_in(cx, request['organization_id'], creation=creation)['au']
        previous = service.store.existing(cx, request, principal)
        if previous is not None:
            return previous, None
        rules.authorize(state, principal)
        try:
            intents.validate_input(request['kind'], request['data'])
            require(request['base_version'] == state['version'], 'AU 版本已变化')
            rules.effective(state, {row[0] for row in accounts.execute('SELECT principal_id FROM owner_account')})
            if starting:
                data = request['data']
                connection = rules.connection(state, data['connection_id'], data['expected_revision'])
            else:
                work = matched_work(state, request['data'])
                step = candidate_step(work, decision_result(work, request['data']))
                wire = WorkExecutionStore.load_request(cx, step)['wire_body']
        except (Rejected, KeyError, TypeError):
            return None, None
    if starting:
        try:
            models = service.app.models
            models.check_grant(models.backend(), request['organization_id'], connection)
            return None, connection_scope(connection)
        except (Rejected, OSError, ServiceError):
            return None, None
    identity = (step['model_request_id'], step.get('request_sha256'))
    if wire is None:  # Original controlled channels without a remote grant API.
        return None, identity
    try:
        channel = service.transport
        if channel is None and service.transport_factory is not None:
            channel = service.transport_factory(request['organization_id'], step['connection'])
        if channel is not None and channel.current_authorized(*identity) is True:
            return None, identity
    except Exception:
        pass
    return None, None


def decide(service, cx, state, data, principal, grant):
    work = matched_work(state, data)
    intent = work['intent']
    require(principal == intent['authorized_principal_id'], '只有该原候选的有效决定主体可以采用')
    require(approval_scope(service, cx, state, work) == intent['approval'],
            '原工作资料、模型、章程、责任或资源版本已变化')
    result = decision_result(work, data)
    step = candidate_step(work, result)
    require(grant == (step['model_request_id'], step.get('request_sha256')),
            '原模型请求的当前授权未确认，保留候选')
    WorkContextStore.load(cx, work, step['context_scope'])
    deliver(state, work, result, principal, data['reason'], decision=intent['decision'])
    return {key: data[key] for key in ('work_id', 'intent_id', 'result_id', 'result_seq', 'sha256', 'input_cursor')} | {
        'message': '当前治理者已采用并交付该原候选'}


def finish_stopped(state, work):
    if pending_steps(work) or work['status'] in rules.CLOSED:
        return
    intent = work['intent']
    rules.finish_attempt(state, {'work_id': work['id'], 'attempt_id': intent['attempt_id'],
                                 'outcome': 'stopped', 'reason': intent['reason']})
    work.update(status='stopped', version=work['version'] + 1)


def stop(state, data):
    work = matched_work(state, data)
    intent = work['intent']
    require(intent['status'] not in ('delivered', 'stopped'), '原工作意图已经终结')
    set_status(intent, 'stopped', '已关闭原工作批准；原请求及用量继续保留：' + data['reason'])
    for step in pending_steps(work):
        if step.get('dispatch_phase') == 'prepared' and step['status'] == 'reserved':
            dispatch.settle(step, 'refused', '原工作已停止，封存请求未越过派发边界')
    finish_stopped(state, work)
    return {'work_id': work['id'], 'intent_id': intent['id'], 'message': intent['reason']}


def note_input(work):
    intent = work.get('intent')
    if intent and intent['status'] == 'awaiting_decision':
        set_status(intent, 'running', '原候选保留；新增输入等待纳入后再形成决定')


def progress(service, cx, state, work, phase):
    intent = work['intent']
    if compatible_since(cx, state, work):
        intent['checked_version'] = state['version'] + 1
    charter = state.pop('charter')
    dispatch.event(service.store, cx, state, charter, {'id': intent['id'], 'kind': 'start_work_intent',
                   'data': {'work_id': work['id']}}, intent['authorized_principal_id'], 'intent_' + phase)


def pump(service, directory, creation, work_id):
    """Advance one original turn, or use U-092 GET/recovery for its unresolved request."""
    au_id = creation['allocated_au_id']
    with service.app.mutex, service.app.catalog() as accounts, service.store.transaction(directory) as cx:
        service.require_host()
        state = CoreAUStore.read_in(cx, au_id, creation=creation)['au']
        work = rules.records(state)['works'].get(work_id, {})
        intent = work.get('intent')
        if not intent or intent['status'] in ('delivered', 'awaiting_decision'):
            return 'idle'
        pending = pending_steps(work)
        require(len(pending) <= 1, '原工作有多个未决调用；须核对原记录')
        if intent['status'] in ('stopped', 'blocked') and not pending:
            if intent['status'] == 'stopped' and work['status'] not in rules.CLOSED:
                finish_stopped(state, work)
                progress(service, cx, state, work, 'stopped')
            return 'idle'
        attempt = work['attempts'][0]
        owner = ownership.owner(attempt)
        if owner['instance'] != service.app.instance:
            owner = ownership.claim(work, attempt['id'], service.app.instance, host_live=True)
            progress(service, cx, state, work, 'recovered')
            state = CoreAUStore.read_in(cx, au_id, creation=creation)['au']
            work = rules.records(state)['works'][work_id]
            intent = work['intent']
            pending = pending_steps(work)
        approval = Approval(au_id, work_id, intent['id'], attempt['id'], intent['authorized_principal_id'], owner)
        actionable = intent['status'] in ACTIONABLE
        if actionable:
            problem = None
            try:
                authorize(service, cx, accounts, state, work_id, approval)
            except Rejected as error:
                problem = str(error)
            latest = next(iter(reversed(work.get('steps', []))), {})
            if not pending and not problem:
                if latest.get('status') == 'released' or latest.get('model_outcome') == 'not_adoptable':
                    problem = latest['reason']
                elif rules.budget(work)['used'] >= work['max_calls']:
                    problem = '原工作调用预算已用完；保留候选和未纳入输入，不能交付'
            if problem:
                set_status(intent, 'blocked', problem)
                progress(service, cx, state, work, 'blocked')
                actionable = False
        if not actionable and (not pending or pending[0].get('dispatch_phase') == 'prepared'):
            return 'idle'
        if pending:
            if actionable and intent['status'] != 'waiting_unknown':
                set_status(intent, 'waiting_unknown',
                           '原模型请求待核对；保留预约，宿主重开或收存新输入时可再次查询原请求')
                progress(service, cx, state, work, 'waiting')
            request = None
        else:
            if intent['status'] != 'running':
                set_status(intent, 'running', '原执行正在按批准的工作边界推进')
                progress(service, cx, state, work, 'running')
            step_index = len(work.get('steps', [])) + 1
            command_id = uuid.uuid5(uuid.NAMESPACE_OID, f"work-intent:{au_id}:{intent['id']}:{step_index}").hex
            request = {'id': command_id, 'organization_id': au_id, 'base_version': state['version'],
                       'kind': 'run_step', 'data': {'work_id': work_id}}
    if request is None:
        from .work_recovery import resume
        receipt = resume(service, None, directory, creation, work_id, approval.attempt_id, approval.owner,
                         approval=approval)
        return 'again' if receipt and receipt.get('model_outcome') != 'unknown' else 'poll'
    try:
        receipt = service.run_step(None, request, approval=approval)
    except Rejected as error:
        block_failed_turn(service, directory, creation, approval, str(error))
    else:
        if receipt.get('status') == 'rejected':
            block_failed_turn(service, directory, creation, approval, receipt['message'])
    return 'again'


def block_failed_turn(service, directory, creation, approval, reason):
    with service.app.mutex, service.store.transaction(directory) as cx:
        if service.stopping:
            return
        state = CoreAUStore.read_in(cx, approval.au_id, creation=creation)['au']
        work = rules.records(state)['works'][approval.work_id]
        if work['intent']['status'] in ACTIONABLE and ownership.owner(work['attempts'][0]) == approval.owner:
            set_status(work['intent'], 'blocked', reason)
            progress(service, cx, state, work, 'blocked')


def drive(service, au_id, work_id, wakeup):
    key = (au_id, work_id)
    thread = threading.current_thread()
    try:
        directory, creation = service.app.governance.locate(au_id)
        polls = 0
        while not service.stopping:
            wakeup.clear()
            outcome = pump(service, directory, creation, work_id)
            if outcome == 'again':
                polls = 0
                continue
            if outcome == 'poll' and polls < 2:
                polls += 1
                if wakeup.wait(polls):
                    polls = 0
                continue
            with service.app.mutex:
                if wakeup.is_set():
                    polls = 0
                    continue
                service.intent_workers.pop(key, None)
                break
    except Rejected as error:
        if not service.stopping:
            LOG.warning('持久工作驱动暂时停止 (%s)', type(error).__name__)
    except Exception as error:
        LOG.warning('持久工作驱动保存失败 (%s)', type(error).__name__)
    finally:
        with service.app.mutex:
            if service.intent_workers.get(key) is wakeup:
                del service.intent_workers[key]
            service.app.jobs.remove(thread)


def wake(service, au_id, work_id):
    key = (au_id, work_id)
    with service.app.mutex:
        if service.stopping:
            return
        wakeup = service.intent_workers.get(key)
        if wakeup is not None:
            wakeup.set()
            return
        wakeup = threading.Event()
        thread = threading.Thread(target=drive, args=(service, au_id, work_id, wakeup), daemon=True,
                                  name='core-work-intent')
        service.intent_workers[key] = wakeup
        service.app.jobs.append(thread)
        try:
            thread.start()
        except RuntimeError:
            service.app.jobs.remove(thread)
            del service.intent_workers[key]
            LOG.warning('当前宿主无法唤醒持久工作；重开时可从原工作恢复')


def recover(service):
    for entry in service.app._catalog_entries():
        if entry['profile'] != 'core_v1':
            continue
        try:
            directory, creation = service.app.governance.locate(entry['id'])
            state = CoreAUStore().read(directory, entry['id'], creation=creation)['au']
        except (Rejected, OSError, sqlite3.Error) as error:
            LOG.warning('暂时无法核对一个 AU 的持久工作，保留原执行记录 (%s)', type(error).__name__)
            continue
        for work in rules.records(state)['works'].values():
            intent = work.get('intent')
            if intent and (intent['status'] in ACTIONABLE or pending_steps(work)):
                wake(service, entry['id'], work['id'])
