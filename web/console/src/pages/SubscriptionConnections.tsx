import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { request, errorText } from '../api/client';
import { useWorkspace } from '../app/workspace';
import { Card } from '../components/ui';
import './SubscriptionConnections.css';

interface Receipt { id: string; action: string; status: string; message: string; url?: string; instructions?: string }
interface Status { available: boolean; pending: Receipt[]; providers: { id: string; name: string; connected: boolean }[] }
export default function SubscriptionConnections() {
  const { session, connected } = useWorkspace();
  const allowed = !!session?.platform_admin;
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<Receipt>();
  const storage = 'union-subscription-request:' + session?.service_instance + ':' + session?.session_scope;
  const [view,setView]=useState(storage);
  const activeScope=useRef(storage);activeScope.current=storage;
  const [pending, setPending] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  useEffect(() => { setView(storage); setPending(sessionStorage.getItem(storage) || ''); setKey(''); setReceipt(undefined); setError(''); setBusy(false); }, [storage]);
  const status = useQuery({queryKey:['subscriptions',storage,allowed],
    enabled: allowed && connected, queryFn:()=>request<Status>('/api/subscriptions'), retry:false, refetchInterval:10000});
  const result = useQuery({queryKey:['subscription-receipt',storage,pending],
    enabled: allowed && connected && view===storage && !!pending,
    queryFn:()=>request<{receipt:Receipt}>('/api/subscription-receipts?id='+encodeURIComponent(pending)),
    retry:false,refetchInterval:2000});
  const current = view===storage ? result.data?.receipt || receipt : undefined;
  async function submit(action:'save_go'|'authorize_chatgpt', event?: FormEvent) {
    const scope=storage;
    event?.preventDefault(); setBusy(true); setError('');
    const id = crypto.randomUUID();
    // Persist identity before a write; a timed out write is queried, never retried.
    sessionStorage.setItem(storage,id); setPending(id); setReceipt(undefined);
    const api_key = key; setKey('');
    try {
      const response = await request<{receipt:Receipt}>('/api/subscription-commands',{method:'POST',
        headers:{'Content-Type':'application/json'},body:JSON.stringify({id,action,...(action==='save_go'?{api_key}:{})})});
      if(activeScope.current!==scope)return;
      setReceipt(response.receipt); await status.refetch();
    } catch(e) { if(activeScope.current===scope)setError(errorText(e)+'；请查询原请求结果，勿重复提交。'); }
    finally {if(activeScope.current===scope)setBusy(false);}
  }
  if(!allowed) return null;
  async function reconcile() {
    const scope=storage;
    setBusy(true);setError('');
    try {
      const response=await request<{receipt:Receipt}>('/api/subscription-commands',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),action:'reconcile',target_id:pending,confirmed_ended:confirmed})});
      if(activeScope.current!==scope)return;
      setReceipt(response.receipt);await result.refetch();await status.refetch();if(activeScope.current===scope)setConfirmed(false);
    } catch(e){if(activeScope.current===scope)setError(errorText(e));}finally{if(activeScope.current===scope)setBusy(false);}
  }
  const waiting = busy || (!!pending && (!current || !['succeeded','failed','reconciled'].includes(current.status))) || !!status.data?.pending?.length;
  return <Card title="订阅与账号连接">
    <p>直接在工作台配置已有订阅，无需登录服务器。认证保存在服务端；保存和授权不调用模型。</p>
    <p className="form-note">这是平台托管的账号连接。公司使用前仍需明确绑定、额度与能力验证；不会自动启动组织或开发调度。</p>
    {status.isError && <p role="alert">订阅连接状态暂不可读取</p>}
    {status.data && !status.data.available && <p role="alert">订阅接入服务暂不可用，请联系平台维护者；此处无需填写服务器地址。</p>}
    <div className="subscription-grid">
      <section><h3>OpenCode Go</h3><p>{status.data?.providers.find(p=>p.id==='opencode-go')?.connected?'认证已保存 · 模型能力未验证':'尚未连接'}</p>
        <form onSubmit={e=>void submit('save_go',e)}><label>Go API Key<input aria-label="Go API Key" type="password" value={view===storage?key:''} onChange={e=>setKey(e.target.value)} autoComplete="off" maxLength={4096} required /></label>
        <button className="button primary" type="submit" disabled={!connected||!status.data?.available||waiting||!key.trim()}>保存 Go 连接</button></form>
      </section>
      <section><h3>ChatGPT 订阅</h3><p>{status.data?.providers.find(p=>p.id==='openai')?.connected?'账号已授权 · 模型能力未验证':'尚未连接'}</p>
        <p>点击后在官方页面完成设备授权，返回这里查看结果。无需输入 ChatGPT 密码或 API Key。</p>
        <button className="button primary" type="button" onClick={()=>void submit('authorize_chatgpt')} disabled={!connected||!status.data?.available||waiting}>连接 ChatGPT 订阅</button>
      </section>
    </div>
    {error && <p role="alert">{error}</p>}
    {!!status.data?.pending?.length && <div><p>有正在授权或待核对的账号操作。查询原流程，不会重新提交：</p>{status.data.pending.map(r=><button className="button" key={r.id} type="button" onClick={()=>{setPending(r.id);sessionStorage.setItem(storage,r.id);setConfirmed(false);}}>{r.action==='save_go'?'Go连接':'ChatGPT授权'} · {r.status} · 查看原流程</button>)}</div>}
    {current && <div role="status"><p>{current.message}</p>
      {current.url && <a className="button" href={current.url} target="_blank" rel="noopener noreferrer">打开官方授权页面</a>}
      {current.instructions && <pre className="subscription-instructions">{current.instructions}</pre>}
      <p className="form-note">请求 {current.id} · {current.status}</p></div>}
    {current?.status==='unknown' && <div><label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} />我已在账号服务/官方页面核对原操作已结束，设备码已取消或过期；仅看到“已连接”不代表原操作结束。</label><button className="button" type="button" disabled={!confirmed||busy} onClick={()=>void reconcile()}>记录核对并结束跟踪</button><p>仅记录人工核对，不推定原请求成功，也不会自动重新授权。</p></div>}
    {pending && <button className="button" type="button" onClick={()=>{void result.refetch();void status.refetch();}}>查询原请求结果</button>}
  </Card>;
}
