import { draftTitle, remainingCalls } from './model';
import type { ModelDraft, ModelRead, ModelRequest } from './types';

export function ModelPreview({
  draft,
  request,
  read,
}: {
  draft: ModelDraft;
  request: ModelRequest;
  read: ModelRead;
}) {
  const data = request.data;
  return (
    <section className="preview-panel" aria-label="模型操作预览">
      <h3>{draftTitle(draft)} · 提交预览</h3>
      <p>
        AU：{draft.core.au.name} · 基准版本 v{request.base_version}
      </p>
      {request.kind === 'save_connection' && (
        <dl className="au-facts">
          <div>
            <dt>连接</dt>
            <dd>
              {String(data.name)} · {String(data.model)}
            </dd>
          </div>
          <div>
            <dt>接入方式</dt>
            <dd>
              {data.profile !== 'modeld_grant'
                ? `${data.profile === 'openai_responses' ? 'OpenAI Responses API · ' : ''}${String(data.base_url)}`
                : `已有 AU 授权 ${data.grant_ref} · v${data.grant_revision}`}
            </dd>
          </div>
          <div>
            <dt>本次影响</dt>
            <dd>
              保存连接，不推理、不切换默认。{draft.connection ? '旧版本验证结论不会沿用。' : ''}
            </dd>
          </div>
          <div>
            <dt>每次输出上限</dt>
            <dd>{String(data.max_output_tokens)} token</dd>
          </div>
        </dl>
      )}
      {request.kind === 'grant_model_resources' && (
        <>
          <p>
            调用总上限：{read.resources.grant?.max_calls ?? '未授权'} → {String(data.max_calls)}{' '}
            次。已用或预约 {read.resources.reserved_calls} 次。
          </p>
          <p>
            {data.allow_unknown_cost
              ? '已明确接受供应商费用可能未知；不承诺金额封顶。'
              : '未接受费用未知，不能发起接入验证。'}
          </p>
          <p>授权依据：{String(data.reason)}</p>
        </>
      )}
      {request.kind === 'start_model_check' && (
        <>
          <p>
            连接：{draft.connection!.name} · v{draft.connection!.revision} ·{' '}
            {draft.connection!.model}
          </p>
          <p>
            资料：{String(data.document_name)} · {String(data.document_text).length}{' '}
            字符。内容将发送给所选模型服务。
          </p>
          <p>
            预留两次推理和一次只读资料工具；当前剩余 {remainingCalls(read)} 次调用，费用可能未知。
          </p>
          <p>
            责任：
            {data.binding_id
              ? '所选的当前本人职责绑定'
              : '由当前登录治理者本人承担，并保存独立责任记录'}
            。
          </p>
        </>
      )}
      {request.kind === 'set_connection' && (
        <p>
          {draft.makeDefault
            ? '采用默认连接不调用模型，也不把未测试的配置标记为已验证。'
            : draft.enabled
              ? '启用增加连接版本；原记录与用量保留。'
              : '停用增加连接版本；在途结果仍按原请求核对，不承诺远端已取消。'}
        </p>
      )}
      {request.kind === 'reconcile_connection' && (
        <p>只查询原保存操作 {String(data.operation_id)}，不再次提交注册。</p>
      )}
      {request.kind === 'reconcile_model_check' && (
        <p>
          核对原验证 {String(data.check_id)}；如仍有授权，可继续尚未派发的后续步骤。未知调用不重发。
        </p>
      )}
      {request.kind === 'cancel_model_check' && (
        <p>停止依据：{String(data.reason)}。这是本地停止请求，未确认费用仍保留。</p>
      )}
    </section>
  );
}
