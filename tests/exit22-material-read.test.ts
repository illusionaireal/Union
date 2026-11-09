import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

// Execute the driver's existing pre-delivery gate; never run its real-model main.
const source=readFileSync(new URL('../scripts/exit22c_download.cjs',import.meta.url),'utf8');
const start=source.indexOf('  const deliveryBefore = await snapshot();');
const end=source.indexOf('  const resultControls =',start);
assert.ok(start>=0 && end>start);
const block=source.slice(start,end);
const requireScript=createRequire(new URL('../scripts/exit22c_download.cjs',import.meta.url));
const document='# 合成资料\n\n原资料🧪\n';
const sha256=createHash('sha256').update(document,'utf8').digest('hex');
const result={id:'result-original',status:'candidate',sha256:'a'.repeat(64),sources:['work-original#t1']};
const original:any={protocol:'core.work.v1',organization_id:'au-original',version:12,
  access:{principal_id:'principal-original'},works:[{id:'work-original',results:[result],
    attempt_ids:[],attempts:[{id:'attempt-original'}],steps:[{step_ref:'work-original#s1',status:'used',
      attempt_id:'attempt-original',command_id:'command-original',model_request_id:'request-original'}],
    tool_calls:[{step_ref:'work-original#t1',tool:'read_document',attempt_id:'attempt-original',
      arguments:{path:'brief.md'},sha256,bytes:Buffer.byteLength(document,'utf8')}]}]};
type Change=(value:any)=>void;
async function gate(change:Change=()=>{}) {
  const read=structuredClone(original);change(read);
  const files=new Map();
  const context={require:requireScript,material:{path:'brief.md',sha256,bytes:Buffer.byteLength(document,'utf8')},
    createdReceipt:{organization_id:'au-original'},workId:'work-original',resultId:result.id,
    recorded:result.sha256,recordedFull:structuredClone(result),snapshot:async()=>read,
    check:(name:string,value:any=true)=>assert.ok(value,name),
    fs:{writeFileSync:(name:string,body:string)=>files.set(name,JSON.parse(body))},
    path:{join:(...parts:string[])=>parts.join('/')},output:'/synthetic'};
  let error;try {await vm.runInNewContext('(async()=>{'+block+'})()',context);}catch(e){error=e;}
  return {error,files};
}
test('original Unicode material receipt cited by the original candidate passes',async()=>{
  assert.ifError((await gate()).error);
});
for(const [name,change] of [
  ['no material read',(s:any)=>{s.works[0].tool_calls=[];}],
  ['listing only',(s:any)=>{s.works[0].tool_calls[0].tool='list_documents';}],
  ['another material path',(s:any)=>{s.works[0].tool_calls[0].arguments.path='other.md';}],
  ['another material digest',(s:any)=>{s.works[0].tool_calls[0].sha256='b'.repeat(64);}],
  ['character count instead of UTF-8 bytes',(s:any)=>{s.works[0].tool_calls[0].bytes=document.length;}],
  ['read not cited by candidate',(s:any)=>{s.works[0].tool_calls[0].step_ref='work-original#t2';}],
  ['duplicate receipt identity',(s:any)=>{s.works[0].tool_calls.push(structuredClone(s.works[0].tool_calls[0]));}],
  ['receipt from another attempt',(s:any)=>{s.works[0].tool_calls[0].attempt_id='attempt-other';}],
  ['unknown model outcome',(s:any)=>{s.works[0].steps[0].status='unknown';}],
  ['manual step without original request',(s:any)=>{delete s.works[0].steps[0].model_request_id;}],
] as [string,Change][]) test('pre-delivery driver rejects '+name,async()=>{
  const value=await gate(change);assert.ok(value.error,'driver accepted '+name);
  assert.equal(value.files.size,0,'no passing material evidence on failure');
});
