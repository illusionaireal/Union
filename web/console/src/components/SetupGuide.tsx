import { ArrowRight, Check, Cpu, Flag, Play } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useWorkspace } from '../app/workspace';
import { CommandButton } from '../features/commands/CommandProvider';

export function SetupGuide() {
  const { data, session } = useWorkspace();
  const { search } = useLocation();
  const configured = !!data?.execution_config.api_connection_id;
  const started = !!data?.runs.some((run) => run.kind !== 'connection_test');
  return (
    <section className="setup-guide" aria-label="公司启动准备">
      <div className="section-intro">
        <div>
          <span className="eyebrow">GET STARTED</span>
          <h2>从目标到行动，三步开始</h2>
        </div>
        <span className="quiet-pill">
          {Number(!!data) + Number(configured) + Number(started)} / 3 已准备
        </span>
      </div>
      <div className="setup-grid">
        <article className={data ? 'setup-step complete' : 'setup-step'}>
          <span className="step-icon">{data ? <Check size={21} /> : <Flag size={21} />}</span>
          <span className="step-number">01</span>
          <h3>定义目标与边界</h3>
          <p>
            {data ? data.organization.goal : '提供公司的目标，采用章程，并设置本次运行的调用额度。'}
          </p>
          {data ? (
            <Link to={{ pathname: '/settings', search }}>
              查看公司设置 <ArrowRight size={14} />
            </Link>
          ) : (
            <CommandButton kind="create" primary>
              创建我的 AI 公司
            </CommandButton>
          )}
        </article>
        <article className={configured ? 'setup-step complete' : 'setup-step'}>
          <span className="step-icon">
            <Cpu size={21} />
          </span>
          <span className="step-number">02</span>
          <h3>接入你的模型</h3>
          <p>
            {configured
              ? '已绑定默认连接。可以查看配置、修改模型，或确认一次连接测试。'
              : '填写 API 地址、API Key 与模型名称，保存后再测试连接。'}
          </p>
          <Link className="setup-action" to={{ pathname: '/models', search }}>
            {configured ? '管理模型与 API' : '添加模型 API'} <ArrowRight size={14} />
          </Link>
        </article>
        <article className={started ? 'setup-step complete' : 'setup-step'}>
          <span className="step-icon">
            <Play size={21} />
          </span>
          <span className="step-number">03</span>
          <h3>启动与观察协作</h3>
          <p>
            {started
              ? '沿着成员、工作和成果查看进展，依据实际回执继续下一步。'
              : '确认有限调用后启动。团队和工作由组织形成，成果持续保存。'}
          </p>
          <Link to={{ pathname: '/resources', search }}>
            了解执行与额度 <ArrowRight size={14} />
          </Link>
        </article>
      </div>
      {session?.role === 'observer' && (
        <p className="form-note">当前为观察者会话，可以查看进展；配置和启动由发起人操作。</p>
      )}
    </section>
  );
}

export function PageStats({
  items,
}: {
  items: { label: string; value: string | number; note?: string }[];
}) {
  return (
    <div className="page-stats">
      {items.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          {item.note && <small>{item.note}</small>}
        </div>
      ))}
    </div>
  );
}
