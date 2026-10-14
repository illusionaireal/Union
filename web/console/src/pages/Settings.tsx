import { Cpu, ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../app/workspace';
import { Badge, Card, Empty, Json } from '../components/ui';
import { CommandButton } from '../features/commands/CommandProvider';
import { titles } from '../features/commands/model';
import { DetailLink } from '../features/details/Details';
export default function Settings() {
  const { data, session } = useWorkspace();
  const d = data!;
  return (
    <>
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
            : '宿主尚未启用 Codex；可先保存模型，当前仍使用 Fixture 模拟。'}{' '}
          保存不调用模型，也不验证模型可用性。
        </p>
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
