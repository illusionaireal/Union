import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../app/App';
import { api } from '../../api/client';
import { WorkspaceProvider, useWorkspace } from '../../app/workspace';
import { CommandButton, CommandProvider } from './CommandProvider';
import type { Receipt, Session } from '../../api/types';

const principal = '327e9c0f-0734-49ef-a2b8-7e4a3b6583bd';
const session: Session = {
  role: 'board', service_instance: 'boundary-test', session_scope: 'session-a',
  principal_id: principal, core_protocol: 'core.au.v1', organizations: [], executors: ['fixture'],
};
const auth = { configured: true, authenticated: true, can_setup: false, account: 'owner' };

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  HTMLDialogElement.prototype.close = function () { this.open = false; };
  sessionStorage.clear();
  window.history.replaceState(null, '', '/overview');
  vi.spyOn(api, 'session').mockResolvedValue(session);
  vi.spyOn(api, 'authStatus').mockResolvedValue(auth);
  vi.spyOn(api, 'receipt').mockRejectedValue(new Error('回执存储暂不可读'));
});

function mountApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);
  return client;
}

async function preview() {
  await waitFor(() => expect(screen.getByRole('button', { name: /^创建 AU$/ })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: /^创建 AU$/ }));
  fireEvent.change(screen.getByLabelText('AU目标'), { target: { value: 'Retain this private goal' } });
  fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
  return screen.findByRole('button', { name: '确认提交' });
}

describe('core creation identity and receipt boundaries', () => {
  it.each(['id', 'kind'] as const)('rejects a POST receipt with the wrong %s and retains the original V1 request', async field => {
    const submit = vi.spyOn(api, 'command').mockImplementation(async request => ({ receipt: {
      ...request, organization_id: 'org-wrong', actor: 'controlled', created_at: 'controlled',
      status: 'succeeded', message: 'Unrelated success',
      ...(field === 'kind' ? { kind: 'create' as const } : { id: 'other-request' }),
    } }));
    mountApp();
    const button = await preview();
    await act(async () => fireEvent.click(button));
    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toContainEqual({
      id: submit.mock.calls[0][0].id, organization_id: null, kind: 'create_v1',
    });
    expect(screen.queryByText('Unrelated success')).not.toBeInTheDocument();
    expect(await screen.findByText(/回执与原请求不匹配/)).toBeVisible();
  });

  it('keeps an unsubmitted creation draft and focus through a same-principal session renewal', async () => {
    const submit = vi.spyOn(api, 'command');
    const client = mountApp();
    await preview();
    screen.getByLabelText('AU目标').focus();
    const resolveStatuses: Array<(value: typeof auth) => void> = [];
    vi.mocked(api.authStatus).mockImplementation(() => new Promise(resolve => resolveStatuses.push(resolve)));
    vi.mocked(api.session).mockResolvedValue({ ...session, session_scope: 'renewed-session' });
    await act(async () => client.invalidateQueries({ queryKey: ['workspace'] }));
    await waitFor(() => expect(api.session).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText('AU目标')).toHaveValue('Retain this private goal');
    expect(screen.getByLabelText('AU目标')).toHaveFocus();
    await act(async () => resolveStatuses.forEach(resolve => resolve(auth)));
    expect(screen.getByLabelText('AU目标')).toHaveValue('Retain this private goal');
    expect(submit).not.toHaveBeenCalled();
  });

  it('checks the current principal again before sending a prepared draft', async () => {
    const submit = vi.spyOn(api, 'command').mockImplementation(() => new Promise(() => {}));
    function Probe() {
      const workspace = useWorkspace();
      return <><p data-testid="principal">{workspace.session?.principal_id}</p>
        <CommandButton kind="create_v1">创建 AU</CommandButton>
        <button onClick={() => void workspace.refresh()}>刷新身份</button></>;
    }
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    render(<QueryClientProvider client={client}><BrowserRouter><WorkspaceProvider><CommandProvider><Probe /></CommandProvider></WorkspaceProvider></BrowserRouter></QueryClientProvider>);
    await preview();
    const changed = { ...session, principal_id: '00181221-7722-46ad-87e1-2b8a8f7aa9b4', session_scope: 'session-b' };
    vi.mocked(api.session).mockResolvedValue(changed);
    await act(async () => fireEvent.click(screen.getByRole('button', { name: '刷新身份' })));
    await waitFor(() => expect(screen.getByTestId('principal')).toHaveTextContent(changed.principal_id));
    await act(async () => fireEvent.click(screen.getByRole('button', { name: '确认提交' })));
    expect(submit).not.toHaveBeenCalled();
  });

  it('refuses to bind a draft to a different principal even before the workspace poll notices the change', async () => {
    const submit = vi.spyOn(api, 'command').mockImplementation(() => new Promise(() => {}));
    mountApp();
    const button = await preview();
    vi.mocked(api.session).mockResolvedValue({
      ...session, principal_id: '00181221-7722-46ad-87e1-2b8a8f7aa9b4', session_scope: 'changed-session',
    });
    await act(async () => fireEvent.click(button));
    expect(submit).not.toHaveBeenCalled();
    expect(await screen.findByText(/身份.*变化/)).toBeVisible();
  });

  it.each([false, true])('adopts a delayed creation result only for its original principal (changed=%s)', async changed => {
    let finish!: (value: { receipt: Receipt }) => void;
    const submit = vi.spyOn(api, 'command').mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const client = mountApp();
    const button = await preview();
    await act(async () => fireEvent.click(button));
    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    vi.mocked(api.session).mockResolvedValue({
      ...session, session_scope: 'renewed-session',
      principal_id: changed ? '00181221-7722-46ad-87e1-2b8a8f7aa9b4' : principal,
    });
    await act(async () => client.invalidateQueries({ queryKey: ['workspace'] }));
    if (changed) await waitFor(() => expect(screen.getByRole('button', { name: /^创建 AU$/ })).toBeEnabled());
    const request = submit.mock.calls[0][0];
    await act(async () => finish({ receipt: {
      id: request.id, kind: 'create_v1', base_version: null, organization_id: 'org-owned-by-a',
      actor: 'controlled', created_at: 'controlled', status: 'succeeded', message: 'Original account result',
    } }));
    if (changed) {
      expect(window.location.search).not.toContain('org-owned-by-a');
      expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toContainEqual({
        id: request.id, kind: 'create_v1', organization_id: null,
      });
      expect(screen.queryByText('Original account result')).not.toBeInTheDocument();
    } else {
      await waitFor(() => expect(window.location.search).toContain('org-owned-by-a'));
      expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toEqual([]);
    }
  });

  it('shows a lookup failure beside an unknown receipt while retaining its original ID', async () => {
    const submit = vi.spyOn(api, 'command').mockImplementation(async request => ({ receipt: {
      ...request, organization_id: 'org-allocated', actor: 'controlled', created_at: 'controlled',
      status: 'unknown', message: '创建记录待核对',
    } }));
    mountApp();
    const button = await preview();
    await act(async () => fireEvent.click(button));
    await screen.findByText('创建记录待核对');
    fireEvent.click(screen.getByRole('button', { name: '查询此请求回执' }));
    expect(await screen.findByText(/回执存储暂不可读/)).toBeVisible();
    expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toContainEqual({
      id: submit.mock.calls[0][0].id, organization_id: null, kind: 'create_v1',
    });
  });

  it('does not create an AU when the user cancels while the identity preflight is still pending', async () => {
    const submit = vi.spyOn(api, 'command');
    mountApp();
    const button = await preview();
    let finish!: (value: Session) => void;
    vi.mocked(api.session).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    await act(async () => fireEvent.click(button));
    await waitFor(() => expect(finish).toBeTypeOf('function'));
    const fieldsLocked = screen.getByLabelText('AU目标').matches(':disabled');
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(screen.queryByLabelText('AU目标')).not.toBeInTheDocument();
    await act(async () => finish(session));
    expect(submit).not.toHaveBeenCalled();
    expect(fieldsLocked).toBe(true);
    expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toEqual([]);
  });
});
