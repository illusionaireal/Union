// S05/G10: real React + HTTP + SQLite, isolated accounts and human local submissions.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const crypto = require('node:crypto');
const readline = require('node:readline');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const privateRoot = path.join(root, '.union');
fs.mkdirSync(privateRoot, { recursive: true });
const dataRoot = fs.mkdtempSync(path.join(privateRoot, 's05-browser-'));
const output = path.resolve(process.env.UNION_S05_UI_EVIDENCE || path.join(privateRoot, 's05-ui-browser'));
const assetRoot = path.join(root, 'web', 'console', 'dist', 'assets');
const consoleAssets = Object.fromEntries(fs.readdirSync(assetRoot).filter(name => /\.(js|css)$/.test(name)).sort()
  .map(name => [name, crypto.createHash('sha256').update(fs.readFileSync(path.join(assetRoot, name))).digest('hex')]));
const checks = [], requests = [], uiKinds = new Set(), errors = [], secrets = [], readability = [];
const dialogReads = new WeakMap();
let browser, host, lines, origin, pageA, pageB, pageC;
const password = () => { const value = crypto.randomUUID() + '!Safe9'; secrets.push(value); return value; };
const accounts = {
  a: { username: 's05-owner', password: password() },
  b: { username: 's05-successor', password: password() },
  c: { username: 's05-participant', password: password() },
};
const longNames = {
  au: ('S05 长名称治理验收 · ' + '明确责任与可核对内部记录'.repeat(20)).slice(0, 200),
  member: ('原记录人 · ' + '责任成员姓名'.repeat(40)).slice(0, 200),
  work: 'InternalRecord-' + 'W'.repeat(185),
};
const progress = stage => process.stdout.write(JSON.stringify({ stage }) + '\n');
const check = (name, value = true) => { assert.ok(value, name); checks.push(name); };
const sanitize = value => secrets.reduce((text, secret) => text.split(secret).join('[private]'), String(value))
  .split(dataRoot).join('[private test data]').replace(/#launch=[^\s"']+/g, '#launch=[private]');
function nextLine() {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('The isolated browser host did not respond')), 20000);
    lines.once('line', line => { clearTimeout(timeout); resolve(JSON.parse(line)); });
  });
}
async function until(predicate, message, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error(message);
}
async function session(page) { return page.evaluate(async () => (await fetch('/api/session')).json()); }
async function read(page, id) {
  return page.evaluate(async au => {
    const response = await fetch('/api/v1/aus/' + au);
    return { status: response.status, value: await response.json() };
  }, id);
}
async function requestReceipt(page, command) {
  return page.evaluate(async reference => {
    const response = await fetch('/api/v1/governance/receipts?' + new URLSearchParams({ organization_id: reference.organization_id, id: reference.id }));
    return { status: response.status, value: await response.json() };
  }, command);
}
async function directCommand(page, id, kind, data) {
  const current = await read(page, id);
  assert.equal(current.status, 200);
  return page.evaluate(async command => {
    const response = await fetch('/api/v1/governance/commands', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(command),
    });
    return { status: response.status, value: await response.json() };
  }, { id: crypto.randomUUID(), organization_id: id, base_version: current.value.au.version, kind, data });
}
async function connected(page) { await page.getByText('已连接本机服务', { exact: true }).waitFor(); }
async function refresh(page) {
  const auId = new URL(page.url()).searchParams.get('organization');
  assert.ok(auId, 'The refresh target is an explicit AU');
  const initiated = new Set();
  const observe = request => { if (request.method() === 'GET') initiated.add(request); };
  page.on('request', observe);
  const responses = Promise.all(['/api/session', '/api/v1/aus/' + auId].map(pathname =>
    page.waitForResponse(response => initiated.has(response.request()) && new URL(response.url()).pathname === pathname)));
  try {
    await page.locator('#refresh').click();
    const [identity, projection] = await responses;
    assert.equal(identity.status(), 200, 'The current session refresh succeeded');
    assert.equal(projection.status(), 200, 'The requested AU refresh succeeded');
    const current = await projection.json();
    await until(async () => {
      const rendered = await page.locator('#snapshot-meta').textContent();
      return rendered.includes(auId) && rendered.includes(`状态 v${current.au.version} ·`);
    }, 'The full AU refresh was not applied before the next operation');
    await connected(page);
  } finally { page.off('request', observe); }
}
async function field(dialog, name, value) {
  const input = dialog.locator(`[name="${name}"]`);
  const tag = await input.evaluate(element => element.tagName);
  if (typeof value === 'boolean') { if (value) await input.check(); else await input.uncheck(); }
  else if (tag === 'SELECT') {
    try { await input.selectOption(value, { timeout: 5000 }); }
    catch (failure) {
      const context = dialogReads.get(dialog), page = dialog.page();
      const selectedWork = dialog.locator('[name="work_id"]');
      const workId = await selectedWork.count() ? await selectedWork.inputValue() : null;
      const current = await read(page, context.organization_id);
      const mandate = current.value.au?.mandates[String(value)];
      const binding = mandate ? current.value.au.bindings[mandate.binding_id] : undefined;
      const work = current.value.au?.work[workId];
      throw Error('Governance option missing: ' + JSON.stringify({ ...context, field: name, expected_option: String(value),
        rendered_at_failure: await page.locator('#snapshot-meta').textContent(),
        rendered_options: await input.locator('option').evaluateAll(options => options.map(option => option.value)),
        current_read: { status: current.status, version: current.value.au?.version, mandate,
          binding: binding && { id: binding.id, active: binding.active, version: binding.version },
          work: work && { id: work.id, status: work.status, version: work.version } },
        error: failure.message }));
    }
  }
  else await input.fill(String(value));
}
async function openCommand(page, kind, fields = {}) {
  const context = { kind, organization_id: new URL(page.url()).searchParams.get('organization'),
    rendered_when_opened: await page.locator('#snapshot-meta').textContent() };
  await page.locator(`[data-governance="${kind}"]`).first().click();
  const dialog = page.locator('#governance-dialog');
  await dialog.waitFor({ state: 'visible' });
  dialogReads.set(dialog, context);
  for (const [name, value] of Object.entries(fields)) await field(dialog, name, value);
  return dialog;
}
async function confirm(dialog) {
  await dialog.getByRole('button', { name: '预览影响', exact: true }).click();
  const button = dialog.getByRole('button', { name: '确认提交', exact: true });
  await button.waitFor(); await button.click();
}
async function runCommand(page, kind, fields = {}, expected = 'succeeded') {
  const dialog = await openCommand(page, kind, fields);
  const posted = page.waitForRequest(value => new URL(value.url()).pathname === '/api/v1/governance/commands' && value.method() === 'POST');
  await confirm(dialog);
  const command = (await posted).postDataJSON();
  await dialog.getByRole('region', { name: '原治理请求回执' }).waitFor();
  const receipt = await requestReceipt(page, command);
  assert.equal(receipt.status, 200, 'Original issuer can read its own command receipt');
  assert.equal(receipt.value.receipt.status, expected, `${kind}: ${sanitize(receipt.value.receipt.message)}`);
  assert.equal(receipt.value.receipt.id, command.id);
  uiKinds.add(kind);
  if (expected === 'succeeded') await dialog.getByRole('button', { name: '完成，返回工作台', exact: true }).click();
  else await dialog.locator('#close-governance').click();
  await refresh(page);
  const details = page.locator('.data-footer details');
  if (!await details.evaluate(element => element.open)) await details.locator('summary').click();
  try {
    await until(async () => (await page.locator('#snapshot-meta').innerText()).includes(`状态 v${receipt.value.receipt.version}`), 'The UI did not refresh the saved command version');
  } catch (failure) {
    const current = await read(page, command.organization_id);
    const metadata = await page.locator('#snapshot-meta').evaluate(element => ({
      rendered: element.innerText, content: element.textContent, expanded: element.closest('details')?.open,
    }));
    throw Error(`${failure.message}: ${JSON.stringify({kind, receipt_version: receipt.value.receipt.version,
      current_status: current.status, current_version: current.value.au?.version, metadata})}`);
  }
  return { command, receipt: receipt.value.receipt };
}
async function navigate(page, id, section) {
  await page.goto(`${origin}/${section}?organization=${encodeURIComponent(id)}`);
  await connected(page);
}
async function account(page, value, owner = false) {
  await page.goto(origin + '/overview');
  if (!owner) await page.getByRole('button', { name: '登记核心参与者', exact: true }).click();
  await page.locator('[name="username"]').fill(value.username);
  await page.locator('[name="password"]').fill(value.password);
  await page.getByRole('button', { name: owner ? '建立管理员账号' : '登记核心参与者', exact: true }).click();
  const recovery = page.getByLabel('账号恢复码', { exact: true });
  await recovery.waitFor(); value.recovery = await recovery.inputValue(); secrets.push(value.recovery);
  if (!owner) {
    await page.waitForTimeout(3200);
    check('Registration retains the recovery code through background authentication reads', await recovery.isVisible());
  }
  await page.getByRole('button', { name: '已保存，进入工作台', exact: true }).click();
  await connected(page);
  const current = await session(page); value.principal = current.principal_id;
  check('Account exposes its stable principal for explicit nominations and appointments',
    await page.getByLabel('当前核心身份标识', { exact: true }).inputValue() === value.principal);
  if (!owner) check('Registered core participant starts with no AU, legacy or platform permissions',
    current.role === 'core' && !current.platform_admin && current.organizations.length === 0 &&
    await page.getByRole('button', { name: '旧版兼容试验（含小说）', exact: true }).isDisabled());
}
async function viewports(page, name) {
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    check(`${name} fits ${width}px`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await measureReadability(page, '.governance-workspace .quiet-pill', `${name} status at ${width}px`, 12);
    await page.screenshot({ path: path.join(output, `${name}-${width}.png`), fullPage: true });
  }
}
async function measureReadability(page, selector, label, minimumFont) {
  const measurements = await page.locator(selector).evaluateAll(elements => {
    const channels = color => color.match(/[\d.]+/g).map(Number);
    const luminance = rgb => rgb.slice(0, 3).map(value => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    return elements.filter(element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden').map(element => {
      const style = getComputedStyle(element);
      let ancestor = element, background = 'rgb(255, 255, 255)';
      while (ancestor) {
        const candidate = getComputedStyle(ancestor).backgroundColor;
        const rgba = channels(candidate);
        if (rgba.length === 3 || rgba[3] === 1) { background = candidate; break; }
        ancestor = ancestor.parentElement;
      }
      const foreground = luminance(channels(style.color)), backdrop = luminance(channels(background));
      return { font_size: Number.parseFloat(style.fontSize), color: style.color, background,
        contrast: (Math.max(foreground, backdrop) + 0.05) / (Math.min(foreground, backdrop) + 0.05) };
    });
  });
  assert.ok(measurements.length, `${label} has rendered text to measure`);
  readability.push({ label, selector, minimum_font: minimumFont, minimum_contrast: 4.5, measurements });
  fs.writeFileSync(path.join(output, 'readability.json'), JSON.stringify(readability, null, 2));
}
function assertReadability() {
  const failures = readability.flatMap(group => group.measurements
    .filter(value => value.font_size < group.minimum_font || value.contrast < group.minimum_contrast)
    .map(value => ({ label: group.label, ...value })));
  assert.equal(failures.length, 0, 'Governance text readability failed: ' + JSON.stringify(failures));
  check('Rendered governance status and confirmation text meet readable sizes and at least 4.5:1 contrast at all four widths');
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  host = spawn(process.env.UNION_PYTHON || 'python3', ['-X', 'utf8', 'tests/model_access_browser_host.py', '--root', dataRoot],
    { cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' } });
  host.stderr.on('data', value => errors.push(String(value)));
  lines = readline.createInterface({ input: host.stdout });
  const ready = await nextLine(); origin = ready.origin;
  if (ready.board_url) secrets.push(ready.board_url);
  browser = await chromium.launch({ headless: true, executablePath: process.env.UNION_CHROMIUM_PATH ||
    (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : chromium.executablePath()) });
  const contextA = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const contextB = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const contextC = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  [pageA, pageB, pageC] = await Promise.all([contextA.newPage(), contextB.newPage(), contextC.newPage()]);
  for (const page of [pageA, pageB, pageC]) {
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      const pathname = new URL(request.url()).pathname;
      if (request.method() === 'POST' && ['/api/commands', '/api/v1/governance/commands'].includes(pathname))
        requests.push({ pathname, command: request.postDataJSON() });
    });
  }
  progress('core accounts and single-principal local governance');
  await account(pageA, accounts.a, true);
  await account(pageB, accounts.b);
  await account(pageC, accounts.c);
  await pageA.locator('[data-command="create_v1"]').first().click();
  await pageA.getByLabel('AU名称', { exact: true }).fill(longNames.au);
  await pageA.getByLabel('AU目标', { exact: true }).fill('明确责任并持久保存可核对的内部文字记录。');
  await pageA.locator('#preview-operation').click(); await pageA.locator('#commit-operation').click();
  await pageA.getByRole('button', { name: '完成，返回工作台', exact: true }).click();
  await pageA.getByRole('region', { name: 'AU准备记录', exact: true }).waitFor();
  const auId = (await session(pageA)).organizations[0].id;
  await runCommand(pageA, 'adopt_governance', { timeout_seconds: '3600', reason: '单主体预先采用超时退出程序' });
  await runCommand(pageA, 'activate_governance', { reason: '明确启用本地内部记录范围' });
  await runCommand(pageA, 'renew_governance', { reason: '显式核对并续期' });
  await navigate(pageA, auId, 'tasks');
  const appointmentA = await runCommand(pageA, 'appoint', { name: longNames.member, duty: '明确承担内部记录责任' });
  const bindingA = appointmentA.command.data.binding_id;
  await runCommand(pageA, 'update_appointment', { binding_id: bindingA, duty: '按当前版本记录决定与交接', reason: '补充明确职责' });
  const workA = await runCommand(pageA, 'create_work', { binding_id: bindingA, title: longNames.work, instruction: '记录真实的受控验收步骤与边界' });
  const firstWork = workA.command.data.work_id;
  const grantA = await runCommand(pageA, 'grant_mandate', { work_id: firstWork, binding_id: bindingA });
  const startA = await runCommand(pageA, 'begin_local_action', { work_id: firstWork, mandate_id: grantA.command.data.mandate_id });
  const firstAttempt = startA.command.data.attempt_id;
  await runCommand(pageA, 'submit_local_result', { attempt_id: firstAttempt, content: '由一个明确责任主体完成的受控内部记录。' });
  await runCommand(pageA, 'accept_local_result', { attempt_id: firstAttempt, reason: '已核对责任、授权、版本与内容' });
  const single = (await read(pageA, auId)).value;
  check('The real forms preserve legal 200-character AU, member and unbroken Work names',
    single.au.name === longNames.au && single.au.members[appointmentA.command.data.member_id].name === longNames.member &&
    single.au.work[firstWork].title === longNames.work && Object.values(longNames).every(value => value.length === 200));
  check('A single human principal completes Work → Mandate → local submission → accepted record through React and HTTP',
    single.au.work[firstWork].status === 'delivered' && single.au.attempts[firstAttempt].kind === 'local_submission' &&
    single.au.results[firstAttempt].content === '由一个明确责任主体完成的受控内部记录。');
  check('Local governance does not activate autonomous business, model dispatch, resource use or external commitment',
    !single.capabilities.autonomous_business && single.au.autonomy_state === 'inactive' && single.au.resource_state === 'planned' &&
    ['model_dispatch', 'resource_use', 'external_commitment'].every(item => single.capabilities.unavailable.includes(item)));

  await navigate(pageA, auId, 'settings');
  await runCommand(pageA, 'amend_charter', { charter_text: '暂时撤销内部记录授权。', record_memory: false, reason: '核对旧有效规则修订后的执行边界' });
  await navigate(pageA, auId, 'tasks');
  const workB = await runCommand(pageA, 'create_work', { binding_id: bindingA, title: '沿原标识交接的工作', instruction: '保留撤权与交接前后的内容和责任' });
  const handoffWork = workB.command.data.work_id;
  const deniedGrant = await runCommand(pageA, 'grant_mandate', { work_id: handoffWork, binding_id: bindingA }, 'rejected');
  check('The same production grant boundary rejects record_memory after its charter permission is withdrawn', deniedGrant.receipt.effect === 'none');
  await navigate(pageA, auId, 'settings');
  await runCommand(pageA, 'amend_charter', { charter_text: '按有效责任与授权保存内部记录。', record_memory: true, reason: '旧规则允许的明确修订' });
  await navigate(pageA, auId, 'overview');
  await runCommand(pageA, 'set_goal', { goal: '保持原工作标识并验证可恢复的内部记录。', reason: '明确后续范围' });

  progress('lost-response recovery and service restart');
  let lostReceipt;
  await pageA.route('**/api/v1/governance/commands', async route => {
    const response = await route.fetch(); lostReceipt = (await response.json()).receipt;
    await route.abort('connectionreset');
  }, { times: 1 });
  const originalCount = requests.filter(item => item.pathname === '/api/v1/governance/commands').length;
  const uncertain = await openCommand(pageA, 'set_goal', { goal: '重启后仍按原请求核对治理事实。', reason: '原请求恢复验收' });
  await confirm(uncertain);
  await uncertain.getByRole('heading', { name: '结果尚未确认', exact: true }).waitFor();
  const originalRequest = requests.filter(item => item.pathname === '/api/v1/governance/commands').at(-1).command;
  check('Lost governance POST response leaves the form, original ID and no resubmit control',
    await uncertain.locator('[name="goal"]').inputValue() === '重启后仍按原请求核对治理事实。' &&
    await uncertain.getByRole('button', { name: '确认提交', exact: true }).count() === 0 && lostReceipt.status === 'succeeded');
  const pending = await pageA.evaluate(() => sessionStorage.getItem('union-governance-requests'));
  check('Browser recovery storage contains only request metadata, never private form content or credentials',
    pending.includes(originalRequest.id) && !pending.includes('重启后仍按原请求核对治理事实') && !pending.includes(accounts.a.password));
  const outage = route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'storage_unavailable', error: '受控的回执查询暂不可用' }) });
  await pageA.route('**/api/v1/governance/receipts?*', outage);
  await uncertain.getByRole('button', { name: '查询原请求回执', exact: true }).click();
  await uncertain.getByText(/原请求标识已保留/).waitFor();
  await uncertain.locator('#close-governance').click();
  await pageA.reload(); await connected(pageA);
  host.stdin.write('{"op":"restart"}\n'); assert.equal((await nextLine()).restarted, true);
  await pageA.reload(); await connected(pageA);
  await pageA.unroute('**/api/v1/governance/receipts?*', outage);
  await pageA.getByRole('button', { name: `查询原请求 ${originalRequest.id}`, exact: true }).click();
  await pageA.locator('#governance-receipt-dialog').getByRole('region', { name: '原治理请求回执' }).waitFor();
  await pageA.locator('#close-governance-receipt').click();
  check('Reload and server restart recover the original issuer receipt without another POST',
    requests.filter(item => item.pathname === '/api/v1/governance/commands').length === originalCount + 1 &&
    (await session(pageA)).principal_id === accounts.a.principal && (await read(pageA, auId)).value.au.id === auId);

  progress('finite delegation, revocation and responsibility handoff');
  await navigate(pageA, auId, 'tasks');
  const appointmentB = await runCommand(pageA, 'appoint', { name: '接收记录人', principal_id: accounts.b.principal, duty: '接收并核对原内部工作' });
  const appointmentC = await runCommand(pageA, 'appoint', { name: '有限受托记录人', principal_id: accounts.c.principal, duty: '仅在有限授权内提交文字' });
  const bindingB = appointmentB.command.data.binding_id, bindingC = appointmentC.command.data.binding_id;
  const parent = await runCommand(pageA, 'grant_mandate', { work_id: handoffWork, binding_id: bindingA, can_delegate: true });
  const parentId = parent.command.data.mandate_id;
  const child = await runCommand(pageA, 'grant_mandate', { work_id: handoffWork, binding_id: bindingB, parent_id: parentId, can_delegate: true });
  await navigate(pageB, auId, 'tasks');
  const grandchild = await runCommand(pageB, 'grant_mandate', { work_id: handoffWork, binding_id: bindingC, parent_id: child.command.data.mandate_id });
  await navigate(pageC, auId, 'tasks');
  const delegated = await runCommand(pageC, 'begin_local_action', { work_id: handoffWork, mandate_id: grandchild.command.data.mandate_id });
  const delegatedAttempt = delegated.command.data.attempt_id;
  check('A → B → C delegation uses real accounts and the original Work with a three-mandate chain',
    (await read(pageC, auId)).value.au.attempts[delegatedAttempt].mandates.length === 3);
  await refresh(pageA);
  await runCommand(pageA, 'revoke_mandate', { mandate_id: parentId, reason: '明确撤回上游授权' });
  await refresh(pageC);
  const late = await runCommand(pageC, 'submit_local_result', { attempt_id: delegatedAttempt, content: '已经撤权后到达的内容只作为未采用事实保留。' }, 'rejected');
  const rejected = (await read(pageC, auId)).value;
  check('Revoked descendant content is preserved as evidence_only and does not complete or alter accepted Work results',
    late.receipt.effect === 'evidence_only' && rejected.au.attempts[delegatedAttempt].status === 'not_adopted' &&
    rejected.au.work[handoffWork].status === 'open' && rejected.au.work[handoffWork].result_ids.length === 0);
  const newAction = await directCommand(pageC, auId, 'begin_local_action', { attempt_id: crypto.randomUUID(), work_id: handoffWork, mandate_id: grandchild.command.data.mandate_id });
  check('A new action under a revoked ancestor is rejected at the production HTTP boundary',
    newAction.status === 200 && newAction.value.receipt.status === 'rejected');

  await refresh(pageA);
  const unrelatedWork = await runCommand(pageA, 'create_work', { binding_id: bindingB, title: '不受撤权影响的独立工作', instruction: '验证局部撤权不阻塞其他工作' });
  const independentId = unrelatedWork.command.data.work_id;
  const independentGrant = await runCommand(pageA, 'grant_mandate', { work_id: independentId, binding_id: bindingB });
  await refresh(pageB);
  const independentStart = await runCommand(pageB, 'begin_local_action', { work_id: independentId, mandate_id: independentGrant.command.data.mandate_id });
  await runCommand(pageB, 'submit_local_result', { attempt_id: independentStart.command.data.attempt_id, content: '独立工作继续完成其内部记录。' });
  await refresh(pageA);
  await runCommand(pageA, 'accept_local_result', { attempt_id: independentStart.command.data.attempt_id, reason: '独立授权与当前版本有效' });
  check('An unrelated Work continues through submission and acceptance after revocation', (await read(pageA, auId)).value.au.work[independentId].status === 'delivered');
  await runCommand(pageA, 'handoff_responsibility', { from_binding_id: bindingA, to_binding_id: bindingB, reason: '由接收记录人继续原工作责任' });
  const handed = (await read(pageA, auId)).value;
  check('Responsibility handoff retains the original Work and failed attempt while invalidating the old binding',
    handed.au.work[handoffWork].responsible_binding_id === bindingB && handed.au.work[handoffWork].status === 'needs_review' &&
    !handed.au.bindings[bindingA].active && handed.au.attempts[delegatedAttempt].status === 'not_adopted' &&
    handed.au.work[firstWork].responsible_binding_id === bindingA);
  await runCommand(pageA, 'update_work', { work_id: handoffWork, title: '沿原标识交接的工作', instruction: '核对旧内容后由新责任继续', status: 'open', reason: '明确采用交接并继续' });
  const handedGrant = await runCommand(pageA, 'grant_mandate', { work_id: handoffWork, binding_id: bindingB });
  // A bounded slow AU read must not let the harness open a form from an older snapshot.
  await pageB.route('**/api/v1/aus/' + auId, async route => {
    await new Promise(resolve => setTimeout(resolve, 600));
    await route.continue();
  }, { times: 1 });
  await refresh(pageB);
  const handedStart = await runCommand(pageB, 'begin_local_action', { work_id: handoffWork, mandate_id: handedGrant.command.data.mandate_id });
  await runCommand(pageB, 'submit_local_result', { attempt_id: handedStart.command.data.attempt_id, content: '接收责任后沿原工作形成的内部记录。' });
  await refresh(pageA);
  await runCommand(pageA, 'accept_local_result', { attempt_id: handedStart.command.data.attempt_id, reason: '新责任、授权和原工作均已核对' });
  check('The recipient completes the same Work after explicit review and a new mandate',
    (await read(pageA, auId)).value.au.work[handoffWork].status === 'delivered');

  progress('self-confirmed governance transfer and reserved recovery');
  await navigate(pageA, auId, 'overview');
  const nomination = await runCommand(pageA, 'nominate_governor', { principal_id: accounts.b.principal, reason: '提名另一账号接任治理' });
  await navigate(pageB, auId, 'overview');
  await runCommand(pageB, 'accept_governance', { reason: '接任者本人确认治理责任' });
  const transferred = (await read(pageB, auId)).value;
  check('A second core account confirms governance transfer; the immutable original root remains and local governance returns to prepared',
    transferred.au.governance.current_principal_id === accounts.b.principal && transferred.au.governance_root.governor_principal_id === accounts.a.principal && transferred.governance_status === 'prepared');
  await pageA.locator('#refresh').click();
  await until(async () => await pageA.getByRole('region', { name: '本地治理', exact: true }).count() === 0, 'The old principal projection remained after losing AU access');
  check('The old creator loses current AU projection after governance and responsibility handoff', (await read(pageA, auId)).status === 403);
  await pageA.getByRole('button', { name: `查询原请求 ${nomination.command.id}`, exact: true }).click();
  await pageA.locator('#governance-receipt-dialog').getByRole('region', { name: '原治理请求回执' }).waitFor();
  check('The revoked original issuer can still query its own historical governance receipt', (await requestReceipt(pageA, nomination.command)).status === 200);
  await pageA.locator('#close-governance-receipt').click();
  const unauthorized = await pageA.evaluate(async command => {
    const response = await fetch('/api/v1/governance/commands', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(command) });
    return { status: response.status, value: await response.json() };
  }, { id: crypto.randomUUID(), organization_id: auId, kind: 'amend_charter', base_version: transferred.au.version, data: { charter: transferred.au.charter, reason: '旧主体的受控拒绝检查' } });
  check('Being the immutable creator does not restore old governance authority', unauthorized.status === 403 && unauthorized.value.code === 'not_authorized');

  // Registration recovery is exercised after a real AU handoff, preserving its principal.
  await pageB.getByRole('button', { name: '退出登录', exact: true }).click();
  await pageB.getByRole('button', { name: '忘记密码，使用恢复码', exact: true }).click();
  await pageB.locator('[name="username"]').fill(accounts.b.username);
  await pageB.locator('[name="code"]').fill(accounts.b.recovery);
  accounts.b.password = password();
  await pageB.locator('[name="new_password"]').fill(accounts.b.password);
  await pageB.getByRole('button', { name: '恢复账号', exact: true }).click();
  await until(async () => await pageB.getByLabel('账号恢复码', { exact: true }).count() > 0 || await pageB.getByText('已连接本机服务', { exact: true }).count() > 0, 'The recovered core account did not return to the workspace');
  if (await pageB.getByLabel('账号恢复码', { exact: true }).count()) {
    secrets.push(await pageB.getByLabel('账号恢复码', { exact: true }).inputValue());
    await pageB.getByRole('button', { name: '已保存，进入工作台', exact: true }).click();
  }
  await connected(pageB);
  check('A registered participant recovers its password and retains its current governance principal', (await session(pageB)).principal_id === accounts.b.principal);
  await navigate(pageB, auId, 'overview');
  await runCommand(pageB, 'configure_governance', { unavailability_mode: 'successor_after_timeout', timeout_seconds: '60', successor_principal_id: accounts.a.principal, reason: '预先明确失能后的恢复主体' });
  await navigate(pageA, auId, 'overview');
  await runCommand(pageA, 'acknowledge_recovery', { reason: '指定后继者本人确认当前恢复职责' });
  await refresh(pageB);
  await runCommand(pageB, 'activate_governance', { reason: '后继确认后启用有界本地治理' });
  const activated = (await read(pageB, auId)).value;
  const validUntil = activated.au.governance.valid_until * 1000;
  await viewports(pageB, 'governance');
  await navigate(pageB, auId, 'tasks'); await viewports(pageB, 'responsibility');
  await navigate(pageB, auId, 'overview');
  const form = await openCommand(pageB, 'set_goal', { goal: '键盘预览后取消，不应提交的目标。', reason: '取消预检检查' });
  for (const width of [1440, 1024, 390, 320]) {
    await pageB.setViewportSize({ width, height: 900 });
    check(`Governance form fits ${width}px`, await pageB.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  }
  await form.locator('[name="goal"]').focus();
  await pageB.waitForTimeout(4300);
  check('Background polling retains the governance form draft and keyboard focus',
    await form.locator('[name="goal"]').inputValue() === '键盘预览后取消，不应提交的目标。' &&
    await pageB.evaluate(() => document.activeElement?.getAttribute('name') === 'goal'));
  await form.getByRole('button', { name: '预览影响', exact: true }).focus(); await pageB.keyboard.press('Enter');
  await form.getByRole('button', { name: '确认提交', exact: true }).waitFor();
  for (const width of [1440, 1024, 390, 320]) {
    await pageB.setViewportSize({ width, height: 900 });
    check(`Governance confirmation preview fits ${width}px`, await pageB.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    for (const [selector, label] of [
      ['.preview-panel > p:not(.form-note)', 'confirmation effects and versions'],
      ['.preview-panel .form-note', 'confirmation effective-result notice'],
      ['.preview-panel .au-facts dt', 'confirmation field labels'],
      ['.preview-panel .au-facts dd', 'confirmation values'],
      ['.preview-panel h3', 'confirmation heading'],
      ['.preview-panel summary', 'confirmation full-content control'],
    ]) await measureReadability(pageB, '#governance-dialog ' + selector, `${label} at ${width}px`, 14);
  }
  await pageB.screenshot({ path: path.join(output, 'preview-320.png'), fullPage: true });
  await form.screenshot({ path: path.join(output, 'preview-320-dialog.png') });
  await form.getByRole('button', { name: '确认提交', exact: true }).scrollIntoViewIfNeeded();
  await form.screenshot({ path: path.join(output, 'preview-320-confirm.png') });
  assertReadability();
  let releasePreflight;
  const hold = new Promise(resolve => { releasePreflight = resolve; });
  await pageB.route('**/api/session', async route => { await hold; await route.continue().catch(() => undefined); });
  const beforeCancel = requests.length;
  await form.getByRole('button', { name: '确认提交', exact: true }).click();
  await form.getByText('正在核对身份…', { exact: true }).waitFor();
  await pageB.keyboard.press('Escape'); releasePreflight();
  await pageB.waitForTimeout(300);
  check('Keyboard cancellation during identity preflight sends no governance POST', requests.length === beforeCancel);
  check('Keyboard cancellation returns focus to the command trigger',
    await pageB.locator('[data-governance="set_goal"]').first().evaluate(element => document.activeElement === element));
  await pageB.unroute('**/api/session');
  progress('waiting for the adopted 60-second governance deadline');
  await until(async () => Date.now() > validUntil + 250, 'The adopted governance deadline did not pass', 65000);
  await navigate(pageA, auId, 'overview');
  await runCommand(pageA, 'recover_governance', { reason: '按已经确认的超时程序接任，无需失能者在线批准' });
  const recovered = (await read(pageA, auId)).value;
  check('The preconfirmed successor recovers through the real expired deadline and preserves AU, original root and Work history',
    recovered.au.id === auId && recovered.au.governance.current_principal_id === accounts.a.principal &&
    recovered.au.governance_root.governor_principal_id === accounts.a.principal && recovered.au.work[handoffWork].status === 'delivered' && recovered.governance_status === 'prepared');
  await runCommand(pageA, 'exit_governance', { reason: '受控验收结束，明确退出本地治理' });
  check('Explicit exit preserves adopted results and does not claim remote cancellation',
    (await read(pageA, auId)).value.governance_status === 'exited' && Object.keys((await read(pageA, auId)).value.au.results).length === 3);
  const expectedKinds = ['adopt_governance', 'configure_governance', 'acknowledge_recovery', 'activate_governance', 'renew_governance', 'nominate_governor', 'accept_governance', 'recover_governance', 'exit_governance', 'amend_charter', 'set_goal', 'appoint', 'update_appointment', 'create_work', 'update_work', 'grant_mandate', 'revoke_mandate', 'handoff_responsibility', 'begin_local_action', 'submit_local_result', 'accept_local_result'];
  check('All 21 S05 command kinds complete their rendered preview and production HTTP path', expectedKinds.every(kind => uiKinds.has(kind)));
  check('No model or legacy execution command was dispatched', requests.filter(item => item.pathname === '/api/commands').every(item => item.command.kind === 'create_v1'));
  check('No browser or service exception occurred', errors.length === 0);
  const result = { controlled: true, evidence_scope: 'React / HTTP / SQLite; human local submissions; not autonomous business',
    observed_at: new Date().toISOString(), console_assets: consoleAssets,
    node: process.version, browser: browser.version(), command_kinds: [...uiKinds].sort(),
    submitted_commands: requests.length, real_model_dispatches: 0,
    readability_groups: readability.length, readability_measurements: readability.reduce((count, group) => count + group.measurements.length, 0), checks };
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify(result, null, 2));
  process.stdout.write(JSON.stringify({ passed: checks.length, command_kinds: uiKinds.size, real_model_dispatches: 0 }) + '\n');
})().catch(error => {
  const message = sanitize(error.message);
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, 'failure.json'), JSON.stringify({ checks, error: message, errors: errors.map(sanitize) }, null, 2));
  process.stderr.write(message + '\n'); process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (host && host.exitCode === null && !host.stdin.destroyed) {
    host.stdin.write('{"op":"stop"}\n');
    await new Promise(resolve => { host.once('exit', resolve); setTimeout(() => { host.kill(); resolve(); }, 5000).unref(); });
  }
});
