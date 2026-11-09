import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import test from 'node:test';
const require = createRequire(import.meta.url);
const {cancelFromPage, validateCancelCommand, validateCancelReceipt} = require('../scripts/exit22-page-cancel.cjs');
const reference = {organization_id:'au-original', work_id:'work-original', step_ref:'original#s1',
  attempt_id:'attempt-original', command_id:'run-original', model_request_id:'model-original',
  principal_id:'reader-original', service_instance:'service-original', connection:{id:'connection', revision:1}};
const command = {id:'cancel-original', kind:'cancel_step', organization_id:reference.organization_id,
  base_version:12, data:{work_id:reference.work_id, step_id:reference.step_ref}};
const receipt = {id:command.id, kind:command.kind, organization_id:command.organization_id,
  base_version:12, version:13, actor_principal_id:reference.principal_id, status:'succeeded', effect:'applied',
  step:{step_ref:reference.step_ref}, model_request_id:reference.model_request_id, cancel_accepted:true};

test('original page command and delivered original receipt are accepted', () => {
  validateCancelCommand(command, reference, 11);
  assert.equal(validateCancelReceipt({status:200, body:{receipt}}, command, reference), receipt);
});
for (const [name, change] of Object.entries({
  'empty ID':{id:''}, 'wrong kind':{kind:'run_loop'}, 'wrong AU':{organization_id:'other'},
  'wrong Work':{data:{...command.data,work_id:'other'}}, 'wrong step':{data:{...command.data,step_id:'other'}},
  'old version':{base_version:9}, 'missing version':{base_version:undefined},
})) test('page cancellation refuses '+name, () => {
  assert.throws(()=>validateCancelCommand({...command,...change},reference,11), {name:'AssertionError'});
});
for (const [name, change] of Object.entries({
  'replacement ID':{id:'other'}, 'wrong kind':{kind:'start_attempt'}, 'wrong AU':{organization_id:'other'},
  'wrong reader':{actor_principal_id:'other'}, 'rejection':{status:'rejected'}, 'unknown':{status:'unknown'},
  'not adopted':{effect:'evidence_only'}, 'different base':{base_version:11}, 'old version':{version:12},
  'wrong step':{step:{step_ref:'other'}}, 'different model request':{model_request_id:'other'},
  'delivery missing':{cancel_accepted:undefined}, 'delivery refused':{cancel_accepted:false},
})) test('original cancel lookup refuses '+name, () => {
  assert.throws(()=>validateCancelReceipt({status:200,body:{receipt:{...receipt,...change}}},command,reference), {name:'AssertionError'});
});
for (const status of [401,403,404,500]) test('HTTP '+status+' cannot certify cancellation', () => {
  assert.throws(()=>validateCancelReceipt({status,body:{receipt}},command,reference), {name:'AssertionError'});
});
for (const fault of ['principal','service','attempt','model','connection','settled']) {
  test('changed '+fault+' refuses before any page cancel', async () => {
    const session = {core_protocol:'core.au.v1',principal_id:reference.principal_id,service_instance:reference.service_instance};
    const step = {...structuredClone(reference),status:'reserved'};
    if (fault==='principal') session.principal_id='other';
    if (fault==='service') session.service_instance='other';
    if (fault==='attempt') step.attempt_id='other';
    if (fault==='model') step.model_request_id='other';
    if (fault==='connection') step.connection.revision=2;
    if (fault==='settled') step.status='unknown';
    const page = {evaluate:async()=>({session:{status:200,body:session},current:{status:200,body:session},
      work:{status:200,body:{protocol:'core.work.v1',organization_id:reference.organization_id,
        access:{principal_id:reference.principal_id},version:12,works:[{id:reference.work_id,steps:[step]}]}}}),
      locator:()=>{throw Error('must reject before locating/clicking any control');}};
    await assert.rejects(cancelFromPage(page,reference), {name:'AssertionError'});
  });
}
