const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { randomUUID } = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const host = spawn(process.env.UNION_PYTHON, [path.join(process.cwd(), 'scripts', 'u106_result_delivery_host.py')],
    {cwd:process.cwd(),stdio:['pipe','pipe','inherit'],windowsHide:true});
  const lines=createInterface({input:host.stdout})[Symbol.asyncIterator]();
  async function read() {
    let timer;
    try{return await Promise.race([lines.next().then(r=>{assert.equal(r.done,false);return JSON.parse(r.value);}),
      new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('fixture timeout')),30000);})]);}
    finally{clearTimeout(timer);}
  }
  let browser;
  try {
    const ready=await read();
    browser=await chromium.launch({headless:true,executablePath:process.env.UNION_CHROMIUM_PATH});
    const context=await browser.newContext();
    await context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true,sameSite:'Lax'}]);
    const page=await context.newPage();page.setDefaultTimeout(5000);
    const originalRequests=[],savedReceipts=[];let failed;
    await page.route('**/api/v1/work/commands',async route=>{
      try{
        const request=route.request().postDataJSON();originalRequests.push(request);
        if(originalRequests.length===1){
          const models=await (await context.request.get(ready.origin+'/api/v1/models?organization_id='+ready.organization_id)).json();
          const c=models.connections[0];
          const update=await context.request.post(ready.origin+'/api/v1/models/commands',{headers:{Origin:ready.origin},data:{
            id:randomUUID(),organization_id:ready.organization_id,base_version:models.version,kind:'set_connection',
            data:{connection_id:c.id,expected_revision:c.revision,enabled:false,make_default:false}}});
          assert.equal(update.status(),200);assert.equal((await update.json()).receipt.status,'succeeded');
        }
        const response=await route.fetch();assert.equal(response.status(),200);
        const body=await response.json();savedReceipts.push(body.receipt);
        await route.fulfill({response});
      }catch(error){failed=error;await route.abort().catch(()=>{});}
    });
    await page.goto(ready.origin+'/tasks?organization='+ready.organization_id);
    await page.getByRole('button',{name:'采用此成果',exact:true}).click();
    await page.waitForFunction(()=>document.body.innerText.includes('AU 版本已变化')).catch(error=>{
      console.error('review receipt states',JSON.stringify(savedReceipts.map(r=>({status:r.status,message:r.message}))));
      throw failed||error;
    });
    if(failed)throw failed;
    assert.equal(savedReceipts[0].status,'rejected');
    assert.equal(originalRequests.length,1);
    await page.getByRole('button',{name:/重新|再次|重试|采用此成果/}).click();
    await page.getByRole('button',{name:'采用此成果',exact:true}).click();
    await page.getByText('已采用该成果并记录采用人',{exact:true}).waitFor();
    if(failed)throw failed;
    assert.equal(originalRequests.length,2);assert.notEqual(originalRequests[0].id,originalRequests[1].id);
    assert.equal(savedReceipts[1].status,'succeeded');
    const stored=await page.evaluate(()=>JSON.stringify(sessionStorage));
    for(const original of originalRequests)assert.ok(stored.includes(original.id));
    for(let i=0;i<2;i++){
      const response=await context.request.get(ready.origin+'/api/v1/governance/receipts?organization_id='+ready.organization_id+'&id='+originalRequests[i].id);
      assert.equal(response.status(),200);assert.deepEqual((await response.json()).receipt,savedReceipts[i]);
    }
    await page.reload();
    await page.getByRole('button',{name:'查询采用原请求',exact:true}).click();
    await page.getByText('已采用该成果并记录采用人',{exact:true}).waitFor();
    assert.equal(originalRequests.length,2);
    assert.equal(await page.getByRole('button',{name:/重新|再次|重试/}).count(),0);
    host.stdin.write('check\n');const report=await read();
    assert.deepEqual(report,{fake_model_calls:2,real_model_calls:0});
    const output=process.env.UNION_U106_INDEPENDENT_EVIDENCE;fs.mkdirSync(output,{recursive:true});
    fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({scope:'controlled',checks:[
      'actual concurrent AU update causes a genuine rejected work receipt',
      'no automatic retry on the rejected command',
      'explicit new action revalidates and uses a new command ID',
      'original rejection and successful adoption both preserved',
      'reload looks up successful original without another POST',
      'successful adoption is not offered for retry',
      'two local fake turns and zero real inference'],work_posts:2,...report},null,2));
    console.log('Independent U106 rejected recovery: 7 passed; Work POST=2; real model=0');
  }finally{
    if(browser)await browser.close();host.stdin.end('\n');
    if(host.exitCode===null)await new Promise(resolve=>host.once('exit',resolve));
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
