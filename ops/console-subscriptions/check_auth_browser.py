"""Real HTTPS React UI with explicitly simulated subscription actions; native starts are probed separately."""
import json,os,subprocess
from pathlib import Path
base=Path('/volume1/docker/union-dev')
out=base/'install/auth-repair-browser';out.mkdir(mode=0o700,exist_ok=True);os.chown(out,10001,10001)
js=r'''const fs=require('fs');const {chromium}=require('/deps/playwright-core');
(async()=>{const {url}=JSON.parse(fs.readFileSync('/access.json','utf8'));const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});const checks=[];
try{const c=await b.newContext({ignoreHTTPSErrors:true,viewport:{width:1440,height:1000}});const p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
await p.goto(url);await p.getByText('已连接本机服务',{exact:true}).waitFor();await p.getByRole('heading',{name:'订阅与账号连接'}).waitFor();
const live=await c.request.get('https://192.168.1.29:18766/api/subscriptions');const liveStatus=await live.json();if(!liveStatus.native_available)throw Error('real native backend unavailable');checks.push('actual HTTPS UI sees authenticated native backend');
if(liveStatus.pending.length)throw Error('unexpected real pending intent before browser fixture');checks.push('old diagnosed failure no longer blocks a fresh user login');
let receipt;let commands=[];const terminal=['succeeded','failed'];
await p.route('**/api/subscriptions',r=>r.fulfill({json:{available:true,native_available:true,key_available:true,providers:[],pending:receipt&&!terminal.includes(receipt.status)?[receipt]:[]}}));
await p.route('**/api/subscription-receipts?*',r=>r.fulfill({json:{receipt}}));
await p.route('**/api/subscription-commands',r=>{const v=r.request().postDataJSON();commands.push(v.action);if(v.action==='authorize_go')receipt={id:v.id,action:v.action,status:'authorizing',message:'受控浏览器替身：Go账号授权',url:'https://opencode.ai/console/auth/device',instructions:'模拟设备码 TEST-CODE'};else if(v.action==='authorize_chatgpt')receipt={id:v.id,action:v.action,status:'authorizing',message:'受控浏览器替身：ChatGPT账号授权',url:'https://auth.openai.com/api/accounts/authorize',instructions:'模拟远程回调说明',needs_callback:true};else if(v.action==='complete_chatgpt'){if(v.target_id!==receipt.id||!v.callback_url.includes('TEST_CALLBACK'))throw Error('callback command mismatch');receipt={...receipt,status:'succeeded',message:'受控浏览器替身：回调完成',needs_callback:false};}else throw Error('unexpected browser mutation');return r.fulfill({json:{receipt}})});
await p.reload();const go=p.getByRole('button',{name:'连接 OpenCode Go 账号'});await go.waitFor();await p.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(x=>x.textContent==='连接 OpenCode Go 账号'&&!x.disabled));await go.click();
await p.getByRole('link',{name:'打开官方授权页面'}).waitFor();if(await p.getByRole('link',{name:'打开官方授权页面'}).getAttribute('href')!=='https://opencode.ai/console/auth/device')throw Error('Go link wrong');checks.push('simulated Go button produces official link and device instructions without API key');
receipt={...receipt,status:'failed',message:'受控浏览器替身：Go测试已结束'};await p.reload();const chat=p.getByRole('button',{name:'连接 ChatGPT 订阅'});await p.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(x=>x.textContent==='连接 ChatGPT 订阅'&&!x.disabled));await chat.click();
const field=p.getByLabel('官方授权后的完整回调地址');await field.waitFor();if(await field.getAttribute('type')!=='password')throw Error('callback not masked');checks.push('simulated ChatGPT browser authorization shows official link and masked callback');
await p.setViewportSize({width:320,height:900});if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('mobile callback overflow');await p.screenshot({path:'/output/auth-mobile-simulated.png',fullPage:true});checks.push('320px callback form has no horizontal overflow');
await field.fill('http://127.0.0.1:49152/auth/callback?code=TEST_CALLBACK&state=test');await p.getByRole('button',{name:'完成 ChatGPT 连接'}).click();await p.getByText('受控浏览器替身：回调完成',{exact:true}).waitFor();
if((await p.evaluate(()=>JSON.stringify(sessionStorage))).includes('TEST_CALLBACK'))throw Error('callback credential persisted');checks.push('simulated callback clears input, stores only request identity and shows final receipt');
if(commands.join(',')!=='authorize_go,authorize_chatgpt,complete_chatgpt')throw Error('duplicate commands');checks.push('each simulated action submitted once');
await p.setViewportSize({width:1440,height:1000});await p.screenshot({path:'/output/auth-desktop-simulated.png',fullPage:true});
if(!(await c.cookies()).some(x=>x.secure&&x.httpOnly))throw Error('secure cookie missing');checks.push('actual TLS session Secure HttpOnly cookie');
const hostile=await c.request.post('https://192.168.1.29:18766/api/subscription-commands',{headers:{Origin:'https://evil.example'},data:{id:'hostile',action:'authorize_go'}});if(hostile.status()!==403)throw Error('cross origin allowed');checks.push('actual cross-origin mutation403');
const anon=await b.newContext({ignoreHTTPSErrors:true});const denied=await anon.request.get('https://192.168.1.29:18766/api/subscriptions');if(denied.status()!==401)throw Error('anonymous allowed');await anon.close();checks.push('actual anonymous account read401');
if(errors.length)throw Error('browser runtime error');checks.push('no browser runtime errors');
console.log(JSON.stringify({checks,subscription_actions:'explicitly_simulated',real_model_calls:0,real_account_login:false,self_signed_certificate_test_exception:true}));
}finally{await b.close()}})().catch(e=>{console.error(e.message);process.exit(1)})'''
p=subprocess.run(['/usr/local/bin/docker','run','--rm','--network','host','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,exec,uid=10001,gid=10001','--shm-size','256m',
    '-v',str(base/'Union/node_modules')+':/deps:ro','-v',str(base/'ui-private/access.json')+':/access.json:ro','-v',str(out)+':/output:rw',
    'union-dev-tools:2026-11-01','node','-e',js],capture_output=True,text=True,timeout=90)
(out/'result.json').write_text(p.stdout);(out/'stderr.log').write_text(p.stderr)
print('browser_exit_code='+str(p.returncode));print(p.stdout);print(p.stderr);raise SystemExit(p.returncode)
