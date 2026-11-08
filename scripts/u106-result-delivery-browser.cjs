// Actual Core route, HTTP transactions, SQLite and existing automatic loop with an explicit fake.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { createHash } = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const host = spawn(process.env.UNION_PYTHON || 'python3', [path.join(__dirname, 'u106_result_delivery_host.py')],
    {cwd: path.join(__dirname, '..'), stdio: ['pipe', 'pipe', 'inherit']});
  const lines = createInterface({input: host.stdout})[Symbol.asyncIterator]();
  async function readLine() {
    let timer;
    try { return await Promise.race([lines.next().then(r => {
      assert.equal(r.done, false, 'fixture exited'); return JSON.parse(r.value);
    }), new Promise((_, reject) => {timer = setTimeout(() => reject(Error('fixture timeout')), 30000);})]); }
    finally {clearTimeout(timer);}
  }
  let browser;
  try {
    const ready = await readLine();
    browser = await chromium.launch({headless:true,
      ...(process.env.UNION_CHROMIUM_PATH ? {executablePath:process.env.UNION_CHROMIUM_PATH} : {})});
    const context = await browser.newContext();
    const cookie = {name:ready.cookie_name, value:ready.token, url:ready.origin, httpOnly:true, sameSite:'Lax'};
    await context.addCookies([cookie]);
    const page = await context.newPage();
    const workUrl = ready.origin + '/api/v1/work?organization_id=' + ready.organization_id;
    const routeUrl = ready.origin + '/tasks?organization=' + ready.organization_id;
    const originals = [], receipts = [];
    let posted, routeError;
    await page.route('**/api/v1/work/commands', async route => {
      try {
        const original = route.request().postDataJSON(); originals.push(original);
        const stored = await page.evaluate(() => JSON.stringify(sessionStorage));
        assert.ok(stored.includes(original.id), 'original persisted before POST');
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        const receipt = (await response.json()).receipt; receipts.push(receipt);
        assert.equal(receipt.status, 'succeeded');
        await route.abort('failed'); // Real committed operation, lost client response.
      } catch (error) {routeError = error; await route.abort().catch(() => {});}
      finally {posted?.();}
    });
    await page.goto(routeUrl);
    await page.getByRole('button', {name:'采用此成果',exact:true}).waitFor();
    const before = await (await context.request.get(workUrl)).json();
    assert.equal(before.access.can_start, false);
    assert.equal(before.access.can_manage_results, true);
    assert.equal(before.works[0].attempts[0].status, 'running');
    assert.equal(await page.getByLabel('成果正文', {exact:true}).count(), 0);
    assert.equal(await page.getByRole('button', {name:'结束执行',exact:true}).count(), 0);
    for (const [kind, action, query, message] of [
      ['adopt_result', '采用此成果', '查询采用原请求', '已采用该成果并记录采用人'],
      ['deliver_work', '交付此成果', '查询交付原请求', '已按采用的成果把该工作记为完成'],
    ]) {
      const committed = new Promise(resolve => {posted = resolve;});
      await page.getByRole('button', {name:action,exact:true}).click();
      await committed; if(routeError)throw routeError;
      assert.equal(originals.at(-1).kind, kind);
      await page.reload();
      await page.getByRole('button', {name:query,exact:true}).click();
      await page.getByText(message, {exact:true}).waitFor();
    }
    assert.equal(originals.length, 2);
    await page.getByText('工作已交付', {exact:true}).waitFor();
    await page.getByRole('button', {name:'查询采用原请求',exact:true}).click();
    await page.getByText('已采用该成果并记录采用人', {exact:true}).waitFor();
    const read = await (await context.request.get(workUrl)).json();
    assert.equal(read.works[0].status, 'delivered');
    assert.equal(read.works[0].attempts[0].status, 'closed');
    const link = page.getByRole('link', {name:'下载',exact:true});
    assert.ok((await link.getAttribute('href')).includes('work_id=' + ready.work_id));
    const download = await (await context.request.get(ready.origin + await link.getAttribute('href'))).json();
    assert.equal(download.work_id, ready.work_id);
    assert.equal(download.result.id, ready.result.id);
    assert.deepEqual(download.result.sources, ready.result.sources);
    assert.equal(createHash('sha256').update(download.content).digest('hex'), ready.result.sha256);
    const event = page.waitForEvent('download'); await link.click();
    const file = await event; const bytes = fs.readFileSync(await file.path(), 'utf8');
    assert.deepEqual(JSON.parse(bytes), download);
    for(const width of [1440,390,320]) {
      await page.setViewportSize({width,height:900});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'overflow '+width);
    }
    // Real current-principal rejection clears the formerly readable work, keeping server facts.
    await context.addCookies([{...cookie,value:ready.other_token}]);
    await page.getByRole('button',{name:'查询交付原请求',exact:true}).click();
    await page.waitForFunction(() => !document.querySelector('[data-work="work-overview"]'));
    await context.addCookies([cookie]);
    for(let i=0;i<originals.length;i++) {
      const response=await context.request.get(ready.origin+'/api/v1/governance/receipts?organization_id='+ready.organization_id+'&id='+originals[i].id);
      assert.deepEqual((await response.json()).receipt, receipts[i]);
    }
    assert.equal(originals.length, 2);
    host.stdin.write('check\n'); const report = await readLine();
    assert.deepEqual(report,{fake_model_calls:2,real_model_calls:0});
    const checks = ['actual Core route', 'disabled connection retains result authority', 'identity persisted before both POSTs',
      'adoption response lost after transaction', 'adopted state reload keeps original GET', 'original loop attempt closed on adoption',
      'delivery response lost after transaction', 'delivered state reload keeps both original GETs', 'exactly two action POSTs',
      'source/result/work/digest match', 'actual browser download matches HTTP', 'three viewport widths',
      'foreign principal clears prior content', 'original server receipts survive', 'manual body and finish controls hidden',
      'two fake turns and zero real calls'];
    const output=path.resolve(process.env.UNION_U106_EVIDENCE || '.union/u106-browser');fs.mkdirSync(output,{recursive:true});
    fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({scope:'controlled',checks,work_posts:originals.length,
      command_ids:originals.map(r=>r.id),...report},null,2));
    console.log('U106 browser: '+checks.length+' passed; action POST=2; fake=2; real=0');
  } finally {
    if(browser)await browser.close();host.stdin.end('\n');
    if(host.exitCode===null)await new Promise(resolve=>host.once('exit',resolve));
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
