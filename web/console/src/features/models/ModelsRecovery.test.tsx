import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api/client';
import { principal } from '../governance/test-fixtures';
import {
  accepted,
  checkedRun,
  closeResult,
  confirm,
  fillConnection,
  fixture,
  json,
  mount,
  open,
  savedConnection,
} from './test-fixtures';

let state: ReturnType<typeof fixture>;
beforeEach(() => {
  state = fixture();
});
afterEach(() => {
  vi.unstubAllGlobals();
});
const stored = () => JSON.parse(sessionStorage.getItem('union-model-requests') || '[]');

describe('model original-request recovery', () => {
  it('never replays a lost save and only queries the original receipt', async () => {
    state.state.onCommand = async () => {
      throw new Error('连接中断');
    };
    mount();
    await fillConnection();
    await confirm();
    expect(await screen.findByText('结果尚未确认')).toBeVisible();
    expect(screen.queryByRole('button', { name: '预览影响' })).not.toBeInTheDocument();
    const original = state.commands[0];
    expect(stored()[0]).toMatchObject({
      id: original.id,
      kind: 'save_connection',
      target: original.data.connection_id,
      principal_id: principal,
    });
    expect(stored()[0]).not.toHaveProperty('data');
    expect(sessionStorage.getItem('union-model-requests')).not.toContain(
      'test-key-not-a-real-secret',
    );
    state.receipts.set(original.id, accepted(original));
    fireEvent.click(screen.getByRole('button', { name: '查询原请求回执' }));
    await closeResult();
    expect(state.commands).toHaveLength(1);
    expect(
      state.fetchMock.mock.calls.some(
        ([url]) => String(url).includes('/models/receipts?') && String(url).includes(original.id),
      ),
    ).toBe(true);
  });

  it('treats a concrete validation error as rejected input instead of unknown', async () => {
    state.state.onCommand = async () =>
      json({ code: 'invalid_request', error: '模型地址不合法' }, 400);
    mount();
    await fillConnection();
    await confirm();
    expect(await screen.findByText(/模型地址不合法/)).toBeVisible();
    expect(screen.getByLabelText('连接名称')).toHaveValue('我的文本模型');
    expect(screen.getByLabelText('API Key')).toHaveValue('');
    expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
    expect(screen.queryByText('结果尚未确认')).not.toBeInTheDocument();
    expect(stored()).toHaveLength(0);
  });

  it('keeps an unmatched response unknown without displaying another AU receipt', async () => {
    state.state.onCommand = async (command) =>
      json({
        receipt: {
          ...accepted(command),
          organization_id: 'different-au',
          message: 'other private result',
        },
      });
    mount();
    await fillConnection();
    await confirm();
    expect(await screen.findByText('结果尚未确认')).toBeVisible();
    expect(screen.queryByText('other private result')).not.toBeInTheDocument();
    expect(stored()[0].resolved).toBe(false);
    expect(state.commands).toHaveLength(1);
  });

  it('retains own receipt lookup after AU read access is denied and clears former output', async () => {
    state.read.checks.push(checkedRun());
    state.read.connections.push(savedConnection());
    const reference = {
      id: 'original-save',
      organization_id: 'core-au',
      base_version: 12,
      kind: 'save_connection',
      principal_id: principal,
      service_instance: state.session.service_instance,
      target: 'connection-one',
      resolved: false,
    };
    sessionStorage.setItem('union-model-requests', JSON.stringify([reference]));
    state.receipts.set(reference.id, accepted({ ...reference, data: {} }));
    const { client } = mount();
    expect(
      await screen.findByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).toBeVisible();
    state.state.onRead = async () => json({ code: 'not_authorized', error: '读取权限已变化' }, 403);
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    await waitFor(() =>
      expect(
        screen.queryByText('资料描述了持续责任。校验码：controlled-challenge'),
      ).not.toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole('button', { name: '查询原请求 original-save' }));
    expect(await screen.findByText('模型操作已受理')).toBeVisible();
    expect(state.commands).toHaveLength(0);
  });

  it('recovers after a service restart using the original issuer and ID', async () => {
    const reference = {
      id: 'before-restart',
      organization_id: 'core-au',
      base_version: 11,
      kind: 'save_connection',
      principal_id: principal,
      service_instance: 'retired-process',
      target: 'connection-one',
      resolved: false,
    };
    sessionStorage.setItem('union-model-requests', JSON.stringify([reference]));
    state.receipts.set(reference.id, accepted({ ...reference, data: {} }));
    mount();
    fireEvent.click(await screen.findByRole('button', { name: '查询原请求 before-restart' }));
    expect(await screen.findByText('模型操作已受理')).toBeVisible();
    expect(state.commands).toHaveLength(0);
    expect(stored()[0]).toMatchObject({
      id: 'before-restart',
      service_instance: 'retired-process',
      resolved: true,
    });
  });

  it('reconciles a saved unknown operation explicitly without resubmitting credentials', async () => {
    state.read.operations.push({ id: 'lost-save', status: 'unknown', message: '保存结果未确认' });
    mount();
    await open('核对原保存操作');
    await confirm();
    await closeResult();
    expect(state.commands).toHaveLength(1);
    expect(state.commands[0]).toMatchObject({
      kind: 'reconcile_connection',
      data: { operation_id: 'lost-save' },
    });
    expect(state.commands[0].data).not.toHaveProperty('api_key');
  });

  it('keeps other connections usable when one verification is unknown', async () => {
    state.read.connections.push(savedConnection(), savedConnection('connection-two'));
    state.read.checks.push(checkedRun('original-check', 'unknown'));
    state.read.resources.grant = {
      max_calls: 6,
      allow_unknown_cost: true,
      revision: 1,
      reason: 'bounded',
    };
    state.read.resources.reserved_calls = 2;
    mount();
    const heading = await screen.findByRole('heading', { name: '另一模型' });
    const second = within(heading.closest('li')!);
    expect(second.getByRole('button', { name: '验证工具往返' })).toBeEnabled();
    const first = within(screen.getByRole('heading', { name: '我的文本模型' }).closest('li')!);
    expect(first.getByRole('button', { name: '验证工具往返' })).toBeDisabled();
    await open('核对原验证');
    await confirm();
    await closeResult();
    expect(state.commands[0]).toMatchObject({
      kind: 'reconcile_model_check',
      data: { check_id: 'original-check' },
    });
    expect(state.commands.some((command) => command.kind === 'start_model_check')).toBe(false);
  });

  it('allows the current governor to request local stop while governance is unavailable', async () => {
    state.read.connections.push(savedConnection());
    state.read.checks.push(checkedRun('unknown-check', 'unknown'));
    state.read.governance_status = 'unavailable';
    state.read.access.can_configure = false;
    mount();
    await open('停止后续步骤');
    fireEvent.change(screen.getByLabelText('停止依据'), { target: { value: '暂时停止后续验证' } });
    await confirm();
    await closeResult();
    expect(state.commands[0]).toMatchObject({
      kind: 'cancel_model_check',
      data: { check_id: 'unknown-check', reason: '暂时停止后续验证' },
    });
    expect(screen.queryByText('远端已取消')).not.toBeInTheDocument();
    expect(screen.getByText('81 / 17')).toBeVisible();
  });

  it('lets an unavailable current governor disable a connection while enable and default stay unavailable', async () => {
    state.read.connections.push(savedConnection(), {
      ...savedConnection('connection-two'),
      enabled: false,
    });
    state.read.governance_status = 'unavailable';
    state.read.access.can_configure = false;
    sessionStorage.setItem(
      'union-model-requests',
      JSON.stringify([
        {
          id: 'unconfirmed-configuration',
          organization_id: 'core-au',
          base_version: 11,
          kind: 'save_connection',
          principal_id: principal,
          service_instance: state.session.service_instance,
          target: 'connection-one',
          resolved: false,
        },
      ]),
    );
    mount();
    expect(await screen.findByRole('button', { name: '停用连接' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '启用连接' })).toBeDisabled();
    expect(
      screen
        .getAllByRole('button', { name: '设为默认' })
        .every((button) => button.hasAttribute('disabled')),
    ).toBe(true);
    await open('停用连接');
    await confirm();
    await closeResult();
    expect(state.commands[0]).toMatchObject({
      kind: 'set_connection',
      data: {
        connection_id: 'connection-one',
        expected_revision: 1,
        enabled: false,
        make_default: false,
      },
    });
  });

  it('does not submit if the dialog is cancelled while checking current identity', async () => {
    let finish!: (value: typeof state.session) => void;
    mount();
    await fillConnection();
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    const confirmButton = await screen.findByRole('button', { name: '确认提交' });
    vi.mocked(api.session).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    fireEvent.click(confirmButton);
    await waitFor(() => expect(finish).toBeDefined());
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    await act(async () => {
      finish(state.session);
    });
    expect(state.commands).toHaveLength(0);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
