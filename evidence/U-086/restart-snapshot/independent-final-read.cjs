// Execute exact snapshot/restart fragments only, never driver main or inference.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {createRequire}=require('node:module');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../../..');
const requireDriver=createRequire(path.join(root,'scripts/exit22c_download.cjs'));
const original={protocol:'core.work.v1',organization_id:'au-original',version:20,
  access:{principal_id:'principal-original'},works:[{id:'work-original',status:'delivered',
    delivered_result_id:'result-original',budget:{max_calls:3,used:1,reserved:1},
    results:[{id:'result-original',status:'adopted',sha256:'digest-original'}],steps:[
      {step_ref:'step-1',attempt_id:'attempt-original',command_id:'loop-original',model_request_id:'model-1',
        status:'used',usage:{input_tokens:438,output_tokens:46},cost_status:'unknown',reason:'completed',connection:{id:'c1',revision:1}},
      {step_ref:'step-2',attempt_id:'attempt-original',command_id:'loop-original',model_request_id:'model-2',
        status:'unknown',usage:null,cost_status:'unknown',reason:'interrupted',connection:{id:'c1',revision:1}},
    ]}]};
const hashes={};
async function run(driver,at=0,change='principal'){
  const source=fs.readFileSync(path.join(root,'scripts',driver),'utf8');
  hashes[driver]=createHash('sha256').update(source).digest('hex');
  const between=(start,end)=>{assert.equal(source.split(start).length,2);assert.ok(source.includes(end));
    const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(b>a);return source.slice(a,b)};
  const snapshot=between('async function snapshot(', 'async function coreWork()');
  const restart=between('  const before = await snapshot();', "  fs.writeFileSync(path.join(output, 'checks.json')");
  let restarted=false,workReads=0,sessionReads=0,principal='principal-original',service='service-before',authenticated=true;
  const files=new Map(),requests=[];
  const context={require:requireDriver,assert,URLSearchParams,
    createdReceipt:{organization_id:'au-original'},workId:'work-original',resultId:'result-original',recorded:'digest-original',
    inflight:structuredClone(original.works[0].steps[1]),output:'/synthetic',path:{join:(...p)=>p.join('/')},
    fs:{writeFileSync:(name,data)=>files.set(name.split('/').at(-1),JSON.parse(data))},
    check:(name,value=true)=>assert.ok(value,name),host:{kill(){}},running:{child:{once:(_,fn)=>fn()}},
    startHost:async()=>{restarted=true;service='service-after';return {origin:'http://synthetic.invalid',child:{}}},
    page:{goto:async()=>{},getByText:()=>({waitFor:async()=>{}}),evaluate:async(fn,arg)=>
      vm.runInNewContext('('+fn.toString()+')(__arg)',{...context,__arg:arg})},
    fetch:async(url,init)=>{
      assert.ok(!init?.method||init.method==='GET');requests.push(url);
      if(url==='/api/session'){
        sessionReads++;return {status:authenticated?200:401,json:async()=>authenticated?
          {core_protocol:'core.au.v1',principal_id:principal,service_instance:service}:{error:'not_authenticated'}};
      }
      const parsed=new URL(url,'http://synthetic.invalid');
      assert.equal(parsed.pathname,'/api/v1/work');assert.equal(parsed.searchParams.get('organization_id'),'au-original');
      workReads++;
      // The GET was authorized when it began; the session changes before the
      // body returns. A surrounding current-session recheck must reject it.
      const body=structuredClone(original);
      if(restarted&&workReads===at){
        if(change==='principal')principal='another-principal';
        if(change==='service')service='another-service';
        if(change==='expired')authenticated=false;
      }
      return {status:200,json:async()=>body};
    }};
  let error=null,errorType=null;
  try{await vm.runInNewContext(snapshot+'\n(async()=>{'+restart+'\n})()',context,{timeout:1000})}
  catch(e){error=e.message;errorType=e.name}
  return {accepted:error===null,error,error_type:errorType,workReads,sessionReads,
    current:{principal,service,authenticated},savedAfter:files.has('snapshot-after-restart.json'),requests};
}
async function main(){
  const cases=[
    ['stable-interrupt','exit22b_page.cjs',0,'principal',true],
    ['stable-download','exit22c_download.cjs',0,'principal',true],
    ['guarded-interrupt-principal','exit22b_page.cjs',2,'principal',false],
    ['guarded-download-principal','exit22c_download.cjs',2,'principal',false],
    ['final-download-principal','exit22c_download.cjs',3,'principal',false],
    ['final-download-service','exit22c_download.cjs',3,'service',false],
    ['final-download-expired','exit22c_download.cjs',3,'expired',false],
  ];
  const observations=[];
  for(const [name,driver,at,change,expected]of cases){const observed=await run(driver,at,change);
    observations.push({name,expected_accept:expected,...observed,
      pass:expected?observed.accepted:!observed.accepted&&observed.error_type==='AssertionError'})}
  const report={head:'9d7fe98ea9e790d89f16f6a128af949ecda8ccb8',source_sha256:hashes,
    passed:observations.filter(x=>x.pass).length,failed:observations.filter(x=>!x.pass).length,observations,
    real_model_calls:0,scope:'Exact source VM/session-race acceptance checks; no browser, HTTP server, driver main or product change'};
  console.log(JSON.stringify(report,null,2));if(report.failed)process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=2});
