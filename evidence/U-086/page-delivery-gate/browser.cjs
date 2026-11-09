// Execute the exact driver action block on the real Core UI and disposable SQLite.
// The host prepares two explicit fake model turns; driver main is never imported.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { once } = require('node:events');
const { createHash } = require('node:crypto');
const { createRequire } = require('node:module');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../..');
const source = fs.readFileSync(path.join(root, 'scripts/exit22c_download.cjs'), 'utf8');
const marker = "  check('downloaded title is the recorded title', meta.title === recordedTitle);";
assert.equal(source.split(marker).length, 2);
const start = source.indexOf(marker) + marker.length;
const end = source.indexOf('  const before = await snapshot();', start);
assert.ok(end > start);
const action = source.slice(start, end);
const {readSnapshot} = require(path.join(root, 'scripts/exit22-restart-evidence.cjs'));

async function scenario(browser, hidden) {
  const host = spawn(process.env.UNION_PYTHON, ['scripts/u106_result_delivery_host.py'],
    {cwd:root, stdio:['pipe','pipe','pipe'], env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'}});
  host.stderr.resume();
  const exited = once(host, 'exit');
  const lines = createInterface({input:host.stdout})[Symbol.asyncIterator]();
  async function readLine() {
    let timer;
    try {return await Promise.race([lines.next().then(r => {
      assert.equal(r.done,false,'fixture exited early');return JSON.parse(r.value);
    }),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('fixture timeout')),30000);})]);}
    finally {clearTimeout(timer);}
  }
  let context;
  try {
    const ready = await readLine();
    context = await browser.newContext();
    await context.addCookies([{name:ready.cookie_name,value:ready.token,url:ready.origin,httpOnly:true,sameSite:'Lax'}]);
    const page = await context.newPage();
    await page.goto(ready.origin+'/tasks?organization='+ready.organization_id);
    try {await page.getByRole('button',{name:'采用此成果',exact:true}).waitFor({timeout:10000});}
    catch(error) {throw Error('fixture UI not ready: '+(await page.locator('body').innerText()).slice(0,600));}
    const clicks = [], posts = [], files = new Map();
    await page.exposeFunction('recordResultClick',name=>clicks.push(name));
    await page.evaluate(()=>document.addEventListener('click',event=>{
      const button=event.target.closest('button');
      if(button && ['采用此成果','交付此成果'].includes(button.textContent))
        window.recordResultClick(button.textContent);
    }));
    page.on('request',request=>{
      if(request.method()==='POST' && new URL(request.url()).pathname==='/api/v1/work/commands')
        posts.push(request.postDataJSON());
    });
    if(hidden)await page.locator('.work-result-delivery').evaluateAll(nodes=>nodes.forEach(node=>node.remove()));
    page.setDefaultTimeout(hidden?1200:15000);
    const snapshot=()=>readSnapshot(page,ready.organization_id,ready.work_id);
    let error;
    try {
      await vm.runInNewContext('(async()=>{'+action+'})()',{
        require:createRequire(path.join(root,'scripts/exit22c_download.cjs')),
        material:{path:'nested/a.md',sha256:createHash('sha256').update('a 正文\n','utf8').digest('hex'),
          bytes:Buffer.byteLength('a 正文\n','utf8')},
        page,assert,URL,JSON,createdReceipt:{organization_id:ready.organization_id},
        workId:ready.work_id,resultId:ready.result.id,recorded:ready.result.sha256,recordedFull:ready.result,
        snapshot,coreWork:snapshot,output:'/synthetic',path,
        fs:{writeFileSync:(name,value)=>files.set(name,JSON.parse(value))},
        check:(name,value=true)=>assert.ok(value,name),
        waitFor:async(predicate,name)=>{
          for(let n=0;n<60;n++){if(await predicate())return;await new Promise(r=>setTimeout(r,100));}
          throw Error('timeout: '+name);
        },
      });
    } catch(caught) {error=caught;}
    const final = (await snapshot()).works.find(w=>w.id===ready.work_id);
    if(hidden){
      assert.ok(error,'missing Core UI must reject; direct API success is not page acceptance');
      assert.equal(posts.length,0,'missing controls caused a hidden write');
      assert.equal(final.results[0].status,'candidate');assert.equal(files.size,0);
    } else {
      assert.ifError(error);
      assert.deepEqual(clicks,['采用此成果','交付此成果'],'both actual Core controls must be used');
      assert.deepEqual(posts.map(p=>p.kind),['adopt_result','deliver_work']);
      for(const p of posts){assert.equal(p.data.work_id,ready.work_id);assert.equal(p.data.result_id,ready.result.id);}
      assert.equal(final.status,'delivered');assert.equal(final.delivered_result_id,ready.result.id);
      assert.equal(final.results[0].status,'adopted');assert.equal(files.size,1);
      // The downstream original-request snapshot contract remains valid.
      await page.reload();
      const reopened=await snapshot();
      assert.equal(reopened.works.find(w=>w.id===ready.work_id).delivered_result_id,ready.result.id);
    }
    host.stdin.write('check\n');const counts=await readLine();
    assert.deepEqual(counts,{fake_model_calls:2,real_model_calls:0});
    return {case:hidden?'missing-controls':'actual-controls',passed:true,work_posts:posts.length,...counts};
  } finally {
    if(context)await context.close();host.stdin.end('\n');
    const [code]=await exited;assert.equal(code,0,'fixture exit');
  }
}

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.UNION_CHROMIUM_PATH});
  const results=[];
  try {for(const hidden of [false,true]){
    try {results.push(await scenario(browser,hidden));}
    catch(error){results.push({case:hidden?'missing-controls':'actual-controls',passed:false,error:String(error)});}
  }} finally {await browser.close();}
  console.log(JSON.stringify({scope:'controlled',results},null,2));
  if(results.some(r=>!r.passed))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
