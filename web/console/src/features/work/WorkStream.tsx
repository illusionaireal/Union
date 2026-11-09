import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import type { CoreWorkEvents, CoreWorkItem, CoreWorkStep, WorkEventConnection } from '../../api/types';
import './work-stream.css';

type Scope = { principalId: string; serviceInstance: string; organizationId: string; workId: string };
const connectionKeys = ['id', 'revision', 'profile', 'model', 'grant_ref', 'grant_revision', 'max_output_tokens', 'task_ms'] as const;
const connectionKey = (connection?: WorkEventConnection) => JSON.stringify(connectionKeys.map(k => connection?.[k] ?? null));
const identity = (step: CoreWorkStep) => JSON.stringify([
  step.step_ref, step.attempt_id, step.command_id, step.model_request_id, connectionKey(step.connection),
]);
const incompatible = () => new ApiError('原工作输出身份或事件不一致', 409, 'incompatible_state');

export function WorkStream({ item, scope }: { item: CoreWorkItem; scope: Scope }) {
  const [selection, setSelection] = useState('');
  const [expanded, setExpanded] = useState(false);
  const options = item.steps.filter(step => step.command_id && step.model_request_id);
  const selected = selection ? options.find(step => identity(step) === selection) : options.at(-1);
  if (!options.length && !expanded) return null;
  return <section className="work-stream" aria-label="工作原请求输出">
    <label>查看哪次工作调用
      <select aria-label="查看哪次工作调用" value={selected ? identity(selected) : ''} onChange={e => setSelection(e.target.value)}>
        {!selected && <option value="" disabled>原调用已不可用，请明确选择</option>}
        {options.map(step => <option key={identity(step)} value={identity(step)}>
          {step.step_ref} · {step.model_request_id}
        </option>)}
      </select>
    </label>
    <button type="button" onClick={() => {
      if (!expanded && selected) setSelection(identity(selected));
      setExpanded(value => !value);
    }}>{expanded ? '收起工作输出' : '查看工作输出'}</button>
    {expanded && (selected?.can_observe && selected.connection
      ? <Observation key={identity(selected)} scope={scope} step={selected} />
      : <p role="status">原调用或读取资格已变化，输出已清除。请核对原工作记录。</p>)}
  </section>;
}

function Observation({ scope, step }: { scope: Scope; step: CoreWorkStep }) {
  const [text, setText] = useState('');
  const [tools, setTools] = useState<string[]>([]);
  const [note, setNote] = useState('');
  const [value, setValue] = useState<CoreWorkEvents>();
  const [pending, setPending] = useState(false);
  const [reload, setReload] = useState(0);
  const history = useRef(new Map<number, CoreWorkEvents['events'][number]>());
  const cursor = useRef(0);
  const limited = useRef(false);
  const key = JSON.stringify([scope, identity(step)]);
  const currentKey = useRef(key); currentKey.current = key;
  useEffect(() => {
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const current = () => { abort.signal.throwIfAborted(); if (currentKey.current !== key) throw incompatible(); };
    const verify = async () => {
      const session = await api.session(abort.signal);
      current();
      if (session.core_protocol !== 'core.au.v1' || session.principal_id !== scope.principalId ||
          session.service_instance !== scope.serviceInstance) throw incompatible();
    };
    const clear = () => {
      history.current.clear(); cursor.current = 0; limited.current = false;
      setText(''); setTools([]); setValue(undefined);
    };
    const poll = async () => {
      setPending(true);
      try {
        await verify();
        const checkingOnly = limited.current;
        const result = checkingOnly
          ? await api.coreWorkEvents(scope.organizationId, scope.workId, step.step_ref, cursor.current, abort.signal, true)
          : await api.coreWorkEvents(scope.organizationId, scope.workId, step.step_ref, cursor.current, abort.signal);
        await verify(); current();
        if (!result || result.protocol !== 'core.work-events.v1' || result.source !== 'persisted_modeld_events' ||
            result.organization_id !== scope.organizationId || result.work_id !== scope.workId ||
            result.step_ref !== step.step_ref || result.attempt_id !== step.attempt_id ||
            result.command_id !== step.command_id || result.model_request_id !== step.model_request_id ||
            result.access?.principal_id !== scope.principalId || result.access?.service_instance !== scope.serviceInstance ||
            connectionKey(result.connection) !== connectionKey(step.connection) ||
            !Number.isSafeInteger(result.version) || result.version < 0 ||
            !['prepared', 'dispatching', 'queued', 'connecting', 'streaming', 'running', 'completed', 'failed', 'interrupted', 'cancel_requested'].includes(result.state) ||
            typeof result.has_more !== 'boolean' || typeof result.truncated !== 'boolean' || typeof result.events_complete !== 'boolean' ||
            !Number.isSafeInteger(result.cursor) || result.cursor < cursor.current ||
            !Number.isSafeInteger(result.last_seq) || result.last_seq < result.cursor ||
            !Array.isArray(result.events) || result.events.length > 500 ||
            result.authorization_only !== checkingOnly || (checkingOnly && result.events.length !== 0) ||
            (result.has_more && result.cursor <= cursor.current)) throw incompatible();
        const next = new Map(history.current);
        let last = 0;
        for (const event of result.events) {
          if (!event || !Number.isSafeInteger(event.seq) || event.seq <= last || event.seq > result.cursor ||
              !(event.type === 'text_delta' && typeof event.text === 'string' ||
                event.type === 'tool_call_complete' && event.name === 'read_document')) throw incompatible();
          last = event.seq;
          const prior = next.get(event.seq);
          if (prior ? JSON.stringify(prior) !== JSON.stringify(event) : event.seq <= cursor.current) throw incompatible();
          next.set(event.seq, event);
        }
        let remaining = 262144;
        const bounded = new Map<number, CoreWorkEvents['events'][number]>();
        limited.current ||= result.truncated;
        for (const [seq, event] of next) {
          if (bounded.size >= 20000) { limited.current = true; break; }
          if (event.type === 'text_delta') {
            const content = event.text.slice(0, remaining);
            limited.current ||= content.length !== event.text.length;
            remaining -= content.length;
            bounded.set(seq, { ...event, text: content });
          } else bounded.set(seq, event);
        }
        history.current = bounded; cursor.current = result.cursor;
        setText([...bounded.values()].filter(e => e.type === 'text_delta').map(e => e.text).join(''));
        setTools([...new Set([...bounded.values()].filter(e => e.type === 'tool_call_complete').map(e => e.name))]);
        setValue({ ...result, truncated: limited.current }); setNote('');
        // Terminal text retains permission checks too; no completion can prolong old authority.
        timer = setTimeout(() => void poll(), limited.current ? 3000 : result.has_more ? 100 :
          ['completed', 'failed', 'interrupted'].includes(result.state) ? 3000 : 1000);
      } catch (failure) {
        if (abort.signal.aborted) return;
        if (failure instanceof ApiError && ([401, 403].includes(failure.status ?? 0) || failure.code === 'incompatible_state')) {
          clear(); setNote('权限或原请求身份已变化，工作输出已清除。');
        } else {
          setNote('观测已断开，保留最近记录；请稍后查询同一原请求。');
          if (limited.current) timer = setTimeout(() => void poll(), 3000);
        }
      } finally { if (!abort.signal.aborted) setPending(false); }
    };
    void poll();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [key, reload]);
  return <section aria-label="原工作输出观测">
    <p>原请求：{step.model_request_id} · {step.attempt_id} · {step.step_ref}</p>
    <p>这是已保存的部分输出；完成、取消与用量以原工作记录为准。</p>
    {note && <p role="alert">{note}</p>}
    {text && <pre className="au-text">{text}</pre>}
    {!!tools.length && <p>模型提出工具调用：{tools.join('、')}。实际执行以原工作回执为准。</p>}
    {value && !text && <p>尚无可显示的原请求文本，这不表示远端未执行。</p>}
    {value && <p>已读取事件序号 {value.cursor}。{!value.events_complete && '原事件观测可能不完整。'}
      {value.truncated && '显示已截断，正文加载已停止；仍定期核对读取权限。'}</p>}
    <button type="button" disabled={pending} onClick={() => setReload(n => n + 1)}>
      {value?.truncated ? '核对原工作输出权限' : '查询原工作输出'}
    </button>
  </section>;
}
