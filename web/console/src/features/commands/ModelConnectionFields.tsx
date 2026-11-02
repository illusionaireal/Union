import { useEffect, useState } from 'react';
import type {ModelConnection} from '../../api/types';
import {api} from '../../api/client';

const providers = [
  {id:'custom', name:'自定义兼容接口', url:'', protocol:'openai_chat_completions'},
  {id:'openai', name:'OpenAI API', url:'https://api.openai.com/v1', protocol:'openai_responses'},
  {id:'anthropic', name:'Anthropic API', url:'https://api.anthropic.com/v1', protocol:'anthropic_messages'},
  {id:'google', name:'Google Gemini API', url:'https://generativelanguage.googleapis.com/v1beta', protocol:'google_generate_content'},
  {id:'openrouter', name:'OpenRouter', url:'https://openrouter.ai/api/v1', protocol:'openai_chat_completions'},
  {id:'local', name:'本地 / 自托管兼容服务', url:'http://127.0.0.1:11434/v1', protocol:'openai_chat_completions'},
];
export function ModelConnectionFields({connection, newId, endpoint, hasDefault}: {connection?:ModelConnection; newId:string; endpoint?:string; hasDefault:boolean}) {
  const [provider,setProvider]=useState(connection?.config.provider || 'custom');
  const [url,setUrl]=useState(connection?.config.base_url || endpoint || '');
  const [protocol,setProtocol]=useState(connection?.config.protocol || 'openai_chat_completions');
  const [source,setSource]=useState(connection?.config.api_key_file?'file':connection?.config.api_key_env?'env':connection?.config.auth_type==='none'?'none':'key');
  const [basis,setBasis]=useState(connection?.config.billing?.basis || 'unknown');
  const [catalog,setCatalog]=useState<Array<{provider:string;model:string}>>([]);
  useEffect(()=>{let active=true; void api.catalog().then(result=>{if(active)setCatalog(result.models);}).catch(()=>{}); return ()=>{active=false;};},[]);
  return <>
    <p className="form-note">选择接口，填写凭据与模型。保存不会调用模型，也不会启动组织。</p>
    <input type="hidden" name="api_enabled" value={String(connection?.config.enabled ?? true)} />
    <label className="operation-field">供应商<select name="provider" value={provider} onChange={e=>{const selected=providers.find(p=>p.id===e.target.value)!;setProvider(selected.id);setUrl(selected.url);setProtocol(selected.protocol);}}>{providers.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <label className="operation-field">API 根地址<input name="base_url" type="url" required value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://your-provider.example/v1" /></label>
    <label className="operation-field">API 模型 ID<input name="api_model" required maxLength={128} defaultValue={connection?.config.model || ''} list="union-model-options" placeholder="搜索目录或直接输入模型 ID" /></label>
    <datalist id="union-model-options">{catalog.filter(m=>provider==='custom'||m.provider===provider).map(m=><option key={m.provider+'/'+m.model} value={m.model}>{m.provider}</option>)}</datalist>
    <label className="operation-field">认证方式<select value={source} onChange={e=>setSource(e.target.value)}><option value="key">API Key</option><option value="env">服务端环境变量引用（平台管理员）</option><option value="file">宿主已登记凭据文件（平台管理员）</option><option value="none">无需认证的自托管服务</option></select></label>
    <input name="auth_type" type="hidden" value={source==='none'?'none':'key'} />
    {source==='key' && <label className="operation-field">API Key（留空保留原密钥）<input name="api_key" type="password" autoComplete="new-password" maxLength={4096} /></label>}
    {source==='env' && <label className="operation-field">环境变量名<input name="api_key_env" required defaultValue={connection?.config.api_key_env || ''} pattern="[A-Za-z_][A-Za-z0-9_]*" maxLength={64} placeholder="UNION_MODEL_API_KEY" /></label>}
    {source==='file' && <label className="operation-field">凭据文件别名<input name="api_key_file" required defaultValue={connection?.config.api_key_file || ''} pattern="[A-Za-z0-9][A-Za-z0-9_.\-]*" maxLength={80} placeholder="primary-model-key" /><span className="form-note">由宿主登记私有凭据目录，填写其中的文件别名。这里不接收宿主路径。</span></label>}
    <p className="form-note">订阅账号请使用页面的账号连接入口。API 接口与订阅额度分别验证。</p>
    <label className="check-field"><input name="bind_default" type="checkbox" defaultChecked={!connection&&!hasDefault} />保存后设为当前 AU 默认模型</label>
    <details><summary>高级设置</summary>
      <label className="operation-field">上下文策略<select name="context_strategy" defaultValue={connection?.config.context_policy?.strategy||'trim_history'}><option value="trim_history">保留当前任务，裁剪完整旧对话</option><option value="reject">超出窗口时停止并提示</option></select></label>
      <label className="operation-field">上下文窗口（可选的手动上限）<input name="context_window" type="number" min={512} max={10000000} defaultValue={connection?.config.context_policy?.window} /></label>
      <label className="operation-field">成本口径<select name="cost_basis" value={basis} onChange={e=>setBasis(e.target.value as typeof basis)}><option value="unknown">未知，暂不估算金额</option><option value="metered">按量 API</option><option value="subscription">周期订阅</option><option value="owned">自有部署资源</option></select></label>
      <label className="operation-field">计费币种<input name="billing_currency" defaultValue={connection?.config.billing?.currency || ''} pattern="[A-Z]{3}" placeholder="USD / CNY" required={basis==='metered'} /></label>
      <label className="operation-field">费率版本<input name="billing_revision" defaultValue={connection?.config.billing?.revision || ''} maxLength={80} required={basis==='metered'} placeholder="price-2026-11" /></label>
      {basis==='metered' && <><label className="operation-field">每百万输入 token 单价（最小货币单位）<input name="input_rate" type="number" min={0} step={1} required defaultValue={connection?.config.billing?.input_per_million_minor} /></label><label className="operation-field">每百万输出 token 单价（最小货币单位）<input name="output_rate" type="number" min={0} step={1} required defaultValue={connection?.config.billing?.output_per_million_minor} /></label></>}
      {basis==='metered' && <label className="operation-field">每百万缓存读取 token 单价（可选）<input name="cache_rate" type="number" min={0} step={1} defaultValue={connection?.config.billing?.cache_read_per_million_minor} /></label>}
      <p className="form-note">金额估算不会扩大资源额度。订阅及自有成本先记录用量，可在期末分摊。</p>
      <label className="operation-field">协议<select name="protocol" value={protocol} onChange={e=>setProtocol(e.target.value)}><option value="openai_chat_completions">Chat Completions</option><option value="openai_responses">Responses</option><option value="anthropic_messages">Anthropic Messages</option><option value="google_generate_content">Gemini generateContent</option></select></label>
      <label className="operation-field">连接 ID<input name="connection_id" required defaultValue={connection?.id||newId} readOnly={!!connection} maxLength={80} /></label>
      <label className="operation-field">连接名称<input name="connection_name" required defaultValue={connection?.config.name||'我的模型连接'} maxLength={100} /></label>
      <label className="operation-field">输出上限字段<select name="token_limit_field" defaultValue={connection?.config.token_limit_field||'max_tokens'}><option value="max_tokens">max_tokens</option><option value="max_completion_tokens">max_completion_tokens</option></select></label>
      <label className="operation-field">最大输出 token<input name="max_output_tokens" type="number" required min={1} max={32768} defaultValue={connection?.config.max_output_tokens||8192} /></label>
      <label className="operation-field">API 超时（秒）<input name="api_timeout" type="number" required min={1} max={600} defaultValue={connection?.config.timeout_seconds||180} /></label>
      <label className="check-field"><input name="allow_private_http" type="checkbox" defaultChecked={connection?.config.allow_private_http} />允许此连接访问明确填写的内网 HTTP 地址</label>
      <label className="operation-field">配置说明<input name="reason" required defaultValue="为组织接入模型" /></label>
    </details>
  </>;
}
