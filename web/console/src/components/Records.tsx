import { FileText, ArrowUpRight } from 'lucide-react';
import type { Artifact, Work } from '../api/types';
import { useWorkspace } from '../app/workspace';
import { DetailLink } from '../features/details/Details';
import { Badge, Empty } from './ui';
export function WorkRows({ works }: { works: Work[] }) {
  const { data } = useWorkspace();
  return works.length ? (
    <div className="runtime-list">
      {works.map((w) => (
        <article key={w.id} className="runtime-row">
          <div className="row-main">
            <DetailLink kind="work" id={w.id}>
              {w.title}
            </DetailLink>
            <small>
              {w.id} · {data?.organization.members[w.member_id]?.name || w.member_id}
            </small>
            {!!w.dependencies.length && (
              <p className="state-note">
                依赖{' '}
                {w.dependencies.map((d) => (
                  <DetailLink key={d} kind="work" id={d}>
                    {data?.organization.work[d]?.title || d}
                  </DetailLink>
                ))}
              </p>
            )}
          </div>
          <Badge value={w.display_status} />
        </article>
      ))}
    </div>
  ) : (
    <Empty title="没有匹配的工作">可以清空筛选，或等待组织形成正式工作。</Empty>
  );
}
export function ArtifactRows({ artifacts }: { artifacts: Artifact[] }) {
  const { data } = useWorkspace();
  return artifacts.length ? (
    <div>
      {artifacts.map((a) => (
        <article key={a.id} className="runtime-row">
          <span className="file-icon">
            <FileText size={21} />
          </span>
          <div className="row-main">
            <DetailLink kind="artifact" id={a.id}>
              {a.name}
            </DetailLink>
            <small>
              版本 {a.version} · {data?.organization.members[a.member_id]?.name || a.member_id}
            </small>
          </div>
          <ArrowUpRight className="muted" size={17} aria-label="打开时校验" />
        </article>
      ))}
    </div>
  ) : (
    <Empty title="还没有成果">工作交付后，可读取实际文件与版本。</Empty>
  );
}
export function MemberRows() {
  const { data } = useWorkspace();
  const state = data!.organization;
  const members = Object.values(state.members);
  return members.length ? (
    <div>
      {members.map((m, i) => (
        <article key={m.id} className="runtime-row">
          <span className={`avatar tone-${i % 3}`}>{m.name.slice(0, 1)}</span>
          <div className="row-main">
            <DetailLink kind="member" id={m.id}>
              {m.name}
            </DetailLink>
            <small>
              {Object.values(state.assignments)
                .filter((a) => a.active && a.member_id === m.id)
                .map((a) => state.positions[a.position_id]?.title)
                .join('、') || '尚未任职'}
            </small>
          </div>
          <span className="member-mark">AI</span>
        </article>
      ))}
    </div>
  ) : (
    <Empty title="组织尚未形成">成员与岗位将在有限运行中形成。</Empty>
  );
}
