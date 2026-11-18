import type { GovernedAURead } from '../api/types';
import { Card } from '../components/ui';
import { GovernanceButton } from '../features/governance/GovernanceProvider';

export const governanceStatus = { prepared: '治理准备中', active: '本地治理有效', unavailable: '治理当前不可用', exited: '治理已退出' };

/** The current governance projection; no Work execution or route dispatch. */
export function OrganizationGovernance({ read }: { read: GovernedAURead }) {
  const { au } = read;
  const governance = au.governance;
  return <>
    <Card title="组织目的" action={<GovernanceButton kind="set_goal" />}>
      <p className="au-text">{au.goal}</p>
      <p>内部文字记录：{read.capabilities.local_submission ? '已启用' : '未启用'}</p>
    </Card>
    {read.readiness_gaps.length > 0 && <div className="connection-warning" role="status">
      <p>当前治理读取报告的缺口：</p><ul>{read.readiness_gaps.map(gap => <li key={gap}>{gap}</li>)}</ul>
    </div>}
    <Card title="当前治理">
      <p>{governanceStatus[read.governance_status]} · 政策版本 {au.policy_version}</p>
      <p>当前治理权来自有效规则。初始主体是创建历史，账号或宿主访问不会替代当前授权。</p>
      <p>有效期限：{governance.valid_until === null ? '尚未启用' : new Date(governance.valid_until * 1000).toLocaleString('zh-CN')}</p>
      <details><summary>治理主体与程序</summary><dl className="au-facts">
        <div><dt>当前治理主体</dt><dd>{governance.current_principal_id}</dd></div>
        <div><dt>最终决定方</dt><dd>{governance.final_decision_principal_id}</dd></div>
        <div><dt>初始治理主体</dt><dd>{au.governance_root.governor_principal_id}</dd></div>
        <div><dt>失能处理</dt><dd>{governance.unavailability.mode === 'exit_after_timeout' ? '到期后退出' : '到期后由已确认后继者接任'}</dd></div>
      </dl></details>
      <div className="governance-actions"><GovernanceButton kind="activate_governance" primary /><GovernanceButton kind="renew_governance" /><GovernanceButton kind="acknowledge_recovery" /><GovernanceButton kind="accept_governance" /><GovernanceButton kind="recover_governance" /><GovernanceButton kind="configure_governance" /><GovernanceButton kind="nominate_governor" /><GovernanceButton kind="exit_governance" /></div>
    </Card>
    <Card title={`当前章程 · v${au.charter_version}`} action={<GovernanceButton kind="amend_charter" />}><p className="au-text">{au.charter.text}</p><p>修订须按当前规则采用，预览与保存输入不会自动生效。</p></Card>
    <Card title="成员与责任"><p>当前有 {Object.values(au.bindings).filter(item => item.active).length} 项有效职责绑定。完整成员、AI 工作交接与权限说明仍在接通。</p></Card>
  </>;
}
