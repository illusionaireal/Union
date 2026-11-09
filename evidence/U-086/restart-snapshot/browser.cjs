// Exercise the new helper over real Chrome -> HTTP -> SQLite, without driver main.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const assert = require('node:assert/strict');
const { readSnapshot, compareSnapshots } = require('../../../scripts/exit22-restart-evidence.cjs');

async function main() {
  const child = spawn(process.env.UNION_PYTHON || 'python3', [path.join(__dirname, 'http-host.py')],
    { cwd: path.resolve(__dirname, '../../..'), stdio: ['pipe', 'pipe', 'inherit'] });
  const completion = new Promise(resolve => child.once('exit', (code, signal) => resolve({ code, signal })));
  const lines = createInterface({ input: child.stdout });
  const iterator = lines[Symbol.asyncIterator]();
  async function ready() {
    let timer;
    try {
      return await Promise.race([iterator.next().then(value => {
        assert.equal(value.done, false, 'host exited before readback');
        return JSON.parse(value.value);
      }), new Promise((_, reject) => { timer = setTimeout(() => reject(Error('fixture read timeout')), 30000); })]);
    } finally { clearTimeout(timer); }
  }
  let browser;
  const writes = [];
  try {
    let host = await ready();
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('request', request => { if (request.method() !== 'GET') writes.push(request.method()); });
    async function connect() {
      await context.addCookies([{ name: host.cookie_name, value: host.token, url: host.origin, httpOnly: true }]);
      // Loading a JSON endpoint avoids any unrelated UI observers or actions.
      await page.goto(host.origin + '/api/session');
    }
    await connect();
    const before = await readSnapshot(page, host.organization_id, host.work_id);
    const oldService = await page.evaluate(async () => (await (await fetch('/api/session')).json()).service_instance);
    child.stdin.write('reopen\n'); host = await ready();
    await connect();
    const after = await readSnapshot(page, host.organization_id, host.work_id);
    const newService = await page.evaluate(async () => (await (await fetch('/api/session')).json()).service_instance);
    assert.notEqual(oldService, newService);
    const result = compareSnapshots(before, after, host.organization_id, host.work_id);
    assert.equal(result.model_request_identity_count, 2);
    assert.equal(result.transport_dispatch_count, null);
    assert.deepEqual(writes, []);
    await page.route('**/api/v1/work?*', route => route.fulfill({ status: 403,
      contentType: 'application/json', body: JSON.stringify(after) }));
    await assert.rejects(readSnapshot(page, host.organization_id, host.work_id), /HTTP status/);
    await page.unroute('**/api/v1/work?*');
    await assert.rejects(readSnapshot(page, host.organization_id, 'another-work'), /original Work/);
    console.log('Core snapshot browser: two original requests and budget survive SQLite restart; changed service accepted, HTTP403 and wrong Work rejected; GET-only; fake turns=2, real=0.');
  } finally {
    if (browser) await browser.close();
    child.stdin.end('stop\n');
    let timer;
    try {
      const done = await Promise.race([completion, new Promise(resolve => {
        timer = setTimeout(() => resolve({ timeout: true }), 15000);
      })]);
      if (done.timeout) { child.kill(); throw Error('fixture cleanup timeout'); }
      assert.equal(done.code, 0, 'fixture cleanup failed');
    } finally { clearTimeout(timer); lines.close(); }
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
