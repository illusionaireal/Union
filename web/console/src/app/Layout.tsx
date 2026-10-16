import { useEffect } from 'react';
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom';
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
  Cpu,
  ArrowUpRight,
} from 'lucide-react';
import { useWorkspace } from './workspace';
import { CommandButton, useCommands } from '../features/commands/CommandProvider';
import { Card, Empty, sourceName } from '../components/ui';

const pages = [
  {
    key: 'overview',
    label: '公司总览',
    title: '公司总览',
    description: '把目标交给团队，把进展带回这里。',
    icon: LayoutDashboard,
    group: '工作空间',
  },
  {
    key: 'members',
    label: '成员与岗位',
    title: '团队与责任',
    description: '了解每位成员的职责，以及工作如何在团队中流转。',
    icon: Users,
  },
  {
    key: 'tasks',
    label: '工作',
    title: '工作与协作',
    description: '从目标拆解到实际交付，查看每一步的负责人和依赖。',
    icon: ListChecks,
  },
  {
    key: 'artifacts',
    label: '成果',
    title: '成果资料库',
    description: '查看团队交付的内容，沿版本与来源追溯每一份成果。',
    icon: Files,
  },
  {
    key: 'activity',
    label: '活动',
    title: '活动与决定',
    description: '了解发生了什么，以及为什么作出下一步安排。',
    icon: History,
  },
  {
    key: 'models',
    label: '模型与 API',
    title: '模型与 API',
    description: '连接模型服务，为当前公司配置实际执行能力。',
    icon: Cpu,
    group: '运行管理',
  },
  {
    key: 'resources',
    label: '执行与资源',
    title: '执行与资源',
    description: '掌握调用额度、运行状态，以及需要处理的异常。',
    icon: Activity,
  },
  {
    key: 'settings',
    label: '组织设置',
    title: '公司治理与设置',
    description: '管理目标、章程和资源，查看已提交操作的实际结果。',
    icon: Settings,
  },
];
export function Layout() {
  const { session, data, orgId, selectOrg, connected, error, lastSuccess, loading, refresh } =
    useWorkspace();
  const { pending, inspect } = useCommands();
  const location = useLocation();
  const page = pages.find((p) => '/' + p.key === location.pathname) || pages[0];
  const search = orgId ? '?organization=' + encodeURIComponent(orgId) : '';
  const openPage = page.key === 'overview' || page.key === 'models';
  useEffect(() => {
    document.title = page.label + ' · UNION';
  }, [page.label]);
  return (
    <>
      <a className="skip" href="#main">
        跳转到正文
      </a>
      <aside className="sidebar" aria-label="工作台导航">
        <NavLink to={{ pathname: '/overview', search }} className="brand">
          <span className="brand-symbol">u</span>
          <span>
            UNION<small>YOUR AI COMPANY</small>
          </span>
        </NavLink>
        <label className="workspace-switch">
          <span className="org-icon">{data?.organization.name.slice(0, 1) || 'U'}</span>
          <span className="workspace-select">
            <small>当前公司</small>
            <select
              id="org-select"
              aria-label="当前组织"
              value={orgId}
              onChange={(e) => selectOrg(e.target.value)}
            >
              {!session?.organizations.length && <option value="">尚未创建公司</option>}
              {session?.organizations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </span>
        </label>
        <nav id="navigation">
          {pages.map(({ key, label, icon: Icon, group }) => (
            <div className="nav-entry" key={key}>
              {group && <div className="nav-caption">{group}</div>}
              <NavLink
                to={{ pathname: '/' + key, search }}
                data-nav={key}
                className={({ isActive }) => 'nav-button' + (isActive ? ' active' : '')}
              >
                <Icon size={19} strokeWidth={1.7} />
                <span>{label}</span>
                {key === 'models' && !data?.execution_config.api_connection_id && (
                  <span className="nav-tag">配置</span>
                )}
              </NavLink>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <Link className="sidebar-connect" to={{ pathname: '/models', search }}>
            <Cpu size={20} />
            <div>
              <strong>连接你的模型</strong>
              <small>API 地址 · 密钥 · 模型</small>
            </div>
            <ArrowUpRight size={16} />
          </Link>
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
              <small>本地工作空间 · 记录持久保存</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <span>工作空间</span>
            <span>/</span>
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
              <div className="eyebrow">UNION / {page.key.toUpperCase()}</div>
              <h1 id="page-title">{page.title}</h1>
              <p id="page-description">{page.description}</p>
            </div>
            <div className="connection">
              <div>
                <span className={'dot ' + (connected ? 'green' : 'amber')} />
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
                : '请从本机启动链接连接工作台。'}
            </div>
          )}
          {page.key === 'overview' && data && (
            <section id="console-controls" className="console-controls" aria-label="组织操作">
              <div className="console-buttons">
                <CommandButton kind="start" primary>
                  <Play size={15} />
                  启动／继续
                </CommandButton>
                <CommandButton kind="pause">
                  <Pause size={15} />
                  暂停派发
                </CommandButton>
                <CommandButton kind="event">
                  <MessageSquarePlus size={15} />
                  提交事件
                </CommandButton>
                <CommandButton kind="create">
                  <Plus size={15} />
                  新建公司
                </CommandButton>
                {data.execution_state === 'unknown' && (
                  <CommandButton kind="reconcile">核对执行</CommandButton>
                )}
              </div>
              <p className="console-hint">
                {session?.role === 'observer'
                  ? '观察者可以查看与下载，配置和运行由发起人操作。'
                  : '先确认调用范围，再启动。操作进展与结果均有回执。'}
              </p>
            </section>
          )}
          {pending
            .filter((p) => !p.organization_id || p.organization_id === orgId)
            .map((p) => (
              <p className="pending-note" key={p.id}>
                有一项操作等待回执{' '}
                <button
                  className="text-button"
                  data-query-receipt={p.id}
                  onClick={() => inspect(p)}
                >
                  查询原请求
                </button>
              </p>
            ))}
          <div id="view">
            {data || openPage ? (
              <Outlet />
            ) : (
              <Card title="先建立你的公司">
                <Empty title={loading ? '正在读取组织' : '这里将保存公司的工作记录'}>
                  完成创建后，在这里查看团队、协作和成果。
                </Empty>
                <div className="empty-actions">
                  <CommandButton kind="create" primary>
                    创建我的 AI 公司
                  </CommandButton>
                  <Link className="button secondary" to={{ pathname: '/overview', search }}>
                    回到总览
                  </Link>
                </div>
              </Card>
            )}
          </div>
          <footer className="data-footer">
            <details>
              <summary>
                <ShieldCheck size={13} />
                数据与运行记录
              </summary>
              <span id="snapshot-meta">
                {data
                  ? data.organization.id +
                    ' · 状态 v' +
                    data.organization.version +
                    ' · 章程 v' +
                    data.organization.charter_version +
                    ' · 快照 ' +
                    data.snapshot_sequence +
                    ' · 采集 ' +
                    data.collected_at
                  : '尚无组织快照'}
              </span>
            </details>
            <span>读取和刷新不派发工作</span>
          </footer>
        </main>
      </div>
    </>
  );
}
