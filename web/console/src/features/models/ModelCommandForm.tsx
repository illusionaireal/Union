import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, errorText } from '../../api/client';
import { modelsApi } from './api';
import { commandTarget, hasBlockingModelCheck, isRecoveryAction, readModelForm } from './model';
import { pendingForTarget, referenceKey } from './requests';
import { ModelFields } from './ModelFields';
import { ModelPreview } from './ModelPreview';
import { ModelReceiptView } from './ModelReceiptView';
import type { ModelDraft, ModelRead, ModelReference, ModelRequest } from './types';
import type { ModelsController } from './useModels';

export function ModelCommandForm({
  draft,
  controller,
  close,
}: {
  draft: ModelDraft;
  controller: ModelsController;
  close: () => void;
}) {
  const form = useRef<HTMLFormElement>(null);
  const alive = useRef(true),
    busy = useRef(false);
  const abort = useRef<AbortController | null>(null);
  const [phase, setPhase] = useState('');
  const [error, setError] = useState(''),
    [lookupError, setLookupError] = useState('');
  const [unknown, setUnknown] = useState(false),
    [querying, setQuerying] = useState(false);
  const [preview, setPreview] = useState<{ request: ModelRequest; read: ModelRead }>();
  const [reference, setReference] = useState<ModelReference>();
  const receipt = reference ? controller.receipts[referenceKey(reference)] : undefined;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      abort.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!receipt) return;
    setUnknown(false);
    setError('');
    if (receipt.status === 'rejected') setPreview(undefined);
  }, [receipt]);
  const current = async () => {
    if (!alive.current) throw new Error('操作已关闭');
    abort.current = new AbortController();
    const read = await controller.readCurrent(draft.kind, abort.current.signal, draft);
    if (!alive.current) throw new Error('操作已关闭');
    if (draft.connection) {
      const connection = read.connections.find((item) => item.id === draft.connection!.id);
      if (!connection || connection.revision !== draft.connection.revision)
        throw new Error('连接已变化；请关闭并检查当前连接，原输入暂时保留');
    }
    return read;
  };
  const changed = () => {
    if (!busy.current) setPreview(undefined);
  };
  const makePreview = async (event: FormEvent) => {
    event.preventDefault();
    if (busy.current || unknown) return;
    busy.current = true;
    setPhase('preview');
    setError('');
    setLookupError('');
    try {
      const data = readModelForm(draft, form.current!);
      const unresolved = pendingForTarget(controller.references, draft.scope, commandTarget(draft));
      if (unresolved && !isRecoveryAction(draft.kind, draft)) {
        setReference(unresolved);
        setUnknown(true);
        setPreview(undefined);
        setError('此连接有结果未知的原请求，请先查询回执。');
        return;
      }
      const read = await current();
      if (draft.kind === 'start_model_check' && hasBlockingModelCheck(read, draft.connection!))
        throw new Error('此连接仍有未结束的验证，请先核对原验证');
      setReference(undefined);
      setPreview({
        read,
        request: {
          id: crypto.randomUUID(),
          organization_id: draft.scope.organizationId,
          base_version: read.version,
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
  };
  const submit = async () => {
    if (!preview || busy.current || unknown) return;
    busy.current = true;
    setPhase('identity');
    setError('');
    const sending = preview.request;
    let original: ModelReference | undefined;
    let posted = false,
      received = false;
    try {
      const fresh = await current();
      if (fresh.version !== sending.base_version)
        throw new Error('AU 状态已变化，请重新预览；尚未提交');
      original = {
        id: sending.id,
        organization_id: sending.organization_id,
        kind: sending.kind,
        base_version: sending.base_version,
        principal_id: draft.scope.principalId,
        service_instance: draft.scope.serviceInstance,
        target: commandTarget(draft),
        resolved: false,
      };
      try {
        controller.remember(original);
      } catch {
        throw new Error('浏览器无法保留原请求标识，尚未提交；请允许会话存储后重试');
      }
      controller.assertCurrent();
      if (!alive.current) return;
      setReference(original);
      setPhase('submitting');
      const key = form.current?.elements.namedItem('api_key');
      if (key instanceof HTMLInputElement) key.value = '';
      setPreview(undefined);
      posted = true;
      const result = await modelsApi.command(sending);
      received = true;
      if (!alive.current) return;
      await controller.record(original, result.receipt);
    } catch (failure) {
      if (!alive.current) return;
      const rejected =
        !received &&
        failure instanceof ApiError &&
        ([400, 401, 403, 413, 422].includes(failure.status ?? 0) ||
          [
            'invalid_request',
            'not_authenticated',
            'not_authorized',
            'unsupported_capability',
            'incompatible_state',
          ].includes(failure.code ?? ''));
      if (!posted || rejected) {
        if (original) controller.forget(original);
        setReference(undefined);
        setPreview(undefined);
        setError(errorText(failure) + '；非秘密输入已保留，请核对后重新预览。');
        if (rejected) void controller.refresh();
      } else {
        setUnknown(true);
        setPreview(undefined);
        setError(errorText(failure) + '；原请求已保留，请查询回执，不要重复提交。');
      }
    } finally {
      if (posted) delete sending.data.api_key;
      if (alive.current) {
        busy.current = false;
        setPhase('');
      }
    }
  };
  const lookup = async () => {
    if (!reference || querying) return;
    setQuerying(true);
    setLookupError('');
    try {
      await controller.lookup(reference);
    } catch (failure) {
      if (alive.current) setLookupError(errorText(failure) + '；原请求标识已保留。');
    } finally {
      if (alive.current) setQuerying(false);
    }
  };
  return (
    <>
      <form
        ref={form}
        className="governance-form model-form"
        onSubmit={makePreview}
        hidden={receipt?.status === 'succeeded'}
      >
        <fieldset disabled={!!phase || unknown} onChange={changed}>
          <ModelFields draft={draft} changed={changed} />
        </fieldset>
        {!controller.connected && (
          <p role="status">连接或当前读取状态不可用；输入保留，恢复并刷新后才能提交。</p>
        )}
        {error && (
          <p role="alert" className="operation-error">
            {error}
          </p>
        )}
        {preview && <ModelPreview draft={draft} request={preview.request} read={preview.read} />}
        <div className="operation-footer">
          <button type="button" className="button secondary" onClick={close}>
            取消
          </button>
          {!unknown && (
            <button
              type="submit"
              className="button secondary"
              disabled={!!phase || !controller.connected}
            >
              {phase === 'preview' ? '正在读取当前状态…' : '预览影响'}
            </button>
          )}
          {preview && (
            <button
              type="button"
              className="button primary"
              disabled={!!phase || !controller.connected}
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
      {(receipt || unknown) && reference && (
        <div className="governance-result" role="status">
          {receipt ? (
            <ModelReceiptView receipt={receipt} />
          ) : (
            <>
              <h3>结果尚未确认</h3>
              <p>
                原请求 {reference.id} 已保留。关闭不会取消服务端操作；只查询原请求，不重复提交。
              </p>
            </>
          )}
          <button
            type="button"
            className="button secondary"
            disabled={querying}
            onClick={() => void lookup()}
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
          <button type="button" className="button primary" onClick={close}>
            返回模型配置
          </button>
        </div>
      )}
    </>
  );
}
