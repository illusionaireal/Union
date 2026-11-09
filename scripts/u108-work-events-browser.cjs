// Actual Core HTTP/SQLite and Chrome. Exactly one explicit loopback model request.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function finishFixture(child, completion, lines, timeout = 15000) {
  if (child.exitCode === null && !child.killed) child.stdin.end('stop\n');
  let timer;
  try {
    const outcome = await Promise.race([completion, new Promise(resolve => {
      timer = setTimeout(() => resolve({timeout: true}), timeout);
    })]);
    if (outcome.timeout) { child.kill(); throw Error('fixture shutdown timed out'); }
    assert.equal(outcome.code, 0, 'fixture shutdown failed: '+(outcome.signal || outcome.error || outcome.code));
  } finally { clearTimeout(timer); lines.close(); }
}

async function main() {
  const child = spawn(process.env.UNION_PYTHON || 'python3', [path.join(__dirname, 'u108_work_events_host.py')],
    {cwd:path.join(__dirname,'..'), stdio:['pipe','pipe','inherit']});
  const queue=[], readers=[];
  const lines=createInterface({input:child.stdout}); let exited=false;
  const completion=new Promise(resolve=>{
    child.once('close',(code,signal)=>resolve({code,signal}));
    child.once('error',error=>resolve({error}));
  });
  lines.on('line',line=>{const data=JSON.parse(line), reader=readers.shift(); if(reader)reader.resolve(data);else queue.push(data)});
  child.once('exit',code=>{exited=true;readers.splice(0).forEach(r=>r.reject(Error('fixture exited '+code)))});
  const next=()=>queue.length?Promise.resolve(queue.shift()):exited?Promise.reject(Error('fixture exited')):
    new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('fixture response timeout')),30000);
      readers.push({resolve:x=>{clearTimeout(timer);resolve(x)},reject:e=>{clearTimeout(timer);reject(e)}})});
  const control=async cmd=>{child.stdin.write(cmd+'\n');return next()};
  let browser; const checks=[];
  const dest=process.env.UNION_U108_EVIDENCE||'.union/u108-work-events-browser';
  const check=(name,condition)=>{assert.ok(condition,name);checks.push(name)};
  try {
    let ready=await next();
    browser=await chromium.launch({headless:true,...(process.env.UNION_CHROMIUM_PATH?{executablePath:process.env.UNION_CHROMIUM_PATH}:{})});
    const context=await browser.newContext();
    const cookie=()=>context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true,sameSite:'Lax'}]);
    await cookie();const page=await context.newPage();page.setDefaultTimeout(10000);
    const commands=[], reads=[];
    page.on('request',r=>{if(r.url().includes('/api/v1/work/commands'))commands.push(r.postDataJSON());
      if(r.url().includes('/api/v1/work/events'))reads.push(r.url())});
    const url=()=>ready.origin+'/tasks?organization='+encodeURIComponent(ready.organization_id);
    await page.goto(url());
    await page.getByRole('button',{name:'运行 AI 工作',exact:true}).click();
    // The POST remains in flight; observe its committed reservation from a separate GET.
    await page.getByRole('group',{name:'原运行请求',exact:true}).waitFor();
    await page.getByRole('button',{name:'刷新 AI 工作',exact:true}).click();
    await page.getByRole('button',{name:'查看工作输出',exact:true}).click();
    await page.getByText('原工作部分正文',{exact:true}).waitFor();
    const original=await control('inspect');check('one original fake model dispatch',original.fake_model_posts===1);
    const step=original.steps[0];check('partial text precedes cancellation',step.status==='reserved'&&original.cancel_posts===0);
    check('only original step is observed',reads.length>0&&reads.every(x=>new URL(x).searchParams.get('step_ref')===step.step_ref));
    check('no native or tool argument disclosure',!(await page.content()).includes('private-'));
    for (const width of [1440,390,320]) {
      await page.setViewportSize({width,height:900});
      check('expanded output fits '+width+'px',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    }
    const stored=await page.evaluate(()=>JSON.stringify(localStorage)+JSON.stringify(sessionStorage));
    check('output not stored in browser',!stored.includes('原工作部分正文'));
    await page.route('**/api/v1/work/events?**',route=>route.abort('failed'),{times:1});
    await page.getByRole('button',{name:'查询原工作输出',exact:true}).click();
    await page.getByText('观测已断开，保留最近记录；请稍后查询同一原请求。',{exact:true}).waitFor();
    check('disconnection retains original prefix',await page.getByText('原工作部分正文',{exact:true}).isVisible());
    await page.getByRole('button',{name:'查询原工作输出',exact:true}).click();
    await page.getByText('观测已断开，保留最近记录；请稍后查询同一原请求。',{exact:true}).waitFor({state:'hidden'});
    check('reconnect uses original cursor',reads.some(x=>new URL(x).searchParams.get('after')==='3'));
    await page.reload();await page.getByRole('button',{name:'查看工作输出',exact:true}).click();
    await page.getByText('原工作部分正文',{exact:true}).waitFor();
    check('reload does not repeat run command',commands.filter(c=>c.kind==='run_loop').length===1);
    const wrong=await context.request.get(ready.origin+'/api/v1/work/events?'+new URLSearchParams({
      organization_id:ready.organization_id,work_id:'other-work',step_ref:step.step_ref,after:'0'}));
    check('cross-work observation refused',wrong.status()===403);
    await control('truncate');
    await page.getByRole('button',{name:'核对原工作输出权限',exact:true}).waitFor();
    check('server truncation stops body loading explicitly',await page.getByText(/显示已截断，正文加载已停止/).isVisible());
    const cappedReads=reads.length;
    await control('revoke-read');
    await page.getByText('权限或原请求身份已变化，工作输出已清除。',{exact:true}).waitFor();
    check('truncated permission recheck uses metadata only',reads.slice(cappedReads).length>0&&
      reads.slice(cappedReads).every(x=>new URL(x).searchParams.get('authorization_only')==='1'));
    check('revocation clears the capped private text',await page.locator('.work-stream pre').count()===0);
    await page.getByRole('button',{name:'取消本次执行',exact:true}).click();
    await page.getByText('权限或原请求身份已变化，工作输出已清除。',{exact:true}).waitFor();
    let interrupted;const deadline=Date.now()+10000;
    do {interrupted=await control('inspect');if(interrupted.steps[0]?.status==='unknown')break;await new Promise(r=>setTimeout(r,50))}while(Date.now()<deadline);
    check('cancel targets only original model request',interrupted.cancel_posts===1&&interrupted.fake_model_posts===1);
    check('unknown reservation remains occupied',interrupted.steps[0].status==='unknown'&&interrupted.budget.reserved===1);
    check('original step identities preserved',Object.keys(step).filter(k=>k!=='status').every(k=>step[k]===interrupted.steps[0][k]));
    ready=await control('reopen');await cookie();await page.goto(url());
    await page.getByRole('button',{name:'查看工作输出',exact:true}).click();
    await page.getByText('权限或原请求身份已变化，工作输出已清除。',{exact:true}).waitFor();
    const reopened=await control('inspect');
    check('restart keeps original unknown request and budget',JSON.stringify(reopened.steps)===JSON.stringify(interrupted.steps)&&reopened.budget.reserved===1);
    check('restart never redispatches',reopened.fake_model_posts===1&&commands.length===2);
    fs.mkdirSync(dest,{recursive:true});
    await page.screenshot({path:path.join(dest,'restart.png'),fullPage:true});
  } finally {
    try { await browser?.close(); } finally { await finishFixture(child,completion,lines); }
  }
  fs.writeFileSync(path.join(dest,'checks.json'),JSON.stringify({passed:checks.length,checks,real_model_calls:0,fake_model_calls:1,cancel_posts:1,fixture_exit:0},null,2));
  console.log(JSON.stringify({passed:checks.length,real_model_calls:0,fake_model_calls:1,cancel_posts:1,fixture_exit:0}));
}
module.exports={finishFixture};
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1});
