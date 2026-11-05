import type { CoreAURead } from '../../api/types';
import { isGovernedAU } from '../../api/core-boundary';
import { Json } from '../../components/ui';
import { effects, titles, type GovernanceDraft } from './model';
import type { GovernanceConfig, GovernanceRequest } from './types';

export function GovernancePreview({
  draft,
  request,
  current,
}: {
  draft: GovernanceDraft;
  request: GovernanceRequest;
  current: CoreAURead;
}) {
  const labels: Record<string, string> = {
    goal: '拟采用目标',
    reason: '决定依据',
    principal_id: '目标核心身份',
    name: '成员姓名',
    duty: '职责',
    title: '工作标题',
    instruction: '工作说明',
    content: '提交内容',
    work_id: '工作',
    binding_id: '责任绑定',
    responsible_binding_id: '工作责任',
    from_binding_id: '原责任',
    to_binding_id: '接收责任',
    mandate_id: '授权',
    parent_id: '授权来源',
    attempt_id: '提交记录',
    status: '工作状态',
  };
  const display = (name: string, value: unknown) => {
    if (isGovernedAU(current) && typeof value === 'string') {
      const { au } = current;
      if (name.includes('binding') && au.bindings[value])
        return `${au.members[au.bindings[value].member_id]?.name} · ${au.bindings[value].duty}`;
      if (name === 'work_id' && au.work[value]) return au.work[value].title;
    }
    if (name === 'status') return value === 'stopped' ? '停止' : '开放';
    return value === null
      ? name === 'principal_id'
        ? '取消当前提名'
        : '当前治理者直接授权'
      : String(value);
  };
  const config = request.data.config as GovernanceConfig | undefined;
  const charter = request.data.charter as CoreAURead['au']['charter'] | undefined;
  return (
    <section className="preview-panel" aria-label="治理提交预览">
      <h3>{titles[draft.kind]} · 提交预览</h3>
      <p>{effects[draft.kind]}</p>
      <p>
        AU：{current.au.name} · 基准版本 v{request.base_version} · 政策 v{current.au.policy_version}
      </p>
      {request.kind === 'set_goal' && (
        <>
          <p>当前目标</p>
          <p className="au-text">{current.au.goal}</p>
        </>
      )}
      {config && (
        <dl className="au-facts">
          <div>
            <dt>最终决定方</dt>
            <dd>{config.final_decision_principal_id}</dd>
          </div>
          <div>
            <dt>失能程序</dt>
            <dd>
              {config.unavailability.mode === 'exit_after_timeout'
                ? '到期退出'
                : '由已确认后继者接任'}{' '}
              · {config.unavailability.timeout_seconds} 秒
            </dd>
          </div>
          {config.unavailability.successor_principal_id && (
            <div>
              <dt>后继者</dt>
              <dd>{config.unavailability.successor_principal_id}</dd>
            </div>
          )}
        </dl>
      )}
      {charter && (
        <>
          <p>当前章程</p>
          <p className="au-text">{current.au.charter.text}</p>
          <p>拟采用章程</p>
          <p className="au-text">{charter.text}</p>
          <p>
            内部文字记录：{charter.allowed_operations.includes('record_memory') ? '允许' : '撤销'}
            ；修章入口：{charter.board_can_amend ? '允许' : '关闭'}。
          </p>
        </>
      )}
      <dl className="au-facts">
        {Object.entries(request.data)
          .filter(([key]) => key in labels)
          .map(([key, value]) => (
            <div key={key}>
              <dt>{labels[key]}</dt>
              <dd className="au-text">{display(key, value)}</dd>
            </div>
          ))}
      </dl>
      {'can_delegate' in request.data && (
        <p>继续再委托：{request.data.can_delegate ? '允许在父级范围内' : '不允许'}。</p>
      )}
      <details>
        <summary>查看完整提交内容</summary>
        <Json value={request.data} />
      </details>
      <p className="form-note">只有服务器回执确认后才生效。确认前取消不会提交。</p>
    </section>
  );
}
