// Real Core HTTP/SQLite: a confirmed receipt never grants continued AU access.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const host = spawn(process.env.UNION_PYTHON || 'python3',
    [path.join(__dirname, 'u105_work_registration_host.py'), '--late-access'],
    { cwd: path.join(__dirname, '..'), stdio: ['pipe', 'pipe', 'inherit'] });
  const lines = createInterface({ input: host.stdout })[Symbol.asyncIterator]();
  async function readLine() {
    let timer;
    try {
      return await Promise.race([lines.next().then(r => {
        assert.equal(r.done, false, 'fixture exited without report'); return JSON.parse(r.value);
      }), new Promise((_, reject) => { timer = setTimeout(() => reject(Error('fixture timeout')), 30000); })]);
    } finally { clearTimeout(timer); }
  }
  let browser, releasePost;
  const held = new Promise(resolve => { releasePost = resolve; });
  try {
    const ready = await readLine();
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext();
    const setToken = value => context.addCookies([{ name: ready.cookie_name, value,
      url: ready.origin, httpOnly: true, sameSite: 'Lax' }]);
    await setToken(ready.token);
    const page = await context.newPage();
    let original, posts = 0, routeFailure, committed;
    const transaction = new Promise(resolve => { committed = resolve; });
    await page.route('**/api/v1/work/commands', async route => {
      posts++;
      try {
        original = route.request().postDataJSON();
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        assert.equal((await response.json()).receipt.status, 'succeeded');
        committed();
        await held; // Commit and original GET finish before the POST response arrives.
        await route.fulfill({ response });
      } catch (error) { routeFailure = error; committed(); }
    });
    await page.goto(ready.origin + '/tasks?organization=' + encodeURIComponent(ready.organization_id));
    await page.getByText('登记新的 AI 工作', { exact: true }).click();
    await page.getByLabel('工作标题', { exact: true }).fill('U105 已确认工作');
    await page.getByLabel('目标', { exact: true }).fill('原事实保留，读取仍需当前授权');
    await page.getByLabel('资料目录引用', { exact: true }).fill('project-docs');
    await page.getByRole('button', { name: '登记 AI 工作', exact: true }).click();
    await transaction;
    if (routeFailure) throw routeFailure;
    await page.getByRole('button', { name: '查询登记原请求', exact: true }).click();
    await page.getByText(/^登记已记录 ·/).waitFor();
    await page.getByText('U105 已确认工作', { exact: true }).waitFor();
    await setToken(ready.other_token);
    const workUrl = ready.origin + '/api/v1/work?organization_id=' + encodeURIComponent(ready.organization_id);
    assert.equal((await context.request.get(workUrl)).status(), 403);
    const changedSession = await (await context.request.get(ready.origin + '/api/session')).json();
    const checkedSession = page.waitForResponse(response => new URL(response.url()).pathname === '/api/session');
    const deliveredPost = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/work/commands');
    releasePost();
    assert.equal((await deliveredPost).status(), 200);
    assert.equal((await (await checkedSession).json()).principal_id, changedSession.principal_id);
    // Either the command boundary or the workspace identity boundary may clear
    // first. DOM tests isolate the command race; this checks the whole real route.
    await page.getByText('U105 已确认工作', { exact: true }).waitFor({ state: 'hidden' });
    assert.equal(await page.getByText('U105 已确认工作', { exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: '登记另一项工作', exact: true }).count(), 0);
    assert.ok(await page.evaluate(id => JSON.stringify(sessionStorage).includes(id), original.id));
    assert.equal(posts, 1);
    await setToken(ready.token);
    const read = await (await context.request.get(workUrl)).json();
    assert.equal(read.works.length, 1);
    assert.equal(read.works[0].id, original.data.work_id);
    host.stdin.write('check\n');
    const report = await readLine();
    assert.equal(report.model_requests, 0);
    const output = path.resolve(process.env.UNION_U105_ACCESS_EVIDENCE || '.union/u105-confirmed-access');
    fs.mkdirSync(output, { recursive: true });
    const checks = ['committed POST held while original GET confirms', 'other authenticated principal denied AU read',
      'late POST acceptance clears previous work and result', 'original command identity retained',
      'original Work persists without duplicate POST', 'zero inference requests'];
    fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ scope: 'controlled', checks,
      work_posts: posts, model_requests: report.model_requests }, null, 2));
    console.log('U105 confirmed access browser: ' + checks.length + ' passed; work POST=1; model requests=0');
  } finally {
    releasePost();
    if (browser) await browser.close();
    host.stdin.end('\n');
    if (host.exitCode === null) await new Promise(resolve => host.once('exit', resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
