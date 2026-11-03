import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { request, errorText } from '../api/client';
import { useWorkspace } from '../app/workspace';
import { Card } from '../components/ui';

interface Receipt { id: string; action: string; status: string; message: string; target_id?: string; url?: string; instructions?: string }
interface Account { id: string; name: string; workspace: string | null }
interface Model { id: string; name: string; tools: boolean; context?: number; output?: number }

export default function ModelServiceConnections() {
  const { session, connected, orgId, data, refresh } = useWorkspace();
  const allowed = !!session?.platform_admin, cache = useQueryClient();
  const scope = ['union-model-service', session?.service_instance, session?.session_scope, orgId].join(':');
  const active = useRef(scope); active.current = scope;
  const [view, setView] = useState(scope);
  const [account, setAccount] = useState(''), [model, setModel] = useState('');
  const [pending, setPending] = useState(''), [error, setError] = useState('');
  const [busy, setBusy] = useState(false), [bind, setBind] = useState(true);
  useEffect(() => {
    setView(scope); setPending(sessionStorage.getItem(scope) || ''); setAccount(''); setModel(''); setError(''); setBusy(false);
  }, [scope]);
  const status = useQuery({ queryKey: ['model-service', scope], enabled: allowed && connected,
    queryFn: () => request<{ available: boolean; accounts: Account[] }>('/api/model-service'), retry: false, refetchInterval: 10000 });
  const models = useQuery({ queryKey: ['model-service-models', scope, account], enabled: allowed && connected && !!account && view === scope,
    queryFn: () => request<{ models: Model[] }>('/api/model-account-models?account_ref=' + encodeURIComponent(account)), retry: false });
  const receipt = useQuery({ queryKey: ['model-service-receipt', scope, pending], enabled: allowed && connected && !!pending && view === scope,
    queryFn: () => request<{ receipt: Receipt }>('/api/model-account-receipts?id=' + encodeURIComponent(pending)), retry: false, refetchInterval: 2000 });
  const current = view === scope ? receipt.data?.receipt : undefined;
  const waiting = busy || !!pending && (!current || ['accepted','unknown'].includes(current.status));
  async function submit(action: 'authorize_go' | 'adopt' | 'finish_adoption') {
    const target = scope, id = crypto.randomUUID(), targetId = current?.target_id || pending;
    setBusy(true); setError(''); setPending(id); sessionStorage.setItem(scope, id);
    try {
      await request('/api/model-account-commands', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, action, ...(action === 'adopt' ? {
          organization_id: orgId, account_ref: account, model, connection_id: 'go-' + id, name: 'OpenCode Go · ' + model,
          bind_default: bind, reason: '平台管理员选择账号与模型，授予当前组织使用',
        } : action === 'finish_adoption' ? { target_id: targetId } : {}) }) });
      if (active.current !== target) return;
      await cache.invalidateQueries({ queryKey: ['model-connections'] }); await status.refetch(); await refresh();
    } catch (e) { if (active.current === target) setError(errorText(e) + '；请查询原请求，勿重复提交。'); }
    finally { if (active.current === target) setBusy(false); }
  }
  if (!allowed) return null;
  const selected = models.data?.models.find(m => m.id === model);
  return <Card title="组织模型接入">
    <p>连接 OpenCode Go 账号，选择模型并授权给当前组织。采用后，可在模型卡片测试连接或开始有限运行。</p>
    {!status.data?.available && <p role="status">正式模型服务尚未就绪，请联系平台维护者完成安装。</p>}
    <button className="button" disabled={!connected || !status.data?.available || waiting} onClick={() => void submit('authorize_go')}>登录正式 Go 账号</button>
    {!!status.data?.accounts.length && <div className="subscription-account">
      <label>用于当前组织的账号<select aria-label="用于当前组织的账号" value={view === scope ? account : ''} onChange={e => { setAccount(e.target.value); setModel(''); }}>
        <option value="">选择已连接账号</option>{status.data.accounts.map(a => <option key={a.id} value={a.id}>{a.name}{a.workspace ? ' · ' + a.workspace : ''} · {a.id.slice(-6)}</option>)}
      </select></label>
      {account && <label>正式 Go 模型<select aria-label="正式 Go 模型" value={model} onChange={e => setModel(e.target.value)}>
        <option value="">选择账号可用模型</option>{models.data?.models.map(m => <option key={m.id} value={m.id}>{m.name} · {m.id}</option>)}
      </select></label>}
      {models.isError && <p role="alert">账号模型暂不可读取，请检查账号授权。</p>}
      {selected && <p>上下文 {selected.context ?? '未知'} · 输出 {selected.output ?? '未知'} · 工具 {selected.tools ? '目录声明支持' : '未确认'}</p>}
      <label><input type="checkbox" checked={bind} onChange={e => setBind(e.target.checked)} />设为当前组织默认模型</label>
      <button className="button primary" disabled={!connected || !orgId || !selected || waiting} onClick={() => void submit('adopt')}>授权给 {data?.organization.name || '当前组织'} 并保存连接</button>
      <p className="form-note">采用不会调用模型。运行仍受组织授权和调用额度限制；真实结果见运行记录。</p>
    </div>}
    {error && <p role="alert">{error}</p>}
    {current && <div role="status"><p>{current.message}</p>{current.url && <a className="button" href={current.url} target="_blank" rel="noopener noreferrer">打开账号授权页面</a>}
      {current.instructions && <pre>{current.instructions}</pre>}<p className="form-note">请求 {current.id} · {current.status}</p></div>}
    {current?.status === 'unknown' && ['adopt','finish_adoption'].includes(current.action) && <button className="button" disabled={busy || !connected} onClick={() => void submit('finish_adoption')}>查询原授权并完成采用</button>}
    {pending && <button className="button" onClick={() => { void receipt.refetch(); void status.refetch(); }}>查询原接入结果</button>}
  </Card>;
}
