import {useQuery} from '@tanstack/react-query';
import {useWorkspace} from '../../app/workspace';
import {errorText} from '../../api/client';
import type {WorkScope} from './useWorkCommand';
import {readResultWork} from './result-reading';
import {ResultList} from './ResultList';
import {ResultReader} from './ResultReader';
import './result-reading.css';

function Results({scope, workId, resultId}: {scope: WorkScope; workId?: string; resultId?: string}) {
  const read = useQuery({queryKey:['result-work',scope],queryFn:({signal})=>readResultWork(scope,signal),retry:false,gcTime:0});
  if (read.isPending) return <p role="status">正在核对成果与原工作…</p>;
  if (read.error || !read.data) return <section><p role="alert">{errorText(read.error)}</p>
    <button className="button secondary" onClick={()=>void read.refetch()}>重试成果读取</button></section>;
  if (workId && resultId) {
    const work = read.data.works.find(x=>x.id===workId);
    const result = work?.results.find(x=>x.id===resultId);
    if (!work || !result) return <p role="alert">指定工作或成果不存在或不属于当前组织，未读取其他成果。</p>;
    return <ResultReader key={JSON.stringify([scope,work.id,work.version,work.status,work.delivered_result_id,result])}
      scope={scope} work={work} result={result} onRefresh={()=>read.refetch()} />;
  }
  return <section aria-label="组织成果"><h1>成果</h1>
    <p>阅读同一工作的版本正文、来源和采用依据；候选与已交付分别核对。</p>
    <ResultList organizationId={scope.organizationId} works={read.data.works} />
    <button className="button secondary" disabled={read.isFetching} onClick={()=>void read.refetch()}>刷新成果列表</button></section>;
}
export function CoreResults({workId, resultId}: {workId?: string; resultId?: string}) {
  const {core,session,connected} = useWorkspace();
  if (!core || !session?.principal_id || !session.service_instance || !connected)
    return <p role="alert">当前身份或连接未确认，请刷新组织后重开成果。</p>;
  const scope={organizationId:core.au.id,principalId:session.principal_id,serviceInstance:session.service_instance};
  return <Results key={JSON.stringify([scope,workId,resultId])} scope={scope} workId={workId} resultId={resultId} />;
}
