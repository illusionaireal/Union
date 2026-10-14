import { useState, type InputHTMLAttributes, type ReactNode } from 'react';
import type { Charter, CommandKind, Session, Snapshot } from '../../api/types';
import { defaultCharter } from './model';
function Field({
  name,
  label,
  value = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  name: string;
  label: string;
  value?: string | number;
}) {
  return (
    <label className="operation-field">
      {label}
      <input name={name} defaultValue={value} required {...props} />
    </label>
  );
}
function Area({
  name,
  label,
  value = '',
  rows = 3,
}: {
  name: string;
  label: string;
  value?: string;
  rows?: number;
}) {
  return (
    <label className="operation-field">
      {label}
      <textarea name={name} defaultValue={value} rows={rows} required maxLength={100000} />
    </label>
  );
}
function Select({ name, label, children }: { name: string; label: string; children: ReactNode }) {
  return (
    <label className="operation-field">
      {label}
      <select name={name}>{children}</select>
    </label>
  );
}
function Reason() {
  return <Area name="reason" label="操作理由与核对依据" />;
}
function Rules({ charter }: { charter: Charter }) {
  const { text, ...rules } = charter;
  return (
    <>
      <Area name="charter_text" label="章程正文" value={text} />
      <details>
        <summary>受支持的规则字段</summary>
        <Area
          name="charter_rules"
          label="组织操作、工具、保留事项与修章入口"
          value={JSON.stringify(rules, null, 2)}
          rows={8}
        />
        <p className="form-note">只接受已实现的规则字段；正文不隐式授予权限。</p>
      </details>
    </>
  );
}
export function CommandFields({
  kind,
  data,
  session,
}: {
  kind: CommandKind;
  data?: Snapshot;
  session: Session;
}) {
  const [executor, setExecutor] = useState(session.executors[0] || 'fixture');
  const [eventId] = useState(() => crypto.randomUUID());
  const model = (label: string, hidden = false) => (
    <Field
      name="model"
      label={label}
      value={data?.execution_config.codex_model || ''}
      required={false}
      maxLength={128}
      autoComplete="off"
      spellCheck={false}
      placeholder="留空使用 CLI 默认"
      disabled={hidden}
    />
  );
  if (kind === 'create')
    return (
      <>
        <Field name="name" label="组织名称" value="我的试验组织" maxLength={200} />
        <Area name="goal" label="组织目标" />
        <Field
          name="board_name"
          label="章程采用人"
          value="本机发起人（本地测试采用）"
          maxLength={200}
        />
        <Rules charter={defaultCharter} />
        <div className="field-grid">
          <Field
            name="max_calls"
            label="累计调用上限"
            value={8}
            type="number"
            min={1}
            max={10000}
          />
          <Field
            name="timeout_seconds"
            label="单次超时（秒）"
            value={180}
            type="number"
            min={1}
            max={3600}
          />
        </div>
      </>
    );
  if (!data) return null;
  switch (kind) {
    case 'start':
      return (
        <>
          <p className="form-note">
            已占用 {data.budget.calls_reserved} / {data.budget.max_calls} 次；每次最多{' '}
            {data.organization.resources.timeout_seconds} 秒。
            {data.execution_state === 'unconfirmed' &&
              '持久执行活性未确认：启动入口先取得互斥锁并检查原执行；遗留执行将进入 unknown，不会重派。'}
          </p>
          <label className="operation-field">
            执行器
            <select
              name="executor"
              value={executor}
              onChange={(e) => setExecutor(e.target.value as typeof executor)}
            >
              {session.executors.map((e) => (
                <option
                  key={e}
                  value={e}
                  disabled={e === 'api' && !data.execution_config.api_connection_id}
                >
                  {e === 'fixture'
                    ? 'Fixture · 确定性模拟'
                    : e === 'api'
                      ? '模型 API · 默认连接，费用未知'
                      : 'Codex · 真实执行器，费用未知'}
                </option>
              ))}
            </select>
          </label>
          {executor === 'api' && (
            <p className="form-note">
              默认 API 连接：{data.execution_config.api_connection_id || '尚未绑定'}
              。模型使用该连接保存的配置。
            </p>
          )}
          <div hidden={executor !== 'codex'}>
            {model('本次模型（可覆盖组织默认值）', executor !== 'codex')}
          </div>
          <Field
            name="max_steps"
            label="本次最多执行步数"
            value={Math.min(8, data.budget.max_calls - data.budget.calls_reserved)}
            type="number"
            min={1}
            max={data.budget.max_calls - data.budget.calls_reserved}
          />
          <Field
            name="max_seconds"
            label="等待新事件窗口（秒，0 表示不持续等待）"
            value={0}
            type="number"
            min={0}
            max={86400}
          />
          <label className="check-field">
            <input type="checkbox" name="allow_unknown_cost" />
            明确接受本次有限真实调用的费用未知条件。Fixture 不调用模型。
          </label>
        </>
      );
    case 'model':
      return (
        <>
          {model('该组织的 Codex 默认模型')}
          <p className="form-note">
            填写执行器支持的模型 ID；留空恢复 CLI 默认。保存不调用模型，也不验证模型可用性。
          </p>
          <Reason />
        </>
      );
    case 'pause':
      return (
        <p className="form-note">
          提交后停止新的派发；在途调用仍需等待回执。暂停不代表远程执行已取消，未知结果需要核对。
        </p>
      );
    case 'event':
      return (
        <>
          <Select name="kind" label="事件类型">
            <option value="opinion">发起人意见</option>
            <option value="fact">事实记录</option>
            <option value="external_feedback">外部反馈</option>
          </Select>
          <Field name="event_id" label="来源事件或回执 ID" value={eventId} />
          <Area name="content" label="事件内容" />
          <Field name="source" label="可核验来源" />
          <Select name="simulated" label="来源标记">
            <option value="true">模拟资料</option>
            <option value="false">真实来源声明，仍需核验</option>
          </Select>
          <p className="form-note">意见与反馈进入事件循环，不直接覆盖正式工作。</p>
        </>
      );
    case 'resources':
      return (
        <>
          <p className="form-note">
            已有 {data.budget.calls_reserved} 次调用占用不会返还。当前上限 {data.budget.max_calls}{' '}
            次。
          </p>
          <Field
            name="max_calls"
            label="新的累计调用上限"
            value={data.budget.max_calls}
            type="number"
            min={Math.max(1, data.budget.calls_reserved)}
            max={10000}
          />
          <Field
            name="timeout_seconds"
            label="新的单次超时（秒）"
            value={data.organization.resources.timeout_seconds}
            type="number"
            min={1}
            max={3600}
          />
          <Reason />
        </>
      );
    case 'amend':
      return (
        <>
          <Rules charter={data.charter} />
          <Reason />
        </>
      );
    case 'reconcile':
      return (
        <>
          <Select name="run_id" label="待核对执行">
            {data.runs
              .filter((r) => r.status === 'unknown')
              .map((r) => (
                <option value={r.id} key={r.id}>
                  {r.id} · {r.work_id || (r.kind === 'connection_test' ? '连接测试' : '组织决定')}
                </option>
              ))}
          </Select>
          <Select name="resolution" label="核对结论">
            <option value="confirmed_not_executed">有依据确认未执行</option>
            <option value="abandon">放弃本次执行</option>
          </Select>
          <Reason />
          <p className="form-note">核对不退款，不自动重试，也不自动导入远程成果。</p>
        </>
      );
  }
}
