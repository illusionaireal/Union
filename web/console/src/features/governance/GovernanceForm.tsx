import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorText } from '../../api/client';
import { matchesCoreRead } from '../../api/core-boundary';
import type { CoreAURead } from '../../api/types';
import { useWorkspace } from '../../app/workspace';
import { governanceApi } from './api';
import {
  available,
  commandTarget,
  readGovernanceForm,
  sameScope,
  type GovernanceDraft,
} from './model';
import { referenceKey, type GovernanceReference } from './receipts';
import type { GovernanceRequest } from './types';
import { GovernanceFields } from './GovernanceFields';
import { useGovernance } from './GovernanceProvider';
import { GovernanceReceiptView } from './GovernanceReceiptView';
import { GovernancePreview } from './GovernancePreview';

export function GovernanceForm({
  draft,
  onClose,
}: {
  draft: GovernanceDraft;
  onClose: () => void;
}) {
  const workspace = useWorkspace();
  const workspaceRef = useRef(workspace);
  workspaceRef.current = workspace;
  const governance = useGovernance();
  const form = useRef<HTMLFormElement>(null);
  const alive = useRef(true),
    busy = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const [phase, setPhase] = useState<'' | 'preview' | 'identity' | 'submitting'>('');
  const [preview, setPreview] = useState<{ request: GovernanceRequest; current: CoreAURead }>();
  const [reference, setReference] = useState<GovernanceReference>();
  const [error, setError] = useState(''),
    [lookupError, setLookupError] = useState('');
  const [unknown, setUnknown] = useState(false),
    [querying, setQuerying] = useState(false);
  const receipt = reference ? governance.receipts[referenceKey(reference)] : undefined;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!receipt) return;
    busy.current = false;
    setPhase('');
    setUnknown(false);
    setError('');
    if (receipt.status === 'rejected') setPreview(undefined);
  }, [receipt]);
  const assertCurrent = () => {
    if (!alive.current) throw new Error('操作已关闭');
    if (!sameScope(draft.scope, workspaceRef.current.session, workspaceRef.current.orgId))
      throw new Error('核心身份或服务已变化，或已切换 AU；尚未提交');
  };
  async function readCurrent() {
    assertCurrent();
    if (!workspaceRef.current.connected)
      throw new Error('连接或当前读取权限不可用；请先刷新，输入已保留');
    controller.current = new AbortController();
    const session = await api.session(controller.current.signal);
    assertCurrent();
    if (!sameScope(draft.scope, session, draft.scope.organizationId))
      throw new Error('核心身份或服务已变化；尚未提交');
    const current = await api.coreAU(draft.scope.organizationId, controller.current.signal);
    assertCurrent();
    if (!matchesCoreRead(current, session, draft.scope.organizationId))
      throw new Error('AU 读取与当前身份或服务不一致；尚未提交');
    if (!available(current, draft.kind))
      throw new Error('当前主体已不能执行此操作；尚未提交，请刷新当前权限');
    return current;
  }
  async function makePreview(event: FormEvent) {
    event.preventDefault();
    if (busy.current || unknown) return;
    busy.current = true;
    setPhase('preview');
    setError('');
    setLookupError('');
    try {
      const data = readGovernanceForm(draft, form.current!);
      const unresolved = governance.references.find(
        (item) =>
          !item.resolved &&
          item.principal_id === draft.scope.principalId &&
          item.organization_id === draft.scope.organizationId &&
          item.kind === draft.kind &&
          (!item.target || item.target === commandTarget(draft.kind, data)),
      );
      if (unresolved) {
        setReference(unresolved);
        setPreview(undefined);
        setUnknown(true);
        setError('此操作范围已有结果未知的原请求，请先查询原回执。');
        return;
      }
      const current = await readCurrent();
      assertCurrent();
      setReference(undefined);
      setPreview({
        current,
        request: {
          id: crypto.randomUUID(),
          organization_id: draft.scope.organizationId,
          base_version: current.au.version,
          kind: draft.kind,
          data,
        },
      });
    } catch (failure) {
      if (alive.current) {
        setError(errorText(failure));
        setPreview(undefined);
      }
    } finally {
      if (alive.current) {
        busy.current = false;
        setPhase('');
      }
    }
  }
  async function submit() {
    if (!preview || busy.current || unknown) return;
    busy.current = true;
    setPhase('identity');
    setError('');
    const sending = preview.request;
    let original: GovernanceReference | undefined;
    let posted = false;
    let received = false;
    try {
      const fresh = await readCurrent();
      assertCurrent();
      if (fresh.au.version !== sending.base_version)
        throw new Error('状态已变化，请重新预览；输入已保留，尚未提交');
      original = {
        id: sending.id,
        kind: sending.kind,
        organization_id: sending.organization_id,
        base_version: sending.base_version,
        principal_id: draft.scope.principalId,
        service_instance: draft.scope.serviceInstance,
        resolved: false,
        target: commandTarget(sending.kind, sending.data),
      };
      try {
        governance.remember(original);
      } catch {
        throw new Error('浏览器无法保留原请求标识，尚未提交；请允许会话存储后重试');
      }
      assertCurrent();
      setReference(original);
      setPhase('submitting');
      posted = true;
      const result = await governanceApi.command(sending);
      received = true;
      if (!alive.current) return;
      await governance.record(original, result.receipt, draft.scope);
    } catch (failure) {
      if (!alive.current) return;
      // A failed identity check after the POST response cannot prove non-execution.
      const explicitRejection =
        !received &&
        failure instanceof ApiError &&
        ([401, 403].includes(failure.status ?? 0) ||
          [
            'invalid_request',
            'not_authenticated',
            'not_authorized',
            'incompatible_state',
            'unsupported_capability',
          ].includes(failure.code ?? ''));
      if (!posted || explicitRejection) {
        if (original) governance.forget(original);
        setReference(undefined);
        setPreview(undefined);
        setError(errorText(failure) + '；输入已保留，请核对后重新预览。');
        if (explicitRejection) void workspaceRef.current.refresh();
      } else {
        setPreview(undefined);
        setUnknown(true);
        setError(errorText(failure) + '；原请求已保留，请查询回执，不要重复提交。');
      }
    } finally {
      if (alive.current) {
        busy.current = false;
        setPhase('');
      }
    }
  }
  async function query() {
    if (!reference || querying) return;
    setQuerying(true);
    setLookupError('');
    try {
      await governance.lookup(reference, draft.scope);
    } catch (failure) {
      if (alive.current)
        setLookupError(errorText(failure) + '；原请求标识已保留，请恢复原身份或连接后再查询。');
    } finally {
      if (alive.current) setQuerying(false);
    }
  }
  return (
    <>
      <form
        className="governance-form"
        ref={form}
        onSubmit={makePreview}
        hidden={receipt?.status === 'succeeded'}
      >
        <fieldset
          disabled={!!phase || unknown}
          onChange={() => {
            if (!busy.current) setPreview(undefined);
          }}
        >
          <GovernanceFields draft={draft} />
        </fieldset>
        {error && (
          <p role="alert" className="operation-error">
            {error}
          </p>
        )}
        {preview && (
          <GovernancePreview draft={draft} request={preview.request} current={preview.current} />
        )}
        <div className="operation-footer">
          <button type="button" className="button secondary" onClick={onClose}>
            取消
          </button>
          {!unknown && (
            <button type="submit" className="button secondary" disabled={!!phase}>
              {phase === 'preview' ? '正在读取当前状态…' : '预览影响'}
            </button>
          )}
          {preview && (
            <button
              type="button"
              className="button primary"
              disabled={!!phase}
              onClick={() => void submit()}
            >
              {phase === 'identity'
                ? '正在核对身份…'
                : phase === 'submitting'
                  ? '正在提交…'
                  : '确认提交'}
            </button>
          )}
        </div>
      </form>
      {(unknown || receipt) && reference && (
        <div className="governance-result" role="status">
          {receipt ? (
            <GovernanceReceiptView receipt={receipt} />
          ) : (
            <>
              <h3>结果尚未确认</h3>
              <p>原请求 {reference.id} 已保留。关闭窗口不会撤回服务器操作。</p>
            </>
          )}
          <button
            type="button"
            className="button secondary"
            disabled={querying}
            onClick={() => void query()}
          >
            {querying ? '正在查询原请求…' : '查询原请求回执'}
          </button>
          {lookupError && (
            <p role="alert" className="operation-error">
              {lookupError}
            </p>
          )}
        </div>
      )}
      {receipt?.status === 'succeeded' && (
        <div className="operation-footer">
          <button type="button" className="button primary" onClick={onClose}>
            完成，返回工作台
          </button>
        </div>
      )}
    </>
  );
}
