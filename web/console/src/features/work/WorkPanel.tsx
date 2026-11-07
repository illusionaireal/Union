import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api, errorText } from '../../api/client';
import { useQuery as useModelsQuery } from '@tanstack/react-query';
import type { CoreWorkItem } from '../../api/types';
import { Card } from '../../components/ui';

function money(item: CoreWorkItem) {
  const { max_calls: max, reserved, used } = item.budget;
  return `${used} 已用 · ${reserved} 已预约 · 上限 ${max}`;
}

function receipt(item: CoreWorkItem) {
  const last = item.tool_calls[item.tool_calls.length - 1];
  if (!last) return '尚无工具回执';
  const detail = last.sha256 ? `sha256 ${last.sha256.slice(0, 12)}…` : `${last.count ?? 0} 份资料`;
  return `${last.tool} @ ${last.step_ref} · ${detail}`;
}

function resultHref(organizationId: string, id: string) {
  return `/api/v1/work/results?organization_id=${encodeURIComponent(organizationId)}&id=${encodeURIComponent(id)}`;
}

function attempt(item: CoreWorkItem) {
  const running = item.attempts.find((value) => value.status === 'running');
  const unknown = item.attempts.find((value) => value.status === 'unknown');
  if (unknown) return `执行结果未知，待核对（${unknown.id}）`;
  if (running) return `执行中（${running.id}）`;
  return item.attempts.length ? '本轮执行已结束' : '尚未开始执行';
}

function StartWorkForm({ organizationId, send, busy }: { organizationId: string; send: (kind: string, payload: Record<string, unknown>) => void; busy: boolean }) {
  const models = useModelsQuery({
    queryKey: ['core-models', organizationId],
    queryFn: ({ signal }) => api.coreModels(organizationId, signal),
  });
  const [title, setTitle] = useState('');
  const [goal, setGoal] = useState('');
  const [materials, setMaterials] = useState('');
  const [maxCalls, setMaxCalls] = useState('4');
  const [tools, setTools] = useState<string[]>(['read_document']);
  const connection = (models.data?.connections ?? []).find((value) => value.is_default && value.enabled);
  const toggleTool = (tool: string) =>
    setTools((current) => (current.includes(tool) ? current.filter((value) => value !== tool) : [...current, tool]));
  const needsMaterials = tools.includes('read_document') || tools.includes('list_documents');
  const ready = title.trim() !== '' && goal.trim() !== '' && tools.length > 0 && (needsMaterials ? materials.trim() !== '' : true);
  return (
    <details className="start-work">
      <summary>登记新的 AI 工作</summary>
      {!connection && <p className="form-note">还没有已采用的默认模型连接；先在“模型与 API”页保存、测试并采用一个连接。</p>}
      <label>
        工作标题
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        目标
        <textarea value={goal} onChange={(event) => setGoal(event.target.value)} />
      </label>
      <label>
        资料目录引用
        <input value={materials} onChange={(event) => setMaterials(event.target.value)} placeholder="宿主已登记的引用，例如 project-docs" />
      </label>
      <label>
        调用上限
        <input type="number" min={1} value={maxCalls} onChange={(event) => setMaxCalls(event.target.value)} />
      </label>
      <fieldset>
        <legend>允许的工具</legend>
        {['read_document', 'list_documents'].map((tool) => (
          <label key={tool}>
            <input type="checkbox" checked={tools.includes(tool)} onChange={() => toggleTool(tool)} />
            {tool}
          </label>
        ))}
      </fieldset>
      <button
        type="button"
        disabled={busy || !ready || !connection}
        onClick={() => {
          const workId = 'work-' + Date.now();
          send('start_work', {
            work_id: workId,
            title,
            goal,
            member_name: '资料整理 Agent',
            member_id: workId + '-member',
            binding_id: workId + '-binding',
            mandate_id: workId + '-mandate',
            definition_id: workId + '-definition',
            connection_id: connection?.id,
            expected_revision: connection?.revision,
            materials_root: needsMaterials ? materials : null,
            max_calls: Number(maxCalls),
            tools,
            reason: '界面登记有责任成员的 AI 工作',
          });
        }}
      >
        登记 AI 工作
      </button>
    </details>
  );
}

function ResultForm({ item, send, busy }: { item: CoreWorkItem; send: (kind: string, payload: Record<string, unknown>) => void; busy: boolean }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const refs = [...item.steps.map((step) => step.step_ref), ...item.tool_calls.map((call) => call.step_ref)];
  const toggle = (ref: string) =>
    setSources((current) => (current.includes(ref) ? current.filter((value) => value !== ref) : [...current, ref]));
  const ready = title.trim() !== '' && content.trim() !== '' && sources.length > 0;
  return (
    <details className="result-form">
      <summary>提交候选成果</summary>
      <label>
        成果标题
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        成果正文
        <textarea value={content} onChange={(event) => setContent(event.target.value)} />
      </label>
      <fieldset>
        <legend>来源回执</legend>
        {refs.length === 0 && <p>还没有可引用的执行步进或工具回执；先开始执行并读取资料。</p>}
        {refs.map((ref) => (
          <label key={ref}>
            <input type="checkbox" checked={sources.includes(ref)} onChange={() => toggle(ref)} />
            {ref}
          </label>
        ))}
      </fieldset>
      <button
        type="button"
        disabled={busy || !ready}
        onClick={() =>
          send('submit_result', {
            work_id: item.id,
            result_id: 'result-' + Date.now(),
            title,
            content,
            sources,
          })
        }
      >
        提交成果
      </button>
    </details>
  );
}

function AttemptActions({ item, send, busy }: { item: CoreWorkItem; send: (kind: string, payload: Record<string, unknown>) => void; busy: boolean }) {
  const [outcome, setOutcome] = useState('delivered');
  const running = item.attempts.find((attempt) => attempt.status === 'running');
  if (!running) return null;
  return (
    <span className="attempt-actions">
      <label>
        结束结果
        <select value={outcome} onChange={(event) => setOutcome(event.target.value)}>
          <option value="delivered">已交付</option>
          <option value="failed">失败</option>
          <option value="stopped">停止</option>
          <option value="unknown">结果未知</option>
        </select>
      </label>
      <button
        type="button"
        disabled={busy}
        onClick={() =>
          send('finish_attempt', {
            work_id: item.id,
            attempt_id: running.id,
            outcome,
            reason: '界面操作：以 ' + outcome + ' 结束该次执行',
          })
        }
      >
        结束执行
      </button>
    </span>
  );
}

export function WorkPanel({ organizationId }: { organizationId: string }) {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ status: string; message?: string } | null>(null);
  const { data, isPending, error } = useQuery({
    queryKey: ['core-work', organizationId],
    queryFn: ({ signal }) => api.coreWork(organizationId, signal),
  });
  const send = async (kind: string, payload: Record<string, unknown>) => {
    if (!data) return;
    setBusy(true);
    setNote(null);
    try {
      const response = await api.coreWorkCommand({
        id: 'ui-' + Date.now() + '-' + Math.random().toString(16).slice(2),
        organization_id: organizationId,
        base_version: data.version,
        kind,
        data: payload,
      });
      setNote(response.receipt);
      await client.invalidateQueries({ queryKey: ['core-work', organizationId] });
    } catch (failure) {
      setNote({ status: 'failed', message: errorText(failure) });
    } finally {
      setBusy(false);
    }
  };
  if (isPending) return <Card title="AI 工作（V1）">正在读取…</Card>;
  if (error || !data) return <Card title="AI 工作（V1）">读取失败，可刷新重试。</Card>;
  if (!data.works.length) {
    return (
      <Card title="AI 工作（V1）">
        {data.access.can_start && <StartWorkForm organizationId={organizationId} send={send} busy={busy} />}
        <p>尚未登记 V1 工作。登记后这里会显示负责成员、有效授权、调用预算、执行尝试与工具回执。</p>
      </Card>
    );
  }
  return (
    <Card title="AI 工作（V1）">
      {data.access.can_start && <StartWorkForm organizationId={organizationId} send={send} busy={busy} />}
      <ul className="work-panel" aria-label="V1 工作列表">
        {data.works.map((item) => (
          <li key={item.id} data-work={item.id}>
            <strong>{item.title}</strong>
            <p>{item.goal}</p>
            <dl>
              <div><dt>负责成员</dt><dd>{item.responsible.name}（{item.responsible.duty}）</dd></div>
              <div><dt>有效授权</dt><dd>{item.mandate.actions.join('、')}{item.mandate.active ? '' : '（已失效）'}</dd></div>
              <div><dt>调用预算</dt><dd>{money(item)}</dd></div>
              <div><dt>执行</dt><dd>{attempt(item)}</dd></div>
              <div><dt>最近工具回执</dt><dd>{receipt(item)}</dd></div>
              <div>
                <dt>成果</dt>
                <dd>
                  {item.results.length === 0 && '尚无候选成果'}
                  {item.results.map((value) => (
                    <span key={value.id} className="result-line">
                      {value.title}（{value.status === 'adopted' ? '已采用' : '候选'} · {value.sha256.slice(0, 12)}…）
                      <a href={resultHref(organizationId, value.id)} download={`${value.id}.json`}>下载</a>
                    </span>
                  ))}
                </dd>
              </div>
              <div>
                <dt>授权资料</dt>
                <dd>
                  {item.materials.reference
                    ? `${item.materials.reference} · ${item.materials.available ? `可读 ${item.materials.documents} 份` : '宿主未就绪'}`
                    : '未绑定'}
                </dd>
              </div>
            </dl>
            <div className="work-actions">
              <button type="button" disabled={busy} onClick={() => send('start_attempt', { work_id: item.id })}>
                开始执行
              </button>
              <button type="button" disabled={busy} onClick={() => send('reserve_step', { work_id: item.id })}>
                预约一次调用
              </button>
              <AttemptActions item={item} send={send} busy={busy} />
              {(() => {
                const adopted = item.results.find((value) => value.status === 'adopted');
                const running = item.attempts.some((attempt) => attempt.status === 'running');
                if (!adopted || running || item.status === 'delivered') return null;
                return (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => send('deliver_work', { work_id: item.id, result_id: adopted.id })}
                  >
                    完成工作
                  </button>
                );
              })()}
              {item.results
                .filter((value) => value.status === 'candidate')
                .map((value) => (
                  <button
                    key={value.id}
                    type="button"
                    disabled={busy}
                    onClick={() => send('adopt_result', { work_id: item.id, result_id: value.id })}
                  >
                    采用成果
                  </button>
                ))}
            </div>
            <ResultForm item={item} send={send} busy={busy} />
          </li>
        ))}
      </ul>
      {note && (
        <p role="status" className="form-note">
          {note.status === 'succeeded' ? '操作已记录：' + (note.message ?? '') : '操作未完成：' + (note.message ?? note.status)}
        </p>
      )}
    </Card>
  );
}
