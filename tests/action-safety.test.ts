import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { Store, MockProvider, execute, reconcile } from '../spikes/action-safety/store.ts';
import type { Request } from '../spikes/action-safety/store.ts';
const policy = {unionId:'u1',actor:'agent:u1',version:'p1',currency:'USD',target:'mock:vendor'};
const request = (key='order1', maxMinor=60): Request => ({unionId:'u1',key,actor:'agent:u1',policyVersion:'p1',currency:'USD',target:'mock:vendor',action:'mock.purchase',maxMinor});
function fixture(t: any) {
  const dir=mkdtempSync(join(tmpdir(),'union-test-'));
  const local=join(dir,'local.sqlite'), remote=join(dir,'remote.sqlite');
  const store=new Store(local), provider=new MockProvider(remote);
  store.seed('u1','USD',100); store.seed('u2','USD',100);
  t.after(()=>{store.close();provider.close();rmSync(dir,{recursive:true,force:true});});
  return {store,provider,local,remote};
}
function child(mode: string, local: string, remote: string, key='order1', minor=60): Promise<number | null> {
  return new Promise((resolve,reject)=>{
    const p=spawn(process.execPath,[fileURLToPath(new URL('./child.ts',import.meta.url)),mode,local,remote,key,String(minor)],{stdio:['ignore','ignore','pipe']});
    let stderr='';p.stderr.on('data',d=>stderr+=d);p.on('error',reject);
    p.on('close',code=>[0,3,42].includes(code!)?resolve(code):reject(new Error(stderr || `child ${code}`)));
  });
}
test('retry uses the same reservation; changed request is rejected',t=>{
  const {store,provider}=fixture(t);
  store.reserve(request(),policy);store.reserve(request(),policy);
  assert.equal(store.budget('u1').heldMinor,60);
  assert.throws(()=>store.reserve(request('order1',61),policy),/idempotency conflict/);
  execute(store,provider,'u1','order1');execute(store,provider,'u1','order1');
  assert.equal(provider.count(),1);assert.equal(store.budget('u1').spentMinor,60);
  assert.equal(store.budget('u1').heldMinor,0);
});
test('unauthorized model actions and tenant/currency changes leave budget untouched',t=>{
  const {store,provider}=fixture(t);
  for(const patch of [{actor:'investor:u1'},{unionId:'u2'},{policyVersion:'p2'},
    {action:'budget.raise'},{action:'shell.exec'},{target:'real:bank'},{currency:'EUR'}]) {
    assert.throws(()=>store.reserve({...request(),...patch},policy),/unauthorized/);
  }
  assert.equal(store.budget('u1').heldMinor,0);assert.equal(store.budget('u2').heldMinor,0);
  assert.equal(provider.count(),0);
});
test('only positive safe integer amounts and bounded keys are accepted',t=>{
  const {store}=fixture(t);
  for(const value of [-1,0,0.1,NaN,Infinity,Number.MAX_SAFE_INTEGER+1])
    assert.throws(()=>store.reserve(request('bad',value),policy),/invalid amount/);
  for(const key of ['', ' ', 'a'.repeat(129)]) assert.throws(()=>store.reserve(request(key),policy),/invalid key/);
  assert.equal(store.budget('u1').heldMinor,0);
});
test('eight competing processes cannot exceed a 100-minor-unit hard budget',async t=>{
  const {store,local,remote}=fixture(t);
  const codes=await Promise.all(Array.from({length:8},(_,i)=>child('reserve',local,remote,`concurrent-${i}`,30)));
  assert.equal(codes.filter(x=>x===0).length,3);
  assert.equal(codes.filter(x=>x===3).length,5);
  assert.equal(store.budget('u1').heldMinor,90);assert.equal(store.budget('u2').heldMinor,0);
});
test('process crash after external success recovers by lookup without repeating the effect',async t=>{
  const {store,provider,local,remote}=fixture(t);
  assert.equal(await child('crash-after-external',local,remote),42);
  assert.equal(store.get('u1','order1')!.status,'executing');assert.equal(provider.count(),1);
  execute(store,provider,'u1','order1'); // Does not re-submit while executing.
  reconcile(store,provider,'u1','order1');reconcile(store,provider,'u1','order1');
  assert.equal(provider.count(),1);assert.equal(store.get('u1','order1')!.status,'succeeded');
  assert.equal(store.budget('u1').spentMinor,60);assert.equal(store.budget('u1').heldMinor,0);
});
test('crash before external call retains reservation when lookup is inconclusive',async t=>{
  const {store,provider,local,remote}=fixture(t);
  assert.equal(await child('crash-before-external',local,remote),42);
  reconcile(store,provider,'u1','order1');execute(store,provider,'u1','order1');
  assert.equal(provider.count(),0);assert.equal(store.get('u1','order1')!.status,'unknown');
  assert.equal(store.budget('u1').heldMinor,60);
  assert.throws(()=>store.reserve(request('next',50),policy),/budget unavailable/);
});
test('definitive failure releases reservation exactly once',t=>{
  const {store}=fixture(t);store.reserve(request(),policy);store.claim('u1','order1');
  store.finish('u1','order1',{state:'failed'});store.finish('u1','order1',{state:'failed'});
  assert.equal(store.budget('u1').heldMinor,0);assert.equal(store.budget('u1').spentMinor,0);
  assert.throws(()=>store.finish('u1','order1',{state:'succeeded',actualMinor:60}),/conflicting receipt/);
});
test('settling below maximum releases the difference and invalid receipt rolls back',t=>{
  const {store}=fixture(t);store.reserve(request(),policy);store.claim('u1','order1');
  assert.throws(()=>store.finish('u1','order1',{state:'succeeded',actualMinor:61}),/exceeds reservation/);
  assert.equal(store.budget('u1').heldMinor,60);
  assert.equal(store.get('u1','order1')!.status,'executing');
  store.finish('u1','order1',{state:'succeeded',actualMinor:40});
  assert.equal(store.budget('u1').heldMinor,0);assert.equal(store.budget('u1').spentMinor,40);
});
test('same key across test tenants remains independent',t=>{
  const {store,provider}=fixture(t);store.reserve(request(),policy);
  store.reserve({...request(),unionId:'u2',actor:'agent:u2'},{...policy,unionId:'u2',actor:'agent:u2'});
  execute(store,provider,'u1','order1');execute(store,provider,'u2','order1');
  assert.equal(provider.count(),2);assert.equal(store.budget('u1').spentMinor,60);assert.equal(store.budget('u2').spentMinor,60);
});
