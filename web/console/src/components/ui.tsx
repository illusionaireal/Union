import type { ReactNode } from 'react';
import { CircleDashed, ArrowUpRight } from 'lucide-react';
export const labels: Record<string, string> = {
  bootstrap: '组织尚未形成',
  experiment_complete: '三个经营周期已完成',
  execute_work: '等待派发工作',
  decide: '等待组织决定',
  wait: '等待新事件',
  running: '协作进行中',
  unconfirmed: '执行活性未确认',
  unknown: '执行待核对',
  blocked: '运行受阻',
  paused: '派发已暂停',
  pause_requested: '暂停已请求，等待在途回执',
  needs_review: '执行待核对',
  dependent: '等待依赖',
  pending: '待执行',
  delivered: '已交付',
  continued: '进度已保存',
  progress: '工具进度已保存',
  failed: '执行失败',
  cancelled: '已取消',
  reconciled: '已核对',
  accepted: '已受理',
  rejected: '已拒绝',
  succeeded: '已完成',
  idle: '无在途执行',
  enabled: '允许派发',
};
export const sourceName = (source: string) =>
  ({
    fixture: 'Fixture · 模拟',
    real: '真实执行记录',
    mixed: '模拟与真实混合',
    not_run: '尚未执行',
  })[source] || source;
export function Badge({ value }: { value: string }) {
  const color = ['delivered', 'succeeded'].includes(value)
    ? 'green'
    : ['unknown', 'failed', 'rejected', 'needs_review'].includes(value)
      ? 'red'
      : ['wait', 'paused', 'dependent', 'unconfirmed', 'blocked', 'pause_requested'].includes(value)
        ? 'amber'
        : 'purple';
  return (
    <span className={`badge ${color}`}>
      <span className="badge-dot" />
      {labels[value] || value}
    </span>
  );
}
export function Card({
  title,
  children,
  action,
  className = '',
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      <div className="card-heading">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty-state">
      <CircleDashed size={30} aria-hidden="true" />
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}
export function Json({ value }: { value: unknown }) {
  return <pre className="detail-data">{JSON.stringify(value, null, 2)}</pre>;
}
export function SmallArrow() {
  return <ArrowUpRight size={15} aria-hidden="true" />;
}
