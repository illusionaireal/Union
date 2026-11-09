import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

const require = createRequire(new URL('../scripts/exit22b_page.cjs', import.meta.url));
const session = { core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-before' };
const original = {
  protocol: 'core.work.v1', organization_id: 'au-original', version: 20,
  access: { principal_id: session.principal_id },
  works: [{ id: 'work-original', status: 'delivered', delivered_result_id: 'result-original',
    budget: { max_calls: 3, used: 1, reserved: 1 },
    results: [{ id: 'result-original', status: 'adopted', sha256: 'digest-original' }],
    steps: [
      { step_ref: 'step-1', attempt_id: 'attempt-original', command_id: 'loop-original',
        model_request_id: 'model-1', status: 'used', usage: { input_tokens: 438, output_tokens: 46 },
        cost_status: 'unknown', reason: 'completed', connection: { id: 'connection-original', revision: 1 } },
      { step_ref: 'step-2', attempt_id: 'attempt-original', command_id: 'loop-original',
        model_request_id: 'model-2', status: 'unknown', usage: null, cost_status: 'unknown',
        reason: 'interrupted', connection: { id: 'connection-original', revision: 1 } },
    ],
  }],
};

for (const driver of ['exit22b_page.cjs', 'exit22c_download.cjs']) {
  const source = readFileSync(new URL('../scripts/' + driver, import.meta.url), 'utf8');
  const snapshotStart = source.indexOf('async function snapshot(');
  const snapshotEnd = source.indexOf('async function coreWork()', snapshotStart);
  const restartStart = source.indexOf('  const before = await snapshot();');
  const restartEnd = source.indexOf("  fs.writeFileSync(path.join(output, 'checks.json')", restartStart);
  assert.ok(snapshotStart >= 0 && snapshotEnd > snapshotStart && restartStart >= 0 && restartEnd > restartStart);
  const snapshotSource = source.slice(snapshotStart, snapshotEnd);
  const restartSource = source.slice(restartStart, restartEnd);

  async function run(options: { after?: any; before?: any; status?: number; session?: any; sessionAfter?: any; snapshotOnly?: boolean } = {}) {
    let restarted = false;
    let sessionReads = 0;
    const paths: string[] = [], files = new Map<string, any>();
    const context: any = {
      // Cancel receipt recovery has its own adversarial driver/HTTP/browser suite.
      // Keep this fixture focused on request/usage/budget snapshot preservation.
      require: (name: string) => name === './exit22-cancel-evidence.cjs'
        ? { readCancelEvidence: async () => ({ receipt: { id: 'cancel-original' } }) } : require(name),
      originalCancelReference: {}, cancelEvidenceBefore: { receipt: { id: 'cancel-original' } },
      assert, URLSearchParams,
      createdReceipt: { organization_id: 'au-original' }, workId: 'work-original',
      resultId: 'result-original', recorded: 'digest-original', inflight: structuredClone(original.works[0].steps[1]),
      output: '/synthetic', path: { join: (...parts: string[]) => parts.join('/') },
      fs: { writeFileSync: (name: string, text: string) => files.set(name.split('/').at(-1)!, JSON.parse(text)) },
      check: (name: string, value: unknown = true) => assert.ok(value, name),
      host: { kill: () => {} }, running: { child: { once: (_: string, fn: () => void) => fn() } },
      startHost: async () => { restarted = true; return { origin: 'http://synthetic.invalid', child: {} }; },
      document: { querySelector: () => ({ value: 'au-original' }) },
      page: { evaluate: async (fn: (arg: unknown) => unknown, arg: unknown) =>
        vm.runInNewContext('(' + fn.toString() + ')(__arg)', { ...context, __arg: arg }),
        goto: async () => {}, getByText: () => ({ waitFor: async () => {} }) },
      fetch: async (url: string, init?: { method?: string }) => {
        assert.ok(!init?.method || init.method === 'GET', 'restart evidence must not write or dispatch');
        paths.push(url);
        if (url === '/api/session') {
          sessionReads++;
          return { status: 200, json: async () => ({ ...session,
            ...(restarted ? { service_instance: 'service-after' } : {}), ...options.session,
            ...(sessionReads > 1 ? options.sessionAfter : {}) }) };
        }
        const parsed = new URL(url, 'http://synthetic.invalid');
        assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
        if (parsed.pathname === '/api/snapshot') return { status: 409, json: async () => ({ error: 'unsupported_capability' }) };
        assert.equal(parsed.pathname, '/api/v1/work');
        return { status: options.status ?? 200,
          json: async () => structuredClone(restarted ? options.after ?? original : options.before ?? original) };
      },
    };
    await vm.runInNewContext(snapshotSource + '\n(async () => {' +
      (options.snapshotOnly ? 'return snapshot();' : restartSource) + '\n})()', context, { timeout: 1000 });
    return { files, paths };
  }

  test(driver + ': same-run Core snapshots preserve two requests and unknown usage', async () => {
    const { files, paths } = await run();
    assert.equal(files.get('snapshot-before-restart.json')?.protocol, 'core.work.v1');
    assert.equal(files.get('snapshot-after-restart.json')?.organization_id, 'au-original');
    assert.ok(!paths.some(p => p.startsWith('/api/snapshot')));
    const summary = files.get('restart-request-comparison.json');
    assert.equal(summary?.model_request_identity_count, 2);
    assert.equal(summary?.requests.find((r: any) => r.model_request_id === 'model-2').usage, null);
  });

  test(driver + ': reject bad HTTP, scope and session before saving a snapshot', async t => {
    const cases: [string, any][] = [
      ['403', { status: 403 }], ['legacy error', { before: { error: 'unsupported_capability' } }],
      ['wrong AU', { before: { ...original, organization_id: 'another-au' } }],
      ['wrong protocol', { before: { ...original, protocol: 'legacy.v0' } }],
      ['wrong principal', { before: { ...original, access: { principal_id: 'another-principal' } } }],
      ['missing Work', { before: { ...original, works: [] } }],
      ['not Core session', { session: { core_protocol: null } }],
      ['principal changes during read', { sessionAfter: { principal_id: 'another-principal' } }],
      ['service changes during read', { sessionAfter: { service_instance: 'another-service' } }],
    ];
    for (const [name, options] of cases) await t.test(name, () => assert.rejects(run({ ...options, snapshotOnly: true })));
  });

  test(driver + ': malformed original requests cannot establish a baseline', async t => {
    const cases: [string, (body: any) => void][] = [
      ['zero requests', b => { b.works[0].steps = []; }],
      ['missing request identity', b => { delete b.works[0].steps[0].model_request_id; }],
      ['duplicate request identity', b => { b.works[0].steps[1].model_request_id = 'model-1'; }],
      ['unsettled request', b => { b.works[0].steps[1].status = 'reserved'; }],
      ['duplicate original Work', b => { b.works.push(structuredClone(b.works[0])); }],
    ];
    for (const [name, change] of cases) await t.test(name, async () => {
      const before = structuredClone(original); change(before);
      await assert.rejects(run({ before, snapshotOnly: true }));
    });
  });

  test(driver + ': reject changed persisted facts and new request identities', async t => {
    const cases: [string, (body: any) => void][] = [
      ['extra request', b => b.works[0].steps.push({ ...b.works[0].steps[0], step_ref: 'step-3', model_request_id: 'model-3' })],
      ['missing original request', b => b.works[0].steps.shift()],
      ['substituted request', b => { b.works[0].steps[0].model_request_id = 'another-request'; }],
      ['changed original loop', b => { b.works[0].steps[1].command_id = 'another-loop'; }],
      ['lost usage', b => { b.works[0].steps[0].usage = null; }],
      ['unknown usage fabricated as zero', b => { b.works[0].steps[1].usage = { input_tokens: 0, output_tokens: 0 }; }],
      ['lost reservation', b => { b.works[0].budget.reserved = 0; }],
      ['unknown released', b => { b.works[0].steps[1].status = 'released'; }],
      ['changed connection', b => { b.works[0].steps[0].connection.revision++; }],
    ];
    for (const [name, change] of cases) await t.test(name, async () => {
      const after = structuredClone(original); change(after); await assert.rejects(run({ after }));
    });
  });

  test(driver + ': normal restart permits reordered steps and JSON keys', async () => {
    const after = structuredClone(original);
    after.works[0].steps.reverse();
    after.works[0].budget = { reserved: 1, used: 1, max_calls: 3 };
    await run({ after });
  });

  test(driver + ': completed request with unreported usage remains explicitly unknown', async () => {
    const before = structuredClone(original);
    before.works[0].steps[0].usage = null;
    const result = await run({ before, after: before });
    assert.equal(result.files.get('restart-request-comparison.json').requests[0].usage, null);
  });
}
