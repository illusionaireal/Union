import { request } from '../../api/client';
import type { GovernanceReceipt, GovernanceRequest } from './types';

export const governanceApi = {
  command: (command: GovernanceRequest) =>
    request<{ receipt: GovernanceReceipt }>('/api/v1/governance/commands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    }),
  receipt: (organizationId: string, id: string) =>
    request<{ receipt: GovernanceReceipt }>(
      '/api/v1/governance/receipts?' +
        new URLSearchParams({ organization_id: organizationId, id }).toString(),
    ),
};
