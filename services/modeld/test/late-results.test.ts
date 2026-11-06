import { afterEach, expect, test } from 'bun:test';
import { createHash } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { canonical, Journal, type InferenceInput } from '../src/journal';
import { startService, type InferenceKernel } from '../src/server';

const directories: string[] = [], services: Awaited<ReturnType<typeof startService>>[] = [];
afterEach(async () => {
  for (const service of services.splice(0)) await service.close();
  for (const directory of directories.splice(0)) {
    expect(dirname(resolve(directory))).toBe(resolve(tmpdir()));
    expect(basename(directory).startsWith('union-modeld-facts-')).toBe(true);
    rmSync(directory, { recursive: true, force: true });
  }
});
const knownResult = { message: { role: 'assistant', content: 'late answer', tool_calls: [{ id: 'observed-call' }] },
  usage: { input_tokens: 19, output_tokens: 7, modeld_usage: { inputTokens: 19, outputTokens: 7, cost: 0.004 } } };
function input(): InferenceInput {
  return { id: 'request-facts', run_id: 'request-facts', au_id: 'au-facts', connection_id: 'connection-facts',
    connection_revision: 1, grant_ref: 'grant-facts', grant_revision: 1, model_id: 'model-facts',
    messages: [{ role: 'user', content: 'read the controlled document' }], tools: [],
    generation: { maxOutputTokens: 40 }, deadlines: { first_event_ms: 1000, idle_ms: 1000, task_ms: 3000 } };
}
async function setup(infer: InferenceKernel['infer']) {
  const directory = mkdtempSync(join(tmpdir(), 'union-modeld-facts-')); directories.push(directory);
  let dispatches = 0;
  const service = await startService({ directory, port: 0, upstream: 'controlled-facts',
    adminToken: 'facts-admin-'.padEnd(48, 'a'), workerToken: 'facts-worker-'.padEnd(48, 'w'),
    kernel: async () => ({ accounts: async () => [{ id: 'account-facts' }], models: async () => [{ id: 'model-facts' }],
      connect: async () => { throw new Error('unused'); }, close: async () => {},
      infer: async (...args) => { dispatches++; return infer(...args); } }) });
  services.push(service);
  const call = (method: string, path: string, body?: unknown, admin = false) => fetch(new URL(path, service.url), {
    method, headers: { authorization: 'Bearer ' + (admin ? 'facts-admin-'.padEnd(48, 'a') : 'facts-worker-'.padEnd(48, 'w')),
      'content-type': 'application/json' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  expect((await call('POST', '/v1/grants', { id: 'grant-facts', au_id: 'au-facts', account_ref: 'account-facts',
    model_ids: ['model-facts'] }, true)).status).toBe(201);
  return { service, call, dispatches: () => dispatches };
}
async function settled(call: Awaited<ReturnType<typeof setup>>['call']) {
  for (let n = 0; n < 100; n++) {
    const response = await call('GET', '/v1/requests/request-facts?au_id=au-facts');
    expect(response.status).toBe(200);
    const row = await response.json() as any;
    if (['completed', 'failed', 'interrupted'].includes(row.state)) return row;
    await Bun.sleep(10);
  }
  throw new Error('controlled request did not finish');
}

test('revocation after completion preserves original AU evidence and digest but removes action authorization', async () => {
  const { call, dispatches } = await setup(async () => knownResult);
  const original = input();
  expect((await call('POST', '/v1/requests', original)).status).toBe(202);
  expect((await settled(call)).state).toBe('completed');
  expect((await call('POST', '/v1/grants/grant-facts/revoke', { revision: 1 }, true)).status).toBe(200);
  const response = await call('GET', '/v1/requests/request-facts?au_id=au-facts');
  expect(response.status).toBe(200);
  const row = await response.json() as any;
  expect(row.state).toBe('completed');
  expect(row.action_authorized).toBe(false);
  expect(row.result).toEqual(knownResult);
  expect(row.request_digest).toBe(createHash('sha256').update(canonical(original)).digest('hex'));
  expect((await call('GET', '/v1/requests/request-facts?au_id=au-other')).status).toBe(404);
  expect((await call('POST', '/v1/requests', { ...original, id: 'new-request', run_id: 'new-request' })).status).toBe(403);
  expect(dispatches()).toBe(1);
});

for (const stop of ['revoke', 'cancel'] as const) test(`${stop} preserves dispatched late usage and result without making tools actionable`, async () => {
  let release!: () => void, started!: () => void;
  const ready = new Promise<void>(r => { started = r; });
  const held = new Promise<void>(r => { release = r; });
  let wasAborted = false;
  const { call, dispatches } = await setup(async (_account, _input, signal, event) => {
    started();
    await held;
    wasAborted = signal.aborted;
    event('native_event', { type: 'usage', usage: knownResult.usage.modeld_usage });
    return knownResult;
  });
  try {
    expect((await call('POST', '/v1/requests', input())).status).toBe(202);
    await ready;
    const stopped = stop === 'revoke'
      ? await call('POST', '/v1/grants/grant-facts/revoke', { revision: 1 }, true)
      : await call('POST', '/v1/requests/request-facts/cancel?au_id=au-facts');
    expect(stopped.status).toBe(stop === 'revoke' ? 200 : 202);
    release();
    const row = await settled(call);
    expect(wasAborted).toBe(true);
    expect(row.state).toBe('interrupted');
    expect(row.action_authorized).toBe(false);
    expect(row.result).toEqual(knownResult);
    const history = await (await call('GET', '/v1/requests/request-facts/events?au_id=au-facts')).json() as any;
    expect(history.events.some((e: any) => e.type === 'native_event' && e.payload.usage.cost === 0.004)).toBe(true);
    expect(dispatches()).toBe(1);
  } finally { release(); }
});

test('a result observed after an interrupted terminal state is retained once without reopening execution', () => {
  const directory = mkdtempSync(join(tmpdir(), 'union-modeld-facts-')); directories.push(directory);
  const journal = new Journal(directory);
  try {
    journal.createGrant({ id: 'grant-facts', au_id: 'au-facts', account_ref: 'account-facts', model_ids: ['model-facts'] });
    journal.submit(input()); journal.begin('request-facts', 'au-facts');
    journal.finish('request-facts', 'interrupted', null, 'provider_result_unconfirmed');
    journal.finish('request-facts', 'completed', knownResult);
    const row = journal.get('request-facts', 'au-facts');
    expect(row.state).toBe('interrupted');
    expect(JSON.parse(row.result!)).toEqual(knownResult);
    const count = journal.events('request-facts', 'au-facts', 0).length;
    journal.finish('request-facts', 'completed', knownResult);
    expect(journal.events('request-facts', 'au-facts', 0)).toHaveLength(count);
    expect(journal.begin('request-facts', 'au-facts')).toBeNull();
  } finally { journal.close(); }
});
