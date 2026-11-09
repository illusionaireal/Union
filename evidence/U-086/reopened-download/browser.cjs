// Execute the real download driver's restart tail in Chrome against Core/SQLite.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { createRequire } = require('node:module');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { readSnapshot } = require('../../../scripts/exit22-restart-evidence.cjs');
const root = path.resolve(__dirname, '../../..');
const source = fs.readFileSync(process.env.UNION_EXIT22_DRIVER_SOURCE || path.join(root, 'scripts/exit22c_download.cjs'), 'utf8');
const start = source.indexOf('  const authenticatedAfter = await snapshot();');
const end = source.indexOf("  fs.writeFileSync(path.join(output, 'checks.json'),", start);
assert.ok(start >= 0 && end > start);
const block = source.slice(start, end);

async function main() {
  const child = spawn(process.env.UNION_PYTHON || 'python3',
    [path.join(__dirname, '../result-provenance/http-host.py')],
    {cwd:root, stdio:['pipe','pipe','inherit']});
  const completion = new Promise(resolve => child.once('exit', (code,signal) => resolve({code,signal})));
  const reader = createInterface({input:child.stdout}), lines = reader[Symbol.asyncIterator]();
  async function ready() {
    let timer;
    try { return await Promise.race([lines.next().then(v => {assert.equal(v.done,false); return JSON.parse(v.value);}),
      new Promise((_,reject) => {timer=setTimeout(() => reject(Error('fixture timeout')),30000);})]); }
    finally {clearTimeout(timer);}
  }
  let browser;
  const writes = [], results = [];
  try {
    let host = await ready();
    browser = await chromium.launch({headless:true,
      ...(process.env.UNION_CHROMIUM_PATH ? {executablePath:process.env.UNION_CHROMIUM_PATH} : {})});
    const context = await browser.newContext(), page = await context.newPage();
    page.on('request',r => {if(r.method() !== 'GET') writes.push(r.method());});
    async function connect() {
      await context.addCookies([{name:host.cookie_name,value:host.token,url:host.origin,httpOnly:true}]);
      await page.goto(host.origin + '/api/session');
    }
    await connect();
    const before = await readSnapshot(page,host.organization_id,host.work_id);
    const original = before.works.find(w => w.id===host.work_id).results[0];
    child.stdin.write('reopen\n'); host = await ready(); await connect();
    const modes = ['original', 'missing-body', 'corrupt-body', 'denied', 'wrong-work',
      'wrong-result', 'wrong-source', 'wrong-bytes', 'expired', 'principal', 'service'];
    for (const mode of modes) {
      const files = new Map(); let downloaded=false, resultGets=0;
      await page.route('**/api/v1/work/results?*', async route => {
        const url = new URL(route.request().url());
        assert.equal(url.searchParams.get('organization_id'),host.organization_id);
        assert.equal(url.searchParams.get('work_id'),host.work_id);
        assert.equal(url.searchParams.get('id'),original.id);
        resultGets++; downloaded=true;
        const response=await route.fetch(), body=await response.json();
        assert.equal(response.status(),200);
        if(mode==='missing-body') delete body.content;
        if(mode==='corrupt-body') body.content+='changed';
        if(mode==='wrong-work') body.work_id='other-work';
        if(mode==='wrong-result') body.result.id='other-result';
        if(mode==='wrong-source') body.result.sources=['other-step'];
        if(mode==='wrong-bytes') body.result.bytes=body.content.length;
        await route.fulfill({response,status:mode==='denied'?403:200,json:body});
      });
      await page.route('**/api/session',async route => {
        const response=await route.fetch(),body=await response.json();
        if(downloaded && mode==='principal') body.principal_id='other-principal';
        if(downloaded && mode==='service') body.service_instance='other-service';
        await route.fulfill({response,status:downloaded&&mode==='expired'?401:200,json:body});
      });
      try {
        let error;
        try { await vm.runInNewContext('(async () => {'+block+'})()', {
          require:createRequire(path.join(root,'scripts/exit22c_download.cjs')),page,before,
          createdReceipt:{organization_id:host.organization_id}, workId:host.work_id,
          resultId:original.id, recorded:original.sha256,
          snapshot:() => readSnapshot(page,host.organization_id,host.work_id),
          check:(name,value=true) => assert.ok(value,name),path,output:'/synthetic',
          fs:{writeFileSync:(name,body) => files.set(path.basename(name),JSON.parse(body))},
        }); } catch(e) {error=e;}
        if(mode==='original') assert.ifError(error);
        else assert.ok(error,'original driver must reject '+mode);
        if(mode==='original' && files.has('result-body-after-restart.json')) {
          const evidence=files.get('result-body-after-restart.json');
          assert.equal(evidence.sha256,original.sha256); assert.equal(evidence.bytes,original.bytes);
          assert.equal(Object.hasOwn(evidence,'content'),false);
        }
        results.push({mode,passed:true,result_gets:resultGets});
      } catch(e) {results.push({mode,passed:false,error:String(e),result_gets:resultGets});}
      finally {await page.unroute('**/api/v1/work/results?*');await page.unroute('**/api/session');}
    }
    assert.deepEqual(await readSnapshot(page,host.organization_id,host.work_id),before,
      'response faults did not change original persisted facts');
    assert.deepEqual(writes,[],'no business command or model dispatch');
  } finally {
    if(browser) await browser.close(); child.stdin.end('stop\n');
    let timer;
    try {const value=await Promise.race([completion,new Promise(resolve => {timer=setTimeout(()=>resolve({timeout:true}),15000);})]);
      if(value.timeout){child.kill();throw Error('fixture cleanup timeout');}
      assert.equal(value.code,0,'two fake calls, zero real calls, fixture shutdown');
    } finally {clearTimeout(timer);reader.close();}
  }
  console.log(JSON.stringify({scope:'controlled',fake_model_calls:2,real_model_calls:0,core_writes:writes.length,results},null,2));
  if(results.some(r=>!r.passed)) process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=1;});
