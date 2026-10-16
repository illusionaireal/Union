import { ArrowRight, Flag, CheckCircle2, Clock3, Cpu } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useWorkspace } from '../app/workspace';
import { Card, Badge, labels } from '../components/ui';
import { SetupGuide, PageStats } from '../components/SetupGuide';
import { CompanyPanel } from '../components/Company';
import { ArtifactRows, WorkRows, MemberRows } from '../components/Records';
import { DetailLink } from '../features/details/Details';
import { FailureNotice } from '../components/FailureNotice';

export default function Overview() {
  const { data: d } = useWorkspace();
  const { search } = useLocation();
  if (!d)
    return (
      <>
        <section className="welcome-hero">
          <div>
            <span className="hero-kicker">一家围绕目标运转的 AI 公司</span>
            <h2>
              给出目标，
              <br />
              让协作开始。
            </h2>
            <p>
              建立团队的共同目标，连接你的模型，在一个工作空间里持续推进工作、交付成果与下一轮行动。
            </p>
            <Link className="button light" to={{ pathname: '/models', search }}>
              了解模型接入 <ArrowRight size={16} />
            </Link>
          </div>
          <div className="welcome-system" aria-hidden="true">
            <span>目标</span>
            <i />
            <span>团队 · 协作</span>
            <i />
            <span>成果 · 下一步</span>
          </div>
        </section>
        <SetupGuide />
      </>
    );
  const s = d.organization,
    works = Object.values(s.work),
    artifacts = Object.values(s.artifacts);
  const hasActivity = d.runs.some((run) => run.kind !== 'connection_test');
  const lastRun = d.runs.at(-1);
  const running = works.filter((w) => w.display_status === 'running'),
    done = works.filter((w) => w.status === 'delivered');
  const stage = d.company?.completed
    ? 'experiment_complete'
    : d.dispatch_state === 'pause_requested'
      ? 'pause_requested'
      : d.next_step;
  const active = works.filter((w) => !['delivered', 'cancelled'].includes(w.status));
  const next =
    d.blocked_reasons.join('；') ||
    (d.company?.completed
      ? '本次试验已完成，请审读实际成果与反馈后的改变。'
      : d.next_review_at
        ? '等待新事件，复查时间 ' + d.next_review_at
        : hasActivity
          ? '根据待办和反馈继续安排下一步。'
          : '先连接模型，再确认有限调用并启动协作。');
  const more = (path: string) => (
    <Link className="more-link" to={{ pathname: path, search }}>
      查看全部 <ArrowRight size={14} />
    </Link>
  );
  return (
    <>
      <section className="mission-panel">
        <div className="mission-copy">
          <span className="hero-kicker">
            <Flag size={15} />
            当前目标
          </span>
          <h2>{s.name}</h2>
          <p>{s.goal}</p>
          <div className="hero-tags">
            <Badge value={stage} />
            <Badge value={d.execution_state} />
            <Badge value={d.dispatch_state} />
          </div>
        </div>
        <div className="mission-next">
          <span className="eyebrow">下一步</span>
          <h3>
            {d.execution_config.api_connection_id ? '保持行动有据可循' : '为公司接入执行模型'}
          </h3>
          <p>{next}</p>
          <Link
            to={{
              pathname: d.execution_config.api_connection_id ? '/resources' : '/models',
              search,
            }}
          >
            {d.execution_config.api_connection_id ? '查看运行详情' : '添加模型 API'}{' '}
            <ArrowRight size={15} />
          </Link>
        </div>
      </section>
      {lastRun?.failure && ['failed', 'unknown'].includes(lastRun.status) && (
        <FailureNotice failure={lastRun.failure} />
      )}
      {!hasActivity && <SetupGuide />}
      <PageStats
        items={[
          { label: '团队成员', value: Object.keys(s.members).length, note: '稳定身份与岗位责任' },
          { label: '协作中的工作', value: active.length, note: running.length + ' 项正在执行' },
          { label: '已交付工作', value: done.length, note: artifacts.length + ' 份成果版本' },
          {
            label: '剩余调用额度',
            value: Math.max(0, d.budget.max_calls - d.budget.calls_reserved),
            note: '累计上限 ' + d.budget.max_calls + ' 次',
          },
        ]}
      />
      <div className="overview-grid">
        <div className="column">
          <Card title="需要关注的工作" action={more('/tasks')}>
            <WorkRows works={(active.length ? active : done).slice(0, 5)} />
          </Card>
          <Card title="最近交付" action={more('/artifacts')}>
            <ArtifactRows
              artifacts={[...artifacts]
                .sort((a, b) => b.created_at.localeCompare(a.created_at))
                .slice(0, 4)}
            />
          </Card>
        </div>
        <div className="column">
          <Card title="运行准备">
            <div className="readiness-row">
              <Cpu size={19} />
              <div>
                <strong>模型连接</strong>
                <p>{d.execution_config.api_connection_id || '尚未连接模型 API'}</p>
              </div>
              <Link className="text-button" to={{ pathname: '/models', search }}>
                管理
              </Link>
            </div>
            <div className="readiness-row">
              <CheckCircle2 size={19} />
              <div>
                <strong>章程已采用</strong>
                <p>当前版本 v{s.charter_version}</p>
              </div>
              <Link className="text-button" to={{ pathname: '/settings', search }}>
                查看
              </Link>
            </div>
            <div className="readiness-row">
              <Clock3 size={19} />
              <div>
                <strong>有限运行</strong>
                <p>
                  单次超时 {s.resources.timeout_seconds} 秒 · 已用 {d.budget.calls_reserved} 次
                </p>
              </div>
            </div>
          </Card>
          <Card title="协作团队" action={more('/members')}>
            <MemberRows />
          </Card>
          {d.decisions.length > 0 && (
            <Card title="最近决定" action={more('/activity')}>
              {d.decisions.slice(0, 3).map((item) => (
                <div className="decision-note" key={item.id}>
                  <DetailLink kind="decision" id={item.id}>
                    {item.data.issue}
                  </DetailLink>
                  <small>
                    {labels[item.status] || item.status} · {item.created_at}
                  </small>
                </div>
              ))}
            </Card>
          )}
        </div>
      </div>
      {d.company && (
        <div className="business-module">
          <div className="section-intro">
            <div>
              <span className="eyebrow">BUSINESS EXPERIMENT</span>
              <h2>业务试验 · 小说公司</h2>
            </div>
            <span className="quiet-pill">模拟平台</span>
          </div>
          <CompanyPanel />
        </div>
      )}
    </>
  );
}
