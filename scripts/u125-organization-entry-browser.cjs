// U-125 / E01-E05,E08: production React + real local HTTP/auth/persistence.
// Synthetic prepared AUs only. Fault injection is identified in each check.
// Deliberately does not exercise the deferred U-126 creation form or Work UI.
const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const readline = require('node:readline');
const { chromium } = require('playwright-core');

const root = path.resolve(__dirname, '..');
const runId = new Date().toISOString().replace(/[:.]/g, '-');
const output = path.resolve(root, process.env.UNION_U125_EVIDENCE || '.union/u125-organization-entry', runId);
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'union-u125-browser-'));
const python = process.env.UNION_PYTHON || 'python3';
const checks = [], requests = [], browserErrors = [], serviceErrors = [], layoutFailures = [];
const expectedCommands = new Map();
const pendingReleases = new Set();
const startedAt = new Date().toISOString();
let host, browser, lines, origin, activePage;
let stage = 'setup';
let buildHash;

function check(name, value = true) {
  assert.ok(value, name);
  checks.push({ name, stage });
}
function checkLayout(name, value) {
  if (value) check(name);
  else layoutFailures.push({ name, stage });
}
const documentHash = () => createHash('sha256').update(fs.readFileSync(path.join(root, 'web/console/dist/index.html'))).digest('hex');
function nextLine() {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('Local browser host did not respond')), 20000);
    lines.once('line', line => {
      clearTimeout(timeout);
      try { resolve(JSON.parse(line)); } catch { reject(Error('Local host returned invalid control output')); }
    });
  });
}
async function until(predicate, description, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw Error(description);
}
const pathname = page => new URL(page.url()).pathname;
const coreReads = (from = 0, pageName) => requests.slice(from)
  .filter(item => item.path.startsWith('/api/v1/aus/') && (!pageName || item.page === pageName));
const commands = () => requests.filter(item => item.method === 'POST' && item.path === '/api/commands');
const requestJSON = (page, url, body) => page.evaluate(async ({ url, body }) => {
  const response = await fetch(url, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return { status: response.status, value: await response.json() };
}, { url, body });
const readSession = async page => {
  const response = await requestJSON(page, '/api/session');
  assert.equal(response.status, 200, 'Session must be read from the actual HTTP service');
  return response.value;
};
const mainHeading = (page, name) => page.locator('.organization-page-heading').getByRole('heading', { name, exact: true });
async function listed(page) {
  await mainHeading(page, '我的组织').waitFor();
  await until(async () => await page.locator('[data-command="create_v1"]').isEnabled(), 'Organization list did not become connected');
}
async function opened(page, id, name, section = '', title = '概况') {
  await until(() => pathname(page) === `/au/${id}${section ? '/' + section : ''}`, 'Scoped URL did not resolve');
  await mainHeading(page, title).waitFor();
  await until(async () => await page.locator('.organization-current').textContent() === name, 'Current AU did not finish its authorized read');
  if (!section) await page.getByRole('heading', { name, exact: true }).waitFor();
}
async function gotoAU(page, au, section = '', title = '概况') {
  const response = await page.goto(`${origin}/au/${au.id}${section ? '/' + section : ''}`);
  assert.equal(response.status(), 200, 'Declared organization URL must serve the production document');
  await opened(page, au.id, au.name, section, title);
}
async function refresh(page) {
  await page.getByRole('button', { name: '刷新', exact: true }).click();
}
function monitor(page, name) {
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => browserErrors.push({ page: name, message: error.message }));
  page.on('request', request => {
    const url = new URL(request.url());
    if (!['http:', 'https:'].includes(url.protocol)) return;
    const record = { page: name, stage, method: request.method(), path: url.pathname, originMatches: url.origin === origin };
    if (url.pathname === '/api/commands' && request.method() === 'POST') {
      const body = request.postDataJSON();
      record.id = body.id;
      record.kind = body.kind;
      record.expectedFixture = expectedCommands.get(body.id) === body.kind;
    }
    requests.push(record); // No cookie, body, recovery code, ticket or query value is recorded.
  });
}
const fixtureCharter = {
  text: 'U-125 受控浏览器章程：仅保存准备记录，无对外发布、支付或模型执行授权。',
  allowed_operations: ['create_member', 'create_position', 'update_position', 'assign', 'set_policy',
    'create_work', 'handoff', 'pause_work', 'resume_work', 'cancel_work', 'update_work', 'wait', 'set_strategy', 'record_memory'],
  allowed_tools: ['produce_artifact'],
  reserved_matters: ['goal', 'resources', 'charter', 'funding', 'dissolution'],
  board_can_amend: true,
};
async function createFixture(page, suffix, name, goal, kind = 'create_v1') {
  const id = `u125-fixture-${suffix}`;
  expectedCommands.set(id, kind);
  const response = await requestJSON(page, '/api/commands', {
    id, organization_id: null, base_version: null, kind,
    data: { name, goal, board_name: '受控准备记录', charter: fixtureCharter,
      resources: { max_calls: 8, timeout_seconds: 180 } },
  });
  assert.equal(response.status, 200, 'Controlled fixture creation HTTP status');
  assert.equal(response.value.receipt.status, 'succeeded', 'Controlled fixture creation receipt');
  return { id: response.value.receipt.organization_id, name, goal, requestId: id };
}
async function setup(page, username, register = false) {
  await page.goto(origin + '/');
  if (register) {
    await page.getByRole('heading', { name: '登录 UNION', exact: true }).waitFor();
    await page.getByRole('button', { name: '登记核心参与者', exact: true }).click();
  }
  const title = register ? '登记核心参与者' : '建立管理员账号';
  await page.getByRole('heading', { name: title, exact: true }).waitFor();
  await page.getByLabel('账号', { exact: true }).fill(username);
  await page.getByLabel('密码', { exact: true }).fill('u125-isolated-browser-password');
  await page.getByRole('button', { name: title, exact: true }).click();
  await page.getByLabel('账号恢复码', { exact: true }).waitFor();
  await page.getByRole('button', { name: '已保存，进入工作台', exact: true }).click();
  await listed(page);
}
async function login(page, username) {
  await page.getByRole('heading', { name: '登录 UNION', exact: true }).waitFor();
  await page.getByLabel('账号', { exact: true }).fill(username);
  await page.getByLabel('密码', { exact: true }).fill('u125-isolated-browser-password');
  await page.getByRole('button', { name: '登录 UNION', exact: true }).click();
}
async function noProtectedBody(page, au, description) {
  await until(async () => !await page.getByText(au.goal, { exact: true }).count() &&
    !await page.getByRole('heading', { name: au.name, exact: true }).count(), description);
}
async function layoutFits(page, description) {
  const fit = await page.evaluate(() => ({
    viewport: innerWidth,
    document: document.documentElement.scrollWidth,
    main: document.querySelector('main')?.getBoundingClientRect().right,
  }));
  checkLayout(`${description} (viewport=${fit.viewport}, document=${fit.document}, mainRight=${fit.main})`,
    fit.document <= fit.viewport + 1 && fit.main <= fit.viewport + 1);
}
async function delayRead(page, auId) {
  let started, release;
  const seen = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('Injected delayed AU read did not reach the local service')), 15000);
    started = () => { clearTimeout(timeout); resolve(); };
  });
  const held = new Promise(resolve => { release = resolve; });
  pendingReleases.add(release);
  const pattern = `**/api/v1/aus/${auId}`;
  const handler = async route => {
    const response = await route.fetch(); // The held response is real authorized HTTP data.
    started();
    await held;
    try { await route.fulfill({ response }); } catch (error) {
      if (!/cancel|closed|disposed|handled/i.test(error.message)) throw error;
    }
  };
  await page.route(pattern, handler);
  return { seen, release: () => { release(); pendingReleases.delete(release); }, clear: () => page.unroute(pattern, handler) };
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  assert.ok(fs.existsSync(path.join(root, 'web/console/dist/index.html')), 'Run npm run build:console first');
  buildHash = documentHash();
  const hostEnv = { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' };
  for (const key of Object.keys(hostEnv)) if (key.startsWith('UNION_KANBAN') || key === 'UNION_MODELD_CONFIG') delete hostEnv[key];
  host = spawn(python, ['-X', 'utf8', 'tests/model_access_browser_host.py', '--root', temp],
    { cwd: root, env: hostEnv, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
  host.stderr.on('data', data => serviceErrors.push(String(data)));
  lines = readline.createInterface({ input: host.stdout });
  ({ origin } = await nextLine()); // The host's one-time ticket is never consumed or logged.
  browser = await chromium.launch({ headless: true,
    executablePath: process.env.UNION_CHROMIUM_PATH || (process.platform === 'win32'
      ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : chromium.executablePath()) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  activePage = page;
  monitor(page, 'owner');
  await setup(page, 'u125-browser-owner');
  const sessionA = await readSession(page);
  check('E01: fixed-address first setup enters the empty V1 list without a ticket or private platform account',
    pathname(page) === '/organizations' && sessionA.core_protocol === 'core.au.v1' && !!sessionA.principal_id && !sessionA.platform_admin);
  check('E01: empty entry reads no AU, snapshot or legacy artifact', coreReads().length === 0 &&
    await page.getByRole('heading', { name: '还没有可访问的 V1 组织', exact: true }).count() === 1);
  check('E08: the empty list offers one labeled V1 creation action and no legacy selector or creation control',
    await page.locator('[data-command="create_v1"]').count() === 1 &&
    await page.locator('#org-select,[data-command="create"]').count() === 0);

  stage = 'controlled-fixtures';
  const legacy = await createFixture(page, 'legacy', 'U-125 legacy fixture', '旧版隔离记录，不应出现在 V1 界面。', 'create');
  const a = await createFixture(page, 'a', 'U-125-A-' + 'A'.repeat(192), '组织甲的受控目的：保留同一身份和准备记录，不调用模型。');
  const b = await createFixture(page, 'b', 'U-125 组织乙', '组织乙的独立目的：页面切换不得继承组织甲的内容。');
  const beforeList = requests.length;
  await page.goto(origin + '/');
  await listed(page);
  const catalog = await readSession(page);
  check('E01: an existing legacy catalog entry does not become the default AU or appear in the V1 list',
    catalog.organizations.some(item => item.id === legacy.id && item.profile !== 'core_v1') &&
    await page.getByRole('list', { name: '可访问的组织' }).getByRole('link').count() === 2 &&
    await page.getByText(legacy.name, { exact: true }).count() === 0 && coreReads(beforeList).length === 0);
  check('E01: existing V1 entries are listed without selecting or reading the first AU', pathname(page) === '/organizations');
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await layoutFits(page, `E08: organization list fits ${width}px with a 200-character AU name`);
    await page.screenshot({ path: path.join(output, `list-${width}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('list', { name: '可访问的组织' }).getByRole('link').filter({ hasText: a.name }).click();
  await opened(page, a.id, a.name);
  const originalRead = await requestJSON(page, '/api/v1/aus/' + a.id);
  check('E01: explicit selection opens the selected prepared AU with its trusted original principal',
    originalRead.status === 200 && originalRead.value.au.governance_root.governor_principal_id === sessionA.principal_id &&
    originalRead.value.au.autonomy_state === 'inactive' && originalRead.value.au.resource_state === 'planned' &&
    await page.getByText(a.goal, { exact: true }).count() === 1);
  check('E08: overview distinguishes preparation, planned calls and inactive business without claiming empty work or zero spending',
    (await page.locator('.organization-state').innerText()).includes('尚未启用') &&
    (await page.locator('.organization-main').innerText()).includes('不据此推断组织没有工作或资源消耗'));
  const recent = await page.evaluate(() => JSON.parse(localStorage.getItem('union-recent-au-v1')));
  check('E01: recent navigation stores only a versioned identity/service/AU reference',
    Object.keys(recent).sort().join(',') === 'au_id,principal_id,service_instance,version' && recent.au_id === a.id &&
    recent.principal_id === sessionA.principal_id && recent.service_instance === sessionA.service_instance && recent.version === 1);
  const beforeRecent = requests.length;
  await page.goto(origin + '/');
  await opened(page, a.id, a.name);
  check('E01: home revalidates the current principal and recent AU before reopening it',
    coreReads(beforeRecent).some(item => item.path === '/api/v1/aus/' + a.id));

  stage = 'navigation-and-layout';
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await layoutFits(page, `E08: prepared overview fits ${width}px with the full 200-character AU name`);
    checkLayout(`E08: full AU name is readable inside the main column at ${width}px`, await page.evaluate(() => {
      const heading = document.querySelector('.organization-purpose h2');
      const main = document.querySelector('main').getBoundingClientRect();
      const range = document.createRange(); range.selectNodeContents(heading);
      return Array.from(range.getClientRects()).every(rect => rect.left >= main.left - 1 && rect.right <= main.right + 1);
    }));
    const nav = page.getByRole('navigation', { name: '组织页面' });
    check(`E08: navigation exposes ${width <= 768 ? 'four direct' : 'eight'} organization pages at ${width}px`,
      await nav.locator('a:visible').count() === (width <= 768 ? 4 : 8));
    checkLayout(`E08: the extra-page toggle is visible only at mobile width (${width}px)`,
      await page.getByRole('button', { name: '更多页面', exact: true }).isVisible() === (width <= 768));
    if (width <= 768) {
      const menu = page.getByRole('button', { name: '更多页面', exact: true });
      await menu.focus(); await page.keyboard.press('Enter');
      check(`E08: mobile remaining navigation expands by keyboard at ${width}px`,
        await menu.getAttribute('aria-expanded') === 'true' && await nav.locator('a:visible').count() === 8);
      await page.keyboard.press('Shift+Tab');
      check(`E08: expanded mobile links are keyboard reachable at ${width}px`,
        await page.evaluate(() => document.activeElement?.getAttribute('data-nav') === 'collaboration'));
      await menu.focus(); await page.keyboard.press('Enter');
    }
    await page.screenshot({ path: path.join(output, `overview-${width}.png`), fullPage: true });
  }
  const account = page.getByRole('button', { name: '账号与登录', exact: true });
  await account.focus(); await page.keyboard.press('Enter');
  await page.getByRole('dialog', { name: '账号与登录', exact: true }).waitFor();
  check('E08: account dialog takes keyboard focus and labels the current core identity',
    await page.evaluate(() => !!document.activeElement?.closest('#account-dialog')) &&
    await page.getByLabel('当前核心身份标识', { exact: true }).inputValue() === sessionA.principal_id);
  await page.keyboard.press('Escape');
  check('E08: Escape closes the account dialog and restores a visible keyboard focus to its trigger',
    await page.getByRole('dialog').count() === 0 && await account.evaluate(element => {
      const style = getComputedStyle(element);
      return document.activeElement === element && style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
    }));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('navigation', { name: '组织页面' }).getByRole('link', { name: '工作', exact: true }).focus();
  await page.keyboard.press('Enter');
  await opened(page, a.id, a.name, 'work', '工作');
  // Heading visibility precedes Layout's post-commit focus effect on a fast VM.
  // Wait on the actual required focus; a permanently unfocused heading still fails.
  await until(() => mainHeading(page, '工作').evaluate(element => document.activeElement === element),
    'E08: keyboard navigation did not move focus to the new page heading');
  check('E08: keyboard navigation moves focus to the new page heading',
    await mainHeading(page, '工作').evaluate(element => document.activeElement === element));
  const sections = [['work', '工作'], ['results', '成果'], ['attention', '关注事项'], ['resources', '能力与资源'],
    ['governance', '治理与成员'], ['improvement', '改进'], ['collaboration', '合作']];
  for (const [section, title] of sections) {
    await gotoAU(page, a, section, title);
    for (const width of [1440, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await layoutFits(page, `E08: ${section} scoped shell fits ${width}px`);
    }
    check(`E02: ${section} uses only the current AU navigation and no legacy execution form`,
      await page.getByRole('navigation', { name: '组织页面' }).locator(`a:not([href^="/au/${a.id}"])`).count() === 0 &&
      await page.locator('[data-command="start"],#org-select').count() === 0);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await gotoAU(page, a);
  await page.goto(origin + '/tasks?organization=' + a.id);
  await opened(page, a.id, a.name, 'work', '工作');
  check('E02: a scoped old tasks link replaces itself with the canonical Work URL', new URL(page.url()).search === '');
  await page.goBack(); await opened(page, a.id, a.name);
  await page.goForward(); await opened(page, a.id, a.name, 'work', '工作');
  await page.reload(); await opened(page, a.id, a.name, 'work', '工作');
  check('E02/E08: back, forward and reload preserve the explicit AU and page after alias replacement');
  const beforeConflict = requests.length;
  await page.goto(`${origin}/au/${b.id}/work/work.beta/results/result.beta?organization=${a.id}`);
  await opened(page, b.id, b.name, 'work/work.beta/results/result.beta', '成果');
  check('E02: AU/Work/result deep link wins over a conflicting organization query without reading the other AU',
    coreReads(beforeConflict).length > 0 && coreReads(beforeConflict).every(item => item.path === '/api/v1/aus/' + b.id));
  await page.getByRole('alert').filter({hasText:'指定工作或成果不存在'}).waitFor();
  check('E02: a missing result deep link preserves all scope components and explicitly rejects body fallback',
    (await page.locator('main').innerText()).includes('指定工作或成果不存在') &&
    !requests.slice(beforeConflict).some(item => item.path === '/api/v1/work/results'));
  for (const target of ['/overview', '/tasks', '/artifacts', '/models', '/members', '/resources', '/activity', '/settings']) {
    const before = requests.length;
    await page.goto(origin + target); await listed(page);
    check(`E02: unscoped ${target} returns to the list without reading the recent AU`,
      pathname(page) === '/organizations' && coreReads(before).length === 0);
  }
  await page.goto(origin + '/gateways'); await listed(page);
  check('E02: old gateway entry explains the optional-platform boundary without loading legacy management',
    (await page.locator('main').innerText()).includes('平台网关管理由可选平台提供'));
  for (const target of [legacy.id, 'org-u125-missing']) {
    for (const route of ['/tasks?organization=' + target, '/au/' + target]) {
      const before = requests.length;
      await page.goto(origin + route);
      await page.getByRole('heading', { name: '暂时无法打开这个入口', exact: true }).waitFor();
      check(`E02: ${target === legacy.id ? 'legacy' : 'unknown'} explicit AU in ${route.startsWith('/au/') ? 'canonical' : 'old'} route is refused without falling back to any AU`,
        coreReads(before).length === 0 && await page.getByRole('link', { name: '返回组织列表', exact: true }).count() === 1);
    }
  }
  for (const target of ['/not-a-declared-page', '/api/u125-missing', '/au/invalid%252fsegment', `/au/${a.id}/work/w/results/r/extra`]) {
    const response = await context.request.get(origin + target);
    check(`E05: undeclared or encoded path ${target.replace(a.id, ':auId')} returns 404 instead of SPA HTML`,
      response.status() === 404 && !(response.headers()['content-type'] || '').includes('text/html'));
  }
  const document = await context.request.get(`${origin}/au/${a.id}/work/work.beta/results/result.beta`);
  check('E05: declared deep-link HTML retains CSP, same-origin connect policy and nosniff',
    document.status() === 200 && document.headers()['content-type'].includes('text/html') &&
    document.headers()['content-security-policy'].includes("connect-src 'self'") &&
    document.headers()['x-content-type-options'] === 'nosniff');

  stage = 'read-fault-injection';
  await gotoAU(page, a, 'governance', '治理与成员');
  const adopt = page.getByRole('button', { name: '采用本地治理', exact: true });
  await until(() => adopt.isEnabled(), 'Prepared governance action was not available before the network fault');
  const beforeOfflineCommands = commands().length;
  await context.setOffline(true);
  await page.getByText(/当前连接不可用，以下是/).waitFor();
  check('E04: same-AU browser offline retains an explicitly stale authorized snapshot and disables new decisions',
    await page.getByText(fixtureCharter.text, { exact: true }).count() === 1 && await adopt.isDisabled() &&
    (await page.locator('main').innerText()).includes('可能已过期'));
  await refresh(page);
  await until(() => commands().length === beforeOfflineCommands, 'Offline refresh unexpectedly submitted a command');
  await context.setOffline(false);
  await until(() => adopt.isEnabled(), 'Reconnect did not restore the current verified preparation state');
  check('E04: reconnect performs reads only and does not turn the preparation plan into execution', commands().length === beforeOfflineCommands);
  const denial = route => route.fulfill({ status: 403, contentType: 'application/json',
    body: JSON.stringify({ error: 'U-125 injected AU access denial', code: 'not_authorized' }) });
  await page.route(`**/api/v1/aus/${a.id}`, denial);
  await refresh(page);
  await page.getByRole('heading', { name: '暂时无法打开这个入口', exact: true }).waitFor();
  check('E03: injected current-AU 403 clears the protected charter and its action',
    await page.getByText(fixtureCharter.text, { exact: true }).count() === 0 && await adopt.count() === 0);
  await context.setOffline(true); await refresh(page);
  check('E03: disconnect after an explicit AU denial cannot resurrect its old protected body',
    await page.getByText(fixtureCharter.text, { exact: true }).count() === 0 && await adopt.count() === 0);
  await page.unroute(`**/api/v1/aus/${a.id}`, denial);
  await context.setOffline(false);
  await gotoAU(page, b);
  const delayed = await delayRead(page, a.id);
  await page.getByRole('link', { name: '我的组织', exact: true }).click(); await listed(page);
  await page.getByRole('list', { name: '可访问的组织' }).getByRole('link').filter({ hasText: a.name }).click();
  await delayed.seen;
  await noProtectedBody(page, b, 'Switching to a pending AU retained the prior body');
  check('E03: an injected delayed AU read hides the prior organization before the new response');
  await page.getByRole('link', { name: '我的组织', exact: true }).click(); await listed(page);
  await page.getByRole('list', { name: '可访问的组织' }).getByRole('link').filter({ hasText: b.name }).click();
  await opened(page, b.id, b.name);
  delayed.release(); await delayed.clear();
  await page.waitForTimeout(250);
  check('E03: the delayed or cancelled A response cannot replace B after an explicit organization switch',
    pathname(page) === '/au/' + b.id && await page.getByText(b.goal, { exact: true }).count() === 1 &&
    await page.getByText(a.goal, { exact: true }).count() === 0);

  stage = 'independent-principals';
  const contextB = await browser.newContext({ viewport: { width: 1024, height: 1000 } });
  const pageB = await contextB.newPage(); monitor(pageB, 'participant');
  await setup(pageB, 'u125-browser-participant', true);
  const sessionB = await readSession(pageB);
  check('E03: a separately registered principal has no access to the owner prepared AUs',
    sessionB.principal_id !== sessionA.principal_id && !sessionB.organizations.some(item => [a.id, b.id].includes(item.id)));
  const c = await createFixture(pageB, 'c', 'U-125 参与者组织', '独立参与者目的，仅由当前核心身份核验。');
  const beforeCrossPrincipal = requests.length;
  await pageB.goto(origin + '/au/' + a.id);
  await pageB.getByRole('heading', { name: '暂时无法打开这个入口', exact: true }).waitFor();
  check('E03: real other-principal deep-link refusal does not fetch the owner AU or select a substitute',
    coreReads(beforeCrossPrincipal, 'participant').length === 0);
  const forbidden = await requestJSON(pageB, '/api/v1/aus/' + a.id);
  check('E03: the real HTTP service also rejects another principal directly, without protected body contents',
    forbidden.status === 403 && !JSON.stringify(forbidden.value).includes(a.goal));
  await gotoAU(pageB, c);
  await gotoAU(page, a);
  const sessionBCurrent = await readSession(pageB);
  await page.evaluate(reference => localStorage.setItem('union-recent-au-v1', JSON.stringify(reference)), {
    version: 1, service_instance: sessionBCurrent.service_instance, principal_id: sessionBCurrent.principal_id, au_id: c.id,
  });
  const beforeForeignRecent = requests.length;
  await page.goto(origin + '/'); await listed(page);
  check('E01/E03: a recent reference belonging to the other real principal cannot select or read their AU',
    pathname(page) === '/organizations' && coreReads(beforeForeignRecent, 'owner').length === 0);
  await gotoAU(page, a);
  const principalDelay = await delayRead(page, a.id);
  await refresh(page); await principalDelay.seen;
  const swapped = route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sessionBCurrent) });
  await page.route('**/api/session', swapped);
  await refresh(page);
  await noProtectedBody(page, a, 'Injected principal change retained owner data');
  await page.getByRole('heading', { name: '暂时无法打开这个入口', exact: true }).waitFor();
  check('E03: injected session principal change clears the previously protected organization in the open tab',
    await page.locator('.organization-current').textContent() === '组织空间');
  principalDelay.release(); await principalDelay.clear();
  await page.waitForTimeout(250);
  check('E03: a late authorized response from the old principal cannot restore their body after session change',
    await page.getByText(a.goal, { exact: true }).count() === 0 && await page.locator('.organization-purpose').count() === 0);
  await page.unroute('**/api/session', swapped);
  await gotoAU(page, a);
  const current = await readSession(page);
  const removed = route => route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ ...current, organizations: current.organizations.filter(item => item.id !== a.id) }) });
  await page.route('**/api/session', removed);
  const beforeRemoval = requests.length;
  await refresh(page);
  await page.getByRole('heading', { name: '暂时无法打开这个入口', exact: true }).waitFor();
  await noProtectedBody(page, a, 'Injected catalog removal retained the body');
  check('E03: injected directory removal invalidates the current body without reading a substitute', coreReads(beforeRemoval).length === 0);
  await page.unroute('**/api/session', removed);
  await gotoAU(page, a);
  const serviceChanged = route => route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ ...current, service_instance: 'u125-injected-service-instance' }) });
  await page.route('**/api/session', serviceChanged);
  const serviceDelay = await delayRead(page, a.id);
  await refresh(page); await serviceDelay.seen;
  await noProtectedBody(page, a, 'Injected service change retained the previous service body while re-reading');
  check('E03: injected service-instance change hides the old body until a new authorized AU read completes');
  serviceDelay.release(); await serviceDelay.clear();
  await page.unroute('**/api/session', serviceChanged);
  await gotoAU(page, a);
  const expired = route => route.fulfill({ status: 401, contentType: 'application/json',
    body: JSON.stringify({ error: 'U-125 injected session expiry', code: 'not_authorized' }) });
  await page.route('**/api/session', expired);
  await refresh(page);
  await noProtectedBody(page, a, 'Injected 401 retained protected body');
  check('E03: injected session 401 removes the protected AU and its available actions',
    await page.locator('.organization-purpose').count() === 0 && await page.locator('[data-governance]').count() === 0);
  await page.unroute('**/api/session', expired);
  await gotoAU(page, a);

  stage = 'restart-and-normal-login';
  const beforeRestartCommands = commands().length;
  const restarted = nextLine(); host.stdin.write('{"op":"restart"}\n');
  assert.equal((await restarted).restarted, true);
  await page.reload(); await opened(page, a.id, a.name);
  const restartSession = await readSession(page);
  const restartRead = await requestJSON(page, '/api/v1/aus/' + a.id);
  check('E01/E03: actual service restart retains the original stable principal, AU and preparation bytes',
    restartSession.principal_id === sessionA.principal_id && restartSession.service_instance !== sessionA.service_instance &&
    JSON.stringify(restartRead.value) === JSON.stringify(originalRead.value) && commands().length === beforeRestartCommands);
  await page.getByRole('button', { name: '账号与登录', exact: true }).click();
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  await login(page, 'u125-browser-owner');
  await opened(page, a.id, a.name);
  check('E01/E08: normal password sign-in reopens the scoped original AU without another ticket or creation',
    (await readSession(page)).principal_id === sessionA.principal_id && commands().length === beforeRestartCommands);

  stage = 'storage-fault-injection';
  const storageContext = await browser.newContext({ storageState: { cookies: await context.cookies(), origins: [] } });
  await storageContext.addInitScript(() => {
    const get = Storage.prototype.getItem, set = Storage.prototype.setItem;
    Storage.prototype.getItem = function (key) {
      if (key === 'union-recent-au-v1') throw new DOMException('Injected preference storage denial', 'SecurityError');
      return get.call(this, key);
    };
    Storage.prototype.setItem = function (key, value) {
      if (key === 'union-recent-au-v1') throw new DOMException('Injected preference storage denial', 'SecurityError');
      return set.call(this, key, value);
    };
  });
  const storagePage = await storageContext.newPage(); monitor(storagePage, 'storage-fault');
  await storagePage.goto(origin + '/'); await listed(storagePage);
  await storagePage.getByRole('list', { name: '可访问的组织' }).getByRole('link').filter({ hasText: b.name }).click();
  await opened(storagePage, b.id, b.name);
  await storagePage.reload(); await opened(storagePage, b.id, b.name);
  check('E01/E08: injected unavailable preference storage still permits the list, explicit selection and deep-link reload');
  await storageContext.close(); await contextB.close();

  stage = 'final-invariants';
  const finalSession = await readSession(page);
  check('E01-E04: exactly the original owner A/B and isolated legacy record remain, with no substitute or duplicate AU',
    finalSession.organizations.length === 3 && [legacy.id, a.id, b.id].every(id => finalSession.organizations.some(item => item.id === id)));
  check('E01-E04: only four explicitly declared fixture creates ran; navigation/recovery dispatched no command',
    commands().length === 4 && commands().every(item => item.expectedFixture) &&
    !requests.some(item => item.method !== 'GET' && item.method !== 'HEAD' && item.path.startsWith('/api/') &&
      item.path !== '/api/commands' && !item.path.startsWith('/api/auth/')));
  check('E01-E04: no V1 route reads a legacy snapshot/artifact/workspace or dispatches model/work execution',
    !requests.some(item => ['/api/snapshot', '/api/artifact', '/api/gateways', '/api/connections', '/api/model-settings'].includes(item.path)) &&
    !requests.some(item => /\/api\/v1\/(models|work)\/commands/.test(item.path)));
  check('E01-E08: browser network is same-origin and no unhandled browser or service exception occurred',
    requests.every(item => item.originMatches) && browserErrors.length === 0 && serviceErrors.length === 0);
  check('Verification served one unchanged production build throughout the browser run', documentHash() === buildHash);
  assert.equal(layoutFailures.length, 0, `${layoutFailures.length} responsive assertions failed; inspect failure.json`);
  const versions = {
    node: process.version, browser: browser.version(),
    python: spawnSync(python, ['--version'], { encoding: 'utf8', windowsHide: true }).stdout.trim(),
    head: spawnSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8', windowsHide: true }).stdout.trim(),
    assets: fs.readdirSync(path.join(root, 'web/console/dist/assets')).sort(),
  };
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({
    task: 'U-125', startedAt, finishedAt: new Date().toISOString(), controlled: true,
    realProviderCalls: 0, fixtureCreates: commands().length, versions, buildHash, checks, requests,
    injectedFaults: ['browser offline', 'AU 403', 'delayed AU read', 'session principal/service/401',
      'directory removal', 'preference storage unavailable'],
    limits: ['Prepared AU entry only; U-126 creation form and original-request uncertainty are separate.',
      'Work automatic intent remains a separate gate; missing result links reject fallback. U122 valid result reading is verified separately.',
      'No real provider, real resource grant, deployment, screen-reader or physical-device testing.'],
  }, null, 2));
  process.stdout.write(JSON.stringify({ passed: checks.length, fixtureCreates: commands().length, realProviderCalls: 0,
    evidence: path.relative(root, output).replaceAll('\\', '/') }) + '\n');
})().catch(async error => {
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, 'failure.json'), JSON.stringify({ stage, checks, layoutFailures, requests, buildHash,
    error: error.message, browserErrors, serviceErrors }, null, 2));
  // Never capture account setup/recovery screens or their one-time recovery codes.
  if (activePage && !activePage.isClosed() && await activePage.locator('.organization-main').count() &&
      !await activePage.getByRole('dialog').count()) {
    await activePage.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
  }
  process.stderr.write(JSON.stringify({ stage, passedBeforeFailure: checks.length, layoutFailures: layoutFailures.length, error: error.message,
    evidence: path.relative(root, output).replaceAll('\\', '/') }) + '\n');
  process.exitCode = 1;
}).finally(async () => {
  for (const release of pendingReleases) release();
  if (browser) await browser.close();
  if (host && host.exitCode === null) {
    host.stdin.write('{"op":"stop"}\n');
    await new Promise(resolve => {
      host.once('exit', resolve);
      setTimeout(() => { host.kill(); resolve(); }, 5000).unref();
    });
  }
  lines?.close();
});
