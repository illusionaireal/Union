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
from urllib.parse import urlsplit

from .engine import encoded, identifier, now, require


class BackendRejected(Exception):
    pass


class AuthBackend:
    def __init__(self, credential_file):
        self.credential_file = credential_file

    def call(self, method, path, data=None, timeout=4):
        env = dict(line.split('=', 1) for line in Path(self.credential_file).read_text().splitlines() if '=' in line)
        token = base64.b64encode((env['OPENCODE_SERVER_USERNAME'] + ':' + env['OPENCODE_SERVER_PASSWORD']).encode()).decode()
        request = urllib.request.Request('http://127.0.0.1:4096' + path,
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
    def __init__(self, app, backend=None):
        self.app = app
        configured = os.environ.get('UNION_SUBSCRIPTION_AUTH_FILE')
        self.backend = backend or (AuthBackend(configured) if configured else None)
        if self.backend and os.name != 'nt':
            require(self.app.root.stat().st_mode & 0o077 == 0, '启用订阅认证需要宿主私有服务目录0700')
            self.app.db.chmod(0o600)
        self.lock = threading.RLock()
        self.active = set()
        with app.catalog() as cx:
            cx.execute('CREATE TABLE IF NOT EXISTS subscription_commands(id TEXT PRIMARY KEY, digest TEXT, owner TEXT, receipt TEXT)')
            cx.execute('CREATE TABLE IF NOT EXISTS subscription_reconciliations(id TEXT PRIMARY KEY, digest TEXT, owner TEXT, receipt TEXT)')
            # External OAuth/session results are not assumed cancelled by restart.
            for row in cx.execute('SELECT id,receipt FROM subscription_commands').fetchall():
                receipt = json.loads(row['receipt'])
                if receipt['status'] in ('accepted', 'authorizing'):
                    receipt.update(status='unknown', message='授权流程被中断；请核对当前连接状态，不自动重新发起')
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
        with self.app.read_catalog() as cx:
            pending = [json.loads(r[0]) for r in cx.execute('SELECT receipt FROM subscription_commands')]
        pending = [{k:r[k] for k in ('id','action','status','message')} for r in pending if r['status'] in ('accepted','authorizing','unknown')]
        return {'available': available, 'pending': pending, 'providers': [
            {'id': name, 'name': label, 'connected': name in connected, 'model_access': 'not_verified'}
            for name, label in [('opencode-go', 'OpenCode Go'), ('openai', 'ChatGPT')]],
            'scope': 'host_account', 'automatic_dispatch': False}

    def _save(self, request_id, receipt):
        with self.app.catalog() as cx:
            row = cx.execute('SELECT receipt FROM subscription_commands WHERE id=?', (request_id,)).fetchone()
            if row and json.loads(row[0])['status'] != 'reconciled':
                cx.execute('UPDATE subscription_commands SET receipt=? WHERE id=?', (encoded(receipt), request_id))

    def command(self, token, value):
        owner = self.authorize(token)
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
        require(action in ('save_go', 'authorize_chatgpt'), '订阅操作不支持')
        require(self.backend is not None, '此服务尚未启用订阅接入')
        if action == 'save_go':
            require(set(value) == {'id', 'action', 'api_key'} and isinstance(value['api_key'], str)
                    and 0 < len(value['api_key']) <= 4096 and all(ord(c) > 32 for c in value['api_key']), '密钥格式无效')
        else:
            require(set(value) == {'id', 'action'}, '授权不接收密钥、URL或方法编号')
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
                require(not any(r['action'] == action and r['status'] in ('accepted', 'authorizing', 'unknown') for r in active),
                        '已有授权或待核对流程，请先查询原流程')
                cx.execute('INSERT INTO subscription_commands VALUES (?,?,?,?)', (value['id'], digest, owner, encoded(receipt)))
            sent = False
            try:
                if action == 'save_go':
                    sent = True
                    require(self.backend.call('PUT', '/auth/opencode-go', {'type': 'api', 'key': value['api_key']}) is True, '保存未获确认')
                    receipt.update(status='succeeded', message='Go认证已保存；模型权限及组织执行能力尚未验证')
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
