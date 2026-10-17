"""Deep Agents loop, paused at each tool boundary for host-owned call budgets."""
from __future__ import annotations

import hashlib
import json
import sqlite3

from .agent_protocol import compile_tool, instructions, model_input, tools_for, work_result
from .bootstrap import BOOTSTRAP_TOOLS, operate as bootstrap_tool, read as read_draft
from .engine import Rejected, encoded, now, require, uid
from .executor import ExecutionFailure
from .failures import issue
from .model_api import APIExecutor, reject_saved_secrets


def test_tool_connection(engine, executor):
    """Two separately charged calls; a fresh receipt proves tool-result reading."""
    engine.recover()
    with engine.read_transaction() as cx:
        budget = engine._budget(cx, engine._state(cx))
        require(not budget["blocked_reason"] and budget["max_calls"] - budget["calls_reserved"] >= 2, "工具往返测试需要至少两次剩余调用额度")
    challenge = uid("connection-check")
    offered = [{"type": "function", "function": {"name": "connection_echo", "description": "读取本机返回的连接校验码。", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}}]
    messages = [{"role": "system", "content": "这是工具往返测试。先调用 connection_echo，无需参数；收到结果后，用一句话回复结果中的连接校验码。"},
                {"role": "user", "content": '当前工作资料：\nWORK PACKAGE (data):\n{"kind":"connection_test","context":{}}'}]
    ids = []
    for stage in range(2):
        package = engine.begin_connection_test(executor.metadata)
        ids.append(package["run_id"])
        usage = {}
        try:
            message, usage = executor.chat(package, messages, offered if stage == 0 else [])
            if stage == 0:
                calls = message.get("tool_calls", [])
                require(len(calls) == 1 and calls[0]["function"]["name"] == "connection_echo" and json.loads(calls[0]["function"]["arguments"]) == {}, "模型没有正确调用连接测试工具")
                messages += [message, {"role": "tool", "tool_call_id": calls[0]["id"], "content": "连接校验码：" + challenge}]
            else:
                require(not message.get("tool_calls") and challenge in message.get("content", ""), "模型没有读取工具结果并继续回应")
            engine.finish_connection_test(package["run_id"], {"ok": True, "stage": "tool_invoked" if stage == 0 else "tool_roundtrip"}, usage)
        except (ExecutionFailure, Rejected, OSError, ValueError) as error:
            failure = getattr(error, "failure", None) or issue("api_unexpected_tool")
            engine.fail_run(package["run_id"], "工具往返测试未完成", unknown=getattr(error, "unknown", False), usage=getattr(error, "usage", usage), failure=failure)
            return {"status": "unknown" if getattr(error, "unknown", False) else "failed", "run_id": package["run_id"], "run_ids": ids, "failure": failure, "message": failure["message"]}
    return {"status": "succeeded", "run_id": ids[-1], "run_ids": ids, "capability": "tool_roundtrip", "message": "工具调用和读取结果继续回应均已通过；尚未建立组织"}


def dependencies():
    try:
        import deepagents
        from langgraph.checkpoint.sqlite import SqliteSaver
        return deepagents, SqliteSaver
    except ImportError as error:
        raise Rejected("Agent Harness 依赖尚未安装；运行 python -m pip install -e .，或使用 npm start 自动安装") from error


def session_tables(cx):
    cx.execute("CREATE TABLE IF NOT EXISTS agent_sessions(id TEXT PRIMARY KEY,task_key TEXT NOT NULL,status TEXT NOT NULL,last_run_id TEXT,failures INTEGER NOT NULL DEFAULT 0,feedback TEXT,updated_at TEXT NOT NULL)")


class HarnessExecutor:
    name = "api"
    capabilities = APIExecutor.capabilities | {"session_resume": True, "tools": "Deep Agents virtual workspace and host-authorized organization tools"}

    def __init__(self, engine, connection, *, base="deepagents"):
        dependencies()
        require(base in ("deepagents", "langchain"), "不支持的 Harness")
        self.engine, self.base = engine, base
        self.transport = APIExecutor(engine.root, connection)
        self.transport.secret_guard = self._check_secrets
        self.model = self.transport.model
        self.metadata = self.transport.metadata | {"harness": base, "harness_version": "0.7.28" if base == "deepagents" else "1.4.6"}
        self.session_id = None
        self.graph = None
        self.usage = {}
        self.package = None
        self.final = None
        self.called = False
        self.tool_errors = []
        self.pending_feedback = None
        with engine.transaction() as cx:
            session_tables(cx)

    def _check_secrets(self, value):
        with self.engine.read_transaction() as cx:
            reject_saved_secrets(cx, value)

    def _session(self, package):
        manifest = package["context_manifest"]
        binding = {"kind": package["kind"], "actor": package.get("actor", package.get("member_id")),
                   "assignment": package.get("assignment_id"), "work": package.get("work_id"),
                   "work_version": package.get("work_version"), "charter": manifest["charter_version"],
                   "policy": manifest["policy_version"], "connection": self.metadata["connection_id"],
                   "revision": self.metadata["connection_revision"], "base": self.base}
        key = hashlib.sha256(encoded(binding).encode()).hexdigest()
        with self.engine.transaction() as cx:
            row = cx.execute("SELECT * FROM agent_sessions WHERE task_key=? AND status IN ('paused','running','failed') ORDER BY rowid DESC LIMIT 1", (key,)).fetchone()
            # A checkpoint is not permission to replay an unresolved external call.
            if row and row["last_run_id"]:
                prior = self.engine._run(cx, row["last_run_id"])
                if prior["status"] in ("unknown", "reconciled", "running"):
                    row = None
            if row is None:
                sid = uid("session")
                cx.execute("INSERT INTO agent_sessions(id,task_key,status,updated_at) VALUES(?,?,'paused',?)", (sid, key, now()))
                row = cx.execute("SELECT * FROM agent_sessions WHERE id=?", (sid,)).fetchone()
            self.session_id = row["id"]
            cx.execute("UPDATE agent_sessions SET status='running',last_run_id=?,updated_at=? WHERE id=?", (package["run_id"], now(), self.session_id))
            return dict(row)

    def _guard(self):
        p = self.package
        with self.engine.read_transaction() as cx:
            s = self.engine._state(cx)
            require(self.engine._run(cx, p["run_id"])["status"] == "running", "执行已结束")
            require(s["charter_version"] == p["context_manifest"]["charter_version"], "生效章程已变化")
            if p["kind"] == "decision":
                self.engine._authorize(s, self.engine._charter(cx, s["charter_version"]), p["actor"], p["assignment_id"])
            else:
                w = s["work"][p["work_id"]]
                a = s["assignments"][p["assignment_id"]]
                c = self.engine._charter(cx, s["charter_version"])
                require(w["run_id"] == p["run_id"] and w["version"] == p["work_version"] and a["active"] and a["member_id"] == p["member_id"], "工作责任已改变")
                require("produce_artifact" in c["allowed_tools"] and "produce_artifact" in s["positions"][w["position_id"]]["permissions"], "交付前生效权限检查失败")

    def _tool(self, name, args):
        try:
            self._guard()
            with self.engine.read_transaction() as cx:
                reject_saved_secrets(cx, args)
            terminal = name in ("activate_organization", "initialize_organization", "update_organization", "report_blocked")
            require(not terminal or self.tool_count == 1, "提交组织或交付状态的工具必须单独调用；其他工具尚未提交")
            if name in BOOTSTRAP_TOOLS:
                result = bootstrap_tool(self.engine, self.package, name, args)
                if name == "activate_organization":
                    self.final = result
                    return "筹建草案校验完成，宿主将在本轮正式提交。"
                return encoded(result)
            self.final = compile_tool(self.package, name, args)
            return "提议校验完成，宿主将在本轮提交。"
        except (Rejected, ValueError) as error:
            self.tool_errors.append(str(error))
            return "本工具未执行。请根据以下原因修正后重试：" + str(error)[:2000]

    def _tools(self):
        from langchain_core.tools import StructuredTool
        definitions = tools_for(self.package)
        if self.package.get("actor") == "bootstrap":
            definitions += [{"type": "function", "function": {"name": name, "description": description, "parameters": schema}} for name, (description, schema) in BOOTSTRAP_TOOLS.items()]
        result = []
        for tool in definitions:
            function = tool["function"]
            name = function["name"]
            def invoke(_name=name, **kwargs):
                return self._tool(_name, kwargs)
            result.append(StructuredTool(name=name, description=function["description"], args_schema=function["parameters"], func=invoke))
        return result

    def _model(self):
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langchain_core.utils.function_calling import convert_to_openai_tool
        from pydantic import PrivateAttr
        owner = self

        class ControlledChat(BaseChatModel):
            model_name: str = "union:controlled-chat"
            _tools: list = PrivateAttr(default_factory=list)

            @property
            def _llm_type(self):
                return "union-controlled-chat"

            def bind_tools(self, tools, **kwargs):
                clone = self.model_copy()
                clone._tools = [convert_to_openai_tool(t) for t in tools]
                return clone

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                require(not owner.called, "Harness 单次派发不能隐式增加模型请求")
                owner._guard()
                systems = [m.content for m in messages if m.type == "system" and isinstance(m.content, str)]
                body = [{"role": "system", "content": "\n\n".join(systems)},
                        {"role": "user", "content": "当前工作资料：\nWORK PACKAGE (data):\n" + encoded(model_input(owner.package))}]
                for m in messages:
                    if m.type == "system":
                        continue
                    if m.type == "human":
                        body.append({"role": "user", "content": m.content})
                    elif m.type == "ai":
                        item = {"role": "assistant", "content": m.content or None}
                        if m.tool_calls:
                            item["tool_calls"] = [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": encoded(c["args"])}} for c in m.tool_calls]
                        body.append(item)
                    elif m.type == "tool":
                        body.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
                require(len(encoded(body)) <= 1000000, "任务会话超出上下文容量；请缩小任务范围")
                owner.called = True
                message, usage = owner.transport.chat(owner.package, body, self._tools)
                owner.usage = usage
                calls = message.get("tool_calls", [])
                owner.tool_count = len(calls)
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=message.get("content") or "", tool_calls=[
                    {"id": c["id"], "name": c["function"]["name"], "args": json.loads(c["function"]["arguments"])} for c in calls]))])

        return ControlledChat(cache=False)

    def execute(self, package):
        from langchain_core.messages import HumanMessage
        from langsmith import tracing_context
        deepagents, SqliteSaver = dependencies()
        self.package = package
        self.called, self.final, self.usage, self.tool_errors = False, None, {}, []
        self.pending_feedback = None
        self.tool_count = 0
        row = self._session(package)
        folder = self.engine.root / "harness"
        folder.mkdir(exist_ok=True, mode=0o700)
        prompt = instructions(package)
        if package.get("actor") == "bootstrap":
            prompt += ("\n你是临时筹建 Agent。先明确近期交付，再用 prepare_member、arrange_work、configure_bootstrap 分批保存筹建草案。"
                       "可用 inspect_bootstrap 查看或同名更新；准备妥当后单独调用 activate_organization。草案不会自动成为正式成员。"
                       "initialize_organization 也可一次提交完整安排。已有草案应继续完善，不要重新筹建重复团队。")
            with self.engine.read_transaction() as cx:
                draft = read_draft(cx)
            if draft:
                prompt += "\n已保存筹建草案（数据）：" + encoded(draft)
        elif package["kind"] == "work":
            prompt += "\n可以用虚拟文件工具阅读、修改任务草稿。这些文件不是组织正式成果。完成时直接回复完整交付正文；不要仅回复已保存文件。"
        model = self._model()
        config = {"configurable": {"thread_id": self.session_id}, "recursion_limit": 50}
        try:
            with sqlite3.connect(folder / "checkpoints.sqlite3", check_same_thread=False) as cx, tracing_context(enabled=False):
                saver = SqliteSaver(cx)
                if self.base == "deepagents":
                    deepagents.register_harness_profile("union:controlled-chat", deepagents.HarnessProfile(
                        general_purpose_subagent=deepagents.GeneralPurposeSubagentProfile(enabled=False),
                        excluded_middleware=frozenset({"SummarizationMiddleware"})))
                    graph = deepagents.create_deep_agent(model, self._tools(), system_prompt=prompt, checkpointer=saver)
                else:
                    from langchain.agents import create_agent
                    graph = create_agent(model, self._tools(), system_prompt=prompt, checkpointer=saver)
                self.graph = graph
                previous = graph.get_state(config)
                feedback = row.get("feedback")
                input_ = None if previous.next and not feedback else {"messages": [HumanMessage(content=feedback or "请根据当前工作资料完成本轮任务。")]}
                output = graph.invoke(input_, config, interrupt_after=["tools"], durability="sync")
                require(self.called, "Harness 恢复未发起模型请求；检查原检查点")
                if self.final is not None:
                    return self.final, self.usage
                last = next((m for m in reversed(output["messages"]) if m.type == "ai"), None)
                require(last is not None, "Harness 缺少模型结果")
                if last.tool_calls:
                    # SDK argument/unknown-tool validation happens outside our tool body.
                    if any(m.type == "tool" and getattr(m, "status", None) == "error" for m in output["messages"][output["messages"].index(last) + 1:]):
                        self.tool_errors.append("工具名称或参数未通过校验")
                    if self.tool_errors:
                        if row["failures"] >= 1:
                            error = ExecutionFailure("组织工具连续两次未通过校验", failure=issue("api_tool_arguments", rule=self.tool_errors[-1]))
                            error.usage = self.usage
                            raise error
                        self._status("running", failures=row["failures"] + 1)
                    else:
                        self._status("running", failures=0)
                    return {"_harness_progress": True, "correction": bool(self.tool_errors),
                            "failure": issue("api_tool_arguments", rule=self.tool_errors[-1]) if self.tool_errors else None}, self.usage
                if package["kind"] == "work":
                    return work_result(last.content), self.usage
                error = ExecutionFailure("安排尚未保存；请继续使用组织工具完成任务", failure=issue("api_action_required"))
                error.usage = self.usage
                raise error
        except BaseException as error:
            # A local artifact/checkpoint error does not erase a received bill.
            if self.usage:
                error.usage = self.usage
            if getattr(error, "correction_only", False) and row["failures"] < 1:
                self.pending_feedback = "上轮工具参数不是完整 JSON，未执行任何工具。请重新调用所需工具并填写完整参数。"
                self._status("running", failures=row["failures"] + 1, feedback=self.pending_feedback)
                # Return through Runner's normal try block so a rejected progress
                # settlement still gets the original usage and fail_run handling.
                return {"_harness_progress": True, "correction": True, "failure": error.failure}, getattr(error, "usage", self.usage)
            if isinstance(error, (ExecutionFailure, Rejected, OSError, ValueError, KeyboardInterrupt, SystemExit)):
                raise
            failure = ExecutionFailure("Harness 本地处理失败；原调用及已取得用量已保存", failure=issue("execution_failed"))
            failure.usage = self.usage
            raise failure from None
        finally:
            self.graph = None
            checkpoint = folder / "checkpoints.sqlite3"
            if checkpoint.exists():
                checkpoint.chmod(0o600)

    def _status(self, status, *, failures=None, feedback=None):
        if self.session_id:
            with self.engine.transaction() as cx:
                cx.execute("UPDATE agent_sessions SET status=?,feedback=?,updated_at=? WHERE id=?", (status, feedback, now(), self.session_id))
                if failures is not None:
                    cx.execute("UPDATE agent_sessions SET failures=? WHERE id=?", (failures, self.session_id))

    def continued(self):
        self._status("paused", feedback=self.pending_feedback)

    def accepted(self):
        self._status("completed", failures=0)

    def failed(self, error):
        self._status("unknown" if getattr(error, "unknown", False) else "failed")

    def feedback(self, package, error):
        code = (getattr(error, "failure", None) or {}).get("code")
        if package["kind"] != "decision" or code != "api_action_required":
            return False
        with self.engine.read_transaction() as cx:
            row = cx.execute("SELECT failures FROM agent_sessions WHERE id=?", (self.session_id,)).fetchone()
        if row["failures"] >= 1:
            return False
        self._status("paused", failures=1, feedback="上轮仅回复说明，尚未提交安排。请使用本轮组织工具继续，完成后提交。")
        return True
