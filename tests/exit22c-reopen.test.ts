import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Execute the real driver's restart assertions, never its model/browser main.
const source = readFileSync(new URL('../scripts/exit22c_download.cjs', import.meta.url), 'utf8');
const start = '  const reopenedResponse = await page.evaluate(async auId => {';
const end = "  // Restart request conservation.";
assert.equal(source.split(start).length, 2);
assert.equal(source.split(end).length, 2);
const block = source.slice(source.indexOf(start), source.indexOf(end));
const original = {
  protocol: 'core.work.v1', organization_id: 'original-au',
  works: [{ id: 'original-work', status: 'delivered', delivered_result_id: 'original-result',
    results: [{ id: 'original-result', status: 'adopted', sha256: 'original-digest' }] }],
};

async function reopen(body: typeof original, status = 200) {
  let reads = 0;
  const context = {
    workId: 'original-work', resultId: 'original-result', recorded: 'original-digest',
    createdReceipt: { organization_id: 'original-au' },
    page: { evaluate: async (fn: (id: string) => unknown, arg: string) => fn(arg) },
    fetch: async () => { reads++; return { status, json: async () => body }; },
    check: (name: string, value: unknown = true) => assert.ok(value, name),
  };
  await vm.runInNewContext('(async () => {' + block + '\n})()', context, { timeout: 1000 });
  assert.equal(reads, 1);
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
