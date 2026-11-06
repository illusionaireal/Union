"""Pure creation rules shared by prepared V1 and explicit legacy callers."""
import copy
import math
import uuid

from ..errors import require

OPERATIONS = {"create_member", "create_position", "update_position", "assign", "set_policy", "create_work",
              "handoff", "pause_work", "resume_work", "cancel_work", "update_work",
              "wait", "set_strategy", "record_memory", "request_support", "submit_chapter", "review_cycle"}
TOOLS = {"produce_artifact", "workspace_execute"}
FIELDS = {"name", "goal", "board_name", "charter", "resources"}


def text(value, label, limit=100000):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit, label + "必须是非空且有界的文本")
    return value


def validate_charter(c, *, v1=False):
    require(isinstance(c, dict), "章程必须是对象")
    require(set(c) == {"text", "allowed_operations", "allowed_tools", "reserved_matters", "board_can_amend"},
            "章程只支持明确的正文、操作、工具、保留事项和修章字段")
    text(c["text"], "章程正文")
    for field, known in (("allowed_operations", OPERATIONS), ("allowed_tools", TOOLS | ({"read_document"} if v1 else set())),
                         ("reserved_matters", {"goal", "resources", "charter", "funding", "dissolution"})):
        require(isinstance(c[field], list) and all(isinstance(v, str) for v in c[field])
                and set(c[field]) <= known, "章程含不支持的 " + field)
    require(type(c["board_can_amend"]) is bool, "修章权限必须显式为布尔值")


def validate_resources(r):
    require(isinstance(r, dict) and set(r) <= {"max_calls", "timeout_seconds", "max_cost", "cost_reserve_per_call"}, "不支持的资源配置；token 仅记录用量")
    require(type(r.get("max_calls")) is int and 0 < r["max_calls"] <= 10000, "必须提供有限的正整数调用上限")
    require(type(r.get("timeout_seconds")) is int and 1 <= r["timeout_seconds"] <= 3600, "必须提供 1–3600 秒的每次超时")
    for name in ("max_cost", "cost_reserve_per_call"):
        if name in r:
            require(type(r[name]) in (int, float) and math.isfinite(r[name]) and r[name] > 0, "费用配置必须是有限正数")


def validate_creation(data):
    require(isinstance(data, dict) and set(data) == FIELDS, "创建字段不完整或含不支持的字段")
    validate_charter(data["charter"])
    validate_resources(data["resources"])
    require(set(data["resources"]) == {"max_calls", "timeout_seconds"}, "工作台仅支持调用次数与超时；金额未知")
    for field in ("name", "goal", "board_name"):
        text(data[field], field, 200 if field != "goal" else 100000)


def valid_principal(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False


def prepared_state(au_id, data, principal):
    require(valid_principal(principal), "核心主体标识无效")
    return {"id": au_id, "name": data["name"], "goal": data["goal"], "board_name": data["board_name"],
            "version": 0, "charter_version": 1, "policy_version": 0, "runtime_profile": "core_v1",
            "schema_version": 1, "autonomy_state": "inactive", "resource_state": "planned",
            "resources": copy.deepcopy(data["resources"]),
            "governance_root": {"creator_principal_id": principal, "governor_principal_id": principal}}
