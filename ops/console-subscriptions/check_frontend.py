import json
import os
from pathlib import Path
import subprocess

base=Path('/volume1/docker/union-dev')
output=base/'install/subscription-browser';output.mkdir(exist_ok=True,mode=0o700);os.chown(output,10001,10001)
js='''const fs=require('fs');const {chromium}=require('/deps/playwright-core');
(async()=>{const {url}=JSON.parse(fs.readFileSync('/access.json','utf8'));const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});const checks=[];
try{const c=await b.newContext({ignoreHTTPSErrors:true,viewport:{width:1440,height:1000}});const p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
await p.goto(url);await p.getByText('已连接本机服务',{exact:true}).waitFor();await p.getByRole('heading',{name:'订阅与账号连接'}).waitFor();
checks.push('AI-UNION models page contains subscription configuration without organization');
if(await p.getByLabel('Go API Key').getAttribute('type')!=='password')throw Error('key input is not masked');checks.push('Go key input is masked');
await p.getByRole('button',{name:'连接 ChatGPT 订阅'}).waitFor();await p.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(x=>x.textContent==='连接 ChatGPT 订阅'&&!x.disabled),null,{timeout:25000});checks.push('ChatGPT authorization control is available');
if(!(await c.cookies()).some(x=>x.secure&&x.httpOnly))throw Error('Secure cookie missing');checks.push('TLS session uses Secure HttpOnly cookie');
const hostile=await c.request.post('https://192.168.1.29:18766/api/subscription-commands',{headers:{Origin:'https://evil.example'},data:{id:'hostile',action:'save_go',api_key:'NEVER_SENT'}});if(hostile.status()!==403)throw Error('cross origin allowed');checks.push('cross-origin mutation rejected before backend');
const anonymous=await b.newContext({ignoreHTTPSErrors:true});const denied=await anonymous.request.get('https://192.168.1.29:18766/api/subscriptions');if(denied.status()!==401)throw Error('anonymous access allowed');await anonymous.close();checks.push('anonymous account access denied');
await p.screenshot({path:'/output/models-desktop.png',fullPage:true});await p.setViewportSize({width:320,height:900});if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('mobile overflow');await p.screenshot({path:'/output/models-mobile.png',fullPage:true});checks.push('320px layout has no horizontal overflow');
if(errors.length)throw Error(errors.join(';'));checks.push('no browser runtime errors');
console.log(JSON.stringify({checks,real_model_calls:0,credentials_submitted:false,self_signed_certificate_test_exception:true}));
}finally{await b.close()}})().catch(e=>{console.error(e.message);process.exit(1)})'''
p=subprocess.run(['/usr/local/bin/docker','run','--rm','--network','host','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','10001:10001',
    '--tmpfs','/tmp:rw,exec,nosuid,size=512m,uid=10001,gid=10001','--shm-size','256m',
    '-v',str(base/'Union/node_modules')+':/deps:ro','-v',str(base/'ui-private/access.json')+':/access.json:ro','-v',str(output)+':/output:rw',
    'union-dev-tools:2026-11-01','node','-e',js],capture_output=True,text=True,timeout=90)
(output/'result.json').write_text(p.stdout);(output/'stderr.log').write_text(p.stderr)
print('browser_exit_code='+str(p.returncode));print(p.stdout);print(p.stderr)
raise SystemExit(p.returncode)
