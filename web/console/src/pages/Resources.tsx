import { useWorkspace } from '../app/workspace';
import { Card, Badge, Empty, labels, sourceName } from '../components/ui';
import { CommandButton } from '../features/commands/CommandProvider';
import { DetailLink } from '../features/details/Details';
import { PageStats } from '../components/SetupGuide';
export default function Resources() {
  const { data } = useWorkspace();
  const d = data!;
  return (
    <>
      <PageStats
        items={[
          { label: '累计调用占用', value: d.budget.calls_reserved, note: '失败和未知结果保留占用' },
          {
            label: '剩余额度',
            value: Math.max(0, d.budget.max_calls - d.budget.calls_reserved),
            note: '上限 ' + d.budget.max_calls + ' 次',
          },
          {
            label: '用量回执',
            value: d.runs.filter((r) => r.usage).length + ' / ' + d.runs.length,
            note: '仅显示实际收到的记录',
          },
          {
            label: '待核对执行',
            value: d.runs.filter((r) => r.status === 'unknown').length,
            note: '未知结果先核对',
          },
        ]}
      />
      <div className="cards-grid">
        <Card title="调用额度">
          <div className="budget-number">
            {d.budget.calls_reserved}
            <span> / {d.budget.max_calls} 次</span>
          </div>
          <progress
            className="budget-progress"
            aria-label="累计调用占用"
            value={d.budget.calls_reserved}
            max={d.budget.max_calls}
          />
          <p>单次超时 {d.organization.resources.timeout_seconds} 秒；失败和未知调用保留占用。</p>
          <CommandButton kind="resources" />
        </Card>
        <Card title="执行依据">
          <dl className="detail-dl">
            <div>
              <dt>执行来源</dt>
              <dd>{sourceName(d.source)}</dd>
            </div>
            <div>
              <dt>宿主活性</dt>
              <dd>{d.host_activity.confirmed ? '已确认' : '无有效活性依据'}</dd>
            </div>
            <div>
              <dt>执行记录</dt>
              <dd>{labels[d.execution_state]}</dd>
            </div>
            <div>
              <dt>派发状态</dt>
              <dd>{labels[d.dispatch_state]}</dd>
            </div>
            <div>
              <dt>金额费用</dt>
              <dd>未知</dd>
            </div>
          </dl>
        </Card>
      </div>
      <Card title="执行记录">
        {d.runs.length ? (
          d.runs.map((r) => (
            <article key={r.id} className="runtime-row">
              <div className="row-main">
                <DetailLink kind="run" id={r.id}>
                  {r.work_id || '组织决定'}
                </DetailLink>
                <small>
                  {r.id} · {r.executor}
                  {r.simulated ? ' · 模拟' : ' · 真实执行器'}
                </small>
                <small>
                  开始 {r.started_at}
                  <br />
                  结束 {r.ended_at || '未结束'}
                </small>
              </div>
              <Badge value={r.display_status} />
            </article>
          ))
        ) : (
          <Empty title="尚无调用">读取和刷新不消耗调用额度。</Empty>
        )}
      </Card>
    </>
  );
}
