// Read-only original cancel evidence. Does not issue or replay commands.
const assert = require('node:assert/strict');

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}

async function readCancelEvidence(page, reference, expectedReceipt) {
  for (const key of ['organization_id', 'work_id', 'cancel_id', 'principal_id',
    'step_ref', 'attempt_id', 'command_id', 'model_request_id']) {
    assert.ok(typeof reference[key] === 'string' && reference[key].trim(), 'original cancel reference ' + key);
  }
  assert.ok(reference.connection && typeof reference.connection === 'object', 'original connection');
  let response;
  try {
    response = await page.evaluate(async ref => {
      const read = async url => {
        const r = await fetch(url);
        return { status: r.status, body: await r.json() };
      };
      const query = new URLSearchParams({ organization_id: ref.organization_id });
      const session = await read('/api/session');
      const work = await read('/api/v1/work?' + query);
      query.set('id', ref.cancel_id);
      const receipt = await read('/api/v1/governance/receipts?' + query);
      const current = await read('/api/session');
      return { session, work, receipt, current };
    }, reference);
  } catch (error) {
    // Transport/JSON interruption: keep a structured diagnostic, never an invented outcome.
    const failure = new Error('original cancel evidence transport failure: '
      + String((error && error.message) || error));
    failure.http = null;
    failure.route = null;
    failure.status = null;
    failure.code = 'transport_error';
    throw failure;
  }
  // Record every route outcome before asserting, so a failure can be attributed to
  // the exact route, status and Core error code instead of a bare status mismatch.
  const routes = {
    session: '/api/session', work: '/api/v1/work',
    receipt: '/api/v1/governance/receipts', current: '/api/session',
  };
  const observedStatus = key => {
    const value = response && response[key];
    return value && typeof value.status === 'number' ? value.status : null;
  };
  const http = Object.fromEntries(Object.entries(routes)
    .map(([key, route]) => [key, { route, status: observedStatus(key) }]));
  for (const [key, route] of Object.entries(routes)) {
    const value = (response && response[key]) || {};
    if (value.status !== 200) {
      const code = value.status === undefined || value.status === null
        ? 'unknown_shape'
        : ((value.body && (value.body.code || value.body.error)) || '');
      const error = new Error('original cancel evidence ' + key + ' read failed: ' + route
        + ' HTTP ' + String(value.status) + (code ? ' ' + code : ''));
      // Keep every completed route outcome on the error so a durable failure archive can
      // record them; the map holds routes, statuses and Core codes only - never bodies.
      error.http = http;
      error.route = route;
      error.status = value.status === undefined ? null : value.status;
      error.code = code || null;
      throw error;
    }
  }
  const { session, current } = response;
  let receipt;
  try {
    for (const value of [session.body, current.body]) {
    assert.equal(value?.core_protocol, 'core.au.v1');
    assert.equal(value.principal_id, reference.principal_id, 'original cancel principal');
    assert.ok(typeof value.service_instance === 'string' && value.service_instance, 'current Core service');
  }
  assert.equal(current.body.service_instance, session.body.service_instance, 'service changed during cancel read');
  const work = response.work.body;
  assert.equal(work?.protocol, 'core.work.v1');
  assert.equal(work.organization_id, reference.organization_id);
  assert.equal(work.access?.principal_id, reference.principal_id);
  assert.ok(Number.isSafeInteger(work.version) && work.version >= 0, 'current Work version');
  assert.ok(Array.isArray(work.works), 'Core Work list');
  const matches = work.works.filter(w => w.id === reference.work_id);
  assert.equal(matches.length, 1, 'exactly one original Work');
  assert.ok(Array.isArray(matches[0].steps), 'original Work steps');
  const steps = matches[0].steps.filter(s => s.step_ref === reference.step_ref);
  assert.equal(steps.length, 1, 'exactly one original step');
  for (const key of ['attempt_id', 'command_id', 'model_request_id']) {
    assert.equal(steps[0][key], reference[key], 'original step ' + key);
  }
  assert.deepEqual(canonical(steps[0].connection), canonical(reference.connection), 'original step connection');
  receipt = response.receipt.body?.receipt;
  assert.ok(receipt, 'original cancel receipt exists');
  for (const [key, value] of Object.entries({ id: reference.cancel_id, organization_id: reference.organization_id,
    actor_principal_id: reference.principal_id, kind: 'cancel_step', status: 'succeeded', effect: 'applied',
    model_request_id: reference.model_request_id, cancel_accepted: true })) {
    assert.equal(receipt[key], value, 'original cancel receipt ' + key);
  }
  assert.equal(receipt.step?.step_ref, reference.step_ref);
  assert.equal(receipt.step?.model_request_id, reference.model_request_id);
  assert.deepEqual(canonical(receipt.cancel_connection), canonical(reference.connection), 'original cancel connection');
  assert.ok(Number.isSafeInteger(receipt.base_version) && receipt.base_version >= 0
    && Number.isSafeInteger(receipt.version) && receipt.version > receipt.base_version, 'original cancel versions');
  assert.equal(receipt.delivery?.cancel_accepted, true, 'durable cancel delivery');
  assert.equal(receipt.delivery.message, receipt.message, 'consistent delivery observation');
  assert.deepEqual(canonical(receipt), canonical(expectedReceipt), 'original cancel receipt facts changed');
  } catch (error) {
    // Every GET above returned 200, so the safe route map is already known: a later strict
    // validation rejection must keep it and must rethrow the original error unchanged.
    if (error && typeof error === 'object') {
      if (!error.http) error.http = http;
      if (error.route === undefined) error.route = null;
      if (error.status === undefined) error.status = null;
      if (!error.code) error.code = 'validation_failed';
    }
    throw error;
  }
  return { protocol: 'acceptance.cancel-receipt.v1', reference, service_instance: session.body.service_instance,
    http, receipt };
}

module.exports = { readCancelEvidence };
