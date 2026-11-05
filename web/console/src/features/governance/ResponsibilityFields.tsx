import { useState, type ReactNode } from 'react';
import { isGovernedAU } from '../../api/core-boundary';
import { Area, Field } from '../commands/form-fields';
import { DecisionReason, PrincipalField } from './fields';
import type { GovernanceDraft } from './model';

function Choices({
  name,
  label,
  value,
  onChange,
  children,
}: {
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="operation-field">
      {label}
      <select name={name} required value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}
export function ResponsibilityFields({ draft }: { draft: GovernanceDraft }) {
  if (!isGovernedAU(draft.read)) return null;
  return <BoundResponsibilityFields draft={draft} />;
}
function BoundResponsibilityFields({ draft }: { draft: GovernanceDraft }) {
  if (!isGovernedAU(draft.read)) throw new Error('需要当前治理记录');
  const { au } = draft.read;
  const activeBindings = Object.values(au.bindings).filter((item) => item.active);
  const works = Object.values(au.work);
  const ownAttempts = Object.values(au.attempts).filter((attempt) =>
    draft.kind === 'accept_local_result'
      ? attempt.status === 'submitted'
      : attempt.principal_id === draft.scope.principalId && attempt.status === 'open',
  );
  const [bindingId, setBindingId] = useState(
    draft.defaults.binding_id ?? activeBindings[0]?.id ?? '',
  );
  const [workId, setWorkId] = useState(draft.defaults.work_id ?? works[0]?.id ?? '');
  const [attemptId, setAttemptId] = useState(draft.defaults.attempt_id ?? ownAttempts[0]?.id ?? '');
  const [fromBinding, setFromBinding] = useState(
    draft.defaults.from_binding_id ?? activeBindings[0]?.id ?? '',
  );
  const [toBinding, setToBinding] = useState(
    draft.defaults.to_binding_id ??
      activeBindings.find((item) => item.id !== fromBinding)?.id ??
      '',
  );
  const [selectedMandate, setSelectedMandate] = useState(
    draft.defaults.mandate_id ?? Object.values(au.mandates).find((item) => item.active)?.id ?? '',
  );
  const bindingLabel = (id: string) => {
    const binding = au.bindings[id];
    return binding
      ? `${au.members[binding.member_id]?.name ?? binding.member_id} · ${binding.duty}`
      : id;
  };
  const bindingOptions = activeBindings.length ? (
    activeBindings.map((item) => (
      <option key={item.id} value={item.id}>
        {bindingLabel(item.id)}
      </option>
    ))
  ) : (
    <option value="">请先登记责任成员</option>
  );
  const workChoices = (
    <Choices name="work_id" label="工作" value={workId} onChange={setWorkId}>
      {works.length ? (
        works.map((item) => (
          <option key={item.id} value={item.id}>
            {item.title}
          </option>
        ))
      ) : (
        <option value="">请先创建内部工作</option>
      )}
    </Choices>
  );
  const bindingChoices = (
    <Choices name="binding_id" label="责任成员" value={bindingId} onChange={setBindingId}>
      {bindingOptions}
    </Choices>
  );
  const work = au.work[workId];
  const attempt = au.attempts[attemptId];
  const mandateOptions = Object.values(au.mandates).filter((item) => item.active);
  const ownMandates = mandateOptions.filter(
    (item) =>
      item.work_id === workId &&
      au.members[au.bindings[item.binding_id]?.member_id]?.principal_id === draft.scope.principalId,
  );
  const hidden = (name: string, value: string) => <input type="hidden" name={name} value={value} />;
  switch (draft.kind) {
    case 'appoint':
      return (
        <>
          {hidden('member_id', draft.defaults.member_id)}
          {hidden('binding_id', draft.defaults.new_binding_id)}
          <Field name="name" label="成员姓名" maxLength={200} />
          <PrincipalField
            name="principal_id"
            label="成员核心身份标识"
            value={draft.scope.principalId}
          />
          <p className="form-note">默认是你本人；任命他人时，使用其已登记账号的稳定标识。</p>
          <Area name="duty" label="职责说明" />
        </>
      );
    case 'update_appointment':
      return (
        <>
          {bindingChoices}
          <Area key={bindingId} name="duty" label="职责说明" value={au.bindings[bindingId]?.duty} />
          <DecisionReason />
        </>
      );
    case 'create_work':
      return (
        <>
          {hidden('work_id', draft.defaults.new_work_id)}
          {bindingChoices}
          <Field name="title" label="工作标题" maxLength={200} />
          <Area name="instruction" label="工作说明" />
        </>
      );
    case 'update_work':
      return (
        <>
          {workChoices}
          <div key={workId}>
            <Field name="title" label="工作标题" value={work?.title} maxLength={200} />
            <Area name="instruction" label="工作说明" value={work?.instruction} />
            <label className="operation-field">
              工作状态
              <select name="status" defaultValue={work?.status === 'stopped' ? 'stopped' : 'open'}>
                <option value="open">开放</option>
                <option value="stopped">停止</option>
              </select>
            </label>
          </div>
          <DecisionReason />
        </>
      );
    case 'grant_mandate':
      return (
        <>
          {hidden('mandate_id', draft.defaults.new_mandate_id)}
          {workChoices}
          {bindingChoices}
          <label className="operation-field">
            授权来源
            <select
              name="parent_id"
              key={workId}
              defaultValue={
                draft.defaults.parent_id ??
                (draft.read.access.role === 'governor'
                  ? ''
                  : (ownMandates.find((item) => item.can_delegate)?.id ?? ''))
              }
            >
              {draft.read.access.role === 'governor' && (
                <option value="">当前治理者直接授权</option>
              )}
              {ownMandates
                .filter((item) => item.can_delegate)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {bindingLabel(item.binding_id)} · 授权 {item.id}
                  </option>
                ))}
            </select>
          </label>
          <p>行动范围：内部文字记录（record_memory）。</p>
          <label className="check-field">
            <input name="can_delegate" type="checkbox" />
            允许继续有限再委托
          </label>
        </>
      );
    case 'revoke_mandate':
      return (
        <>
          <Choices
            name="mandate_id"
            label="授权"
            value={selectedMandate}
            onChange={setSelectedMandate}
          >
            {mandateOptions.length ? (
              mandateOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {au.work[item.work_id]?.title} · {bindingLabel(item.binding_id)} · {item.id}
                </option>
              ))
            ) : (
              <option value="">暂无有效授权记录</option>
            )}
          </Choices>
          <DecisionReason />
        </>
      );
    case 'handoff_responsibility':
      return (
        <>
          <Choices
            name="from_binding_id"
            label="原责任成员"
            value={fromBinding}
            onChange={setFromBinding}
          >
            {bindingOptions}
          </Choices>
          <Choices
            name="to_binding_id"
            label="接收责任成员"
            value={toBinding}
            onChange={setToBinding}
          >
            {bindingOptions}
          </Choices>
          <p>
            将沿原标识交接：
            {works
              .filter(
                (item) =>
                  item.responsible_binding_id === fromBinding && item.status !== 'delivered',
              )
              .map((item) => item.title)
              .join('、') || '暂无未完成工作'}
            。
          </p>
          <DecisionReason />
        </>
      );
    case 'begin_local_action':
      return (
        <>
          {hidden('attempt_id', draft.defaults.new_attempt_id)}
          {workChoices}
          <label className="operation-field">
            本次授权
            <select
              name="mandate_id"
              key={workId}
              defaultValue={draft.defaults.mandate_id ?? ownMandates[0]?.id ?? ''}
              required
            >
              {ownMandates.length ? (
                ownMandates.map((item) => (
                  <option key={item.id} value={item.id}>
                    {bindingLabel(item.binding_id)} · {item.id}
                  </option>
                ))
              ) : (
                <option value="">请先为你的当前责任授予授权</option>
              )}
            </select>
          </label>
        </>
      );
    case 'submit_local_result':
    case 'accept_local_result':
      return (
        <>
          <Choices name="attempt_id" label="提交记录" value={attemptId} onChange={setAttemptId}>
            {ownAttempts.length ? (
              ownAttempts.map((item) => (
                <option key={item.id} value={item.id}>
                  {au.work[item.work_id]?.title} · {au.members[item.member_id]?.name} · {item.id}
                </option>
              ))
            ) : (
              <option value="">暂无可选提交记录</option>
            )}
          </Choices>
          {draft.kind === 'submit_local_result' ? (
            <Area name="content" label="文字内容" rows={7} />
          ) : (
            <>
              <p>待采用内容</p>
              <blockquote className="au-text">
                {attempt?.content ?? '请选择已提交的内容'}
              </blockquote>
              <p className="form-note">
                原章程 v{attempt?.charter_version} · 政策 v{attempt?.policy_version} · 工作 v
                {attempt?.work_version} · 职责 v{attempt?.binding_version}。服务端在采用时再次核对。
              </p>
              <DecisionReason />
            </>
          )}
        </>
      );
    default:
      return null;
  }
}
