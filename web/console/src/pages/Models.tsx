import { useQuery } from '@tanstack/react-query';
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

export default function Models() {
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
  return (
    <>
      <section className="model-intro">
        <span className="model-intro-icon">
          <PlugZap size={28} />
        </span>
        <div>
          <h2>把模型接入公司的工作流</h2>
          <p>
            使用 Chat Completions 兼容接口。配置 API
            根地址、密钥和模型，保存后选择一次连接测试，再回到总览启动。
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
      {!d ? (
        <Card title="先为连接选择一个公司">
          <Empty title="模型连接随公司保存">
            创建公司后，即可在此填写 API 地址、API Key
            和模型名称。通用公司与业务试验都使用这个入口。
          </Empty>
          <div className="empty-actions">
            <CommandButton kind="create" primary>
              创建公司并继续配置
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
              { label: '验证方式', value: '一次连接测试', note: '测试会占用调用额度' },
            ]}
          />
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
                <div className="endpoint">
                  <Globe size={15} />
                  <span>{c.config.base_url}</span>
                </div>
                <div className="key-status">
                  <KeyRound size={15} />
                  {c.has_api_key ? 'API Key 已保存，内容不回显' : '未保存 API Key'}
                </div>
                <dl className="connection-facts">
                  <div>
                    <dt>输出上限</dt>
                    <dd>{c.config.max_output_tokens.toLocaleString()} tokens</dd>
                  </div>
                  <div>
                    <dt>请求超时</dt>
                    <dd>{c.config.timeout_seconds} 秒</dd>
                  </div>
                  <div>
                    <dt>输出模式</dt>
                    <dd>
                      {c.config.response_format === 'json_schema' ? 'JSON Schema' : 'JSON Object'}
                    </dd>
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
