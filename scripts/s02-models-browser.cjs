// S02/M09: actual React, core HTTP, SQLite, modeld and pinned SDK on loopback.
// The provider is explicitly controlled. This does not prove a real account/profile.
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
const dataRoot = fs.mkdtempSync(path.join(privateRoot, 's02-browser-'));
const output = path.resolve(process.env.UNION_S02_UI_EVIDENCE || path.join(privateRoot, 's02-ui-browser'));
const secrets = [], errors = [], checks = [], requests = [], readability = [];
const credential = () => { const value = crypto.randomUUID() + '!Safe9'; secrets.push(value); return value; };
const apiKey = credential();
const accounts = { bootstrap: { username: 's02-bootstrap', password: credential() },
  core: { username: 's02-core', password: credential() } };
let browser, host, modeld, hostLines, origin, modeldReady, page;
const progress = stage => process.stdout.write(JSON.stringify({ stage }) + '\n');
const check = (name, value = true) => { assert.ok(value, name); checks.push(name); };
const sanitize = value => secrets.reduce((text, secret) => text.split(secret).join('[private]'), String(value))
  .split(dataRoot).join('[private test data]').replace(/#launch=[^\s"']+/g, '#launch=[private]');
function jsonLines(child) {
  const lines = readline.createInterface({ input: child.stdout });
  const pending = [], queue = [];
  lines.on('line', line => { const item = JSON.parse(line); if (pending.length) pending.shift()(item); else queue.push(item); });
  return () => queue.length ? Promise.resolve(queue.shift()) : new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('Isolated host readiness timed out')), 25000);
    pending.push(value => { clearTimeout(timeout); resolve(value); });
  });
}
async function until(predicate, message, timeout = 25000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error(message);
}
async function get(page, pathname) {
  return page.evaluate(async pathname => {
    const response = await fetch(pathname);
    return { status: response.status, value: await response.json() };
  }, pathname);
}
const session = async page => (await get(page, '/api/session')).value;
const auRead = async (page, id) => (await get(page, '/api/v1/aus/' + id)).value;
const modelRead = async (page, id) => (await get(page, '/api/v1/models?' + new URLSearchParams({ organization_id: id }))).value;
const stats = async () => { const response = await fetch(modeldReady.stats_url); assert.equal(response.status, 200); return response.json(); };
const connected = page => page.getByText('已连接本机服务', { exact: true }).waitFor();
async function navigate(page, id, section) {
  await page.goto(`${origin}/${section}?organization=${encodeURIComponent(id)}`);
  await connected(page);
  if (section === 'models') await page.getByRole('heading', { name: '接入模型，核对实际工具能力', exact: true }).waitFor();
}
async function field(dialog, name, value) {
  const input = dialog.locator(`[name="${name}"]`);
  const details = input.locator('xpath=ancestor::details[1]');
  if (await details.count() && !await details.evaluate(element => element.open)) await details.locator('summary').click();
  if (typeof value === 'boolean') await input.setChecked(value);
  else if (await input.evaluate(element => element.tagName) === 'SELECT') await input.selectOption(String(value));
  else await input.fill(String(value));
}
async function confirm(dialog) {
  await dialog.getByRole('button', { name: '预览影响', exact: true }).click();
  await dialog.getByRole('button', { name: '确认提交', exact: true }).click();
}
async function refreshModels(page) {
  await page.getByRole('button', { name: '刷新模型记录', exact: true }).click();
  await connected(page);
}
async function modelCommand(page, label, fields = {}, container = page) {
  await container.getByRole('button', { name: label, exact: true }).click();
  const dialog = page.locator('#model-command-dialog');
  await dialog.waitFor();
  for (const [name, value] of Object.entries(fields)) await field(dialog, name, value);
  const posted = page.waitForRequest(request => new URL(request.url()).pathname === '/api/v1/models/commands' && request.method() === 'POST');
  const [sent] = await Promise.all([posted, confirm(dialog)]);
  const command = sent.postDataJSON();
  await dialog.getByRole('region', { name: '模型命令回执', exact: true }).waitFor();
  const receipt = await get(page, '/api/v1/models/receipts?' + new URLSearchParams({ organization_id: command.organization_id, id: command.id }));
  assert.equal(receipt.status, 200);
  assert.equal(receipt.value.receipt.status, 'succeeded', sanitize(receipt.value.receipt.message));
  await dialog.getByRole('button', { name: '返回模型配置', exact: true }).click();
  await refreshModels(page);
  return { command, receipt: receipt.value.receipt };
}
async function governance(page, id, kind, fields) {
  await page.locator(`[data-governance="${kind}"]`).first().click();
  const dialog = page.locator('#governance-dialog');
  for (const [name, value] of Object.entries(fields)) await field(dialog, name, value);
  const response = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/governance/commands' && response.request().method() === 'POST');
  await confirm(dialog);
  const receipt = (await (await response).json()).receipt;
  assert.equal(receipt.status, 'succeeded', sanitize(receipt.message));
  await dialog.getByRole('button', { name: '完成，返回工作台', exact: true }).click();
  await page.locator('#refresh').click();
  await until(async () => (await page.locator('#snapshot-meta').textContent()).includes(`状态 v${receipt.version} ·`), 'Governance projection did not refresh');
  return auRead(page, id);
}
async function register(page, account, setup = false) {
  await page.goto(origin + '/overview');
  if (!setup) await page.getByRole('button', { name: '登记核心参与者', exact: true }).click();
  await page.locator('[name="username"]').fill(account.username);
  await page.locator('[name="password"]').fill(account.password);
  await page.getByRole('button', { name: setup ? '建立管理员账号' : '登记核心参与者', exact: true }).click();
  const recovery = page.getByLabel('账号恢复码', { exact: true });
  await recovery.waitFor(); secrets.push(await recovery.inputValue());
  await page.getByRole('button', { name: '已保存，进入工作台', exact: true }).click();
  await connected(page);
  account.principal = (await session(page)).principal_id;
}
async function createAU(page, name) {
  await page.locator('[data-command="create_v1"]').first().click();
  await page.getByLabel('AU名称', { exact: true }).fill(name);
  await page.getByLabel('AU目标', { exact: true }).fill('核对明确选择的文本资料和有限模型工具往返。');
  await page.locator('#preview-operation').click(); await page.locator('#commit-operation').click();
  await page.getByRole('button', { name: '完成，返回工作台', exact: true }).click();
  await page.getByRole('region', { name: 'AU准备记录', exact: true }).waitFor();
  return (await session(page)).organizations.find(au => au.name === name).id;
}
async function screenshots(page, name) {
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    check(`${name} has no page overflow at ${width}px`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const values = await page.locator('.core-models .quiet-pill, .core-models .security-note').evaluateAll(elements => {
      const channels = color => color.match(/[\d.]+/g).map(Number);
      const luminance = rgb => rgb.slice(0, 3).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; })
        .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
      return elements.filter(el => el.getClientRects().length).map(el => {
        const style = getComputedStyle(el); let parent = el, background = 'rgb(255, 255, 255)';
        while (parent) { const color = getComputedStyle(parent).backgroundColor, rgba = channels(color);
          if (rgba.length === 3 || rgba[3] === 1) { background = color; break; } parent = parent.parentElement; }
        const a = luminance(channels(style.color)), b = luminance(channels(background));
        return { size: parseFloat(style.fontSize), contrast: (Math.max(a, b) + .05) / (Math.min(a, b) + .05) };
      });
    });
    check(`${name} status text is legible at ${width}px`, values.length > 0 && values.every(v => v.size >= 12 && v.contrast >= 4.5));
    readability.push({ name, width, values });
    await page.screenshot({ path: path.join(output, `${name}-${width}.png`), fullPage: true });
    const opener = page.getByRole('button', { name: '添加模型连接', exact: true });
    await opener.focus(); await page.keyboard.press('Enter');
    const dialog = page.locator('#model-command-dialog'); await dialog.waitFor();
    await field(dialog, 'name', '用于检查窄屏长名称和错误提示换行的模型连接');
    for (const [key, value] of Object.entries({ base_url: modeldReady.provider_base_url, api_key: apiKey, model: modeldReady.model_id })) await field(dialog, key, value);
    for (let i = 0; i < 9; i++) {
      await page.keyboard.press(i % 2 ? 'Shift+Tab' : 'Tab');
      assert.ok(await dialog.evaluate(el => el.contains(document.activeElement)), 'Modal focus remains contained');
    }
    await dialog.getByRole('button', { name: '预览影响', exact: true }).click();
    check(`${name} dialog preview and keyboard work at ${width}px`, await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1));
    await page.keyboard.press('Escape'); await dialog.waitFor({ state: 'hidden' });
    check(`${name} dialog restores keyboard focus at ${width}px`, await opener.evaluate(el => el === document.activeElement));
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
}
async function stop(child, message) {
  if (!child || child.exitCode !== null) return;
  await new Promise(resolve => {
    child.once('exit', resolve);
    if (message && !child.stdin.destroyed) child.stdin.write(message); else child.kill();
    setTimeout(() => { child.kill(); resolve(); }, 5000).unref();
  });
}

(async () => {
  assert.ok(process.env.UNION_BUN, 'Set UNION_BUN to the pinned Bun executable');
  fs.mkdirSync(output, { recursive: true });
  for (const [name, value] of [['admin.token', credential()], ['worker.token', credential()], ['api.token', apiKey]])
    fs.writeFileSync(path.join(dataRoot, name), value, { mode: 0o600 });
  modeld = spawn(process.env.UNION_BUN, ['services/modeld/test/fixtures/core-modeld-host.ts'],
    { cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  // SDK diagnostics stay private; only explicit browser errors enter public evidence.
  const sdkLog = fs.createWriteStream(path.join(dataRoot, 'sdk.log')); modeld.stderr.pipe(sdkLog);
  const ready = jsonLines(modeld);
  modeld.stdin.end(JSON.stringify({ directory: dataRoot, admin_token_file: 'admin.token', worker_token_file: 'worker.token', api_key_file: 'api.token' }));
  modeldReady = await ready(); assert.equal(modeldReady.ready, true);
  const clientConfig = path.join(dataRoot, 'client.json');
  fs.writeFileSync(clientConfig, JSON.stringify({ origin: modeldReady.modeld_url, admin_token_file: 'admin.token', worker_token_file: 'worker.token' }), { mode: 0o600 });
  host = spawn(process.env.UNION_PYTHON || 'python3', ['-X', 'utf8', 'tests/model_access_browser_host.py', '--root', path.join(dataRoot, 'core')],
    { cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, UNION_MODELD_CONFIG: clientConfig, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' } });
  host.stderr.on('data', value => errors.push(String(value)));
  hostLines = jsonLines(host); const coreReady = await hostLines(); origin = coreReady.origin;
  if (coreReady.board_url) secrets.push(coreReady.board_url);
  browser = await chromium.launch({ headless: true, executablePath: process.env.UNION_CHROMIUM_PATH ||
    (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : chromium.executablePath()) });
  const adminContext = await browser.newContext(), context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const adminPage = await adminContext.newPage(); page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/models/commands') requests.push(request.postDataJSON());
  });
  progress('ordinary core account and governed AU');
  await register(adminPage, accounts.bootstrap, true); await register(page, accounts.core);
  const identity = await session(page);
  check('The model journey starts as an ordinary core account without platform administration', identity.role === 'core' && !identity.platform_admin);
  const auId = await createAU(page, 'S02 所选资料验证');
  await governance(page, auId, 'adopt_governance', { timeout_seconds: 3600, reason: '明确采用有限验证的失能退出程序' });
  await governance(page, auId, 'activate_governance', { reason: '启用本轮有限的模型接入验证' });
  await navigate(page, auId, 'models');
  check('The models route is available in core mode', await page.getByRole('button', { name: '添加模型连接', exact: true }).isEnabled());
  await page.getByRole('button', { name: '添加模型连接', exact: true }).focus(); await page.keyboard.press('Enter');
  const keyboardDialog = page.locator('#model-command-dialog'); await keyboardDialog.waitFor();
  await page.keyboard.press('Escape'); await keyboardDialog.waitFor({ state: 'hidden' });
  check('Keyboard opens and closes the model dialog and restores the invoking control', await page.getByRole('button', { name: '添加模型连接', exact: true }).evaluate(el => el === document.activeElement));
  const saved = await modelCommand(page, '添加模型连接', { name: '所选文本模型', profile: 'openai_compatible',
    base_url: modeldReady.provider_base_url, api_key: apiKey, model: modeldReady.model_id, max_output_tokens: 256 });
  await until(async () => (await modelRead(page, auId)).operations.some(op => op.id === saved.receipt.operation_id && op.status === 'succeeded'), 'Connection registration did not finish');
  await refreshModels(page); await page.getByRole('heading', { name: '所选文本模型', exact: true }).waitFor();
  const connection = page.locator('.model-connections li').filter({ has: page.getByRole('heading', { name: '所选文本模型', exact: true }) });
  check('Saving performs zero inference and does not silently adopt a default', (await stats()).inference_posts === 0 && !(await modelRead(page, auId)).connections[0].is_default);
  check('Validation remains unavailable without explicit resource and document authority', await connection.getByRole('button', { name: '验证工具往返', exact: true }).isDisabled());
  await modelCommand(page, '授予有限调用', { max_calls: 2, allow_unknown_cost: true, reason: '只允许两次受控回环推理，费用未知明确保留' });
  await navigate(page, auId, 'settings');
  await governance(page, auId, 'amend_charter', { charter_text: '只读本次主动提交的资料，保留内部记录。', read_document: true, reason: '启用接入验证的受限只读工具' });
  await navigate(page, auId, 'models');
  await connection.getByRole('button', { name: '验证工具往返', exact: true }).click();
  const dialog = page.locator('#model-command-dialog');
  const documentText = '本次只读资料：交付方案包括创建 AU、明确授权、记录每次推理和可核对的工具结果。';
  await dialog.getByLabel('选择文本资料', { exact: true }).setInputFiles({ name: 'selected-material.txt', mimeType: 'text/plain', buffer: Buffer.from(documentText) });
  await until(async () => await dialog.locator('[name="document_text"]').inputValue() === documentText, 'Selected file was not loaded');
  await dialog.locator('[name="document_text"]').focus();
  await page.waitForTimeout(4300);
  check('Background model/session refresh preserves selected material and editing focus', await dialog.locator('[name="document_text"]').inputValue() === documentText && await dialog.locator('[name="document_text"]').evaluate(el => el === document.activeElement));
  const submitted = page.waitForRequest(request => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/models/commands');
  await confirm(dialog); const checkCommand = (await submitted).postDataJSON();
  await dialog.getByRole('region', { name: '模型命令回执', exact: true }).waitFor();
  await dialog.getByRole('button', { name: '返回模型配置', exact: true }).click();
  await until(async () => (await modelRead(page, auId)).checks.some(value => value.status === 'succeeded'), 'The actual tool roundtrip did not finish');
  await refreshModels(page); await page.getByText('工具往返已通过', { exact: true }).waitFor();
  const result = (await modelRead(page, auId)).checks[0], observed = await stats();
  const tool = JSON.parse(observed.calls[1].body.messages.find(message => message.role === 'tool').content);
  check('Two actual SDK HTTP calls return the selected material and tool-generated challenge', observed.inference_posts === 2 && observed.real_model_calls === 0 && result.output.includes(documentText) && result.output.includes(tool.challenge));
  check('The first inference has no copy of the selected private body or challenge', !JSON.stringify(observed.calls[0].body).includes(documentText) && !JSON.stringify(observed.calls[0].body).includes(tool.challenge));
  check('Each inference retains its own tokens and unknown cost', result.attempts.length === 2 && result.attempts.every(attempt => attempt.usage.input_tokens === 18 && attempt.usage.cost_minor === null));
  await modelCommand(page, '设为默认', {}, connection);
  check('Default adoption is explicit and adds no inference', (await modelRead(page, auId)).connections[0].is_default && (await stats()).inference_posts === 2);
  await screenshots(page, 'completed-model-check');

  progress('lost save response, original receipt and restart');
  await page.route('**/api/v1/models/commands', async route => { await route.fetch(); await route.abort('connectionreset'); }, { times: 1 });
  await page.getByRole('button', { name: '添加模型连接', exact: true }).click();
  const uncertain = page.locator('#model-command-dialog');
  for (const [name, value] of Object.entries({ name: '待核对第二连接', base_url: modeldReady.provider_base_url, api_key: apiKey, model: modeldReady.model_id })) await field(uncertain, name, value);
  await confirm(uncertain); await uncertain.getByRole('heading', { name: '结果尚未确认', exact: true }).waitFor();
  const original = requests.at(-1), countBefore = requests.length;
  check('Lost save response clears the secret and offers lookup instead of resubmission', await uncertain.locator('[name="api_key"]').inputValue() === '' && await uncertain.getByRole('button', { name: '确认提交', exact: true }).count() === 0);
  const unavailable = route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: '受控回执查询暂不可用', code: 'storage_unavailable' }) });
  await page.route('**/api/v1/models/receipts?*', unavailable);
  await uncertain.getByRole('button', { name: '查询原请求回执', exact: true }).click();
  await uncertain.getByRole('alert').filter({ hasText: '暂不可用' }).waitFor();
  await uncertain.locator('#close-model-command').click();
  check('An unresolved save does not disable another connection management path', await connection.getByRole('button', { name: '编辑连接', exact: true }).isEnabled());
  const cached = await page.evaluate(() => sessionStorage.getItem('union-model-requests'));
  check('Recovery cache holds identifiers only, without key or selected document', cached.includes(original.id) && !cached.includes(apiKey) && !cached.includes(documentText));
  await page.reload(); await connected(page);
  host.stdin.write('{"op":"restart"}\n'); assert.equal((await hostLines()).restarted, true);
  await page.unroute('**/api/v1/models/receipts?*', unavailable);
  await page.reload(); await connected(page);
  await page.getByRole('button', { name: `查询原请求 ${original.id}`, exact: true }).click();
  await page.locator('.model-recovery').getByRole('region', { name: '模型命令回执', exact: true }).waitFor();
  check('Reload and core restart recover the same save without POST replay or extra inference', requests.length === countBefore && (await stats()).inference_posts === 2);
  check('The same account, default and accepted output survive restart', (await session(page)).principal_id === identity.principal_id && (await modelRead(page, auId)).connections.find(c => c.id === saved.command.data.connection_id).is_default && (await modelRead(page, auId)).checks[0].output === result.output);
  const stranger = await get(adminPage, '/api/v1/models?' + new URLSearchParams({ organization_id: auId }));
  check('Platform administration alone cannot read this core AU model configuration', stranger.status === 403);
  const leak = JSON.stringify(await modelRead(page, auId));
  check('Public model projection and original command receipts do not contain credentials', !leak.includes(apiKey) && !(JSON.stringify((await get(page, '/api/v1/models/receipts?' + new URLSearchParams({ organization_id: auId, id: saved.command.id }))).value)).includes(apiKey));
  check('Old engine model endpoints cannot accept a V1 AU', (await get(page, '/api/models?' + new URLSearchParams({ organization_id: auId }))).status !== 200);

  progress('safe diagnostics, interrupted usage and independent connections');
  await modelCommand(page, '调整有限调用', { max_calls: 8, allow_unknown_cost: true, reason: '仅回环错误诊断测试，固定五个单次请求' });
  for (const [fault, code] of [['auth','provider_authentication_failed'], ['missing','model_not_found'],
    ['limit','provider_rate_limited'], ['unavailable','provider_unavailable'], ['interrupt','provider_result_unconfirmed']]) {
    const title = '受控诊断 ' + fault;
    const added = await modelCommand(page, '添加模型连接', { name: title, profile: 'openai_compatible',
      base_url: modeldReady.provider_base_url, api_key: apiKey, model: modeldReady.model_id + ':' + fault });
    await until(async () => (await modelRead(page, auId)).operations.some(op => op.id === added.receipt.operation_id && op.status === 'succeeded'), 'Diagnostic connection did not save');
    await refreshModels(page);
    const card = page.locator('.model-connections li').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
    const checked = await modelCommand(page, '验证工具往返', { document_name: title, document_text: '错误分支不应执行资料工具。' }, card);
    await until(async () => (await modelRead(page, auId)).checks.some(item => item.id === checked.receipt.check_id && item.status === 'unknown'), 'Provider error did not become a recoverable diagnostic');
    await refreshModels(page);
    const current = (await modelRead(page, auId)).checks.find(item => item.id === checked.receipt.check_id);
    const record = page.locator('.model-checks > li').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
    await record.getByText('下一步：' + current.diagnostic.next_step, { exact: true }).first().waitFor();
    check(`${fault} shows a safe specific diagnosis and next step`, current.diagnostic.code === code && (await record.innerText()).includes(current.diagnostic.next_step) && !(await record.innerText()).includes(apiKey));
    if (fault === 'interrupt') check('Interrupted original-event usage remains visible with unknown cost',
      current.attempts[0].usage.input_tokens === 37 && current.attempts[0].usage.basis === 'events' &&
      (await record.innerText()).includes('37 / 9') && (await record.innerText()).includes('已观测事件'));
    check(`${fault} cannot block management of an unrelated connection`, await connection.getByRole('button', { name: '编辑连接', exact: true }).isEnabled());
    await modelCommand(page, '停止后续步骤', { reason: '结束此受控错误的后续步骤，保留原调用和用量' }, record);
    await until(async () => (await modelRead(page, auId)).checks.some(item => item.id === current.id && item.stop_requested && item.status === 'unknown'), 'Local stop did not retain the original uncertain result');
  }
  await screenshots(page, 'model-diagnostics');
  const postsBeforeIsolation = (await stats()).inference_posts;
  await page.getByRole('button', { name: '添加模型连接', exact: true }).click();
  const offlineDialog = page.locator('#model-command-dialog'); await field(offlineDialog, 'name', '断网保留的输入');
  await context.setOffline(true); await page.waitForTimeout(4300);
  await context.setOffline(false); await connected(page);
  check('Offline recovery retains non-secret input and does not auto-submit', await offlineDialog.locator('[name="name"]').inputValue() === '断网保留的输入' && (await stats()).inference_posts === postsBeforeIsolation);
  await page.keyboard.press('Escape');
  progress('explicit Responses profile saves through core HTTP and actual modeld');
  const responsesSaved = await modelCommand(page, '添加模型连接', { name: 'Responses 受控连接',
    profile: 'openai_responses', base_url: modeldReady.provider_base_url, api_key: apiKey,
    model: modeldReady.model_id, max_output_tokens: 256 });
  await until(async () => (await modelRead(page, auId)).operations.some(op => op.id === responsesSaved.receipt.operation_id && op.status === 'succeeded'), 'Responses registration did not finish');
  await refreshModels(page);
  const responsesConnection = (await modelRead(page, auId)).connections.find(c => c.id === responsesSaved.command.data.connection_id);
  check('Responses profile is explicitly saved by the actual core and modeld', responsesConnection.profile === 'openai_responses');
  check('Saving Responses neither infers nor replaces the current default', !responsesConnection.is_default && (await stats()).inference_posts === postsBeforeIsolation);
  const responsesCard = page.locator('.model-connections li').filter({ has: page.getByRole('heading', { name: 'Responses 受控连接', exact: true }) });
  await responsesCard.getByRole('button', { name: '编辑连接', exact: true }).click();
  const responsesDialog = page.locator('#model-command-dialog');
  check('Editing keeps the native protocol but never refills its key', await responsesDialog.locator('[name="profile"]').inputValue() === 'openai_responses' && await responsesDialog.locator('[name="api_key"]').inputValue() === '');
  await page.keyboard.press('Escape');
  await navigate(page, auId, 'overview');
  const otherAU = await createAU(page, 'S02 身份隔离对照');
  await navigate(page, auId, 'models');
  let releaseLate;
  const late = new Promise(resolve => { releaseLate = resolve; });
  let captured;
  const intercepted = new Promise(resolve => { captured = resolve; });
  await page.route('**/api/v1/models?*', async route => {
    const response = await route.fetch(); captured(); await late; await route.fulfill({ response }).catch(() => {});
  }, { times: 1 });
  await page.getByRole('button', { name: '刷新模型记录', exact: true }).click(); await intercepted;
  await page.getByLabel('当前组织', { exact: true }).selectOption(otherAU);
  releaseLate(); await page.locator('.core-models').getByText('还没有保存的连接', { exact: true }).waitFor();
  check('A late original-AU response cannot populate the newly selected AU', !(await page.locator('.core-models').innerText()).includes(documentText) && !(await page.locator('.core-models').innerText()).includes('所选文本模型'));
  await context.clearCookies(); await page.reload();
  await register(page, { username: 's02-other-core', password: credential() });
  check('A different core account cannot read the old model records', (await get(page, '/api/v1/models?' + new URLSearchParams({ organization_id: auId }))).status === 403 && !(await page.locator('body').innerText()).includes(documentText));
  check('Identity and offline checks do not dispatch additional inference', (await stats()).inference_posts === postsBeforeIsolation);
  check('No browser or core service exception occurred', errors.length === 0);
  const assets = path.join(root, 'web/console/dist/assets');
  const record = { controlled: true, evidence_scope: 'React/core HTTP/SQLite/modeld/pinned SDK/loopback; no real account',
    observed_at: new Date().toISOString(), node: process.version, browser: browser.version(),
    console_assets: Object.fromEntries(fs.readdirSync(assets).filter(name => /\.(js|css)$/.test(name)).sort().map(name => [name, crypto.createHash('sha256').update(fs.readFileSync(path.join(assets, name))).digest('hex')])),
    inference_posts: (await stats()).inference_posts, successful_roundtrip_posts: 2, real_model_calls: 0, model_commands: requests.length,
    command_kinds: [...new Set(requests.map(request => request.kind))].sort(), checks, readability };
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify(record, null, 2) + '\n');
  process.stdout.write(JSON.stringify({ passed: checks.length, inference_posts: record.inference_posts, real_model_calls: 0 }) + '\n');
})().catch(async error => {
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, 'failure.json'), JSON.stringify({ checks, error: sanitize(error.message), errors: errors.map(sanitize) }, null, 2));
  if (page) await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
  process.stderr.write(sanitize(error.message) + '\n'); process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  await stop(host, '{"op":"stop"}\n'); await stop(modeld);
});
