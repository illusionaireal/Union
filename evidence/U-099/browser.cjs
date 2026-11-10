// Read the original Responses run through the actual React/core UI; no inference.
const { chromium } = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const root = path.resolve(process.env.UNION_RESPONSES_ACCEPTANCE_STATE);
const meta = JSON.parse(fs.readFileSync(path.join(root, 'acceptance-private.json'), 'utf8'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const checks = [], posts = [], errors = [];
const check = (label, pass) => { assert.ok(pass, label); checks.push(label); };
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.UNION_CHROMIUM_PATH, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', error => errors.push(error.name));
  page.on('request', request => { if (request.method() === 'POST') posts.push(new URL(request.url()).pathname); });
  try {
    await page.goto(meta.origin + '/models?organization=' + encodeURIComponent(meta.au_id));
    await page.locator('[name="username"]').fill(meta.username);
    await page.locator('[name="password"]').fill(meta.password);
    await page.getByRole('button', { name: '登录 UNION', exact: true }).click();
    await page.getByRole('heading', { name: '接入模型，核对实际工具能力', exact: true }).waitFor();
    const normal = page.locator('.model-checks > li').filter({ has: page.getByRole('heading', { name: 'normal-synthetic.txt', exact: true }) });
    await normal.locator('blockquote').waitFor();
    check('Original real Responses reply survives restart', sha(await normal.locator('blockquote').innerText()) === meta.normal_verified.output_sha256);
    check('Selected GPT-6 Luna connection is visible', (await normal.innerText()).includes('GPT-6 Luna'));
    check('Actual Responses profile is identified', (await page.locator('.model-connections').innerText()).includes('Responses'));
    const normalText = await normal.innerText();
    check('Actual per-request usage is visible', meta.normal_check.attempts.every(a =>
      a.usage.input_tokens !== null && a.usage.output_tokens !== null && normalText.includes(`${a.usage.input_tokens} / ${a.usage.output_tokens}`)));
    check('Unknown monetary cost remains unknown', (await normal.innerText()).includes('未知'));
    await page.getByLabel('查看哪次原调用', { exact: true }).selectOption(meta.normal_check.id + ':' + meta.normal_check.attempt_ids[1]);
    await page.getByRole('button', { name: '查看生成过程', exact: true }).click();
    const observation = page.getByRole('region', { name: '原调用生成观测', exact: true });
    await observation.locator('pre').waitFor();
    check('Original saved events reconstruct the actual answer', sha(await observation.locator('pre').innerText()) === meta.normal_verified.output_sha256);
    await page.getByRole('button', { name: '查询原生成记录', exact: true }).click();
    await page.waitForTimeout(300);
    check('Repeated event read retains the original request identity', (await observation.innerText()).includes(meta.normal_check.attempt_ids[1]));
    if (process.env.UNION_RESPONSES_CAPABILITY_DECLARED === '1') {
      check('Real claim identifies only the tested Go model', (await page.locator('body').innerText()).includes('Go GPT-6 Luna'));
      check('Live input still disclosed as unsupported', (await page.locator('body').innerText()).includes('尚未实现执行期间追加输入'));
    }
    await page.reload();
    await normal.locator('blockquote').waitFor();
    check('Refresh returns the same original answer', sha(await normal.locator('blockquote').innerText()) === meta.normal_verified.output_sha256);
    check('Browser has no model/business POST', posts.every(route => route === '/api/auth/login'));
    check('No browser runtime errors', errors.length === 0);
    const suffix = Date.now();
    await page.screenshot({ path: path.join(root, `browser-${suffix}-private.png`), fullPage: true });
    const result = { passed: true, checks, post_routes: posts, errors };
    fs.writeFileSync(path.join(root, `browser-${suffix}-checks.json`), JSON.stringify(result, null, 2));
    fs.writeFileSync(path.join(root, 'browser-latest-checks.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify({ passed: true, checks: checks.length, model_commands: 0 }));
  } catch (error) {
    const suffix = Date.now();
    fs.writeFileSync(path.join(root, `browser-failure-${suffix}-private.json`), JSON.stringify({ checks, error: String(error), posts, errors }, null, 2));
    await page.screenshot({ path: path.join(root, `browser-failure-${suffix}-private.png`), fullPage: true });
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
