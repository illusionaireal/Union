import { request } from '../../api/client';
import type { ModelRead, ModelReceipt, ModelRequest } from './types';

export const modelsApi = {
  read: (organizationId: string, signal?: AbortSignal) =>
    request<ModelRead>(
      '/api/v1/models?' + new URLSearchParams({ organization_id: organizationId }),
      { signal },
    ),
  command: (command: ModelRequest) =>
    request<{ receipt: ModelReceipt }>('/api/v1/models/commands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    }),
  receipt: (organizationId: string, id: string) =>
    request<{ receipt: ModelReceipt }>(
      '/api/v1/models/receipts?' + new URLSearchParams({ organization_id: organizationId, id }),
    ),
};
