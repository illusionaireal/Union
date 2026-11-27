import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createHash, webcrypto } from 'node:crypto';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { api, ApiError } from '../../api/client';
import type { CoreModels, CoreWork, CoreWorkItem, CoreWorkResult, Session, WorkDeliveryMode, WorkIntentStatus } from '../../api/types';
import { WorkPanel } from './WorkPanel';
import { MaterialWorkPreparation } from '../materials/MaterialWorkPreparation';

const workspace = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));
vi.mock('../../app/workspace', () => ({ useWorkspace: () => workspace.current }));

vi.mock('../../api/client', async (original) => ({
  ...(await original<typeof import('../../api/client')>()),
  api: {
    session: vi.fn(),
    coreWork: vi.fn(),
    coreModels: vi.fn(),
    coreMaterials: vi.fn(),
    coreWorkCommand: vi.fn(),
    coreWorkReceipt: vi.fn(),
  },
}));
const session = {
  core_protocol: 'core.au.v1',
  principal_id: 'p1',
  service_instance: 's1',
} as Session;
let work: CoreWork, models: CoreModels;
const receipt = (r: Record<string, unknown>) => ({
  id: String(r.id),
  kind: r.kind,
  organization_id: r.organization_id,
  base_version: r.base_version,
  actor_principal_id: 'p1',
  status: 'succeeded',
  version: 5,
  work_id: (r.data as Record<string, unknown>).work_id,
  message: r.kind === 'start_work_intent' ? '意图已接受' : r.kind === 'decide_work_intent' ? '已记录治理决定' :
    r.kind === 'stop_work_intent' ? '已记录停止' : '登记完成',
  ...(r.kind === 'start_work_intent' ? { intent_id: r.id, attempt_id: 'a1', delivery_mode: (r.data as Record<string, unknown>).delivery_mode } : {}),
  ...(['decide_work_intent', 'stop_work_intent'].includes(String(r.kind)) ? Object.fromEntries(
    Object.entries(r.data as Record<string, unknown>).filter(([k]) => k !== 'reason')) : {}),
});
function mount(principalId = 'p1', organizationId = 'au-1') {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}
    >
      <WorkPanel
        organizationId={organizationId}
        principalId={principalId}
        serviceInstance="s1"
        readOnly
        allowExecution
        allowRegistration
      />
    </QueryClientProvider>,
  );
}
function mountNormal() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <MemoryRouter><MaterialWorkPreparation /></MemoryRouter>
    </QueryClientProvider>,
  );
}
async function fill(normal = false) {
  fireEvent.click(await screen.findByText(normal ? '提出工作目标' : '登记新的 AI 工作'));
  fireEvent.change(screen.getByLabelText('工作标题'), { target: { value: '项目概览' } });
  fireEvent.change(screen.getByLabelText('目标'), { target: { value: '私有目标正文' } });
  fireEvent.change(screen.getByLabelText('负责 AI 成员名称'), { target: { value: '研究助手' } });
  await screen.findByRole('option', {name: '授权资料.md · 版本 1'});
  fireEvent.change(screen.getByLabelText('选择业务资料'), { target: { value: `material-${'a'.repeat(32)}:1` } });
  fireEvent.change(screen.getByLabelText('调用上限'), { target: { value: '2' } });
  const button = screen.getByRole('button', { name: normal ? '开始工作' : '登记 AI 工作' });
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal('crypto', webcrypto);
  sessionStorage.clear();
  workspace.current = { core: { au: { id: 'au-1' } }, session };
  work = {
    protocol: 'core.work.v1',
    organization_id: 'au-1',
    version: 4,
    access: { principal_id: 'p1', can_start: true },
    works: [],
    capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
  };
  models = {
    protocol: 'core.models.v1',
    organization_id: 'au-1',
    version: 4,
    access: { principal_id: 'p1', can_configure: true },
    governance_status: 'active',
    document_read_allowed: true,
    connections: [
      {
        id: 'c1',
        name: '当前默认连接',
        revision: 2,
        enabled: true,
        is_default: true,
        profile: 'modeld_grant',
        model: 'model',
      },
    ],
    resources: { grant: null, reserved_calls: 0, plan_max_calls: 10 },
  };
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.coreWork).mockImplementation(async () => structuredClone(work));
  vi.mocked(api.coreModels).mockImplementation(async () => structuredClone(models));
  vi.mocked(api.coreMaterials).mockImplementation(async () => ({protocol: 'core.materials.v1',
    organization_id: work.organization_id, version: work.version, access: {principal_id: work.access.principal_id, can_manage: true},
    limits: {bytes_per_material: 65536, materials: 16, total_bytes: 1048576},
    materials: [{id: 'material-' + 'a'.repeat(32), name: '授权资料.md', source: 'paste', scope: 'au_read_only',
      version: 1, sha256: 'b'.repeat(64), bytes: 5, read_allowed: true, created_at: '', reason: '明确只读'}]}));
  vi.mocked(api.coreWorkCommand).mockImplementation(async r => {
    if (r.kind === 'start_work_intent') persistStart(r);
    return { receipt: receipt(r) };
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it('starts a durable intent with one submission from the normal Work route', async () => {
  mountNormal();
  const button = await fill(true);
  fireEvent.click(button);
  fireEvent.click(button);
  await screen.findByText('意图已接受');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.coreWorkCommand).mock.calls[0][0]).toMatchObject({
    id: expect.stringMatching(new RegExp(`^intent-${createHash('sha256').update('au-1').digest('hex').slice(0, 24)}-[a-f0-9]{32}$`)),
    kind: 'start_work_intent',
    data: { constraints: '', delivery_mode: 'automatic_text', material_version: 1 },
  });
});

it('blocks an oversized UTF-8 start envelope before saving an original ID and keeps the goal', async () => {
  mountNormal();
  const start = await fill(true);
  const oversizedGoal = '研'.repeat(67000);
  fireEvent.change(screen.getByLabelText('目标'), {target: {value: oversizedGoal}});
  fireEvent.click(start);
  await screen.findByText(/请求超过 200000 UTF-8 字节/);
  expect(screen.getByLabelText('目标')).toHaveValue(oversizedGoal);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(sessionStorage.length).toBe(0);
});

it('recovers an uncertain start across service restart by original intent ID without posting again', async () => {
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  const view = mountNormal();
  const button = await fill(true);
  fireEvent.change(screen.getByLabelText('约束（选填）'), { target: { value: '只用这份资料' } });
  fireEvent.change(screen.getByRole('combobox', { name: '交付方式' }), { target: { value: 'governor_review' } });
  fireEvent.click(button);
  await screen.findByText('连接中断');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  expect(original.data).toMatchObject({ constraints: '只用这份资料', delivery_mode: 'governor_review' });
  expect(JSON.stringify(sessionStorage)).toContain(String(original.id));
  expect(JSON.stringify(sessionStorage)).not.toMatch(/只用这份资料|私有目标正文/);
  view.unmount();
  persistStart(original, 'running');
  work.access.can_start = false;
  const restarted = { ...session, service_instance: 's2' };
  workspace.current = { core: { au: { id: 'au-1' } }, session: restarted };
  vi.mocked(api.session).mockResolvedValue(restarted);
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  mountNormal();
  fireEvent.click(await screen.findByRole('button', { name: '查询开始工作的原请求' }));
  await screen.findByText('意图已接受');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each([
  [400, 'invalid_request'],
  [403, 'not_authorized'],
] as const)('preserves the start draft after direct HTTP %i refusal and requires a new explicit ID', async (status, code) => {
  vi.mocked(api.coreWorkCommand).mockRejectedValueOnce(new ApiError('服务器明确拒绝请求', status, code));
  mountNormal();
  const start = await fill(true);
  fireEvent.change(screen.getByLabelText('约束（选填）'), { target: { value: '保留原约束' } });
  fireEvent.click(start);
  await screen.findByText('服务器明确拒绝请求');
  expect(screen.getByRole('button', {name: '查询开始工作的原请求'})).toBeEnabled();
  fireEvent.click(screen.getByRole('button', {name: '返回工作目标'}));
  expect(screen.getByLabelText('目标')).toHaveValue('私有目标正文');
  expect(screen.getByLabelText('约束（选填）')).toHaveValue('保留原约束');
  fireEvent.click(screen.getByText('提出工作目标'));
  const retry = screen.getByRole('button', {name: '开始工作'});
  await waitFor(() => expect(retry).toBeEnabled());
  fireEvent.click(retry);
  await screen.findByText('意图已接受');
  const requests = vi.mocked(api.coreWorkCommand).mock.calls.map(([r]) => r);
  expect(requests).toHaveLength(2);
  expect(requests[1].id).not.toBe(requests[0].id);
  expect(JSON.stringify(sessionStorage)).toContain(String(requests[0].id));
});

it('keeps the original start unresolved when only its later Work read is invalid', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementationOnce(async r => {
    persistStart(r);
    vi.mocked(api.coreWork).mockRejectedValueOnce(new ApiError('提交后的读取失败', 400, 'invalid_request'));
    return { receipt: receipt(r) };
  });
  mountNormal();
  fireEvent.click(await fill(true));
  await screen.findByText('提交后的读取失败');
  expect(screen.getByRole('button', {name: '查询开始工作的原请求'})).toBeEnabled();
  expect(screen.queryByRole('button', {name: '返回工作目标'})).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each([401, 403])('keeps a direct HTTP %i without a Core code unresolved', async status => {
  vi.mocked(api.coreWorkCommand).mockRejectedValueOnce(new ApiError('中间服务返回错误', status));
  mountNormal();
  fireEvent.click(await fill(true));
  await screen.findByText('中间服务返回错误');
  expect(screen.getByRole('button', {name: '查询开始工作的原请求'})).toBeEnabled();
  expect(screen.queryByRole('button', {name: '返回工作目标'})).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each([
  [400, 'invalid_request'],
  [401, 'not_authenticated'],
  [403, 'not_authorized'],
] as const)('retains a verified original start after a late HTTP %i refusal', async (status, code) => {
  let fail!: (reason: Error) => void;
  vi.mocked(api.coreWorkCommand).mockImplementationOnce(() => new Promise((_resolve, reject) => {fail = reject;}));
  mountNormal();
  fireEvent.click(await fill(true));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  persistStart(original);
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({receipt: receipt(original)});
  fireEvent.click(await screen.findByRole('button', {name: '查询开始工作的原请求'}));
  await screen.findByText('意图已接受');
  fail(new ApiError('迟到的命令拒绝', status, code));
  await waitFor(() => expect(screen.getByRole('button', {name: '提出另一项工作'})).toBeEnabled());
  expect(screen.queryByText('迟到的命令拒绝')).toBeNull();
  expect(JSON.stringify(sessionStorage)).not.toContain('refusedBeforeAcceptance');
});

const candidate: CoreWorkResult = { id: 'result-1', seq: 1, title: '可读候选', sha256: 'c'.repeat(64), bytes: 4,
  status: 'candidate', sources: ['work-1#1'], created_at: '', adopted_at: null };
const decision = { result_id: candidate.id, result_seq: candidate.seq, sha256: candidate.sha256,
  input_cursor: 2, authorized_principal_id: 'p1' };
function workItem(overrides: Partial<CoreWorkItem> = {}): CoreWorkItem {
  return {
    id: 'work-1', title: '原工作', goal: '说明资料', status: 'pending', version: 1, max_calls: 2,
    materials_root: null, created_at: '', responsible: { member_id: 'm1', name: '研究成员', binding_id: 'b1', duty: '研究' },
    definition: { id: 'd1', version: 1, connection_id: 'c1', model: 'model', tools: [] },
    mandate: { id: 'ma1', version: 1, actions: [], active: true }, attempt_ids: ['a1'], result_ids: [],
    tool_calls: [], attempts: [{ id: 'a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null }],
    steps: [], budget: { max_calls: 2, reserved: 0, used: 1 },
    materials: { reference: null, available: false, documents: 0 }, results: [], input_seq: 0,
    ...overrides,
  };
}
function persistStart(request: Record<string, unknown>, status: WorkIntentStatus = 'accepted') {
  const data = request.data as Record<string, string>;
  work.works.push(workItem({
    id: data.work_id,
    intent: { id: String(request.id), status, delivery_mode: data.delivery_mode as WorkDeliveryMode,
      authorized_principal_id: 'p1', attempt_id: 'a1', reason: '原执行待推进' },
  }));
  work.version++;
}
function managedWork(status: WorkIntentStatus = 'awaiting_decision') {
  work.access.can_manage_results = true;
  work.works = [workItem({
    attempts: [], result_ids: [candidate.id], results: [candidate], input_seq: 2,
    intent: { id: 'intent-1', status, delivery_mode: 'governor_review', authorized_principal_id: 'p1',
      attempt_id: 'a1', reason: '等待核对候选覆盖的输入', decision },
  })];
}

it('keeps the original start unresolved when the accepted receipt names a different attempt', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementationOnce(async r => {
    persistStart(r, 'running');
    return { receipt: { ...receipt(r), attempt_id: 'different-attempt' } };
  });
  mountNormal();
  fireEvent.click(await fill(true));
  await screen.findByText(/回执与原工作不匹配/);
  expect(screen.getByRole('button', {name: '查询开始工作的原请求'})).toBeEnabled();
  expect(screen.queryByRole('button', {name: '提出另一项工作'})).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it('uses the projected candidate for one explicit decision and links to the scoped reader', async () => {
  managedWork();
  vi.mocked(api.coreWorkCommand).mockImplementation(async r => {
    const item = work.works[0];
    item.intent!.status = 'delivered';
    item.status = 'delivered';
    item.delivered_result_id = candidate.id;
    item.results = [{ ...candidate, status: 'adopted' }];
    work.version++;
    return { receipt: receipt(r) };
  });
  mountNormal();
  await screen.findByText('等待治理决定');
  expect(screen.getByRole('link', {name: '阅读与下载'})).toHaveAttribute('href', '/au/au-1/work/work-1/results/result-1');
  expect(screen.queryByText('已交付')).toBeNull();
  expect(screen.queryByRole('button', {name: '开始执行'})).toBeNull();
  fireEvent.click(screen.getByRole('button', {name: '批准并交付此成果'}));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledWith(expect.objectContaining({
    kind: 'decide_work_intent', base_version: 4,
    data: { work_id: 'work-1', intent_id: 'intent-1', result_id: candidate.id, result_seq: candidate.seq,
      sha256: candidate.sha256, input_cursor: 2, reason: expect.any(String) },
  })));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  await screen.findByText('已记录治理决定');
  expect(await screen.findByText('已交付')).toBeVisible();
  expect(screen.queryByRole('button', {name: '批准并交付此成果'})).toBeNull();
});

it('stops the original intent without a manual finish or remote cancellation claim', async () => {
  managedWork('waiting_unknown');
  work.works[0].budget.reserved = 1;
  vi.mocked(api.coreWorkCommand).mockImplementation(async r => {
    work.works[0].intent!.status = 'stopped';
    work.works[0].intent!.reason = '未决原请求和预算仍须核对';
    work.version++;
    return { receipt: receipt(r) };
  });
  mountNormal();
  fireEvent.click(await screen.findByRole('button', {name: '停止工作'}));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledWith(expect.objectContaining({
    kind: 'stop_work_intent', base_version: 4,
    data: { work_id: 'work-1', intent_id: 'intent-1', reason: expect.any(String) },
  })));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  await screen.findByText('已记录停止');
  expect(await screen.findByText('已停止后续推进')).toBeVisible();
  expect(screen.getByText(/1 已预约/)).toBeVisible();
  expect(screen.queryByText('已交付')).toBeNull();
});

it('withholds candidate approval when the projection reports newer input', async () => {
  managedWork();
  work.works[0].input_seq = 3;
  mountNormal();
  await screen.findByText('等待治理决定');
  expect(screen.queryByRole('button', {name: '批准并交付此成果'})).toBeNull();
  expect(screen.getByRole('link', {name: '阅读与下载'})).toBeVisible();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('explains when the current viewer cannot approve and preserves the candidate link', async () => {
  managedWork();
  work.works[0].intent!.decision = { ...decision, authorized_principal_id: 'another-principal' };
  mountNormal();
  await screen.findByText('当前身份不能批准此候选，等待有权治理者处理。');
  expect(screen.queryByRole('button', {name: '批准并交付此成果'})).toBeNull();
  expect(screen.getByRole('link', {name: '阅读与下载'})).toBeVisible();
});

it('keeps legacy manual commands unavailable for managed Work', async () => {
  managedWork('accepted');
  work.works[0].results = [];
  work.works[0].result_ids = [];
  mount();
  await screen.findByText('原工作');
  expect(screen.queryByRole('button', {name: '准备本轮执行'})).toBeNull();
});

it.each([
  ['批准并交付此成果', '批准交付', 400, 'invalid_request'],
  ['停止工作', '停止工作', 403, 'not_authorized'],
] as const)('restores the %s action only after a definite refusal', async (action, label, status, code) => {
  managedWork();
  vi.mocked(api.coreWorkCommand).mockRejectedValueOnce(new ApiError('操作明确被拒绝', status, code));
  mountNormal();
  fireEvent.click(await screen.findByRole('button', {name: action}));
  await screen.findByText('操作明确被拒绝');
  expect(screen.getByRole('button', {name: `查询${label}的原请求`})).toBeEnabled();
  fireEvent.click(screen.getByRole('button', {name: `重新核对${label}`}));
  expect(screen.getByRole('button', {name: action})).toBeEnabled();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it('Core empty state registers one bounded responsible Work, persisting original identity before POST', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    expect(JSON.stringify(sessionStorage)).toContain(String(r.id));
    expect(JSON.stringify(sessionStorage)).toContain(
      String((r.data as Record<string, unknown>).work_id),
    );
    expect(JSON.stringify(sessionStorage)).not.toMatch(/私有目标正文|private-docs|研究助手/);
    return { receipt: receipt(r) };
  });
  mount();
  const button = await fill();
  fireEvent.click(button);
  fireEvent.click(button);
  await screen.findByText('登记完成');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.coreWorkCommand).mock.calls[0][0]).toMatchObject({
    kind: 'start_work',
    base_version: 4,
    data: {
      title: '项目概览',
      goal: '私有目标正文',
      member_name: '研究助手',
      connection_id: 'c1',
      expected_revision: 2,
      materials_root: 'material-' + 'a'.repeat(32), material_version: 1,
      max_calls: 2,
      tools: ['read_document'],
    },
  });
  expect(screen.queryByLabelText('成果正文')).toBeNull();
  expect(screen.queryByText('结束执行')).toBeNull();
});

it('lost response reload keeps original lookup even without permission to start, and never replays', async () => {
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  const view = mount();
  fireEvent.click(await fill());
  await screen.findByText('连接中断');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  work.access.can_start = false;
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询登记原请求' }));
  await screen.findByText('登记完成');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('button', { name: '登记 AI 工作' })).toBeNull();
});

it('storage failure prevents any POST', async () => {
  mount();
  const button = await fill();
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota');
  });
  fireEvent.click(button);
  await screen.findByText(/浏览器无法保留原请求/);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it.each(['principal', 'service', 'authorization', 'connection', 'version', 'model-scope'])(
  'fresh %s change rejects registration before POST',
  async (change) => {
    mount();
    const button = await fill();
    if (change === 'principal')
      vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'p2' });
    if (change === 'service')
      vi.mocked(api.session).mockResolvedValue({ ...session, service_instance: 's2' });
    if (change === 'authorization') work.access.can_start = false;
    if (change === 'connection') models.connections[0].revision++;
    if (change === 'version') work.version++;
    if (change === 'model-scope') models.organization_id = 'au-2';
    fireEvent.click(button);
    await screen.findByText(/权限或身份已变化|配置或版本已变化|当前不能登记新工作/);
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
    if (change === 'model-scope') expect(screen.queryByLabelText('目标')).toBeNull();
  },
);

it.each(['actor', 'work', 'version'])('mismatched %s receipt stays unresolved', async (change) => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({
    receipt: {
      ...receipt(r),
      ...(change === 'actor'
        ? { actor_principal_id: 'p2' }
        : change === 'work'
          ? { work_id: 'wrong' }
          : { base_version: 99 }),
    },
  }));
  mount();
  fireEvent.click(await fill());
  await screen.findByText(/回执与原请求不匹配/);
  expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
  expect(screen.getByRole('button', { name: '查询登记原请求' })).toBeTruthy();
});

it('loss of registration eligibility preserves readable work and its original execution lookup', async () => {
  work.works = [
    {
      id: 'existing-work',
      title: '已有工作',
      goal: '原工作继续负责',
      status: 'pending',
      version: 1,
      max_calls: 2,
      materials_root: 'docs',
      created_at: '',
      responsible: { member_id: 'm0', name: '原助手', binding_id: 'b0', duty: '交付' },
      definition: {
        id: 'd0',
        version: 1,
        connection_id: 'c1',
        model: 'model',
        tools: ['read_document'],
      },
      mandate: { id: 'ma0', version: 1, actions: ['read_document'], active: true },
      attempt_ids: [],
      result_ids: [],
      attempts: [],
      steps: [],
      tool_calls: [],
      results: [],
      budget: { max_calls: 2, reserved: 1, used: 0 },
      materials: { reference: 'docs', available: true, documents: 1 },
    },
  ];
  const scope = {
    principalId: 'p1',
    serviceInstance: 's1',
    organizationId: 'au-1',
    workId: 'existing-work',
  };
  const original = {
    ...scope,
    id: 'existing-command',
    kind: 'run_loop',
    base_version: 3,
    resolved: false,
  };
  sessionStorage.setItem(
    'union-work-execution:' + JSON.stringify(scope),
    JSON.stringify([original]),
  );
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({
    receipt: {
      id: original.id,
      kind: original.kind,
      organization_id: 'au-1',
      base_version: 3,
      actor_principal_id: 'p1',
      status: 'succeeded',
      version: 4,
      message: '原执行已核对',
    },
  });
  mount();
  const button = await fill();
  work.access.can_start = false;
  fireEvent.click(button);
  await screen.findByText(/权限或身份已变化|当前不能登记新工作/);
  expect(screen.getByText('已有工作')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: '查询原请求' }));
  await screen.findByText('原执行已核对');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id);
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: '登记 AI 工作' })).toBeNull();
});

it.each([401, 403])(
  'an actual AU read denial (%s) still clears registration and prevents POST',
  async (status) => {
    mount();
    const button = await fill();
    vi.mocked(api.coreWork).mockRejectedValue(new ApiError('not_authorized', status));
    fireEvent.click(button);
    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByLabelText('目标')).toBeNull();
    expect(api.coreWorkCommand).not.toHaveBeenCalled();
  },
);

it('corrupt persisted identity prevents a replacement POST', async () => {
  sessionStorage.setItem(
    'union-work-command:' +
      JSON.stringify({ principalId: 'p1', serviceInstance: 's1', organizationId: 'au-1' }),
    '{broken',
  );
  mount();
  await screen.findByText(/原请求记录不可读/);
  expect(screen.getByRole('button', { name: '登记 AI 工作' })).toBeDisabled();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('an unknown receipt retains original identity and prevents another registration', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => ({
    receipt: { ...receipt(r), status: 'unknown', message: '结果未知' },
  }));
  mount();
  fireEvent.click(await fill());
  await screen.findByText('结果未知');
  expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
  expect(screen.getByRole('button', { name: '查询登记原请求' })).toBeTruthy();
});

it('reload revalidates a persisted completion before allowing another registration', async () => {
  const view = mount();
  fireEvent.click(await fill());
  await screen.findByText('登记完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  mount();
  await screen.findByRole('button', { name: '查询登记原请求' });
  expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
  await screen.findByRole('button', { name: '登记另一项工作' });
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each(['0', '-1', '1.5', '10001'])('invalid call cap %s cannot be submitted', async (calls) => {
  mount();
  const button = await fill();
  fireEvent.change(screen.getByLabelText('调用上限'), { target: { value: calls } });
  expect(button).toBeDisabled();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('a confirmed original permits only explicit new work, retaining the previous identity', async () => {
  mount();
  fireEvent.click(await fill());
  await screen.findByText('登记完成');
  const first = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  fireEvent.click(screen.getByRole('button', { name: '登记另一项工作' }));
  fireEvent.click(await fill());
  await screen.findByText('登记完成');
  const second = vi.mocked(api.coreWorkCommand).mock.calls[1][0];
  expect(first.id).not.toBe(second.id);
  expect(JSON.stringify(sessionStorage)).toContain(String(first.id));
  expect(JSON.stringify(sessionStorage)).toContain(String(second.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(2);
});

it('receipt-only 403 preserves original ID when current AU read remains authorized', async () => {
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('连接中断'));
  vi.mocked(api.coreWorkReceipt).mockRejectedValue(new ApiError('not_authorized', 403));
  mount();
  fireEvent.click(await fill());
  await screen.findByText('连接中断');
  fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
  await screen.findByText(/原回执尚不可取得/);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: '查询登记原请求' })).toBeEnabled();
});

it('permission lost after committed POST clears old result and prevents adoption', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    vi.mocked(api.coreWork).mockRejectedValue(new ApiError('not_authorized', 403));
    return { receipt: receipt(r) };
  });
  mount();
  fireEvent.click(await fill());
  await screen.findByText(/权限或身份已变化/);
  expect(screen.queryByText('登记完成')).toBeNull();
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(sessionStorage)).toContain('start_work');
});

it('unmounted old principal cannot adopt a late response into the new scope', async () => {
  let finish!: (v: { receipt: ReturnType<typeof receipt> }) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const view = mount();
  fireEvent.click(await fill());
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  view.unmount();
  work.access.principal_id = 'p2';
  work.access.can_start = false;
  mount('p2');
  finish({ receipt: receipt(original) });
  await screen.findByText(/尚未登记 V1 工作/);
  expect(screen.queryByText('登记完成')).toBeNull();
  expect(screen.queryByRole('button', { name: '查询登记原请求' })).toBeNull();
});

it('a late failed POST cannot downgrade an independently confirmed original receipt', async () => {
  let fail!: (reason: Error) => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(
    () =>
      new Promise((_resolve, reject) => {
        fail = reject;
      }),
  );
  mount();
  fireEvent.click(await fill());
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
  await screen.findByText('登记完成');
  fail(new Error('late lost response'));
  await waitFor(() => expect(screen.getByRole('button', { name: '登记另一项工作' })).toBeEnabled());
  expect(screen.getByText('登记完成')).toBeTruthy();
  expect(screen.queryByText('late lost response')).toBeNull();
});

it.each(['principal', 'service', 'read401', 'read403', 'post401', 'post403'])(
  'confirmed receipt does not suppress a later %s denial while POST is pending',
  async (change) => {
    let finish!: (value: { receipt: ReturnType<typeof receipt> }) => void;
    let fail!: (reason: Error) => void;
    vi.mocked(api.coreWorkCommand).mockImplementation(
      () => new Promise((resolve, reject) => { finish = resolve; fail = reject; }),
    );
    mount();
    fireEvent.click(await fill());
    await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(1));
    const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
    vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
    fireEvent.click(screen.getByRole('button', { name: '查询登记原请求' }));
    await screen.findByText('登记完成');

    if (change === 'principal')
      vi.mocked(api.session).mockResolvedValue({ ...session, principal_id: 'p2' });
    if (change === 'service')
      vi.mocked(api.session).mockResolvedValue({ ...session, service_instance: 's2' });
    if (change.startsWith('read'))
      vi.mocked(api.coreWork).mockRejectedValue(new ApiError('not_authorized', Number(change.slice(4))));
    if (change.startsWith('post')) fail(new ApiError('not_authorized', Number(change.slice(4))));
    else finish({ receipt: receipt(original) });

    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByText('登记完成')).toBeNull();
    expect(screen.queryByRole('button', { name: '登记另一项工作' })).toBeNull();
    expect(JSON.stringify(sessionStorage)).toContain(String(original.id));
    expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  },
);
