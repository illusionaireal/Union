const { chromium } = require('playwright-core');
const { spawn, execFileSync } = require('node:child_process');
const readline = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const repoRoot = path.resolve(__dirname, '../..');
  const sourceHead = execFileSync('git', ['rev-parse', 'HEAD'], {cwd:repoRoot,encoding:'utf8'}).trim();
  const output = path.join(repoRoot, '.union/u081-independent-review');
  const host = spawn(process.env.UNION_PYTHON, ['scripts/u081_work_read_host.py'], {
    cwd: repoRoot, stdio: ['pipe', 'pipe', 'pipe'],
  });
  let browser;
  try {
    const ready = await new Promise((resolve, reject) => {
      const lines = readline.createInterface({ input: host.stdout });
      const timer = setTimeout(() => reject(Error('fixture startup timeout')), 30000);
      lines.once('line', line => { clearTimeout(timer); resolve(JSON.parse(line)); });
      host.once('error', error => { clearTimeout(timer); reject(error); });
      host.once('exit', code => { clearTimeout(timer); reject(Error('fixture exited: ' + code)); });
    });
    browser = await chromium.launch({headless:true, executablePath:process.env.UNION_CHROMIUM_PATH});
    const context = await browser.newContext();
    await context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true,sameSite:'Lax'}]);
    const page = await context.newPage();
    const writes = [];
    page.on('request', r => { if (r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/work/commands') writes.push(r.method()); });
    const url = ready.origin + '/tasks?organization=' + encodeURIComponent(ready.organization_id);
    const endpoint = '**/api/v1/work?*';
    const list = page.getByRole('list', {name:'V1 工作列表',exact:true});
    await page.goto(url);
    await list.waitFor();
    const href = await list.getByRole('link', {name:'下载',exact:true}).getAttribute('href');
    const download = await context.request.get(ready.origin + href);
    assert.equal(download.status(), 200);
    const document = await download.json();
    assert.ok(document.content, 'download must contain stored content');
    const checks = ['authenticated download contains stored result body'];
    for (const [field, change] of [
      ['principal', data => data.access.principal_id = 'different-principal'],
      ['organization', data => data.organization_id = 'different-au'],
      ['protocol', data => data.protocol = 'unknown.protocol'],
    ]) {
      let hits = 0;
      await page.route(endpoint, async route => {
        hits++;
        const original = await route.fetch();
        const data = await original.json();
        change(data);
        await route.fulfill({response:original,json:data});
      });
      await page.reload();
      try {
        await page.getByText('工作读取与当前身份或组织不匹配，请刷新后重试。').waitFor({timeout:10000});
      } catch (error) {
        console.log(JSON.stringify({field,hits,listCount:await list.count()}));
        throw error;
      }
      assert.equal(await list.count(), 0);
      assert.equal(await page.locator('a[href*="/api/v1/work/results"]').count(), 0);
      checks.push(field + ' mismatch hides records and downloads');
      await page.unroute(endpoint);
    }
    await page.reload();
    await list.waitFor();
    await page.route(endpoint, route => route.fulfill({status:403,json:{error:'permission_denied',message:'review denial'}}));
    await page.getByRole('button', {name:'刷新 AI 工作',exact:true}).click();
    await page.getByText('读取失败，可刷新重试。').waitFor();
    assert.equal(await list.count(), 0);
    checks.push('403 refresh removes previously rendered work');
    await context.clearCookies();
    const denied = await context.request.get(ready.origin + href);
    assert.equal(denied.status(), 401);
    checks.push('download endpoint rejects an expired session');
    assert.equal(writes.length, 0);
    checks.push('all review navigation remains free of work writes');
    fs.mkdirSync(output, {recursive:true});
    fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({
      source_head:sourceHead, reviewer:'codex-home', implementer:'chatGPT-online',
      scope:'controlled', checks, real_model_calls:0,
    }, null, 2));
    console.log('Independent U081 review: ' + checks.length + ' browser checks passed; real model calls: 0');
  } finally {
    if (browser) await browser.close();
    host.stdin.end('\n');
    await new Promise(resolve => host.exitCode !== null ? resolve() : host.once('exit', resolve));
  }
}
main().catch(error => {console.error(error.message);process.exitCode=1;});
