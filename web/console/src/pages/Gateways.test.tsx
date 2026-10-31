import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, type Gateway } from '../api/client';
import Gateways from './Gateways';
const state = vi.hoisted(() => ({ session: { role: 'board', platform_admin: true, service_instance: 'test' }, connected: true }));
vi.mock('../app/workspace', () => ({ useWorkspace: () => state }));
const record: Gateway = { id: 'gateway-test', revision: 1, config: { name: 'New API 测试', service_url: 'https://gateway.example:8443', api_base_url: 'https://gateway.example/v1', admin_url: 'https://gateway.example/console', mode: 'external' }, health: 'unavailable', version: null, deployment_state: 'unknown', checked_at: '2026-10-30T00:00:00Z', message: '无法读取网关状态；部署状态未知', capabilities: [] };
function mount() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><Gateways /></MemoryRouter></QueryClientProvider>); }
beforeEach(() => { vi.restoreAllMocks(); state.session.platform_admin = true; state.connected = true; });
describe('gateway platform boundary and operations', () => {
  it('does not fetch or show operations without explicit platform permission', () => {
    state.session.platform_admin = false;
    const read = vi.spyOn(api, 'gateways'); mount();
    expect(screen.getByText('需要宿主授予平台管理权限')).toBeVisible(); expect(read).not.toHaveBeenCalled();
  });
  it('separates unavailable health from unknown deployment, hides unsupported controls and opens isolated links', async () => {
    vi.spyOn(api, 'gateways').mockResolvedValue({ gateways: [record], receipts: [], service_instance: 'test' });
    const write = vi.spyOn(api, 'gatewayCommand').mockResolvedValue({ receipt: { id: 'probe', gateway_id: record.id, kind: 'probe', status: 'accepted', message: '健康检测已受理', created_at: 'now' } });
    mount(); await screen.findByText('无法确认可用');
    expect(screen.getByText('未知（尚无部署控制器）')).toBeVisible(); expect(screen.getByText('8443（访问端口，内部端口未知）')).toBeVisible();
    expect(screen.queryByRole('button', { name: '停止' })).not.toBeInTheDocument(); expect(screen.queryByRole('button', { name: '更新' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开 New API 后台' })).toHaveAttribute('rel', 'noopener noreferrer');
    expect(write).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole('button', { name: '检测健康' }));
    await waitFor(() => expect(write).toHaveBeenCalledWith(expect.objectContaining({ gateway_id: record.id, base_revision: 1, kind: 'probe', data: {} })));
  });
  it('uses the original registration revision after a background refresh', async () => {
    const read = vi.spyOn(api, 'gateways').mockResolvedValue({ gateways: [record], service_instance: 'test' });
    const write = vi.spyOn(api, 'gatewayCommand').mockResolvedValue({ receipt: { id: 'save', gateway_id: record.id, kind: 'save', status: 'rejected', message: '版本冲突', created_at: 'now' } });
    mount(); fireEvent.click(await screen.findByRole('button', { name: '编辑' }));
    fireEvent.change(screen.getByLabelText('网关名称'), { target: { value: '用户编辑内容' } });
    read.mockResolvedValue({ gateways: [{ ...record, revision: 2 }], service_instance: 'test' });
    fireEvent.click(screen.getByRole('button', { name: '保存登记' }));
    await waitFor(() => expect(write).toHaveBeenCalledWith(expect.objectContaining({ base_revision: 1, data: { config: { ...record.config, name: '用户编辑内容' } } })));
    expect(screen.getByLabelText('网关名称')).toHaveValue('用户编辑内容');
  });
});
