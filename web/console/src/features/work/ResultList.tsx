import {Link} from 'react-router-dom';
import type {CoreWorkItem} from '../../api/types';
import {organizationPath} from '../../app/organization-routes';

export function ResultList({organizationId, works}: {organizationId: string; works: CoreWorkItem[]}) {
  const rows = works.flatMap(work => work.results.map(result => ({work, result})));
  if (!rows.length) return <p>还没有 V1 成果。这里会显示本组织工作产生的成果，空列表不会触发模型调用。</p>;
  return <ul className="core-result-list">{rows.map(({work, result}) => <li key={`${work.id}:${result.id}`}>
    <div><h2>{result.title}</h2><p>来源工作：{work.title} · 版本 {result.seq}</p>
      <p>{result.status === 'adopted' ? '已采用' : '候选'}
        {work.delivered_result_id === result.id && work.status === 'delivered' ? ' · 已交付' : ''}</p></div>
    <Link className="button secondary" to={`${organizationPath(organizationId, 'work')}/${encodeURIComponent(work.id)}/results/${encodeURIComponent(result.id)}`}>阅读与下载</Link>
  </li>)}</ul>;
}
