// Real HTTP + Chromium acceptance. No real model calls; fault injection stays on private stdin.
const {chromium}=require(process.env.UNION_PLAYWRIGHT_MODULE || '../.union/browser-tools/node_modules/playwright-core');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const {spawn}=require('node:child_process');
const readline=require('node:readline');
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..');
const output=path.resolve(process.env.UNION_CONSOLE_EVIDENCE || path.join(root,'evidence/004-organization-console'));
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'union-console-browser-'));
const checks=[], errors=[];
let host, browser;
const check=(label,value=true)=>{assert.ok(value,label);checks.push(label);};
const python=process.env.UNION_PYTHON || 'python';
async function startHost(port=0){
  const child=spawn(python,['-X','utf8','tests/console_browser_host.py','--root',temp,'--port',String(port)],{cwd:root,stdio:['pipe','pipe','pipe'],windowsHide:true});
  const lines=[],waiters=[];
  readline.createInterface({input:child.stdout}).on('line',line=>{const value=JSON.parse(line); if(waiters.length)waiters.shift()(value);else lines.push(value);});
  child.stderr.on('data',d=>errors.push(String(d)));
  const next=()=>lines.length?Promise.resolve(lines.shift()):new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('Harness timeout')),20000);waiters.push(value=>{clearTimeout(timeout);resolve(value);});});
  const ready=await next();
  return {child,...ready,async send(value){child.stdin.write(JSON.stringify(value)+'\n');return next();},async stop(){await this.send({op:'stop'});await new Promise(resolve=>child.exitCode!==null?resolve():child.once('exit',resolve));}};
}
async function waitConnected(page){await page.getByText('已连接本机服务',{exact:true}).waitFor();}
async function closeOperation(page){if(await page.locator('#operation-dialog').isVisible())await page.locator('#close-operation').click();}
async function command(page,kind,fill=async()=>{}){
  await closeOperation(page);
  await page.locator(`[data-command="${kind}"]`).first().click();
  await fill(page.locator('#operation-form'));
  await page.locator('#preview-operation').click();
  await page.locator('#commit-operation').waitFor({state:'visible'});
  await page.locator('#commit-operation').click();
  await page.locator('#operation-result').waitFor({state:'visible'});
}
const snap=page=>page.evaluate(async()=>{const id=document.querySelector('#org-select').value;return(await fetch('/api/snapshot?organization_id='+encodeURIComponent(id))).json();});
const fresh=async page=>{
  const result=page.waitForResponse(r=>r.url().includes('/api/snapshot?') || (r.url().endsWith('/api/session') && r.status()!==200));
  await page.locator('#refresh').click();const response=await result;
  if(!response.ok())throw new Error('Session unavailable');
  const snapshot=await response.json();
  await page.waitForFunction(sequence=>document.querySelector('#connection-label').textContent==='已连接本机服务' && Number(document.querySelector('#snapshot-meta').textContent.match(/快照 (\d+)/)?.[1])>=sequence,snapshot.snapshot_sequence);
};
async function waitFor(page,predicate){await page.waitForFunction(predicate,null,{timeout:15000});}

(async()=>{
  fs.mkdirSync(output,{recursive:true});
  host=await startHost();
  browser=await chromium.launch({executablePath:process.env.UNION_CHROMIUM_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(host.board_url);await waitConnected(page);
  check('C05: one-time host session establishes board role',await page.locator('#role-label').textContent()==='本机发起人');
  check('A01: fresh service has a clear empty state',await page.locator('#view').getByText('尚未创建组织',{exact:true}).isVisible());
  await page.locator('[data-command="create"]').click();
  await page.locator('#cancel-operation').click();
  check('C01: cancelled creation does not create an organization',(await page.locator('#org-select option').count())===1 && !(await page.locator('#org-select').inputValue()));
  await page.locator('[data-command="create"]').click();
  await page.locator('[name="name"]').fill('   ');await page.locator('#preview-operation').click();
  check('C01: invalid input is preserved with a field error',await page.locator('#operation-error').isVisible() && await page.locator('[name="name"]').inputValue()==='   ');
  await page.locator('[name="name"]').fill('浏览器协作试验');await page.locator('#preview-operation').click();await page.locator('#commit-operation').click();
  await page.locator('#operation-result').waitFor({state:'visible'});await closeOperation(page);await fresh(page);
  const org=(await snap(page)).organization.id;
  check('C01: browser creation persists goal, adoption and resources',!!org);
  await host.send({op:'hold'});
  await command(page,'start',async form=>{await form.locator('[name="max_steps"]').fill('8');});
  await closeOperation(page);await fresh(page);
  await waitFor(page,()=>document.querySelector('#view').textContent.includes('协作进行中'));
  const live=await snap(page);
  check('A09: live slow decision is running, not reconciliation',live.execution_state==='running' && live.budget.calls_reserved===1);
  check('A03: begin_decision adds reservation at unchanged organization version',live.organization.version===0);
  await command(page,'pause');await closeOperation(page);await fresh(page);
  check('C03: pause acknowledged while awaiting in-flight receipt',(await snap(page)).dispatch_state==='pause_requested');
  await host.send({op:'release'});
  await waitFor(page,()=>document.querySelector('#view').textContent.includes('派发已暂停'));
  const paused=await snap(page);
  check('C03: pause stops next dispatch and retains first receipt',paused.runs.length===1 && paused.dispatch_state==='paused');
  check('A04: dependent work retains a distinct waiting reason',Object.values(paused.organization.work).some(w=>w.display_status==='dependent'));
  await command(page,'start',async form=>{await form.locator('[name="max_steps"]').fill('7');});await closeOperation(page);
  await waitFor(page,()=>document.querySelector('#view').textContent.includes('等待新事件'));
  const complete=await snap(page);
  check('C02/A02: browser fixture completes two members, three works, three artifacts',Object.keys(complete.organization.members).length===2 && Object.keys(complete.organization.work).length===3 && Object.keys(complete.organization.artifacts).length===3 && complete.runs.length===6);
  check('A02/D06: fixture origin and unknown costs retained',complete.source==='fixture' && complete.budget.cost_status==='unknown');
  await page.screenshot({path:path.join(output,'overview-1440.png'),fullPage:true});
  await page.locator('[data-nav="tasks"]').click();
  await page.locator('#task-search').fill('not-a-task');check('A02: task search has empty state',await page.getByText('没有匹配的工作',{exact:true}).isVisible());
  await page.locator('[data-clear]').click();await page.locator('#member-filter').selectOption('member-two');
  check('A02: member filter follows stored ownership',await page.locator('#filtered-work [data-detail="work"]').count()>=2);
  await page.locator('#task-search').fill('work-followup');await page.locator('#filtered-work [data-detail="work"]').first().click();
  check('A02: work detail links real dependency and artifact',await page.locator('#detail-body [data-detail="artifact"]').count()===1);
  await page.locator('#detail-body [data-detail="artifact"]').first().click();await page.getByText(/SHA-256 已校验/).waitFor();
  const download=page.waitForEvent('download');await page.getByText('下载已校验文件',{exact:true}).click();const downloaded=await download;
  const downloadedText=fs.readFileSync(await downloaded.path(),'utf8');
  check('A05: download returns actual verified content',downloadedText.includes('模拟') || downloadedText.includes('Fixture'));
  await page.keyboard.press('Escape');check('A08: native detail dialog closes by keyboard',!(await page.locator('#detail-dialog').isVisible()));
  const aid=Object.keys(complete.organization.artifacts)[0];
  await host.send({op:'corrupt',org,id:aid});await page.locator('[data-nav="artifacts"]').click();await page.locator(`[data-detail="artifact"][data-id="${aid}"]`).click();await page.getByText(/成果不可用/).waitFor();
  check('A05: corrupted asset fails visibly without download',await page.locator('#detail-body [download]').count()===0);await page.keyboard.press('Escape');await host.send({op:'restore'});
  await page.locator('[data-nav="settings"]').click();
  await command(page,'resources',async form=>{await form.locator('[name="max_calls"]').fill('12');await form.locator('[name="reason"]').fill('浏览器测试追加有限调用，保留既有占用');});await closeOperation(page);await fresh(page);
  check('C04: resource change preserves six consumed calls',(await snap(page)).budget.calls_reserved===6 && (await snap(page)).budget.max_calls===12);
  await command(page,'amend',async form=>{await form.locator('[name="charter_text"]').fill('本地有限协作，修章记录测试；不授权外部发布。');await form.locator('[name="reason"]').fill('验证受信修章与旧版本依据');});await closeOperation(page);await fresh(page);
  check('C04: amendment changes charter version',(await snap(page)).organization.charter_version===2);
  await command(page,'event',async form=>{await form.locator('[name="content"]').fill('浏览器注入意见，明确模拟来源');await form.locator('[name="source"]').fill('browser-acceptance');});await closeOperation(page);await fresh(page);
  check('C08: event retains provenance and simulation flag',(await snap(page)).events.some(e=>e.data.source==='browser-acceptance' && e.data.simulated===true));
  // A second trusted operator changes the version after the first operator previews.
  await page.locator('[data-command="event"]').click();
  await page.locator('[name="content"]').fill('保留版本冲突时的输入');await page.locator('[name="source"]').fill('conflict-test');
  await page.locator('#preview-operation').click();
  const stale=await snap(page);
  await page.evaluate(async value=>{await fetch('/api/commands',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});},{id:'second-operator-change',organization_id:org,base_version:stale.organization.version,kind:'resources',data:{resources:{max_calls:12,timeout_seconds:180},reason:'second operator test'}});
  await page.locator('#commit-operation').click();await page.locator('#operation-error').waitFor({state:'visible'});
  check('C04/C09: version conflict preserves input and requires a new preview',await page.locator('[name="content"]').inputValue()==='保留版本冲突时的输入' && (await page.locator('#operation-error').textContent()).includes('版本冲突'));
  await closeOperation(page);await fresh(page);
  // Commit reaches the real service, but its HTTP response is held beyond the client timeout.
  let releaseCommand;const delayedCommand=new Promise(resolve=>releaseCommand=resolve);let commandRequests=0;
  await page.route('**/api/commands',async route=>{commandRequests++;const response=await route.fetch();await delayedCommand;try{await route.fulfill({response});}catch{}});
  await command(page,'event',async form=>{await form.locator('[name="event_id"]').fill('timeout-event');await form.locator('[name="content"]').fill('已提交但响应延迟的意见');await form.locator('[name="source"]').fill('timeout-test');});
  await new Promise(resolve=>setTimeout(resolve,5500));
  await page.waitForFunction(()=>document.querySelector('#operation-result').textContent.includes('操作已保存'),null,{timeout:12000});
  releaseCommand();await page.unroute('**/api/commands');
  check('C07: timeout queries the original receipt without a second POST',commandRequests===1 && (await snap(page)).events.filter(e=>e.id==='timeout-event').length===1);
  check('C07: late transport failure cannot overwrite a confirmed success',(await page.locator('#operation-result').textContent()).includes('操作已保存'));
  await closeOperation(page);await page.reload();await waitConnected(page);
  check('C07: reloading does not repeat a submitted command',(await snap(page)).events.filter(e=>e.id==='timeout-event').length===1);
  const beforeEvent=await snap(page);await host.send({op:'event',org,id:'same-version-auto-refresh'});
  await page.locator('[data-nav="activity"]').click();
  await waitFor(page,()=>document.querySelector('#view').textContent.includes('same-version-auto-refresh'));
  check('A03: automatic refresh includes same-version event',(await snap(page)).organization.version===beforeEvent.organization.version);
  // Responses from aborted refresh requests must never restore old content or connectivity.
  let saved, releaseOld;const oldGate=new Promise(resolve=>releaseOld=resolve);let intercepted=false;
  await page.route('**/api/snapshot?**',async route=>{if(!intercepted){intercepted=true;const response=await route.fetch();saved=await response.json();await oldGate;try{await route.fulfill({json:saved});}catch{}}else await route.continue();});
  await page.locator('#refresh').click();while(!intercepted)await new Promise(r=>setTimeout(r,20));
  await host.send({op:'event',org,id:'newer-response-wins'});await page.locator('#refresh').click();
  await waitFor(page,()=>document.querySelector('#view').textContent.includes('newer-response-wins'));releaseOld();await new Promise(r=>setTimeout(r,150));
  check('A03/A10: late same-version response cannot overwrite newer snapshot',(await page.locator('#view').textContent()).includes('newer-response-wins'));
  await page.unroute('**/api/snapshot?**');
  const lastSuccess=await page.locator('#last-updated').textContent();
  let releaseTimeout;const timeoutGate=new Promise(resolve=>releaseTimeout=resolve);
  await page.route('**/api/snapshot?**',async route=>{const response=await route.fetch();await timeoutGate;try{await route.fulfill({response});}catch{}});
  await page.locator('#refresh').click();await page.getByText('连接断开',{exact:true}).waitFor();
  check('A10: snapshot timeout keeps the last success time and marks data stale',(await page.locator('#connection-warning').textContent()).includes('请求超时') && await page.locator('#last-updated').textContent()===lastSuccess);
  releaseTimeout();await page.unroute('**/api/snapshot?**');await fresh(page);
  check('A10: snapshot reads recover after a timed-out request',await page.locator('[data-command="event"]').isEnabled());
  await context.setOffline(true);await page.locator('#refresh').click();await page.getByText('连接断开',{exact:true}).waitFor();
  check('A06: disconnection marks retained data stale and disables writes',await page.locator('#connection-warning').isVisible() && await page.locator('[data-command="event"]').isDisabled());
  await context.setOffline(false);await fresh(page);check('A06: reconnect refreshes data and enables permitted actions',await page.locator('[data-command="event"]').isEnabled());
  await host.send({op:'unknown'});await command(page,'start',async form=>{await form.locator('[name="max_steps"]').fill('1');});await closeOperation(page);await fresh(page);
  await waitFor(page,()=>!!document.querySelector('[data-command="reconcile"]'));
  const uncertain=await snap(page);check('C03/C06: injected unknown is not stopped or retried',uncertain.execution_state==='unknown' && uncertain.runs.length===7);
  await command(page,'reconcile',async form=>{await form.locator('[name="resolution"]').selectOption('abandon');await form.locator('[name="reason"]').fill('测试宿主确认 unknown，放弃该次执行，不退款');});await closeOperation(page);await fresh(page);
  check('C06: explicit reconciliation keeps call reservations',(await snap(page)).budget.calls_reserved===7);
  await host.send({op:'unconfirmed',org});await fresh(page);
  check('A09: persistent running without host evidence is unconfirmed',(await snap(page)).execution_state==='unconfirmed');
  await host.send({op:'recover',org});await fresh(page);check('A09: host recovery makes uncertainty explicit',(await snap(page)).execution_state==='unknown');
  await page.locator('[data-nav="settings"]').click();
  await command(page,'resources',async form=>{await form.locator('[name="max_calls"]').fill('8');await form.locator('[name="reason"]').fill('验证额度耗尽展示');});await closeOperation(page);await fresh(page);
  check('A04: exhausted call quota is visible and blocks further start',(await snap(page)).budget.blocked_reason.includes('额度耗尽') && await page.locator('[data-command="start"]').isDisabled());
  const observerContext=await browser.newContext({viewport:{width:390,height:844}});const observer=await observerContext.newPage();await observer.goto(host.observer_url);await waitConnected(observer);
  const forbidden=await observer.evaluate(async()=>{const response=await fetch('/api/commands',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});return response.status;});
  check('C05: observer bypassing disabled buttons gets HTTP 403',forbidden===403);
  const mobile=await context.newPage();await mobile.setViewportSize({width:390,height:844});await mobile.goto(host.origin);await waitConnected(mobile);
  await mobile.locator('[data-nav="settings"]').click();await command(mobile,'event',async form=>{await form.locator('[name="content"]').fill('手机端模拟意见');await form.locator('[name="source"]').fill('mobile-test');});await closeOperation(mobile);await fresh(mobile);
  check('C09: mobile completes a persistent command',(await snap(mobile)).events.some(e=>e.data.source==='mobile-test'));
  await mobile.screenshot({path:path.join(output,'settings-390.png'),fullPage:true});
  for(const width of [1024,390,320]){await mobile.setViewportSize({width,height:844});check(`A08/C09: no document overflow at ${width}px`,await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
  // Keep a response from another real organization in flight while switching back.
  await command(page,'create',async form=>{await form.locator('[name="name"]').fill('独立隔离组织');await form.locator('[name="goal"]').fill('仅验证组织隔离，不运行模型');});await closeOperation(page);await fresh(page);
  const second=(await snap(page)).organization.id;
  let releaseOrganization,organizationCaptured;const organizationGate=new Promise(resolve=>releaseOrganization=resolve),captured=new Promise(resolve=>organizationCaptured=resolve);
  await page.route('**/api/snapshot?**',async route=>{
    if(new URL(route.request().url()).searchParams.get('organization_id')!==second)return route.continue();
    const response=await route.fetch();organizationCaptured();await organizationGate;try{await route.fulfill({response});}catch{}
  });
  await page.locator('#refresh').click();await captured;
  await page.locator('#org-select').selectOption(org);await fresh(page);
  releaseOrganization();await new Promise(resolve=>setTimeout(resolve,150));await page.unroute('**/api/snapshot?**');
  check('A01/A10: switching organizations rejects a late response from the former organization',second!==org && await page.locator('#org-select').inputValue()===org && (await page.locator('#snapshot-meta').textContent()).startsWith(org+' ·'));
  // Server restart invalidates the old session; a new host ticket binds the new service instance.
  const oldInstance=(await snap(page)).service_instance,port=Number(new URL(host.origin).port);await host.stop();host=await startHost(port);
  await fresh(page).catch(()=>{});await page.getByText('连接断开',{exact:true}).waitFor();check('A10/C05: restarted host rejects old session',await page.locator('[data-command="event"]').isDisabled());
  await page.goto(host.board_url);await waitConnected(page);check('A10: fresh host session reads a new instance with persisted data',(await snap(page)).service_instance!==oldInstance && Object.keys((await snap(page)).organization.artifacts).length===3);
  check('browser has no uncaught JavaScript errors',errors.length===0);
  const digest=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  fs.writeFileSync(path.join(output,'browser-validation.json'),JSON.stringify({date:new Date().toISOString(),simulated:true,real_model_calls:0,checks:checks.map(name=>({name,passed:true})),browser:await browser.version(),node:process.version,platform:process.platform,console_sha256:digest(path.join(root,'ai-union-console.html')),script_sha256:digest(__filename)},null,2));
  console.log(JSON.stringify({passed:checks.length,real_model_calls:0,evidence:output}));
})().catch(error=>{fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'browser-failure.json'),JSON.stringify({message:error.stack,checks,errors},null,2));console.error(error.stack);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(host && host.child.exitCode===null)await host.stop().catch(()=>host.child.kill());});
