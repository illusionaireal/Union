import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../../api/client';
import App from '../../app/App';
import type { CoreAURead } from '../../api/types';
import type { GovernanceKind, GovernanceRequest } from './types';
import {
  governedAU,
  governanceSession,
  otherPrincipal,
  preparedAU,
  principal,
} from './test-fixtures';

const auth = { configured: true, authenticated: true, can_setup: false, account: 'participant' };
const json = (value: unknown, status = 200) =>
  ({ ok: status < 400, status, json: async () => value }) as Response;
const receipt = (request: GovernanceRequest) => ({
  id: request.id,
  organization_id: request.organization_id,
  kind: request.kind,
  base_version: request.base_version,
  actor_principal_id: principal,
  created_at: '2026-11-05T00:00:00Z',
  status: 'succeeded' as const,
  message: '本地操作已保存',
  version: request.base_version + 1,
});
let fetchMock = vi.fn<typeof fetch>();
beforeEach(() => {
  window.history.replaceState(null, '', '/overview?organization=core-au');
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
  vi.spyOn(api, 'session').mockResolvedValue(governanceSession);
  vi.spyOn(api, 'authStatus').mockResolvedValue(auth);
  vi.spyOn(api, 'coreAU').mockResolvedValue(governedAU());
  vi.spyOn(api, 'coreWork').mockResolvedValue({
    protocol: 'core.work.v1', organization_id: 'core-au', version: 3,
    access: { principal_id: principal, can_start: false }, works: [],
    capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false },
  });
  fetchMock = vi.fn(async (_path, init) =>
    json({ receipt: receipt(JSON.parse(String(init?.body))) }),
  );
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

function mount(read?: CoreAURead, path = 'overview') {
  if (read) vi.mocked(api.coreAU).mockResolvedValue(read);
  window.history.replaceState(null, '', `/${path}?organization=core-au`);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  const view = render(
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>,
  );
  return { client, view };
}
async function open(label: string) {
  fireEvent.click((await screen.findAllByRole('button', { name: label }))[0]);
  return screen.findByRole('dialog');
}
function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}
async function preview() {
  fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
  return screen.findByRole('button', { name: '确认提交' });
}
async function commit() {
  const button = await preview();
  fireEvent.click(button);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  return JSON.parse(String(fetchMock.mock.calls[0][1]?.body)) as GovernanceRequest;
}

describe('governance user journey', () => {
  it.each(['overview', 'tasks', 'settings'])(
    'keeps account-level AU creation available from a governed %s page without governing commands',
    async (path) => {
      const read = governedAU();
      read.access.commands = [];
      mount(read, path);
      const creation = await screen.findByRole('button', { name: '创建另一个 AU' });
      expect(creation).toBeEnabled();
      fireEvent.click(creation);
      expect(await screen.findByLabelText('AU名称')).toBeVisible();
    },
  );

  it('renders server readiness gaps without misreporting missing governing identities as an expired deadline', async () => {
    const read = governedAU();
    read.governance_status = 'unavailable';
    read.capabilities.local_submission = false;
    read.readiness_gaps = ['当前治理账号已失效，请按现行失能程序处理', '指定后继账号不存在'];
    read.access.commands = [];
    mount(read);
    expect(await screen.findByText('当前治理账号已失效，请按现行失能程序处理')).toBeVisible();
    expect(screen.getByText('指定后继账号不存在')).toBeVisible();
    expect(screen.queryByText('治理期限已到')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '续期治理' })).not.toBeInTheDocument();
  });

  it('separates the original root from current authority and renders only server-provided actions', async () => {
    const read = governedAU();
    read.au.governance_root = {
      creator_principal_id: otherPrincipal,
      governor_principal_id: otherPrincipal,
    };
    read.access.commands = ['renew_governance'];
    mount(read);
    const section = await screen.findByRole('region', { name: '本地治理' });
    expect(within(section).getByText('当前治理者')).toBeVisible();
    expect(within(section).getByText('初始治理主体')).toBeVisible();
    expect(within(section).getByText(otherPrincipal)).toBeVisible();
    expect(within(section).getByText('最终决定方')).toBeVisible();
    expect(screen.getByRole('button', { name: '续期治理' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: '修订章程' })).not.toBeInTheDocument();
    expect(
      screen.getByText('内部文字记录已启用；AI 执行、资源使用和对外承诺尚未启用。'),
    ).toBeVisible();
  });

  it('previews and adopts a single-principal exit procedure without activating business', async () => {
    mount(preparedAU());
    await open('采用本地治理');
    fill('有效期（秒）', '3600');
    fill('决定依据', '采用单主体超时退出程序');
    const request = await commit();
    expect(request).toMatchObject({
      organization_id: 'core-au',
      base_version: 0,
      kind: 'adopt_governance',
      data: {
        reason: '采用单主体超时退出程序',
        config: {
          profile: 'local_governance.v1',
          final_decision_principal_id: principal,
          reserved_matters: [
            'charter',
            'goal',
            'resources',
            'appointments',
            'mandates',
            'dissolution',
          ],
          unavailability: { mode: 'exit_after_timeout', timeout_seconds: 3600 },
        },
      },
    });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/governance/commands');
    expect(await screen.findByText('本地操作已保存')).toBeVisible();
    expect(screen.getByText('这是原请求的历史回执，不代表你现在仍有 AU 权限。')).toBeVisible();
  });

  it('configures an explicit successor principal without treating its name as authority', async () => {
    mount();
    await open('调整治理程序');
    fill('失能处理方式', 'successor_after_timeout');
    fill('后继者核心身份标识', otherPrincipal);
    fill('有效期（秒）', '7200');
    fill('决定依据', '预先指定恢复责任');
    const request = await commit();
    expect(request.data).toMatchObject({
      config: {
        unavailability: {
          mode: 'successor_after_timeout',
          successor_principal_id: otherPrincipal,
          timeout_seconds: 7200,
        },
      },
    });
    expect(request.kind).toBe('configure_governance');
  });

  it.each([
    ['acknowledge_recovery', '确认恢复职责'],
    ['activate_governance', '启用本地治理'],
    ['renew_governance', '续期治理'],
    ['accept_governance', '确认接任治理'],
    ['recover_governance', '按失能程序接任'],
    ['exit_governance', '退出治理'],
  ] as const)(
    'previews and explicitly submits %s using the current server version',
    async (kind, label) => {
      const read = governedAU();
      read.access.commands = [kind];
      mount(read);
      await open(label);
      fill('决定依据', '当前主体明确确认');
      const request = await commit();
      expect(request).toMatchObject({
        kind,
        base_version: 12,
        data: { reason: '当前主体明确确认' },
      });
    },
  );

  it('nominates another core identity and offers explicit cancellation of an existing nomination', async () => {
    const read = governedAU();
    read.au.governance.nomination = {
      principal_id: otherPrincipal,
      policy_version: 1,
      reason: '已有提名',
    };
    mount(read);
    await open('提名治理接任者');
    fireEvent.click(screen.getByLabelText('取消当前提名'));
    fill('决定依据', '撤回尚未确认的提名');
    const request = await commit();
    expect(request.data).toEqual({ principal_id: null, reason: '撤回尚未确认的提名' });
  });

  it('revises only the displayed charter fields while preserving other stored fields', async () => {
    mount(undefined, 'settings');
    await open('修订章程');
    fill('章程正文', '内部记录暂不采用');
    fireEvent.click(screen.getByLabelText('允许内部文字记录'));
    fill('决定依据', '暂停此项行动');
    const request = await commit();
    expect(request.data).toEqual({
      reason: '暂停此项行动',
      charter: {
        ...governedAU().au.charter,
        text: '内部记录暂不采用',
        allowed_operations: [],
      },
    });
  });

  it('retains a new goal draft and focus across same-principal renewal and polling', async () => {
    const { client } = mount();
    await open('更新目标');
    fill('AU目标', '尚未提交的目标');
    const field = screen.getByLabelText('AU目标');
    field.focus();
    vi.mocked(api.session).mockResolvedValue({
      ...governanceSession,
      session_scope: 'renewed-session',
    });
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['workspace'] });
    });
    expect(screen.getByLabelText('AU目标')).toBe(field);
    expect(field).toHaveValue('尚未提交的目标');
    expect(field).toHaveFocus();
    fill('决定依据', '更新当前目标');
    const request = await commit();
    expect(request).toMatchObject({
      kind: 'set_goal',
      data: { goal: '尚未提交的目标', reason: '更新当前目标' },
    });
  });
});

describe('controlled responsibility forms', () => {
  it('appoints a human member with separate generated member and responsibility IDs', async () => {
    mount(undefined, 'tasks');
    await open('登记责任成员');
    fill('成员姓名', '参与记录的人');
    fill('成员核心身份标识', otherPrincipal);
    fill('职责说明', '保存明确的文字记录');
    const request = await commit();
    expect(request).toMatchObject({
      kind: 'appoint',
      data: {
        principal_id: otherPrincipal,
        name: '参与记录的人',
        duty: '保存明确的文字记录',
      },
    });
    expect(request.data.member_id).toMatch(/^[a-zA-Z0-9-]+$/);
    expect(request.data.binding_id).not.toBe(request.data.member_id);
  });

  it.each([
    {
      kind: 'update_appointment',
      label: '修改职责',
      fields: { 职责说明: '修订后的明确职责', 决定依据: '职责范围变化' },
      data: { binding_id: 'binding-one', duty: '修订后的明确职责', reason: '职责范围变化' },
    },
    {
      kind: 'create_work',
      label: '创建内部工作',
      fields: { 工作标题: '新的内部记录', 工作说明: '记录可核对的内容' },
      data: {
        responsible_binding_id: 'binding-one',
        title: '新的内部记录',
        instruction: '记录可核对的内容',
      },
    },
    {
      kind: 'update_work',
      label: '调整工作',
      fields: {
        工作标题: '调整后的内部工作',
        工作说明: '保存必要内容',
        工作状态: 'stopped',
        决定依据: '范围待核对',
      },
      data: {
        work_id: 'work-one',
        title: '调整后的内部工作',
        instruction: '保存必要内容',
        status: 'stopped',
        reason: '范围待核对',
      },
    },
    {
      kind: 'grant_mandate',
      label: '授予文字记录授权',
      fields: {},
      data: {
        work_id: 'work-one',
        binding_id: 'binding-one',
        parent_id: null,
        actions: ['record_memory'],
        can_delegate: false,
      },
    },
    {
      kind: 'revoke_mandate',
      label: '撤销授权',
      fields: { 决定依据: '该范围不再获准' },
      data: { mandate_id: 'mandate-one', reason: '该范围不再获准' },
    },
    {
      kind: 'handoff_responsibility',
      label: '交接责任',
      fields: { 接收责任成员: 'binding-two', 决定依据: '由接收人继续原工作' },
      data: {
        from_binding_id: 'binding-one',
        to_binding_id: 'binding-two',
        reason: '由接收人继续原工作',
      },
    },
    {
      kind: 'begin_local_action',
      label: '开始文字提交',
      fields: {},
      data: { work_id: 'work-one', mandate_id: 'mandate-one' },
    },
    {
      kind: 'submit_local_result',
      label: '提交文字内容',
      fields: { 文字内容: '受控的内部手工记录' },
      data: { attempt_id: 'attempt-one', content: '受控的内部手工记录' },
    },
    {
      kind: 'accept_local_result',
      label: '采用提交内容',
      fields: { 决定依据: '已核对记录与责任' },
      data: { attempt_id: 'attempt-submitted', reason: '已核对记录与责任' },
    },
  ])(
    'uses existing record choices for $kind and sends its exact responsibility payload',
    async ({ kind, label, fields, data }) => {
      const read = governedAU();
      read.access.commands = [kind as GovernanceKind];
      mount(read, 'tasks');
      await open(label);
      for (const [name, value] of Object.entries(fields)) fill(name, value);
      const request = await commit();
      expect(request.kind).toBe(kind);
      expect(request.data).toMatchObject(data);
      expect(screen.getByText('受控内部记录 · 人类手工提交')).toBeVisible();
    },
  );
});

describe('governance command recovery boundaries', () => {
  it.each([undefined, 'not_authenticated'])(
    'keeps an editable draft after a command endpoint 401 with code %s',
    async (code) => {
      fetchMock.mockResolvedValue(json({ code, error: '命令入口拒绝登录' }, 401));
      mount();
      await open('更新目标');
      fill('AU目标', '尚未提交的目标');
      fill('决定依据', '恢复登录后重新核对');
      const request = await commit();
      expect(await screen.findByText(/命令入口拒绝登录/)).toBeVisible();
      expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
      expect(screen.getByLabelText('AU目标')).toHaveValue('尚未提交的目标');
      expect(screen.queryByText('结果尚未确认')).not.toBeInTheDocument();
      expect(sessionStorage.getItem('union-governance-requests') ?? '').not.toContain(request.id);
    },
  );

  it.each([
    { status: 401, code: 'not_authenticated' },
    { status: 401, code: undefined },
    { status: 409, code: 'incompatible_state' },
  ])(
    'retains the original request when identity verification fails with $status/$code after a successful POST',
    async ({ status, code }) => {
      fetchMock.mockImplementation(async (_path, init) => {
        const original = JSON.parse(String(init?.body)) as GovernanceRequest;
        vi.mocked(api.session).mockRejectedValue(new ApiError('身份复核失败', status, code));
        return json({ receipt: receipt(original) });
      });
      mount();
      const dialog = await open('更新目标');
      fill('AU目标', '已提交但尚未确认的目标');
      fill('决定依据', '保留原请求以核对保存结果');
      const request = await commit();
      expect(await within(dialog).findByText(/身份复核失败/)).toBeVisible();
      expect(sessionStorage.getItem('union-governance-requests')).toContain(request.id);
      expect(screen.getByText('结果尚未确认')).toBeVisible();
      expect(screen.queryByRole('button', { name: '预览影响' })).not.toBeInTheDocument();
      vi.mocked(api.session).mockResolvedValue(governanceSession);
      fetchMock.mockResolvedValueOnce(json({ receipt: receipt(request) }));
      fireEvent.click(screen.getByRole('button', { name: '查询原请求回执' }));
      expect(await screen.findByText('本地操作已保存')).toBeVisible();
      expect(fetchMock.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(1);
    },
  );

  it('treats an explicit unsupported adoption as a known rejection and keeps an editable draft', async () => {
    fetchMock.mockResolvedValue(
      json({ code: 'unsupported_capability', error: '当前初始章程不允许采用本地治理' }, 409),
    );
    mount(preparedAU());
    await open('采用本地治理');
    fill('决定依据', '保留未被采用的配置');
    const request = await commit();
    expect(await screen.findByText(/当前初始章程不允许采用本地治理/)).toBeVisible();
    expect(screen.queryByText('结果尚未确认')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
    expect(screen.getByLabelText('决定依据')).toHaveValue('保留未被采用的配置');
    expect(sessionStorage.getItem('union-governance-requests') ?? '').not.toContain(request.id);
  });

  it('recognizes a rejected original receipt even when the server version is lower than its requested base', async () => {
    fetchMock.mockImplementation(async (_path, init) =>
      json({
        receipt: {
          ...receipt(JSON.parse(String(init?.body))),
          status: 'rejected',
          effect: 'none',
          version: 11,
          message: '请求基准版本高于当前状态',
        },
      }),
    );
    mount();
    await open('更新目标');
    fill('AU目标', '尚未采用的目标');
    fill('决定依据', '核对基准版本');
    await commit();
    expect(await screen.findByText('请求基准版本高于当前状态')).toBeVisible();
    expect(screen.queryByText('结果尚未确认')).not.toBeInTheDocument();
    expect(screen.getByLabelText('AU目标')).toHaveValue('尚未采用的目标');
  });

  it('preserves rejected input and requires a new preview after a server version rejection', async () => {
    fetchMock.mockImplementation(async (_path, init) =>
      json({
        receipt: {
          ...receipt(JSON.parse(String(init?.body))),
          status: 'rejected',
          message: '状态版本已变化，请重新读取',
        },
      }),
    );
    mount();
    await open('更新目标');
    fill('AU目标', '保留我的目标');
    fill('决定依据', '需要重新核对');
    await commit();
    expect(await screen.findByText('状态版本已变化，请重新读取')).toBeVisible();
    expect(screen.getByLabelText('AU目标')).toHaveValue('保留我的目标');
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
  });

  it('keeps an unknown original ID and only queries it without persisting or replaying its content', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('连接中断'));
    mount();
    await open('更新目标');
    fill('AU目标', '不写入浏览器存储的私有目标');
    fill('决定依据', '私有决定依据');
    const request = await commit();
    expect(await screen.findByText('结果尚未确认')).toBeVisible();
    expect(screen.getByLabelText('AU目标')).toHaveValue('不写入浏览器存储的私有目标');
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(sessionStorage.getItem('union-governance-requests')).toContain(request.id);
    expect(sessionStorage.getItem('union-governance-requests')).not.toContain('私有');
    fetchMock.mockResolvedValueOnce(json({ receipt: receipt(request) }));
    fireEvent.click(screen.getByRole('button', { name: '查询原请求回执' }));
    expect(await screen.findByText('本地操作已保存')).toBeVisible();
    expect(fetchMock.mock.calls[1][0]).toBe(
      `/api/v1/governance/receipts?organization_id=core-au&id=${request.id}`,
    );
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(1);
  });

  it('keeps query errors next to the original request and never offers a replay', async () => {
    fetchMock.mockRejectedValue(new TypeError('服务暂不可达'));
    mount();
    await open('更新目标');
    fill('AU目标', '等待查询的目标');
    fill('决定依据', '当前决定');
    const request = await commit();
    fireEvent.click(await screen.findByRole('button', { name: '查询原请求回执' }));
    expect(await screen.findByText(/原请求标识已保留/)).toBeVisible();
    expect(sessionStorage.getItem('union-governance-requests')).toContain(request.id);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(1);
  });

  it('does not create a second request for the same action after closing an unknown result', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('响应丢失'));
    mount();
    await open('更新目标');
    fill('AU目标', '结果未知的目标');
    fill('决定依据', '先前依据');
    const original = await commit();
    await screen.findByText('结果尚未确认');
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    await open('更新目标');
    fill('AU目标', '再次输入同一范围的目标');
    fill('决定依据', '再次填写');
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(await screen.findByText('结果尚未确认')).toBeVisible();
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByText(new RegExp(original.id))).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keeps an unknown action local and lets a different work proceed with its own request', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('响应丢失'));
    const read = governedAU();
    read.au.work['independent-work'] = {
      ...read.au.work['work-one'],
      id: 'independent-work',
      title: '另一项独立工作',
    };
    read.au.mandates['independent-mandate'] = {
      ...read.au.mandates['mandate-one'],
      id: 'independent-mandate',
      work_id: 'independent-work',
    };
    mount(read, 'tasks');
    await open('开始文字提交');
    const original = await commit();
    await screen.findByText('结果尚未确认');
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    await open('开始文字提交');
    fill('工作', 'independent-work');
    fireEvent.click(await preview());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const next = JSON.parse(String(fetchMock.mock.calls[1][1]?.body)) as GovernanceRequest;
    expect(next.id).not.toBe(original.id);
    expect(next.data.work_id).toBe('independent-work');
    expect(sessionStorage.getItem('union-governance-requests')).toContain(original.id);
  });

  it('recovers an original request after reload onto a new service instance with the same principal', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('响应丢失'));
    const { view } = mount();
    await open('更新目标');
    fill('AU目标', '重启后按原 ID 查询');
    fill('决定依据', '原依据');
    const request = await commit();
    await screen.findByText('结果尚未确认');
    view.unmount();
    const read = governedAU();
    read.access.service_instance = 'restarted-service';
    vi.mocked(api.session).mockResolvedValue({
      ...governanceSession,
      service_instance: 'restarted-service',
    });
    fetchMock.mockResolvedValueOnce(json({ receipt: receipt(request) }));
    mount(read);
    fireEvent.click(await screen.findByRole('button', { name: `查询原请求 ${request.id}` }));
    expect(await screen.findByText('本地操作已保存')).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(1);
  });

  it('refreshes evidence-only rejection while retaining the unadopted content and its original request', async () => {
    fetchMock.mockImplementation(async (_path, init) =>
      json({
        receipt: {
          ...receipt(JSON.parse(String(init?.body))),
          status: 'rejected',
          effect: 'evidence_only',
          message: '内容已保留但不采用',
        },
      }),
    );
    mount(undefined, 'tasks');
    await open('提交文字内容');
    fill('文字内容', '撤权后到达的内部记录');
    const before = vi.mocked(api.coreAU).mock.calls.length;
    const request = await commit();
    expect(await screen.findByText('内容已保留但不采用')).toBeVisible();
    expect(screen.getByLabelText('文字内容')).toHaveValue('撤权后到达的内部记录');
    expect(screen.getByText('迟到内容已保留为未采用记录；工作尚未因此完成。')).toBeVisible();
    await waitFor(() => expect(api.coreAU).toHaveBeenCalledTimes(before + 3));
    expect(sessionStorage.getItem('union-governance-requests')).toContain(request.id);
  });

  it('does not send when browser request-identity storage is unavailable', async () => {
    mount();
    await open('更新目标');
    fill('AU目标', '等待安全保存原请求');
    fill('决定依据', '原依据');
    const button = await preview();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    fireEvent.click(button);
    expect(await screen.findByText(/浏览器无法保留原请求标识/)).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByLabelText('AU目标')).toHaveValue('等待安全保存原请求');
  });

  it('stops before POST when the current AU version changed after preview', async () => {
    mount();
    await open('更新目标');
    fill('AU目标', '还未提交的目标');
    fill('决定依据', '原本的依据');
    const button = await preview();
    const updated = governedAU();
    updated.au.version += 1;
    vi.mocked(api.coreAU).mockResolvedValue(updated);
    fireEvent.click(button);
    expect(await screen.findByText(/状态已变化/)).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByLabelText('AU目标')).toHaveValue('还未提交的目标');
  });

  it.each(['principal_id', 'service_instance'] as const)(
    'stops a preflight when %s changes before the workspace poll',
    async (field) => {
      mount();
      await open('更新目标');
      fill('AU目标', '原身份的目标');
      fill('决定依据', '原主体依据');
      const button = await preview();
      vi.mocked(api.session).mockResolvedValue({
        ...governanceSession,
        [field]: 'another-identity',
      });
      fireEvent.click(button);
      expect(await screen.findByText(/身份或服务已变化/)).toBeVisible();
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it('does not send a command when the user cancels a pending identity preflight', async () => {
    mount();
    await open('更新目标');
    fill('AU目标', '已经取消的输入');
    fill('决定依据', '不再提交');
    const button = await preview();
    let finish!: (value: typeof governanceSession) => void;
    vi.mocked(api.session).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    fireEvent.click(button);
    await screen.findByText('正在核对身份…');
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    await act(async () => {
      finish(governanceSession);
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it.each(['id', 'kind', 'organization_id', 'actor_principal_id', 'base_version'] as const)(
    'rejects an unrelated receipt with a mismatched %s',
    async (field) => {
      fetchMock.mockImplementation(async (_path, init) =>
        json({
          receipt: {
            ...receipt(JSON.parse(String(init?.body))),
            [field]: field === 'base_version' ? 999 : 'unrelated',
            message: '别人的回执内容',
          },
        }),
      );
      mount();
      await open('更新目标');
      fill('AU目标', '原目标');
      fill('决定依据', '原依据');
      const request = await commit();
      expect(await screen.findByText(/回执与原请求不匹配/)).toBeVisible();
      expect(screen.queryByText('别人的回执内容')).not.toBeInTheDocument();
      expect(sessionStorage.getItem('union-governance-requests')).toContain(request.id);
    },
  );

  it.each(['principal_id', 'service_instance'] as const)(
    'does not apply a late POST response after the current %s changed',
    async (field) => {
      let finish!: (value: Response) => void;
      fetchMock.mockImplementation(
        () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      );
      mount();
      await open('更新目标');
      fill('AU目标', '原目标');
      fill('决定依据', '原依据');
      const request = await commit();
      vi.mocked(api.session).mockResolvedValue({
        ...governanceSession,
        [field]: field === 'principal_id' ? otherPrincipal : 'another-service',
      });
      await act(async () => {
        finish(json({ receipt: { ...receipt(request), message: '旧身份的迟到成功' } }));
      });
      expect(screen.queryByText('旧身份的迟到成功')).not.toBeInTheDocument();
      expect(sessionStorage.getItem('union-governance-requests')).toContain(request.id);
    },
  );

  it('lets the original issuer query its own receipt after losing current AU access', async () => {
    const { client } = mount();
    await open('更新目标');
    fill('AU目标', '本人原请求');
    fill('决定依据', '先前有效决定');
    const request = await commit();
    await screen.findByText('本地操作已保存');
    fireEvent.click(screen.getByRole('button', { name: '完成，返回工作台' }));
    vi.mocked(api.coreAU).mockRejectedValue(
      new ApiError('当前主体没有 AU 读取权限', 403, 'not_authorized'),
    );
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['workspace'] });
    });
    await waitFor(() =>
      expect(screen.queryByRole('region', { name: '本地治理' })).not.toBeInTheDocument(),
    );
    fetchMock.mockResolvedValueOnce(json({ receipt: receipt(request) }));
    fireEvent.click(screen.getByRole('button', { name: `查询原请求 ${request.id}` }));
    expect(await screen.findByText('本地操作已保存')).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(1);
  });
});
