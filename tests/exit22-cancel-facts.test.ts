import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// The card asks for three separate facts: local acceptance, how the supervised step
// settled locally, and the remote fact. A local Work step in `unknown` is not a modeld
// interruption receipt, so the interrupted flag must stay unknown unless an explicit
// validated receipt is supplied (review recheck-f5ebff8-20261113, cancel-facts-contract).
const requireFacts = createRequire(new URL('../scripts/exit22-cancel-facts.cjs', import.meta.url));
const { buildCancelFacts } = requireFacts('../scripts/exit22-cancel-facts.cjs');

function receipt(overrides: any = {}) {
  return { id: 'cancel-1', status: 'succeeded', message: 'delivered', cancel_accepted: true,
    kind: 'cancel_step', effect: 'applied', ...overrides };
}

function step(overrides: any = {}) {
  return { step_ref: 'step-1', model_request_id: 'model-1', attempt_id: 'attempt-1',
    status: 'unknown', reason: 'work_step_wait_expired', usage: null, cost_status: 'unknown', ...overrides };
}

function work(overrides: any = {}) {
  return { id: 'work-1', budget: { max_calls: 3, used: 0, reserved: 1 }, ...overrides };
}

for (const reason of ['work_step_wait_expired', 'work_step_failed', 'transport connection lost', null, undefined]) {
  test(`a local unknown step (${String(reason)}) never claims a modeld interruption`, () => {
    const facts = buildCancelFacts({ receipt: receipt(), step: step({ reason }), work: work() });
    assert.equal(facts.local_acceptance.accepted, true);
    assert.equal(facts.modeld_settlement.step_status, 'unknown');
    assert.equal(facts.modeld_settlement.reason, reason ?? null);
    assert.equal(facts.modeld_settlement.usage, null);
    assert.equal(facts.reservation.reserved, 1);
    assert.equal(facts.remote_fact.status, 'unknown');
    assert.notEqual(facts.modeld_settlement.interrupted, true);
    assert.equal(facts.modeld_settlement.interrupted, null);
    assert.equal(facts.modeld_settlement.modeld_source, 'unavailable');
  });
}

test('an explicit validated modeld interruption receipt is the only way to claim interrupted', () => {
  const facts = buildCancelFacts({ receipt: receipt(), step: step({ reason: 'work_step_interrupted' }),
    work: work(), modeldReceipt: { status: 'interrupted', model_request_id: 'model-1' } });
  assert.equal(facts.modeld_settlement.interrupted, true);
  assert.equal(facts.modeld_settlement.modeld_source, 'explicit_receipt');
  assert.equal(facts.modeld_settlement.reason, 'work_step_interrupted');
  assert.equal(facts.remote_fact.status, 'unknown');
});

test('a used step reports a completed call without claiming interruption and keeps usage', () => {
  const usage = { input_tokens: 5, output_tokens: 7 };
  const facts = buildCancelFacts({ receipt: receipt(),
    step: step({ status: 'used', reason: null, usage, cost_status: 'recorded' }),
    work: work({ budget: { max_calls: 3, used: 1, reserved: 0 } }) });
  assert.equal(facts.modeld_settlement.interrupted, false);
  assert.deepEqual(facts.modeld_settlement.usage, usage);
  assert.equal(facts.modeld_settlement.cost_status, 'recorded');
  assert.equal(facts.reservation.used, 1);
  assert.equal(facts.reservation.reserved, 0);
});

test('an absent step stays unobserved and never invents a modeld state', () => {
  const facts = buildCancelFacts({ receipt: receipt(), step: null, work: work() });
  assert.equal(facts.modeld_settlement.observed, false);
  assert.equal(facts.modeld_settlement.step_status, null);
  assert.equal(facts.modeld_settlement.interrupted, null);
  assert.equal(facts.modeld_settlement.usage, null);
  assert.equal(facts.modeld_settlement.modeld_source, 'unavailable');
  assert.equal(facts.remote_fact.status, 'unknown');
});

test('the remote fact is never upgraded by local acceptance or a local settlement', () => {
  const facts = buildCancelFacts({ receipt: receipt(), step: step({ status: 'used', usage: {} }), work: work() });
  assert.equal(facts.remote_fact.status, 'unknown');
  assert.match(facts.remote_fact.reason, /远端/);
  assert.ok(!('remote_stopped' in facts));
});
