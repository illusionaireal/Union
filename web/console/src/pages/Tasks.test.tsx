import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Tasks from './Tasks';

const workspace = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
const work = vi.hoisted(() => ({ coreWork: vi.fn() }));
vi.mock('../app/workspace', () => ({ useWorkspace: () => workspace.value }));
vi.mock('../api/client', () => ({ api: work }));
vi.mock('../components/Records', () => ({ WorkRows: () => <div>旧版工作</div> }));

describe('work page', () => {
  it('shows the V1 work panel for a core AU', async () => {
    work.coreWork.mockResolvedValue({
      protocol: 'core.work.v1', organization_id: 'au-1', version: 1,
      access: { principal_id: 'p1', can_start: true },
      works: [{
        id: 'work-overview', title: '项目概览', goal: '阅读授权资料', status: 'pending', version: 1, max_calls: 4,
        materials_root: 'project-docs', created_at: '2026-11-07T00:00:00Z', attempt_ids: [], result_ids: [],
        responsible: { member_id: 'm1', name: '资料整理 Agent', binding_id: 'b1', duty: '交付项目概览' },
        definition: { id: 'd1', version: 1, connection_id: 'c1', model: 'model-a', tools: [] },
        mandate: { id: 'ma1', version: 1, actions: ['read_document'], active: true },
        tool_calls: [], attempts: [], steps: [], budget: { max_calls: 4, reserved: 0, used: 0 },
        materials: { reference: 'project-docs', available: false, documents: 0 },
      }],
      capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
    });
    workspace.value = {
      data: { organization: { work: {}, members: {} } },
      core: { au: { id: 'au-1' } },
    };
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><Tasks /></MemoryRouter></QueryClientProvider>);
    await waitFor(() => expect(screen.getByText('项目概览')).toBeTruthy());
    expect(screen.getByText('资料整理 Agent（交付项目概览）')).toBeTruthy();
    expect(screen.getByText('旧版工作')).toBeTruthy();
  });
});
