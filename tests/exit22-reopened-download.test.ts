import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

// Execute the complete real restart tail, never its real-model main.
const source = readFileSync(new URL('../scripts/exit22c_download.cjs', import.meta.url), 'utf8');
const start = '  const authenticatedAfter = await snapshot();';
const end = "  fs.writeFileSync(path.join(output, 'checks.json'),";
assert.equal(source.split(start).length, 2);
assert.ok(source.indexOf(end, source.indexOf(start)) > source.indexOf(start));
const block = source.slice(source.indexOf(start), source.indexOf(end));
const requireScript = createRequire(new URL('../scripts/exit22c_download.cjs', import.meta.url));
const content = '原成果🧪\n';
const result = { id: 'result-original', title: '原成果', status: 'adopted',
  sha256: createHash('sha256').update(content, 'utf8').digest('hex'),
  bytes: Buffer.byteLength(content, 'utf8'), sources: ['work-original#s1'] };
const original = { protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
  access: { principal_id: 'principal-original' }, works: [{ id: 'work-original',
    status: 'delivered', delivered_result_id: result.id, results: [result],
    budget: { max_calls: 3, used: 1, reserved: 0 }, steps: [{ step_ref: 'work-original#s1',
      attempt_id: 'attempt-original', command_id: 'command-original', model_request_id: 'request-original',
      status: 'used', usage: null, cost_status: 'unknown', reason: 'complete', connection: {id:'connection-original'} }] }] };

type Fault = (value: any) => void;
async function reopen(change: Fault = () => {}, sessionChange: Fault = () => {}) {
  const response = {status: 200, body: {protocol: 'core.work.v1', organization_id: 'au-original',
    work_id: 'work-original', result: structuredClone(result), content}};
  change(response);
  const urls: string[] = [], files = new Map();
  let sessions = 0;
  const fetch = async (url: string, init?: any) => {
    assert.ok(!init?.method || init.method === 'GET', 'observation is read-only');
    urls.push(url);
    if (url === '/api/session') {
      const value = {status:200, body:{core_protocol:'core.au.v1',
        principal_id:'principal-original', service_instance:'new-service-after-restart'}};
      if (++sessions === 2) sessionChange(value);
      return {status:value.status, json:async () => value.body};
    }
    const parsed = new URL(url, 'http://localhost');
    assert.equal(parsed.pathname, '/api/v1/work/results');
    assert.equal(parsed.searchParams.get('organization_id'), 'au-original');
    assert.equal(parsed.searchParams.get('work_id'), 'work-original');
    assert.equal(parsed.searchParams.get('id'), result.id);
    return {status:response.status, json:async () => response.body};
  };
  const context = { require:requireScript, workId:'work-original', resultId:result.id,
    recorded:result.sha256, createdReceipt:{organization_id:'au-original'}, before:structuredClone(original),
    page:{evaluate:async (fn: any, arg:any) => vm.runInNewContext('(' + fn.toString() + ')(arg)', {fetch,arg,encodeURIComponent})},
    snapshot:async () => structuredClone(original), check:(name:string, value:any = true) => assert.ok(value,name),
    fs:{writeFileSync:(name:string,body:string) => files.set(name,JSON.parse(body))},
    path:{join:(...parts:string[]) => parts.join('/')}, output:'/synthetic' };
  let error;
  try { await vm.runInNewContext('(async () => {' + block + '})()', context); }
  catch (value) { error = value; }
  return {error,urls,files};
}

test('original Unicode result and unchanged snapshots survive a service restart', async () => {
  const value = await reopen(); assert.ifError(value.error);
  assert.equal(value.urls.length, 3, 'one original result GET between current session reads');
  const evidence = value.files.get('/synthetic/result-body-after-restart.json');
  assert.equal(evidence.sha256, result.sha256);
  assert.equal(evidence.bytes, result.bytes);
  assert.equal(Object.hasOwn(evidence, 'content'), false, 'public evidence contains no body');
});
for (const [name, change] of [
  ['missing body', (v:any) => {delete v.body.content;}],
  ['corrupted body with unchanged metadata', (v:any) => {v.body.content += 'changed';}],
  ['HTTP 403 with an otherwise matching body', (v:any) => {v.status=403;}],
  ['HTTP 500 with an otherwise matching body', (v:any) => {v.status=500;}],
  ['another AU', (v:any) => {v.body.organization_id='au-other';}],
  ['another Work', (v:any) => {v.body.work_id='work-other';}],
  ['another result', (v:any) => {v.body.result.id='result-other';}],
  ['another protocol', (v:any) => {v.body.protocol='error.v1';}],
  ['changed sources', (v:any) => {v.body.result.sources=['other'];}],
  ['changed title', (v:any) => {v.body.result.title='other';}],
  ['character count instead of UTF-8 bytes', (v:any) => {v.body.result.bytes=content.length;}],
] as [string,Fault][]) test('reopened download rejects ' + name, async () => {
  const value = await reopen(change); assert.ok(value.error, 'driver must reject ' + name);
  assert.equal(value.files.size, 0, 'do not record successful restart after a failed body read');
});
for (const [name, change] of [
  ['session revoked after body GET', (v:any) => {v.status=401;}],
  ['principal changed during body GET', (v:any) => {v.body.principal_id='other';}],
  ['service changed during body GET', (v:any) => {v.body.service_instance='other';}],
] as [string,Fault][]) test(name, async () => {
  const value = await reopen(undefined, change); assert.ok(value.error, name);
  assert.equal(value.files.size, 0);
});
