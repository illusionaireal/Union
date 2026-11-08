// Actual React + HTTP + SQLite, using only an explicit loopback model double.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const host = spawn(process.env.UNION_PYTHON || 'python3', [path.join(__dirname, 'u081_work_read_host.py')], {
    cwd: path.join(__dirname, '..'), stdio: ['pipe', 'pipe', 'inherit'],
  });
  let browser;
  try {
    const ready = await new Promise((resolve, reject) => {
      const lines = readline.createInterface({ input: host.stdout });
      const timeout = setTimeout(() => reject(Error('Isolated U081 host did not become ready')), 30000);
      lines.once('line', line => { clearTimeout(timeout); resolve(JSON.parse(line)); });
      host.once('error', error => { clearTimeout(timeout); reject(error); });
      host.once('exit', code => { clearTimeout(timeout); reject(Error(`Isolated host exited (${code})`)); });
    });
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}),
    });
    const context = await browser.newContext();
    await context.addCookies([{ name: ready.cookie_name, value: ready.token, url: ready.origin,
      httpOnly: true, sameSite: 'Lax' }]);
    const page = await context.newPage();
    const writes = [];
    page.on('request', request => {
      if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands') writes.push(request);
    });
    const url = `${ready.origin}/tasks?organization=${encodeURIComponent(ready.organization_id)}`;
    await page.goto(url);
    const works = page.getByRole('list', { name: 'V1 工作列表', exact: true });
    await works.getByText('项目概览', { exact: true }).waitFor();
    assert.equal(await page.getByText('登记新的 AI 工作', { exact: true }).count(), 1);
    assert.equal(await page.getByRole('button', { name: '预约一次调用', exact: true }).count(), 0);
    assert.equal(await page.getByLabel('成果正文', { exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: '结束执行', exact: true }).count(), 0);
    const link = works.getByRole('link', { name: '下载', exact: true });
    const result = await context.request.get(new URL(await link.getAttribute('href'), ready.origin).href);
    assert.equal(result.status(), 200);
    await page.getByRole('button', { name: '刷新 AI 工作', exact: true }).click();
    await works.getByText('项目概览', { exact: true }).waitFor();
    await page.reload();
    await page.getByRole('list', { name: 'V1 工作列表', exact: true }).waitFor();
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}px`);
    }
    assert.equal(writes.length, 0);
    const output = path.resolve(process.env.UNION_U081_EVIDENCE || '.union/u081-work-read-browser');
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({
      scope: 'controlled', checks: ['core route shows persisted work', 'result download over authenticated HTTP',
        'registration available; manual bookkeeping hidden', 'refresh and reload', '1440/390/320 widths', 'zero work POSTs'],
      real_model_calls: 0,
    }, null, 2));
    console.log('U081 browser: 6 controlled checks passed; real model calls: 0');
  } finally {
    if (browser) await browser.close();
    host.stdin.end('\n');
    await new Promise(resolve => { if (host.exitCode !== null) resolve(); else host.once('exit', resolve); });
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
