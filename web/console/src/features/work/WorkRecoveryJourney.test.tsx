import {fireEvent,screen} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {fixture,mount} from '../models/test-fixtures';
import {api} from '../../api/client';
import type {CoreWork} from '../../api/types';

let state:ReturnType<typeof fixture>;
let read:CoreWork;
let requests:Record<string,unknown>[];
const receipts=new Map<string,unknown>();
beforeEach(()=>{
  state=fixture(); requests=[];receipts.clear();
  read={protocol:'core.work.v1',organization_id:'core-au',version:12,
    access:{principal_id:state.session.principal_id!,can_start:true,can_manage_results:true},
    capabilities:{work_registration:true,execution:'available',autonomous_business:false},works:[{
      id:'work-original',title:'原工作',goal:'继续原资料研究',status:'running',version:1,max_calls:2,materials_root:'project-docs',created_at:'',
      responsible:{member_id:'member-one',name:'研究成员',binding_id:'binding-one',duty:'研究'},
      definition:{id:'definition-one',version:1,connection_id:'connection-one',model:'controlled-model',tools:['read_document']},
      mandate:{id:'mandate-one',version:1,actions:['read_document'],active:true},attempt_ids:[],result_ids:[],tool_calls:[],steps:[],
      budget:{max_calls:2,reserved:1,used:0},materials:{reference:'project-docs',available:true,documents:1},results:[],
      attempts:[Object.assign({id:'work-original#a1',seq:1,status:'running' as const,outcome:null,started_at:'',ended_at:null,stale:true},
        {execution_owner:{instance:'old-service',epoch:1},recovery:{eligible:true,reason:'原服务已结束，可恢复同一次执行'}})]}]};
  vi.spyOn(api,'coreWork').mockImplementation(async()=>structuredClone(read));
  vi.spyOn(api,'coreWorkCommand').mockImplementation(async request=>{
    requests.push(request);read.version++;state.core.au.version=read.version;
    const receipt={id:String(request.id),kind:request.kind,organization_id:'core-au',base_version:request.base_version,
      actor_principal_id:state.session.principal_id,status:'succeeded',version:read.version,
      work_id:'work-original',attempt_id:'work-original#a1',execution_owner:{instance:state.session.service_instance,epoch:2},
      message:'原恢复意图已采用，实际执行仍按原请求核对'};
    receipts.set(String(request.id),receipt);return {receipt};
  });
  vi.spyOn(api,'coreWorkReceipt').mockImplementation(async(_,id)=>({receipt:receipts.get(id)}));
});

async function open(){
  mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button',{name:'恢复原执行'}));
  fireEvent.change(screen.getByLabelText('恢复依据'),{target:{value:'接回同一责任和已保存进度'}});
  return screen.getByRole('button',{name:'确认恢复原执行'});
}

it('recovers the original attempt through one scoped command without manual finish/start',async()=>{
  fireEvent.click(await open());
  await screen.findByText('原恢复意图已采用，实际执行仍按原请求核对');
  expect(requests).toHaveLength(1);expect(requests[0].kind).toBe('recover_work');
  expect(requests[0].data).toEqual({work_id:'work-original',attempt_id:'work-original#a1',reason:'接回同一责任和已保存进度'});
  expect(JSON.stringify(sessionStorage)).not.toContain('接回同一责任');
});

it('keeps unknown recovery as an original-ID query rather than resending after refresh',async()=>{
  const send=vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async r=>{await send(r);throw new Error('lost recovery response');});
  fireEvent.click(await open());await screen.findByRole('button',{name:'查询恢复原请求'});
  const original=String(requests[0].id);
  fireEvent.click(screen.getByRole('button',{name:'查询恢复原请求'}));
  await screen.findByText('原恢复意图已采用，实际执行仍按原请求核对');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('core-au',original);expect(requests).toHaveLength(1);
});

it('loads only original recovery metadata after service restart and explicitly queries the original ID',async()=>{
  const send=vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async r=>{await send(r);throw new Error('lost recovery response');});
  const view=mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button',{name:'恢复原执行'}));
  fireEvent.change(screen.getByLabelText('恢复依据'),{target:{value:'不丢原执行'}});
  fireEvent.click(screen.getByRole('button',{name:'确认恢复原执行'}));await screen.findByRole('button',{name:'查询恢复原请求'});
  const original=String(requests[0].id);view.view.unmount();state.session.service_instance='restarted-service';
  state.core.access.service_instance=state.session.service_instance;
  state.read.access.service_instance=state.session.service_instance;
  mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button',{name:'查询恢复原请求'}));
  await screen.findByText('原恢复意图已采用，实际执行仍按原请求核对');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('core-au',original);expect(requests).toHaveLength(1);
});

it('rejects changed owner or eligibility before any recovery POST',async()=>{
  const confirm=await open();
  Object.assign(read.works[0].attempts[0],{execution_owner:{instance:'other',epoch:3},recovery:{eligible:false,reason:'已有当前执行'}});
  fireEvent.click(confirm);
  await screen.findByText(/原执行所有者或恢复资格已变化/);expect(requests).toHaveLength(0);
});

it('rejects a successful receipt owned by a foreign service while keeping the original query',async()=>{
  const send=vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request=>{
    const reply=await send(request) as {receipt:Record<string,unknown>};
    reply.receipt.execution_owner={instance:'foreign-host',epoch:2};
    return reply as never;
  });
  fireEvent.click(await open());
  await screen.findByText(/回执与原请求不匹配/);
  expect(screen.queryByRole('button',{name:'继续核对原请求'})).toBeNull();
  expect(screen.getByRole('button',{name:'查询恢复原请求'})).toBeEnabled();
});

it('clears the recovery draft and original-work content on current permission loss',async()=>{
  await open();
  vi.mocked(api.coreWorkCommand).mockRejectedValue(Object.assign(new Error('not permitted'),{status:403}));
  fireEvent.click(screen.getByRole('button',{name:'确认恢复原执行'}));
  await screen.findByRole('alert');expect(screen.queryByLabelText('恢复依据')).toBeNull();
  expect(screen.queryByRole('heading',{name:'原工作'})).toBeNull();
});

it('allows explicit recovery after re-login when the original POST was directly denied before acceptance',async()=>{
  const send=vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async r=>{requests.push(r);throw Object.assign(new Error('not permitted'),{status:403});});
  const view=mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button',{name:'恢复原执行'}));
  fireEvent.change(screen.getByLabelText('恢复依据'),{target:{value:'第一次请求'}});
  fireEvent.click(screen.getByRole('button',{name:'确认恢复原执行'}));
  await screen.findByRole('alert');const original=String(requests[0].id);view.view.unmount();
  vi.mocked(api.coreWorkCommand).mockImplementation(send);
  mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button',{name:'继续核对原请求'}));
  fireEvent.change(screen.getByLabelText('恢复依据'),{target:{value:'重新登录后明确恢复'}});
  fireEvent.click(screen.getByRole('button',{name:'确认恢复原执行'}));
  await screen.findByText('原恢复意图已采用，实际执行仍按原请求核对');
  expect(requests).toHaveLength(2);expect(requests[1].id).not.toBe(original);
  expect(JSON.stringify(sessionStorage)).toContain(original);
});
