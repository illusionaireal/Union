import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// Records whether reopening the same work dispatched anything new. Read-only inputs.
const requireHelper = createRequire(new URL('../scripts/exit22-replay-observation.cjs', import.meta.url));
const { recordReplayObservation } = requireHelper('../scripts/exit22-replay-observation.cjs');

function harness() {
  const files = new Map<string, any>();
  const checks: Array<{ label: string; passed: boolean }> = [];
  return {
    files, checks,
    deps: {
      fs: { writeFileSync: (name: string, text: string) => files.set(name.split('/').at(-1)!, JSON.parse(text)) },
      path: { join: (...parts: string[]) => parts.join('/') },
      output: 'out',
      workId: 'work-original',
      check: (label: string, passed = true) => checks.push({ label, passed }),
    },
  };
}

function workBody(attempts: string[], modelRequests: string[], used: number) {
  return {
    protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
    access: { principal_id: 'principal-original' },
    works: [{ id: 'work-original', budget: { max_calls: 3, used, reserved: 1 }, attempts: [],
      steps: modelRequests.map((id, index) => ({ step_ref: 'step-' + (index + 1), attempt_id: attempts[0],
        command_id: 'loop-t' + (index + 1), model_request_id: id, status: 'unknown', usage: null,
        cost_status: 'unknown', reason: 'interrupted', connection: { id: 'c', revision: 1 } })),
      results: [] }],
  };
}

test('an unchanged reopen records unchanged state and claims no passing check', () => {
  const { deps, files, checks } = harness();
  recordReplayObservation({ ...deps, before: workBody(['work-original#a1'], ['model-1'], 0),
    after: workBody(['work-original#a1'], ['model-1'], 0) });
  const record = files.get('replay-observation.json');
  assert.equal(record.status, 'unchanged');
  assert.equal(record.dispatch_count, null);
  assert.ok(!('new_dispatches' in record));
  // Unchanged persisted state is not proof that reopening dispatched nothing.
  assert.equal(checks.length, 0);
});

test('a missing before side is recorded as unavailable without claiming zero', () => {
  const { deps, files, checks } = harness();
  recordReplayObservation({ ...deps, before: { code: 'unsupported_capability' },
    after: workBody(['work-original#a1'], ['model-1'], 0) });
  const record = files.get('replay-observation.json');
  assert.equal(record.status, 'unavailable');
  assert.equal(record.new_dispatches, null);
  assert.match(record.reason, /before snapshot/);
  assert.equal(checks.length, 0);
});

test('a new dispatch after reopen writes a failed record and a failing check', () => {
  const { deps, files, checks } = harness();
  recordReplayObservation({ ...deps, before: workBody(['work-original#a1'], ['model-1'], 0),
    after: workBody(['work-original#a1'], ['model-1', 'model-2'], 0) });
  const record = files.get('replay-observation.json');
  assert.equal(record.status, 'failed');
  assert.match(record.reason, /model requests 1 -> 2/);
  assert.equal(checks.length, 1);
  assert.equal(checks[0].passed, false);
});
