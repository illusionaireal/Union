// Read actual persisted real-provider evidence through the production React UI.
// Start acceptance.py serve first. This probe sends no model/work commands.
const { chromium } = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const state = path.resolve(process.env.UNION_RESPONSES_ACCEPTANCE_STATE);
const meta = JSON.parse(fs.readFileSync(path.join(state, 'acceptance-private.json'), 'utf8'));
const checks = [], posts = [], errors = [];
const check = (label, value) => { assert.ok(value, label); checks.push(label); };
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
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
    const interrupted = page.locator('.model-checks > li').filter({ has: page.getByRole('heading', { name: 'interrupt-synthetic.txt', exact: true }) });
    await normal.locator('blockquote').waitFor();
    check('Real selected-model reply is rendered byte-for-byte after restart',
      sha(await normal.locator('blockquote').innerText()) === meta.normal_verified.output_sha256);
    check('Both original checks remain visible', await normal.count() === 1 && await interrupted.count() === 1);
    check('Actual selected model is named', (await page.locator('body').innerText()).includes('GPT-6 Luna'));
    const normalText = await normal.innerText();
    check('Normal request usage comes from the real provider', meta.normal_check.attempts.every(
      attempt => normalText.includes(`${attempt.usage.input_tokens} / ${attempt.usage.output_tokens}`)));
    check('Interrupted outcome remains explicitly unknown', (await interrupted.innerText()).includes('待核对'));
    check('Unknown interrupted usage is not shown as zero', (await interrupted.innerText()).includes('未知 / 未知'));
    check('Costs remain unknown', (await normal.innerText()).includes('未知') && (await interrupted.innerText()).includes('未知'));
    await page.getByLabel('查看哪次原调用', { exact: true }).selectOption(meta.normal_check.id + ':' + meta.normal_check.attempt_ids[1]);
    await page.getByRole('button', { name: '查看生成过程', exact: true }).click();
    const observation = page.getByRole('region', { name: '原调用生成观测', exact: true });
    await observation.locator('pre').waitFor();
    check('Normal saved stream reconstructs the original response', sha(await observation.locator('pre').innerText()) === meta.normal_verified.output_sha256);
    await page.getByLabel('查看哪次原调用', { exact: true }).selectOption(meta.before_cancel.check_id + ':' + meta.before_cancel.request_id);
    await observation.locator('pre').waitFor();
    await page.waitForFunction(id => document.querySelector('[aria-label="原调用生成观测"]')?.textContent.includes(id), meta.before_cancel.request_id);
    check('Cancelled original request retains the exact pre-cancel prefix',
      sha(Buffer.from(await observation.locator('pre').innerText()).subarray(0, meta.before_cancel.text_bytes)) === meta.before_cancel.text_sha256);
    await page.getByRole('button', { name: '查询原生成记录', exact: true }).click();
    await page.waitForTimeout(500);
    check('Repeat observation still names the same cancelled request', (await observation.innerText()).includes(meta.before_cancel.request_id));
    check('Repeated query preserves the original pre-cancel prefix', sha(Buffer.from(await observation.locator('pre').innerText()).subarray(0, meta.before_cancel.text_bytes)) === meta.before_cancel.text_sha256);
    check('Live-input limitation remains disclosed', (await page.locator('body').innerText()).includes('尚未实现执行期间追加输入'));
    if (process.env.UNION_RESPONSES_CAPABILITY_DECLARED === '1') {
    check('Real streaming evidence names only the selected Go model',
      (await page.locator('body').innerText()).includes('Go GPT-6 Luna 已验证真实 Responses 生成中的原文本及重启后页面读取；其他模型/服务分别验收。'));
    check('Remote cancellation and usage uncertainty remain disclosed',
      (await page.locator('body').innerText()).includes('未确认提供方已取消，中断用量/费用仍未知，占用保留。'));
    }
    await page.reload();
    await page.getByRole('heading', { name: 'normal-synthetic.txt', exact: true }).waitFor();
    check('Refresh preserves original successful reply', sha(await normal.locator('blockquote').innerText()) === meta.normal_verified.output_sha256);
    check('Refresh preserves the unknown interrupted check', (await interrupted.innerText()).includes('待核对') && (await interrupted.innerText()).includes('未知 / 未知'));
    await page.getByLabel('查看哪次原调用', { exact: true }).selectOption(meta.before_cancel.check_id + ':' + meta.before_cancel.request_id);
    await page.getByRole('button', { name: '查看生成过程', exact: true }).click();
    await observation.locator('pre').waitFor();
    check('Refresh reconstructs the original pre-cancel prefix', sha(Buffer.from(await observation.locator('pre').innerText()).subarray(0, meta.before_cancel.text_bytes)) === meta.before_cancel.text_sha256);
    check('Browser observation issues no model or business commands', posts.every(route => route === '/api/auth/login'));
    check('No browser runtime errors', errors.length === 0);
    const stamp = Date.now();
    await page.screenshot({ path: path.join(state, `u100-browser-${stamp}-private.png`), fullPage: true });
    const result = JSON.stringify({ passed: true, checks, post_routes: posts, errors }, null, 2);
    fs.writeFileSync(path.join(state, `u100-browser-${stamp}-checks.json`), result);
    fs.writeFileSync(path.join(state, 'u100-browser-latest-checks.json'), result);
    console.log(JSON.stringify({ passed: true, checks: checks.length, model_commands: 0 }));
  } catch (error) {
    const failedAt = Date.now();
    fs.writeFileSync(path.join(state, `u100-browser-failure-${failedAt}-private.json`), JSON.stringify({ checks, error: String(error), post_routes: posts, errors }, null, 2));
    await page.screenshot({ path: path.join(state, `u100-browser-failure-${failedAt}-private.png`), fullPage: true });
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
