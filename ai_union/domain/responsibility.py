"""Small-AU human responsibility and bounded local submissions, not AI execution."""
from datetime import datetime, timezone
import hashlib

from .creation import text, valid_principal
from . import governance
from ..errors import CoreError, Rejected, require

FIELDS = {
    "appoint": {"member_id", "principal_id", "name", "binding_id", "duty"},
    "update_appointment": {"binding_id", "duty", "reason"},
    "create_work": {"work_id", "title", "instruction", "responsible_binding_id"},
    "update_work": {"work_id", "title", "instruction", "status", "reason"},
    "grant_mandate": {"mandate_id", "work_id", "binding_id", "parent_id", "actions", "can_delegate"},
    "revoke_mandate": {"mandate_id", "reason"},
    "handoff_responsibility": {"from_binding_id", "to_binding_id", "reason"},
    "begin_local_action": {"attempt_id", "work_id", "mandate_id"},
    "submit_local_result": {"attempt_id", "content"},
    "accept_local_result": {"attempt_id", "reason"},
    "set_goal": {"goal", "reason"},
}
VERSIONS = ("goal_version", "charter_version", "policy_version")
MEMBER_COMMANDS = {"grant_mandate", "begin_local_action"}


def validate_input(kind, data):
    governance.exact(data, FIELDS[kind])
    for key in ("reason", "duty", "goal", "instruction", "content"):
        if key in data:
            text(data[key], key, 100000 if key in ("goal", "instruction", "content") else 10000)
    for key in ("name", "title"):
        if key in data:
            text(data[key], key, 200)
    if kind == "appoint":
        require(valid_principal(data["principal_id"]), "须使用已登记的核心主体标识")
    if kind == "grant_mandate":
        require(data["actions"] == ["record_memory"], "本程序只支持有界内部 record_memory 授权")
        require(type(data["can_delegate"]) is bool, "须明确是否允许再委托")
    if kind == "update_work":
        require(data["status"] in ("open", "stopped"), "只能明确继续或停止该工作")


def authorize(state, kind, principal):
    if kind == "submit_local_result":
        return  # The existing original attempt is checked before accepting content.
    if principal == governance.current(state):
        return
    if kind in MEMBER_COMMANDS and governance.has_member(state, principal):
        return
    raise CoreError("not_authorized")


def active_appointment(state, binding_id):
    value = state["bindings"].get(binding_id)
    require(value is not None and value["active"], "责任绑定已失效或不属于此 AU")
    return value


def binding(state, binding_id, principals):
    value = active_appointment(state, binding_id)
    member = state["members"][value["member_id"]]
    require(member["principal_id"] in principals, "责任主体身份已失效")
    return value, member


def chain(state, mandate_id, work_id, principals):
    values, seen = [], set()
    while mandate_id is not None:
        require(mandate_id not in seen and len(seen) < 4, "再委托链循环或超过本程序四层范围")
        seen.add(mandate_id)
        mandate = state["mandates"].get(mandate_id)
        require(mandate is not None and mandate["active"] and mandate["work_id"] == work_id, "授权或其祖先已撤销，或不属于此工作")
        appointment, _ = binding(state, mandate["binding_id"], principals)
        require(appointment["version"] == mandate["binding_version"], "授权的任职职责版本已变化")
        require(mandate["work_version"] == state["work"][work_id]["version"], "授权的工作范围已变化")
        require(all(mandate[key] == state[key] for key in VERSIONS), "授权的目标、章程或治理版本已变化")
        if values:
            require(mandate["can_delegate"] and set(values[-1]["actions"]) <= set(mandate["actions"]), "再委托超出上级授权")
        values.append(mandate)
        mandate_id = mandate["parent_id"]
    require(values, "缺少此工作的有效授权")
    return list(reversed(values))


def authority(state, charter, principal, work_id, mandate_id, clock, principals):
    require(governance.effective_status(state, clock) == "active", "本地治理尚未生效、已到期或已经退出")
    governance.validate_live_targets(state, principals)
    require("record_memory" in charter["allowed_operations"], "当前有效章程未允许内部记录行动")
    work = state["work"].get(work_id)
    require(work is not None and work["status"] == "open", "工作不存在、已停止或需要先核对交接")
    binding(state, work["responsible_binding_id"], principals)
    mandates = chain(state, mandate_id, work_id, principals)
    require("record_memory" in mandates[-1]["actions"], "此授权未允许内部记录行动")
    appointment, member = binding(state, mandates[-1]["binding_id"], principals)
    require(member["principal_id"] == principal, "当前主体不是此授权的责任成员")
    return {"work_id": work_id, "work_version": work["version"], "binding_id": appointment["id"],
            "binding_version": appointment["version"], "member_id": member["id"], "principal_id": principal,
            "mandates": [{"id": mandate["id"], "version": mandate["version"]} for mandate in mandates],
            **{key: state[key] for key in VERSIONS}}


def check_attempt(state, charter, attempt, clock, principals):
    actual = authority(state, charter, attempt["principal_id"], attempt["work_id"], attempt["mandates"][-1]["id"], clock, principals)
    require(all(attempt[key] == value for key, value in actual.items()), "原尝试的责任、授权或有效范围已经变化")


def apply(state, charter, kind, data, principal, clock, principals):
    """Mutate a transaction-local copy; only late evidence returns a refusal."""
    require(state["schema_version"] in governance.SUPPORTED_SCHEMAS, "须先采用可执行的本地治理程序")
    if kind == "submit_local_result":
        attempt = state["attempts"].get(data["attempt_id"])
        if attempt is None or attempt["principal_id"] != principal:
            raise CoreError("not_authorized")
        require(attempt["status"] == "open", "原尝试已经提交内容；请查询原回执")
        refusal = None
        try:
            check_attempt(state, charter, attempt, clock, principals)
        except Rejected as error:
            refusal = str(error)
        attempt.update(content=data["content"], sha256=hashlib.sha256(data["content"].encode("utf-8")).hexdigest(),
                       status="not_adopted" if refusal else "submitted", authority_reason=refusal or "当前授权有效；等待采用")
        return "迟到内容已保留为未采用事实：" + refusal if refusal else None
    authorize(state, kind, principal)
    require(governance.effective_status(state, clock) in ("prepared", "active"), "治理已到期或退出；未完责任和原尝试仍保留")
    if kind == "appoint":
        member_id, binding_id = data["member_id"], data["binding_id"]
        require(data["principal_id"] in principals, "目标核心身份未登记")
        require(member_id not in state["members"] and binding_id not in state["bindings"], "成员或责任绑定标识已存在")
        state["members"][member_id] = {"id": member_id, "name": data["name"], "principal_id": data["principal_id"], "kind": "human"}
        state["bindings"][binding_id] = {"id": binding_id, "member_id": member_id, "duty": data["duty"], "version": 1, "active": True}
    elif kind == "update_appointment":
        appointment, _ = binding(state, data["binding_id"], principals)
        appointment.update(duty=data["duty"], version=appointment["version"] + 1)
    elif kind == "create_work":
        key = data["work_id"]
        require(key not in state["work"], "工作标识已存在")
        binding(state, data["responsible_binding_id"], principals)
        state["work"][key] = {"id": key, "title": data["title"], "instruction": data["instruction"],
                              "responsible_binding_id": data["responsible_binding_id"], "version": 1,
                              "status": "open", "history": [], "result_ids": []}
    elif kind == "update_work":
        work = state["work"].get(data["work_id"])
        require(work is not None and work["status"] != "delivered", "不能改写已经交付的工作历史")
        work.update(title=data["title"], instruction=data["instruction"], status=data["status"], version=work["version"] + 1)
    elif kind == "grant_mandate":
        key = data["mandate_id"]
        require(key not in state["mandates"], "授权标识已存在")
        work = state["work"].get(data["work_id"])
        require(work is not None and work["status"] == "open", "工作不在可授权状态")
        require("record_memory" in charter["allowed_operations"], "当前章程未允许此操作")
        appointment, _ = binding(state, data["binding_id"], principals)
        parent = data["parent_id"]
        if parent is None:
            require(principal == governance.current(state), "只有当前治理者能够发起根授权")
        else:
            packet = authority(state, charter, principal, work["id"], parent, clock, principals)
            source = state["mandates"][parent]
            require(source["can_delegate"] and len(packet["mandates"]) < 4, "上级未允许继续再委托或已达四层上限")
            require(set(data["actions"]) <= set(source["actions"]), "不能扩大上级授权的动作范围")
        state["mandates"][key] = {"id": key, "work_id": work["id"], "work_version": work["version"],
                                  "binding_id": appointment["id"], "binding_version": appointment["version"],
                                  "parent_id": parent, "actions": list(data["actions"]), "can_delegate": data["can_delegate"],
                                  "active": True, "version": 1, "issuer_principal_id": principal,
                                  **{key: state[key] for key in VERSIONS}}
    elif kind == "revoke_mandate":
        mandate = state["mandates"].get(data["mandate_id"])
        require(mandate is not None and mandate["active"], "授权不存在或已经撤销")
        mandate.update(active=False, version=mandate["version"] + 1)
    elif kind == "handoff_responsibility":
        # The old responsibility survives loss of its account. Only the new
        # recipient must be able to authenticate to take subsequent action.
        source = active_appointment(state, data["from_binding_id"])
        target, _ = binding(state, data["to_binding_id"], principals)
        require(source["id"] != target["id"], "必须交给另一个有效责任绑定")
        source.update(active=False, version=source["version"] + 1)
        for work in state["work"].values():
            if work["responsible_binding_id"] == source["id"] and work["status"] != "delivered":
                work["history"].append({"from_binding_id": source["id"], "to_binding_id": target["id"], "reason": data["reason"]})
                work.update(responsible_binding_id=target["id"], version=work["version"] + 1, status="needs_review")
    elif kind == "begin_local_action":
        key = data["attempt_id"]
        require(key not in state["attempts"], "本地尝试标识已存在；请查询原回执")
        packet = authority(state, charter, principal, data["work_id"], data["mandate_id"], clock, principals)
        state["attempts"][key] = packet | {"id": key, "kind": "local_submission", "status": "open"}
    elif kind == "accept_local_result":
        attempt = state["attempts"].get(data["attempt_id"])
        require(attempt is not None and attempt["status"] == "submitted", "没有可采用的当前提交；未采用事实不能直接升级为成果")
        check_attempt(state, charter, attempt, clock, principals)
        require(hashlib.sha256(attempt["content"].encode("utf-8")).hexdigest() == attempt["sha256"], "提交内容完整性校验失败")
        key = attempt["id"]
        state["results"][key] = {"id": key, "work_id": attempt["work_id"], "attempt_id": attempt["id"],
                                  "content": attempt["content"], "sha256": attempt["sha256"], "accepted_by": principal,
                                  "author_member_id": attempt["member_id"], "created_at": datetime.fromtimestamp(clock, timezone.utc).isoformat()}
        attempt["status"] = "accepted"
        work = state["work"][attempt["work_id"]]
        work["result_ids"].append(key)
        work.update(status="delivered", version=work["version"] + 1)
    elif kind == "set_goal":
        state.update(goal=data["goal"], goal_version=state["goal_version"] + 1)
    return None


def commands(state, principal, clock):
    role, status = governance.reader_role(state, principal), governance.effective_status(state, clock)
    result = []
    if role == "governor" and status in ("prepared", "active"):
        result.extend(kind for kind in FIELDS if kind not in ("begin_local_action", "submit_local_result", "accept_local_result"))
    if (role == "governor" or governance.has_member(state, principal)) and status == "active":
        result.extend(MEMBER_COMMANDS)
        if role == "governor":
            result.append("accept_local_result")
    if any(attempt["principal_id"] == principal and attempt["status"] == "open" for attempt in state["attempts"].values()):
        result.append("submit_local_result")
    return list(dict.fromkeys(result))


def validate_state(state):
    for table in ("members", "bindings", "work", "mandates", "attempts", "results"):
        for key, value in state[table].items():
            require(isinstance(key, str) and bool(key) and isinstance(value, dict) and value.get("id") == key, "责任对象标识不一致")
            if table in ("bindings", "work", "mandates"):
                require(type(value.get("version")) is int and value["version"] >= 1, "责任对象版本无效")
            if table in ("bindings", "mandates"):
                require(type(value.get("active")) is bool, "责任有效状态无效")
    for member in state["members"].values():
        require(member.get("kind") == "human" and valid_principal(member.get("principal_id")), "本地成员身份无效")
    for appointment in state["bindings"].values():
        require(appointment.get("member_id") in state["members"], "责任绑定缺少原成员")
    for work in state["work"].values():
        require(work.get("responsible_binding_id") in state["bindings"] and work.get("status") in ("open", "stopped", "delivered", "needs_review"), "工作责任或状态无效")
    for mandate in state["mandates"].values():
        require(mandate.get("binding_id") in state["bindings"] and mandate.get("work_id") in state["work"], "授权缺少本 AU 责任或工作")
    for attempt in state["attempts"].values():
        require(attempt.get("kind") == "local_submission" and attempt.get("status") in ("open", "submitted", "not_adopted", "accepted"), "本地尝试记录无效")
        require(attempt.get("work_id") in state["work"] and attempt.get("member_id") in state["members"], "本地尝试责任缺失")
