import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, errorText } from '../../api/client';
import type { CoreWorkItem, Session } from '../../api/types';

type Kind = 'start_attempt' | 'run_loop' | 'cancel_step';
type Scope = {
  principalId: string;
  serviceInstance: string;
  organizationId: string;
  workId: string;
};
type Reference = Scope & { id: string; kind: Kind; base_version: number; resolved: boolean };
class ScopeLost extends Error {}
const storageKey = (scope: Scope) => 'union-work-execution:' + JSON.stringify(scope);
function load(scope: Scope): Reference[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(storageKey(scope)) || '[]');
    return Array.isArray(value)
      ? value
          .filter(
            (r): r is Reference =>
              r &&
              Object.entries(scope).every(([k, v]) => r[k] === v) &&
              typeof r.id === 'string' &&
              r.id.length > 0 &&
              ['start_attempt', 'run_loop', 'cancel_step'].includes(r.kind) &&
              Number.isInteger(r.base_version) &&
              r.base_version >= 0 &&
              typeof r.resolved === 'boolean',
          )
          .map((r) => ({
            ...scope,
            id: r.id,
            kind: r.kind,
            base_version: r.base_version,
            resolved: r.resolved,
          }))
      : [];
  } catch {
    return [];
  }
}
const sameSession = (scope: Scope, session: Session) =>
  session.core_protocol === 'core.au.v1' &&
  session.principal_id === scope.principalId &&
  session.service_instance === scope.serviceInstance;

/** Only request identities survive reload; every POST and receipt belongs to one scope. */
export function WorkExecution({
  item,
  scope,
  canExecute,
  onAccessLost,
}: {
  item: CoreWorkItem;
  scope: Scope;
  canExecute: boolean;
  onAccessLost: () => void;
}) {
  const client = useQueryClient();
  const [references, setReferences] = useState(() => load(scope));
  const refs = useRef(references);
  const alive = useRef(true),
    busy = useRef(false),
    querying = useRef(false);
  const scopeRef = useRef(storageKey(scope));
  scopeRef.current = storageKey(scope);
  const [sending, setSending] = useState(false),
    [checking, setChecking] = useState(false);
  const [note, setNote] = useState('');
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const key = storageKey(scope);
  const current = () => alive.current && scopeRef.current === key;
  const requireCurrent = () => {
    if (!current()) throw new ScopeLost('权限或身份已变化，请重开当前工作页');
  };
  const liveSession = async () => {
    const session = await api.session();
    requireCurrent();
    if (!sameSession(scope, session)) throw new ScopeLost('权限或身份已变化，请重开当前工作页');
  };
  const remember = (reference: Reference) => {
    const next = [...refs.current.filter((r) => r.kind !== reference.kind), reference];
    try {
      sessionStorage.setItem(key, JSON.stringify(next));
    } catch {
      throw new Error('浏览器无法保留原请求，尚未提交');
    }
    refs.current = next;
    setReferences(next);
  };
  const accept = async (original: Reference, value: unknown) => {
    requireCurrent();
    const r = value as Record<string, unknown> | null;
    if (
      !r ||
      r.id !== original.id ||
      r.kind !== original.kind ||
      r.organization_id !== scope.organizationId ||
      r.base_version !== original.base_version ||
      r.actor_principal_id !== scope.principalId ||
      !Number.isInteger(r.version) ||
      Number(r.version) < 0 ||
      !['succeeded', 'rejected', 'unknown'].includes(String(r.status))
    )
      throw new Error('回执与原请求不匹配');
    await liveSession();
    // A later POST response must not downgrade an independently confirmed original receipt.
    if (!refs.current.some((x) => x.id === original.id && x.resolved)) {
      const resolved = r.status !== 'unknown' && r.model_outcome !== 'unknown';
      const next = refs.current.map((x) => (x.id === original.id ? { ...x, resolved } : x));
      refs.current = next;
      setReferences(next);
      try {
        sessionStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* Original identity remains. */
      }
      setNote(String(r.message || (resolved ? '原请求已记录' : '执行结果未知，请查询原请求')));
    }
    await client.invalidateQueries({ queryKey: ['core-work', scope.organizationId] });
  };
  const failure = (error: unknown) => {
    if (!current()) return;
    if (
      error instanceof ScopeLost ||
      [401, 403].includes(Number((error as { status?: number })?.status))
    ) {
      onAccessLost();
      return;
    }
    setNote(errorText(error));
  };
  const kind: Kind = item.attempts.some((a) => a.status === 'running')
    ? 'run_loop'
    : 'start_attempt';
  const reference = references.find((r) => !r.resolved) || references.find((r) => r.kind === kind);
  const eligible =
    canExecute &&
    item.mandate.active &&
    !item.attempts.some((a) => a.stale) &&
    !['delivered', 'stopped', 'failed'].includes(item.status) &&
    !item.attempts.some((a) => a.status === 'unknown') &&
    item.budget.reserved === 0 &&
    item.budget.used < item.budget.max_calls &&
    item.results.length === 0;
  async function send() {
    if (busy.current || reference || !eligible) return;
    busy.current = true;
    setSending(true);
    setNote('');
    try {
      await liveSession();
      const read = await api.coreWork(scope.organizationId);
      requireCurrent();
      if (
        read.protocol !== 'core.work.v1' ||
        read.organization_id !== scope.organizationId ||
        read.access.principal_id !== scope.principalId ||
        !read.access.can_start
      )
        throw new ScopeLost('权限或身份已变化');
      const work = read.works.find((w) => w.id === scope.workId);
      if (
        !work ||
        work.attempts.some((a) => a.stale) ||
        !work.mandate.active ||
        work.budget.reserved ||
        work.budget.used >= work.budget.max_calls ||
        work.results.length ||
        ['delivered', 'stopped', 'failed'].includes(work.status) ||
        work.attempts.some((a) => a.status === 'unknown') ||
        work.attempts.some((a) => a.status === 'running') !== (kind === 'run_loop')
      ) {
        await client.invalidateQueries({ queryKey: ['core-work', scope.organizationId] });
        throw new Error('工作状态已变化，请核对刷新后的记录');
      }
      const original: Reference = {
        ...scope,
        id: crypto.randomUUID(),
        kind,
        base_version: read.version,
        resolved: false,
      };
      remember(original);
      requireCurrent();
      const result = await api.coreWorkCommand({
        id: original.id,
        kind,
        base_version: original.base_version,
        organization_id: scope.organizationId,
        data: { work_id: scope.workId },
      });
      if (current()) await accept(original, result.receipt);
    } catch (error) {
      failure(error);
    } finally {
      busy.current = false;
      if (current()) setSending(false);
    }
  }
  async function lookup() {
    if (!reference || querying.current) return;
    querying.current = true;
    setChecking(true);
    try {
      await liveSession();
      const result = await api.coreWorkReceipt(scope.organizationId, reference.id);
      if (current()) await accept(reference, result.receipt);
    } catch (error) {
      if (Number((error as { status?: number })?.status) === 403) {
        // The receipt endpoint deliberately uses 403 for both missing and foreign
        // receipts. A long loop may not have committed its final receipt yet.
        try {
          await liveSession();
          const read = await api.coreWork(scope.organizationId);
          requireCurrent();
          if (
            read.protocol !== 'core.work.v1' ||
            read.organization_id !== scope.organizationId ||
            read.access.principal_id !== scope.principalId
          ) {
            throw new ScopeLost('权限或身份已变化');
          }
          await liveSession();
          await client.invalidateQueries({ queryKey: ['core-work', scope.organizationId] });
          requireCurrent();
          if (!refs.current.some((r) => r.id === reference.id && r.resolved)) {
            setNote('原回执尚不可取得；原请求已保留，请稍后查询。');
          }
        } catch (accessError) {
          failure(accessError);
        }
      } else {
        failure(error);
      }
    } finally {
      querying.current = false;
      if (current()) setChecking(false);
    }
  }
  const cancellable = item.steps.find((step) => step.status === 'reserved');
  const [cancelling, setCancelling] = useState(false);
  async function cancelLocal() {
    if (busy.current || !cancellable || reference) return;
    busy.current = true;
    setCancelling(true);
    setNote('');
    try {
      await liveSession();
      const read = await api.coreWork(scope.organizationId);
      requireCurrent();
      if (
        read.protocol !== 'core.work.v1' ||
        read.organization_id !== scope.organizationId ||
        read.access.principal_id !== scope.principalId ||
        !read.access.can_start
      )
        throw new ScopeLost('权限或身份已变化');
      const work = read.works.find((w) => w.id === scope.workId);
      const step = work?.steps.find((value) => value.step_ref === cancellable.step_ref);
      if (!work || !step || step.status !== 'reserved' || step.step_ref !== cancellable.step_ref) {
        await client.invalidateQueries({ queryKey: ['core-work', scope.organizationId] });
        throw new Error('工作状态已变化，请核对刷新后的记录');
      }
      const original: Reference = {
        ...scope,
        id: crypto.randomUUID(),
        kind: 'cancel_step',
        base_version: read.version,
        resolved: false,
      };
      remember(original);
      requireCurrent();
      const result = await api.coreWorkCommand({
        id: original.id,
        kind: 'cancel_step',
        base_version: original.base_version,
        organization_id: scope.organizationId,
        data: { work_id: scope.workId, step_id: step.step_ref,
                reason: '页面级取消：操作者请求停止本次执行' },
      });
      if (current()) await accept(original, result.receipt);
    } catch (error) {
      failure(error);
    } finally {
      busy.current = false;
      if (current()) setCancelling(false);
    }
  }
  return (
    <div className="work-execution" aria-label={'运行 ' + item.title}>
      {cancellable && (
        <button type="button" disabled={cancelling} onClick={() => void cancelLocal()}>
          取消本次执行
        </button>
      )}
      {reference ? (
        <>
          <p>
            {reference.resolved ? '本次操作已记录' : '原请求已保留；请查询，不要重复运行'} ·{' '}
            {reference.id}
          </p>
          <button type="button" disabled={checking} onClick={() => void lookup()}>
            查询原请求
          </button>
        </>
      ) : (
        eligible && (
          <button type="button" disabled={sending} onClick={() => void send()}>
            {kind === 'run_loop' ? '运行 AI 工作' : '准备本轮执行'}
          </button>
        )
      )}
      {note && <p role="status">{note}</p>}
    </div>
  );
}
