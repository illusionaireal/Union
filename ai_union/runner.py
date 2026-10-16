"""Bounded event-driven dispatcher. No fixed CEO or content production pipeline."""
import time
from contextlib import contextmanager

from .engine import Rejected
from .executor import ExecutionFailure
from .locking import file_lock
from .activity import activity


@contextmanager
def exclusive(engine):
    guard = file_lock(engine.root / "runner.lock")
    try:
        guard.__enter__()
    except OSError as e:
        raise Rejected("此组织已有运行进程；不能并行启动第二个派发器") from e
    try:
        yield
    finally:
        guard.__exit__(None, None, None)


def step(engine, executor):
    if engine.paused():
        return {"action": "paused", "reason": "派发已暂停"}
    engine.wake_due()
    ready = engine.ready_work()
    state = engine.state()
    if any(r["status"] in ("unknown", "running") for r in engine.runs()):
        return {"action": "blocked", "reason": "未知或在途执行需要核对"}
    company = state.get("company")
    awaiting_review = company and len(company["chapters"]) > len(company["reviews"])
    if state["phase"] != "bootstrap" and not ready and not engine.events(True) and not awaiting_review:
        return {"action": "wait", "reason": "没有待办或新事件", "next_review_at": engine.status()["next_review_at"]}
    if company and len(company["reviews"]) >= company["target_cycles"]:
        return {"action": "wait", "reason": "三个经营周期已完成，等待董事会验收"}
    if awaiting_review:
        ready = []  # Feedback must be decided on before pre-planned work is dispatched.
    metadata = {"execution": executor.metadata} if hasattr(executor, "metadata") else {}
    package = engine.begin_work(ready[0], executor.name, **metadata) if ready and state["phase"] != "bootstrap" else engine.begin_decision(executor.name, **metadata)
    usage = {}
    try:
        result, usage = executor.execute(package)
        if package["kind"] == "decision":
            engine.finish_decision(package["run_id"], result, usage)
        else:
            engine.finish_work(package["run_id"], result, usage)
        return {"action": package["kind"], "run_id": package["run_id"], "work_id": package.get("work_id"), "executor": executor.name}
    except (ExecutionFailure, Rejected, OSError, ValueError) as e:
        engine.fail_run(package["run_id"], str(e), unknown=getattr(e, "unknown", False), usage=getattr(e, "usage", usage))
        return {"action": "blocked", "run_id": package["run_id"], "reason": str(e)}
    except BaseException:
        engine.fail_run(package["run_id"], "执行被中断；先核对结果", unknown=True)
        raise


def test_connection(engine, executor):
    """Caller holds the dispatch lock and authorizes one charged probe."""
    engine.recover()
    package = engine.begin_connection_test(executor.metadata)
    try:
        result, usage = executor.execute(package)
        engine.finish_connection_test(package["run_id"], result, usage)
        return {"action": "connection_test", "run_id": package["run_id"], "status": "succeeded", "usage": engine.usage()[-1]["usage"]}
    except (ExecutionFailure, Rejected, OSError, ValueError) as error:
        engine.fail_run(package["run_id"], str(error), unknown=getattr(error, "unknown", False), usage=getattr(error, "usage", {}))
        return {"action": "connection_test", "run_id": package["run_id"], "status": "unknown" if getattr(error, "unknown", False) else "failed", "message": str(error)}
    except BaseException:
        engine.fail_run(package["run_id"], "连接测试被中断；远程结果未知", unknown=True)
        raise


def run(engine, executor, max_steps):
    if type(max_steps) is not int or not 1 <= max_steps <= 10000:
        raise Rejected("必须提供有限正整数步数")
    actions = []
    with exclusive(engine), activity(engine):
        # A factory resolves mutable host settings only after the dispatch lock is held.
        executor = executor() if callable(executor) else executor
        engine.recover()
        for _ in range(max_steps):
            try:
                action = step(engine, executor)
            except Rejected as e:
                action = {"action": "blocked", "reason": str(e)}
            actions.append(action)
            if action["action"] in ("wait", "blocked", "paused"):
                break
    return actions


def watch(engine, executor, max_steps, max_seconds, poll_seconds=1):
    """Wait for external/due events without model calls. Lifetime is bounded between calls."""
    if type(max_steps) is not int or not 1 <= max_steps <= 10000 or type(max_seconds) is not int or not 1 <= max_seconds <= 86400:
        raise Rejected("watch 必须提供有限的调用步数和运行秒数")
    deadline = time.monotonic() + max_seconds
    actions = []
    calls = 0
    with exclusive(engine), activity(engine):
        executor = executor() if callable(executor) else executor
        engine.recover()
        while calls < max_steps and time.monotonic() < deadline:
            try:
                action = step(engine, executor)
            except Rejected as e:
                action = {"action": "blocked", "reason": str(e)}
            if action["action"] == "wait":
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    time.sleep(min(poll_seconds, remaining))
                continue
            actions.append(action)
            if action["action"] in ("blocked", "paused"):
                break
            calls += 1
    return actions or [{"action": "wait", "reason": "等待期间没有新事件"}]
