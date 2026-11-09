import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

const require = createRequire(new URL('../scripts/exit22b_page.cjs', import.meta.url));
const source = readFileSync(new URL('../scripts/exit22b_page.cjs', import.meta.url), 'utf8');
const start = source.indexOf('  // Same-run original GET must return');
const end = source.indexOf('  // on the race with the real model', start);
assert.ok(start >= 0 && end > start);
const originalGet = source.slice(start, end);
const restartStart = source.indexOf('  const restartComparison =');
const restartEnd = source.indexOf("  fs.writeFileSync(path.join(output, 'checks.json')", restartStart);
const restartGet = source.slice(restartStart, restartEnd);

const session = { core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-original' };
const connection = { id: 'connection-original', revision: 1, profile: 'modeld_grant', model: 'fake' };
const inflight = { step_ref: 'step-original', attempt_id: 'attempt-original', command_id: 'loop-original-t1',
  model_request_id: 'model-original', connection };
const receipt = { id: 'cancel-original', organization_id: 'au-original', kind: 'cancel_step',
  base_version: 10, version: 11, actor_principal_id: session.principal_id, status: 'succeeded', effect: 'applied',
  step: { step_ref: inflight.step_ref, model_request_id: inflight.model_request_id,
    status: 'reserved', cancel_requested_at: '2026-11-09T08:00:00Z' },
  model_request_id: inflight.model_request_id, cancel_connection: connection, cancel_accepted: true,
  message: 'delivered', delivery: { cancel_accepted: true, message: 'delivered' } };
const work = { protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
  access: { principal_id: session.principal_id }, works: [{ id: 'work-original',
    steps: [{ ...inflight, status: 'unknown', usage: null, cost_status: 'unknown', reason: 'interrupted' }],
    budget: { max_calls: 1, used: 0, reserved: 1 } }] };

type Options = { status?: number; receipt?: any; work?: any; session?: any; lateSession?: any;
  restart?: boolean; afterReceipt?: any; afterStatus?: number };
async function run(options: Options = {}) {
  let restarted = false, sessionReads = 0;
  const gets: string[] = [], files = new Map<string, any>();
  const context: any = {
    require, assert, URLSearchParams, crypto: { randomUUID: () => { throw Error('no new identity'); } },
    createdReceipt: { organization_id: 'au-original' }, workId: 'work-original',
    inflight: structuredClone(inflight), cancelCommandId: 'cancel-original',
    outputSession: structuredClone(session), outputObservation: { principal_id: session.principal_id },
    cancelOutcome: { status: 200, receipt: structuredClone(receipt) }, cancelReceipt: structuredClone(receipt),
    before: structuredClone(work), after: structuredClone(work),
    output: '/synthetic', path: { join: (...parts: string[]) => parts.join('/') },
    fs: { writeFileSync: (name: string, text: string) => files.set(name.split('/').at(-1)!, JSON.parse(text)) },
    check: (name: string, value: unknown = true) => assert.ok(value, name),
    page: { evaluate: async (fn: (arg: unknown) => unknown, arg: unknown) =>
      vm.runInNewContext('(' + fn.toString() + ')(__arg)', { ...context, __arg: arg }) },
    fetch: async (url: string, init?: { method?: string }) => {
      assert.ok(!init?.method || init.method === 'GET', 'evidence cannot cancel or dispatch');
      gets.push(url);
      if (url === '/api/session') {
        sessionReads++;
        return { status: 200, json: async () => ({ ...session,
          ...(restarted ? { service_instance: 'service-reopened' } : {}), ...options.session,
          ...(sessionReads % 2 === 0 ? options.lateSession : {}) }) };
      }
      const parsed = new URL(url, 'http://synthetic.invalid');
      assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
      if (parsed.pathname === '/api/v1/work') return { status: 200, json: async () => structuredClone(options.work ?? work) };
      assert.equal(parsed.pathname, '/api/v1/governance/receipts');
      assert.equal(parsed.searchParams.get('id'), 'cancel-original');
      return { status: restarted ? options.afterStatus ?? 200 : options.status ?? 200,
        json: async () => ({ receipt: structuredClone(restarted ? options.afterReceipt ?? receipt : options.receipt ?? receipt) }) };
    },
    reopen: () => { restarted = true; sessionReads = 0; },
  };
  await vm.runInNewContext('(async () => {' + originalGet +
    (options.restart ? '\nreopen();\n' + restartGet : '') + '\n})()', context, { timeout: 1000 });
  return { gets, files };
}

test('original delivered cancel GET succeeds without any new command', async () => { await run(); });
test('cancel GET must validate HTTP status even when its body looks successful', async t => {
  for (const status of [401, 403, 404, 409, 500]) await t.test(String(status), () => assert.rejects(run({ status })));
});
test('cancel GET must bind the complete original receipt', async t => {
  const changes: [string, (r: any) => void][] = [
    ['another AU', r => { r.organization_id = 'another-au'; }],
    ['another actor', r => { r.actor_principal_id = 'another-principal'; }],
    ['another kind', r => { r.kind = 'run_loop'; }],
    ['rejected command', r => { r.status = 'rejected'; r.effect = 'none'; }],
    ['another step', r => { r.step.step_ref = 'another-step'; }],
    ['another step request', r => { r.step.model_request_id = 'another-model'; }],
    ['wrong original connection', r => { r.cancel_connection.revision = 2; }],
    ['missing delivery', r => { delete r.delivery; }],
    ['different delivery', r => { r.delivery.cancel_accepted = false; }],
    ['invalid version', r => { r.version = null; }],
    ['changed persisted receipt', r => { r.message = 'substituted'; }],
  ];
  for (const [name, change] of changes) await t.test(name, async () => {
    const value = structuredClone(receipt); change(value); await assert.rejects(run({ receipt: value }));
  });
});
test('receipt step must resolve to the original Work and attempt', async t => {
  const changes: [string, (r: any) => void][] = [
    ['missing Work', r => { r.works = []; }],
    ['wrong Work', r => { r.works[0].id = 'another-work'; }],
    ['missing step', r => { r.works[0].steps = []; }],
    ['duplicate step', r => { r.works[0].steps.push(structuredClone(r.works[0].steps[0])); }],
    ['wrong attempt', r => { r.works[0].steps[0].attempt_id = 'another-attempt'; }],
    ['wrong step command', r => { r.works[0].steps[0].command_id = 'another-command'; }],
    ['wrong current principal', r => { r.access.principal_id = 'another-principal'; }],
  ];
  for (const [name, change] of changes) await t.test(name, async () => {
    const value = structuredClone(work); change(value); await assert.rejects(run({ work: value }));
  });
});
test('current session and service are checked around the receipt read', async t => {
  for (const [name, options] of [
    ['another principal', { session: { principal_id: 'another-principal' } }],
    ['principal changes', { lateSession: { principal_id: 'another-principal' } }],
    ['service changes', { lateSession: { service_instance: 'another-service' } }],
  ] as const) await t.test(name, () => assert.rejects(run(options)));
});
test('restart re-queries the same cancel and preserves its receipt when service changes', async () => {
  const result = await run({ restart: true });
  assert.equal(result.gets.filter(url => url.startsWith('/api/v1/governance/receipts')).length, 2);
  assert.equal(result.files.get('cancel-receipt-after-restart.json')?.receipt.id, 'cancel-original');
});
test('restart cannot pass if the original cancel receipt disappears', async () => {
  await assert.rejects(run({ restart: true, afterStatus: 403 }));
});
test('restart cannot pass if the original receipt is replaced', async () => {
  await assert.rejects(run({ restart: true, afterReceipt: { ...receipt, id: 'another-cancel' } }));
});
