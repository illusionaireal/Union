import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '../../api/client';
import { WorkStream } from './WorkStream';

// Independent review of PR50@8bcf5da, current codex-home duty session.
// The implementation remains unchanged. No real models, timers or network.
vi.mock('../../api/client', async original => ({
  ...(await original<typeof import('../../api/client')>()),
  api: { session: vi.fn(), coreWorkEvents: vi.fn(), coreWorkCommand: vi.fn() },
}));
const scope = { principalId: 'review-p', serviceInstance: 'review-service', organizationId: 'review-au', workId: 'review-work' };
const connection = { id: 'review-connection', revision: 1, profile: 'openai_compatible', model: 'review-model',
  grant_ref: 'review-grant', grant_revision: 1, max_output_tokens: 100 };
const step = { step_ref: 'review-work#s1', attempt_id: 'review-work#a1', command_id: 'review-command',
  model_request_id: 'review-model-request', connection, can_observe: true };
const prefix = 'private-prefix-for-current-governor';
const page = (truncated = false) => ({ protocol: 'core.work-events.v1', organization_id: scope.organizationId,
  work_id: scope.workId, ...step, access: { principal_id: scope.principalId, service_instance: scope.serviceInstance },
  version: 5, source: 'persisted_modeld_events', state: 'completed',
  events: [{ seq: 1, type: 'text_delta', text: prefix }], cursor: 1, last_seq: 1,
  has_more: false, events_complete: false, truncated, authorization_only: false });
beforeEach(() => {
  vi.useFakeTimers(); vi.resetAllMocks();
  vi.mocked(api.session).mockResolvedValue({ core_protocol: 'core.au.v1', principal_id: scope.principalId,
    service_instance: scope.serviceInstance } as any);
});
afterEach(() => { cleanup(); vi.useRealTimers(); });
async function open(value: any) {
  vi.mocked(api.coreWorkEvents).mockResolvedValue(value);
  render(<WorkStream item={{ id: scope.workId, steps: [step] } as any} scope={scope} />);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: '查看工作输出' })); });
  expect(screen.getByText(prefix)).toBeVisible();
}
it('control: terminal output is cleared after remote authorization revocation', async () => {
  await open(page(false));
  vi.mocked(api.coreWorkEvents).mockRejectedValue(new ApiError('revoked', 403, 'not_authorized'));
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(screen.queryByText(prefix)).toBeNull();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});
it('truncated terminal output must still be cleared after remote authorization revocation', async () => {
  await open(page(true));
  vi.mocked(api.coreWorkEvents).mockRejectedValue(new ApiError('revoked', 403, 'not_authorized'));
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(screen.queryByText(prefix)).toBeNull();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});
it('truncated terminal output must still revalidate an expired session', async () => {
  await open(page(true));
  vi.mocked(api.session).mockRejectedValue(new ApiError('expired', 401, 'not_authenticated'));
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(screen.queryByText(prefix)).toBeNull();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('metadata recovery never resumes event loading and still clears after later revocation', async () => {
  await open(page(true));
  vi.mocked(api.coreWorkEvents).mockRejectedValueOnce(new ApiError('offline', 503, 'storage_unavailable'))
    .mockResolvedValueOnce({ ...page(false), events: [], authorization_only: true } as any)
    .mockRejectedValue(new ApiError('revoked', 403, 'not_authorized'));
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  expect(screen.getByText(prefix)).toBeVisible();
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  expect(screen.getByText(prefix)).toBeVisible();
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  expect(screen.queryByText(prefix)).toBeNull();
  const calls = vi.mocked(api.coreWorkEvents).mock.calls.slice(1);
  expect(calls).toHaveLength(3);
  expect(calls.every(call => call[3] === 1 && call[5] === true)).toBe(true);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('a pending metadata response cannot restore text after session expiry', async () => {
  await open(page(true));
  let finish!: (value: any) => void;
  vi.mocked(api.coreWorkEvents).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
  expect(finish).toBeTypeOf('function');
  vi.mocked(api.session).mockRejectedValue(new ApiError('expired', 401, 'not_authenticated'));
  await act(async () => { finish({ ...page(false), events: [], authorization_only: true }); });
  expect(screen.queryByText(prefix)).toBeNull();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it.each(['attempt_id', 'command_id', 'connection'])('changing the original %s never follows a reused step ref', async field => {
  vi.mocked(api.coreWorkEvents).mockResolvedValue(page(false) as any);
  const item = { id: scope.workId, steps: [structuredClone(step)] };
  const view = render(<WorkStream item={item as any} scope={scope} />);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: '查看工作输出' })); });
  expect(screen.getByText(prefix)).toBeVisible();
  const changed = { ...step, [field]: field === 'connection' ? { ...connection, grant_revision: 2 } : 'replacement' };
  view.rerender(<WorkStream item={{ ...item, steps: [changed] } as any} scope={scope} />);
  expect(screen.queryByText(prefix)).toBeNull();
  expect(screen.getByText('原调用或读取资格已变化，输出已清除。请核对原工作记录。')).toBeVisible();
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(api.coreWorkEvents).toHaveBeenCalledTimes(1);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});
