import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

// Execute each driver's entire preparation prefix; no real host/model is started.
// This catches extra resources that isolated endpoint/transport tests cannot see.
for (const driver of ['exit22b_page.cjs', 'exit22c_download.cjs']) {
  const source = readFileSync(new URL('../scripts/' + driver, import.meta.url), 'utf8');
  const start = source.indexOf('  createdReceipt = await page.evaluate');
  const end = source.indexOf('  // Reload the work read', start);
  assert.ok(start >= 0 && end > start);
  const prefix = source.slice(start, end);
  async function run(failure?: 'create' | 'prepare') {
    const creations: any[] = [], grants: any[] = [], commands: any[] = [];
    let grantReply: any;
    const context: any = {
      crypto: {randomUUID: () => 'creation-' + (creations.length + 1)},
      document: {querySelector: () => ({value: 'au-1'})},
      fetch: async (url: string, init?: any) => {
        let body: any;
        if (init?.method === 'POST') {
          const c = JSON.parse(init.body);
          if (c.kind === 'create_v1') {
            creations.push(c);
            body = {receipt: {id: c.id, status: failure === 'create' ? 'unknown' : 'succeeded', organization_id: 'au-' + creations.length}};
          } else {
            commands.push(c);
            body = {receipt: {status: 'succeeded'}};
          }
        } else if (url === '/api/auth/status') body = {configured: true, authenticated: true};
        else if (url.startsWith('/api/v1/aus/')) body = {au: {version: 1, governance_root: {governor_principal_id: 'principal-original'}}};
        else body = {access: {can_start: true}, connections: [{id: 'connection-a', is_default: true, enabled: true}], works: []};
        return {ok: true, status: 200, json: async () => body};
      },
      process: {env: {UNION_REAL_MODEL: 'synthetic-model'}},
      running: {origin: 'http://localhost'}, errors: [], output: '/synthetic',
      path: {join: (...parts: string[]) => parts.join('/')},
      check: (name: string, value: any = true) => assert.ok(value, name),
      setTimeout, clearTimeout,
      host: {stdout: {}, stdin: {write: (raw: string) => {
        const c = JSON.parse(raw); assert.equal(c.op, 'prepare'); grants.push(c);
        grantReply = {prepared: failure !== 'prepare', grant_ref: 'grant-' + grants.length};
      }}},
      readline: {createInterface: () => ({once: (_: string, fn: any) => fn(JSON.stringify(grantReply))})},
    };
    const target = {waitFor: async () => {}, click: async () => {}};
    context.page = {evaluate: (fn: any, arg: any) => vm.runInNewContext('(' + fn.toString() + ')(arg)', {...context, arg}),
      goto: async () => {}, getByText: () => target, locator: () => target, waitForURL: async () => {}};
    let error, outcome;
    try {outcome = await vm.runInNewContext('(async()=>{' + prefix + ';return {createdReceipt,hostGrantRef};})()', context);}
    catch (caught) {error = caught;}
    return {error, outcome, creations, grants, commands};
  }
  test(driver + ': navigation preserves the sole created AU instead of leaving an untracked second AU', async () => {
    const r = await run(); assert.ifError(r.error);
    assert.equal(r.creations.length, 1, 'one acceptance run must create one AU');
    assert.equal(r.outcome.createdReceipt.organization_id, 'au-1');
    for (const c of r.commands.filter(c => c.organization_id)) assert.equal(c.organization_id, 'au-1');
  });
  test(driver + ': refresh does not mint a second grant or replace the adopted grant reference', async () => {
    const r = await run(); assert.ifError(r.error);
    assert.deepEqual(r.grants, [{op: 'prepare', au_id: 'au-1'}]);
    const saved = r.commands.find(c => c.kind === 'save_connection');
    assert.equal(saved.data.grant_ref, r.outcome.hostGrantRef);
    assert.equal(saved.data.grant_ref, 'grant-1');
  });
  test(driver + ': unknown creation stops without a new AU or grant', async () => {
    const r = await run('create'); assert.match(String(r.error), /create_v1 failed/);
    assert.equal(r.creations.length, 1); assert.equal(r.grants.length, 0);
  });
  test(driver + ': failed prepare stops without a second grant or connection adoption', async () => {
    const r = await run('prepare'); assert.match(String(r.error), /prepare failed/);
    assert.equal(r.grants.length, 1);
    assert.equal(r.commands.filter(c => c.kind === 'save_connection').length, 0);
  });
}
