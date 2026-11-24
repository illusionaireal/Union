import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { accepted, closeResult, confirm, fill, fixture, json, mount, savedConnection } from './test-fixtures';

let state: ReturnType<typeof fixture>;
beforeEach(() => { state = fixture(); });
afterEach(() => { vi.unstubAllGlobals(); });
const preparation = () => screen.getByRole('region', { name: '资源准备进度' });
const next = (name: string) => within(preparation()).getByRole('button', { name });

describe('U119 continuous resource preparation', () => {
  it('guides save, bounded grant and independent default adoption without mandatory inference', async () => {
    mount('/au/core-au/resources');
    await screen.findByRole('region', { name: '资源准备进度' });
    fireEvent.click(next('填写模型连接'));
    fill('连接名称', '同一组织的连接'); fill('API 根地址', 'https://models.example.test/v1');
    fill('API Key', 'test-key-not-a-real-secret'); fill('模型标识', 'text-model');
    await confirm(); await closeResult();
    expect(state.commands.map(c => c.kind)).toEqual(['save_connection']);
    fireEvent.click(next('设置有限调用'));
    fill('调用总上限', '4'); fill('授权依据', '两次验证并保留两次余量');
    fireEvent.click(screen.getByLabelText('接受供应商费用可能未知'));
    await confirm(); await closeResult();
    expect(state.commands.map(c => c.kind)).toEqual(['save_connection', 'grant_model_resources']);
    fireEvent.click(next('采用所选默认连接'));
    await confirm(); await closeResult();
    expect(state.commands.map(c => c.kind)).toEqual(['save_connection', 'grant_model_resources', 'set_connection']);
    expect(within(preparation()).getByText('所选连接已采用为默认，当前版本尚未验证。')).toBeVisible();
    expect(within(preparation()).getByRole('link', { name: '返回组织概况' })).toHaveAttribute('href', '/au/core-au');
    expect(within(preparation()).getByText(/业务资料授权与正式工作仍需另行准备/)).toBeVisible();
    expect(state.read.capabilities.autonomous_business).toBe(false);
  });

  it('offers a scoped tool decision that preserves the charter and uses the original governance command', async () => {
    state.read.connections.push(savedConnection());
    state.read.resources.grant = { max_calls: 4, allow_unknown_cost: true, revision: 1, reason: 'bounded' };
    state.read.document_read_allowed = false;
    state.core.au.charter.allowed_tools = ['workspace_execute', 'workspace_execute'];
    state.core.au.charter.text = '原章程正文，不改写';
    const originalCharter = structuredClone(state.core.au.charter);
    const governanceCommands: Array<Record<string, any>> = [];
    vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      if (String(path) === '/api/v1/governance/commands') {
        const command = JSON.parse(String(init?.body)); governanceCommands.push(command);
        state.core.au.charter = command.data.charter;
        state.core.au.version += 1; state.read.version = state.core.au.version;
        state.read.document_read_allowed = true;
        return json({ receipt: accepted(command) });
      }
      return state.fetchMock(path, init);
    }));
    mount('/au/core-au/resources');
    await screen.findByRole('region', { name: '资源准备进度' });
    fireEvent.click(next('允许只读验证资料'));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).queryByRole('textbox', { name: '章程正文' })).not.toBeInTheDocument();
    expect(within(dialog).getByText(/不授予宿主文件访问或业务资料许可/)).toBeVisible();
    fill('决定依据', '仅允许本次明确选择的公开验证文本');
    fireEvent.click(within(dialog).getByRole('button', { name: '预览影响' }));
    await screen.findByText('验证资料工具：允许只读所选文本。');
    expect(governanceCommands).toHaveLength(0);
    fireEvent.click(within(dialog).getByRole('button', { name: '确认提交' }));
    await waitFor(() => expect(governanceCommands).toHaveLength(1));
    expect(governanceCommands[0]).toMatchObject({ organization_id: 'core-au', kind: 'amend_charter',
      data: { reason: '仅允许本次明确选择的公开验证文本', charter: { ...originalCharter,
        allowed_tools: [...originalCharter.allowed_tools, 'read_document'] } } });
    expect(state.commands).toHaveLength(0);
    expect(sessionStorage.getItem('union-governance-requests')).not.toContain(originalCharter.text);
  });

  it('requires a connection choice when several exist and never swaps a lost selection on refresh', async () => {
    state.read.connections.push(savedConnection(), savedConnection('connection-two'));
    const { client } = mount('/au/core-au/resources');
    const select = await screen.findByLabelText('本次准备的模型连接');
    expect(select).toHaveValue('');
    fireEvent.change(select, { target: { value: 'connection-one' } });
    expect(select).toHaveValue('connection-one');
    state.read.connections = [savedConnection('connection-two')];
    await client.invalidateQueries({ queryKey: ['core-models'] });
    expect(await screen.findByText('原选择的连接已不可用；请明确选择另一连接。')).toBeVisible();
    expect(within(preparation()).queryByRole('button', { name: '采用所选默认连接' })).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it.each([0, 1])('states plan %i cannot cover a complete check without extending it', async plan => {
    state.read.resources.plan_max_calls = plan;
    state.read.connections.push(savedConnection());
    mount('/au/core-au/resources');
    await screen.findByRole('region', { name: '资源准备进度' });
    expect(within(preparation()).getByText(/创建计划不足两次调用，当前无法完成工具往返验证/)).toBeVisible();
    expect(next('进行两次调用验证')).toBeDisabled();
    expect(state.commands).toHaveLength(0);
  });

  it('refuses a tool preview from an older charter instead of overwriting a concurrent decision', async () => {
    state.read.connections.push(savedConnection());
    state.read.resources.grant = { max_calls: 4, allow_unknown_cost: true, revision: 1, reason: 'bounded' };
    state.read.document_read_allowed = false;
    mount('/au/core-au/resources');
    await screen.findByRole('region', { name: '资源准备进度' });
    fireEvent.click(next('允许只读验证资料'));
    await screen.findByRole('dialog');
    fill('决定依据', '保留这份输入并核对变化');
    state.core.au.version += 1;
    state.core.au.charter.text = '另一项已采用修订';
    state.core.au.charter.allowed_tools.push('workspace_execute');
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(await screen.findByText(/章程已变化，请关闭后核对当前规则/)).toBeVisible();
    expect(screen.getByLabelText('决定依据')).toHaveValue('保留这份输入并核对变化');
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(state.fetchMock.mock.calls.some(([url]) => url === '/api/v1/governance/commands')).toBe(false);
  });

  it('allows default adoption directly when the user has not accepted unknown costs or a document tool', async () => {
    state.read.connections.push(savedConnection());
    state.read.document_read_allowed = false;
    state.read.resources.grant = { max_calls: 4, allow_unknown_cost: false, reason: 'no spending', revision: 1 };
    mount('/au/core-au/resources');
    await screen.findByRole('region', { name: '资源准备进度' });
    fireEvent.click(next('采用所选默认连接'));
    await confirm(); await closeResult();
    expect(state.commands.map(c => c.kind)).toEqual(['set_connection']);
    expect(state.read.document_read_allowed).toBe(false);
    expect(state.read.resources.grant.allow_unknown_cost).toBe(false);
    expect(next('进行两次调用验证')).toBeDisabled();
  });

  it('offers an explicit enable action for a stopped selected connection', async () => {
    state.read.connections.push({ ...savedConnection(), enabled: false });
    state.read.resources.grant = { max_calls: 4, allow_unknown_cost: true, reason: 'bounded', revision: 1 };
    mount('/au/core-au/resources');
    await screen.findByRole('region', { name: '资源准备进度' });
    fireEvent.click(next('启用所选连接'));
    await confirm(); await closeResult();
    expect(state.commands[0]).toMatchObject({ kind: 'set_connection', data: { connection_id: 'connection-one', enabled: true, make_default: false } });
    expect(state.read.connections[0].is_default).toBe(false);
    expect(state.read.checks).toHaveLength(0);
  });
});
