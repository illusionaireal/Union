import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { request, errorText } from '../api/client';
import { useWorkspace } from '../app/workspace';
import { Card } from '../components/ui';
import './SubscriptionConnections.css';

interface Receipt { id: string; action: string; status: string; message: string; url?: string; instructions?: string; needs_callback?: boolean }
interface Status { available: boolean; native_available?: boolean; key_available?: boolean; pending: Receipt[]; providers: { id: string; name: string; connected: boolean; last_success?: string | null }[] }
interface LimitWindow { percent: number | null; limited: boolean; resets_at: number | null }
interface AccountInfo {
  available: boolean;
  workspace: { name?: string | null; usage_url?: string | null };
  limits: { rolling?: LimitWindow; weekly?: LimitWindow; monthly?: LimitWindow };
  accounts: { id: string; method: string }[];
  models: { id: string; name: string; context: number | null; output: number | null; tools: boolean; input: string[]; status: string | null }[];
  default_model: string | null;
}
export default function SubscriptionConnections() {
  const { session, connected } = useWorkspace();
  const allowed = !!session?.platform_admin;
  const [key, setKey] = useState('');
  const [callback, setCallback] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<Receipt>();
  const storage = 'union-subscription-request:' + session?.service_instance + ':' + session?.session_scope;
  const [view,setView]=useState(storage);
  const activeScope=useRef(storage);activeScope.current=storage;
  const [pending, setPending] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [model, setModel] = useState('');
  useEffect(() => { setView(storage); setPending(sessionStorage.getItem(storage) || ''); setKey(''); setCallback(''); setReceipt(undefined); setError(''); setBusy(false); }, [storage]);
  const status = useQuery({queryKey:['subscriptions',storage,allowed],
    enabled: allowed && connected, queryFn:()=>request<Status>('/api/subscriptions'), retry:false, refetchInterval:10000});
  const result = useQuery({queryKey:['subscription-receipt',storage,pending],
    enabled: allowed && connected && view===storage && !!pending,
    queryFn:()=>request<{receipt:Receipt}>('/api/subscription-receipts?id='+encodeURIComponent(pending)),
    retry:false,refetchInterval:2000});
  const account = useQuery({queryKey:['subscription-account',storage,allowed],
    enabled: allowed && connected,
    queryFn:()=>request<AccountInfo>('/api/subscription-account'),
    retry:false,refetchInterval:30000});
  const current = view===storage ? result.data?.receipt || receipt : undefined;
  async function submit(action:'save_go'|'authorize_go'|'authorize_chatgpt', event?: FormEvent) {
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
  async function complete(event:FormEvent) {
    event.preventDefault();if(!current)return;
    const scope=storage;const callback_url=callback;setCallback('');setBusy(true);setError('');
    // Only request identity is persisted. Callback codes remain in transient memory.
    const id=crypto.randomUUID();sessionStorage.setItem(storage+':callback',id);
    try {
      const response=await request<{receipt:Receipt}>('/api/subscription-commands',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,action:'complete_chatgpt',target_id:current.id,callback_url})});
      if(activeScope.current!==scope)return;
      setReceipt(response.receipt);await result.refetch();
    }catch(e){if(activeScope.current===scope)setError(errorText(e)+'；请查询原授权结果。');}finally{if(activeScope.current===scope)setBusy(false);}
  }
  const waiting = (go:boolean) => busy || (!!pending && !current) || [current,...(status.data?.pending||[])].some(r=>r && (go?r.action==='save_go'||r.action==='authorize_go':r.action==='authorize_chatgpt') && !['succeeded','failed','reconciled'].includes(r.status));
  // Persisted success time, so a reload still shows that an authorization landed.
  const lastSuccess = (id: string) => {
    const value = status.data?.providers.find(p=>p.id===id)?.last_success;
    return value ? ' · 最近授权 ' + new Date(value).toLocaleString('zh-CN', { hour12: false }) : '';
  };
  // Older servers or failed reads must not blank the card: only render the
  // account block when the payload actually carries workspace + models.
  const accountInfo = account.data?.available && account.data.workspace ? account.data : undefined;
  const goModels = accountInfo?.models ?? [];
  const selected = goModels.find(m=>m.id===model);
  return <Card title="订阅与账号连接">
    <p>直接在工作台配置已有订阅，无需登录服务器。认证保存在服务端；保存和授权不调用模型。</p>
    <p className="form-note">这是平台托管的账号连接。公司使用前仍需明确绑定、额度与能力验证；不会自动启动组织或开发调度。</p>
    {status.isError && <p role="alert">订阅连接状态暂不可读取</p>}
    {status.data && !status.data.available && <p role="alert">订阅接入服务暂不可用，请联系平台维护者；此处无需填写服务器地址。</p>}
    <div className="subscription-grid">
      <section><h3>OpenCode Go</h3><p>{status.data?.providers.find(p=>p.id==='opencode-go')?.connected?'认证已保存 · 模型能力未验证':'尚未连接'}{lastSuccess('opencode-go')}</p>
        <p>使用 OpenCode Console 账号登录，在官方页面选择已订阅 Go 的工作区，无需寻找 API Key。</p>
        <button className="button primary" type="button" onClick={()=>void submit('authorize_go')} disabled={!connected||!status.data?.native_available||waiting(true)}>连接 OpenCode Go 账号</button>
        <details><summary>已有个人 API Key？</summary><p>在官方 Console 的账号菜单 → Account → Personal API keys 创建，选择订阅 Go 的工作区。服务账号密钥与个人 Go 权益不同。</p><a href="https://opencode.ai/v2/docs/console/api/#personal-api-keys" target="_blank" rel="noopener noreferrer">查看官方个人密钥说明</a>
        <form onSubmit={e=>void submit('save_go',e)}><label>Go API Key<input aria-label="Go API Key" type="password" value={view===storage?key:''} onChange={e=>setKey(e.target.value)} autoComplete="off" maxLength={4096} required /></label>
        <button className="button" type="submit" disabled={!connected||!(status.data?.key_available??status.data?.available)||waiting(true)||!key.trim()}>保存 Go 连接</button></form></details>
        {accountInfo && <div className="subscription-account">
          <p>工作区：{accountInfo.workspace.name || '未知'}
            {accountInfo.workspace.usage_url && <a href={accountInfo.workspace.usage_url} target="_blank" rel="noopener noreferrer">官方用量</a>}
            {` · 已连接 ${accountInfo.accounts?.length ?? 0} 个账号`}</p>
          <ul className="subscription-limits">
            {([['rolling','滚动'],['weekly','每周'],['monthly','每月']] as const).map(([key,label])=>{
              const item = accountInfo.limits?.[key];
              if (!item || item.percent === null || item.percent === undefined) return null;
              return <li key={key}>{label} {item.percent}%{item.limited?'（已达上限）':''}
                {item.resets_at?` · ${new Date(item.resets_at).toLocaleString('zh-CN',{hour12:false})} 重置`:''}</li>;
            })}
          </ul>
          {goModels.length>0 && <div>
            <label>Go 可用模型<select aria-label="Go 可用模型" value={model} onChange={e=>setModel(e.target.value)}>
              <option value="">选择模型（{goModels.length} 个可用）</option>
              {goModels.map(m=><option key={m.id} value={m.id}>{m.name} · {m.id}</option>)}
            </select></label>
            {selected && <p className="form-note">上下文 {selected.context ?? '未知'} · 输出上限 {selected.output ?? '未知'} · 工具 {selected.tools?'支持':'未确认'}{accountInfo.default_model===selected.id?' · 官方默认':''}</p>}
            {selected && <button className="button" type="button" onClick={()=>void navigator.clipboard?.writeText(selected.id)}>复制模型 ID</button>}
            <p className="form-note">此处为兼容认证服务的只读目录。正式使用请在「组织模型接入」选择账号和模型，授权给当前组织。</p>
          </div>}
        </div>}
      </section>
      <section><h3>ChatGPT 订阅</h3><p>{status.data?.providers.find(p=>p.id==='openai')?.connected?'账号已授权 · 模型能力未验证':'尚未连接'}{lastSuccess('openai')}</p>
        <p>点击后打开官方登录页面，完成账号授权。远程服务器需在本页提交最终回调地址；不要把回调地址发到聊天。无需输入 ChatGPT 密码或 API Key。</p>
        <button className="button primary" type="button" onClick={()=>void submit('authorize_chatgpt')} disabled={!connected||!(status.data?.native_available??status.data?.available)||waiting(false)}>连接 ChatGPT 订阅</button>
      </section>
    </div>
    {error && <p role="alert">{error}</p>}
    {!!status.data?.pending?.length && <div><p>有正在授权或待核对的账号操作。查询原流程，不会重新提交：</p>{status.data.pending.map(r=><button className="button" key={r.id} type="button" onClick={()=>{setPending(r.id);sessionStorage.setItem(storage,r.id);setConfirmed(false);setCallback('');}}>{r.action==='save_go'||r.action==='authorize_go'?'Go连接':'ChatGPT授权'} · {r.status} · 查看原流程</button>)}</div>}
    {current && <div role="status"><p>{current.message}</p>
      {current.url && <a className="button" href={current.url} target="_blank" rel="noopener noreferrer">打开官方授权页面</a>}
      {current.instructions && <pre className="subscription-instructions">{current.instructions}</pre>}
      <p className="form-note">请求 {current.id} · {current.status}</p></div>}
    {current?.status==='authorizing' && current.needs_callback && <form className="subscription-callback" onSubmit={e=>void complete(e)}><label>官方授权后的完整回调地址<input aria-label="官方授权后的完整回调地址" type="password" autoComplete="off" value={view===storage?callback:''} onChange={e=>setCallback(e.target.value)} maxLength={16000} required /></label><button className="button primary" type="submit" disabled={busy||!callback.trim()}>完成 ChatGPT 连接</button></form>}
    {current?.status==='unknown' && <div><label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} />我已在账号服务/官方页面核对原操作已结束，设备码已取消或过期；仅看到“已连接”不代表原操作结束。</label><button className="button" type="button" disabled={!confirmed||busy} onClick={()=>void reconcile()}>记录核对并结束跟踪</button><p>仅记录人工核对，不推定原请求成功，也不会自动重新授权。</p></div>}
    {pending && <button className="button" type="button" onClick={()=>{void result.refetch();void status.refetch();}}>查询原请求结果</button>}
  </Card>;
}
