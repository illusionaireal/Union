"""Pure AU business-material metadata rules; content has one private store."""
import hashlib
import re
import time

from . import governance
from .creation import text
from ..errors import require

KINDS = {'import_material', 'revoke_material'}
MAX_BYTES = 65536
MAX_ITEMS = 16
MAX_TOTAL_BYTES = 1048576
ID = re.compile(r'material-[a-f0-9]{32}\Z')
HASH = re.compile(r'[a-f0-9]{64}\Z')


def records(state):
    return state.get('business_materials') or {}


def validate_input(kind, data):
    require(kind in KINDS, '不支持的业务资料命令')
    fields = {'material_id', 'name', 'content', 'source', 'reason'} if kind == 'import_material' else {
        'material_id', 'expected_version', 'reason'}
    governance.exact(data, fields)
    require(isinstance(data['material_id'], str) and ID.fullmatch(data['material_id']), '业务资料引用无效')
    text(data['reason'], '授权依据', 10000)
    if kind == 'revoke_material':
        require(type(data['expected_version']) is int and data['expected_version'] >= 1, '须提供资料版本')
        return
    text(data['name'], '资料名称', 120)
    require(not any(ord(c) < 32 or c in '/\\:' for c in data['name']), '资料名称不得包含路径或控制字符')
    require(data['name'].lower().endswith(('.txt', '.md')), '仅支持 .txt 或 .md 文本资料')
    require(data['source'] in ('file', 'paste'), '资料来源必须是选择文件或粘贴文本')
    require(isinstance(data['content'], str) and data['content'].strip() and '\x00' not in data['content'], '资料必须是非空 UTF-8 文本')
    require(len(data['content'].encode('utf-8')) <= MAX_BYTES, '资料超过 64 KiB 导入上限')


def apply(state, kind, data, principal, clock=None):
    items = state.setdefault('business_materials', {})
    at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() if clock is None else clock))
    if kind == 'revoke_material':
        item = items.get(data['material_id'])
        require(item is not None, '资料不存在或不属于此 AU')
        require(item['version'] == data['expected_version'] and item['read_allowed'], '资料版本或许可已变化')
        item.update(version=item['version'] + 1, read_allowed=False, revoked_at=at,
                    revoked_by=principal, revoke_reason=data['reason'])
        return dict(item)
    require(data['material_id'] not in items, '资料引用已存在；不能覆盖原正文或历史')
    require(len(items) < MAX_ITEMS, '本版本最多导入 16 份资料，已撤销历史仍保留')
    raw = data['content'].encode('utf-8')
    require(sum(item['bytes'] for item in items.values()) + len(raw) <= MAX_TOTAL_BYTES, '业务资料总量超过 1 MiB 上限')
    item = {'id': data['material_id'], 'name': data['name'], 'source': data['source'], 'scope': 'au_read_only',
            'version': 1, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'read_allowed': True,
            'created_at': at, 'authorized_by': principal, 'reason': data['reason']}
    items[item['id']] = item
    return dict(item)


def selected(state, material_id, version):
    item = records(state).get(material_id)
    require(item is not None, '资料不存在或不属于此 AU')
    require(item['read_allowed'] and item['version'] == version, '资料已撤权或版本已变化，不能继续读取')
    return item


def validate_state(state):
    items = records(state)
    require(isinstance(items, dict) and len(items) <= MAX_ITEMS, '业务资料元数据无效')
    for key, item in items.items():
        require(isinstance(item, dict) and ID.fullmatch(key) and item.get('id') == key,
                '业务资料身份不一致')
        require(type(item.get('version')) is int and item['version'] in (1, 2)
                and type(item.get('read_allowed')) is bool and item['read_allowed'] == (item['version'] == 1),
                '业务资料授权版本不一致')
        require(isinstance(item.get('sha256'), str) and HASH.fullmatch(item['sha256'])
                and type(item.get('bytes')) is int and 0 < item['bytes'] <= MAX_BYTES
                and item.get('scope') == 'au_read_only' and item.get('source') in ('file', 'paste'),
                '业务资料摘要或范围无效')
    require(sum(item['bytes'] for item in items.values()) <= MAX_TOTAL_BYTES, '业务资料总量无效')
