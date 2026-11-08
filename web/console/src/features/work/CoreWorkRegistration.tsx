import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import { useWorkCommand, WorkScopeLost, type WorkScope } from './useWorkCommand';

export function CoreWorkRegistration({
  scope,
  canStart,
  onAccessLost,
}: {
  scope: WorkScope;
  canStart: boolean;
  onAccessLost: () => void;
}) {
  const command = useWorkCommand(scope, onAccessLost);
  const models = useQuery({
    queryKey: ['work-registration-models', scope],
    queryFn: ({ signal }) => api.coreModels(scope.organizationId, signal),
    enabled: canStart,
  });
  const [title, setTitle] = useState(''),
    [goal, setGoal] = useState('');
  const [member, setMember] = useState('AI 助手'),
    [materials, setMaterials] = useState('');
  const [maxCalls, setMaxCalls] = useState('2');
  const [tools, setTools] = useState(['read_document']);
  const modelRead = models.data;
  const connection = modelRead?.connections.find((c) => c.is_default && c.enabled);
  const matches =
    modelRead?.protocol === 'core.models.v1' &&
    modelRead.organization_id === scope.organizationId &&
    modelRead.access.principal_id === scope.principalId;
  const calls = Number(maxCalls);
  const ready =
    matches &&
    connection &&
    modelRead.document_read_allowed &&
    title.trim() &&
    goal.trim() &&
    member.trim() &&
    /^[\p{L}\p{N}][\p{L}\p{N}_-]{0,63}$/u.test(materials) &&
    tools.length &&
    Number.isInteger(calls) &&
    calls > 0 &&
    calls <= Math.min(10000, modelRead.resources.plan_max_calls);
  async function submit() {
    if (!ready || !modelRead || !connection || !canStart) return;
    const workId = 'work-' + crypto.randomUUID();
    const data = {
      work_id: workId,
      title,
      goal,
      member_name: member,
      member_id: workId + '-member',
      binding_id: workId + '-binding',
      mandate_id: workId + '-mandate',
      definition_id: workId + '-definition',
      connection_id: connection.id,
      expected_revision: connection.revision,
      materials_root: materials,
      max_calls: calls,
      tools: [...tools],
      reason: '用户在核心任务页登记目标、责任与有限预算',
    };
    await command.send(data, modelRead.version, async (read) => {
      const fresh = await api.coreModels(scope.organizationId);
      const selected = fresh.connections.find((c) => c.id === connection.id);
      if (
        fresh.protocol !== 'core.models.v1' ||
        fresh.organization_id !== scope.organizationId ||
        fresh.access.principal_id !== scope.principalId
      )
        throw new WorkScopeLost();
      if (
        fresh.version !== read.version ||
        !fresh.access.can_configure ||
        fresh.governance_status !== 'active' ||
        !fresh.document_read_allowed ||
        !selected?.enabled ||
        !selected.is_default ||
        selected.revision !== connection.revision ||
        calls > fresh.resources.plan_max_calls
      ) {
        throw new Error('配置或版本已变化，请刷新核对后提交');
      }
    });
  }
  return (
    <section aria-label="登记 AI 工作">
      {command.reference ? (
        <>
          <p>
            {command.reference.resolved ? '登记已记录' : '登记原请求已保留；请查询，不要重复登记'} ·{' '}
            {command.reference.id}
          </p>
          <button type="button" disabled={command.checking} onClick={() => void command.lookup()}>
            查询登记原请求
          </button>
          {canStart && command.reference.resolved && (
            <button
              type="button"
              disabled={command.sending || command.checking}
              onClick={() => {
                command.another();
                setTitle('');
                setGoal('');
                setMaterials('');
                void models.refetch();
              }}
            >
              登记另一项工作
            </button>
          )}
        </>
      ) : (
        canStart && (
          <details className="start-work">
            <summary>登记新的 AI 工作</summary>
            <p>保存目标、责任成员和调用预算；登记不调用模型，保存后可另行准备并运行。</p>
            {matches && connection ? (
              <p>
                采用连接：{connection.name} · {connection.model}
              </p>
            ) : (
              <p>尚无可用的已采用连接，请先到“模型与 API”页核对。</p>
            )}
            <label>
              工作标题
              <input maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label>
              目标
              <textarea maxLength={100000} value={goal} onChange={(e) => setGoal(e.target.value)} />
            </label>
            <label>
              负责 AI 成员名称
              <input maxLength={200} value={member} onChange={(e) => setMember(e.target.value)} />
            </label>
            <label>
              资料目录引用
              <input
                value={materials}
                onChange={(e) => setMaterials(e.target.value)}
                placeholder="宿主已登记的资料引用"
              />
            </label>
            <label>
              调用上限
              <input
                type="number"
                min={1}
                max={10000}
                step={1}
                value={maxCalls}
                onChange={(e) => setMaxCalls(e.target.value)}
              />
            </label>
            <fieldset>
              <legend>允许的工具</legend>
              {['read_document', 'list_documents'].map((tool) => (
                <label key={tool}>
                  <input
                    type="checkbox"
                    checked={tools.includes(tool)}
                    onChange={() =>
                      setTools((list) =>
                        list.includes(tool) ? list.filter((t) => t !== tool) : [...list, tool],
                      )
                    }
                  />
                  {tool}
                </label>
              ))}
            </fieldset>
            <button
              type="button"
              disabled={!ready || command.sending || command.blocked || models.isFetching}
              onClick={() => void submit()}
            >
              登记 AI 工作
            </button>
            <button
              type="button"
              disabled={command.sending || models.isFetching}
              onClick={() => void models.refetch()}
            >
              刷新登记配置
            </button>
          </details>
        )
      )}
      {command.note && <p role="status">{command.note}</p>}
    </section>
  );
}
