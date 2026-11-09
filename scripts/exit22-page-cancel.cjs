// Acceptance action: the Core page owns the sole POST and original-ID recovery.
const assert = require('node:assert/strict');
const {readCancelEvidence} = require('./exit22-cancel-evidence.cjs');

function validateCancelCommand(command, reference, version) {
  assert.ok(typeof command.id === 'string' && command.id.trim(), 'page cancel command ID');
  assert.equal(command.kind, 'cancel_step');
  assert.equal(command.organization_id, reference.organization_id, 'page cancel AU');
  assert.equal(command.data?.work_id, reference.work_id, 'page cancel Work');
  assert.equal(command.data?.step_id, reference.step_ref, 'page cancel step');
  assert.ok(Number.isSafeInteger(command.base_version) && command.base_version >= version, 'page cancel version');
}

function validateCancelReceipt(response, command, reference) {
  assert.equal(response.status, 200, 'page cancel receipt HTTP');
  const r = response.body?.receipt;
  assert.ok(r, 'page cancel receipt exists');
  for (const key of ['id', 'kind', 'organization_id', 'base_version'])
    assert.equal(r[key], command[key], 'page cancel receipt ' + key);
  assert.equal(r.actor_principal_id, reference.principal_id, 'page cancel receipt principal');
  assert.equal(r.status, 'succeeded', 'page cancel command succeeded');
  assert.equal(r.effect, 'applied');
  assert.ok(Number.isSafeInteger(r.version) && r.version > command.base_version, 'page cancel receipt version');
  assert.equal(r.step?.step_ref, reference.step_ref, 'page cancel receipt step');
  assert.equal(r.model_request_id, reference.model_request_id, 'page cancel model request');
  assert.equal(r.cancel_accepted, true, 'page cancel delivery accepted');
  return r;
}

async function cancelFromPage(page, reference) {
  for (const key of ['organization_id', 'work_id', 'step_ref', 'attempt_id', 'command_id',
    'model_request_id', 'principal_id', 'service_instance'])
    assert.ok(typeof reference[key] === 'string' && reference[key].trim(), 'observed original ' + key);
  const read = async () => {
    const value = await page.evaluate(async ref => {
      const get = async url => {const r = await fetch(url); return {status:r.status, body:await r.json()};};
      const session = await get('/api/session');
      const work = await get('/api/v1/work?organization_id=' + encodeURIComponent(ref.organization_id));
      const current = await get('/api/session');
      return {session, work, current};
    }, reference);
    for (const s of [value.session, value.current]) {
      assert.equal(s.status, 200, 'current cancel session HTTP');
      assert.equal(s.body?.core_protocol, 'core.au.v1');
      assert.equal(s.body.principal_id, reference.principal_id, 'observed cancel principal');
      assert.equal(s.body.service_instance, reference.service_instance, 'observed cancel service');
    }
    assert.equal(value.work.status, 200, 'current cancel Work HTTP');
    const w = value.work.body;
    assert.equal(w.protocol, 'core.work.v1');
    assert.equal(w.organization_id, reference.organization_id);
    assert.equal(w.access?.principal_id, reference.principal_id);
    const matches = w.works.filter(v => v.id === reference.work_id);
    assert.equal(matches.length, 1, 'one original cancellation Work');
    const steps = matches[0].steps.filter(s => s.step_ref === reference.step_ref);
    assert.equal(steps.length, 1, 'one original cancellation step');
    for (const key of ['attempt_id', 'command_id', 'model_request_id'])
      assert.equal(steps[0][key], reference[key], 'observed cancel ' + key);
    assert.deepEqual(steps[0].connection, reference.connection, 'observed cancel connection');
    return {work:w, step:steps[0]};
  };
  const before = await read();
  assert.equal(before.step.status, 'reserved', 'observed request is still in flight');
  const card = page.locator('[data-work=' + JSON.stringify(reference.work_id) + ']');
  const button = card.getByRole('button', {name:'取消本次执行', exact:true});
  await button.waitFor();
  assert.equal(await button.isEnabled(), true, 'original page cancel is enabled');
  const requests = [];
  let settle;
  const ended = new Promise(resolve => { settle = resolve; });
  const capture = r => {
    if (r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/work/commands') requests.push(r);
  };
  const finish = r => {
    if (requests.includes(r) && r.postDataJSON()?.kind === 'cancel_step') settle(r);
  };
  page.on('request', capture);
  page.on('requestfinished', finish);
  page.on('requestfailed', finish);
  try {
    const [request] = await Promise.all([
      page.waitForRequest(r => r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/work/commands'
        && r.postDataJSON()?.kind === 'cancel_step'), button.click(),
    ]);
    const command = request.postDataJSON();
    validateCancelCommand(command, reference, before.work.version);
    // Playwright's response.finished() may never resolve for a failed body.
    // Observe either terminal request event, installed before the click.
    assert.equal(await ended, request, 'original cancel transmission ended');
    // A lost response ends this transmission. Never issue a substitute cancel.
    const post = await request.response();
    let submittedReceipt;
    if (post) {
      assert.equal(post.status(), 200, 'page cancel receipt HTTP');
      if (!request.failure())
        submittedReceipt = validateCancelReceipt({status:post.status(), body:await post.json()}, command, reference);
    }
    const group = () => card.getByRole('group', {name:'原取消请求', exact:true});
    await group().waitFor();
    assert.ok((await group().innerText()).includes(command.id), 'page retains the original cancel ID');
    await page.reload();
    await group().waitFor();
    assert.ok((await group().innerText()).includes(command.id), 'reopened page retains original cancel ID');
    const [response] = await Promise.all([
      page.waitForResponse(r => {
        const url = new URL(r.url());
        return r.request().method() === 'GET' && url.pathname === '/api/v1/governance/receipts'
          && url.searchParams.get('organization_id') === reference.organization_id
          && url.searchParams.get('id') === command.id;
      }), group().getByRole('button', {name:'查询原请求', exact:true}).click(),
    ]);
    const receipt = validateCancelReceipt({status:response.status(), body:await response.json()}, command, reference);
    if (submittedReceipt) assert.deepEqual(receipt, submittedReceipt, 'original POST and GET cancel facts');
    await read(); // Identity must still match the reader who observed the output.
    await readCancelEvidence(page, {...reference, cancel_id:command.id}, receipt);
    await read();
    assert.equal(requests.length, 1, 'one page cancel POST; recovery performs only GET');
    return {command, receipt};
  } finally {
    page.off('request', capture);
    page.off('requestfinished', finish);
    page.off('requestfailed', finish);
  }
}

module.exports = {cancelFromPage, validateCancelCommand, validateCancelReceipt};
