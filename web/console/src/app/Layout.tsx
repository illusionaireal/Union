import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { ArrowLeft, ChevronDown, RefreshCw } from 'lucide-react';
import { useWorkspace } from './workspace';
import { organizationPath, organizationRoute, organizationSections } from './organization-routes';
import { AccountSettings } from '../pages/Identity';
import { Dialog } from '../components/Dialog';
import { CreationRecovery } from '../features/commands/CreationRecovery';
import { GovernanceRecovery } from '../features/governance/GovernanceProvider';
import './organization-shell.css';

export function Layout() {
  const { core, connected, error, loading, lastSuccess, refresh } = useWorkspace();
  const location = useLocation();
  const route = organizationRoute(location.pathname, location.search);
  const [expanded, setExpanded] = useState(false);
  const [account, setAccount] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const previousPath = useRef(location.pathname);
  const section = route.section;
  const title = route.kind === 'au'
    ? organizationSections.find(item => item.path === section)?.label ?? '组织空间'
    : route.kind === 'invalid' ? '链接不可用' : '我的组织';
  useEffect(() => {
    document.title = `${title} · ai-union`;
    setExpanded(false);
    if (previousPath.current !== location.pathname) heading.current?.focus();
    previousPath.current = location.pathname;
  }, [location.pathname, title]);
  return <div className="organization-shell">
    <a className="skip" href="#main">跳转到正文</a>
    <header className="organization-header">
      <Link className="organization-brand" to="/organizations"><span aria-hidden="true">u</span>ai-union</Link>
      <div className="organization-header-actions">
        {route.kind === 'au' && <Link className="button secondary" to="/organizations"><ArrowLeft size={16} />我的组织</Link>}
        <button className="button secondary" onClick={() => setAccount(true)}>账号与登录</button>
      </div>
    </header>
    <div className="organization-body">
      {route.kind === 'au' && <aside className="organization-navigation" aria-label="组织空间导航">
        <p className="organization-current">{core?.au.name ?? '组织空间'}</p>
        <nav aria-label="组织页面">
          {organizationSections.map((item, index) => <Link
            key={item.path} to={organizationPath(route.organizationId, item.path)}
            data-nav={item.path || 'overview'}
            aria-current={item.path === section ? 'page' : undefined}
            className={`organization-nav-link${item.path === section ? ' active' : ''}${index > 3 ? ' organization-extra' : ''}${expanded ? ' expanded' : ''}`}
          >{item.label}</Link>)}
        </nav>
        <button className="button secondary organization-menu" aria-expanded={expanded}
          onClick={() => setExpanded(value => !value)}>更多页面<ChevronDown size={16} /></button>
      </aside>}
      <main id="main" className="organization-main">
        <div className="organization-page-heading">
          <h1 ref={heading} tabIndex={-1}>{title}</h1>
          <button className="button secondary" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw size={15} />刷新
          </button>
        </div>
        {!connected && core && <div className="connection-warning" role="status">
          当前连接不可用，以下是 {lastSuccess || '上次连接时'} 核验的记录，可能已过期。恢复连接后才能提交新操作。{error}
        </div>}
        <CreationRecovery />
        <GovernanceRecovery />
        <Outlet />
      </main>
    </div>
    {account && <Dialog id="account-dialog" closeId="close-account" title="账号与登录" onClose={() => setAccount(false)}>
      <AccountSettings />
    </Dialog>}
  </div>;
}
