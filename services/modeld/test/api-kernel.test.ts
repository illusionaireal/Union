import { expect, test } from 'bun:test';
import { join } from 'node:path';

test('independent API profile uses the pinned single-stream kernel over actual loopback HTTP', async () => {
  const child = Bun.spawn([process.execPath, join(import.meta.dir, 'fixtures/api-kernel-probe.ts')], { stdout: 'pipe', stderr: 'pipe' });
  const [stdout, stderr, code] = await Promise.all([new Response(child.stdout).text(), new Response(child.stderr).text(), child.exited]);
  if (code) throw new Error(stdout + stderr);
  const result = JSON.parse(stdout.trim().split('\n').at(-1)!);
  expect(result.real_model_calls).toBe(0);
  expect(result.account_config_requests).toBe(0);
  expect(result.tool_roundtrip).toBe(true);
  expect(result.native_scope_and_signature).toBe(true);
  expect(result.unsupported_capabilities_rejected).toBe(true);
  expect(result.no_automatic_retry).toBe(true);
  expect(result.known_usage_survives_cancel).toBe(true);
}, 30000);
