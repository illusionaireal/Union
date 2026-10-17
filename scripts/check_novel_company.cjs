// Full browser -> Python -> local HTTP provider -> three company cycles; all model outputs simulated.
const { chromium } = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const root = path.resolve(__dirname, '..');
const output = path.resolve(process.env.UNION_NOVEL_EVIDENCE || path.join(root, '.union/novel-browser-evidence'));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'union-novel-browser-'));
const checks = [], errors = [];
let host, browser;
const check = (label, condition = true) => { assert.ok(condition, label); checks.push(label); };
async function close(page) { if (await page.locator('#operation-dialog').isVisible()) await page.locator('#close-operation').click(); }
async function refresh(page) { await page.locator('#refresh').click(); await page.waitForTimeout(250); }
async function command(page, kind, fill = async () => {}) {
  await close(page);
  await page.locator(`[data-command="${kind}"]`).first().click();
  await fill(page.locator('#operation-form'));
  await page.locator('#preview-operation').click();
  await page.locator('#commit-operation').click();
  await page.locator('#operation-result').waitFor();
}
(async () => {
  fs.mkdirSync(output, { recursive: true });
  host = spawn(process.env.UNION_PYTHON || 'python3', ['-X', 'utf8', 'tests/novel_browser_host.py', '--root', temp], { cwd: root, stdio: ['pipe', 'pipe', 'pipe'] });
  host.stderr.on('data', data => errors.push(String(data)));
  const ready = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Host startup timeout')), 15000);
    readline.createInterface({ input: host.stdout }).once('line', line => { clearTimeout(timer); resolve(JSON.parse(line)); });
  });
  browser = await chromium.launch({ executablePath: process.env.UNION_CHROMIUM_PATH || chromium.executablePath(), headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(ready.board_url);
  await page.getByText('已连接本机服务', { exact: true }).waitFor();
  await command(page, 'create', async form => {
    await form.locator('[name="company_template"]').selectOption('novel');
    await form.locator('[name="name"]').fill('小说公司 · HTTP 模拟验收');
    check('Novel template provides target, charter, budget and finite resources', (await form.locator('[name="goal"]').inputValue()).includes('连续交付三章') && await form.locator('[name="max_calls"]').inputValue() === '32');
  });
  await close(page);
  await page.locator('.company-panel').waitFor();
  await page.locator('[data-nav="models"]').click();
  await page.getByRole('heading', { name: '模型与 API', exact: true }).waitFor();
  check('Settings has configuration actions without repeated create/run buttons', await page.locator('[data-command="create"], [data-command="start"]').count() === 0);
  const secret = 'browser-test-key-not-real';
  await page.locator('[data-command="api_connection"]').first().click();
  await page.locator('[name="connection_id"]').fill('primary');
  await page.locator('[name="base_url"]').fill(ready.provider_url);
  await page.locator('[name="api_model"]').fill('local-test-model');
  await page.locator('[name="api_key"]').fill(secret);
  await page.locator('#preview-operation').click();
  check('API preview never displays key', !(await page.locator('#operation-preview').innerText()).includes(secret));
  await page.locator('#commit-operation').click(); await page.locator('#operation-result').waitFor();
  await close(page); await refresh(page);
  check('API configuration binds default connection', await page.locator('[data-connection="primary"]').isVisible());
  check('Browser storage contains no API secret', await page.evaluate(k => !JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }).includes(k), secret));
  await command(page, 'api_test', async form => { await form.locator('[name="allow_unknown_cost"]').check(); });
  await close(page);
  await page.waitForFunction(async () => {
    const org = document.querySelector('#org-select').value;
    const s = await (await fetch('/api/snapshot?organization_id=' + org)).json();
    return s.receipts.some(r => r.kind === 'api_test' && r.status === 'succeeded');
  });
  check('Connection test completes through actual HTTP adapter');
  await page.locator('[data-nav="overview"]').click(); await refresh(page);
  await command(page, 'start', async form => {
    check('Bound API is selected automatically', await form.locator('[name="executor"]').inputValue() === 'api');
    await form.locator('[name="allow_unknown_cost"]').check();
  });
  await close(page);
  await page.waitForFunction(async () => {
    const org = document.querySelector('#org-select').value;
    const s = await (await fetch('/api/snapshot?organization_id=' + org)).json();
    return s.company?.completed;
  }, null, { timeout: 20000 });
  await refresh(page);
  await page.getByText(/三个周期已完成，已停止/).waitFor();
  const snap = await page.evaluate(async () => (await fetch('/api/snapshot?organization_id=' + document.querySelector('#org-select').value)).json());
  check('One start delivers same-book three chapters and three reviews after two probe calls', snap.company.chapters.length === 3 && snap.company.reviews.length === 3 && snap.runs.length === 13);
  check('Negative feedback has a delivered follow-up task', snap.company.feedback_actions[1].delivered_work_ids.includes('chapter-3'));
  check('All HTTP double calls stay visibly simulated', snap.source === 'fixture' && snap.runs.every(r => r.simulated));
  check('Immutable mock settlement totals are correct', snap.company.totals.income_minor === 660 && snap.company.totals.operating_cost_minor === 101);
  await page.screenshot({ path: path.join(output, 'novel-company-desktop.png'), fullPage: true });
  await page.locator('.company-panel').screenshot({ path: path.join(output, 'novel-company-panel.png') });
  await page.locator('.company-chapter').nth(2).getByText('阅读已交付正文 →').click();
  await page.getByText(/SHA-256 已校验/).waitFor();
  check('Delivered chapter is readable with hash validation', (await page.locator('#detail-dialog').innerText()).includes('检票员把打孔钳抵在阿禾的手背上'));
  await page.keyboard.press('Escape');
  await page.reload(); await page.locator('.company-panel').waitFor();
  check('Reload retains company completion', await page.getByText(/三个周期已完成，已停止/).isVisible());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, 'novel-company-mobile.png'), fullPage: true });
  check('Mobile layout avoids horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.setViewportSize({ width: 320, height: 740 });
  check('320px layout avoids horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  check('No browser exceptions or host failures', errors.length === 0);
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ simulated: true, real_model_calls: 0, checks, errors }, null, 2));
  fs.writeFileSync(path.join(output, 'company.json'), JSON.stringify(snap.company, null, 2));
  console.log(JSON.stringify({ checks: checks.length, real_model_calls: 0, output }));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (host) { host.stdin.end('{"op":"stop"}\n'); await new Promise(resolve => { if (host.exitCode !== null) resolve(); else host.once('exit', resolve); }); }
  fs.rmSync(temp, { recursive: true, force: true });
});
