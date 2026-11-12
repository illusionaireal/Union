import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// The card asks for three separate facts: local acceptance, modeld settlement and the
// remote fact. The remote fact can never be proven from this machine.
const requireFacts = createRequire(new URL('../scripts/exit22-cancel-facts.cjs', import.meta.url));
const { buildCancelFacts } = requireFacts('../scripts/exit22-cancel-facts.cjs');

function receipt(overrides: any = {}) {
  return { id: 'cancel-1', status: 'succeeded', message: 'delivered', cancel_accepted: true,
    kind: 'cancel_step', effect: 'applied', ...overrides };
}

function step(overrides: any = {}) {
  return { step_ref: 'step-1', model_request_id: 'model-1', attempt_id: 'attempt-1',
    status: 'unknown', reason: 'interrupted', usage: null, cost_status: 'unknown', ...overrides };
}

function work(overrides: any = {}) {
  return { id: 'work-1', budget: { max_calls: 3, used: 0, reserved: 1 }, ...overrides };
}

test('an accepted cancel with an interrupted step keeps the three facts separate', () => {
  const facts = buildCancelFacts({ receipt: receipt(), step: step(), work: work() });
  assert.equal(facts.protocol, 'acceptance.cancel-facts.v1');
  assert.deepEqual(facts.local_acceptance,
    { accepted: true, receipt_id: 'cancel-1', status: 'succeeded', delivery_message: 'delivered' });
  assert.equal(facts.modeld_settlement.step_status, 'unknown');
  assert.equal(facts.modeld_settlement.interrupted, true);
  assert.equal(facts.modeld_settlement.reason, 'interrupted');
  assert.equal(facts.remote_fact.status, 'unknown');
});

test('a settled used step is not reported as interrupted and keeps its usage', () => {
  const facts = buildCancelFacts({ receipt: receipt(),
    step: step({ status: 'used', reason: null, usage: { input_tokens: 5, output_tokens: 7 }, cost_status: 'recorded' }),
    work: work({ budget: { max_calls: 3, used: 1, reserved: 0 } }) });
  assert.equal(facts.modeld_settlement.interrupted, false);
  assert.deepEqual(facts.modeld_settlement.usage, { input_tokens: 5, output_tokens: 7 });
  assert.equal(facts.modeld_settlement.cost_status, 'recorded');
  assert.equal(facts.reservation.used, 1);
  assert.equal(facts.reservation.reserved, 0);
});

test('the remote fact stays unknown and is never upgraded by a local acceptance', () => {
  const facts = buildCancelFacts({ receipt: receipt(), step: step(), work: work() });
  assert.equal(facts.remote_fact.status, 'unknown');
  assert.match(facts.remote_fact.reason, /本地|本机/);
  assert.ok(!('remote_stopped' in facts));
  assert.ok(!('cancelled_remote' in facts));
});

test('a missing step is recorded as not observed instead of being invented', () => {
  const facts = buildCancelFacts({ receipt: receipt(), step: null, work: work() });
  assert.equal(facts.modeld_settlement.observed, false);
  assert.equal(facts.modeld_settlement.step_status, null);
  assert.equal(facts.modeld_settlement.interrupted, null);
  assert.equal(facts.remote_fact.status, 'unknown');
});
