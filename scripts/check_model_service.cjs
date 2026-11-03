// Actual browser + same-origin Python; controlled account/inference service only.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path'), readline = require('node:readline'), assert = require('node:assert/strict');
const root=path.resolve(__dirname,'..'), temp=fs.mkdtempSync(path.join(os.tmpdir(),'union-model-service-browser-'));
const output=path.resolve(process.env.UNION_MODEL_SERVICE_EVIDENCE || '.union/model-service-browser');fs.mkdirSync(output,{recursive:true});
const checks=[], errors=[];let host,browser;
(async()=>{
  host=spawn(process.env.UNION_PYTHON||'python3',['-X','utf8','tests/model_service_browser_host.py','--root',temp],{cwd:root,stdio:['pipe','pipe','pipe']});
  host.stderr.on('data',data=>errors.push(String(data)));
  const lines=readline.createInterface({input:host.stdout});
  const ready=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Test host startup timed out')),20000);lines.once('line',line=>{clearTimeout(timer);resolve(JSON.parse(line));});});
  browser=await chromium.launch({executablePath:process.env.UNION_CHROMIUM_PATH||(process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':undefined),headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.board_url);
  await page.getByRole('button',{name:'设置管理员账号',exact:true}).click();
  await page.locator('[name="username"]').fill('model-service-browser');
  await page.locator('[name="password"]').fill('controlled-browser-password');
  await page.getByRole('button',{name:'建立管理员账号',exact:true}).click();
  await page.getByLabel('账号恢复码',{exact:true}).waitFor();
  await page.getByRole('button',{name:'已保存，进入工作台'}).click();
  await page.getByLabel('用于当前组织的账号').selectOption('controlled-account');
  await page.getByLabel('正式 Go 模型').selectOption('controlled-model');
  await page.getByRole('button',{name:'授权给 受控接入验收组织 并保存连接'}).click();
  await page.getByText('账号已授权给当前组织，模型连接已保存；真实运行尚待验证',{exact:true}).waitFor();checks.push('Selected account and model adopted into existing AU');
  await page.locator('[data-connection]').first().waitFor();
  assert.match(await page.locator('[data-connection]').first().innerText(),/当前组织已获账号使用授权/);checks.push('Managed connection displays AU grant instead of missing API key');
  await page.reload();await page.locator('[data-connection]').first().waitFor();checks.push('Connection and adoption receipt survive page reload');
  await page.locator('[data-connection] [data-command="api_test"]').first().click();
  await page.locator('[name="allow_unknown_cost"]').check();await page.locator('#preview-operation').click();await page.locator('#commit-operation').click();await page.locator('#operation-result').waitFor();await page.locator('#close-operation').click();
  await page.waitForFunction(async()=>{const id=document.querySelector('#org-select').value;const s=await(await fetch('/api/snapshot?organization_id='+id)).json();return s.receipts.some(r=>r.kind==='api_test'&&r.status==='succeeded');});
  checks.push('Existing bounded tool-roundtrip flow works through the adopted service connection');
  await page.locator('#refresh').click();await page.getByRole('heading',{name:'最近模型请求',exact:true}).waitFor();await page.getByText('受控模型流',{exact:true}).waitFor();checks.push('Stored model events are visible through same-origin AU-scoped API');
  await page.locator('[data-connection] [data-command="api_connection"]').first().click();
  await page.locator('[name="service_enabled"]').uncheck();await page.locator('[name="max_output_tokens"]').fill('4096');
  await page.locator('#preview-operation').click();await page.locator('#commit-operation').click();await page.locator('#operation-result').waitFor();await page.locator('#close-operation').click();
  await page.waitForFunction(async()=>{const id=document.querySelector('#org-select').value;const c=await(await fetch('/api/model-connections?organization_id='+id)).json();return c.connections[0]?.config.enabled===false&&c.connections[0]?.config.max_output_tokens===4096;});
  checks.push('AU board can disable managed connection and edit output limit without adding a model call');
  await page.setViewportSize({width:320,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks.push('Adoption and streaming view fit 320px');
  assert.deepEqual(errors,[]);checks.push('No browser or host exceptions');
  fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({simulated:true,real_model_calls:0,checks},null,2));console.log(JSON.stringify({passed:checks.length,real_model_calls:0}));
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(host){host.stdin.write('{"op":"stop"}\n');await new Promise(resolve=>{host.once('exit',resolve);setTimeout(()=>{host.kill();resolve();},5000).unref();});}
});
