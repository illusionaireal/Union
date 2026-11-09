// Execute the exact original-output gate and cancel action. Never load driver main.
const {chromium}=require('playwright-core');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const {once}=require('node:events');
const {createRequire}=require('node:module');
const crypto=require('node:crypto');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..');
const driver=path.join(root,'scripts/exit22b_page.cjs');
const source=fs.readFileSync(process.argv[2]||driver,'utf8');
const start=source.indexOf('  // Original-output acceptance gate.');
const end=source.indexOf('  // on the race with the real model',start);
assert.ok(start>=0 && end>start);
const fragment=source.slice(start,end);
async function scenario(browser,mode) {
  const host=spawn(process.env.UNION_PYTHON||'python3',[path.join(__dirname,'http-host.py')],
    {cwd:root,stdio:['pipe','pipe','inherit'],env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',UNION_CANCEL_RESPONSE_FAULT:mode}});
  const exited=once(host,'exit'),lines=createInterface({input:host.stdout})[Symbol.asyncIterator]();
  async function next(){let timer;try{return await Promise.race([
    lines.next().then(r=>{assert.equal(r.done,false);return JSON.parse(r.value);}),
    new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('host timeout')),30000);})
  ]);}finally{clearTimeout(timer);}}
  const control=async op=>{host.stdin.write(op+'\n');return next();};
  let context;
  try {
    let ready=await next();context=await browser.newContext();
    const connect=async()=>context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true}]);
    await connect();const page=await context.newPage();page.setDefaultTimeout(mode==='missing'?1200:8000);
    const posts=[],clicks=[],files=new Map();let routeError;const cancelResponses=[];
    page.on('response',r=>{if(r.request().method()==='POST'&&r.request().postDataJSON()?.kind==='cancel_step')cancelResponses.push(r);});
    await page.exposeFunction('recordCancelClick',name=>clicks.push(name));
    await page.addInitScript(hidden=>{
      document.addEventListener('click',e=>{const b=e.target.closest('button');
        if(b && (b.textContent==='取消本次执行'||b.closest('[aria-label="原取消请求"]')))
          window.recordCancelClick(b.textContent);});
      if(hidden)new MutationObserver(()=>document.querySelectorAll('button').forEach(b=>{
        if(b.textContent==='取消本次执行')b.remove();
      })).observe(document,{subtree:true,childList:true});
    },mode==='missing');
    page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/v1/work/commands')posts.push(r.postDataJSON());});
    if(mode==='lost')await page.route('**/api/v1/work/commands',async route=>{
      if(route.request().postDataJSON().kind!=='cancel_step')return route.continue();
      try{const response=await route.fetch();assert.equal(response.status(),200);
        assert.equal((await response.json()).receipt.cancel_accepted,true);await route.abort('failed');}
      catch(e){routeError=e;await route.abort().catch(()=>{});}
    });
    if(mode==='no-output')await page.route('**/api/v1/work/events?*',async route=>{
      const response=await route.fetch(),body=await response.json();
      Object.assign(body,{events:[],cursor:0,last_seq:0,has_more:false});await route.fulfill({response,json:body});
    });
    if(['receipt','denied','principal','service'].includes(mode))await page.route('**/api/v1/governance/receipts?*',async route=>{
      if(!posts.some(p=>p.kind==='cancel_step'))return route.continue();
      const response=await route.fetch(),body=await response.json();
      if(mode==='receipt')body.receipt.model_request_id='replacement';
      if(['principal','service'].includes(mode))await page.route('**/api/session',async sr=>{
        const original=await sr.fetch(),body=await original.json();
        body[mode==='principal'?'principal_id':'service_instance']='replacement';await sr.fulfill({response:original,json:body});
      });
      await route.fulfill({response,status:mode==='denied'?403:response.status(),json:body});
    });
    const workRead=async()=>page.evaluate(async id=>{
      const r=await fetch('/api/v1/work?organization_id='+encodeURIComponent(id));
      if(r.status!==200)throw Error('Work read '+r.status);return r.json();
    },ready.organization_id);
    await page.goto(ready.origin+'/tasks?organization='+ready.organization_id);
    await page.getByRole('button',{name:'运行 AI 工作',exact:true}).click();
    let work;const deadline=Date.now()+8000;
    do {work=(await workRead()).works[0];if(work.steps[0]?.status==='reserved')break;
      await page.waitForTimeout(50);}while(Date.now()<deadline);
    assert.equal(work.steps[0]?.status,'reserved');
    await page.getByRole('button',{name:'刷新 AI 工作',exact:true}).click();
    let error,result;
    let timer;try {result=await Promise.race([vm.runInNewContext('(async()=>{'+fragment+';return {originalCancelReference,cancelEvidenceBefore};})()',{
      page,require:createRequire(driver),crypto,TextEncoder,URL,URLSearchParams,
      createdReceipt:{organization_id:ready.organization_id},workId:work.id,inflight:work.steps[0],
      coreWork:workRead,output:'/synthetic',path,fs:{writeFileSync:(name,value)=>files.set(path.basename(name),JSON.parse(value))},
      check:(name,value=true)=>assert.ok(value,name),
      waitFor:async(predicate,name)=>{for(let n=0;n<12;n++){if(await predicate())return;await page.waitForTimeout(50);}throw Error('timeout: '+name);},
    }),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('fragment blocked after transport completion')),15000);})]);}catch(e){error=e;}finally{clearTimeout(timer);}
    if(routeError)throw routeError;
    if(['body-lost','denied-body-lost','malformed'].includes(mode)){
      assert.equal(cancelResponses.length,1,'actual cancel response headers received');
      assert.equal(cancelResponses[0].status(),mode==='denied-body-lost'?403:200);
      const failure=cancelResponses[0].request().failure();
      if(mode==='malformed')assert.equal(failure,null,'malformed body fully transferred');
      else assert.ok(failure,'actual response body transfer interrupted');
    }
    if(['missing','no-output'].includes(mode)) {
      assert.ok(error,'unavailable page/output must fail acceptance');
      assert.deepEqual(posts.map(p=>p.kind),['run_loop'],'no direct cancel fallback');
      assert.equal(files.has('cancel-receipt-before-restart.json'),false);
    }else if(['receipt','denied','principal','service','denied-body-lost','malformed'].includes(mode)) {
      assert.ok(error,'wrong receipt or identity must fail acceptance');
      assert.equal(files.has('cancel-receipt-before-restart.json'),false);
      assert.deepEqual(posts.map(p=>p.kind),['run_loop','cancel_step']);
    }else {
      assert.ifError(error);
      assert.deepEqual(clicks,['取消本次执行','查询原请求'],'actual cancel and recovery controls');
      assert.deepEqual(posts.map(p=>p.kind),['run_loop','cancel_step']);
      assert.equal(result.originalCancelReference.cancel_id,posts[1].id);
      assert.equal(posts[1].data.work_id,work.id);assert.equal(posts[1].data.step_id,work.steps[0].step_ref);
      assert.equal(files.get('original-output-observation.json').model_request_id,work.steps[0].model_request_id);
      ready=await control('reopen');await connect();
      await page.goto(ready.origin+'/tasks?organization='+ready.organization_id);
      const {readCancelEvidence}=require('../../../scripts/exit22-cancel-evidence.cjs');
      const reopened=await readCancelEvidence(page,result.originalCancelReference,result.cancelEvidenceBefore.receipt);
      assert.deepEqual(reopened.receipt,result.cancelEvidenceBefore.receipt);
      assert.equal(posts.length,2,'reopen cannot reissue run or cancel');
    }
    const counts=await control('inspect');assert.equal(counts.fake_model_posts,1);assert.equal(counts.real_model_calls,0);
    assert.equal(counts.cancel_posts,['missing','no-output'].includes(mode)?0:1);
    assert.equal(counts.budget.reserved,1);assert.equal(counts.budget.used,0);
    return {mode,passed:true,...counts};
  }finally{if(context)await context.close();host.stdin.end('stop\n');const [code]=await exited;assert.equal(code,0,'fixture cleanup');}
}
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.UNION_CHROMIUM_PATH?{executablePath:process.env.UNION_CHROMIUM_PATH}:{})});
  const results=[];
  try{for(const mode of (process.env.UNION_CANCEL_ACTION_CASES||'normal,body-lost,denied-body-lost,malformed').split(',')){
    try{results.push(await scenario(browser,mode));}catch(e){results.push({mode,passed:false,error:String(e)});}
  }}finally{await browser.close();}
  console.log(JSON.stringify({scope:'controlled',results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
