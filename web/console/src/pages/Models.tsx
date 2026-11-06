import { useQuery } from '@tanstack/react-query';
import SubscriptionConnections from './SubscriptionConnections';
import ModelServiceConnections from './ModelServiceConnections';
import ModelRunStream from './ModelRunStream';
import { Link, useLocation } from 'react-router-dom';
import {
  Cpu,
  Plus,
  KeyRound,
  ArrowRight,
  Globe,
  Settings2,
  ShieldCheck,
  PlugZap,
} from 'lucide-react';
import { api, errorText } from '../api/client';
import { useWorkspace } from '../app/workspace';
import { Card, Empty, Badge } from '../components/ui';
import { PageStats } from '../components/SetupGuide';
import { CommandButton } from '../features/commands/CommandProvider';
import { DetailLink } from '../features/details/Details';
import { FailureNotice } from '../components/FailureNotice';
import CoreModels from '../features/models/CoreModels';

export default function Models() {
  const { core, data, session, orgId } = useWorkspace();
  const coreMode = !!core || session?.organizations.find((item) => item.id === orgId)?.profile === 'core_v1' || (!data && session?.role === 'core');
  return coreMode ? <CoreModels /> : <LegacyModels />;
}

function LegacyModels() {
  const { data: d, session, orgId, connected } = useWorkspace();
  const { search } = useLocation();
  const board = session?.role === 'board',
    enabled = !!session?.executors.includes('api');
  const connections = useQuery({
    queryKey: [
      'model-connections',
      session?.service_instance,
      session?.role,
      orgId,
      d?.organization.version,
    ],
    enabled: connected && board && !!d && enabled,
    queryFn: ({ signal }) => api.connections(orgId, signal),
    retry: false,
    networkMode: 'always',
    refetchInterval: connected ? 4000 : false,
  });
  const list = connections.data?.connections || [];
  const active = d?.execution_config.api_connection_id;
  const gateways = useQuery({
    queryKey: ['gateway-choices', session?.service_instance, session?.role, orgId],
    enabled: connected && board && !!d && enabled,
    queryFn: ({ signal }) => api.gatewayChoices(orgId, signal),
    retry: false, refetchInterval: 4000,
  });
  const costs=useQuery({queryKey:['model-costs',session?.service_instance,session?.session_scope,orgId,d?.organization.version],enabled:connected&&board&&!!d,queryFn:()=>api.modelCosts(orgId),retry:false});
  return (
    <>
      <ModelServiceConnections />
      <ModelRunStream />
      <SubscriptionConnections />
      <section className="model-intro">
        <span className="model-intro-icon">
          <PlugZap size={28} />
        </span>
        <div>
          <h2>把模型接入公司的工作流</h2>
          <p>
            选择供应商与模型，保存连接，再测试工具往返能力。测试通过后采用为默认，回到总览开始协作。
          </p>
          <span className="security-note">
            <ShieldCheck size={14} />
            密钥不回显 · 保存不调用模型 · 按公司独立配置
          </span>
        </div>
        {d && board && enabled && (
          <CommandButton kind="api_connection" primary>
            <Plus size={16} />
            添加 API 连接
          </CommandButton>
        )}
      </section>
      {d && board && enabled && <div className="identity-actions">
        <CommandButton kind="api_import">导入配置</CommandButton>
        <a className="button secondary" href={api.exportModels(orgId)}>导出配置（不含密钥）</a>
        <CommandButton kind="api_binding">配置岗位模型与备用顺序</CommandButton>
        <CommandButton kind="api_cost_allocate">记录期末成本分摊</CommandButton>
      </div>}
      {d && board && <p className="form-note">默认备用顺序：{d.execution_config.fallbacks?.join(' → ') || '未设置'}。岗位绑定：{Object.entries(d.execution_config.roles || {}).map(([role,slot])=>`${d.organization.positions[role]?.title || role}：${slot.connection_id}${slot.fallbacks?.length?'（备用：'+slot.fallbacks.join(' → ')+'）':''}`).join('；') || '均继承默认'}。</p>}
      {!d ? (
        <Card title="先创建 AU 准备记录">
          <Empty title="模型连接按 AU 保存">
            新 AU 当前只保存资源计划，模型配置和调用尚未启用。
            已有旧版组织可继续使用兼容模型配置。
          </Empty>
          <div className="empty-actions">
            <CommandButton kind="create_v1" primary>
              创建 AU 准备记录
            </CommandButton>
          </div>
        </Card>
      ) : !board ? (
        <Card title="模型配置由发起人管理">
          <Empty title="当前为观察者会话">
            可以查看当前默认连接标识，连接详情和修改需要发起人会话。
          </Empty>
          <p>默认连接：{active || '尚未绑定'}</p>
        </Card>
      ) : !enabled ? (
        <Card title="本机尚未启用模型 API">
          <Empty title="API 配置当前不可用">请检查本机服务的启动配置，再刷新此页面。</Empty>
        </Card>
      ) : (
        <>
          <PageStats
            items={[
              {
                label: '已保存连接',
                value: connections.isSuccess ? list.length : '—',
                note: '仅当前公司',
              },
              { label: '默认连接', value: active || '尚未设置', note: '有限运行使用此连接' },
              { label: '验证方式', value: '工具往返测试', note: '两次调用，验证工具与继续执行' },
            ]}
          />
          {gateways.isError && <p role="alert">平台网关列表暂不可读；仍可手动配置独立 API 连接。</p>}
          {!!gateways.data?.gateways.length && <Card title="使用平台登记的网关">
            <p>选择公开接入地址，再填写该公司自己的令牌和模型。保存不调用模型，也不共享其他公司的密钥。</p>
            <div className="empty-actions">{gateways.data.gateways.map(gateway => <CommandButton key={gateway.id} kind="api_connection" options={{ gateway }}>使用 {gateway.config.name}</CommandButton>)}</div>
          </Card>}
          {!connected && (
            <div className="connection-warning" role="status">
              连接已断开，以下为最近读取的配置。恢复连接后才能操作。
            </div>
          )}
          {connections.isPending && (
            <Card title="读取模型连接">
              <p role="status">正在读取已保存配置…</p>
            </Card>
          )}
          {connections.isError && (
            <Card title="暂时无法读取连接">
              <p role="alert">{errorText(connections.error)}</p>
              <button
                className="button secondary"
                disabled={!connected}
                onClick={() => void connections.refetch()}
              >
                重新读取
              </button>
            </Card>
          )}
          {connections.isSuccess && list.length === 0 && (
            <Card title="添加第一个模型连接" className="model-empty">
              <Cpu size={36} />
              <h3>连接模型后，公司才能开始真实协作</h3>
              <p>
                准备供应商提供的 API 地址、API Key 和模型
                ID。你可以保存多个连接，随时更换默认使用的模型。
              </p>
              <CommandButton kind="api_connection" primary>
                <Plus size={16} />
                添加 API 连接
              </CommandButton>
            </Card>
          )}
          <div className="connection-grid">
            {list.map((c) => (
              <section
                className={'model-card' + (active === c.id ? ' is-default' : '')}
                key={c.id}
                data-connection={c.id}
              >
                {c.gateway_ref && <p className="form-note">网关登记来源：{c.gateway_ref.id} · v{c.gateway_ref.revision}（地址快照）</p>}
                <div className="model-card-heading">
                  <span className="provider-icon">
                    <Cpu size={23} />
                  </span>
                  <div>
                    <h2>{c.config.name}</h2>
                    <small>
                      {c.id} · v{c.revision}
                    </small>
                  </div>
                  <span className={'quiet-pill ' + (active === c.id ? 'selected' : '')}>
                    {active === c.id ? '默认连接' : '已保存'}
                  </span>
                </div>
                <strong className="connected-model">{c.config.model}</strong>
                <p className="form-note">{c.config.protocol || 'openai_chat_completions'} · 上下文 {c.catalog?.context_window?.toLocaleString() || '未知'} · 工具能力 {c.catalog?.tool_call===true?'目录声明支持':c.catalog?.tool_call===false?'目录声明不支持':'未知，需测试'} · 成本 {c.config.billing?.basis || 'unknown'}</p>
                {c.catalog?.cost && <p className="form-note">目录基础参考价（USD / 百万文本 token）：输入 {c.catalog.cost.input??'未知'}，输出 {c.catalog.cost.output??'未知'}。不自动用于本 AU 计费。</p>}
                <div className="endpoint">
                  <Globe size={15} />
                  <span>{c.config.backend === 'modeld' ? '平台托管模型服务' : c.config.base_url}</span>
                </div>
                <div className="key-status">
                  <KeyRound size={15} />
                  {c.config.backend === 'modeld' ? c.config.grant_ref ? '当前组织已获账号使用授权' : '等待平台管理员重新授权' : c.has_api_key ? 'API Key 已保存，内容不回显' : '未保存 API Key'}
                </div>
                <dl className="connection-facts">
                  <div>
                    <dt>输出上限</dt>
                    <dd>{c.config.max_output_tokens.toLocaleString()} tokens</dd>
                  </div>
                  <div>
                    <dt>{c.config.backend === 'modeld' ? '首事件 / 空闲超时' : '请求超时'}</dt>
                    <dd>{c.config.deadlines ? `${c.config.deadlines.first_event_ms / 1000} / ${c.config.deadlines.idle_ms / 1000} 秒` : `${c.config.timeout_seconds} 秒`}</dd>
                  </div>
                  <div>
                    <dt>输出模式</dt>
                    <dd>普通对话与组织工具</dd>
                  </div>
                  <div>
                    <dt>连接状态</dt>
                    <dd>{c.config.enabled ? '已启用' : '已停用'}</dd>
                  </div>
                </dl>
                <p className="form-note">保存配置不代表测试成功。连接测试的实际结果见下方回执。</p>
                <div className="connection-actions">
                  <CommandButton kind="api_connection" options={{ connection: c }}>
                    <Settings2 size={15} />
                    编辑连接
                  </CommandButton>
                  {active !== c.id && <CommandButton kind="api_test" options={{connection:c}}>测试此连接</CommandButton>}
                  {active === c.id ? (
                    <>
                      <CommandButton kind="api_test" options={{ connection: c }} primary>
                        测试连接
                      </CommandButton>
                      <CommandButton kind="api_binding" options={{ connectionId: '' }}>
                        取消默认
                      </CommandButton>
                    </>
                  ) : (
                    <CommandButton kind="api_binding" options={{ connectionId: c.id }}>
                      设为默认
                    </CommandButton>
                  )}
                </div>
              </section>
            ))}
          </div>
          <Card
            title="连接测试与配置回执"
            action={
              <Link className="more-link" to={{ pathname: '/settings', search }}>
                所有回执 <ArrowRight size={14} />
              </Link>
            }
          >
            {d.receipts.filter((r) => r.kind.startsWith('api_')).length ? (
              d.receipts
                .filter((r) => r.kind.startsWith('api_'))
                .slice(0, 6)
                .map((r) => (
                  <article className="command-receipt" key={r.id}>
                    <div className="receipt-heading">
                      <DetailLink kind="receipt" id={r.id}>
                        {r.kind === 'api_test'
                          ? '连接测试'
                          : r.kind === 'api_binding'
                            ? '默认连接变更'
                            : '保存连接'}
                      </DetailLink>
                      <Badge value={r.status} />
                    </div>
                    <p>{r.message}</p>
                    {r.failure && <FailureNotice failure={r.failure} />}
                    <small>{r.created_at}</small>
                  </article>
                ))
            ) : (
              <Empty title="还没有连接操作记录">保存配置和测试连接后，实际结果将在这里显示。</Empty>
            )}
          </Card>
          <Card title="模型用量与费用口径">
            <p className="form-note">金额采用最小货币单位。按量金额是估算；订阅与自有成本期末分摊，未知金额保持为空。</p>
            <div className="table-scroll"><table><thead><tr><th>调用</th><th>输入 / 输出 token</th><th>成本口径</th><th>金额</th><th>旧消息裁剪</th></tr></thead><tbody>{d.runs.slice(-10).reverse().map(run=><tr key={run.id}><td>{run.id}</td><td>{run.usage?.input_tokens??'未知'} / {run.usage?.output_tokens??'未知'}</td><td>{run.usage?.cost_basis||'unknown'}</td><td>{run.usage?.cost_minor==null?'未知':`${run.usage.cost_minor} ${run.usage.currency}（${run.usage.cost_status}）`}</td><td>{run.usage?.context?.dropped_messages??0}</td></tr>)}</tbody></table></div>
            {!!costs.data?.vouchers.length && <details><summary>期末分摊凭证</summary>{costs.data.vouchers.map(v=><p key={v.id}>{v.id} · {v.period} · {v.amount_minor} {v.currency} · {v.basis}</p>)}</details>}
          </Card>
          <div className="next-action-banner">
            <div>
              <strong>配置就绪，回到目标继续推进</strong>
              <p>在总览确认有限调用，组织将在现有授权内开展协作。</p>
            </div>
            <Link className="button primary" to={{ pathname: '/overview', search }}>
              前往公司总览 <ArrowRight size={16} />
            </Link>
          </div>
        </>
      )}
    </>
  );
}
