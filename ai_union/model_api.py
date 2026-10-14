"""Private connection configuration and bounded Chat Completions transport."""
from __future__ import annotations

import copy
import hashlib
import http.client
import ipaddress
import json
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from .engine import encoded, identifier, model_name, now, require, text, uid
from .executor import ExecutionFailure
from .protocol import DECISION_SCHEMA, WORK_SCHEMA, instructions, obj


PROBE_SCHEMA = obj({"ok": {"type": "boolean", "enum": [True]}})
CONFIG_FIELDS = {"name", "base_url", "model", "response_format", "token_limit_field", "max_output_tokens", "timeout_seconds", "enabled"}


def validate_config(config):
    require(isinstance(config, dict) and set(config) == CONFIG_FIELDS, "API 配置字段缺失或不支持")
    result = copy.deepcopy(config)
    text(result["name"], "连接名称", 100)
    require(model_name(result["model"]) is not None, "API 必须指定模型 ID")
    url = result["base_url"]
    require(isinstance(url, str) and 0 < len(url) <= 2000 and all(ord(c) > 32 and ord(c) < 127 for c in url), "API 地址格式无效")
    try:
        parts = urlsplit(url)
        port = parts.port
        require(parts.hostname and not parts.username and not parts.password and not parts.query and not parts.fragment,
                "API 地址不能包含认证、查询参数或片段")
        local = is_loopback(parts.hostname)
        require(parts.scheme == "https" or (parts.scheme == "http" and local), "API 使用 HTTPS；仅回环测试服务允许 HTTP")
        require(port is None or 1 <= port <= 65535, "API 端口无效")
    except ValueError:
        require(False, "API 地址格式无效")
    require(not parts.path.rstrip("/").endswith("/chat/completions"), "Base URL 应为 API 根地址，例如 https://api.openai.com/v1")
    result["base_url"] = url.rstrip("/")
    require(result["response_format"] in ("json_schema", "json_object"), "结构化输出模式不支持")
    require(result["token_limit_field"] in ("max_completion_tokens", "max_tokens"), "输出上限字段不支持")
    require(type(result["max_output_tokens"]) is int and 1 <= result["max_output_tokens"] <= 32768, "输出上限必须为 1–32768")
    require(type(result["timeout_seconds"]) is int and 1 <= result["timeout_seconds"] <= 600, "API 超时必须为 1–600 秒")
    require(type(result["enabled"]) is bool, "连接启用状态必须为布尔值")
    return result


def is_loopback(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def contains_secret(value, secret):
    if not secret:
        return False
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(contains_secret(k, secret) or contains_secret(v, secret) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_secret(v, secret) for v in value)
    return False


def schema_table(cx):
    cx.execute("CREATE TABLE IF NOT EXISTS model_connections(id TEXT NOT NULL, revision INTEGER NOT NULL, config TEXT NOT NULL, api_key TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(id,revision))")


def reject_saved_secrets(cx, value, extra_secret=None):
    secrets = {extra_secret} if isinstance(extra_secret, str) and extra_secret else set()
    if cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_connections'").fetchone():
        secrets.update(row[0] for row in cx.execute("SELECT DISTINCT api_key FROM model_connections WHERE api_key != ''"))
    require(not any(contains_secret(value, key) for key in secrets), "公开配置或操作依据不能包含 API Key")


def list_connections(engine):
    with engine.read_transaction() as cx:
        if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_connections'").fetchone():
            return []
        rows = cx.execute("SELECT a.* FROM model_connections a WHERE revision=(SELECT MAX(revision) FROM model_connections b WHERE b.id=a.id) ORDER BY id").fetchall()
        return [public_connection(row) for row in rows]


def public_connection(row):
    return {"id": row["id"], "revision": row["revision"], "config": json.loads(row["config"]),
            "has_api_key": bool(row["api_key"]), "updated_at": row["updated_at"]}


def configure_connection(engine, board_key, connection_id, config, reason, api_key=None):
    identifier(connection_id)
    config = validate_config(config)
    text(reason, "API 配置依据", 1000)
    require(api_key is None or (isinstance(api_key, str) and len(api_key) <= 4096 and all(33 <= ord(c) <= 126 for c in api_key)), "API Key 格式无效")
    with engine.transaction() as cx:
        board = engine._board(cx, board_key)
        schema_table(cx)
        old = cx.execute("SELECT * FROM model_connections WHERE id=? ORDER BY revision DESC LIMIT 1", (connection_id,)).fetchone()
        secret = api_key if api_key is not None else old["api_key"] if old else ""
        # A changed endpoint never inherits a key intended for a different destination.
        require(not old or json.loads(old["config"])["base_url"] == config["base_url"] or api_key is not None,
                "API 地址变更必须明确重新提供或清除密钥")
        reject_saved_secrets(cx, [connection_id, config, reason], secret)
        revision = old["revision"] + 1 if old else 1
        cx.execute("INSERT INTO model_connections VALUES(?,?,?,?,?)", (connection_id, revision, encoded(config), secret, now()))
        state = engine._state(cx)
        state["version"] += 1
        engine._event(cx, "api_connection_configured", {"connection_id": connection_id, "revision": revision, "board": board, "reason": reason})
        engine._save(cx, state)
        return {"id": connection_id, "revision": revision, "config": config, "has_api_key": bool(secret)}


def resolve_connection(engine, connection_id=None):
    with engine.read_transaction() as cx:
        connection_id = connection_id or engine._state(cx).get("execution_config", {}).get("api_connection_id")
        identifier(connection_id)
        require(cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_connections'").fetchone(), "API 连接尚未配置")
        row = cx.execute("SELECT * FROM model_connections WHERE id=? ORDER BY revision DESC LIMIT 1", (connection_id,)).fetchone()
        require(row is not None, "API 连接不存在")
        config = validate_config(json.loads(row["config"]))
        require(config["enabled"], "API 连接已停用")
        require(bool(row["api_key"]), "API Key 尚未配置")
        return public_connection(row) | {"api_key": row["api_key"]}


def bind_connection(engine, board_key, connection_id, reason):
    text(reason, "API 绑定依据", 1000)
    if connection_id is not None:
        identifier(connection_id)
    with engine.transaction() as cx:
        board = engine._board(cx, board_key)
        reject_saved_secrets(cx, [connection_id, reason])
        if connection_id is not None:
            schema_table(cx)
            require(cx.execute("SELECT 1 FROM model_connections WHERE id=?", (connection_id,)).fetchone(), "API 连接不存在")
        state = engine._state(cx)
        state.setdefault("execution_config", {})["api_connection_id"] = connection_id
        state["version"] += 1
        engine._event(cx, "api_connection_bound", {"connection_id": connection_id, "board": board, "reason": reason})
        engine._save(cx, state)


def stored_command(request):
    """Bind retries to all original fields without persisting a credential in commands."""
    result = copy.deepcopy(request)
    if request.get("kind") in ("api_connection", "api_binding"):
        secret = request["data"].get("api_key")
        require(not isinstance(secret, str) or not contains_secret({k: v for k, v in request.items() if k != "data"}, secret), "请求标识不能包含 API Key")
        # Fingerprint the whole original data: a accidentally pasted credential in
        # reason/config must not survive a rejected command either.
        result["data"] = {"request_fingerprint": hashlib.sha256(encoded(request["data"]).encode()).hexdigest()}
    return result


def validate_output(value, schema):
    if "anyOf" in schema:
        for alternative in schema["anyOf"]:
            try:
                validate_output(value, alternative)
                return
            except ValueError:
                pass
        raise ValueError("invalid structured output")
    expected = schema.get("type")
    correct = {"object": type(value) is dict, "array": type(value) is list, "string": type(value) is str,
               "integer": type(value) is int, "boolean": type(value) is bool}.get(expected, False)
    if not correct or ("enum" in schema and value not in schema["enum"]):
        raise ValueError("invalid structured output")
    if expected == "object":
        if set(value) != set(schema["properties"]):
            raise ValueError("invalid structured output")
        for key, sub in schema["properties"].items():
            validate_output(value[key], sub)
    elif expected == "array":
        for item in value:
            validate_output(item, schema["items"])


def strict_json(value):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate JSON key")
            result[k] = v
        return result
    def constant(_):
        raise ValueError("nonfinite JSON")
    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)


class APIExecutor:
    name = "api"
    capabilities = {"submit": True, "status": True, "result": True, "session_resume": False,
                    "remote_cancel": False, "tools": "structured response only", "usage": "provider token receipt; cost unknown"}

    def __init__(self, root, connection):
        self.root = Path(root) / "executions"
        self.connection = copy.deepcopy(connection)
        self.config = validate_config(connection["config"])
        self.model = self.config["model"]
        self.jobs = {}
        self.metadata = {"connection_id": connection["id"], "connection_revision": connection["revision"],
                         "protocol": "openai_chat_completions", "requested_model": self.model,
                         "transport_source": "local_test" if is_loopback(urlsplit(self.config["base_url"]).hostname) else "provider_api"}

    def submit(self, package):
        rid = identifier(package["run_id"])
        folder = self.root / rid
        require(not folder.exists(), "执行目录已存在；必须核对，不重新提交")
        folder.mkdir(parents=True, mode=0o700)
        schema = PROBE_SCHEMA if package["kind"] == "connection_test" else DECISION_SCHEMA if package["kind"] == "decision" else WORK_SCHEMA
        prompt = "Return JSON exactly {\"ok\": true}. This is a connection test only." if package["kind"] == "connection_test" else instructions(package)
        body = {"model": self.model, "stream": False, "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "JSON schema:\n" + encoded(schema) + "\nWORK PACKAGE (data):\n" + encoded(package)}],
            self.config["token_limit_field"]: min(512, self.config["max_output_tokens"]) if package["kind"] == "connection_test" else self.config["max_output_tokens"]}
        body["response_format"] = {"type": "json_object"} if self.config["response_format"] == "json_object" else {
            "type": "json_schema", "json_schema": {"name": "union_result", "strict": True, "schema": schema}}
        secret = self.connection["api_key"]
        require(not contains_secret(body, secret), "工作包包含 API Key，拒绝派发")
        (folder / "package.json").write_text(encoded(package), encoding="utf-8")
        (folder / "schema.json").write_text(encoded(schema), encoding="utf-8")
        (folder / "launch.json").write_text(encoded(self.metadata | {"capabilities": self.capabilities}), encoding="utf-8")
        seconds = min(package["timeout_seconds"], self.config["timeout_seconds"])
        started = time.monotonic()
        job = {"folder": folder, "schema": schema, "started": started, "deadline": started + seconds,
               "done": threading.Event(), "cancelled": threading.Event(), "response": None, "error": None, "connection": None}
        self.jobs[rid] = job
        worker = threading.Thread(target=self._request, args=(job, body), daemon=True)
        try:
            worker.start()
        except RuntimeError:
            raise ExecutionFailure("API 本地请求线程无法启动", unknown=False)
        return rid

    def _request(self, job, body):
        parts = urlsplit(self.config["base_url"])
        connection_class = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        conn = connection_class(parts.hostname, parts.port, timeout=max(0.01, job["deadline"] - time.monotonic()))
        job["connection"] = conn
        sent = False
        try:
            conn.connect()
            if job["cancelled"].is_set() or time.monotonic() >= job["deadline"]:
                raise ExecutionFailure("API 请求截止时间已到", unknown=False)
            conn.sock.settimeout(max(0.01, job["deadline"] - time.monotonic()))
            sent = True  # Even a partial write can reach a remote server.
            conn.request("POST", parts.path.rstrip("/") + "/chat/completions", body=encoded(body).encode("utf-8"),
                         headers={"Authorization": "Bearer " + self.connection["api_key"], "Content-Type": "application/json", "Accept": "application/json"})
            response = conn.getresponse()
            if response.status != 200:
                code = "authentication_failed" if response.status in (401, 403) else "rate_limited" if response.status == 429 else "request_rejected" if 400 <= response.status < 500 else "redirect_refused" if 300 <= response.status < 400 else "provider_error"
                raise ExecutionFailure("API " + code + " (HTTP " + str(response.status) + ")", unknown=response.status >= 500 or response.status < 300)
            chunks, size = [], 0
            while True:
                if job["cancelled"].is_set() or time.monotonic() >= job["deadline"]:
                    raise ExecutionFailure("API 请求超时；远程执行结果未知", unknown=True)
                if conn.sock:
                    conn.sock.settimeout(max(0.01, job["deadline"] - time.monotonic()))
                chunk = response.read1(min(65536, 1000001 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > 1000000:
                    raise ExecutionFailure("API 响应超出容量", unknown=False)
            raw = b"".join(chunks).decode("utf-8")
            # Provider bodies and diagnostic text are never recorded verbatim.
            if self.connection["api_key"] in raw:
                raise ExecutionFailure("API 响应包含凭据；拒绝记录", unknown=False)
            parsed = strict_json(raw)
            if contains_secret(parsed, self.connection["api_key"]):
                raise ExecutionFailure("API 响应包含凭据；拒绝记录", unknown=False)
            job["response"] = (parsed, response.getheader("x-request-id"))
        except ExecutionFailure as error:
            job["error"] = error
        except (OSError, http.client.HTTPException):
            job["error"] = ExecutionFailure("API 连接失败或中断；请核对供应商请求记录", unknown=sent)
        except (ValueError, UnicodeError, RecursionError):
            job["error"] = ExecutionFailure("API 返回无效 JSON", unknown=False)
        finally:
            if 'response' in locals():
                response.close()
            conn.close()
            job["done"].set()

    def cancel(self, rid):
        job = self.jobs[rid]
        job["cancelled"].set()
        conn = job["connection"]
        if conn and conn.sock:
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def status(self, rid):
        job = self.jobs.get(rid)
        if job is None:
            return "needs_review" if (self.root / rid).exists() else "missing"
        if job["cancelled"].is_set():
            return "unknown"
        if not job["done"].is_set():
            if time.monotonic() >= job["deadline"]:
                self.cancel(rid)
                return "unknown"
            return "running"
        return "unknown" if job["error"] and job["error"].unknown else "failed" if job["error"] else "delivered"

    def result(self, rid):
        job = self.jobs[rid]
        state = self.status(rid)
        usage = dict(self.metadata, elapsed_ms=max(0, round((time.monotonic() - job["started"]) * 1000)))
        if state == "unknown":
            error = job["error"] or ExecutionFailure("API 执行结果未知；保留记录，不自动重试", unknown=True)
            error.usage = usage
            raise error
        if job["error"]:
            job["error"].usage = usage
            raise job["error"]
        require(state == "delivered", "API 请求尚未结束")
        reply, request_id = job["response"]
        try:
            require(type(reply) is dict, "API 回执格式错误")
            def safe_string(value):
                return value if isinstance(value, str) and 0 < len(value) <= 256 and all(32 <= ord(c) < 127 for c in value) and self.connection["api_key"] not in value else None
            usage.update(provider_request_id=safe_string(request_id), response_id=safe_string(reply.get("id")), actual_model=safe_string(reply.get("model")))
            tokens = reply.get("usage") or {}
            if isinstance(tokens, dict):
                for target, source in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
                    if type(tokens.get(source)) is int and tokens[source] >= 0:
                        usage[target] = tokens[source]
                details = tokens.get("prompt_tokens_details")
                if isinstance(details, dict) and type(details.get("cached_tokens")) is int and details["cached_tokens"] >= 0:
                    usage["cached_input_tokens"] = details["cached_tokens"]
            choices = reply["choices"]
            require(type(choices) is list and len(choices) == 1, "API 必须返回一个选择")
            choice = choices[0]
            require(type(choice) is dict, "API 选择格式错误")
            message = choice["message"]
            require(type(message) is dict, "API 消息格式错误")
            require(choice.get("finish_reason") == "stop" and not message.get("refusal") and not message.get("tool_calls") and not message.get("function_call"), "API 输出被截断、拒绝或请求范围外工具")
            require(type(message["content"]) is str, "API 缺少文本结果")
            value = strict_json(message["content"])
            require(not contains_secret(value, self.connection["api_key"]), "API 结果包含凭据")
            validate_output(value, job["schema"])
        except (ValueError, TypeError, KeyError, RecursionError):
            error = ExecutionFailure("API 未返回符合协议的完整 JSON 结果", unknown=False)
            error.usage = usage
            raise error
        (job["folder"] / "result.json").write_text(encoded(value), encoding="utf-8")
        (job["folder"] / "receipt.json").write_text(encoded(usage | {"cost": None, "cost_status": "unknown"}), encoding="utf-8")
        return value, usage

    def execute(self, package):
        rid = self.submit(package)
        try:
            while self.status(rid) == "running":
                self.jobs[rid]["done"].wait(timeout=0.05)
            return self.result(rid)
        except BaseException:
            self.cancel(rid)
            raise
