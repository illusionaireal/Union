// Controlled integration verification, not an independent implementation review.
const { chromium } = require('playwright-core');
const { spawn, execFileSync } = require('node:child_process');
const readline = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const assert = require('node:assert/strict');

async function main() {
  const root = path.resolve(__dirname, '../../..');
  const head = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
  const host = spawn(process.env.UNION_PYTHON || 'python3', [path.join(__dirname, 'host.py')], {
    cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
  });
  let browser;
  let diagnostic = '';
  host.stderr.on('data', data => { diagnostic += data.toString(); });
  // Keep fixture diagnostics private; never forward setup cookies or host paths.
  const exited = new Promise(resolve => host.once('exit', resolve));
  try {
    const ready = await new Promise((resolve, reject) => {
      const lines = readline.createInterface({ input: host.stdout });
      const timer = setTimeout(() => reject(Error('combined fixture startup timeout')), 60000);
      lines.once('line', line => { clearTimeout(timer); resolve(JSON.parse(line)); });
      host.once('error', () => { clearTimeout(timer); reject(Error('combined fixture spawn failed')); });
      host.once('exit', code => { clearTimeout(timer); reject(Error('combined fixture failed: ' + code)); });
    });
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}),
    });
    const context = await browser.newContext();
    await context.addCookies([{ name: ready.cookie_name, value: ready.token, url: ready.origin,
      httpOnly: true, sameSite: 'Lax' }]);
    const au = await context.request.get(ready.origin + '/api/v1/aus/' + ready.organization_id);
    assert.equal(au.status(), 200);
    assert.equal((await au.json()).au.schema_version, 4);
    const page = await context.newPage();
    const writes = [];
    page.on('request', request => {
      if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands') writes.push(request);
    });
    await page.goto(ready.origin + '/tasks?organization=' + encodeURIComponent(ready.organization_id));
    const completed = page.locator('[data-work="work-http"]');
    const pending = page.locator('[data-work="work-pending"]');
    await completed.waitFor();
    await pending.waitFor();
    assert.ok((await completed.innerText()).includes('2 已用 · 0 已预约'));
    assert.ok((await pending.innerText()).includes('0 已用 · 1 已预约'));
    const href = await completed.getByRole('link', { name: '下载', exact: true }).getAttribute('href');
    const result = await context.request.get(ready.origin + href);
    assert.equal(result.status(), 200);
    const document = await result.json();
    assert.equal(document.content, ready.expected_result);
    assert.equal(document.organization_id, ready.organization_id);
    assert.equal(document.result.bytes, Buffer.byteLength(ready.expected_result));
    assert.equal(document.result.sha256, createHash('sha256').update(ready.expected_result).digest('hex'));
    await page.getByRole('button', { name: '刷新 AI 工作', exact: true }).click();
    await completed.waitFor();
    await page.reload();
    await completed.waitFor();
    await pending.waitFor();
    assert.ok((await pending.innerText()).includes('0 已用 · 1 已预约'));
    assert.equal(await page.getByRole('button', { name: '预约一次调用', exact: true }).count(), 0);
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    await context.clearCookies();
    assert.equal((await context.request.get(ready.origin + href)).status(), 401);
    assert.equal(writes.length, 0);
    host.stdin.end('\n');
    assert.equal(await exited, 0, 'fixture final no-redispatch assertion');
    const output = path.join(root, '.union/s03-combined-20261108');
    fs.mkdirSync(output, { recursive: true });
    const checks = ['schema 4 survives normal Console restart',
      'document body delivered to the subsequent loopback model turn',
      'stored document digest and exact result bytes agree',
      'three distinct original model request IDs across two Works',
      'reopened unknown request retains its original reservation without redispatch',
      'completed and pending Work budgets visible together in the core route',
      'refresh/reload preserve both Works', 'read-only controls and zero Work POSTs',
      '1440/390/320 widths', 'expired session cannot download result'];
    fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify({
      source_head: head, scope: 'controlled', actor: 'codex-home', independent_review: false,
      checks, loopback_model_posts: ready.model_posts, real_model_calls: 0,
    }, null, 2) + '\n');
    console.log('Combined S03 integration: ' + checks.length + ' checks passed; real model calls: 0');
  } finally {
    if (browser) await browser.close();
    if (host.exitCode === null) host.stdin.end('\n');
    await exited;
    if (diagnostic) {
      const output = path.join(root, '.union/s03-combined-20261108');
      fs.mkdirSync(output, { recursive: true });
      fs.writeFileSync(path.join(output, 'fixture-private.log'), diagnostic);
    }
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
