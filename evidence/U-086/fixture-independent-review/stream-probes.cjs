// Independent exact-fragment checks, not Bun/kernel or real-model execution.
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {createHash} = require('node:crypto');
const {stripTypeScriptTypes} = require('node:module');
const FIX = '563882e6fee67a96bbd617808f06488f8a02d7c7';
const COMBO = '23ad59e4335a14d30d02fa19ce3f3cd7ee5393a2';
const file = 'services/modeld/test/fixtures/secret-boundaries-probe.ts';
const source = sha => execFileSync('git',['show',`${sha}:${file}`],{encoding:'utf8'});
const text = source(FIX);
assert.equal(text,source(COMBO));
const start = "  if (scenario === 'ordinary') {";
const end = "  return new Response(chunks.map(frame).join('')";
assert.equal(text.split(start).length,2);
assert.equal(text.split(end).length,2);
const fragment = text.slice(text.indexOf(start),text.indexOf(end));
const create = new Function('return '+stripTypeScriptTypes(
  '(function(scenario,chunks,frame,setTimeout,clearTimeout){'+fragment+'})'))();
const frame = data => 'data: '+JSON.stringify(data)+'\n\n';
const chunks = [{choices:[{delta:{content:'safe ordinary answer'}}]},
  {choices:[{delta:{},finish_reason:'stop'}]}, {choices:[],usage:{prompt_tokens:13,completion_tokens:7}}];
const checks=[];
const check = (label,value) => {assert.ok(value,label);checks.push(label)};
async function readWithDeadline(reader,ms) {
  let timer;
  try {return await Promise.race([reader.read(),new Promise((_,reject)=>{
    timer=setTimeout(()=>reject(Error('controlled idle deadline')),ms);
  })]);} finally {clearTimeout(timer)}
}
async function main() {
  assert.match(text,/first_event_ms: 5000, idle_ms: 5000, task_ms: 15000/);
  assert.match(text,/performance\.now\(\) \+ 20000/);
  check('bounded fixture deadlines retained',true);
  let reader=create('ordinary',chunks,frame,setTimeout,clearTimeout).body.getReader();
  const first=await reader.read();
  check('safe first chunk arrives before delayed finish',new TextDecoder().decode(first.value)===frame(chunks[0]));
  await assert.rejects(readWithDeadline(reader,1000),/controlled idle deadline/);
  check('old 1000ms idle cannot accept the delayed finish',true);
  await reader.cancel();
  reader=create('ordinary',chunks,frame,setTimeout,clearTimeout).body.getReader();
  await reader.read();
  const started=performance.now(),last=await readWithDeadline(reader,5000);
  check('exact fixture delays final frame at least 1.1s',performance.now()-started>=1100);
  check('5000ms permits original finish and usage intact',
    new TextDecoder().decode(last.value)===chunks.slice(1).map(frame).join('')+'data: [DONE]\n\n');
  check('stream closes without another frame',(await reader.read()).done);
  let scheduled,cleared=0,fired=0;
  const trackedSet=(fn,ms)=>(scheduled=setTimeout(()=>{fired++;fn()},ms));
  const trackedClear=timer=>{assert.equal(timer,scheduled);cleared++;clearTimeout(timer)};
  reader=create('ordinary',chunks,frame,trackedSet,trackedClear).body.getReader();
  await reader.read();await reader.cancel();
  await new Promise(resolve=>setTimeout(resolve,1300));
  check('cancel clears the exact outstanding timer',cleared===1&&fired===0);
  console.log(JSON.stringify({fixture:FIX,combination:COMBO,node:process.version,
    source_sha256:createHash('sha256').update(text).digest('hex'),passed:checks.length,checks,
    scope:'Exact ordinary ReadableStream fragment only; no Bun/kernel execution, sockets or real model calls'},null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1});
