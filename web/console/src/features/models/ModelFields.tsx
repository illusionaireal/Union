import { useEffect, useRef, useState } from 'react';
import { isGovernedAU } from '../../api/core-boundary';
import { Area, Field } from '../commands/form-fields';
import type { ModelDraft, ModelProfile } from './types';

export function ModelFields({ draft, changed }: { draft: ModelDraft; changed: () => void }) {
  if (draft.kind === 'save_connection') return <ConnectionFields draft={draft} />;
  if (draft.kind === 'start_model_check') return <DocumentFields draft={draft} changed={changed} />;
  if (draft.kind === 'grant_model_resources')
    return (
      <>
        <p>授权仅用于模型接入验证。每次完整验证预留两次调用；保存授权本身不调用模型。</p>
        <p>
          创建计划最多 {draft.read.resources.plan_max_calls} 次，已用或预约{' '}
          {draft.read.resources.reserved_calls} 次。
        </p>
        <Field
          name="max_calls"
          label="调用总上限"
          type="number"
          min={Math.max(1, draft.read.resources.reserved_calls)}
          max={Math.min(10000, draft.read.resources.plan_max_calls)}
          step={1}
          value={
            draft.read.resources.grant?.max_calls ??
            Math.min(2, draft.read.resources.plan_max_calls)
          }
        />
        <label className="check-field">
          <input
            type="checkbox"
            name="allow_unknown_cost"
            defaultChecked={draft.read.resources.grant?.allow_unknown_cost ?? false}
          />
          接受供应商费用可能未知
        </label>
        <p className="form-note">
          次数与每次输出有上限；供应商未提供金额时保留未知，这不是金额封顶。未接受未知费用时不能发起验证。
        </p>
        <Area name="reason" label="授权依据" />
      </>
    );
  if (draft.kind === 'cancel_model_check')
    return (
      <>
        <p>停止后续步骤，并请求模型服务取消。已经发生或未确认的调用和费用仍保留。</p>
        <Area name="reason" label="停止依据" />
      </>
    );
  if (draft.kind === 'reconcile_model_check')
    return (
      <p>
        查询原验证 {draft.check!.id}
        。授权仍有效时可继续尚未派发的下一步；不会重新发送结果未知的调用。
      </p>
    );
  if (draft.kind === 'reconcile_connection')
    return <p>核对原保存操作 {draft.operation!.id}；只查询模型服务原注册结果，不再次提交密钥。</p>;
  return (
    <p>
      {draft.makeDefault
        ? '将此连接用于后续获准的模型工作。采用不发起测试；尚未验证的状态会保留。'
        : draft.enabled
          ? '启用此连接。原验证结论需按新的连接版本重新核对。'
          : '停用后不能发起新验证；原请求和费用保留供核对。'}
      当前连接：{draft.connection!.name}。
    </p>
  );
}
function ConnectionFields({ draft }: { draft: ModelDraft }) {
  const connection = draft.connection;
  const [profile, setProfile] = useState<ModelProfile>(
    connection?.profile ?? draft.read.capabilities.profiles[0] ?? 'openai_compatible',
  );
  return (
    <>
      <p>保存连接不调用模型，也不改变默认连接。密钥由模型服务私有保存，不会回显。</p>
      <Field name="name" label="连接名称" value={connection?.name} maxLength={100} />
      <label className="operation-field">
        接入方式
        <select
          name="profile"
          value={profile}
          onChange={(event) => setProfile(event.target.value as ModelProfile)}
        >
          {draft.read.capabilities.profiles.includes('openai_compatible') && (
            <option value="openai_compatible">兼容 OpenAI 的文本 API</option>
          )}
          {draft.read.capabilities.profiles.includes('modeld_grant') && (
            <option value="modeld_grant">已授予本 AU 的模型服务授权</option>
          )}
        </select>
      </label>
      {profile === 'openai_compatible' ? (
        <>
          <Field
            name="base_url"
            label="API 根地址"
            type="url"
            value={connection?.base_url}
            placeholder="https://api.example.com/v1"
            autoComplete="off"
          />
          <Field
            name="api_key"
            label="API Key"
            type="password"
            autoComplete="new-password"
            spellCheck={false}
            maxLength={4096}
            pattern="[!-~]+"
            title="1–4096 个可打印 ASCII 字符，不能含空白"
          />
          {connection && (
            <p className="form-note">编辑时请重新输入密钥；变更地址不会沿用旧密钥。</p>
          )}
        </>
      ) : (
        <>
          <p className="form-note">
            使用宿主已明确授予本 AU 的标识和当前版本。此处不会列出其他账号或替你扩大授权。
          </p>
          <Field name="grant_ref" label="AU 授权标识" value={connection?.grant_ref} />
          <Field
            name="grant_revision"
            label="授权版本"
            type="number"
            min={1}
            step={1}
            value={connection?.grant_revision ?? 1}
          />
        </>
      )}
      <Field
        name="model"
        label="模型标识"
        value={connection?.model}
        maxLength={256}
        autoComplete="off"
      />
      <details>
        <summary>输出限制</summary>
        <Field
          name="max_output_tokens"
          label="每次输出上限（token）"
          type="number"
          min={1}
          max={32768}
          step={1}
          value={connection?.max_output_tokens ?? 1024}
        />
        <p className="form-note">
          当前支持文本和所选资料的客户端只读工具；媒体与其他工具尚未启用。
        </p>
      </details>
    </>
  );
}
function DocumentFields({ draft, changed }: { draft: ModelDraft; changed: () => void }) {
  const [name, setName] = useState(''),
    [text, setText] = useState(''),
    [error, setError] = useState('');
  const reader = useRef<FileReader | null>(null);
  useEffect(() => () => reader.current?.abort(), []);
  const bindings = isGovernedAU(draft.core)
    ? Object.values(draft.core.au.bindings).filter(
        (binding) =>
          binding.active &&
          isGovernedAU(draft.core) &&
          draft.core.au.members[binding.member_id]?.principal_id === draft.scope.principalId,
      )
    : [];
  const selectFile = (file: File | undefined) => {
    if (!file) return;
    reader.current?.abort();
    setError('');
    if (
      file.size > 131072 ||
      !(file.type.startsWith('text/') || /\.(txt|md|csv|json)$/i.test(file.name))
    ) {
      setError('请选择一份文本资料，正文最多 32768 个字符；不支持图片或 PDF');
      return;
    }
    const task = new FileReader();
    reader.current = task;
    task.onload = () => {
      const content = String(task.result ?? '');
      if (!content.trim() || content.length > 32768 || content.includes('\0')) {
        setError('资料须为非空文本且不超过 32768 个字符；原输入已保留');
        return;
      }
      setName(file.name);
      setText(content);
      changed();
    };
    task.onerror = () => setError('未能读取所选文件；请重新选择或直接粘贴文本');
    task.readAsText(file, 'UTF-8');
  };
  return (
    <>
      <p>
        验证会向“{draft.connection!.name}
        ”发起两次推理，并把所选资料通过一次只读工具返回模型。请核对资料适合发送给该模型服务。
      </p>
      <label className="operation-field">
        负责此验证
        <select name="binding_id" defaultValue="">
          <option value="">由我负责这次验证（记录独立责任）</option>
          {bindings.map((binding) => (
            <option key={binding.id} value={binding.id}>
              {isGovernedAU(draft.core) ? draft.core.au.members[binding.member_id]?.name : ''} ·{' '}
              {binding.duty}
            </option>
          ))}
        </select>
      </label>
      <p className="form-note">
        系统保存责任成员、验证工作、有限授权和执行定义。验证结果供接入检查，不是正式业务成果。
      </p>
      <label className="operation-field">
        选择文本资料
        <input
          type="file"
          accept="text/*,.txt,.md,.csv,.json"
          onChange={(event) => selectFile(event.target.files?.[0])}
        />
      </label>
      {error && (
        <p role="alert" className="operation-error">
          {error}
        </p>
      )}
      <label className="operation-field">
        资料名称
        <input
          name="document_name"
          required
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <label className="operation-field">
        资料正文
        <textarea
          name="document_text"
          required
          maxLength={32768}
          rows={6}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      <p className="form-note">
        也可以直接填写文本。只读取本次明确提交的内容，不接受宿主文件路径。
      </p>
    </>
  );
}
