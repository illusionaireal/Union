import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, errorText } from '../../api/client';
import type { CoreWork } from '../../api/types';

export type WorkScope = { principalId: string; serviceInstance: string; organizationId: string };
export type ResultCommandTarget = {
  kind: 'adopt_result' | 'deliver_work';
  workId: string;
  resultId: string;
  sha256: string;
};
export type MaterialCommandTarget =
  | { kind: 'import_material'; sha256?: string }
  | { kind: 'revoke_material'; materialId: string; version: number; sha256: string };
export type RecoveryCommandTarget = {kind: 'recover_work'; workId: string; attemptId: string};
type CommandTarget = ResultCommandTarget | MaterialCommandTarget | RecoveryCommandTarget;
const materialTarget = (target?: CommandTarget): target is MaterialCommandTarget =>
  target?.kind === 'import_material' || target?.kind === 'revoke_material';
const recoveryTarget = (target?: CommandTarget): target is RecoveryCommandTarget => target?.kind === 'recover_work';
const survivesRestart = (target?: CommandTarget) => materialTarget(target) || recoveryTarget(target);
type Reference = WorkScope & {
  originServiceInstance?: string;
  id: string;
  kind: 'start_work' | CommandTarget['kind'];
  workId?: string;
  attemptId?: string;
  materialId?: string;
  materialVersion?: number;
  resultId?: string;
  sha256?: string;
  base_version: number;
  resolved: boolean;
  outcome?: string;
  refusedBeforeAcceptance?: boolean;
};
export class WorkScopeLost extends Error {}
export const accessLost = (error: unknown) =>
  error instanceof WorkScopeLost ||
  [401, 403].includes(Number((error as { status?: number })?.status));
const storageKey = (scope: WorkScope, target?: CommandTarget) =>
  'union-work-command:' +
  JSON.stringify(survivesRestart(target) ? {principalId: scope.principalId, organizationId: scope.organizationId} : scope) +
  (target ? ':' + JSON.stringify(materialTarget(target)
    ? [target.kind, target.kind === 'revoke_material' ? target.materialId : 'imports']
    : recoveryTarget(target) ? [target.kind, target.workId, target.attemptId]
    : [target.kind, target.workId, target.resultId]) : '');
function load(scope: WorkScope, target?: CommandTarget): Reference[] {
  const value: unknown = JSON.parse(sessionStorage.getItem(storageKey(scope, target)) || '[]');
  if (
    !Array.isArray(value) ||
    !value.every(
      (r) =>
        r &&
        Object.entries(scope).every(([k, v]) => (survivesRestart(target) && k === 'serviceInstance') || r[k] === v) &&
        typeof r.serviceInstance === 'string' && !!r.serviceInstance &&
        (r.originServiceInstance === undefined || typeof r.originServiceInstance === 'string') &&
        typeof r.id === 'string' &&
        r.id &&
        r.kind === (target?.kind ?? 'start_work') &&
        (materialTarget(target) ?
          typeof r.materialId === 'string' && /^material-[a-f0-9]{32}$/.test(r.materialId) &&
          Number.isInteger(r.materialVersion) && r.materialVersion >= 0 &&
          typeof r.sha256 === 'string' && /^[a-f0-9]{64}$/.test(r.sha256) &&
          (target.kind === 'import_material' || r.materialId === target.materialId)
          : typeof r.workId === 'string' && r.workId && (!target ||
          (recoveryTarget(target) ? r.workId === target.workId && r.attemptId === target.attemptId : r.workId === target.workId &&
            r.resultId === target.resultId &&
            typeof r.sha256 === 'string' &&
            /^[a-f0-9]{64}$/.test(r.sha256)))) &&
        Number.isInteger(r.base_version) &&
        r.base_version >= 0 &&
        typeof r.resolved === 'boolean',
    )
  ) {
    throw new Error('原请求记录不可读；请保留记录并核对，尚未提交');
  }
  return value.map((r) => ({
    ...scope,
    ...(survivesRestart(target) ? {originServiceInstance: r.originServiceInstance ?? r.serviceInstance} : {}),
    id: r.id,
    kind: r.kind,
    ...(materialTarget(target) ? { materialId: r.materialId, materialVersion: r.materialVersion, sha256: r.sha256 }
      : recoveryTarget(target) ? {workId: r.workId, attemptId: r.attemptId}
      : { workId: r.workId, ...(target ? { resultId: r.resultId, sha256: r.sha256 } : {}) }),
    base_version: r.base_version,
    // Persisted completion is a recovery hint; verify the receipt again this mount.
    ...(recoveryTarget(target) && r.refusedBeforeAcceptance === true ? {refusedBeforeAcceptance: true, outcome: 'rejected'} : {}),
    resolved: recoveryTarget(target) && r.refusedBeforeAcceptance === true,
  }));
}

/** One scoped command, no retry queue and no persisted form contents. */
export function useWorkCommand(
  scope: WorkScope,
  onAccessLost: () => void,
  target?: CommandTarget,
) {
  const client = useQueryClient();
  const [initial] = useState(() => {
    try {
      return { references: load(scope, target), error: '' };
    } catch {
      return {
        references: [] as Reference[],
        error: '原请求记录不可读；请保留记录并核对，尚未提交',
      };
    }
  });
  const refs = useRef(initial.references);
  const [reference, setReference] = useState<Reference | undefined>(() =>
    initial.references.at(-1),
  );
  const [note, setNote] = useState(initial.error);
  const [sending, setSending] = useState(false),
    [checking, setChecking] = useState(false);
  const busy = useRef(false),
    querying = useRef(false),
    alive = useRef(true);
  const key = storageKey(scope, target),
    latestKey = useRef(key);
  latestKey.current = key;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const current = () => alive.current && latestKey.current === key;
  const requireCurrent = () => {
    if (!current()) throw new WorkScopeLost();
  };
  const liveSession = async () => {
    const session = await api.session();
    requireCurrent();
    if (
      session.core_protocol !== 'core.au.v1' ||
      session.principal_id !== scope.principalId ||
      session.service_instance !== scope.serviceInstance
    )
      throw new WorkScopeLost();
  };
  const liveRead = async () => {
    const read = await api.coreWork(scope.organizationId);
    requireCurrent();
    if (
      read.protocol !== 'core.work.v1' ||
      read.organization_id !== scope.organizationId ||
      read.access.principal_id !== scope.principalId
    )
      throw new WorkScopeLost();
    return read;
  };
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ['core-work', scope.organizationId] });
    if (materialTarget(target)) await client.invalidateQueries({ queryKey: ['core-materials', scope.organizationId] });
  };
  const failure = (error: unknown) => {
    if (!current()) return;
    if (accessLost(error)) onAccessLost();
    else setNote(errorText(error));
  };
  const accept = async (original: Reference, value: unknown) => {
    requireCurrent();
    const r = value as Record<string, unknown> | null;
    const result = r?.result as Record<string, unknown> | undefined;
    const work = r?.work as Record<string, unknown> | undefined;
    const material = r?.material as Record<string, unknown> | undefined;
    const owner = r?.execution_owner as {instance?: unknown; epoch?: unknown} | undefined;
    const successMatches =
      original.kind === 'import_material' || original.kind === 'revoke_material'
        ? material?.id === original.materialId && material?.sha256 === original.sha256 &&
          material?.version === (original.kind === 'import_material' ? 1 : Number(original.materialVersion) + 1) &&
          material?.read_allowed === (original.kind === 'import_material')
        : original.kind === 'recover_work'
        ? r?.work_id === original.workId && r?.attempt_id === original.attemptId &&
          owner?.instance === (original.originServiceInstance ?? original.serviceInstance) &&
          Number.isInteger(owner?.epoch) && Number(owner?.epoch) >= 1
        : original.kind === 'start_work'
        ? r?.work_id === original.workId
        : original.kind === 'adopt_result'
          ? result?.id === original.resultId &&
            result?.sha256 === original.sha256 &&
            result?.status === 'adopted'
          : work?.work_id === original.workId &&
            work?.result_id === original.resultId &&
            work?.work_status === 'delivered';
    if (
      !r ||
      r.id !== original.id ||
      r.kind !== original.kind ||
      r.organization_id !== scope.organizationId ||
      r.base_version !== original.base_version ||
      r.actor_principal_id !== scope.principalId ||
      !Number.isInteger(r.version) ||
      Number(r.version) < original.base_version ||
      !['succeeded', 'rejected', 'unknown'].includes(String(r.status)) ||
      (r.status === 'succeeded' && !successMatches)
    )
      throw new Error('回执与原请求不匹配');
    await liveSession();
    await liveRead();
    await liveSession();
    // A late response cannot overwrite a confirmed receipt or a subsequent command.
    if (
      refs.current.at(-1)?.id !== original.id ||
      refs.current.some((x) => x.id === original.id && x.resolved)
    )
      return;
    const next = { ...original, resolved: r.status !== 'unknown', outcome: String(r.status) };
    refs.current = refs.current.map((x) => (x.id === original.id ? next : x));
    setReference(next);
    try {
      sessionStorage.setItem(key, JSON.stringify(refs.current));
    } catch {
      /* Keep the original unresolved ID. */
    }
    setNote(String(r.message || (next.resolved ? '操作已记录' : '结果未知，请查询原请求')));
    await refresh();
  };
  async function send(
    data: Record<string, unknown>,
    baseVersion: number,
    preflight: (read: CoreWork) => Promise<void>,
  ) {
    if (busy.current || reference || initial.error) return;
    busy.current = true;
    setSending(true);
    setNote('');
    let dispatchedId: string | undefined;
    let acceptedResponse = false;
    try {
      await liveSession();
      const read = await liveRead();
      if (!(target ? read.access.can_manage_results : read.access.can_start)) {
        await liveSession();
        await refresh();
        throw new Error(
          target
            ? '当前不能采用或交付成果；已有成果和原请求仍可查询，请核对当前治理授权。'
            : '当前不能登记新工作；已有工作和原请求仍可查询，请核对模型连接及当前授权。',
        );
      }
      if (read.version !== baseVersion) throw new Error('配置或版本已变化，请刷新核对后提交');
      await preflight(read);
      requireCurrent();
      await liveSession();
      const original: Reference = {
        ...scope,
        id: crypto.randomUUID(),
        kind: target?.kind ?? 'start_work',
        ...(materialTarget(target) ? {
          materialId: String(data.material_id), materialVersion: target.kind === 'import_material' ? 0 : target.version,
          sha256: target.sha256,
        } : recoveryTarget(target) ? {workId: String(data.work_id), attemptId: target.attemptId}
          : { workId: String(data.work_id), ...(target ? { resultId: target.resultId, sha256: target.sha256 } : {}) }),
        base_version: read.version,
        resolved: false,
      };
      const next = [...refs.current, original];
      try {
        sessionStorage.setItem(key, JSON.stringify(next));
      } catch {
        throw new Error('浏览器无法保留原请求，尚未提交');
      }
      refs.current = next;
      setReference(original);
      requireCurrent();
      dispatchedId = original.id;
      const response = await api.coreWorkCommand({
        id: original.id,
        organization_id: scope.organizationId,
        kind: original.kind,
        base_version: original.base_version,
        data,
      });
      acceptedResponse = true;
      if (current()) await accept(original, response.receipt);
    } catch (error) {
      // Only a direct auth refusal from this recovery POST proves it was not
      // accepted. Later read loss or an unknown/404 lookup never clears intent.
      if (current() && recoveryTarget(target) && dispatchedId && !acceptedResponse &&
          [401,403].includes(Number((error as {status?:number})?.status))) {
        refs.current = refs.current.map(r=>r.id===dispatchedId ? {...r,resolved:true,outcome:'rejected',refusedBeforeAcceptance:true} : r);
        setReference(refs.current.at(-1));
        try { sessionStorage.setItem(key,JSON.stringify(refs.current)); } catch { /* The original ID remains queryable. */ }
      }
      // A confirmed receipt preserves execution history, not ongoing read access.
      if (
        accessLost(error) ||
        !dispatchedId ||
        !refs.current.some((r) => r.id === dispatchedId && r.resolved)
      )
        failure(error);
    } finally {
      busy.current = false;
      if (current()) setSending(false);
    }
  }
  async function lookup() {
    if (!reference || querying.current) return;
    const original = reference;
    querying.current = true;
    setChecking(true);
    try {
      await liveSession();
      const response = await api.coreWorkReceipt(scope.organizationId, original.id);
      if (current()) await accept(original, response.receipt);
    } catch (error) {
      if (Number((error as { status?: number })?.status) === 403) {
        try {
          await liveSession();
          await liveRead();
          await liveSession();
          if (!refs.current.some((x) => x.id === original.id && x.resolved))
            setNote('原回执尚不可取得；原请求已保留，请稍后查询。');
        } catch (accessError) {
          failure(accessError);
        }
      } else if (
        accessLost(error) ||
        !refs.current.some((x) => x.id === original.id && x.resolved)
      ) {
        failure(error);
      }
    } finally {
      querying.current = false;
      if (current()) setChecking(false);
    }
  }
  function another() {
    if (!reference?.resolved || busy.current || querying.current) return;
    setReference(undefined);
    setNote('');
  }
  return { reference, note, sending, checking, blocked: !!initial.error, send, lookup, another, verifyScope: liveSession };
}
