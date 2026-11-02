import { ModelConnectionFields } from './ModelConnectionFields';
import { useState, type InputHTMLAttributes, type ReactNode } from 'react';
import type { Charter, CommandKind, Session, Snapshot } from '../../api/types';
import { defaultCharter, novelCharter } from './model';
import type { CommandOptions } from './CommandProvider';
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
function Select({
  name,
  label,
  children,
  value,
}: {
  name: string;
  label: string;
  children: ReactNode;
  value?: string;
}) {
  return (
    <label className="operation-field">
      {label}
      <select name={name} defaultValue={value}>
        {children}
      </select>
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
  options,
}: {
  kind: CommandKind;
  data?: Snapshot;
  session: Session;
  options?: CommandOptions;
}) {
  const [executor, setExecutor] = useState(
    data?.execution_config.api_connection_id && session.executors.includes('api')
      ? 'api'
      : session.executors[0] || 'fixture',
  );
  const [template, setTemplate] = useState('generic');
  const [newConnectionId] = useState(() => 'model-' + crypto.randomUUID().slice(0, 8));
  const connection = options?.connection;
  const [eventId] = useState(() => crypto.randomUUID());
  const [media,setMedia]=useState<Array<{name:string;mime:string;data:string}>>([]);
  const [mediaLoading,setMediaLoading]=useState(false);
  const [mediaError,setMediaError]=useState('');
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
        <label className="operation-field">
          创建类型
          <select
            name="company_template"
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          >
            <option value="generic">通用 AI 公司 · 按目标自主协作</option>
            <option value="novel">小说公司 · 三周期首版</option>
          </select>
        </label>
        <Field
          key={template + '-name'}
          name="name"
          label="公司名称"
          value={template === 'novel' ? '我的 AI 小说公司' : '我的 AI 公司'}
          maxLength={200}
        />
        <Area
          key={template + '-goal'}
          name="goal"
          label="公司目标"
          value={
            template === 'novel'
              ? '自主组织团队，创作同一本中文网络小说并连续交付三章；向模拟平台投稿，核算成本，依据反馈调整后续创作。'
              : ''
          }
        />
        {template === 'novel' && (
          <>
            <Field
              name="initial_budget_minor"
              label="启动模拟预算（分，10000 = ¥100）"
              type="number"
              min={1}
              max={10000000000}
              value={10000}
            />
            <div className="field-grid">
              <Field
                name="input_price_minor_per_million"
                label="输入单价（分 / 百万 token）"
                type="number"
                min={0}
                max={10000000000}
                value={100}
              />
              <Field
                name="output_price_minor_per_million"
                label="输出单价（分 / 百万 token）"
                type="number"
                min={0}
                max={10000000000}
                value={500}
              />
            </div>
            <p className="form-note">
              单价是可编辑示例，请按供应商填写。预算为经营试验阈值；真实 API
              账单另计，单次调用可能使估算余额越限。第二章固定低订阅，用于观察后续调整。
            </p>
          </>
        )}
        <Field
          name="board_name"
          label="章程采用人"
          value="本机发起人（本地测试采用）"
          maxLength={200}
        />
        <Rules key={template} charter={template === 'novel' ? novelCharter : defaultCharter} />
        <div className="field-grid">
          <Field
            name="max_calls"
            key={template}
            label="累计调用上限"
            value={template === 'novel' ? 32 : 8}
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
            value={Math.min(
              data.company ? 30 : 8,
              data.budget.max_calls - data.budget.calls_reserved,
            )}
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
    case 'api_cost_allocate':
      return <>
        <p className="form-note">仅记录已经发生的周期费用分摊，不付款、不调用模型。原始调用不改写，同一调用不能重复分摊。</p>
        <Field name="voucher_id" label="分摊凭证 ID" value={'cost-'+eventId} />
        <Select name="allocation_basis" label="费用口径"><option value="subscription">订阅费用</option><option value="owned">自有资源费用</option></Select>
        <Field name="currency" label="币种" value="USD" pattern="[A-Z]{3}" />
        <Field name="period" label="账期" placeholder="2026-11" />
        <Field name="amount_minor" label="周期总金额（最小货币单位）" type="number" min={0} step={1} />
        <Area name="allocation_runs" label="需要分摊的调用 ID（逗号分隔）" />
        <Reason />
      </>;
    case 'api_import':
      return <>
        <p className="form-note">导入仅保存连接配置，不测试、不启动。文件不应包含密钥或宿主凭据引用。</p>
        <label className="operation-field">配置文件<input type="file" accept=".json,application/json" onChange={e=>{const form=e.currentTarget.form; const file=e.target.files?.[0]; if(file&&form) void file.text().then(value=>{const input=form.elements.namedItem('bundle') as HTMLTextAreaElement; input.value=value;});}} /></label>
        <Area name="bundle" label="待导入配置预览" rows={8} />
        <Select name="import_mode" label="重名处理" value="reject"><option value="reject">拒绝覆盖，保留现有配置</option><option value="rename">自动重命名导入</option><option value="replace">替换同名配置，并清除其密钥</option></Select>
        <Field name="reason" label="导入说明" value="从配置文件导入连接" />
      </>;
    case 'api_connection':
      return <>
        <input type="hidden" name="gateway_id" value={options?.gateway?.id || connection?.gateway_ref?.id || ''} />
        <input type="hidden" name="gateway_revision" value={options?.gateway?.revision || connection?.gateway_ref?.revision || ''} />
        {connection?.gateway_ref && <label className="check-row"><input type="checkbox" name="detach_gateway" />改为独立 API 连接</label>}
        <ModelConnectionFields connection={connection} newId={newConnectionId} endpoint={options?.gateway?.config.api_base_url} hasDefault={!!data?.execution_config.api_connection_id} />
      </>;
    case 'api_binding':
      return (
        <>
          <Select name="binding_role" label="岗位或执行职责（留空为默认）" value="">
            <option value="">组织默认</option>
            {Object.entries(data.organization.positions).map(([id,p])=><option key={id} value={id}>{p.title} · {id}</option>)}
            <option value="planner">组织决策（兼容配置）</option><option value="worker">普通工作（兼容配置）</option><option value="reviewer">评审（兼容配置）</option>
          </Select>
          <label className="check-field"><input type="checkbox" name="configure_fallbacks" />同时配置备用连接顺序</label>
          <Field name="fallbacks" label="备用连接 ID（逗号分隔，最多3个）" required={false} />
          <Field
            name="connection_id"
            label="连接 ID（留空解绑）"
            required={false}
            value={options?.connectionId ?? data.execution_config.api_connection_id ?? ''}
          />
          <Reason />
        </>
      );
    case 'company_usage':
      return (
        <>
          <p className="form-note">
            依据供应商回执补录缺失用量，原调用记录保留。确实未计费时填 0
            并说明证据；不得把未知费用当作零。未知执行须先核对结果。
          </p>
          <Select name="run_id" label="缺失用量的调用">
            {data.company?.ledger
              .filter((r) => r.kind === 'model' && r.amount_minor === null)
              .map((r) => (
                <option key={r.id} value={r.reference}>
                  {r.reference}
                </option>
              ))}
          </Select>
          <Field
            name="input_tokens"
            label="核对输入 token"
            type="number"
            min={0}
            max={1000000000}
          />
          <Field
            name="output_tokens"
            label="核对输出 token"
            type="number"
            min={0}
            max={1000000000}
          />
          <Reason />
        </>
      );
    case 'api_test':
      return (
        <>
          <input type="hidden" name="test_connection_id" value={connection?.id || ''} />
          <p>
            测试连接 {connection?.id || data.execution_config.api_connection_id}
            ，验证调用工具及读取结果继续回应，占用两次调用额度，分别保存用量和回执。
            {connection
              ? ` 最大输出 ${connection.config.max_output_tokens.toLocaleString()} token；实际超时 ${Math.min(connection.config.timeout_seconds, data.organization.resources.timeout_seconds)} 秒，取连接与公司单次超时中的较小值。`
              : ' 沿用当前连接配置的最大输出；超时同时受公司单次上限约束。'}
          </p>
          <label className="check-field">
            <input name="allow_unknown_cost" type="checkbox" />
            接受两次真实模型调用，验证工具往返，费用未知。
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
          <label className="operation-field">添加图片或 PDF 资料<input type="file" multiple accept="image/png,image/jpeg,image/webp,image/gif,application/pdf" onChange={async e=>{
            const files=Array.from(e.target.files||[]);setMediaLoading(true);setMediaError('');setMedia([]);
            try {
              if(files.length>4||files.reduce((sum,f)=>sum+f.size,0)>49152)throw new Error('最多4份资料，总大小不超过48KiB');
              const items=await Promise.all(files.map(async file=>{const bytes=new Uint8Array(await file.arrayBuffer());return {name:file.name,mime:file.type,data:btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''))};}));
              setMedia(items);
            }catch(error){setMediaError(error instanceof Error?error.message:'资料读取失败');}finally{setMediaLoading(false);}
          }} /></label>
          <input type="hidden" name="attachments_json" value={media.length?JSON.stringify(media):''} />
          <input type="hidden" name="media_loading" value={String(mediaLoading)} />
          <input type="hidden" name="media_error" value={mediaError} />
          {mediaError&&<p role="alert">{mediaError}</p>}
          <p className="form-note">资料以模型输入事件提交，仅进入已有授权的决策上下文。模型须明确支持该类型，否则拒绝调用。当前单次总大小上限48KiB。</p>
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
