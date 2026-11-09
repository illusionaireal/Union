// Assert existing public facts; never read files, replay work or dispatch a model.
const assert = require('node:assert/strict');

function verifyMaterialRead(snapshot, reference, result, material) {
  const {organization_id, work_id} = reference;
  assert.equal(snapshot?.protocol, 'core.work.v1', 'material snapshot protocol');
  assert.equal(snapshot.organization_id, organization_id, 'material snapshot original AU');
  assert.ok(snapshot.access?.principal_id, 'material snapshot authenticated principal');
  const works = snapshot.works.filter(work => work.id === work_id);
  assert.equal(works.length, 1, 'material read belongs to exactly one original Work');
  const work = works[0];
  assert.ok(Array.isArray(work.tool_calls), 'persisted original tool receipts');
  const ids = work.tool_calls.map(call => call.step_ref);
  assert.ok(ids.every(id => typeof id === 'string' && id.trim()), 'tool receipt identities');
  assert.equal(new Set(ids).size, ids.length, 'unique original tool receipt identities');
  const reads = work.tool_calls.filter(call => call.tool === 'read_document'
    && call.arguments?.path === material.path);
  assert.equal(reads.length, 1, 'exactly one original material read');
  const read = reads[0];
  assert.equal(read.sha256, material.sha256, 'read the original material digest');
  assert.equal(read.bytes, material.bytes, 'read the original material UTF-8 bytes');
  assert.ok(result.sources.includes(read.step_ref), 'original candidate cites its material receipt');
  assert.equal(work.attempts.filter(attempt => attempt.id === read.attempt_id).length, 1,
    'material receipt belongs to an original attempt');
  const requests = work.steps.filter(step => step.attempt_id === read.attempt_id
    && step.status === 'used' && step.command_id && step.model_request_id);
  assert.ok(requests.length > 0, 'material receipt has an executed automatic request');
  return {protocol:'acceptance.material-read.v1', organization_id, work_id,
    principal_id:snapshot.access.principal_id, result_id:result.id,
    tool_receipt_id:read.step_ref, attempt_id:read.attempt_id,
    path:material.path, sha256:read.sha256, bytes:read.bytes};
}

module.exports = {verifyMaterialRead};
