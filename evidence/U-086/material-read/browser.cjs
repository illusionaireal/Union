// The actual pre-delivery driver gate reads genuine Core/SQLite facts in Chrome.
const {chromium}=require('playwright-core');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const {createRequire}=require('node:module');
const {createHash}=require('node:crypto');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const assert=require('node:assert/strict');
const {readSnapshot}=require('../../../scripts/exit22-restart-evidence.cjs');
const root=path.resolve(__dirname,'../../..');
const source=fs.readFileSync(process.env.UNION_EXIT22_DRIVER_SOURCE || path.join(root,'scripts/exit22c_download.cjs'),'utf8');
const start=source.indexOf('  const deliveryBefore = await snapshot();');
const end=source.indexOf('  const resultControls =',start);
assert.ok(start>=0 && end>start);
const block=source.slice(start,end);

async function main(){
  const host=spawn(process.env.UNION_PYTHON || 'python3',['scripts/u106_result_delivery_host.py'],
    {cwd:root,stdio:['pipe','pipe','inherit']});
  const exit=new Promise(resolve=>host.once('exit',(code,signal)=>resolve({code,signal})));
  const reader=createInterface({input:host.stdout}),lines=reader[Symbol.asyncIterator]();
  async function ready(){let timer;try{return await Promise.race([
    lines.next().then(v=>{assert.equal(v.done,false);return JSON.parse(v.value);}),
    new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('fixture timeout')),30000);})]);
  }finally{clearTimeout(timer);}}
  let browser;const results=[],writes=[];
  try{
    const fixture=await ready();
    browser=await chromium.launch({headless:true,...(process.env.UNION_CHROMIUM_PATH?
      {executablePath:process.env.UNION_CHROMIUM_PATH}:{})});
    const context=await browser.newContext(),page=await context.newPage();
    await context.addCookies([{name:fixture.cookie_name,value:fixture.token,url:fixture.origin,httpOnly:true}]);
    await page.goto(fixture.origin+'/api/session');
    page.on('request',r=>{if(r.method()!=='GET')writes.push(r.method());});
    const before=await readSnapshot(page,fixture.organization_id,fixture.work_id);
    const material={path:'nested/a.md',sha256:createHash('sha256').update('a 正文\n','utf8').digest('hex'),
      bytes:Buffer.byteLength('a 正文\n','utf8')};
    const modes=['original','no-read','list-only','wrong-path','wrong-digest','wrong-bytes','uncited','duplicate','other-attempt','unknown'];
    for(const mode of modes){
      let workGets=0;
      await page.route('**/api/v1/work?*',async route=>{
        workGets++;const response=await route.fetch(),body=await response.json();
        assert.equal(response.status(),200);
        const work=body.works.find(w=>w.id===fixture.work_id),read=work.tool_calls[0];
        if(mode==='no-read')work.tool_calls=[];
        if(mode==='list-only')read.tool='list_documents';
        if(mode==='wrong-path')read.arguments.path='other.md';
        if(mode==='wrong-digest')read.sha256='a'.repeat(64);
        if(mode==='wrong-bytes')read.bytes='a 正文\n'.length;
        if(mode==='uncited')read.step_ref='other-receipt';
        if(mode==='duplicate')work.tool_calls.push({...read});
        if(mode==='other-attempt')read.attempt_id='other-attempt';
        if(mode==='unknown')for(const step of work.steps)step.status='unknown';
        if(mode==='unknown'){work.budget.used=0;work.budget.reserved=work.steps.length;}
        await route.fulfill({response,json:body});
      });
      try{
        let error;
        try{await vm.runInNewContext('(async()=>{'+block+'})()',{
          require:createRequire(path.join(root,'scripts/exit22c_download.cjs')),material,
          createdReceipt:{organization_id:fixture.organization_id},workId:fixture.work_id,
          resultId:fixture.result.id,recorded:fixture.result.sha256,recordedFull:fixture.result,
          snapshot:()=>readSnapshot(page,fixture.organization_id,fixture.work_id),
          check:(name,value=true)=>assert.ok(value,name),path,output:'/synthetic',fs:{writeFileSync:()=>{}}});
        }catch(e){error=e;}
        if(mode==='original')assert.ifError(error);else assert.ok(error,'driver accepted '+mode);
        assert.equal(workGets,1);results.push({mode,passed:true,work_gets:workGets});
      }catch(e){results.push({mode,passed:false,error:String(e),work_gets:workGets});}
      finally{await page.unroute('**/api/v1/work?*');}
    }
    assert.deepEqual(await readSnapshot(page,fixture.organization_id,fixture.work_id),before);
    assert.deepEqual(writes,[]);
    host.stdin.write('check\n');assert.deepEqual(await ready(),{fake_model_calls:2,real_model_calls:0});
  }finally{
    if(browser)await browser.close();host.stdin.end();let timer;
    try{const result=await Promise.race([exit,new Promise(resolve=>{timer=setTimeout(()=>resolve({timeout:true}),15000);})]);
      if(result.timeout){host.kill();throw Error('fixture shutdown timeout');}assert.equal(result.code,0);
    }finally{clearTimeout(timer);reader.close();}
  }
  console.log(JSON.stringify({scope:'controlled',fake_model_calls:2,real_model_calls:0,writes:writes.length,results},null,2));
  if(results.some(r=>!r.passed))process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=1;});
