import {ApiError, api} from '../../api/client';
import type {CoreWork, CoreWorkItem, CoreWorkResult, CoreWorkResultContent, Session} from '../../api/types';
import type {WorkScope} from './useWorkCommand';

export function checkResultSession(session: Session, scope: WorkScope) {
  if (session.core_protocol !== 'core.au.v1' || session.principal_id !== scope.principalId ||
    session.service_instance !== scope.serviceInstance ||
    !session.organizations.some(x => x.id === scope.organizationId && x.profile === 'core_v1'))
    throw new ApiError('身份、服务或组织访问已变化，请重开当前组织', 403);
}

export async function readResultWork(scope: WorkScope, signal: AbortSignal): Promise<CoreWork> {
  checkResultSession(await api.session(signal), scope);
  signal.throwIfAborted();
  const value = await api.coreWork(scope.organizationId, signal);
  signal.throwIfAborted();
  if (value.protocol !== 'core.work.v1' || value.organization_id !== scope.organizationId ||
    value.access.principal_id !== scope.principalId)
    throw new ApiError('工作读取与当前身份或组织不一致，请刷新核对', 403);
  checkResultSession(await api.session(signal), scope);
  signal.throwIfAborted();
  return value;
}

export async function checkedResult(scope: WorkScope, work: CoreWorkItem, expected: CoreWorkResult,
  signal: AbortSignal): Promise<CoreWorkResultContent> {
  const value = await api.coreWorkResult(scope.organizationId, work.id, expected.id, signal);
  signal.throwIfAborted();
  const r = value.result;
  if (value.protocol !== 'core.work.v1' || value.organization_id !== scope.organizationId ||
    value.work_id !== work.id || !r || r.id !== expected.id || r.seq !== expected.seq ||
    r.sha256 !== expected.sha256 || r.bytes !== expected.bytes ||
    JSON.stringify(r.sources) !== JSON.stringify(expected.sources) ||
    r.status !== expected.status || r.adopted_at !== expected.adopted_at || typeof value.content !== 'string')
    throw new ApiError('成果身份、版本或来源与当前工作不一致，请刷新核对', 409);
  const bytes = new TextEncoder().encode(value.content);
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), x => x.toString(16).padStart(2, '0')).join('');
  signal.throwIfAborted();
  if (bytes.length !== r.bytes || digest !== r.sha256)
    throw new ApiError('成果正文摘要或字节校验失败，请保留原记录核对', 409);
  checkResultSession(await api.session(signal), scope);
  signal.throwIfAborted();
  return value;
}
