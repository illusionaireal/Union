import { useQuery, useQueryClient } from '@tanstack/react-query';
import { request } from '../api/client';
import { useWorkspace } from '../app/workspace';
import { Card } from '../components/ui';
interface StreamView { cursor: number; text: string; tools: string[]; state: string; more?: boolean }
interface Events { last_seq: number; state: string; has_more?: boolean; events: { type: string; payload: { text?: string; name?: string } }[] }
export default function ModelRunStream() {
  const { session, connected, orgId, data } = useWorkspace(), cache = useQueryClient();
  const run = [...(data?.runs || [])].reverse().find(r => r.execution?.transport_source === 'model_service');
  const key = ['model-run-stream',session?.service_instance,session?.session_scope,orgId,run?.id];
  const query = useQuery({ queryKey:key, enabled:connected && session?.role === 'board' && !!run,
    retry:false, refetchInterval:q => q.state.data?.more ? 200 : run?.status === 'running' ? 1000 : false,
    queryFn:async () => {
      const prior = cache.getQueryData<StreamView>(key) || {cursor:0,text:'',tools:[],state:'running'};
      const result = await request<Events>('/api/model-request-events?' + new URLSearchParams({organization_id:orgId,run_id:run!.id,after:String(prior.cursor)}));
      return {cursor:result.last_seq,text:prior.text + result.events.filter(e=>e.type==='text_delta').map(e=>e.payload.text || '').join(''),
        tools:[...prior.tools,...result.events.filter(e=>e.type==='tool_call_complete').map(e=>e.payload.name || '')],state:result.state,more:result.has_more};
    } });
  if (!run || session?.role !== 'board') return null;
  return <Card title="最近模型请求"><p>{run.id} · {run.display_status}</p>
    {query.isError && <p role="alert">流事件暂不可读取；原请求保留，请稍后查询。</p>}
    {query.data?.text && <pre className="subscription-instructions">{query.data.text}</pre>}
    {!!query.data?.tools.length && <p>模型提出工具调用：{query.data.tools.join('、')}。实际执行结果以组织运行记录为准。</p>}
    <button className="button" onClick={()=>void query.refetch()}>查询原模型请求</button>
  </Card>;
}
