"""Platform-managed account adoption, separate from AU inference authorization."""
import hashlib
import json
import threading
from urllib.parse import urlencode

from .engine import Rejected, encoded, identifier, now, require
from .model_service import ModelServiceClient, ServiceError, validate_service_config
from .model_api import configure_connection, bind_connection, reject_saved_secrets
from .runner import exclusive


class ModelAccounts:
    def __init__(self, app, client=None):
        self.app, self.client = app, client
        self.lock = threading.RLock()
        with app.catalog() as cx:
            cx.execute('CREATE TABLE IF NOT EXISTS model_account_commands(id TEXT PRIMARY KEY,digest TEXT,owner TEXT,payload TEXT,receipt TEXT)')
            for row in cx.execute('SELECT id,receipt FROM model_account_commands').fetchall():
                receipt = json.loads(row['receipt'])
                if receipt['status'] == 'accepted':
                    receipt.update(status='unknown', message='操作被中断；查询原授权，不能重复提交')
                    cx.execute('UPDATE model_account_commands SET receipt=? WHERE id=?', (encoded(receipt), row['id']))

    def authorize(self, token):
        session = self.app.session(token)
        require(session['role'] == 'board' and session.get('platform_admin') and session['organizations'] is None,
                '此操作需要宿主授予的平台管理员会话')
        return hashlib.sha256(token.encode()).hexdigest()

    def backend(self):
        return self.client or ModelServiceClient()

    def status(self, token):
        self.authorize(token)
        try:
            client = self.backend()
            runtime = client.runtime()
            accounts = client.call('GET', '/v1/accounts', admin=True)['accounts']
            return {'available': True, 'runtime':{k:runtime[k] for k in ('protocol_version','upstream') if k in runtime},
                    'accounts':[{k:a[k] for k in ('id','name','workspace','state','auth_method') if k in a} for a in accounts]}
        except (Rejected, ServiceError, OSError, ValueError, KeyError):
            return {'available': False, 'accounts': []}

    def models(self, token, account):
        self.authorize(token); identifier(account)
        try:
            models = self.backend().call('GET', '/v1/accounts/' + account + '/models', admin=True)['models']
            return {'models':[{k:m[k] for k in ('id','name','context','output','tools','input') if k in m} for m in models]}
        except ServiceError:
            raise Rejected('当前账号的模型目录暂不可读取；请检查账号状态') from None

    def receipt(self, token, request_id):
        owner = self.authorize(token); identifier(request_id)
        with self.app.read_catalog() as cx:
            row = cx.execute('SELECT * FROM model_account_commands WHERE id=?', (request_id,)).fetchone()
        require(row is not None, '未找到模型账号操作')
        receipt, payload = json.loads(row['receipt']), json.loads(row['payload'])
        if payload['action'] == 'authorize_go':
            try:
                remote = self.backend().call('GET', '/v1/auth/' + request_id, admin=True)
                receipt.update(status='succeeded' if remote['state'] == 'connected' else 'unknown' if remote['state'] == 'unknown' else 'accepted')
                receipt['message'] = '账号已连接；可选择模型授予组织' if remote['state'] == 'connected' else '请完成或核对原账号授权流程'
                if row['owner'] == owner:
                    for key in ('url', 'instructions'):
                        if remote.get(key): receipt[key] = remote[key]
            except ServiceError:
                pass
        return receipt

    def command(self, token, value):
        owner = self.authorize(token)
        require(isinstance(value, dict), '操作格式无效')
        action = value.get('action')
        fields = {'authorize_go': {'id','action'},
                  'adopt': {'id','action','organization_id','account_ref','model','connection_id','name','bind_default','reason'},
                  'finish_adoption': {'id','action','target_id'}}
        require(action in fields and set(value) == fields[action], '操作字段无效')
        identifier(value['id'])
        digest = hashlib.sha256(encoded(value).encode()).hexdigest()
        with self.lock:
            with self.app.read_catalog() as cx:
                old = cx.execute('SELECT * FROM model_account_commands WHERE id=?', (value['id'],)).fetchone()
            if old:
                require(old['digest'] == digest, '请求标识已用于不同操作')
                return self.receipt(token, value['id'])
            payload = dict(value)
            if action == 'adopt':
                engine = self.app.engine(token, value['organization_id'])
                with engine.read_transaction() as cx:
                    reject_saved_secrets(cx, value)
                identifier(value['account_ref']); identifier(value['connection_id'])
                require(type(value['bind_default']) is bool, '默认连接选项无效')
                from .model_api import list_connections
                previous = next((c for c in list_connections(engine) if c['id'] == value['connection_id']), None)
                payload['expected_revision'] = previous['revision'] if previous else 0
                validate_service_config(self.config(payload))
            if action == 'finish_adoption':
                identifier(value['target_id'])
            receipt = {'id':value['id'], 'action':action, 'status':'accepted', 'message':'操作已保存', 'created_at':now()}
            if action == 'finish_adoption': receipt['target_id'] = value['target_id']
            with self.app.catalog() as cx:
                cx.execute('INSERT INTO model_account_commands VALUES(?,?,?,?,?)', (value['id'],digest,owner,encoded(payload),encoded(receipt)))
            try:
                client = self.backend()
                if action == 'authorize_go':
                    client.call('POST', '/v1/auth/' + value['id'], {}, admin=True)
                    return self.receipt(token, value['id'])
                if action == 'adopt':
                    grant = client.call('POST', '/v1/grants', {'id':value['id'], 'au_id':value['organization_id'],
                      'account_ref':value['account_ref'], 'model_ids':[value['model']]}, admin=True)
                else:
                    with self.app.read_catalog() as cx:
                        row = cx.execute('SELECT payload FROM model_account_commands WHERE id=?', (value['target_id'],)).fetchone()
                    require(row is not None, '原采用操作不存在')
                    payload = json.loads(row['payload'])
                    require(payload['action'] == 'adopt', '原操作不是模型采用')
                    grant = client.call('GET', '/v1/grants/' + value['target_id'], admin=True)
                self.adopt(token, payload, grant)
                receipt.update(status='succeeded', message='账号已授权给当前组织，模型连接已保存；真实运行尚待验证', connection_id=payload['connection_id'])
            except (ServiceError, Rejected, OSError, ValueError, KeyError):
                receipt.update(status='unknown', message='采用结果待核对；保留原请求标识，查询原授权后完成采用')
            with self.app.catalog() as cx:
                cx.execute('UPDATE model_account_commands SET receipt=? WHERE id=?', (encoded(receipt), value['id']))
                if action == 'finish_adoption' and receipt['status'] == 'succeeded':
                    original = cx.execute('SELECT receipt FROM model_account_commands WHERE id=?', (value['target_id'],)).fetchone()
                    result = json.loads(original[0])
                    result.update(status='succeeded', message=receipt['message'], connection_id=payload['connection_id'])
                    cx.execute('UPDATE model_account_commands SET receipt=? WHERE id=?', (encoded(result),value['target_id']))
            return receipt

    @staticmethod
    def config(value):
        return {'version':2, 'backend':'modeld', 'name':value['name'], 'model':value['model'],
                'grant_ref':value['id'], 'grant_revision':1, 'enabled':True, 'max_output_tokens':8192,
                'deadlines':{'first_event_ms':180000, 'idle_ms':120000, 'task_ms':None},
                'billing':{'basis':'subscription'}}

    def adopt(self, token, value, grant):
        self.authorize(token)
        require(grant['id'] == value['id'] and grant['au_id'] == value['organization_id'] and
                grant['account_ref'] == value['account_ref'] and grant['revision'] == 1 and
                not grant['revoked_at'] and grant['model_ids'] == [value['model']], '原授权范围不匹配')
        engine = self.app.engine(token, value['organization_id'])
        with exclusive(engine), engine.transaction() as cx:
            cx.execute('CREATE TABLE IF NOT EXISTS model_account_adoptions(id TEXT PRIMARY KEY,connection_id TEXT,revision INTEGER)')
            if cx.execute('SELECT 1 FROM model_account_adoptions WHERE id=?', (value['id'],)).fetchone(): return
            old = cx.execute('SELECT MAX(revision) FROM model_connections WHERE id=?', (value['connection_id'],)).fetchone() if cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_connections'").fetchone() else None
            require((old[0] if old and old[0] else 0) == value['expected_revision'], '连接已被其他操作修改，不能覆盖')
            key = (engine.root / 'board.key').read_text().strip()
            saved = configure_connection(engine, key, value['connection_id'], self.config(value), value['reason'], api_key='')
            if value['bind_default']: bind_connection(engine, key, value['connection_id'], value['reason'], fallbacks=[])
            cx.execute('INSERT INTO model_account_adoptions VALUES(?,?,?)', (value['id'],saved['id'],saved['revision']))

    def events(self, token, organization_id, run_id, after):
        require(self.app.session(token)['role'] == 'board', '观察者不能读取模型内容')
        engine = self.app.engine(token, organization_id); identifier(run_id)
        require(type(after) is int and after >= 0, '事件序号无效')
        with engine.read_transaction() as cx:
            run = engine._run(cx, run_id)
            if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_service_events'").fetchone():
                return {'events':[], 'state':run['status']}
            rows = cx.execute('SELECT event FROM model_service_events WHERE run_id=? AND seq>? ORDER BY seq LIMIT 500', (run_id, after))
            # Native state remains private to the host; only explicit display events reach browsers.
            events = [json.loads(row[0]) for row in rows]
            safe = []
            for event in events:
                if event['type'] in ('text_delta','tool_call_complete','queued','completed','failed','interrupted'):
                    safe.append(event)
            return {'events':safe, 'state':run['status'], 'last_seq':events[-1]['seq'] if events else after, 'has_more':len(events) == 500}
