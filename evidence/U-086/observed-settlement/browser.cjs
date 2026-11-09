// Original settlement and rebuilt-state assertions; real Core HTTP/SQLite, fake model only.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { once } = require('node:events');
const { createRequire } = require('node:module');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../..');
const driver = path.join(root, 'scripts/exit22b_page.cjs');
const source = fs.readFileSync(driver, 'utf8');
const start = source.indexOf('  // on the race with the real model');
const end = source.indexOf('  const restartComparison =', start);
assert.ok(start >= 0 && end > start);
const fragment = source.slice(start, end);
const { readCancelEvidence } = require('../../../scripts/exit22-cancel-evidence.cjs');

async function scenario(browser, mode) {
  const child = spawn(process.env.UNION_PYTHON || 'python3',
    [path.join(__dirname, '../cancel-receipt-recovery/http-host.py')],
    { cwd: root, stdio: ['pipe', 'pipe', 'inherit'] });
  const exited = once(child, 'exit');
  const reader = createInterface({ input: child.stdout });
  const lines = reader[Symbol.asyncIterator]();
  async function next() {
    let timer;
    try {
      return await Promise.race([
        lines.next().then(value => { assert.equal(value.done, false); return JSON.parse(value.value); }),
        new Promise((_, reject) => { timer = setTimeout(() => reject(Error('host timeout')), 30000); }),
      ]);
    } finally { clearTimeout(timer); }
  }
  let context;
  try {
    let ready = await next();
    const original = ready.reference;
    context = await browser.newContext();
    const page = await context.newPage();
    const writes = [], files = new Map();
    page.on('request', r => { if (r.method() !== 'GET') writes.push(r.method()); });
    const connect = async () => context.addCookies([
      { name: ready.cookie_name, value: ready.token, url: ready.origin, httpOnly: true },
    ]);
    await connect();
    await page.goto(ready.origin + '/api/session');
    const coreWork = async () => page.evaluate(async id => {
      const r = await fetch('/api/v1/work?organization_id=' + encodeURIComponent(id));
      if (r.status !== 200) throw Error('Work HTTP ' + r.status);
      return r.json();
    }, original.organization_id);
    const actual = await coreWork();
    const actualWork = actual.works.find(w => w.id === original.work_id);
    assert.equal(actualWork.steps[0].status, 'unknown');
    assert.equal(actualWork.budget.reserved, 1);
    if (mode !== 'unknown') await page.route('**/api/v1/work?*', async route => {
      const response = await route.fetch(), body = await response.json();
      const work = body.works.find(w => w.id === original.work_id);
      work.steps.find(s => s.step_ref === original.step_ref).status = 'released';
      work.budget.reserved = mode === 'released-reserved' ? 1 : 0;
      await route.fulfill({ response, json: body });
    });
    let rebuilding;
    let error;
    try {
      await vm.runInNewContext('(async () => {' + fragment + '})()', {
        require: createRequire(driver), page, coreWork,
        // This legacy single-step fixture omits usage; snapshot helper coverage
        // uses full-loop fixtures in Node and the existing snapshot suite.
        snapshot: coreWork,
        inflight: original, workId: original.work_id,
        createdReceipt: { organization_id: original.organization_id },
        originalCancelReference: original, cancelEvidenceBefore: { receipt: ready.receipt },
        output: '/synthetic', path,
        fs: { writeFileSync: (name, value) => files.set(path.basename(name), JSON.parse(value)) },
        check: (name, value = true) => assert.ok(value, name),
        waitFor: async (predicate, name) => { assert.ok(await predicate(), name); },
        host: { kill: () => { child.stdin.write('reopen\n'); rebuilding = next(); } },
        running: { child: { once: (name, resolve) => {
          assert.equal(name, 'exit'); rebuilding.then(resolve);
        } } },
        startHost: async () => {
          ready = await rebuilding; await connect();
          return { origin: ready.origin + '/tasks?organization=' + original.organization_id, child: {} };
        },
      });
    } catch (e) { error = e; }
    if (mode === 'unknown') {
      assert.ifError(error);
      const recovered = await readCancelEvidence(page, original, ready.receipt);
      assert.equal(recovered.receipt.id, original.cancel_id);
      const reopened = (await coreWork()).works.find(w => w.id === original.work_id);
      assert.deepEqual(reopened.steps, actualWork.steps, 'SQLite restart preserves the original call');
      assert.deepEqual(reopened.budget, actualWork.budget, 'SQLite restart preserves the reservation');
    } else {
      assert.ok(error, 'released observed call must not pass acceptance');
      assert.match(String(error), /step settled as released/);
      assert.equal(files.has('snapshot-before-restart.json'), false);
    }
    assert.deepEqual(writes, [], 'settlement/rebuild evidence never dispatches or cancels');
    return { mode, passed: true, fake_model_calls: 1, fake_cancel_calls: 1, core_writes: 0, real_model_calls: 0 };
  } finally {
    if (context) await context.close();
    child.stdin.end('stop\n');
    const [code] = await exited;
    reader.close();
    assert.equal(code, 0, 'fixture verified original call counts and cleaned up');
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}) });
  const results = [];
  try {
    for (const mode of ['unknown', 'released', 'released-reserved']) {
      try { results.push(await scenario(browser, mode)); }
      catch (e) { results.push({ mode, passed: false, error: String(e) }); }
    }
  } finally { await browser.close(); }
  console.log(JSON.stringify({ scope: 'controlled settlement, not real output acceptance', results }, null, 2));
  if (results.some(r => !r.passed)) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
