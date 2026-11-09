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
const settlement = fragment('  // on the race with the real model', '  const before = await snapshot();');
const restart = fragment('  const after = await snapshot();', "  fs.writeFileSync(path.join(output, 'checks.json')");
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
  access: { principal_id: session.principal_id }, works: [{ id: 'work-original',
    steps: [{ ...step, status: 'unknown', usage: null, cost_status: 'unknown', reason: 'interrupted' }],
    budget: { max_calls: 1, used: 0, reserved: 1 } }] };
const text = '原请求输出🔎';

async function run(options: { status?: string; reserved?: number; afterStatus?: string; otherReleased?: boolean; noOutput?: boolean } = {}) {
  const persisted = structuredClone(work);
  if (options.status) persisted.works[0].steps[0].status = options.status;
  persisted.works[0].budget.used = options.status === 'used' ? 1 : 0;
  persisted.works[0].budget.reserved = options.reserved ?? (options.status && options.status !== 'unknown' ? 0 : 1);
  if (options.otherReleased) persisted.works[0].steps.push({ ...structuredClone(persisted.works[0].steps[0]), step_ref: 'work-original#s2', model_request_id: 'never-executed', status: 'released', reason: 'not dispatched' });
  let reopened = false, eventReads = 0;
  const files = new Map<string, any>(), gets: string[] = [];
  const context: any = {
    require, URL, URLSearchParams, TextEncoder, crypto: { createHash },
    createdReceipt: { organization_id: 'au-original' }, workId: 'work-original', inflight: structuredClone(step),
    cancelCommandId: receipt.id, cancelOutcome: { status: 200, receipt: structuredClone(receipt) },

    output: '/synthetic', path: { join: (...parts: string[]) => parts.join('/') },
    fs: { writeFileSync: (name: string, value: string) => {
      files.set(name.split('/').at(-1)!, JSON.parse(value));
    } },
    coreWork: async () => structuredClone(persisted),
    snapshot: async () => require('./exit22-restart-evidence.cjs').readSnapshot(context.page, 'au-original', 'work-original'),
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
        return { status: 200, json: async () => ({ ...session,
          ...(reopened ? { service_instance: 'service-reopened' } : {})
        }) };
      }
      const parsed = new URL(url, 'http://synthetic.invalid');
      assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
      if (parsed.pathname === '/api/v1/work/events') {
        assert.equal(parsed.searchParams.get('work_id'), 'work-original');
        assert.equal(parsed.searchParams.get('step_ref'), step.step_ref);
        assert.equal(parsed.searchParams.get('after'), String(eventReads));
        eventReads++;
        return { status: 200, json: async () => ({ protocol: 'core.work-events.v1',
          source: 'persisted_modeld_events', organization_id: 'au-original', work_id: 'work-original',
          ...structuredClone(step), version: 12, access: { principal_id: session.principal_id,
            service_instance: session.service_instance }, authorization_only: false,
          cursor: eventReads, last_seq: eventReads, has_more: eventReads === 1,
          events: options.noOutput || eventReads === 1 ? [] : [{ seq: 2, type: 'text_delta', text }]        }) };
      }
      if (parsed.pathname === '/api/v1/work') return { status: 200, json: async () => { const value = structuredClone(persisted); if (reopened && options.afterStatus) value.works[0].steps[0].status = options.afterStatus; return value; } };
      assert.equal(parsed.pathname, '/api/v1/governance/receipts');
      assert.equal(parsed.searchParams.get('id'), receipt.id);
      return { status: 200, json: async () => ({ receipt: structuredClone(receipt)        }) };
    },
    reopen: () => { reopened = true; },
  };
  await vm.runInNewContext('(async () => {' + gate + cancel + settlement + '\nconst before = await snapshot(); reopen();\n' + restart + '\n})()', context);
  return { files, gets };
}

test('observed interrupt: unknown keeps the original reservation and null usage', async () => {
  const { files } = await run();
  assert.ok(files.get('original-output-observation.json').text_bytes > 0);
  const fact = files.get('restart-request-comparison.json');
  assert.equal(fact.budget.reserved, 1);
  assert.equal(fact.requests[0].usage, null);
});
test('observed interrupt: completed call keeps used occupancy with unreported usage', async () => {
  const { files } = await run({ status: 'used' });
  assert.equal(files.get('restart-request-comparison.json').budget.used, 1);
  assert.equal(files.get('restart-request-comparison.json').requests[0].usage, null);
});
test('observed interrupt: released original call is rejected even when both snapshots agree', async () => {
  await assert.rejects(run({ status: 'released' }), /step settled as released/);
});
test('observed interrupt: retaining a budget does not legitimize a released original call', async () => {
  await assert.rejects(run({ status: 'released', reserved: 1 }), /step settled as released/);
});
test('observed interrupt: unknown still requires its reservation', async () => {
  await assert.rejects(run({ reserved: 0 }), /unknown settlement keeps/);
});
test('observed interrupt: reopened original call cannot become released', async () => {
  await assert.rejects(run({ afterStatus: 'released' }), /settled step survives the rebuild as released|restart preserves every original request fact|original budget retains every unknown reservation/);
});
test('observed interrupt: a different unexecuted released step does not invalidate the original call', async () => {
  const { files } = await run({ otherReleased: true });
  assert.equal(files.get('restart-request-comparison.json').requests.length, 2);
});
test('observed interrupt: absent original output cannot reach settlement acceptance', async () => {
  await assert.rejects(run({ noOutput: true }), /output timeout/);
});
