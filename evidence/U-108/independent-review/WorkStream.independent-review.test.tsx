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
  has_more: false, events_complete: false, truncated });
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
