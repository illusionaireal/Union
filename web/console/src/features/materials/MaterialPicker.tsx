import type { BusinessMaterial } from '../../api/types';
import { useId } from 'react';
import { errorText } from '../../api/client';
import { organizationPath } from '../../app/organization-routes';
import type { WorkScope } from '../work/useWorkCommand';
import { useMaterials } from './useMaterials';

export function MaterialPicker({ scope, value, onChange }: {
  scope: WorkScope; value: BusinessMaterial | null; onChange: (value: BusinessMaterial | null) => void;
}) {
  const id = useId();
  const read = useMaterials(scope);
  const items = !read.error ? read.data?.materials.filter(item => item.read_allowed) ?? [] : [];
  const selected = items.find(item => item.id === value?.id && item.version === value.version && item.sha256 === value.sha256);
  const lost = !!value && !selected;
  return <div className="material-picker">
    <label htmlFor={id}>选择业务资料</label>
      <select id={id} value={value ? `${value.id}:${value.version}` : ''} disabled={!read.data || !!read.error}
        onChange={event => onChange(items.find(item => `${item.id}:${item.version}` === event.target.value) ?? null)}>
        <option value="">请选择已授权资料</option>
        {lost && <option value={`${value.id}:${value.version}`} disabled>原选择已不可用</option>}
        {items.map(item => <option key={item.id} value={`${item.id}:${item.version}`}>{item.name} · 版本 {item.version}</option>)}
      </select>
    {read.isPending && <p role="status">正在核对资料许可…</p>}
    {read.error && <p role="alert">{errorText(read.error)}；请刷新资料后重试。</p>}
    {lost && <p role="status">原资料许可或版本已变化，请明确重新选择；不会换成另一份资料。</p>}
    {selected && <p>本组织只读 · {selected.bytes} 字节 · SHA-256 {selected.sha256}</p>}
    {!read.isPending && !items.length && !read.error && <p>尚无已授权业务资料。</p>}
    <a className="button secondary" href={organizationPath(scope.organizationId, 'resources')}>准备业务资料</a>
  </div>;
}
