import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// readSnapshot is read-only: only page.evaluate is faked, no request is issued here.
const requireHelpers = createRequire(new URL('../scripts/exit22-restart-evidence.cjs', import.meta.url));
const { readSnapshot } = requireHelpers('../scripts/exit22-restart-evidence.cjs');

const session = { core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-1' };
const workBody = {
  protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
  access: { principal_id: session.principal_id },
  works: [{ id: 'work-original', budget: { max_calls: 3, used: 1, reserved: 0 }, attempts: [],
    steps: [{ step_ref: 'step-1', attempt_id: 'work-original#a1', command_id: 'loop-original-t1',
      model_request_id: 'model-1', status: 'used', usage: { input_tokens: 438, output_tokens: 46 },
      cost_status: 'unknown', reason: 'completed', connection: { id: 'connection-original', revision: 1 } }],
    results: [] }],
};

function page(value: any) {
  return { evaluate: async () => structuredClone(value) };
}
function payload(overrides: any = {}) {
  return { session: { status: 200, body: structuredClone(session) },
    work: { status: 200, body: structuredClone(workBody) },
    current: { status: 200, body: structuredClone(session) }, ...overrides };
}

test('a successful read returns the original Core work body', async () => {
  const body = await readSnapshot(page(payload()), 'au-original', 'work-original');
  assert.equal(body.protocol, 'core.work.v1');
  assert.equal(body.organization_id, 'au-original');
});

test('a rejected session read names the route, status and Core error code', async () => {
  const rejected = payload({ session: { status: 409, body: { code: 'unsupported_capability' } } });
  await assert.rejects(() => readSnapshot(page(rejected), 'au-original', 'work-original'), (error: any) => {
    assert.match(String(error.message), /\/api\/session/);
    assert.match(String(error.message), /409/);
    assert.match(String(error.message), /unsupported_capability/);
    return true;
  });
});

test('a rejected work read names the work route and its status', async () => {
  const rejected = payload({ work: { status: 503, body: { code: 'storage_unavailable' } } });
  await assert.rejects(() => readSnapshot(page(rejected), 'au-original', 'work-original'), (error: any) => {
    assert.match(String(error.message), /\/api\/v1\/work/);
    assert.match(String(error.message), /503/);
    assert.match(String(error.message), /storage_unavailable/);
    return true;
  });
});
