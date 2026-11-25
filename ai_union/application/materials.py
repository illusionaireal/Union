"""U120 public material preparation through the existing sole AU writer."""
import copy
import hashlib

from ..adapters.core_au_store import CoreAUStore, encoded
from ..adapters.material_store import MaterialStore
from ..domain import governance, materials, work
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require


def read(service, token, au_id):
    value = service.app.core_au(token, au_id)
    principal = service.app.creation.principal(service.app.session(token))
    state = value['au']
    work.authorize(state, principal)
    return {'protocol': 'core.materials.v1', 'organization_id': au_id, 'version': state['version'],
            'access': {'principal_id': principal, 'can_manage': value.get('governance_status') == 'active'},
            'limits': {'bytes_per_material': materials.MAX_BYTES, 'materials': materials.MAX_ITEMS,
                       'total_bytes': materials.MAX_TOTAL_BYTES},
            'materials': [dict(item) for item in materials.records(state).values()]}


def command(service, token, incoming):
    principal = service.app.creation.principal(service.app.session(token))
    request = copy.deepcopy(incoming)
    try:
        governance.exact(request, {'id', 'organization_id', 'base_version', 'kind', 'data'})
        identifier(request['id'])
        identifier(request['organization_id'])
        require(type(request['base_version']) is int and request['base_version'] >= 0, '须提供当前 AU 版本')
        materials.validate_input(request['kind'], request['data'])
    except (Rejected, TypeError, ValueError, KeyError, UnicodeError) as error:
        raise CoreError('invalid_request', str(error)) from error
    content = None
    stored = copy.deepcopy(request)
    if request['kind'] == 'import_material':
        content = stored['data'].pop('content')
        stored['data']['content_sha256'] = hashlib.sha256(content.encode('utf-8')).hexdigest()
    with service.app.mutex, service.app.catalog() as accounts:
        require(service.app.identity.principal_in(accounts, token) == principal, '登录主体已变化')
        directory, intent = service.app.governance.locate(request['organization_id'])
        with service.store.transaction(directory) as cx:
            state = CoreAUStore.read_in(cx, request['organization_id'], creation=intent)['au']
            previous = service.store.existing(cx, stored, principal)
            if previous is not None:
                return previous
            work.authorize(state, principal)
            service.store.ensure_commands(cx)
            local = copy.deepcopy(state)
            charter = local.pop('charter')
            receipt = {key: request[key] for key in ('id', 'organization_id', 'base_version', 'kind')} | {
                'actor_principal_id': principal, 'created_at': now(), 'status': 'succeeded', 'effect': 'applied'}
            changed = False
            cx.execute('SAVEPOINT material_command')
            try:
                require(request['base_version'] == local['version'], 'AU 版本已变化；请核对原输入')
                work.effective(local, {row[0] for row in accounts.execute('SELECT principal_id FROM owner_account')})
                item = materials.apply(local, request['kind'], request['data'], principal)
                if content is not None:
                    MaterialStore.save(cx, item, content)
                local['version'] += 1
                receipt.update(material=item, message='资料已导入并授权本组织只读；未调用模型' if content is not None
                               else '已撤销后续资料读取；原正文、工作和执行历史保留')
                changed = True
            except Rejected as error:
                cx.execute('ROLLBACK TO material_command')
                local = copy.deepcopy(state)
                local.pop('charter')
                receipt.update(status='rejected', effect='none', message=str(error))
            cx.execute('RELEASE material_command')
            receipt['version'] = local['version']
            service.store.save(cx, local, charter, stored, receipt, local['policy_version'], changed=changed)
            return receipt
