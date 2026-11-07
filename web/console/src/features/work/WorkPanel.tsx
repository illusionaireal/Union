import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { CoreWorkItem } from '../../api/types';
import { Card } from '../../components/ui';

function money(item: CoreWorkItem) {
  const { max_calls: max, reserved, used } = item.budget;
  return `${used} 已用 · ${reserved} 已预约 · 上限 ${max}`;
}

function receipt(item: CoreWorkItem) {
  const last = item.tool_calls[item.tool_calls.length - 1];
  if (!last) return '尚无工具回执';
  const detail = last.sha256 ? `sha256 ${last.sha256.slice(0, 12)}…` : `${last.count ?? 0} 份资料`;
  return `${last.tool} @ ${last.step_ref} · ${detail}`;
}

function attempt(item: CoreWorkItem) {
  const running = item.attempts.find((value) => value.status === 'running');
  const unknown = item.attempts.find((value) => value.status === 'unknown');
  if (unknown) return `执行结果未知，待核对（${unknown.id}）`;
  if (running) return `执行中（${running.id}）`;
  return item.attempts.length ? '本轮执行已结束' : '尚未开始执行';
}

export function WorkPanel({ organizationId }: { organizationId: string }) {
  const { data, isPending, error } = useQuery({
    queryKey: ['core-work', organizationId],
    queryFn: ({ signal }) => api.coreWork(organizationId, signal),
  });
  if (isPending) return <Card title="AI 工作（V1）">正在读取…</Card>;
  if (error || !data) return <Card title="AI 工作（V1）">读取失败，可刷新重试。</Card>;
  if (!data.works.length) {
    return (
      <Card title="AI 工作（V1）">
        <p>尚未登记 V1 工作。登记后这里会显示负责成员、有效授权、调用预算、执行尝试与工具回执。</p>
      </Card>
    );
  }
  return (
    <Card title="AI 工作（V1）">
      <ul className="work-panel" aria-label="V1 工作列表">
        {data.works.map((item) => (
          <li key={item.id} data-work={item.id}>
            <strong>{item.title}</strong>
            <p>{item.goal}</p>
            <dl>
              <div><dt>负责成员</dt><dd>{item.responsible.name}（{item.responsible.duty}）</dd></div>
              <div><dt>有效授权</dt><dd>{item.mandate.actions.join('、')}{item.mandate.active ? '' : '（已失效）'}</dd></div>
              <div><dt>调用预算</dt><dd>{money(item)}</dd></div>
              <div><dt>执行</dt><dd>{attempt(item)}</dd></div>
              <div><dt>最近工具回执</dt><dd>{receipt(item)}</dd></div>
              <div>
                <dt>授权资料</dt>
                <dd>
                  {item.materials.reference
                    ? `${item.materials.reference} · ${item.materials.available ? `可读 ${item.materials.documents} 份` : '宿主未就绪'}`
                    : '未绑定'}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </Card>
  );
}
