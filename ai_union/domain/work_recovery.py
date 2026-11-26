"""Original execution ownership rules; trusted host facts are supplied by application."""
import copy

from ..errors import require


def owner(attempt):
    return attempt.get("execution_owner") or {"instance": attempt.get("host_instance"), "epoch": 0}


def validate(attempt):
    value = attempt.get("execution_owner")
    if value is not None:
        require(isinstance(value, dict) and set(value) == {"instance", "epoch"}
                and isinstance(value["instance"], str) and value["instance"]
                and type(value["epoch"]) is int and value["epoch"] >= 1, "执行所有者或 epoch 无效")


def eligibility(attempt, instance, *, host_live, worker_active=False, continuable=False):
    if not host_live:
        return {"eligible": False, "reason": "当前宿主已停止，不能接回执行"}
    if attempt["status"] != "running":
        return {"eligible": False, "reason": "该次执行已结束或结果未知，须先核对原执行"}
    if worker_active:
        return {"eligible": False, "reason": "当前宿主原执行或恢复仍在运行，不能另起副本"}
    if owner(attempt)["instance"] == instance and continuable:
        return {"eligible": True, "reason": "核对并继续原请求，模型不重放；当前所有者和 epoch 保留"}
    if owner(attempt)["instance"] == instance:
        return {"eligible": False, "reason": "当前宿主已持有该次执行，不能另起恢复副本"}
    return {"eligible": True, "reason": "原宿主已结束，可接回同一次执行并核对原请求"}


def claim(work, attempt_id, instance, *, host_live, worker_active=False):
    attempt = next((a for a in work.get("attempts", []) if a["id"] == attempt_id), None)
    require(attempt is not None, "该工作没有此执行尝试")
    result = eligibility(attempt, instance, host_live=host_live, worker_active=worker_active)
    require(result["eligible"], result["reason"])
    attempt["execution_owner"] = {"instance": instance, "epoch": owner(attempt)["epoch"] + 1}
    return copy.deepcopy(attempt["execution_owner"])


def assert_owner(attempt, expected):
    require(owner(attempt) == expected, "执行所有者或 epoch 已变化；旧执行不能继续行动或采用")
