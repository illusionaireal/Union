"""Local host-bound sessions, durable commands and bounded dispatcher jobs."""
import copy
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from contextlib import closing, contextmanager, nullcontext
from pathlib import Path

from .activity import activity
from .engine import Engine, Rejected, encoded, identifier, model_name, now, require, text, uid, validate_charter, validate_resources
from .executor import CodexExecutor, FixtureExecutor
from .locking import file_lock
from .observation import snapshot
from .runner import exclusive, step, test_connection
from .model_api import APIExecutor, bind_connection, configure_connection, list_connections, resolve_connection, stored_command, reject_saved_secrets
from .failures import runtime_failure


class Console:
    def __init__(self, root, fixture=None, enable_codex=False, enable_api=True):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._guard = file_lock(self.root / "console.lock")
        self._guard.__enter__()
        self.db = self.root / "console.sqlite3"
        self.instance = uid("service")
        self.sessions = {}
        self.tickets = {}
        self.jobs = []
        self.mutex = threading.RLock()
        self.sequence = 0
        self.fixture = fixture
        self.enable_codex = enable_codex
        self.enable_api = enable_api
        self.executor_factory = self._executor
        self.closed = False
        with self.catalog() as cx:
            cx.execute("CREATE TABLE IF NOT EXISTS organizations(id TEXT PRIMARY KEY, folder TEXT NOT NULL)")
            cx.execute("CREATE TABLE IF NOT EXISTS creations(id TEXT PRIMARY KEY, payload TEXT NOT NULL, receipt TEXT NOT NULL, folder TEXT NOT NULL)")
            for row in cx.execute("SELECT id,receipt FROM creations").fetchall():
                receipt = json.loads(row["receipt"])
                if receipt["status"] == "accepted":
                    receipt.update(status="unknown", message="创建过程被中断；保留原目录，请在宿主核对。不要重复创建。")
                    cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), row["id"]))
        # Stale job receipts are preserved as uncertain, never automatically replayed.
        for item in self.organizations():
            e = Engine(self.root / item["folder"])
            with e.transaction() as cx:
                self._schema(cx)
                for row in cx.execute("SELECT id,receipt FROM commands").fetchall():
                    receipt = json.loads(row["receipt"])
                    if receipt["status"] == "accepted":
                        receipt.update(status="unknown", message="宿主作业中断；检查原执行记录，不能据此推断远程取消。")
                        cx.execute("UPDATE commands SET receipt=? WHERE id=?", (encoded(receipt), row["id"]))

    @contextmanager
    def catalog(self):
        with closing(sqlite3.connect(self.db, timeout=10)) as cx, cx:
            cx.row_factory = sqlite3.Row
            cx.execute("BEGIN IMMEDIATE")
            yield cx

    def organizations(self):
        with self.read_catalog() as cx:
            return [dict(row) for row in cx.execute("SELECT * FROM organizations ORDER BY rowid")]

    @contextmanager
    def read_catalog(self):
        with closing(sqlite3.connect(self.db.as_uri() + "?mode=ro", uri=True)) as cx:
            cx.row_factory = sqlite3.Row
            cx.execute("PRAGMA query_only=ON")
            cx.execute("BEGIN")
            yield cx

    def new_session(self, role, organizations=None):
        require(role in ("board", "observer"), "不支持的宿主角色")
        token = secrets.token_urlsafe(32)
        with self.mutex:
            self.sessions[token] = {"role": role, "organizations": None if organizations is None else frozenset(organizations),
                                    "expires": time.monotonic() + 8 * 3600, "actor": "local " + role}
        return token

    def ticket(self, role):
        token = secrets.token_urlsafe(32)
        with self.mutex:
            self.tickets[token] = (role, time.monotonic() + 600)
        return token

    def exchange(self, ticket):
        with self.mutex:
            entry = self.tickets.pop(ticket, None)
        require(entry is not None and entry[1] > time.monotonic(), "启动链接无效或已过期；请在宿主重新生成")
        return self.new_session(entry[0])

    def session(self, token):
        with self.mutex:
            session = self.sessions.get(token)
            require(session is not None and session["expires"] > time.monotonic(), "会话失效；请从宿主重新打开工作台")
            return dict(session)

    def engine(self, token, organization_id):
        session = self.session(token)
        identifier(organization_id)
        require(session["organizations"] is None or organization_id in session["organizations"], "会话无权访问此组织")
        with self.read_catalog() as cx:
            row = cx.execute("SELECT folder FROM organizations WHERE id=?", (organization_id,)).fetchone()
        require(row is not None, "组织不存在或不在此服务范围内")
        return Engine(self.root / row["folder"])

    def session_info(self, token):
        session = self.session(token)
        orgs = []
        for item in self.organizations():
            if session["organizations"] is None or item["id"] in session["organizations"]:
                e = self.engine(token, item["id"])
                with e.read_transaction() as cx:
                    state = e._state(cx)
                    orgs.append({"id": state["id"], "name": state["name"]})
        return {"role": session["role"], "organizations": orgs, "service_instance": self.instance,
                "executors": (["fixture"] if self.fixture is not None else []) + (["codex"] if self.enable_codex else []) + (["api"] if self.enable_api else [])}

    def model_connections(self, token, org_id):
        require(self.session(token)["role"] == "board", "观察者不能读取 API 连接配置")
        e = self.engine(token, org_id)
        return {"connections": list_connections(e), "api_enabled": self.enable_api,
                "api_connection_id": e.state().get("execution_config", {}).get("api_connection_id")}

    def observe(self, token, org_id, offset=0):
        e = self.engine(token, org_id)
        # Sequence is assigned before reading; clients also bind each request to their current epoch.
        with self.mutex:
            self.sequence += 1
            sequence = self.sequence
        result = snapshot(e, offset=offset)
        return result | {"service_instance": self.instance, "snapshot_sequence": sequence}

    @staticmethod
    def _schema(cx):
        cx.execute("CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, payload TEXT NOT NULL, receipt TEXT NOT NULL)")

    @staticmethod
    def _existing(cx, request, table="commands"):
        row = cx.execute(f"SELECT payload,receipt FROM {table} WHERE id=?", (request["id"],)).fetchone()
        if row:
            require(row["payload"] == encoded(request), "请求标识已用于不同参数；请查询原回执")
            return json.loads(row["receipt"])
        return None

    def receipt(self, token, org_id, request_id):
        identifier(request_id)
        self.session(token)
        if org_id:
            with self.engine(token, org_id).read_transaction() as cx:
                row = cx.execute("SELECT receipt FROM commands WHERE id=?", (request_id,)).fetchone()
        else:
            require(self.session(token)["role"] == "board", "创建回执需要发起人会话")
            require(self.session(token)["organizations"] is None, "此会话没有创建回执访问权限")
            with self.read_catalog() as cx:
                row = cx.execute("SELECT receipt FROM creations WHERE id=?", (request_id,)).fetchone()
        require(row is not None, "未找到此请求；请保留原请求标识核对")
        receipt = json.loads(row[0])
        # Organization receipts were scoped before the query. Creation receipts require
        # the global host board and must remain readable even if registration failed.
        return receipt

    def command(self, token, request):
        request = copy.deepcopy(request)
        session = self.session(token)
        require(session["role"] == "board", "观察者不能提交操作")
        require(isinstance(request, dict) and set(request) == {"id", "organization_id", "base_version", "kind", "data"}, "无效命令字段")
        identifier(request["id"])
        require(request["kind"] in ("create", "event", "resources", "model", "amend", "reconcile", "start", "pause", "api_connection", "api_binding", "api_test", "company_usage", "controller_descriptor", "respond_request"), "不支持的命令")
        require(isinstance(request["data"], dict), "命令数据必须为对象")
        require(len(encoded(request)) <= 200000, "命令过大")
        receipt = {k: request[k] for k in ("id", "organization_id", "base_version", "kind")}
        receipt.update(actor=session["actor"], created_at=now(), status="accepted", message="操作已受理")
        if request["kind"] == "create":
            require(session["organizations"] is None, "此会话没有创建组织权限")
            return self._create(request, receipt)
        e = self.engine(token, request["organization_id"])
        public_input = copy.deepcopy(request)
        if request["kind"] == "api_connection":
            public_input["data"].pop("api_key", None)
        private_key = (e.root / "board.key").read_text(encoding="utf-8").strip() if request["kind"] in ("controller_descriptor", "respond_request") else None
        with e.read_transaction() as cx:
            # Reject credentials before even a rejected command can persist them.
            reject_saved_secrets(cx, public_input, extra_secret=private_key)
        persisted = stored_command(request)
        with e.read_transaction() as cx:
            prior = self._existing(cx, persisted)
        if prior:
            return prior
        guard = exclusive(e) if request["kind"] in ("start", "resources", "model", "amend", "reconcile", "api_connection", "api_binding", "api_test", "company_usage", "controller_descriptor", "respond_request") else nullcontext()
        acquired = False
        transferred = False
        try:
            guard.__enter__()
            acquired = True
            with e.transaction() as cx:
                prior = self._existing(cx, persisted)
                if prior:
                    return prior
                try:
                    with e.transaction():
                        state = e._state(cx)
                        require(type(request["base_version"]) is int and request["base_version"] == state["version"], "版本冲突；刷新并重新预览，输入已保留")
                        result = self._execute(e, request)
                    job_command = request["kind"] in ("start", "api_test")
                    receipt.update(status="accepted" if job_command else "succeeded", message="有限调用已受理" if job_command else "操作已保存")
                    if job_command:
                        receipt.update(executor="api" if request["kind"] == "api_test" else request["data"]["executor"], requested_model=getattr(result, "model", None))
                        if hasattr(result, "metadata"):
                            receipt["execution"] = result.metadata
                    elif request["kind"] == "api_connection":
                        receipt["connection"] = result
                except (Rejected, KeyError, TypeError) as error:
                    receipt.update(status="rejected", message=str(error) if isinstance(error, Rejected) else "命令字段缺失或类型不正确")
                cx.execute("INSERT INTO commands VALUES(?,?,?)", (request["id"], encoded(persisted), encoded(receipt)))
            if receipt["status"] == "accepted":
                try:
                    with self.mutex:
                        target = self._probe_job if request["kind"] == "api_test" else self._job
                        thread = threading.Thread(target=target, args=(e, request, result, guard), daemon=False)
                        thread.start()
                        self.jobs.append(thread)
                        transferred = True
                except (RuntimeError, OSError):
                    # Thread.start failed before the job could dispatch. Keep a terminal
                    # receipt and stop dispatch; this request must never be replayed.
                    receipt.update(status="rejected", ended_at=now(),
                                   message="宿主无法启动运行作业；未派发调用，已暂停派发。请保留回执，待宿主恢复后重新启动。")
                    with e.transaction() as cx:
                        if request["kind"] == "start":
                            e.set_paused(True)
                        cx.execute("UPDATE commands SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
            return receipt
        except Rejected as error:
            with e.transaction() as cx:
                prior = self._existing(cx, persisted)
                if prior:
                    return prior
                receipt.update(status="rejected", message=str(error))
                cx.execute("INSERT INTO commands VALUES(?,?,?)", (request["id"], encoded(persisted), encoded(receipt)))
            return receipt
        finally:
            if acquired and not transferred:
                guard.__exit__(None, None, None)

    def _create(self, request, receipt):
        require(request["organization_id"] is None and request["base_version"] is None, "创建不应引用已有组织版本")
        data = request["data"]
        folder = "organizations/" + hashlib.sha256(request["id"].encode()).hexdigest()
        # Persist allocation before filesystem work. A crash becomes unknown, never a second organization.
        with self.mutex:
            with self.catalog() as cx:
                prior = self._existing(cx, request, "creations")
                if prior:
                    return prior
                cx.execute("INSERT INTO creations VALUES(?,?,?,?)", (request["id"], encoded(request), encoded(receipt), folder))
            try:
                require(set(data) - {"company", "controller_ref"} == {"name", "goal", "board_name", "charter", "resources"}, "创建字段不完整或含不支持的字段")
                if "controller_ref" in data:
                    from .au_contract import validate_descriptor
                    validate_descriptor(data["controller_ref"])
                if "company" in data:
                    from .company import validate_config, create
                    validate_config(data["company"])
                    require({"submit_chapter", "review_cycle"} <= set(data["charter"]["allowed_operations"]), "小说公司章程须授权模拟投稿与经营复盘")
                validate_charter(data["charter"])
                validate_resources(data["resources"])
                require(set(data["resources"]) == {"max_calls", "timeout_seconds"}, "工作台仅支持调用次数与超时；金额未知")
                for field in ("name", "goal", "board_name"):
                    text(data[field], field, 200 if field != "goal" else 100000)
                directory = self.root / folder
                require(not directory.exists(), "分配目录已存在；请核对原创建请求")
                directory.mkdir(parents=True, mode=0o700)
                key = secrets.token_urlsafe(48)
                import os
                fd = os.open(directory / "board.key", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(key)
                engine = Engine.create(directory, data["name"], data["goal"], data["charter"], data["resources"], data["board_name"], key)
                with engine.transaction() as cx:
                    self._schema(cx)
                    state = engine._state(cx)
                    org_id = state["id"]
                    if "company" in data:
                        state["company"] = create(data["company"])
                        engine._save(cx, state)
                    if "controller_ref" in data:
                        from .au_contract import configure_descriptor
                        configure_descriptor(engine, key, data["controller_ref"], "initial controller description", state["version"])
                receipt.update(organization_id=org_id, status="succeeded", message="组织已创建并采用章程；尚未启动执行")
                with self.catalog() as cx:
                    cx.execute("INSERT INTO organizations VALUES(?,?)", (org_id, folder))
                    cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
            except (Rejected, KeyError, TypeError) as error:
                receipt.update(status="rejected", message=str(error) if isinstance(error, Rejected) else "创建字段类型不正确")
                with self.catalog() as cx:
                    cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
            except (OSError, sqlite3.Error):
                receipt.update(status="unknown", message="创建存储过程未确认；保留分配目录与原请求，请在宿主核对")
                with self.catalog() as cx:
                    cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
            return receipt

    def _execute(self, e, request):
        kind, data = request["kind"], request["data"]
        fields = {"event": {"event_id", "kind", "content", "source", "simulated"}, "pause": set(),
                  "resources": {"resources", "reason"}, "model": {"model", "reason"}, "amend": {"charter", "reason"},
                  "reconcile": {"run_id", "resolution", "reason"}, "start": {"executor", "model", "connection_id", "max_steps", "max_seconds", "allow_unknown_cost"},
                  "api_connection": {"connection_id", "config", "api_key", "reason", "bind_default"}, "api_binding": {"connection_id", "reason"},
                  "api_test": {"connection_id", "allow_unknown_cost", "tools"}, "company_usage": {"run_id", "input_tokens", "output_tokens", "reason"},
                  "controller_descriptor": {"controller_ref", "reason"},
                  "respond_request": {"request_id", "status", "reason"}}
        optional = {"event": {"event_id"}, "start": {"model", "connection_id", "max_seconds", "allow_unknown_cost"},
                    "api_connection": {"api_key", "bind_default"}, "api_test": {"connection_id", "tools"}}
        require(set(data) <= fields[kind] and fields[kind] - optional.get(kind, set()) <= set(data), "命令字段缺失或不支持")
        if kind == "pause":
            e.set_paused(True)
        elif kind == "event":
            text(data["content"], "事件内容")
            text(data["source"], "事件来源", 1000)
            require(type(data["simulated"]) is bool, "事件需要显式布尔模拟标记")
            require(data["kind"] in ("opinion", "fact", "external_feedback"), "不支持此输入事件类型")
            e.add_event(data.get("event_id", request["id"]), data["kind"], {k: data[k] for k in ("content", "source", "simulated")})
        elif kind in ("start", "api_test"):
            require(type(data.get("max_steps", 1)) is int and 1 <= data.get("max_steps", 1) <= 10000, "运行需要有限正整数步数")
            require(type(data.get("max_seconds", 0)) is int and 0 <= data.get("max_seconds", 0) <= 86400, "等待窗口必须为 0–86400 秒")
            require(type(data.get("allow_unknown_cost", False)) is bool, "费用确认必须为布尔值")
            state = e.state()
            with e.transaction() as cx:
                budget = e._budget(cx, state)
                require(not budget["blocked_reason"], budget["blocked_reason"])
            require(not any(r["status"] == "unknown" for r in e.runs()), "执行结果未知；先核对原执行")
            require(data.get("max_steps", 1) <= budget["max_calls"] - budget["calls_reserved"], "本次步数超过剩余调用额度")
            executor_name = "api" if kind == "api_test" else data["executor"]
            require(executor_name == "api" or not data.get("connection_id"), "此执行器不使用 API 连接")
            if executor_name == "api":
                require(self.enable_api and data.get("allow_unknown_cost") is True, "宿主未启用 API 或未接受有限调用费用未知")
                require("max_cost" not in state["resources"], "API 不支持金额硬上限")
                require(data.get("model") in (None, ""), "API 模型由连接配置固定；请选择或更新连接")
                connection = resolve_connection(e, data.get("connection_id"))
                executor = APIExecutor(e.root, connection)
                if kind == "start":
                    from .harness import HarnessExecutor
                    executor = HarnessExecutor(e, connection)
                    e.set_paused(False)
                else:
                    require(type(data.get("tools", False)) is bool, "工具测试选项必须为布尔值")
                    executor.tool_probe = data.get("tools", False)
                return executor
            elif executor_name == "codex":
                require(self.enable_codex and data.get("allow_unknown_cost") is True, "宿主未启用 Codex 或未接受有限调用费用未知")
                require("max_cost" not in state["resources"], "此执行器不支持金额硬上限")
                model = model_name(data.get("model", state.get("execution_config", {}).get("codex_model")))
            else:
                require(data["executor"] == "fixture" and self.fixture is not None, "执行器未配置")
                require(data.get("model") in (None, ""), "Fixture 不使用真实模型；请清空本次模型")
                model = None
            executor = self.executor_factory(e, data | {"model": model})
            e.set_paused(False)
            return executor
        else:
            key = (e.root / "board.key").read_text(encoding="utf-8").strip()
            if kind == "controller_descriptor":
                from .au_contract import configure_descriptor
                configure_descriptor(e, key, data["controller_ref"], data["reason"], request["base_version"])
            elif kind == "respond_request":
                from .support_requests import respond
                respond(e, key, data["request_id"], data["status"], data["reason"], request["base_version"])
            elif kind == "resources":
                require(set(data["resources"]) == {"max_calls", "timeout_seconds"}, "工作台仅支持调用次数与超时；金额未知")
                require(type(data["resources"].get("max_calls")) is int and data["resources"]["max_calls"] >= len(e.runs()), "新上限不能低于累计占用")
                e.configure_resources(key, data["resources"], data["reason"])
            elif kind == "amend":
                e.amend(key, data["charter"], data["reason"])
            elif kind == "model":
                e.configure_model(key, data["model"], data["reason"])
            elif kind == "api_connection":
                require(self.enable_api, "宿主未启用 API")
                require(type(data.get("bind_default", False)) is bool, "默认连接标记须为布尔值")
                result = configure_connection(e, key, data["connection_id"], data["config"], data["reason"], data.get("api_key"))
                if data.get("bind_default"):
                    bind_connection(e, key, data["connection_id"], data["reason"])
                return result
            elif kind == "company_usage":
                from .company import resolve_usage
                resolve_usage(e, key, data["run_id"], data["input_tokens"], data["output_tokens"], data["reason"])
            elif kind == "api_binding":
                require(self.enable_api, "宿主未启用 API")
                bind_connection(e, key, data["connection_id"], data["reason"])
            else:
                e.reconcile(key, data["run_id"], data["resolution"], data["reason"])

    def _executor(self, e, data):
        if data["executor"] == "codex":
            return CodexExecutor(e.root, model=data.get("model"))
        if e.state().get("company"):
            from .novel_demo import NovelDemoExecutor
            return NovelDemoExecutor()
        used = len([r for r in e.runs() if r["executor"] == "fixture"])
        return FixtureExecutor(copy.deepcopy(self.fixture[used:]))

    def _probe_job(self, e, request, executor, guard):
        outcome = {"status": "unknown", "message": "连接测试中断；请核对原执行记录"}
        try:
            with activity(e):
                if getattr(executor, "tool_probe", False):
                    from .harness import test_tool_connection
                    outcome = test_tool_connection(e, executor)
                else:
                    outcome = test_connection(e, executor)
        except (Rejected, OSError, ValueError):
            outcome = {"status": "blocked", "message": "连接测试受阻；查看资源和原执行状态"}
        finally:
            try:
                with e.transaction() as cx:
                    receipt = json.loads(cx.execute("SELECT receipt FROM commands WHERE id=?", (request["id"],)).fetchone()[0])
                    receipt.update(outcome, ended_at=now())
                    cx.execute("UPDATE commands SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
            finally:
                guard.__exit__(None, None, None)

    def _job(self, e, request, executor, guard):
        actions = []
        failure = None
        status, message = "succeeded", "有限运行已结束"
        try:
            with activity(e):
                e.recover()  # The exclusive lock proves there is no live owner. Unknown remains blocked.
                deadline = time.monotonic() + request["data"].get("max_seconds", 0)
                calls = 0
                while calls < request["data"]["max_steps"]:
                    try:
                        action = step(e, executor)
                    except Rejected as error:
                        action = {"action": "blocked", "reason": str(error), "failure": runtime_failure(error)}
                    # Do not expose private executor diagnostics in browser receipts.
                    actions.append({k: action[k] for k in ("action", "run_id", "work_id", "failure") if k in action})
                    if action["action"] == "wait" and time.monotonic() < deadline:
                        time.sleep(min(0.5, max(0, deadline - time.monotonic())))
                        actions.pop()
                        continue
                    if action["action"] in ("blocked", "wait", "paused"):
                        if action["action"] == "blocked":
                            failure = action.get("failure")
                            status, message = "blocked", failure["message"] if failure else "运行受阻；查看组织状态及宿主执行记录"
                        break
                    calls += 1
                    if request["data"].get("max_seconds") and time.monotonic() >= deadline:
                        break
                if actions and actions[-1]["action"] == "correction":
                    actions[-1]["action"] = "blocked"
                    failure = actions[-1].get("failure")
                    status, message = "blocked", "本次调用额度或运行时间已用完；组织提议尚待修正"
                elif actions and actions[-1]["action"] == "progress":
                    message = "本次有限调用已结束；筹建或任务进度已保存，继续运行可接续"
        except BaseException:
            status, message = "unknown", "宿主作业中断；保留原执行记录并核对，不能推断远程取消"
        finally:
            try:
                with e.transaction() as cx:
                    row = cx.execute("SELECT receipt FROM commands WHERE id=?", (request["id"],)).fetchone()
                    receipt = json.loads(row[0])
                    receipt.update(status=status, message=message, ended_at=now(), actions=actions)
                    if failure:
                        receipt["failure"] = failure
                    cx.execute("UPDATE commands SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
            finally:
                guard.__exit__(None, None, None)

    def join_jobs(self):
        with self.mutex:
            jobs = list(self.jobs)
        for thread in jobs:
            thread.join(timeout=10)
            require(not thread.is_alive(), "运行作业仍在等待回执")

    def close(self):
        if not self.closed:
            # Graceful host shutdown stops further dispatch, retaining in-flight results.
            for item in self.organizations():
                Engine(self.root / item["folder"]).set_paused(True)
            self.join_jobs()
            self._guard.__exit__(None, None, None)
            self.closed = True
