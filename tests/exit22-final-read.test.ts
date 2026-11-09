import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

// Exact download restart code and the real snapshot helper, never driver main.
const requireDriver = createRequire(new URL('../scripts/exit22c_download.cjs', import.meta.url));
const source = readFileSync(new URL('../scripts/exit22c_download.cjs', import.meta.url), 'utf8');
function fragment(start: string, end: string) {
  assert.equal(source.split(start).length, 2);
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert.ok(b > a);
  return source.slice(a, b);
}
const snapshot = fragment('async function snapshot(', 'async function coreWork()');
const restart = fragment('  const before = await snapshot();', "  fs.writeFileSync(path.join(output, 'checks.json')");
const original = { protocol: 'core.work.v1', organization_id: 'au-original', version: 20,
  access: { principal_id: 'principal-original' }, works: [{ id: 'work-original', status: 'delivered',
    delivered_result_id: 'result-original', budget: { max_calls: 3, used: 1, reserved: 1 },
    results: [{ id: 'result-original', status: 'adopted', sha256: 'digest-original' }],
    steps: [{ step_ref: 'step-original', attempt_id: 'attempt-original', command_id: 'loop-original',
      model_request_id: 'model-original', status: 'unknown', usage: null, cost_status: 'unknown',
      reason: 'interrupted', connection: { id: 'connection-original', revision: 1 } },
      { step_ref: 'step-used', attempt_id: 'attempt-original', command_id: 'loop-completed',
        model_request_id: 'model-completed', status: 'used', usage: null, cost_status: 'unknown',
        reason: 'completed', connection: { id: 'connection-original', revision: 1 } }] }] };

async function observe(change?: 'principal' | 'service' | 'expired') {
  let workReads = 0, restarted = false, authenticated = true;
  let principal = 'principal-original', service = 'service-before';
  const saved = new Map<string, any>();
  const context: any = {
    require: requireDriver, assert, URLSearchParams,
    createdReceipt: { organization_id: 'au-original' }, workId: 'work-original',
    resultId: 'result-original', recorded: 'digest-original', output: '/synthetic',
    path: { join: (...parts: string[]) => parts.join('/') },
    fs: { writeFileSync: (name: string, body: string) => saved.set(name.split('/').at(-1)!, JSON.parse(body)) },
    check: (name: string, value: unknown = true) => assert.ok(value, name),
    host: { kill() {} }, running: { child: { once: (_: string, fn: () => void) => fn() } },
    startHost: async () => { restarted = true; service = 'service-after';
      return { origin: 'http://synthetic.invalid', child: {} }; },
    page: { goto: async () => {}, getByText: () => ({ waitFor: async () => {} }),
      evaluate: async (fn: (arg: unknown) => unknown, arg: unknown) =>
        vm.runInNewContext('(' + fn.toString() + ')(__arg)', { ...context, __arg: arg }) },
    fetch: async (url: string, init?: { method?: string }) => {
      assert.ok(!init?.method || init.method === 'GET', 'observation never writes or dispatches');
      if (url === '/api/session') return { status: authenticated ? 200 : 401, json: async () =>
        authenticated ? { core_protocol: 'core.au.v1', principal_id: principal, service_instance: service }
          : { error: 'not_authenticated' } };
      const parsed = new URL(url, 'http://synthetic.invalid');
      assert.equal(parsed.pathname, '/api/v1/work');
      assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
      workReads++;
      // The original body was authorized at GET entry; identity changes in flight.
      const body = structuredClone(original);
      if (restarted && workReads === 3) {
        if (change === 'principal') principal = 'another-principal';
        if (change === 'service') service = 'another-service';
        if (change === 'expired') authenticated = false;
      }
      return { status: 200, json: async () => body };
    },
  };
  let failure: any;
  try { await vm.runInNewContext(snapshot + '\n(async () => {' + restart + '\n})()', context, { timeout: 1000 }); }
  catch (error) { failure = error; }
  assert.equal(workReads, 3, 'exercise the actual final Work GET');
  return { saved, failure };
}

test('final download read preserves the original result and unknown usage after a stable restart', async () => {
  const { saved, failure } = await observe();
  assert.equal(failure, undefined);
  assert.deepEqual(saved.get('snapshot-after-restart.json'), original);
  assert.equal(saved.get('restart-request-comparison.json').requests[0].usage, null);
});
for (const change of ['principal', 'service', 'expired'] as const) {
  test('final download GET rejects in-flight ' + change + ' before saving success', async () => {
    const { saved, failure } = await observe(change);
    assert.equal(failure?.name, 'AssertionError', 'must reject authorization change, not fail in the harness');
    assert.ok(saved.has('snapshot-before-restart.json'), 'retain the valid before observation');
    assert.ok(!saved.has('snapshot-after-restart.json'), 'do not save an unverified final body');
    assert.ok(!saved.has('restart-request-comparison.json'), 'do not claim successful recovery');
  });
}
