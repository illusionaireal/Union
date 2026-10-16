import { Link, useLocation } from 'react-router-dom';
import { Cpu, ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../app/workspace';
import { Badge, Card, Empty, Json } from '../components/ui';
import { CommandButton } from '../features/commands/CommandProvider';
import { titles } from '../features/commands/model';
import { DetailLink } from '../features/details/Details';
export default function Settings() {
  const { data, session } = useWorkspace();
  const { search } = useLocation();
  const d = data!;
  return (
    <>
      <section className="settings-identity">
        <div className="identity-mark">{d.organization.name.slice(0, 1)}</div>
        <div>
          <span className="eyebrow">公司档案</span>
          <h2>{d.organization.name}</h2>
          <p>{d.organization.goal}</p>
        </div>
        <span className="quiet-pill">章程 v{d.organization.charter_version}</span>
      </section>
      <div className="next-action-banner">
        <div>
          <strong>模型与 API 已有独立管理入口</strong>
          <p>
            默认连接：{d.execution_config.api_connection_id || '尚未配置'}
            。在模型页面添加、编辑或测试连接。
          </p>
        </div>
        <Link className="button primary" to={{ pathname: '/models', search }}>
          管理模型与 API
        </Link>
      </div>
      <Card title="模型设置" action={<Cpu size={20} className="muted" />}>
        <div className="setting-row">
          <div>
            <p>Codex 默认模型</p>
            <strong id="configured-model" className="model-name">
              {d.execution_config.codex_model || 'CLI 默认（未指定）'}
            </strong>
          </div>
          <CommandButton kind="model" />
        </div>
        <p className="form-note">
          {session?.executors.includes('codex')
            ? '真实执行器已由宿主启用；启动时可覆盖本次模型。'
            : '宿主尚未启用 Codex；可先保存其默认模型。'}{' '}
          保存不调用模型，也不验证模型可用性。
        </p>
        {session?.executors.includes('api') && (
          <p className="form-note">
            组织默认 API 连接：{d.execution_config.api_connection_id || '尚未绑定'}
            。完成连接配置与绑定后，可在运行表单选择模型 API。
          </p>
        )}
      </Card>
      <div className="cards-grid">
        <Card
          title={'已采用章程 · v' + d.organization.charter_version}
          action={<ShieldCheck size={20} className="muted" />}
        >
          <p className="charter-copy">{d.charter.text}</p>
          <p>
            文本成果工具：{d.charter.allowed_tools.includes('produce_artifact') ? '允许' : '未授权'}{' '}
            · 当前修章入口：{d.charter.board_can_amend ? '允许' : '不允许'}
          </p>
          <CommandButton kind="amend">预览修章</CommandButton>
          <details>
            <summary>受支持规则</summary>
            <Json value={d.charter} />
          </details>
        </Card>
        <Card title="资源与异常处理">
          <p>
            已占用 {d.budget.calls_reserved} / {d.budget.max_calls} 次调用
          </p>
          <p>单次 {d.organization.resources.timeout_seconds} 秒；金额费用未知。</p>
          <div className="detail-links">
            <CommandButton kind="resources" />
            <CommandButton kind="reconcile" />
            {!!d.company?.totals.unknown_model_costs && <CommandButton kind="company_usage" />}
          </div>
        </Card>
      </div>
      <Card title="操作回执">
        {d.receipts.length ? (
          d.receipts.map((r) => (
            <article key={r.id} className="command-receipt">
              <div className="receipt-heading">
                <DetailLink kind="receipt" id={r.id}>
                  {titles[r.kind] || r.kind}
                </DetailLink>
                <Badge value={r.status} />
              </div>
              <p>{r.message}</p>
              <small>
                {r.id} · {r.actor} · 基准 v{r.base_version} · {r.created_at}
              </small>
            </article>
          ))
        ) : (
          <Empty title="暂无操作回执">提交操作后在此查询结果。</Empty>
        )}
      </Card>
    </>
  );
}
