import { createContext, useContext, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, errorText } from '../../api/client';
import { useWorkspace } from '../../app/workspace';
import { Dialog } from '../../components/Dialog';
import { Badge, Json, sourceName } from '../../components/ui';
import { WorkRows } from '../../components/Records';
import { FailureNotice } from '../../components/FailureNotice';

type Kind = 'work' | 'member' | 'artifact' | 'event' | 'decision' | 'run' | 'receipt';
interface Selection {
  kind: Kind;
  id: string;
  organization: string;
}
const Context = createContext<(kind: Kind, id: string) => void>(() => undefined);
export function DetailLink({
  kind,
  id,
  children,
}: {
  kind: Kind;
  id: string;
  children: ReactNode;
}) {
  const open = useContext(Context);
  return (
    <button className="text-button" data-detail={kind} data-id={id} onClick={() => open(kind, id)}>
      {children}
    </button>
  );
}
export function DetailsProvider({ children }: { children: ReactNode }) {
  const { data, orgId } = useWorkspace();
  const [selection, setSelection] = useState<Selection | null>(null);
  const selected = selection?.organization === orgId ? selection : null;
  return (
    <Context.Provider value={(kind, id) => setSelection({ kind, id, organization: orgId })}>
      {children}
      {selected && data && <Details selection={selected} onClose={() => setSelection(null)} />}
    </Context.Provider>
  );
}
function ArtifactDetail({ id }: { id: string }) {
  const { data, orgId, session } = useWorkspace();
  const result = useQuery({
    queryKey: ['artifact', session?.service_instance, orgId, id],
    queryFn: ({ signal }) => api.artifact(orgId, id, signal),
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
  if (result.isPending || result.isFetching) return <p>正在读取文件并校验 SHA-256…</p>;
  if (result.isError || !result.data.verified)
    return (
      <>
        <p className="operation-error">
          成果不可用：{result.isError ? errorText(result.error) : '完整性校验未确认'}
        </p>
        <p>交付历史保留；不能将当前文件视为可用成果。</p>
      </>
    );
  const artifact = result.data;
  return (
    <>
      <p className="notice-source">
        {sourceName(data!.source)} · SHA-256 已校验 · v{artifact.version}
      </p>
      <small>{artifact.sha256}</small>
      <pre className="detail-data">{artifact.content}</pre>
      <div className="detail-links">
        <DetailLink kind="work" id={artifact.work_id}>
          来源工作
        </DetailLink>
        <DetailLink kind="member" id={artifact.member_id}>
          负责成员
        </DetailLink>
        <a className="button primary" href={api.download(orgId, id)} download>
          下载已校验文件
        </a>
      </div>
    </>
  );
}
function Details({
  selection: { kind, id },
  onClose,
}: {
  selection: Selection;
  onClose: () => void;
}) {
  const { data } = useWorkspace();
  const snapshot = data!;
  const state = snapshot.organization;
  let title = '记录详情';
  let body: ReactNode = <p>当前快照中没有这条记录，可刷新或在活动页翻页查找。</p>;
  if (kind === 'artifact') {
    title = state.artifacts[id]?.name || '组织成果';
    body = <ArtifactDetail key={id} id={id} />;
  } else if (kind === 'work' && state.work[id]) {
    const w = state.work[id];
    title = w.title;
    body = (
      <>
        <Badge value={w.display_status} />
        <p>{w.instruction}</p>
        <dl className="detail-dl">
          <div>
            <dt>负责成员</dt>
            <dd>
              <DetailLink kind="member" id={w.member_id}>
                {state.members[w.member_id]?.name || w.member_id}
              </DetailLink>
            </dd>
          </div>
          <div>
            <dt>工作版本与任职</dt>
            <dd>
              v{w.version} · {w.assignment_id}
            </dd>
          </div>
        </dl>
        <p>{w.summary || '尚无交付说明'}</p>
        <div className="detail-links">
          {w.dependencies.map((d) => (
            <DetailLink key={d} kind="work" id={d}>
              依赖：{state.work[d]?.title || d}
            </DetailLink>
          ))}
          {w.artifact_ids.map((a) => (
            <DetailLink key={a} kind="artifact" id={a}>
              {state.artifacts[a]?.name || a}
            </DetailLink>
          ))}
          {w.run_id && (
            <DetailLink kind="run" id={w.run_id}>
              执行记录
            </DetailLink>
          )}
        </div>
        <h3>关联决定</h3>
        {snapshot.decisions
          .filter((d) => JSON.stringify(d.data.operations).includes('"' + id + '"'))
          .map((d) => (
            <p key={d.id}>
              <DetailLink kind="decision" id={d.id}>
                {d.data.issue}
              </DetailLink>
            </p>
          ))}
        <p className="form-note">此处展示当前活动页的决定，更多记录可在活动中翻页查看。</p>
      </>
    );
  } else if (kind === 'member' && state.members[id]) {
    const member = state.members[id];
    title = member.name;
    body = (
      <>
        <p>
          {member.id} · {sourceName(snapshot.source)}
        </p>
        {Object.values(state.assignments)
          .filter((a) => a.member_id === id)
          .map((a) => (
            <p key={a.id}>
              {state.positions[a.position_id]?.title} · {a.active ? '当前任职' : '历史任职／已交接'}{' '}
              · {a.id}
            </p>
          ))}
        <WorkRows works={Object.values(state.work).filter((w) => w.member_id === id)} />
      </>
    );
  } else if (kind !== 'work' && kind !== 'member') {
    const rows = {
      event: snapshot.events,
      decision: snapshot.decisions,
      run: snapshot.runs,
      receipt: snapshot.receipts,
    }[kind];
    const row = rows.find((r) => r.id === id);
    title = { event: '组织事件', decision: '组织决定', run: '执行记录', receipt: '操作回执' }[kind];
    if (row)
      body = (
        <>
          {'failure' in row && row.failure && (
            <FailureNotice failure={row.failure} onNavigate={onClose} />
          )}
          {'status' in row && (
            <Badge value={'display_status' in row ? row.display_status : row.status} />
          )}
          <Json value={row} />
          {'usage' in row && (
            <>
              <p>
                输入 token：{row.usage?.input_tokens ?? '未提供'} · 输出 token：
                {row.usage?.output_tokens ?? '未提供'} · 金额未知
              </p>
              {row.work_id && (
                <DetailLink kind="work" id={row.work_id}>
                  关联工作
                </DetailLink>
              )}
            </>
          )}
        </>
      );
  }
  return (
    <Dialog id="detail-dialog" title={title} closeId="close-dialog" onClose={onClose}>
      <div id="detail-body">{body}</div>
    </Dialog>
  );
}
