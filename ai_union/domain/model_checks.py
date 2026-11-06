"""Bounded verification Work/Execution, independent of any model or database."""
import copy
import uuid

from . import governance, model_access, responsibility
from .creation import text
from ..errors import require

DEFINITION = {"id": "core.model_check", "version": 1, "tools": ["read_document"],
    "instructions": "先调用 read_document 读取指定资料。收到工具结果后，给出简短资料概要并原样附上 challenge 校验码；不要调用其他工具。",
    "scope": "two_inferences_one_read_only_tool"}
FIELDS = {
    "start_model_check": {"connection_id", "expected_revision", "binding_id", "document_name", "document_text"},
    "reconcile_model_check": {"check_id"},
    "cancel_model_check": {"check_id", "reason"},
}


def validate_input(kind, data):
    governance.exact(data, FIELDS[kind])
    if kind == "start_model_check":
        text(data["document_name"], "资料名称", 200)
        text(data["document_text"], "资料正文", 32768)
        require(type(data["expected_revision"]) is int and data["expected_revision"] >= 1, "连接版本无效")
    if kind == "cancel_model_check":
        text(data["reason"], "停止依据", 10000)


def prepare(state, charter, data, principal, request_id, clock, principals):
    models = model_access.initialize(state)
    require("read_document" in charter["allowed_tools"], "当前章程尚未允许 read_document；请按有效程序允许只读资料工具")
    connection = model_access.connection(state, data["connection_id"], data["expected_revision"])
    require(connection["enabled"], "连接已停用")
    grant = models["resource_grant"]
    require(grant and grant["allow_unknown_cost"], "须先明确授予有限调用并接受供应商费用可能未知")
    require(model_access.occupied_calls(models) + 2 <= grant["max_calls"], "完整工具往返需要两次未被占用的调用额度")
    suffix = uuid.uuid5(uuid.NAMESPACE_URL, state["id"] + ":" + request_id).hex
    work_id, mandate_id = "model-work-" + suffix, "model-mandate-" + suffix
    require(work_id not in state["work"] and mandate_id not in state["mandates"], "验证工作或授权标识已经存在；原责任和历史不能覆盖")
    binding_id = data["binding_id"]
    if binding_id is None:
        owned = next((b for b in state["bindings"].values() if b["active"] and b.get("purpose") == "connection_check"
                      and state["members"][b["member_id"]]["principal_id"] == principal), None)
        if owned:
            binding_id = owned["id"]
        else:
            member_id, binding_id = "model-member-" + suffix, "model-binding-" + suffix
            require(member_id not in state["members"] and binding_id not in state["bindings"], "验证责任标识已存在；不能覆盖原成员或任职")
            state["members"][member_id] = {"id": member_id, "principal_id": principal, "name": "接入验证负责人", "kind": "human"}
            state["bindings"][binding_id] = {"id": binding_id, "member_id": member_id, "duty": "负责本 AU 有限模型接入验证",
                "version": 1, "active": True, "purpose": "connection_check"}
    appointment, member = responsibility.binding(state, binding_id, principals)
    require(member["principal_id"] == principal, "验证须由实际承担此绑定的核心主体发起")
    state["work"][work_id] = {"id": work_id, "title": "验证连接：" + connection["name"], "instruction": "读取所选资料，验证模型完整工具往返",
        "responsible_binding_id": binding_id, "version": 1, "status": "open", "history": [], "result_ids": [], "model_check_id": request_id}
    state["mandates"][mandate_id] = {"id": mandate_id, "work_id": work_id, "work_version": 1, "binding_id": binding_id,
        "binding_version": appointment["version"], "parent_id": None, "actions": ["model_check"], "can_delegate": False,
        "active": True, "version": 1, "issuer_principal_id": principal, **{k: state[k] for k in model_access.VERSIONS}}
    check = {"id": request_id, "principal_id": principal, "member_id": member["id"], "binding_id": binding_id,
        "binding_version": appointment["version"], "work_id": work_id, "work_version": 1, "mandate_id": mandate_id, "mandate_version": 1,
        "agent_definition": copy.deepcopy(DEFINITION), "versions": {k: state[k] for k in model_access.VERSIONS},
        "connection_id": connection["id"], "connection_revision": connection["revision"],
        "grant_ref": connection["grant_ref"], "grant_revision": connection["grant_revision"], "resource_revision": grant["revision"],
        "purpose": "connection_check", "status": "queued", "stage": 0, "attempt_ids": [], "attempts": [],
        "stop_requested": False, "output": None, "document_name": data["document_name"], "message": "已预留两次调用，等待验证",
        "waiting": {"object": request_id, "condition": "原模型请求有完整结果", "responsible_member_id": member["id"], "scope": "execution"}}
    models["checks"][request_id] = check
    return check


def authority(state, charter, check, clock, principals):
    model_access.active(state, check["principal_id"], clock, principals)
    require(not check["stop_requested"], "此验证已请求停止")
    require(check["agent_definition"] == DEFINITION, "原 Agent Definition 版本不再受当前执行器支持")
    require("read_document" in charter["allowed_tools"], "当前章程未允许只读资料工具")
    require(all(state[k] == v for k, v in check["versions"].items()), "原验证的目标/章程/治理版本已变化")
    work = state["work"].get(check["work_id"])
    require(work and work["status"] == "open" and work["version"] == check["work_version"], "验证工作已停止、交接或范围已变化")
    chain = responsibility.chain(state, check["mandate_id"], check["work_id"], principals)
    require(chain[-1]["version"] == check["mandate_version"] and chain[-1]["actions"] == ["model_check"], "验证授权已变化")
    appointment, member = responsibility.binding(state, check["binding_id"], principals)
    require(appointment["version"] == check["binding_version"] and member["id"] == check["member_id"]
            and member["principal_id"] == check["principal_id"], "原责任绑定已变化")
    connection = model_access.connection(state, check["connection_id"], check["connection_revision"])
    require(connection["enabled"] and connection["grant_ref"] == check["grant_ref"]
            and connection["grant_revision"] == check["grant_revision"], "原连接或模型服务授权已经变化")
    grant = state["model_access"]["resource_grant"]
    require(grant and grant["revision"] == check["resource_revision"] and grant["allow_unknown_cost"], "原资源授权已变化")
    return connection


def validate_state(state):
    for check in state["model_access"]["checks"].values():
        require(check["work_id"] in state["work"] and check["member_id"] in state["members"]
                and check["binding_id"] in state["bindings"] and check["mandate_id"] in state["mandates"], "模型验证责任关系不完整")
        require(check["status"] in ("queued", "running", "unknown", "not_adopted", "failed", "succeeded", "cancel_requested"), "模型验证状态无效")
        require(type(check["stage"]) is int and check["stage"] in (0, 1, 2) and len(check["attempt_ids"]) <= 2
                and len(set(check["attempt_ids"])) == len(check["attempt_ids"]) and len(check["attempt_ids"]) == len(check["attempts"]), "模型阶段或尝试标识不一致")
