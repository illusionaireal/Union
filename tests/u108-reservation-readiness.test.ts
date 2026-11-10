import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import test from 'node:test';
const {waitForOriginalReservation}=createRequire(import.meta.url)('../scripts/u108-work-events-browser.cjs');

const command={id:'original',kind:'run_loop',organization_id:'au-a',data:{work_id:'work-a'}};
const step={command_id:'original-t1',status:'reserved',step_ref:'work-a#s1',attempt_id:'work-a#a1',model_request_id:'model-a'};
const snapshot=(steps:unknown[]=[],reserved=0)=>({protocol:'core.work.v1',organization_id:'au-a',
  works:[{id:'work-a',steps,budget:{reserved}}]});

test('waits through the pre-reservation snapshot and returns the same original step',async()=>{
  const values=[snapshot(),snapshot(),snapshot([step],1)];
  const deadlines:number[]=[];
  const found=await waitForOriginalReservation(async remaining=>{deadlines.push(remaining);return values.shift();},
    command,{timeout:1000,interval:1});
  assert.equal(found,step);assert.equal(deadlines.length,3);
  assert.ok(deadlines.every(x=>x>0&&x<=1000));
});

test('does not accept a different work, command, settled step or missing occupied budget',async()=>{
  const otherWork=snapshot([step],1);otherWork.works[0].id='other-work';
  const values=[otherWork,snapshot([{...step,command_id:'other-t1'}],1),
    snapshot([{...step,status:'used'}],1),snapshot([step],0),snapshot([step],1)];
  let reads=0;
  assert.equal(await waitForOriginalReservation(async()=>{reads++;return values.shift();},command,
    {timeout:1000,interval:1}),step);
  assert.equal(reads,5);
});

test('an already committed original reservation succeeds with one read',async()=>{
  let reads=0;
  assert.equal(await waitForOriginalReservation(async()=>{reads++;return snapshot([step],1);},command),step);
  assert.equal(reads,1);
});

test('a reservation that never appears fails within the bounded polling window',async()=>{
  let reads=0;
  await assert.rejects(waitForOriginalReservation(async()=>{reads++;return snapshot();},command,
    {timeout:25,interval:1}),/not observed before deadline/);
  const stoppedAt=reads;await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(reads,stoppedAt);assert.ok(reads>0);
});

for(const field of ['protocol','organization_id']) test('rejects changed read scope: '+field,async()=>{
  let reads=0;
  await assert.rejects(waitForOriginalReservation(async()=>{reads++;return {...snapshot([step],1),[field]:'wrong'};},
    command),/reservation read/);
  assert.equal(reads,1);
});

test('read failure stops immediately without polling or replacing the command',async()=>{
  let reads=0;
  await assert.rejects(waitForOriginalReservation(async()=>{reads++;throw Error('HTTP 403');},command),/HTTP 403/);
  assert.equal(reads,1);assert.equal(command.id,'original');
});
