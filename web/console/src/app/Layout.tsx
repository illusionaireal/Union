import { useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  ListChecks,
  Files,
  History,
  Activity,
  Settings,
  RefreshCw,
  Plus,
  Play,
  Pause,
  MessageSquarePlus,
  ShieldCheck,
  ArrowUpRight,
} from 'lucide-react';
import { useWorkspace } from './workspace';
import { CommandButton, useCommands } from '../features/commands/CommandProvider';
import { Card, Empty, sourceName } from '../components/ui';
const pages = [
  {
    key: 'overview',
    label: '总览',
    title: '组织总览',
    description: '从当前行动，到下一轮决定。',
    icon: LayoutDashboard,
  },
  {
    key: 'members',
    label: '成员与岗位',
    title: '成员与岗位',
    description: '稳定身份、明确责任，以及可以延续的协作。',
    icon: Users,
  },
  {
    key: 'tasks',
    label: '工作',
    title: '工作与依赖',
    description: '每项工作都有责任人、依据与可追溯的结果。',
    icon: ListChecks,
  },
  {
    key: 'artifacts',
    label: '成果',
    title: '组织成果',
    description: '读取实际文件，核对版本与来源。',
    icon: Files,
  },
  {
    key: 'activity',
    label: '活动',
    title: '事件与决定',
    description: '当前安排如何形成，后续行动因何发生。',
    icon: History,
  },
  {
    key: 'resources',
    label: '执行与资源',
    title: '执行与资源',
    description: '调用有边界，未知费用如实显示。',
    icon: Activity,
  },
  {
    key: 'settings',
    label: '组织设置',
    title: '组织设置与回执',
    description: '采用规则、调整资源，并确认操作结果。',
    icon: Settings,
  },
];
export function Layout() {
  const { session, data, orgId, selectOrg, connected, error, lastSuccess, loading, refresh } =
    useWorkspace();
  const { pending, inspect } = useCommands();
  const location = useLocation();
  const page = pages.find((p) => '/' + p.key === location.pathname) || pages[0];
  const organizationSearch = orgId ? '?organization=' + encodeURIComponent(orgId) : '';
  useEffect(() => {
    document.title = `${page.label} · ai-union`;
  }, [page.label]);
  return (
    <>
      <a className="skip" href="#main">
        跳转到正文
      </a>
      <aside className="sidebar" aria-label="工作台导航">
        <NavLink to={{ pathname: '/overview', search: organizationSearch }} className="brand">
          <span className="brand-symbol" aria-hidden="true">
            u
          </span>
          <span>
            ai-union<span className="brand-dot">.</span>
          </span>
        </NavLink>
        <label className="workspace-switch">
          <span className="org-icon">U</span>
          <span className="workspace-select">
            <small>当前组织</small>
            <select
              id="org-select"
              aria-label="当前组织"
              value={orgId}
              onChange={(e) => selectOrg(e.target.value)}
            >
              {!session?.organizations.length && <option value="">尚未创建组织</option>}
              {session?.organizations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </span>
        </label>
        <div className="nav-caption">WORKSPACE</div>
        <nav id="navigation">
          {pages.map(({ key, label, icon: Icon }) => (
            <NavLink
              key={key}
              to={{ pathname: '/' + key, search: organizationSearch }}
              data-nav={key}
              className={({ isActive }) => 'nav-button' + (isActive ? ' active' : '')}
            >
              <Icon size={19} strokeWidth={1.8} />
              <span>{label}</span>
              <span className="nav-active-dot" />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <ShieldCheck size={21} />
            <strong>有边界地自主协作</strong>
            <p>
              目标指引行动，章程约束权限。
              <br />
              每次决定留下可追溯的依据。
            </p>
            <span>
              本机组织 · 持久记录 <ArrowUpRight size={13} />
            </span>
          </div>
          <div className="sidebar-footer">
            <span className="avatar tiny human">人</span>
            <div>
              <strong id="role-label">
                {session
                  ? session.role === 'board'
                    ? '本机发起人'
                    : '本机观察者'
                  : '等待本机会话'}
              </strong>
              <small>LOCAL WORKSPACE</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            组织工作台 <span>/</span>
            <strong id="breadcrumb-page">{page.label}</strong>
          </div>
          <div className="topbar-actions">
            <span id="source-label" className="source-label">
              {data ? sourceName(data.source) : '尚未执行'}
            </span>
            <button
              id="refresh"
              className="button secondary compact"
              onClick={() => void refresh()}
            >
              <RefreshCw size={15} />
              刷新
            </button>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <div className="eyebrow">ORGANIZATION WORKSPACE</div>
              <h1 id="page-title">{page.title}</h1>
              <p id="page-description">{page.description}</p>
            </div>
            <div className="connection">
              <div>
                <span className={`dot ${connected ? 'green' : 'amber'}`} />
                <span id="connection-label">
                  {connected ? '已连接本机服务' : loading ? '正在连接' : '连接断开'}
                </span>
              </div>
              <small id="last-updated">
                {lastSuccess ? '最近更新 ' + lastSuccess : '等待首次读取'}
              </small>
            </div>
          </div>
          {error && (
            <div id="connection-warning" className="connection-warning" role="status">
              {error}。
              {data
                ? '以下为最后成功快照，数据已过期；输入与原请求标识保留。'
                : '尚无实时组织数据，请从本机启动链接连接。'}
            </div>
          )}
          <section id="console-controls" className="console-controls" aria-label="组织操作">
            <div className="console-buttons">
              <CommandButton kind="create">
                <Plus size={15} />
                新建组织
              </CommandButton>
              <CommandButton kind="start" primary>
                <Play size={14} />
                启动／继续
              </CommandButton>
              <CommandButton kind="pause">
                <Pause size={14} />
                暂停派发
              </CommandButton>
              <CommandButton kind="event">
                <MessageSquarePlus size={15} />
                提交事件
              </CommandButton>
              {data?.execution_state === 'unknown' && (
                <CommandButton kind="reconcile">核对执行</CommandButton>
              )}
            </div>
            <p className="console-hint">
              {!connected
                ? '连接后可读取组织；操作前需要取得有效会话与当前快照。'
                : session?.role === 'observer'
                  ? '观察者会话：可读取与下载，不能提交组织操作。'
                  : '操作先预览，再提交。受理后的实际结果保存在操作回执中。'}
            </p>
            {pending
              .filter((p) => !p.organization_id || p.organization_id === orgId)
              .map((p) => (
                <p className="pending-note" key={p.id}>
                  请求 {p.id} 尚待最终回执{' '}
                  <button
                    className="text-button"
                    data-query-receipt={p.id}
                    onClick={() => inspect(p)}
                  >
                    查询原请求
                  </button>
                </p>
              ))}
          </section>
          <div id="view">
            {data ? (
              <Outlet />
            ) : (
              <Card
                title={session && !session.organizations.length ? '从一个目标开始' : '连接本机组织'}
              >
                <Empty
                  title={
                    session && !session.organizations.length
                      ? '尚未创建组织'
                      : loading
                        ? '正在读取组织'
                        : '尚无实时数据'
                  }
                >
                  {session && !session.organizations.length
                    ? '创建并采用章程后，再明确启动有限运行。创建不会自动调用模型。'
                    : '从本机启动链接建立会话后，显示组织的实际记录。'}
                </Empty>
              </Card>
            )}
          </div>
          <footer className="data-footer">
            <span id="snapshot-meta">
              {data
                ? `${data.organization.id} · 状态 v${data.organization.version} · 章程 v${data.organization.charter_version} · 快照 ${data.snapshot_sequence} · 采集 ${data.collected_at}`
                : '尚无组织快照'}
            </span>
            <span>读取和刷新不派发工作</span>
          </footer>
        </main>
      </div>
    </>
  );
}
