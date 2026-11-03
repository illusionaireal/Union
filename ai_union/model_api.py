"""Private connection configuration and bounded Chat Completions transport."""
from __future__ import annotations

import copy
import base64
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import getproxies, proxy_bypass

from .engine import Rejected, encoded, identifier, model_name, now, require, text, uid
from .executor import ExecutionFailure
from .failures import issue
from .agent_protocol import compile_tool, instructions, model_input, tools_for, work_result
from . import catalog as model_catalog
from .model_protocols import PROTOCOLS, encode_request, decode_response


OPTIONAL_CONFIG = {'response_format','api_key_env','api_key_file','auth_type','provider','protocol','allow_private_http','billing','context_policy'}
CONFIG_FIELDS = {"name", "base_url", "model", "response_format", "token_limit_field", "max_output_tokens", "timeout_seconds", "api_key_env", "enabled"} | OPTIONAL_CONFIG
ROLES = ("planner", "worker", "reviewer")
ROLE_BY_KIND = {"work": "worker", "decision": "planner", "connection_test": None}
MAX_FALLBACKS = 3


def api_connection(parts, timeout):
    """Honor the host's HTTPS proxy without weakening destination TLS verification."""
    if parts.scheme != "https":
        return http.client.HTTPConnection(parts.hostname, parts.port, timeout=timeout)
    proxy = getproxies().get("https")
    if not proxy or is_loopback(parts.hostname) or proxy_bypass(parts.hostname):
        return http.client.HTTPSConnection(parts.hostname, parts.port, timeout=timeout)
    try:
        target = urlsplit(proxy if "://" in proxy else "http://" + proxy)
        if target.scheme != "http" or not target.hostname or target.path not in ("", "/") or target.query or target.fragment:
            raise ValueError("Unsupported proxy")
        connection = http.client.HTTPSConnection(target.hostname, target.port or 80, timeout=timeout)
        headers = {}
        if target.username is not None:
            credentials = unquote(target.username) + ":" + unquote(target.password or "")
            headers["Proxy-Authorization"] = "Basic " + base64.b64encode(credentials.encode()).decode("ascii")
        connection.set_tunnel(parts.hostname, parts.port or 443, headers=headers)
        return connection
    except ValueError:
        # Never silently bypass a configured proxy or expose its credentials.
        raise OSError("HTTPS proxy configuration is unsupported") from None


def validate_config(config):
    if isinstance(config, dict) and config.get('backend') == 'modeld':
        from .model_service import validate_service_config
        return validate_service_config(config)
    require(isinstance(config, dict) and CONFIG_FIELDS - OPTIONAL_CONFIG <= set(config) <= CONFIG_FIELDS, "API 配置字段缺失或不支持")
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
        private = False
        try:
            address=ipaddress.ip_address(parts.hostname)
            private=any(address in network for network in (ipaddress.ip_network('10.0.0.0/8'),ipaddress.ip_network('172.16.0.0/12'),ipaddress.ip_network('192.168.0.0/16'),ipaddress.ip_network('fc00::/7')) if address.version==network.version)
        except ValueError: pass
        require(type(result.get('allow_private_http',False)) is bool, '内网HTTP声明无效')
        require(parts.scheme == "https" or (parts.scheme == "http" and (local or private and result.get('allow_private_http') is True)), "API 使用HTTPS；内网HTTP须明确声明并填写私有IP")
        require(port is None or 1 <= port <= 65535, "API 端口无效")
    except ValueError:
        require(False, "API 地址格式无效")
    result["base_url"] = url.rstrip("/")
    for suffix in ('/chat/completions','/responses','/messages'):
        if result['base_url'].endswith(suffix): result['base_url']=result['base_url'][:-len(suffix)]
    require(result.get('protocol','openai_chat_completions') in PROTOCOLS, '模型协议不支持')
    require(result.get('auth_type','key') in ('key','none'), '认证方式不支持')
    if 'provider' in result: identifier(result['provider'])
    if 'context_policy' in result:
        from .model_context import validate_policy
        validate_policy(result['context_policy'])
    if 'billing' in result:
        from .model_billing import validate_billing
        validate_billing(result['billing'])
    require(result.get("response_format", "agent") in ("agent", "json_schema", "json_object"), "输出模式不支持")
    # Read old connection records without perpetuating their forced output mode.
    result["response_format"] = "agent"
    require(result["token_limit_field"] in ("max_completion_tokens", "max_tokens"), "输出上限字段不支持")
    require(type(result["max_output_tokens"]) is int and 1 <= result["max_output_tokens"] <= 32768, "输出上限必须为 1–32768")
    require(type(result["timeout_seconds"]) is int and 1 <= result["timeout_seconds"] <= 600, "API 超时必须为 1–600 秒")
    if "api_key_env" in result:
        require(isinstance(result["api_key_env"], str)
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", result["api_key_env"]) is not None,
                "API Key 环境变量名无效")
        allowed={name.strip() for name in os.environ.get('UNION_MODEL_KEY_ENV_ALLOWLIST','').split(',')}
        name=result['api_key_env']
        require(name not in {'UNION_MODEL_CATALOG','UNION_MODEL_CREDENTIAL_DIR','UNION_MODEL_KEY_ENV_ALLOWLIST'} and
                (name.startswith('UNION_MODEL_') and name.endswith(('_KEY','_TOKEN')) or name in allowed), '此环境变量未获宿主模型凭据授权')
    if 'api_key_file' in result: identifier(result['api_key_file'])
    require(not (result.get('api_key_env') and result.get('api_key_file')), '凭据引用只能选择一种来源')
    require(result.get('auth_type','key')!='none' or not (result.get('api_key_env') or result.get('api_key_file')), '无需认证不能同时引用凭据')
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
        for row in cx.execute("SELECT api_key, config FROM model_connections"):
            if json.loads(row[1]).get('api_key_file'):
                file_secret, _ = connection_key({'api_key':row[0], 'config':row[1]})
                if file_secret: secrets.add(file_secret)
            if row[0]:
                secrets.add(row[0])
            # An environment reference is public as a name but its value is not.
            name = json.loads(row[1]).get("api_key_env")
            if name and os.environ.get(name):
                secrets.add(os.environ[name])
    require(not any(contains_secret(value, key) for key in secrets), "公开配置或操作依据不能包含 API Key")


def list_connections(engine):
    with engine.read_transaction() as cx:
        if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_connections'").fetchone():
            return []
        rows = cx.execute("SELECT a.* FROM model_connections a WHERE revision=(SELECT MAX(revision) FROM model_connections b WHERE b.id=a.id) ORDER BY id").fetchall()
        linked = cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_gateway_refs'").fetchone()
        result = []
        for row in rows:
            item = public_connection(row)
            ref = cx.execute("SELECT reference FROM model_gateway_refs WHERE id=? AND revision=?", (row["id"], row["revision"])).fetchone() if linked else None
            if ref:
                item["gateway_ref"] = json.loads(ref[0])
            result.append(item)
        return result


def connection_key(row):
    """Resolve a credential at use time; an environment reference is never persisted."""
    config = json.loads(row["config"])
    if config.get('backend') == 'modeld': return '', 'model_service'
    if config.get('auth_type')=='none': return '', 'none'
    if row["api_key"]:
        return row["api_key"], "inline"
    if config.get('api_key_file'):
        directory=os.environ.get('UNION_MODEL_CREDENTIAL_DIR')
        if not directory: return '', 'missing_file'
        root=Path(directory).resolve(); path=root/config['api_key_file']
        require(not path.is_symlink() and path.resolve().parent==root, '凭据文件引用越界')
        try:
            require(path.stat().st_size<=4096, '凭据文件过大')
            if os.name!='nt': require(path.stat().st_mode & 0o077 == 0, '凭据文件需为私有权限')
            value=path.read_text(encoding='utf-8').strip()
        except OSError: return '', 'missing_file'
        require(value and all(33<=ord(c)<=126 for c in value), '凭据文件内容无效')
        return value, 'file'
    name = config.get("api_key_env")
    if not name:
        return "", None
    value = os.environ.get(name, "")
    return (value, "env") if value else ("", "missing")


def public_connection(row):
    config = validate_config(json.loads(row["config"]))
    key, source = connection_key(row)
    # Read-only metadata; an unknown model stays null instead of being guessed.
    return {"id": row["id"], "revision": row["revision"], "config": config,
            "has_api_key": bool(key), "key_source": source, "updated_at": row["updated_at"],
            "catalog": model_catalog.metadata(config["model"],config.get('provider'))}


def configure_connection(engine, board_key, connection_id, config, reason, api_key=None, *, gateway_ref=None):
    identifier(connection_id)
    config = validate_config(config)
    service = config.get('backend') == 'modeld'
    if service:
        with engine.read_transaction() as cx:
            engine._board(cx, board_key)
        require(api_key in (None, '') and gateway_ref is None, '托管模型不能携带 API 密钥或网关引用')
        if config['enabled']:
            from .model_service import ModelServiceClient, ServiceError
            try:
                grant = ModelServiceClient().call('GET', '/v1/grants/' + config['grant_ref'], admin=True)
            except ServiceError:
                raise Rejected('模型使用授权暂不可核实') from None
            require(grant['au_id'] == engine.state()['id'] and grant['revision'] == config['grant_revision']
                    and not grant['revoked_at'] and config['model'] in grant['model_ids'], '模型使用授权不匹配或已撤销')
    text(reason, "API 配置依据", 1000)
    require(api_key is None or (isinstance(api_key, str) and len(api_key) <= 4096 and all(33 <= ord(c) <= 126 for c in api_key)), "API Key 格式无效")
    with engine.transaction() as cx:
        board = engine._board(cx, board_key)
        schema_table(cx)
        old = cx.execute("SELECT * FROM model_connections WHERE id=? ORDER BY revision DESC LIMIT 1", (connection_id,)).fetchone()
        if service or config.get('auth_type')=='none':
            require(api_key in (None,''), '无需认证不能同时提供密钥')
            secret=''
        elif config.get("api_key_env") or config.get('api_key_file'):
            require(api_key is None, "环境变量引用与内联密钥只能二选一")
            secret = ""
        else:
            secret = api_key if api_key is not None else old["api_key"] if old else ""
        # A changed endpoint never inherits a key intended for a different destination.
        require(not old or (json.loads(old["config"]).get("base_url") == config.get("base_url") and json.loads(old['config']).get('protocol','openai_chat_completions')==config.get('protocol','openai_chat_completions')) or api_key is not None or config.get("api_key_env") or config.get('api_key_file'),
                "API 地址变更必须明确重新提供或清除密钥")
        effective_secret, _ = connection_key({'api_key':secret, 'config':encoded(config)})
        reject_saved_secrets(cx, [connection_id, config, reason], effective_secret or secret)
        revision = old["revision"] + 1 if old else 1
        cx.execute("INSERT INTO model_connections VALUES(?,?,?,?,?)", (connection_id, revision, encoded(config), secret, now()))
        if gateway_ref is not None:
            cx.execute("CREATE TABLE IF NOT EXISTS model_gateway_refs(id TEXT NOT NULL, revision INTEGER NOT NULL, reference TEXT NOT NULL, PRIMARY KEY(id,revision))")
            cx.execute("INSERT INTO model_gateway_refs VALUES(?,?,?)", (connection_id, revision, encoded(gateway_ref)))
        state = engine._state(cx)
        state["version"] += 1
        engine._event(cx, "api_connection_configured", {"connection_id": connection_id, "revision": revision, "board": board, "reason": reason})
        engine._save(cx, state)
        key, source = connection_key({"api_key": secret, "config": encoded(config)})
        return {"id": connection_id, "revision": revision, "config": config,
                "has_api_key": bool(key), "key_source": source}


def _role_connection_id(execution, role):
    if role is None:
        return execution.get("api_connection_id")
    identifier(role)
    slot = (execution.get("roles") or {}).get(role) or {}
    return slot.get("connection_id")


def _resolved(cx, connection_id):
    row = cx.execute("SELECT * FROM model_connections WHERE id=? ORDER BY revision DESC LIMIT 1", (connection_id,)).fetchone()
    require(row is not None, "API 连接不存在")
    config = validate_config(json.loads(row["config"]))
    require(config["enabled"], "API 连接已停用")
    secret, source = connection_key(row)
    if source == "missing":
        require(False, "API Key 环境变量未设置或为空：" + config["api_key_env"])
    require(source in ('none', 'model_service') or bool(secret), "API Key 或宿主凭据文件尚未配置")
    return public_connection(row) | {"api_key": secret}


def resolve_connection(engine, connection_id=None, role=None):
    """Resolve a role's credential, with availability fallback only.

    A connection that cannot serve a request at all (missing, disabled or without a
    credential) may be replaced by the configured chain. Runtime failures are never
    retried here: an unknown outcome still has to be reconciled.
    """
    with engine.read_transaction() as cx:
        require(cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_connections'").fetchone(), "API 连接尚未配置")
        if connection_id is not None:
            identifier(connection_id)
            return _resolved(cx, connection_id)
        execution = engine._state(cx).get("execution_config", {})
        preferred = connection_id or _role_connection_id(execution, role) or execution.get("api_connection_id")
        identifier(preferred)
        chain = [preferred] + [item for item in _fallback_ids(execution, role) if item != preferred]
        reason = None
        for candidate in chain:
            try:
                connection = _resolved(cx, candidate)
            except Rejected as error:
                reason = reason or error
                continue
            if candidate != preferred:
                connection["fallback_from"] = preferred
            return connection
        raise reason


def _fallback_ids(execution, role=None):
    slot=(execution.get('roles') or {}).get(role) or {}
    return slot.get('fallbacks', execution.get('fallbacks') or [])


def resolve_chain(engine, *, role=None):
    """Primary plus the fallbacks that can actually serve a request.

    The primary is resolved strictly (an unusable role or default is an error);
    fallbacks that cannot serve a request are skipped so one stale entry cannot
    disable the whole chain.
    """
    primary = resolve_connection(engine, role=role)
    with engine.read_transaction() as cx:
        execution = engine._state(cx).get("execution_config", {})
        candidates = [item for item in _fallback_ids(execution, role) if item != primary["id"]]
        fallbacks = []
        for candidate in candidates:
            try:
                fallbacks.append(_resolved(cx, candidate))
            except Rejected:
                continue
    return primary, fallbacks


def resolve_roles(engine):
    """Resolve every role independently; a role that cannot serve a request is None."""
    resolved = {}
    with engine.read_transaction() as cx:
        configured=engine._state(cx).get('execution_config',{}).get('roles',{})
    for role in dict.fromkeys([*ROLES,*configured]):
        try:
            resolved[role] = resolve_connection(engine, role=role)
            _, chain=resolve_chain(engine,role=role)
            resolved[role]['_fallback_connections']=chain
        except Rejected:
            resolved[role] = None
    return resolved


def bind_connection(engine, board_key, connection_id, reason, *, role=None, fallbacks=None):
    text(reason, "API 绑定依据", 1000)
    if role is not None: identifier(role)
    if connection_id is not None:
        identifier(connection_id)
    if fallbacks is not None:
        require(isinstance(fallbacks, list) and len(fallbacks) <= MAX_FALLBACKS, "回退链最多三条")
        require(all(isinstance(item, str) for item in fallbacks), "回退连接标识无效")
        for item in fallbacks:
            identifier(item)
        require(len(set(fallbacks)) == len(fallbacks), "回退链不能重复")
        require(connection_id not in fallbacks, "默认连接不能同时作为回退")
    with engine.transaction() as cx:
        board = engine._board(cx, board_key)
        state = engine._state(cx)
        require(role is None or role in ROLES or role in state['positions'], '未知岗位或执行职责')
        reject_saved_secrets(cx, [connection_id, role, fallbacks, reason])
        if connection_id is not None or fallbacks:
            schema_table(cx)
            for item in ([connection_id] if connection_id else []) + list(fallbacks or []):
                require(cx.execute("SELECT 1 FROM model_connections WHERE id=?", (item,)).fetchone(), "API 连接不存在")
        state = engine._state(cx)
        execution = state.setdefault("execution_config", {})
        if role is None:
            execution["api_connection_id"] = connection_id
        elif connection_id is None:
            (execution.get("roles") or {}).pop(role, None)
        else:
            execution.setdefault("roles", {})[role] = {"connection_id": connection_id}
        if fallbacks is not None:
            if role is None: execution["fallbacks"] = list(fallbacks)
            elif connection_id is not None: execution['roles'][role]['fallbacks']=list(fallbacks)
        state["version"] += 1
        engine._event(cx, "api_connection_bound", {"connection_id": connection_id, "role": role,
                                                   "fallbacks": list(fallbacks) if fallbacks is not None else None,
                                                   "board": board, "reason": reason})
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
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise ValueError("工具参数缺少：" + ", ".join(sorted(missing)))
        if set(value) - set(schema["properties"]):
            raise ValueError("工具参数含不支持的字段")
        for key in value:
            validate_output(value[key], schema["properties"][key])
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
                    "remote_cancel": False, "tools": "host-authorized organization tools; plain text delivery", "usage": "provider token receipt; cost unknown"}

    def __init__(self, root, connection, *, fallbacks=()):
        self.root = Path(root) / "executions"
        self.connection = copy.deepcopy(connection)
        self.config = validate_config(connection["config"])
        self.model = self.config["model"]
        self.fallbacks = [copy.deepcopy(item) for item in fallbacks]
        self.active_secrets = tuple(c['api_key'] for c in [self.connection,*self.fallbacks] if c.get('api_key'))
        self.jobs = {}
        self.attempt_budget = None
        self.correction = None
        self.corrections_used = 0
        self.secret_guard = self._saved_secret_guard if (Path(root) / "state.sqlite3").is_file() else None
        self.metadata = {"connection_id": connection["id"], "connection_revision": connection["revision"],
                         "protocol": self.config.get('protocol','openai_chat_completions'), "requested_model": self.model,
                         "transport_source": "local_test" if is_loopback(urlsplit(self.config["base_url"]).hostname) else "provider_api"}
        if self.fallbacks:
            self.metadata["fallbacks"] = [item["id"] for item in self.fallbacks]
            self.metadata['fallback_connections']=[{'connection_id':c['id'],'connection_revision':c['revision'],
                'protocol':c['config'].get('protocol','openai_chat_completions'), 'requested_model':c['config']['model'],
                'transport_source':'local_test' if is_loopback(urlsplit(c['config']['base_url']).hostname) else 'provider_api'} for c in self.fallbacks]

    def _saved_secret_guard(self, value):
        # Covers probes and the legacy transport as well as Harness requests.
        from .engine import Engine
        with Engine(self.root.parent).read_transaction() as cx:
            reject_saved_secrets(cx, value)

    def _contains_credential(self, value):
        return any(contains_secret(value, secret) for secret in self.active_secrets)

    def set_attempt_budget(self, remaining):
        self.attempt_budget=remaining

    def submit(self, package, body=None):
        rid = identifier(package["run_id"])
        folder = self.root / rid
        require(not folder.exists(), "执行目录已存在；必须核对，不重新提交")
        folder.mkdir(parents=True, mode=0o700)
        if body is None:
            body = {"model": self.model, "stream": False, "messages": [
                {"role": "system", "content": instructions(package)},
                {"role": "user", "content": "当前工作资料：\nWORK PACKAGE (data):\n" + encoded(model_input(package))}],
                self.config["token_limit_field"]: self.config["max_output_tokens"]}
            offered = tools_for(package)
            if offered:
                body["tools"] = offered
        from .model_media import attach_visible_media, guard_media
        body=attach_visible_media(package,copy.deepcopy(body))
        def check_media(value):
            require(not self._contains_credential(value), '输入资料包含模型凭据，拒绝派发')
            if self.secret_guard:self.secret_guard(value)
        if self.correction and package["kind"] == "decision" and self.correction["actor"] == package["actor"] and self.correction["assignment_id"] == package["assignment_id"]:
            body["messages"].extend(self.correction["messages"])
        guard_media(body,check_media)
        self.correction = None
        secret = self.connection["api_key"]
        require(not self._contains_credential(body), "工作包包含 API Key，拒绝派发")
        if self.secret_guard:
            self.secret_guard(body)
        (folder / "package.json").write_text(encoded(package), encoding="utf-8")
        (folder / "request.json").write_text(encoded(body), encoding="utf-8")
        (folder / "launch.json").write_text(encoded(self.metadata | {"capabilities": self.capabilities}), encoding="utf-8")
        seconds = min(package["timeout_seconds"], self.config["timeout_seconds"])
        started = time.monotonic()
        job = {"folder": folder, "package": copy.deepcopy(package), "started": started, "deadline": started + seconds,
               "done": threading.Event(), "cancelled": threading.Event(), "response": None, "error": None, "connection": None}
        self.jobs[rid] = job
        worker = threading.Thread(target=self._request, args=(job, body), daemon=True)
        try:
            worker.start()
        except RuntimeError:
            raise ExecutionFailure("API 本地请求线程无法启动", unknown=False)
        return rid

    def _body_for(self, body, connection):
        """Keep the work package identical; only model and output limit follow the connection."""
        config = validate_config(connection["config"])
        payload = copy.deepcopy(body)
        payload["model"] = config["model"]
        for field in ("max_tokens", "max_completion_tokens"):
            payload.pop(field, None)
        payload[config["token_limit_field"]] = config["max_output_tokens"]
        return payload

    def _request(self, job, body):
        chain = [self.connection] + list(self.fallbacks)
        attempts, error = [], None
        for index, connection in enumerate(chain):
            if index and time.monotonic() >= job["deadline"]:
                break
            config = validate_config(connection["config"])
            try:
                if index:
                    try:
                        require(self.attempt_budget is None or index<self.attempt_budget,'本次有限调用额度已耗尽')
                        if (self.root.parent/'state.sqlite3').is_file():
                            from .engine import Engine
                            Engine(self.root.parent).reserve_model_attempt(job['package']['run_id'],index,connection)
                    except Rejected:
                        raise ExecutionFailure('当前授权或调用额度不允许备用请求；原失败已保存', failure=issue('execution_failed')) from None
                self._attempt(job, body if index == 0 else self._body_for(body, connection), connection, config)
            except ExecutionFailure as failure:
                error = failure
                attempts.append({"connection_id": connection["id"], "revision": connection["revision"],
                                 "unknown": bool(failure.unknown),
                                 "code": (failure.failure or {}).get("code")})
                job["attempts"] = attempts
                # A sent-but-unconfirmed request is never retried elsewhere.
                eligible=(failure.failure or {}).get('code') in {'api_authentication','api_rate_limited','api_request_rejected','api_redirect','api_connection'}
                if failure.unknown or not eligible or index == len(chain) - 1:
                    if index:
                        job["fallback_from"] = chain[0]["id"]
                    break
                continue
            error = None
            if index:
                job["fallback_from"] = chain[0]["id"]
                job["attempts"] = attempts
            break
        if error is not None:
            job["error"] = error
        job["done"].set()

    def _attempt(self, job, body, connection, config):
        parts = urlsplit(config["base_url"])
        conn = None
        sent = False
        try:
            if (self.root.parent/'state.sqlite3').is_file():
                from .engine import Engine
                Engine(self.root.parent).check_model_dispatch(job['package']['run_id'],connection)
            from .model_context import prepare_context
            body, context_report=prepare_context(config, body)
            job['context_report']=context_report
            job['billing']=config.get('billing')
            job['execution_metadata']={'connection_id':connection['id'], 'connection_revision':connection['revision'],
                'protocol':config.get('protocol','openai_chat_completions'), 'requested_model':config['model'],
                'transport_source':'local_test' if is_loopback(parts.hostname) else 'provider_api'}
            wire, suffix, auth_headers = encode_request(config.get('protocol','openai_chat_completions'), body, connection['api_key'])
            require(not self._contains_credential(wire), '请求内容包含凭据，拒绝派发')
            if self.secret_guard: self.secret_guard(wire)
            conn = api_connection(parts, max(0.01, job["deadline"] - time.monotonic()))
            job["connection"] = conn
            conn.connect()
            if job["cancelled"].is_set() or time.monotonic() >= job["deadline"]:
                raise ExecutionFailure("API 请求截止时间已到", unknown=False)
            conn.sock.settimeout(max(0.01, job["deadline"] - time.monotonic()))
            sent = True  # Even a partial write can reach a remote server.
            conn.request("POST", parts.path.rstrip("/") + suffix, body=encoded(wire).encode("utf-8"),
                         headers={**auth_headers, "Content-Type": "application/json", "Accept": "application/json"})
            response = conn.getresponse()
            if response.status != 200:
                code = "authentication_failed" if response.status in (401, 403) else "rate_limited" if response.status == 429 else "request_rejected" if 400 <= response.status < 500 else "redirect_refused" if 300 <= response.status < 400 else "provider_error"
                parameter = None
                # Error bodies are untrusted and may echo keys. Keep only a known parameter name.
                if response.status == 400:
                    try:
                        body_error = strict_json(response.read(16385))
                        parameter = body_error.get("error", {}).get("param")
                    except (ValueError, TypeError, AttributeError, OSError, http.client.HTTPException):
                        pass
                public_code = {"authentication_failed": "api_authentication", "rate_limited": "api_rate_limited", "redirect_refused": "api_redirect"}.get(code, "api_" + code)
                raise ExecutionFailure("API " + code + " (HTTP " + str(response.status) + ")", unknown=response.status >= 500 or response.status < 300,
                                       failure=issue(public_code, http_status=response.status, parameter=parameter))
            chunks, size = [], 0
            while True:
                if job["cancelled"].is_set() or time.monotonic() >= job["deadline"]:
                    raise ExecutionFailure("API 请求超时；远程执行结果未知", unknown=True, failure=issue("api_timeout"))
                if conn.sock:
                    conn.sock.settimeout(max(0.01, job["deadline"] - time.monotonic()))
                chunk = response.read1(min(65536, 1000001 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > 1000000:
                    raise ExecutionFailure("API 响应超出容量", unknown=False, failure=issue("api_response_too_large"))
            raw = b"".join(chunks).decode("utf-8")
            parsed = decode_response(config.get('protocol','openai_chat_completions'), strict_json(raw))
            # Kept only in private memory until result() extracts token counters
            # and rejects secrets before any message/receipt is persisted.
            job["response"] = (parsed, response.getheader("x-request-id"))
            job["connection_used"] = {"id": connection["id"], "revision": connection["revision"]}
        except ExecutionFailure:
            raise
        except (OSError, http.client.HTTPException):
            raise ExecutionFailure("API 连接失败或中断；请核对供应商请求记录", unknown=sent, failure=issue("api_connection"))
        except (ValueError, UnicodeError, RecursionError, KeyError, TypeError, AttributeError):
            raise ExecutionFailure("API 返回无效 JSON", unknown=False, failure=issue("api_invalid_json"))
        finally:
            if 'response' in locals():
                response.close()
            if conn:
                conn.close()

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
        usage.update(job.get('execution_metadata', {}))
        if job.get('context_report'): usage['context']=job['context_report']
        from .model_billing import calculate
        usage.update(calculate(job.get('billing'), usage))
        for key in ("fallback_from", "connection_used", "attempts"):
            if job.get(key) is not None:
                usage[key] = job[key]
        if state == "unknown":
            error = job["error"] or ExecutionFailure("API 执行结果未知；保留记录，不自动重试", unknown=True, failure=issue("api_timeout"))
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
                if not (isinstance(value, str) and 0 < len(value) <= 256 and all(32 <= ord(c) < 127 for c in value) and not self._contains_credential(value)):
                    return None
                if self.secret_guard:
                    try:
                        self.secret_guard(value)
                    except Rejected:
                        return None
                return value
            usage.update(provider_request_id=safe_string(request_id), response_id=safe_string(reply.get("id")), actual_model=safe_string(reply.get("model")))
            tokens = reply.get("usage") or {}
            if isinstance(tokens, dict):
                for target, source in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
                    if type(tokens.get(source)) is int and tokens[source] >= 0:
                        usage[target] = tokens[source]
                details = tokens.get("prompt_tokens_details")
                if isinstance(details, dict) and type(details.get("cached_tokens")) is int and details["cached_tokens"] >= 0:
                    usage["cached_input_tokens"] = details["cached_tokens"]
            def guard_secrets(value):
                try:
                    require(not self._contains_credential(value), "响应包含凭据")
                    if self.secret_guard:
                        self.secret_guard(value)
                except Rejected:
                    error = ExecutionFailure("API 响应包含已保存凭据；拒绝记录", failure=issue("api_secret_response"))
                    error.usage = {k: v for k, v in usage.items() if k not in ("actual_model", "provider_request_id", "response_id")}
                    raise error
            usage.update(calculate(job.get('billing'), usage))
            guard_secrets(reply)
            choices = reply["choices"]
            require(type(choices) is list and len(choices) == 1, "API 必须返回一个选择")
            choice = choices[0]
            require(type(choice) is dict, "API 选择格式错误")
            message = choice["message"]
            require(type(message) is dict, "API 消息格式错误")
            if choice.get("finish_reason") not in ("stop", "tool_calls") or message.get("refusal") or message.get("function_call"):
                code = "api_output_truncated" if choice.get("finish_reason") == "length" else "api_refusal" if message.get("refusal") or choice.get("finish_reason") == "content_filter" else "api_unexpected_tool" if message.get("tool_calls") or message.get("function_call") else "api_invalid_json"
                error = ExecutionFailure("API 输出被截断、拒绝或请求范围外工具", unknown=False, failure=issue(code))
                error.usage = usage
                raise error
            package = job["package"]
            calls = message.get("tool_calls")
            if job.get("message_only"):
                # Decode every nested JSON argument before the SDK can checkpoint it.
                safe = {"role": "assistant", "content": message.get("content") if isinstance(message.get("content"), str) else ""}
                if message.get('_provider_parts'): safe['_provider_parts']=copy.deepcopy(message['_provider_parts'])
                if calls:
                    require(type(calls) is list and 1 <= len(calls) <= 30, "工具调用数量无效")
                    ids = set()
                    for call in calls:
                        require(type(call) is dict and call.get("type") == "function" and type(call.get("id")) is str and 0 < len(call["id"]) <= 256 and call["id"] not in ids, "工具调用格式不完整")
                        ids.add(call["id"])
                        function = call.get("function")
                        require(type(function) is dict and type(function.get("name")) is str and type(function.get("arguments")) is str, "工具调用缺少名称或参数")
                        try:
                            arguments = strict_json(function["arguments"])
                        except (ValueError, RecursionError):
                            error = ExecutionFailure("工具参数不是完整 JSON；未执行工具", failure=issue("api_tool_arguments"))
                            error.usage = usage
                            error.correction_only = True
                            raise error
                        guard_secrets(arguments)
                        if self._contains_credential(arguments):
                            error = ExecutionFailure("API 工具参数包含凭据；拒绝记录", failure=issue("api_secret_response"))
                            error.usage = usage
                            raise error
                        require(type(arguments) is dict, "工具参数必须是对象")
                    safe["tool_calls"] = copy.deepcopy(calls)
                else:
                    require(choice.get("finish_reason") == "stop" and bool(safe["content"].strip()), "API 缺少文本结果")
                (job["folder"] / "result.json").write_text(encoded(safe), encoding="utf-8")
                (job["folder"] / "receipt.json").write_text(encoded(usage), encoding="utf-8")
                return safe, usage
            if calls:
                require(type(calls) is list and len(calls) == 1, "每轮只能提交一项组织工具调用")
                call = calls[0]
                require(type(call) is dict and call.get("type") == "function" and type(call.get("id")) is str and bool(call["id"]), "工具调用格式不完整")
                function = call.get("function")
                require(type(function) is dict and type(function.get("name")) is str and type(function.get("arguments")) is str, "工具调用缺少名称或参数")
                try:
                    arguments = strict_json(function["arguments"])
                    guard_secrets(arguments)
                    # Function arguments are a second JSON document. Escaped credentials
                    # become visible only after decoding that document.
                    if self._contains_credential(arguments):
                        error = ExecutionFailure("API 工具参数包含凭据；拒绝记录", failure=issue("api_secret_response"))
                        error.usage = usage
                        raise error
                    # Only retain supported fields after credential checks.
                    job["assistant"] = {"role": "assistant", "content": message.get("content") if isinstance(message.get("content"), str) else None, "tool_calls": copy.deepcopy(calls)}
                    value = compile_tool(package, function["name"], arguments)
                except (ValueError, Rejected, TypeError, KeyError) as error:
                    if not job.get("assistant"):
                        # Malformed argument JSON cannot be checked for decoded secrets.
                        # Give fixed feedback without storing or replaying that message.
                        job["correction_only"] = True
                    failure = ExecutionFailure(str(error), failure=issue("api_tool_arguments", rule=str(error)))
                    failure.usage = usage
                    raise failure from error
            else:
                require(choice.get("finish_reason") == "stop", "工具结束标记缺少工具调用")
                content = message.get("content")
                require(type(content) is str and bool(content.strip()), "API 缺少文本结果")
                if package["kind"] == "connection_test":
                    value = {"ok": True}
                elif package["kind"] == "work":
                    value = work_result(content)
                else:
                    job["assistant"] = {"role": "assistant", "content": content}
                    error = ExecutionFailure("安排尚未保存；请调用本轮组织工具完成本次决定", failure=issue("api_action_required"))
                    error.usage = usage
                    raise error
        except (ValueError, TypeError, KeyError, RecursionError, Rejected):
            error = ExecutionFailure("API 返回的消息或工具调用不完整", unknown=False, failure=issue("api_invalid_json"))
            error.usage = usage
            raise error
        (job["folder"] / "result.json").write_text(encoded(value), encoding="utf-8")
        (job["folder"] / "receipt.json").write_text(encoded(usage), encoding="utf-8")
        return value, usage

    def feedback(self, package, error):
        """One conversational correction, dispatched as a new, separately reserved run."""
        job = self.jobs.get(package["run_id"], {})
        code = (getattr(error, "failure", None) or {}).get("code")
        eligible = isinstance(error, Rejected) or code in ("api_action_required", "api_tool_arguments")
        if package["kind"] != "decision" or not eligible or getattr(error, "unknown", False) or not (job.get("assistant") or job.get("correction_only")) or self.corrections_used >= 1:
            return False
        assistant = job.get("assistant")
        reason = "本轮提议未执行，组织没有发生部分变更。请依据当前工作资料修正后调用工具。原因：" + str(error)[:2000]
        if job.get("correction_only"):
            reason = "本轮工具参数不是完整 JSON，未执行任何组织变更。请根据当前工作资料重新调用工具并填写完整参数。"
        messages = [assistant] if assistant else []
        calls = assistant.get("tool_calls", []) if assistant else []
        messages.extend({"role": "tool", "tool_call_id": call["id"], "content": reason} for call in calls)
        if not calls:
            messages.append({"role": "user", "content": reason})
        self.correction = {"actor": package["actor"], "assignment_id": package["assignment_id"], "messages": messages}
        self.corrections_used += 1
        (job["folder"] / "feedback.json").write_text(encoded(messages), encoding="utf-8")
        return True

    def accepted(self):
        self.correction = None
        self.corrections_used = 0

    def execute(self, package):
        rid = self.submit(package)
        try:
            while self.status(rid) == "running":
                self.jobs[rid]["done"].wait(timeout=0.05)
            return self.result(rid)
        except BaseException:
            self.cancel(rid)
            raise

    def chat(self, package, messages, tools):
        """One request only. The SDK owns the loop; this transport never retries."""
        body = {"model": self.model, "stream": False, "messages": messages,
                self.config["token_limit_field"]: self.config["max_output_tokens"]}
        if tools:
            body["tools"] = tools
        rid = self.submit(package, body)
        self.jobs[rid]["message_only"] = True
        try:
            while self.status(rid) == "running":
                self.jobs[rid]["done"].wait(timeout=0.05)
            return self.result(rid)
        except BaseException:
            self.cancel(rid)
            raise
