"""Optional host-bound business workspace. Never execute agent commands on the host."""
from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .engine import Engine, Rejected, encoded, now, require, text
from .executor import ExecutionFailure
from .model_api import reject_saved_secrets
from .runner import exclusive

TOOL = "workspace_execute"
OUTPUT_LIMIT = 65536
DEFINITION = {"type": "function", "function": {
    "name": TOOL,
    "description": "在宿主绑定的隔离工作区 /workspace 执行命令，读取或修改真实业务文件、运行测试。网络关闭；不会访问宿主私有文件。每轮仅单独调用一次；以实际退出码和输出判断结果。",
    "parameters": {"type": "object", "properties": {"command": {"type": "string"}},
                   "required": ["command"], "additionalProperties": False}}}


def schema(cx):
    cx.execute("CREATE TABLE IF NOT EXISTS workspace_grant(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,config TEXT NOT NULL)")
    cx.execute("CREATE TABLE IF NOT EXISTS workspace_commands(run_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,command TEXT NOT NULL,container TEXT NOT NULL,status TEXT NOT NULL,result TEXT,created_at TEXT NOT NULL)")


def binding(engine):
    with engine.read_transaction() as cx:
        if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='workspace_grant'").fetchone():
            return None
        row = cx.execute("SELECT revision,config FROM workspace_grant WHERE id=1").fetchone()
        return {"revision": row["revision"], "config": json.loads(row["config"])} if row else None


def validate_config(engine, config):
    require(isinstance(config, dict) and set(config) == {"directory", "image", "timeout_seconds", "enabled"}, "工作区配置字段不正确")
    require(type(config["enabled"]) is bool, "工作区启用必须为布尔值")
    require(type(config["timeout_seconds"]) is int and 1 <= config["timeout_seconds"] <= 120, "工作区命令限时必须为 1–120 秒")
    require(isinstance(config["image"], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", config["image"]), "使用本机预先安装的完整 Docker image ID，禁止自动拉取镜像")
    text(config["directory"], "工作区目录", 4096)
    raw = Path(config["directory"])
    require(raw.is_absolute() and raw.is_dir() and not raw.is_symlink(), "工作区须为现有绝对目录，不能是符号链接")
    directory = raw.resolve()
    require(not any(c in str(directory) for c in (",", "\n", "\r")), "工作区路径含不支持字符")
    runtime = Path(__file__).resolve().parents[1]
    require(not directory.is_relative_to(engine.root) and not engine.root.is_relative_to(directory), "工作区不能与组织私有目录重叠")
    require(not runtime.is_relative_to(directory) and not directory.is_relative_to(runtime), "使用独立业务目录，不能挂载运行系统源码目录")
    for item in directory.rglob("*"):
        require(not item.is_symlink() and (item.is_file() or item.is_dir()), "首次绑定不能包含链接或特殊文件")
        require(item.name not in {".git", ".union", "board.key", "local-access.json", ".env"} and not item.name.startswith(".env."), "首次绑定包含私有数据或 Git 元数据；请使用干净业务快照")
    return config | {"directory": str(directory)}


def configure(engine, key, config, reason):
    text(reason, "宿主授权依据", 2000)
    with exclusive(engine), engine.transaction() as cx:
        board = engine._board(cx, key)
        config = validate_config(engine, config)
        reject_saved_secrets(cx, [config, reason])
        schema(cx)
        require(not cx.execute("SELECT 1 FROM workspace_commands WHERE status IN ('started','unknown')").fetchone(), "先核对原工作区未知命令；配置不能清除回执")
        prior = cx.execute("SELECT revision FROM workspace_grant WHERE id=1").fetchone()
        revision = prior[0] + 1 if prior else 1
        cx.execute("INSERT OR REPLACE INTO workspace_grant VALUES(1,?,?)", (revision, encoded(config)))
        state = engine._state(cx)
        state["version"] += 1
        engine._save(cx, state)
        engine._event(cx, "workspace_configured", {"revision": revision, "enabled": config["enabled"], "board": board, "reason": reason})
    return {"revision": revision, "enabled": config["enabled"]}


def authorized(engine, package, cx):
    require(package.get("kind") == "work", "工作区只提供给有责任归属的正式工作")
    state = engine._state(cx)
    require(not engine.paused(cx), "派发已暂停，不能启动工作区命令")
    run = engine._run(cx, package["run_id"])
    require(run["status"] == "running" and run["package"] == package, "工作区调用必须绑定当前宿主工作包")
    require(state["charter_version"] == package["context_manifest"]["charter_version"], "章程依据已变化")
    work = state["work"][package["work_id"]]
    assignment = state["assignments"][package["assignment_id"]]
    require(work["run_id"] == package["run_id"] and work["status"] == "running" and work["version"] == package["work_version"], "工作责任或版本已变化")
    require(assignment["active"] and assignment["member_id"] == package["member_id"] and assignment["position_id"] == work["position_id"], "任职已失效")
    charter = engine._charter(cx, state["charter_version"])
    require(TOOL in charter["allowed_tools"] and TOOL in state["positions"][work["position_id"]]["permissions"], "章程或岗位未授权工作区工具")


def disable(engine, key, reason):
    """Revocation never depends on a healthy workspace or settled command receipts."""
    text(reason, "停用依据", 2000)
    with exclusive(engine), engine.transaction() as cx:
        board = engine._board(cx, key)
        reject_saved_secrets(cx, reason)
        schema(cx)
        row = cx.execute("SELECT revision,config FROM workspace_grant WHERE id=1").fetchone()
        require(row is not None, "尚无工作区绑定")
        config = json.loads(row["config"]) | {"enabled": False}
        revision = row["revision"] + 1
        cx.execute("UPDATE workspace_grant SET revision=?,config=? WHERE id=1", (revision, encoded(config)))
        state = engine._state(cx)
        state["version"] += 1
        engine._save(cx, state)
        engine._event(cx, "workspace_disabled", {"revision": revision, "board": board, "reason": reason})
    return {"revision": revision, "enabled": False}


def available(engine, package):
    if package.get("kind") != "work":
        return False
    grant = binding(engine)
    if not grant or not grant["config"]["enabled"]:
        return False
    try:
        with engine.read_transaction() as cx:
            authorized(engine, package, cx)
        return True
    except Rejected:
        return False


def container_argv(config, command, name, docker_config):
    uid = os.getuid() or 65534
    gid = os.getgid() or 65534
    return ["docker", "--config", docker_config, "--host", "unix:///var/run/docker.sock",
            "run", "--name", name, "--pull=never", "--network=none", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=128",
            "--memory=1g", "--memory-swap=1g", "--cpus=1", "--user", f"{uid}:{gid}",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m", "--workdir", "/workspace",
            "--env", "HOME=/tmp", "--mount", f"type=bind,src={config['directory']},dst=/workspace",
            "--entrypoint", "/bin/sh", config["image"], "-c", command]


def run_container(config, command, name):
    require(sys.platform == "linux" and shutil.which("docker"), "缺少 Linux Docker 运行条件；不会降级到宿主 shell")
    env = {"PATH": os.defpath, "LANG": "C.UTF-8"}
    with tempfile.TemporaryDirectory(prefix="union-docker-") as private:
        argv = container_argv(config, command, name, private)
        argv[0] = shutil.which("docker")
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, env=env, start_new_session=True)
        except OSError:
            raise Rejected("Docker 客户端无法启动；没有执行成员命令") from None
        output = bytearray()
        deadline = time.monotonic() + config["timeout_seconds"]
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    require(time.monotonic() < deadline, "工作区命令超时；需核对容器与业务文件")
                    for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                        chunk = os.read(key.fd, 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            output.extend(chunk)
                            require(len(output) <= OUTPUT_LIMIT, "工作区输出超过64KiB；需核对执行结果")
            code = process.wait(timeout=max(0.01, deadline - time.monotonic()))
            require(code >= 0, "Docker 客户端被信号终止；不能推断容器已停止")
            inspected = subprocess.run(argv[:5] + ["inspect", "--format", "{{json .State}}", name],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, env=env)
            require(inspected.returncode == 0 and len(inspected.stdout) < OUTPUT_LIMIT, "未取得容器停止证据")
            state = json.loads(inspected.stdout)
            require(state.get("Running") is False and state.get("Status") == "exited" and type(state.get("ExitCode")) is int, "容器未确认退出")
            # Container state, not the attach client's return code, is authoritative.
            result = {"exit_code": state["ExitCode"], "output": output.decode("utf-8", errors="replace"),
                      "container_exit_confirmed": True, "finished_at": state.get("FinishedAt")}
            try:
                subprocess.run(argv[:5] + ["rm", name], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, env=env)
            except (OSError, subprocess.TimeoutExpired):
                pass  # Confirmed stopped container may safely await host cleanup.
            return result
        except BaseException as error:
            if process.poll() is None:
                process.kill()
                process.wait()
            try:
                subprocess.run(argv[:5] + ["rm", "-f", name], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, env=env)
            except (OSError, subprocess.TimeoutExpired):
                pass
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            raise ExecutionFailure("工作区命令被中断；容器清理已尝试，结果仍须核对", unknown=True) from None
        finally:
            process.stdout.close()


def execute(engine, package, command):
    text(command, "工作区命令", 16384)
    rid = package["run_id"]
    with engine.transaction() as cx:
        authorized(engine, package, cx)
        reject_saved_secrets(cx, command)
        schema(cx)
        row = cx.execute("SELECT * FROM workspace_commands WHERE run_id=?", (rid,)).fetchone()
        if row:
            require(row["command"] == command, "同一调用不能执行第二个不同命令")
            if row["status"] in ("completed", "failed_before_start"):
                return json.loads(row["result"])
            raise ExecutionFailure("原工作区命令未确认或已核对封存；禁止重放", unknown=True)
        require(not cx.execute("SELECT 1 FROM workspace_commands WHERE status IN ('started','unknown')").fetchone(), "存在未核对工作区命令；停止新的工作区执行")
        grant = cx.execute("SELECT revision,config FROM workspace_grant WHERE id=1").fetchone()
        require(grant is not None, "宿主未绑定工作区")
        config = json.loads(grant["config"])
        require(config["enabled"], "工作区已停用")
        directory = Path(config["directory"])
        require(directory.is_dir() and directory.resolve() == directory and not directory.is_symlink(), "绑定的工作区目录已经改变")
        name = "union-" + rid
        cx.execute("INSERT INTO workspace_commands VALUES(?,?,?,?,?,?,?)", (rid, grant["revision"], command, name, "started", None, now()))
    try:
        result = run_container(config, command, name) | {"command_id": rid, "workspace_revision": grant["revision"]}
    except BaseException as error:
        status = "failed_before_start" if isinstance(error, Rejected) else "unknown"
        try:
            with engine.transaction() as cx:
                cx.execute("UPDATE workspace_commands SET status=?,result=? WHERE run_id=?", (status, encoded({"error": "工作区启动失败" if status == "failed_before_start" else "工作区结果未知，需核对"}), rid))
        except Exception:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise error
            raise ExecutionFailure("工作区结果及失败回执未确认；需核对原命令", unknown=True) from None
        if isinstance(error, (Rejected, KeyboardInterrupt, SystemExit)):
            raise
        raise ExecutionFailure("工作区结果未知；需核对原命令和容器", unknown=True) from None
    try:
        with engine.transaction() as cx:
            reject_saved_secrets(cx, result)
            cx.execute("UPDATE workspace_commands SET status='completed',result=? WHERE run_id=?", (encoded(result), rid))
            engine._event(cx, "workspace_command_completed", {"run_id": rid, "work_id": package["work_id"], "exit_code": result["exit_code"]})
    except Exception:
        # The command already ran; a failed receipt write must never permit replay.
        raise ExecutionFailure("工作区已执行，但结果未安全保存；需核对原命令", unknown=True) from None
    return result


def receipts(engine):
    with engine.read_transaction() as cx:
        if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='workspace_commands'").fetchone():
            return []
        return [dict(r) | {"result": json.loads(r["result"]) if r["result"] else None} for r in cx.execute("SELECT * FROM workspace_commands ORDER BY rowid")]


def reconcile(engine, key, run_id, reason):
    text(reason, "容器停止及文件核对依据", 2000)
    with exclusive(engine), engine.transaction() as cx:
        board = engine._board(cx, key)
        reject_saved_secrets(cx, reason)
        schema(cx)
        require(engine._run(cx, run_id)["status"] == "reconciled", "先通过原核对入口核对未知运行；不要假设容器已停止")
        changed = cx.execute("UPDATE workspace_commands SET status='reconciled' WHERE run_id=? AND status IN ('started','unknown')", (run_id,)).rowcount
        require(changed == 1, "没有待核对工作区命令")
        engine._event(cx, "workspace_command_reconciled", {"run_id": run_id, "board": board, "reason": reason})


def main(argv=None):
    parser = argparse.ArgumentParser(description="宿主工作区授权与回执；不调用模型")
    parser.add_argument("--root", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    configure_parser = commands.add_parser("configure")
    configure_parser.add_argument("--config", required=True)
    reconcile_parser = commands.add_parser("reconcile")
    reconcile_parser.add_argument("--run-id", required=True)
    disable_parser = commands.add_parser("disable")
    for child in (configure_parser, reconcile_parser, disable_parser):
        child.add_argument("--board-key-file", required=True)
        child.add_argument("--reason", required=True)
    commands.add_parser("status")
    args = parser.parse_args(argv)
    try:
        engine = Engine(args.root)
        if args.command == "status":
            result = {"binding": binding(engine), "commands": receipts(engine)}
        else:
            key = Path(args.board_key_file).read_text().strip()
            if args.command == "configure":
                result = configure(engine, key, json.loads(Path(args.config).read_text()), args.reason)
            elif args.command == "disable":
                result = disable(engine, key, args.reason)
            else:
                result = reconcile(engine, key, args.run_id, args.reason)
        print(encoded(result))
        return 0
    except (Rejected, OSError, ValueError) as error:
        print(encoded({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
