import type {
  ArtifactContent,
  CommandRequest,
  ModelConnection,
  Receipt,
  Session,
  Snapshot,
} from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
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
    if (!response.ok) throw new ApiError(value.error || '请求未成功', response.status);
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
  receipt: (id: string, organization_id: string | null) =>
    request<{ receipt: Receipt }>(
      '/api/receipts?' + query({ id, ...(organization_id ? { organization_id } : {}) }),
    ),
  artifact: (organization_id: string, id: string, signal?: AbortSignal) =>
    request<ArtifactContent>('/api/artifact?' + query({ organization_id, id }), { signal }),
  download: (organization_id: string, id: string) =>
    '/api/artifact?' + query({ organization_id, id, download: '1' }),
};
