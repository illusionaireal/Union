import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../api/client';
import type { CoreAURead, Session } from '../api/types';
import { defaultCharter } from '../features/commands/model';
import App from './App';
import { WorkspaceProvider, useWorkspace } from './workspace';

const session: Session = {
  role: 'core', principal_id: 'principal-one', service_instance: 'service-one',
  session_scope: 'login-one', core_protocol: 'core.au.v1', executors: [],
  organizations: [
    { id: 'first', name: '资料研究组织', profile: 'core_v1' },
    { id: 'second', name: '写作组织', profile: 'core_v1' },
    { id: 'legacy', name: '旧版试验', profile: 'legacy_v0' },
  ],
};
const prepared = (id: string, principal = 'principal-one'): CoreAURead => ({
  protocol: 'core.au.v1',
  au: {
    id, name: id === 'first' ? '资料研究组织' : '写作组织', goal: '持续整理有来源的资料',
    board_name: '创建人', version: 0, charter_version: 1, policy_version: 0,
    schema_version: 1, runtime_profile: 'core_v1', autonomy_state: 'inactive', resource_state: 'planned',
    governance_root: { creator_principal_id: principal, governor_principal_id: principal },
    charter: defaultCharter, resources: { max_calls: 8, timeout_seconds: 180 },
  },
  capabilities: { read: true, autonomous_business: false, charter_enforcement: 'not_activated' },
});

function ScopeProbe() {
  const state = useWorkspace();
  const navigate = useNavigate();
  return <>
    <output data-testid="principal">{state.session?.principal_id ?? 'none'}</output>
    <output data-testid="scope">{state.core?.au.id ?? 'none'}</output>
    <output data-testid="name">{state.core?.au.name ?? 'none'}</output>
    <output data-testid="problem">{state.error}</output>
    <button onClick={() => state.selectOrg('second')}>打开第二个组织</button>
    <button onClick={() => state.selectOrg('first')}>打开第一个组织</button>
    <button onClick={() => navigate('/overview?organization=first')}>打开旧概况链接</button>
    <button onClick={() => void state.refresh()}>重新读取</button>
    <button disabled={!state.connected}>需要最新权限的动作</button>
  </>;
}
function mount(full = false, gcTime = 0) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime } } });
  return render(<QueryClientProvider client={client}><BrowserRouter>
    {full ? <App /> : <WorkspaceProvider><ScopeProbe /></WorkspaceProvider>}
  </BrowserRouter></QueryClientProvider>);
}
beforeEach(() => {
  window.history.replaceState(null, '', '/organizations');
  localStorage.clear(); sessionStorage.clear();
  vi.spyOn(api, 'session').mockResolvedValue(session);
  vi.spyOn(api, 'authStatus').mockResolvedValue({
    configured: true, authenticated: true, can_setup: false, account: '参与者',
  });
  vi.spyOn(api, 'coreAU').mockImplementation(async id => prepared(id));
  vi.spyOn(api, 'snapshot').mockRejectedValue(new Error('新入口不能读取旧快照'));
  vi.spyOn(api, 'receipt').mockRejectedValue(new Error('未授权的自动回执查询'));
});

describe('V1 organization entry', () => {
  it.each(['create', 'create_v1'] as const)('preserves unscoped historical %s references without automatic lookup', async kind => {
    const original = [{ id: 'historical-request', kind, organization_id: null }];
    sessionStorage.setItem('union-pending', JSON.stringify(original));
    mount(true);
    await screen.findByRole('link', { name: /资料研究组织/ });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 50)); });
    expect(api.receipt).not.toHaveBeenCalled();
    expect(JSON.parse(sessionStorage.getItem('union-pending')!)).toEqual(original);
    expect(screen.getByText(kind === 'create' ? /旧版操作引用已保留/ : /历史创建引用尚未绑定账户/)).toBeVisible();
  });

  it('does not poll a creation owned by another principal or silently open its AU', async () => {
    sessionStorage.setItem('union-pending', JSON.stringify([{ id: 'other-creation', kind: 'create_v1', organization_id: null,
      principal_id: 'other', service_instance: session.service_instance, service_origin: window.location.origin }]));
    mount(true);
    await screen.findByRole('link', { name: /资料研究组织/ });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 50)); });
    expect(api.receipt).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe('/organizations');
  });

  it('offers explicit recovery for a partial historical creation without guessing its missing scope', async () => {
    sessionStorage.setItem('union-pending', JSON.stringify([{ id: 'partial-creation', kind: 'create_v1',
      organization_id: null, principal_id: session.principal_id, service_instance: 'before-restart' }]));
    mount(true);
    await screen.findByRole('link', { name: /资料研究组织/ });
    expect(api.receipt).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '查询原请求' })).toBeVisible();
  });

  it.each([{ principal_id: 'different-principal' }, { service_origin: 'https://different-service.invalid' }])(
    'withholds partial historical recovery when a known scope field mismatches: %j', async scope => {
      sessionStorage.setItem('union-pending', JSON.stringify([{ id: 'partial-other', kind: 'create_v1',
        organization_id: null, ...scope }]));
      mount(true);
      await screen.findByRole('link', { name: /资料研究组织/ });
      expect(api.receipt).not.toHaveBeenCalled();
      expect(screen.queryByRole('button', { name: '查询原请求' })).not.toBeInTheDocument();
    },
  );

  it('queries an owned original creation after restart without overriding explicit navigation', async () => {
    window.history.replaceState(null, '', '/au/second');
    sessionStorage.setItem('union-pending', JSON.stringify([{ id: 'original-creation', kind: 'create_v1', organization_id: null,
      principal_id: session.principal_id, service_instance: 'before-restart', service_origin: window.location.origin }]));
    vi.mocked(api.receipt).mockResolvedValue({ receipt: { id: 'original-creation', kind: 'create_v1', organization_id: 'first',
      base_version: null, status: 'succeeded', actor: 'controlled', created_at: '', message: '原创建已核对' } });
    mount(true);
    await waitFor(() => expect(api.receipt).toHaveBeenCalledWith('original-creation', null, 'create_v1'));
    await screen.findByText('原创建已核对');
    expect(window.location.pathname).toBe('/au/second');
    expect(api.coreAU).not.toHaveBeenCalledWith('first', expect.any(AbortSignal));
    expect(screen.getByRole('link', { name: '打开已创建的组织' })).toHaveAttribute('href', '/au/first');
  });
  it.each(['/', '/organizations'])('does not select the first AU at %s', async path => {
    window.history.replaceState(null, '', path);
    mount();
    await waitFor(() => expect(screen.getByTestId('principal')).toHaveTextContent('principal-one'));
    expect(api.coreAU).not.toHaveBeenCalled();
    expect(api.snapshot).not.toHaveBeenCalled();
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
  });

  it('lists authorized V1 organizations without a legacy default or legacy creation', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, organizations: [session.organizations[2], ...session.organizations.slice(0, 2)] });
    mount(true);
    expect(await screen.findByRole('heading', { name: '我的组织', level: 1 })).toBeVisible();
    expect(screen.getByRole('link', { name: /资料研究组织/ })).toHaveAttribute('href', '/au/first');
    expect(screen.getByRole('link', { name: /写作组织/ })).toHaveAttribute('href', '/au/second');
    expect(screen.queryByRole('link', { name: /旧版试验/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /旧版兼容/ })).not.toBeInTheDocument();
    expect(api.coreAU).not.toHaveBeenCalled();
    expect(api.snapshot).not.toHaveBeenCalled();
  });

  it('uses the explicit path AU instead of a conflicting legacy query', async () => {
    window.history.replaceState(null, '', '/au/second/work?organization=first');
    mount();
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('second'));
    expect(api.coreAU).toHaveBeenCalledWith('second', expect.any(AbortSignal));
    expect(api.coreAU).not.toHaveBeenCalledWith('first', expect.any(AbortSignal));
    expect(api.snapshot).not.toHaveBeenCalled();
  });

  it.each(['/au/missing', '/au/legacy', '/au/first/unknown', '/au/first%2Fsecond', '/au/%ZZ', '/au/first/work/invalid%255Fid'])('does not fall back from rejected target %s', async path => {
    window.history.replaceState(null, '', path);
    mount();
    await waitFor(() => expect(screen.getByTestId('principal')).toHaveTextContent('principal-one'));
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
    expect(api.coreAU).not.toHaveBeenCalled();
    expect(api.snapshot).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '需要最新权限的动作' })).toBeDisabled();
  });

  it('resolves a valid old link to the new scoped page, without mounting the old shell', async () => {
    window.history.replaceState(null, '', '/tasks?organization=second');
    mount(true);
    expect(await screen.findByRole('heading', { name: '工作', level: 1 })).toBeVisible();
    await waitFor(() => expect(window.location.pathname).toBe('/au/second/work'));
    expect(screen.queryByRole('button', { name: '启动／继续' })).not.toBeInTheDocument();
    expect(api.snapshot).not.toHaveBeenCalled();
  });

  it('explains the optional platform boundary when resolving an old gateways link', async () => {
    window.history.replaceState(null, '', '/gateways');
    mount(true);
    expect(await screen.findByText(/平台网关管理由可选平台提供/)).toBeVisible();
    expect(window.location.pathname).toBe('/organizations');
    expect(api.coreAU).not.toHaveBeenCalled();
  });

  it('marks results as the active navigation for a scoped Work result link', async () => {
    window.history.replaceState(null, '', '/au/second/work/work-1/results/result-1');
    mount(true);
    await screen.findByRole('heading', { name: '成果', level: 1 });
    expect(screen.getByRole('link', { name: '成果' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: '工作' })).not.toHaveAttribute('aria-current');
  });

  it.each([403, 404])('returns to the list when a recent AU is no longer readable (%s)', async status => {
    window.history.replaceState(null, '', '/');
    localStorage.setItem('union-recent-au-v1', JSON.stringify({ version: 1, principal_id: session.principal_id,
      service_instance: session.service_instance, au_id: 'second' }));
    vi.mocked(api.coreAU).mockRejectedValue(new ApiError('最近组织当前不可读', status));
    mount(true);
    await screen.findByRole('link', { name: /资料研究组织/ });
    await waitFor(() => expect(window.location.pathname).toBe('/organizations'));
    expect(api.coreAU).not.toHaveBeenCalledWith('first', expect.any(AbortSignal));
  });

  it.each(['/organizations/', '/ORGANIZATIONS'])('rejects a router-normalized undeclared list path %s', async path => {
    window.history.replaceState(null, '', path);
    mount(true);
    expect(await screen.findByRole('heading', { name: '暂时无法打开这个入口' })).toBeVisible();
    expect(screen.queryByRole('link', { name: /资料研究组织/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '创建组织' })).not.toBeInTheDocument();
    expect(api.coreAU).not.toHaveBeenCalled();
  });

  it('reopens a verified recent AU and keeps only a navigation reference', async () => {
    window.history.replaceState(null, '', '/au/second');
    const first = mount();
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('second'));
    first.unmount();
    const saved = Object.keys(localStorage).map(key => localStorage.getItem(key)).join('');
    expect(saved).toContain('second');
    expect(saved).not.toContain('写作组织');
    expect(saved).not.toContain('持续整理');
    window.history.replaceState(null, '', '/');
    mount();
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('second'));
  });

  it('waits for a recent AU read before resolving the full authenticated home route', async () => {
    window.history.replaceState(null, '', '/');
    localStorage.setItem('union-recent-au-v1', JSON.stringify({ version: 1,
      principal_id: session.principal_id, service_instance: session.service_instance, au_id: 'second' }));
    let resolveRead!: (value: CoreAURead) => void;
    vi.mocked(api.coreAU).mockReturnValueOnce(new Promise(resolve => { resolveRead = resolve; }));
    mount(true);
    await waitFor(() => expect(api.coreAU).toHaveBeenCalledWith('second', expect.any(AbortSignal)));
    expect(window.location.pathname).toBe('/');
    expect(screen.queryByRole('heading', { name: '我的组织' })).not.toBeInTheDocument();
    await act(async () => { resolveRead(prepared('second')); });
    await screen.findByRole('heading', { name: '写作组织' });
    await waitFor(() => expect(window.location.pathname).toBe('/au/second'));
  });

  it('does not use a different principal or service recent AU', async () => {
    window.history.replaceState(null, '', '/au/second');
    const first = mount();
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('second'));
    first.unmount();
    vi.mocked(api.coreAU).mockClear();
    vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'principal-two', service_instance: 'service-two' });
    window.history.replaceState(null, '', '/');
    mount();
    await waitFor(() => expect(screen.getByTestId('principal')).toHaveTextContent('principal-two'));
    expect(api.coreAU).not.toHaveBeenCalled();
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
  });

  it('ignores a late AU result after a newer explicit navigation', async () => {
    window.history.replaceState(null, '', '/au/first');
    let resolveFirst!: (value: CoreAURead) => void;
    vi.mocked(api.coreAU).mockImplementation(id => id === 'first'
      ? new Promise(resolve => { resolveFirst = resolve; }) : Promise.resolve(prepared(id)));
    mount();
    await waitFor(() => expect(api.coreAU).toHaveBeenCalledWith('first', expect.any(AbortSignal)));
    fireEvent.click(screen.getByRole('button', { name: '打开第二个组织' }));
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('second'));
    await act(async () => { resolveFirst(prepared('first')); });
    expect(screen.getByTestId('scope')).toHaveTextContent('second');
    expect(window.location.pathname).toBe('/au/second');
  });

  it('erases a denied projection and does not resurrect it after network loss', async () => {
    window.history.replaceState(null, '', '/au/first');
    mount();
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('first'));
    vi.mocked(api.coreAU).mockRejectedValue(new ApiError('当前无权读取', 403));
    fireEvent.click(screen.getByRole('button', { name: '重新读取' }));
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('none'));
    vi.mocked(api.session).mockRejectedValue(new TypeError('连接断开'));
    fireEvent.click(screen.getByRole('button', { name: '重新读取' }));
    await waitFor(() => expect(screen.getByTestId('problem')).toHaveTextContent('连接断开'));
    expect(screen.getByTestId('name')).toHaveTextContent('none');
    expect(screen.getByRole('button', { name: '需要最新权限的动作' })).toBeDisabled();
  });

  it('clears a previously readable AU when the service protocol becomes incompatible', async () => {
    window.history.replaceState(null, '', '/au/first');
    mount();
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('first'));
    vi.mocked(api.session).mockResolvedValue({ ...session, core_protocol: undefined });
    fireEvent.click(screen.getByRole('button', { name: '重新读取' }));
    await waitFor(() => expect(screen.getByTestId('problem')).toHaveTextContent('不兼容'));
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
    expect(screen.getByRole('button', { name: '需要最新权限的动作' })).toBeDisabled();
  });

  it('does not resurrect a denied AU from a different cached route during network failure', async () => {
    window.history.replaceState(null, '', '/au/first');
    mount(false, 60000);
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('first'));
    vi.mocked(api.coreAU).mockRejectedValue(new ApiError('读取权已撤销', 403));
    fireEvent.click(screen.getByRole('button', { name: '打开旧概况链接' }));
    await waitFor(() => expect(screen.getByTestId('problem')).toHaveTextContent('读取权已撤销'));
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
    vi.mocked(api.session).mockRejectedValue(new TypeError('网络中断'));
    fireEvent.click(screen.getByRole('button', { name: '打开第一个组织' }));
    await waitFor(() => expect(screen.getByTestId('problem')).toHaveTextContent('网络中断'));
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
    expect(screen.getByTestId('name')).not.toHaveTextContent('资料研究组织');
  });

  it('does not resurrect an AU after learning an incompatible protocol on the list route', async () => {
    window.history.replaceState(null, '', '/au/first');
    mount(false, 60000);
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('first'));
    vi.mocked(api.session).mockResolvedValue({ ...session, core_protocol: undefined });
    act(() => {
      window.history.pushState(null, '', '/organizations');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    await waitFor(() => expect(screen.getByTestId('scope')).toHaveTextContent('none'));
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 50)); });
    vi.mocked(api.session).mockRejectedValue(new TypeError('网络中断'));
    fireEvent.click(screen.getByRole('button', { name: '打开第一个组织' }));
    await waitFor(() => expect(screen.getByTestId('problem')).toHaveTextContent('网络中断'));
    expect(screen.getByTestId('scope')).toHaveTextContent('none');
  });
});
