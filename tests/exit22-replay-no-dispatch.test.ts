import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// The restart helpers are read-only comparisons over already-read Core work bodies.
const requireHelpers = createRequire(new URL('../scripts/exit22-restart-evidence.cjs', import.meta.url));
const { observeNoNewDispatch } = requireHelpers('../scripts/exit22-restart-evidence.cjs');

function workBody(attempts: string[], modelRequests: string[], used: number, reserved: number) {
  return {
    protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
    access: { principal_id: 'principal-original' },
    works: [{
      id: 'work-original',
      budget: { max_calls: 3, used, reserved },
      attempts: attempts.map((id, index) => ({ id, seq: index + 1 })),
      steps: modelRequests.map((modelRequestId, index) => ({
        step_ref: 'step-' + (index + 1), attempt_id: attempts[0], model_request_id: modelRequestId })),
    }],
  };
}

test('an unchanged restart observes zero new dispatches', async () => {
  const before = workBody(['work-original#a1'], ['model-1', 'model-2'], 1, 1);
  const after = workBody(['work-original#a1'], ['model-1', 'model-2'], 1, 1);
  const observation = observeNoNewDispatch(before, after, 'work-original');
  assert.equal(observation.status, 'observed');
  assert.equal(observation.new_dispatches, 0);
  assert.deepEqual(observation.attempts, { before: 1, after: 1 });
  assert.deepEqual(observation.model_requests, { before: 2, after: 2 });
  assert.deepEqual(observation.budget, { before: { used: 1, reserved: 1 }, after: { used: 1, reserved: 1 } });
});

test('a new attempt after restart is rejected as a new dispatch', async () => {
  const before = workBody(['work-original#a1'], ['model-1'], 1, 1);
  const after = workBody(['work-original#a1', 'work-original#a2'], ['model-1', 'model-2'], 1, 1);
  assert.throws(() => observeNoNewDispatch(before, after, 'work-original'),
    /new dispatch after restart: attempts 1 -> 2/);
});

test('a new model request after restart is rejected as a new dispatch', async () => {
  const before = workBody(['work-original#a1'], ['model-1'], 1, 1);
  const after = workBody(['work-original#a1'], ['model-1', 'model-2'], 1, 1);
  assert.throws(() => observeNoNewDispatch(before, after, 'work-original'), /model requests 1 -> 2/);
});

test('an increased used counter is rejected as a new dispatch', async () => {
  const before = workBody(['work-original#a1'], ['model-1'], 1, 1);
  const after = workBody(['work-original#a1'], ['model-1'], 2, 1);
  assert.throws(() => observeNoNewDispatch(before, after, 'work-original'), /budget used 1 -> 2/);
});

test('a missing before side is reported unavailable instead of guessed', async () => {
  const before = { code: 'unsupported_capability', error: '此 AU 尚在准备态，自主行动与资源操作尚未启用' };
  const after = workBody(['work-original#a1'], ['model-1'], 1, 1);
  const observation = observeNoNewDispatch(before, after, 'work-original');
  assert.equal(observation.status, 'unavailable');
  assert.match(observation.reason, /before snapshot/);
  assert.match(observation.reason, /unsupported_capability/);
});
