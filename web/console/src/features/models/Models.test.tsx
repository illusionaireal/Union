import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  accepted,
  checkedRun,
  closeResult,
  confirm,
  fill,
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

describe('core model access user journey', () => {
  it('opens the core models route and navigation for a normal core governor', async () => {
    mount();
    expect(await screen.findByRole('button', { name: '添加模型连接' })).toBeEnabled();
    expect(screen.getByRole('link', { name: /模型与 API/ })).toHaveAttribute(
      'href',
      '/models?organization=core-au',
    );
    expect(screen.getByRole('heading', { level: 1, name: '模型与 API' })).toBeVisible();
    expect(screen.queryByText('当前为观察者会话')).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it('states each profile capability scope without generalizing one profile', async () => {
    mount();
    expect(
      await screen.findByRole('heading', { name: '各接入方式的能力范围' }),
    ).toBeVisible();
    expect(screen.getByText('OpenAI 兼容 API（自填密钥）')).toBeVisible();
    expect(screen.getByText('modeld 授权（本机模型服务）')).toBeVisible();
    expect(screen.getAllByText('真实已验证')).toHaveLength(3);
    expect(screen.getByText(/页面不承诺边生成边显示/)).toBeVisible();
    expect(screen.getAllByText('不支持').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('仅受控验证').length).toBeGreaterThanOrEqual(2);
    // 每条已验证声明各自带证据路径，不是把整页笼统标注一次。
    // 3 条真实验证 + 1 条受控验证各自带同一条证据路径；不支持的项不带证据。
    expect(
      screen.getAllByText(/evidence\/058-s02-model-tools\/README\.md/),
    ).toHaveLength(4);
  });

  it('saves without inference or adoption, clears the key and keeps only request identities', async () => {
    mount();
    await fillConnection();
    await confirm();
    await waitFor(() => expect(state.commands).toHaveLength(1));
    expect(state.commands[0]).toMatchObject({
      kind: 'save_connection',
      data: {
        expected_revision: 0,
        profile: 'openai_compatible',
        api_key: 'test-key-not-a-real-secret',
        model: 'text-model',
      },
    });
    expect(screen.getByLabelText('API Key')).toHaveValue('');
    expect(sessionStorage.getItem('union-model-requests')).not.toContain(
      'test-key-not-a-real-secret',
    );
    await closeResult();
    expect(await screen.findByRole('heading', { name: '我的文本模型' })).toBeVisible();
    expect(screen.getByText('尚未验证此版本')).toBeVisible();
    expect(
      state.commands.some((command) =>
        ['start_model_check', 'set_connection'].includes(command.kind),
      ),
    ).toBe(false);
  });

  it('grants bounded resources, reads a selected document twice and adopts independently', async () => {
    state.read.connections.push(savedConnection());
    mount();
    await open('授予有限调用');
    fill('调用总上限', '4');
    fill('授权依据', '核对当前模型的只读资料能力');
    fireEvent.click(screen.getByLabelText('接受供应商费用可能未知'));
    await confirm();
    await closeResult();
    await open('验证工具往返');
    const file = new File(['持续责任不会因会话结束而消失。'], '项目说明.txt', {
      type: 'text/plain',
    });
    fireEvent.change(screen.getByLabelText('选择文本资料'), { target: { files: [file] } });
    await waitFor(() =>
      expect(screen.getByLabelText('资料正文')).toHaveValue('持续责任不会因会话结束而消失。'),
    );
    await confirm();
    await closeResult();
    expect(state.commands[1]).toMatchObject({
      kind: 'start_model_check',
      data: {
        binding_id: null,
        document_name: '项目说明.txt',
        document_text: '持续责任不会因会话结束而消失。',
        connection_id: 'connection-one',
        expected_revision: 1,
      },
    });
    expect(
      await screen.findByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).toBeVisible();
    expect(screen.getByText('81 / 17')).toBeVisible();
    expect(screen.getByText('132 / 31')).toBeVisible();
    expect(screen.getAllByText('未知').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText('责任、授权与逐次依据'));
    // 逐次依据要显示绑定到这次检查的执行定义；不能用宽泛匹配，避免与能力范围里的证据路径混淆。
    expect(screen.getByText(/执行定义：core\.model_check · v1/)).toBeVisible();
    expect(sessionStorage.getItem('union-model-requests')).not.toContain('持续责任');
    await open('设为默认');
    await confirm();
    await closeResult();
    expect(state.commands[2]).toMatchObject({
      kind: 'set_connection',
      data: { connection_id: 'connection-one', enabled: true, make_default: true },
    });
    expect(screen.getByText('当前默认')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: '刷新模型记录' }));
    expect(
      await screen.findByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).toBeVisible();
  });

  it('can adopt an enabled untested connection without purchasing a check', async () => {
    state.read.connections.push(savedConnection());
    mount();
    await open('设为默认');
    await confirm();
    await closeResult();
    expect(state.commands.map((command) => command.kind)).toEqual(['set_connection']);
    expect(screen.getByText('尚未验证此版本')).toBeVisible();
  });

  it('requires a fresh API key when editing an endpoint and does not reuse an old check', async () => {
    const connection = savedConnection();
    connection.last_check = {
      check_id: 'old-check',
      revision: 0,
      profile: connection.profile,
      at: 1800000000,
    };
    state.read.connections.push(connection);
    mount();
    await open('编辑连接');
    expect(screen.getByLabelText('API Key')).toBeRequired();
    expect(screen.getByLabelText('API Key')).toHaveValue('');
    fill('API 根地址', 'https://another.example.test/v1');
    fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(state.commands).toHaveLength(0);
  });

  it('uses only an explicitly supplied modeld grant, without listing host accounts', async () => {
    mount();
    await open('添加模型连接');
    fill('接入方式', 'modeld_grant');
    fill('连接名称', '预授模型');
    fill('模型标识', 'granted-model');
    fill('AU 授权标识', 'grant-ours');
    fill('授权版本', '2');
    await confirm();
    await waitFor(() => expect(state.commands).toHaveLength(1));
    expect(state.commands[0].data).toMatchObject({
      profile: 'modeld_grant',
      grant_ref: 'grant-ours',
      grant_revision: 2,
    });
    expect(state.commands[0].data).not.toHaveProperty('api_key');
    expect(
      state.fetchMock.mock.calls.every(([url]) => String(url).startsWith('/api/v1/models')),
    ).toBe(true);
  });

  it.each([
    ['空白', 'invalid key'],
    ['非 ASCII 字符', '测试密钥'],
    ['超过 4096 字符', 'x'.repeat(4097)],
  ])('rejects a credential containing %s before preview or POST', async (_name, key) => {
    mount();
    await fillConnection();
    fill('API Key', key);
    fireEvent.submit(screen.getByLabelText('API Key').closest('form')!);
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('API Key')).toHaveAttribute('maxlength', '4096');
    expect(state.commands).toHaveLength(0);
  });

  it('keeps normal inputs after a persisted domain rejection and allows a new preview', async () => {
    state.state.onCommand = async (command) =>
      json({
        receipt: {
          ...accepted(command),
          status: 'rejected',
          effect: 'none',
          message: 'AU 版本已变化；请重新预览',
        },
      });
    mount();
    await fillConnection();
    await confirm();
    expect(await screen.findByText('AU 版本已变化；请重新预览')).toBeVisible();
    expect(screen.getByLabelText('连接名称')).toHaveValue('我的文本模型');
    expect(screen.getByLabelText('API Key')).toHaveValue('');
    expect(screen.getByRole('button', { name: '预览影响' })).toBeEnabled();
    expect(screen.queryByText('结果尚未确认')).not.toBeInTheDocument();
  });

  it('offers the governance next step when the charter lacks the read-only tool', async () => {
    state.read.connections.push(savedConnection());
    state.read.document_read_allowed = false;
    mount();
    expect(await screen.findByRole('link', { name: '前往治理页允许只读资料工具' })).toHaveAttribute(
      'href',
      '/settings?organization=core-au',
    );
    expect(screen.getByRole('button', { name: '验证工具往返' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '设为默认' })).toBeEnabled();
  });

  it('reads persisted schema 3 records without legacy fallback', async () => {
    Object.assign(state.core.au, { schema_version: 3 });
    state.read.connections.push(savedConnection());
    state.read.checks.push(checkedRun());
    mount();
    expect(
      await screen.findByText('资料描述了持续责任。校验码：controlled-challenge'),
    ).toBeVisible();
    expect(screen.queryByText('当前为观察者会话')).not.toBeInTheDocument();
  });

  it('lets the V1 governor explicitly enable read_document while preserving other tools', async () => {
    state.core.au.charter.allowed_tools = ['publish_artifact'];
    state.fetchMock.mockImplementation(async (_url, init) =>
      json({ receipt: accepted(JSON.parse(String(init?.body))) }),
    );
    mount('/settings?organization=core-au');
    await open('修订章程');
    fireEvent.click(screen.getByLabelText('允许只读所选验证资料'));
    fill('决定依据', '开放有限模型接入验证');
    await confirm();
    await waitFor(() => expect(state.fetchMock).toHaveBeenCalled());
    const command = JSON.parse(String(state.fetchMock.mock.calls[0][1]?.body));
    expect(command.data.charter.allowed_tools).toEqual(['publish_artifact', 'read_document']);
    expect(command.kind).toBe('amend_charter');
  });
});
