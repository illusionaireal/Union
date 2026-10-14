import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, request } from './client';
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
describe('same-origin API client', () => {
  it('sends one command with the original ID and does not retry a rejected request', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: '版本冲突' }) });
    vi.stubGlobal('fetch', fetch);
    const command = {
      id: 'original-id',
      kind: 'pause' as const,
      organization_id: 'org',
      base_version: 2,
      data: {},
    };
    await expect(api.command(command)).rejects.toMatchObject({ status: 409, message: '版本冲突' });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][1]).toMatchObject({
      credentials: 'same-origin',
      cache: 'no-store',
      body: JSON.stringify(command),
    });
  });
  it('aborts a timed-out write and reports uncertainty without replay', async () => {
    vi.useFakeTimers();
    const fetch = vi.fn(
      (_path: string, init: RequestInit) =>
        new Promise((_resolve, reject) =>
          init.signal!.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          ),
        ),
    );
    vi.stubGlobal('fetch', fetch);
    const pending = request('/api/commands', { method: 'POST' });
    const assertion = expect(pending).rejects.toEqual(new ApiError('请求超时，请刷新或查询原回执'));
    await vi.advanceTimersByTimeAsync(5000);
    await assertion;
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('propagates Query cancellation to the actual request', async () => {
    const fetch = vi.fn(
      (_path: string, init: RequestInit) =>
        new Promise((_resolve, reject) =>
          init.signal!.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          ),
        ),
    );
    vi.stubGlobal('fetch', fetch);
    const controller = new AbortController();
    const pending = api.snapshot('org-1', 50, controller.signal);
    const assertion = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    controller.abort();
    await assertion;
    expect(fetch.mock.calls[0][0]).toBe('/api/snapshot?organization_id=org-1&offset=50');
  });
});
