"""Host-provisioned owner login. Only opaque, revocable session hashes persist."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from .engine import encoded, require

SESSION_SECONDS = 8 * 3600
REMEMBER_SECONDS = 30 * 86400


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value, salt):
    return hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, maxmem=64*1024*1024).hex()


def validate_password(password):
    require(isinstance(password, str) and 12 <= len(password) <= 256, '密码须为12至256个字符')


class Identity:
    def __init__(self, app):
        self.app = app
        app.db.chmod(0o600)

    def configured(self):
        with self.app.read_catalog() as cx:
            return bool(cx.execute('SELECT 1 FROM owner_account').fetchone())

    def setup(self, token, username, password, remember=False):
        session = self.app.session(token) if token else None
        if session is None:
            # A single-host deployment may be claimed by the first visitor when
            # no session cookie is present and no account exists. The owner row
            # is unique, so a later visitor cannot re-claim it; the host resets
            # with scripts/reset_owner.py. Platform management stays a host
            # opt-in, because it reaches host credentials and account backends.
            require(not self.configured(), '管理员已设置，请登录')
            platform_admin = os.environ.get('UNION_FIRST_CLAIM_PLATFORM_ADMIN') == '1'
        else:
            require(session['role'] == 'board' and session['organizations'] is None, '首次设置需要宿主发起人会话')
            platform_admin = session.get('platform_admin', False)
        require(type(remember) is bool, '记住登录字段无效')
        validate_password(password)
        require(isinstance(username, str) and re.fullmatch(r'[a-zA-Z0-9_.@-]{3,100}', username), '账号须为3至100位字母、数字或_.@-')
        username = username.lower()
        salt, recovery = secrets.token_hex(16), secrets.token_urlsafe(32)
        digest = password_hash(password, salt)
        with self.app.catalog() as cx:
            require(not cx.execute('SELECT 1 FROM owner_account').fetchone(), '管理员已设置，请登录')
            cx.execute('INSERT INTO owner_account(username,salt,password_hash,recovery_hash,platform_admin,principal_id) VALUES(?,?,?,?,?,?)',
                       (username, salt, digest, fingerprint(recovery), int(platform_admin), str(uuid.uuid4())))
            account = cx.execute('SELECT * FROM owner_account WHERE username=?', (username,)).fetchone()
            result = self._issue_in(cx, account, remember) | {'recovery_code': recovery}
        with self.app.mutex:
            self.app.sessions.pop(token, None)
        return result

    def _issue(self, username, remember, expected_password_hash=None):
        require(type(remember) is bool, '记住登录字段无效')
        with self.app.catalog() as cx:
            account = cx.execute('SELECT * FROM owner_account WHERE username=?', (username,)).fetchone()
            require(account is not None and (expected_password_hash is None or hmac.compare_digest(expected_password_hash, account['password_hash'])), '认证信息已变更，请重新登录')
            return self._issue_in(cx, account, remember)

    def _issue_in(self, cx, account, remember):
        token = secrets.token_urlsafe(32)
        lifetime = REMEMBER_SECONDS if remember else SESSION_SECONDS
        current = time.time()
        username = account['username']
        data = {'role': 'board', 'organizations': None, 'platform_admin': bool(account['platform_admin']), 'actor': 'account:'+username,
                'view_id': secrets.token_urlsafe(16), 'account': username, 'remember': remember,
                'principal_id': account['principal_id']}
        cx.execute('DELETE FROM login_sessions WHERE deadline<=?', (current,))
        cx.execute('INSERT INTO login_sessions VALUES(?,?,?,?,?)', (fingerprint(token), username, encoded(data), current+lifetime, current+lifetime))
        return {'token': token, 'max_age': lifetime}

    def session(self, token):
        with self.app.catalog() as cx:
            return self._session_in(cx, token)

    def principal_in(self, cx, token):
        from .errors import CoreError, Rejected
        try:
            return self._session_in(cx, token)['principal_id']
        except Rejected as error:
            raise CoreError('not_authenticated') from error

    def _session_in(self, cx, token):
        require(isinstance(token, str) and 20 <= len(token) <= 128, '请登录工作台')
        current = time.time()
        row = cx.execute('SELECT * FROM login_sessions WHERE digest=?', (fingerprint(token),)).fetchone()
        require(row is not None and min(row['expires'], row['deadline']) > current, '登录已过期，请重新登录')
        data = json.loads(row['data'])
        account = cx.execute('SELECT principal_id FROM owner_account WHERE username=?', (row['username'],)).fetchone()
        require(account is not None and isinstance(data.get('principal_id'), str)
                and data['principal_id'] == account['principal_id'], '登录主体已失效，请重新登录')
        # The server enforces both inactivity and absolute expiry. Cookies
        # cannot extend the deadline; revocation deletes the hashed record.
        expiry = min(row['deadline'], current+(REMEMBER_SECONDS if data['remember'] else SESSION_SECONDS))
        if expiry-row['expires'] > 60:
            cx.execute('UPDATE login_sessions SET expires=? WHERE digest=?', (expiry, fingerprint(token)))
        return data | {'expires': expiry}

    def _check_limit(self):
        with self.app.read_catalog() as cx:
            row = cx.execute('SELECT * FROM login_limit WHERE id=1').fetchone()
        require(row is None or row['until'] <= time.time(), '登录尝试过多，请稍后再试')

    def _failure(self):
        current = time.time()
        with self.app.catalog() as cx:
            row = cx.execute('SELECT * FROM login_limit WHERE id=1').fetchone()
            failures = row['failures']+1 if row and current-row['until'] < 900 else 1
            cx.execute('INSERT OR REPLACE INTO login_limit VALUES(1,?,?)', (failures, current+60 if failures >= 8 else current-1))

    def login(self, username, password, remember=False):
        self._check_limit()
        require(isinstance(username, str) and isinstance(password, str) and len(username)<=100 and len(password)<=256, '账号或密码不正确')
        with self.app.read_catalog() as cx:
            row = cx.execute('SELECT * FROM owner_account WHERE username=?', (username.lower(),)).fetchone()
        digest = password_hash(password, row['salt'] if row else '00'*16)
        if row is None or not hmac.compare_digest(digest, row['password_hash']):
            self._failure()
            require(False, '账号或密码不正确')
        with self.app.catalog() as cx:
            cx.execute('DELETE FROM login_limit')
        return self._issue(row['username'], remember, row['password_hash'])

    def logout(self, token):
        if isinstance(token, str):
            self.app.sessions.pop(token, None)
            with self.app.catalog() as cx:
                cx.execute('DELETE FROM login_sessions WHERE digest=?', (fingerprint(token),))

    def change_password(self, token, password, new_password):
        session = self.session(token)
        validate_password(new_password)
        with self.app.read_catalog() as cx:
            row = cx.execute('SELECT * FROM owner_account WHERE username=?', (session['account'],)).fetchone()
        require(isinstance(password, str) and len(password)<=256 and hmac.compare_digest(password_hash(password, row['salt']), row['password_hash']), '当前密码不正确')
        return self._replace(row['username'], new_password, session['remember'], expected_password_hash=row['password_hash'])

    def _replace(self, username, password, remember, recovery=None, expected_password_hash=None, expected_recovery_hash=None):
        salt = secrets.token_hex(16)
        digest = password_hash(password, salt)
        with self.app.catalog() as cx:
            account = cx.execute('SELECT * FROM owner_account WHERE username=?', (username,)).fetchone()
            require(account is not None, '认证信息已变更')
            require(expected_password_hash is None or hmac.compare_digest(expected_password_hash, account['password_hash']), '认证信息已变更')
            require(expected_recovery_hash is None or hmac.compare_digest(expected_recovery_hash, account['recovery_hash']), '恢复信息已使用或已变更')
            cx.execute('UPDATE owner_account SET salt=?,password_hash=? WHERE username=?', (salt, digest, username))
            if recovery:
                cx.execute('UPDATE owner_account SET recovery_hash=? WHERE username=?', (fingerprint(recovery), username))
            cx.execute('DELETE FROM login_sessions WHERE username=?', (username,))
            return self._issue_in(cx, account, remember)

    def recover(self, username, code, new_password):
        self._check_limit()
        validate_password(new_password)
        require(isinstance(username, str) and isinstance(code, str) and len(code)<=128, '恢复信息不正确')
        with self.app.read_catalog() as cx:
            row = cx.execute('SELECT * FROM owner_account WHERE username=?', (username.lower(),)).fetchone()
        if row is None or not hmac.compare_digest(fingerprint(code), row['recovery_hash']):
            self._failure(); require(False, '恢复信息不正确')
        recovery = secrets.token_urlsafe(32)
        result = self._replace(row['username'], new_password, False, recovery, expected_recovery_hash=row['recovery_hash'])
        with self.app.catalog() as cx: cx.execute('DELETE FROM login_limit')
        return result | {'recovery_code': recovery}
