import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

// Compose actual driver fragments. Do not import its real main or supply an
// invented outputObservation to the cancellation side of the boundary.
const require = createRequire(new URL('../scripts/exit22b_page.cjs', import.meta.url));
const source = readFileSync(new URL('../scripts/exit22b_page.cjs', import.meta.url), 'utf8');
function fragment(start: string, end: string) {
  assert.equal(source.split(start).length, 2);
  const begin = source.indexOf(start), finish = source.indexOf(end, begin);
  assert.ok(finish > begin);
  return source.slice(begin, finish);
}
const gate = fragment('  // Original-output acceptance gate.',
  "  check('in-flight automatic reservation carries the line-end id: ");
const cancel = fragment('  // Same-run original GET must return', '  // on the race with the real model');
const restart = fragment('  const restartComparison =', "  fs.writeFileSync(path.join(output, 'checks.json')");
const session = { core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-original' };
const connection = { id: 'connection-original', revision: 1, profile: 'modeld_grant', model: 'fake',
  grant_ref: 'grant-original', grant_revision: 1, max_output_tokens: 100, task_ms: 30000 };
const step = { step_ref: 'work-original#s1', attempt_id: 'attempt-original', command_id: 'loop-original-t1',
  model_request_id: 'request-original', connection };
const receipt = { id: 'cancel-original', organization_id: 'au-original', kind: 'cancel_step',
  base_version: 10, version: 11, actor_principal_id: session.principal_id, status: 'succeeded', effect: 'applied',
  step: { step_ref: step.step_ref, model_request_id: step.model_request_id, status: 'reserved' },
  model_request_id: step.model_request_id, cancel_connection: connection, cancel_accepted: true,
  message: 'delivered', delivery: { cancel_accepted: true, message: 'delivered' } };
const work = { protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
  access: { principal_id: session.principal_id }, works: [{ id: 'work-original', results: [],
    steps: [{ ...step, status: 'unknown', usage: null, cost_status: 'unknown', reason: 'interrupted' }],
    budget: { max_calls: 1, used: 0, reserved: 1 } }] };
const text = '原请求输出🔎';

async function run(options: { nextPrincipal?: string; lateService?: string; replacedReceipt?: boolean } = {}) {
  let outputSaved = false, reopened = false, receiptSessionReads = 0, eventReads = 0;
  const files = new Map<string, any>(), gets: string[] = [];
  const context: any = {
    require, URL, URLSearchParams, TextEncoder, crypto: { createHash },
    createdReceipt: { organization_id: 'au-original' }, workId: 'work-original', inflight: structuredClone(step),
    cancelCommandId: receipt.id, cancelOutcome: { status: 200, receipt: structuredClone(receipt) },
    before: structuredClone(work), after: structuredClone(work),
    output: '/synthetic', path: { join: (...parts: string[]) => parts.join('/') },
    fs: { writeFileSync: (name: string, value: string) => {
      files.set(name.split('/').at(-1)!, JSON.parse(value));
      if (name.endsWith('original-output-observation.json')) outputSaved = true;
    } },
    coreWork: async () => structuredClone(work),
    check: (name: string, value: unknown = true) => assert.ok(value, name),
    waitFor: async (predicate: () => Promise<boolean>) => {
      for (let i = 0; i < 3; i++) if (await predicate()) return;
      throw Error('output timeout');
    },
    page: { evaluate: async (fn: (arg: unknown) => unknown, arg: unknown) =>
      vm.runInNewContext('(' + fn.toString() + ')(__arg)', { ...context, __arg: arg }) },
    fetch: async (url: string, init?: { method?: string }) => {
      assert.ok(!init?.method || init.method === 'GET', 'observation must never dispatch or cancel');
      gets.push(url);
      if (url === '/api/session') {
        if (outputSaved) receiptSessionReads++;
        return { status: 200, json: async () => ({ ...session,
          ...(reopened ? { service_instance: 'service-reopened' } : {}),
          ...(outputSaved && options.nextPrincipal ? { principal_id: options.nextPrincipal } : {}),
          ...(outputSaved && receiptSessionReads === 2 && options.lateService
            ? { service_instance: options.lateService } : {}) }) };
      }
      const parsed = new URL(url, 'http://synthetic.invalid');
      assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
      if (parsed.pathname === '/api/v1/work/events') {
        assert.equal(parsed.searchParams.get('work_id'), 'work-original');
        assert.equal(parsed.searchParams.get('step_ref'), step.step_ref);
        assert.equal(parsed.searchParams.get('after'), eventReads ? '1' : '0');
        eventReads++;
        return { status: 200, json: async () => ({ protocol: 'core.work-events.v1',
          source: 'persisted_modeld_events', organization_id: 'au-original', work_id: 'work-original',
          ...structuredClone(step), version: 12, access: { principal_id: session.principal_id,
            service_instance: session.service_instance }, authorization_only: false,
          cursor: eventReads, last_seq: eventReads, has_more: eventReads === 1,
          events: eventReads === 1 ? [] : [{ seq: 2, type: 'text_delta', text }] }) };
      }
      if (parsed.pathname === '/api/v1/work') return { status: 200, json: async () => structuredClone(work) };
      assert.equal(parsed.pathname, '/api/v1/governance/receipts');
      assert.equal(parsed.searchParams.get('id'), receipt.id);
      return { status: 200, json: async () => ({ receipt: { ...structuredClone(receipt),
        ...(reopened && options.replacedReceipt ? { id: 'other-cancel' } : {}) } }) };
    },
    reopen: () => { reopened = true; receiptSessionReads = 0; },
  };
  await vm.runInNewContext('(async () => {' + gate + cancel + '\nreopen();\n' + restart + '\n})()', context);
  return { files, gets };
}

test('actual observed reader survives original cancel GET and service restart without new POST', async () => {
  const { files, gets } = await run();
  const observed = files.get('original-output-observation.json');
  assert.equal(observed.principal_id, session.principal_id);
  assert.equal(observed.service_instance, session.service_instance);
  assert.equal(observed.model_request_id, step.model_request_id);
  assert.equal(observed.text_bytes, Buffer.byteLength(text));
  assert.equal(observed.text_sha256, createHash('sha256').update(text).digest('hex'));
  assert.ok(!JSON.stringify(observed).includes(text));
  assert.equal(files.get('cancel-receipt-before-restart.json').reference.principal_id, observed.principal_id);
  assert.deepEqual(files.get('cancel-receipt-after-restart.json').receipt, receipt);
  assert.equal(files.get('cancel-receipt-after-restart.json').service_instance, 'service-reopened');
  assert.equal(gets.filter(url => url.startsWith('/api/v1/governance/receipts')).length, 2);
  assert.equal(files.get('restart-request-comparison.json').budget.reserved, 1);
});

test('reader change after output cannot replace the original principal for cancel recovery', async () => {
  await assert.rejects(run({ nextPrincipal: 'principal-other' }), { name: 'AssertionError', message: /original cancel principal/ });
});
test('service change during the downstream read is still rejected', async () => {
  await assert.rejects(run({ lateService: 'service-other' }), { name: 'AssertionError', message: /service changed during cancel read/ });
});
test('composed restart still rejects a substituted original receipt', async () => {
  await assert.rejects(run({ replacedReceipt: true }), { name: 'AssertionError', message: /original cancel receipt id/ });
});
