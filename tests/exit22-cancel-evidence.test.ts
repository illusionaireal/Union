import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// Direct unit coverage of the read-only original-cancel evidence helper.
// The helper never issues or replays commands; only page.evaluate is faked here.
const requireHelper = createRequire(new URL('../scripts/exit22-cancel-evidence.cjs', import.meta.url));
const { readCancelEvidence } = requireHelper('../scripts/exit22-cancel-evidence.cjs');

const connection = { id: 'connection-original', revision: 1 };
const reference = {
  organization_id: 'au-original', work_id: 'work-original', cancel_id: 'cancel-original',
  principal_id: 'principal-original', step_ref: 'step-original', attempt_id: 'attempt-original',
  command_id: 'loop-original-t2', model_request_id: 'model-original', connection,
};
const receipt = {
  id: 'cancel-original', organization_id: 'au-original', kind: 'cancel_step', status: 'succeeded',
  effect: 'applied', actor_principal_id: 'principal-original', model_request_id: 'model-original',
  cancel_accepted: true, base_version: 10, version: 11, message: 'delivered',
  step: { step_ref: 'step-original', model_request_id: 'model-original' },
  cancel_connection: connection, delivery: { cancel_accepted: true, message: 'delivered' },
};

function payload(overrides: any = {}) {
  const session = { status: 200, body: {
    core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-original' } };
  return {
    session: structuredClone(session),
    work: { status: 200, body: {
      protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
      access: { principal_id: 'principal-original' },
      works: [{ id: 'work-original', steps: [{ step_ref: 'step-original', attempt_id: 'attempt-original',
        command_id: 'loop-original-t2', model_request_id: 'model-original', connection }] }] } },
    receipt: { status: 200, body: { receipt: structuredClone(receipt) } },
    current: structuredClone(session),
    ...overrides,
  };
}

function fakePage(value: any) {
  return { evaluate: async () => structuredClone(value) };
}

test('cancel evidence records the per-route HTTP outcome for attribution', async () => {
  const evidence = await readCancelEvidence(fakePage(payload()), reference, receipt);
  assert.equal(evidence.protocol, 'acceptance.cancel-receipt.v1');
  assert.deepEqual(evidence.receipt, receipt);
  // Without the per-route outcomes a failure cannot be attributed to a route.
  assert.deepEqual(evidence.http, {
    session: { route: '/api/session', status: 200 },
    work: { route: '/api/v1/work', status: 200 },
    receipt: { route: '/api/v1/governance/receipts', status: 200 },
    current: { route: '/api/session', status: 200 },
  });
});

test('a rejected read preserves every completed route outcome on the error', async () => {
  // The review (PR83) requires the durable failure archive to keep the outcomes that
  // were already observed, not just the first failing message.
  const mixed = payload({
    session: { status: 409, body: { code: 'unsupported_capability' } },
    work: { status: 503, body: { code: 'storage_unavailable' } },
    receipt: { status: 404, body: { code: 'not_authorized' } },
    current: { status: 200, body: { core_protocol: 'core.au.v1', principal_id: 'principal-original', service_instance: 'service-original' } },
  });
  await assert.rejects(() => readCancelEvidence(fakePage(mixed), reference, receipt), (error: any) => {
    assert.deepEqual(error.http, {
      session: { route: '/api/session', status: 409 },
      work: { route: '/api/v1/work', status: 503 },
      receipt: { route: '/api/v1/governance/receipts', status: 404 },
      current: { route: '/api/session', status: 200 },
    });
    return true;
  });
});

test('a transport failure keeps a structured reason and no invented outcome', async () => {
  // The review left network/JSON interruption unexpanded; a transport failure must still
  // produce a structured diagnostic instead of an untyped rejection.
  const failing = { evaluate: async () => { throw new Error('socket hang up'); } };
  await assert.rejects(() => readCancelEvidence(failing as any, reference, receipt), (error: any) => {
    assert.equal(error.code, 'transport_error');
    assert.equal(error.http, null);
    assert.match(String(error.message), /socket hang up/);
    return true;
  });
});

test('a malformed response is recorded as unknown status, not as success', async () => {
  const malformed = payload({ work: { status: undefined, body: { protocol: 'core.work.v1' } } });
  await assert.rejects(() => readCancelEvidence(fakePage(malformed), reference, receipt), (error: any) => {
    assert.equal(error.http.work.status, null);
    assert.equal(error.code, 'unknown_shape');
    return true;
  });
});

test('a rejected session read names the route, status and Core error code', async () => {
  const rejected = payload({
    session: { status: 409, body: { code: 'unsupported_capability', error: '此 AU 尚在准备态' } },
  });
  await assert.rejects(
    () => readCancelEvidence(fakePage(rejected), reference, receipt),
    (error: any) => {
      assert.match(String(error.message), /\/api\/session/);
      assert.match(String(error.message), /409/);
      assert.match(String(error.message), /unsupported_capability/);
      return true;
    },
  );
});

test('a mismatched cancel receipt still fails the durable-fact comparison', async () => {
  const changed = payload();
  changed.receipt.body.receipt.base_version = 11;
  changed.receipt.body.receipt.version = 11;
  await assert.rejects(
    () => readCancelEvidence(fakePage(changed), reference, receipt),
    /original cancel versions/,
  );
});

// PR83 counterexample 1/4 + 2 legitimate controls: the strict identity validation runs after
// every GET returned 200, so its rejection must still carry the completed safe route map.
const validationHttp = {
  session: { route: '/api/session', status: 200 },
  work: { route: '/api/v1/work', status: 200 },
  receipt: { route: '/api/v1/governance/receipts', status: 200 },
  current: { route: '/api/session', status: 200 },
};

test('a session principal mismatch keeps the four-route map and rejects strictly', async () => {
  const tampered = payload();
  tampered.session.body.principal_id = 'principal-other';
  await assert.rejects(() => readCancelEvidence(fakePage(tampered), reference, receipt), (error: any) => {
    assert.deepEqual(error.http, validationHttp);
    assert.equal(error.code, 'ERR_ASSERTION');
    return true;
  });
});

test('a current principal mismatch keeps the four-route map and rejects strictly', async () => {
  const tampered = payload();
  tampered.current.body.principal_id = 'principal-other';
  await assert.rejects(() => readCancelEvidence(fakePage(tampered), reference, receipt), (error: any) => {
    assert.deepEqual(error.http, validationHttp);
    return true;
  });
});

test('an original receipt id mismatch keeps the four-route map and rejects strictly', async () => {
  const tampered = payload();
  tampered.receipt.body.receipt.id = 'receipt-other';
  await assert.rejects(() => readCancelEvidence(fakePage(tampered), reference, receipt), (error: any) => {
    assert.deepEqual(error.http, validationHttp);
    return true;
  });
});

test('changed original receipt facts keep the four-route map and reject strictly', async () => {
  const tampered = payload();
  tampered.receipt.body.receipt.message = 'different message';
  await assert.rejects(() => readCancelEvidence(fakePage(tampered), reference, receipt), (error: any) => {
    assert.deepEqual(error.http, validationHttp);
    return true;
  });
});

test('control: a clean read still returns the evidence together with its route map', async () => {
  const evidence = await readCancelEvidence(fakePage(payload()), reference, receipt);
  assert.deepEqual(evidence.http, validationHttp);
  assert.equal(evidence.receipt.id, reference.cancel_id);
  assert.equal(evidence.protocol, 'acceptance.cancel-receipt.v1');
});

test('control: a clean read with a newer work version still passes', async () => {
  const newer = payload();
  newer.work.body.version = 99;
  const evidence = await readCancelEvidence(fakePage(newer), reference, receipt);
  assert.equal(evidence.http.work.status, 200);
});