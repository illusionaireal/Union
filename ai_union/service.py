"""Supervise a bounded API watch on an operator-managed persistent host.

Systemd may restart a clean observation window, but cumulative Engine budgets
survive restarts. Exit 2 is terminal for the supplied service unit. Unknown
executions are recovered for reconciliation, never automatically replayed.
"""
import argparse
import sys

from .engine import Engine, Rejected, encoded
from .harness import HarnessExecutor
from .model_api import resolve_connection
from .runner import watch


def serve(engine, *, max_steps, max_seconds, allow_unknown_cost):
    from .engine import require
    require(allow_unknown_cost, "必须明确接受有限调用内费用未知；服务不会自动追加资源")

    def executor():
        require("max_cost" not in engine.state()["resources"], "API 不支持金额硬上限")
        return HarnessExecutor(engine, resolve_connection(engine))

    actions = watch(engine, executor, max_steps, max_seconds)
    terminal = any(a["action"] in ("blocked", "paused") for a in actions)
    # Exhaustion can happen exactly on the last permitted dispatch, before step
    # has a chance to observe it. Do not restart such a service as healthy.
    with engine.read_transaction() as cx:
        budget = engine._budget(cx, engine._state(cx))
    return {"actions": actions, "budget": budget, "restart_allowed": not terminal and not budget["blocked_reason"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="持久主机上的有限 API 组织监听；不配置资金或工具权限")
    parser.add_argument("--root", required=True, help="实际组织目录，非 Console 服务目录")
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    parser.add_argument("--allow-unknown-cost", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = serve(Engine(args.root), max_steps=args.max_steps, max_seconds=args.max_seconds, allow_unknown_cost=args.allow_unknown_cost)
        print(encoded(result), flush=True)
        return 0 if result["restart_allowed"] else 2
    except (Rejected, OSError, ValueError) as error:
        print(encoded({"error": str(error), "type": type(error).__name__, "restart_allowed": False}), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
