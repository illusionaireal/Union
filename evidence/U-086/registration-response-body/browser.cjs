// Run the complete registration prefix of each driver on actual Core/SQLite.
// Never load driver main or configure a real model. Host rejects all inference.
const {chromium}=require('playwright-core');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const {once}=require('node:events');
const {createRequire}=require('node:module');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..');
const actions=['登记 AI 工作','查询登记原请求','准备本轮执行'];
function action(driver) {
  const source=fs.readFileSync(path.join(root,'scripts',driver),'utf8');
  const start=source.indexOf('  // Reload the work read');
  const end=source.indexOf("  await card().getByRole('button', { name: /运行 AI 工作|自动执行/ }).click();",start);
  assert.ok(start>=0 && end>start);
  return source.slice(start,end);
}
async function scenario(browser,driver,mode) {
  const host=spawn(process.env.UNION_PYTHON,[path.join(__dirname,'http-host.py')],
    {cwd:root,stdio:['pipe','pipe','pipe'],env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',UNION_REGISTRATION_RESPONSE_FAULT:mode}});
  host.stderr.resume();const exited=once(host,'exit');
  const lines=createInterface({input:host.stdout})[Symbol.asyncIterator]();
  async function readLine(){let timer;try{return await Promise.race([
    lines.next().then(r=>{assert.equal(r.done,false);return JSON.parse(r.value);}),
    new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('host timeout')),30000);})
  ]);}finally{clearTimeout(timer);}}
  let context;
  try {
    const ready=await readLine();context=await browser.newContext();
    await context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true,sameSite:'Lax'}]);
    const page=await context.newPage(),posts=[],clicks=[],files=new Map();
    const responses=[],failed=[],finished=[];
    const registration=r=>r.method()==='POST' && new URL(r.url()).pathname==='/api/v1/work/commands' && r.postDataJSON()?.kind==='start_work';
    page.on('response',r=>{if(registration(r.request()))responses.push(r.status());});
    page.on('requestfailed',r=>{if(registration(r))failed.push(r);});
    page.on('requestfinished',r=>{if(registration(r))finished.push(r);});
    page.setDefaultTimeout(12000);
    await page.exposeFunction('recordRegistrationClick',name=>clicks.push(name));
    await page.addInitScript(actions=>{
      document.addEventListener('click',e=>{const b=e.target.closest('button');
        if(b && actions.includes(b.textContent))window.recordRegistrationClick(b.textContent);});
    },actions);
    page.on('request',r=>{if(r.method()==='POST' && new URL(r.url()).pathname==='/api/v1/work/commands')posts.push(r.postDataJSON());});
    await page.goto(ready.origin+'/tasks?organization='+ready.organization_id);
    let error,outcome,timer;
    try {outcome=await Promise.race([vm.runInNewContext('(async()=>{'+action(driver)+';return workId;})()',{
      page,require:createRequire(path.join(root,'scripts',driver)),
      running:{origin:ready.origin},createdReceipt:{organization_id:ready.organization_id},
      workId:'work-exit',goal:'受控页面登记与原请求恢复',errors:[],output:'/synthetic',path,
      fs:{writeFileSync:(name,value)=>files.set(name,JSON.parse(value))},
      check:(name,value=true)=>assert.ok(value,name),
    }),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('registration recovery exceeded 15s bound')),15000);})]);}catch(e){error=e;}finally{clearTimeout(timer);}
    const read=await (await context.request.get(ready.origin+'/api/v1/work?organization_id='+ready.organization_id)).json();
    if(['body-lost','denied-body-lost'].includes(mode)) {
      assert.deepEqual(responses,[mode==='denied-body-lost'?403:200],'real HTTP headers precede failed transfer');
      assert.equal(failed.length,1);assert.equal(finished.length,0);
    } else {assert.deepEqual(responses,[200]);assert.equal(failed.length,0);assert.equal(finished.length,1);}
    if(['denied-body-lost','malformed','receipt-body'].includes(mode)) {
      if(mode==='denied-body-lost')assert.match(String(error),/registration POST HTTP/,'known 403 is not recovered as transport loss');
      else assert.ok(error,'complete invalid POST receipt must stop acceptance');
      assert.deepEqual(posts.map(p=>p.kind),['start_work']);
      assert.equal(read.works.length,1);assert.equal(read.works[0].attempts.length,0);assert.equal(files.size,0);
    }else {
      assert.ifError(error);assert.deepEqual(clicks,actions,'use all actual Core controls');
      assert.deepEqual(posts.map(p=>p.kind),['start_work','start_attempt']);
      const original=posts[0];assert.notEqual(original.data.work_id,'work-exit');
      assert.equal(outcome,original.data.work_id);assert.equal(posts[1].data.work_id,outcome);
      assert.equal(read.works.length,1);assert.equal(read.works[0].id,outcome);
      assert.equal(read.works[0].attempts.length,1);assert.equal(read.works[0].steps.length,0);
      assert.equal(read.works[0].budget.reserved,0);assert.equal(read.works[0].budget.used,0);
      assert.equal(files.size,1);
      await page.reload();assert.equal(posts.length,2,'refresh must not repeat registration/preparation');
    }
    host.stdin.write('check\n');const counts=await readLine();assert.equal(counts.model_requests,0);
    return {driver,mode,passed:true,work_posts:posts.length,model_requests:0,registration_response_statuses:responses,failed_transfers:failed.length};
  }finally{if(context)await context.close();host.stdin.end('\n');const [code]=await exited;assert.equal(code,0);}
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.UNION_CHROMIUM_PATH});const results=[];
  const modes=process.env.UNION_REGISTRATION_CASES?.split(',')||['normal','body-lost','denied-body-lost','malformed','receipt-body'];
  try{for(const driver of ['exit22b_page.cjs','exit22c_download.cjs'])for(const mode of modes){
    try{results.push(await scenario(browser,driver,mode));}
    catch(error){results.push({driver,mode,passed:false,error:String(error)});}
  }}finally{await browser.close();}
  console.log(JSON.stringify({scope:'controlled',results},null,2));
  if(results.some(r=>!r.passed))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
