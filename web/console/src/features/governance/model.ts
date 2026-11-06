import type { CoreAURead, Session } from '../../api/types';
import { isGovernedAU } from '../../api/core-boundary';
import type { GovernanceKind, GovernanceRequest } from './types';

export const titles: Record<GovernanceKind, string> = {
  adopt_governance: '采用本地治理',
  configure_governance: '调整治理程序',
  acknowledge_recovery: '确认恢复职责',
  activate_governance: '启用本地治理',
  renew_governance: '续期治理',
  nominate_governor: '提名治理接任者',
  accept_governance: '确认接任治理',
  recover_governance: '按失能程序接任',
  exit_governance: '退出治理',
  amend_charter: '修订章程',
  set_goal: '更新目标',
  appoint: '登记责任成员',
  update_appointment: '修改职责',
  create_work: '创建内部工作',
  update_work: '调整工作',
  grant_mandate: '授予文字记录授权',
  revoke_mandate: '撤销授权',
  handoff_responsibility: '交接责任',
  begin_local_action: '开始文字提交',
  submit_local_result: '提交文字内容',
  accept_local_result: '采用提交内容',
};
export const effects: Record<GovernanceKind, string> = {
  adopt_governance: '采用后保存治理程序，仍需明确启用。只支持本地内部文字记录。',
  configure_governance: '新程序会清除原恢复确认与提名，并回到准备态。原授权需按当前版本核对。',
  acknowledge_recovery: '你确认承担此政策版本的恢复职责，当前不会取得普通治理权。',
  activate_governance:
    '启用本地治理和明确获准的内部文字记录。不会运行 AI、使用资源或作出外部承诺。',
  renew_governance: '由服务器按当前程序重设有效期限。浏览页面不会自动续期。',
  nominate_governor: '提名本身不交出治理权；接任者须以自己的核心账号确认。',
  accept_governance: '当前治理权交给你，初始主体保留在历史中。接任后需重新核对治理程序并启用。',
  recover_governance: '按预先确认的失能程序接任。原责任与在途内容保留，接任后回到准备态。',
  exit_governance: '退出后停止本地治理行动。原责任、未完成工作与提交记录保留，不等于取消远程操作。',
  amend_charter:
    '按当前章程决定此次修订；新规则不能为本次修订补授权。原版本的授权与尝试需重新核对。',
  set_goal: '修改当前目标。旧目标版本下的尝试不能直接采用。',
  appoint: '登记一名人类责任成员及独立职责绑定；尚未授予任何工作授权。',
  update_appointment: '增加职责版本。旧职责版本的授权与提交尝试不能继续采用。',
  create_work: '保存内部工作和明确责任，不派发模型或工具。执行前还需单独授予授权。',
  update_work: '工作范围与版本变化后，旧授权和旧尝试需要重新核对。停止的工作不接受新行动或采用。',
  grant_mandate: '只授予该工作的内部文字记录权限。再委托受父级范围、任职和当前版本约束。',
  revoke_mandate: '该授权及其后代失效；已发出的尝试不能继续采用。其他独立工作的授权不因此改变。',
  handoff_responsibility:
    '沿原工作标识交接未完成责任，旧职责绑定失效。原尝试与已采用历史保留；接收者需重新获权。',
  begin_local_action: '开始一项人类手工文字提交，固定当前责任与授权版本。这不是 AI 执行。',
  submit_local_result: '内容先提交供核对。授权已失效的迟到内容仅保存为未采用，不完成工作。',
  accept_local_result: '再次核对原提交的身份、范围、期限和全部版本；通过后采用内容并完成原工作。',
};
export interface GovernanceScope {
  principalId: string;
  serviceInstance: string;
  organizationId: string;
}
export interface GovernanceDraft {
  key: string;
  kind: GovernanceKind;
  read: CoreAURead;
  scope: GovernanceScope;
  defaults: Record<string, string>;
}
export function sameScope(
  scope: GovernanceScope,
  session: Session | undefined,
  organizationId: string,
) {
  return (
    !!session?.principal_id &&
    session.core_protocol === 'core.au.v1' &&
    scope.principalId === session.principal_id &&
    scope.serviceInstance === session.service_instance &&
    scope.organizationId === organizationId
  );
}
export function available(read: CoreAURead, kind: GovernanceKind): boolean {
  return isGovernedAU(read) ? read.access.commands.includes(kind) : kind === 'adopt_governance';
}
/** Non-content target identity keeps an unknown write local to its affected subject. */
export function commandTarget(kind: GovernanceKind, data: GovernanceRequest['data']): string {
  const key: Partial<Record<GovernanceKind, string>> = {
    appoint: 'principal_id',
    create_work: 'responsible_binding_id',
    update_appointment: 'binding_id',
    handoff_responsibility: 'from_binding_id',
    revoke_mandate: 'mandate_id',
    grant_mandate: 'work_id',
    update_work: 'work_id',
    begin_local_action: 'work_id',
    submit_local_result: 'attempt_id',
    accept_local_result: 'attempt_id',
  };
  return key[kind] ? String(data[key[kind]!] ?? '') : 'governance';
}
const reservedMatters = ['charter', 'goal', 'resources', 'appointments', 'mandates', 'dissolution'];
export function readGovernanceForm(
  draft: GovernanceDraft,
  form: HTMLFormElement,
): GovernanceRequest['data'] {
  const values = new FormData(form);
  const str = (name: string) => String(values.get(name) ?? '').trim();
  for (const field of form.querySelectorAll<
    HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
  >('[required]')) {
    if (!field.disabled && !field.value.trim()) throw new Error('请填写必填内容或选择已有记录');
  }
  const reason = str('reason');
  const work_id = str('work_id'),
    binding_id = str('binding_id'),
    attempt_id = str('attempt_id');
  switch (draft.kind) {
    case 'adopt_governance':
    case 'configure_governance':
      return {
        reason,
        config: {
          profile: 'local_governance.v1',
          final_decision_principal_id: isGovernedAU(draft.read)
            ? draft.read.au.governance.current_principal_id
            : draft.read.au.governance_root.governor_principal_id,
          reserved_matters: reservedMatters,
          unavailability: {
            mode: str('unavailability_mode'),
            timeout_seconds: Number(str('timeout_seconds')),
            ...(str('unavailability_mode') === 'successor_after_timeout'
              ? { successor_principal_id: str('successor_principal_id') }
              : {}),
          },
        },
      };
    case 'nominate_governor':
      return {
        principal_id: values.get('cancel_nomination') === 'on' ? null : str('principal_id'),
        reason,
      };
    case 'set_goal':
      return { goal: str('goal'), reason };
    case 'amend_charter':
      return {
        reason,
        charter: {
          ...draft.read.au.charter,
          text: str('charter_text'),
          board_can_amend: values.get('board_can_amend') === 'on',
          allowed_operations: [
            ...draft.read.au.charter.allowed_operations.filter(
              (operation) => operation !== 'record_memory',
            ),
            ...(values.get('record_memory') === 'on' ? ['record_memory'] : []),
          ],
          allowed_tools: [
            ...draft.read.au.charter.allowed_tools.filter((tool) => tool !== 'read_document'),
            ...(values.get('read_document') === 'on' ? ['read_document'] : []),
          ],
        },
      };
    case 'appoint':
      return {
        member_id: str('member_id'),
        binding_id,
        principal_id: str('principal_id'),
        name: str('name'),
        duty: str('duty'),
      };
    case 'update_appointment':
      return { binding_id, duty: str('duty'), reason };
    case 'create_work':
      return {
        work_id,
        title: str('title'),
        instruction: str('instruction'),
        responsible_binding_id: binding_id,
      };
    case 'update_work':
      return {
        work_id,
        title: str('title'),
        instruction: str('instruction'),
        status: str('status'),
        reason,
      };
    case 'grant_mandate':
      return {
        mandate_id: str('mandate_id'),
        work_id,
        binding_id,
        parent_id: str('parent_id') || null,
        actions: ['record_memory'],
        can_delegate: values.get('can_delegate') === 'on',
      };
    case 'revoke_mandate':
      return { mandate_id: str('mandate_id'), reason };
    case 'handoff_responsibility':
      return {
        from_binding_id: str('from_binding_id'),
        to_binding_id: str('to_binding_id'),
        reason,
      };
    case 'begin_local_action':
      return { attempt_id, work_id, mandate_id: str('mandate_id') };
    case 'submit_local_result':
      return { attempt_id, content: String(values.get('content') ?? '') };
    case 'accept_local_result':
      return { attempt_id, reason };
    default:
      return { reason };
  }
}
