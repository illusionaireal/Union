"""Same-attempt recovery and one shared normal/recovery result adoption path."""
import copy
import sqlite3
from contextlib import closing, contextmanager

from ..adapters import documents
from ..adapters.core_au_store import CoreAUStore
from ..adapters.work_context_store import WorkContextStore
from ..adapters.work_execution_store import WorkExecutionStore
from ..domain import work as rules, work_recovery as ownership
from ..errors import CoreError, Rejected, require
from ..work_transport import UnadoptableWorkResult
from . import work_dispatch as dispatch


class WorkExecutionFenced(Rejected):
    """Local authority/fence denial is not a remote refusal or cancellation."""


def recovery_projection(service, state, projected, can_manage):
    work = rules.records(state)["works"][projected["id"]]
    host_live = not (service.stopping or service.app.stopping or service.app.closed)
    for attempt in projected["attempts"]:
        attempt["execution_owner"] = copy.deepcopy(ownership.owner(attempt))
        active = any(service.active_steps.get((state["id"], s.get("command_id")), 0)
                     for s in work.get("steps", []) if s["attempt_id"] == attempt["id"])
        active = active or (state["id"], work["id"], attempt["id"]) in service.active_recoveries
        active = active or any((state["id"], loop["command_id"]) in service.active_loops
                                  for loop in work.get("loops", []))
        continuable = any(s["attempt_id"] == attempt["id"] and s["status"] in ("reserved", "unknown")
                          and s.get("execution_sha256") for s in work.get("steps", []))
        continuable = continuable or any(loop.get("attempt_id") == attempt["id"] and loop.get("execution_sha256")
                                         for loop in work.get("loops", []))
        result = ownership.eligibility(attempt, service.app.instance, host_live=host_live,
                                       worker_active=active, continuable=continuable)
        if not can_manage:
            result = {"eligible": False, "reason": "仅当前有效治理者可接回原执行"}
        if result["eligible"]:
            try:
                local = copy.deepcopy(state)
                current_work = rules.records(local)["works"][work["id"]]
                next(a for a in current_work["attempts"] if a["id"] == attempt["id"])["execution_owner"] = {
                    "instance": service.app.instance, "epoch": attempt["execution_owner"]["epoch"] + 1}
                directory, _ = service.app.governance.locate(state["id"])
                with closing(sqlite3.connect((directory / "state.sqlite3").as_uri() + "?mode=ro", uri=True)) as cx:
                    cx.execute("PRAGMA query_only=ON")
                    cx.execute("BEGIN")
                    if ownership.owner(attempt)["instance"] == service.app.instance and not _continuable(service, cx, work, attempt["id"]):
                        result = ownership.eligibility(attempt, service.app.instance, host_live=host_live)
                    else:
                        validate_recovery_inputs(service, cx, local, state["charter"], current_work, attempt["id"])
            except (Rejected, OSError, sqlite3.Error) as error:
                result = {"eligible": False, "reason": str(error)}
        attempt["recovery"] = result


adopt_turn = dispatch.adopt_turn


def _continuable(service, cx, work, attempt_id):
    if any(s["attempt_id"] == attempt_id and s["status"] in ("reserved", "unknown")
           and s.get("execution_sha256") for s in work.get("steps", [])):
        return True
    for loop in work.get("loops", []):
        if loop.get("attempt_id") == attempt_id and loop.get("execution_sha256"):
            original = WorkExecutionStore.load_loop(cx, loop)
            previous = service.store.existing(cx, original, loop["principal_id"])
            if previous is None or previous.get("model_outcome") == "unknown":
                return True
    return False


def prepare_recovery(service, cx, state, charter, data, marker):
    work = rules.records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    attempt = next((a for a in work.get("attempts", []) if a["id"] == data["attempt_id"]), None)
    require(attempt is not None, "该工作没有此执行尝试")
    key = (state["id"], work["id"], attempt["id"])
    active = key in service.active_recoveries or any(
        service.active_steps.get((state["id"], s.get("command_id")), 0) for s in work.get("steps", [])) or any(
        (state["id"], loop["command_id"]) in service.active_loops for loop in work.get("loops", []))
    continuable = _continuable(service, cx, work, attempt["id"])
    result = ownership.eligibility(attempt, service.app.instance, host_live=True,
                                   worker_active=active, continuable=continuable)
    require(result["eligible"], result["reason"])
    current = ownership.owner(attempt)["instance"] == service.app.instance
    owner = copy.deepcopy(ownership.owner(attempt)) if current else ownership.claim(
        work, attempt["id"], service.app.instance, host_live=True)
    validate_recovery_inputs(service, cx, state, charter, work, attempt["id"])
    state["schema_version"] = max(state["schema_version"], 5)
    service.active_recoveries[key] = marker
    return {"execution_owner": owner, "attempt_id": attempt["id"], "work_id": work["id"],
            "message": result["reason"]}


def validate_recovery_inputs(service, cx, state, charter, work, attempt_id):
    pending = [s for s in work.get("steps", []) if s["attempt_id"] == attempt_id
               and s["status"] in ("reserved", "unknown") and s.get("command_id")]
    require(len(pending) <= 1, "原执行有多个未决模型请求；须核对原记录")
    plan = rules.step_plan(state, charter, work["id"], service.app.instance,
                           pending[0]["step_ref"] if pending else None)
    history, _, bindings = WorkContextStore.load(cx, work, plan["context_scope"])
    if any(m["role"] == "tool" for m in history):
        binding = documents.WorkDocuments(service.app.root, state, work, cx).binding
        require(bindings and all(item == binding for item in bindings), "资料授权或目录绑定已变化；原上下文不能恢复")
    if pending:
        step = pending[0]
        snapshot = WorkExecutionStore.load_request(cx, step)
        require(snapshot["wire_body"] is not None and step.get("request_sha256"),
                "原调用缺少精确模型输入摘要；仅可核对原请求，不能重派或采用")
        require(plan["context_scope"] == step["context_scope"] and plan["connection"] == step["connection"]
                and state["policy_version"] == step["policy_version"]
                and state["charter_version"] == step["charter_version"], "原调用的有效授权或执行版本已变化")
        service.verify_material_binding(snapshot["plan"], state)
        if step.get("observed_sha256"):
            WorkExecutionStore.load_observed(cx, step)
    for loop in work.get("loops", []):
        if loop.get("attempt_id") == attempt_id:
            WorkExecutionStore.load_loop(cx, loop)


def _state(service, cx, request, intent):
    return CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]


def _fence(service, state, work_id, expected_owner):
    try:
        service.require_host()
        work = rules.records(state)["works"][work_id]
        require(work.get("attempts"), "原执行尝试缺失")
        ownership.assert_owner(work["attempts"][-1], expected_owner)
    except Rejected as error:
        raise WorkExecutionFenced(str(error)) from error


def _authorize(service, cx, accounts, token, state, snapshot, step, expected_owner, *, approval=None):
    _fence(service, state, snapshot["request"]["data"]["work_id"], expected_owner)
    work_id = snapshot['request']['data']['work_id']
    if approval is not None:
        from . import work_intent
        principal = work_intent.authorize(service, cx, accounts, state, work_id, approval)
    else:
        principal = service.app.identity.principal_in(accounts, token)
    rules.authorize(state, principal)
    rules.effective(state, {r[0] for r in accounts.execute("SELECT principal_id FROM owner_account")})
    plan = snapshot["plan"]
    service.verify_material_binding(plan, state)
    current = rules.step_plan(state, state["charter"], plan["work_id"], service.app.instance, step["step_ref"])
    require(current["context_scope"] == step["context_scope"] and current["connection"] == step["connection"]
            and current["attempt_id"] == step["attempt_id"]
            and state["policy_version"] == step["policy_version"]
            and state["charter_version"] == step["charter_version"], "原调用的有效授权或执行版本已变化")
    # Verify retained assistant/tool snapshots; never reread changed document content.
    work = rules.records(state)["works"][plan["work_id"]]
    WorkContextStore.load(cx, work, plan["context_scope"])
    from .work_inputs import validate_attachment
    validate_attachment(cx, state, work, step, plan)
    return principal


@contextmanager
def post_guard(service, token, directory, intent, request, principal, expected_owner, *, approval=None):
    """Last dispatch admission; an admitted network operation holds no shared lock."""
    with service.app.mutex, service.app.catalog() as accounts:
        with service.store.transaction(directory) as cx:
            state = _state(service, cx, request, intent)
            step = dispatch.find(state, request, principal)
            snapshot = WorkExecutionStore.load_request(cx, step)
            try:
                _authorize(service, cx, accounts, token, state, snapshot, step, expected_owner, approval=approval)
            except Rejected as error:
                raise WorkExecutionFenced(str(error)) from error
            require(step["dispatch_phase"] == "dispatching", "原调用尚未持久提交派发边界")
    yield


def send_prepared(service, token, directory, intent, request, principal, expected_owner, transport, *, approval=None):
    """Only a proven prepared snapshot may make its original first POST."""
    with service.app.mutex, service.app.catalog() as accounts:
        with service.store.transaction(directory) as cx:
            state = _state(service, cx, request, intent)
            step = dispatch.find(state, request, principal)
            snapshot = WorkExecutionStore.load_request(cx, step)
            _authorize(service, cx, accounts, token, state, snapshot, step, expected_owner, approval=approval)
            require(step["dispatch_phase"] == "prepared", "原调用可能已经派发；只能查询原请求")
            state = copy.deepcopy(state)
            charter = state.pop("charter")
            step = dispatch.find(state, request, principal)
            step["dispatch_phase"] = "dispatching"
            dispatch.event(service.store, cx, state, charter, request, principal, "dispatching")
    plan = snapshot["plan"]
    if snapshot["wire_body"] is not None:
        require(hasattr(transport, "chat_body"), "宿主通道不能发送原 wire 快照")
        return transport.chat_body(snapshot["wire_body"], post_guard=lambda: post_guard(
            service, token, directory, intent, request, principal, expected_owner, approval=approval))
    # Legacy/custom channels retain their original chat contract. Modeld always
    # uses chat_body, with the exact saved body and a fence around the actual POST.
    with post_guard(service, token, directory, intent, request, principal, expected_owner, approval=approval):
        pass
    return transport.chat(copy.deepcopy(plan["package"]), copy.deepcopy(plan["messages"]),
                          copy.deepcopy(plan["tools"]))


def observe(service, directory, intent, request, principal, message, usage, *, action_authorized=True):
    """Completed remote facts survive loss of local owner/authority before adoption."""
    with service.app.mutex, service.store.transaction(directory) as cx:
        state = _state(service, cx, request, intent)
        step = dispatch.find(state, request, principal)
        require(step is not None, "缺少原调用预约")
        WorkExecutionStore.load_request(cx, step)
        if step.get("observed_sha256"):
            WorkExecutionStore.save_observed(cx, step, message, usage, action_authorized=action_authorized)
            return
        state = copy.deepcopy(state)
        charter = state.pop("charter")
        step = dispatch.find(state, request, principal)
        WorkExecutionStore.save_observed(cx, step, message, usage, action_authorized=action_authorized)
        from .work_inputs import observe as observe_inputs
        observe_inputs(state, step)
        step.update(dispatch_phase="observed", adoption_pending=step["status"] in ("reserved", "unknown"),
                    usage={k: usage[k] for k in ("input_tokens", "output_tokens")
                           if isinstance(usage, dict) and type(usage.get(k)) is int and usage[k] >= 0})
        dispatch.event(service.store, cx, state, charter, request, principal, "observed_complete")


def adopt_observed(service, token, directory, intent, request, principal, expected_owner, *, approval=None):
    with service.app.mutex, service.store.transaction(directory) as cx:
        initial = _state(service, cx, request, intent)
        original = dispatch.find(initial, request, principal)
        previous = service.store.existing(cx, request, principal)
        if original["status"] not in ("reserved", "unknown"):
            return previous or dispatch.pending(request, principal, initial, original)
        try:
            _fence(service, initial, request["data"]["work_id"], expected_owner)
        except WorkExecutionFenced:
            return dispatch.pending(request, principal, initial, original)
        sealed = WorkExecutionStore.load_request(cx, original)
    remote_authorized = True
    if sealed["wire_body"] is not None:
        try:
            channel = service.transport
            if channel is None and service.transport_factory is not None:
                channel = service.transport_factory(request["organization_id"], original["connection"])
            require(channel is not None and hasattr(channel, "current_authorized"),
                    "宿主模型通道不能核对原请求的当前授权；保留完整观察与预约")
            remote_authorized = channel.current_authorized(original["model_request_id"], original["request_sha256"])
            require(type(remote_authorized) is bool, "模型通道未明确原请求的当前行动授权")
        except Exception:
            return dispatch.pending(request, principal, initial, original)
    with service.app.mutex, service.app.catalog() as accounts:
        with service.store.transaction(directory) as cx:
            state = _state(service, cx, request, intent)
            step = dispatch.find(state, request, principal)
            previous = service.store.existing(cx, request, principal)
            if step["status"] not in ("reserved", "unknown"):
                return previous or dispatch.pending(request, principal, state, step)
            try:
                _fence(service, state, request["data"]["work_id"], expected_owner)
            except Rejected:
                # Fencing does not discard a known completion or settle somebody
                # else's step. The current owner can adopt its saved fact later.
                return dispatch.pending(request, principal, state, step)
            snapshot = WorkExecutionStore.load_request(cx, step)
            observed = WorkExecutionStore.load_observed(cx, step)
            state = copy.deepcopy(state)
            charter = state.pop("charter")
            receipt = dispatch.receipt(request, principal, state["version"],
                                       message="已执行一次自动模型步进")
            cx.execute("SAVEPOINT work_step")
            try:
                actor = _authorize(service, cx, accounts, token, state | {"charter": charter},
                                   snapshot, step, expected_owner, approval=approval)
                require(observed["action_authorized"] is True and remote_authorized,
                        "原模型调用已完成，但当前模型授权失效")
                local = copy.deepcopy(state)
                original = dispatch.find(local, request, principal)
                original["status"] = "reserved"  # Confirmed original unknown, same reservation.
                receipt.update(adopt_turn(service, cx, local, charter, request, actor, snapshot["plan"],
                                          original, observed["message"], observed["usage"], expected_owner))
                original.update(dispatch_phase="adopted", adoption_pending=False)
                if approval is not None and receipt['result']:
                    from .work_intent import candidate_produced
                    candidate_produced(local, request['data']['work_id'], actor)
                state = local
            except (Rejected, CoreError) as error:
                cx.execute("ROLLBACK TO work_step")
                original = dispatch.find(state, request, principal)
                try:
                    _fence(service, state, request["data"]["work_id"], expected_owner)
                except WorkExecutionFenced:
                    cx.execute("RELEASE work_step")
                    return dispatch.pending(request, principal, state, original)
                dispatch.settle(original, "not_adoptable", str(error), observed["usage"])
                original.update(dispatch_phase="observed", adoption_pending=False)
                receipt.update(status="rejected", effect="evidence_only", model_outcome="not_adoptable",
                    message="调用已完成但结果不能采用：" + str(error), usage=original["usage"],
                    step=original["step_ref"], model_request_id=original["model_request_id"],
                    tool_calls=0, result=False, cost_status="unknown")
            cx.execute("RELEASE work_step")
            dispatch.event(service.store, cx, state, charter, request, principal, "adopted")
            receipt["version"] = state["version"]
            if previous is None:
                service.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=False)
            return receipt


def resume(service, token, directory, intent, work_id, attempt_id, expected_owner, *, approval=None):
    """Resume an original reserved request, never create a replacement attempt."""
    with service.app.mutex, service.store.transaction(directory) as cx:
        state = CoreAUStore.read_in(cx, intent["allocated_au_id"], creation=intent)["au"]
        _fence(service, state, work_id, expected_owner)
        work = rules.records(state)["works"][work_id]
        pending = [s for s in work.get("steps", []) if s["attempt_id"] == attempt_id
                   and s["status"] in ("reserved", "unknown") and s.get("command_id")]
        if not pending:
            step = None
        else:
            require(len(pending) == 1, "原执行有多个未决模型请求；须核对原记录")
            step = copy.deepcopy(pending[0])
            snapshot = WorkExecutionStore.load_request(cx, step)
    if step is None:
        return (resume_loop(service, token, directory, intent, work_id, attempt_id, expected_owner)
                if approval is None else None)
    request = snapshot["request"]
    principal = step["principal_id"]
    if step.get("observed_sha256"):
        adopted = adopt_observed(service, token, directory, intent, request, principal, expected_owner, approval=approval)
        if approval is not None:
            return adopted
        return resume_loop(service, token, directory, intent, work_id, attempt_id, expected_owner)
    try:
        channel = service.transport
        if channel is None and service.transport_factory is not None:
            channel = service.transport_factory(request["organization_id"], step["connection"])
        require(channel is not None, "宿主尚未配置原模型通道；保留原请求预约")
        if step.get("dispatch_phase") == "prepared" and step["status"] == "reserved":
            require(snapshot["wire_body"] is not None, "原调用缺少精确 wire 快照；不能重派")
            message, usage = send_prepared(service, token, directory, intent, request, principal, expected_owner,
                                           channel, approval=approval)
            result = {"message": message, "usage": usage, "action_authorized": True}
        else:
            require(step.get("request_sha256") and hasattr(channel, "lookup_result"),
                    "原调用缺少输入摘要或完整查询能力；保留预约，仅核对原请求")
            result = channel.lookup_result(step["model_request_id"], step["request_sha256"])
        if result is None:
            return
        observe(service, directory, intent, request, principal, result["message"], result["usage"],
                action_authorized=result["action_authorized"])
        adopted = adopt_observed(service, token, directory, intent, request, principal, expected_owner, approval=approval)
        if approval is not None:
            return adopted
        return resume_loop(service, token, directory, intent, work_id, attempt_id, expected_owner)
    except UnadoptableWorkResult as error:
        if error.observed_message is not None:
            observe(service, directory, intent, request, principal, error.observed_message, error.observed_usage,
                    action_authorized=False)
            return adopt_observed(service, token, directory, intent, request, principal, expected_owner, approval=approval)
        return service.record_channel_outcome(directory, intent, request, principal, str(error), completed=error,
                                              expected_owner=expected_owner)
    except Exception:
        # Missing, tampered, denied or lost lookup is not proof of absent execution.
        # Current owner remains responsible and the original reservation survives.
        return None


def recovered_turn(service, directory, intent, request, expected_owner, loop):
    """Current adopted facts advance an original loop; issuer receipts stay immutable."""
    with service.app.mutex, service.store.transaction(directory) as cx:
        state = _state(service, cx, request, intent)
        _fence(service, state, request["data"]["work_id"], expected_owner)
        work = rules.records(state)["works"][request["data"]["work_id"]]
        step = next((s for s in work.get("steps", []) if s.get("command_id") == request["id"]), None)
        if step is None:
            request["base_version"] = state["version"]
            return None
        snapshot = dispatch.child_snapshot(cx, step, request, loop)
        request.clear()
        request.update(snapshot["request"])
        if step["status"] != "used" or step.get("dispatch_phase") != "adopted":
            return dispatch.pending(request, step["principal_id"], state, step)
        WorkContextStore.load(cx, work, step["context_scope"])
        result_id = "result-" + request["id"].replace("-", "")[:12]
        private = WorkExecutionStore.load_observed(cx, step)
        assistant, calls = service.model_turn(private["message"], snapshot["plan"])
        return dispatch.receipt(request, step["principal_id"], state["version"],
            step=step["step_ref"], tool_calls=len(calls),
            result=bool(assistant['content'] and not calls and any(r['id'] == result_id for r in work.get('results', []))),
            usage=step.get("usage", {}),
            message="原循环已采用的原步进事实", cost_status="unknown")


def resume_loop(service, token, directory, intent, work_id, attempt_id, expected_owner):
    with service.app.mutex, service.store.transaction(directory) as cx:
        state = CoreAUStore.read_in(cx, intent["allocated_au_id"], creation=intent)["au"]
        _fence(service, state, work_id, expected_owner)
        work = rules.records(state)["works"][work_id]
        if any(s["status"] in ("reserved", "unknown") for s in work.get("steps", []) if s["attempt_id"] == attempt_id):
            return
        loops = [item for item in work.get("loops", []) if item.get("attempt_id") == attempt_id]
        if not loops:
            return
        loop = loops[-1]
        request = WorkExecutionStore.load_loop(cx, loop)
        previous = service.store.existing(cx, request, loop["principal_id"])
        if previous is not None and previous.get("model_outcome") != "unknown":
            return
        key = (state["id"], loop["command_id"])
        require(key not in service.active_loops, "当前宿主原循环仍在执行；不能启动副本")
        service.active_loops.add(key)
    try:
        return service.drive_loop(token, request, loop["principal_id"], directory, intent, loop,
                                  recovery_owner=expected_owner)
    finally:
        with service.app.mutex:
            service.active_loops.discard(key)
