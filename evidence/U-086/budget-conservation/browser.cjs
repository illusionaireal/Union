// Real Core HTTP/SQLite snapshots; two fake model turns, zero real requests.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const assert = require('node:assert/strict');
const { readSnapshot, compareSnapshots } = require('../../../scripts/exit22-restart-evidence.cjs');

async function main() {
  const child = spawn(process.env.UNION_PYTHON || 'python3',
    [path.join(__dirname, '../restart-snapshot/http-host.py')],
    { cwd: path.resolve(__dirname, '../../..'), stdio: ['pipe', 'pipe', 'inherit'] });
  const completion = new Promise(resolve => child.once('exit', (code, signal) => resolve({ code, signal })));
  const reader = createInterface({ input: child.stdout });
  const lines = reader[Symbol.asyncIterator]();
  async function ready() {
    let timer;
    try {
      return await Promise.race([lines.next().then(value => {
        assert.equal(value.done, false, 'host must return its original state');
        return JSON.parse(value.value);
      }), new Promise((_, reject) => { timer = setTimeout(() => reject(Error('host timeout')), 30000); })]);
    } finally { clearTimeout(timer); }
  }
  let browser;
  const results = [], writes = [];
  try {
    let host = await ready();
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext(), page = await context.newPage();
    page.on('request', request => { if (request.method() !== 'GET') writes.push(request.method()); });
    async function connect() {
      await context.addCookies([{ name: host.cookie_name, value: host.token, url: host.origin, httpOnly: true }]);
      await page.goto(host.origin + '/api/session');
    }
    await connect();
    const before = await readSnapshot(page, host.organization_id, host.work_id);
    const original = before.works.find(w => w.id === host.work_id);
    assert.equal(original.steps.length, 2);
    assert.equal(original.budget.used, 2);
    assert.equal(original.budget.reserved, 0);
    child.stdin.write('reopen\n'); host = await ready();
    await connect();
    const after = await readSnapshot(page, host.organization_id, host.work_id);
    const comparison = compareSnapshots(before, after, host.organization_id, host.work_id);
    assert.equal(comparison.model_request_identity_count, 2);
    results.push({ mode: 'original-two-used-after-restart', passed: true });
    const cases = [
      ['lost-all-used', w => { w.budget.used = 0; }],
      ['lost-one-used', w => { w.budget.used = 1; }],
      ['invented-used', w => { w.budget.used = 3; }],
      ['lost-unknown-reservation', w => {
        w.steps[1].status = 'unknown'; w.steps[1].usage = null; w.budget.used = 1;
      }],
      ['invented-reservation', w => { w.budget.reserved = 1; }],
      ['occupancy-exceeds-limit', w => { w.budget.max_calls = 1; }],
    ];
    for (const [mode, change] of cases) {
      await page.route('**/api/v1/work?*', async route => {
        const response = await route.fetch(), body = await response.json();
        change(body.works.find(w => w.id === host.work_id));
        await route.fulfill({ response, json: body });
      });
      try {
        await assert.rejects(readSnapshot(page, host.organization_id, host.work_id), /budget/);
        results.push({ mode, passed: true });
      } catch (e) { results.push({ mode, passed: false, error: String(e) }); }
      finally { await page.unroute('**/api/v1/work?*'); }
    }
    assert.deepEqual(await readSnapshot(page, host.organization_id, host.work_id), after,
      'fault injection did not change any persisted request or budget');
    assert.deepEqual(writes, [], 'observation never dispatches or cancels');
  } finally {
    if (browser) await browser.close();
    child.stdin.end('stop\n');
    let timer;
    try {
      const result = await Promise.race([completion, new Promise(resolve => {
        timer = setTimeout(() => resolve({ timeout: true }), 15000);
      })]);
      if (result.timeout) { child.kill(); throw Error('fixture cleanup timeout'); }
      assert.equal(result.code, 0, 'fixture confirms two fake calls and clean shutdown');
    } finally { clearTimeout(timer); reader.close(); }
  }
  console.log(JSON.stringify({ scope: 'controlled', fake_model_calls: 2, real_model_calls: 0,
    core_writes: writes.length, results }, null, 2));
  if (results.some(r => !r.passed)) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
