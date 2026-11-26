import { MemoryRouter } from 'react-router-dom';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { ResultList } from './ResultList';

afterEach(cleanup);

function read(value: {works: unknown[]}) {
  return render(<MemoryRouter><ResultList organizationId="au-1" works={value.works as import('../../api/types').CoreWorkItem[]} /></MemoryRouter>);
}

const base = { protocol: 'core.work.v1', organization_id: 'au-1', version: 5, access: { principal_id: 'p1', can_start: true } };

describe('V1 results list', () => {
  it('lists adopted and candidate results with a Work-scoped reading and download route per result', async () => {
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
    const links = screen.getAllByText('阅读与下载').map((node) => node.getAttribute('href') ?? '');
    expect(links[0]).toBe('/au/au-1/work/work-overview/results/result-a');
  });

  it('explains when no V1 result exists yet', async () => {
    read({ ...base, works: [] });
    await waitFor(() => expect(screen.getByText(/还没有 V1 成果/)).toBeTruthy());
  });
});
