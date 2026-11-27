import {act, fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {createHash, webcrypto} from 'node:crypto';
import {Blob as NodeBlob} from 'node:buffer';
import {fixture, mount, json} from '../models/test-fixtures';
import {api} from '../../api/client';
import type {CoreWork, CoreWorkItem, CoreWorkResult} from '../../api/types';

let state: ReturnType<typeof fixture>;
let read: CoreWork;
let responses: Record<string, {content: string; result: CoreWorkResult}>;
let downloads: Blob[];
const content = '公开测试正文\n<script>window.resultExecuted=true</script>\n研究结论：保留原来源。';
function result(body = content): CoreWorkResult {
  return {id:'same-result',seq:1,title:'研究报告',sha256:createHash('sha256').update(body).digest('hex'),
    bytes:Buffer.byteLength(body),sources:['step-1'],status:'candidate',created_at:'2026-11-26T00:00:00Z',adopted_at:null};
}
function work(id: string, body = content): CoreWorkItem {
  const r=result(body);
  return {id,title:id==='work-a'?'甲工作':'乙工作',goal:'研究授权资料',status:'pending',version:1,max_calls:2,
    materials_root:null,created_at:'2026-11-26T00:00:00Z',responsible:{member_id:'m1',name:'研究成员',binding_id:'b1',duty:'研究'},
    definition:{id:'d1',version:1,connection_id:'c1',model:'controlled-model',tools:['read_document']},
    mandate:{id:'ma1',version:1,actions:['read_document'],active:true},attempt_ids:['a1'],result_ids:[r.id],
    attempts:[],steps:[{seq:1,step_ref:'step-1',attempt_id:'a1',purpose:'work',status:'used',at:'2026-11-26T00:00:00Z'}],
    tool_calls:[],budget:{max_calls:2,reserved:0,used:1},materials:{reference:null,available:false,documents:0},results:[r]};
}
beforeEach(() => {
  state=fixture(); downloads=[];
  vi.stubGlobal('crypto',webcrypto);vi.stubGlobal('Blob',NodeBlob);
  read={protocol:'core.work.v1',organization_id:'core-au',version:12,
    access:{principal_id:state.session.principal_id!,can_start:true,can_manage_results:true},
    works:[work('work-a'),work('work-b','乙工作自己的成果')],capabilities:{work_registration:true,execution:'available',autonomous_business:false}};
  responses=Object.fromEntries(read.works.map(w=>[w.id,{content:w.id==='work-a'?content:'乙工作自己的成果',result:w.results[0]}]));
  vi.spyOn(api,'coreWork').mockImplementation(async ()=>structuredClone(read));
  const original=vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async (path,init)=>{
    const u=new URL(String(path),'http://localhost');
    if(u.pathname==='/api/v1/work/results') {
      const id=u.searchParams.get('work_id')!;const response=responses[id];
      return response?json({protocol:'core.work.v1',organization_id:'core-au',work_id:id,...structuredClone(response)}):json({error:'没有此成果'},400);
    }
    return original(path,init);
  });
  Object.defineProperty(URL,'createObjectURL',{configurable:true,value:vi.fn((blob:Blob)=>{downloads.push(blob);return 'blob:result-download';})});
  Object.defineProperty(URL,'revokeObjectURL',{configurable:true,value:vi.fn()});
  vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
});
afterEach(()=>vi.unstubAllGlobals());

it('lists the same result ID in two Works with separate full identity links',async()=>{
  mount('/au/core-au/results');
  const links=await screen.findAllByRole('link',{name:'阅读与下载'});
  expect(links.map(x=>x.getAttribute('href'))).toEqual([
    '/au/core-au/work/work-a/results/same-result','/au/core-au/work/work-b/results/same-result']);
  expect(screen.getAllByText('候选')).toHaveLength(2);
});

it('reads escaped body, version and source in the original Work, then downloads text with fresh authorization',async()=>{
  mount('/au/core-au/work/work-a/results/same-result');
  const body=await screen.findByLabelText('成果正文');expect(body.textContent).toBe(content);
  expect(body.querySelector('script')).toBeNull();expect(screen.getByText(/版本 1/)).toBeVisible();
  expect(screen.getByRole('link',{name:'返回原工作'})).toHaveAttribute('href','/au/core-au/work/work-a');
  expect(screen.getByText(/step-1/)).toBeVisible();
  const before=vi.mocked(api.session).mock.calls.length;
  fireEvent.click(screen.getByRole('button',{name:'下载正文'}));
  await waitFor(()=>expect(downloads).toHaveLength(1));
  expect(vi.mocked(api.session).mock.calls.length).toBeGreaterThan(before);
  expect(await downloads[0].text()).toBe(content);expect(downloads[0].type).toMatch(/^text\/plain/);
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:result-download');
  expect(state.commands).toEqual([]);
});

it('opens the other Work directly without reading the first Work body',async()=>{
  mount('/au/core-au/work/work-b/results/same-result');
  expect((await screen.findByLabelText('成果正文')).textContent).toBe('乙工作自己的成果');
  const reads=vi.mocked(fetch).mock.calls.filter(([p])=>String(p).startsWith('/api/v1/work/results'));
  expect(reads.every(([p])=>String(p).includes('work_id=work-b'))).toBe(true);
});

it('displays the input coverage of the saved result rather than the newer Work cursor',async()=>{
  Object.assign(read.works[0],{input_cursor:3});
  Object.assign(read.works[0].results[0],{input_cursor:1,input_refs:['input-original'],input_step_ref:'step-1'});
  mount('/au/core-au/work/work-a/results/same-result');
  await screen.findByLabelText('成果正文');
  expect(screen.getByText('采用至输入 1')).toBeVisible();
  expect(screen.getByText(/原步骤 step-1 · 本步附入 input-original/)).toBeVisible();
});

it('distinguishes adopted and this delivered version without marking unrelated versions delivered',async()=>{
  const w=read.works[0];w.status='delivered';
  Object.assign(w,{delivered_result_id:'same-result',delivered_at:'2026-11-26T01:00:00Z'});
  Object.assign(w.results[0],{status:'adopted',adopted_at:'2026-11-26T00:30:00Z',adopted_by_principal_id:state.session.principal_id});
  mount('/au/core-au/work/work-a/results/same-result');
  await screen.findByLabelText('成果正文');expect(screen.getByText('已交付')).toBeVisible();
  expect(screen.getByText('已采用')).toBeVisible();expect(screen.getByText(new RegExp(state.session.principal_id!))).toBeVisible();
});

it('rejects a missing Work rather than choosing another matching result ID',async()=>{
  mount('/au/core-au/work/missing-work/results/same-result');
  expect(await screen.findByRole('alert')).toHaveTextContent('指定工作或成果不存在');
  expect(screen.queryByLabelText('成果正文')).toBeNull();
  expect(vi.mocked(fetch).mock.calls.filter(([p])=>String(p).startsWith('/api/v1/work/results'))).toHaveLength(0);
});

it('rejects a mismatched digest and never exposes or downloads corrupted body',async()=>{
  responses['work-a'].content='损坏且不可泄露的正文';
  mount('/au/core-au/work/work-a/results/same-result');
  expect(await screen.findByRole('alert')).toHaveTextContent(/摘要|校验/);
  expect(screen.queryByText('损坏且不可泄露的正文')).toBeNull();expect(screen.queryByLabelText('成果正文')).toBeNull();
  expect(screen.queryByRole('button',{name:'下载正文'})).toBeNull();
});

it('clears content when a refreshed read is explicitly forbidden',async()=>{
  mount('/au/core-au/work/work-a/results/same-result');await screen.findByLabelText('成果正文');
  const old=vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async(p,i)=>String(p).startsWith('/api/v1/work/results')?json({error:'成果读取权限已撤销'},403):old(p,i));
  fireEvent.click(screen.getByRole('button',{name:'刷新成果'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('成果读取权限已撤销');
  expect(screen.queryByLabelText('成果正文')).toBeNull();expect(downloads).toHaveLength(0);
});

it('cancels a delayed body when the service identity changes',async()=>{
  const old=vi.mocked(fetch).getMockImplementation()!;let release:(r:Response)=>void=()=>{};
  vi.mocked(fetch).mockImplementation((p,i)=>String(p).startsWith('/api/v1/work/results')?
    new Promise(resolve=>{release=resolve;}):old(p,i));
  mount('/au/core-au/work/work-a/results/same-result');
  await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([p])=>String(p).startsWith('/api/v1/work/results'))).toBe(true));
  state.session.service_instance='replacement-service';fireEvent.focus(window);
  await waitFor(()=>expect(vi.mocked(api.session).mock.calls.length).toBeGreaterThan(1));
  await act(async()=>release(json({protocol:'core.work.v1',organization_id:'core-au',work_id:'work-a',...responses['work-a']})));
  expect(screen.queryByLabelText('成果正文')).toBeNull();expect(downloads).toHaveLength(0);
});

it('refuses a download after session identity changes and clears the old text',async()=>{
  mount('/au/core-au/work/work-a/results/same-result');await screen.findByLabelText('成果正文');
  state.session.service_instance='replacement-service';
  fireEvent.click(screen.getByRole('button',{name:'下载正文'}));
  expect(await screen.findByRole('alert')).toHaveTextContent(/身份|服务/);
  expect(screen.queryByLabelText('成果正文')).toBeNull();expect(downloads).toHaveLength(0);
  expect(screen.queryByRole('heading',{name:'研究报告'})).toBeNull();
});

it('refreshes adoption metadata with the body rather than trapping the user on an old candidate',async()=>{
  mount('/au/core-au/work/work-a/results/same-result');await screen.findByLabelText('成果正文');
  Object.assign(read.works[0].results[0],{status:'adopted',adopted_at:'2026-11-26T01:00:00Z',adopted_by_principal_id:state.session.principal_id});
  fireEvent.click(screen.getByRole('button',{name:'刷新成果'}));
  expect(await screen.findByText('已采用')).toBeVisible();
  expect((await screen.findByLabelText('成果正文')).textContent).toBe(content);
});

it('rejects an initial late body when the actual service session has changed before Workspace observes it',async()=>{
  const original=vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async(p,i)=>{
    const response=await original(p,i);
    if(String(p).startsWith('/api/v1/work/results'))state.session.service_instance='replacement-service';
    return response;
  });
  mount('/au/core-au/work/work-a/results/same-result');
  expect(await screen.findByRole('alert')).toHaveTextContent(/身份|服务/);
  expect(screen.queryByLabelText('成果正文')).toBeNull();
  expect(screen.queryByRole('heading',{name:'研究报告'})).toBeNull();
});

it('clears the protected result list when service changes during the Work projection read',async()=>{
  vi.mocked(api.coreWork).mockImplementation(async()=>{
    state.session.service_instance='replacement-service';return structuredClone(read);
  });
  mount('/au/core-au/results');
  expect(await screen.findByRole('alert')).toHaveTextContent(/身份|服务/);
  expect(screen.queryByRole('link',{name:'阅读与下载'})).toBeNull();
  expect(screen.queryByText('研究报告')).toBeNull();
});
