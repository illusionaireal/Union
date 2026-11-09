import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
// Controlled DOM regressions for the two independent original command references.
function reserved(automatic: boolean) {
  current.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  current.works[0].budget.reserved = 1;
  current.works[0].steps = [
    {
      seq: 1,
      step_ref: 'w1#s1',
      attempt_id: 'w1#a1',
      purpose: 'work_step',
      status: 'reserved',
      command_id: automatic ? 'original-run' : null,
      model_request_id: automatic ? 'original-model-request' : undefined,
      at: '',
    },
  ];
}

it('the actual automatic reservation has an original-request cancel entry', async () => {
  reserved(true);
  mount();
  await screen.findByText('已登记概览');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: '取消本次执行' })).toBeEnabled();
});

it('a lost cancel response retains its original lookup after reload', async () => {
  reserved(false); // Only to reach the candidate's newly added cancel handler.
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('cancel response lost'));
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await screen.findByText('cancel response lost');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  expect(original.kind).toBe('cancel_step');
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each(['principal_id', 'service_instance'] as const)(
  'cancel completion after %s changes cannot disclose the old receipt',
  async (field) => {
    reserved(false);
    vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
      vi.mocked(api.session).mockResolvedValue({ ...session, [field]: 'other-scope' });
      return { receipt: { ...receipt(r), message: 'old-scope cancellation detail' } };
    });
    mount();
    fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByText('old-scope cancellation detail')).toBeNull();
    expect(screen.queryByText('已登记概览')).toBeNull();
  },
);

it('browsing an unknown reservation does not send any command', async () => {
  reserved(true);
  current.works[0].steps[0].status = 'unknown';
  mount();
  await screen.findByText('已登记概览');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: '取消本次执行' })).toBeNull();
});

it('a retained page run-loop request does not block cancelling its running step', async () => {
  reserved(true);
  current.works[0].steps = [];
  current.works[0].budget.reserved = 0;
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    if (r.kind === 'run_loop') {
      reserved(true);
      current.works[0].steps[0].command_id = String(r.id);
      throw new Error('running loop response lost');
    }
    return { receipt: receipt(r) };
  });
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText('running loop response lost');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.coreWorkCommand).mock.calls.map(([r]) => r.kind)).toEqual([
    'run_loop',
    'cancel_step',
  ]);
});

it('an accepted cancel retains its original lookup after reload', async () => {
  reserved(true);
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await screen.findByText('原请求已完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  expect(original.kind).toBe('cancel_step');
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id));
  await screen.findByText('原请求已完成');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each([true, false])('an intent-only original GET can advance to delivery %s without another POST', async (accepted) => {
  reserved(true);
  let finish!: (value: { receipt: ReturnType<typeof receipt> }) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  const intent = { ...receipt(original), model_request_id: 'original-model-request',
    cancel_accepted: null, message: '取消意图已提交；送达尚未核对' };
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: intent });
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText(intent.message);
  const observation = { cancel_accepted: accepted, message: accepted ? '已送达原请求' : '未确认送达原请求' };
  const delivered = { ...intent, ...observation, delivery: observation };
  await act(async () => { finish({ receipt: delivered }); });
  await screen.findByText(observation.message);
  // A delayed GET can still contain the earlier durable intent snapshot.
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(screen.getByRole('button', { name: '查询原请求' })).toBeEnabled());
  expect(screen.getByText(observation.message)).toBeVisible();
  expect(screen.queryByText(intent.message)).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(sessionStorage)).not.toContain(observation.message);
});

it('a lost POST after intent lookup allows the original GET to reveal durable delivery', async () => {
  reserved(true);
  let fail!: (error: Error) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(() => new Promise((_resolve, reject) => { fail = reject; }));
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  const intent = { ...receipt(original), model_request_id: 'original-model-request',
    cancel_accepted: null, message: '取消意图已提交；送达尚未核对' };
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: intent });
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText(intent.message);
  await act(async () => { fail(new Error('lost response')); });
  const observation = { cancel_accepted: true, message: '已送达原请求' };
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: { ...intent, ...observation, delivery: observation } });
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText(observation.message);
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await screen.findByText(observation.message);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it('a completed run can be displayed after reload and cannot regress to unknown', async () => {
  reserved(true);
  current.works[0].steps = [];
  current.works[0].budget.reserved = 0;
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText('原请求已完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  mount();
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await screen.findByText('原请求已完成');
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: { ...receipt(original),
    status: 'unknown', message: 'old unknown snapshot' } });
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(screen.getByRole('button', { name: '查询原请求' })).toBeEnabled());
  expect(screen.getByText('原请求已完成')).toBeVisible();
  expect(screen.queryByText('old unknown snapshot')).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each([
  [true, 'active'], [true, 'delivered'], [false, 'active'], [false, 'delivered'],
] as const)('closed attempt keeps the actual run lookup (prepare=%s, work=%s)', async (prepare, status) => {
  if (!prepare) {
    reserved(true);
    current.works[0].steps = [];
    current.works[0].budget.reserved = 0;
  }
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    if (r.kind === 'start_attempt') {
      reserved(true);
      current.works[0].steps = [];
      current.works[0].budget.reserved = 0;
    }
    return { receipt: receipt(r) };
  });
  const view = mount();
  if (prepare) fireEvent.click(await screen.findByRole('button', { name: '准备本轮执行' }));
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText('原请求已完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls.at(-1)![0];
  expect(original.kind).toBe('run_loop');
  current.works[0].attempts[0].status = 'closed';
  current.works[0].attempts[0].outcome = 'stopped';
  current.works[0].status = status;
  current.access.can_start = false;
  fireEvent.click(screen.getByRole('button', { name: '刷新 AI 工作' }));
  await screen.findByText('本轮执行已结束');
  expect(within(screen.getByRole('group', { name: '原运行请求' })).getByText(new RegExp(String(original.id)))).toBeVisible();
  view.unmount();
  mount();
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  const recovered = await screen.findByRole('group', { name: '原运行请求' });
  expect(within(recovered).getByText(new RegExp(String(original.id)))).toBeVisible();
  fireEvent.click(within(recovered).getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id));
  await screen.findByText('原请求已完成');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(prepare ? 2 : 1);
  expect(screen.queryByRole('button', { name: '准备本轮执行' })).toBeNull();
});

it('can cancel while the original page run POST is still pending and retain both lookups', async () => {
  reserved(true);
  current.works[0].steps = [];
  current.works[0].budget.reserved = 0;
  let finishRun!: (value: { receipt: ReturnType<typeof receipt> }) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation((r) => {
    if (r.kind === 'run_loop') {
      reserved(true);
      current.works[0].steps[0].command_id = String(r.id);
      return new Promise((resolve) => {
        finishRun = resolve;
      });
    }
    return Promise.resolve({ receipt: receipt(r) });
  });
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole('button', { name: '刷新 AI 工作' }));
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(2));
  await screen.findByText('原请求已完成');
  const [run, cancel] = vi.mocked(api.coreWorkCommand).mock.calls.map(([r]) => r);
  expect([run.kind, cancel.kind]).toEqual(['run_loop', 'cancel_step']);
  expect(run.id).not.toBe(cancel.id);
  finishRun({ receipt: receipt(run) });
  await waitFor(() => expect(screen.getAllByText(/本次操作已记录/)).toHaveLength(2));
  view.unmount();
  current.access.can_start = false;
  vi.mocked(api.coreWorkReceipt).mockImplementation(async (_au, id) => ({
    receipt: receipt(id === run.id ? run : cancel),
  }));
  mount();
  const running = await screen.findByRole('group', { name: '原运行请求' });
  const cancelled = screen.getByRole('group', { name: '原取消请求' });
  fireEvent.click(within(running).getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', run.id));
  await waitFor(() => expect(within(cancelled).getByRole('button')).toBeEnabled());
  fireEvent.click(within(cancelled).getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', cancel.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(2);
});

it('does not replace an original cancel ID after reload or another click', async () => {
  reserved(true);
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await screen.findByText('原请求已完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  mount();
  const button = await screen.findByRole('button', { name: '取消本次执行' });
  expect(button).toBeDisabled();
  fireEvent.click(button);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(sessionStorage)).toContain(original.id);
});

it('a readable reservation without new-action eligibility offers no new cancel', async () => {
  reserved(true);
  current.access.can_start = false;
  mount();
  await screen.findByText('已登记概览');
  expect(screen.queryByRole('button', { name: '取消本次执行' })).toBeNull();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('losing only new-action eligibility before cancel preserves the original run lookup', async () => {
  reserved(true);
  current.works[0].steps = [];
  current.works[0].budget.reserved = 0;
  vi.mocked(api.coreWorkCommand).mockImplementation(async () => {
    reserved(true);
    throw new Error('run response lost');
  });
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText('run response lost');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  mount();
  const cancel = await screen.findByRole('button', { name: '取消本次执行' });
  current.access.can_start = false;
  await act(async () => { fireEvent.click(cancel); });
  expect(screen.getByText('已登记概览')).toBeVisible();
  const group = screen.getByRole('group', { name: '原运行请求' });
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(within(group).getByRole('button', { name: '查询原请求' }));
  await screen.findByText('原请求已完成');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each(['start_attempt', 'run_loop'])('%s preflight refuses a new action without hiding readable work', async (kind) => {
  if (kind === 'run_loop') {
    reserved(true);
    current.works[0].steps = [];
    current.works[0].budget.reserved = 0;
  }
  mount();
  const button = await screen.findByRole('button', { name: kind === 'run_loop' ? '运行 AI 工作' : '准备本轮执行' });
  current.access.can_start = false;
  await act(async () => { fireEvent.click(button); });
  expect(screen.getByText('已登记概览')).toBeVisible();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  await waitFor(() => expect(screen.queryByRole('button', { name: /准备本轮执行|运行 AI 工作/ })).toBeNull());
});

it.each(['run_loop', 'cancel_step'])(
  'a late %s POST transport failure cannot replace its independently confirmed receipt',
  async (kind) => {
    reserved(true);
    if (kind === 'run_loop') {
      current.works[0].steps = [];
      current.works[0].budget.reserved = 0;
    }
    let fail!: (error: Error) => void;
    vi.mocked(api.coreWorkCommand).mockImplementation(() => new Promise((_resolve, reject) => { fail = reject; }));
    mount();
    fireEvent.click(await screen.findByRole('button', { name: kind === 'run_loop' ? '运行 AI 工作' : '取消本次执行' }));
    await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
    const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
    vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
    fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
    await screen.findByText('原请求已完成');
    await act(async () => { fail(new Error('late transport failure')); });
    expect(screen.getByText('原请求已完成')).toBeVisible();
    expect(screen.queryByText('late transport failure')).toBeNull();
    expect(screen.getByText(/本次操作已记录/)).toBeVisible();
    expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  },
);

it('a failed repeat GET preserves a confirmed cancel while actual access loss still clears it', async () => {
  reserved(true);
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await screen.findByText('原请求已完成');
  vi.mocked(api.coreWorkReceipt).mockRejectedValue(new Error('GET temporarily unavailable'));
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(screen.getByRole('button', { name: '查询原请求' })).toBeEnabled());
  expect(screen.getByText('原请求已完成')).toBeVisible();
  vi.mocked(api.coreWorkReceipt).mockRejectedValue(new ApiError('no session', 401, 'unauthorized'));
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText(/权限或身份已变化/);
  expect(screen.queryByText('已登记概览')).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each([401, 403])('a late POST %i still clears an independently confirmed cancel', async (status) => {
  reserved(true);
  let fail!: (error: Error) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(() => new Promise((_resolve, reject) => { fail = reject; }));
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText('原请求已完成');
  await act(async () => { fail(new ApiError('access lost', status, 'unauthorized')); });
  await screen.findByText(/权限或身份已变化/);
  expect(screen.queryByText('原请求已完成')).toBeNull();
});
