import { Link, useLocation } from 'react-router-dom';
import type { ExecutionFailure } from '../api/types';

export function FailureNotice({
  failure,
  onNavigate,
}: {
  failure: ExecutionFailure;
  onNavigate?: () => void;
}) {
  const { search } = useLocation();
  return (
    <div className="connection-warning" role="alert" data-execution-failure={failure.code}>
      <strong>{failure.message}</strong>
      {failure.parameter && <p>供应商拒绝的参数：{failure.parameter}</p>}
      <p>{failure.recovery}</p>
      <div className="detail-links">
        <Link to={{ pathname: '/models', search }} onClick={onNavigate}>
          检查模型与 API
        </Link>
        <Link to={{ pathname: '/settings', search }} onClick={onNavigate}>
          核对执行或缺失用量
        </Link>
      </div>
    </div>
  );
}
