import { useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { api } from '../../api/client';
import { useWorkCommand, WorkScopeLost, type WorkScope } from './useWorkCommand';
import { MaterialPicker } from '../materials/MaterialPicker';
import { checkMaterials, useMaterials } from '../materials/useMaterials';
import type { BusinessMaterial, WorkDeliveryMode } from '../../api/types';

export function CoreWorkRegistration({
  scope,
  canStart,
  onAccessLost,
  durableIntent = false,
}: {
  scope: WorkScope;
  canStart: boolean;
  onAccessLost: () => void;
  durableIntent?: boolean;
}) {
  const command = useWorkCommand(scope, onAccessLost, durableIntent ? {kind: 'start_work_intent'} : undefined);
  const models = useQuery({
    queryKey: ['work-registration-models', scope],
    queryFn: ({ signal }) => api.coreModels(scope.organizationId, signal),
    enabled: canStart,
  });
  const [title, setTitle] = useState(''),
    [goal, setGoal] = useState('');
  const [constraints, setConstraints] = useState('');
  const [deliveryMode, setDeliveryMode] = useState<WorkDeliveryMode>('automatic_text');
  const deliveryModeId = useId();
  const [member, setMember] = useState('AI 助手'),
    [materials, setMaterials] = useState<BusinessMaterial | null>(null);
  const materialRead = useMaterials(scope);
  const selectedMaterial = !materialRead.error ? materialRead.data?.materials.find(item =>
    item.id === materials?.id && item.version === materials.version && item.sha256 === materials.sha256 && item.read_allowed) : undefined;
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
    canStart &&
    !models.error &&
    matches &&
    connection &&
    (!durableIntent || (modelRead.access.can_configure && modelRead.governance_status === 'active' && constraints.length <= 4096)) &&
    modelRead.document_read_allowed &&
    title.trim() &&
    goal.trim() &&
    member.trim() &&
    selectedMaterial &&
    tools.length &&
    Number.isInteger(calls) &&
    calls > 0 &&
    calls <= Math.min(10000, modelRead.resources.plan_max_calls);
  async function submit() {
    if (!ready || !modelRead || !connection || !canStart || !selectedMaterial) return;
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
      materials_root: selectedMaterial.id,
      material_version: selectedMaterial.version,
      max_calls: calls,
      tools: [...tools],
      ...(durableIntent ? { constraints, delivery_mode: deliveryMode } : {}),
      reason: durableIntent ? '用户批准这项工作的目标、责任、调用预算与交付方式' : '用户在核心任务页登记目标、责任与有限预算',
    };
    await command.send(data, modelRead.version, async (read) => {
      const freshMaterials = checkMaterials(await api.coreMaterials(scope.organizationId), scope);
      const currentMaterial = freshMaterials.materials.find(item => item.id === selectedMaterial.id);
      if (freshMaterials.version !== read.version || !currentMaterial?.read_allowed ||
          currentMaterial.version !== selectedMaterial.version || currentMaterial.sha256 !== selectedMaterial.sha256)
        throw new Error('资料许可或版本已变化，请重新选择后提交');
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
    <section aria-label={durableIntent ? '开始 AI 工作' : '登记 AI 工作'}>
      {command.reference ? (
        <>
          {durableIntent ? <>
            <p>{command.reference.resolved ? (command.reference.outcome === 'succeeded' ? '工作意图已持久接受，进度见原工作。' : '开始工作的请求已被拒绝。') : '开始工作的原请求已保留，请查询原回执。'}</p>
            <details><summary>开始工作请求记录</summary><p>{command.reference.id}</p></details>
          </> : <p>
              {command.reference.resolved ? '登记已记录' : '登记原请求已保留；请查询，不要重复登记'} ·{' '}
              {command.reference.id}
            </p>}
          <button type="button" disabled={command.checking} onClick={() => void command.lookup()}>
            {durableIntent ? '查询开始工作的原请求' : '查询登记原请求'}
          </button>
          {canStart && command.reference.resolved && (
            <button
              type="button"
              disabled={command.sending || command.checking}
              onClick={() => {
                command.another();
                if (!durableIntent || command.reference?.outcome === 'succeeded') {
                  setTitle('');
                  setGoal('');
                  setConstraints('');
                  setDeliveryMode('automatic_text');
                  setMaterials(null);
                }
                void models.refetch();
              }}
            >
              {durableIntent ? (command.reference.outcome === 'succeeded' ? '提出另一项工作' : '返回工作目标') : '登记另一项工作'}
            </button>
          )}
        </>
      ) : (
        (canStart || durableIntent) && (
          <details className="start-work">
            <summary>{durableIntent ? '提出工作目标' : '登记新的 AI 工作'}</summary>
            {durableIntent ? <>
              <p>批准后，工作按所选资料、模型版本、工具和调用上限推进。目标与约束只用于执行这项工作。</p>
              {!canStart && <p>当前无法开始工作。请核对治理授权和已采用的默认模型连接。可在本页保留目标。</p>}
              {matches && connection && (!modelRead.document_read_allowed || modelRead.governance_status !== 'active' || !modelRead.access.can_configure) &&
                <p>当前治理或资料工具授权不足，请到“能力与资源”核对。</p>}
            </> : <p>保存目标、责任成员和调用预算；登记不调用模型，保存后可另行准备并运行。</p>}
            {matches && connection ? (
              <p>
                采用连接：{connection.name} · {connection.model}{durableIntent && ` · 版本 ${connection.revision}`}
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
            {durableIntent && <label>
              约束（选填）
              <textarea maxLength={4096} value={constraints} onChange={(e) => setConstraints(e.target.value)} />
            </label>}
            <label>
              负责 AI 成员名称
              <input maxLength={200} value={member} onChange={(e) => setMember(e.target.value)} />
            </label>
            <MaterialPicker scope={scope} value={materials} onChange={setMaterials} />
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
            {durableIntent && <>
              <label htmlFor={deliveryModeId}>交付方式</label>
              <select id={deliveryModeId} value={deliveryMode} onChange={e => setDeliveryMode(e.target.value === 'governor_review' ? 'governor_review' : 'automatic_text')}>
                <option value="automatic_text">自动交付文本</option>
                <option value="governor_review">由治理者审查后交付</option>
              </select>
              <p>自动交付范围仅限这项工作的同组织文本成果。章程、组织目标、资源、任职、授权与退出事项仍按组织治理规则处理。</p>
            </>}
            <button
              type="button"
              disabled={!ready || command.sending || command.blocked || models.isFetching}
              onClick={() => void submit()}
            >
              {durableIntent ? '开始工作' : '登记 AI 工作'}
            </button>
            <button
              type="button"
              disabled={command.sending || models.isFetching}
              onClick={() => void models.refetch()}
            >
              {durableIntent ? '刷新模型配置' : '刷新登记配置'}
            </button>
          </details>
        )
      )}
      {command.note && <p role="status">{command.note}</p>}
    </section>
  );
}
