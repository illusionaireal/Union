import { test, expect } from 'bun:test';
import { join } from 'node:path';
test('pinned native kernel preserves account scope, refresh, tools and single-attempt HTTP boundaries', async () => {
  const child = Bun.spawn([process.execPath, join(import.meta.dir, 'fixtures/kernel-probe.ts')], { stdout:'pipe', stderr:'pipe' });
  const [stdout, stderr, code] = await Promise.all([new Response(child.stdout).text(), new Response(child.stderr).text(), child.exited]);
  if (code) throw new Error(stdout + stderr);
  const result = JSON.parse(stdout.trim().split('\n').at(-1)!);
  expect(result.real_model_calls).toBe(0);
  expect(result.first_event_timeout_enforced).toBe(true);
  expect(result.checks).toHaveLength(11);
  expect(result.oauth_refresh_requests).toBe(1);
}, 30000);
test('device authorization completes and persists the selected account exactly once', async () => {
  const child = Bun.spawn([process.execPath, join(import.meta.dir, 'fixtures/auth-probe.ts')], { stdout:'pipe', stderr:'pipe' });
  const [stdout, stderr, code] = await Promise.all([new Response(child.stdout).text(), new Response(child.stderr).text(), child.exited]);
  if (code) throw new Error(stdout + stderr);
  const result = JSON.parse(stdout.trim().split('\n').at(-1)!);
  expect(result.auth_completed).toBe(true);
  expect(result.token_requests).toBe(1);
  expect(result.real_model_calls).toBe(0);
}, 30000);
