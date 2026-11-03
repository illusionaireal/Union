"""Versioned AU-local connection transfer, without credentials or host references."""
import copy
from .engine import identifier, require
from .model_api import configure_connection, list_connections, validate_config

PRIVATE_FIELDS = {'api_key_env', 'api_key_file'}


def export_connections(engine):
    items = []
    for c in list_connections(engine):
        config = {k:v for k,v in c['config'].items() if k not in PRIVATE_FIELDS}
        if config.get('backend') == 'modeld':
            config.update(grant_ref=None, grant_revision=None, enabled=False)
        items.append({'id':c['id'], 'config':config})
    return {'version': 1, 'connections': items}


def validate_bundle(bundle):
    require(isinstance(bundle, dict) and set(bundle)=={'version','connections'} and type(bundle['version']) is int and bundle['version']==1, '配置文件版本或字段无效')
    require(isinstance(bundle['connections'], list) and 0 < len(bundle['connections']) <= 100, '一次可导入1至100个连接')
    result, ids = [], set()
    for item in bundle['connections']:
        require(isinstance(item, dict) and set(item)=={'id','config'}, '导入连接字段无效，不允许携带密钥')
        identifier(item['id'])
        require(item['id'] not in ids, '导入文件含重复连接ID')
        ids.add(item['id'])
        require(isinstance(item['config'], dict) and not PRIVATE_FIELDS.intersection(item['config']), '导入文件不能携带宿主凭据引用')
        if item['config'].get('backend') == 'modeld':
            require(item['config'].get('grant_ref') is None and item['config'].get('grant_revision') is None
                    and item['config'].get('enabled') is False, '导入不能转移模型使用授权；请由平台管理员重新授予')
        result.append({'id':item['id'], 'config':validate_config(item['config'])})
    return result


def import_connections(engine, key, bundle, mode, reason):
    require(mode in ('reject','rename','replace'), '请选择重名处理方式')
    items = validate_bundle(bundle)
    with engine.transaction() as cx:
        engine._board(cx, key)
        existing = {c['id'] for c in list_connections(engine)}
        occupied = existing | {item['id'] for item in items}
        results = []
        for item in items:
            target = item['id']
            if target in existing:
                require(mode != 'reject', '连接ID已存在：'+target)
                if mode == 'rename':
                    index = 1
                    while f'{target[:60]}-import-{index}' in occupied: index += 1
                    target = f'{target[:60]}-import-{index}'; occupied.add(target)
            # Never inherit a key from the target AU into imported endpoint data.
            configure_connection(engine, key, target, copy.deepcopy(item['config']), reason, api_key='')
            results.append({'source_id':item['id'], 'id':target, 'needs_credentials':True})
        return results
