import { afterEach, expect, test } from 'bun:test';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { startService } from '../src/server';

const directories: string[] = [], services: Awaited<ReturnType<typeof startService>>[] = [];
const adminToken = 'api-admin-fixture-'.padEnd(48, 'a'), workerToken = 'api-worker-fixture-'.padEnd(48, 'w');
afterEach(async () => {
  for (const service of services.splice(0)) await service.close();
  for (const directory of directories.splice(0)) {
    expect(dirname(resolve(directory))).toBe(resolve(tmpdir()));
    expect(basename(directory).startsWith('union-modeld-api-')).toBe(true);
    rmSync(directory, { recursive: true, force: true });
  }
});
function registration() {
  return { id: randomUUID(), au_id: randomUUID(), principal_id: randomUUID(), name: 'Controlled API profile',
    base_url: 'http://127.0.0.1:32123/v1', api_key: 's02-controlled-only-key-123456789', model_id: 'controlled-model' };
}
async function setup(directory = mkdtempSync(join(tmpdir(), 'union-modeld-api-'))) {
  if (!directories.includes(directory)) directories.push(directory);
  let accountReads = 0, modelReads = 0, inferenceCalls = 0;
  const received: { account: any; input: any }[] = [];
  const service = await startService({ directory, port: 0, adminToken, workerToken, upstream: 'controlled-api',
    kernel: async () => ({
      accounts: async () => { accountReads++; return [{ id: 'go-fixture-account' }]; },
      models: async () => { modelReads++; return [{ id: 'go-fixture-model' }]; },
      connect: async () => { throw new Error('not used'); }, close: async () => {},
      infer: async () => { throw new Error('API account was incorrectly sent to Go'); },
      inferAPI: async (account: unknown, input: unknown) => {
        inferenceCalls++; received.push({ account, input });
        return { message: { role: 'assistant', content: 'controlled API result' }, usage: { input_tokens: 5, output_tokens: 3 } };
      },
    }) });
  services.push(service);
  const call = (method: string, path: string, body?: unknown, role: 'admin' | 'worker' = 'admin') => fetch(new URL(path, service.url), {
    method, headers: { authorization: 'Bearer ' + (role === 'admin' ? adminToken : workerToken), 'content-type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  return { directory, service, call, received,
    counts: () => ({ accountReads, modelReads, inferenceCalls }) };
}
function lookup(body: ReturnType<typeof registration>) {
  return `/v1/api-connections/${body.id}?au_id=${body.au_id}&principal_id=${body.principal_id}`;
}
async function save(call: Awaited<ReturnType<typeof setup>>['call'], body = registration()) {
  const response = await call('POST', '/v1/api-connections', body);
  expect(response.status).toBe(201);
  return { body, receipt: await response.json() as any };
}

test('saving an API connection is atomic, durable, idempotent and independent from Go or inference', async () => {
  const { directory, service, call, counts } = await setup();
  const { body, receipt } = await save(call);
  expect(Object.keys(receipt).sort()).toEqual(['id', 'au_id', 'principal_id', 'name', 'profile', 'model_id', 'grant_ref', 'grant_revision'].sort());
  expect(receipt).toMatchObject({ id: body.id, au_id: body.au_id, principal_id: body.principal_id,
    name: body.name, profile: 'openai_compatible', model_id: body.model_id, grant_revision: 1 });
  expect(JSON.stringify(receipt)).not.toContain(body.api_key);
  const grant = service.journal.grant(receipt.grant_ref);
  expect(grant.au_id).toBe(body.au_id); expect(grant.model_ids).toEqual([body.model_id]);
  expect((await save(call, { ...body })).receipt).toEqual(receipt);
  expect(counts()).toEqual({ accountReads: 0, modelReads: 0, inferenceCalls: 0 });
  await service.close(); services.splice(services.indexOf(service), 1);
  const reopened = await setup(directory);
  expect(await (await reopened.call('GET', lookup(body))).json()).toEqual(receipt);
  expect((await save(reopened.call, body)).receipt).toEqual(receipt);
  expect(reopened.counts()).toEqual({ accountReads: 0, modelReads: 0, inferenceCalls: 0 });
  expect(reopened.service.journal.db.query('SELECT COUNT(*) AS n FROM api_connections').get()).toEqual({ n: 1 });
  expect(reopened.service.journal.db.query('SELECT COUNT(*) AS n FROM grants').get()).toEqual({ n: 1 });
  expect(reopened.service.journal.db.query('SELECT COUNT(*) AS n FROM grant_audit').get()).toEqual({ n: 1 });
});

test('API registration accepts stable command identifiers including the full request identifier limit', async () => {
  const { call, service } = await setup();
  for (const id of ['model.settings:save-1', 'r'.repeat(160)]) {
    const body = { ...registration(), id };
    const { receipt } = await save(call, body);
    expect(receipt.id).toBe(id);
    expect(await (await call('GET', lookup(body))).json()).toEqual(receipt);
    expect((await save(call, body)).receipt).toEqual(receipt);
    const grant = service.journal.grant(receipt.grant_ref);
    expect(grant.id.length).toBeLessThanOrEqual(160);
    expect(grant.account_ref.length).toBeLessThanOrEqual(160);
  }
});

test('registration accepts the core org AU identifier while preserving existing UUID AU compatibility', async () => {
  const { call, service } = await setup();
  for (const au_id of ['org-' + randomUUID().replaceAll('-', ''), randomUUID()]) {
    const body = { ...registration(), au_id };
    const { receipt } = await save(call, body);
    expect(receipt.au_id).toBe(au_id);
    expect(service.journal.grant(receipt.grant_ref).au_id).toBe(au_id);
    expect(await (await call('GET', lookup(body))).json()).toEqual(receipt);
  }
});

test('same registration ID cannot replace any secret, endpoint, identity, model or name', async () => {
  const { call, service } = await setup();
  const { body, receipt } = await save(call);
  for (const changed of [
    { api_key: body.api_key + '-other' }, { base_url: 'https://other.invalid/v1' },
    { au_id: randomUUID() }, { principal_id: randomUUID() }, { model_id: 'other-model' }, { name: 'Changed name' },
  ]) {
    const response = await call('POST', '/v1/api-connections', { ...body, ...changed });
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ error: 'api_connection_id_conflict' });
  }
  expect(await (await call('GET', lookup(body))).json()).toEqual(receipt);
  expect(service.journal.db.query('SELECT COUNT(*) AS n FROM api_connections').get()).toEqual({ n: 1 });
});

test('registration recovery requires the exact original AU and principal, with admin/worker role separation', async () => {
  const { call, counts } = await setup();
  const { body, receipt } = await save(call);
  expect((await call('POST', '/v1/api-connections', registration(), 'worker')).status).toBe(403);
  expect((await call('GET', lookup(body), undefined, 'worker')).status).toBe(403);
  expect((await call('GET', lookup({ ...body, au_id: randomUUID() }))).status).toBe(403);
  expect((await call('GET', lookup({ ...body, principal_id: randomUUID() }))).status).toBe(403);
  expect((await call('GET', `/v1/api-connections/${body.id}`)).status).toBe(400);
  expect((await call('GET', lookup({ ...body, id: randomUUID() }))).status).toBe(404);
  expect(await (await call('GET', lookup(body))).json()).toEqual(receipt);
  expect(counts()).toEqual({ accountReads: 0, modelReads: 0, inferenceCalls: 0 });
});

test('API account is never listed or re-granted through the legacy Go account endpoints', async () => {
  const { call, service, counts } = await setup();
  const { receipt } = await save(call);
  const account = service.journal.grant(receipt.grant_ref).account_ref;
  const listed = await (await call('GET', '/v1/accounts')).json() as any;
  expect(listed.accounts).toEqual([{ id: 'go-fixture-account' }]);
  expect((await call('GET', `/v1/accounts/${account}/models`)).status).toBe(403);
  expect((await call('POST', '/v1/grants', { id: 'stolen-api-grant', au_id: randomUUID(),
    account_ref: account, model_ids: [receipt.model_id] })).status).toBe(403);
  expect(counts().modelReads).toBe(0);
});

test('registration replay after revocation retains the original save receipt without restoring the grant', async () => {
  const { call, service } = await setup();
  const { body, receipt } = await save(call);
  expect((await call('POST', `/v1/grants/${receipt.grant_ref}/revoke`, { revision: 1 })).status).toBe(200);
  expect((await save(call, body)).receipt).toEqual(receipt);
  expect(await (await call('GET', lookup(body))).json()).toEqual(receipt);
  const current = service.journal.grant(receipt.grant_ref);
  expect(current.revision).toBe(2); expect(current.revoked_at).not.toBeNull();
  expect(service.journal.db.query('SELECT COUNT(*) AS n FROM grants').get()).toEqual({ n: 1 });
});

test('an interrupted registration transaction leaves neither an account nor a grant', async () => {
  const { call, service } = await setup();
  // Fail the audit write after account/grant creation would have started.
  service.journal.db.exec("CREATE TRIGGER deny_fixture_grant BEFORE INSERT ON grant_audit BEGIN SELECT RAISE(ABORT, 'controlled failure'); END");
  const body = registration();
  expect((await call('POST', '/v1/api-connections', body)).status).toBe(500);
  expect(service.journal.db.query('SELECT COUNT(*) AS n FROM api_connections').get()).toEqual({ n: 0 });
  expect(service.journal.db.query('SELECT COUNT(*) AS n FROM grants').get()).toEqual({ n: 0 });
  expect((await call('GET', lookup(body))).status).toBe(404);
  service.journal.db.exec('DROP TRIGGER deny_fixture_grant');
  expect((await save(call, body)).receipt.id).toBe(body.id);
});

test('API account and fixed grant reach only the selected private inference path', async () => {
  const { call, received, counts } = await setup();
  const { body, receipt } = await save(call);
  const id = randomUUID();
  const task = { id, run_id: id, au_id: body.au_id, connection_id: randomUUID(), connection_revision: 1,
    grant_ref: receipt.grant_ref, grant_revision: 1, model_id: body.model_id, messages: [{ role: 'user', content: 'hello' }],
    tools: [], generation: { maxOutputTokens: 15 }, deadlines: { first_event_ms: 1000, idle_ms: 1000, task_ms: 3000 } };
  expect((await call('POST', '/v1/requests', { ...task, au_id: randomUUID() }, 'worker')).status).toBe(403);
  expect((await call('POST', '/v1/requests', { ...task, model_id: 'wrong-model' }, 'worker')).status).toBe(403);
  expect((await call('POST', '/v1/requests', task, 'worker')).status).toBe(202);
  let result: any;
  for (let i = 0; i < 100; i++) {
    result = await (await call('GET', `/v1/requests/${id}?au_id=${body.au_id}`, undefined, 'worker')).json();
    if (['completed', 'failed', 'interrupted'].includes(result.state)) break;
    await Bun.sleep(10);
  }
  expect(result.state).toBe('completed');
  expect(result.action_authorized).toBe(true);
  expect(result.result.message.content).toBe('controlled API result');
  expect(JSON.stringify(result)).not.toContain(body.api_key);
  expect(received[0].account).toMatchObject({ au_id: body.au_id, api_key: body.api_key, base_url: body.base_url, model_id: body.model_id });
  expect(received[0].input).toEqual(task);
  expect(counts()).toEqual({ accountReads: 0, modelReads: 0, inferenceCalls: 1 });
});

test('registration rejects unsupported or ambiguous endpoint, header, profile, identity and key input without saving', async () => {
  const { call, service } = await setup();
  const original = registration();
  for (const change of [
    { base_url: 'http://provider.invalid/v1' }, { base_url: 'ftp://provider.invalid/v1' },
    { base_url: 'https://user:pass@provider.invalid/v1' }, { base_url: 'https://provider.invalid/v1?secret=x' },
    { base_url: 'https://provider.invalid/v1#fragment' }, { base_url: 'not a URL' },
    { base_url: ' http://127.0.0.1/v1' }, { base_url: 'https://provider.invalid/v1\n' },
    { id: 'invalid/operation' }, { au_id: 'invalid/au' }, { principal_id: 'display-name' },
    { api_key: '' }, { api_key: 'unsafe\r\nheader' }, { api_key: 'k'.repeat(4097) },
    { headers: { authorization: 'override' } }, { profile: 'anthropic' },
    { name: '' }, { model_id: '' }, { name: original.api_key },
  ]) {
    const response = await call('POST', '/v1/api-connections', { ...original, ...change });
    expect(response.status).toBe(400);
    expect(await response.text()).not.toContain(original.api_key);
  }
  expect(service.journal.db.query('SELECT COUNT(*) AS n FROM api_connections').get()).toEqual({ n: 0 });
  expect(service.journal.db.query('SELECT COUNT(*) AS n FROM grants').get()).toEqual({ n: 0 });
});

for (const [variant, api_key] of [
  ['ordinary', 'fixture-private-credential-738461'],
  ['quote', 'fixture-private-"credential-738461'],
  ['backslash', 'fixture-private-\\credential-738461'],
  ['quote-and-backslash', 'fixture-private-"\\credential-738461'],
] as const) {
  for (const field of ['name', 'model_id', 'base_url'] as const) {
    test(`registration never persists or returns a ${variant} credential embedded in ${field}`, async () => {
      const { call, service, counts } = await setup();
      const body = { ...registration(), api_key,
        [field]: field === 'base_url' ? 'http://127.0.0.1/' + api_key : 'label:' + api_key };
      const response = await call('POST', '/v1/api-connections', body);
      expect(response.status).toBe(400);
      expect(await response.json()).toEqual({ error: 'credential_in_api_connection_metadata' });
      expect((await call('GET', lookup(body))).status).toBe(404);
      expect(service.journal.db.query('SELECT COUNT(*) AS n FROM api_connections').get()).toEqual({ n: 0 });
      expect(service.journal.db.query('SELECT COUNT(*) AS n FROM grants').get()).toEqual({ n: 0 });
      expect(counts()).toEqual({ accountReads: 0, modelReads: 0, inferenceCalls: 0 });
    });
  }
}
