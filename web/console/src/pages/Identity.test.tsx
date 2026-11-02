import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import { IdentityBoundary } from './Identity';

const workspace = vi.hoisted(() => ({ session: undefined as undefined | { service_instance: string; session_scope: string }, loading: false }));
vi.mock('../app/workspace', () => ({ useWorkspace: () => workspace }));

const unconfigured = { configured: false, authenticated: false, can_setup: true, account: null };
const configured = { configured: true, authenticated: false, can_setup: false, account: null };
const signedIn = { configured: true, authenticated: true, can_setup: false, account: 'owner' };

function mount(children: ReactNode = <p>工作台内容</p>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const tree = (node: ReactNode) => (
    <QueryClientProvider client={client}>
      <IdentityBoundary>{node}</IdentityBoundary>
    </QueryClientProvider>
  );
  return { client, view: render(tree(children)), tree };
}

function submitForm(button: HTMLElement) {
  const form = button.closest('form');
  if (!form) throw new Error('表单未找到');
  fireEvent.submit(form);
}

const reload = vi.fn();

beforeEach(() => {
  workspace.session = undefined;
  workspace.loading = false;
  vi.stubGlobal('location', { ...window.location, reload });
});

afterEach(() => {
  vi.unstubAllGlobals();
  reload.mockReset();
});

describe('identity boundary', () => {
  it('shows the setup form on an unconfigured deployment and keeps its fields', async () => {
    vi.spyOn(api, 'authStatus').mockResolvedValue(unconfigured);
    mount();
    expect(await screen.findByRole('heading', { name: '建立管理员账号' })).toBeVisible();
    expect(screen.getByLabelText('账号')).toBeVisible();
    expect(screen.getByLabelText('密码')).toHaveAttribute('minlength', '12');
    expect(screen.getByRole('button', { name: '建立管理员账号' })).toBeEnabled();
  });

  it('keeps what the user typed while background refreshes run', async () => {
    const status = vi.spyOn(api, 'authStatus').mockResolvedValue(unconfigured);
    const { client, view, tree } = mount();
    const password = await screen.findByLabelText('密码');
    fireEvent.change(screen.getByLabelText('账号'), { target: { value: 'owner' } });
    fireEvent.change(password, { target: { value: 'correct-horse-password' } });
    const before = status.mock.calls.length;
    workspace.loading = true;
    view.rerender(tree(<p>工作台内容</p>));
    await act(async () => {
      await client.refetchQueries({ queryKey: ['identity'] });
    });
    expect(status.mock.calls.length).toBeGreaterThan(before);
    expect(screen.queryByText('正在连接工作台…')).not.toBeInTheDocument();
    expect(screen.getByLabelText('账号')).toHaveValue('owner');
    expect(screen.getByLabelText('密码')).toHaveValue('correct-horse-password');
  });

  it('submits the first claim once, shows the recovery code and does not reload', async () => {
    vi.spyOn(api, 'authStatus').mockResolvedValue(unconfigured);
    const auth = vi.spyOn(api, 'auth').mockResolvedValue({ recovery_code: 'RECOVERY-ONCE' });
    mount();
    fireEvent.change(await screen.findByLabelText('账号'), { target: { value: 'Owner' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'correct-horse-password' } });
    submitForm(screen.getByRole('button', { name: '建立管理员账号' }));
    await waitFor(() =>
      expect(auth).toHaveBeenCalledWith('setup', { username: 'Owner', password: 'correct-horse-password', remember: false }),
    );
    expect(await screen.findByText('请保存恢复码')).toBeVisible();
    expect(screen.getByLabelText('账号恢复码')).toHaveValue('RECOVERY-ONCE');
    expect(auth).toHaveBeenCalledTimes(1);
    expect(reload).not.toHaveBeenCalled();
  });

  it('sends the remember option and shows server errors without leaving the form', async () => {
    vi.spyOn(api, 'authStatus').mockResolvedValue(configured);
    const auth = vi.spyOn(api, 'auth').mockRejectedValue(new Error('账号或密码不正确'));
    mount();
    fireEvent.change(await screen.findByLabelText('账号'), { target: { value: 'owner' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong-password' } });
    fireEvent.click(screen.getByLabelText('记住此设备，最长30天'));
    submitForm(screen.getByRole('button', { name: '登录 UNION' }));
    await waitFor(() =>
      expect(auth).toHaveBeenCalledWith('login', { username: 'owner', password: 'wrong-password', remember: true }),
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('账号或密码不正确');
    expect(screen.getByLabelText('密码')).toHaveValue('wrong-password');
    expect(reload).not.toHaveBeenCalled();
  });

  it('disables the submit button while a request is in flight', async () => {
    vi.spyOn(api, 'authStatus').mockResolvedValue(configured);
    let release: (value: { recovery_code?: string | null }) => void = () => {};
    vi.spyOn(api, 'auth').mockImplementation(() => new Promise((resolve) => { release = resolve; }));
    mount();
    fireEvent.change(await screen.findByLabelText('账号'), { target: { value: 'owner' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong-password' } });
    submitForm(screen.getByRole('button', { name: '登录 UNION' }));
    const busy = await screen.findByRole('button', { name: '正在处理…' });
    expect(busy).toBeDisabled();
    await act(async () => { release({}); });
  });

  it('shows login once configured and switches to the recovery form', async () => {
    vi.spyOn(api, 'authStatus').mockResolvedValue(configured);
    mount();
    expect(await screen.findByRole('heading', { name: '登录 UNION' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: '忘记密码，使用恢复码' }));
    expect(screen.getByRole('heading', { name: '恢复账号' })).toBeVisible();
    expect(screen.getByLabelText('恢复码')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: '返回登录' }));
    expect(screen.getByRole('heading', { name: '登录 UNION' })).toBeVisible();
  });

  it('renders the workspace only after authentication', async () => {
    vi.spyOn(api, 'authStatus').mockResolvedValue(signedIn);
    mount();
    expect(await screen.findByText('工作台内容')).toBeVisible();
    expect(screen.queryByRole('heading', { name: '登录 UNION' })).not.toBeInTheDocument();
  });

  it('reports a failed first read and offers a retry', async () => {
    vi.spyOn(api, 'authStatus').mockRejectedValue(new Error('服务暂不可用'));
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法连接工作台');
    expect(screen.getByRole('button', { name: '重试' })).toBeVisible();
  });
});
