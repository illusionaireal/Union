// Installation diagnosis only. No model, credentials or external endpoint.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
(async () => {
  const child = spawn('/repo/.venv/bin/python', ['tests/gateway_browser_host.py', '--root', fs.mkdtempSync(path.join(os.tmpdir(), 'union-diagnostic-'))]);
  let stderr = ''; child.stderr.on('data', d => stderr += d);
  const ready = await new Promise((resolve, reject) => {
    child.on('error', reject);
    readline.createInterface({input: child.stdout}).once('line', line => resolve(JSON.parse(line)));
  });
  let browser;
  try {
    browser = await chromium.launch({executablePath: '/usr/bin/chromium', headless: true});
    const page = await browser.newPage();
    const errors = [], responses = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('requestfailed', r => errors.push(new URL(r.url()).pathname + ': ' + r.failure()?.errorText));
    page.on('response', r => responses.push([new URL(r.url()).pathname, r.status()]));
    await page.goto(ready.admin_url);
    await page.waitForTimeout(7000);
    await page.screenshot({path: '/repo/.union/browser-diagnostic.png', fullPage:true});
    console.log(JSON.stringify({errors, responses, body: await page.locator('body').innerText(), server_stderr: stderr}));
  } finally { if(browser) await browser.close(); child.kill(); }
})().catch(e=>{console.error(e);process.exit(1)});
