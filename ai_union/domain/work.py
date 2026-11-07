"""V1 work responsibility rules: who answers for a goal and under which authority.

Pure rules only. No transport, storage, model or host access; the governance
store remains the single writer of AU facts.
"""
import time

from . import governance, model_profiles
from .creation import text
from ..errors import CoreError, require

PROTOCOL = "core.work.v1"
FIELDS = {
    "start_work": {"work_id", "title", "member_name", "goal", "member_id", "binding_id", "mandate_id",
                   "definition_id", "connection_id", "expected_revision", "materials_root", "max_calls",
                   "tools", "reason"},
}
TOOLS = {"read_document", "produce_artifact"}
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
    for mandate in records_value["mandates"].values():
        require(mandate.get("work_id") in records_value["works"]
                and mandate.get("binding_id") in records_value["bindings"]
                and type(mandate.get("active")) is bool and type(mandate.get("version")) is int
                and isinstance(mandate.get("actions"), list), "工作授权无效")


def projection(state):
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
            "attempt_ids": list(work["attempt_ids"]), "result_ids": list(work["result_ids"])})
    return sorted(result, key=lambda value: value["created_at"] + value["id"])
