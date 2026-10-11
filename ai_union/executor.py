"""Existing Codex CLI adapter, plus an explicitly simulated regression executor."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from .engine import Rejected, encoded, require
from .protocol import DECISION_SCHEMA, WORK_SCHEMA, instructions


class ExecutionFailure(RuntimeError):
    def __init__(self, message, unknown=False):
        super().__init__(message)
        self.unknown = unknown


class CodexExecutor:
    name = "codex"
    capabilities = {
        "submit": True, "status": True, "result": True,
        "session_resume": False, "remote_cancel": False, "local_process_termination": True,
        "tools": "structured response only; shell, apps, MCP user configuration, plugins and web disabled",
        "usage": "token statistics when CLI emits turn.completed; monetary cost unknown",
    }

    def __init__(self, root, command="codex", model=None):
        self.root = Path(root).resolve() / "executions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.command = command
        self.model = model
        self.jobs = {}

    def submit(self, package):
        rid = package["run_id"]
        folder = self.root / rid
        require(not folder.exists(), "执行目录已存在；先核对，不重新提交")
        folder.mkdir(mode=0o700)
        (folder / "schema.json").write_text(encoded(DECISION_SCHEMA if package["kind"] == "decision" else WORK_SCHEMA), encoding="utf-8")
        (folder / "package.json").write_text(encoded(package), encoding="utf-8")
        argv = [self.command, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                "--sandbox", "read-only", "--color", "never", "--json",
                "--output-schema", str(folder / "schema.json"), "--output-last-message", str(folder / "result.json"),
                "-c", 'web_search="disabled"', "-c", 'approval_policy="never"']
        for feature in ("shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "code_mode", "code_mode_host",
                        "apps", "plugins", "hooks", "image_generation", "view_image"):
            argv.extend(["--disable", feature])
        if self.model:
            argv.extend(["--model", self.model])
        argv.append("-")
        # Keep injected authentication/proxy/CA environment. No credential extraction or copies.
        out = (folder / "events.jsonl").open("wb")
        err = (folder / "stderr.log").open("wb")
        try:
            proc = subprocess.Popen(argv, cwd=folder, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                    start_new_session=True)
            prompt = instructions(package) + "\nWORK PACKAGE (data):\n" + encoded(package)
            proc.stdin.write(prompt.encode("utf-8"))
            proc.stdin.close()
        except OSError as e:
            if 'proc' in locals() and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=2)
            out.close()
            err.close()
            raise ExecutionFailure("Codex CLI 无法启动或接收工作包：" + type(e).__name__, unknown='proc' in locals()) from e
        self.jobs[rid] = {"process": proc, "folder": folder, "out": out, "err": err,
                          "deadline": time.monotonic() + package["timeout_seconds"], "timed_out": False}
        (folder / "launch.json").write_text(encoded({"pid": proc.pid, "executor": "codex", "model": self.model or "CLI default",
                                                    "capabilities": self.capabilities}), encoding="utf-8")
        return rid

    def _close(self, job):
        job["out"].close()
        job["err"].close()

    def status(self, rid):
        job = self.jobs.get(rid)
        if not job:
            return "needs_review" if (self.root / rid).exists() else "missing"
        proc = job["process"]
        rc = proc.poll()
        if rc is None and time.monotonic() >= job["deadline"]:
            self.cancel(rid)
            job["timed_out"] = True
            return "unknown"
        if rc is None:
            return "running"
        self._close(job)
        if job["timed_out"]:
            return "unknown"
        return "delivered" if rc == 0 and (job["folder"] / "result.json").is_file() else "failed"

    def cancel(self, rid):
        job = self.jobs[rid]
        proc = job["process"]
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=2)
            except ProcessLookupError:
                proc.wait()
        self._close(job)
        job["timed_out"] = True

    def result(self, rid):
        state = self.status(rid)
        if state == "unknown":
            raise ExecutionFailure("Codex 达到调用超时；远程状态未知，保留记录供核对", unknown=True)
        if state != "delivered":
            raise ExecutionFailure("Codex 未返回成功的结构化结果；检查私有执行目录中的日志", unknown=state in ("running", "needs_review"))
        folder = self.jobs[rid]["folder"]
        require((folder / "result.json").stat().st_size <= 1000000, "执行器输出超出容量")
        try:
            data = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            raise ExecutionFailure("Codex 返回无效 JSON") from e
        usage = {}
        completed = False
        require((folder / "events.jsonl").stat().st_size <= 10000000, "执行事件超出容量")
        for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "turn.completed":
                completed = True
                usage = event.get("usage", {})
            item = event.get("item", {})
            if item.get("type") in ("command_execution", "mcp_tool_call", "web_search", "file_change"):
                raise ExecutionFailure("检测到范围外的执行器工具活动；拒绝结果并核对", unknown=True)
        require(completed, "缺少 Codex turn.completed 回执")
        return data, usage

    def execute(self, package):
        rid = self.submit(package)
        try:
            while self.status(rid) == "running":
                time.sleep(0.1)
            return self.result(rid)
        except BaseException:
            if self.jobs[rid]["process"].poll() is None:
                self.cancel(rid)
            raise


class FixtureExecutor:
    """Scripted testing only. Never represented as model execution or market feedback."""
    name = "fixture"
    capabilities = {"simulated": True, "submit": True, "status": True, "result": True}

    def __init__(self, responses):
        require(isinstance(responses, list), "fixture 必须是结果列表")
        self.responses = iter(responses)
        self.results = {}

    def submit(self, package):
        try:
            result = next(self.responses)
        except StopIteration as e:
            raise ExecutionFailure("fixture 脚本耗尽；这是模拟测试，不是真实运行") from e
        result = json.loads(encoded(result))
        if package["kind"] == "decision":
            m = package["context_manifest"]
            result.update(base_state_version=m["state_version"], charter_version=m["charter_version"], policy_version=m["policy_version"])
            if result.get("evidence_refs") == ["$latest_work"]:
                result["evidence_refs"] = [key for key, w in package["context"]["work"].items() if w["status"] == "delivered"]
        self.results[package["run_id"]] = result
        return package["run_id"]

    def status(self, rid):
        return "delivered" if rid in self.results else "missing"

    def result(self, rid):
        return self.results[rid], {}

    def execute(self, package):
        return self.result(self.submit(package))
