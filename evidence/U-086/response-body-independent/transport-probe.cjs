const assert=require('node:assert/strict'),{EventEmitter}=require('node:events');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process');
const root=process.cwd(),baseRequire=require('node:module').createRequire(path.join(root,'scripts','review.cjs'));
const ref={organization_id:'au-original',work_id:'work-original',step_ref:'work-original#s1',attempt_id:'attempt-original',command_id:'run-original',model_request_id:'model-original',principal_id:'principal-original',service_instance:'service-original',connection:{id:'connection-original',revision:1}};
const input={title:'title',goal:'goal',member_name:'AI',materials_root:'docs',max_calls:3,tools:['read_document','list_documents'],connection_id:'connection-original',expected_revision:1};
function load(file,sha){const source=sha?cp.execFileSync('git',['show',sha+':scripts/'+file],{encoding:'utf8'}):fs.readFileSync(path.join(root,'scripts',file),'utf8');const module={exports:{}};vm.runInNewContext('(function(require,module,exports){'+source+'\n})',{URL,URLSearchParams,console})(baseRequire,module,module.exports);return module.exports;}
function pageFixture(kind,fault){
 const page=new EventEmitter();let requestWait,responseWait,posts=0,lookup=0,stage=0;
 const cmd={id:kind+'-original',kind,organization_id:ref.organization_id,base_version:12,data:kind==='cancel_step'?{work_id:ref.work_id,step_id:ref.step_ref}:{...input,work_id:ref.work_id,member_id:'member',binding_id:'binding',definition_id:'definition',mandate_id:'mandate'}};
 const receipt={id:cmd.id,kind,organization_id:ref.organization_id,base_version:12,version:13,actor_principal_id:ref.principal_id,status:'succeeded',effect:'applied',...(kind==='cancel_step'?{step:{step_ref:ref.step_ref,model_request_id:ref.model_request_id},model_request_id:ref.model_request_id,cancel_connection:ref.connection,cancel_accepted:true,message:'delivered',delivery:{cancel_accepted:true,message:'delivered'}}:{work_id:ref.work_id})};
 const snapshot=()=>({protocol:'core.work.v1',organization_id:ref.organization_id,version:stage?13:12,access:{principal_id:ref.principal_id},works:kind==='start_work'&&!stage?[]:[kind==='cancel_step'?{id:ref.work_id,steps:[{...ref,status:stage?'unknown':'reserved'}]}:{id:ref.work_id,title:input.title,goal:input.goal,materials_root:input.materials_root,max_calls:3,responsible:{member_id:'member',binding_id:'binding',name:'AI'},definition:{id:'definition',version:1,connection_id:input.connection_id,tools:input.tools},mandate:{id:'mandate',version:1,active:true},materials:{available:true},budget:{max_calls:3,used:0,reserved:0},steps:[],results:[],attempts:stage>1?[{id:'attempt-original',owner_principal_id:ref.principal_id,status:'running'}]:[]}]});
 const session={status:200,body:{core_protocol:'core.au.v1',principal_id:ref.principal_id,service_instance:ref.service_instance}};
 page.evaluate=async()=>({session:structuredClone(session),current:structuredClone(session),work:{status:200,body:snapshot()},receipt:{status:200,body:{receipt:structuredClone(receipt)}}});
 page.waitForRequest=()=>new Promise(resolve=>{requestWait=resolve;});
 page.waitForResponse=predicate=>new Promise(resolve=>{responseWait={predicate,resolve};});
 const emitResponse=response=>{if(responseWait&&responseWait.predicate(response)){const {resolve}=responseWait;responseWait=null;resolve(response);}};
 page.reload=async()=>{};
 const send=async(type)=>{
  if(type==='lookup'){lookup++;const response={status:()=>200,json:async()=>({receipt:structuredClone(receipt)}),url:()=> 'http://localhost/api/v1/governance/receipts?organization_id='+ref.organization_id+'&id='+cmd.id,request:()=>({method:()=> 'GET'})};emitResponse(response);return;}
  const c=type==='start_attempt'?{id:'prepare-original',kind:'start_attempt',organization_id:ref.organization_id,base_version:13,data:{work_id:ref.work_id}}:cmd;
  const prepared={id:c.id,kind:c.kind,organization_id:ref.organization_id,base_version:13,version:14,actor_principal_id:ref.principal_id,status:'succeeded',attempt:{id:'attempt-original',status:'running',owner_principal_id:ref.principal_id}};
  const fail=type!=='start_attempt'&&['body-lost','denied-body-lost'].includes(fault);
  const status=type!=='start_attempt'&&fault==='denied-body-lost'?403:200;
  const response={url:()=> 'http://localhost/api/v1/work/commands',status:()=>status,finished:()=>fail?new Promise(()=>{}):Promise.resolve(null),json:async()=>{if(type!=='start_attempt'&&fault==='malformed')throw new SyntaxError('complete malformed JSON');return {receipt:structuredClone(type==='start_attempt'?prepared:fault==='wrong-receipt'?{...receipt,id:'wrong'}:receipt)};},request:()=>request};
  const request={method:()=> 'POST',url:()=> 'http://localhost/api/v1/work/commands',postDataJSON:()=>c,response:async()=>response,failure:()=>fail?{errorText:'net::ERR_CONTENT_LENGTH_MISMATCH'}:null};
  posts++;stage=type==='start_attempt'?2:1;page.emit('request',request);
  if(requestWait){const resolve=requestWait;requestWait=null;resolve(request);}
  setImmediate(()=>{page.emit(fail?'requestfailed':'requestfinished',request);emitResponse(response);});
 };
 const target=name=>({waitFor:async()=>{},isEnabled:async()=>true,innerText:async()=>cmd.id,fill:async()=>{},setChecked:async()=>{},getByRole:(_role,o)=>target(o.name),click:async()=>{if(name==='取消本次执行'||name==='登记 AI 工作')return send(kind);if(name==='准备本轮执行')return send('start_attempt');if(name==='查询原请求'||name==='查询登记原请求')return send('lookup');}});
 page.getByRole=(_r,o)=>target(o.name);page.getByLabel=(name)=>target(name);page.getByText=name=>target(name);page.locator=()=>target('card');
 return {page,stats:()=>({posts,lookup,listeners:page.eventNames().map(n=>[n,page.listenerCount(n)])})};
}
(async()=>{const results=[];
for(const [kind,file,fn,base] of [['cancel_step','exit22-page-cancel.cjs','cancelFromPage','b446caf2a6507f283836e9009984d49f8c93541d'],['start_work','exit22-registration-evidence.cjs','registerAndPrepare','bef1e54fca6f02a347c6954a9a13a2aa9b53cfc7']])for(const source of ['base','candidate'])for(const fault of ['normal','body-lost','denied-body-lost','malformed','wrong-receipt']){
 const h=load(file,source==='base'?base:null),{page,stats}=pageFixture(kind,fault);let timer,error,value;
 try{value=await Promise.race([kind==='cancel_step'?h[fn](page,ref):h[fn](page,ref.organization_id,input),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('BOUNDED_HANG')),150);})]);}catch(e){error=e;}finally{clearTimeout(timer);}
 const result={kind,source,fault,outcome:error?error.message:'accepted',...stats()};
 if(source==='candidate'){const accept=['normal','body-lost'].includes(fault);if(accept)assert.ifError(error);else {assert.ok(error);assert.notEqual(error.message,'BOUNDED_HANG');}assert.equal(result.posts,kind==='start_work'&&accept?2:1);assert.deepEqual(result.listeners,[]);}
 if(source==='base'){if(fault==='normal')assert.ifError(error);else if(fault.includes('body-lost'))assert.equal(error?.message,'BOUNDED_HANG');else if(kind==='start_work')assert.ifError(error);else assert.ok(error);}
 results.push(result);
}
console.log(JSON.stringify({scope:'independent synthetic Playwright event API; no HTTP/browser/model',results},null,2));})().catch(e=>{console.error(e);process.exitCode=1;});
