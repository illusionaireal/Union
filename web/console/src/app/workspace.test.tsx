import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../api/client';
import type { Session, Snapshot } from '../api/types';
import { IdentityBoundary } from '../pages/Identity';
import { WorkspaceProvider, useWorkspace } from './workspace';

const session: Session = {
  role: 'board', service_instance: 'host-one', session_scope: 'session-one',
  organizations: [{ id: 'first', name: 'First' }, { id: 'second', name: 'Second' }],
  executors: ['fixture'],
};
const snapshot = (id: string) => ({
  service_instance: session.service_instance, snapshot_sequence: 1,
  organization: { id },
}) as Snapshot;

function WorkspaceProbe() {
  const workspace = useWorkspace();
  return <>
    <input aria-label="Draft" defaultValue="" />
    <button onClick={() => workspace.selectOrg('second')}>Switch organization</button>
    <button disabled={!workspace.connected}>Submit command</button>
    <output data-testid="organization">{workspace.data?.organization.id ?? 'No snapshot'}</output>
    <output data-testid="loading">{String(workspace.loading)}</output>
  </>;
}

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><BrowserRouter><WorkspaceProvider>
    <IdentityBoundary><WorkspaceProbe /></IdentityBoundary>
  </WorkspaceProvider></BrowserRouter></QueryClientProvider>);
}

beforeEach(() => {
  window.history.replaceState(null, '', '/overview?organization=first');
});

describe('workspace organization transitions', () => {
  it('keeps the session and draft mounted while withholding old organization data and writes', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(session);
    vi.spyOn(api, 'authStatus').mockResolvedValue({
      configured: true, authenticated: true, can_setup: false, account: 'owner',
    });
    let finishSnapshot!: (value: Snapshot) => void;
    vi.spyOn(api, 'snapshot').mockImplementation(async (id) => id === 'first'
      ? snapshot(id) : new Promise((resolve) => { finishSnapshot = resolve; }));
    mount();
    await waitFor(() => expect(screen.getByTestId('organization')).toHaveTextContent('first'));
    const draft = screen.getByLabelText('Draft');
    fireEvent.change(draft, { target: { value: 'Unsaved work' } });
    fireEvent.click(screen.getByText('Switch organization'));
    await waitFor(() => expect(api.snapshot).toHaveBeenCalledWith('second', 0, expect.any(AbortSignal)));
    expect(screen.getByLabelText('Draft')).toBe(draft);
    expect(draft).toHaveValue('Unsaved work');
    expect(screen.getByTestId('organization')).toHaveTextContent('No snapshot');
    expect(screen.getByTestId('loading')).toHaveTextContent('true');
    expect(screen.getByText('Submit command')).toBeDisabled();
    await act(async () => { finishSnapshot(snapshot('second')); });
    await waitFor(() => expect(screen.getByTestId('organization')).toHaveTextContent('second'));
    expect(screen.getByLabelText('Draft')).toBe(draft);
    expect(screen.getByText('Submit command')).toBeEnabled();
  });

  it.each(['session_scope', 'service_instance'] as const)('rechecks identity when %s changes', async (field) => {
    vi.spyOn(api, 'session').mockResolvedValue(session);
    const auth = vi.spyOn(api, 'authStatus').mockResolvedValue({
      configured: true, authenticated: true, can_setup: false, account: 'owner',
    });
    vi.spyOn(api, 'snapshot').mockImplementation(async (id) => snapshot(id));
    mount();
    await waitFor(() => expect(screen.getByTestId('organization')).toHaveTextContent('first'));
    vi.mocked(api.session).mockResolvedValue({ ...session, [field]: 'replacement' });
    vi.mocked(api.snapshot).mockImplementation(async (id) => ({
      ...snapshot(id), service_instance: field === 'service_instance' ? 'replacement' : session.service_instance,
    }));
    auth.mockResolvedValue({ configured: true, authenticated: false, can_setup: false, account: null });
    fireEvent.click(screen.getByText('Switch organization'));
    await waitFor(() => expect(screen.getByRole('heading', { name: '登录 UNION' })).toBeVisible());
    expect(screen.queryByLabelText('Draft')).not.toBeInTheDocument();
    expect(screen.queryByText('Submit command')).not.toBeInTheDocument();
  });

  it('drops the placeholder when the new workspace read rejects an expired session', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(session);
    const auth = vi.spyOn(api, 'authStatus').mockResolvedValue({
      configured: true, authenticated: true, can_setup: false, account: 'owner',
    });
    vi.spyOn(api, 'snapshot').mockImplementation(async (id) => snapshot(id));
    mount();
    await waitFor(() => expect(screen.getByTestId('organization')).toHaveTextContent('first'));
    vi.mocked(api.session).mockRejectedValue(new ApiError('session expired', 401));
    auth.mockResolvedValue({ configured: true, authenticated: false, can_setup: false, account: null });
    fireEvent.click(screen.getByText('Switch organization'));
    await waitFor(() => expect(screen.getByRole('heading', { name: '登录 UNION' })).toBeVisible());
    expect(screen.queryByLabelText('Draft')).not.toBeInTheDocument();
    expect(screen.queryByText('Submit command')).not.toBeInTheDocument();
    expect(api.snapshot).not.toHaveBeenCalledWith('second', 0, expect.any(AbortSignal));
  });
});
