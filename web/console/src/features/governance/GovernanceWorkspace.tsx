import { Link, useLocation } from 'react-router-dom';
import type { GovernedAURead } from '../../api/types';
import { Card, Empty, Json } from '../../components/ui';
import { GovernanceButton } from './GovernanceProvider';
import { ResponsibilityWorkspace } from './ResponsibilityWorkspace';
import { titles } from './model';

const statuses = {
  prepared: '治理准备态',
  active: '本地治理有效',
  unavailable: '治理当前不可用',
  exited: '治理已退出',
};
const matterNames: Record<string, string> = {
  charter: '章程',
  goal: '目标',
  resources: '资源',
  appointments: '任职',
  mandates: '授权',
  dissolution: '解散',
};
export function GovernanceWorkspace({ read }: { read: GovernedAURead }) {
  const { pathname, search } = useLocation();
  const { au } = read;
  const governance = au.governance;
  if (pathname === '/tasks') return <ResponsibilityWorkspace read={read} />;
  if (pathname === '/settings')
    return (
      <section className="governance-workspace" aria-label="章程与采用记录">
        <Card
          title={`当前章程 · v${au.charter_version}`}
          action={<GovernanceButton kind="amend_charter" />}
        >
          <p className="au-text">{au.charter.text}</p>
          <p>
            内部文字记录：
            {au.charter.allowed_operations.includes('record_memory') ? '允许' : '未授权'} ·
            修章入口：{au.charter.board_can_amend ? '允许' : '关闭'}。
          </p>
          <details>
            <summary>查看保存的完整章程</summary>
            <Json value={au.charter} />
          </details>
        </Card>
        <Card title="资源计划">
          <p>
            计划调用上限 {au.resources.max_calls} 次 · 单次超时 {au.resources.timeout_seconds} 秒。
          </p>
          <p>尚未授予、预约或使用资源；本地记录不调用模型。</p>
        </Card>
        <Card title="治理采用历史">
          {read.history.length ? (
            <ol className="governance-records">
              {[...read.history].reverse().map((item) => (
                <li key={item.version}>
                  <h3>
                    {titles[item.kind]} · v{item.version}
                  </h3>
                  <p>{item.reason}</p>
                  <p className="form-note">
                    主体 {item.principal_id} · 依据政策 v{item.prior_policy_version} ·{' '}
                    {item.created_at}
                  </p>
                  <details>
                    <summary>原请求标识</summary>
                    <p>{item.command_id}</p>
                  </details>
                </li>
              ))}
            </ol>
          ) : (
            <Empty title="尚无治理采用历史">每次生效的治理命令将保留版本与采用依据。</Empty>
          )}
        </Card>
      </section>
    );
  return (
    <section className="governance-workspace" aria-label="本地治理">
      <div className="mission-panel">
        <div className="mission-copy">
          <span className="quiet-pill">{statuses[read.governance_status]}</span>
          <h2>{au.name}</h2>
          <p className="au-text">{au.goal}</p>
          <GovernanceButton kind="set_goal" />
        </div>
      </div>
      <p className="governance-boundary">
        {read.capabilities.local_submission
          ? '内部文字记录已启用；AI 执行、资源使用和对外承诺尚未启用。'
          : '当前内部文字记录尚不可执行。AI 执行、资源使用和对外承诺尚未启用。'}
      </p>
      {read.readiness_gaps.length > 0 && (
        <div role="alert" className="connection-warning">
          <strong>当前启用条件未满足</strong>
          <ul>
            {read.readiness_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
      <Card title="当前治理与期限">
        <dl className="au-facts">
          <div>
            <dt>当前治理者</dt>
            <dd>{governance.current_principal_id}</dd>
          </div>
          <div>
            <dt>最终决定方</dt>
            <dd>{governance.final_decision_principal_id}</dd>
          </div>
          <div>
            <dt>初始治理主体</dt>
            <dd>{au.governance_root.governor_principal_id}</dd>
          </div>
          <div>
            <dt>当前政策</dt>
            <dd>
              v{au.policy_version} · {statuses[read.governance_status]}
            </dd>
          </div>
          <div>
            <dt>有效期限</dt>
            <dd>
              {governance.valid_until === null
                ? '尚未启用'
                : new Date(governance.valid_until * 1000).toLocaleString('zh-CN', {
                    hour12: false,
                  })}
            </dd>
          </div>
        </dl>
        <p className="form-note">
          初始主体是创建历史。当前操作权来自有效治理与责任授权，浏览和刷新不会自动续期。
        </p>
        {read.governance_status === 'unavailable' && (
          <p role="status">请按已采用的失能程序处理当前不可用状态；未完成责任和在途内容仍保留。</p>
        )}
        <div className="governance-actions">
          <GovernanceButton kind="activate_governance" primary />
          <GovernanceButton kind="renew_governance" />
          <GovernanceButton kind="acknowledge_recovery" />
          <GovernanceButton kind="accept_governance" primary />
          <GovernanceButton kind="recover_governance" />
          <GovernanceButton kind="configure_governance" />
          <GovernanceButton kind="nominate_governor" />
          <GovernanceButton kind="exit_governance" />
        </div>
      </Card>
      <Card title="已采用的治理程序">
        <dl className="au-facts">
          <div>
            <dt>保留事项</dt>
            <dd>
              {governance.reserved_matters.map((item) => matterNames[item] ?? item).join('、')}
            </dd>
          </div>
          <div>
            <dt>失能处理</dt>
            <dd>
              {governance.unavailability.mode === 'exit_after_timeout'
                ? '到期后退出'
                : '到期后由已确认后继者接任'}{' '}
              · {governance.unavailability.timeout_seconds} 秒
            </dd>
          </div>
          {governance.unavailability.successor_principal_id && (
            <>
              <div>
                <dt>指定后继者</dt>
                <dd>{governance.unavailability.successor_principal_id}</dd>
              </div>
              <div>
                <dt>恢复职责确认</dt>
                <dd>
                  {governance.recovery_ack
                    ? `已确认政策 v${governance.recovery_ack.policy_version}`
                    : '尚待后继者自行确认'}
                </dd>
              </div>
            </>
          )}
          {governance.nomination && (
            <div>
              <dt>待确认提名</dt>
              <dd>
                {governance.nomination.principal_id}
                <p>{governance.nomination.reason}</p>
                <small>
                  提名政策 v{governance.nomination.policy_version}，须由该账号自行确认。
                </small>
              </dd>
            </div>
          )}
        </dl>
      </Card>
      <Card
        title="内部责任与工作"
        action={
          <Link className="text-button" to={{ pathname: '/tasks', search }}>
            责任与工作
          </Link>
        }
      >
        <p>
          {Object.values(au.bindings).filter((item) => item.active).length} 项有效职责 ·{' '}
          {Object.keys(au.work).length} 项内部工作 · {Object.keys(au.results).length}{' '}
          份已采用内部记录。
        </p>
        <p>登记责任成员后，明确工作与有限授权，再由责任人提交文字，最后由当前治理者核对采用。</p>
      </Card>
    </section>
  );
}
