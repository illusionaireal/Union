const {chromium}=require('playwright-core');
const {spawn}=require('node:child_process');
const readline=require('node:readline');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const path=require('node:path');
const P=__dirname+'/';
const REPO=path.resolve(__dirname,'../../../..');
const OUT=path.resolve(process.env.UNION_U075_REVIEW_EVIDENCE||path.join(REPO,'.union','U-075-review'));
fs.mkdirSync(OUT,{recursive:true});
async function main(){
 const host=spawn(process.env.UNION_PYTHON||'python3',[P+'browser_host.py'],{
  cwd:REPO,windowsHide:true,stdio:['pipe','pipe','pipe'],
  env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONPATH:REPO}});
 const err=fs.createWriteStream(path.join(OUT,'host.log'));host.stderr.pipe(err);
 const queue=[],waiters=[];readline.createInterface({input:host.stdout}).on('line',line=>{const v=JSON.parse(line);if(waiters.length)waiters.shift()(v);else queue.push(v);});
 const next=()=>queue.length?Promise.resolve(queue.shift()):new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(Error('Independent fixture deadline')),30000);waiters.push(v=>{clearTimeout(t);resolve(v);});});
 const command=async op=>{host.stdin.write(JSON.stringify({op})+'\n');return next();};
 let browser;const checks=[],posts=[],responses=[];
 try{
  let ready=await next();
  browser=await chromium.launch({headless:true,...(process.env.UNION_CHROMIUM_PATH?{executablePath:process.env.UNION_CHROMIUM_PATH}:{})});
  const context=await browser.newContext();
  const page=await context.newPage();
  page.on('request',r=>{if(r.method()==='POST')posts.push(new URL(r.url()).pathname);});
  page.on('response',async r=>{if(r.url().includes('/api/v1/models/events?')&&r.ok())responses.push(await r.json());});
  const visit=async()=>{await context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true,sameSite:'Lax'}]);await page.goto(ready.origin+'/models?organization='+ready.organization_id);await page.getByRole('button',{name:'查看生成过程',exact:true}).click();};
  const region=page.getByRole('region',{name:'原调用生成观测',exact:true});
  const exact=async()=>{await region.getByText('中断前的原正文',{exact:true}).waitFor();assert.equal(await region.locator('pre').innerText(),'中断前的原正文');};
  await visit();await exact();checks.push('Cancelled original text is readable through exact candidate React and HTTP');
  assert.ok(responses.some(r=>r.organization_id===ready.organization_id&&r.check_id===ready.check_id&&r.attempt_id===ready.attempt_id&&r.access.principal_id===ready.principal_id));checks.push('Observed response retains current principal and original AU/check/request');
  await page.reload();await page.getByRole('button',{name:'查看生成过程',exact:true}).click();await exact();checks.push('Browser refresh retains the same cancelled text');
  ready=await command('restart');await visit();await exact();assert.equal(ready.requests,1);assert.equal(ready.reserved,1);checks.push('Core restart preserves unknown reservation and dispatch count');
  assert.ok((await page.locator('body').innerText()).includes('已用 Go deepseek-v4.1-flash'));checks.push('Capability evidence keeps the selected-model qualifier');
  await command('revoke');await region.getByRole('button',{name:'查询原生成记录',exact:true}).click();await page.getByText(/生成内容已清除/).waitFor();assert.equal(await page.getByText('中断前的原正文',{exact:true}).count(),0);checks.push('Current grant revocation clears cancelled text');
  const final=await command('status');assert.equal(final.requests,1);assert.equal(final.reserved,1);assert.equal(posts.length,0);checks.push('Observation sends zero browser POSTs and zero additional model requests');
  const result={head:'a7c80cc649b44c439359f0b8f5ce5970dcc5ca6f',checks,passed:true,fake_model_requests:1,real_model_requests:0,browser_posts:posts.length};
  fs.writeFileSync(path.join(OUT,'checks.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({passed:true,checks:checks.length,fake_model_requests:1,real_model_requests:0,browser_posts:posts.length}));
 }finally{if(browser)await browser.close();host.stdin.end(JSON.stringify({op:'stop'})+'\n');await new Promise(resolve=>{if(host.exitCode!==null)return resolve();const t=setTimeout(()=>{host.kill();resolve();},10000);host.once('exit',()=>{clearTimeout(t);resolve();});});err.end();}
}
main().catch(e=>{console.error(e.name+': '+e.message);process.exitCode=1;});
