import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '../../api/client';
import type { CoreWork, CoreWorkItem, Session } from '../../api/types';
import { WorkPanel } from './WorkPanel';

vi.mock('../../api/client', async (original) => ({
  ...(await original<typeof import('../../api/client')>()),
  api: { session: vi.fn(), coreWork: vi.fn(), coreWorkCommand: vi.fn(), coreWorkReceipt: vi.fn() },
}));
const session = {
  core_protocol: 'core.au.v1',
  principal_id: 'p1',
  service_instance: 's1',
  organizations: [{ id: 'au-1', profile: 'core_v1' }],
} as Session;
let current: CoreWork;
const item = (): CoreWorkItem => ({
  id: 'w1',
  title: '已登记概览',
  goal: '私有目标不得存储',
  status: 'pending',
  version: 1,
  max_calls: 2,
  materials_root: 'docs',
  created_at: '',
  responsible: { member_id: 'm1', name: 'Agent', binding_id: 'b1', duty: '交付' },
  definition: {
    id: 'd1',
    version: 1,
    connection_id: 'c1',
    model: 'model',
    tools: ['read_document'],
  },
  mandate: { id: 'ma1', version: 1, actions: ['read_document'], active: true },
  attempt_ids: [],
  result_ids: [],
  attempts: [],
  steps: [],
  tool_calls: [],
  results: [],
  budget: { max_calls: 2, reserved: 0, used: 0 },
  materials: { reference: 'docs', available: true, documents: 1 },
});
const receipt = (r: Record<string, unknown>) => ({
  id: String(r.id),
  organization_id: r.organization_id,
  kind: r.kind,
  base_version: r.base_version,
  actor_principal_id: 'p1',
  status: 'succeeded',
  version: 5,
  message: '原请求已完成',
});
function mount() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}
    >
      <WorkPanel
        organizationId="au-1"
        principalId="p1"
        serviceInstance="s1"
        readOnly
        allowExecution
      />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  current = {
    protocol: 'core.work.v1',
    organization_id: 'au-1',
    version: 4,
    access: { principal_id: 'p1', can_start: true },
    capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
    works: [item()],
  };
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.coreWork).mockImplementation(async () => structuredClone(current));
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({ receipt: receipt(r) }));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it('a stale attempt from the previous host has no new dispatch control', async () => {
  current.works[0].attempts = [
    {
      id: 'w1#a1',
      seq: 1,
      status: 'running',
      outcome: null,
      started_at: '',
      ended_at: null,
      stale: true,
    },
  ];
  mount();
  await screen.findByText('已登记概览');
  expect(screen.queryByRole('button', { name: '运行 AI 工作' })).toBeNull();
});
it('prepares explicitly, then actually dispatches run_loop once using current version', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    if (r.kind === 'start_attempt') {
      current.version = 5;
      current.works[0].attempts = [
        { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
      ];
    }
    return { receipt: receipt(r) };
  });
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '准备本轮执行' }));
  await screen.findByRole('button', { name: '运行 AI 工作' });
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: '运行 AI 工作' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.coreWorkCommand).mock.calls[1][0]).toMatchObject({
    kind: 'run_loop',
    organization_id: 'au-1',
    base_version: 5,
    data: { work_id: 'w1' },
  });
});
it('lost response survives reload with only the original identity and queries without any replay', async () => {
  current.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText(/原请求已保留/);
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  expect(JSON.stringify(sessionStorage)).not.toContain('私有目标');
  expect(JSON.stringify(sessionStorage)).toContain(String(original.id));
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await screen.findByText(/本次操作已记录/);
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});
it('a missing or unknown original receipt keeps its ID and cannot dispatch a replacement', async () => {
  current.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('丢失响应'));
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText(/原请求已保留/);
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  vi.mocked(api.coreWorkReceipt).mockRejectedValueOnce(new Error('原请求尚无回执'));
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText('原请求尚无回执');
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({
    receipt: { ...receipt(original), model_outcome: 'unknown' },
  });
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledTimes(2));
  expect(screen.getByText(/原请求已保留/)).toBeTruthy();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});
it.each(['principal_id', 'service_instance'] as const)(
  'a changed cookie %s while the POST completes clears prior work and receipt content',
  async (field) => {
    current.works[0].attempts = [
      { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
    ];
    vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
      vi.mocked(api.session).mockResolvedValue({ ...session, [field]: 'another' });
      return { receipt: { ...receipt(r), message: '迟到私有结果' } };
    });
    mount();
    fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByText('已登记概览')).toBeNull();
    expect(screen.queryByText('迟到私有结果')).toBeNull();
  },
);
it('permission loss on fresh read prevents dispatch and an unknown reservation has no new run', async () => {
  const view = mount();
  await screen.findByText('已登记概览');
  current.access.can_start = false;
  fireEvent.click(screen.getByRole('button', { name: '准备本轮执行' }));
  await screen.findByText(/权限或身份已变化/);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  view.unmount();
  current.access.can_start = true;
  current.works[0].budget.reserved = 1;
  mount();
  await screen.findByText('已登记概览');
  expect(screen.queryByRole('button', { name: '准备本轮执行' })).toBeNull();
});
it('double click stays single POST and a mismatched receipt never enables replacement dispatch', async () => {
  current.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  let resolve!: (value: Awaited<ReturnType<typeof api.coreWorkCommand>>) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  mount();
  const button = await screen.findByRole('button', { name: '运行 AI 工作' });
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  resolve({ receipt: { ...receipt(original), id: 'wrong-request' } });
  await screen.findByText(/原请求已保留/);
  expect(screen.queryByRole('button', { name: '运行 AI 工作' })).toBeNull();
});
it('storage refusal prevents POST and cookie principal mismatch clears old work', async () => {
  const view = mount();
  await screen.findByText('已登记概览');
  vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'other' });
  fireEvent.click(screen.getByRole('button', { name: '准备本轮执行' }));
  await screen.findByText(/权限或身份已变化/);
  expect(screen.queryByText('已登记概览')).toBeNull();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  view.unmount();
  vi.mocked(api.session).mockResolvedValue(session);
  mount();
  const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota');
  });
  fireEvent.click(await screen.findByRole('button', { name: '准备本轮执行' }));
  await screen.findByText(/无法保留原请求/);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  spy.mockRestore();
});

it('a pending original receipt returns 403 without removing an independently authorized work or its lookup', async () => {
  current.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  let finish!: (value: Awaited<ReturnType<typeof api.coreWorkCommand>>) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  vi.mocked(api.coreWorkReceipt).mockRejectedValue(new ApiError('无权访问', 403, 'not_authorized'));
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await screen.findByText(/原回执尚不可取得/);
  expect(screen.getByText('已登记概览')).toBeTruthy();
  expect(screen.getByRole('button', { name: '查询原请求' })).toBeEnabled();
  expect(screen.queryByRole('button', { name: '运行 AI 工作' })).toBeNull();
  expect(JSON.stringify(sessionStorage)).toContain(String(original.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  finish({ receipt: receipt(original) });
  await screen.findByText(/本次操作已记录/);
});

it.each(['denied', 'principal', 'organization', 'protocol', 'session'])(
  'a forbidden receipt still clears old work when the independent access check is %s',
  async (failure) => {
    vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('丢失响应'));
    mount();
    fireEvent.click(await screen.findByRole('button', { name: '准备本轮执行' }));
    await screen.findByText(/原请求已保留/);
    vi.mocked(api.coreWorkReceipt).mockRejectedValue(new ApiError('无权访问', 403, 'not_authorized'));
    vi.mocked(api.coreWork).mockImplementation(async () => {
      if (failure === 'denied') throw new ApiError('无权访问', 403, 'not_authorized');
      const read = structuredClone(current);
      if (failure === 'principal') read.access.principal_id = 'p2';
      if (failure === 'organization') read.organization_id = 'au-2';
      if (failure === 'protocol') read.protocol = 'other' as CoreWork['protocol'];
      if (failure === 'session') vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'p2' });
      return read;
    });
    fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByText('已登记概览')).toBeNull();
    expect(screen.queryByRole('button', { name: '查询原请求' })).toBeNull();
    expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  },
);
