import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import { isGovernedAU } from '../../api/core-boundary';
import { Card } from '../../components/ui';
import { modelsApi } from './api';
import { assertSession } from './requests';
import type { ModelEvent, ModelEvents } from './types';
import type { ModelsController } from './useModels';

interface History { cursor: number; events: Map<number, ModelEvent>; truncated: boolean }
const empty = (): History => ({ cursor: 0, events: new Map(), truncated: false });
const mismatch = () => new ApiError('原生成记录身份或序号不一致', 409, 'incompatible_state');
const activeStates = new Set(['prepared', 'dispatching', 'queued', 'running']);

function append(prior: History, result: ModelEvents): History {
  if (!Number.isSafeInteger(result.cursor) || !Number.isSafeInteger(result.last_seq) ||
      result.cursor < prior.cursor || result.last_seq < result.cursor || !Array.isArray(result.events) ||
      result.events.length > 500 || (result.has_more && result.cursor <= prior.cursor)) throw mismatch();
  const events = new Map(prior.events);
  let last = 0;
  for (const event of result.events) {
    if (!event || !Number.isSafeInteger(event.seq) || event.seq <= last || event.seq > result.cursor ||
        !(event.type === 'text_delta' && typeof event.text === 'string' ||
          event.type === 'tool_call_complete' && event.name === 'read_document')) throw mismatch();
    last = event.seq;
    const previous = events.get(event.seq);
    if (previous ? JSON.stringify(previous) !== JSON.stringify(event) : event.seq <= prior.cursor) throw mismatch();
    events.set(event.seq, event);
  }
  // Bound in-memory observation. The authoritative journal remains unchanged.
  let remaining = 262144, truncated = prior.truncated || result.truncated;
  for (const event of events.values()) {
    if (event.type === 'text_delta') {
      remaining -= event.text.length;
      if (remaining < 0) truncated = true;
    }
  }
  truncated ||= events.size >= 20000;
  return { cursor: result.cursor, events, truncated };
}

export function ModelStream({ controller }: { controller: ModelsController }) {
  const [selection, setSelection] = useState('');
  const [expanded, setExpanded] = useState(false);
  const options = controller.read?.checks.flatMap(check => check.attempts.map(attempt => ({
    key: `${check.id}:${attempt.id}`, checkId: check.id, attemptId: attempt.id,
    connectionId: check.connection_id, connectionRevision: check.connection_revision,
    label: `${check.document_name} · 第 ${attempt.stage + 1} 次`,
  }))) ?? [];
  const selected = selection ? options.find(item => item.key === selection) : options.at(-1);
  const connection = controller.read?.connections.find(item => item.id === selected?.connectionId);
  const readable = !!selected && !!connection?.enabled && connection.revision === selected.connectionRevision;
  const core = controller.workspace.core;
  if (!options.length || !core || !isGovernedAU(core) || core.access.role !== 'governor') return null;
  return <Card title="原请求生成过程">
    <p>查看已保存的部分输出；完整回应、采用结果与用量见原验证记录。</p>
    <label>查看哪次原调用
      <select aria-label="查看哪次原调用" value={selected?.key ?? ''}
        onChange={event => setSelection(event.target.value)}>
        {!selected && <option value="" disabled>请选择原调用</option>}
        {options.map(item => <option key={item.key} value={item.key}>{item.label}</option>)}
      </select>
    </label>
    <button type="button" className="button secondary" onClick={() => {
      if (!expanded && selected) setSelection(selected.key);
      setExpanded(value => !value);
    }}>
      {expanded ? '收起生成过程' : '查看生成过程'}
    </button>
    {expanded && (readable && selected ? <Observation key={selected.key} controller={controller}
      checkId={selected.checkId} attemptId={selected.attemptId} />
      : <p role="status">原调用的连接或读取资格已变化，生成内容已清除。可选择其他原调用。</p>)}
  </Card>;
}

function Observation({ controller, checkId, attemptId }: {
  controller: ModelsController; checkId: string; attemptId: string;
}) {
  const current = useRef(controller);
  current.current = controller;
  const history = useRef(empty());
  const [value, setValue] = useState<ModelEvents>();
  const [text, setText] = useState('');
  const [tools, setTools] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const { principalId, serviceInstance, organizationId } = controller.scope;
  useEffect(() => {
    if (!controller.connected) return;
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const verify = async () => {
      current.current.assertCurrent();
      const session = await api.session(abort.signal);
      abort.signal.throwIfAborted();
      try { assertSession({ principalId, serviceInstance, organizationId }, session); }
      catch { throw mismatch(); }
      current.current.assertCurrent();
    };
    const poll = async () => {
      setPending(true);
      try {
        await verify();
        const result = await modelsApi.events(organizationId, checkId, attemptId, history.current.cursor, abort.signal);
        await verify();
        if (!result || result.protocol !== 'core.model-events.v1' || result.source !== 'persisted_modeld_events' ||
            result.organization_id !== organizationId || result.check_id !== checkId || result.attempt_id !== attemptId ||
            result.access?.principal_id !== principalId || result.access?.service_instance !== serviceInstance) throw mismatch();
        history.current = append(history.current, result);
        const events = [...history.current.events.values()];
        setText(events.filter(e => e.type === 'text_delta').map(e => e.text).join('').slice(0, 262144));
        setTools(events.filter(e => e.type === 'tool_call_complete').map(e => e.name));
        setValue({ ...result, truncated: history.current.truncated });
        setError('');
        if (!history.current.truncated && (result.has_more || activeStates.has(result.state)))
          timer = setTimeout(() => void poll(), result.has_more ? 100 : 1000);
      } catch (failure) {
        if (abort.signal.aborted) return;
        if (failure instanceof ApiError && ([401, 403].includes(failure.status ?? 0) || failure.code === 'incompatible_state')) {
          history.current = empty(); setText(''); setTools([]); setValue(undefined);
          setError('权限或原请求身份已变化，生成内容已清除。');
        } else setError('生成观测已断开，以下保留最近记录。可稍后查询同一原请求。');
      } finally { if (!abort.signal.aborted) setPending(false); }
    };
    void poll();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [principalId, serviceInstance, organizationId, checkId, attemptId, refresh, controller.connected]);
  return <section aria-label="原调用生成观测">
    <p className="form-note">原调用：{attemptId}</p>
    {error && <p role="alert">{error}</p>}
    {!controller.connected && <p role="status">生成观测已断开，恢复连接后仅查询原记录。</p>}
    {pending && !value && <p role="status">正在读取原生成记录…</p>}
    {text && <pre className="au-text">{text}</pre>}
    {!!tools.length && <p>模型提出工具调用：{tools.join('、')}。实际读取以原验证记录为准。</p>}
    {value && !text && !tools.length && <p>尚无可显示的已保存文本；这不表示远端没有执行。</p>}
    {value && <p className="form-note">已读取事件序号 {value.cursor}。
      {activeStates.has(value.state) ? '原调用仍在进行，部分输出尚非完成结果。' : '原调用已停止或结束；完整结果以验证记录为准。'}
      {!value.events_complete && '已保存观测可能不完整。'}
      {value.truncated && '内容过长，当前显示已截断，自动观测已停止。'}</p>}
    <button type="button" className="button secondary" disabled={pending || !controller.connected || value?.truncated}
      onClick={() => setRefresh(value => value + 1)}>查询原生成记录</button>
  </section>;
}
