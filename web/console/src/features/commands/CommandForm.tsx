import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api, errorText } from '../../api/client';
import type { CommandRequest, Receipt } from '../../api/types';
import { useWorkspace } from '../../app/workspace';
import { Badge, Json } from '../../components/ui';
import { CommandFields } from './fields';
import { blocked, readForm, titles } from './model';
import { useCommands, type Draft } from './CommandProvider';
export function ReceiptView({ receipt, onQuery }: { receipt: Receipt; onQuery: () => void }) {
  return (
    <section className="operation-success">
      <Badge value={receipt.status} />
      <h3>{receipt.message}</h3>
      <p>
        请求 {receipt.id}
        <br />
        组织 {receipt.organization_id || '尚未创建'}
        <br />
        操作者 {receipt.actor} · 基准版本 {receipt.base_version ?? '新建'}
      </p>
      <button
        type="button"
        className="button secondary"
        data-query-receipt={receipt.id}
        onClick={onQuery}
      >
        查询此请求回执
      </button>
    </section>
  );
}
export function CommandForm({ draft, onClose }: { draft: Draft; onClose: () => void }) {
  const workspace = useWorkspace();
  const commands = useCommands();
  const form = useRef<HTMLFormElement>(null);
  const submitting = useRef(false);
  const [preview, setPreview] = useState<CommandRequest | null>(null);
  const [request, setRequest] = useState<CommandRequest | null>(null);
  const [error, setError] = useState('');
  const [unknown, setUnknown] = useState(false);
  const receipt = request ? commands.receipts[request.id] : undefined;
  const mutation = useMutation({ mutationFn: api.command, retry: false, networkMode: 'always' });
  const reason = blocked(draft.kind, workspace.connected, workspace.session, workspace.data);
  useEffect(() => {
    if (receipt?.status === 'rejected') {
      submitting.current = false;
      setPreview(null);
      setError(receipt.message + '；输入已保留，请刷新后重新预览。');
    }
  }, [receipt]);
  function makePreview(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    try {
      if (reason) throw new Error(reason);
      if (draft.organizationId && draft.organizationId !== workspace.orgId)
        throw new Error('组织已切换，请关闭后重新选择操作');
      const data = readForm(draft.kind, form.current!);
      setPreview({
        id: crypto.randomUUID(),
        kind: draft.kind,
        organization_id: draft.organizationId,
        base_version: draft.kind === 'create' ? null : workspace.data!.organization.version,
        data,
      });
      setRequest(null);
      setUnknown(false);
      setError('');
    } catch (failure) {
      setError(errorText(failure));
      setPreview(null);
    }
  }
  async function submit() {
    if (!preview || submitting.current) return;
    if (reason) {
      setError(reason);
      return;
    }
    if (
      draft.organizationId &&
      (draft.organizationId !== workspace.orgId ||
        preview.base_version !== workspace.data?.organization.version)
    ) {
      setError('版本冲突或组织已切换；请重新预览，输入已保留。');
      setPreview(null);
      return;
    }
    const sending = preview;
    try {
      commands.remember({
        id: sending.id,
        organization_id: sending.organization_id,
        kind: sending.kind,
      });
    } catch {
      setError('浏览器无法保留请求标识，尚未提交。请允许会话存储后重试。');
      return;
    }
    submitting.current = true;
    setRequest(sending);
    setError('');
    try {
      const result = await mutation.mutateAsync(sending);
      commands.record(result.receipt);
      void workspace.refresh();
    } catch (failure) {
      // Receipt queries continue independently and take precedence over transport errors.
      setUnknown(true);
      setError(errorText(failure) + '；请查询原请求，不要重复提交。');
      void commands.lookup(sending).catch(() => undefined);
    }
  }
  const hasResult = !!receipt || unknown;
  const hideForm = !!receipt && receipt.status !== 'rejected';
  const previous =
    draft.kind === 'resources'
      ? workspace.data?.organization.resources
      : draft.kind === 'amend'
        ? workspace.data?.charter
        : draft.kind === 'model'
          ? workspace.data?.execution_config
          : null;
  return (
    <>
      <form id="operation-form" ref={form} onSubmit={makePreview} hidden={hideForm}>
        <fieldset
          id="operation-fields"
          disabled={submitting.current && receipt?.status !== 'rejected'}
          onChange={() => {
            if (!submitting.current) setPreview(null);
          }}
        >
          <CommandFields kind={draft.kind} data={draft.data} session={draft.session} />
        </fieldset>
        <p
          id="operation-error"
          className="operation-error"
          role="alert"
          hidden={!error || (!!receipt && receipt.status !== 'rejected')}
        >
          {error}
        </p>
        {preview && (
          <section id="operation-preview" className="preview-panel">
            <h3>{titles[draft.kind]} · 提交预览</h3>
            <p>
              目标：{preview.organization_id || '新组织'} · 基准版本{' '}
              {preview.base_version ?? '新建'}
            </p>
            {previous && (
              <>
                <p>当前采用</p>
                <Json value={previous} />
                <p>拟采用</p>
              </>
            )}
            <Json value={preview.data} />
            {draft.kind === 'amend' && (
              <p>
                受影响的未完成工作：
                {Object.values(workspace.data?.organization.work || {})
                  .filter((w) => !['delivered', 'cancelled'].includes(w.status))
                  .map((w) => w.title)
                  .join('、') || '无'}
                。撤回文本工具后相关未完成工作暂停。
              </p>
            )}
            <small>只有服务器回执确认后，操作才生效。取消不会提交。</small>
          </section>
        )}
        <div className="operation-footer">
          <button
            type="button"
            id="cancel-operation"
            className="button secondary"
            onClick={onClose}
          >
            取消
          </button>
          <button
            type="submit"
            id="preview-operation"
            className="button secondary"
            disabled={submitting.current}
          >
            预览影响
          </button>
          {preview && (
            <button
              type="button"
              id="commit-operation"
              className="button primary"
              disabled={submitting.current || !!reason}
              onClick={() => void submit()}
            >
              {mutation.isPending ? '正在提交…' : '确认提交'}
            </button>
          )}
        </div>
      </form>
      {hasResult && request && (
        <div id="operation-result" role="status">
          {receipt ? (
            <ReceiptView
              receipt={receipt}
              onQuery={() => {
                void commands.lookup(request).catch((e) => setError(errorText(e)));
              }}
            />
          ) : (
            <section className="preview-panel">
              <h3>结果尚未确认</h3>
              <p>原请求 {request.id} 已保留，正在核对服务器回执。</p>
              <button
                type="button"
                className="button secondary"
                data-query-receipt={request.id}
                onClick={() => {
                  void commands.lookup(request).catch((e) => setError(errorText(e)));
                }}
              >
                查询原请求回执
              </button>
            </section>
          )}
        </div>
      )}
    </>
  );
}
