import {useEffect, useId, useRef, useState} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import {api, errorText} from '../../api/client';
import type {CoreWorkInput, CoreWorkItem} from '../../api/types';
import {checkResultSession, readResultWork} from './result-reading';
import {accessLost, useWorkCommand, type WorkScope} from './useWorkCommand';
import './work-inputs.css';

const labels = {received: '已收存', attached: '已附入原请求', observed: '模型已观察', consumed: '已正式采用'};
function validText(content: string) {
  if (!content.trim() || content.includes('\0') || new TextEncoder().encode(content).length > 65536) return false;
  for (let i = 0; i < content.length; i++) {
    const code = content.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = content.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
    } else if (code >= 0xdc00 && code <= 0xdfff) return false;
  }
  return true;
}
const provenance = (work: CoreWorkItem) => JSON.stringify([work.responsible, work.definition, work.mandate]);

function InputBody({scope, workId, input, canRead, onAccessLost}: {
  scope: WorkScope; workId: string; input: CoreWorkInput; canRead: boolean; onAccessLost: () => void;
}) {
  const [body, setBody] = useState<string>(), [note, setNote] = useState(''), [busy, setBusy] = useState(false);
  const bodyId = useId();
  const request = useRef<AbortController | undefined>(undefined);
  const client = useQueryClient();
  useEffect(() => () => request.current?.abort(), []);
  async function open() {
    if (!canRead || busy) return;
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    const signal = controller.signal;
    setNote(''); setBusy(true); setBody(undefined);
    try {
      const read = await readResultWork(scope, signal);
      const current = read.works.find(work => work.id === workId)?.inputs?.find(item => item.id === input.id);
      if (read.access.can_read_inputs !== true || !current || current.sha256 !== input.sha256 ||
        JSON.stringify(current.source_scope) !== JSON.stringify(input.source_scope))
        throw new Error('输入读取资格或来源已变化，请刷新核对');
      const value = await api.coreWorkInput(scope.organizationId, workId, input.id, signal);
      signal.throwIfAborted();
      const r = value.input;
      if (value.protocol !== 'core.work-input.v1' || value.organization_id !== scope.organizationId ||
        value.work_id !== workId || !r || r.id !== input.id || r.seq !== input.seq ||
        r.sha256 !== input.sha256 || r.bytes !== input.bytes || r.source_kind !== 'requirement' ||
        r.actor_principal_id !== input.actor_principal_id || r.received_at !== input.received_at ||
        r.reason !== input.reason || JSON.stringify(r.source_scope) !== JSON.stringify(input.source_scope) ||
        typeof value.content !== 'string' || !validText(value.content))
        throw new Error('输入身份、来源或正文校验失败，请保留原记录核对');
      const bytes = new TextEncoder().encode(value.content);
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), x => x.toString(16).padStart(2, '0')).join('');
      signal.throwIfAborted();
      if (digest !== input.sha256 || bytes.length !== input.bytes)
        throw new Error('输入身份、来源或正文校验失败，请保留原记录核对');
      const latest = await readResultWork(scope, signal);
      if (latest.access.can_read_inputs !== true || !latest.works.find(w => w.id === workId)?.inputs?.some(i =>
        i.id === input.id && i.sha256 === input.sha256 && JSON.stringify(i.source_scope) === JSON.stringify(input.source_scope)))
        throw new Error('输入读取资格或来源已变化，请刷新核对');
      checkResultSession(await api.session(signal), scope); signal.throwIfAborted(); setBody(value.content);
    } catch (error) {
      if (signal.aborted) return;
      if (accessLost(error)) {
        // A body-only refusal does not prove loss of the entire Work projection.
        try {await readResultWork(scope, signal);} catch {if (!signal.aborted) onAccessLost(); return;}
      }
      if (!signal.aborted) {setNote(errorText(error)); await client.invalidateQueries({queryKey: ['core-work', scope.organizationId]});}
    } finally {if (!signal.aborted) setBusy(false);}
  }
  return <>
    <button className="button secondary" type="button" disabled={!canRead} aria-disabled={busy}
      aria-expanded={body !== undefined} aria-controls={bodyId}
      onClick={() => { if (body === undefined) void open(); else setBody(undefined); }}>
      {busy ? '正在核对输入正文…' : body === undefined ? '阅读输入正文' : '收起输入正文'}
    </button>
    <div id={bodyId} hidden={body === undefined}>{body !== undefined && <pre aria-label="已收存输入正文">{body}</pre>}</div>
    {note && <p role="status">{note}</p>}
  </>;
}

export function WorkInputs({scope, work, version, canAppend, canRead, onAccessLost}: {
  scope: WorkScope; work: CoreWorkItem; version: number; canAppend: boolean; canRead: boolean; onAccessLost: () => void;
}) {
  const [content, setContent] = useState(''), [reason, setReason] = useState(''), [note, setNote] = useState('');
  const feedbackId = useId();
  const command = useWorkCommand(scope, onAccessLost, {kind: 'append_work_input', workId: work.id});
  const draftScope = JSON.stringify([provenance(work), canAppend, canRead]);
  const [previousDraftScope, setPreviousDraftScope] = useState(draftScope);
  if (draftScope !== previousDraftScope) {
    setPreviousDraftScope(draftScope);
    setContent(''); setReason(''); setNote('');
  }
  useEffect(() => {
    if (command.reference?.resolved && command.reference.outcome === 'succeeded') {setContent(''); setReason('');}
  }, [command.reference]);
  async function send() {
    setNote('');
    if (!validText(content)) {setNote('输入须为有效 UTF-8 文本，不含 NUL 或孤立代理字符，最多 65536 字节；正文未截断。'); return;}
    if (!reason.trim() || reason.length > 10000) {setNote('请填写补充依据，最多 10000 字符。'); return;}
    await command.send({work_id: work.id, input_id: 'input-' + crypto.randomUUID().replaceAll('-', ''), content, reason}, version, async read => {
      const current = read.works.find(w => w.id === work.id);
      if (!current || provenance(current) !== provenance(work) || !['pending', 'running', 'waiting'].includes(current.status))
        throw new Error('原工作状态、责任或来源已变化，请刷新核对');
    });
  }
  const inputs = work.inputs ?? [];
  const pending = work.input_summary?.pending ?? inputs.filter(i => i.status !== 'consumed').length;
  return <section className="work-inputs" aria-label="原工作补充输入">
    <h3>补充原工作要求</h3>
    <p>输入留在这项工作中，不增加预算或授予权限。已结束工作不会因此重新开始。</p>
    <p>正式采用表示进入执行上下文，不表示要求已经实现。仍待采用 {pending} 项，由 {work.responsible.name} 继续承担。</p>
    {!canAppend && <p>当前不能收存补充输入；原工作和原请求仍可核对。</p>}
    <form onSubmit={e => {e.preventDefault(); void send();}}>
      <label>补充输入正文<textarea aria-label="补充输入正文" aria-describedby={note ? feedbackId : undefined} value={content} onChange={e => setContent(e.target.value)}
        disabled={!canAppend || command.sending || !!command.reference} required /></label>
      <p>最多 65536 UTF-8 字节，当前 {new TextEncoder().encode(content).length} 字节；每项工作最多 100 项、累计 8 MiB。正文只保留在当前页面内存。</p>
      <label>补充依据<textarea aria-label="补充依据" aria-describedby={note ? feedbackId : undefined} value={reason} onChange={e => setReason(e.target.value)}
        disabled={!canAppend || command.sending || !!command.reference} maxLength={10000} required /></label>
      <button className="button primary" type="submit" disabled={!canAppend || command.sending || !!command.reference || command.blocked || !content.trim() || !reason.trim()}>收存补充输入</button>
    </form>
    {command.reference && <>
      {!command.reference.resolved && <p>结果待核对。请查询原请求，避免重复提交。</p>}
      {command.reference.refusedBeforeAcceptance && <p>原提交已明确被拒绝，没有收存新输入。</p>}
      <button className="button secondary" type="button" disabled={command.checking || command.sending} onClick={() => void command.lookup()}>查询输入原请求</button>
      {command.reference.resolved && canAppend && <button className="button secondary" type="button" disabled={command.checking || command.sending}
        onClick={() => {command.another(); setNote('');}}>继续补充输入</button>}
      <details><summary>输入请求记录</summary><p>{command.reference.id} · {command.reference.inputId} · SHA-256 {command.reference.sha256}</p></details>
    </>}
    {(note || command.note) && <p id={feedbackId} role="status">{note || command.note}</p>}
    {!inputs.length && <p>尚无已收存的补充输入。</p>}
    <ol className="work-input-list">{inputs.map(input => <li key={input.id}>
      <p><strong>{labels[input.status]}</strong> · 输入 {input.seq} · {input.received_at}</p>
      <p>补充依据：{input.reason}</p>
      <p>来源成员 {input.source_scope.member_id} · 提交主体 {input.actor_principal_id}</p>
      <InputBody key={JSON.stringify([scope, work.id, input.id, input.sha256, input.source_scope, canRead])}
        scope={scope} workId={work.id} input={input} canRead={canRead} onAccessLost={onAccessLost} />
      <details><summary>输入来源与采用依据</summary>
        <p>绑定 {input.source_scope.binding_id} · 版本 {input.source_scope.binding_version}；定义 {input.source_scope.definition_id} · 版本 {input.source_scope.definition_version}</p>
        <p>Mandate {input.source_scope.mandate_id} · 版本 {input.source_scope.mandate_version}；章程版本 {input.source_scope.charter_version} · 政策版本 {input.source_scope.policy_version}</p>
        <p>原输入 {input.id} · {input.bytes} 字节 · SHA-256 {input.sha256}</p>
        {input.attachments.map((attachment, i) => <div key={i}>
          <p>原步骤 {attachment.step_ref} · 原模型请求 {attachment.model_request_id} · 请求摘要 {attachment.request_sha256}</p>
          <p>附入时间 {attachment.attached_at} · 观察时间 {attachment.observed_at ?? '尚无'} · 正式采用时间 {attachment.consumed_at ?? '尚无'}</p>
          <p>执行所有者 {attachment.execution_owner.instance} · epoch {attachment.execution_owner.epoch}</p>
        </div>)}
        <p>按序采用前缀 {work.input_cursor ?? 0}；后到输入或仍待采用的要求未由此证明已回应。</p>
      </details>
    </li>)}</ol>
  </section>;
}
