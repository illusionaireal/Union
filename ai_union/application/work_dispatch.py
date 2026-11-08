"""Internal dispatch facts, committed through the existing GovernanceStore owner."""
import copy
import hashlib
import uuid

from ..adapters.core_au_store import encoded
from ..domain import work as rules
from ..engine import now
from ..errors import CoreError, require


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
    state["schema_version"] = 4
    state["version"] += 1
    request = {"id": "dispatch-" + str(uuid.uuid4()), "organization_id": state["id"],
               "base_version": before, "kind": "work_dispatch_" + phase,
               "data": {"command_id": original["id"], "command_sha256": request_digest(original)}}
    store.ensure_commands(cx)
    store.save(cx, state, charter, request, receipt(request, principal, state["version"]),
               state["policy_version"], changed=True)


def prepare(store, cx, state, request, principal, plan, instance):
    state = copy.deepcopy(state)
    charter = state.pop("charter")
    step = rules.reserve_step(state, request["data"], instance=instance)
    step.update(command_id=request["id"], command_sha256=request_digest(request), principal_id=principal,
                model_request_id=request_id(request), context_scope=copy.deepcopy(plan["context_scope"]),
                connection=copy.deepcopy(plan["connection"]), policy_version=state["policy_version"],
                charter_version=state["charter_version"], host_instance=instance, cost_status="unknown")
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
