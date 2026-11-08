import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '../../api/client';
import type { CoreModels, CoreWork, Session } from '../../api/types';
import { WorkPanel } from './WorkPanel';

vi.mock('../../api/client', async (original) => ({
  ...(await original<typeof import('../../api/client')>()),
  api: {
    session: vi.fn(),
    coreWork: vi.fn(),
    coreModels: vi.fn(),
    coreWorkCommand: vi.fn(),
    coreWorkReceipt: vi.fn(),
  },
}));
const session = {
  core_protocol: 'core.au.v1',
  principal_id: 'p1',
  service_instance: 's1',
} as Session;
let work: CoreWork, models: CoreModels;
const receipt = (r: Record<string, unknown>) => ({
  id: String(r.id),
  kind: r.kind,
  organization_id: r.organization_id,
  base_version: r.base_version,
  actor_principal_id: 'p1',
  status: 'succeeded',
  version: 5,
  work_id: (r.data as Record<string, unknown>).work_id,
  message: '登记完成',
});
function mount(principalId = 'p1', organizationId = 'au-1') {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}
    >
      <WorkPanel
        organizationId={organizationId}
        principalId={principalId}
        serviceInstance="s1"
        readOnly
        allowExecution
        allowRegistration
      />
    </QueryClientProvider>,
  );
}
async function fill() {
  fireEvent.click(await screen.findByText('登记新的 AI 工作'));
  fireEvent.change(screen.getByLabelText('工作标题'), { target: { value: '项目概览' } });
  fireEvent.change(screen.getByLabelText('目标'), { target: { value: '私有目标正文' } });
  fireEvent.change(screen.getByLabelText('负责 AI 成员名称'), { target: { value: '研究助手' } });
  fireEvent.change(screen.getByLabelText('资料目录引用'), { target: { value: 'private-docs' } });
  fireEvent.change(screen.getByLabelText('调用上限'), { target: { value: '2' } });
  const button = screen.getByRole('button', { name: '登记 AI 工作' });
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  work = {
    protocol: 'core.work.v1',
    organization_id: 'au-1',
    version: 4,
    access: { principal_id: 'p1', can_start: true },
    works: [],
    capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
  };
  models = {
    protocol: 'core.models.v1',
    organization_id: 'au-1',
    version: 4,
    access: { principal_id: 'p1', can_configure: true },
    governance_status: 'active',
    document_read_allowed: true,
    connections: [
      {
        id: 'c1',
        name: '当前默认连接',
        revision: 2,
        enabled: true,
        is_default: true,
        profile: 'modeld_grant',
        model: 'model',
      },
    ],
    resources: { grant: null, reserved_calls: 0, plan_max_calls: 10 },
  };
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.coreWork).mockImplementation(async () => structuredClone(work));
  vi.mocked(api.coreModels).mockImplementation(async () => structuredClone(models));
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({ receipt: receipt(r) }));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it('Core empty state registers one bounded responsible Work, persisting original identity before POST', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    expect(JSON.stringify(sessionStorage)).toContain(String(r.id));
    expect(JSON.stringify(sessionStorage)).toContain(
      String((r.data as Record<string, unknown>).work_id),
    );
    expect(JSON.stringify(sessionStorage)).not.toMatch(/私有目标正文|private-docs|研究助手/);
    return { receipt: receipt(r) };
  });
  mount();
  const button = await fill();
  fireEvent.click(button);
  fireEvent.click(button);
  await screen.findByText('登记完成');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.coreWorkCommand).mock.calls[0][0]).toMatchObject({
    kind: 'start_work',
    base_version: 4,
    data: {
      title: '项目概览',
      goal: '私有目标正文',
      member_name: '研究助手',
      connection_id: 'c1',
      expected_revision: 2,
      materials_root: 'private-docs',
      max_calls: 2,
      tools: ['read_document'],
    },
  });
  expect(screen.queryByLabelText('成果正文')).toBeNull();
  expect(screen.queryByText('结束执行')).toBeNull();
});

it('lost response reload keeps original lookup even without permission to start, and never replays', async () => {
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  const view = mount();
  fireEvent.click(await fill());
  await screen.findByText('连接中断');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  work.access.can_start = false;
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询登记原请求' }));
  await screen.findByText('登记完成');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('button', { name: '登记 AI 工作' })).toBeNull();
});

it('storage failure prevents any POST', async () => {
  mount();
  const button = await fill();
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota');
  });
  fireEvent.click(button);
  await screen.findByText(/浏览器无法保留原请求/);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it.each(['principal', 'service', 'authorization', 'connection', 'version', 'model-scope'])(
  'fresh %s change rejects registration before POST',
  async (change) => {
    mount();
    const button = await fill();
    if (change === 'principal')
      vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'p2' });
    if (change === 'service')
      vi.mocked(api.session).mockResolvedValue({ ...session, service_instance: 's2' });
    if (change === 'authorization') work.access.can_start = false;
    if (change === 'connection') models.connections[0].revision++;
    if (change === 'version') work.version++;
    if (change === 'model-scope') models.organization_id = 'au-2';
    fireEvent.click(button);
    await screen.findByText(/权限或身份已变化|配置或版本已变化|当前不能登记新工作/);
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
    if (change === 'model-scope') expect(screen.queryByLabelText('目标')).toBeNull();
  },
);

it.each(['actor', 'work', 'version'])('mismatched %s receipt stays unresolved', async (change) => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({
    receipt: {
      ...receipt(r),
      ...(change === 'actor'
        ? { actor_principal_id: 'p2' }
        : change === 'work'
          ? { work_id: 'wrong' }
          : { base_version: 99 }),
    },
  }));
  mount();
  fireEvent.click(await fill());
  await screen.findByText(/回执与原请求不匹配/);
  expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
  expect(screen.getByRole('button', { name: '查询登记原请求' })).toBeTruthy();
});

it('loss of registration eligibility preserves readable work and its original execution lookup', async () => {
  work.works = [
    {
      id: 'existing-work',
      title: '已有工作',
      goal: '原工作继续负责',
      status: 'pending',
      version: 1,
      max_calls: 2,
      materials_root: 'docs',
      created_at: '',
      responsible: { member_id: 'm0', name: '原助手', binding_id: 'b0', duty: '交付' },
      definition: {
        id: 'd0',
        version: 1,
        connection_id: 'c1',
        model: 'model',
        tools: ['read_document'],
      },
      mandate: { id: 'ma0', version: 1, actions: ['read_document'], active: true },
      attempt_ids: [],
      result_ids: [],
      attempts: [],
      steps: [],
      tool_calls: [],
      results: [],
      budget: { max_calls: 2, reserved: 1, used: 0 },
      materials: { reference: 'docs', available: true, documents: 1 },
    },
  ];
  const scope = {
    principalId: 'p1',
    serviceInstance: 's1',
    organizationId: 'au-1',
    workId: 'existing-work',
  };
  const original = {
    ...scope,
    id: 'existing-command',
    kind: 'run_loop',
    base_version: 3,
    resolved: false,
  };
  sessionStorage.setItem(
    'union-work-execution:' + JSON.stringify(scope),
    JSON.stringify([original]),
  );
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({
    receipt: {
      id: original.id,
      kind: original.kind,
      organization_id: 'au-1',
      base_version: 3,
      actor_principal_id: 'p1',
      status: 'succeeded',
      version: 4,
      message: '原执行已核对',
    },
  });
  mount();
  const button = await fill();
  work.access.can_start = false;
  fireEvent.click(button);
  await screen.findByText(/权限或身份已变化|当前不能登记新工作/);
  expect(screen.getByText('已有工作')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText('原执行已核对');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: '登记 AI 工作' })).toBeNull();
});

it.each([401, 403])(
  'an actual AU read denial (%s) still clears registration and prevents POST',
  async (status) => {
    mount();
    const button = await fill();
    vi.mocked(api.coreWork).mockRejectedValue(new ApiError('not_authorized', status));
    fireEvent.click(button);
    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByLabelText('目标')).toBeNull();
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
  },
);

it('corrupt persisted identity prevents a replacement POST', async () => {
  sessionStorage.setItem(
    'union-work-command:' +
      JSON.stringify({ principalId: 'p1', serviceInstance: 's1', organizationId: 'au-1' }),
    '{broken',
  );
  mount();
  await screen.findByText(/原请求记录不可读/);
  expect(screen.getByRole('button', { name: '登记 AI 工作' })).toBeDisabled();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('an unknown receipt retains original identity and prevents another registration', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({
    receipt: { ...receipt(r), status: 'unknown', message: '结果未知' },
  }));
  mount();
  fireEvent.click(await fill());
  await screen.findByText('结果未知');
  expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
  expect(screen.getByRole('button', { name: '查询登记原请求' })).toBeTruthy();
});

it('reload revalidates a persisted completion before allowing another registration', async () => {
  const view = mount();
  fireEvent.click(await fill());
  await screen.findByText('登记完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  mount();
  await screen.findByRole('button', { name: '查询登记原请求' });
  expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
  await screen.findByRole('button', { name: '登记另一项工作' });
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each(['0', '-1', '1.5', '10001'])('invalid call cap %s cannot be submitted', async (calls) => {
  mount();
  const button = await fill();
  fireEvent.change(screen.getByLabelText('调用上限'), { target: { value: calls } });
  expect(button).toBeDisabled();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('a confirmed original permits only explicit new work, retaining the previous identity', async () => {
  mount();
  fireEvent.click(await fill());
  await screen.findByText('登记完成');
  const first = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  fireEvent.click(screen.getByRole('button', { name: '登记另一项工作' }));
  fireEvent.click(await fill());
  await screen.findByText('登记完成');
  const second = vi.mocked(api.coreWorkCommand).mock.calls[1][0];
  expect(first.id).not.toBe(second.id);
  expect(JSON.stringify(sessionStorage)).toContain(String(first.id));
  expect(JSON.stringify(sessionStorage)).toContain(String(second.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(2);
});

it('receipt-only 403 preserves original ID when current AU read remains authorized', async () => {
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  vi.mocked(api.coreWorkReceipt).mockRejectedValue(new ApiError('not_authorized', 403));
  mount();
  fireEvent.click(await fill());
  await screen.findByText('连接中断');
  fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
  await screen.findByText(/原回执尚不可取得/);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: '查询登记原请求' })).toBeEnabled();
});

it('permission lost after committed POST clears old result and prevents adoption', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    vi.mocked(api.coreWork).mockRejectedValue(new ApiError('not_authorized', 403));
    return { receipt: receipt(r) };
  });
  mount();
  fireEvent.click(await fill());
  await screen.findByText(/权限或身份已变化/);
  expect(screen.queryByText('登记完成')).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(sessionStorage)).toContain('start_work');
});

it('unmounted old principal cannot adopt a late response into the new scope', async () => {
  let finish!: (v: { receipt: ReturnType<typeof receipt> }) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const view = mount();
  fireEvent.click(await fill());
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  work.access.principal_id = 'p2';
  work.access.can_start = false;
  mount('p2');
  finish({ receipt: receipt(original) });
  await screen.findByText(/尚未登记 V1 工作/);
  expect(screen.queryByText('登记完成')).toBeNull();
  expect(screen.queryByRole('button', { name: '查询登记原请求' })).toBeNull();
});

it('a late failed POST cannot downgrade an independently confirmed original receipt', async () => {
  let fail!: (reason: Error) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(
    () =>
      new Promise((_resolve, reject) => {
        fail = reject;
      }),
  );
  mount();
  fireEvent.click(await fill());
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
  await screen.findByText('登记完成');
  fail(new Error('late lost response'));
  await waitFor(() => expect(screen.getByRole('button', { name: '登记另一项工作' })).toBeEnabled());
  expect(screen.getByText('登记完成')).toBeTruthy();
  expect(screen.queryByText('late lost response')).toBeNull();
});
