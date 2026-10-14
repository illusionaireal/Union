import { useWorkspace } from '../app/workspace';
import { MemberRows } from '../components/Records';
import { Card, Empty } from '../components/ui';
export default function Members() {
  const { data } = useWorkspace();
  const positions = Object.values(data!.organization.positions);
  return (
    <div className="cards-grid">
      <Card title="稳定成员身份">
        <MemberRows />
      </Card>
      <Card title="岗位与职责">
        {positions.length ? (
          positions.map((p) => (
            <article className="position-row" key={p.id}>
              <span className="badge purple">岗位 v{p.version}</span>
              <h3>{p.title}</h3>
              <p>{p.mandate}</p>
              <small>{p.id}</small>
            </article>
          ))
        ) : (
          <Empty title="尚未形成岗位">职责来自组织决定，身份在交接中延续。</Empty>
        )}
      </Card>
    </div>
  );
}
