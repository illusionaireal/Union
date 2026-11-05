import type { GovernedAURead } from '../../api/types';
import { Card, Empty } from '../../components/ui';
import { GovernanceButton } from './GovernanceProvider';

const workStatuses = {
  open: '开放',
  stopped: '已停止',
  delivered: '已完成',
  needs_review: '待核对',
};
const attemptStatuses = {
  open: '待提交内容',
  submitted: '已提交，待采用',
  not_adopted: '未采用',
  accepted: '已采用',
};
export function ResponsibilityWorkspace({ read }: { read: GovernedAURead }) {
  const { au } = read;
  const bindings = Object.values(au.bindings),
    work = Object.values(au.work);
  const mandates = Object.values(au.mandates),
    attempts = Object.values(au.attempts),
    results = Object.values(au.results);
  const name = (bindingId: string) =>
    au.members[au.bindings[bindingId]?.member_id]?.name ?? bindingId;
  return (
    <section className="governance-workspace" aria-label="责任与工作">
      <p className="governance-boundary">受控内部记录 · 人类手工提交</p>
      <Card title="责任成员" action={<GovernanceButton kind="appoint" primary />}>
        {bindings.length ? (
          <ul className="governance-records">
            {bindings.map((binding) => (
              <li key={binding.id}>
                <div className="governance-record-heading">
                  <h3>{name(binding.id)}</h3>
                  <span className="quiet-pill">
                    {binding.active ? '职责有效' : '职责已失效'} · v{binding.version}
                  </span>
                </div>
                <p className="au-text">{binding.duty}</p>
                <details>
                  <summary>身份与职责标识</summary>
                  <p>核心主体 {au.members[binding.member_id]?.principal_id}</p>
                  <p>
                    人类成员 {binding.member_id} · 职责 {binding.id}
                  </p>
                </details>
                {binding.active && (
                  <div className="governance-actions">
                    <GovernanceButton
                      kind="update_appointment"
                      defaults={{ binding_id: binding.id }}
                    />
                    <GovernanceButton
                      kind="handoff_responsibility"
                      defaults={{ from_binding_id: binding.id }}
                    />
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="先明确一位责任成员">
            可登记你本人；单主体 AU 无需另外创建成员或层级。登记职责不自动授予工作权限。
          </Empty>
        )}
      </Card>
      <Card title="内部工作" action={<GovernanceButton kind="create_work" primary />}>
        {work.length ? (
          <ul className="governance-records">
            {work.map((item) => (
              <li key={item.id}>
                <div className="governance-record-heading">
                  <h3>{item.title}</h3>
                  <span className="quiet-pill">
                    {workStatuses[item.status]} · v{item.version}
                  </span>
                </div>
                <p className="au-text">{item.instruction}</p>
                <p>责任人：{name(item.responsible_binding_id)}</p>
                {item.status === 'needs_review' && (
                  <p>请先通过“调整工作”核对交接内容并明确继续，再为新责任成员授予授权。</p>
                )}
                <div className="governance-actions">
                  <GovernanceButton kind="update_work" defaults={{ work_id: item.id }} />
                  <GovernanceButton
                    kind="grant_mandate"
                    defaults={{ work_id: item.id, binding_id: item.responsible_binding_id }}
                  />
                  <GovernanceButton
                    kind="begin_local_action"
                    defaults={{ work_id: item.id }}
                    primary
                  />
                </div>
                <details>
                  <summary>原工作标识与交接历史</summary>
                  <p>{item.id}</p>
                  {item.history.length ? (
                    <ol>
                      {item.history.map((entry, index) => (
                        <li key={index}>
                          {name(entry.from_binding_id)} → {name(entry.to_binding_id)}：
                          {entry.reason}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p>尚无责任交接。</p>
                  )}
                </details>
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="尚无内部工作">为有效责任成员创建工作，再单独授予文字记录授权。</Empty>
        )}
      </Card>
      <Card title="有限授权">
        {mandates.length ? (
          <ul className="governance-records">
            {mandates.map((item) => (
              <li key={item.id}>
                <h3>
                  {au.work[item.work_id]?.title ?? item.work_id} · {name(item.binding_id)}
                </h3>
                <p>
                  {item.active ? '授权记录有效' : '已撤销'} · 仅内部文字记录 ·{' '}
                  {item.can_delegate ? '允许有限再委托' : '不可再委托'}。
                </p>
                <p className="form-note">动作与采用时仍核对全部祖先、当前职责、政策和期限。</p>
                <details>
                  <summary>授权依据与版本</summary>
                  <p>
                    {item.id} · v{item.version} · 职责 v{item.binding_version}
                  </p>
                  <p>父级 {item.parent_id ?? '当前治理者直接授予'}</p>
                </details>
                {item.active && (
                  <GovernanceButton kind="revoke_mandate" defaults={{ mandate_id: item.id }} />
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="尚无有限授权">责任绑定与工作不会自动产生行动权限。</Empty>
        )}
      </Card>
      <Card title="文字提交与采用">
        {attempts.length ? (
          <ul className="governance-records">
            {attempts.map((attempt) => (
              <li key={attempt.id}>
                <div className="governance-record-heading">
                  <h3>{au.work[attempt.work_id]?.title ?? attempt.work_id}</h3>
                  <span className="quiet-pill">{attemptStatuses[attempt.status]}</span>
                </div>
                <p>提交人：{au.members[attempt.member_id]?.name ?? attempt.member_id}</p>
                {attempt.content && <blockquote className="au-text">{attempt.content}</blockquote>}
                {attempt.status === 'not_adopted' && (
                  <p>内容保留为未采用记录，不改变已采用成果。{attempt.authority_reason}</p>
                )}
                <details>
                  <summary>原提交身份与版本</summary>
                  <p>
                    {attempt.id} · 核心主体 {attempt.principal_id}
                  </p>
                  <p>
                    工作 v{attempt.work_version} · 职责 v{attempt.binding_version} · 章程 v
                    {attempt.charter_version} · 政策 v{attempt.policy_version} · 目标 v
                    {attempt.goal_version}
                  </p>
                  <p>
                    授权链：
                    {attempt.mandates.map((item) => `${item.id} v${item.version}`).join(' → ')}
                  </p>
                </details>
                <div className="governance-actions">
                  {attempt.status === 'open' &&
                    attempt.principal_id === read.access.principal_id && (
                      <GovernanceButton
                        kind="submit_local_result"
                        defaults={{ attempt_id: attempt.id }}
                        primary
                      />
                    )}
                  {attempt.status === 'submitted' && (
                    <GovernanceButton
                      kind="accept_local_result"
                      defaults={{ attempt_id: attempt.id }}
                      primary
                    />
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="尚无文字提交">
            责任人明确开始提交后，再填写内容。每次采用都会重新核对当前授权。
          </Empty>
        )}
      </Card>
      <Card title="已采用的内部记录">
        {results.length ? (
          <ul className="governance-records">
            {results.map((result) => (
              <li key={result.id}>
                <h3>{au.work[result.work_id]?.title ?? result.work_id}</h3>
                <p className="au-text">{result.content}</p>
                <p className="form-note">
                  原作者 {au.members[result.author_member_id]?.name ?? result.author_member_id} ·{' '}
                  {result.created_at}
                </p>
                <details>
                  <summary>采用来源</summary>
                  <p>
                    原工作 {result.work_id} · 提交 {result.attempt_id}
                  </p>
                  <p>采用主体 {result.accepted_by}</p>
                  <p>内容摘要 {result.sha256}</p>
                </details>
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="尚无已采用内容">已提交和已采用分别记录；这里的内容是受控内部记录。</Empty>
        )}
      </Card>
    </section>
  );
}
