// S01/T12: real Chromium and a restartable local HTTP service, no model calls.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'union-core-browser-'));
const output = path.resolve(process.env.UNION_CORE_EVIDENCE || '.union/core-creation-browser');
const checks = [], errors = [], commands = [], receiptUrls = [];
let host, browser, lines;
const check = (name, value = true) => { assert.ok(value, name); checks.push(name); };
const connected = page => page.getByText('已连接本机服务', { exact: true }).waitFor();
const session = page => page.evaluate(async () => (await fetch('/api/session')).json());
const pending = page => page.evaluate(() => JSON.parse(sessionStorage.getItem('union-pending') || '[]'));
function nextLine() {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('Local browser host did not respond')), 20000);
    lines.once('line', line => { clearTimeout(timeout); resolve(JSON.parse(line)); });
  });
}
async function until(predicate, description) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error(description);
}
async function createForm(page, name, goal) {
  await page.locator('[data-command="create_v1"]').first().click();
  await page.getByLabel('AU名称', { exact: true }).fill(name);
  await page.getByLabel('AU目标', { exact: true }).fill(goal);
}
async function submit(page) {
  await page.locator('#preview-operation').click();
  await page.locator('#commit-operation').click();
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  host = spawn(process.env.UNION_PYTHON || 'python3',
    ['-X', 'utf8', 'tests/model_access_browser_host.py', '--root', temp],
    { cwd: root, stdio: ['pipe', 'pipe', 'pipe'] });
  host.stderr.on('data', data => errors.push(String(data)));
  lines = readline.createInterface({ input: host.stdout });
  const ready = await nextLine();
  browser = await chromium.launch({
    executablePath: process.env.UNION_CHROMIUM_PATH ||
      (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : chromium.executablePath()),
    headless: true,
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.pathname === '/api/commands' && request.method() === 'POST')
      commands.push(request.postDataJSON());
    if (url.pathname.endsWith('/receipts')) receiptUrls.push(url.pathname + url.search);
  });

  // Use the fixed normal entry; the private host ticket is deliberately unused.
  await page.goto(ready.origin + '/overview');
  await page.getByRole('heading', { name: '建立管理员账号', exact: true }).waitFor();
  await page.locator('[name="username"]').fill('s01-browser-owner');
  await page.locator('[name="password"]').fill('s01-browser-only-password');
  await page.getByRole('button', { name: '建立管理员账号', exact: true }).click();
  await page.getByLabel('账号恢复码', { exact: true }).waitFor();
  await page.getByRole('button', { name: '已保存，进入工作台', exact: true }).click();
  await connected(page);
  const originalSession = await session(page);
  check('Normal first setup supplies a stable core principal without a platform account',
    originalSession.core_protocol === 'core.au.v1' && /^[a-f0-9-]{36}$/.test(originalSession.principal_id) &&
    !originalSession.platform_admin);
  check('Ordinary creation is V1 and legacy creation is explicitly separate',
    await page.locator('[data-command="create_v1"]').isEnabled() &&
    await page.getByRole('button', { name: '旧版兼容试验（含小说）', exact: true }).isEnabled());

  await createForm(page, 'A'.repeat(200), '持久保存同一 AU 的目标、初始治理主体和资源计划。');
  const goal = await page.getByLabel('AU目标', { exact: true }).inputValue();
  await page.getByLabel('AU目标', { exact: true }).focus();
  await page.waitForTimeout(4300);
  check('Background reads preserve creation input and keyboard focus',
    await page.getByLabel('AU目标', { exact: true }).inputValue() === goal &&
    await page.evaluate(() => document.activeElement?.getAttribute('name') === 'goal'));
  await context.setOffline(true);
  await page.getByText('浏览器网络已断开', { exact: false }).waitFor();
  await page.locator('#preview-operation').click();
  check('Offline preview keeps the original input and sends no create request',
    await page.getByLabel('AU目标', { exact: true }).inputValue() === goal && commands.length === 0);
  await context.setOffline(false);
  await connected(page);
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    check('Creation form fits ' + width + 'px',
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    if (width === 320)
      await page.screenshot({ path: path.join(output, 'create-mobile.png'), fullPage: true });
  }
  await page.locator('#preview-operation').focus();
  await page.keyboard.press('Enter');
  await page.locator('#commit-operation').focus();
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: '完成，返回工作台', exact: true }).waitFor();
  check('Keyboard submission returns a prepared receipt with an explicit inactive boundary',
    (await page.locator('#operation-result').innerText()).includes('自主行动尚未启用') &&
    commands.length === 1 && commands[0].kind === 'create_v1');
  await page.getByRole('button', { name: '完成，返回工作台', exact: true }).click();
  await page.getByRole('region', { name: 'AU准备记录', exact: true }).waitFor();
  const first = (await session(page)).organizations[0];
  const readAU = id => page.evaluate(async auId => (await fetch('/api/v1/aus/' + auId)).json(), id);
  const original = await readAU(first.id);
  check('Prepared state, resource plan and trusted governance root agree across UI and HTTP',
    original.au.autonomy_state === 'inactive' && original.au.resource_state === 'planned' &&
    original.au.governance_root.governor_principal_id === originalSession.principal_id &&
    original.au.governance_root.creator_principal_id === originalSession.principal_id &&
    original.au.goal === goal && !original.capabilities.autonomous_business);
  check('Prepared workspace exposes no legacy run or model configuration action',
    await page.locator('[data-command="start"],[data-command="api_connection"],[data-command="api_test"]').count() === 0);
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    check('Prepared record fits ' + width + 'px',
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    check('The complete supported AU name is readable at ' + width + 'px', await page.evaluate(() => {
      const heading = document.querySelector('.prepared-au .mission-copy h2');
      const panel = heading.closest('.mission-panel').getBoundingClientRect();
      const range = document.createRange();
      range.selectNodeContents(heading);
      return Array.from(range.getClientRects()).every(rect => rect.left >= panel.left && rect.right <= panel.right);
    }));
    if ([1440, 320].includes(width))
      await page.screenshot({ path: path.join(output, 'prepared-' + width + '.png'), fullPage: true });
  }
  await page.reload(); await connected(page);
  check('Reload reopens the original AU', (await readAU(first.id)).au.id === first.id);
  host.stdin.write('{"op":"restart"}\n');
  assert.equal((await nextLine()).restarted, true);
  await page.reload(); await connected(page);
  check('Service restart preserves the account principal, AU and governance record',
    (await session(page)).principal_id === originalSession.principal_id &&
    JSON.stringify(await readAU(first.id)) === JSON.stringify(original));
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  await page.getByRole('heading', { name: '登录 UNION', exact: true }).waitFor();
  await page.locator('[name="username"]').fill('s01-browser-owner');
  await page.locator('[name="password"]').fill('s01-browser-only-password');
  await page.getByRole('button', { name: '登录 UNION', exact: true }).click();
  await connected(page);
  check('Normal password login reopens the same AU without another invitation',
    (await session(page)).principal_id === originalSession.principal_id &&
    (await readAU(first.id)).au.id === first.id);

  await page.getByRole('button', { name: '旧版兼容试验（含小说）', exact: true }).click();
  await page.locator('[name="company_template"]').selectOption('novel');
  await page.locator('[name="goal"]').fill('保留旧版输入，不提交或运行。');
  await context.setOffline(true);
  check('The explicit legacy form preserves its input during a network interruption',
    await page.locator('[name="goal"]').inputValue() === '保留旧版输入，不提交或运行。');
  await context.setOffline(false);
  await page.keyboard.press('Escape');
  await connected(page);

  // Persist a second AU, then lose only its POST response. Block lookup until
  // reload so recovery must use the original kind/ID from session storage.
  let storedReceipt;
  const blockedReceipts = route => route.fulfill({
    status: 503, contentType: 'application/json',
    body: JSON.stringify({ code: 'storage_unavailable', error: 'Controlled lookup outage' }),
  });
  await page.route('**/api/v1/receipts?*', blockedReceipts);
  await page.route('**/api/commands', async route => {
    const response = await route.fetch();
    storedReceipt = (await response.json()).receipt;
    await route.abort('connectionreset');
  }, { times: 1 });
  await createForm(page, 'S01 原请求恢复', '丢失响应后仍只查询原创建请求。');
  await submit(page);
  await page.getByRole('heading', { name: '结果尚未确认', exact: true }).waitFor();
  const retained = await pending(page);
  check('Lost POST response retains only original request identity, never input or credentials',
    retained.length === 1 && retained[0].id === commands[1].id && retained[0].kind === 'create_v1' &&
    retained[0].organization_id === null && !JSON.stringify(retained).includes('丢失响应'));
  assert.equal(storedReceipt.status, 'succeeded');
  await page.locator('#close-operation').click();
  await page.reload(); await connected(page);
  check('Reload retains the pending creation and does not send it again',
    commands.length === 2 && (await pending(page))[0].id === commands[1].id);
  await page.getByRole('button', { name: '查询原请求', exact: true }).click();
  await page.unroute('**/api/v1/receipts?*', blockedReceipts);
  await until(async () => (await pending(page)).length === 0, 'Original creation receipt did not reconcile');
  await page.getByRole('heading', { name: /AU已准备/ }).waitFor();
  await page.locator('#close-operation').click();
  await connected(page);
  check('Recovery queries the versioned creation receipt without an organization parameter',
    receiptUrls.some(url => url.startsWith('/api/v1/receipts?id=' + commands[1].id)) &&
    receiptUrls.every(url => !url.includes('organization_id')) && commands.length === 2);
  const finalSession = await session(page);
  check('Recovery retains exactly the original two AU IDs with no duplicate creation',
    finalSession.organizations.length === 2 && finalSession.organizations.some(item => item.id === first.id) &&
    finalSession.organizations.some(item => item.id === storedReceipt.organization_id));
  await page.locator('#org-select').selectOption(first.id);
  await until(async () => await page.getByRole('region', { name: 'AU准备记录' }).getByRole('heading', { name: original.au.name, exact: true }).count() === 1,
    'Original AU was not displayed after switching');
  check('Switching restores the original AU instead of the recovered request content',
    (await page.getByRole('region', { name: 'AU准备记录' }).innerText()).includes(goal));
  check('Only the two explicitly submitted creation commands ran, with zero model calls',
    commands.length === 2 && commands.every(command => command.kind === 'create_v1'));
  check('No browser or service exception occurred', errors.length === 0);
  fs.writeFileSync(path.join(output, 'checks.json'),
    JSON.stringify({ controlled: true, realProviderCalls: 0, node: process.version, checks }, null, 2));
  process.stdout.write(JSON.stringify({ passed: checks.length, realProviderCalls: 0 }) + '\n');
})().catch(error => {
  console.error(error.message);
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, 'failure.json'), JSON.stringify({ checks, error: error.message, errors }, null, 2));
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (host) {
    host.stdin.write('{"op":"stop"}\n');
    await new Promise(resolve => {
      host.once('exit', resolve);
      setTimeout(() => { host.kill(); resolve(); }, 5000).unref();
    });
  }
});
