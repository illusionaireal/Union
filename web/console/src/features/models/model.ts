import type { CoreConnection, ModelDraft, ModelKind, ModelRead, ModelRequest } from './types';

export const titles: Record<ModelKind, string> = {
  save_connection: '保存模型连接',
  reconcile_connection: '核对原保存操作',
  set_connection: '变更连接用途',
  grant_model_resources: '授予有限调用',
  start_model_check: '验证工具往返',
  reconcile_model_check: '核对原验证',
  cancel_model_check: '停止后续步骤',
};
export function draftTitle(draft: ModelDraft) {
  if (draft.kind === 'save_connection') return draft.connection ? '编辑连接' : '添加模型连接';
  if (draft.kind === 'set_connection')
    return draft.makeDefault ? '设为默认' : draft.enabled ? '启用连接' : '停用连接';
  return titles[draft.kind];
}
export const remainingCalls = (read: ModelRead) =>
  Math.max(0, (read.resources.grant?.max_calls ?? 0) - read.resources.reserved_calls);
export function hasBlockingModelCheck(read: ModelRead, connection: CoreConnection) {
  return read.checks.some(
    (check) =>
      check.connection_id === connection.id &&
      check.connection_revision === connection.revision &&
      !check.stop_requested &&
      ['queued', 'running', 'unknown', 'cancel_requested'].includes(check.status),
  );
}
export function isRecoveryAction(
  kind: ModelKind,
  options: Pick<ModelDraft, 'enabled' | 'makeDefault'> = {},
) {
  return (
    ['reconcile_connection', 'reconcile_model_check', 'cancel_model_check'].includes(kind) ||
    (kind === 'set_connection' && options.enabled === false && !options.makeDefault)
  );
}
export function commandTarget(draft: ModelDraft) {
  if (draft.check) return draft.check.connection_id;
  if (draft.operation) return draft.operation.id;
  if (draft.kind === 'grant_model_resources') return 'model-resources';
  return draft.connection?.id ?? draft.key;
}
export function readModelForm(draft: ModelDraft, form: HTMLFormElement): ModelRequest['data'] {
  for (const field of form.querySelectorAll<
    HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
  >('input, textarea, select')) {
    if (!field.checkValidity()) {
      field.reportValidity();
      throw new Error('请补全并检查标出的字段');
    }
  }
  const values = new FormData(form);
  const str = (name: string) => String(values.get(name) ?? '').trim();
  const num = (name: string) => Number(str(name));
  switch (draft.kind) {
    case 'save_connection': {
      const data = {
        connection_id: draft.connection?.id ?? draft.key,
        expected_revision: draft.connection?.revision ?? 0,
        name: str('name'),
        profile: str('profile'),
        model: str('model'),
        max_output_tokens: num('max_output_tokens'),
      };
      if (data.profile === 'modeld_grant')
        return { ...data, grant_ref: str('grant_ref'), grant_revision: num('grant_revision') };
      const apiKey = String(values.get('api_key') ?? '');
      if (!/^[\x21-\x7e]{1,4096}$/.test(apiKey))
        throw new Error('API Key 须为 1–4096 个可打印 ASCII 字符，不能含空白');
      const address = new URL(str('base_url'));
      if (
        address.username ||
        address.password ||
        address.search ||
        address.hash ||
        !(
          address.protocol === 'https:' ||
          (address.protocol === 'http:' &&
            ['localhost', '127.0.0.1', '[::1]'].includes(address.hostname))
        )
      )
        throw new Error(
          'API 地址须使用 HTTPS（本机回环可用 HTTP），且不能包含账号、查询参数或片段',
        );
      return { ...data, base_url: str('base_url'), api_key: apiKey };
    }
    case 'set_connection':
      return {
        connection_id: draft.connection!.id,
        expected_revision: draft.connection!.revision,
        enabled: draft.enabled ?? true,
        make_default: draft.makeDefault ?? false,
      };
    case 'grant_model_resources':
      return {
        max_calls: num('max_calls'),
        allow_unknown_cost: values.get('allow_unknown_cost') === 'on',
        reason: str('reason'),
      };
    case 'start_model_check':
      return {
        connection_id: draft.connection!.id,
        expected_revision: draft.connection!.revision,
        binding_id: str('binding_id') || null,
        document_name: str('document_name'),
        document_text: str('document_text'),
      };
    case 'reconcile_connection':
      return { operation_id: draft.operation!.id };
    case 'reconcile_model_check':
      return { check_id: draft.check!.id };
    case 'cancel_model_check':
      return { check_id: draft.check!.id, reason: str('reason') };
  }
}
