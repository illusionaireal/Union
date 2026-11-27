import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, ApiError, errorText } from '../../api/client';
import type { CoreWork, WorkDeliveryMode, WorkIntentCandidate } from '../../api/types';

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
export type InputCommandTarget = {kind: 'append_work_input'; workId: string};
type IntentCommandTarget = {kind: 'start_work_intent'} |
  {kind: 'decide_work_intent' | 'stop_work_intent'; workId: string; intentId: string};
type CommandTarget = ResultCommandTarget | MaterialCommandTarget | RecoveryCommandTarget | InputCommandTarget | IntentCommandTarget;
const materialTarget = (target?: CommandTarget): target is MaterialCommandTarget =>
  target?.kind === 'import_material' || target?.kind === 'revoke_material';
const recoveryTarget = (target?: CommandTarget): target is RecoveryCommandTarget => target?.kind === 'recover_work';
const inputTarget = (target?: CommandTarget): target is InputCommandTarget => target?.kind === 'append_work_input';
const intentTarget = (target?: CommandTarget): target is IntentCommandTarget =>
  target?.kind === 'start_work_intent' || target?.kind === 'decide_work_intent' || target?.kind === 'stop_work_intent';
const survivesRestart = (target?: CommandTarget) => materialTarget(target) || recoveryTarget(target) || inputTarget(target) || intentTarget(target);
const directRefusalTarget = (target?: CommandTarget) => recoveryTarget(target) || inputTarget(target) || intentTarget(target);
const utf8 = new TextEncoder();
async function sha256(value: string) {
  const digest = await crypto.subtle.digest('SHA-256', utf8.encode(value));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}
type Reference = WorkScope & {
  originServiceInstance?: string;
  id: string;
  kind: 'start_work' | CommandTarget['kind'];
  workId?: string;
  intentId?: string;
  deliveryMode?: WorkDeliveryMode;
  candidate?: WorkIntentCandidate;
  attemptId?: string;
  inputId?: string;
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
    : inputTarget(target) ? [target.kind, target.workId]
    : intentTarget(target) ? target.kind === 'start_work_intent' ? [target.kind] : [target.kind, target.workId, target.intentId]
    : [target.kind, target.workId, target.resultId]) : '');
const deliveryMode = (mode: unknown): mode is WorkDeliveryMode => mode === 'automatic_text' || mode === 'governor_review';
const intentCandidate = (r: Record<string, unknown> | null | undefined): r is WorkIntentCandidate & Record<string, unknown> =>
  typeof r?.result_id === 'string' && !!r.result_id && Number.isSafeInteger(r.result_seq) && Number(r.result_seq) > 0 &&
  typeof r.sha256 === 'string' && /^[a-f0-9]{64}$/.test(r.sha256) && Number.isSafeInteger(r.input_cursor) && Number(r.input_cursor) >= 0;
function validIntentReference(r: Reference, target: IntentCommandTarget) {
  if (target.kind === 'start_work_intent') return r.intentId === r.id && deliveryMode(r.deliveryMode);
  return r.workId === target.workId && r.intentId === target.intentId &&
    (target.kind === 'stop_work_intent' || intentCandidate(r.candidate as Record<string, unknown> | undefined));
}
function intentReference(target: IntentCommandTarget, data: Record<string, unknown>, id: string) {
  if (target.kind === 'start_work_intent') {
    if (!deliveryMode(data.delivery_mode)) throw new Error('交付方式无效，尚未提交');
    return {workId: String(data.work_id), intentId: id, deliveryMode: data.delivery_mode};
  }
  if (data.work_id !== target.workId || data.intent_id !== target.intentId)
    throw new Error('工作或意图已变化，尚未提交');
  const identifiers = {workId: target.workId, intentId: target.intentId};
  if (target.kind === 'stop_work_intent') return identifiers;
  if (!intentCandidate(data)) throw new Error('候选成果无效，尚未提交');
  // Persist query identity, never the user-supplied reason or form contents.
  const {result_id, result_seq, sha256, input_cursor} = data;
  return {...identifiers, candidate: {result_id, result_seq, sha256, input_cursor}};
}
function matchesIntentReceipt(original: Reference, value: Record<string, unknown> | null) {
  if (value?.work_id !== original.workId || value?.intent_id !== original.intentId) return false;
  if (original.kind === 'start_work_intent')
    return value?.delivery_mode === original.deliveryMode && typeof value?.attempt_id === 'string' && !!value.attempt_id;
  if (original.kind === 'stop_work_intent') return true;
  return !!original.candidate && Object.entries(original.candidate).every(([key, expected]) => value?.[key] === expected);
}
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
          (intentTarget(target) ? validIntentReference(r, target)
          : inputTarget(target) ? r.workId === target.workId && /^input-[a-f0-9]{32}$/.test(r.inputId) &&
            typeof r.sha256 === 'string' && /^[a-f0-9]{64}$/.test(r.sha256)
          : recoveryTarget(target) ? r.workId === target.workId && r.attemptId === target.attemptId : r.workId === target.workId &&
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
      : inputTarget(target) ? {workId: r.workId, inputId: r.inputId, sha256: r.sha256}
      : intentTarget(target) ? {workId: r.workId, intentId: r.intentId, deliveryMode: r.deliveryMode, candidate: r.candidate}
      : { workId: r.workId, ...(target ? { resultId: r.resultId, sha256: r.sha256 } : {}) }),
    base_version: r.base_version,
    // Persisted completion is a recovery hint; verify the receipt again this mount.
    ...(directRefusalTarget(target) && r.refusedBeforeAcceptance === true ? {refusedBeforeAcceptance: true, outcome: 'rejected'} : {}),
    resolved: directRefusalTarget(target) && r.refusedBeforeAcceptance === true,
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
    liveKey = JSON.stringify([key, scope.serviceInstance]),
    latestKey = useRef(liveKey);
  latestKey.current = liveKey;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const current = () => alive.current && latestKey.current === liveKey;
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
    const input = r?.input as Record<string, unknown> | undefined;
    const owner = r?.execution_owner as {instance?: unknown; epoch?: unknown} | undefined;
    const successMatches =
      original.kind === 'import_material' || original.kind === 'revoke_material'
        ? material?.id === original.materialId && material?.sha256 === original.sha256 &&
          material?.version === (original.kind === 'import_material' ? 1 : Number(original.materialVersion) + 1) &&
          material?.read_allowed === (original.kind === 'import_material')
        : original.kind === 'append_work_input'
        ? r?.work_id === original.workId && input?.id === original.inputId && input?.sha256 === original.sha256 &&
          input?.actor_principal_id === scope.principalId && input?.source_kind === 'requirement' &&
          Number.isInteger(input?.seq) && Number(input?.seq) > 0 &&
          Number.isInteger(input?.bytes) && Number(input?.bytes) > 0 && Number(input?.bytes) <= 65536 &&
          ['received', 'attached', 'observed', 'consumed'].includes(String(input?.status))
        : original.kind === 'recover_work'
        ? r?.work_id === original.workId && r?.attempt_id === original.attemptId &&
          owner?.instance === (original.originServiceInstance ?? original.serviceInstance) &&
          Number.isInteger(owner?.epoch) && Number(owner?.epoch) >= 1
        : original.kind === 'start_work'
        ? r?.work_id === original.workId
        : intentTarget(target)
        ? matchesIntentReceipt(original, r)
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
    const read = await liveRead();
    await liveSession();
    if (original.kind === 'start_work_intent' && r.status === 'succeeded') {
      const row = read.works.find(item => item.id === original.workId);
      const intent = row?.intent;
      if (!row || !intent || intent.id !== original.intentId || intent.delivery_mode !== original.deliveryMode ||
          intent.authorized_principal_id !== scope.principalId || intent.attempt_id !== r.attempt_id ||
          !row.attempts.some(attempt => attempt.id === intent.attempt_id))
        throw new Error('回执与原工作不匹配，请核对开始工作的原请求。');
    }
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
    let awaitingPostResponse = false;
    try {
      await liveSession();
      const read = await liveRead();
      const starts = !target || target.kind === 'start_work_intent';
      if (!(inputTarget(target) ? read.access.can_append_input === true : starts ? read.access.can_start : read.access.can_manage_results)) {
        await liveSession();
        await refresh();
        throw new Error(
          inputTarget(target)
            ? '当前不能收存补充输入；原工作和原请求仍可查询，请核对当前治理授权。'
            : !starts
            ? '当前不能采用或交付成果；已有成果和原请求仍可查询，请核对当前治理授权。'
            : target?.kind === 'start_work_intent'
            ? '当前不能开始新工作；请核对模型连接和当前治理授权。'
            : '当前不能登记新工作；已有工作和原请求仍可查询，请核对模型连接及当前授权。',
        );
      }
      if (read.version !== baseVersion) throw new Error('配置或版本已变化，请刷新核对后提交');
      await preflight(read);
      requireCurrent();
      await liveSession();
      const inputSha = inputTarget(target) ? await sha256(String(data.content)) : undefined;
      const uuid = crypto.randomUUID();
      const id = target?.kind === 'start_work_intent'
        ? `intent-${(await sha256(scope.organizationId)).slice(0, 24)}-${uuid.replaceAll('-', '')}`
        : uuid;
      requireCurrent();
      const original: Reference = {
        ...scope,
        id,
        kind: target?.kind ?? 'start_work',
        ...(materialTarget(target) ? {
          materialId: String(data.material_id), materialVersion: target.kind === 'import_material' ? 0 : target.version,
          sha256: target.sha256,
        } : recoveryTarget(target) ? {workId: String(data.work_id), attemptId: target.attemptId}
          : inputTarget(target) ? {workId: String(data.work_id), inputId: String(data.input_id), sha256: inputSha}
          : intentTarget(target) ? intentReference(target, data, id)
          : { workId: String(data.work_id), ...(target ? { resultId: target.resultId, sha256: target.sha256 } : {}) }),
        base_version: read.version,
        resolved: false,
      };
      const request = {
        id: original.id,
        organization_id: scope.organizationId,
        kind: original.kind,
        base_version: original.base_version,
        data,
      };
      if (original.kind === 'start_work_intent' && utf8.encode(JSON.stringify(request)).byteLength > 200000)
        throw new Error('请求超过 200000 UTF-8 字节，请缩短目标或约束后再提交。');
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
      awaitingPostResponse = true;
      const response = await api.coreWorkCommand(request);
      acceptedResponse = true;
      awaitingPostResponse = false;
      if (current()) await accept(original, response.receipt);
    } catch (error) {
      // Explicit pre-transaction format refusals and direct auth refusals are known.
      // A later read failure or another 4xx leaves the original request unresolved.
      const detail = error as {status?: number; code?: string};
      const intent = intentTarget(target);
      const direct = !!dispatchedId && awaitingPostResponse && !acceptedResponse;
      const settled = () => refs.current.find(r => r.id === dispatchedId && r.resolved);
      const formatRefusal = (inputTarget(target) || (intent && error instanceof ApiError)) && direct &&
        detail?.status === 400 && detail?.code === 'invalid_request';
      const authStatus = [401, 403].includes(Number(detail?.status));
      const typedAuthRefusal = error instanceof ApiError &&
        ((error.status === 401 && error.code === 'not_authenticated') ||
          (error.status === 403 && error.code === 'not_authorized'));
      if (current() && directRefusalTarget(target) && direct && !settled() &&
          (formatRefusal || (intent ? typedAuthRefusal : authStatus))) {
        refs.current = refs.current.map(r=>r.id===dispatchedId ? {...r,resolved:true,outcome:'rejected',refusedBeforeAcceptance:true} : r);
        setReference(refs.current.at(-1));
        try { sessionStorage.setItem(key,JSON.stringify(refs.current)); } catch { /* The original ID remains queryable. */ }
      }
      if (current() && direct && ((inputTarget(target) && detail?.status === 403) || (intent && authStatus))) {
        try {
          await liveSession();
          await liveRead();
          await liveSession();
          const confirmed = settled();
          if (!confirmed || confirmed.refusedBeforeAcceptance) setNote(errorText(error));
          await refresh();
        } catch (readError) {
          failure(readError);
        }
        return;
      }
      // A confirmed receipt preserves execution history, not ongoing read access.
      if (
        accessLost(error) || (formatRefusal && (!settled() || settled()?.refusedBeforeAcceptance)) ||
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
