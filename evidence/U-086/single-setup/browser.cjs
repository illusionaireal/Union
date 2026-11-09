// Run actual creation/navigation code, never the inference portion of driver main.
const {chromium} = require('playwright-core');
const {spawn} = require('node:child_process');
const {createInterface} = require('node:readline');
const {once} = require('node:events');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../..');

async function scenario(browser, driver) {
  const source = fs.readFileSync(path.join(root, 'scripts', driver), 'utf8');
  const start = source.indexOf('  createdReceipt = await page.evaluate');
  const end = source.indexOf('  let hostGrantRef = null;', start);
  assert.ok(start >= 0 && end > start);
  const host = spawn(process.env.UNION_PYTHON, [path.join(__dirname, 'host.py')],
    {cwd:root, stdio:['pipe','pipe','pipe'], env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'}});
  host.stderr.resume();
  const exited = once(host, 'exit');
  const lines = createInterface({input:host.stdout})[Symbol.asyncIterator]();
  let context, timer;
  try {
    const running = await Promise.race([lines.next().then(r=>{
      assert.equal(r.done,false,'host exited early');return JSON.parse(r.value);
    }),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('host timeout')),30000);})]);
    clearTimeout(timer);
    context = await browser.newContext();
    const page = await context.newPage(), commands = [];
    page.on('request',request=>{
      if(request.method()==='POST' && new URL(request.url()).pathname==='/api/commands')
        commands.push(request.postDataJSON());
    });
    await page.goto(running.board_url);
    const receipt = await vm.runInNewContext('(async()=>{'+source.slice(start,end)+';return createdReceipt;})()',{
      page,running,path,output:root,errors:[],check:(name,value=true)=>assert.ok(value,name),
    });
    assert.equal(commands.length,1,'one driver preparation must create exactly one persisted AU');
    assert.equal(commands[0].id,receipt.id);
    const read = async()=>page.evaluate(async()=>{
      const response=await fetch('/api/session');
      if(response.status!==200)throw Error('session read rejected');return response.json();
    });
    let session = await read();
    assert.deepEqual(session.organizations.map(au=>au.id),[receipt.organization_id]);
    await page.reload();session=await read();
    assert.deepEqual(session.organizations.map(au=>au.id),[receipt.organization_id]);
    assert.equal(commands.length,1,'reload must not create another AU');
    return {driver,passed:true,created_aus:commands.length,real_model_calls:0,modeld_grants:0};
  } finally {
    clearTimeout(timer);if(context)await context.close();host.stdin.end('\n');
    const [code]=await exited;assert.equal(code,0,'fixture exit');
  }
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.UNION_CHROMIUM_PATH});
  const results=[];
  try {for(const driver of ['exit22b_page.cjs','exit22c_download.cjs']){
    try {results.push(await scenario(browser,driver));}
    catch(error){results.push({driver,passed:false,error:String(error)});}
  }} finally {await browser.close();}
  console.log(JSON.stringify({scope:'controlled',results},null,2));
  if(results.some(result=>!result.passed))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
