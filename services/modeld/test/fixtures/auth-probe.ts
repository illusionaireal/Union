// Fixed OAuth implementation with an entirely intercepted HTTP client. No network.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { Kernel } from '../../src/kernel';
const directory=mkdtempSync(join(tmpdir(),'union-modeld-auth-test-'));
const original=globalThis.fetch;
let codeRequests=0, tokenRequests=0;
globalThis.fetch=Object.assign(async (input:any,init?:any) => {
  const req=new Request(input,init), path=new URL(req.url).pathname;
  if(path.endsWith('/auth/device/code')) {
    codeRequests++;
    return Response.json({device_code:'controlled-device-secret',user_code:'TEST-CODE',verification_uri_complete:'https://example.invalid/device',expires_in:60,interval:0});
  }
  if(path.endsWith('/auth/device/token')) {
    tokenRequests++;
    assert.equal((await req.json() as any).device_code,'controlled-device-secret');
    return Response.json({access_token:'controlled-access',refresh_token:'controlled-refresh',expires_in:3600,org_id:'test-org'});
  }
  if(path.endsWith('/api/user')) return Response.json({id:'test-user',email:'controlled@example.invalid'});
  if(path.endsWith('/api/orgs')) return Response.json([{id:'test-org',name:'Controlled workspace'}]);
  throw new Error('Network forbidden by authentication test');
}, {preconnect:original.preconnect});
let kernel:Kernel|undefined;
try {
  kernel=await Kernel.create(directory);
  const flow=await kernel.connect();
  assert.ok(flow.attempt.attempt_id);
  assert.equal(flow.attempt.instructions,'Enter code: TEST-CODE');
  await flow.complete();
  const accounts=await kernel.accounts();
  assert.equal(accounts.length,1);
  assert.equal(accounts[0].workspace,'Controlled workspace');
  assert.ok(!JSON.stringify(accounts).includes('controlled-access'));
  await flow.complete();
  assert.equal(codeRequests,1);assert.equal(tokenRequests,1);
  console.log(JSON.stringify({auth_completed:true,device_requests:codeRequests,token_requests:tokenRequests,real_model_calls:0}));
} finally {
  if(kernel)await kernel.close();globalThis.fetch=original;rmSync(directory,{recursive:true,force:true});
}
