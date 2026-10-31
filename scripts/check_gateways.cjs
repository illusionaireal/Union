// Real browser + local HTTP doubles only; no real New API or supplier credentials.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'union-gateway-'));
const output = path.resolve(process.env.UNION_GATEWAY_EVIDENCE || '.union/gateway-browser-evidence');
const checks = [];
let host, browser;
function check(name, value) { assert.ok(value, name); checks.push(name); }
(async () => {
  fs.mkdirSync(output, { recursive: true });
  host = spawn(process.env.UNION_PYTHON || 'python3', ['tests/gateway_browser_host.py', '--root', temp], { cwd: root, stdio: ['pipe','pipe','pipe'] });
  const ready = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Local host did not start')), 15000);
    host.once('error', reject);
    readline.createInterface({ input: host.stdout }).once('line', line => { clearTimeout(timer); resolve(JSON.parse(line)); });
  });
  browser = await chromium.launch({ ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}), headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto(ready.admin_url); await page.getByText('已连接本机服务', { exact: true }).waitFor();
  await page.locator('[data-nav="gateways"]').click();
  await page.getByLabel('网关名称', { exact: true }).fill('New API · 本地替身');
  await page.getByLabel('服务根地址（用于健康检测）', { exact: true }).fill(ready.provider_url);
  await page.getByLabel('API 根地址（通常以 /v1 结尾）', { exact: true }).fill(ready.provider_url + '/v1');
  await page.getByLabel('管理后台地址', { exact: true }).fill(ready.provider_url);
  await page.getByRole('button', { name: '保存登记', exact: true }).click();
  await page.getByRole('heading', { name: 'New API · 本地替身', exact: true }).waitFor();
  check('registration does not run a health probe', await page.getByText('尚未检测', { exact: true }).count() > 0);
  await page.getByRole('button', { name: '检测健康', exact: true }).click();
  await page.getByText('local-double-v1', { exact: true }).waitFor();
  check('health keeps deployment unknown', await page.getByText('未知（尚无部署控制器）', { exact: true }).isVisible());
  check('unsupported update and stop controls are absent', !(await page.getByRole('button', { name: /^(更新|停止|重启)$/ }).count()));
  await page.screenshot({ path: path.join(output, 'gateways-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: '编辑', exact: true }).click();
  await page.getByLabel('网关名称', { exact: true }).fill('New API · 已编辑');
  await page.getByRole('button', { name: '保存登记', exact: true }).click();
  await page.getByRole('heading', { name: 'New API · 已编辑', exact: true }).waitFor();
  await page.locator('[data-nav="models"]').click();
  await page.getByRole('button', { name: '使用 New API · 已编辑', exact: true }).click();
  check('AU receives only the public endpoint and no inherited token', await page.locator('[name="base_url"]').inputValue() === ready.provider_url + '/v1' && await page.locator('[name="api_key"]').inputValue() === '');
  await page.locator('[name="api_model"]').fill('local-tool-double');
  await page.locator('[name="api_key"]').fill('explicit-local-test-key');
  await page.locator('#preview-operation').click(); await page.locator('#commit-operation').click();
  await page.locator('#operation-result').waitFor(); await page.locator('#close-operation').click();
  await page.getByText(/网关登记来源：/).waitFor();
  await page.locator('[data-command="api_test"]').first().click();
  await page.locator('[name="allow_unknown_cost"]').check();
  await page.locator('#preview-operation').click(); await page.locator('#commit-operation').click();
  await page.locator('#operation-result').waitFor();
  const probeId = await page.locator('#operation-result [data-query-receipt]').getAttribute('data-query-receipt');
  await page.waitForFunction(async ({ oid, id }) => (await (await fetch('/api/receipts?organization_id='+oid+'&id='+id)).json()).receipt.status !== 'accepted', { oid: ready.organization_id, id: probeId });
  check('tool probe succeeds against local model double', await page.evaluate(async ({ oid, id }) => (await (await fetch('/api/receipts?organization_id='+oid+'&id='+id)).json()).receipt.status === 'succeeded', { oid: ready.organization_id, id: probeId }));
  await page.waitForFunction(async oid => (await (await fetch('/api/snapshot?organization_id='+oid)).json()).budget.calls_reserved === 2, ready.organization_id);
  await page.locator('#close-operation').click();
  check('tool roundtrip reserves two simulated calls', true);
  await page.locator('[data-nav="gateways"]').click();
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    check('mobile layout fits '+width, await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  }
  await page.screenshot({ path: path.join(output, 'gateways-mobile.png'), fullPage: true });
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '解除登记', exact: true }).click();
  await page.getByRole('heading', { name: '尚未接入网关', exact: true }).waitFor();
  await page.locator('[data-nav="models"]').click();
  check('archive preserves AU connection snapshot', await page.getByText(/网关登记来源：/).isVisible());
  const ordinary = await browser.newPage(); await ordinary.goto(ready.board_url);
  await ordinary.getByText('已连接本机服务', { exact: true }).waitFor();
  check('ordinary board cannot manage platform', !(await ordinary.locator('[data-nav="gateways"]').count()));
  check('ordinary board direct endpoint is rejected', await ordinary.evaluate(async () => (await fetch('/api/gateways')).status) === 403);
  check('no browser runtime errors', errors.length === 0);
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ simulated: true, realProviderCalls: 0, checks }, null, 2));
  console.log(JSON.stringify({ checks: checks.length, simulated: true, realProviderCalls: 0 }));
})().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (host && host.exitCode === null) {
    host.stdin.end(JSON.stringify({ op: 'stop' })+'\n');
    await new Promise(resolve => { const timer = setTimeout(() => { host.kill(); resolve(); }, 10000); host.once('exit', () => { clearTimeout(timer); resolve(); }); });
  }
  fs.rmSync(temp, { recursive: true, force: true });
});
