import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ResultList } from './ResultList';

afterEach(cleanup);

const work = vi.hoisted(() => ({ coreWork: vi.fn() }));
vi.mock('../../api/client', () => ({ api: work, errorText: (error: unknown) => String(error) }));

function read(value: unknown) {
  work.coreWork.mockResolvedValue(value);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><ResultList organizationId="au-1" /></QueryClientProvider>);
}

const base = { protocol: 'core.work.v1', organization_id: 'au-1', version: 5, access: { principal_id: 'p1', can_start: true } };

describe('V1 results list', () => {
  it('lists adopted and candidate results with a download link per result', async () => {
    read({
      ...base,
      works: [
        {
          id: 'work-overview', title: '项目概览', results: [
            { id: 'result-a', title: '项目概览（第一版）', sha256: 'abcdef0123456789', status: 'adopted', created_at: '2026-11-08T00:00:00Z' },
            { id: 'result-b', title: '项目概览（候选）', sha256: 'ffff000011112222', status: 'candidate', created_at: '2026-11-08T00:05:00Z' },
          ],
        },
      ],
    });
    await waitFor(() => expect(screen.getByText('项目概览（第一版）')).toBeTruthy());
    expect(screen.getByText('项目概览（候选）')).toBeTruthy();
    expect(screen.getByText('已采用')).toBeTruthy();
    expect(screen.getByText('候选')).toBeTruthy();
    const links = screen.getAllByText('下载').map((node) => node.getAttribute('href') ?? '');
    expect(links[0]).toContain('/api/v1/work/results?organization_id=au-1');
    expect(links[0]).toContain('id=result-a');
  });

  it('explains when no V1 result exists yet', async () => {
    read({ ...base, works: [] });
    await waitFor(() => expect(screen.getByText(/还没有 V1 成果/)).toBeTruthy());
  });
});
