import { Link, useLocation } from 'react-router-dom';
import { useWorkspace } from '../app/workspace';
import { Card } from './ui';
import { DetailLink } from '../features/details/Details';
const money = (n: number) => '¥' + (n / 100).toFixed(2);
export function CompanyPanel() {
  const { data } = useWorkspace();
  const { search } = useLocation();
  const company = data?.company;
  if (!company) return null;
  const t = company.totals;
  return (
    <section className="company-panel" aria-label="小说公司经营">
      <Card
        title={
          company.book_title ? `《${company.book_title}》· 经营试验` : '一家开箱即用的 AI 小说公司'
        }
      >
        <p className="form-note">
          模拟平台 · 3 个经营周期 ·{' '}
          {data?.source === 'fixture'
            ? '当前为脚本演示，未调用真实模型'
            : '模型用量与模拟经营数据分别记录'}
        </p>
        <div className="company-steps">
          <span>01 创建公司 ✓</span>
          <Link to={{ pathname: '/settings', search }}>
            02 {data?.execution_config.api_connection_id ? '模型已配置' : '配置并测试模型 API'}
          </Link>
          <span>03 运行与交付 {company.chapters.length}/3</span>
          <span>04 经营复盘 {company.reviews.length}/3</span>
        </div>
        <div className="company-finances">
          <div>
            <small>试验余额{t.unknown_model_costs ? '（成本未齐）' : ''}</small>
            <strong>{money(t.balance_minor)}</strong>
          </div>
          <div>
            <small>模拟订阅收入</small>
            <strong>{money(t.income_minor)}</strong>
          </div>
          <div>
            <small>模拟经营支出</small>
            <strong>{money(t.operating_cost_minor)}</strong>
          </div>
          <div>
            <small>模型费用估算 / 模拟用量演示</small>
            <strong>{money(t.model_estimate_minor)}</strong>
          </div>
        </div>
        <p className="form-note">
          启动模拟预算 {money(t.initial_budget_minor)}
          。余额包含模拟收支与模型估算，不能视为真实账户或盈利；缺失费用 {t.unknown_model_costs}{' '}
          笔。
        </p>
        {company.completed && (
          <p className="company-complete">
            三个周期已完成，已停止本次有限试验。{company.quality_review}
          </p>
        )}
        {!data?.execution_config.api_connection_id && (
          <p>先到组织设置接入模型；也可选择 Fixture 查看明确标识的脚本演示。</p>
        )}
        <div className="company-chapters">
          {[1, 2, 3].map((n) => {
            const ch = company.chapters.find((c) => c.chapter_number === n);
            const review = company.feedback_actions.find((r) => r.chapter_number === n);
            return (
              <article
                key={n}
                className={'company-chapter' + (ch?.negative_feedback ? ' negative' : '')}
              >
                <span className="eyebrow">CYCLE 0{n}</span>
                <h3>{ch ? ch.title : `第 ${n} 章 · 等待交付`}</h3>
                {ch ? (
                  <>
                    <DetailLink kind="artifact" id={ch.artifact_id}>
                      阅读已交付正文 →
                    </DetailLink>
                    <p>
                      模拟订阅 {ch.subscriptions} · 收入 {money(ch.income_minor)}
                    </p>
                    <p>{ch.feedback}</p>
                    {review ? (
                      <>
                        <DetailLink kind="decision" id={review.decision_id}>
                          查看经营决定
                        </DetailLink>
                        <p>{review.response}</p>
                        <div className="detail-links">
                          {review.next_work_ids.map((id) => (
                            <DetailLink key={id} kind="work" id={id}>
                              {review.delivered_work_ids.includes(id)
                                ? '✓ 后续工作已交付'
                                : '后续工作待执行'}
                            </DetailLink>
                          ))}
                        </div>
                      </>
                    ) : (
                      <p className="form-note">等待组织分析反馈并安排下一步。</p>
                    )}
                  </>
                ) : (
                  <p className="form-note">由组织自主计划与创作。</p>
                )}
              </article>
            );
          })}
        </div>
        <details>
          <summary>查看经营账本 · {company.ledger.length} 笔</summary>
          <div className="company-ledger">
            <table>
              <thead>
                <tr>
                  <th>类型</th>
                  <th>金额</th>
                  <th>来源</th>
                  <th>依据</th>
                </tr>
              </thead>
              <tbody>
                {company.ledger.map((row) => (
                  <tr key={row.id}>
                    <td>
                      {{ model: '模型', subscription: '订阅', server: '服务器', tax: '模拟税费' }[
                        row.kind
                      ] || row.kind}
                    </td>
                    <td>{row.amount_minor === null ? '未知' : money(row.amount_minor)}</td>
                    <td>
                      {{
                        mock_platform: '模拟平台',
                        simulated_usage: '模拟用量',
                        provider_usage_estimate: '供应商用量 × 配置单价',
                        board_usage_estimate: '董事会核对用量 × 配置单价',
                      }[row.source] || row.source}
                    </td>
                    <td>
                      {row.kind === 'model'
                        ? `${row.input_tokens ?? '?'} 输入 / ${row.output_tokens ?? '?'} 输出 token`
                        : row.reference}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Card>
    </section>
  );
}
