const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { test } = require('node:test');
const candidate = process.env.UNION_REVIEW_CANDIDATE;
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'source-manifest.json'), 'utf8'));
const unavailable = Object.entries(manifest.files).filter(([name, expected]) =>
  !candidate || !fs.existsSync(path.join(candidate, name)) ||
  createHash('sha256').update(fs.readFileSync(path.join(candidate, name))).digest('hex') !== expected);
if (unavailable.length) {
  console.log(JSON.stringify({ status: 'input_unavailable', tests: 0, files: unavailable.map(([name]) => name) }));
  process.exit(2);
}
const { buildCancelFacts } = require(path.join(candidate, 'scripts/exit22-cancel-facts.cjs'));
const receipt = { id: 'synthetic-cancel', status: 'succeeded', kind: 'cancel_step', effect: 'applied', cancel_accepted: true, message: 'local cancellation accepted' };
const work = { id: 'synthetic-work', budget: { max_calls: 3, used: 1, reserved: 1 } };
const step = { step_ref: 'synthetic-step', model_request_id: 'synthetic-original-request', status: 'unknown', usage: null, cost_status: 'unknown' };
for (const reason of ['work_step_wait_expired', 'work_step_failed', 'transport connection lost', null]) {
  test(`local unknown (${reason}) does not prove modeld interruption`, () => {
    const facts = buildCancelFacts({ receipt, step: { ...step, reason }, work });
    assert.equal(facts.local_acceptance.accepted, true);
    assert.equal(facts.modeld_settlement.step_status, 'unknown');
    assert.equal(facts.modeld_settlement.reason, reason);
    assert.equal(facts.modeld_settlement.usage, null);
    assert.equal(facts.reservation.reserved, 1);
    assert.equal(facts.remote_fact.status, 'unknown');
    assert.notEqual(facts.modeld_settlement.interrupted, true, 'unknown local result must not assert a modeld interrupted receipt');
  });
}
test('control: used step preserves usage without claiming interruption', () => {
  const usage = { input_tokens: 5, output_tokens: 7 };
  const facts = buildCancelFacts({ receipt, step: { ...step, status: 'used', reason: null, usage }, work });
  assert.equal(facts.modeld_settlement.interrupted, false);
  assert.deepEqual(facts.modeld_settlement.usage, usage);
  assert.equal(facts.remote_fact.status, 'unknown');
});
test('control: absent step remains unobserved with unknown usage and remote outcome', () => {
  const facts = buildCancelFacts({ receipt, step: null, work });
  assert.equal(facts.modeld_settlement.observed, false);
  assert.equal(facts.modeld_settlement.interrupted, null);
  assert.equal(facts.modeld_settlement.usage, null);
  assert.equal(facts.remote_fact.status, 'unknown');
});
test('control: explicit interrupted reason is preserved independently of remote outcome', () => {
  const facts = buildCancelFacts({ receipt, step: { ...step, reason: 'work_step_interrupted' }, work });
  assert.equal(facts.modeld_settlement.reason, 'work_step_interrupted');
  assert.equal(facts.modeld_settlement.step_status, 'unknown');
  assert.equal(facts.remote_fact.status, 'unknown');
});
