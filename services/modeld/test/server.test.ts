import { afterEach, expect, test } from 'bun:test';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startService, own, type InferenceKernel } from '../src/server';

const directories: string[] = [], services: Awaited<ReturnType<typeof startService>>[] = [];
afterEach(async () => { for (const s of services.splice(0)) await s.close(); for (const d of directories.splice(0)) rmSync(d, { recursive:true, force:true }); });
async function setup(infer?: InferenceKernel['infer']) {
  const directory = mkdtempSync(join(tmpdir(), 'union-modeld-http-')); directories.push(directory);
  let calls = 0;
  const s = await startService({ directory, port:0, upstream:'controlled-test', adminToken:'a'.repeat(48), workerToken:'w'.repeat(48),
    kernel: async () => ({ accounts:async () => [{id:'account-a'}], models:async () => [{id:'model-a'}],
      connect:async () => { throw new Error('not used'); }, close:async () => {},
      infer:async (...args) => { calls++; return infer ? infer(...args) : { message:{role:'assistant',content:'controlled'},usage:{} }; } }) });
  services.push(s);
  const call = (method:string, path:string, body?:unknown, role='worker') => fetch(new URL(path,s.url), {
    method, headers:{authorization:'Bearer '+(role==='admin'?'a':'w').repeat(48),'content-type':'application/json'},
    body:body===undefined?undefined:JSON.stringify(body) });
  expect((await call('POST','/v1/grants',{id:'grant-a',au_id:'au-a',account_ref:'account-a',model_ids:['model-a']},'admin')).status).toBe(201);
  const input = {id:'run-a',run_id:'run-a',au_id:'au-a',connection_id:'connection-a',connection_revision:1,
    grant_ref:'grant-a',grant_revision:1,model_id:'model-a',messages:[{role:'user',content:'controlled test'}],tools:[],
    generation:{maxOutputTokens:10},deadlines:{first_event_ms:1000,idle_ms:1000,task_ms:3000}};
  return { s, call, input, directory, calls:() => calls };
}
async function terminal(call:any) {
  for (let n=0;n<100;n++) {
    const row = await (await call('GET','/v1/requests/run-a?au_id=au-a')).json();
    if (['completed','failed','interrupted'].includes(row.state)) return row;
    await Bun.sleep(10);
  }
  throw new Error('request did not finish');
}
test('one accepted POST is durable, repeat lookup never starts a second inference; roles and AU are isolated', async () => {
  const {call,input,calls,directory} = await setup();
  expect(() => own(directory)).toThrow('already_running');
  expect((await call('GET','/v1/accounts')).status).toBe(403);
  expect((await call('POST','/v1/requests',input,'admin')).status).toBe(403);
  expect((await call('POST','/v1/requests',{...input,au_id:'au-b'})).status).toBe(403);
  expect((await call('POST','/v1/requests',input)).status).toBe(202);
  expect((await terminal(call)).state).toBe('completed');
  await call('POST','/v1/requests',input);
  expect(calls()).toBe(1);
  expect((await call('GET','/v1/requests/run-a?au_id=au-b')).status).toBe(404);
  expect((await call('POST','/v1/requests',{...input,generation:{maxOutputTokens:0}})).status).toBe(400);
});
test('cancel and grant revocation fence late tool results without claiming remote cancellation', async () => {
  let finish: (()=>void) | undefined;
  const {call,input,s} = await setup(async (_account,_input,_signal,event) => {
    event('text_delta',{text:'partial'});
    await new Promise<void>(r => { finish=r; });
    return {message:{role:'assistant',tool_calls:[{id:'late'}]}};
  });
  await call('POST','/v1/requests',input);
  while (!finish) await Bun.sleep(5);
  await call('POST','/v1/grants/grant-a/revoke',{revision:1},'admin');
  finish();
  const row = await terminal(call);
  expect(row.state).toBe('interrupted'); expect(row.action_authorized).toBe(false);
  expect(row.result).toEqual({ message: { role: 'assistant', tool_calls: [{ id: 'late' }] } });
  expect(s.journal.events(input.id,input.au_id,0).some(e=>e.type==='text_delta')).toBe(true);
  expect((await call('POST','/v1/requests',{...input,id:'run-b',run_id:'run-b'})).status).toBe(403);
});
