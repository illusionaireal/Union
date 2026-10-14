import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Session, Snapshot } from '../../api/types';
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
