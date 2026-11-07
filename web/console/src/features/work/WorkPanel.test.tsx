import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CoreWork, CoreWorkItem } from '../../api/types';
import { WorkPanel } from './WorkPanel';

afterEach(cleanup);

const coreWork = vi.hoisted(() => ({ coreWork: vi.fn(), coreWorkCommand: vi.fn(), coreModels: vi.fn() }));
vi.mock('../../api/client', () => ({
  api: coreWork,
  errorText: (error: unknown) => (error instanceof Error ? error.message : '服务暂不可用'),
}));

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
    read({ ...base, access: { principal_id: 'p1', can_start: false } });
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
    const link = screen.getByText('下载').getAttribute('href') ?? '';
    expect(link).toContain('/api/v1/work/results?organization_id=au-1');
    expect(link).toContain('id=result-overview');
  });
it('starts an execution and adopts a candidate result through the API', async () => {
    read({
      ...base,
      works: [item({
        results: [{
          id: 'result-overview', seq: 1, title: '项目概览（第一版）', sha256: 'abcdef0123456789', bytes: 24,
          sources: ['work-overview#s1'], status: 'candidate', created_at: '2026-11-08T00:00:00Z', adopted_at: null,
        }],
      })],
    });
    coreWork.coreWorkCommand.mockResolvedValue({ receipt: { status: 'succeeded', message: '已开始一次执行尝试' } });

    fireEvent.click(await screen.findByText('开始执行'));
    await waitFor(() => expect(coreWork.coreWorkCommand).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'start_attempt', organization_id: 'au-1', base_version: 3 })));

    fireEvent.click(await screen.findByText('采用成果'));
    await waitFor(() => expect(coreWork.coreWorkCommand).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'adopt_result', data: { work_id: 'work-overview', result_id: 'result-overview' } })));

    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('操作已记录'));
  });

  it('submits a candidate result with the selected sources', async () => {
    read({
      ...base,
      works: [item({
        steps: [{ seq: 1, step_ref: 'work-overview#s1', attempt_id: 'work-overview#a1', purpose: 'work_step', status: 'used', at: '2026-11-08T00:00:00Z' }],
      })],
    });
    const content = await screen.findByLabelText('成果正文');
    fireEvent.change(content, { target: { value: '# 概览\n- 依据 nested/a.md\n' } });
    fireEvent.change(screen.getByLabelText('成果标题'), { target: { value: '项目概览（第一版）' } });
    fireEvent.click(screen.getByLabelText('work-overview#s1'));
    coreWork.coreWorkCommand.mockResolvedValue({ receipt: { status: 'succeeded', message: '已登记候选成果与来源；尚未采用' } });

    fireEvent.click(screen.getByText('提交成果'));
    await waitFor(() => expect(coreWork.coreWorkCommand).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'submit_result',
      data: expect.objectContaining({
        work_id: 'work-overview', title: '项目概览（第一版）',
        content: '# 概览\n- 依据 nested/a.md\n', sources: ['work-overview#s1'],
      }),
    })));
  });

  it('closes a running attempt with an explicit outcome', async () => {
    read({
      ...base,
      works: [item({
        attempts: [{ id: 'work-overview#a1', seq: 1, status: 'running', outcome: null, started_at: '2026-11-08T00:00:00Z', ended_at: null }],
      })],
    });
    fireEvent.change(await screen.findByLabelText('结束结果'), { target: { value: 'unknown' } });
    coreWork.coreWorkCommand.mockResolvedValue({ receipt: { status: 'succeeded', message: '已结束该次执行尝试并记录结果类别' } });

    fireEvent.click(screen.getByText('结束执行'));
    await waitFor(() => expect(coreWork.coreWorkCommand).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'finish_attempt',
      data: expect.objectContaining({ work_id: 'work-overview', attempt_id: 'work-overview#a1', outcome: 'unknown' }),
    })));
  });

  it('registers an AI work from the page with the adopted default connection', async () => {
    coreWork.coreModels.mockResolvedValue({
      protocol: 'core.models.v1', organization_id: 'au-1', version: 3,
      access: { principal_id: 'p1', can_configure: true }, governance_status: 'active',
      document_read_allowed: true,
      connections: [{ id: 'connection-a', name: '主连接', revision: 1, enabled: true, is_default: true, profile: 'modeld_grant', model: 'model-a' }],
      resources: { grant: null, reserved_calls: 0, plan_max_calls: 12 },
    });
    read({ ...base, works: [] });

    fireEvent.change(await screen.findByLabelText('工作标题'), { target: { value: '项目概览' } });
    fireEvent.change(screen.getByLabelText('目标'), { target: { value: '阅读授权资料写一份概览' } });
    fireEvent.change(screen.getByLabelText('资料目录引用'), { target: { value: 'project-docs' } });
    fireEvent.change(screen.getByLabelText('调用上限'), { target: { value: '4' } });
    coreWork.coreWorkCommand.mockResolvedValue({ receipt: { status: 'succeeded', message: '已登记有责任成员的工作' } });

    await waitFor(() => expect(screen.getByText('登记 AI 工作')).toBeEnabled());
    fireEvent.click(screen.getByText('登记 AI 工作'));
    await waitFor(() => expect(coreWork.coreWorkCommand).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'start_work',
      data: expect.objectContaining({
        title: '项目概览', goal: '阅读授权资料写一份概览', materials_root: 'project-docs', max_calls: 4,
        tools: ['read_document'], connection_id: 'connection-a', expected_revision: 1,
      }),
    })));
  });

  it('completes a work with its adopted result', async () => {
    read({
      ...base,
      works: [item({
        results: [{
          id: 'result-overview', seq: 1, title: '项目概览（第一版）', sha256: 'abcdef0123456789', bytes: 24,
          sources: ['work-overview#s1'], status: 'adopted', created_at: '2026-11-08T00:00:00Z', adopted_at: '2026-11-08T00:10:00Z',
        }],
      })],
    });
    coreWork.coreWorkCommand.mockResolvedValue({ receipt: { status: 'succeeded', message: '已按采用的成果把该工作记为完成' } });
    fireEvent.click(await screen.findByText('完成工作'));
    await waitFor(() => expect(coreWork.coreWorkCommand).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'deliver_work',
      data: { work_id: 'work-overview', result_id: 'result-overview' },
    })));
  });

  it('hides the completion button while an execution is still running', async () => {
    read({
      ...base,
      works: [item({
        attempts: [{ id: 'work-overview#a1', seq: 1, status: 'running', outcome: null, started_at: '2026-11-08T00:00:00Z', ended_at: null }],
        results: [{
          id: 'result-overview', seq: 1, title: '项目概览（第一版）', sha256: 'abcdef0123456789', bytes: 24,
          sources: ['work-overview#s1'], status: 'adopted', created_at: '2026-11-08T00:00:00Z', adopted_at: '2026-11-08T00:10:00Z',
        }],
      })],
    });
    await screen.findByText(/项目概览（第一版）/);
    expect(screen.queryByText('完成工作')).toBeNull();
  });
});
