import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { checkedRun, fixture, json, mount, savedConnection } from './test-fixtures';
import { otherPrincipal } from '../governance/test-fixtures';

let state: ReturnType<typeof fixture>;
let calls: URL[];
let respond: (url: URL) => Promise<Response>;
const page = (extra: Record<string, unknown> = {}) => ({
  protocol: 'core.model-events.v1', organization_id: 'core-au', check_id: 'check-one',
  attempt_id: 'attempt-one', access: state.read.access, version: state.read.version,
  source: 'persisted_modeld_events', state: 'completed', cursor: 3, last_seq: 3,
  has_more: false, events_complete: true, truncated: false,
  events: [{ seq: 1, type: 'text_delta', text: '部分正文' },
    { seq: 3, type: 'tool_call_complete', name: 'read_document' }], ...extra,
});
beforeEach(() => {
  state = fixture();
  state.read.connections = [savedConnection()];
  const check = checkedRun('check-one', 'running');
  check.attempts = [check.attempts[0]];
  state.read.checks = [check];
  calls = [];
  respond = async () => json(page());
  const original = globalThis.fetch;
  vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
    const url = new URL(String(input), 'http://localhost');
    if (url.pathname === '/api/v1/models/events') {
      calls.push(url);
      return respond(url);
    }
    return original(input, init);
  }));
});
afterEach(() => vi.unstubAllGlobals());

async function open() {
  fireEvent.click(await screen.findByRole('button', { name: '查看生成过程' }));
}
describe('V1 original-request observation', () => {
  it('renders partial text as text and original tool names without posting a command', async () => {
    respond = async () => json(page({ events: [{ seq: 1, type: 'text_delta', text: '<img src=x>部分正文' }], state: 'running' }));
    mount();
    expect(calls).toHaveLength(0);
    await open();
    expect(await screen.findByText('<img src=x>部分正文')).toBeVisible();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(calls[0].searchParams.get('after')).toBe('0');
    expect(calls[0].searchParams.get('attempt_id')).toBe('attempt-one');
    expect(state.commands).toHaveLength(0);
  });
  it('deduplicates repeat pages and retains the original cursor across a failed read', async () => {
    mount(); await open();
    expect(await screen.findByText('部分正文')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[1].searchParams.get('after')).toBe('3');
    expect(screen.getByText('部分正文')).toBeVisible();
    respond = async () => { throw new TypeError('offline'); };
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText(/生成观测已断开/)).toBeVisible();
    expect(screen.getByText('部分正文')).toBeVisible();
    respond = async () => json(page({ cursor: 4, last_seq: 4,
      events: [{ seq: 4, type: 'text_delta', text: '接续' }] }));
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText('部分正文接续')).toBeVisible();
    expect(calls.at(-1)!.searchParams.get('after')).toBe('3');
    expect(state.commands).toHaveLength(0);
  });
  it.each(['organization_id', 'attempt_id', 'check_id', 'protocol'])('clears content on mismatched %s', async (key) => {
    mount(); await open();
    await screen.findByText('部分正文');
    respond = async () => json(page({ [key]: 'wrong' }));
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText(/生成内容已清除/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
  });
  it('clears content when the stream grant is revoked despite a still readable model list', async () => {
    mount(); await open(); await screen.findByText('部分正文');
    respond = async () => json({ code: 'not_authorized', error: 'denied' }, 403);
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText(/生成内容已清除/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });
  it('ignores a delayed result after a principal switch and does not persist text', async () => {
    let finish!: (r: Response) => void;
    respond = () => new Promise(resolve => { finish = resolve; });
    const { client } = mount(); await open();
    await waitFor(() => expect(finish).toBeDefined());
    const old = page();
    state.session.principal_id = otherPrincipal;
    state.core.access.principal_id = otherPrincipal;
    state.read.access.principal_id = otherPrincipal;
    state.read.checks = [];
    await act(async () => { await client.invalidateQueries({ queryKey: ['workspace'] }); finish(json(old)); });
    await waitFor(() => expect(screen.queryByText('部分正文')).not.toBeInTheDocument());
    expect(JSON.stringify(sessionStorage)).not.toContain('部分正文');
    expect(JSON.stringify(localStorage)).not.toContain('部分正文');
    expect(state.commands).toHaveLength(0);
  });
  it('rejects a changed cookie identity even before workspace refresh', async () => {
    mount(); await open(); await screen.findByText('部分正文');
    respond = async () => { state.session.principal_id = otherPrincipal; return json(page()); };
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    await waitFor(() => expect(screen.queryByText('部分正文')).not.toBeInTheDocument());
    expect(state.commands).toHaveLength(0);
  });
  it('rejects conflicting same-sequence text and discards its old output', async () => {
    mount(); await open(); await screen.findByText('部分正文');
    respond = async () => json(page({ events: [{ seq: 1, type: 'text_delta', text: 'conflicting' }] }));
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText(/生成内容已清除/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
    expect(screen.queryByText('conflicting')).not.toBeInTheDocument();
  });
  it.each([null, { events: [null] }])('clears malformed observation responses', async malformed => {
    mount(); await open(); await screen.findByText('部分正文');
    respond = async () => json(malformed === null ? null : page(malformed));
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText(/生成内容已清除/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
  });
  it.each(['principal_id', 'service_instance'])('clears a response for another %s', async key => {
    mount(); await open(); await screen.findByText('部分正文');
    respond = async () => json(page({ access: { ...state.read.access, [key]: 'other' } }));
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    expect(await screen.findByText(/生成内容已清除/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
  });
  it('keeps the selected original attempt when the check creates its next attempt', async () => {
    const { client } = mount(); await open(); await screen.findByText('部分正文');
    state.read.checks[0].attempts.push({ ...state.read.checks[0].attempts[0], id: 'attempt-two', stage: 1 });
    await act(async () => { await client.invalidateQueries({ queryKey: ['core-models'] }); });
    await screen.findByRole('option', { name: '项目说明.txt · 第 2 次' });
    expect(screen.getByRole('combobox', { name: '查看哪次原调用' })).toHaveValue('check-one:attempt-one');
    expect(calls.every(url => url.searchParams.get('attempt_id') === 'attempt-one')).toBe(true);
  });
  it.each(['disabled', 'revised', 'removed'])('clears stopped output when its connection is %s in the current projection', async change => {
    const { client } = mount(); await open(); await screen.findByText('部分正文');
    if (change === 'disabled') state.read.connections[0].enabled = false;
    else if (change === 'revised') state.read.connections[0].revision += 1;
    else state.read.connections = [];
    await act(async () => { await client.invalidateQueries({ queryKey: ['core-models'] }); });
    await waitFor(() => expect(screen.queryByText('部分正文')).not.toBeInTheDocument());
    expect(await screen.findByText(/原调用的连接或读取资格已变化/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
    expect(calls).toHaveLength(1);
    expect(state.commands).toHaveLength(0);
  });
  it('discards a delayed observation after current connection access is removed', async () => {
    const { client } = mount(); await open(); await screen.findByText('部分正文');
    let finish!: (r: Response) => void;
    respond = () => new Promise(resolve => { finish = resolve; });
    fireEvent.click(screen.getByRole('button', { name: '查询原生成记录' }));
    await waitFor(() => expect(finish).toBeDefined());
    state.read.connections[0].enabled = false;
    await act(async () => { await client.invalidateQueries({ queryKey: ['core-models'] }); });
    await waitFor(() => expect(screen.queryByText('部分正文')).not.toBeInTheDocument());
    await screen.findByText(/原调用的连接或读取资格已变化/);
    await act(async () => { finish(json(page({ cursor: 4, last_seq: 4,
      events: [{ seq: 4, type: 'text_delta', text: '迟到正文' }] }))); });
    expect(screen.queryByText(/部分正文|迟到正文/)).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });
  it('does not replace a removed selected request with a different available attempt', async () => {
    const { client } = mount(); await open(); await screen.findByText('部分正文');
    state.read.checks[0].attempts = [{ ...state.read.checks[0].attempts[0], id: 'attempt-two', stage: 1 }];
    await act(async () => { await client.invalidateQueries({ queryKey: ['core-models'] }); });
    await screen.findByRole('option', { name: '项目说明.txt · 第 2 次' });
    await waitFor(() => expect(screen.queryByText('部分正文')).not.toBeInTheDocument());
    expect(await screen.findByText(/原调用的连接或读取资格已变化/)).toBeVisible();
    expect(screen.queryByText('部分正文')).not.toBeInTheDocument();
    expect(calls.every(url => url.searchParams.get('attempt_id') === 'attempt-one')).toBe(true);
    expect(state.commands).toHaveLength(0);
  });
  it('keeps stopped output for unchanged authority when unrelated connection metadata changes', async () => {
    const { client } = mount(); await open(); await screen.findByText('部分正文');
    state.read.connections[0].last_check = { check_id: 'check-one', revision: 1, profile: 'openai_compatible', at: 1 };
    state.read.connections.push({ ...savedConnection('other-connection'), enabled: false });
    state.read.version += 1;
    await act(async () => { await client.invalidateQueries({ queryKey: ['core-models'] }); });
    await screen.findByText('另一模型');
    expect(screen.getByText('部分正文')).toBeVisible();
    expect(calls).toHaveLength(1);
    expect(state.commands).toHaveLength(0);
  });
});
