"""Prepare one real company through the existing Console; never manufacture members.

Preparation and inspection perform no model calls. The stable creation request
preserves the catalog's crash/unknown and idempotency semantics.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from .console import Console
from .engine import Engine, Rejected, encoded, require
from .evaluation import execution_receipt
from .model_api import resolve_connection

REPO = Path(__file__).resolve().parents[1]
REQUEST_ID = "prepare-ai-union-corp-v1"


def prepare(root, profile, board_name):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(isinstance(profile, dict) and set(profile) == {"name", "goal", "charter", "resources"}, "公司配置字段不完整或不支持")
    app = Console(root, fixture=None)
    try:
        return app.command(app.new_session("board"), {
            "id": REQUEST_ID, "organization_id": None, "base_version": None,
            "kind": "create", "data": profile | {"board_name": board_name},
        })
    finally:
        app.close()


def company_engine(root):
    """Read-only discovery also works while the actual Console holds its lock."""
    root = Path(root).resolve()
    db = root / "console.sqlite3"
    require(db.is_file(), "公司尚未准备；先执行 prepare")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as cx:
        row = cx.execute("SELECT receipt,folder FROM creations WHERE id=?", (REQUEST_ID,)).fetchone()
        require(row is not None, "未找到公司的原创建请求；不猜测其他组织")
        receipt = json.loads(row[0])
        require(receipt["status"] == "succeeded", "原创建请求未成功；保留原目录和回执核对，不重复创建")
        directory = (root / row[1]).resolve()
        require(directory.is_relative_to(root / "organizations"), "公司目录超出服务范围")
        registered = cx.execute("SELECT folder FROM organizations WHERE id=?", (receipt["organization_id"],)).fetchone()
        require(registered is not None and registered[0] == row[1], "创建回执与组织目录不一致；请在宿主核对")
    engine = Engine(directory)
    require(engine.state()["id"] == receipt["organization_id"], "公司标识与登记记录不一致")
    return engine


def inspect_company(root):
    engine = company_engine(root)
    status = engine.status()
    blockers = []
    if status["budget"]["blocked_reason"]:
        blockers.append({"code": "resources", "message": status["budget"]["blocked_reason"]})
    if status["dispatch_state"] != "enabled":
        blockers.append({"code": "paused", "message": "派发已暂停；由董事会通过工作台继续"})
    if any(r["status"] in ("running", "unknown") for r in status["runs"]):
        blockers.append({"code": "unresolved_execution", "message": "存在在途或未知执行；先核对，禁止自动重放"})
    connection = None
    try:
        private = resolve_connection(engine)
        connection = {k: private[k] for k in ("id", "revision", "config")}
    except Rejected:
        blockers.append({"code": "model_connection", "message": "尚无已绑定且启用、带密钥的真实模型连接；在模型与 API 页面配置"})
    try:
        dependencies = all(importlib.util.find_spec(name) is not None for name in ("deepagents", "langgraph.checkpoint.sqlite"))
    except ModuleNotFoundError:
        dependencies = False
    if not dependencies:
        blockers.append({"code": "harness_dependencies", "message": "项目 Python 未安装固定 Harness 依赖"})
    # A saved API key is configuration, not a successful network/tool probe.
    tool_tested = False
    if connection:
        # Observation deliberately omits raw results. Inspect the private rows only
        # to return a boolean, never their secrets or provider text.
        with engine.read_transaction() as cx:
            for row in cx.execute("SELECT * FROM runs WHERE kind='connection_test' AND status='delivered'"):
                result, package = json.loads(row["result"]), json.loads(row["package"])
                metadata = package.get("execution", {})
                run = dict(row) | {"package": package, "usage": json.loads(row["usage"]) if row["usage"] else None}
                if result.get("stage") == "tool_roundtrip" and metadata.get("transport_source") == "provider_api" and metadata.get("connection_id") == connection["id"] and metadata.get("connection_revision") == connection["revision"] and execution_receipt(engine, run):
                    tool_tested = True
    build_ready = (REPO / "web/console/dist/index.html").is_file()
    from .workspace import binding, receipts
    grant = binding(engine)
    commands = receipts(engine)
    real_runs = {r["id"] for r in engine.runs() if r["executor"] == "api"
                 and r["package"].get("execution", {}).get("transport_source") == "provider_api"
                 and execution_receipt(engine, r)}
    workspace = {
        "configured": bool(grant and grant["config"]["enabled"]),
        "docker_cli_present": shutil.which("docker") is not None,
        "charter_allows_tool": "workspace_execute" in engine.charter()["allowed_tools"],
        "unresolved_commands": sum(c["status"] in ("started", "unknown") for c in commands),
        "real_commands_confirmed": sum(c["status"] == "completed" and c["run_id"] in real_runs and bool(c["result"].get("container_exit_confirmed")) for c in commands),
    }
    return {
        "organization_id": status["organization"]["id"], "name": status["organization"]["name"],
        "organization_root": str(engine.root), "phase": status["organization"]["phase"],
        "members": len(status["organization"]["members"]), "work": len(status["organization"]["work"]),
        "artifacts": len(status["organization"]["artifacts"]), "budget": status["budget"],
        "model_connection": connection, "tool_roundtrip_verified": tool_tested,
        "can_attempt_bootstrap": not blockers, "bootstrap_blockers": blockers,
        "console_build_ready": build_ready, "source": status["source"],
        "development_workspace": workspace,
        "operating_blockers": [
            {"code": "development_tools", "message": "隔离工作区适配已实现；本公司的实际容器、授权、代码交付与部署运维仍须逐项接入和验收"},
            {"code": "persistent_host", "message": "尚无该公司已安装并验证的持久主机与自动接续证据；本机进程不等于常驻托管"},
        ],
        "autonomous_operation_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="ai-union-corp 筹建与启动检查；不会自动调用模型")
    parser.add_argument("--root", default=".union/ai-union-corp")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare", help="幂等保存目标、阶段章程、资源和组织登记，不编造团队")
    create.add_argument("--profile", default=str(REPO / "examples/ai-union-corp.json"))
    create.add_argument("--board-name", required=True)
    commands.add_parser("status", help="只读检查，可与工作台同时运行")
    serve = commands.add_parser("serve", help="启动真实 React 工作台；禁用 fixture 和 Codex，不自动启动模型")
    serve.add_argument("--port", type=int, default=8766)
    try:
        args = parser.parse_args(argv)
        if args.command == "prepare":
            result = prepare(args.root, json.loads(Path(args.profile).read_text(encoding="utf-8")), args.board_name)
            print(encoded(result))
            return 0 if result["status"] == "succeeded" else 2
        if args.command == "status":
            print(encoded(inspect_company(args.root)))
            return 0
        company_engine(args.root)
        require((REPO / "web/console/dist/index.html").is_file(), "先执行 npm run build:console")
        from .server import Server
        app = Console(args.root, fixture=None, enable_codex=False)
        try:
            server = Server(app, args.port)
            try:
                access = {role: server.origin + "/#launch=" + app.ticket(role) for role in ("board", "observer")}
                path = app.root / "local-access.json"
                # Existing files must also have their mode repaired.
                fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
                if hasattr(os, "fchmod"):
                    os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    file.write(encoded(access))
                print(encoded({"console": server.origin, "local_access_file": str(path), "model_started": False}), flush=True)
                server.serve_forever(poll_interval=0.2)
            finally:
                server.server_close()
        finally:
            app.close()
        return 0
    except KeyboardInterrupt:
        return 0
    except (Rejected, OSError, ValueError, sqlite3.Error) as error:
        print(encoded({"error": str(error), "type": type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
