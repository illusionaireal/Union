import { useEffect, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, errorText, type Gateway, type GatewayCommand, type GatewayConfig } from '../api/client';
import { useWorkspace } from '../app/workspace';
import { Card, Empty } from '../components/ui';

const blank: GatewayConfig = { name: '', service_url: '', api_base_url: '', admin_url: '', mode: 'external' };
const healthNames = { unknown: '尚未检测', healthy: '健康', unavailable: '无法确认可用' };

export default function Gateways() {
  const { session, connected } = useWorkspace();
  const [editing, setEditing] = useState<Gateway | null>(null);
  const [form, setForm] = useState<GatewayConfig>(blank);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [uncertain, setUncertain] = useState<GatewayCommand | null>(null);
  const allowed = !!session?.platform_admin;
  const query = useQuery({
    queryKey: ['gateways', session?.service_instance, session?.role, allowed],
    enabled: allowed && connected,
    queryFn: ({ signal }) => api.gateways(undefined, signal),
    retry: false, refetchInterval: 4000,
  });
  useEffect(() => {
    setEditing(null); setForm(blank); setMessage(''); setUncertain(null);
  }, [session?.service_instance, allowed]);
  async function submit(command: GatewayCommand) {
    setBusy(true); setMessage('');
    try {
      const { receipt } = await api.gatewayCommand(command);
      setUncertain(null);
      setMessage(`${receipt.message} · 请求 ${receipt.id}`);
      if (receipt.status === 'succeeded' && command.kind === 'save') {
        setEditing(null); setForm(blank);
      }
      await query.refetch();
    } catch (error) {
      setUncertain(command);
      setMessage(`${errorText(error)}。请查询下方记录，重试会保留原请求标识 ${command.id}。`);
    } finally { setBusy(false); }
  }
  function action(gateway: Gateway, kind: 'archive' | 'probe') {
    if (kind === 'archive' && !window.confirm('解除网关登记？现有 AU 独立连接与远端服务保持原状，令牌撤销需到网关后台执行。')) return;
    void submit({ id: crypto.randomUUID(), gateway_id: gateway.id, base_revision: gateway.revision, kind, data: {} });
  }
  function save(event: FormEvent) {
    event.preventDefault();
    void submit({ id: crypto.randomUUID(), gateway_id: editing?.id || 'gateway-' + crypto.randomUUID().slice(0, 12),
      base_revision: editing?.revision || 0, kind: 'save', data: { config: form } });
  }
  if (!allowed) return <Card title="平台网关管理"><Empty title="需要宿主授予平台管理权限">组织发起人权限不包含网关管理。请由宿主启用网关管理入口。</Empty></Card>;
  const disabled = !connected || busy || query.isError || !query.data;
  return <>
    <p className="form-note">New API 负责渠道、路由和用量；这里管理实例接入。健康检测不调用模型。模型测试在公司的“模型与 API”页面单独执行。</p>
    {query.isPending && <p role="status">正在读取网关登记…</p>}
    {query.isError && <p role="alert">{errorText(query.error)}。<button className="text-button" onClick={() => void query.refetch()}>重新读取</button></p>}
    {!connected && <p role="status" className="connection-warning">服务连接已断开，以下为最近读取的记录；操作暂不可用。</p>}
    <div className="connection-grid">
      {query.data?.gateways.map(gateway => <Card key={gateway.id} title={gateway.config.name}>
        <p>{gateway.config.mode === 'managed' ? '平台托管登记 · 运维控制尚未接通' : '外部接入'}</p>
        <dl className="gateway-facts">
          <dt>API 地址</dt><dd>{gateway.config.api_base_url}</dd>
          <dt>服务端口</dt><dd>{new URL(gateway.config.service_url).port || (gateway.config.service_url.startsWith('https:') ? '443' : '80')}（访问端口，内部端口未知）</dd>
          <dt>运行版本</dt><dd>{gateway.version || '未知'}</dd>
          <dt>健康状态</dt><dd>{healthNames[gateway.health]}</dd>
          <dt>部署状态</dt><dd>未知（尚无部署控制器）</dd>
          <dt>检测时间</dt><dd>{gateway.checked_at || '尚未检测'}</dd>
        </dl>
        <p className="form-note">{gateway.message}</p>
        <div className="empty-actions">
          <button className="button secondary" disabled={disabled} onClick={() => action(gateway, 'probe')}>检测健康</button>
          <button className="button secondary" disabled={disabled} onClick={() => { setEditing(gateway); setForm({ ...gateway.config }); }}>编辑</button>
          <button className="button secondary" onClick={() => void navigator.clipboard.writeText(gateway.config.api_base_url).then(() => setMessage('API 地址已复制')).catch(() => setMessage('复制失败，请手动复制地址'))}>复制 API 地址</button>
          <a className="button secondary" href={gateway.config.admin_url} target="_blank" rel="noopener noreferrer">打开 New API 后台</a>
          <button className="text-button" disabled={disabled} onClick={() => action(gateway, 'archive')}>解除登记</button>
        </div>
      </Card>)}
    </div>
    {query.data?.gateways.length === 0 && <Card title="尚未接入网关"><p>登记已有 New API 实例，然后检测健康；保存不会部署服务或调用模型。</p></Card>}
    <Card title={editing ? '编辑网关登记' : '接入 New API 实例'}>
      <form onSubmit={save} className="gateway-form">
        <label>网关名称<input required maxLength={100} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label>
        {(['service_url', 'api_base_url', 'admin_url'] as const).map((key, i) => <label key={key}>
          {['服务根地址（用于健康检测）', 'API 根地址（通常以 /v1 结尾）', '管理后台地址'][i]}
          <input type="url" required maxLength={2000} placeholder={i === 1 ? 'https://gateway.example/v1' : 'https://gateway.example'} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} />
        </label>)}
        <label>接入方式<select value={form.mode} onChange={e => setForm({ ...form, mode: e.target.value as GatewayConfig['mode'] })}><option value="external">外部接入</option><option value="managed">平台托管（仅登记，运维待接通）</option></select></label>
        <p className="form-note">使用 HTTPS；本机回环地址可用 HTTP。此处不保存管理员密钥或上游凭据。修改登记不会自动迁移 AU 的现有连接。</p>
        <div className="empty-actions"><button className="button primary" disabled={disabled} type="submit">保存登记</button>
          {editing && <button type="button" className="button secondary" onClick={() => { setEditing(null); setForm(blank); }}>取消编辑</button>}
          <Link to="/models" className="button secondary">为公司配置模型连接</Link>
        </div>
      </form>
    </Card>
    {message && <p role="status">{message}</p>}
    {uncertain && <button className="button secondary" disabled={!connected || busy} onClick={() => void submit(uncertain)}>查询或重试原请求</button>}
    <Card title="最近操作回执"><p className="form-note">显示最近 20 项。失败或中断不代表远端已停止；检测失败也不证明模型不可用。</p>
      {query.data?.receipts?.map(receipt => <p key={receipt.id}>{receipt.created_at} · {receipt.gateway_id} · {receipt.status} · {receipt.message}<br /><small>请求 {receipt.id}</small></p>)}
    </Card>
  </>;
}
