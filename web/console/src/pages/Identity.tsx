import { useState, type FormEvent, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, errorText } from '../api/client';
import { useWorkspace } from '../app/workspace';
import './Identity.css';

type Mode = 'login' | 'setup' | 'recover' | 'password';
export function IdentityForm({mode, onCancel}: {mode: Mode; onCancel?: () => void}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [recovery, setRecovery] = useState('');
  const titles = {login:'登录 UNION', setup:'建立管理员账号', recover:'恢复账号', password:'修改登录密码'};
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const value: Record<string, unknown> = mode==='password'
      ? {password:data.get('password'), new_password:data.get('new_password')}
      : mode==='recover' ? {username:data.get('username'), code:data.get('code'), new_password:data.get('new_password')}
      : {username:data.get('username'), password:data.get('password'), remember:data.get('remember')==='on'};
    setBusy(true); setError('');
    try {
      const result = await api.auth(mode, value);
      form.reset();
      if (result.recovery_code) setRecovery(result.recovery_code);
      else window.location.reload();
    } catch (failure) { setError(errorText(failure)); }
    finally { setBusy(false); }
  }
  return <section className="identity-panel" aria-label={titles[mode]}>
    <h1>{titles[mode]}</h1>
    <p>{mode==='setup' ? '设置一次，以后直接用账号密码进入。此部署的第一个设置者成为管理员。' : mode==='recover' ? '使用首次设置时保存的恢复码。恢复后，旧密码和所有旧登录会话失效。' : mode==='password' ? '修改后其他设备的登录会话将失效。' : '登录你的工作台，继续管理目标、团队与成果。'}</p>
    {recovery ? <div role="status"><h2>请保存恢复码</h2><p>仅在本次显示。丢失密码时可用它恢复账号。</p><textarea aria-label="账号恢复码" readOnly value={recovery} autoComplete="off" /><button className="button primary" onClick={()=>window.location.reload()}>已保存，进入工作台</button></div>
    : <form onSubmit={submit}>
      {mode!=='password' && <label>账号<input name="username" autoComplete="username" required minLength={3} maxLength={100} pattern="[a-zA-Z0-9_.@\-]+" /></label>}
      {mode==='recover' ? <label>恢复码<input name="code" type="password" required autoComplete="off" maxLength={128} /></label> : <label>{mode==='password'?'当前密码':'密码'}<input name="password" type="password" autoComplete={mode==='setup'?'new-password':'current-password'} required minLength={mode==='setup'?12:1} maxLength={256} /></label>}
      {(mode==='password'||mode==='recover') && <label>新密码<input name="new_password" type="password" required minLength={12} maxLength={256} autoComplete="new-password" /></label>}
      {(mode==='setup'||mode==='login') && <label className="identity-remember"><input name="remember" type="checkbox" />记住此设备，最长30天</label>}
      <p className="form-note">设置密码至少12个字符。普通登录有效8小时，记住设备最长30天。</p>
      {error && <p role="alert">{error}</p>}
      <div className="identity-actions"><button className="button primary" disabled={busy}>{busy?'正在处理…':titles[mode]}</button>{onCancel && <button type="button" className="button secondary" onClick={onCancel}>返回</button>}</div>
    </form>}
  </section>;
}

export function AccountSettings() {
  const {session} = useWorkspace();
  const [mode, setMode] = useState<Mode>();
  const status = useQuery({queryKey:['identity', session?.service_instance, session?.session_scope], queryFn:api.authStatus, retry:false});
  if (mode) return <IdentityForm mode={mode} onCancel={()=>setMode(undefined)} />;
  return <section className="identity-settings"><h2>账号与登录</h2><p>{status.data?.account ? `当前账号：${status.data.account}` : '当前使用宿主会话。设置账号后，可直接用固定地址登录。'}</p>
    {!status.data?.configured && status.data?.can_setup && <button className="button primary" onClick={()=>setMode('setup')}>设置管理员账号</button>}
    {status.data?.account && <button className="button secondary" onClick={()=>setMode('password')}>修改密码</button>}
    <button className="button secondary" onClick={()=>void api.auth('logout',{}).then(()=>window.location.reload())}>退出登录</button>
  </section>;
}

export function IdentityBoundary({children}: {children: ReactNode}) {
  const {session, loading} = useWorkspace();
  const [recover, setRecover] = useState(false);
  const status = useQuery({queryKey:['identity', session?.service_instance, session?.session_scope], queryFn:api.authStatus, retry:false, refetchInterval:3000});
  if (status.isPending || loading && !status.data?.authenticated) return <main className="identity-page"><p role="status">正在连接工作台…</p></main>;
  if (status.isError) return <main className="identity-page"><p role="alert">暂时无法连接工作台。{errorText(status.error)}</p><button onClick={()=>void status.refetch()}>重试</button></main>;
  if (!status.data.authenticated) return <main className="identity-page"><div><span className="identity-brand">UNION</span>
    {status.data.configured ? <><IdentityForm mode={recover?'recover':'login'} /><button className="button secondary" onClick={()=>setRecover(!recover)}>{recover?'返回登录':'忘记密码，使用恢复码'}</button></>
      : <IdentityForm mode="setup" />}
    </div></main>;
  return <>{children}</>;
}
