import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorText } from '../../api/client';
import { useWorkspace } from '../../app/workspace';
import { organizationPath } from '../../app/organization-routes';
import { CoreWorkRegistration } from '../work/CoreWorkRegistration';
import type { WorkScope } from '../work/useWorkCommand';
import './materials.css';

function Preparation({ scope, workId }: { scope: WorkScope; workId?: string }) {
  const [lost, setLost] = useState(false);
  const read = useQuery({
    queryKey: ['core-work', scope.organizationId, scope.principalId, scope.serviceInstance],
    queryFn: ({ signal }) => api.coreWork(scope.organizationId, signal), retry: false,
  });
  const value = !read.error ? read.data : undefined;
  const matches = value?.protocol === 'core.work.v1' && value.organization_id === scope.organizationId &&
    value.access.principal_id === scope.principalId;
  const works = matches ? value!.works.filter(work => !workId || work.id === workId) : [];
  if (lost) return <p role="alert">工作读取权限已变化，请刷新组织后重开。</p>;
  return <section className="business-materials" aria-label="工作资料准备">
    <h1>工作资料准备</h1>
    <p>选择已授权资料，保存这项工作的目标、责任与有限调用边界。登记不调用模型；完整自动推进与交付入口尚待接通。</p>
    {read.isPending ? <p role="status">正在核对原工作与资料绑定…</p> : !matches || !value ?
      <p role="alert">工作暂不可读取；{errorText(read.error)}，请刷新核对当前身份。</p> : <>
      {!workId && <CoreWorkRegistration scope={scope} canStart={value.access.can_start} onAccessLost={() => setLost(true)} />}
      {!works.length && <p>{workId ? '指定工作不存在或不属于当前组织，未读取其他工作内容。' : '尚无已登记工作。'}</p>}
      <ul className="material-list">{works.map(work => <li key={work.id}>
        <h2>{work.title}</h2><p>{work.goal}</p>
        <p>责任：{work.responsible.name} · {work.status} · 调用上限 {work.max_calls}</p>
        <p>{work.materials.available ? '资料绑定当前可读' : '资料许可或准备条件需核对'} · {work.materials.documents} 份</p>
        {work.tool_calls.filter(call => call.tool === 'read_document').map(call => <p key={call.step_ref}>
          实际读取依据：{String(call.arguments.path)} · {call.bytes} 字节 · SHA-256 {call.sha256} · 原工具回执 {call.step_ref}
        </p>)}
        {!work.tool_calls.some(call => call.tool === 'read_document') && <p>尚无实际资料读取依据；保存绑定不等于已读取。</p>}
      </li>)}</ul>
    </>}
    <button className="button secondary" disabled={read.isFetching} onClick={() => void read.refetch()}>刷新工作资料依据</button>
    <Link className="button secondary" to={organizationPath(scope.organizationId, 'resources')}>返回能力与资源</Link>
  </section>;
}

export function MaterialWorkPreparation({ workId }: { workId?: string }) {
  const { core, session } = useWorkspace();
  if (!core || !session?.principal_id || !session.service_instance) return null;
  const scope = {organizationId: core.au.id, principalId: session.principal_id, serviceInstance: session.service_instance};
  return <Preparation key={JSON.stringify([scope, workId])} scope={scope} workId={workId} />;
}
