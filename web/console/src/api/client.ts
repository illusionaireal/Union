import type {
  ArtifactContent,
  CommandRequest,
  CommandKind,
  CoreAURead,
  CoreWork,
  CoreModels,
  ModelConnection,
  Receipt,
  Session,
  Snapshot,
} from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : '服务暂不可用';
}
/** Cancellation and timeouts apply to reads AND writes; a timed out write is never retried. */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (init.signal?.aborted) controller.abort();
  init.signal?.addEventListener('abort', cancel, { once: true });
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 5000);
  try {
    const response = await fetch(path, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...init,
      signal: controller.signal,
    });
    const value = await response.json();
    if (!response.ok) throw new ApiError(value.error || '请求未成功', response.status, value.code);
    return value as T;
  } catch (error) {
    if (timedOut) throw new ApiError('请求超时，请刷新或查询原回执');
    throw error;
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener('abort', cancel);
  }
}
const query = (values: Record<string, string>) => new URLSearchParams(values).toString();
export const api = {
  coreAU: (id: string, signal?: AbortSignal) =>
    request<CoreAURead>('/api/v1/aus/' + encodeURIComponent(id), { signal }),
  coreWork: (id: string, signal?: AbortSignal) =>
    request<CoreWork>('/api/v1/work?organization_id=' + encodeURIComponent(id), { signal }),
  coreModels: (id: string, signal?: AbortSignal) =>
    request<CoreModels>('/api/v1/models?organization_id=' + encodeURIComponent(id), { signal }),
  coreWorkCommand: (body: Record<string, unknown>) =>
    request<{ receipt: { id?: string; status: string; message?: string } }>('/api/v1/work/commands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  catalog: () => request<{version:number; models: Array<{provider:string; model:string; context_window?:number; tool_call?:boolean; revision?:string}>}>('/api/model-catalog'),
  exportModels: (organization_id: string) => '/api/model-export?' + query({organization_id}),
  modelCosts: (organization_id: string) => request<{vouchers:Array<{id:string;basis:string;period:string;amount_minor:number;currency:string}>}>('/api/model-costs?'+query({organization_id})),
  authStatus: () => request<{configured: boolean; authenticated: boolean; can_setup: boolean; account: string | null}>('/api/auth/status'),
  auth: (action: 'setup' | 'register' | 'login' | 'recover' | 'password' | 'logout', data: Record<string, unknown>) =>
    request<{recovery_code?: string | null}>('/api/auth/' + action, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data)}),
  gateways: (organization_id?: string, signal?: AbortSignal) =>
    request<GatewayList>('/api/gateways' + (organization_id ? '?' + query({ organization_id }) : ''), { signal }),
  gatewayChoices: (organization_id: string, signal?: AbortSignal) =>
    request<{ gateways: GatewayChoice[]; service_instance: string }>('/api/gateways?' + query({ organization_id }), { signal }),
  gatewayCommand: (command: GatewayCommand) =>
    request<{ receipt: GatewayReceipt }>('/api/gateway-commands', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(command),
    }),
  connections: (organization_id: string, signal?: AbortSignal) =>
    request<{
      connections: ModelConnection[];
      api_enabled: boolean;
      api_connection_id: string | null;
    }>('/api/model-connections?' + query({ organization_id }), { signal }),
  session: (signal?: AbortSignal) => request<Session>('/api/session', { signal }),
  exchange: (ticket: string) =>
    request<Session>('/api/session', { method: 'POST', headers: { 'X-Union-Launch': ticket } }),
  snapshot: (organization_id: string, offset: number, signal?: AbortSignal) =>
    request<Snapshot>('/api/snapshot?' + query({ organization_id, offset: String(offset) }), {
      signal,
    }),
  command: (command: CommandRequest) =>
    request<{ receipt: Receipt }>('/api/commands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    }),
  receipt: (id: string, organization_id: string | null, kind?: CommandKind) =>
    request<{ receipt: Receipt }>(
      (kind === 'create_v1' ? '/api/v1/receipts?' : '/api/receipts?') +
      query({ id, ...(organization_id && kind !== 'create' && kind !== 'create_v1' ? { organization_id } : {}) }),
    ),
  artifact: (organization_id: string, id: string, signal?: AbortSignal) =>
    request<ArtifactContent>('/api/artifact?' + query({ organization_id, id }), { signal }),
  download: (organization_id: string, id: string) =>
    '/api/artifact?' + query({ organization_id, id, download: '1' }),
};

export interface GatewayConfig {
  name: string;
  service_url: string;
  api_base_url: string;
  admin_url: string;
  mode: 'external' | 'managed';
}
export interface Gateway {
  id: string;
  revision: number;
  config: GatewayConfig;
  health: 'unknown' | 'healthy' | 'unavailable';
  version: string | null;
  checked_at: string | null;
  message: string;
  deployment_state: 'unknown';
  capabilities: string[];
}
export type GatewayChoice = Pick<Gateway, 'id' | 'revision'> & { config: Pick<GatewayConfig, 'name' | 'api_base_url'> };
export interface GatewayCommand {
  id: string;
  gateway_id: string;
  base_revision: number;
  kind: 'save' | 'archive' | 'probe';
  data: { config?: GatewayConfig };
}
export interface GatewayReceipt {
  id: string;
  gateway_id: string;
  kind: string;
  status: string;
  message: string;
  created_at: string;
}
export interface GatewayList {
  gateways: Gateway[];
  receipts?: GatewayReceipt[];
  service_instance: string;
}
