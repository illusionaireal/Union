import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';

// The module tests cover the facts builder; this test covers the driver wiring itself, so a
// silent break (wrong file name, dropped write, reordered block) cannot slip through until a
// real run. It executes the exact driver region with a controlled context.
const driverPath = new URL('../scripts/exit22b_page.cjs', import.meta.url);
const source = readFileSync(driverPath, 'utf8');
const requireDriver = createRequire(driverPath);

function region() {
  const start = source.indexOf("check('an unknown settlement keeps the budget reserved'");
  const end = source.indexOf('// Persisted facts must survive');
  assert.ok(start > 0, 'driver start marker exists');
  assert.ok(end > start, 'driver end marker after start');
  return source.slice(start, end);
}

function execute({ step, work, cancelReceipt }) {
  const files = new Map<string, any>();
  const checks: Array<{ label: string; passed: boolean }> = [];
  const fs = { writeFileSync: (name: string, text: string) => files.set(name.split('/').at(-1)!, JSON.parse(text)) };
  const path = { join: (...parts: string[]) => parts.join('/') };
  const run = new Function('fs', 'path', 'output', 'check', 'require', 'step', 'work', 'cancelReceipt',
    region());
  run(fs, path, 'out', (label: string, passed = true) => checks.push({ label, passed }),
    requireDriver, step, work, cancelReceipt);
  return { files, checks };
}

const receipt = { id: 'cancel-1', status: 'succeeded', message: 'delivered', cancel_accepted: true };
const step = { step_ref: 'step-1', status: 'unknown', reason: 'interrupted', usage: null, cost_status: 'unknown' };
const work = { id: 'work-1', budget: { max_calls: 3, used: 0, reserved: 1 } };

test('the driver writes cancel-facts.json with the three separate facts', () => {
  const { files, checks } = execute({ step, work, cancelReceipt: receipt });
  const facts = files.get('cancel-facts.json');
  assert.ok(facts, 'cancel-facts.json written');
  assert.equal(facts.protocol, 'acceptance.cancel-facts.v1');
  assert.equal(facts.local_acceptance.accepted, true);
  assert.equal(facts.modeld_settlement.step_status, 'unknown');
  assert.equal(facts.modeld_settlement.interrupted, true);
  assert.equal(facts.remote_fact.status, 'unknown');
  assert.equal(facts.reservation.reserved, 1);
  // The region still runs its own settlement checks.
  assert.equal(checks.length, 1);
});

test('the wiring keeps its guard so a partial review context cannot throw', () => {
  // Review harnesses execute this region without cancelReceipt; the guard must skip the write.
  const files = new Map<string, any>();
  const fs = { writeFileSync: (name: string, text: string) => files.set(name.split('/').at(-1)!, JSON.parse(text)) };
  const path = { join: (...parts: string[]) => parts.join('/') };
  const run = new Function('fs', 'path', 'output', 'check', 'require', 'step', 'work',
    region());
  assert.doesNotThrow(() => run(fs, path, 'out', () => {}, requireDriver, step, work));
  assert.equal(files.size, 0);
});
