import { Link } from 'react-router-dom';
import { useWorkspace } from '../../app/workspace';
import { organizationPath } from '../../app/organization-routes';
import { useCommands } from './CommandProvider';
import { inspectableCreation, ownedCreation, unscopedCreation } from './receipts';

export function CreationRecovery() {
  const { session } = useWorkspace();
  const { pending, receipts, inspect } = useCommands();
  const recoverable = pending.filter(item => ownedCreation(item, session) || inspectableCreation(item, session));
  const confirmed = Object.values(receipts).filter(item => item.kind === 'create_v1' && item.status === 'succeeded');
  if (!pending.length && !confirmed.length) return null;
  return <section className="creation-recovery" aria-label="创建恢复">
    {recoverable.map(item => <div key={item.id}>
      <p>{unscopedCreation(item) ? '历史创建引用尚未绑定账户。请确认正在使用原账户，再显式核对。' : '有一项创建等待核对。只查询原请求，不会再次创建组织。'}</p>
      <button className="button secondary" onClick={() => inspect(item)}>查询原请求</button>
    </div>)}
    {pending.some(item => item.kind !== 'create_v1') && <p>旧版操作引用已保留，需由原受控客户端核对。</p>}
    {pending.some(item => item.kind === 'create_v1' && !ownedCreation(item, session) && !inspectableCreation(item, session)) && <p>还有其他账户或服务的创建引用，切回原账户与服务后可核对。</p>}
    {confirmed.map(item => <div key={item.id}><p>{item.message}</p>{item.organization_id && <Link className="button secondary" to={organizationPath(item.organization_id)}>打开已创建的组织</Link>}</div>)}
  </section>;
}
