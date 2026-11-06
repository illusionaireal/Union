import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { expect, vi } from 'vitest';
import App from '../../app/App';
import { api } from '../../api/client';
import { governedAU, governanceSession, principal } from '../governance/test-fixtures';
import type { CoreConnection, ModelCheck, ModelRead } from './types';

type FixtureCheck = ModelCheck & {
  versions: { goal_version: number; charter_version: number; policy_version: number };
  grant_ref: string;
  grant_revision: number;
  purpose: 'connection_check';
  attempt_ids: string[];
};

export interface TestCommand {
  id: string;
  organization_id: string;
  base_version: number;
  kind: string;
  data: Record<string, unknown>;
}
export const json = (value: unknown, status = 200) =>
  ({ ok: status < 400, status, json: async () => value }) as Response;
export const savedConnection = (id = 'connection-one'): CoreConnection => ({
  id,
  revision: 1,
  name: id === 'connection-one' ? '我的文本模型' : '另一模型',
  profile: 'openai_compatible',
  model: 'text-model',
  base_url: 'https://models.example.test/v1',
  max_output_tokens: 1024,
  grant_ref: 'grant-one',
  grant_revision: 1,
  enabled: true,
  is_default: false,
  last_check: null,
});
export const checkedRun = (
  id = 'check-one',
  status: ModelCheck['status'] = 'succeeded',
): FixtureCheck => ({
  id,
  principal_id: principal,
  member_id: 'member-one',
  binding_id: 'binding-one',
  binding_version: 1,
  work_id: 'model-work-one',
  work_version: 1,
  mandate_id: 'model-mandate-one',
  mandate_version: 1,
  agent_definition: { id: 'core.model_check', version: 1, tools: ['read_document'] },
  versions: { goal_version: 1, charter_version: 1, policy_version: 1 },
  connection_id: 'connection-one',
  connection_revision: 1,
  resource_revision: 1,
  grant_ref: 'grant-one',
  grant_revision: 1,
  purpose: 'connection_check',
  status,
  stage: status === 'succeeded' ? 2 : 0,
  stop_requested: false,
  document_name: '项目说明.txt',
  output: status === 'succeeded' ? '资料描述了持续责任。校验码：controlled-challenge' : null,
  message: status === 'succeeded' ? '模型已读取工具结果并完成回应' : '原调用结果待核对',
  waiting:
    status === 'succeeded'
      ? null
      : {
          object: id,
          condition: '原模型请求有完整结果',
          responsible_member_id: 'member-one',
          scope: 'execution',
        },
  attempts: [
    {
      id: 'attempt-one',
      stage: 0,
      state: 'completed',
      purpose: 'connection_check',
      usage: {
        input_tokens: 81,
        output_tokens: 17,
        cached_input_tokens: null,
        cache_write_tokens: null,
        reasoning_tokens: null,
        cost_minor: null,
        currency: null,
        cost_status: 'unknown',
      },
    },
    {
      id: 'attempt-two',
      stage: 1,
      state: status === 'succeeded' ? 'completed' : 'unknown',
      purpose: 'connection_check',
      usage: {
        input_tokens: 132,
        output_tokens: 31,
        cached_input_tokens: null,
        cache_write_tokens: null,
        reasoning_tokens: null,
        cost_minor: null,
        currency: null,
        cost_status: 'unknown',
      },
    },
  ],
  attempt_ids: ['attempt-one', 'attempt-two'],
});
export function fixture() {
  const core = governedAU();
  core.au.resources.max_calls = 10;
  const session = structuredClone(governanceSession);
  const read: ModelRead = {
    protocol: 'core.models.v1',
    organization_id: 'core-au',
    version: core.au.version,
    access: {
      principal_id: principal,
      service_instance: session.service_instance,
      can_configure: true,
    },
    governance_status: 'active',
    document_read_allowed: true,
    capabilities: {
      profiles: ['openai_compatible', 'modeld_grant'],
      tools: ['read_document'],
      profile_scope: {
        openai_compatible: {
          title: 'OpenAI 兼容 API（自填密钥）',
          auth: 'api_key',
          capabilities: {
            text_answer: {
              status: 'verified_real',
              note: 'U-072 已用所选连接完成两次真实推理，回答已保存。',
              evidence: 'evidence/058-s02-model-tools/README.md',
            },
            tool_roundtrip: {
              status: 'verified_real',
              note: '真实读取所选文本，经 read_document 回执继续回答。',
              evidence: 'evidence/058-s02-model-tools/README.md',
            },
            usage_reporting: {
              status: 'verified_real',
              note: '真实响应记录输入/输出 token；供应商未返回金额时保留未知。',
              evidence: 'evidence/058-s02-model-tools/README.md',
            },
            streaming: {
              status: 'unsupported',
              note: '连接检查要求完整应答，页面不承诺边生成边显示。',
            },
            long_job_new_input: {
              status: 'unsupported',
              note: '长任务执行期间追加输入尚未实现；刷新后用原请求查询。',
            },
            cancel_and_query: {
              status: 'controlled',
              note: '取消意图、原请求查询和 unknown 保留已受控验证，未做真实中断恢复。',
              evidence: 'evidence/058-s02-model-tools/README.md',
            },
          },
        },
        modeld_grant: {
          title: 'modeld 授权（本机模型服务）',
          auth: 'grant',
          capabilities: {
            text_answer: {
              status: 'controlled',
              note: '以显式模型替身验证文本回答；未用真实账号验收此 profile。',
              evidence: 'tests/test_core_model_checks.py',
            },
            tool_roundtrip: {
              status: 'controlled',
              note: '两阶段工具往返、回执配对和迟到结果隔离已受控验证。',
              evidence: 'tests/test_core_model_checks.py',
            },
            usage_reporting: {
              status: 'controlled',
              note: '事件与结果用量合并、金额未知保留已受控验证。',
              evidence: 'tests/test_core_model_checks.py',
            },
            streaming: {
              status: 'unsupported',
              note: '连接检查要求完整应答，此 profile 未验证流式输出。',
            },
            long_job_new_input: {
              status: 'unsupported',
              note: '此 profile 未验证长任务执行期间接收新输入。',
            },
            cancel_and_query: {
              status: 'controlled',
              note: '取消、原请求查询与 unknown 保留已受控验证。',
              evidence: 'tests/test_core_model_recovery.py',
            },
          },
        },
      },
      autonomous_business: false,
    },
    connections: [],
    operations: [],
    checks: [],
    resources: {
      grant: null,
      reserved_calls: 0,
      plan_max_calls: 10,
    },
  };
  const commands: TestCommand[] = [];
  const receipts = new Map<string, unknown>();
  const state = {
    core,
    session,
    read,
    commands,
    receipts,
    onCommand: undefined as undefined | ((command: TestCommand) => Promise<Response>),
    onRead: undefined as undefined | (() => Promise<Response>),
  };
  vi.spyOn(api, 'session').mockImplementation(async () => structuredClone(state.session));
  vi.spyOn(api, 'authStatus').mockResolvedValue({
    configured: true,
    authenticated: true,
    can_setup: false,
    account: 'participant',
  });
  vi.spyOn(api, 'coreAU').mockImplementation(async () => structuredClone(state.core));
  const fetchMock = vi.fn<typeof fetch>(async (path, init) => {
    const url = String(path);
    if (url.startsWith('/api/v1/models?'))
      return state.onRead ? state.onRead() : json(structuredClone(state.read));
    if (url.startsWith('/api/v1/models/receipts?')) {
      const id = new URL(url, 'http://localhost').searchParams.get('id')!;
      return receipts.has(id)
        ? json({ receipt: receipts.get(id) })
        : json({ error: '原回执尚未可读' }, 404);
    }
    if (url === '/api/v1/models/commands') {
      const command = JSON.parse(String(init?.body)) as TestCommand;
      commands.push(command);
      if (state.onCommand) return state.onCommand(command);
      const receipt = accepted(command);
      receipts.set(command.id, receipt);
      read.version += 1;
      core.au.version = read.version;
      if (command.kind === 'save_connection') {
        const connection = savedConnection(String(command.data.connection_id));
        const publicData = { ...command.data };
        delete publicData.api_key;
        Object.assign(connection, publicData, {
          id: command.data.connection_id,
          revision: Number(command.data.expected_revision) + 1,
        });
        read.connections = [
          ...read.connections.filter((item) => item.id !== connection.id),
          connection,
        ];
        read.operations.push({
          id: command.id,
          status: 'succeeded',
          message: '连接已保存；尚未调用模型',
        });
        Object.assign(receipt, { operation_id: command.id });
      }
      if (command.kind === 'grant_model_resources')
        read.resources.grant = { ...command.data, revision: 1 } as typeof read.resources.grant;
      if (command.kind === 'start_model_check') {
        const check = checkedRun(command.id);
        check.connection_id = String(command.data.connection_id);
        read.checks.push(check);
        read.resources.reserved_calls += 2;
        const connection = read.connections.find((item) => item.id === check.connection_id)!;
        connection.last_check = {
          check_id: check.id,
          revision: connection.revision,
          profile: connection.profile,
          at: 1800000000,
        };
        Object.assign(receipt, { check_id: command.id });
      }
      if (command.kind === 'set_connection') {
        read.connections.forEach((item) => {
          if (command.data.make_default) item.is_default = item.id === command.data.connection_id;
          if (item.id === command.data.connection_id) item.enabled = Boolean(command.data.enabled);
        });
      }
      return json({ receipt });
    }
    throw new Error('Unexpected fetch ' + url);
  });
  vi.stubGlobal('fetch', fetchMock);
  return { ...state, fetchMock, state };
}
export function accepted(command: TestCommand) {
  return {
    id: command.id,
    organization_id: command.organization_id,
    kind: command.kind,
    base_version: command.base_version,
    version: command.base_version + 1,
    actor_principal_id: principal,
    created_at: '2026-11-06T00:00:00Z',
    status: 'succeeded',
    effect: 'applied',
    message: '模型操作已受理；结果另行显示',
  };
}
export function mount(path = '/models?organization=core-au') {
  window.history.replaceState(null, '', path);
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
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
export async function open(label: string) {
  fireEvent.click(await screen.findByRole('button', { name: label }));
  return screen.findByRole('dialog');
}
export function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}
export async function confirm() {
  fireEvent.click(screen.getByRole('button', { name: '预览影响' }));
  fireEvent.click(await screen.findByRole('button', { name: '确认提交' }));
}
export async function closeResult() {
  fireEvent.click(await screen.findByRole('button', { name: '返回模型配置' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
}
export async function fillConnection() {
  await open('添加模型连接');
  fill('连接名称', '我的文本模型');
  fill('API 根地址', 'https://models.example.test/v1');
  fill('API Key', 'test-key-not-a-real-secret');
  fill('模型标识', 'text-model');
}
