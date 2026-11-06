import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, RefreshCw } from 'lucide-react';
import { errorText } from '../../api/client';
import { useWorkspace } from '../../app/workspace';
import { Card } from '../../components/ui';
import { Dialog } from '../../components/Dialog';
import { sameScope, type GovernanceScope } from '../governance/model';
import { useModels } from './useModels';
import { ModelCommandForm } from './ModelCommandForm';
import { ModelRecovery } from './ModelReceiptView';
import { ProfileScope } from './ProfileScope';
import {
  CheckRecords,
  ConnectionRecords,
  OperationRecords,
  type OpenModelCommand,
} from './ModelRecords';
import { draftTitle, remainingCalls } from './model';
import type { ModelDraft } from './types';
import './models.css';

export default function CoreModels() {
  const { session, orgId } = useWorkspace();
  const scope = {
    principalId: session?.principal_id ?? '',
    serviceInstance: session?.service_instance ?? '',
    organizationId: orgId,
  };
  return (
    <ModelWorkspace key={`${scope.principalId}:${scope.serviceInstance}:${orgId}`} scope={scope} />
  );
}
function ModelWorkspace({ scope }: { scope: GovernanceScope }) {
  const controller = useModels(scope);
  const { workspace, read } = controller;
  const [draft, setDraft] = useState<ModelDraft>();
  const draftAllowed = !!draft && controller.allowed(draft.kind, draft);
  useEffect(() => {
    if (draft && !draftAllowed) setDraft(undefined);
  }, [draft, draftAllowed]);
  const search = '?organization=' + encodeURIComponent(scope.organizationId);
  const open: OpenModelCommand = (kind, options = {}) => {
    if (!read || !workspace.core || !controller.connected || !controller.allowed(kind, options))
      return;
    setDraft({
      key: crypto.randomUUID(),
      kind,
      read: structuredClone(read),
      core: structuredClone(workspace.core),
      scope,
      ...structuredClone(options),
    });
  };
  return (
    <div className="governance-workspace core-models">
      <section className="model-intro">
        <div>
          <h2>接入模型，核对实际工具能力</h2>
          <p>
            保存连接、授予有限调用、选择资料验证，再独立决定是否采用默认。每一步都有原请求和结果记录。
          </p>
          <span className="security-note">密钥不回显 · 保存不推理 · 只读取所选文本</span>
        </div>
        {read?.access.can_configure && (
          <button
            type="button"
            className="button primary"
            disabled={!controller.connected}
            onClick={() => open('save_connection')}
          >
            <Plus size={16} />
            添加模型连接
          </button>
        )}
      </section>
      <ModelRecovery controller={controller} />
      <div className="model-refresh">
        <button
          type="button"
          className="button secondary"
          onClick={() => {
            void workspace.refresh();
            void controller.refresh();
          }}
        >
          <RefreshCw size={15} />
          刷新模型记录
        </button>
      </div>
      {!read ? (
        <Card title="模型记录暂不可用">
          <p role="status">
            {controller.loading && workspace.core
              ? '正在读取当前 AU 的模型连接…'
              : controller.denied
                ? '当前身份或读取权限已变化，旧模型内容已清除。可以查询自己的原请求。'
                : '选择有权限的 AU 并恢复连接后，可读取原模型配置。'}
          </p>
          {controller.error && <p role="alert">{errorText(controller.error)}</p>}
          <Link className="button secondary" to={{ pathname: '/overview', search }}>
            前往 AU 与治理
          </Link>
        </Card>
      ) : (
        <>
          {!controller.connected && (
            <p role="status" className="connection-warning">
              模型读取已断开，以下为最近记录；输入保留，恢复后才能提交。
              {controller.error ? errorText(controller.error) : ''}
            </p>
          )}
          {!read.access.can_configure && (
            <div className="governance-boundary">
              <p>当前治理或权限尚不能配置模型。请在治理页核对实际身份、有效期和缺失条件。</p>
              <Link className="button secondary" to={{ pathname: '/overview', search }}>
                前往 AU 与治理
              </Link>
            </div>
          )}
          {!read.document_read_allowed && (
            <div className="governance-boundary">
              <p>当前章程尚未允许只读所选验证资料；保存连接与采用默认无需调用模型。</p>
              <Link className="button secondary" to={{ pathname: '/settings', search }}>
                前往治理页允许只读资料工具
              </Link>
            </div>
          )}
          <ProfileScope read={read} />
          <Card
            title="有限调用授权"
            action={
              read.access.can_configure && (
                <button
                  type="button"
                  className="button secondary"
                  disabled={!controller.connected || read.resources.plan_max_calls < 1}
                  onClick={() => open('grant_model_resources')}
                >
                  {read.resources.grant ? '调整有限调用' : '授予有限调用'}
                </button>
              )
            }
          >
            <dl className="au-facts">
              <div>
                <dt>创建计划上限</dt>
                <dd>{read.resources.plan_max_calls} 次</dd>
              </div>
              <div>
                <dt>实际授权上限</dt>
                <dd>
                  {read.resources.grant ? `${read.resources.grant.max_calls} 次` : '尚未授权'}
                </dd>
              </div>
              <div>
                <dt>已用或预约</dt>
                <dd>{read.resources.reserved_calls} 次</dd>
              </div>
              <div>
                <dt>可用次数</dt>
                <dd>{remainingCalls(read)} 次</dd>
              </div>
            </dl>
            <p>完整工具往返预留两次推理；只授权次数与输出限制，供应商费用可能未知。</p>
            {read.resources.plan_max_calls === 0 && (
              <p>创建时的资源计划为零，当前不能授予模型调用；已保存连接仍可管理。</p>
            )}
            {!!read.resources.grant && !read.resources.grant.allow_unknown_cost && (
              <p>当前未接受费用未知；请调整授权后再验证。</p>
            )}
            {!!read.resources.grant && remainingCalls(read) < 2 && (
              <p>完整验证需要至少两次未被占用的调用额度。</p>
            )}
          </Card>
          <ConnectionRecords controller={controller} open={open} />
          <OperationRecords controller={controller} open={open} />
          <CheckRecords controller={controller} open={open} />
        </>
      )}
      {draft && draftAllowed && sameScope(draft.scope, workspace.session, workspace.orgId) && (
        <Dialog
          key={draft.key}
          id="model-command-dialog"
          closeId="close-model-command"
          title={draftTitle(draft)}
          onClose={() => setDraft(undefined)}
        >
          <ModelCommandForm
            draft={draft}
            controller={controller}
            close={() => setDraft(undefined)}
          />
        </Dialog>
      )}
    </div>
  );
}
