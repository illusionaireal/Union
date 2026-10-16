import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ModelConnection, Session, Snapshot } from '../../api/types';
import { CommandFields } from './fields';
import { readForm } from './model';
const session: Session = {
  role: 'board',
  organizations: [],
  service_instance: 'test',
  executors: ['fixture', 'codex'],
};
const data = {
  execution_config: { codex_model: 'saved-model' },
  budget: { max_calls: 8, calls_reserved: 2 },
  organization: { resources: { timeout_seconds: 180 } },
} as Snapshot;
function mount(kind: 'event' | 'model' | 'start') {
  const result = render(
    <form aria-label="操作表单">
      <CommandFields kind={kind} session={session} data={data} />
    </form>,
  );
  return { ...result, form: screen.getByRole('form') as HTMLFormElement };
}
describe('operation form interactions', () => {
  it('keeps edited content and focus across snapshot refreshes', () => {
    const { rerender, form } = mount('event');
    const content = screen.getByLabelText('事件内容');
    content.focus();
    fireEvent.change(content, { target: { value: '尚未提交的输入' } });
    rerender(
      <form aria-label="操作表单">
        <CommandFields kind="event" session={{ ...session }} data={{ ...data }} />
      </form>,
    );
    expect(content).toHaveValue('尚未提交的输入');
    expect(content).toHaveFocus();
    fireEvent.change(screen.getByLabelText('可核验来源'), { target: { value: 'unit-test' } });
    expect(readForm('event', form)).toMatchObject({
      content: '尚未提交的输入',
      source: 'unit-test',
      simulated: true,
    });
  });
  it('rejects whitespace required values and invalid model IDs, but allows clearing defaults', () => {
    const { form } = mount('model');
    fireEvent.change(screen.getByLabelText('操作理由与核对依据'), { target: { value: '   ' } });
    expect(() => readForm('model', form)).toThrow('空格');
    fireEvent.change(screen.getByLabelText('操作理由与核对依据'), {
      target: { value: '恢复默认' },
    });
    fireEvent.change(screen.getByLabelText('该组织的 Codex 默认模型'), {
      target: { value: '<invalid>' },
    });
    expect(() => readForm('model', form)).toThrow('模型 ID');
    fireEvent.change(screen.getByLabelText('该组织的 Codex 默认模型'), { target: { value: '' } });
    expect(readForm('model', form)).toEqual({ model: null, reason: '恢复默认' });
  });
  it('uses the configured model only for Codex and requires acceptance of unknown costs', () => {
    const { form } = mount('start');
    expect(readForm('start', form)).toMatchObject({
      executor: 'fixture',
      model: null,
      max_steps: 6,
    });
    fireEvent.change(screen.getByLabelText('执行器'), { target: { value: 'codex' } });
    expect(screen.getByLabelText('本次模型（可覆盖组织默认值）')).toHaveValue('saved-model');
    expect(() => readForm('start', form)).toThrow('费用未知');
    fireEvent.click(screen.getByRole('checkbox'));
    expect(readForm('start', form)).toMatchObject({
      executor: 'codex',
      model: 'saved-model',
      allow_unknown_cost: true,
    });
  });
  it('recognizes a bound API executor and requires its own cost acceptance', () => {
    const apiSession: Session = { ...session, executors: ['fixture', 'codex', 'api'] };
    const apiData = {
      ...data,
      execution_config: { codex_model: 'saved-model', api_connection_id: 'primary' },
    };
    const { rerender } = render(
      <form aria-label="操作表单">
        <CommandFields kind="start" session={apiSession} data={apiData} />
      </form>,
    );
    const form = screen.getByRole('form') as HTMLFormElement;
    expect(screen.getByRole('option', { name: '模型 API · 默认连接，费用未知' })).toBeEnabled();
    fireEvent.change(screen.getByLabelText('执行器'), { target: { value: 'api' } });
    expect(screen.getByText(/默认 API 连接：primary/)).toBeVisible();
    expect(screen.getByLabelText('本次模型（可覆盖组织默认值）')).toBeDisabled();
    expect(() => readForm('start', form)).toThrow('费用未知');
    fireEvent.click(screen.getByRole('checkbox'));
    expect(readForm('start', form)).toMatchObject({
      executor: 'api',
      model: null,
      allow_unknown_cost: true,
    });
    rerender(
      <form aria-label="操作表单">
        <CommandFields kind="start" session={apiSession} data={data} />
      </form>,
    );
    expect(screen.getByRole('option', { name: '模型 API · 默认连接，费用未知' })).toBeDisabled();
  });
});

describe('novel company setup', () => {
  it('adopts the novel charter with integer monetary configuration', () => {
    render(
      <form aria-label="操作表单">
        <CommandFields kind="create" session={session} />
      </form>,
    );
    fireEvent.change(screen.getByLabelText('创建类型'), { target: { value: 'novel' } });
    const value = readForm('create', screen.getByRole('form') as HTMLFormElement);
    expect(value).toMatchObject({
      company: {
        initial_budget_minor: 10000,
        input_price_minor_per_million: 100,
        output_price_minor_per_million: 500,
      },
      resources: { max_calls: 32 },
    });
    expect((value.charter as { allowed_operations: string[] }).allowed_operations).toContain(
      'submit_chapter',
    );
    expect((value.charter as { allowed_operations: string[] }).allowed_operations).toContain(
      'review_cycle',
    );
  });
  it('saves and binds API config, retaining a blank key instead of clearing it', async () => {
    const { publicPreview } = await import('./model');
    render(
      <form aria-label="操作表单">
        <CommandFields kind="api_connection" session={session} data={data} />
      </form>,
    );
    fireEvent.change(screen.getByLabelText('API 根地址'), {
      target: { value: 'https://example.test/v1' },
    });
    fireEvent.change(screen.getByLabelText('API 模型 ID'), { target: { value: 'model-a' } });
    const form = screen.getByRole('form') as HTMLFormElement;
    expect(readForm('api_connection', form)).not.toHaveProperty('api_key');
    fireEvent.change(screen.getByLabelText('API Key（留空保留原密钥）'), {
      target: { value: 'private-test-key' },
    });
    const request = readForm('api_connection', form);
    expect(request).toMatchObject({
      bind_default: true,
      api_key: 'private-test-key',
      config: { response_format: 'agent', token_limit_field: 'max_tokens' },
    });
    expect(screen.queryByLabelText('结构化输出模式')).not.toBeInTheDocument();
    expect(JSON.stringify(publicPreview(request))).not.toContain('private-test-key');
  });
});

describe('saved API connection editing', () => {
  const connection: ModelConnection = {
    id: 'existing',
    revision: 2,
    has_api_key: true,
    updated_at: '2026-10-16',
    config: {
      name: '已有连接',
      base_url: 'https://example.test/v1',
      model: 'existing-model',
      response_format: 'json_object',
      token_limit_field: 'max_tokens',
      max_output_tokens: 2048,
      timeout_seconds: 90,
      enabled: true,
    },
  };
  it('prefills the selected public configuration and retains its key without putting it in the form', () => {
    render(
      <form aria-label="操作表单">
        <CommandFields
          kind="api_connection"
          session={session}
          data={data}
          options={{ connection }}
        />
      </form>,
    );
    expect(screen.getByLabelText('连接 ID')).toHaveValue('existing');
    expect(screen.getByLabelText('连接 ID')).toHaveAttribute('readonly');
    expect(screen.getByLabelText('API Key（留空保留原密钥）')).toHaveValue('');
    const saved = readForm('api_connection', screen.getByRole('form') as HTMLFormElement);
    expect(saved.config).toEqual({ ...connection.config, response_format: 'agent' });
    expect(saved).not.toHaveProperty('api_key');
  });
  it('creates a distinct new connection even when a default is already bound', () => {
    render(
      <form aria-label="操作表单">
        <CommandFields
          kind="api_connection"
          session={session}
          data={{ ...data, execution_config: { codex_model: null, api_connection_id: 'existing' } }}
        />
      </form>,
    );
    expect(screen.getByLabelText('连接 ID')).not.toHaveValue('existing');
    expect(screen.getByLabelText('API 根地址')).toHaveValue('');
  });
});
