import { afterEach, expect, it, vi } from 'vitest';
import { api } from './client';
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
it('a long work loop is not aborted by the five-second read timeout and is never retried', async () => {
  vi.useFakeTimers();
  let finish!: (value: Response) => void;
  let signal: AbortSignal;
  const fetch = vi.fn((_url, init) => {
    signal = init.signal;
    return new Promise<Response>((r) => {
      finish = r;
    });
  });
  vi.stubGlobal('fetch', fetch);
  const result = api.coreWorkCommand({ kind: 'run_loop', id: 'original' });
  await vi.advanceTimersByTimeAsync(30000);
  expect(signal!.aborted).toBe(false);
  expect(fetch).toHaveBeenCalledTimes(1);
  finish(new Response(JSON.stringify({ receipt: { id: 'original', status: 'succeeded' } })));
  expect((await result).receipt.id).toBe('original');
});
