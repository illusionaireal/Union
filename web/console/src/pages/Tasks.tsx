import { Search } from 'lucide-react';
import { useUrlState } from '../app/url-state';
import { useWorkspace } from '../app/workspace';
import { WorkRows } from '../components/Records';
import { Card, labels } from '../components/ui';
export default function Tasks() {
  const { data } = useWorkspace();
  const [params, update] = useUrlState();
  const query = params.get('q') || '',
    status = params.get('status') || 'all',
    member = params.get('member') || 'all';
  const set = (name: string, value: string) =>
    update((next) => {
      value && value !== 'all' ? next.set(name, value) : next.delete(name);
    });
  const works = Object.values(data!.organization.work);
  const filtered = works.filter(
    (w) =>
      (status === 'all' || w.display_status === status) &&
      (member === 'all' || w.member_id === member) &&
      `${w.id} ${w.title} ${w.instruction}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );
  return (
    <Card
      title="工作列表"
      action={
        <span className="count-label">
          {filtered.length} / {works.length} 项工作
        </span>
      }
    >
      <div className="filter-bar">
        <label className="search-field">
          <Search size={17} />
          <input
            id="task-search"
            aria-label="搜索工作"
            placeholder="搜索工作名称或 ID…"
            value={query}
            onChange={(e) => set('q', e.target.value)}
          />
        </label>
        <select
          id="work-filter"
          aria-label="工作状态"
          value={status}
          onChange={(e) => set('status', e.target.value)}
        >
          <option value="all">全部状态</option>
          {[...new Set(works.map((w) => w.display_status))].map((s) => (
            <option key={s} value={s}>
              {labels[s] || s}
            </option>
          ))}
        </select>
        <select
          id="member-filter"
          aria-label="负责成员"
          value={member}
          onChange={(e) => set('member', e.target.value)}
        >
          <option value="all">全部成员</option>
          {Object.values(data!.organization.members).map((m) => (
            <option value={m.id} key={m.id}>
              {m.name}
            </option>
          ))}
        </select>
        <button
          className="text-button"
          data-clear
          onClick={() =>
            update((next) => {
              ['q', 'status', 'member'].forEach((k) => next.delete(k));
            })
          }
        >
          清空筛选
        </button>
      </div>
      <div id="filtered-work">
        <WorkRows works={filtered} />
      </div>
    </Card>
  );
}
