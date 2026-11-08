"""V1 model configuration and bounded resource grants; no transport or storage."""
import copy
from urllib.parse import urlsplit

from . import governance, model_profiles
from .creation import text
from ..errors import CoreError, require

FIELDS = {
    "reconcile_connection": {"operation_id"},
    "set_connection": {"connection_id", "expected_revision", "enabled", "make_default"},
    "grant_model_resources": {"max_calls", "allow_unknown_cost", "reason"},
}
CONNECTION_FIELDS = {"connection_id", "expected_revision", "name", "profile", "model", "max_output_tokens"}
VERSIONS = ("goal_version", "charter_version", "policy_version")


def validate_input(kind, data):
    from . import model_checks
    if kind in model_checks.FIELDS:
        return model_checks.validate_input(kind, data)
    if kind == "save_connection":
        profile = data.get("profile")
        require(model_profiles.supports(profile), "此版本不支持所选模型 profile")
        private = model_profiles.private_fields(profile)
        governance.exact(data, CONNECTION_FIELDS | private)
        text(data["name"], "连接名称", 100)
        text(data["model"], "模型标识", 256)
        require(type(data["max_output_tokens"]) is int and 1 <= data["max_output_tokens"] <= 32768, "输出上限须为 1–32768")
        if model_profiles.requires_api_key(profile):
            parsed = urlsplit(data["base_url"])
            require(parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                    "模型地址不支持用户信息、查询或片段")
            require(parsed.scheme == "https" or parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1"),
                    "模型地址须使用 HTTPS；自托管回环地址可使用 HTTP")
        else:
            require(type(data["grant_revision"]) is int and data["grant_revision"] > 0, "须提供当前模型服务 grant revision")
    else:
        require(kind in FIELDS, "不支持的核心模型命令")
        governance.exact(data, FIELDS[kind])
    if "expected_revision" in data:
        require(type(data["expected_revision"]) is int and data["expected_revision"] >= 0, "连接预期版本无效")
    if kind == "set_connection":
        require(type(data["enabled"]) is bool and type(data["make_default"]) is bool, "连接启用/采用须明确")
        require(data["enabled"] or not data["make_default"], "不能采用已停用的连接")
    if kind == "grant_model_resources":
        require(type(data["max_calls"]) is int and 1 <= data["max_calls"] <= 10000, "须提供有限正整数调用上限")
        require(type(data["allow_unknown_cost"]) is bool, "须明确是否接受费用未知")
        text(data["reason"], "授权依据", 10000)


def authorize(state, principal):
    if principal != governance.current(state):
        raise CoreError("not_authorized")


def active(state, principal, clock, principals):
    authorize(state, principal)
    require(state["schema_version"] in governance.SUPPORTED_SCHEMAS, "须先采用 S05 本地治理")
    require(governance.effective_status(state, clock) == "active", "须先激活或恢复有效的本地治理")
    governance.validate_live_targets(state, principals)


def initialize(state):
    if state["schema_version"] == 2:
        state.update(schema_version=3, model_access={"connections": {}, "operations": {}, "checks": {},
            "resource_grant": None, "default_connection_id": None})
    return state["model_access"]


def connection(state, connection_id, revision=None):
    value = state["model_access"]["connections"].get(connection_id)
    require(value is not None, "连接不属于此 AU 或尚未保存成功")
    if revision is not None:
        require(value["revision"] == revision, "连接版本已变化；请检查当前配置")
    return value


def occupied_calls(models):
    return sum(2 if check["status"] in ("queued", "running", "unknown") and not check.get("stop_requested")
               else sum(attempt["state"] != "prepared" for attempt in check["attempts"])
               for check in models["checks"].values())


def apply(state, kind, data, principal, request_id):
    models = initialize(state)
    if kind == "save_connection":
        old = models["connections"].get(data["connection_id"])
        require((old["revision"] if old else 0) == data["expected_revision"], "连接版本已变化；不能覆盖其他修改")
        public = {k: copy.deepcopy(v) for k, v in data.items() if k != "api_key_sha256"}
        models["operations"][request_id] = {"id": request_id, "principal_id": principal, "status": "saving",
            "config": public, "versions": {k: state[k] for k in VERSIONS}, "message": "正在保存连接；不调用模型"}
        return {"operation_id": request_id}
    if kind == "reconcile_connection":
        operation = models["operations"].get(data["operation_id"])
        require(operation and operation["principal_id"] == principal, "原保存操作不属于当前主体")
        require(operation["status"] == "unknown", "只有未确认的原保存需要核对")
        operation.update(status="saving", message="查询原模型服务保存结果")
        return {"operation_id": operation["id"]}
    if kind == "set_connection":
        value = connection(state, data["connection_id"], data["expected_revision"])
        if value["enabled"] != data["enabled"]:
            value.update(enabled=data["enabled"], revision=value["revision"] + 1, last_check=None)
        if data["make_default"]:
            models["default_connection_id"] = value["id"]
        elif not value["enabled"] and models["default_connection_id"] == value["id"]:
            models["default_connection_id"] = None
    if kind == "grant_model_resources":
        require(occupied_calls(models) <= data["max_calls"] <= state["resources"]["max_calls"],
                "调用上限不能超过创建计划或低于已经使用/预约的次数")
        prior = models["resource_grant"]
        models["resource_grant"] = copy.deepcopy(data) | {"revision": prior["revision"] + 1 if prior else 1,
            "principal_id": principal, "purpose": "connection_check"}
    return {}


def validate_state(state):
    models = state.get("model_access")
    governance.exact(models, {"connections", "operations", "checks", "resource_grant", "default_connection_id"}, "模型状态")
    for table in ("connections", "operations", "checks"):
        require(isinstance(models[table], dict), "模型记录不完整")
        for key, value in models[table].items():
            require(isinstance(value, dict) and value.get("id") == key, "模型记录身份不一致")
    for value in models["connections"].values():
        require(type(value["revision"]) is int and value["revision"] >= 1 and type(value["enabled"]) is bool, "模型连接版本无效")
        require(model_profiles.supports(value["profile"]), "模型 profile 不支持")
    require(models["default_connection_id"] is None or models["default_connection_id"] in models["connections"], "默认连接不属于此 AU")
    from .model_checks import validate_state as validate_checks
    validate_checks(state)
