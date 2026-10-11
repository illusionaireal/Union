import argparse
import json
import secrets
import sys
from pathlib import Path

from .engine import Engine, Rejected, encoded, require
from .evaluation import evaluate
from .executor import CodexExecutor, FixtureExecutor
from .runner import exclusive, run, watch

GOAL = "一个持续经营线上内容品牌的 AI 内容工作室。"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def board_key(args):
    return Path(args.board_key_file).read_text(encoding="utf-8").strip()


def parser():
    p = argparse.ArgumentParser(description="ai-union: 组织启动与首次协作，本地单组织运行时")
    p.add_argument("--root", default=".union/org", help="组织数据库与资产目录")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="采用章程并保存目标；生成本地董事会凭据")
    init.add_argument("--name", required=True)
    init.add_argument("--goal", default=GOAL)
    init.add_argument("--charter", required=True)
    init.add_argument("--resources", required=True)
    init.add_argument("--board-name", required=True, help="采用人；测试使用应在身份中注明")
    for name in ("status", "events", "decisions", "usage", "evaluate"):
        s = sub.add_parser(name)
        if name == "evaluate":
            s.add_argument("--output", help="将报告保存为 JSON")
    context = sub.add_parser("context")
    context.add_argument("--work-id")
    for cmd in ("run", "watch"):
        start = sub.add_parser(cmd, help="有限步派发；watch 等待外部事件和复查到期")
        start.add_argument("--executor", choices=("codex", "fixture"), required=True)
        start.add_argument("--fixture", help="明确标为模拟的结果脚本")
        start.add_argument("--max-steps", type=int, required=True)
        start.add_argument("--model", help="Codex 模型；省略时使用 CLI 默认")
        start.add_argument("--allow-unknown-cost", action="store_true", help="明确接受有限调用内费用未知；不表示金额上限得到保证")
        if cmd == "watch":
            start.add_argument("--max-seconds", type=int, required=True, help="调用之间检查的总生命周期；在途调用仍受每次超时限制")
    amend = sub.add_parser("amend")
    amend.add_argument("--charter", required=True)
    resource = sub.add_parser("resources")
    resource.add_argument("--config", required=True)
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--run-id", required=True)
    reconcile.add_argument("--resolution", choices=("confirmed_not_executed", "abandon"), required=True)
    for s in (amend, resource, reconcile):
        s.add_argument("--board-key-file", required=True)
        s.add_argument("--reason", required=True)
    event = sub.add_parser("event", help="导入可溯源事实；外部反馈需要真实来源或模拟标记")
    event.add_argument("--id", required=True)
    event.add_argument("--kind", required=True)
    event.add_argument("--data", required=True, help="JSON 文件")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = Path(args.root).resolve()
        if args.command == "init":
            require(not (root / "board.key").exists(), "董事会凭据已存在；不能覆盖")
            key = secrets.token_urlsafe(48)
            engine = Engine.create(root, args.name, args.goal, load(args.charter), load(args.resources), args.board_name, key)
            path = root / "board.key"
            # Exclusive creation and permissions avoid leaking the board capability into a shared file.
            import os
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(key + "\n")
            result = {"organization_id": engine.state()["id"], "root": str(root), "board_key_file": str(path), "adopted_charter_version": 1}
        else:
            engine = Engine(root)
            if args.command in ("status", "events", "decisions", "usage", "context"):
                result = engine.context(args.work_id) if args.command == "context" else getattr(engine, args.command)()
            elif args.command == "evaluate":
                result = evaluate(engine)
                if args.output:
                    output = Path(args.output)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(encoded(result) + "\n", encoding="utf-8")
            elif args.command in ("run", "watch"):
                if args.executor == "fixture":
                    require(bool(args.fixture), "模拟执行必须提供 --fixture 文件")
                    executor = FixtureExecutor(load(args.fixture))
                else:
                    require(args.allow_unknown_cost, "目前 Codex 金额费用未知；需显式 --allow-unknown-cost 并设置有限资源")
                    require("max_cost" not in engine.state()["resources"], "Codex 无可核实单次费用上限；不能在金额硬上限下运行")
                    executor = CodexExecutor(root, model=args.model)
                actions = watch(engine, executor, args.max_steps, args.max_seconds) if args.command == "watch" else run(engine, executor, args.max_steps)
                result = {"executor": executor.name, "simulated": executor.name == "fixture", "actions": actions, "status": engine.status()}
            elif args.command == "event":
                data = load(args.data)
                if args.kind == "external_feedback":
                    require(isinstance(data, dict) and bool(data.get("source")) and type(data.get("simulated")) is bool, "外部反馈必须包含 source 及显式 simulated 标记")
                result = {"inserted": engine.add_event(args.id, args.kind, data)}
            else:
                with exclusive(engine):
                    if args.command == "amend":
                        engine.amend(board_key(args), load(args.charter), args.reason)
                    elif args.command == "resources":
                        engine.configure_resources(board_key(args), load(args.config), args.reason)
                    elif args.command == "reconcile":
                        engine.reconcile(board_key(args), args.run_id, args.resolution, args.reason)
                result = engine.status()
        print(encoded(result))
        if args.command in ("run", "watch") and any(a["action"] == "blocked" for a in result["actions"]):
            return 2
        if args.command == "evaluate" and not result["real_agent_verified"]:
            return 3
        return 0
    except (Rejected, OSError, ValueError, KeyError) as e:
        print(encoded({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
