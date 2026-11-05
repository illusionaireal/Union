import { Badge } from '../../components/ui';
import type { GovernanceReceipt } from './types';

export function GovernanceReceiptView({ receipt }: { receipt: GovernanceReceipt }) {
  return (
    <section className="governance-receipt" aria-label="原治理请求回执">
      <Badge value={receipt.status} />
      <h3>{receipt.message}</h3>
      {receipt.effect === 'evidence_only' && <p>迟到内容已保留为未采用记录；工作尚未因此完成。</p>}
      <dl className="au-facts">
        <div>
          <dt>原请求</dt>
          <dd>{receipt.id}</dd>
        </div>
        <div>
          <dt>AU</dt>
          <dd>{receipt.organization_id}</dd>
        </div>
        <div>
          <dt>原提交主体</dt>
          <dd>{receipt.actor_principal_id}</dd>
        </div>
        <div>
          <dt>版本</dt>
          <dd>
            基准 v{receipt.base_version} · 回执 v{receipt.version}
          </dd>
        </div>
      </dl>
      <p className="form-note">这是原请求的历史回执，不代表你现在仍有 AU 权限。</p>
    </section>
  );
}
