import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '../../api/client';
import { WorkPanel } from './WorkPanel';

vi.mock('../../api/client', async original => ({
  ...(await original<typeof import('../../api/client')>()),
  api: { session: vi.fn(), coreWork: vi.fn(), coreWorkEvents: vi.fn(), coreWorkCommand: vi.fn() },
}));
const connection = { id: 'c1', revision: 1, profile: 'openai_compatible', model: 'm1',
  grant_ref: 'g1', grant_revision: 1, max_output_tokens: 100 };
const step = { seq: 1, step_ref: 'w1#s1', attempt_id: 'w1#a1', purpose: 'work_step',
  status: 'reserved', command_id: 'cmd1', model_request_id: 'original-model',
  connection, can_observe: true, at: '' };
const session = { core_protocol: 'core.au.v1', principal_id: 'p1', service_instance: 's1', organizations: [{ id: 'au1', profile: 'core_v1' }] };
let work: any;
function result(events = [{ seq: 1, type: 'text_delta', text: '原步进正文' }]) {
  return { protocol: 'core.work-events.v1', organization_id: 'au1', work_id: 'w1',
    step_ref: step.step_ref, attempt_id: step.attempt_id, command_id: step.command_id,
    model_request_id: step.model_request_id, connection, access: { principal_id: 'p1', service_instance: 's1' },
    version: 5, source: 'persisted_modeld_events', state: 'completed', events, cursor: 1, last_seq: 1,
    has_more: false, events_complete: true, truncated: false };
}
function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
    <WorkPanel organizationId="au1" principalId="p1" serviceInstance="s1" readOnly allowExecution />
  </QueryClientProvider>);
}
beforeEach(() => {
  vi.resetAllMocks(); sessionStorage.clear(); localStorage.clear();
  work = { protocol: 'core.work.v1', organization_id: 'au1', version: 5, access: { principal_id: 'p1', can_start: false },
    capabilities: {}, works: [{ id: 'w1', title: '工作', goal: '目标', status: 'active',
      responsible: { name: 'AI', duty: '交付' }, mandate: { active: true, actions: [] },
      budget: { max_calls: 2, reserved: 1, used: 0 }, attempts: [], steps: [structuredClone(step)],
      tool_calls: [], results: [], materials: {} }] };
  vi.mocked(api.session).mockResolvedValue(session as any);
  vi.mocked(api.coreWork).mockImplementation(async () => structuredClone(work));
  vi.mocked(api.coreWorkEvents).mockResolvedValue(result() as any);
});
afterEach(cleanup);
it('shows the original work request output with read-only eligibility and never dispatches or stores text', async () => {
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('原步进正文');
  expect(api.coreWorkEvents).toHaveBeenCalledWith('au1', 'w1', 'w1#s1', 0, expect.any(AbortSignal));
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(JSON.stringify(sessionStorage) + JSON.stringify(localStorage)).not.toContain('原步进正文');
});
it('clears confirmed output on a forbidden read', async () => {
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('原步进正文');
  vi.mocked(api.coreWorkEvents).mockRejectedValue(new ApiError('denied', 403, 'not_authorized'));
  fireEvent.click(screen.getByRole('button', { name: '查询原工作输出' }));
  await waitFor(() => expect(screen.queryByText('原步进正文')).toBeNull());
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});
it('shows supported tool event names while treating them separately from executed tool facts', async () => {
  vi.mocked(api.coreWorkEvents).mockResolvedValue({ ...result(),
    events: [{ seq: 1, type: 'tool_call_complete', name: 'read_document' }] } as any);
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('模型提出工具调用：read_document。实际执行以原工作回执为准。');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});
it.each(['organization_id', 'work_id', 'step_ref', 'attempt_id', 'command_id', 'model_request_id'])(
  'refuses a response with a different original %s', async field => {
    vi.mocked(api.coreWorkEvents).mockResolvedValue({ ...result(), [field]: 'other' } as any);
    mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
    await screen.findByText('权限或原请求身份已变化，工作输出已清除。');
    expect(screen.queryByText('原步进正文')).toBeNull();
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
  },
);
it('refuses a changed original connection revision and a changed session after GET', async () => {
  vi.mocked(api.coreWorkEvents).mockResolvedValue({ ...result(), connection: { ...connection, revision: 2 } } as any);
  let view = mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('权限或原请求身份已变化，工作输出已清除。');
  view.unmount();
  vi.mocked(api.coreWorkEvents).mockResolvedValue(result() as any);
  vi.mocked(api.session).mockResolvedValueOnce(session as any).mockResolvedValue({ ...session, principal_id: 'other' } as any);
  view = mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('权限或原请求身份已变化，工作输出已清除。');
  expect(screen.queryByText('原步进正文')).toBeNull();
});
it('retains a disconnected prefix and retries only the same original ID and cursor', async () => {
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('原步进正文');
  vi.mocked(api.coreWorkEvents).mockRejectedValueOnce(new Error('offline'));
  fireEvent.click(screen.getByRole('button', { name: '查询原工作输出' }));
  await screen.findByText('观测已断开，保留最近记录；请稍后查询同一原请求。');
  expect(screen.getByText('原步进正文')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: '查询原工作输出' }));
  await waitFor(() => expect(api.coreWorkEvents).toHaveBeenCalledTimes(3));
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  expect(api.coreWorkEvents).toHaveBeenLastCalledWith('au1', 'w1', 'w1#s1', 1, expect.any(AbortSignal));
  expect(screen.getAllByText('原步进正文')).toHaveLength(1);
});
it('clears on a changed projection and ignores an already pending late response', async () => {
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('原步进正文');
  let finish!: (value: any) => void;
  vi.mocked(api.coreWorkEvents).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  fireEvent.click(screen.getByRole('button', { name: '查询原工作输出' }));
  await waitFor(() => expect(api.coreWorkEvents).toHaveBeenCalledTimes(2));
  work.works[0].steps[0].can_observe = false;
  fireEvent.click(screen.getByRole('button', { name: '刷新 AI 工作' }));
  await screen.findByText('原调用或读取资格已变化，输出已清除。请核对原工作记录。');
  finish(result([{seq: 1, type: 'text_delta', text: '迟到私有正文'}]));
  await waitFor(() => expect(screen.queryByText('原步进正文')).toBeNull());
  expect(screen.queryByText('迟到私有正文')).toBeNull();
});
it('does not silently select a later model request when the selected step disappears', async () => {
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('原步进正文');
  work.works[0].steps = [{ ...step, step_ref: 'w1#s2', model_request_id: 'new-model' }];
  fireEvent.click(screen.getByRole('button', { name: '刷新 AI 工作' }));
  await screen.findByText('原调用或读取资格已变化，输出已清除。请核对原工作记录。');
  expect(api.coreWorkEvents).toHaveBeenCalledTimes(1);
});
it('continues checking read permission after terminal output', async () => {
  mount(); fireEvent.click(await screen.findByRole('button', { name: '查看工作输出' }));
  await screen.findByText('原步进正文');
  vi.mocked(api.coreWorkEvents).mockRejectedValue(new ApiError('revoked',403,'not_authorized'));
  await screen.findByText('权限或原请求身份已变化，工作输出已清除。', {}, { timeout: 4500 });
  expect(screen.queryByText('原步进正文')).toBeNull();
});
