// Page-level 22-C: register work through Core, observe its original model output,
// cancel through the page, then rebuild and query the same durable requests.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const output = process.env.UNION_EXIT22B_UI_EVIDENCE || path.join(os.tmpdir(), 'union-exit22b-ui');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'union-exit22b-'));
const checks = [], errors = [];
function loadJson(name) {
  try { return JSON.parse(fs.readFileSync(process.env[name], 'utf-8')); }
  catch { return null; }
}
const check = (name, value = true) => { assert.ok(value, name); checks.push(name); };
let host, browser, page;
let workId;
const nonce = 'UNION-EXIT22B-' + crypto.randomUUID().slice(0, 8);
const goal = '第一步必须调用 read_document 读取 brief.md 的完整正文；第二步用最终回答写三行中文概览，不要再调用任何工具。';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function snapshot() {
  return require('./exit22-restart-evidence.cjs').readSnapshot(
    page, createdReceipt.organization_id, workId);
}
async function coreWork() {
  return page.evaluate(async () => {
    const id = document.querySelector('#org-select').value;
    return (await fetch('/api/v1/work?organization_id=' + id)).json();
  });
}
async function waitFor(predicate, name, timeout) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await predicate()) { check(name); return; }
    await sleep(2000);
  }
  throw new Error(name + ' timed out');
}
function startHost() {
  const child = spawn(process.env.UNION_PYTHON, ['-X', 'utf8', 'scripts/exit22b_host.py', '--root', temp],
    { cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, UNION_MODELD_CONFIG: process.env.UNION_MODELD_CONFIG } });
  child.stderr.on('data', d => errors.push('host: ' + String(d)));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('host timeout')), 20000);
    readline.createInterface({ input: child.stdout }).once('line', line => {
      clearTimeout(timer); resolve({ child, ...JSON.parse(line) });
    });
  });
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const materials = path.join(temp, 'materials');
  fs.mkdirSync(materials, { recursive: true });
  const document = '# 合成资料\n\n本次页面级验收代号 ' + nonce + '。\n';
  fs.writeFileSync(path.join(materials, 'brief.md'), Buffer.from(document, 'utf8'));
  fs.writeFileSync(path.join(temp, 'document-roots.json'),
    JSON.stringify({ version: 1, roots: { 'project-docs': materials } }));

  let running = await startHost();
  host = running.child;
  browser = await chromium.launch({ executablePath: process.env.UNION_CHROMIUM_PATH, headless: true });
  page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
  page.on('pageerror', e => errors.push('page: ' + e.message));
  // The page needs a real account: first claim the owner account, then log in.
  await page.goto(running.board_url);
  // The ticket session lets the first visitor claim the owner account; after that the
  // account session (cookie) is what authorizes create_v1 and the core reads.
  createdReceipt = await page.evaluate(async () => {
    const status = await (await fetch('/api/auth/status')).json();
    const password = 'Exit22b!Safe9';
    if (!status.configured) {
      const response = await fetch('/api/auth/setup', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'exit22b-owner', password, remember: true }),
      });
      if (!response.ok) throw new Error('setup http ' + response.status + ': ' + (await response.text()).slice(0, 200));
    }
    const login = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'exit22b-owner', password, remember: true }),
    });
    if (!login.ok) throw new Error('login http ' + login.status + ': ' + (await login.text()).slice(0, 200));
    const who = await (await fetch('/api/auth/status')).json();
    if (!who.authenticated) throw new Error('still not authenticated: ' + JSON.stringify(who));
    const create = await fetch('/api/commands', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: crypto.randomUUID(), organization_id: null, base_version: null,
        kind: 'create_v1',
        data: { name: '22B 页面验收组织', goal: '完成一次页面级有界验收', board_name: 'Owner display',
                charter: { text: '测试章程：有限的本地组织协作；无对外发布授权。',
                  allowed_operations: ['create_member', 'create_position', 'update_position', 'assign', 'set_policy',
                    'create_work', 'handoff', 'pause_work', 'resume_work', 'cancel_work', 'update_work', 'wait',
                    'set_strategy', 'record_memory'],
                  allowed_tools: ['produce_artifact', 'workspace_execute'],
                  reserved_matters: ['goal', 'resources', 'charter', 'funding', 'dissolution'],
                  board_can_amend: true },
                resources: { max_calls: 12, timeout_seconds: 30 } } }),
    });
    const value = await create.json();
    if (!value.receipt || (value.receipt.status !== 'accepted' && value.receipt.status !== 'succeeded')) {
      throw new Error('create_v1 failed: ' + JSON.stringify(value).slice(0, 300));
    }
    return value.receipt;
  });
  await page.goto(running.origin);
  try {
    await page.getByText('已连接本机服务', { exact: true }).waitFor({ timeout: 15000 });
  } catch (bannerError) {
    const shot = path.join(output, 'first-load.png');
    await page.screenshot({ path: shot, fullPage: true });
    errors.push('banner missing; url=' + page.url() + ' shot=' + shot + ' body=' +
      (await page.locator('body').innerText()).slice(0, 400));
    throw bannerError;
  }
  check('private ticket page loads');

  await page.goto(running.origin);
  await page.getByText('已连接本机服务', { exact: true }).waitFor();

  let hostGrantRef = null;
  host.stdin.write(JSON.stringify({ op: 'prepare', au_id: createdReceipt.organization_id }) + '\n');
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('prepare timeout')), 20000);
    readline.createInterface({ input: host.stdout }).once('line', line => {
      const value = JSON.parse(line);
      clearTimeout(timer);
      hostGrantRef = value.grant_ref || null;
      value.prepared ? resolve() : reject(new Error('prepare failed: ' + JSON.stringify(value)));
    });
  });
  // Adopt and activate local governance: schema 1 -> governed, so the tasks page appears.
  await page.evaluate(async auId => {
    const version = (await (await fetch('/api/v1/aus/' + auId)).json()).au.version;
    const command = async (kind, data) => {
      const version = (await (await fetch('/api/v1/aus/' + auId)).json()).au.version;
      const response = await fetch('/api/v1/governance/commands', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: crypto.randomUUID(), organization_id: auId,
          base_version: version, kind, data }),
      });
      const value = await response.json();
      if (!value.receipt || value.receipt.status !== 'succeeded') {
        throw new Error(kind + ' failed: ' + JSON.stringify(value).slice(0, 300));
      }
      return value.receipt;
    };
    const principal = (await (await fetch('/api/v1/aus/' + auId)).json()).au.governance_root.governor_principal_id;
    await command('adopt_governance', { config: {
      profile: 'local_governance.v1', final_decision_principal_id: principal,
      reserved_matters: ['charter', 'goal', 'resources', 'appointments', 'mandates', 'dissolution'],
      unavailability: { mode: 'exit_after_timeout', timeout_seconds: 3600 } },
      reason: '页面级验收采用已知本地治理' });
    await command('activate_governance', { reason: '页面级验收激活本地治理' });
  }, createdReceipt.organization_id);


  await page.evaluate(async config => {
    const auId = config.auId;
    const version = (await (await fetch('/api/v1/aus/' + auId)).json()).au.version;
    const command = async (kind, data) => {
      const response = await fetch('/api/v1/models/commands', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: crypto.randomUUID(), organization_id: auId,
          base_version: (await (await fetch('/api/v1/aus/' + auId)).json()).au.version,
          kind, data }),
      });
      const value = await response.json();
      if (!value.receipt || value.receipt.status !== 'succeeded') {
        throw new Error(kind + ' failed: ' + JSON.stringify(value).slice(0, 300));
      }
      return value.receipt;
    };
    if (!config.grant_ref) throw new Error('grant ref missing from prepare');
    const saved = await command('save_connection', { connection_id: 'connection-a',
      expected_revision: 0, name: '22B page acceptance', profile: 'modeld_grant',
      model: config.model, max_output_tokens: 1024, grant_ref: config.grant_ref,
      grant_revision: 1 });
    if (saved.operation_id) {
      for (let i = 0; i < 100; i++) {
        const models = await (await fetch('/api/v1/models?organization_id=' + config.auId)).json();
        const op = (models.operations || []).find(o => o.id === saved.operation_id);
        if (op && op.status !== 'queued' && op.status !== 'running' && op.status !== 'saving') {
          if (op.status !== 'succeeded') throw new Error('save op failed: ' + JSON.stringify(op).slice(0, 250));
          break;
        }
        await new Promise(r => setTimeout(r, 100));
      }
    }
    await command('set_connection', { connection_id: 'connection-a',
      expected_revision: 1, enabled: true, make_default: true });
  }, { auId: createdReceipt.organization_id, model: process.env.UNION_REAL_MODEL || 'deepseek-v4.1-flash', grant_ref: hostGrantRef });

  const probe = await page.evaluate(async () => {
    const id = document.querySelector('#org-select').value;
    const read = await (await fetch('/api/v1/work?organization_id=' + id)).json();
    const models = await (await fetch('/api/v1/models?organization_id=' + id)).json();
    return { can_start: read.access.can_start,
             conns: (models.connections || []).map(c => ({ id: c.id, is_default: c.is_default, enabled: c.enabled })),
             protocol: models.protocol };
  });
  check('can_start probe: ' + JSON.stringify(probe), probe.can_start === true);
  try {
    await page.locator('[data-nav="tasks"]').waitFor({ timeout: 20000 });
  } catch (navError) {
    errors.push('after governance: url=' + page.url() + ' body=' + (await page.locator('body').innerText()).slice(0, 500));
    throw navError;
  }
  await page.locator('[data-nav="tasks"]').click();
  await page.waitForURL('**/tasks**');
  check('tasks page reachable');
  const cs = await page.evaluate(async () => {
    const id = document.querySelector('#org-select').value;
    const read = await (await fetch('/api/v1/work?organization_id=' + id)).json();
    return { can_start: read.access.can_start, access: read.access,
             gov: read.works, model: (await (await fetch('/api/v1/models?organization_id=' + id)).json()).connections.map(c => ({ id: c.id, is_default: c.is_default, enabled: c.enabled })) };
  });
  if (!cs.can_start) throw new Error('can_start false: ' + JSON.stringify(cs));






  // Reload the work read (the page caches it), then register the work through the form.
  await page.goto(running.origin);
  await page.getByText('已连接本机服务', { exact: true }).waitFor();
  const modelsProbe = await page.evaluate(async () => {
    const id = document.querySelector('#org-select').value;
    return (await (await fetch('/api/v1/models?organization_id=' + id)).json()).connections;
  });
  if (!(modelsProbe || []).some(c => c.is_default && c.enabled)) {
    throw new Error('page models read lacks an enabled default: ' + JSON.stringify(modelsProbe).slice(0, 260));
  }
  errors.push('nav ok, models ok: ' + JSON.stringify(modelsProbe).slice(0, 80));
  await page.locator('[data-nav="tasks"]').click();
  await page.waitForTimeout(1000);
  await page.evaluate(async config => {
    const version = async () => (await (await fetch('/api/v1/aus/' + config.auId)).json()).au.version;
    const gov = async (kind, data) => {
      const response = await fetch('/api/v1/governance/commands', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: crypto.randomUUID(), organization_id: config.auId,
          base_version: await version(), kind, data }),
      });
      const value = await response.json();
      if (!value.receipt || value.receipt.status !== 'succeeded') {
        throw new Error(kind + ' failed: ' + JSON.stringify(value).slice(0, 300));
      }
      return value.receipt;
    };
    await gov('amend_charter', { charter: { text: '测试章程：有限的本地组织协作与有界模型执行；无对外发布授权。',
      allowed_operations: ['create_work', 'handoff', 'pause_work', 'resume_work', 'cancel_work', 'update_work', 'wait'],
      allowed_tools: ['read_document', 'list_documents', 'produce_artifact'],
      reserved_matters: ['goal', 'resources', 'charter', 'funding', 'dissolution'],
      board_can_amend: true }, reason: '页面级 22-B 验收需要只读资料工具' });
  }, { auId: createdReceipt.organization_id, goal });
  await page.goto(running.origin + '/tasks');
  await page.getByText('已连接本机服务', { exact: true }).waitFor();
  const registration = await require('./exit22-registration-evidence.cjs').registerAndPrepare(
    page, createdReceipt.organization_id, { title: '22B 页面验收', goal,
      member_name: '页面验收成员', materials_root: 'project-docs', max_calls: 3,
      tools: ['read_document', 'list_documents'], connection_id: 'connection-a', expected_revision: 1 });
  workId = registration.work_id;
  fs.writeFileSync(path.join(output, 'page-registration-commands.json'), JSON.stringify(registration, null, 2));
  check('original Work registered, recovered and prepared through the Core page');
  const card = () => page.locator('[data-work=' + JSON.stringify(workId) + ']');
  await card().getByRole('button', { name: /运行 AI 工作|自动执行/ }).click();
  // Pin the in-flight automatic request, then require its own output before cancel.
  let inflight = null;
  await waitFor(async () => {
    const read = await coreWork();
    const work = (read.works || []).find(w => w.id === workId);
    inflight = (work.steps || []).find(s => s.status === 'reserved' && s.command_id && s.model_request_id);
    return Boolean(inflight);
  }, 'in-flight automatic reservation visible', 60000);
  // Original-output acceptance gate. Public events bind request identity in the
  // response envelope; individual events intentionally omit request_id.
  const readObservationSession = async () => page.evaluate(async () => {
    const response = await fetch('/api/session');
    return { status: response.status, body: await response.json() };
  });
  const observationSession = await readObservationSession();
  const sessionMatches = value => value.status === 200 && value.body?.core_protocol === 'core.au.v1'
    && Boolean(value.body.principal_id) && Boolean(value.body.service_instance)
    && value.body.principal_id === observationSession.body.principal_id
    && value.body.service_instance === observationSession.body.service_instance;
  check('original output has a current authenticated Core session', sessionMatches(observationSession));
  const connectionKeys = ['id', 'revision', 'profile', 'model', 'grant_ref', 'grant_revision', 'max_output_tokens', 'task_ms'];
  const connectionIdentity = value => JSON.stringify(connectionKeys.map(key => value?.[key] ?? null));
  const originKeys = ['step_ref', 'attempt_id', 'command_id', 'model_request_id'];
  const sameOrigin = value => Boolean(value && inflight.connection)
    && originKeys.every(key => Boolean(inflight[key]) && value[key] === inflight[key])
    && connectionIdentity(value.connection) === connectionIdentity(inflight.connection);
  const originalWork = await coreWork();
  check('original output is bound to the current Core work snapshot',
    originalWork.protocol === 'core.work.v1' && originalWork.organization_id === createdReceipt.organization_id
    && originalWork.access?.principal_id === observationSession.body.principal_id
    && sameOrigin(originalWork.works?.find(w => w.id === workId)?.steps?.find(s => s.step_ref === inflight.step_ref)));
  let observationCursor = 0;
  let outputObservation;
  await waitFor(async () => {
    const response = await page.evaluate(async config => {
      const response = await fetch('/api/v1/work/events?organization_id=' + encodeURIComponent(config.auId)
        + '&work_id=' + encodeURIComponent(config.workId) + '&step_ref=' + encodeURIComponent(config.stepRef)
        + '&after=' + config.after);
      return { status: response.status, body: await response.json() };
    }, { auId: createdReceipt.organization_id, workId, stepRef: inflight.step_ref, after: observationCursor });
    check('original output session remains current after the read', sessionMatches(await readObservationSession()));
    const value = response.body;
    check('original output response identifies the same request and current reader', response.status === 200
      && value?.protocol === 'core.work-events.v1' && value.source === 'persisted_modeld_events'
      && value.organization_id === createdReceipt.organization_id && value.work_id === workId && sameOrigin(value)
      && value.access?.principal_id === observationSession.body.principal_id
      && value.access?.service_instance === observationSession.body.service_instance
      && Number.isSafeInteger(value.version) && value.version >= originalWork.version
      && value.authorization_only === false);
    check('original output cursor is monotonic and the page is bounded',
      Number.isSafeInteger(value.cursor) && value.cursor >= observationCursor && value.last_seq === value.cursor
      && typeof value.has_more === 'boolean' && (!value.has_more || value.cursor > observationCursor)
      && Array.isArray(value.events) && value.events.length <= 500);
    let lastSeq = observationCursor;
    for (const event of value.events) {
      check('original output events are ordered public text or tool observations', event
        && Number.isSafeInteger(event.seq) && event.seq > lastSeq && event.seq <= value.cursor
        && ((event.type === 'text_delta' && typeof event.text === 'string')
          || (event.type === 'tool_call_complete' && event.name === 'read_document')));
      lastSeq = event.seq;
    }
    observationCursor = value.cursor;
    const text = value.events.filter(event => event.type === 'text_delta').map(event => event.text).join('');
    if (!text.trim()) return false;
    outputObservation = { protocol: value.protocol, source: value.source, organization_id: value.organization_id,
      principal_id: observationSession.body.principal_id,
      service_instance: observationSession.body.service_instance,
      work_id: workId, ...Object.fromEntries(originKeys.map(key => [key, value[key]])),
      cursor: value.cursor, text_bytes: new TextEncoder().encode(text).length,
      text_sha256: crypto.createHash('sha256').update(text, 'utf8').digest('hex') };
    return true;
  }, 'original request text observed before cancel', 60000);
  fs.writeFileSync(path.join(output, 'original-output-observation.json'), JSON.stringify(outputObservation, null, 2));
  check('in-flight automatic reservation carries the line-end id: ' + inflight.model_request_id);
  check('the cancelled request is this run\'s own in-flight request (distinct id, own attempt): ' +
        inflight.model_request_id + ' / ' + inflight.attempt_id,
        Boolean(inflight.model_request_id) && Boolean(inflight.attempt_id));
  // Cancel through the product command surface while the model call is running.
  const pageCancellation = await require('./exit22-page-cancel.cjs').cancelFromPage(page, {
    organization_id: createdReceipt.organization_id, work_id: workId, ...inflight,
    principal_id: outputObservation.principal_id, service_instance: outputObservation.service_instance,
  });
  const cancelCommandId = pageCancellation.command.id;
  const cancelOutcome = { status: 200, receipt: pageCancellation.receipt };
  check('cancel accepted by the product: ' + JSON.stringify(cancelOutcome.receipt).slice(0, 160),
        cancelOutcome.status === 200
        && (cancelOutcome.receipt || {}).status === 'succeeded');
  const cancelReceipt = cancelOutcome.receipt || {};
  const cancelStepRef = ((cancelOutcome.receipt.step || {}).step_ref) || '';
  const cancelModelRequest = cancelOutcome.receipt.model_request_id || '';
  const cancelOrg = cancelOutcome.receipt.organization_id || '';
  check('cancel receipt identifies the same command/attempt/step/model request',
        Boolean(cancelOutcome.receipt.id)
        && (typeof inflight === 'undefined' || !inflight
            || (cancelStepRef === inflight.step_ref
            && cancelModelRequest === inflight.model_request_id))
        && (typeof createdReceipt === 'undefined' || !createdReceipt
            || cancelOrg === createdReceipt.organization_id));
  check('delivery observation recorded: ' + cancelOutcome.receipt.cancel_accepted,
        cancelOutcome.receipt.cancel_accepted === true);
  // Same-run original GET is asserted after the settlement window opens.
  // The settlement may be interrupted (unknown kept) or completed (used) depending
  check('cancel receipt id matches the submitted cancel command',
        cancelOutcome.receipt.id === cancelCommandId);
  // Same-run original GET must return the same durable delivery fact.
  const originalCancelReference = { organization_id: createdReceipt.organization_id, work_id: workId,
    cancel_id: cancelCommandId, principal_id: outputObservation.principal_id,
    ...Object.fromEntries(['step_ref', 'attempt_id', 'command_id', 'model_request_id', 'connection']
      .map(key => [key, inflight[key]])) };
  const cancelEvidenceBefore = await require('./exit22-evidence-failure.cjs').readWithFailureRecord({
    loader: (args) => require('./exit22-cancel-evidence.cjs').readCancelEvidence(
      page, args.reference, args.expected),
    reference: originalCancelReference, expected: cancelOutcome.receipt,
    fs, path, output, name: 'cancel-receipt-before-restart', workId });
  fs.writeFileSync(path.join(output, 'cancel-receipt-before-restart.json'), JSON.stringify(cancelEvidenceBefore, null, 2));
  check('original GET returns the complete original delivered cancel receipt');
  // on the race with the real model; both must settle only via the original request.
  await waitFor(async () => {
    const read = await coreWork();
    const work = (read.works || []).find(w => w.id === workId);
    const step = (work.steps || []).find(s => s.step_ref === inflight.step_ref);
    return step && step.status !== 'reserved';
  }, 'the cancelled step settles', 240000);
  const settled = await coreWork();
  const work = (settled.works || []).find(w => w.id === workId);
  const step = (work.steps || []).find(s => s.step_ref === inflight.step_ref);
  // This exact request already produced observed text; it cannot be unexecuted.
  check('step settled as ' + step.status + ' (cost ' + step.cost_status + ')',
        ['unknown', 'used'].includes(step.status));
  check('an unknown settlement keeps the budget reserved',
        step.status !== 'unknown' || work.budget.reserved === 1);
  // Persisted facts must survive a console rebuild on the same root.
  const before = await snapshot();
  fs.writeFileSync(path.join(output, 'snapshot-before-restart.json'), JSON.stringify(before, null, 2));

  // Rebuild the console on the same root and verify persistence.
  host.kill();
  await new Promise(r => running.child.once('exit', r));
  running = await startHost();
  host = running.child;
  await page.goto(running.origin);
  await page.getByText('已连接本机服务', { exact: true }).waitFor();
  const after = await snapshot();
  const entry = (after.works || []).find(w => w.id === workId);
  const adoptedAfter = (entry.results || []).find(r => r.status === 'adopted');
  // This interrupt exit does not adopt/deliver a result; the original-result
  // anchoring applies only when the work carries a delivered id (download exit).
  check('an adopted result survives the rebuild and matches the delivered id: ' + (adoptedAfter && adoptedAfter.id),
        !entry.delivered_result_id || (Boolean(adoptedAfter)
          && entry.delivered_result_id === adoptedAfter.id));
  const settledStep = (entry.steps || []).find(s2 => s2.step_ref === inflight.step_ref);
  check('the settled step survives the rebuild as ' + (settledStep && settledStep.status),
        settledStep && ['unknown', 'used'].includes(settledStep.status));
  check('the settled step keeps its original identity across the rebuild',
        settledStep && (typeof inflight === 'undefined' || !inflight
          || (settledStep.step_ref === inflight.step_ref
          && settledStep.model_request_id === inflight.model_request_id
          && settledStep.attempt_id === inflight.attempt_id)));
  check('the settle reason persists', settledStep && Boolean(settledStep.reason));
  const unresolved = settledStep.status === 'unknown';
  check('an unresolved step keeps its original reservation after the rebuild',
        !unresolved || entry.budget.reserved === 1);
  // Record the reopen observation BEFORE the strict comparison, so a rejected
  // comparison still leaves replay-observation.json behind for attribution.
  require('./exit22-replay-observation.cjs').recordReplayObservation({
    fs, path, output, before, after, workId, check });
  // Counts can match while identities or result bytes differ. Probe the pure comparison
  // first so a rejection is written to the record instead of leaving an 'unchanged' claim.
  try {
    require('./exit22-restart-evidence.cjs').compareSnapshots(
      before, after, createdReceipt.organization_id, workId);
  } catch (error) {
    require('./exit22-replay-observation.cjs').recordReplayComparisonFailure({
      fs, path, output, workId, error });
    throw error;
  }
  const restartComparison = require('./exit22-restart-evidence.cjs').compareSnapshots(
    before, after, createdReceipt.organization_id, workId);
  const cancelEvidenceAfter = await require('./exit22-evidence-failure.cjs').readWithFailureRecord({
    loader: (args) => require('./exit22-cancel-evidence.cjs').readCancelEvidence(
      page, args.reference, args.expected),
    reference: originalCancelReference, expected: cancelEvidenceBefore.receipt,
    fs, path, output, name: 'cancel-receipt-after-restart', workId });
  fs.writeFileSync(path.join(output, 'cancel-receipt-after-restart.json'), JSON.stringify(cancelEvidenceAfter, null, 2));
  check('original cancel receipt survives restart under the original principal and Work');
  fs.writeFileSync(path.join(output, 'restart-request-comparison.json'), JSON.stringify(restartComparison, null, 2));
  fs.writeFileSync(path.join(output, 'snapshot-after-restart.json'), JSON.stringify(after, null, 2));
  fs.writeFileSync(path.join(output, 'checks.json'),
    JSON.stringify({ passed: checks.length, nonce, workId, checks, errors }, null, 2));
  console.log(JSON.stringify({ passed: checks.length, workId, nonce, errors }, null, 2));
})().catch(error => {
  errors.push(String(error && error.stack || error));
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ failed: true, checks, errors }, null, 2));
  console.log(JSON.stringify({ failed: true, checks, errors }, null, 2));
  process.exitCode = 1;
}).finally(async () => {
  try { if (browser) await browser.close(); } catch {}
  try { if (host) host.kill(); } catch {}
});
