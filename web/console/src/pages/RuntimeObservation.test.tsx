import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import type { Snapshot } from '../api/types';
import Members from './Members';
import Resources from './Resources';

const state = vi.hoisted(() => ({ data: null as Snapshot | null }));
vi.mock('../app/workspace', () => ({ useWorkspace: () => state }));
vi.mock('../features/commands/CommandProvider', () => ({ CommandButton: () => <button>受控操作</button> }));
vi.mock('../features/details/Details', () => ({ DetailLink: ({ children }: { children: ReactNode }) => <span>{children}</span> }));

function snapshot(): Snapshot {
  return {
    organization: {
      id: 'org-test', name: '测试组织', goal: '验证运行观察', version: 1, charter_version: 1, policy_version: 1, phase: 'active',
      members: { m1: { id: 'm1', name: '林策' }, m2: { id: 'm2', name: '江墨' } },
      positions: { p1: { id: 'p1', title: '策划', mandate: '规划', version: 1 }, p2: { id: 'p2', title: '写作', mandate: '交付', version: 1 } },
      assignments: { a1: { id: 'a1', member_id: 'm1', position_id: 'p1', active: true }, a2: { id: 'a2', member_id: 'm2', position_id: 'p2', active: true } },
      work: {}, artifacts: {}, resources: { max_calls: 4, timeout_seconds: 60 },
    },
    budget: { calls_reserved: 0, max_calls: 4, blocked_reason: null, cost_status: 'unknown' },
    runs: [], receipts: [], events: [], decisions: [], ready_work: [], execution_config: { codex_model: null }, pending_events: 0,
    next_step: 'wait', blocked_reasons: [], next_review_at: null, collected_at: '2026-10-30T00:00:00Z', execution_state: 'idle', dispatch_state: 'enabled',
    host_activity: { confirmed: false }, runtime: { runtime_id: null, name: '部署位置未登记', mode: 'unregistered', instance_id: null, observed_at: null, liveness: 'unknown', dispatch_state: 'enabled', active_run_id: null, capabilities: [] },
    member_execution: [
      { member_id: 'm1', assignment_ids: ['a1'], current_work_id: 'w1', work_state: 'waiting', reason_codes: ['dependency_pending'], recent_run: null, session: { id: null, updated_at: null, has_checkpoint: false, resume_state: 'not_available' }, workspace: { mode: 'virtual_only', revision: null, available: false, reason_codes: ['workspace_unconfigured'] } },
      { member_id: 'm2', assignment_ids: ['a2'], current_work_id: null, work_state: 'idle', reason_codes: [], recent_run: null, session: { id: null, updated_at: null, has_checkpoint: false, resume_state: 'not_available' }, workspace: { mode: 'virtual_only', revision: null, available: false, reason_codes: ['workspace_unconfigured'] } },
    ],
    pagination: { offset: 0, limit: 50, event_count: 0, decision_count: 0 }, source: 'not_run', service_instance: 'test', snapshot_sequence: 1,
    charter: { text: 'test', allowed_operations: [], allowed_tools: [], reserved_matters: [], board_can_amend: true }, bootstrap: null,
  };
}

describe('member runtime observation', () => {
  it.each([
    ['needs_review', '执行待核对'],
    ['pause_requested', '暂停已请求，结束状态尚待确认'],
  ] as const)('shows the same %s dispatch description in both resource cards', (dispatch, label) => {
    state.data = snapshot();
    state.data.dispatch_state = dispatch;
    state.data.runtime.dispatch_state = dispatch;
    render(<Resources />);
    expect(screen.getAllByText(label)).toHaveLength(2);
  });
  it.each([
    [true, '存在检查点，接续仍需核对'],
    [false, '未发现检查点'],
    [null, '检查点状态未知'],
  ] as const)('shows checkpoint evidence %s without claiming safe resume', (exists, label) => {
    state.data = snapshot();
    // The public contract supports an unknown observation independently of status.
    state.data.member_execution[0].session.has_checkpoint = exists;
    render(<Members />);
    expect(screen.getByText((text) => text.includes('当前工作：w1；会话：') && text.includes(label))).toBeVisible();
    expect(document.body.textContent).not.toContain('可安全恢复');
  });
  it('keeps member work state separate from identity and does not render private workspace details', () => {
    state.data = snapshot(); render(<Members />);
    expect(screen.getAllByText('林策')).toHaveLength(2);
    expect(screen.getByText('等待条件')).toBeVisible();
    expect(screen.getByText('dependency_pending')).toBeVisible();
    expect(document.body.textContent).not.toContain('/workspace');
    expect(document.body.textContent).not.toContain('container');
  });
  it('keeps unregistered deployment separate from unknown host activity', () => {
    state.data = snapshot(); render(<Resources />);
    expect(screen.getByText('部署位置未登记')).toBeVisible();
    expect(screen.getByText('活性未知')).toBeVisible();
    expect(screen.getByText('无已确认的活跃执行')).toBeVisible();
    expect(screen.queryByText('本地控制台有限执行')).toBeNull();
    expect(screen.queryByText('执行待核对')).toBeNull();
    expect(screen.getByText('宿主活性仅反映当前执行证据，不证明部署位置或托管方式。读取不会启动服务、恢复会话或调用模型。')).toBeVisible();
  });
  it('preserves confirmed host evidence without guessing deployment', () => {
    state.data = snapshot();
    state.data.host_activity.confirmed = true;
    state.data.runtime.liveness = 'confirmed';
    state.data.runtime.active_run_id = 'fixture-active-run';
    render(<Resources />);
    expect(screen.getByText('部署位置未登记')).toBeVisible();
    expect(screen.getByText('fixture-active-run')).toBeVisible();
    expect(screen.queryByText('本地控制台有限执行')).toBeNull();
    expect(screen.queryByText('执行待核对')).toBeNull();
  });
  it.each([
    ['embedded', '本地控制台有限执行'],
    ['managed_local', '本机托管'],
    ['external', '外部运行时'],
  ] as const)('keeps display compatibility for an explicit %s mode fixture', (mode, label) => {
    state.data = snapshot();
    state.data.runtime.mode = mode;
    render(<Resources />);
    expect(screen.getByText(label)).toBeVisible();
  });
});
