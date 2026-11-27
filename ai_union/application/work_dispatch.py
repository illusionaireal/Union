"""Internal dispatch facts, committed through the existing GovernanceStore owner."""
import copy
import hashlib
import uuid

from ..adapters import documents
from ..adapters.core_au_store import encoded
from ..adapters.work_context_store import WorkContextStore
from ..adapters.governance_store import commands_in
from ..domain import work_recovery as ownership
from ..domain import work as rules
from ..engine import now
from ..errors import CoreError, Rejected, require


def request_digest(request):
    return hashlib.sha256(encoded(request).encode("utf-8")).hexdigest()


def request_id(request):
    return "work-" + hashlib.sha256(encoded([request["organization_id"], request["id"]]).encode()).hexdigest()


def find(state, request, principal):
    for work in rules.records(state)["works"].values():
        for step in work.get("steps", []):
            if step.get("command_id") != request["id"]:
                continue
            if step["principal_id"] != principal:
                raise CoreError("not_authorized")
            if step["command_sha256"] != request_digest(request):
                raise CoreError("id_conflict", "请求标识已用于不同参数；请查询原回执")
            return step
    return None


def receipt(request, principal, version, **details):
    return {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
        "actor_principal_id": principal, "created_at": now(), "status": "succeeded",
        "effect": "applied", "version": version, **details}


def pending(request, principal, state, step):
    return receipt(request, principal, state["version"], model_outcome="unknown", step=step["step_ref"],
                   model_request_id=step["model_request_id"], tool_calls=0, result=False,
                   message="原模型请求待核对；保留预约，不重新派发", cost_status="unknown")


def event(store, cx, state, charter, original, principal, phase):
    """An internal event uses the current version; the public receipt stays immutable."""
    before = state["version"]
    # Old schema-3 code can manually release automatic reservations. Mark the
    # required semantics in the same commit as the first dispatch/loop intent.
    state["schema_version"] = max(state["schema_version"], 4)
    state["version"] += 1
    request = {"id": "dispatch-" + str(uuid.uuid4()), "organization_id": state["id"],
               "base_version": before, "kind": "work_dispatch_" + phase,
               "data": {"command_id": original["id"], "command_sha256": request_digest(original)}}
    store.ensure_commands(cx)
    store.save(cx, state, charter, request, receipt(request, principal, state["version"]),
               state["policy_version"], changed=True)


def complete_plan(service, cx, state, request):
    """Build the whole next-turn snapshot from one current reservation boundary."""
    plan = rules.step_plan(state, state['charter'], request['data']['work_id'], instance=service.app.instance)
    work = rules.records(state)['works'][plan['work_id']]
    history, plan['sources'], bindings = WorkContextStore.load(cx, work, plan['context_scope'])
    plan['materials_binding'] = None
    if plan['materials_root'] is not None:
        try:
            source = documents.WorkDocuments(service.app.root, state, work, cx)
            plan['materials_binding'] = source.binding
        except Rejected:
            if 'material_version' in work:
                raise
    if any(item['role'] == 'tool' for item in history):
        source = documents.WorkDocuments(service.app.root, state, work, cx)
        require(bindings and all(item == source.binding for item in bindings),
                '宿主资料目录绑定已变化；原上下文不可继续派发')
    plan['messages'].extend(history)
    from .work_inputs import select
    select(cx, state, work, plan)
    return plan


def next_request(service, cx, state, request, principal, loop):
    """Only a trusted original loop may create its next child at the current version."""
    from ..adapters.work_execution_store import WorkExecutionStore
    work = rules.records(state)['works'].get(request['data']['work_id'])
    require(work is not None, '原循环工作不存在')
    original_loop = next((value for value in work.get('loops', []) if value['command_id'] == loop['command_id']), None)
    require(original_loop is not None and original_loop == loop, '原循环意图已变化')
    if not loop.get('bind_children'):
        # Older loops use their original strict child version and digest.
        return request
    original = WorkExecutionStore.load_loop(cx, original_loop)
    require(request['kind'] == 'run_step' and original['organization_id'] == request['organization_id']
            and original['data'] == request['data']
            and original_loop['principal_id'] == principal
            and request['id'] in [original['id'] + '-t' + str(index + 1) for index in range(loop['turn_cap'])],
            '原循环下一步身份不匹配')
    commands = commands_in(cx, state['id'])
    saved = commands.get(request['id'])
    step = next((value for value in work.get('steps', []) if value.get('command_id') == request['id']), None)
    if step is not None:
        frozen = child_snapshot(cx, step, request, loop)['request']
        if saved is not None and (saved['principal_id'] != principal or saved['request'] != frozen):
            raise LoopChildConflict('原循环子命令回执与预约不一致')
        return frozen
    if saved is not None:
        if saved['principal_id'] == principal and saved['request'] == request and saved['value']['status'] == 'rejected':
            return request
        raise LoopChildConflict('原循环子命令标识已被其他请求占用')
    attempt = rules.active_attempt(work, service.app.instance)
    require(attempt['id'] == loop.get('attempt_id'), '原循环执行归属已变化')
    for row in cx.execute('SELECT command_id,kind FROM governance_events WHERE version>? ORDER BY version',
                          (request['base_version'],)):
        command = commands.get(row[0])
        require(row[1] == 'append_work_input' and command is not None
                and command['request']['kind'] == 'append_work_input' and command['value']['status'] == 'succeeded',
                'AU 版本已变化；原循环仅能接续低影响输入收存，须核对其他变化')
    result = copy.deepcopy(request)
    result['base_version'] = state['version']
    return result


class LoopChildConflict(Rejected):
    """A stored command shares a child ID without belonging to the parent loop."""


def child_snapshot(cx, step, request, loop):
    from ..adapters.work_execution_store import WorkExecutionStore
    if loop.get('bind_children') and (step.get('loop_command_id') != loop['command_id']
            or step['attempt_id'] != loop.get('attempt_id') or step['principal_id'] != loop['principal_id']):
        raise LoopChildConflict('原循环子命令标识已被其他执行占用')
    snapshot = WorkExecutionStore.load_request(cx, step)
    frozen = snapshot['request']
    if loop.get('bind_children') and snapshot['plan'].get('loop_command_id') != loop['command_id']:
        raise LoopChildConflict('原循环子命令与封存快照的父循环不一致')
    if any(frozen[key] != request[key] for key in ('id', 'kind', 'organization_id', 'data')):
        raise LoopChildConflict('原循环子命令作用域与预约不一致')
    return snapshot


def prepare(store, cx, state, request, principal, plan, instance, transport=None, *, loop=None):
    state = copy.deepcopy(state)
    charter = state.pop("charter")
    step = rules.reserve_step(state, request["data"], instance=instance)
    attempt = rules.active_attempt(rules.records(state)["works"][plan["work_id"]], instance)
    if attempt.get("execution_owner") is None:
        attempt["execution_owner"] = {"instance": instance, "epoch": 1}
    plan["execution_owner"] = copy.deepcopy(attempt["execution_owner"])
    step.update(command_id=request["id"], command_sha256=request_digest(request), principal_id=principal,
                model_request_id=request_id(request), context_scope=copy.deepcopy(plan["context_scope"]),
                connection=copy.deepcopy(plan["connection"]), policy_version=state["policy_version"],
                charter_version=state["charter_version"], host_instance=instance, cost_status="unknown")
    plan["package"]["run_id"] = step["model_request_id"]
    if loop and loop.get('bind_children'):
        step['loop_command_id'] = loop['command_id']
        plan['loop_command_id'] = loop['command_id']
    from ..adapters.work_execution_store import WorkExecutionStore
    from .work_inputs import fit_request
    wire_body = fit_request(plan, step, request, transport)
    WorkExecutionStore.save_request(cx, step, request, plan, wire_body)
    from .work_inputs import attach
    attach(state, plan, step)
    step.update(dispatch_phase="prepared", adoption_pending=False)
    state["schema_version"] = max(state["schema_version"], 5)
    event(store, cx, state, charter, request, principal, "prepared")
    return copy.deepcopy(step)


def settle(step, outcome, message, usage=None):
    require(step["status"] in ("reserved", "unknown"), "原调用已结算，不能重写")
    step.update(status={"completed": "used", "not_adoptable": "used", "refused": "released",
                        "unknown": "unknown"}[outcome], model_outcome=outcome,
                reason=message, settled_at=now(), cost_status="unknown")
    if usage is not None:
        step["usage"] = {key: usage[key] for key in ("input_tokens", "output_tokens")
                         if type(usage.get(key)) is int and usage[key] >= 0}


def adopt_turn(service, cx, local, charter, request, principal, plan, reservation, message, usage, expected_owner):
    """Original step/tool/context writer, shared by normal and recovered observations."""
    receipt = {}
    work = rules.records(local)["works"][request["data"]["work_id"]]
    current_plan = rules.step_plan(local, charter, work["id"], instance=service.app.instance,
                                   reserved_step=reservation["step_ref"])
    require(current_plan["context_scope"] == reservation["context_scope"]
            and current_plan["connection"] == reservation["connection"]
            and current_plan["attempt_id"] == reservation["attempt_id"]
            and local["policy_version"] == reservation["policy_version"]
            and local["charter_version"] == reservation["charter_version"], "原调用的有效授权或执行版本已变化")
    from .work_inputs import validate_attachment, consume
    validate_attachment(cx, local, work, reservation, plan)
    assistant, parsed_calls = service.model_turn(message, current_plan)
    require(len(work.get("tool_calls") or []) + len(parsed_calls) <= rules.MAX_TOOL_CALLS,
            "该工作的工具调用回执已达上限")
    content = assistant["content"] or ""
    executed = []
    outputs = []
    for call, arguments in parsed_calls:
        name = call["function"]["name"]
        service.require_host()
        ownership.assert_owner(rules.active_attempt(work, service.app.instance), expected_owner)
        rules.tool_target(local, {"work_id": work["id"], "tool": name}, service.app.instance)
        if name == "list_documents":
            source = documents.WorkDocuments(service.app.root, local, work, cx)
            listed = source.list()
            executed.append({"tool": name, "arguments": {},
                             "count": len(listed)} | source.provenance())
            outputs.append({"documents": listed, "count": len(listed)})
        elif name == "read_document":
            source = documents.WorkDocuments(service.app.root, local, work, cx)
            text, digest, size = source.read(arguments.get("path"))
            executed.append({"tool": name, "arguments": {"path": arguments.get("path")},
                             "sha256": digest, "bytes": size} | source.provenance())
            outputs.append({"path": arguments["path"], "content": text, "sha256": digest, "bytes": size})
        else:
            raise Rejected("模型请求了本核心不支持的只读工具")
    payload = {"work_id": request["data"]["work_id"], "content": "" if parsed_calls else content,
               "tool_calls": executed, "sources": plan["sources"],
               "result_id": "result-" + request["id"].replace("-", "")[:12],
               "title": "自动成果：" + work["title"], "usage": usage if isinstance(usage, dict) else {},
               "step_id": reservation["step_ref"]}
    service.require_host()
    ownership.assert_owner(rules.active_attempt(work, service.app.instance), expected_owner)
    receipt.update(rules.apply_step(local, charter, payload, principal, service.app.instance))
    turn_messages = copy.deepcopy(plan.get('input_messages', [])) + [assistant]
    new_receipts = work.get("tool_calls", [])[-len(outputs):] if outputs else []
    for (call, _), output, tool_receipt in zip(parsed_calls, outputs, new_receipts):
        turn_messages.append({"role": "tool", "name": call["function"]["name"],
                              "tool_call_id": call["id"],
                              "content": encoded(output | {"step_ref": tool_receipt["step_ref"]})})
    original = find(local, request, reservation["principal_id"])
    WorkContextStore.save(cx, original, current_plan["context_scope"], turn_messages,
                          [item["step_ref"] for item in new_receipts],
                          source.binding if outputs else None)
    service.require_host()
    ownership.assert_owner(rules.active_attempt(work, service.app.instance), expected_owner)
    WorkContextStore.load(cx, work, current_plan["context_scope"], prefix=current_plan['messages'])
    consume(local, work, original, expected_owner, work['results'][-1] if receipt['result'] else None)
    return receipt
