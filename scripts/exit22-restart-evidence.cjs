// Read-only evidence for the existing bounded acceptance drivers. Never dispatch.
const assert = require('node:assert/strict');

async function readSnapshot(page, auId, workId) {
  const response = await page.evaluate(async id => {
    const read = async url => {
      const r = await fetch(url);
      return { status: r.status, body: await r.json() };
    };
    const session = await read('/api/session');
    const work = await read('/api/v1/work?organization_id=' + encodeURIComponent(id));
    const current = await read('/api/session');
    return { session, work, current };
  }, auId);
  const { session, work, current } = response;
  for (const value of [session, current]) {
    assert.equal(value.status, 200, 'Core session HTTP status');
    assert.equal(value.body?.core_protocol, 'core.au.v1', 'Core session protocol');
    assert.ok(value.body.principal_id && value.body.service_instance, 'authenticated Core identity');
  }
  assert.equal(current.body.principal_id, session.body.principal_id, 'principal changed during snapshot');
  assert.equal(current.body.service_instance, session.body.service_instance, 'service changed during snapshot');
  assert.equal(work.status, 200, 'Core Work snapshot HTTP status');
  const body = work.body;
  assert.equal(body?.protocol, 'core.work.v1', 'Core Work snapshot protocol');
  assert.equal(body.organization_id, auId, 'original AU snapshot');
  assert.equal(body.access?.principal_id, session.body.principal_id, 'snapshot principal');
  assert.ok(Number.isSafeInteger(body.version) && body.version >= 0, 'snapshot version');
  requests(originalWork(body, workId));
  return body;
}

function originalWork(snapshot, workId) {
  assert.ok(Array.isArray(snapshot.works), 'snapshot Work list');
  const matches = snapshot.works.filter(work => work.id === workId);
  assert.equal(matches.length, 1, 'exactly one original Work');
  return matches[0];
}

// Key/list order is transport formatting, not a change of persisted facts.
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}

function requests(work) {
  assert.ok(Array.isArray(work.steps) && work.steps.length > 0, 'original model requests exist');
  const steps = new Set(), ids = new Set();
  const originals = work.steps.map(step => {
    for (const key of ['step_ref', 'attempt_id', 'command_id', 'model_request_id']) {
      assert.ok(typeof step[key] === 'string' && step[key].trim(), 'original request ' + key);
    }
    assert.ok(!steps.has(step.step_ref) && !ids.has(step.model_request_id), 'unique original request identities');
    steps.add(step.step_ref); ids.add(step.model_request_id);
    assert.ok(['used', 'unknown', 'released'].includes(step.status), 'settled original request');
    assert.ok(Object.hasOwn(step, 'usage'), 'explicit request usage, including null');
    if (step.usage !== null) {
      for (const key of ['input_tokens', 'output_tokens']) {
        assert.ok(Number.isSafeInteger(step.usage[key]) && step.usage[key] >= 0, 'known integer usage');
      }
    }
    return Object.fromEntries(['step_ref', 'attempt_id', 'command_id', 'model_request_id',
      'status', 'usage', 'cost_status', 'reason', 'connection'].map(key => [key, step[key]]));
  }).sort((a, b) => a.step_ref.localeCompare(b.step_ref));
  const budget = work.budget;
  assert.ok(budget && Number.isSafeInteger(budget.max_calls) && budget.max_calls > 0,
    'original budget has a positive integer call limit');
  for (const key of ['used', 'reserved']) {
    assert.ok(Number.isSafeInteger(budget[key]) && budget[key] >= 0,
      'original budget has a nonnegative integer ' + key);
  }
  assert.equal(budget.used, originals.filter(step => step.status === 'used').length,
    'original budget counts every used call');
  assert.equal(budget.reserved, originals.filter(step => step.status === 'unknown').length,
    'original budget retains every unknown reservation');
  assert.ok(budget.used + budget.reserved <= budget.max_calls,
    'original budget occupancy stays within its call limit');
  return originals;
}

function compareSnapshots(before, after, auId, workId) {
  for (const snapshot of [before, after]) {
    assert.equal(snapshot?.protocol, 'core.work.v1');
    assert.equal(snapshot.organization_id, auId);
    assert.ok(snapshot.access?.principal_id, 'snapshot authenticated principal');
  }
  assert.equal(after.access.principal_id, before.access.principal_id, 'original principal after restart');
  const original = originalWork(before, workId), reopened = originalWork(after, workId);
  const prior = requests(original), current = requests(reopened);
  assert.deepEqual(canonical(current), canonical(prior), 'restart preserves every original request fact');
  assert.ok(original.budget && reopened.budget, 'original budget exists');
  assert.deepEqual(canonical(reopened.budget), canonical(original.budget), 'restart preserves original budget');
  return { protocol: 'acceptance.restart-requests.v1', organization_id: auId, work_id: workId,
    principal_id: before.access.principal_id, model_request_identity_count: prior.length,
    transport_dispatch_count: null, no_new_request_identity: true, requests: prior,
    budget: original.budget };
}

module.exports = { readSnapshot, compareSnapshots };
