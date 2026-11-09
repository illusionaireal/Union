import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';
const {validateReceipt,validateRegistered}=createRequire(import.meta.url)('../scripts/exit22-registration-evidence.cjs');

const scope={organization_id:'au-original',principal_id:'principal-original',service_instance:'service-original'};
const input={title:'登记目标',goal:'读取授权资料',member_name:'AI成员',materials_root:'docs',max_calls:3,
  tools:['read_document','list_documents'],connection_id:'connection-original',expected_revision:1};
function fixture() {
  const command={id:'registration-original',kind:'start_work',organization_id:scope.organization_id,base_version:12,
    data:{...input,work_id:'work-generated',member_id:'member-generated',binding_id:'binding-generated',
      definition_id:'definition-generated',mandate_id:'mandate-generated'}};
  const receipt={id:command.id,kind:command.kind,organization_id:scope.organization_id,base_version:12,
    actor_principal_id:scope.principal_id,status:'succeeded',version:13,work_id:command.data.work_id};
  const work={id:command.data.work_id,title:input.title,goal:input.goal,materials_root:input.materials_root,max_calls:3,
    responsible:{member_id:command.data.member_id,binding_id:command.data.binding_id,name:input.member_name},
    definition:{id:command.data.definition_id,version:1,connection_id:input.connection_id,tools:[...input.tools]},
    mandate:{id:command.data.mandate_id,version:1,active:true},materials:{available:true},
    budget:{max_calls:3,reserved:0,used:0},attempts:[],steps:[],results:[]};
  const read={protocol:'core.work.v1',organization_id:scope.organization_id,access:{principal_id:scope.principal_id},works:[work]};
  return {command,receipt,work,read};
}
test('original registered Work and receipt remain verifiable without starting any model',()=>{
  const {command,receipt,read}=fixture();
  assert.equal(validateReceipt({status:200,body:{receipt}},command,scope),receipt);
  assert.equal(validateRegistered(read,command,scope,input).id,command.data.work_id);
});
for(const [key,value] of Object.entries({id:'replacement',kind:'deliver_work',organization_id:'another-au',
  base_version:11,actor_principal_id:'other-principal',status:'unknown',version:11,work_id:'different-work'}))
  test('registration cannot accept a substituted receipt: '+key,()=>{
    const {command,receipt}=fixture();assert.throws(()=>validateReceipt({status:200,body:{receipt:{...receipt,[key]:value}}},command,scope));
  });
for(const status of [401,403,404,500])test('unreadable original receipt stops at HTTP '+status,()=>{
  const {command,receipt}=fixture();assert.throws(()=>validateReceipt({status,body:{receipt}},command,scope));
});
const mutations: Record<string,(f:ReturnType<typeof fixture>)=>void>={
  'substituted Work':f=>{f.work.id='replacement';},
  'wrong responsibility':f=>{f.work.responsible.member_id='replacement';},
  'wrong binding':f=>{f.work.responsible.binding_id='replacement';},
  'wrong definition':f=>{f.work.definition.id='replacement';},
  'wrong mandate':f=>{f.work.mandate.id='replacement';},
  'withdrawn mandate':f=>{f.work.mandate.active=false;},
  'wrong goal':f=>{f.work.goal='changed';},
  'changed budget':f=>{f.work.budget.max_calls=30;},
  'preexisting use':f=>{f.work.budget.used=1;},
  'unknown reservation':f=>{f.work.budget.reserved=1;},
  'another Work':f=>{f.read.works.push(structuredClone(f.work));},
  'wrong reader':f=>{f.read.access.principal_id='other';},
  'missing read_document':f=>{f.work.definition.tools=['list_documents'];},
  'different connection':f=>{f.command.data.connection_id='other';f.work.definition.connection_id='other';},
  'changed adopted revision':f=>{f.command.data.expected_revision=2;},
};
for(const [name,mutate] of Object.entries(mutations))test('persisted registration rejects '+name,()=>{
  const f=fixture();mutate(f);assert.throws(()=>validateRegistered(f.read,f.command,scope,input));
});
