import type { Session } from '../../api/types';
import { sameScope, type GovernanceScope } from '../governance/model';
import { modelKinds, type ModelRead, type ModelReceipt, type ModelReference } from './types';

const storageKey = 'union-model-requests';
export const referenceKey = (
  item: Pick<ModelReference, 'principal_id' | 'organization_id' | 'id'>,
) => `${item.principal_id}:${item.organization_id}:${item.id}`;
export function loadReferences(): ModelReference[] {
  try {
    const saved: unknown = JSON.parse(sessionStorage.getItem(storageKey) || '[]');
    if (!Array.isArray(saved)) return [];
    return saved
      .filter(
        (item): item is ModelReference =>
          item &&
          ['id', 'organization_id', 'principal_id', 'service_instance', 'target'].every(
            (key) => typeof item[key] === 'string' && item[key].length > 0,
          ) &&
          modelKinds.includes(item.kind) &&
          Number.isInteger(item.base_version) &&
          item.base_version >= 0 &&
          typeof item.resolved === 'boolean',
      )
      .map(
        ({
          id,
          organization_id,
          base_version,
          kind,
          principal_id,
          service_instance,
          resolved,
          target,
        }) => ({
          id,
          organization_id,
          base_version,
          kind,
          principal_id,
          service_instance,
          resolved,
          target,
        }),
      );
  } catch {
    return [];
  }
}
export function saveReferences(items: ModelReference[]) {
  sessionStorage.setItem(storageKey, JSON.stringify(items));
}
export function matchesModelRead(read: ModelRead, scope: GovernanceScope) {
  return (
    read.protocol === 'core.models.v1' &&
    read.organization_id === scope.organizationId &&
    read.access?.principal_id === scope.principalId &&
    read.access?.service_instance === scope.serviceInstance &&
    Number.isInteger(read.version) &&
    read.version >= 0
  );
}
export function assertSession(scope: GovernanceScope, session: Session) {
  if (!sameScope(scope, session, scope.organizationId))
    throw new Error('核心身份或服务已变化；请刷新后使用原身份查询原请求');
}
export function matchesReceipt(reference: ModelReference, receipt: ModelReceipt) {
  return (
    receipt.id === reference.id &&
    receipt.kind === reference.kind &&
    receipt.organization_id === reference.organization_id &&
    receipt.base_version === reference.base_version &&
    receipt.actor_principal_id === reference.principal_id &&
    ['succeeded', 'rejected'].includes(receipt.status) &&
    Number.isInteger(receipt.version) &&
    receipt.version >= 0
  );
}
export function pendingForTarget(
  references: ModelReference[],
  scope: GovernanceScope,
  target: string,
) {
  return references.find(
    (item) =>
      !item.resolved &&
      item.principal_id === scope.principalId &&
      item.organization_id === scope.organizationId &&
      item.target === target,
  );
}
