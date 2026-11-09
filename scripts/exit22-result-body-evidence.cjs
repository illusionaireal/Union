// Read-only acceptance evidence; never replay work or return a cached body.
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');

async function readResultBody(page, reference, expected) {
  const { organization_id, work_id, principal_id } = reference;
  assert.ok(organization_id && work_id && principal_id && expected?.id, 'original result reference');
  const value = await page.evaluate(async ref => {
    const read = async url => {
      const response = await fetch(url);
      return { status: response.status, body: await response.json() };
    };
    const session = await read('/api/session');
    if (session.status !== 200 || session.body?.core_protocol !== 'core.au.v1'
      || session.body.principal_id !== ref.principal_id || !session.body.service_instance)
      throw Error('original result requires the current authenticated principal');
    const result = await read('/api/v1/work/results?organization_id=' + encodeURIComponent(ref.organization_id)
      + '&work_id=' + encodeURIComponent(ref.work_id) + '&id=' + encodeURIComponent(ref.result_id));
    const current = await read('/api/session');
    return {session, result, current};
  }, {organization_id, work_id, principal_id, result_id: expected.id});
  for (const session of [value.session, value.current]) {
    assert.equal(session.status, 200, 'reopened result current session HTTP');
    assert.equal(session.body?.core_protocol, 'core.au.v1', 'reopened result session protocol');
    assert.equal(session.body.principal_id, principal_id, 'reopened result original principal');
    assert.ok(session.body.service_instance, 'reopened result current service');
    assert.equal(session.body.service_instance, value.session.body.service_instance,
      'service remains current during original result read');
  }
  assert.equal(value.result.status, 200, 'reopened original result HTTP');
  const body = value.result.body;
  assert.equal(body?.protocol, 'core.work.v1', 'reopened result protocol');
  assert.equal(body.organization_id, organization_id, 'reopened result original AU');
  assert.equal(body.work_id, work_id, 'reopened result original Work');
  assert.deepEqual(JSON.parse(JSON.stringify(body.result)), JSON.parse(JSON.stringify(expected)),
    'reopened result preserves the complete original metadata');
  assert.equal(typeof body.content, 'string', 'reopened original body exists');
  const bytes = Buffer.byteLength(body.content, 'utf8');
  const sha256 = createHash('sha256').update(body.content, 'utf8').digest('hex');
  assert.equal(sha256, expected.sha256, 'reopened original body digest');
  assert.equal(bytes, expected.bytes, 'reopened original UTF-8 body bytes');
  return {protocol:'acceptance.result-body.v1', organization_id, work_id,
    result_id:expected.id, principal_id, service_instance:value.session.body.service_instance,
    sha256, bytes};
}

module.exports = {readResultBody};
