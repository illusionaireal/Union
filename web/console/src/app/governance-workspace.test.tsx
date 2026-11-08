import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../api/client';
import type { CoreAURead, Session } from '../api/types';
import { WorkspaceProvider, useWorkspace } from './workspace';

const creator = 'f1dcda46-4e90-4a27-a82c-87a7494e383f';
const successor = '7275c7a4-e8c2-41d8-a40c-c6e0c97c0010';
const session: Session = {
  role: 'core',
  service_instance: 'governance-service',
  session_scope: 'current-login',
  principal_id: successor,
  core_protocol: 'core.au.v1',
  executors: [],
  organizations: [{ id: 'shared-au', name: '有明确责任的 AU', profile: 'core_v1' }],
};
const governed = {
  protocol: 'core.au.v1',
  au: {
    id: 'shared-au',
    name: '有明确责任的 AU',
    goal: '保存内部记录',
    version: 4,
    runtime_profile: 'core_v1',
    schema_version: 2,
    governance_root: { creator_principal_id: creator, governor_principal_id: creator },
  },
  access: {
    principal_id: successor,
    service_instance: session.service_instance,
    role: 'governor',
    commands: ['renew_governance'],
  },
} as unknown as CoreAURead;

function Probe() {
  const workspace = useWorkspace();
  return (
    <>
      <output data-testid="core-name">{workspace.core?.au.name ?? '无 AU 投影'}</output>
      <output data-testid="principal">{workspace.session?.principal_id ?? '无身份'}</output>
      <p role="alert">{workspace.error}</p>
      <button onClick={() => void workspace.refresh()}>刷新当前权限</button>
      <button onClick={() => workspace.selectOrg('another-au')}>切换到另一 AU</button>
      <button onClick={() => workspace.selectOrg('shared-au')}>返回原 AU 地址</button>
      <button disabled={!workspace.connected}>操作</button>
    </>
  );
}
function mount(gcTime = 0) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime } } });
  render(
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <WorkspaceProvider>
          <Probe />
        </WorkspaceProvider>
      </BrowserRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  window.history.replaceState(null, '', '/overview?organization=shared-au');
  vi.spyOn(api, 'session').mockResolvedValue(session);
});

describe('current governance access projection', () => {
  it('keeps the authorized AU readable after dispatch advances its schema', async () => {
    const read = vi.spyOn(api, 'coreAU').mockResolvedValue({
      ...governed,
      au: { ...governed.au, schema_version: 3 },
    } as unknown as CoreAURead);
    mount();
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    read.mockResolvedValue({
      ...governed,
      au: { ...governed.au, schema_version: 4, name: '执行后的同一 AU' },
    } as unknown as CoreAURead);
    fireEvent.click(screen.getByRole('button', { name: '刷新当前权限' }));
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('执行后的同一 AU'),
    );
    expect(screen.getByRole('button', { name: '操作' })).toBeEnabled();
    expect(screen.getByTestId('principal')).toHaveTextContent(successor);
  });

  it.each(['principal_id', 'service_instance', 'organization_scope'] as const)(
    'does not resurrect a cached AU after observing a changed %s',
    async (field) => {
      vi.spyOn(api, 'coreAU').mockResolvedValue(governed);
      mount(60000);
      await waitFor(() =>
        expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
      );
      const nextSession = {
        ...session,
        principal_id: field === 'principal_id' ? creator : successor,
        service_instance:
          field === 'service_instance' ? 'replacement-service' : session.service_instance,
        organizations: [{ id: 'another-au', name: '当前身份的 AU', profile: 'core_v1' as const }],
      };
      vi.mocked(api.session).mockResolvedValue(nextSession);
      vi.mocked(api.coreAU).mockResolvedValue({
        ...governed,
        au: { ...governed.au, id: 'another-au', name: '当前身份的 AU' },
        access: {
          principal_id: nextSession.principal_id,
          service_instance: nextSession.service_instance,
          role: 'governor',
          commands: [],
        },
      } as unknown as CoreAURead);
      fireEvent.click(screen.getByRole('button', { name: '切换到另一 AU' }));
      await waitFor(() =>
        expect(screen.getByTestId('core-name')).toHaveTextContent('当前身份的 AU'),
      );
      vi.mocked(api.session).mockImplementation(() => new Promise(() => {}));
      fireEvent.click(screen.getByRole('button', { name: '返回原 AU 地址' }));
      expect(screen.getByTestId('core-name')).toHaveTextContent('无 AU 投影');
      expect(screen.getByTestId('principal')).toHaveTextContent(nextSession.principal_id!);
      expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
    },
  );

  it('keeps writes disabled when the same principal revisits a cached AU before a fresh read', async () => {
    vi.spyOn(api, 'coreAU').mockResolvedValue(governed);
    mount(60000);
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    vi.mocked(api.session).mockResolvedValue({
      ...session,
      organizations: [
        ...session.organizations,
        { id: 'another-au', name: '另一 AU', profile: 'core_v1' },
      ],
    });
    vi.mocked(api.coreAU).mockResolvedValue({
      ...governed,
      au: { ...governed.au, id: 'another-au', name: '另一 AU' },
    } as unknown as CoreAURead);
    fireEvent.click(screen.getByRole('button', { name: '切换到另一 AU' }));
    await waitFor(() => expect(screen.getByTestId('core-name')).toHaveTextContent('另一 AU'));
    vi.mocked(api.session).mockImplementation(() => new Promise(() => {}));
    fireEvent.click(screen.getByRole('button', { name: '返回原 AU 地址' }));
    expect(screen.getByTestId('principal')).toHaveTextContent(successor);
    expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
  });

  it('keeps a disconnected snapshot during an ordinary session network failure', async () => {
    vi.spyOn(api, 'coreAU').mockResolvedValue(governed);
    mount();
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    vi.mocked(api.session).mockRejectedValue(new TypeError('连接中断'));
    fireEvent.click(screen.getByRole('button', { name: '刷新当前权限' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('连接中断'));
    expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU');
    expect(screen.getByTestId('principal')).toHaveTextContent(successor);
    expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
  });

  it('clears a revoked session and its AU projection even if the next refresh loses the network', async () => {
    vi.spyOn(api, 'coreAU').mockResolvedValue(governed);
    mount();
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    vi.mocked(api.session).mockRejectedValue(new ApiError('会话已失效', 401));
    fireEvent.click(screen.getByRole('button', { name: '刷新当前权限' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('会话已失效'));
    expect(screen.getByTestId('core-name')).toHaveTextContent('无 AU 投影');
    expect(screen.getByTestId('principal')).toHaveTextContent('无身份');
    expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
    vi.mocked(api.session).mockRejectedValue(new TypeError('恢复连接中'));
    fireEvent.click(screen.getByRole('button', { name: '刷新当前权限' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('恢复连接中'));
    expect(screen.getByTestId('core-name')).toHaveTextContent('无 AU 投影');
    expect(screen.getByTestId('principal')).toHaveTextContent('无身份');
  });

  it('accepts the current governor from server access instead of requiring the immutable creator identity', async () => {
    vi.spyOn(api, 'coreAU').mockResolvedValue(governed);
    mount();
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    expect(screen.getByRole('button', { name: '操作' })).toBeEnabled();
  });

  it.each([2, 3, 4].flatMap(schema =>
    ['principal_id', 'service_instance'].map(field => [schema, field] as const),
  ))(
    'withholds a schema %i projection bound to another %s',
    async (schema, field) => {
      vi.spyOn(api, 'coreAU').mockResolvedValue({
        ...governed,
        au: { ...governed.au, schema_version: schema },
        access: {
          principal_id: successor,
          service_instance: session.service_instance,
          role: 'governor',
          commands: [],
          [field]: 'another',
        },
      } as unknown as CoreAURead);
      mount();
      await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('不一致'));
      expect(screen.getByTestId('core-name')).toHaveTextContent('无 AU 投影');
      expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
    },
  );

  it('clears a previously readable prepared AU immediately when current access is revoked', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: creator });
    const read = vi.spyOn(api, 'coreAU').mockResolvedValue({
      ...governed,
      au: {
        ...governed.au,
        schema_version: 1,
      },
    } as unknown as CoreAURead);
    mount();
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    read.mockRejectedValue(new ApiError('当前主体没有 AU 读取权限', 403, 'not_authorized'));
    fireEvent.click(screen.getByRole('button', { name: '刷新当前权限' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('没有 AU 读取权限'));
    expect(screen.getByTestId('core-name')).toHaveTextContent('无 AU 投影');
    expect(screen.getByTestId('principal')).toHaveTextContent(creator);
    expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
  });

  it('does not retain an old principal projection when the new principal cannot read it', async () => {
    vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: creator });
    const read = vi.spyOn(api, 'coreAU').mockResolvedValue({
      ...governed,
      au: {
        ...governed.au,
        schema_version: 1,
      },
    } as unknown as CoreAURead);
    mount();
    await waitFor(() =>
      expect(screen.getByTestId('core-name')).toHaveTextContent('有明确责任的 AU'),
    );
    vi.mocked(api.session).mockResolvedValue(session);
    read.mockRejectedValue(new ApiError('读取服务暂不可用', 503, 'storage_unavailable'));
    fireEvent.click(screen.getByRole('button', { name: '刷新当前权限' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('读取服务暂不可用'));
    expect(screen.getByTestId('core-name')).toHaveTextContent('无 AU 投影');
    expect(screen.getByTestId('principal')).toHaveTextContent(successor);
    expect(screen.getByRole('button', { name: '操作' })).toBeDisabled();
  });
});
