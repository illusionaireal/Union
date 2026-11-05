"""Executable local governance rules; no host, authentication or storage access."""
import copy

from .creation import text, valid_principal, validate_charter
from ..errors import CoreError, require

PROFILE = "local_governance.v1"
RESERVED = {"charter", "goal", "resources", "appointments", "mandates", "dissolution"}
FIELDS = {
    "adopt_governance": {"config", "reason"},
    "acknowledge_recovery": {"reason"},
    "activate_governance": {"reason"},
    "configure_governance": {"config", "reason"},
    "renew_governance": {"reason"},
    "nominate_governor": {"principal_id", "reason"},
    "accept_governance": {"reason"},
    "recover_governance": {"reason"},
    "exit_governance": {"reason"},
    "amend_charter": {"charter", "reason"},
}


def exact(value, fields, label="请求"):
    require(isinstance(value, dict) and set(value) == fields, label + "字段不完整或不支持")


def validate_config(config, principal, *, pending=False):
    exact(config, {"profile", "final_decision_principal_id", "reserved_matters", "unavailability"}, "治理配置")
    require(config["profile"] == PROFILE, "不支持的治理程序")
    require(valid_principal(principal) and config["final_decision_principal_id"] == principal,
            "本程序的最终决定方必须是当前治理主体")
    reserved = config["reserved_matters"]
    require(isinstance(reserved, list) and all(isinstance(item, str) for item in reserved)
            and len(reserved) == len(RESERVED) and set(reserved) == RESERVED, "必须明确本程序的全部保留事项")
    unavailable = config["unavailability"]
    require(isinstance(unavailable, dict), "必须明确治理失能程序")
    mode = unavailable.get("mode")
    require(mode in ("successor_after_timeout", "exit_after_timeout"), "不支持的治理失能程序")
    exact(unavailable, {"mode", "timeout_seconds"} | ({"successor_principal_id"} if mode == "successor_after_timeout" else set()), "失能程序")
    timeout = unavailable["timeout_seconds"]
    require(type(timeout) is int and 60 <= timeout <= 2678400, "治理有效期须为 60–2678400 秒")
    if mode == "successor_after_timeout":
        successor = unavailable["successor_principal_id"]
        require(valid_principal(successor) and (pending or successor != principal), "后继主体必须是另一已登记的核心身份")


def validate_input(kind, data, principal):
    require(kind in FIELDS, "不支持的本地治理命令")
    exact(data, FIELDS[kind])
    if "reason" in data:
        text(data["reason"], "采用依据", 10000)
    if kind in ("adopt_governance", "configure_governance"):
        validate_config(data["config"], principal)
    if kind == "nominate_governor":
        require(data["principal_id"] is None or (valid_principal(data["principal_id"]) and data["principal_id"] != principal),
                "须提名另一已登记的核心主体")
    if kind == "amend_charter":
        validate_charter(data["charter"])


def current(state):
    return state.get("governance", {}).get("current_principal_id", state["governance_root"]["governor_principal_id"])


def effective_status(state, clock):
    governance = state.get("governance")
    if not governance:
        return "prepared"
    if governance["status"] != "active":
        return governance["status"]
    if clock >= governance["valid_until"]:
        return "exited" if governance["unavailability"]["mode"] == "exit_after_timeout" else "unavailable"
    return "active"


def has_member(state, principal):
    members = state.get("members", {})
    return any(binding["active"] and members[binding["member_id"]]["principal_id"] == principal
               for binding in state.get("bindings", {}).values())


def reader_role(state, principal):
    """A display role for the read projection; independent authorities compose."""
    if current(state) == principal:
        return "governor"
    governance = state.get("governance", {})
    if (governance.get("nomination") or {}).get("principal_id") == principal:
        return "nominee"
    if governance.get("unavailability", {}).get("successor_principal_id") == principal:
        return "successor"
    if has_member(state, principal):
        return "member"
    return None


def authorize(state, kind, principal):
    if kind in ("acknowledge_recovery", "recover_governance"):
        allowed = state.get("governance", {}).get("unavailability", {}).get("successor_principal_id") == principal
    elif kind == "accept_governance":
        allowed = (state.get("governance", {}).get("nomination") or {}).get("principal_id") == principal
    elif kind == "exit_governance":
        allowed = reader_role(state, principal) is not None
    else:
        allowed = current(state) == principal
    if not allowed:
        raise CoreError("not_authorized")


def commands(state, principal, clock):
    if state["schema_version"] == 1:
        return ["adopt_governance"] if current(state) == principal else []
    role, status = reader_role(state, principal), effective_status(state, clock)
    result = []
    if role == "governor":
        result.append("exit_governance")
        if status in ("prepared", "active"):
            result.extend(("configure_governance", "amend_charter"))
            result.extend(("activate_governance",) if status == "prepared" else ("renew_governance", "nominate_governor"))
    if state["governance"]["unavailability"].get("successor_principal_id") == principal:
        if status == "prepared":
            result.append("acknowledge_recovery")
        elif status == "unavailable":
            result.append("recover_governance")
    if (state["governance"]["nomination"] or {}).get("principal_id") == principal and status == "active":
        result.append("accept_governance")
    if role and status == "exited" and state["governance"]["status"] != "exited":
        result.append("exit_governance")
    return list(dict.fromkeys(result))


def adopt(state, config):
    state.update(schema_version=2, policy_version=1, goal_version=1,
                 governance=copy.deepcopy(config) | {"current_principal_id": current(state), "status": "prepared",
                    "valid_until": None, "recovery_ack": None, "nomination": None},
                 members={}, bindings={}, work={}, mandates={}, attempts={}, results={})


def revise_policy(state, *, prepare=False):
    state["policy_version"] += 1
    governance = state["governance"]
    governance.update(recovery_ack=None, nomination=None)
    if prepare or governance["unavailability"]["mode"] == "successor_after_timeout":
        governance.update(status="prepared", valid_until=None)


def transfer(state, principal):
    state["governance"].update(current_principal_id=principal, final_decision_principal_id=principal)
    revise_policy(state, prepare=True)


def validate_live_targets(state, principals):
    require(current(state) in principals, "当前治理主体身份已失效")
    successor = state["governance"]["unavailability"].get("successor_principal_id")
    require(successor is None or successor in principals, "已指定的后继身份已失效；须按当前规则重新配置失能程序")


def apply(state, charter, kind, data, principal, clock, principals):
    authorize(state, kind, principal)
    if kind == "adopt_governance":
        require(state["schema_version"] == 1, "治理程序已采用；请使用有效修订入口")
        require(charter["board_can_amend"], "旧有效章程不允许采用新规则；新规则不能自授权")
        adopt(state, data["config"])
        return charter
    require(state["schema_version"] == 2, "须先采用明确的治理程序")
    governance = state["governance"]
    status = effective_status(state, clock)
    if kind not in ("recover_governance", "exit_governance"):
        require(status in ("prepared", "active"), "治理期限已结束；只能按既有失能程序恢复或退出")
    if kind == "acknowledge_recovery":
        require(effective_status(state, clock) == "prepared", "恢复职责须在启用前确认")
        governance["recovery_ack"] = {"principal_id": principal, "policy_version": state["policy_version"]}
    elif kind == "activate_governance":
        require(effective_status(state, clock) == "prepared", "本地治理不在可激活状态")
        validate_live_targets(state, principals)
        validate_config({key: governance[key] for key in ("profile", "final_decision_principal_id", "reserved_matters", "unavailability")}, principal)
        successor = governance["unavailability"].get("successor_principal_id")
        if successor:
            require(governance["recovery_ack"] == {"principal_id": successor, "policy_version": state["policy_version"]},
                    "指定后继主体尚未确认当前恢复职责")
        governance.update(status="active", valid_until=clock + governance["unavailability"]["timeout_seconds"])
    elif kind == "configure_governance":
        require(charter["board_can_amend"], "旧有效章程不允许修订治理程序")
        governance.update(copy.deepcopy(data["config"]))
        revise_policy(state, prepare=True)
    elif kind == "renew_governance":
        require(status == "active", "仅可在有效治理期限内显式续期")
        validate_live_targets(state, principals)
        governance["valid_until"] = clock + governance["unavailability"]["timeout_seconds"]
    elif kind == "nominate_governor":
        require(status == "active", "只有当前有效治理者能够提名")
        governance["nomination"] = ({"principal_id": data["principal_id"], "policy_version": state["policy_version"],
                                     "reason": data["reason"]} if data["principal_id"] else None)
    elif kind == "accept_governance":
        require(status == "active" and governance["nomination"]["policy_version"] == state["policy_version"], "提名或原治理程序已失效")
        transfer(state, principal)
    elif kind == "recover_governance":
        require(status == "unavailable" and governance["unavailability"]["mode"] == "successor_after_timeout", "预先采用的失能恢复条件尚未满足")
        require(governance["recovery_ack"] == {"principal_id": principal, "policy_version": state["policy_version"]}, "当前恢复职责未被确认或已经撤销")
        transfer(state, principal)
    elif kind == "exit_governance":
        require(governance["status"] != "exited", "本地治理已退出")
        require(principal == current(state) or status == "exited", "仅可记录旧程序已经生效的超时退出")
        governance["status"] = "exited"
        revise_policy(state)
        governance["status"] = "exited"
    elif kind == "amend_charter":
        require(charter["board_can_amend"], "当前章程不允许此修订入口；新章程不能授权自身采用")
        charter = copy.deepcopy(data["charter"])
        state["charter_version"] += 1
        revise_policy(state)
    return charter


def validate_state(state, origin, charter):
    require(type(state.get("schema_version")) is int and state["schema_version"] == 2, "AU 治理版本不兼容")
    for name in ("id", "name", "board_name", "runtime_profile", "governance_root", "resources", "autonomy_state", "resource_state"):
        require(state.get(name) == origin[name], "不可变创建边界发生改变")
    for name in ("version", "charter_version", "policy_version", "goal_version"):
        require(type(state.get(name)) is int and state[name] >= 1, "治理版本无效")
    text(state.get("goal"), "目标")
    validate_charter(charter)
    governance = state.get("governance")
    exact(governance, {"profile", "final_decision_principal_id", "reserved_matters", "unavailability", "current_principal_id",
                       "status", "valid_until", "recovery_ack", "nomination"}, "治理记录")
    require(valid_principal(governance["current_principal_id"]), "当前治理主体无效")
    validate_config({key: governance[key] for key in ("profile", "final_decision_principal_id", "reserved_matters", "unavailability")},
                    current(state), pending=governance["status"] in ("prepared", "exited"))
    require(governance["status"] in ("prepared", "active", "exited"), "治理状态无效")
    if governance["status"] == "active":
        require(type(governance["valid_until"]) in (int, float) and governance["valid_until"] > 0, "缺少治理有效期")
    for name in ("members", "bindings", "work", "mandates", "attempts", "results"):
        require(isinstance(state.get(name), dict), "责任记录不完整")
