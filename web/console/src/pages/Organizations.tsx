import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { useWorkspace } from '../app/workspace';
import { organizationPath, type OrganizationSection } from '../app/organization-routes';
import { isGovernedAU } from '../api/core-boundary';
import { Card } from '../components/ui';
import { CommandButton } from '../features/commands/CommandProvider';
import CoreModels from '../features/models/CoreModels';
import { CoreMaterials } from '../features/materials/CoreMaterials';
import { MaterialWorkPreparation } from '../features/materials/MaterialWorkPreparation';
import { GovernanceButton } from '../features/governance/GovernanceProvider';
import { OrganizationGovernance, governanceStatus } from './OrganizationGovernance';

export function EntryProblem() {
  const { error } = useWorkspace();
  return <section className="organization-problem">
    <h2>暂时无法打开这个入口</h2>
    <p role="alert">{error || '当前账户没有可核验的组织记录，或链接已失效。'}</p>
    <Link className="button secondary" to="/organizations">返回组织列表</Link>
  </section>;
}

export function Organizations() {
  const { session, connected, loading, error } = useWorkspace();
  const location = useLocation();
  const organizations = session?.organizations.filter(item => item.profile === 'core_v1') ?? [];
  if (loading && !session) return <p role="status">正在读取有权访问的组织…</p>;
  return <>
    <div className="organization-intro">
      <div><h2>从一个明确的目的开始</h2><p>选择一个组织继续，或创建新的组织，保存目的与边界。一个 Agent 也可以组成 AU。</p></div>
      <CommandButton kind="create_v1" primary>创建组织</CommandButton>
    </div>
    {!connected && <p role="status" className="connection-warning">暂时无法核验当前组织列表。{error} 恢复连接后可继续。</p>}
    {connected && !session?.principal_id && <p role="status">当前登录尚未绑定核心身份，请通过账号与登录建立或登录核心账户。</p>}
    {new URLSearchParams(location.search).get('entry') === 'platform' && <p role="status">这里是独立核心的组织入口。平台网关管理由可选平台提供。</p>}
    {organizations.length ? <ul className="organization-list" aria-label="可访问的组织">
      {organizations.map(item => <li key={item.id}><Link to={organizationPath(item.id)}>
        <span><strong>{item.name}</strong><small>打开后核对当前状态与准备条件</small></span><ArrowUpRight size={21} aria-hidden="true" />
      </Link></li>)}
    </ul> : connected && <section className="organization-empty"><h2>还没有可访问的 V1 组织</h2><p>创建后会绑定你的核心账户。保存准备记录不会调用模型，也不会自动使用资源。</p></section>}
  </>;
}

export function OrganizationOverview() {
  const { core } = useWorkspace();
  if (!core) return null;
  const governed = isGovernedAU(core) ? core : undefined;
  return <>
    <section className="organization-purpose"><span className="eyebrow">AI-UNION / AU</span><h2>{core.au.name}</h2><p className="au-text">{core.au.goal}</p></section>
    <dl className="organization-state">
      <div><dt>治理</dt><dd>{governed ? governanceStatus[governed.governance_status] : '准备中 · 尚未采用'}</dd></div>
      <div><dt>资源计划</dt><dd>计划 {core.au.resources.max_calls} 次调用</dd></div>
      <div><dt>自主业务</dt><dd>尚未启用</dd></div>
    </dl>
    <p className="form-note">资源计划与实际授权、用量分开核对。当前页面未汇总工作与成果，不据此推断组织没有工作或资源消耗。</p>
    <PreparationGaps />
    <div className="organization-next">
      <Link to={organizationPath(core.au.id, 'work')}><h2>工作</h2><p>查看持续工作入口及当前支持范围。</p><span>前往工作 →</span></Link>
      <Link to={organizationPath(core.au.id, 'results')}><h2>成果</h2><p>了解成果阅读、版本和反馈的接入状态。</p><span>前往成果 →</span></Link>
    </div>
  </>;
}

function PreparationGaps() {
  const { core } = useWorkspace();
  if (!core) return null;
  const governed = isGovernedAU(core) ? core : undefined;
  return <Card title="继续准备">
    <ul className="organization-preparation">
      <li><div><h3>治理与责任边界</h3><p>{governed ? '按当前有效规则处理权限、期限和责任。' : '初始治理主体已绑定。需要核对适用规则、保留事项与治理不可用时的处理程序。'}</p></div><Link className="button secondary" to={organizationPath(core.au.id, 'governance')}>查看治理</Link></li>
      <li><div><h3>能力与资源</h3><p>模型连接、工具权限和有限资源需要分别准备；创建本身不会授予调用。</p></div><Link className="button secondary" to={organizationPath(core.au.id, 'resources')}>准备资源</Link></li>
    </ul>
    {!!governed?.readiness_gaps.length && <div role="status"><p>当前治理读取报告的缺口：</p><ul>{governed.readiness_gaps.map(gap => <li key={gap}>{gap}</li>)}</ul></div>}
  </Card>;
}

const gaps = {
  work: ['持续工作入口正在接通', '当前尚不能从这里提交一次完整工作意图并自动推进到交付。原工作、责任和未完成执行仍保留。'],
  results: ['成果阅读入口正在接通', '当前尚未接通按组织、工作和成果版本读取的完整页面。原成果仍保留，页面空白不表示没有成果。'],
  improvement: ['改进记录尚未接通', '低影响试用需要已有授权、版本、检查和撤回依据；效果比较与采用仍需各自证据。'],
  collaboration: ['组织合作尚未接通', '合作需要双方确认承诺、交付与争议处理；组织之间不会因显示在同一空间而获得对方权限。'],
} as const;

export function OrganizationSectionPage({ section }: { section: OrganizationSection }) {
  const { core } = useWorkspace();
  const { workId, resultId } = useParams();
  if (!core) return null;
  if (section === 'resources') return <><CoreModels /><CoreMaterials /></>;
  if (section === 'work') return <MaterialWorkPreparation workId={workId} />;
  if (section === 'governance') return <>{isGovernedAU(core)
    ? <OrganizationGovernance read={core} />
    : <><Card title="初始治理与章程"><p>初始治理主体已绑定创建账户。显示名称不授予权限。</p><p>治理显示名称：{core.au.board_name}</p><p className="au-text">{core.au.charter.text}</p><p>章程内容已保存，尚未采用为有效治理规则。</p><GovernanceButton kind="adopt_governance" primary /></Card><PreparationGaps /></>}</>;
  if (section === 'attention') return <><PreparationGaps /><Card title="工作关注事项尚未汇总"><p>当前只呈现组织准备条件。工作等待、原执行核对和恢复事项仍需接通专属投影，不能把这里视为没有待处理事项。</p></Card></>;
  const gap = gaps[section as keyof typeof gaps];
  if (!gap) return null;
  return <Card title={gap[0]}><p>{gap[1]}</p>{workId && <p>当前链接指向指定工作{resultId ? '及其成果' : ''}，此页面尚未读取对应正文。</p>}<Link className="button secondary" to={organizationPath(core.au.id)}>返回组织概况</Link></Card>;
}
