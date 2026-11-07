import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';
import { Card } from '../../components/ui';

function href(organizationId: string, id: string) {
  return `/api/v1/work/results?organization_id=${encodeURIComponent(organizationId)}&id=${encodeURIComponent(id)}`;
}

export function ResultList({ organizationId }: { organizationId: string }) {
  const { data, isPending, error } = useQuery({
    queryKey: ['core-work', organizationId],
    queryFn: ({ signal }) => api.coreWork(organizationId, signal),
  });
  if (isPending) return <Card title="V1 成果">正在读取…</Card>;
  if (error || !data) return <Card title="V1 成果">读取失败，可刷新重试。</Card>;
  const rows = data.works.flatMap((work) => work.results.map((result) => ({ work, result })));
  if (rows.length === 0) {
    return (
      <Card title="V1 成果">
        <p>还没有 V1 成果。登记 AI 工作并提交候选成果后，这里会显示可打开、可下载的成果。</p>
      </Card>
    );
  }
  return (
    <Card title="V1 成果">
      <table className="results-table">
        <thead>
          <tr>
            <th scope="col">成果</th>
            <th scope="col">来源工作</th>
            <th scope="col">状态</th>
            <th scope="col">摘要</th>
            <th scope="col">读取</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ work, result }) => (
            <tr key={result.id} data-result={result.id}>
              <td>{result.title}</td>
              <td>{work.title}</td>
              <td>{result.status === 'adopted' ? '已采用' : '候选'}</td>
              <td>{result.sha256.slice(0, 12)}…</td>
              <td>
                <a href={href(organizationId, result.id)} download={`${result.id}.json`}>
                  下载
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
