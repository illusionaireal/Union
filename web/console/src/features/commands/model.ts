import type { Charter, CommandKind, ReceiptKind, Session, Snapshot } from '../../api/types';
export const titles: Record<ReceiptKind, string> = {
  create: '创建并采用组织',
  start: '启动／继续有限运行',
  pause: '暂停新的派发',
  event: '提交组织事件',
  resources: '调整资源',
  model: '设置默认模型',
  amend: '修订组织章程',
  reconcile: '核对未知执行',
  api_connection: '配置模型 API 连接',
  api_binding: '绑定默认 API 连接',
  api_test: '测试模型 API 连接',
};
export const defaultCharter: Charter = {
  text: '本地有限组织试验。组织在已配置资源内形成岗位和协作；无对外发布或支付权限。',
  allowed_operations: [
    'create_member',
    'create_position',
    'update_position',
    'assign',
    'set_policy',
    'create_work',
    'handoff',
    'pause_work',
    'resume_work',
    'cancel_work',
    'update_work',
    'wait',
    'set_strategy',
    'record_memory',
  ],
  allowed_tools: ['produce_artifact'],
  reserved_matters: ['goal', 'resources', 'charter', 'funding', 'dissolution'],
  board_can_amend: true,
};
export function blocked(
  kind: CommandKind,
  connected: boolean,
  session?: Session,
  data?: Snapshot,
): string {
  if (!connected) return '连接断开，先读取最新状态';
  if (session?.role !== 'board') return '观察者可查看，操作需要发起人会话';
  if (kind === 'create') return '';
  if (!data) return '请先创建组织';
  if (kind === 'start') {
    if (!session.executors.length) return '宿主尚未配置执行器';
    if (
      !session.executors.some(
        (executor) => executor !== 'api' || data.execution_config.api_connection_id,
      )
    )
      return '请先配置并绑定组织的默认 API 连接';
    if (data.execution_state === 'running' || data.host_activity.confirmed)
      return '已有运行作业，不能重复启动';
    if (data.execution_state === 'unknown') return '执行结果未知，请先核对';
    if (data.budget.blocked_reason) return data.budget.blocked_reason;
  }
  if (['amend', 'resources', 'model', 'reconcile'].includes(kind) && data.host_activity.confirmed)
    return '先暂停派发并等待在途回执';
  if (kind === 'amend' && !data.charter.board_can_amend) return '现行章程不允许此修订入口';
  if (kind === 'reconcile' && !data.runs.some((r) => r.status === 'unknown'))
    return '仅能核对已确认 unknown 的执行';
  return '';
}
export function readForm(kind: CommandKind, form: HTMLFormElement): Record<string, unknown> {
  const values = new FormData(form);
  const str = (name: string) => String(values.get(name) ?? '').trim();
  for (const input of form.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('[required]')) {
    if (!input.disabled && !input.value.trim()) throw new Error('必填内容不能只包含空格');
  }
  const model = str('model') || null;
  if (model && !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(model))
    throw new Error('模型 ID 格式不正确；请填写模型名称或留空使用 CLI 默认');
  const resources = () => ({
    max_calls: Number(str('max_calls')),
    timeout_seconds: Number(str('timeout_seconds')),
  });
  const charter = () => ({ ...JSON.parse(str('charter_rules')), text: str('charter_text') });
  const reason = str('reason');
  switch (kind) {
    case 'create':
      return {
        name: str('name'),
        goal: str('goal'),
        board_name: str('board_name'),
        resources: resources(),
        charter: charter(),
      };
    case 'resources':
      return { resources: resources(), reason };
    case 'amend':
      return { charter: charter(), reason };
    case 'model':
      return { model, reason };
    case 'start': {
      const executor = str('executor');
      const allow_unknown_cost = values.get('allow_unknown_cost') === 'on';
      if ((executor === 'codex' || executor === 'api') && !allow_unknown_cost)
        throw new Error('请明确接受本次有限调用的费用未知条件');
      return {
        executor,
        model: executor === 'codex' ? model : null,
        max_steps: Number(str('max_steps')),
        max_seconds: Number(str('max_seconds')),
        allow_unknown_cost,
      };
    }
    case 'event':
      return {
        kind: str('kind'),
        event_id: str('event_id'),
        content: str('content'),
        source: str('source'),
        simulated: str('simulated') === 'true',
      };
    case 'reconcile':
      return { run_id: str('run_id'), resolution: str('resolution'), reason };
    case 'pause':
      return {};
  }
}
