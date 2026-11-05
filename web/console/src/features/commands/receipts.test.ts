import { describe, expect, it } from 'vitest';
import type { Receipt } from '../../api/types';
import { acceptReceipt, loadPending, savePending } from './receipts';
import { api } from '../../api/client';
import { vi } from 'vitest';
const base: Receipt = {
  id: 'request-1',
  kind: 'event',
  organization_id: 'org-1',
  base_version: 2,
  actor: 'test',
  created_at: '2026-10-13',
  status: 'accepted',
  message: '操作已受理',
};
describe('receipt recovery', () => {
  it('persists V1 request kind and queries its original receipt even with an allocated AU ID', async () => {
    const pending = [{ id: 'core-request', kind: 'create_v1' as const, organization_id: 'org-allocated' }];
    savePending(pending);
    expect(loadPending()).toEqual(pending);
    const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ receipt: base }), { status: 200 }));
    await api.receipt('core-request', 'org-allocated', 'create_v1');
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/receipts?id=core-request');
  });
  it('advances accepted to succeeded and never replaces a terminal receipt with a late result', () => {
    const success = { ...base, status: 'succeeded' as const, message: '操作已保存' };
    expect(acceptReceipt(base, success)).toBe(success);
    expect(acceptReceipt(success, base)).toBe(success);
    expect(acceptReceipt(success, { ...base, status: 'unknown' })).toBe(success);
  });
  it('retains unknown and rejected outcomes for explicit handling', () => {
    for (const status of ['unknown', 'rejected'] as const) {
      const terminal = { ...base, status };
      expect(acceptReceipt(terminal, base)).toBe(terminal);
    }
  });
  it('persists original identities without command bodies and tolerates corrupt storage', () => {
    const pending = [{ id: base.id, kind: base.kind, organization_id: base.organization_id }];
    savePending(pending);
    expect(loadPending()).toEqual(pending);
    sessionStorage.setItem('union-pending', '{}');
    expect(loadPending()).toEqual([]);
    sessionStorage.setItem(
      'union-pending',
      '[null,{"id":123},{"id":"x","organization_id":null,"kind":"invalid"}]',
    );
    expect(loadPending()).toEqual([]);
  });
  it('recovers API request identities without persisting credentials or command bodies', () => {
    const pending = [{ id: 'api-request', organization_id: 'org-1', kind: 'api_test' as const }];
    savePending(pending);
    expect(loadPending()).toEqual(pending);
    expect(sessionStorage.getItem('union-pending')).not.toContain('api_key');
  });
});
