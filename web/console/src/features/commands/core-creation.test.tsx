import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../app/App';
import { api, ApiError } from '../../api/client';
import { defaultCharter } from './model';
import type { CoreAURead, Session } from '../../api/types';

const principal = '327e9c0f-0734-49ef-a2b8-7e4a3b6583bd';
const session: Session = {
  role: 'board', service_instance: 'core-test', session_scope: 'owner-session',
  principal_id: principal, core_protocol: 'core.au.v1', organizations: [], executors: ['fixture'],
};

const prepared: CoreAURead = {
  protocol: 'core.au.v1',
  au: { id: 'org-prepared', name: 'Prepared test AU', goal: 'Keep the original goal',
    version: 0, charter_version: 1, policy_version: 0, runtime_profile: 'core_v1', schema_version: 1,
    autonomy_state: 'inactive', resource_state: 'planned', board_name: 'Initial governor',
    governance_root: { creator_principal_id: principal, governor_principal_id: principal },
    charter: defaultCharter, resources: { max_calls: 8, timeout_seconds: 180 } },
  capabilities: { read: true, autonomous_business: false, charter_enforcement: 'not_activated' },
};

async function fillAndSubmit() {
  await waitFor(() => expect(screen.getByRole('button', { name: /创建我的 AI 公司|创建 AU/ })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: /创建我的 AI 公司|创建 AU/ }));
  fireEvent.change(screen.getByLabelText('AU目标'), { target: { value: 'Keep the original goal' } });
  fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
  fireEvent.click(await screen.findByRole('button', { name: '确认提交' }));
}

export function mountCore() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);
}

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  HTMLDialogElement.prototype.close = function () { this.open = false; };
  sessionStorage.clear();
  window.history.replaceState(null, '', '/overview');
  vi.spyOn(api, 'session').mockResolvedValue(session);
  vi.spyOn(api, 'authStatus').mockResolvedValue({ configured: true, authenticated: true, can_setup: false, account: 'owner' });
  vi.spyOn(api, 'receipt').mockRejectedValue(new Error('pending'));
});

describe('core creation through the workspace', () => {
  it('keeps explicit legacy company creation reachable after reopening a prepared AU', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, organizations: [{ id: prepared.au.id, name: prepared.au.name, profile: 'core_v1' }] });
    vi.spyOn(api, 'coreAU').mockResolvedValue(prepared);
    const submit = vi.spyOn(api, 'command').mockImplementation(() => new Promise(() => {}));
    mountCore();
    await screen.findByRole('region', { name: 'AU准备记录' });
    fireEvent.click(screen.getByRole('button', { name: '旧版兼容试验（含小说）' }));
    fireEvent.change(screen.getByLabelText('创建类型'), { target: { value: 'novel' } });
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    fireEvent.click(await screen.findByRole('button', { name: '确认提交' }));
    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    expect(submit.mock.calls[0][0].kind).toBe('create');
    expect(submit.mock.calls[0][0].data.company).toBeDefined();
  });

  it('explains the prepared boundary at the empty model entry instead of promising immediate configuration', async () => {
    window.history.replaceState(null, '', '/models');
    mountCore();
    await waitFor(() => expect(screen.getByRole('button', { name: '创建 AU 准备记录' })).toBeEnabled());
    expect(screen.queryByText('创建公司并继续配置')).not.toBeInTheDocument();
    expect(screen.getByText(/新 AU 当前只保存资源计划，模型配置和调用尚未启用/)).toBeVisible();
  });

  it('opens the saved prepared AU through V1 and shows bound governance without legacy snapshot calls', async () => {
    const snapshot = vi.spyOn(api, 'snapshot').mockRejectedValue(new Error('must not use legacy snapshot'));
    const fetcher = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify(prepared), { status: 200 }));
    vi.spyOn(api, 'command').mockImplementation(async (request) => {
      vi.mocked(api.session).mockResolvedValue({ ...session, organizations: [{ id: prepared.au.id, name: prepared.au.name, profile: 'core_v1' }] });
      return { receipt: { ...request, organization_id: prepared.au.id, actor: 'account:owner', created_at: 'controlled', status: 'succeeded', message: 'AU已准备' } };
    });
    mountCore();
    await fillAndSubmit();
    fireEvent.click(await screen.findByRole('button', { name: '完成，返回工作台' }));
    expect(await screen.findByRole('region', { name: 'AU准备记录' })).toHaveTextContent('Keep the original goal');
    expect(screen.getByText('业务自治尚未启用')).toBeVisible();
    expect(screen.getByText(principal)).toBeVisible();
    expect(snapshot).not.toHaveBeenCalled();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/aus/org-prepared', expect.any(Object));
    expect(screen.queryByRole('button', { name: '启动／继续' })).not.toBeInTheDocument();
  });

  it('retains an unknown V1 request for lookup after the result dialog closes', async () => {
    vi.spyOn(api, 'command').mockImplementation(async (request) => ({ receipt: {
      ...request, organization_id: 'org-allocated', actor: 'account:owner', created_at: 'controlled',
      status: 'unknown', message: '创建中断，保留原请求',
    } }));
    mountCore();
    await fillAndSubmit();
    await screen.findByText('创建中断，保留原请求');
    expect(sessionStorage.getItem('union-pending')).toContain('create_v1');
    fireEvent.click(screen.getByRole('button', { name: '关闭' }));
    expect(screen.getByRole('button', { name: '查询原请求' })).toBeVisible();
  });

  it('keeps input editable after a pre-allocation V1 validation rejection', async () => {
    vi.spyOn(api, 'command').mockRejectedValue(new ApiError('不支持的章程字段', 400, 'invalid_request'));
    mountCore();
    await fillAndSubmit();
    await screen.findByText(/不支持的章程字段/);
    expect(screen.getByLabelText('AU目标')).toHaveValue('Keep the original goal');
    expect(screen.getByLabelText('AU目标')).toBeEnabled();
    expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
    expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toEqual([]);
  });

  it('refuses ordinary creation on an older service without silently sending legacy create', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, core_protocol: undefined });
    const submit = vi.spyOn(api, 'command');
    mountCore();
    await waitFor(() => expect(screen.getByRole('button', { name: /创建我的 AI 公司|创建 AU/ })).toHaveAttribute('title', expect.stringContaining('版本不兼容')));
    expect(screen.getByRole('button', { name: /创建我的 AI 公司|创建 AU/ })).toBeDisabled();
    expect(submit).not.toHaveBeenCalled();
  });

  it('submits ordinary creation as create_v1 with exactly the five supported fields', async () => {
    const submit = vi.spyOn(api, 'command').mockImplementation(() => new Promise(() => {}));
    mountCore();
    await waitFor(() => expect(screen.getByRole('button', { name: /创建我的 AI 公司|创建 AU/ })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: /创建我的 AI 公司|创建 AU/ }));
    fireEvent.change(screen.getByLabelText(/公司目标|AU目标/), { target: { value: 'Keep the original goal' } });
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    fireEvent.click(await screen.findByRole('button', { name: '确认提交' }));
    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    const request = submit.mock.calls[0][0];
    expect(request.kind).toBe('create_v1');
    expect(request.organization_id).toBeNull();
    expect(request.base_version).toBeNull();
    expect(Object.keys(request.data).sort()).toEqual(['board_name', 'charter', 'goal', 'name', 'resources']);
    expect(sessionStorage.getItem('union-pending')).toContain('create_v1');
    expect(sessionStorage.getItem('union-pending')).not.toContain('Keep the original goal');
  });
});
