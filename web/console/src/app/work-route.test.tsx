import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import type { CoreAURead, CoreWork, Session } from '../api/types';
import { Layout } from './Layout';

const state = vi.hoisted(() => ({ workspace: {} as Record<string, unknown> }));
vi.mock('./workspace', () => ({ useWorkspace: () => state.workspace }));
vi.mock('../features/commands/CommandProvider', () => ({
  useCommands: () => ({ pending: [], inspect: vi.fn() }),
  CommandButton: () => null,
}));
vi.mock('../pages/Identity', () => ({ AccountSettings: () => null }));
vi.mock('../pages/PreparedAU', () => ({ default: () => <p>准备态原入口</p> }));
vi.mock('../features/governance/GovernanceProvider', () => ({
  GovernanceRecovery: () => null,
  GovernanceButton: () => null,
}));
vi.mock('../features/governance/ResponsibilityWorkspace', () => ({
  ResponsibilityWorkspace: () => <p>既有责任工作区</p>,
}));

const core = (principal = 'p1', organization = 'au-1', service = 'service-1') =>
  ({
    protocol: 'core.au.v1',
    au: { id: organization, name: organization, schema_version: 3, runtime_profile: 'core_v1' },
    access: { principal_id: principal, service_instance: service },
  }) as unknown as CoreAURead;
const work = (organization = 'au-1', principal = 'p1'): CoreWork => ({
  protocol: 'core.work.v1',
  organization_id: organization,
  version: 4,
  access: { principal_id: principal, can_start: true },
  capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
  works: [
    {
      id: 'work-1',
      title: '已保存的项目概览',
      goal: '依据资料形成成果',
      status: 'delivered',
      version: 1,
      max_calls: 2,
      materials_root: 'docs',
      created_at: '',
      responsible: { member_id: 'm1', name: '资料 Agent', binding_id: 'b1', duty: '整理资料' },
      definition: {
        id: 'd1',
        version: 1,
        connection_id: 'c1',
        model: 'model',
        tools: ['read_document'],
      },
      mandate: { id: 'ma1', version: 1, actions: ['read_document'], active: true },
      attempt_ids: [],
      result_ids: ['result-1'],
      attempts: [],
      steps: [],
      tool_calls: [],
      budget: { max_calls: 2, reserved: 0, used: 1 },
      materials: { reference: 'docs', available: true, documents: 1 },
      results: [
        {
          id: 'result-1',
          seq: 1,
          title: '概览正文',
          sha256: 'abcdef0123456789',
          bytes: 24,
          sources: ['step-1'],
          status: 'adopted',
          created_at: '',
          adopted_at: '',
        },
      ],
    },
  ],
});

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  const tree = () => (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/tasks?organization=au-1']}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="tasks" element={<p>旧版工作入口</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
  const view = render(tree());
  return { refresh: () => view.rerender(tree()) };
}
beforeEach(() => {
  const session = {
    role: 'core',
    principal_id: 'p1',
    service_instance: 'service-1',
    organizations: [{ id: 'au-1', name: 'au-1', profile: 'core_v1' }],
  } as Session;
  state.workspace = {
    session,
    core: core(),
    orgId: 'au-1',
    connected: true,
    selectOrg: vi.fn(),
    refresh: vi.fn(),
    loading: false,
  };
  vi.spyOn(api, 'coreWork').mockResolvedValue(work());
  vi.spyOn(api, 'coreWorkCommand');
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('AI work on the actual core tasks route', () => {
  it('exposes explicit automatic preparation on the actual core route without manual bookkeeping', async () => {
    const pending = work();
    pending.works[0] = {...pending.works[0],status:'pending',results:[],result_ids:[],budget:{max_calls:2,reserved:0,used:0}};
    vi.mocked(api.coreWork).mockResolvedValue(pending);
    mount();
    expect(await screen.findByRole('button',{name:'准备本轮执行'})).toBeEnabled();
    expect(screen.queryByRole('button',{name:'预约一次调用'})).toBeNull();
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
  });
  it('shows persisted AI work and downloads without opening manual write controls', async () => {
    mount();
    expect(await screen.findByText('已保存的项目概览')).toBeTruthy();
    expect(screen.getByText('既有责任工作区')).toBeTruthy();
    expect(screen.getByText('1 已用 · 0 已预约 · 上限 2')).toBeTruthy();
    expect(screen.getByRole('link', { name: '下载' })).toHaveAttribute(
      'href',
      '/api/v1/work/results?organization_id=au-1&id=result-1',
    );
    expect(screen.getByText('登记新的 AI 工作')).toBeTruthy();
    expect(screen.queryByRole('button', { name: '开始执行' })).toBeNull();
    expect(screen.queryByRole('button', { name: '预约一次调用' })).toBeNull();
    expect(screen.queryByText('提交候选成果')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: '刷新 AI 工作' }));
    await waitFor(() => expect(api.coreWork).toHaveBeenCalledTimes(2));
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
  });

  it.each(['organization', 'principal', 'protocol'])(
    'rejects a mismatched %s projection',
    async (field) => {
      const value = work(
        field === 'organization' ? 'other-au' : 'au-1',
        field === 'principal' ? 'other-person' : 'p1',
      );
      if (field === 'protocol') value.protocol = 'unknown';
      vi.mocked(api.coreWork).mockResolvedValue(value);
      mount();
      expect(await screen.findByText(/工作读取与当前身份或组织不匹配/)).toBeTruthy();
      expect(screen.queryByText('已保存的项目概览')).toBeNull();
      expect(screen.queryByRole('link', { name: '下载' })).toBeNull();
    },
  );

  it.each(['organization', 'principal', 'service'])(
    'clears previous work when the current %s changes',
    async (field) => {
      const view = mount();
      await screen.findByText('已保存的项目概览');
      vi.mocked(api.coreWork).mockImplementation(() => new Promise(() => {}));
      const organization = field === 'organization' ? 'au-2' : 'au-1';
      state.workspace = {
        ...state.workspace,
        orgId: organization,
        core: core(
          field === 'principal' ? 'p2' : 'p1',
          organization,
          field === 'service' ? 'service-2' : 'service-1',
        ),
      };
      view.refresh();
      expect(screen.queryByText('已保存的项目概览')).toBeNull();
      expect(screen.queryByRole('link', { name: '下载' })).toBeNull();
      expect(screen.getByText('正在读取…')).toBeTruthy();
    },
  );

  it('keeps the prepared AU and legacy tasks routes unchanged', () => {
    state.workspace = {
      ...state.workspace,
      core: { ...core(), au: { ...core().au, schema_version: 1 } },
    };
    const view = mount();
    expect(screen.getByText('准备态原入口')).toBeTruthy();
    expect(api.coreWork).not.toHaveBeenCalled();
    state.workspace = {
      ...state.workspace,
      core: undefined,
      session: { role: 'board', organizations: [{ id: 'au-1', name: 'legacy' }] },
      data: { organization: { name: 'legacy' }, execution_config: {} },
    };
    view.refresh();
    expect(screen.getByText('旧版工作入口')).toBeTruthy();
    expect(api.coreWork).not.toHaveBeenCalled();
  });
});
