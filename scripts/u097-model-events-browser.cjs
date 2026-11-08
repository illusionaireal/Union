// Actual React + authenticated HTTP/SQLite, explicit gated model double only.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const host = spawn(process.env.UNION_PYTHON || 'python3', ['scripts/u097_model_events_host.py'], {
    cwd: path.join(__dirname, '..'), windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' },
  });
  const lines = readline.createInterface({ input: host.stdout }), queue = [], waiters = [];
  lines.on('line', line => { const value = JSON.parse(line); if (waiters.length) waiters.shift()(value); else queue.push(value); });
  const next = () => queue.length ? Promise.resolve(queue.shift()) : new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('Isolated U097 fixture timed out')), 30000);
    waiters.push(value => { clearTimeout(timeout); resolve(value); });
  });
  const command = async op => { host.stdin.write(JSON.stringify({ op }) + '\n'); return next(); };
  let browser;
  const checks = [];
  try {
    let ready = await next();
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}),
    });
    const context = await browser.newContext();
    await context.addCookies([{ name: ready.cookie_name, value: ready.token, url: ready.origin, httpOnly: true, sameSite: 'Lax' }]);
    const page = await context.newPage(), posts = [], queries = [];
    page.on('request', request => {
      const url = new URL(request.url());
      if (request.method() === 'POST') posts.push(url.pathname);
      if (url.pathname === '/api/v1/models/events') queries.push(url.searchParams.get('after'));
    });
    const visit = async () => {
      await page.goto(`${ready.origin}/models?organization=${encodeURIComponent(ready.organization_id)}`);
      await page.getByRole('button', { name: '查看生成过程', exact: true }).click();
    };
    await visit();
    const region = page.getByRole('region', { name: '原调用生成观测', exact: true });
    await region.getByText('正在生成的片段一', { exact: true }).waitFor();
    await region.getByText(/原调用仍在进行/).waitFor();
    assert.equal((await command('status')).inference_posts, 1);
    assert.equal(await page.getByText('private-native-canary', { exact: true }).count(), 0);
    checks.push('partial output before completion, native body stays private');
    await command('advance');
    await region.getByText('正在生成的片段一，片段二', { exact: true }).waitFor();
    checks.push('new persisted prefix with original cursor');
    await page.route('**/api/v1/models/events?*', route => route.abort());
    await region.getByText(/生成观测已断开/).waitFor();
    assert.equal(await region.getByText('正在生成的片段一，片段二', { exact: true }).count(), 1);
    await page.unroute('**/api/v1/models/events?*');
    await region.getByRole('button', { name: '查询原生成记录', exact: true }).click();
    await page.waitForFunction(() => !document.querySelector('[aria-label="原调用生成观测"] [role="alert"]'));
    assert.ok(queries.includes('3'));
    checks.push('disconnect retains prefix; reconnect GET deduplicates original events');
    ready = await command('restart');
    await visit();
    await page.getByText('正在生成的片段一，片段二', { exact: true }).waitFor();
    assert.equal(ready.inference_posts, 1);
    checks.push('normal host reopen reads original persisted attempt with no dispatch');
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}px`);
    }
    checks.push('1440/390/320 layout');
    await command('revoke');
    await page.getByRole('button', { name: '查询原生成记录', exact: true }).click();
    await page.getByText(/生成内容已清除/).waitFor();
    assert.equal(await page.getByText('正在生成的片段一，片段二', { exact: true }).count(), 0);
    assert.equal((await command('status')).inference_posts, 1);
    assert.equal(posts.length, 0);
    checks.push('current grant revocation clears output; browser writes and additional model posts are zero');
    const output = path.resolve(process.env.UNION_U097_EVIDENCE || '.union/u097-model-events-browser');
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ scope: 'controlled', checks,
      inference_posts_fixture_setup: 1, inference_posts_from_observation: 0, browser_posts: posts.length,
      real_model_calls: 0 }, null, 2));
    console.log(`U097 browser: ${checks.length} controlled checks passed; real model calls: 0`);
  } finally {
    if (browser) await browser.close();
    host.stdin.end(JSON.stringify({ op: 'stop' }) + '\n');
    await new Promise(resolve => { if (host.exitCode !== null) resolve(); else host.once('exit', resolve); });
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
