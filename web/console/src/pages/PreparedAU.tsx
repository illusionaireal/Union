import { useWorkspace } from '../app/workspace';
import { Card, Json } from '../components/ui';
import { CommandButton } from '../features/commands/CommandProvider';
import { blocked } from '../features/commands/model';
import './PreparedAU.css';

export function CreateAUIntro() {
  const { session, connected } = useWorkspace();
  const reason = blocked('create_v1', connected, session);
  return <section className="au-intro" aria-label="创建AU">
    <span className="eyebrow">AI-UNION / AU</span>
    <h2>从一个明确的目标开始</h2>
    <p>保存 AU 的目标、初始章程与资源计划，并将初始治理主体绑定到你的核心账户。</p>
    <p>创建后可随时重开同一个 AU。业务自治和实际资源使用尚未启用。</p>
    <CommandButton kind="create_v1" primary>创建 AU</CommandButton>
    {reason && <p role="status" className="form-note">{reason}</p>}
    <div className="legacy-creation">
      <p>已有旧版试验继续使用原有记录。小说公司保留独立的兼容入口。</p>
      <CommandButton kind="create">旧版兼容试验（含小说）</CommandButton>
    </div>
  </section>;
}

export default function PreparedAU() {
  const { core } = useWorkspace();
  if (!core) return null;
  const { au } = core;
  const { text, ...rules } = au.charter;
  return <section aria-label="AU准备记录" className="prepared-au">
    <div className="mission-panel">
      <div className="mission-copy">
        <span className="quiet-pill">准备态 · 未激活</span>
        <h2>{au.name}</h2>
        <p className="au-text">{au.goal}</p>
      </div>
    </div>
    <Card title="业务自治尚未启用">
      <p>当前支持保存和读取准备记录。启用前还需完成可执行治理规则、资源授权与执行能力的验证。</p>
      <p>此次创建没有调用模型、安排成员工作或作出外部承诺。</p>
    </Card>
    <Card title="初始治理主体">
      <p>创建者与初始治理主体为同一个核心账户。显示名称仅用于识别，不授予权限。</p>
      <dl className="au-facts">
        <div><dt>显示名称</dt><dd>{au.board_name}</dd></div>
        <div><dt>创建者及治理主体标识</dt><dd>{au.governance_root.governor_principal_id}</dd></div>
      </dl>
      <p className="form-note">正常改密或恢复保留该身份。宿主重置账号后创建的新账号不能接管此 AU。</p>
    </Card>
    <Card title="已保存的初始章程">
      <p className="au-text">{text}</p>
      <details><summary>查看结构化章程内容</summary><Json value={rules} /></details>
      <p className="form-note">章程内容已保存，尚未启用为业务执行规则。</p>
    </Card>
    <Card title="资源计划">
      <dl className="au-facts">
        <div><dt>计划调用上限</dt><dd>{au.resources.max_calls} 次</dd></div>
        <div><dt>计划单次超时</dt><dd>{au.resources.timeout_seconds} 秒</dd></div>
      </dl>
      <p>仅为计划；尚未授予、预约或使用资源。</p>
    </Card>
    <CommandButton kind="create_v1">创建另一个 AU</CommandButton>
  </section>;
}
