import { governanceKinds, type GovernanceReceipt, type GovernanceRequest } from './types';

export interface GovernanceReference extends Pick<
  GovernanceRequest,
  'id' | 'organization_id' | 'kind' | 'base_version'
> {
  principal_id: string;
  service_instance: string;
  resolved: boolean;
  target?: string;
}
export const governanceStorageKey = 'union-governance-requests';
export const referenceKey = (
  item: Pick<GovernanceReference, 'id' | 'organization_id' | 'principal_id'>,
) => `${item.principal_id}:${item.organization_id}:${item.id}`;
export function loadReferences(): GovernanceReference[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(governanceStorageKey) || '[]');
    if (!Array.isArray(value)) return [];
    return value.filter(
      (item): item is GovernanceReference =>
        item &&
        ['id', 'organization_id', 'principal_id', 'service_instance'].every(
          (key) => typeof item[key] === 'string' && item[key].length > 0,
        ) &&
        governanceKinds.includes(item.kind) &&
        Number.isInteger(item.base_version) &&
        item.base_version >= 0 &&
        typeof item.resolved === 'boolean',
    );
  } catch {
    return [];
  }
}
export function saveReferences(items: GovernanceReference[]) {
  sessionStorage.setItem(governanceStorageKey, JSON.stringify(items));
}
export function matchesGovernanceReceipt(
  reference: GovernanceReference,
  receipt: GovernanceReceipt,
): boolean {
  return (
    receipt.id === reference.id &&
    receipt.organization_id === reference.organization_id &&
    receipt.kind === reference.kind &&
    receipt.base_version === reference.base_version &&
    receipt.actor_principal_id === reference.principal_id &&
    ['succeeded', 'rejected'].includes(receipt.status) &&
    Number.isInteger(receipt.version) &&
    receipt.version >= 0
  );
}
