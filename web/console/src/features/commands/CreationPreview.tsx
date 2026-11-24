import type { Charter } from '../../api/types';
import './CreationPreview.css';

export function CreationPreview({ data }: { data: Record<string, unknown> }) {
  const charter = data.charter as Charter;
  const resources = data.resources as { max_calls: number; timeout_seconds: number };
  return <>
    <dl className="connection-facts creation-preview">
      <div><dt>AU名称</dt><dd>{String(data.name)}</dd></div>
      <div><dt>组织目标</dt><dd className="creation-preview-text">{String(data.goal)}</dd></div>
      <div><dt>初始治理绑定</dt><dd>由服务器绑定当前登录账户；显示名称不授予权限。</dd></div>
      <div><dt>治理主体显示名称</dt><dd>{String(data.board_name)}</dd></div>
      <div><dt>章程正文</dt><dd className="creation-preview-text">{charter.text}</dd></div>
      <div><dt>资源计划</dt><dd>计划调用上限 {resources.max_calls} 次，单次超时 {resources.timeout_seconds} 秒；保存不会授予资源或调用模型。</dd></div>
      <div><dt>准备状态</dt><dd>自主行动尚未启用；有效治理与资源就绪需要后续核验。</dd></div>
    </dl>
    <details>
      <summary>核对受支持的初始规则</summary>
      <p>这些规则仅保存为初始章程内容，尚未启用。</p>
      <dl className="connection-facts creation-preview">
        <div><dt>组织操作</dt><dd>{charter.allowed_operations.join('、') || '无'}</dd></div>
        <div><dt>工具</dt><dd>{charter.allowed_tools.join('、') || '无'}</dd></div>
        <div><dt>保留事项</dt><dd>{charter.reserved_matters.join('、') || '无'}</dd></div>
        <div><dt>章程修订入口</dt><dd>{charter.board_can_amend ? '允许受权主体提出修订' : '未开放'}</dd></div>
      </dl>
    </details>
  </>;
}
