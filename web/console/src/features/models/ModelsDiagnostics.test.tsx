import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  checkedRun,
  closeResult,
  confirm,
  fill,
  fixture,
  json,
  mount,
  open,
  savedConnection,
} from './test-fixtures';
import type { ModelAttempt } from './types';

let state: ReturnType<typeof fixture>;
beforeEach(() => {
  state = fixture();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

const attemptRow = (number: number) =>
  within(screen.getByRole('rowheader', { name: `第 ${number} 次` }).closest('tr')!);

describe('model check eligibility after version changes or local stop', () => {
  const previousUnknownCheck = (revision = 1, stopRequested = false) => {
    state.read.connections.push({ ...savedConnection(), revision });
    const check = checkedRun('previous-check', 'unknown');
    check.stop_requested = stopRequested;
    state.read.checks.push(check);
    state.read.resources.grant = {
      max_calls: 4,
      allow_unknown_cost: true,
      revision: 1,
      reason: '明确授权两次已有占用和两次新的验证',
    };
    state.read.resources.reserved_calls = 2;
    return structuredClone(check);
  };

  it('keeps an unstopped unknown check on the same revision blocking another check', async () => {
    previousUnknownCheck();
    mount();
    expect(await screen.findByRole('button', { name: '验证工具往返' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '核对原验证' })).toBeEnabled();
    expect(state.commands).toHaveLength(0);
    expect(state.read.resources.reserved_calls).toBe(2);
  });

  it('rechecks an unfinished current-version check that appears before preview', async () => {
    previousUnknownCheck();
    state.read.checks = [];
    state.read.resources.reserved_calls = 0;
    mount();
    await open('验证工具往返');
    fill('资料名称', '等待预览.txt');
    fill('资料正文', '表单打开后出现新的在途验证，应先处理原验证。');
    state.read.checks.push(checkedRun('appeared-check', 'unknown'));
    state.read.resources.reserved_calls = 2;
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(await screen.findByText('此连接仍有未结束的验证，请先核对原验证')).toBeVisible();
    expect(screen.getByLabelText('资料名称')).toHaveValue('等待预览.txt');
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it.each([
    ['an updated connection version', 2, false],
    ['a requested local stop', 1, true],
  ] as const)('allows an explicit new bounded check after %s', async (_case, revision, stopped) => {
    const previous = previousUnknownCheck(revision, stopped);
    mount();
    expect(await screen.findByRole('button', { name: '验证工具往返' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '核对原验证' })).toBeEnabled();
    expect(screen.getByText('81 / 17')).toBeVisible();
    expect(state.commands).toHaveLength(0);
    expect(state.read.resources.reserved_calls).toBe(2);
    await open('验证工具往返');
    fill('资料名称', '新的有限验证.txt');
    fill('资料正文', '新验证使用新的资料，原未知记录和占用仍然保留。');
    await confirm();
    await closeResult();
    expect(state.commands).toHaveLength(1);
    expect(state.commands[0]).toMatchObject({
      kind: 'start_model_check',
      data: { connection_id: 'connection-one', expected_revision: revision },
    });
    expect(state.read.checks.find((check) => check.id === previous.id)).toEqual(previous);
    expect(state.read.resources.reserved_calls).toBe(4);
  });

  it.each(['remaining calls', 'current permission'] as const)(
    'still requires %s after the previous version or check stops blocking',
    async (boundary) => {
      previousUnknownCheck(2, true);
      if (boundary === 'remaining calls') state.read.resources.grant!.max_calls = 3;
      else state.read.access.can_configure = false;
      mount();
      expect(await screen.findByRole('button', { name: '验证工具往返' })).toBeDisabled();
      expect(state.commands).toHaveLength(0);
      expect(state.read.resources.reserved_calls).toBe(2);
    },
  );
});
describe('model diagnostics and observed usage', () => {
  it('keeps each safe next step with its saving operation, check or attempt', async () => {
    const operationStep = '检查模型服务是否启动并恢复连接，再核对原操作。';
    const checkStep = '核对原执行；结果未知时不要重复提交模型请求。';
    const attemptStep = '检查供应商额度或限流状态；先核对原请求，不自动重试。';
    state.read.operations.push({
      id: 'saving-operation',
      status: 'unknown',
      message: '暂时无法连接本机模型服务',
      diagnostic: { code: 'model_service_unavailable', next_step: operationStep },
    });
    const original = checkedRun('diagnostic-check', 'unknown');
    state.read.checks.push({
      ...original,
      message: '原调用结果尚未确认；已知用量和原请求保留',
      diagnostic: { code: 'provider_result_unconfirmed', next_step: checkStep },
      attempts: [
        original.attempts[0],
        {
          ...original.attempts[1],
          diagnostic: { code: 'provider_rate_limited', next_step: attemptStep },
        },
      ],
    });
    mount();

    const operation = within((await screen.findByText('暂时无法连接本机模型服务')).closest('li')!);
    const check = within(screen.getByRole('heading', { name: '项目说明.txt' }).closest('li')!);
    expect(operation.getByText(operationStep, { exact: false })).toBeVisible();
    expect(operation.queryByText(checkStep, { exact: false })).not.toBeInTheDocument();
    expect(check.getByText(checkStep, { exact: false })).toBeVisible();
    expect(check.queryByText(operationStep, { exact: false })).not.toBeInTheDocument();
    expect(attemptRow(2).getByText(attemptStep, { exact: false })).toBeVisible();
    expect(attemptRow(1).queryByText(attemptStep, { exact: false })).not.toBeInTheDocument();
    expect(check.getByText('验证结果待核对')).toBeVisible();
    expect(state.commands).toHaveLength(0);
  });

  it.each([
    [
      'worker_start_failed',
      '后台验证未能启动；原操作已经保存',
      '请核对原操作后继续；系统不会重复提交原模型请求。',
    ],
    [
      'original_request_missing',
      '模型服务暂未找到原请求记录',
      '核对原模型服务和请求；查不到不代表远端从未执行，不自动重发。',
    ],
    [
      'provider_result_unconfirmed',
      '原调用结果尚未确认；已知用量和原请求保留',
      '核对原执行；结果未知时不要重复提交模型请求。',
    ],
  ])('keeps %s on explicit original-check reconciliation', async (code, message, nextStep) => {
    state.read.connections.push(savedConnection());
    state.read.checks.push({
      ...checkedRun('original-check', 'unknown'),
      message,
      diagnostic: { code, next_step: nextStep },
    });
    const { client } = mount();
    expect(await screen.findByText(nextStep, { exact: false })).toBeVisible();
    expect(screen.getByRole('button', { name: '验证工具往返' })).toBeDisabled();
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    expect(state.commands).toHaveLength(0);
    await open('核对原验证');
    await confirm();
    await closeResult();
    expect(state.commands).toHaveLength(1);
    expect(state.commands[0]).toMatchObject({
      kind: 'reconcile_model_check',
      data: { check_id: 'original-check' },
    });
  });

  it('keeps legacy schema 3 records readable without inventing diagnostics or usage sources', async () => {
    state.read.operations.push({ id: 'old-save', status: 'succeeded', message: '旧连接已保存' });
    state.read.checks.push(checkedRun());
    mount();
    expect(
      await screen.findByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).toBeVisible();
    expect(screen.getByText('81 / 17')).toBeVisible();
    expect(screen.getByText('132 / 31')).toBeVisible();
    expect(attemptRow(1).getByText('用量依据：未知')).toBeVisible();
    expect(attemptRow(2).getByText('用量依据：未知')).toBeVisible();
    expect(screen.queryByText(/下一步：/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('责任、授权与逐次依据'));
    expect(screen.getAllByText(/已观测事件序号：未知/)).toHaveLength(2);
    expect(state.read.checks[0]).not.toHaveProperty('diagnostic');
    expect(state.read.checks[0].attempts[0].usage).not.toHaveProperty('basis');
    expect(state.commands).toHaveLength(0);
  });

  it.each([
    ['cancel_requested', 'cancelled'],
    ['not_adopted', 'not_adopted'],
    ['unknown', 'interrupted'],
  ] as const)(
    'preserves partial event usage when the check is %s',
    async (status, attemptState) => {
      const original = checkedRun('event-check', status);
      state.read.checks.push({
        ...original,
        stop_requested: status === 'cancel_requested',
        attempts: [
          {
            ...original.attempts[0],
            state: attemptState,
            usage: {
              ...original.attempts[0].usage,
              output_tokens: null,
              cached_input_tokens: 17,
              reasoning_tokens: 5,
              cost_minor: 37,
              currency: 'USD',
              cost_status: 'provider_reported',
              basis: 'events',
              observed_through_seq: 8,
            },
          },
          {
            ...original.attempts[1],
            state: 'interrupted',
            usage: {
              ...original.attempts[1].usage,
              cost_minor: 2,
              currency: null,
              basis: 'events',
              observed_through_seq: 13,
            },
          },
        ],
      });
      mount();
      await screen.findByRole('heading', { name: '项目说明.txt' });
      expect(attemptRow(1).getByText('81 / 未知')).toBeVisible();
      expect(attemptRow(1).getByText('37 USD（最小货币单位）')).toBeVisible();
      expect(attemptRow(2).getByText('132 / 31')).toBeVisible();
      expect(attemptRow(2).getByText('未知', { exact: true })).toBeVisible();
      expect(screen.getAllByText('用量依据：已观测事件（非完整结果）')).toHaveLength(2);
      expect(screen.queryByText('工具往返已通过')).not.toBeInTheDocument();
      fireEvent.click(screen.getByText('责任、授权与逐次依据'));
      expect(screen.getByText(/已观测事件序号：8/)).toBeVisible();
      expect(screen.getByText(/已观测事件序号：13/)).toBeVisible();
      expect(screen.getByText(/缓存输入 17，缓存写入 未知，推理 token 5/)).toBeVisible();
      expect(state.commands).toHaveLength(0);
    },
  );

  it('describes a cancelled attempt as local stop without implying a remote cancellation or refund', async () => {
    const check = checkedRun('cancelled-check', 'cancel_requested');
    check.stop_requested = true;
    check.attempts[0].state = 'cancelled';
    state.read.checks.push(check);
    mount();
    await screen.findByRole('heading', { name: '项目说明.txt' });
    expect(attemptRow(1).getByText('本地已停止')).toBeVisible();
    expect(
      attemptRow(1).getByText('本地停止不表示远端已取消或费用退还；已发生用量仍保留。'),
    ).toBeVisible();
    expect(attemptRow(1).getByText('81 / 17')).toBeVisible();
    expect(attemptRow(1).getByText('未知', { exact: true })).toBeVisible();
    expect(screen.getByText('本地停止已请求')).toBeVisible();
    expect(screen.queryByText('已取消', { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '停止后续步骤' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '核对原验证' })).toBeEnabled();
  });

  it('replaces event usage with the received result fields without adding snapshots or attempts', async () => {
    const check = checkedRun('updating-check', 'unknown');
    const first: ModelAttempt = {
      ...check.attempts[0],
      usage: {
        ...check.attempts[0].usage,
        input_tokens: 10,
        output_tokens: null,
        basis: 'events',
        observed_through_seq: 3,
      },
    };
    const second: ModelAttempt = {
      ...check.attempts[1],
      usage: {
        ...check.attempts[1].usage,
        input_tokens: 20,
        output_tokens: 3,
        basis: 'events',
        observed_through_seq: 4,
      },
    };
    check.attempts = [first, second];
    state.read.checks.push(check);
    const { client } = mount();
    await screen.findByRole('heading', { name: '项目说明.txt' });
    expect(attemptRow(1).getByText('用量依据：已观测事件（非完整结果）')).toBeVisible();
    expect(attemptRow(1).getByText('10 / 未知')).toBeVisible();
    const updated: ModelAttempt = {
      ...first,
      state: 'completed',
      usage: {
        ...first.usage,
        input_tokens: 15,
        output_tokens: 2,
        basis: 'result',
        observed_through_seq: 9,
      },
    };
    check.attempts[0] = updated;
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    expect(await attemptRow(1).findByText('15 / 2')).toBeVisible();
    expect(attemptRow(1).getByText('用量依据：最终结果')).toBeVisible();
    expect(attemptRow(1).queryByText('10 / 未知')).not.toBeInTheDocument();
    expect(attemptRow(2).getByText('20 / 3')).toBeVisible();
    expect(attemptRow(2).getByText('用量依据：已观测事件（非完整结果）')).toBeVisible();
    expect(screen.getByText('验证结果待核对')).toBeVisible();
    fireEvent.click(screen.getByText('责任、授权与逐次依据'));
    expect(screen.getByText(/已观测事件序号：9/)).toBeVisible();
    expect(state.commands).toHaveLength(0);
  });

  it('renders next-step text inertly and clears it with revoked AU read access', async () => {
    const nextStep = '检查 <img src=x onerror=alert(1)>，再核对原操作。';
    state.read.checks.push({
      ...checkedRun('private-diagnostic', 'unknown'),
      diagnostic: { code: 'provider_result_unconfirmed', next_step: nextStep },
    });
    const { client, view } = mount();
    expect(await screen.findByText(nextStep, { exact: false })).toBeVisible();
    expect(view.container.querySelector('img[src="x"]')).toBeNull();
    expect(sessionStorage.getItem('union-model-requests') ?? '').not.toContain(nextStep);
    state.state.onRead = async () => json({ code: 'not_authorized', error: '读取权限已变化' }, 403);
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['core-models'] });
    });
    await waitFor(() =>
      expect(screen.queryByText(nextStep, { exact: false })).not.toBeInTheDocument(),
    );
    expect(state.commands).toHaveLength(0);
  });
});
