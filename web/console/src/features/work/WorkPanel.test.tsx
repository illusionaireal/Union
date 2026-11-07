import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { CoreWork, CoreWorkItem } from '../../api/types';
import { WorkPanel } from './WorkPanel';

const coreWork = vi.hoisted(() => ({ coreWork: vi.fn() }));
vi.mock('../../api/client', () => ({ api: coreWork }));

function item(overrides: Partial<CoreWorkItem> = {}): CoreWorkItem {
  return {
    id: 'work-overview', title: '项目概览', goal: '阅读授权资料写一份概览', status: 'pending', version: 1,
    max_calls: 4, materials_root: 'project-docs', created_at: '2026-11-07T00:00:00Z',
    responsible: { member_id: 'm1', name: '资料整理 Agent', binding_id: 'b1', duty: '交付项目概览' },
    definition: { id: 'd1', version: 1, connection_id: 'c1', model: 'model-a', tools: ['list_documents'] },
    mandate: { id: 'ma1', version: 1, actions: ['list_documents'], active: true },
    attempt_ids: [], result_ids: [], tool_calls: [], attempts: [], steps: [],
    budget: { max_calls: 4, reserved: 1, used: 0 },
    materials: { reference: 'project-docs', available: true, documents: 2 }, results: [],
    ...overrides,
  };
}

function read(value: CoreWork) {
  coreWork.coreWork.mockResolvedValue(value);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><WorkPanel organizationId="au-1" /></QueryClientProvider>);
}

const base: CoreWork = {
  protocol: 'core.work.v1', organization_id: 'au-1', version: 3,
  access: { principal_id: 'p1', can_start: true }, works: [item()],
  capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
};

describe('V1 work panel', () => {
  it('shows responsibility, mandate, budget and registered materials', async () => {
    read(base);
    await waitFor(() => expect(screen.getByText('项目概览')).toBeTruthy());
    expect(screen.getByText('资料整理 Agent（交付项目概览）')).toBeTruthy();
    expect(screen.getByText('list_documents')).toBeTruthy();
    expect(screen.getByText('0 已用 · 1 已预约 · 上限 4')).toBeTruthy();
    expect(screen.getByText('project-docs · 可读 2 份')).toBeTruthy();
    expect(screen.getByText('尚未开始执行')).toBeTruthy();
    expect(screen.getByText('尚无工具回执')).toBeTruthy();
    expect(screen.getByText('尚无候选成果')).toBeTruthy();
  });

  it('reports an unknown execution and the last tool receipt instead of success', async () => {
    read({
      ...base,
      works: [item({
        attempts: [{ id: 'work-overview#a2', seq: 2, status: 'unknown', outcome: 'unknown', started_at: '2026-11-07T00:00:00Z', ended_at: null }],
        tool_calls: [{ seq: 1, step_ref: 'work-overview#1', tool: 'read_document', attempt_id: 'work-overview#a2', arguments: { path: 'a.md' }, at: '2026-11-07T00:00:00Z', sha256: 'abcdef0123456789', bytes: 12 }],
      })],
    });
    await waitFor(() => expect(screen.getByText(/执行结果未知，待核对/)).toBeTruthy());
    expect(screen.getByText(/read_document @ work-overview#1 · sha256 abcdef012345/)).toBeTruthy();
  });

  it('explains the empty state when no V1 work exists', async () => {
    read({ ...base, works: [] });
    await waitFor(() => expect(screen.getByText(/尚未登记 V1 工作/)).toBeTruthy());
  });
  it('shows an adopted result with its digest and source count', async () => {
    read({
      ...base,
      works: [item({
        results: [{ id: 'result-overview', seq: 1, title: '项目概览（第一版）', sha256: 'abcdef0123456789', bytes: 24,
          sources: ['work-overview#s1'], status: 'adopted', created_at: '2026-11-08T00:00:00Z', adopted_at: '2026-11-08T00:10:00Z' }],
      })],
    });
    await waitFor(() => expect(screen.getByText(/项目概览（第一版）/)).toBeTruthy());
    expect(screen.getByText(/已采用 · abcdef012345/)).toBeTruthy();
  });
});
