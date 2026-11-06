import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, ApiError } from '../../api/client';
import { isGovernedAU } from '../../api/core-boundary';
import { useWorkspace } from '../../app/workspace';
import { sameScope, type GovernanceScope } from '../governance/model';
import { modelsApi } from './api';
import { isRecoveryAction } from './model';
import {
  assertSession,
  loadReferences,
  matchesModelRead,
  matchesReceipt,
  referenceKey,
  saveReferences,
} from './requests';
import type { ModelDraft, ModelKind, ModelReceipt, ModelReference } from './types';

export function useModels(scope: GovernanceScope) {
  const workspace = useWorkspace();
  const current = useRef(workspace);
  current.current = workspace;
  const alive = useRef(true);
  const [locked, setLocked] = useState(false);
  const [references, setReferences] = useState(loadReferences);
  const referencesRef = useRef(references);
  const [receipts, setReceipts] = useState<Record<string, ModelReceipt>>({});
  const receiptsRef = useRef(receipts);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const assertCurrent = () => {
    if (!alive.current || !sameScope(scope, current.current.session, current.current.orgId))
      throw new Error('核心身份、服务或 AU 已变化；请使用原身份查询原请求');
  };
  const verifySession = async (signal?: AbortSignal) => {
    assertCurrent();
    const session = await api.session(signal);
    assertCurrent();
    try {
      assertSession(scope, session);
    } catch (error) {
      setLocked(true);
      void current.current.refresh();
      throw error;
    }
    return session;
  };
  const fetchProjection = async (signal: AbortSignal) => {
    try {
      await verifySession(signal);
      const read = await modelsApi.read(scope.organizationId, signal);
      signal.throwIfAborted();
      assertCurrent();
      if (!matchesModelRead(read, scope))
        throw new ApiError(
          '模型记录与当前身份、服务或 AU 不一致；请刷新核对',
          409,
          'incompatible_state',
        );
      setLocked(false);
      return read;
    } catch (failure) {
      if (
        alive.current &&
        failure instanceof ApiError &&
        ([401, 403].includes(failure.status ?? 0) || failure.code === 'incompatible_state')
      )
        setLocked(true);
      throw failure;
    }
  };
  const query = useQuery({
    queryKey: ['core-models', scope.serviceInstance, scope.principalId, scope.organizationId],
    enabled: !!workspace.core && workspace.connected && !locked,
    queryFn: ({ signal }) => fetchProjection(signal),
    retry: false,
    networkMode: 'always',
    refetchInterval: 4000,
    refetchIntervalInBackground: false,
  });
  const denied =
    locked ||
    (query.error instanceof ApiError &&
      ([401, 403].includes(query.error.status ?? 0) || query.error.code === 'incompatible_state'));
  const read =
    !denied && workspace.core && query.data && matchesModelRead(query.data, scope)
      ? query.data
      : undefined;
  const canManagePending =
    !!read && isGovernedAU(workspace.core!) && workspace.core!.access.role === 'governor';
  const allowed = (kind: ModelKind, options: Pick<ModelDraft, 'enabled' | 'makeDefault'> = {}) =>
    isRecoveryAction(kind, options) ? canManagePending : !!read?.access.can_configure;
  const connected = workspace.connected && query.isSuccess && query.isFetchedAfterMount && !denied;
  const remember = (reference: ModelReference) => {
    const next = [
      ...referencesRef.current.filter((item) => referenceKey(item) !== referenceKey(reference)),
      reference,
    ];
    saveReferences(next);
    referencesRef.current = next;
    setReferences(next);
  };
  const forget = (reference: ModelReference) => {
    const next = referencesRef.current.filter(
      (item) => referenceKey(item) !== referenceKey(reference),
    );
    referencesRef.current = next;
    setReferences(next);
    try {
      saveReferences(next);
    } catch {
      /* The old reference is safe to query. */
    }
  };
  const record = async (reference: ModelReference, receipt: ModelReceipt) => {
    assertCurrent();
    if (!matchesReceipt(reference, receipt)) throw new Error('回执与原模型请求不匹配');
    await verifySession();
    assertCurrent();
    const key = referenceKey(reference);
    const value = receiptsRef.current[key] ?? receipt;
    receiptsRef.current = { ...receiptsRef.current, [key]: value };
    setReceipts(receiptsRef.current);
    const next = referencesRef.current.map((item) =>
      referenceKey(item) === key ? { ...item, resolved: true } : item,
    );
    referencesRef.current = next;
    setReferences(next);
    try {
      saveReferences(next);
    } catch {
      /* Keep the original identity for recovery. */
    }
    void query.refetch();
    void current.current.refresh();
    return value;
  };
  const lookup = async (reference: ModelReference) => {
    assertCurrent();
    if (reference.principal_id !== scope.principalId) throw new Error('请使用原提交主体查询回执');
    await verifySession();
    const result = await modelsApi.receipt(reference.organization_id, reference.id);
    return record(reference, result.receipt);
  };
  const readCurrent = async (
    kind: ModelKind,
    signal: AbortSignal,
    options: Pick<ModelDraft, 'enabled' | 'makeDefault'> = {},
  ) => {
    assertCurrent();
    if (!current.current.connected || denied)
      throw new Error('连接或读取权限不可用；请刷新后再操作');
    const fresh = await fetchProjection(signal);
    if (isRecoveryAction(kind, options)) {
      if (!canManagePending) throw new Error('当前主体已不能核对或停止此模型操作');
    } else if (!fresh.access.can_configure) {
      setLocked(true);
      void query.refetch();
      throw new Error('当前主体已不能配置模型；请刷新当前权限');
    }
    return fresh;
  };
  return {
    workspace,
    scope,
    read,
    connected,
    allowed,
    denied,
    loading: query.isPending,
    error: query.error,
    references,
    receipts,
    remember,
    forget,
    record,
    lookup,
    readCurrent,
    refresh: () => query.refetch(),
    assertCurrent,
  };
}
export type ModelsController = ReturnType<typeof useModels>;
