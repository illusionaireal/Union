// Page-level 22-B: register work via the page form, run the loop with the real model,
// adopt/deliver through the page, then rebuild the console and verify persistence.
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
const workId = 'work-exit';
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

  // Create a V1 AU through the real creation command (the model-access host starts empty).
  await page.evaluate(async () => {
    const charter = {
      text: "测试章程：有限的本地组织协作；无对外发布授权。",
      allowed_operations: ["create_member", "create_position", "update_position", "assign", "set_policy",
        "create_work", "handoff", "pause_work", "resume_work", "cancel_work", "update_work", "wait",
        "set_strategy", "record_memory"],
      allowed_tools: ["produce_artifact", "workspace_execute"],
      reserved_matters: ["goal", "resources", "charter", "funding", "dissolution"],
      board_can_amend: true,
    };
    const create = await fetch('/api/commands', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: crypto.randomUUID(), organization_id: null, base_version: null,
        kind: 'create_v1',
        data: { name: '22B 页面验收组织', goal: '完成一次页面级有界验收', board_name: 'Owner display',
                charter, resources: { max_calls: 12, timeout_seconds: 30 } } }),
    });
    const value = await create.json();
    if (!value.receipt || (value.receipt.status !== 'accepted' && value.receipt.status !== 'succeeded')) {
      throw new Error('create_v1 failed: ' + JSON.stringify(value).slice(0, 300));
    }
    return value.receipt;
  });
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
    const work = async (kind, data) => {
      const response = await fetch('/api/v1/work/commands', {
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
    const read = await (await fetch('/api/v1/aus/' + config.auId)).json();
    const principal = read.access.principal_id;
    await gov('amend_charter', { charter: { text: '测试章程：有限的本地组织协作与有界模型执行；无对外发布授权。',
      allowed_operations: ['create_work', 'handoff', 'pause_work', 'resume_work', 'cancel_work', 'update_work', 'wait'],
      allowed_tools: ['read_document', 'list_documents', 'produce_artifact'],
      reserved_matters: ['goal', 'resources', 'charter', 'funding', 'dissolution'],
      board_can_amend: true }, reason: '页面级 22-B 验收需要只读资料工具' });
    await gov('appoint', { member_id: 'member-page', principal_id: principal,
      name: '页面验收成员', binding_id: 'binding-page', duty: '完成页面级 22-B 验收' });
    await work('start_work', { work_id: 'work-exit', title: '22B 页面验收',
      goal: config.goal, member_name: '页面验收成员', member_id: 'member-page',
      definition_id: 'def-page', binding_id: 'binding-page', mandate_id: 'ma-page',
      connection_id: 'connection-a', expected_revision: 1,
      materials_root: 'project-docs', max_calls: 3,
      tools: ['read_document', 'list_documents'], reason: '页面级 22-B 验收' });
    await work('start_attempt', { work_id: 'work-exit' });
  }, { auId: createdReceipt.organization_id, goal });
  await page.goto(running.origin + '/tasks');
  await page.getByText('已连接本机服务', { exact: true }).waitFor();
  check('work registered and attempt started through the product API');
  const card = () => page.locator('ul.work-panel li').first();
  await card().getByRole('button', { name: /运行 AI 工作|自动执行/ }).click();
  await waitFor(async () => {
    const read = await coreWork();
    const work = (read.works || []).find(w => w.id === workId);
    return work && work.results.some(r => r.status === 'candidate');
  }, 'candidate result produced by the real model', 240000);
  const resultRead = await page.evaluate(async config => {
    const value = await (await fetch('/api/v1/work/results?organization_id=' + config.auId + '&id=' + config.resultId)).json();
    return value;
  }, { auId: createdReceipt.organization_id, resultId: await page.evaluate(async config => {
    const read = await (await fetch('/api/v1/work?organization_id=' + config.auId)).json();
    const work = (read.works || []).find(w => w.id === 'work-exit');
    return work.results[work.results.length - 1].id;
  }, { auId: createdReceipt.organization_id }) });
  const content = resultRead.result.content || resultRead.content || '';
  const digest = crypto.createHash('sha256').update(Buffer.from(content, 'utf8')).digest('hex');
  const recorded = resultRead.result.sha256;
  if (digest !== recorded) {
    throw new Error('result digest mismatch: computed ' + digest + ' recorded ' + recorded);
  }
  check('result content digest matches recorded sha256: ' + digest, true);
  check('result cites the synthetic nonce: ' + (content.includes(nonce) ? 'yes' : 'no'), content.includes(nonce));
  const recordedFull = resultRead.result || resultRead;
  const resultId = recordedFull.id;
  const recordedTitle = recordedFull.title;
  const download = card().getByRole('link', { name: '下载' });
  const href = await download.getAttribute('href');
  const downloadFetch = await page.evaluate(async href => {
    const response = await fetch(href);
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    return { status: response.status, body };
  }, href);
  const body = downloadFetch.body || {};
  const meta = body.result || {};
  const downloadedContent = body.content || '';
  check('download link present, HTTP 200, and body is the recorded result id: ' + (meta.id || 'none'),
        Boolean(href) && href.includes('/api/v1/work/results')
        && downloadFetch.status === 200 && meta.id === resultId);
  check('downloaded body belongs to the original AU and work',
        body.organization_id === createdReceipt.organization_id && body.work_id === workId);
  const downloadedDigest = crypto.createHash('sha256')
    .update(Buffer.from(downloadedContent, 'utf8')).digest('hex');
  check('downloaded content sha256 matches the recorded digest: ' + downloadedDigest.slice(0, 16),
        downloadedDigest === digest);
  check('downloaded title is the recorded title', meta.title === recordedTitle);
  // Exercise the actual Core result controls. A hidden/disabled control or an
  // unfinished attempt must not be repaired with a direct API write.
  const deliveryBefore = await snapshot();
  const originalEntries = deliveryBefore.works.filter(w => w.id === workId);
  check('exactly one original Work before page delivery', originalEntries.length === 1);
  const candidates = originalEntries[0].results.filter(r => r.id === resultId);
  check('the downloaded original candidate is still current', candidates.length === 1
    && candidates[0].status === 'candidate' && candidates[0].sha256 === recorded
    && JSON.stringify(candidates[0].sources) === JSON.stringify(recordedFull.sources));
  const resultControls = page.locator('[data-work=' + JSON.stringify(workId) + ']')
    .getByRole('region', { name: '成果 ' + resultId, exact: true });
  const pageCommands = [];
  const captureCommand = request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands')
      pageCommands.push(request.postDataJSON());
  };
  page.on('request', captureCommand);
  try {
    await resultControls.getByRole('button', { name: '采用此成果', exact: true }).click();
    // The UI only offers delivery after the original adoption is confirmed and
    // the original attempt is closed by the existing product transaction.
    await resultControls.getByRole('button', { name: '交付此成果', exact: true }).click();
    await waitFor(async () => {
      const read = await snapshot();
      check('page delivery retains the original authenticated principal',
        read.access.principal_id === deliveryBefore.access.principal_id);
      const entries = read.works.filter(w => w.id === workId);
      check('page delivery retains exactly one original Work', entries.length === 1);
      const current = entries[0];
      const results = current.results.filter(r => r.id === resultId);
      check('page delivery retains the original result digest and sources', results.length === 1
        && results[0].sha256 === recorded
        && JSON.stringify(results[0].sources) === JSON.stringify(recordedFull.sources));
      if (current.status !== 'delivered') return false;
      check('page delivered the same adopted result', current.delivered_result_id === resultId
        && results[0].status === 'adopted');
      return true;
    }, 'original result adopted and delivered through the Core page', 60000);
  } finally {
    page.off('request', captureCommand);
  }
  check('exactly the two original page commands were submitted', pageCommands.length === 2
    && pageCommands[0].kind === 'adopt_result' && pageCommands[1].kind === 'deliver_work'
    && pageCommands.every(command => typeof command.id === 'string' && command.id
      && command.organization_id === createdReceipt.organization_id
      && command.data?.work_id === workId && command.data?.result_id === resultId)
    && pageCommands[0].id !== pageCommands[1].id);
  fs.writeFileSync(path.join(output, 'page-delivery-commands.json'), JSON.stringify({
    organization_id: createdReceipt.organization_id, work_id: workId, result_id: resultId,
    sha256: recorded, principal_id: deliveryBefore.access.principal_id,
    commands: pageCommands.map(({ id, kind }) => ({ id, kind })),
  }, null, 2));
  const before = await snapshot();
  fs.writeFileSync(path.join(output, 'snapshot-before-restart.json'), JSON.stringify(before, null, 2));

  // Rebuild the console on the same root and verify persistence.
  host.kill();
  await new Promise(r => running.child.once('exit', r));
  running = await startHost();
  host = running.child;
  await page.goto(running.origin);
  await page.getByText('已连接本机服务', { exact: true }).waitFor();
  const authenticatedAfter = await snapshot();
  // The final GET is wrapped in the same session/Work validation (no raw
  // unguarded fetch) so a mid-flight session/principal change rejects.
  const after = await snapshot();
  check('reopened work snapshot returned HTTP 200 and belongs to the original AU',
        Boolean(after) && after.protocol === 'core.work.v1'
        && after.organization_id === createdReceipt.organization_id);
  const entry = (after.works || []).find(w => w.id === workId);
  check('work still delivered after a console rebuild', Boolean(entry) && entry.status === 'delivered');
  const originalResult = (entry.results || []).find(r => r.id === resultId);
  check('the original adopted result and digest survive the rebuild',
        Boolean(originalResult) && originalResult.status === 'adopted'
        && originalResult.sha256 === recorded);
  check('the rebuilt work remains delivered with the original result', entry.delivered_result_id === resultId);
  // Restart request conservation.
  require('./exit22-restart-evidence.cjs').compareSnapshots(after, authenticatedAfter, createdReceipt.organization_id, workId);
  const restartComparison = require('./exit22-restart-evidence.cjs').compareSnapshots(
    before, after, createdReceipt.organization_id, workId);
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
