"""Explicit host-account configuration. No model requests or arbitrary proxying."""
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import threading
import urllib.request
import urllib.error
from urllib.parse import urlsplit, parse_qs, urlencode
import time
import hmac

from .engine import encoded, identifier, now, require


class BackendRejected(Exception):
    pass


class AuthBackend:
    def __init__(self, credential_file, native=False):
        self.credential_file = credential_file
        self.origin = 'http://127.0.0.1:4097' if native else 'http://127.0.0.1:4096'

    def call(self, method, path, data=None, timeout=4):
        env = dict(line.split('=', 1) for line in Path(self.credential_file).read_text().splitlines() if '=' in line)
        token = base64.b64encode((env['OPENCODE_SERVER_USERNAME'] + ':' + env['OPENCODE_SERVER_PASSWORD']).encode()).decode()
        request = urllib.request.Request(self.origin + path,
            data=None if data is None else encoded(data).encode(), method=method,
            headers={'Authorization': 'Basic ' + token, 'Content-Type': 'application/json'})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(10_000_001)
                require(len(raw) <= 10_000_000, '认证服务响应过大')
                return json.loads(raw)
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500 and error.code not in (408, 409):
                raise BackendRejected() from None
            raise OSError('认证服务结果未确认') from None


class Subscriptions:
    def __init__(self, app, backend=None, native=None):
        self.app = app
        configured = os.environ.get('UNION_SUBSCRIPTION_AUTH_FILE')
        self.backend = backend or (AuthBackend(configured) if configured else None)
        native_file = os.environ.get('UNION_SUBSCRIPTION_V2_AUTH_FILE')
        self.native = native or (AuthBackend(native_file, native=True) if native_file else None)
        if (self.backend or self.native) and os.name != 'nt':
            require(self.app.root.stat().st_mode & 0o077 == 0, '启用订阅认证需要宿主私有服务目录0700')
            self.app.db.chmod(0o600)
        self.lock = threading.RLock()
        self.active = set()
        with app.catalog() as cx:
            cx.execute('CREATE TABLE IF NOT EXISTS subscription_commands(id TEXT PRIMARY KEY, digest TEXT, owner TEXT, receipt TEXT)')
            cx.execute('CREATE TABLE IF NOT EXISTS subscription_reconciliations(id TEXT PRIMARY KEY, digest TEXT, owner TEXT, receipt TEXT)')
            cx.execute('CREATE TABLE IF NOT EXISTS subscription_native(id TEXT PRIMARY KEY, payload TEXT)')
            cx.execute('CREATE TABLE IF NOT EXISTS subscription_callbacks(id TEXT PRIMARY KEY, digest TEXT, owner TEXT, receipt TEXT)')
            # External OAuth/session results are not assumed cancelled by restart.
            for row in cx.execute('SELECT id,receipt FROM subscription_commands').fetchall():
                receipt = json.loads(row['receipt'])
                if receipt['status'] in ('accepted', 'authorizing'):
                    receipt.update(status='unknown', message='授权流程被中断；请核对当前连接状态，不自动重新发起')
                    for key in ('url', 'instructions', 'needs_callback'): receipt.pop(key, None)
                    cx.execute('UPDATE subscription_commands SET receipt=? WHERE id=?', (encoded(receipt), row['id']))

    def authorize(self, token):
        session = self.app.session(token)
        require(session['role'] == 'board' and session.get('platform_admin') and session['organizations'] is None,
                '此操作需要宿主授予的平台管理员会话')
        return hashlib.sha256(token.encode()).hexdigest()

    def receipt(self, token, request_id):
        owner = self.authorize(token)
        identifier(request_id)
        with self.app.read_catalog() as cx:
            row = cx.execute('SELECT owner,receipt FROM subscription_commands WHERE id=?', (request_id,)).fetchone()
        require(row is not None, '未找到授权流程')
        receipt = json.loads(row['receipt'])
        receipt.pop('reconciled_by', None)
        if row['owner'] != owner:
            receipt.pop('url', None); receipt.pop('instructions', None)
            receipt.pop('needs_callback', None)
        return receipt

    def status(self, token):
        self.authorize(token)
        connected = []
        available = bool(self.backend)
        if available:
            try:
                connected = self.backend.call('GET', '/provider').get('connected', [])
            except Exception:
                available = False
        native_available = False
        if self.native:
            try:
                integrations = self.native.call('GET', '/api/integration')['data']
                for item in integrations:
                    if item['id'] in ('opencode', 'openai') and item.get('connections'):
                        connected.append('opencode-go' if item['id'] == 'opencode' else 'openai')
                native_available = True
            except Exception:
                pass
        with self.app.read_catalog() as cx:
            pending = [json.loads(r[0]) for r in cx.execute('SELECT receipt FROM subscription_commands')]
        # A successful authorization must stay visible after a reload, otherwise the
        # only confirmation is a transient panel tied to one browser session.
        last_success = {}
        for receipt in pending:
            if receipt.get('status') != 'succeeded':
                continue
            provider = {'authorize_go': 'opencode-go', 'save_go': 'opencode-go', 'authorize_chatgpt': 'openai'}.get(receipt.get('action'))
            created = receipt.get('created_at') or ''
            if provider and created > last_success.get(provider, ''):
                last_success[provider] = created
        pending = [{k:r[k] for k in ('id','action','status','message')} for r in pending if r['status'] in ('accepted','authorizing','unknown')]
        return {'available': available or native_available, 'native_available': native_available,
                'key_available': available, 'pending': pending, 'providers': [
            {'id': name, 'name': label, 'connected': name in connected, 'model_access': 'not_verified',
             'last_success': last_success.get(name) or None}
            for name, label in [('opencode-go', 'OpenCode Go'), ('openai', 'ChatGPT')]],
            'scope': 'host_account', 'automatic_dispatch': False}

    def _save(self, request_id, receipt):
        with self.app.catalog() as cx:
            row = cx.execute('SELECT receipt FROM subscription_commands WHERE id=?', (request_id,)).fetchone()
            if row and json.loads(row[0])['status'] != 'reconciled':
                cx.execute('UPDATE subscription_commands SET receipt=? WHERE id=?', (encoded(receipt), request_id))

    def command(self, token, value):
        owner = self.authorize(token)
        if isinstance(value, dict) and value.get('action') == 'complete_chatgpt':
            return self._callback(owner, value)
        if isinstance(value, dict) and value.get('action') == 'reconcile':
            require(set(value) == {'id','action','target_id','confirmed_ended'} and value['confirmed_ended'] is True,
                    '核对需要明确确认原操作已在账号服务结束')
            identifier(value['id']); identifier(value['target_id'])
            digest = hashlib.sha256(encoded(value).encode()).hexdigest()
            with self.lock, self.app.catalog() as cx:
                prior=cx.execute('SELECT * FROM subscription_reconciliations WHERE id=?',(value['id'],)).fetchone()
                if prior:
                    require(prior['digest']==digest and prior['owner']==owner,'核对请求标识冲突')
                    return json.loads(prior['receipt'])
                require(value['target_id'] not in self.active, '原授权仍在等待官方结果；请等待结束后核对')
                row = cx.execute('SELECT receipt FROM subscription_commands WHERE id=?', (value['target_id'],)).fetchone()
                require(row is not None, '未找到原流程')
                receipt = json.loads(row[0])
                require(receipt['status'] in ('accepted','authorizing','unknown','reconciled'), '此流程无需核对')
                if receipt['status'] != 'reconciled':
                    receipt.update(previous_status=receipt['status'],status='reconciled',reconciled_by=owner,
                                   reconciled_at=now(),message='已记录管理员确认原操作结束；原请求结果不推定成功。没有重试或调用模型。')
                receipt.pop('url',None);receipt.pop('instructions',None)
                cx.execute('UPDATE subscription_commands SET receipt=? WHERE id=?',(encoded(receipt),value['target_id']))
                public={k:v for k,v in receipt.items() if k!='reconciled_by'}
                cx.execute('INSERT INTO subscription_reconciliations VALUES (?,?,?,?)',(value['id'],digest,owner,encoded(public)))
                return public
        require(isinstance(value, dict) and set(value) in ({'id', 'action'}, {'id', 'action', 'api_key'}), '订阅命令字段无效')
        identifier(value['id'])
        action = value['action']
        require(action in ('save_go', 'authorize_go', 'authorize_chatgpt'), '订阅操作不支持')
        require(self.backend is not None or self.native is not None, '此服务尚未启用订阅接入')
        if action == 'save_go':
            require(self.backend is not None, '密钥接入服务尚未启用')
            require(set(value) == {'id', 'action', 'api_key'} and isinstance(value['api_key'], str)
                    and 0 < len(value['api_key']) <= 4096 and all(ord(c) > 32 for c in value['api_key']), '密钥格式无效')
        else:
            require(set(value) == {'id', 'action'}, '授权不接收密钥、URL或方法编号')
            if action == 'authorize_go': require(self.native is not None, '账号授权服务尚未启用')
        # A process-private keyed digest avoids storing even a reusable hash of a key.
        import hmac
        secret_path = self.app.root / 'subscription-digest.key'
        with self.lock:
            if not secret_path.exists():
                fd = os.open(secret_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, 'wb') as file:
                    file.write(os.urandom(32))
            digest = hmac.new(secret_path.read_bytes(), encoded(value).encode(), hashlib.sha256).hexdigest()
            receipt = {'id': value['id'], 'action': action, 'status': 'accepted', 'created_at': now(),
                       'message': '认证请求已记录；保存不调用模型'}
            with self.app.catalog() as cx:
                prior = cx.execute('SELECT * FROM subscription_commands WHERE id=?', (value['id'],)).fetchone()
                if prior:
                    require(prior['owner'] == owner and prior['digest'] == digest, '请求标识冲突；请查询原回执')
                    return json.loads(prior['receipt'])
                active = [json.loads(r[0]) for r in cx.execute('SELECT receipt FROM subscription_commands')]
                group = ('save_go', 'authorize_go') if action in ('save_go', 'authorize_go') else (action,)
                require(not any(r['action'] in group and r['status'] in ('accepted', 'authorizing', 'unknown') for r in active),
                        '已有授权或待核对流程，请先查询原流程')
                cx.execute('INSERT INTO subscription_commands VALUES (?,?,?,?)', (value['id'], digest, owner, encoded(receipt)))
            sent = False
            try:
                if action == 'save_go':
                    sent = True
                    require(self.backend.call('PUT', '/auth/opencode-go', {'type': 'api', 'key': value['api_key']}) is True, '保存未获确认')
                    receipt.update(status='succeeded', message='Go认证已保存；模型权限及组织执行能力尚未验证')
                elif self.native:
                    sent = True
                    return self._begin_native(value['id'], action, receipt)
                else:
                    methods = self.backend.call('GET', '/provider/auth').get('openai', [])
                    index = next(i for i, m in enumerate(methods) if m.get('type') == 'oauth' and 'headless' in m.get('label', '').lower())
                    sent = True
                    result = self.backend.call('POST', '/provider/openai/oauth/authorize', {'method': index})
                    url = result.get('url', '')
                    parts = urlsplit(url)
                    require(parts.scheme == 'https' and parts.hostname in ('auth.openai.com', 'chatgpt.com')
                            and not parts.username and not parts.password and parts.port in (None, 443), '授权地址未通过校验')
                    code = re.search(r'\b[A-Z0-9]{3,6}-[A-Z0-9]{3,6}\b',str(result.get('instructions','')))
                    require(code is not None, '认证服务未提供有效设备码')
                    receipt.update(status='authorizing', url=url, instructions='请在官方页面输入设备码：'+code[0],
                                   message='请在官方页面完成授权，本页会显示结果')
                    self._save(value['id'], receipt)
                    self.active.add(value['id'])
                    thread = threading.Thread(target=self._complete, args=(value['id'], index, dict(receipt)), daemon=True)
                    thread.start()
                    return receipt
            except BackendRejected:
                receipt.update(status='failed',message='账号服务明确拒绝认证请求；请检查账号设置或网络，修正后可重新发起')
            except Exception:
                # Never reflect provider bodies, keys, paths, or exception strings.
                receipt.update(status='unknown' if sent else 'failed', message='认证结果未确认；查询原回执和连接状态，不自动重发' if sent else '认证服务暂不可用；未发起授权，请稍后重试')
            self._save(value['id'], receipt)
            return receipt

    def _complete(self, request_id, method, receipt):
        try:
            result = self.backend.call('POST', '/provider/openai/oauth/callback', {'method': method}, timeout=600)
            require(result is True, '授权尚未确认')
            receipt.update(status='succeeded', message='ChatGPT授权已保存；模型权限及组织执行能力尚未验证')
        except BackendRejected:
            receipt.update(status='failed',message='官方授权未通过或已失效；请检查账号授权后重新发起')
        except Exception:
            receipt.update(status='unknown', message='授权结果未确认；保留原流程，查询连接状态')
        receipt.pop('url', None)
        receipt.pop('instructions', None)
        self._save(request_id, receipt)
        with self.lock:
            self.active.discard(request_id)

    def _begin_native(self, request_id, action, receipt):
        provider, method = ('opencode', 'device') if action == 'authorize_go' else ('openai', 'chatgpt-token-sharing')
        result = self.native.call('POST', '/api/integration/' + provider + '/connect/oauth',
                                  {'methodID': method}, timeout=12)['data']
        require(result.get('mode') == 'auto', '认证协议不兼容')
        attempt = result['attemptID']
        require(isinstance(attempt, str) and re.fullmatch(r'con_[A-Za-z0-9]+', attempt), '授权标识无效')
        parts = urlsplit(result['url'])
        require(parts.scheme == 'https' and not parts.username and not parts.password and not parts.fragment
                and parts.port in (None, 443) and parts.hostname == ('opencode.ai' if action == 'authorize_go' else 'auth.openai.com'),
                '授权地址未通过校验')
        private = {'provider': provider, 'attempt': attempt, 'submitted': False}
        if action == 'authorize_go':
            code = re.fullmatch(r'Enter code: ([A-Za-z0-9-]{4,40})', result.get('instructions', ''))
            require(code is not None, '认证服务未提供有效设备码')
            instructions = '在官方页面登录，并选择已订阅 Go 的工作区。设备码：' + code[1]
        else:
            require(parts.path == '/api/accounts/authorize', '授权协议不兼容')
            query = parse_qs(parts.query, keep_blank_values=True)
            require(all(len(query.get(k, [])) == 1 for k in ('state', 'redirect_uri')), '授权协议不兼容')
            redirect = urlsplit(query['redirect_uri'][0])
            require(redirect.scheme == 'http' and redirect.hostname == '127.0.0.1' and redirect.port
                    and not redirect.username and not redirect.password and not redirect.query and not redirect.fragment
                    and redirect.path == '/auth/callback', '回调目标不兼容')
            private.update(target=query['redirect_uri'][0], state=query['state'][0])
            instructions = '完成官方授权后，浏览器会跳到你电脑的 127.0.0.1，可能提示无法访问。请复制地址栏中的完整回调地址，粘贴到下方完成连接；无需登录服务器。'
        with self.app.catalog() as cx:
            cx.execute('INSERT INTO subscription_native VALUES (?,?)', (request_id, encoded(private)))
        receipt.update(status='authorizing', url=result['url'], instructions=instructions,
                       needs_callback=action == 'authorize_chatgpt',
                       message='请打开官方授权页面完成登录，再回到这里查看结果')
        self._save(request_id, receipt)
        self.active.add(request_id)
        threading.Thread(target=self._poll_native, args=(request_id, dict(receipt), private), daemon=True).start()
        return receipt

    def _native_status(self, private):
        return self.native.call('GET', '/api/integration/' + private['provider'] + '/connect/oauth/' + private['attempt'])['data']['status']

    def _poll_native(self, request_id, receipt, private):
        try:
            deadline = time.monotonic() + 1200
            while time.monotonic() < deadline:
                status = self._native_status(private)
                if status == 'complete':
                    receipt.update(status='succeeded', message='账号授权已保存；模型权限及组织执行能力尚未验证')
                    break
                if status in ('failed', 'expired'):
                    receipt.update(status='failed', message='官方授权未完成或已过期；请检查账号权限及服务器到官方认证服务的网络后重新发起')
                    break
                require(status == 'pending', '授权状态无效')
                time.sleep(2)
            else:
                raise OSError()
        except Exception:
            receipt.update(status='unknown', message='授权结果未确认；保留原流程，查询连接状态，不自动重新授权')
        for key in ('url', 'instructions', 'needs_callback'): receipt.pop(key, None)
        # Only this exact native attempt's explicit terminal status can resolve transport uncertainty.
        with self.lock:
            with self.app.read_catalog() as cx:
                current = json.loads(cx.execute('SELECT receipt FROM subscription_commands WHERE id=?', (request_id,)).fetchone()[0])
            if current['status'] == 'authorizing' or (current['status'] == 'unknown' and receipt['status'] in ('succeeded', 'failed')):
                if current['status'] == 'unknown':
                    receipt.update(previous_status='unknown', reconciliation_source='native_attempt')
                self._save(request_id, receipt)
            self.active.discard(request_id)

    def _callback(self, owner, value):
        require(set(value) == {'id', 'action', 'target_id', 'callback_url'}, '回调字段无效')
        identifier(value['id']); identifier(value['target_id'])
        require(isinstance(value['callback_url'], str) and len(value['callback_url']) <= 16000
                and all(ord(c) > 32 for c in value['callback_url']), '回调地址格式无效')
        require(self.native is not None, '账号授权服务尚未启用')
        secret = (self.app.root / 'subscription-digest.key').read_bytes()
        digest = hmac.new(secret, encoded(value).encode(), hashlib.sha256).hexdigest()
        with self.lock:
            with self.app.read_catalog() as cx:
                prior = cx.execute('SELECT * FROM subscription_callbacks WHERE id=?', (value['id'],)).fetchone()
                if prior:
                    require(prior['owner'] == owner and prior['digest'] == digest, '回调请求标识冲突')
                    return json.loads(prior['receipt'])
                row = cx.execute('SELECT owner,receipt FROM subscription_commands WHERE id=?', (value['target_id'],)).fetchone()
                require(row is not None and row['owner'] == owner, '请在发起授权的同一会话完成回调')
                receipt = json.loads(row['receipt'])
                require(receipt['action'] == 'authorize_chatgpt' and receipt['status'] == 'authorizing', '原授权当前不能接收回调')
                private_row = cx.execute('SELECT payload FROM subscription_native WHERE id=?', (value['target_id'],)).fetchone()
                require(private_row is not None, '原授权协议不支持回调')
                private = json.loads(private_row[0])
            require(not private['submitted'], '原回调已经提交；请查询原授权结果，勿重复提交')
            target = urlsplit(private['target']); supplied = urlsplit(value['callback_url'])
            require(supplied.scheme == target.scheme and supplied.netloc == target.netloc
                    and supplied.path == target.path and not supplied.fragment and not supplied.username and not supplied.password,
                    '回调地址必须与本次官方授权的回调目标完全一致')
            query = parse_qs(supplied.query, keep_blank_values=True, strict_parsing=True)
            require(set(query) <= {'code', 'state', 'client_id'} and {'code', 'state'} <= set(query)
                    and all(len(v) == 1 and 0 < len(v[0]) <= 8192 and all(ord(c) > 32 for c in v[0]) for v in query.values()),
                    '回调参数无效；请复制完成授权后的完整地址')
            require(hmac.compare_digest(query['state'][0], private['state']), '回调不属于本次授权')
            require(self._native_status(private) == 'pending', '原授权已结束或服务已重启；不转交回调')
            # Reconstruct from the server-held loopback target, never open the submitted URL.
            relay = private['target'] + '?' + urlencode({k:v[0] for k,v in query.items()})
            private['submitted'] = True
            receipt.update(message='回调已接收，正在等待官方认证结果', needs_callback=False)
            with self.app.catalog() as cx:
                cx.execute('UPDATE subscription_native SET payload=? WHERE id=?', (encoded(private), value['target_id']))
                cx.execute('INSERT INTO subscription_callbacks VALUES (?,?,?,?)', (value['id'], digest, owner, encoded(receipt)))
            self._save(value['target_id'], receipt)
            threading.Thread(target=self._relay_callback, args=(value['target_id'], relay), daemon=True).start()
            return receipt

    def _relay_callback(self, request_id, relay):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(relay, timeout=30) as response:
                require(response.status == 200, '官方客户端未确认回调')
                response.read(1_000_000)
        except Exception:
            with self.lock, self.app.catalog() as cx:
                row = cx.execute('SELECT receipt FROM subscription_commands WHERE id=?', (request_id,)).fetchone()
                receipt = json.loads(row[0])
                if receipt['status'] == 'authorizing':
                    receipt.update(status='unknown', message='回调结果未确认；请查询原结果，不要再次提交回调')
                    for key in ('url', 'instructions', 'needs_callback'): receipt.pop(key, None)
                    cx.execute('UPDATE subscription_commands SET receipt=? WHERE id=?', (encoded(receipt), request_id))
