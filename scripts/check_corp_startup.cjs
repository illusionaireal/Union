// Read-only browser acceptance of a newly prepared, running company console.
// Does not create members, configure credentials or call models.
const { chromium } = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(process.env.UNION_CORP_ROOT || '.union/ai-union-corp');
const output = path.resolve(process.env.UNION_CORP_EVIDENCE || '.union/corp-evidence');
const checks = [], errors = [];
const check = (name, value) => { assert.ok(value, name); checks.push(name); };
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const access = JSON.parse(fs.readFileSync(path.join(root, 'local-access.json'), 'utf8'));
  const browser = await chromium.launch({ executablePath: process.env.UNION_CHROMIUM_PATH || chromium.executablePath(), headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(access.board);
    await page.getByText('已连接本机服务', { exact: true }).waitFor();
    check('Board launch exchange removes private URL fragment', !(new URL(page.url())).hash);
    const session = await page.evaluate(async () => (await fetch('/api/session')).json());
    check('Production company entry offers API only and no fixture executor', JSON.stringify(session.executors) === '["api"]');
    check('Existing company is registered in the actual Console', session.organizations.length === 1 && session.organizations[0].name === 'ai-union-corp');
    const organization = session.organizations[0].id;
    const snapshot = await page.evaluate(async id => (await fetch('/api/snapshot?organization_id=' + id)).json(), organization);
    check('Unstarted company is explicitly not_run with zero model calls', snapshot.source === 'not_run' && snapshot.budget.calls_reserved === 0 && snapshot.runs.length === 0);
    check('No scripted members or delivery are substituted', snapshot.organization.phase === 'bootstrap' && Object.keys(snapshot.organization.members).length === 0 && Object.keys(snapshot.organization.artifacts).length === 0);
    check('Company objective includes both products', snapshot.organization.goal.includes('AI-UNION') && snapshot.organization.goal.includes('ai-union-platform'));
    await page.screenshot({ path: path.join(output, 'company-overview-desktop.png'), fullPage: true });
    await page.locator('[data-nav="models"]').click();
    await page.waitForURL(url => url.pathname === '/models');
    check('Model configuration route is accessible before bootstrap', await page.getByRole('heading', { name: '模型与 API', exact: true }).isVisible());
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'company-models-mobile.png'), fullPage: true });
    check('Company mobile console has no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const observer = await browser.newContext();
    try {
      const view = await observer.newPage();
      await view.goto(access.observer);
      await view.getByText('已连接本机服务', { exact: true }).waitFor();
      const result = await view.evaluate(async () => {
        const response = await fetch('/api/commands', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        return response.status;
      });
      check('Observer cannot submit a command', result === 403);
    } finally { await observer.close(); }
    check('React renders without browser errors', errors.length === 0);
    fs.writeFileSync(path.join(output, 'browser-validation.json'), JSON.stringify({ status: 'passed', checks, errors, model_calls: 0, autonomous_operation_verified: false }, null, 2) + '\n');
    console.log(JSON.stringify({ status: 'passed', checks: checks.length, model_calls: 0 }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
