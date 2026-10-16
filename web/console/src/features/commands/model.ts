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
  company_usage: '核对缺失模型用量',
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
    if (data.company?.completed) return '三个周期已完成，请审读交付结果；新试验请创建新公司';
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
  if (
    [
      'amend',
      'resources',
      'model',
      'reconcile',
      'api_connection',
      'api_binding',
      'api_test',
      'company_usage',
    ].includes(kind) &&
    data.host_activity.confirmed
  )
    return '先暂停派发并等待在途回执';
  if (kind === 'amend' && !data.charter.board_can_amend) return '现行章程不允许此修订入口';
  if (kind === 'reconcile' && !data.runs.some((r) => r.status === 'unknown'))
    return '仅能核对已确认 unknown 的执行';
  if (kind === 'api_test' && !data.execution_config.api_connection_id)
    return '请先保存并绑定 API 连接';
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
        ...(str('company_template') === 'novel'
          ? {
              company: {
                initial_budget_minor: Number(str('initial_budget_minor')),
                input_price_minor_per_million: Number(str('input_price_minor_per_million')),
                output_price_minor_per_million: Number(str('output_price_minor_per_million')),
              },
            }
          : {}),
      };
    case 'api_connection':
      return {
        connection_id: str('connection_id'),
        reason: str('reason') || '网页配置模型连接',
        bind_default: true,
        ...(str('api_key') ? { api_key: str('api_key') } : {}),
        config: {
          name: str('connection_name'),
          base_url: str('base_url'),
          model: str('api_model'),
          response_format: str('response_format'),
          token_limit_field: str('token_limit_field'),
          max_output_tokens: Number(str('max_output_tokens')),
          timeout_seconds: Number(str('api_timeout')),
          enabled: true,
        },
      };
    case 'api_binding':
      return { connection_id: str('connection_id') || null, reason };
    case 'company_usage':
      return {
        run_id: str('run_id'),
        input_tokens: Number(str('input_tokens')),
        output_tokens: Number(str('output_tokens')),
        reason,
      };
    case 'api_test':
      if (values.get('allow_unknown_cost') !== 'on')
        throw new Error('请确认连接测试会调用一次真实模型，费用未知');
      return { allow_unknown_cost: true };
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

export const novelCharter: Charter = {
  ...defaultCharter,
  text: '小说公司首版试验：在预算和调用上限内自行决定题材、岗位、成员和创作流程，连续交付同一本小说三章；允许向本地 mock 平台投稿与复盘。模拟收入、服务器与税费不是真实资金；模型费用按配置单价估算。董事会保留目标、预算、章程、融资及解散控制权。',
  allowed_operations: [...defaultCharter.allowed_operations, 'submit_chapter', 'review_cycle'],
};
export function publicPreview(data: Record<string, unknown>) {
  return 'api_key' in data ? { ...data, api_key: '已填写 · 密钥不回显' } : data;
}
