// Real Chrome -> Core HTTP -> SQLite; observations issue no POSTs.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const { createRequire } = require('node:module');
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
    const driverPath = path.resolve(__dirname, '../../../scripts/exit22b_page.cjs');
    // Optional exact historical source, extracted only; never run driver main.
    const source = fs.readFileSync(process.argv[2] || driverPath, 'utf8');
    const gateStart = source.indexOf('  // Original-output acceptance gate.');
    const gateEnd = source.indexOf("  check('in-flight automatic reservation carries the line-end id: ");
    const cancelStart = source.indexOf('  // Same-run original GET must return');
    const cancelEnd = source.indexOf('  // on the race with the real model', cancelStart);
    assert.ok(gateStart >= 0 && gateEnd > gateStart && cancelStart > gateEnd && cancelEnd > cancelStart);
    const saved = new Map();
    const composed = await vm.runInNewContext('(async () => {' + source.slice(gateStart, gateEnd)
      + source.slice(cancelStart, cancelEnd)
      + '\nreturn { original: originalCancelReference, before: cancelEvidenceBefore, observed: outputObservation }; })()', {
      page, TextEncoder, crypto: { createHash }, require: createRequire(driverPath),
      createdReceipt: { organization_id: host.reference.organization_id }, workId: host.reference.work_id,
      inflight: structuredClone(host.reference), cancelCommandId: host.reference.cancel_id,
      cancelOutcome: { receipt: structuredClone(host.receipt) },
      output: '/synthetic', path, fs: { writeFileSync: (name, value) => saved.set(path.basename(name), JSON.parse(value)) },
      coreWork: () => page.evaluate(async id => (await fetch('/api/v1/work?organization_id=' + encodeURIComponent(id))).json(), host.reference.organization_id),
      check: (name, value = true) => assert.ok(value, name),
      waitFor: async predicate => { assert.equal(await predicate(), true, 'seeded original output available'); },
    });
    const { original, before, observed } = composed;
    assert.equal(original.principal_id, observed.principal_id);
    assert.equal(observed.principal_id, host.reference.principal_id);
    assert.equal(observed.service_instance, before.service_instance);
    assert.equal(saved.get('original-output-observation.json').text_bytes, Buffer.byteLength('Controlled original output'));
    assert.ok(!JSON.stringify(observed).includes('Controlled original output'));
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
    console.log('PASS: actual output gate passes its observed reader to original cancel GET before/after SQLite restart; changed service; wrong Work/attempt/principal, HTTP403 and substituted receipt refused. Observation POSTs=0, fake inference=1, fake cancel=1, real=0.');
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
