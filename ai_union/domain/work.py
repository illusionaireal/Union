"""V1 work responsibility rules: who answers for a goal and under which authority.

Pure rules only. No transport, storage, model or host access; the governance
store remains the single writer of AU facts.
"""
import hashlib
import time

from . import governance, model_profiles
from .creation import text
from ..errors import CoreError, Rejected, require

PROTOCOL = "core.work.v1"
FIELDS = {
    "start_work": {"work_id", "title", "member_name", "goal", "member_id", "binding_id", "mandate_id",
                   "definition_id", "connection_id", "expected_revision", "materials_root", "max_calls",
                   "tools", "reason"},
    "invoke_tool": {"work_id", "tool", "arguments"},
    "start_attempt": {"work_id"},
    "reserve_step": {"work_id"},
    "settle_step": {"work_id", "step_id", "status", "reason"},
    "submit_result": {"work_id", "result_id", "title", "content", "sources"},
    "adopt_result": {"work_id", "result_id"},
    "deliver_work": {"work_id", "result_id"},
    "run_step": {"work_id"},
    "run_loop": {"work_id"},
    "reconcile_step": {"work_id", "step_id", "status", "reason"},
    "finish_attempt": {"work_id", "attempt_id", "outcome", "reason"},
}
TOOLS = {"read_document", "list_documents", "produce_artifact"}
MAX_TOOL_CALLS = 50
MAX_ATTEMPTS = 20
OUTCOMES = ("delivered", "failed", "stopped", "unknown")
STEP_STATUSES = ("reserved", "used", "released", "unknown")
SETTLED = ("used", "released", "unknown")
OPEN = ("pending", "running", "waiting")
CLOSED = ("delivered", "stopped", "failed")
TABLES = ("members", "definitions", "bindings", "works", "mandates")


def empty():
    return {table: {} for table in TABLES}


def reference(value):
    """A bounded opaque reference. Host paths and traversal never qualify."""
    return (isinstance(value, str) and 1 <= len(value) <= 64 and value[0].isalnum()
            and all(character.isalnum() or character in "-_" for character in value))


def records(state):
    value = state.get("work_runtime")
    return empty() if value is None else value


def validate_input(kind, data):
    require(kind in FIELDS, "不支持的核心工作命令")
    governance.exact(data, FIELDS[kind])
    if kind == "submit_result":
        require(reference(data["work_id"]) and reference(data["result_id"]), "工作与成果标识必须是 bounded 引用标识")
        text(data["title"], "成果标题", 200)
        text(data["content"], "成果正文", 32768)
        require(isinstance(data["sources"], list) and len(data["sources"]) <= 20
                and all(isinstance(item, str) and len(item) <= 100 for item in data["sources"]),
                "成果来源必须是明确的执行或工具回执引用列表")
        return
    if kind == "reconcile_step":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        require(isinstance(data["step_id"], str) and data["step_id"].startswith(data["work_id"] + "#s")
                and len(data["step_id"]) <= 100, "步进标识无效")
        require(data["status"] in ("used", "released", "failed"), "核对结果必须是 used/released/failed")
        text(data["reason"], "核对依据", 10000)
        return
    if kind == "run_loop":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        return
    if kind == "run_step":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        return
    if kind == "deliver_work":
        require(reference(data["work_id"]) and reference(data["result_id"]), "工作与成果标识必须是 bounded 引用标识")
        return
    if kind == "adopt_result":
        require(reference(data["work_id"]) and reference(data["result_id"]), "工作与成果标识必须是 bounded 引用标识")
        return
    if kind == "reserve_step":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        return
    if kind == "settle_step":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        require(isinstance(data["step_id"], str) and data["step_id"].startswith(data["work_id"] + "#s")
                and len(data["step_id"]) <= 100, "步进标识无效")
        require(data["status"] in SETTLED, "结算结果必须是 used/released/unknown")
        text(data["reason"], "结算依据", 10000)
        return
    if kind == "start_attempt":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        return
    if kind == "finish_attempt":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        require(isinstance(data["attempt_id"], str) and data["attempt_id"].startswith(data["work_id"] + "#a")
                and len(data["attempt_id"]) <= 100, "执行尝试标识无效")
        require(data["outcome"] in OUTCOMES, "执行结果类别必须是 delivered/failed/stopped/unknown")
        text(data["reason"], "结束依据", 10000)
        return
    if kind == "invoke_tool":
        require(reference(data["work_id"]), "工作标识必须是 bounded 引用标识")
        require(isinstance(data["tool"], str) and data["tool"] in TOOLS, "工具不在本核心版本支持的范围")
        require(isinstance(data["arguments"], dict), "工具参数必须是明确的对象")
        if data["tool"] == "read_document":
            governance.exact(data["arguments"], {"path"})
            require(isinstance(data["arguments"]["path"], str) and data["arguments"]["path"],
                    "读取授权资料必须提供目录内相对路径")
        else:
            governance.exact(data["arguments"], set())
        return
    for field in ("work_id", "member_id", "binding_id", "mandate_id", "definition_id", "connection_id"):
        require(reference(data[field]), "工作标识必须是 bounded 引用标识")
    text(data["title"], "工作标题", 200)
    text(data["member_name"], "成员名称", 200)
    text(data["goal"], "工作目标", 100000)
    text(data["reason"], "建立依据", 10000)
    require(data["materials_root"] is None or isinstance(data["materials_root"], str) and len(data["materials_root"]) <= 200,
            "资料目录引用必须是文本或空")
    require(type(data["expected_revision"]) is int and data["expected_revision"] >= 1, "须提供当前模型连接版本")
    require(type(data["max_calls"]) is int and 1 <= data["max_calls"] <= 10000, "须提供有限正整数调用上限")
    require(isinstance(data["tools"], list) and data["tools"] and len(data["tools"]) == len(set(data["tools"]))
            and all(isinstance(item, str) for item in data["tools"]), "工具范围必须是明确的去重列表")


def authorize(state, principal):
    if principal != governance.current(state):
        raise CoreError("not_authorized")


def effective(state, principals, clock=None):
    """A work that needs execution requires a live, active governing procedure."""
    require(state["schema_version"] in (2, 3), "须先采用并激活本地治理，才能建立需要执行的 AI 工作")
    require(governance.effective_status(state, time.time() if clock is None else clock) == "active",
            "治理尚未激活、已到期或已经退出，不能建立需要执行的 AI 工作")
    governance.validate_live_targets(state, principals)


def connection(state, connection_id, revision):
    models = state.get("model_access") or {}
    value = (models.get("connections") or {}).get(connection_id)
    require(value is not None, "模型连接不属于此 AU 或尚未保存成功")
    require(value["revision"] == revision, "模型连接版本已变化；请检查当前配置")
    require(value["enabled"], "模型连接已停用；不能据此建立工作")
    require(models.get("default_connection_id") == connection_id, "须先采用当前模型连接为默认连接")
    return value


def reserved(records_value):
    return sum(value["max_calls"] for value in records_value["works"].values() if value["status"] in OPEN)


def apply(state, charter, kind, data, principal, request_id, clock=None):
    require(kind == "start_work", "不支持的核心工作命令")
    records_value = state.setdefault("work_runtime", empty())
    require(records_value == {table: records_value.get(table, {}) for table in TABLES}, "工作记录字段不完整")
    require("create_work" in charter["allowed_operations"], "当前有效章程未允许建立工作")
    require(set(data["tools"]) <= set(charter["allowed_tools"]), "工具不在当前有效章程允许的范围内")
    require(set(data["tools"]) <= TOOLS, "工具不在本核心版本支持的范围")
    require(data["materials_root"] is None or reference(data["materials_root"]),
            "资料目录须引用宿主已登记的标识，不接受路径或范围外引用")
    require(data["materials_root"] is not None or "read_document" not in data["tools"],
            "使用只读资料工具必须先指定宿主已登记的资料目录引用")
    model = connection(state, data["connection_id"], data["expected_revision"])
    for table in TABLES:
        require(data[{"members": "member_id", "definitions": "definition_id", "bindings": "binding_id",
                      "works": "work_id", "mandates": "mandate_id"}[table]] not in records_value[table],
                "工作、成员、责任绑定或授权标识已存在；请查询原回执")
    require(reserved(records_value) + data["max_calls"] <= state["resources"]["max_calls"],
            "工作调用上限超过此 AU 剩余可用次数；需要调整计划或先完成其他工作")
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if clock is None else clock))
    definitions, members, bindings = records_value["definitions"], records_value["members"], records_value["bindings"]
    definitions[data["definition_id"]] = {
        "id": data["definition_id"], "version": 1, "profile": model["profile"], "model": model["model"],
        "connection_id": model["id"], "connection_revision": model["revision"], "tools": list(data["tools"]),
        "instruction": data["goal"], "created_at": created_at}
    members[data["member_id"]] = {
        "id": data["member_id"], "kind": "ai", "name": data["member_name"],
        "definition_id": data["definition_id"], "definition_version": 1}
    bindings[data["binding_id"]] = {
        "id": data["binding_id"], "member_id": data["member_id"], "duty": data["title"], "version": 1,
        "active": True}
    records_value["works"][data["work_id"]] = {
        "id": data["work_id"], "title": data["title"], "goal": data["goal"],
        "materials_root": data["materials_root"], "max_calls": data["max_calls"], "status": "pending",
        "version": 1, "responsible_binding_id": data["binding_id"], "definition_id": data["definition_id"],
        "definition_version": 1, "mandate_id": data["mandate_id"], "attempt_ids": [], "result_ids": [],
        "created_at": created_at, "request_id": request_id, "authorized_by_principal_id": principal}
    records_value["mandates"][data["mandate_id"]] = {
        "id": data["mandate_id"], "work_id": data["work_id"], "work_version": 1,
        "binding_id": data["binding_id"], "definition_id": data["definition_id"], "definition_version": 1,
        "actions": list(data["tools"]), "version": 1, "active": True,
        "issuer_principal_id": principal, "created_at": created_at}
    return {"work_id": data["work_id"], "member_id": data["member_id"], "binding_id": data["binding_id"],
            "mandate_id": data["mandate_id"], "definition_id": data["definition_id"]}


def validate_state(state):
    """Structural consistency of the optional V1 work section; no cross-AU reference."""
    if state.get("work_runtime") is None:
        return
    records_value = state["work_runtime"]
    governance.exact(records_value, set(TABLES), "工作记录")
    for table in TABLES:
        require(isinstance(records_value[table], dict), "工作记录不完整")
        for key, value in records_value[table].items():
            require(isinstance(value, dict) and value.get("id") == key, "工作记录身份不一致")
    for definition in records_value["definitions"].values():
        require(type(definition.get("version")) is int and definition["version"] >= 1
                and model_profiles.supports(definition.get("profile"))
                and isinstance(definition.get("tools"), list), "Agent Definition 无效")
    for member in records_value["members"].values():
        require(member.get("kind") == "ai" and member.get("definition_id") in records_value["definitions"],
                "AI 成员缺少 Agent Definition")
        definition = records_value["definitions"][member["definition_id"]]
        require(member.get("definition_version") == definition["version"], "AI 成员定义版本不一致")
    for appointment in records_value["bindings"].values():
        require(appointment.get("member_id") in records_value["members"] and type(appointment.get("active")) is bool
                and type(appointment.get("version")) is int, "工作责任绑定无效")
    for work in records_value["works"].values():
        require(work.get("status") in OPEN + CLOSED and type(work.get("version")) is int
                and work.get("responsible_binding_id") in records_value["bindings"]
                and work.get("definition_id") in records_value["definitions"]
                and work.get("mandate_id") in records_value["mandates"], "工作记录缺少责任、定义或授权")
        require(type(work.get("max_calls")) is int and work["max_calls"] >= 1, "工作调用上限无效")
        require(work.get("materials_root") is None or reference(work["materials_root"]), "工作资料引用无效")
        require(work.get("materials_root") is not None
                or "read_document" not in records_value["definitions"][work["definition_id"]].get("tools", []),
                "只读资料工具缺少授权资料目录")
        attempts_value = work.get("attempts") or []
        require(isinstance(attempts_value, list) and len(attempts_value) <= MAX_ATTEMPTS, "执行尝试记录无效")
        for attempt in attempts_value:
            require(isinstance(attempt, dict) and attempt.get("id") == work["id"] + "#a" + str(attempt.get("seq"))
                    and attempt.get("status") in ("running", "unknown", "closed")
                    and (attempt.get("host_instance") is None or isinstance(attempt.get("host_instance"), str))
                    and (attempt.get("outcome") is None or attempt.get("outcome") in OUTCOMES),
                    "执行尝试记录无效")
        steps_value = work.get("steps") or []
        require(isinstance(steps_value, list) and len(steps_value) <= 10000, "步进记录无效")
        for step in steps_value:
            require(isinstance(step, dict) and step.get("step_ref") == work["id"] + "#s" + str(step.get("seq"))
                    and step.get("status") in STEP_STATUSES and step.get("purpose") == "work_step"
                    and isinstance(step.get("attempt_id"), str)
                    and step["attempt_id"].startswith(work["id"] + "#a"), "步进记录无效")
        require((work.get("status") == "delivered") == bool(work.get("delivered_at")),
                "工作完成状态与完成时间不一致")
        if work.get("status") == "delivered":
            require(isinstance(work.get("delivered_result_id"), str)
                    and any(item["id"] == work["delivered_result_id"] for item in work.get("results") or []),
                    "工作完成缺少成果引用")
        results_value = work.get("results") or []
        require(isinstance(results_value, list) and len(results_value) <= 20, "成果记录无效")
        for result in results_value:
            require(isinstance(result, dict) and reference(result.get("id", ""))
                    and result.get("status") in ("candidate", "adopted")
                    and isinstance(result.get("sha256"), str) and len(result["sha256"]) == 64
                    and isinstance(result.get("content"), str)
                    and isinstance(result.get("sources"), list)
                    and (result["status"] == "candidate") == (result.get("adopted_at") is None),
                    "成果记录无效")
        calls = work.get("tool_calls") or []
        require(isinstance(calls, list) and len(calls) <= MAX_TOOL_CALLS, "工具调用回执超出上限")
        for call in calls:
            require(isinstance(call, dict) and call.get("tool") in TOOLS
                    and type(call.get("seq")) is int
                    and call.get("step_ref") == work["id"] + "#" + str(call["seq"]),
                    "工具调用回执无效")
    for mandate in records_value["mandates"].values():
        require(mandate.get("work_id") in records_value["works"]
                and mandate.get("binding_id") in records_value["bindings"]
                and type(mandate.get("active")) is bool and type(mandate.get("version")) is int
                and isinstance(mandate.get("actions"), list), "工作授权无效")


def _stamp(clock=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if clock is None else clock))


def active_attempt(work, instance=None):
    """The one execution allowed to act right now; unknown must be resolved first."""
    calls = work.get("attempts") or []
    unresolved = [item for item in calls if item["status"] == "unknown"]
    require(not unresolved, "上一次执行结果未知；请先核对并结束该次执行")
    running = [item for item in calls if item["status"] == "running"]
    require(len(running) == 1, "该工作没有进行中的执行尝试；请先开始一次执行")
    attempt = running[0]
    held = attempt.get("host_instance")
    if instance is not None and held not in (None, instance):
        raise Rejected("该次执行由已结束的服务实例持有；请先核对并结束该次执行，不能继续用旧实例执行")
    return attempt


def start_attempt(state, data, principal, clock=None, instance=None):
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    require(work["status"] in OPEN, "工作已结束，不能再开始执行")
    calls = work.setdefault("attempts", [])
    require(len(calls) < MAX_ATTEMPTS, "该工作的执行尝试已达上限")
    require(not [item for item in calls if item["status"] in ("running", "unknown")],
            "该工作已有进行中或结果未知的执行；请先结束它")
    root = work.get("materials_root")
    if root is not None:
        for other in records(state)["works"].values():
            if other["id"] == work["id"] or other.get("materials_root") != root:
                continue
            require(not [item for item in other.get("attempts") or [] if item["status"] in ("running", "unknown")],
                    "另一个工作正在使用同一资料目录；请等它结束或为该工作指定其他目录")
    attempt = {"id": work["id"] + "#a" + str(len(calls) + 1), "seq": len(calls) + 1, "status": "running",
               "outcome": None, "owner_principal_id": principal, "reason": None, "host_instance": instance,
               "started_at": _stamp(clock), "ended_at": None}
    calls.append(attempt)
    return attempt


def finish_attempt(state, data, clock=None):
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    attempt = next((item for item in work.get("attempts") or [] if item["id"] == data["attempt_id"]), None)
    require(attempt is not None, "该工作没有此执行尝试")
    require(attempt["status"] in ("running", "unknown"), "该次执行已经结束，不能再改判")
    attempt.update(outcome=data["outcome"], reason=data["reason"], ended_at=_stamp(clock),
                   status="unknown" if data["outcome"] == "unknown" else "closed")
    return attempt


def budget(work):
    """One call per step; unknown keeps its reservation until reconciled."""
    steps = work.get("steps") or []
    reserved = sum(1 for item in steps if item["status"] in ("reserved", "unknown"))
    return {"max_calls": work["max_calls"], "reserved": reserved,
            "used": sum(1 for item in steps if item["status"] == "used")}


def reserve_step(state, data, clock=None, instance=None):
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    require(work["status"] in OPEN, "工作已结束，不能再预约调用")
    attempt = active_attempt(work, instance)
    steps = work.setdefault("steps", [])
    current = budget(work)
    require(current["reserved"] + current["used"] + 1 <= work["max_calls"],
            "该工作的调用上限已用尽；需要调整计划或先完成其他工作")
    step = {"seq": len(steps) + 1, "step_ref": work["id"] + "#s" + str(len(steps) + 1),
            "attempt_id": attempt["id"], "purpose": "work_step", "status": "reserved",
            "at": _stamp(clock), "settled_at": None, "reason": None}
    steps.append(step)
    return step


def settle_step(state, data, clock=None):
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    step = next((item for item in work.get("steps") or [] if item["step_ref"] == data["step_id"]), None)
    require(step is not None, "该工作没有此步进记录")
    require(step["status"] == "reserved", "该步已经结算；原记录不能覆盖，请另立步进")
    step.update(status=data["status"], reason=data["reason"], settled_at=_stamp(clock))
    return step


def _sources(work, sources):
    known = {item["step_ref"] for item in work.get("steps") or []}
    known |= {item["step_ref"] for item in work.get("tool_calls") or []}
    require(len(sources) == len(set(sources)), "成果来源不能重复")
    require(set(sources) <= known, "成果来源必须是本工作已有的执行步进或工具回执")


def submit_result(state, data, principal, clock=None):
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    require(work["status"] in OPEN, "工作已结束，不能再提交成果")
    attempt = active_attempt(work)
    results = work.setdefault("results", [])
    require(len(results) < 20, "该工作的成果数量已达上限")
    require(not any(item["id"] == data["result_id"] for item in results), "成果标识已存在；请查询原回执")
    _sources(work, data["sources"])
    body = data["content"].encode("utf-8")
    result = {"id": data["result_id"], "seq": len(results) + 1, "title": data["title"], "content": data["content"],
              "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "sources": list(data["sources"]),
              "status": "candidate", "attempt_id": attempt["id"], "submitted_by_principal_id": principal,
              "created_at": _stamp(clock), "adopted_at": None, "adopted_by_principal_id": None}
    results.append(result)
    return {key: value for key, value in result.items() if key != "content"}


def adopt_result(state, data, principal, clock=None):
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    result = next((item for item in work.get("results") or [] if item["id"] == data["result_id"]), None)
    require(result is not None, "该工作没有此成果")
    require(result["status"] == "candidate", "该成果已经采用；原采用记录不能覆盖")
    require(hashlib.sha256(result["content"].encode("utf-8")).hexdigest() == result["sha256"],
            "成果正文与登记摘要不一致；不能采用")
    result.update(status="adopted", adopted_at=_stamp(clock), adopted_by_principal_id=principal)
    return {key: value for key, value in result.items() if key != "content"}


def deliver_work(state, data, principal, clock=None):
    """D-03: completion needs an adopted result, and the work then stops accepting actions."""
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    require(work["status"] in OPEN, "该工作已经完成或已结束；原完成记录不能覆盖")
    result = next((item for item in work.get("results") or [] if item["id"] == data["result_id"]), None)
    require(result is not None, "该工作没有此成果")
    require(result["status"] == "adopted", "须先采用该成果，才能把工作记为完成")
    require(not [item for item in work.get("attempts") or [] if item["status"] == "running"],
            "该工作还有进行中的执行；请先结束该次执行")
    work.update(status="delivered", delivered_at=_stamp(clock), delivered_by_principal_id=principal,
                delivered_result_id=result["id"], version=work["version"] + 1)
    return {"work_id": work["id"], "work_status": work["status"], "delivered_at": work["delivered_at"],
            "result_id": result["id"]}


TOOL_SPECS = {
    "list_documents": {"name": "list_documents", "description": "列出宿主已登记只读资料目录内的文档路径。",
                       "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    "read_document": {"name": "read_document", "description": "读取授权资料目录内的一个文本资料。",
                      "parameters": {"type": "object",
                                     "properties": {"path": {"type": "string"}},
                                     "required": ["path"], "additionalProperties": False}},
}


def step_plan(state, charter, work_id, instance=None):
    """What one automatic step would send to the model; pure and revalidated."""
    work = records(state)["works"].get(work_id)
    require(work is not None, "工作不存在或不属于此 AU")
    require(work["status"] in OPEN, "工作已结束，不能继续执行")
    attempt = active_attempt(work, instance)
    definition = records(state)["definitions"][work["definition_id"]]
    binding = records(state)["bindings"][work["responsible_binding_id"]]
    mandate = records(state)["mandates"][work["mandate_id"]]
    require(binding["active"] and mandate["active"], "工作责任绑定或授权已失效")
    current = budget(work)
    require(current["reserved"] + current["used"] < work["max_calls"], "该工作的调用上限已用尽")
    allowed = [name for name in definition.get("tools") or [] if name in TOOL_SPECS]
    require(allowed, "该工作的 Agent 定义没有可用的只读工具")
    require(set(allowed) <= set(charter["allowed_tools"]), "工具不在当前有效章程允许的范围内")
    require(set(allowed) <= set(mandate["actions"]), "工具不在该工作的有效授权范围内")
    messages = [{"role": "system", "content": definition["instruction"]},
                {"role": "user", "content": "目标：" + work["goal"]
                 + "\n请先用电只读工具查看授权资料，再给出可直接交付的成果正文（Markdown）。"}]
    models = state.get("model_access") or {}
    connection = (models.get("connections") or {}).get(definition["connection_id"])
    require(isinstance(connection, dict), "该工作引用的模型连接不存在；请重新配置")
    require(bool(connection.get("enabled")), "该工作的模型连接已停用；请先启用或重新采用有效连接")
    require(models.get("default_connection_id") == definition["connection_id"],
            "须先采用该工作的模型连接为默认连接，才能继续执行")
    return {"work_id": work_id, "attempt_id": attempt["id"], "materials_root": work["materials_root"],
            "connection": dict(connection),
            "context_scope": {"au_id": state["id"], "work_id": work_id,
                              "definition_id": definition["id"], "definition_version": definition["version"],
                              "binding_id": binding["id"], "binding_version": binding["version"],
                              "member_id": binding["member_id"], "mandate_id": mandate["id"],
                              "mandate_version": mandate["version"], "materials_root": work["materials_root"]},
            "messages": messages, "tools": [{"type": "function", "function": TOOL_SPECS[name]} for name in allowed],
            "package": {"kind": "work_step", "work_id": work_id, "attempt_id": attempt["id"],
                        "run_id": work_id + "#s" + str(len(work.get("steps") or []) + 1)}}


def apply_step(state, charter, data, principal, instance, clock=None):
    """Commit one model turn: reserve a step, record the tools it used, settle it."""
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    attempt = active_attempt(work, instance)
    step = reserve_step(state, {"work_id": data["work_id"]}, clock, instance)
    usage = data.get("usage") or {}
    step["usage"] = {key: int(usage[key]) for key in ("input_tokens", "output_tokens")
                     if isinstance(usage.get(key), int)}
    step["cost_status"] = "unknown"
    recorded = []
    for call in data["tool_calls"]:
        require(isinstance(call.get("tool"), str) and call["tool"] in TOOL_SPECS, "模型请求了不支持的只读工具")
        detail = {key: call[key] for key in ("sha256", "bytes", "count") if key in call}
        recorded.append(record_tool_call(work, call["tool"], call.get("arguments") or {}, detail, attempt["id"], clock))
    if data["content"]:
        submit_result(state, {"work_id": data["work_id"], "result_id": data["result_id"],
                              "title": data["title"], "content": data["content"],
                              "sources": list(dict.fromkeys(data.get("sources", [])
                                         + [item["step_ref"] for item in recorded]))}, principal, clock)
    settle_step(state, {"work_id": data["work_id"], "step_id": step["step_ref"],
                        "status": "used", "reason": "模型步进已完成"}, clock)
    return {"step": step["step_ref"], "tool_calls": len(recorded), "result": bool(data["content"]),
            "usage": dict(step["usage"]), "cost_status": step["cost_status"]}


def fail_step(state, data, instance=None, clock=None):
    """A call whose result is unknown keeps its reservation until someone reconciles it."""
    step = reserve_step(state, {"work_id": data["work_id"]}, clock, instance)
    step["cost_status"] = "unknown"
    settle_step(state, {"work_id": data["work_id"], "step_id": step["step_ref"], "status": "unknown",
                        "reason": data["reason"]}, clock)
    return {"step": step["step_ref"], "status": "unknown"}


def reconcile_step(state, data, clock=None):
    """Resolve a step whose model result was unknown, with a recorded reason."""
    work = records(state)["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    step = next((item for item in work.get("steps") or [] if item["step_ref"] == data["step_id"]), None)
    require(step is not None, "该工作没有此步进记录")
    require(step["status"] == "unknown", "只有结果未知的步进需要核对")
    step.update(status=data["status"], reason=data["reason"], settled_at=_stamp(clock))
    return {key: step[key] for key in ("step_ref", "status", "reason")}


def tool_target(state, data, instance=None):
    """Validate a tool call against the responsible member's live mandate."""
    records_value = records(state)
    work = records_value["works"].get(data["work_id"])
    require(work is not None, "工作不存在或不属于此 AU")
    require(work["status"] in OPEN, "工作已结束，不能再调用工具")
    mandate = records_value["mandates"][work["mandate_id"]]
    require(mandate["active"] and data["tool"] in mandate["actions"], "工具不在该工作的有效授权范围内")
    require(work["materials_root"] is not None, "该工作尚未绑定授权资料目录")
    require(len(work.get("tool_calls") or []) < MAX_TOOL_CALLS, "该工作的工具调用回执已达上限")
    return work, mandate, active_attempt(work, instance)


def record_tool_call(work, tool, arguments, detail, attempt_id, clock=None):
    """Persist a durable tool receipt; content stays out of AU state."""
    calls = work.setdefault("tool_calls", [])
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if clock is None else clock))
    entry = {"seq": len(calls) + 1, "step_ref": work["id"] + "#" + str(len(calls) + 1), "tool": tool,
             "attempt_id": attempt_id, "arguments": dict(arguments), "at": at}
    entry.update(detail)
    calls.append(entry)
    return entry


def usage_total(work):
    """Sum the recorded usage of a work's steps; cost stays unknown, never a guess."""
    total = {"input_tokens": 0, "output_tokens": 0}
    for step in work.get("steps") or []:
        usage = step.get("usage") or {}
        for key in total:
            value = usage.get(key)
            if type(value) is int and value >= 0:
                total[key] += value
    return total


def projection(state, instance=None):
    records_value = records(state)
    result = []
    for work in records_value["works"].values():
        appointment = records_value["bindings"][work["responsible_binding_id"]]
        member = records_value["members"][appointment["member_id"]]
        definition = records_value["definitions"][work["definition_id"]]
        mandate = records_value["mandates"][work["mandate_id"]]
        result.append({
            "id": work["id"], "title": work["title"], "goal": work["goal"], "status": work["status"],
            "version": work["version"], "max_calls": work["max_calls"], "materials_root": work["materials_root"],
            "created_at": work["created_at"],
            "responsible": {"member_id": member["id"], "name": member["name"],
                            "binding_id": appointment["id"], "duty": appointment["duty"]},
            "definition": {"id": definition["id"], "version": definition["version"],
                           "connection_id": definition["connection_id"], "model": definition["model"],
                           "tools": list(definition["tools"])},
            "mandate": {"id": mandate["id"], "version": mandate["version"], "actions": list(mandate["actions"]),
                        "active": mandate["active"]},
            "attempt_ids": list(work["attempt_ids"]), "result_ids": list(work["result_ids"]),
            "tool_calls": [dict(call) for call in work.get("tool_calls") or []],
            "attempts": [dict(attempt) | {
                "host_instance": attempt.get("host_instance"),
                "stale": attempt["status"] == "running" and attempt.get("host_instance") not in (None, instance),
                "steps": sum(1 for step in work.get("steps") or [] if step["attempt_id"] == attempt["id"]),
                "tool_calls": sum(1 for call in work.get("tool_calls") or [] if call["attempt_id"] == attempt["id"]),
            } for attempt in work.get("attempts") or []],
            "steps": [dict(step) for step in work.get("steps") or []],
            "budget": budget(work), "usage": usage_total(work), "cost_status": "unknown",
            "delivered_at": work.get("delivered_at"),
            "delivered_result_id": work.get("delivered_result_id"),
            "results": [{key: value for key, value in item.items() if key != "content"}
                        for item in work.get("results") or []]})
    return sorted(result, key=lambda value: value["created_at"] + value["id"])
