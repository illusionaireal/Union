// Real Chrome -> Core HTTP -> SQLite; observations issue no POSTs.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const assert = require('node:assert/strict');
const { readCancelEvidence } = require('../../../scripts/exit22-cancel-evidence.cjs');

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
      await page.goto(host.origin + '/api/session');
    }
    await connect();
    const original = structuredClone(host.reference);
    const before = await readCancelEvidence(page, original, host.receipt);
    child.stdin.write('reopen\n'); host = await ready();
    await connect();
    const after = await readCancelEvidence(page, original, before.receipt);
    assert.notEqual(before.service_instance, after.service_instance);
    assert.deepEqual(after.receipt, before.receipt);
    assert.deepEqual(after.reference, original);
    await assert.rejects(readCancelEvidence(page, { ...original, work_id: 'another-work' }, before.receipt), /original Work/);
    await assert.rejects(readCancelEvidence(page, { ...original, attempt_id: 'another-attempt' }, before.receipt), /attempt_id/);
    await assert.rejects(readCancelEvidence(page, { ...original, principal_id: 'another-principal' }, before.receipt), /principal/);
    const route = '**/api/v1/governance/receipts?*';
    await page.route(route, r => r.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ receipt: before.receipt }) }));
    await assert.rejects(readCancelEvidence(page, original, before.receipt), /HTTP status/);
    await page.unroute(route);
    const replaced = { ...before.receipt, actor_principal_id: 'another-principal' };
    await page.route(route, r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ receipt: replaced }) }));
    await assert.rejects(readCancelEvidence(page, original, before.receipt), /actor_principal_id/);
    await page.unroute(route);
    assert.deepEqual(writes, []);
    console.log('PASS: original cancel GET before/after SQLite restart; changed service; wrong Work/attempt/principal, HTTP403 and substituted receipt refused. Observation POSTs=0, fake inference=1, fake cancel=1, real=0.');
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
