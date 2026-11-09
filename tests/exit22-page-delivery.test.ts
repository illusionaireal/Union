import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

// Run the actual driver action block, never the main that connects real models.
const source = readFileSync(new URL('../scripts/exit22c_download.cjs', import.meta.url), 'utf8');
const marker = "  check('downloaded title is the recorded title', meta.title === recordedTitle);";
assert.equal(source.split(marker).length, 2);
const start = source.indexOf(marker) + marker.length;
const end = source.indexOf('  const before = await snapshot();', start);
assert.ok(end > start);
const action = source.slice(start, end);

type Options = { missingAdopt?: boolean; runningAttempt?: boolean; adoptedOnly?: boolean;
  wrongResult?: boolean; changedPrincipal?: boolean; changedSources?: boolean };
async function run(options: Options = {}) {
  const calls: any[] = [], clicks: string[] = [], files = new Map();
  const listeners = new Set<(request: any) => void>();
  const result = { id: 'result-original', status: 'candidate', sha256: 'a'.repeat(64), sources: ['brief.md'] };
  const work: any = { id: 'work-original', status: 'running', results: [result],
    attempts: [{id: 'attempt-original', status: 'running'}], steps: [] };
  const snapshot = () => ({ protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
    access: { principal_id: options.changedPrincipal && calls.length ? 'other' : 'principal-original' },
    works: [{id: 'work-other', status: 'delivered', results: []}, structuredClone(work)] });
  function execute(kind: string, data: any, ui: boolean) {
    const command = { id: 'command-' + calls.length, organization_id: 'au-original', kind, data };
    calls.push({ ...command, ui });
    for (const listener of listeners) listener({ url: () => 'http://localhost/api/v1/work/commands',
      method: () => 'POST', postDataJSON: () => command });
    if (kind === 'adopt_result') {
      result.status = 'adopted';
      work.attempts[0].status = options.runningAttempt ? 'running' : 'closed';
    }
    if (kind === 'finish_attempt') work.attempts[0].status = 'closed';
    if (kind === 'deliver_work') {
      work.status = options.adoptedOnly ? 'running' : 'delivered';
      work.delivered_result_id = options.wrongResult ? 'result-other' : result.id;
      if (options.changedSources) result.sources = ['unrelated.md'];
    }
    return {receipt: {status: 'succeeded'}};
  }
  const context: any = {
    assert, URL, JSON, createdReceipt: { organization_id: 'au-original' },
    workId: work.id, resultId: result.id, recorded: result.sha256, recordedFull: structuredClone(result),
    output: '/synthetic', path: {join: (...parts: string[]) => parts.join('/')},
    fs: {writeFileSync: (name: string, body: string) => files.set(name, JSON.parse(body))},
    snapshot: async () => snapshot(), coreWork: async () => snapshot(),
    check: (name: string, value: any = true) => assert.ok(value, name),
    waitFor: async (predicate: () => Promise<boolean>, name: string) => {
      for (let n = 0; n < 2; n++) if (await predicate()) return;
      throw Error('timeout: ' + name);
    },
    fetch: async (url: string, init?: any) => ({json: async () => {
      if (init?.method === 'POST') {
        const c = JSON.parse(init.body); return execute(c.kind, c.data, false);
      }
      if (url.startsWith('/api/v1/aus/')) return { au: { version: 10 } };
      return snapshot();
    }}),
  };
  context.crypto = {randomUUID: () => 'api-command-' + calls.length};
  context.page = {
    on: (event: string, listener: any) => {assert.equal(event, 'request'); listeners.add(listener);},
    off: (event: string, listener: any) => {assert.equal(event, 'request'); listeners.delete(listener);},
    evaluate: (fn: any, arg: any) => vm.runInNewContext('(' + fn.toString() + ')(arg)', {...context, arg}),
    locator: (selector: string) => {
      assert.equal(selector, '[data-work="work-original"]');
      return {getByRole: (role: string, selection: any) => {
        assert.equal(role, 'region'); assert.equal(selection.name, '成果 result-original');
        assert.equal(selection.exact, true);
        return {getByRole: (role: string, button: any) => {
          assert.equal(role, 'button'); assert.equal(button.exact, true);
          return {click: async () => {
            if (button.name === '采用此成果') {
              if (options.missingAdopt) throw Error('adopt control unavailable');
              clicks.push(button.name); execute('adopt_result', {work_id: work.id, result_id: result.id}, true);
            } else {
              assert.equal(button.name, '交付此成果');
              if (work.attempts[0].status === 'running') throw Error('deliver control unavailable');
              clicks.push(button.name); execute('deliver_work', {work_id: work.id, result_id: result.id}, true);
            }
          }};
        }};
      }};
    },
  };
  let error;
  try { await vm.runInNewContext('(async () => {' + action + '})()', context); }
  catch (caught) {error = caught;}
  return {error, calls, clicks, files, listeners};
}

test('download acceptance uses both original Core result controls and records only their command IDs', async () => {
  const r = await run(); assert.ifError(r.error);
  assert.deepEqual(r.clicks, ['采用此成果', '交付此成果']);
  assert.deepEqual(r.calls.map(c => [c.kind,c.ui]), [['adopt_result',true], ['deliver_work',true]]);
  assert.equal(r.files.size, 1); assert.equal(r.listeners.size, 0);
});
test('missing adoption control cannot be bypassed with a successful direct API command', async () => {
  const r = await run({missingAdopt: true}); assert.ok(r.error);
  assert.equal(r.calls.length, 0); assert.equal(r.files.size, 0);
});
test('running attempt cannot be closed manually to make delivery acceptance pass', async () => {
  const r = await run({runningAttempt: true}); assert.ok(r.error);
  assert.deepEqual(r.calls.map(c => c.kind), ['adopt_result']); assert.equal(r.files.size, 0);
});
for (const [name, options] of Object.entries({
  'adopted is insufficient without delivery': {adoptedOnly: true},
  'another delivered result is rejected': {wrongResult: true},
  'changed principal is rejected': {changedPrincipal: true},
  'changed original sources are rejected': {changedSources: true},
})) test(name, async () => {
  const r = await run(options); assert.ok(r.error); assert.equal(r.files.size, 0);
});
