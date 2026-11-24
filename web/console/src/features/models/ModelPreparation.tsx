import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { isGovernedAU } from '../../api/core-boundary';
import { organizationPath } from '../../app/organization-routes';
import { GovernanceButton } from '../governance/GovernanceProvider';
import { hasBlockingModelCheck, remainingCalls } from './model';
import { pendingForTarget } from './requests';
import type { OpenModelCommand } from './ModelRecords';
import type { ModelsController } from './useModels';

/** A scoped view of existing facts and commands, never an execution scheduler. */
export function ModelPreparation({ controller, open }: { controller: ModelsController; open: OpenModelCommand }) {
  const { read, workspace, scope } = controller;
  // undefined allows an initial default/sole connection; an explicit choice,
  // including clearing it, is never replaced by a background refresh.
  const [selected, setSelected] = useState<string>();
  useEffect(() => {
    if (selected !== undefined || !read) return;
    const initial = read.connections.find(c => c.is_default) ??
      (read.connections.length === 1 ? read.connections[0] : undefined);
    if (initial) setSelected(initial.id);
  }, [read, selected]);
  if (!read || !workspace.core) return null;
  const connection = read.connections.find(c => c.id === selected);
  const lostSelection = !!selected && !connection;
  const grant = read.resources.grant;
  const pending = !!connection && (pendingForTarget(controller.references, scope, connection.id) ||
    controller.references.some(ref => ref.organization_id === scope.organizationId &&
      ref.target === connection.id && read.operations.some(op => op.id === ref.id && ['saving', 'unknown'].includes(op.status))));
  const resourcePending = pendingForTarget(controller.references, scope, 'model-resources');
  const writable = controller.connected && controller.allowed('save_connection');
  const needsGrant = (!grant || !grant.allow_unknown_cost) && read.resources.plan_max_calls > 0;
  const needsTool = !read.document_read_allowed;
  const verified = !!connection && connection.last_check?.revision === connection.revision &&
    connection.last_check.profile === connection.profile;
  const canCheck = writable && !!connection?.enabled && !pending && !resourcePending &&
    read.document_read_allowed && !!grant?.allow_unknown_cost && remainingCalls(read) >= 2 &&
    !hasBlockingModelCheck(read, connection);
  const core = workspace.core;
  return <section className="model-preparation" aria-label="资源准备进度">
    <h2>继续准备这一个组织</h2>
    <p>逐步核对模型、只读工具与调用边界；每次保存、授权、采用或验证都由你分别决定。</p>
    {read.connections.length > 0 && <label className="operation-field">
      本次准备的模型连接
      <select value={selected ?? ''} onChange={event => setSelected(event.target.value)}>
        <option value="">请选择连接</option>
        {lostSelection && <option value={selected} disabled>原选择已不可用</option>}
        {read.connections.map(c => <option key={c.id} value={c.id}>{c.name}{c.is_default ? '（当前默认）' : ''}{!c.enabled ? '（已停用）' : ''}</option>)}
      </select>
    </label>}
    {lostSelection && <p role="status">原选择的连接已不可用；请明确选择另一连接。</p>}
    <ol className="model-preparation-facts">
      <li><strong>模型连接</strong><span>{connection ? `${connection.name} · ${connection.enabled ? '已保存' : '已停用'}` : '待明确选择或保存'}</span></li>
      <li><strong>只读验证工具</strong><span>{read.document_read_allowed ? '章程已允许所选验证文本' : '尚未允许所选验证文本'}</span></li>
      <li><strong>有限调用</strong><span>{grant ? `已授权 ${grant.max_calls} 次，已用或预约 ${read.resources.reserved_calls} 次，剩余 ${remainingCalls(read)} 次` : `计划 ${read.resources.plan_max_calls} 次，尚未授权`}</span></li>
      <li><strong>默认采用与验证</strong><span>{connection?.is_default
        ? verified ? '所选默认连接的当前版本已通过验证。' : '所选连接已采用为默认，当前版本尚未验证。'
        : verified ? '当前版本已验证，尚未采用为默认。' : '默认采用与验证分别决定，采用不要求先验证。'}</span></li>
    </ol>
    {!read.access.can_configure ? <div className="governance-boundary">
      <p>先核对当前治理与配置资格；登录、保存计划或显示名称不会授予模型使用权。</p>
      {isGovernedAU(core) && <ul>{core.readiness_gaps.map(gap => <li key={gap}>{gap}</li>)}</ul>}
      {!isGovernedAU(core) ? <GovernanceButton kind="adopt_governance" primary>核对初始治理规则</GovernanceButton>
        : <GovernanceButton kind="activate_governance" primary>启用已采用治理</GovernanceButton>}
      <Link className="button secondary" to={organizationPath(scope.organizationId, 'governance')}>查看当前治理条件</Link>
    </div> : <div className="model-preparation-actions">
      {!read.connections.length ? <button className="button primary" disabled={!writable} onClick={() => open('save_connection')}>填写模型连接</button>
        : connection && !pending && !connection.enabled
          ? <button className="button primary" disabled={!writable} onClick={() => open('set_connection', { connection, enabled: true })}>启用所选连接</button>
        : connection && !pending && needsGrant
          ? <button className="button primary" disabled={!writable || !!resourcePending} onClick={() => open('grant_model_resources')}>设置有限调用</button>
          : connection && !pending && !read.document_read_allowed
            ? <GovernanceButton kind="amend_charter" primary defaults={{ resource_tool: 'read_document' }}>允许只读验证资料</GovernanceButton>
            : connection && !pending && !connection.is_default
              ? <button className="button primary" disabled={!writable || !connection.enabled} onClick={() => open('set_connection', { connection, enabled: true, makeDefault: true })}>采用所选默认连接</button>
              : null}
      {connection?.enabled && !connection.is_default && !pending && (needsGrant || needsTool) &&
        <button className="button secondary" disabled={!writable} onClick={() => open('set_connection', { connection, enabled: true, makeDefault: true })}>采用所选默认连接</button>}
      {pending && <p role="status">所选连接有未确认操作，请在原请求记录中核对；不会换连接或重新提交。</p>}
      {connection && <button className="button secondary" disabled={!canCheck} onClick={() => open('start_model_check', { connection })}>进行两次调用验证</button>}
    </div>}
    {read.resources.plan_max_calls < 2 && <p>创建计划不足两次调用，当前无法完成工具往返验证；计划不会自动增加。</p>}
    {!!grant && remainingCalls(read) < 2 && <p>未占用额度不足两次；已有记录保留，完整验证暂不可用。</p>}
    {!!grant && !grant.allow_unknown_cost && <p>当前未接受费用未知，验证暂不可用；调整调用授权需要你明确决定。</p>}
    {connection && !read.document_read_allowed && isGovernedAU(core) && !core.access.commands.includes('amend_charter') &&
      <p>当前规则未允许你修订工具许可，请由有权治理者处理；连接仍可管理。</p>}
    <p className="form-note">调用次数不是金额封顶；验证只读取明确选择的文本。业务资料授权与正式工作仍需另行准备，不代表自主业务已启用。</p>
    <Link className="button secondary" to={organizationPath(scope.organizationId)}>返回组织概况</Link>
  </section>;
}
