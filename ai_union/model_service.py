"""Host-authenticated model service client. A reserved run is sent at most once.

The organization owns budgets and tools; modeld only produces inference results.
Credentials and routing remain in the host's separate authentication runtime.
"""
from __future__ import annotations

import copy
import hashlib
import http.client
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .engine import Engine, Rejected, encoded, identifier, now, require
from .executor import ExecutionFailure
from .failures import issue


def validate_service_config(config):
    from .engine import model_name, text
    fields = {'version', 'backend', 'name', 'model', 'grant_ref', 'grant_revision', 'max_output_tokens', 'deadlines', 'enabled'}
    require(fields <= set(config) <= fields | {'billing'}, '托管模型配置字段无效')
    require(type(config['version']) is int and config['version'] == 2 and config['backend'] == 'modeld', '托管模型版本无效')
    text(config['name'], '连接名称', 100)
    require(model_name(config['model']) is not None, '必须指定模型')
    require(type(config['enabled']) is bool, '启用状态无效')
    if config['grant_ref'] is None:
        require(config['grant_revision'] is None and config['enabled'] is False, '尚未授权的导入连接必须停用')
    else:
        identifier(config['grant_ref'])
        require(type(config['grant_revision']) is int and config['grant_revision'] >= 1, '授权版本无效')
    require(type(config['max_output_tokens']) is int and 1 <= config['max_output_tokens'] <= 32768, '输出上限必须为1–32768')
    deadlines = config['deadlines']
    require(type(deadlines) is dict and set(deadlines) == {'first_event_ms', 'idle_ms', 'task_ms'}, '超时配置无效')
    for field, value in deadlines.items():
        require(field == 'task_ms' and value is None or type(value) is int and 1000 <= value <= 3600000, '超时配置无效')
    if 'billing' in config:
        from .model_billing import validate_billing
        validate_billing(config['billing'])
    return copy.deepcopy(config)


class ServiceError(Exception):
    def __init__(self, code, status=None):
        self.code, self.status = code, status
        super().__init__(code)


class ModelServiceClient:
    def __init__(self, config_file=None):
        path = Path(config_file or os.environ.get('UNION_MODELD_CONFIG', ''))
        require(path.is_file() and not path.is_symlink(), '模型服务宿主配置尚未就绪')
        if os.name != 'nt':
            require(path.stat().st_mode & 0o077 == 0, '模型服务宿主配置须为0600')
        config = json.loads(path.read_text(encoding='utf-8'))
        parts = urlsplit(config['origin'])
        require(parts.scheme == 'http' and parts.hostname in ('127.0.0.1', '::1') and
                parts.path in ('', '/') and not parts.query and not parts.fragment and not parts.username,
                '模型服务必须使用宿主配置的回环地址')
        self.parts = parts
        self.origin = config['origin'].rstrip('/')
        self.tokens = {}
        for role in ('admin', 'worker'):
            token_file = Path(config[role + '_token_file'])
            if not token_file.is_absolute():
                token_file = path.parent / token_file
            require(token_file.is_file() and not token_file.is_symlink(), '模型服务凭据文件无效')
            if os.name != 'nt':
                require(token_file.stat().st_mode & 0o077 == 0, '模型服务凭据须为0600')
            token = token_file.read_text(encoding='utf-8').strip()
            require(32 <= len(token) <= 256 and token.isascii() and all(ord(c) > 32 for c in token), '模型服务凭据格式无效')
            self.tokens[role] = token
        require(self.tokens['admin'] != self.tokens['worker'], '模型服务管理与执行凭据必须分离')

    def call(self, method, path, body=None, *, admin=False, timeout=10):
        connection = http.client.HTTPConnection(self.parts.hostname, self.parts.port, timeout=timeout)
        try:
            connection.request(method, path, None if body is None else encoded(body).encode('utf-8'),
                {'Authorization': 'Bearer ' + self.tokens['admin' if admin else 'worker'], 'Content-Type': 'application/json'})
            response = connection.getresponse()
            data = response.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise ServiceError('model_service_response_too_large')
            if response.status >= 300:
                # Never forward upstream diagnostics/headers which may contain authentication material.
                raise ServiceError('model_service_rejected', response.status)
            return json.loads(data)
        except (OSError, http.client.HTTPException, json.JSONDecodeError):
            raise ServiceError('model_service_unavailable') from None
        finally:
            connection.close()

    def runtime(self):
        result = self.call('GET', '/v1/runtime')
        require(result.get('protocol_version') == 1, '模型服务协议版本不兼容')
        return result

    def request(self, request_id, au_id):
        identifier(request_id); identifier(au_id)
        return self.call('GET', '/v1/requests/' + request_id + '?' + urlencode({'au_id': au_id}))

    def events(self, request_id, au_id, after=0):
        identifier(request_id); identifier(au_id)
        return self.call('GET', '/v1/requests/' + request_id + '/events?' + urlencode({'au_id': au_id, 'after': after}))


def request_tables(cx):
    cx.execute('''CREATE TABLE IF NOT EXISTS model_service_outbox(
        run_id TEXT PRIMARY KEY, digest TEXT NOT NULL, payload TEXT NOT NULL,
        state TEXT NOT NULL, last_seq INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)''')
    cx.execute('''CREATE TABLE IF NOT EXISTS model_service_events(
        run_id TEXT NOT NULL, seq INTEGER NOT NULL, event TEXT NOT NULL, PRIMARY KEY(run_id,seq))''')


class ModelServiceTransport:
    """One Harness turn -> one persistent model request; no hidden attempts."""
    name = 'api'
    def __init__(self, root, connection, *, fallbacks=(), client=None):
        self.engine = Engine(root)
        self.connection = copy.deepcopy(connection)
        self.config = connection['config']
        self.model = self.config['model']
        self.fallbacks = list(fallbacks)
        # Fallbacks are retained in the configuration, but unknown modeld attempts are never replayed.
        self.secret_guard = None
        self.client = client or ModelServiceClient()
        self.metadata = {'connection_id': connection['id'], 'connection_revision': connection['revision'],
                         'protocol': 'union_modeld_v1', 'requested_model': self.model,
                         'transport_source': 'model_service', 'backend': 'modeld',
                         'grant_ref': self.config['grant_ref'], 'grant_revision': self.config['grant_revision']}

    def set_attempt_budget(self, remaining):
        self.attempt_budget = remaining

    def execute(self, package):
        require(package['kind'] == 'connection_test', '正式组织工作须通过 Agent Harness')
        message, usage = self.chat(package, [{'role': 'user', 'content': '请回复一句简短的连接测试确认。'}], [])
        require(not message.get('tool_calls') and bool(message.get('content')), '连接测试没有收到完整文本')
        return {'ok': True}, usage

    def chat(self, package, messages, tools):
        run_id = identifier(package['run_id'])
        self.engine.check_model_dispatch(run_id, self.connection)
        au_id = self.engine.state()['id']
        body = {'id': run_id, 'run_id': run_id, 'au_id': au_id,
                'connection_id': self.connection['id'], 'connection_revision': self.connection['revision'],
                'grant_ref': self.config['grant_ref'], 'grant_revision': self.config['grant_revision'],
                'model_id': self.model, 'messages': copy.deepcopy(messages), 'tools': copy.deepcopy(tools),
                'generation': {'maxOutputTokens': self.config['max_output_tokens']},
                'deadlines': copy.deepcopy(self.config.get('deadlines', {'first_event_ms': 180000, 'idle_ms': 120000,
                                                         'task_ms': package['timeout_seconds'] * 1000}))}
        if self.secret_guard:
            self.secret_guard(body)
        # AU resource limits remain authoritative even if a connection permits a longer stream.
        body['deadlines']['task_ms'] = min(body['deadlines']['task_ms'] or package['timeout_seconds'] * 1000,
                                           package['timeout_seconds'] * 1000)
        digest = hashlib.sha256(encoded(body).encode()).hexdigest()
        with self.engine.transaction() as cx:
            self.engine._check_model_dispatch(cx, self.engine._run(cx, run_id), self.connection)
            request_tables(cx)
            prior = cx.execute('SELECT digest FROM model_service_outbox WHERE run_id=?', (run_id,)).fetchone()
            require(prior is None, '模型请求已保存；请查询原请求，不能重发')
            cx.execute('INSERT INTO model_service_outbox(run_id,digest,payload,state,updated_at) VALUES(?,?,?,?,?)',
                       (run_id, digest, encoded(body), 'submitting', now()))
        started = time.monotonic()
        usage = self.metadata | {'request_id': run_id}
        try:
            # No automatic POST retry. A lost 202 is resolved only with GET by this same ID.
            try:
                self.client.call('POST', '/v1/requests', body)
            except ServiceError as error:
                if error.status in (400, 401, 403, 404, 405, 413, 422):
                    raise ExecutionFailure('模型服务拒绝本次请求', unknown=False, failure=issue('api_request_rejected')) from None
                if error.status is not None and 400 <= error.status < 500:
                    raise ExecutionFailure('模型请求冲突或接收结果未确认；必须核对原请求', unknown=True,
                                           failure=issue('api_provider_error')) from None
            after = 0
            while True:
                if time.monotonic() - started > package['timeout_seconds'] + 15:
                    raise ServiceError('model_service_wait_expired')
                self.engine.check_model_dispatch(run_id, self.connection)
                remote = self.client.request(run_id, au_id)
                require(remote.get('id') == run_id and remote.get('au_id') == au_id, '模型服务回执范围不匹配')
                events = self.client.events(run_id, au_id, after).get('events', [])
                with self.engine.transaction() as cx:
                    for event in events:
                        require(event.get('request_id') == run_id and type(event.get('seq')) is int and event['seq'] > after,
                                '模型流事件标识或顺序不匹配')
                        if self.secret_guard:
                            self.secret_guard(event)
                        cx.execute('INSERT OR IGNORE INTO model_service_events VALUES(?,?,?)', (run_id, event['seq'], encoded(event)))
                        after = event['seq']
                    cx.execute('UPDATE model_service_outbox SET state=?,last_seq=?,updated_at=? WHERE run_id=?',
                               (remote['state'], after, now(), run_id))
                if remote['state'] in ('completed', 'failed', 'interrupted') and len(events) < 500:
                    break
                time.sleep(0.2)
            usage.update(elapsed_ms=round((time.monotonic() - started) * 1000))
            if remote['state'] != 'completed':
                raise ExecutionFailure('模型请求未完成；请查看原请求状态', unknown=remote['state'] == 'interrupted',
                                       failure=issue('api_provider_error'))
            self.engine.check_model_dispatch(run_id, self.connection)
            result = remote.get('result')
            require(isinstance(result, dict) and isinstance(result.get('message'), dict), '模型服务缺少完整结果')
            message = result['message']
            if self.secret_guard:
                self.secret_guard(result)
            from .model_api import strict_json
            calls = message.get('tool_calls', [])
            require(type(calls) is list and len(calls) <= 30, '工具调用数量无效')
            ids = set()
            for call in calls:
                require(call.get('id') and call['id'] not in ids and call.get('type') == 'function', '工具调用标识无效')
                ids.add(call['id'])
                arguments = strict_json(call['function']['arguments'])
                require(type(arguments) is dict, '工具参数必须是完整对象')
                if self.secret_guard:
                    self.secret_guard(arguments)
            usage.update(result.get('usage', {}))
            from .model_billing import calculate
            usage.update(calculate(self.config.get('billing'), usage))
            return message, usage
        except (ServiceError, Rejected, KeyError, TypeError, ValueError) as error:
            try:
                self.client.call('POST', '/v1/requests/' + run_id + '/cancel?' + urlencode({'au_id': au_id}), {})
            except (ServiceError, Rejected):
                pass
            failure = ExecutionFailure('模型服务结果未确认；原请求不自动重发', unknown=True, failure=issue('api_connection'))
            failure.usage = usage
            raise failure from None
        except ExecutionFailure as error:
            error.usage = usage
            raise


def make_transport(root, connection, *, fallbacks=()):
    require(not fallbacks or connection['config'].get('backend') != 'modeld' and
            all(c['config'].get('backend') != 'modeld' for c in fallbacks),
            '托管模型尚不支持备用链；请单独绑定该连接')
    if connection['config'].get('backend') == 'modeld':
        return ModelServiceTransport(root, connection, fallbacks=fallbacks)
    from .model_api import APIExecutor
    return APIExecutor(root, connection, fallbacks=fallbacks)
