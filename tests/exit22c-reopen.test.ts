import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Execute the real driver's restart assertions, never its model/browser main.
const source = readFileSync(new URL('../scripts/exit22c_download.cjs', import.meta.url), 'utf8');
const start = '  const authenticatedAfter = await snapshot();';
const end = "  // Restart request conservation.";
assert.equal(source.split(start).length, 2);
assert.equal(source.split(end).length, 2);
const block = source.slice(source.indexOf(start), source.indexOf(end));
const original = {
  protocol: 'core.work.v1', organization_id: 'original-au', version: 0,
  access: { principal_id: 'p1' },
  works: [{ id: 'original-work', status: 'delivered', delivered_result_id: 'original-result',
    steps: [{ step_ref: 'original-work#s1', attempt_id: 'original-work#a1', command_id: 'c1',
      model_request_id: 'r1', status: 'unknown', usage: null, cost_status: 'unknown',
      reason: 'keep', connection: 'original-connection' }],
    results: [{ id: 'original-result', status: 'adopted', sha256: 'original-digest' }] }],
};

async function reopen(body: typeof original, status = 200) {
  let reads = 0;
  const session = { core_protocol: 'core.au.v1', principal_id: 'p1', service_instance: 's1' };
  const context = {
    workId: 'original-work', resultId: 'original-result', recorded: 'original-digest',
    createdReceipt: { organization_id: 'original-au' },
    page: { evaluate: async (fn: (id: string) => unknown, arg: string) => fn(arg) },
    fetch: async (url: string) => {
      reads++;
      if (url === '/api/session') return { status: 200, json: async () => session };
      return { status, json: async () => body };
    },
    check: (name: string, value: unknown = true) => assert.ok(value, name),
    snapshot: async () => {
      const session = { core_protocol: 'core.au.v1', principal_id: 'p1', service_instance: 's1' };
      const workRead = { status, body };
      assert.equal(workRead.status, 200, 'Core Work snapshot HTTP status');
      assert.equal(workRead.body?.protocol, 'core.work.v1', 'protocol');
      assert.equal(workRead.body.organization_id, 'original-au', 'original AU snapshot');
      assert.equal(workRead.body.access?.principal_id, 'p1', 'snapshot principal');
      return workRead.body;
    },
  };
  await vm.runInNewContext('(async () => {' + block + '\n})()', context, { timeout: 1000 });
}

test('download reopen keeps the original result even beside another adopted result', async () => {
  const body = structuredClone(original);
  body.works[0].results.unshift({ id: 'another-result', status: 'adopted', sha256: 'another-digest' });
  await reopen(body);
});

test('download reopen rejects substituted identity, digest, status, scope and HTTP failures', async t => {
  const cases: [string, (body: typeof original) => void, number?][] = [
    ['another result', body => { body.works[0].results[0].id = 'another-result'; }],
    ['changed digest', body => { body.works[0].results[0].sha256 = 'another-digest'; }],
    ['another delivered result', body => { body.works[0].delivered_result_id = 'another-result'; }],
    ['not adopted', body => { body.works[0].results[0].status = 'candidate'; }],
    ['not delivered', body => { body.works[0].status = 'running'; }],
    ['missing original work', body => { body.works = []; }],
    ['another AU', body => { body.organization_id = 'another-au'; }],
    ['wrong protocol', body => { body.protocol = 'error.v1'; }],
    ['HTTP 403 with a matching body', () => {}, 403],
  ];
  for (const [name, change, status] of cases) {
    await t.test(name, async () => {
      const body = structuredClone(original);
      change(body);
      await assert.rejects(reopen(body, status), { name: 'AssertionError' });
    });
  }
});
