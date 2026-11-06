import { useState } from 'react';
import { errorText } from '../../api/client';
import { referenceKey } from './requests';
import { titles } from './model';
import type { ModelReceipt, ModelReference } from './types';
import type { ModelsController } from './useModels';

export function ModelReceiptView({ receipt }: { receipt: ModelReceipt }) {
  return (
    <section className="model-receipt" aria-label="模型命令回执">
      <h3>{receipt.status === 'succeeded' ? '模型操作已受理' : '模型操作已拒绝'}</h3>
      <p>{receipt.message}</p>
      {receipt.status === 'succeeded' && (receipt.operation_id || receipt.check_id) && (
        <p>原意图已保存；连接保存或模型验证的实际结果请查看下方记录。</p>
      )}
      <details>
        <summary>原请求与责任</summary>
        <p>
          {titles[receipt.kind]} · {receipt.id}
        </p>
        <p>
          AU：{receipt.organization_id} · 提交主体：{receipt.actor_principal_id}
        </p>
        <p>
          基准 v{receipt.base_version} → v{receipt.version} · {receipt.created_at}
        </p>
        <p>这是原请求的历史回执，不代表当前仍有此 AU 的操作权限。</p>
      </details>
    </section>
  );
}
export function ModelRecovery({ controller }: { controller: ModelsController }) {
  const [selected, setSelected] = useState<ModelReference>();
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  const references = controller.references.filter(
    (item) => item.principal_id === controller.scope.principalId,
  );
  if (!references.length) return null;
  const pending = references.filter((item) => !item.resolved);
  const inspect = async (reference: ModelReference) => {
    setSelected(reference);
    setError('');
    setBusy(true);
    try {
      await controller.lookup(reference);
    } catch (failure) {
      setError(errorText(failure) + '；原请求已保留，请恢复原身份或连接后再查询。');
    } finally {
      setBusy(false);
    }
  };
  const receipt = selected && controller.receipts[referenceKey(selected)];
  return (
    <details
      className="governance-recovery model-recovery"
      open={!!selected || pending.length > 0 || !controller.read}
    >
      <summary>
        我的模型请求 · {pending.length ? `${pending.length} 项结果待核对` : '原请求回执'}
      </summary>
      <p>按原主体和请求查询。服务重启或 AU 读取权变化后仍可核对自己的回执；不会重新提交原操作。</p>
      <ul>
        {[...references].reverse().map((reference) => (
          <li key={referenceKey(reference)}>
            <span>
              {titles[reference.kind]} · {reference.organization_id} ·{' '}
              {reference.resolved ? '已有回执' : '结果待核对'}
            </span>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => void inspect(reference)}
            >
              查询原请求 {reference.id}
            </button>
          </li>
        ))}
      </ul>
      {receipt && <ModelReceiptView receipt={receipt} />}
      {busy && <p role="status">正在查询原模型请求…</p>}
      {error && (
        <p role="alert" className="operation-error">
          {error}
        </p>
      )}
    </details>
  );
}
