import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api/client';
import { otherPrincipal } from '../governance/test-fixtures';
import {
  accepted,
  checkedRun,
  confirm,
  fillConnection,
  fixture,
  json,
  mount,
  savedConnection,
} from './test-fixtures';

let state: ReturnType<typeof fixture>;
beforeEach(() => {
  state = fixture();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('model identity, scope and input lifetime', () => {
  it('keeps draft fields and keyboard focus through refresh and same-principal renewal', async () => {
    const { client } = mount();
    await fillConnection();
    const input = screen.getByLabelText('模型标识');
    input.focus();
    state.session.session_scope = 'renewed-session';
    state.read.version += 1;
    state.core.au.version = state.read.version;
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['workspace'] });
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    expect(screen.getByLabelText('模型标识')).toBe(input);
    expect(input).toHaveFocus();
    expect(input).toHaveValue('text-model');
    expect(screen.getByLabelText('API Key')).toHaveValue('test-key-not-a-real-secret');
  });

  it('retains draft while offline and never queues a command for reconnection', async () => {
    mount();
    await fillConnection();
    fireEvent(window, new Event('offline'));
    expect(screen.getByLabelText('模型标识')).toHaveValue('text-model');
    expect(screen.getByRole('button', { name: '预览影响' })).toBeDisabled();
    fireEvent(window, new Event('online'));
    await waitFor(() => expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled());
    expect(state.commands).toHaveLength(0);
  });

  it('clears a draft after permissions change and does not reopen it when access returns', async () => {
    const { client } = mount();
    await fillConnection();
    state.read.access.can_configure = false;
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    state.read.access.can_configure = true;
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    expect(await screen.findByRole('button', { name: '添加模型连接' })).toBeEnabled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it('erases credentials immediately when preflight learns that read access was denied', async () => {
    mount();
    await fillConnection();
    state.state.onRead = async () =>
      json({ code: 'not_authorized', error: '模型读取权已撤回' }, 403);
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    await waitFor(() => expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument());
    expect(state.commands).toHaveLength(0);
  });

  it('rejects a response for a different AU, then can recover on an explicit matching refresh', async () => {
    state.state.onRead = async () => json({ ...state.read, organization_id: 'unrelated-au' });
    mount();
    expect(await screen.findByText(/模型记录与当前身份、服务或 AU 不一致/)).toBeVisible();
    expect(screen.queryByRole('button', { name: '添加模型连接' })).not.toBeInTheDocument();
    state.state.onRead = undefined;
    fireEvent.click(screen.getByRole('button', { name: '刷新模型记录' }));
    expect(await screen.findByRole('button', { name: '添加模型连接' })).toBeEnabled();
    expect(state.commands).toHaveLength(0);
  });

  it('ignores an earlier successful read arriving after a newer permission denial', async () => {
    state.read.checks.push(checkedRun());
    const { client } = mount();
    await fillConnection();
    const previous = structuredClone(state.read);
    let finishOld!: (response: Response) => void;
    state.state.onRead = async () =>
      new Promise((resolve) => {
        finishOld = resolve;
      });
    const refresh = client.invalidateQueries({ queryKey: ['core-models'] });
    await waitFor(() => expect(finishOld).toBeDefined());
    state.state.onRead = async () => json({ code: 'not_authorized', error: '读取权已经撤回' }, 403);
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    await waitFor(() => expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument());
    await act(async () => {
      finishOld(json(previous));
      await refresh;
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
    expect(
      screen.queryByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '添加模型连接' })).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it('rejects a changed cookie identity before any command is posted', async () => {
    mount();
    await fillConnection();
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    const button = await screen.findByRole('button', { name: '确认提交' });
    state.session.principal_id = otherPrincipal;
    fireEvent.click(button);
    await waitFor(() => expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument());
    expect(state.commands).toHaveLength(0);
    expect(sessionStorage.getItem('union-model-requests') ?? '').not.toContain(
      'test-key-not-a-real-secret',
    );
  });

  it('does not expose a late command result to a different principal', async () => {
    let finish!: (response: Response) => void;
    state.state.onCommand = async () =>
      new Promise((resolve) => {
        finish = resolve;
      });
    const { client } = mount();
    await fillConnection();
    await confirm();
    await waitFor(() => expect(finish).toBeDefined());
    const original = state.commands[0];
    state.session.principal_id = otherPrincipal;
    state.core.access.principal_id = otherPrincipal;
    state.read.access.principal_id = otherPrincipal;
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['workspace'] });
    });
    expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument();
    await act(async () => {
      finish(json({ receipt: { ...accepted(original), message: '原主体的私有回执' } }));
    });
    expect(screen.queryByText('原主体的私有回执')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: `查询原请求 ${original.id}` }),
    ).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(1);
  });

  it('clears draft and previous results on a new service instance', async () => {
    state.read.checks.push(checkedRun());
    const { client } = mount();
    await fillConnection();
    state.session.service_instance = 'next-service';
    state.core.access.service_instance = 'next-service';
    state.read.access.service_instance = 'next-service';
    state.read.checks = [];
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['workspace'] });
    });
    expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument();
    expect(
      screen.queryByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it('clears form on AU switch and never displays an old AU response as the new one', async () => {
    state.session.organizations.push({ id: 'core-other', name: '另一个 AU', profile: 'core_v1' });
    vi.mocked(api.coreAU).mockImplementation(async (id) => ({
      ...structuredClone(state.core),
      au: { ...structuredClone(state.core.au), id },
    }));
    mount();
    await fillConnection();
    fireEvent.change(screen.getByRole('combobox', { name: '当前组织' }), {
      target: { value: 'core-other' },
    });
    await waitFor(() => expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument());
    expect(await screen.findByText(/模型记录与当前身份、服务或 AU 不一致/)).toBeVisible();
    expect(state.commands).toHaveLength(0);
  });

  it('renders model output as plain text and does not claim a stale revision is verified', async () => {
    const connection = savedConnection();
    connection.last_check = {
      check_id: 'old-check',
      revision: 0,
      profile: connection.profile,
      at: 1800000000,
    };
    state.read.connections.push(connection);
    const check = checkedRun();
    check.output = '<img src=x onerror=alert(1)> 文本内容';
    state.read.checks.push(check);
    mount();
    expect(await screen.findByText('<img src=x onerror=alert(1)> 文本内容')).toBeVisible();
    expect(screen.getByText('尚未验证此版本')).toBeVisible();
    expect(document.querySelector('img[src=x]')).not.toBeInTheDocument();
  });
});
