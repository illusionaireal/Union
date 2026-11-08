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
let work: CoreWork;
const session = {
  core_protocol: 'core.au.v1',
  principal_id: 'p1',
  service_instance: 's1',
} as Session;
function item(id = 'w1'): CoreWorkItem {
  return {
    id,
    title: '工作 ' + id,
    goal: '原目标',
    status: 'pending',
    version: 1,
    max_calls: 2,
    materials_root: 'docs',
    created_at: '',
    responsible: { member_id: 'm', name: '助手', duty: '研究', binding_id: 'b' },
    definition: {
      id: 'd',
      version: 1,
      connection_id: 'c',
      model: 'fake',
      tools: ['read_document'],
    },
    mandate: { id: 'ma', version: 1, actions: ['read_document'], active: true },
    attempt_ids: [],
    result_ids: ['r1'],
    tool_calls: [],
    attempts: [],
    steps: [],
    budget: { max_calls: 2, used: 2, reserved: 0 },
    materials: { reference: 'docs', available: true, documents: 1 },
    results: [
      {
        id: 'r1',
        seq: 1,
        title: '概览',
        sha256: 'a'.repeat(64),
        bytes: 12,
        sources: [id + '#s1'],
        status: 'candidate',
        created_at: '',
        adopted_at: null,
      },
    ],
  };
}
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
        allowResultDelivery
      />
    </QueryClientProvider>,
  );
}
function receipt(r: Record<string, unknown>): {
  id: string;
  kind: unknown;
  organization_id: unknown;
  base_version: unknown;
  version: number;
  actor_principal_id: string;
  status: string;
  message: string;
  result?: { id: string; sha256: string; status: string };
  work?: { work_id: string; result_id: string; work_status: string };
} {
  const data = r.data as Record<string, string>;
  return {
    id: String(r.id),
    kind: r.kind,
    organization_id: r.organization_id,
    base_version: r.base_version,
    version: Number(r.base_version) + 1,
    actor_principal_id: 'p1',
    status: 'succeeded',
    message: '已确认 ' + r.kind,
    ...(r.kind === 'adopt_result'
      ? { result: { id: data.result_id, sha256: 'a'.repeat(64), status: 'adopted' } }
      : { work: { work_id: data.work_id, result_id: data.result_id, work_status: 'delivered' } }),
  };
}
async function adopt() {
  fireEvent.click(await screen.findByRole('button', { name: '采用此成果' }));
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  work = {
    protocol: 'core.work.v1',
    organization_id: 'au-1',
    version: 4,
    access: { principal_id: 'p1', can_start: false, can_manage_results: true },
    works: [item()],
    capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
  };
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.coreWork).mockImplementation(async () => structuredClone(work));
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({ receipt: receipt(r) }));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it('adopts with disabled model connection, persists scoped identity before a single POST', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    expect(JSON.stringify(sessionStorage)).toContain(String(r.id));
    expect(JSON.stringify(sessionStorage)).not.toContain('原目标');
    return { receipt: receipt(r) };
  });
  mount();
  const button = await screen.findByRole('button', { name: '采用此成果' });
  fireEvent.click(button);
  fireEvent.click(button);
  await screen.findByText('已确认 adopt_result');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.coreWorkCommand).mock.calls[0][0]).toMatchObject({
    kind: 'adopt_result',
    data: { work_id: 'w1', result_id: 'r1' },
    base_version: 4,
  });
  expect(screen.getByText(/来源：w1#s1/)).toBeTruthy();
  expect(screen.getByText('下载').getAttribute('href')).toContain('work_id=w1');
  expect(screen.queryByLabelText('成果正文')).toBeNull();
});

it.each(['adopt_result', 'deliver_work'])(
  'keeps %s recovery after committed state change and reload without replay',
  async (kind) => {
    if (kind === 'deliver_work') work.works[0].results[0].status = 'adopted';
    let original: Record<string, unknown> = {};
    vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
      original = r;
      work.version++;
      work.works[0].results[0].status = 'adopted';
      if (kind === 'deliver_work') work.works[0].status = 'delivered';
      throw new Error('连接中断');
    });
    const view = mount();
    fireEvent.click(
      await screen.findByRole('button', {
        name: kind === 'adopt_result' ? '采用此成果' : '交付此成果',
      }),
    );
    await screen.findByText('连接中断');
    view.unmount();
    work.access.can_manage_results = false;
    vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
    mount();
    fireEvent.click(
      await screen.findByRole('button', {
        name: kind === 'adopt_result' ? '查询采用原请求' : '查询交付原请求',
      }),
    );
    await screen.findByText('已确认 ' + kind);
    expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
    expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  },
);

it.each(['id', 'sha256', 'kind', 'actor', 'work'])(
  'rejects mismatched successful receipt %s',
  async (field) => {
    vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
      const value = receipt(r);
      if (field === 'id') value.result!.id = 'foreign';
      if (field === 'sha256') value.result!.sha256 = 'b'.repeat(64);
      if (field === 'kind') value.kind = 'deliver_work';
      if (field === 'actor') value.actor_principal_id = 'other';
      if (field === 'work') value.work!.work_id = 'foreign';
      return { receipt: value };
    });
    if (field === 'work') work.works[0].results[0].status = 'adopted';
    mount();
    fireEvent.click(
      await screen.findByRole('button', { name: field === 'work' ? '交付此成果' : '采用此成果' }),
    );
    await screen.findByText('回执与原请求不匹配');
    expect(screen.queryByText(/^已确认/)).toBeNull();
  },
);

it('isolates identical result IDs in different works, both commands and old registration references', async () => {
  work.works.push(item('w2'));
  const oldKey =
    'union-work-command:' +
    JSON.stringify({ principalId: 'p1', serviceInstance: 's1', organizationId: 'au-1' });
  sessionStorage.setItem(oldKey, '[]');
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  mount();
  const buttons = await screen.findAllByRole('button', { name: '采用此成果' });
  fireEvent.click(buttons[0]);
  await screen.findByText('连接中断');
  fireEvent.click(buttons[1]);
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(2));
  expect(sessionStorage.getItem(oldKey)).toBe('[]');
  expect(sessionStorage.length).toBe(3);
  expect(screen.getAllByRole('button', { name: '查询采用原请求' })).toHaveLength(2);
});

it('storage failure blocks POST', async () => {
  mount();
  await screen.findByRole('button', { name: '采用此成果' });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw Error('full');
  });
  await adopt();
  await screen.findByText('浏览器无法保留原请求，尚未提交');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it.each(['authority', 'version', 'digest', 'session'])(
  'fresh %s change blocks a new action',
  async (field) => {
    mount();
    await screen.findByRole('button', { name: '采用此成果' });
    if (field === 'authority') work.access.can_manage_results = false;
    if (field === 'version') work.version++;
    if (field === 'digest') work.works[0].results[0].sha256 = 'b'.repeat(64);
    if (field === 'session')
      vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'other' });
    await adopt();
    if (field === 'session')
      await screen.findByText('权限或身份已变化，请刷新当前权限后重开工作页。');
    else await waitFor(() => expect(screen.getByRole('status')).toBeTruthy());
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
  },
);

it('running attempt prevents delivery while preserving adopted result download', async () => {
  work.works[0].results[0].status = 'adopted';
  work.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  mount();
  await screen.findByText(/来源：w1#s1/);
  expect(screen.queryByRole('button', { name: '交付此成果' })).toBeNull();
  expect(screen.getByText('下载')).toBeTruthy();
});

it.each(['transport', 'denied', 'principal', 'service'])(
  'confirmed adoption plus late POST %s preserves facts but rechecks access',
  async (field) => {
    let resolvePost!: (value: { receipt: ReturnType<typeof receipt> }) => void;
    let rejectPost!: (error: Error) => void;
    vi.mocked(api.coreWorkCommand).mockImplementation(
      () =>
        new Promise((resolve, reject) => {
          resolvePost = resolve;
          rejectPost = reject;
        }),
    );
    mount();
    await adopt();
    await screen.findByRole('button', { name: '查询采用原请求' });
    const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
    vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
    fireEvent.click(screen.getByRole('button', { name: '查询采用原请求' }));
    await screen.findByText('已确认 adopt_result');
    if (field === 'transport') rejectPost(Error('迟到网络故障'));
    else if (field === 'denied') rejectPost(new ApiError('无权读取', 403));
    else {
      vi.mocked(api.session).mockResolvedValue({
        ...session,
        ...(field === 'principal' ? { principal_id: 'other' } : { service_instance: 'other' }),
      });
      resolvePost({ receipt: receipt(original) });
    }
    if (field === 'transport') {
      await waitFor(() => expect(screen.queryByText('迟到网络故障')).toBeNull());
      expect(screen.getByText('已确认 adopt_result')).toBeTruthy();
    } else {
      await screen.findByText('权限或身份已变化，请刷新当前权限后重开工作页。');
      expect(screen.queryByText('已确认 adopt_result')).toBeNull();
    }
    expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  },
);

it('a late failed GET does not downgrade an adoption already confirmed by POST', async () => {
  let resolvePost!: (value: { receipt: ReturnType<typeof receipt> }) => void;
  let rejectGet!: (error: Error) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(
    () =>
      new Promise((resolve) => {
        resolvePost = resolve;
      }),
  );
  vi.mocked(api.coreWorkReceipt).mockImplementation(
    () =>
      new Promise((_, reject) => {
        rejectGet = reject;
      }),
  );
  mount();
  await adopt();
  fireEvent.click(await screen.findByRole('button', { name: '查询采用原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledTimes(1));
  resolvePost({ receipt: receipt(vi.mocked(api.coreWorkCommand).mock.calls[0][0]) });
  await screen.findByText('已确认 adopt_result');
  rejectGet(Error('迟到查询故障'));
  await waitFor(() => expect(screen.getByRole('button', { name: '查询采用原请求' })).toBeEnabled());
  expect(screen.queryByText('迟到查询故障')).toBeNull();
  expect(screen.getByText('已确认 adopt_result')).toBeTruthy();
});

it('a verified rejection can be explicitly reconsidered with a new ID while preserving history', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementationOnce(async (r) => ({
    receipt: { ...receipt(r), status: 'rejected', message: '旧版本被拒绝' },
  }));
  mount();
  await adopt();
  await screen.findByText('旧版本被拒绝');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: '重新核对采用' }));
  await adopt();
  await screen.findByText('已确认 adopt_result');
  const calls = vi.mocked(api.coreWorkCommand).mock.calls;
  expect(calls).toHaveLength(2);
  expect(calls[0][0].id).not.toBe(calls[1][0].id);
  expect(JSON.stringify(sessionStorage)).toContain(String(calls[0][0].id));
  expect(JSON.stringify(sessionStorage)).toContain(String(calls[1][0].id));
});
