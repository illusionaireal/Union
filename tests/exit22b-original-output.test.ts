import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Execute only the driver's original-output gate. Never import its real main.
const source = readFileSync(new URL('../scripts/exit22b_page.cjs', import.meta.url), 'utf8');
const oldStart = '  const workEventsCapable = await page.evaluate(';
const newStart = '  // Original-output acceptance gate.';
const start = source.includes(newStart) ? newStart : oldStart;
const end = "  check('in-flight automatic reservation carries the line-end id: ";
assert.equal(source.split(start).length, 2);
assert.equal(source.split(end).length, 2);
const block = source.slice(source.indexOf(start), source.indexOf(end));
const session = { core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-original' };
const connection = { id: 'connection-original', revision: 1, profile: 'openai-compatible', model: 'model-original',
  grant_ref: 'grant-original', grant_revision: 1, max_output_tokens: 100, task_ms: 30000 };
const step = { step_ref: 'work-original#s2', attempt_id: 'work-original#a1', command_id: 'loop-original-t2',
  model_request_id: 'request-original', connection, status: 'reserved' };
const response = { protocol: 'core.work-events.v1', source: 'persisted_modeld_events',
  organization_id: 'au-original', work_id: 'work-original', ...step,
  version: 9, access: { principal_id: session.principal_id, service_instance: session.service_instance },
  state: 'streaming', cursor: 1, last_seq: 1, has_more: false, events_complete: false,
  authorization_only: false, truncated: false,
  events: [{ seq: 1, type: 'text_delta', text: '本次输出' }] };

async function observe(pages: any[] = [response], options: any = {}) {
  const reads: URL[] = [], summaries: any[] = [];
  let sessionReads = 0;
  const ctx = {
    createdReceipt: { organization_id: 'au-original' }, workId: 'work-original', inflight: structuredClone(step),
    URL, TextEncoder, crypto: { createHash }, output: '/synthetic', path: { join: (...parts: string[]) => parts.join('/') },
    fs: { writeFileSync: (_path: string, value: string) => summaries.push(JSON.parse(value)) },
    coreWork: async () => ({ protocol: 'core.work.v1', organization_id: 'au-original', version: 9,
      access: { principal_id: session.principal_id }, works: [{ id: 'work-original', steps: [structuredClone(step)] }] }),
    check: (name: string, value: unknown = true) => assert.ok(value, name),
    waitFor: async (predicate: () => Promise<boolean>) => {
      for (let i = 0; i < 3; i++) if (await predicate()) return;
      throw new Error('original output not observed within the bounded wait');
    },
    page: { evaluate: async (fn: (args: unknown) => unknown, args: unknown) => fn(args) },
    fetch: async (url: string, init?: { method?: string }) => {
      assert.ok(!init?.method || init.method === 'GET', 'observation never writes or dispatches');
      const parsed = new URL(url, 'http://synthetic.invalid');
      if (parsed.pathname === '/api/session') {
        sessionReads++;
        const body = options.changedSession && sessionReads > 1 ? options.changedSession : session;
        return { status: 200, ok: true, json: async () => structuredClone(body) };
      }
      assert.equal(parsed.pathname, '/api/v1/work/events');
      assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
      assert.equal(parsed.searchParams.get('work_id'), 'work-original');
      assert.equal(parsed.searchParams.get('step_ref'), step.step_ref);
      const body = pages[Math.min(reads.length, pages.length - 1)];
      reads.push(parsed);
      const status = options.status ?? 200;
      return { status, ok: status === 200, json: async () => structuredClone(body) };
    },
  };
  await vm.runInNewContext('(async () => {' + block + '\n})()', ctx, { timeout: 1000 });
  return { cursors: reads.map(url => Number(url.searchParams.get('after'))), summaries };
}

test('interrupt accepts public original text without inventing per-event request_id', async () => {
  const result = await observe();
  assert.ok(result.cursors.length > 0);
});

test('interrupt follows the original cursor past filtered and tool-only pages', async () => {
  const first = { ...response, events: [], cursor: 500, last_seq: 500, has_more: true };
  const second = { ...response, events: [{ seq: 501, type: 'text_delta', text: '原请求后续输出' }], cursor: 501, last_seq: 501 };
  const result = await observe([first, second]);
  assert.deepEqual(result.cursors, [0, 500]);
});

test('interrupt rejects unavailable, wrong-origin, non-output and malformed observations', async t => {
  const cases: [string, (value: any) => void, any?][] = [
    ['HTTP 403', () => {}, { status: 403 }],
    ['missing U108', () => {}, { status: 404 }],
    ['unavailable server', () => {}, { status: 503 }],
    ['wrong protocol', b => { b.protocol = 'error.v1'; }],
    ['wrong source', b => { b.source = 'local-reservation'; }],
    ...['organization_id', 'work_id', 'attempt_id', 'step_ref', 'command_id', 'model_request_id'].map(
      key => [`other ${key}`, (b: any) => { b[key] = 'other'; }] as [string, (value: any) => void]),
    ['other principal', b => { b.access.principal_id = 'other'; }],
    ['other service', b => { b.access.service_instance = 'other'; }],
    ['changed original connection', b => { b.connection.revision++; }],
    ['only tool activity', b => { b.events = [{ seq: 1, type: 'tool_call_complete', name: 'read_document' }]; }],
    ['only lifecycle activity', b => { b.events = [{ seq: 1, type: 'state', state: 'streaming' }]; }],
    ['empty text', b => { b.events[0].text = ''; }],
    ['whitespace only', b => { b.events[0].text = ' \n'; }],
    ['wrong text type', b => { b.events[0].text = {}; }],
    ['metadata only', b => { b.authorization_only = true; }],
    ['invalid cursor', b => { b.cursor = -1; }],
    ['invalid sequence', b => { b.events[0].seq = '1'; }],
    ['event beyond cursor', b => { b.events[0].seq = 2; }],
    ['duplicate sequence', b => { b.events.push({ ...b.events[0], text: 'different' }); }],
    ['principal changed in flight', () => {}, { changedSession: { ...session, principal_id: 'other' } }],
    ['service changed in flight', () => {}, { changedSession: { ...session, service_instance: 'other' } }],
  ];
  for (const [name, change, options] of cases) await t.test(name, async () => {
    const body = structuredClone(response);
    change(body);
    await assert.rejects(observe([body], options), error => {
      assert.ok(error instanceof Error);
      // Unexpected TypeErrors/VM failures are not successful contract rejections.
      return error.name === 'AssertionError' || error.message === 'original output not observed within the bounded wait';
    });
  });
});

test('interrupt rejects cursor regression after a filtered page', async () => {
  const first = { ...response, events: [], cursor: 500, last_seq: 500, has_more: true };
  await assert.rejects(observe([first, response]), { name: 'AssertionError' });
});

test('interrupt records original identity and UTF-8 text digest without raw text', async () => {
  const { summaries } = await observe();
  assert.equal(summaries.length, 1);
  assert.equal(summaries[0].model_request_id, step.model_request_id);
  assert.equal(summaries[0].text_bytes, Buffer.byteLength('本次输出', 'utf8'));
  assert.equal(summaries[0].text_sha256, createHash('sha256').update('本次输出', 'utf8').digest('hex'));
  assert.ok(!JSON.stringify(summaries).includes('本次输出'));
});
