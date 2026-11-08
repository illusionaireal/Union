// Actual Core route + authenticated HTTP + SQLite; connection setup uses an explicit double.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

async function main() {
  const host = spawn(process.env.UNION_PYTHON || 'python3', [path.join(__dirname, 'u105_work_registration_host.py')],
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
  let browser;
  try {
    const ready = await readLine();
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext();
    await context.addCookies([{ name: ready.cookie_name, value: ready.token, url: ready.origin, httpOnly: true, sameSite: 'Lax' }]);
    const workUrl = ready.origin + '/api/v1/work?organization_id=' + encodeURIComponent(ready.organization_id);
    const routeUrl = ready.origin + '/tasks?organization=' + encodeURIComponent(ready.organization_id);
    const page = await context.newPage();
    let posts = 0, original, routeFailure, committed;
    async function fill(target) {
      await target.getByText('登记新的 AI 工作', { exact: true }).click();
      await target.getByLabel('工作标题', { exact: true }).fill('U105 页面目标');
      await target.getByLabel('目标', { exact: true }).fill('从实际 Core 路由登记并重开');
      await target.getByLabel('负责 AI 成员名称', { exact: true }).fill('U105 研究助手');
      await target.getByLabel('资料目录引用', { exact: true }).fill('project-docs');
      await target.getByLabel('调用上限', { exact: true }).fill('2');
    }
    await page.route('**/api/v1/work/commands', async route => {
      posts++;
      try {
        original = route.request().postDataJSON();
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        assert.equal((await response.json()).receipt.status, 'succeeded');
        await route.abort('failed'); // Actual transaction committed; lose only its response.
      } catch (error) { routeFailure = error; }
      finally { if (committed) committed(); }
    });
    await page.goto(routeUrl);
    await fill(page);
    await page.evaluate(() => {
      const originalSet = Storage.prototype.setItem;
      Storage.prototype.setItem = function (key, value) {
        if (key.startsWith('union-work-command:')) throw new Error('controlled quota failure');
        return originalSet.call(this, key, value);
      };
    });
    await page.getByRole('button', { name: '登记 AI 工作', exact: true }).click();
    await page.getByText('浏览器无法保留原请求，尚未提交', { exact: true }).waitFor();
    assert.equal(posts, 0);
    assert.equal((await (await context.request.get(workUrl)).json()).works.length, 0);

    await page.reload();
    await fill(page);
    const transaction = new Promise(resolve => { committed = resolve; });
    await page.getByRole('button', { name: '登记 AI 工作', exact: true }).click();
    await transaction;
    if (routeFailure) throw routeFailure;
    await page.reload();
    const lookup = page.getByRole('button', { name: '查询登记原请求', exact: true });
    await lookup.click();
    await page.getByText(/^登记已记录 ·/).waitFor();
    assert.equal(posts, 1);
    assert.equal(original.kind, 'start_work');
    const read = await (await context.request.get(workUrl)).json();
    assert.equal(read.works.length, 1);
    const work = read.works[0];
    assert.equal(work.id, original.data.work_id);
    assert.equal(work.responsible.member_id, original.data.member_id);
    assert.equal(work.definition.id, original.data.definition_id);
    assert.equal(work.mandate.id, original.data.mandate_id);
    assert.deepEqual(work.budget, { max_calls: 2, reserved: 0, used: 0 });
    assert.equal(work.attempts.length, 0);
    assert.equal(work.materials.available, true);
    assert.equal(await page.getByLabel('成果正文', { exact: true }).count(), 0);
    const stored = await page.evaluate(() => JSON.stringify(sessionStorage));
    assert.ok(stored.includes(original.id));
    assert.ok(!stored.includes('project-docs') && !stored.includes('U105 研究助手'));
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'overflow ' + width);
    }

    await page.getByRole('button', { name: '登记另一项工作', exact: true }).click();
    await fill(page);
    const modelsUrl = ready.origin + '/api/v1/models?organization_id=' + encodeURIComponent(ready.organization_id);
    const models = await (await context.request.get(modelsUrl)).json();
    const connection = models.connections.find(c => c.is_default);
    const disabled = await context.request.post(ready.origin + '/api/v1/models/commands', {
      headers: { Origin: ready.origin }, data: { id: randomUUID(), organization_id: ready.organization_id,
        base_version: models.version, kind: 'set_connection', data: { connection_id: connection.id,
          expected_revision: connection.revision, enabled: false, make_default: false } },
    });
    assert.equal(disabled.status(), 200);
    assert.equal((await disabled.json()).receipt.status, 'succeeded');
    await page.getByRole('button', { name: '登记 AI 工作', exact: true }).click();
    try {
      await page.getByText(/权限或身份已变化，请刷新当前权限后重开工作页。/).waitFor({ timeout: 5000 });
    } catch (error) {
      fs.mkdirSync('.union/u105-browser', { recursive: true });
      fs.writeFileSync('.union/u105-browser/controlled-failure.txt', await page.locator('body').innerText());
      throw error;
    }
    assert.equal(posts, 1);
    await page.reload();
    await page.getByRole('button', { name: '查询登记原请求', exact: true }).click();
    await page.getByText(/^登记已记录 ·/).waitFor();
    assert.equal(await page.getByRole('button', { name: '登记 AI 工作', exact: true }).count(), 0);
    host.stdin.write('check\n');
    const report = await readLine();
    assert.equal(report.model_requests, 0);
    const output = path.resolve(process.env.UNION_U105_EVIDENCE || '.union/u105-browser');
    fs.mkdirSync(output, { recursive: true });
    const checks = ['Core /tasks empty registration', 'storage failure prevents POST', 'HTTP transaction persists all responsibility bindings',
      'lost response then reload and original GET', 'no duplicate Work or automatic attempt', 'no form data in storage',
      'three viewport widths', 'fresh permission loss prevents next POST', 'readable receipt without start permission', 'zero inference requests'];
    fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ scope: 'controlled', checks,
      work_posts: posts, work_id: work.id, command_id: original.id, model_requests: report.model_requests }, null, 2));
    console.log('U105 browser: ' + checks.length + ' passed; work POST=1; model requests=0');
  } finally {
    if (browser) await browser.close();
    host.stdin.end('\n');
    if (host.exitCode === null) await new Promise(resolve => host.once('exit', resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
