import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from .engine import Engine, Rejected, encoded, model_name, require
from .evaluation import evaluate
from .executor import CodexExecutor, FixtureExecutor
from .runner import exclusive, run, watch, test_connection
from .model_api import APIExecutor, bind_connection, configure_connection, list_connections, resolve_connection

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
        start.add_argument("--executor", choices=("codex", "fixture", "api"), required=True)
        start.add_argument("--fixture", help="明确标为模拟的结果脚本")
        start.add_argument("--max-steps", type=int, required=True)
        start.add_argument("--model", help="Codex 模型；省略时使用组织模型设置，未设置则使用 CLI 默认")
        start.add_argument("--connection-id", help="API 连接；省略时使用组织绑定的默认连接")
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
    sub.add_parser("api-list", help="列出连接配置，永不返回 API Key")
    configure = sub.add_parser("api-configure", help="保存 API 连接，不调用模型")
    configure.add_argument("--connection-id", required=True)
    configure.add_argument("--config", required=True, help="非秘密 JSON 配置文件")
    secrets = configure.add_mutually_exclusive_group()
    secrets.add_argument("--api-key-env", help="读取指定环境变量；不在命令行传递密钥值")
    secrets.add_argument("--api-key-file", help="读取私有密钥文件")
    secrets.add_argument("--clear-api-key", action="store_true")
    bind = sub.add_parser("api-bind", help="绑定组织默认连接；不传 connection-id 时清除绑定")
    bind.add_argument("--connection-id")
    probe = sub.add_parser("api-test", help="实际连接测试，预约一次调用，不形成组织")
    probe.add_argument("--connection-id")
    probe.add_argument("--allow-unknown-cost", action="store_true")
    for s in (configure, bind, probe):
        s.add_argument("--board-key-file", required=True)
        if s is not probe:
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
                require(args.executor == "api" or not args.connection_id, "此执行器不使用 API 连接")
                if args.executor == "fixture":
                    require(bool(args.fixture), "模拟执行必须提供 --fixture 文件")
                    executor = FixtureExecutor(load(args.fixture))
                elif args.executor == "codex":
                    require(args.allow_unknown_cost, "目前 Codex 金额费用未知；需显式 --allow-unknown-cost 并设置有限资源")
                    def executor():
                        state = engine.state()
                        require("max_cost" not in state["resources"], "Codex 无可核实单次费用上限；不能在金额硬上限下运行")
                        model = args.model if args.model is not None else state.get("execution_config", {}).get("codex_model")
                        return CodexExecutor(root, model=model_name(model))
                else:
                    require(args.allow_unknown_cost, "API 费用未知；需显式 --allow-unknown-cost 并设置有限资源")
                    require(args.model is None, "API 模型由连接配置固定")
                    def executor():
                        require("max_cost" not in engine.state()["resources"], "API 不支持金额硬上限")
                        return APIExecutor(root, resolve_connection(engine, args.connection_id))
                actions = watch(engine, executor, args.max_steps, args.max_seconds) if args.command == "watch" else run(engine, executor, args.max_steps)
                result = {"executor": args.executor, "simulated": args.executor == "fixture", "actions": actions, "status": engine.status()}
                if args.executor == "api":
                    result["simulated"] = any(r["simulated"] for r in result["status"]["runs"])
            elif args.command == "api-list":
                result = {"connections": list_connections(engine), "api_connection_id": engine.state().get("execution_config", {}).get("api_connection_id")}
            elif args.command in ("api-configure", "api-bind", "api-test"):
                with exclusive(engine):
                    key = board_key(args)
                    with engine.read_transaction() as cx:
                        engine._board(cx, key)
                    if args.command == "api-configure":
                        secret = None
                        if args.api_key_env:
                            secret = os.environ.get(args.api_key_env)
                            require(bool(secret), "指定的 API Key 环境变量未设置")
                        elif args.api_key_file:
                            secret = Path(args.api_key_file).read_text(encoding="utf-8").strip()
                            require(bool(secret), "API Key 文件为空")
                        elif args.clear_api_key:
                            secret = ""
                        result = configure_connection(engine, key, args.connection_id, load(args.config), args.reason, secret)
                    elif args.command == "api-bind":
                        bind_connection(engine, key, args.connection_id, args.reason)
                        result = {"api_connection_id": args.connection_id}
                    else:
                        require(args.allow_unknown_cost, "连接测试会产生一次实际调用；需显式 --allow-unknown-cost")
                        result = test_connection(engine, APIExecutor(root, resolve_connection(engine, args.connection_id)))
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
        if args.command == "api-test" and result["status"] != "succeeded":
            return 2
        return 0
    except (Rejected, OSError, ValueError, KeyError) as e:
        print(encoded({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
