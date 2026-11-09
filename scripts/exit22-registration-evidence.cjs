// Acceptance helper: only actual Core controls write; observation uses original IDs.
const assert = require('node:assert/strict');

function validateReceipt(response, command, scope) {
  assert.equal(response.status, 200, 'original receipt HTTP');
  const r = response.body?.receipt;
  assert.ok(r, 'original receipt exists');
  for (const key of ['id', 'kind', 'organization_id', 'base_version'])
    assert.equal(r[key], command[key], 'original receipt ' + key);
  assert.equal(r.actor_principal_id, scope.principal_id, 'original receipt principal');
  assert.equal(r.status, 'succeeded', 'original command succeeded');
  assert.ok(Number.isSafeInteger(r.version) && r.version >= command.base_version, 'receipt version');
  if (command.kind === 'start_work') assert.equal(r.work_id, command.data.work_id, 'registered Work');
  else {
    assert.equal(command.kind, 'start_attempt');
    assert.ok(r.attempt?.id, 'original attempt');
    assert.equal(r.attempt.status, 'running');
    assert.equal(r.attempt.owner_principal_id, scope.principal_id);
  }
  return r;
}

function validateRegistered(read, command, scope, input, prepared) {
  assert.equal(read.protocol, 'core.work.v1');
  assert.equal(read.organization_id, scope.organization_id);
  assert.equal(read.access?.principal_id, scope.principal_id);
  assert.equal(read.works.length, 1, 'one original acceptance Work');
  const w = read.works[0], d = command.data;
  assert.equal(w.id, d.work_id);
  assert.equal(d.connection_id, input.connection_id, 'original adopted connection');
  assert.equal(d.expected_revision, input.expected_revision, 'original adopted revision');
  for (const key of ['title', 'goal', 'materials_root', 'max_calls']) {
    assert.equal(d[key], input[key], 'submitted ' + key);
    assert.equal(w[key], input[key], 'persisted ' + key);
  }
  assert.equal(w.responsible.member_id, d.member_id);
  assert.equal(w.responsible.binding_id, d.binding_id);
  assert.equal(w.responsible.name, input.member_name);
  assert.equal(w.definition.id, d.definition_id);
  assert.equal(w.definition.version, 1);
  assert.equal(w.definition.connection_id, d.connection_id);
  assert.deepEqual([...d.tools].sort(), [...input.tools].sort());
  assert.deepEqual([...w.definition.tools].sort(), [...input.tools].sort());
  assert.equal(w.mandate.id, d.mandate_id);
  assert.equal(w.mandate.version, 1);
  assert.equal(w.mandate.active, true);
  assert.equal(w.materials.available, true);
  assert.equal(w.budget.max_calls, input.max_calls);
  assert.equal(w.budget.reserved, 0);
  assert.equal(w.budget.used, 0);
  assert.equal(w.steps.length, 0, 'no model request before explicit run');
  assert.equal(w.results.length, 0);
  assert.equal(w.attempts.length, prepared ? 1 : 0);
  if (prepared) {
    assert.equal(w.attempts[0].id, prepared.attempt.id, 'prepared original attempt');
    assert.equal(w.attempts[0].owner_principal_id, scope.principal_id);
    assert.equal(w.attempts[0].status, 'running');
  }
  return w;
}

async function registerAndPrepare(page, auId, input) {
  let scope;
  const read = async () => {
    const value = await page.evaluate(async id => {
      const get = async url => { const r = await fetch(url); return {status:r.status, body:await r.json()}; };
      const session = await get('/api/session');
      const work = await get('/api/v1/work?organization_id=' + encodeURIComponent(id));
      const current = await get('/api/session');
      return {session, work, current};
    }, auId);
    for (const s of [value.session, value.current]) {
      assert.equal(s.status, 200, 'authenticated Core session');
      assert.equal(s.body?.core_protocol, 'core.au.v1');
      assert.ok(s.body.principal_id && s.body.service_instance);
      scope ??= {organization_id:auId, principal_id:s.body.principal_id, service_instance:s.body.service_instance};
      assert.equal(s.body.principal_id, scope.principal_id, 'same principal');
      assert.equal(s.body.service_instance, scope.service_instance, 'same service');
    }
    assert.equal(value.work.status, 200, 'current Work HTTP');
    assert.equal(value.work.body.protocol, 'core.work.v1');
    assert.equal(value.work.body.organization_id, auId);
    assert.equal(value.work.body.access?.principal_id, scope.principal_id);
    return value.work.body;
  };
  const before = await read();
  assert.equal(before.works.length, 0, 'registration starts without a prepared Work');
  const commands = [];
  const capture = request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands')
      commands.push(request.postDataJSON());
  };
  page.on('request', capture);
  try {
    await page.getByText('登记新的 AI 工作', {exact:true}).click();
    for (const [label, value] of [['工作标题',input.title],['目标',input.goal],
      ['负责 AI 成员名称',input.member_name],['资料目录引用',input.materials_root],['调用上限',String(input.max_calls)]])
      await page.getByLabel(label, {exact:true}).fill(value);
    for (const tool of ['read_document','list_documents'])
      await page.getByLabel(tool, {exact:true}).setChecked(input.tools.includes(tool));
    const [registrationRequest] = await Promise.all([
      page.waitForRequest(r => r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/work/commands'
        && r.postDataJSON()?.kind === 'start_work'),
      page.getByRole('button', {name:'登记 AI 工作',exact:true}).click(),
    ]);
    // A stored reference appears before dispatch; wait for this transmission,
    // including a lost response, before refreshing to query the original ID.
    const postResponse = await registrationRequest.response();
    if (postResponse) await postResponse.finished();
    await page.getByRole('button', {name:'查询登记原请求',exact:true}).waitFor();
    assert.equal(commands.length, 1, 'one page registration POST');
    const original = commands[0];
    assert.equal(original.kind, 'start_work');
    assert.equal(original.organization_id, auId);
    assert.ok(original.id && original.data?.work_id);
    assert.ok(Number.isSafeInteger(original.base_version) && original.base_version >= 0);
    // Reload deliberately discards the POST result. Recovery must use the stored ID.
    await page.reload();
    const [response] = await Promise.all([
      page.waitForResponse(r => {
        const url = new URL(r.url());
        return r.request().method() === 'GET' && url.pathname === '/api/v1/governance/receipts'
          && url.searchParams.get('organization_id') === auId && url.searchParams.get('id') === original.id;
      }),
      page.getByRole('button', {name:'查询登记原请求',exact:true}).click(),
    ]);
    const registration = validateReceipt({status:response.status(), body:await response.json()}, original, scope);
    await page.getByText(/^登记已记录 ·/).waitFor();
    validateRegistered(await read(), original, scope, input);
    assert.equal(commands.length, 1, 'reopen only queries the original registration');
    const card = page.locator('[data-work=' + JSON.stringify(original.data.work_id) + ']');
    const [attemptResponse] = await Promise.all([
      page.waitForResponse(r => r.request().method() === 'POST'
        && new URL(r.url()).pathname === '/api/v1/work/commands'
        && r.request().postDataJSON()?.kind === 'start_attempt'),
      card.getByRole('button', {name:'准备本轮执行',exact:true}).click(),
    ]);
    assert.equal(commands.length, 2, 'one registration and one preparation');
    const attempt = commands[1];
    assert.equal(attempt.kind, 'start_attempt');
    assert.equal(attempt.organization_id, auId);
    assert.equal(attempt.data.work_id, original.data.work_id);
    assert.ok(attempt.id && attempt.id !== original.id);
    assert.ok(Number.isSafeInteger(attempt.base_version) && attempt.base_version >= registration.version);
    const prepared = validateReceipt({status:attemptResponse.status(), body:await attemptResponse.json()}, attempt, scope);
    validateRegistered(await read(), original, scope, input, prepared);
    await card.getByRole('button', {name:'运行 AI 工作',exact:true}).waitFor();
    return {...scope, work_id:original.data.work_id, attempt_id:prepared.attempt.id,
      commands:commands.map(({id,kind,base_version}) => ({id,kind,base_version})),
      registration_version:registration.version, preparation_version:prepared.version};
  } finally { page.off('request', capture); }
}

module.exports = { registerAndPrepare, validateReceipt, validateRegistered };
