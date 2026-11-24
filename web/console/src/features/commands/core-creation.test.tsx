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
  await waitFor(() => expect(screen.getByRole('button', { name: /创建组织/ })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: /创建组织/ }));
  fireEvent.change(screen.getByLabelText('组织目的'), { target: { value: 'Keep the original goal' } });
  fireEvent.change(screen.getByLabelText('成功依据'), { target: { value: '交付可核验的结果' } });
  fireEvent.change(screen.getByLabelText('约束'), { target: { value: '仅授权内本地保存' } });
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
  localStorage.clear();
  window.history.replaceState(null, '', '/organizations');
  vi.spyOn(api, 'session').mockResolvedValue(session);
  vi.spyOn(api, 'authStatus').mockResolvedValue({ configured: true, authenticated: true, can_setup: false, account: 'owner' });
  vi.spyOn(api, 'receipt').mockRejectedValue(new Error('pending'));
});

describe('core creation through the workspace', () => {
  it('confirms purpose, success evidence and constraints as readable text in the existing five-field protocol', async () => {
    const post = vi.spyOn(api, 'command').mockImplementation(async request => ({ receipt: {
      ...request, actor: 'account:owner', created_at: 'controlled', status: 'rejected', message: '受控拒绝',
    } }));
    mountCore();
    fireEvent.click(await screen.findByRole('button', { name: '创建组织' }));
    await waitFor(() => expect(screen.getByLabelText('组织目的')).toBeEnabled());
    fireEvent.change(screen.getByLabelText('组织目的'), { target: { value: '  整理授权资料  ' } });
    fireEvent.change(screen.getByLabelText('成功依据'), { target: { value: '交付有来源的研究结果' } });
    fireEvent.change(screen.getByLabelText('约束'), { target: { value: '仅本地保存，不对外发布' } });
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    const preview = document.getElementById('operation-preview')!;
    expect(preview.querySelector('pre')).toBeNull();
    expect(preview).toHaveTextContent('当前登录账户');
    expect(preview).toHaveTextContent('仅本地保存，不对外发布');
    expect(preview).toHaveTextContent('尚未启用');
    expect(post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '确认提交' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const request = post.mock.calls[0][0];
    expect(Object.keys(request).sort()).toEqual(['base_version', 'data', 'id', 'kind', 'organization_id']);
    expect(request.kind).toBe('create_v1');
    expect(Object.keys(request.data).sort()).toEqual(['board_name', 'charter', 'goal', 'name', 'resources']);
    expect(request.data.goal).toBe('目的：\n整理授权资料\n\n成功依据：\n交付有来源的研究结果\n\n约束：\n仅本地保存，不对外发布');
    expect(request.data).not.toHaveProperty('principal_id');
  });

  it('rejects the aggregate goal limit before preview without truncating editable input', async () => {
    const post = vi.spyOn(api, 'command');
    mountCore();
    fireEvent.click(await screen.findByRole('button', { name: '创建组织' }));
    const purpose = await screen.findByLabelText('组织目的');
    fireEvent.change(purpose, { target: { value: '目'.repeat(99990) } });
    fireEvent.change(screen.getByLabelText('成功依据'), { target: { value: '完整结果' } });
    fireEvent.change(screen.getByLabelText('约束'), { target: { value: '授权内' } });
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(await screen.findByText(/合计不能超过100000/)).toBeVisible();
    expect(purpose).toHaveValue('目'.repeat(99990));
    expect(purpose).toHaveAttribute('aria-describedby', 'operation-error');
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it('retains a terminal V1 rejection and editable inputs until an explicit new preview', async () => {
    const post = vi.spyOn(api, 'command').mockImplementation(async request => ({ receipt: {
      ...request, actor: 'account:owner', created_at: 'controlled', status: 'rejected', message: '创建被拒绝',
    } }));
    mountCore();
    await fillAndSubmit();
    await screen.findByRole('heading', { name: '创建被拒绝' });
    expect(screen.getByLabelText('组织目的')).toBeVisible();
    expect(screen.getByLabelText('组织目的')).toBeEnabled();
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(sessionStorage.getItem('union-pending')).not.toContain(post.mock.calls[0][0].id);
    fireEvent.change(screen.getByLabelText('组织目的'), { target: { value: '修正目的' } });
    expect(post).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    fireEvent.click(screen.getByRole('button', { name: '确认提交' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1][0].id).not.toBe(post.mock.calls[0][0].id);
  });

  it('preserves the exact supported goal boundary without truncation or premature POST', async () => {
    const post = vi.spyOn(api, 'command');
    mountCore();
    fireEvent.click(await screen.findByRole('button', { name: '创建组织' }));
    fireEvent.change(await screen.findByLabelText('组织目的'), { target: { value: '目'.repeat(99980) } });
    fireEvent.change(screen.getByLabelText('成功依据'), { target: { value: '好' } });
    fireEvent.change(screen.getByLabelText('约束'), { target: { value: '内' } });
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(screen.getByRole('button', { name: '确认提交' })).toBeEnabled();
    expect(document.querySelector('#operation-preview .creation-preview-text')?.textContent).toHaveLength(100000);
    expect(post).not.toHaveBeenCalled();
  });

  it.each([
    {},
    { ...defaultCharter, allowed_operations: null },
    { ...defaultCharter, allowed_tools: 'produce_artifact' },
    { ...defaultCharter, reserved_matters: { goal: true } },
  ])('retains editable advanced rules after shape rejection instead of crashing: %j', async rules => {
    const post = vi.spyOn(api, 'command');
    mountCore();
    fireEvent.click(await screen.findByRole('button', { name: '创建组织' }));
    fireEvent.change(await screen.findByLabelText('组织目的'), { target: { value: '保留私有目的' } });
    fireEvent.change(screen.getByLabelText('成功依据'), { target: { value: '可核验' } });
    fireEvent.change(screen.getByLabelText('约束'), { target: { value: '授权内' } });
    fireEvent.click(screen.getByText('受支持的规则字段'));
    const field = screen.getByLabelText('组织操作、工具、保留事项与修章入口');
    fireEvent.change(field, { target: { value: JSON.stringify(rules) } });
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(await screen.findByText(/章程规则格式不正确/)).toBeVisible();
    expect(field).toHaveValue(JSON.stringify(rules));
    expect(screen.getByLabelText('组织目的')).toHaveValue('保留私有目的');
    expect(post).not.toHaveBeenCalled();
    expect(screen.queryByText('工作台暂时无法显示')).not.toBeInTheDocument();
  });
  it('keeps prepared organizations on the new entry without legacy creation controls', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, organizations: [{ id: prepared.au.id, name: prepared.au.name, profile: 'core_v1' }] });
    vi.spyOn(api, 'coreAU').mockResolvedValue(prepared);
    const submit = vi.spyOn(api, 'command');
    window.history.replaceState(null, '', '/au/org-prepared');
    mountCore();
    expect(await screen.findByRole('heading', { name: prepared.au.name })).toBeVisible();
    expect(screen.queryByRole('button', { name: /旧版兼容/ })).not.toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
  });

  it('resolves an unscoped model link to the organization list without promising configuration', async () => {
    window.history.replaceState(null, '', '/models');
    mountCore();
    await waitFor(() => expect(screen.getByRole('button', { name: '创建组织' })).toBeEnabled());
    expect(window.location.pathname).toBe('/organizations');
    expect(screen.queryByText('创建公司并继续配置')).not.toBeInTheDocument();
    expect(screen.getByText(/保存准备记录不会调用模型/)).toBeVisible();
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
    expect(await screen.findByText('Keep the original goal')).toBeVisible();
    expect(window.location.pathname).toBe('/au/org-prepared');
    expect(screen.getByText('尚未启用')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: '账号与登录' }));
    expect(screen.getByLabelText('当前核心身份标识')).toHaveValue(principal);
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
    expect(screen.getByLabelText('组织目的')).toHaveValue('Keep the original goal');
    expect(screen.getByLabelText('组织目的')).toBeEnabled();
    expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
    expect(JSON.parse(sessionStorage.getItem('union-pending') || '[]')).toEqual([]);
  });

  it('refuses ordinary creation on an older service without silently sending legacy create', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, core_protocol: undefined });
    const submit = vi.spyOn(api, 'command');
    mountCore();
    await waitFor(() => expect(screen.getByRole('button', { name: /创建组织/ })).toHaveAttribute('title', expect.stringContaining('版本不兼容')));
    expect(screen.getByRole('button', { name: /创建组织/ })).toBeDisabled();
    expect(submit).not.toHaveBeenCalled();
  });

  it('submits ordinary creation as create_v1 with exactly the five supported fields', async () => {
    const submit = vi.spyOn(api, 'command').mockImplementation(() => new Promise(() => {}));
    mountCore();
    await waitFor(() => expect(screen.getByRole('button', { name: /创建组织/ })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: /创建组织/ }));
    fireEvent.change(screen.getByLabelText(/组织目的/), { target: { value: 'Keep the original goal' } });
    fireEvent.change(screen.getByLabelText('成功依据'), { target: { value: '交付可核验的结果' } });
    fireEvent.change(screen.getByLabelText('约束'), { target: { value: '仅授权内本地保存' } });
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
