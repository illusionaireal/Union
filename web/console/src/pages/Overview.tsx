import { CompanyPanel } from '../components/Company';
import { Users, ListChecks, Files, Activity, ArrowRight, Sparkles } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useWorkspace } from '../app/workspace';
import { Card, labels, sourceName, Badge } from '../components/ui';
import { ArtifactRows, MemberRows, WorkRows } from '../components/Records';
export default function Overview() {
  const { data } = useWorkspace();
  const { search } = useLocation();
  const d = data!,
    state = d.organization;
  const members = Object.values(state.members),
    works = Object.values(state.work),
    artifacts = Object.values(state.artifacts);
  const stage = d.company?.completed
    ? 'experiment_complete'
    : d.dispatch_state === 'pause_requested'
      ? 'pause_requested'
      : d.next_step;
  const more = (page: string) => (
    <Link className="more-link" to={{ pathname: '/' + page, search }}>
      查看全部 <ArrowRight size={14} />
    </Link>
  );
  const metrics = [
    { title: '正式成员', count: members.length, unit: '人', icon: Users, note: '持续的身份与责任' },
    {
      title: '组织工作',
      count: works.length,
      unit: '项',
      icon: ListChecks,
      note: `${works.filter((w) => w.status === 'delivered').length} 项已交付`,
    },
    {
      title: '成果版本',
      count: artifacts.length,
      unit: '份',
      icon: Files,
      note: '版本与来源可追溯',
    },
    {
      title: '调用占用',
      count: d.budget.calls_reserved,
      unit: `/ ${d.budget.max_calls}`,
      icon: Activity,
      note: '金额费用未知',
    },
  ];
  return (
    <>
      <CompanyPanel />
      <section className="status-hero">
        <div className="hero-main">
          <div className="eyebrow">
            <Sparkles size={15} /> {state.name} · {sourceName(d.source)}
          </div>
          <h2>{labels[stage] || stage}</h2>
          <p className="status-description">{state.goal}</p>
          <div className="hero-tags">
            <Badge value={d.execution_state} />
            <Badge value={d.dispatch_state} />
          </div>
        </div>
        <div className="hero-aside">
          <span className="eyebrow">NEXT ACTION</span>
          <h3>让每一步都有依据</h3>
          <p>
            {(d.company?.completed
              ? '本次试验已停止，等待审读三章正文、衔接与反馈后的实际改变。'
              : d.blocked_reasons.join('；')) ||
              (d.next_review_at
                ? '复查时间 ' + d.next_review_at
                : '按待办与新事件继续；暂无定时复查')}
          </p>
          <span className="hero-loop" aria-hidden="true">
            U
          </span>
        </div>
      </section>
      <section className="metrics" aria-label="组织指标">
        {metrics.map(({ title, count, unit, icon: Icon, note }) => (
          <div className="metric" key={title}>
            <div className="metric-label">
              {title}
              <Icon size={19} />
            </div>
            <div className="metric-number">
              <strong>{count}</strong>
              <span>{unit}</span>
            </div>
            <small>{note}</small>
          </div>
        ))}
      </section>
      <div className="overview-grid">
        <div className="column">
          <Card title="工作与依赖" action={more('tasks')}>
            <WorkRows works={works} />
          </Card>
          <Card title="当前行动">
            <p>
              {d.runs
                .filter((r) => r.status === 'running')
                .map((r) => r.work_id || '组织决定')
                .join('、') || labels[stage]}
            </p>
            <p className="form-note">
              待处理事件 {d.pending_events} 条 · 可派发工作 {d.ready_work.length} 项
            </p>
          </Card>
        </div>
        <div className="column">
          <Card title="协作成员" action={more('members')}>
            <MemberRows />
          </Card>
          <Card title="已保存成果" action={more('artifacts')}>
            <ArtifactRows artifacts={artifacts} />
          </Card>
        </div>
      </div>
    </>
  );
}
