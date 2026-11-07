import { Link } from 'react-router-dom';
import { Card, Empty } from '../../components/ui';
import { hasBlockingModelCheck, remainingCalls } from './model';
import { pendingForTarget } from './requests';
import type { ModelCheck, ModelDiagnostic, ModelDraft, ModelKind, ModelUsage } from './types';
import type { ModelsController } from './useModels';

export type OpenModelCommand = (
  kind: ModelKind,
  options?: Partial<
    Pick<ModelDraft, 'connection' | 'check' | 'operation' | 'enabled' | 'makeDefault'>
  >,
) => void;
function DiagnosticNextStep({ diagnostic }: { diagnostic?: ModelDiagnostic | null }) {
  return diagnostic ? <p className="model-next-step">下一步：{diagnostic.next_step}</p> : null;
}
export function ConnectionRecords({
  controller,
  open,
}: {
  controller: ModelsController;
  open: OpenModelCommand;
}) {
  const { read } = controller;
  if (!read) return null;
  return (
    <Card title="模型连接">
      {!read.connections.length ? (
        <Empty title="还没有保存的连接">填写文本 API，或使用已明确授予本 AU 的模型服务授权。</Empty>
      ) : (
        <ul className="governance-records model-connections">
          {read.connections.map((connection) => {
            const verified =
              connection.last_check?.revision === connection.revision &&
              connection.last_check.profile === connection.profile;
            const pending = pendingForTarget(
              controller.references,
              controller.scope,
              connection.id,
            );
            const saving = controller.references.some(
              (reference) =>
                reference.organization_id === read.organization_id &&
                reference.target === connection.id &&
                reference.kind === 'save_connection' &&
                read.operations.some(
                  (operation) =>
                    operation.id === reference.id &&
                    ['saving', 'unknown'].includes(operation.status),
                ),
            );
            const checking = hasBlockingModelCheck(read, connection);
            const writable =
              controller.connected && controller.allowed('save_connection') && !pending && !saving;
            const canCheck =
              writable &&
              connection.enabled &&
              read.document_read_allowed &&
              read.resources.grant?.allow_unknown_cost &&
              remainingCalls(read) >= 2 &&
              !checking;
            return (
              <li key={connection.id}>
                <div className="governance-record-heading">
                  <h3>{connection.name}</h3>
                  <span className="quiet-pill">
                    {connection.is_default ? '当前默认' : connection.enabled ? '已启用' : '已停用'}
                  </span>
                </div>
                <p>
                  {connection.model} ·{' '}
                  {connection.profile === 'openai_compatible' ? '兼容文本 API'
                    : connection.profile === 'openai_responses' ? 'OpenAI Responses API' : '已有 AU 模型授权'}{' '}
                  · 连接 v{connection.revision}
                </p>
                <p className="model-address">
                  {connection.base_url ??
                    `AU 授权 ${connection.grant_ref} · v${connection.grant_revision}`}
                </p>
                <p>
                  {verified
                    ? `此版本已通过工具往返 · ${new Date(connection.last_check!.at * 1000).toLocaleString('zh-CN')}`
                    : '尚未验证此版本'}
                </p>
                <p className="form-note">
                  每次最多输出 {connection.max_output_tokens} token。采用默认与验证分别操作。
                </p>
                {(pending || saving) && (
                  <p role="status">此连接有待核对的保存或请求，请先查询原记录。</p>
                )}
                {checking && (
                  <p role="status">此连接已有未结束的验证，请在下方查看或核对原验证。</p>
                )}
                <div className="governance-actions">
                  <button
                    type="button"
                    className="button secondary"
                    disabled={!writable}
                    onClick={() => open('save_connection', { connection })}
                  >
                    编辑连接
                  </button>
                  <button
                    type="button"
                    className="button secondary"
                    disabled={!canCheck}
                    onClick={() => open('start_model_check', { connection })}
                  >
                    验证工具往返
                  </button>
                  {!connection.is_default && (
                    <button
                      type="button"
                      className="button secondary"
                      disabled={!writable || !connection.enabled}
                      onClick={() =>
                        open('set_connection', { connection, enabled: true, makeDefault: true })
                      }
                    >
                      设为默认
                    </button>
                  )}
                  <button
                    type="button"
                    className="button secondary"
                    disabled={
                      connection.enabled
                        ? !controller.connected ||
                          !controller.allowed('set_connection', { enabled: false })
                        : !writable
                    }
                    onClick={() =>
                      open('set_connection', { connection, enabled: !connection.enabled })
                    }
                  >
                    {connection.enabled ? '停用连接' : '启用连接'}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
export function OperationRecords({
  controller,
  open,
}: {
  controller: ModelsController;
  open: OpenModelCommand;
}) {
  if (!controller.read?.operations.length) return null;
  return (
    <Card title="连接保存记录">
      <ul className="governance-records">
        {[...controller.read.operations].reverse().map((operation) => (
          <li key={operation.id}>
            <p>
              <strong>
                {operation.status === 'succeeded'
                  ? '连接保存完成'
                  : operation.status === 'unknown'
                    ? '保存结果待核对'
                    : operation.status === 'rejected'
                      ? '连接未采用'
                      : '正在保存连接'}
              </strong>
            </p>
            <p>{operation.message}</p>
            <DiagnosticNextStep diagnostic={operation.diagnostic} />
            <details>
              <summary>原保存标识</summary>
              <p>{operation.id}</p>
            </details>
            {operation.status === 'unknown' && (
              <button
                type="button"
                className="button secondary"
                disabled={!controller.connected || !controller.allowed('reconcile_connection')}
                onClick={() => open('reconcile_connection', { operation })}
              >
                核对原保存操作
              </button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}
const statusLabels: Record<ModelCheck['status'], string> = {
  queued: '等待验证',
  running: '验证进行中',
  unknown: '验证结果待核对',
  not_adopted: '结果未采用',
  failed: '验证未通过',
  succeeded: '工具往返已通过',
  cancel_requested: '本地停止已请求',
};
const attemptLabels: Record<string, string> = {
  prepared: '已预约',
  dispatching: '已派发，等待结果',
  completed: '已完成',
  failed: '失败',
  unknown: '结果待核对',
  not_adopted: '未采用',
  interrupted: '已中断',
  cancelled: '本地已停止',
};
const usageBasis = (usage: ModelUsage) =>
  usage.basis === 'result'
    ? '最终结果'
    : usage.basis === 'events'
      ? '已观测事件（非完整结果）'
      : '未知';
const amount = (usage: ModelUsage) =>
  usage.cost_minor === null || !usage.currency
    ? '未知'
    : `${usage.cost_minor} ${usage.currency}（最小货币单位）`;
export function CheckRecords({
  controller,
  open,
}: {
  controller: ModelsController;
  open: OpenModelCommand;
}) {
  const read = controller.read;
  if (!read) return null;
  return (
    <Card title="工具往返与用量记录">
      <p className="form-note">
        结果按原验证保存。每次推理单独计量；缺失用量和费用保持未知。此处不把接入检查视为正式业务成果。
      </p>
      {!read.checks.length ? (
        <Empty title="还没有验证记录">
          授予两次以上有限调用，并在章程中允许只读资料后，选择连接验证。
        </Empty>
      ) : (
        <ul className="governance-records model-checks">
          {[...read.checks].reverse().map((check) => {
            const canManage = controller.connected && controller.allowed('reconcile_model_check');
            return (
              <li key={check.id}>
                <div className="governance-record-heading">
                  <h3>{check.document_name}</h3>
                  <span className="quiet-pill">{statusLabels[check.status]}</span>
                </div>
                <p>
                  {read.connections.find((connection) => connection.id === check.connection_id)
                    ?.name ?? check.connection_id}{' '}
                  · 验证时连接 v{check.connection_revision}
                </p>
                <p>{check.message}</p>
                <DiagnosticNextStep diagnostic={check.diagnostic} />
                {check.output && <blockquote className="au-text">{check.output}</blockquote>}
                {!!check.attempts.length && (
                  <div className="table-scroll">
                    <table>
                      <caption>每次推理的用量与费用</caption>
                      <thead>
                        <tr>
                          <th>推理</th>
                          <th>状态</th>
                          <th>输入 / 输出 token</th>
                          <th>费用</th>
                        </tr>
                      </thead>
                      <tbody>
                        {check.attempts.map((attempt) => (
                          <tr key={attempt.id}>
                            <th scope="row">第 {attempt.stage + 1} 次</th>
                            <td>
                              <span>{attemptLabels[attempt.state] ?? attempt.state}</span>
                              <DiagnosticNextStep diagnostic={attempt.diagnostic} />
                              {attempt.state === 'cancelled' && (
                                <p className="model-next-step">
                                  本地停止不表示远端已取消或费用退还；已发生用量仍保留。
                                </p>
                              )}
                            </td>
                            <td>
                              <span>
                                {attempt.usage.input_tokens ?? '未知'} /{' '}
                                {attempt.usage.output_tokens ?? '未知'}
                              </span>
                              <p className="model-usage-basis">
                                用量依据：{usageBasis(attempt.usage)}
                              </p>
                            </td>
                            <td>{amount(attempt.usage)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <details>
                  <summary>责任、授权与逐次依据</summary>
                  <p>
                    验证工作：{check.work_id} · 责任成员：{check.member_id}
                  </p>
                  <p>
                    责任绑定：{check.binding_id} · v{check.binding_version}；有限授权：
                    {check.mandate_id} · v{check.mandate_version}
                  </p>
                  <p>
                    执行定义：{check.agent_definition.id} · v{check.agent_definition.version}
                    ；资源授权 v{check.resource_revision}
                  </p>
                  <p>原验证：{check.id}</p>
                  {check.attempts.map((attempt) => (
                    <p key={attempt.id}>
                      第 {attempt.stage + 1} 次：{attempt.id}；缓存输入{' '}
                      {attempt.usage.cached_input_tokens ?? '未知'}，缓存写入{' '}
                      {attempt.usage.cache_write_tokens ?? '未知'}，推理 token{' '}
                      {attempt.usage.reasoning_tokens ?? '未知'}；费用状态{' '}
                      {attempt.usage.cost_status === 'unknown' ? '未知' : attempt.usage.cost_status}
                      ；已观测事件序号：{attempt.usage.observed_through_seq ?? '未知'}。
                    </p>
                  ))}
                  <Link
                    to={{
                      pathname: '/tasks',
                      search: '?organization=' + encodeURIComponent(read.organization_id),
                    }}
                  >
                    查看责任与工作
                  </Link>
                </details>
                {check.waiting && (
                  <p className="form-note">
                    等待：{check.waiting.condition}。责任成员：{check.waiting.responsible_member_id}
                    ；原等待对象：{check.waiting.object}。
                  </p>
                )}
                {['queued', 'running', 'unknown', 'cancel_requested'].includes(check.status) && (
                  <div className="governance-actions">
                    {(check.status === 'unknown' || check.status === 'cancel_requested') && (
                      <button
                        type="button"
                        className="button secondary"
                        disabled={!canManage}
                        onClick={() => open('reconcile_model_check', { check })}
                      >
                        核对原验证
                      </button>
                    )}
                    {!check.stop_requested && (
                      <button
                        type="button"
                        className="button secondary"
                        disabled={!canManage}
                        onClick={() => open('cancel_model_check', { check })}
                      >
                        停止后续步骤
                      </button>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
