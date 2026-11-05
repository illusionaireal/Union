import type { PendingRequest, Receipt } from '../../api/types';
export const pendingKey = 'union-pending';
export function matchesRequest(request: PendingRequest, receipt: Receipt): boolean {
  return receipt.id === request.id && receipt.kind === request.kind &&
    (!request.organization_id || receipt.organization_id === request.organization_id);
}

/** A late POST response/transport error must never downgrade a confirmed receipt. */
export function acceptReceipt(previous: Receipt | undefined, incoming: Receipt): Receipt {
  return previous && previous.status !== 'accepted' ? previous : incoming;
}
export function loadPending(): PendingRequest[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(pendingKey) || '[]');
    if (!Array.isArray(value)) return [];
    return value.filter(
      (v): v is PendingRequest =>
        v &&
        typeof v.id === 'string' &&
        (v.organization_id === null || typeof v.organization_id === 'string') &&
        [
          'create',
          'create_v1',
          'start',
          'pause',
          'event',
          'resources',
          'model',
          'amend',
          'reconcile',
          'api_connection',
          'api_binding',
          'api_test',
          'company_usage',
        ].includes(v.kind),
    );
  } catch {
    return [];
  }
}
export function savePending(value: PendingRequest[]) {
  // Fail before POST when the browser cannot retain the request identity for recovery.
  sessionStorage.setItem(pendingKey, JSON.stringify(value));
}
