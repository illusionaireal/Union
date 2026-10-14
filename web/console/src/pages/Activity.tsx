import { useUrlState } from '../app/url-state';
import { useWorkspace } from '../app/workspace';
import { Card, Badge, Empty } from '../components/ui';
import { DetailLink } from '../features/details/Details';
export default function Activity() {
  const { data, offset, setOffset } = useWorkspace();
  const [params, update] = useUrlState();
  const filter = params.get('type') || 'all';
  const rows = [
    ...data!.events.map((e) => ({
      id: e.id,
      type: 'event' as const,
      title: `${e.kind} · ${e.id}`,
      date: e.created_at,
      status: '',
    })),
    ...data!.decisions.map((d) => ({
      id: d.id,
      type: 'decision' as const,
      title: d.data.issue,
      date: d.created_at,
      status: d.status,
    })),
  ]
    .filter((r) => filter === 'all' || filter === r.type)
    .sort((a, b) => b.date.localeCompare(a.date));
  return (
    <Card title="事件与决定">
      <div className="segmented">
        {[
          ['all', '全部'],
          ['event', '事件'],
          ['decision', '决定'],
        ].map(([key, title]) => (
          <button
            key={key}
            data-activity={key}
            className={filter === key ? 'active' : ''}
            aria-pressed={filter === key}
            onClick={() =>
              update((next) => {
                next.set('type', key);
              })
            }
          >
            {title}
          </button>
        ))}
      </div>
      <div className="timeline">
        {rows.length ? (
          rows.map((r) => (
            <article key={r.type + r.id} className="runtime-row">
              <span className={`timeline-dot ${r.type}`} />
              <div className="row-main">
                <DetailLink kind={r.type} id={r.id}>
                  {r.title}
                </DetailLink>
                <small>
                  {r.date} · {r.id}
                </small>
              </div>
              {r.status ? <Badge value={r.status} /> : <span className="badge grey">事件</span>}
            </article>
          ))
        ) : (
          <Empty title="暂无活动">有效操作、执行与组织决定在此留痕。</Empty>
        )}
      </div>
      <div className="toolbar-pages">
        <button
          className="button secondary"
          data-page="-1"
          disabled={offset === 0}
          onClick={() => setOffset(offset - 50)}
        >
          上一页
        </button>
        <span>第 {Math.floor(offset / 50) + 1} 页 · 每类最多 50 条</span>
        <button
          className="button secondary"
          data-page="1"
          disabled={
            offset + 50 >= Math.max(data!.pagination.event_count, data!.pagination.decision_count)
          }
          onClick={() => setOffset(offset + 50)}
        >
          下一页
        </button>
      </div>
    </Card>
  );
}
