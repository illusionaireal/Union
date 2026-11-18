/** Navigation grammar only. The workspace and public API own scope and access. */
export const organizationSections = [
  { path: '', label: '概况' },
  { path: 'work', label: '工作' },
  { path: 'results', label: '成果' },
  { path: 'attention', label: '关注事项' },
  { path: 'resources', label: '能力与资源' },
  { path: 'governance', label: '治理与成员' },
  { path: 'improvement', label: '改进' },
  { path: 'collaboration', label: '合作' },
] as const;
export type OrganizationSection = typeof organizationSections[number]['path'];
export interface OrganizationRoute {
  kind: 'home' | 'list' | 'au' | 'legacy' | 'invalid';
  organizationId: string;
  section: OrganizationSection;
  error?: string;
}
const aliases: Record<string, OrganizationSection> = {
  '/overview': '', '/tasks': 'work', '/artifacts': 'results', '/activity': 'attention',
  '/models': 'resources', '/resources': 'resources', '/members': 'governance', '/settings': 'governance',
};
export const validObjectId = (id: string) => /^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/.test(id);
export const organizationPath = (id: string, section: OrganizationSection = '') =>
  `/au/${encodeURIComponent(id)}${section ? '/' + section : ''}`;

export function organizationRoute(pathname: string, search: string): OrganizationRoute {
  const invalid: OrganizationRoute = { kind: 'invalid', organizationId: '', section: '', error: '链接无效或页面不存在，请返回组织列表。' };
  let path: string;
  try {
    if (/%(?:2f|5c)/i.test(pathname)) return invalid;
    path = decodeURIComponent(pathname);
  } catch { return invalid; }
  if (path.includes('%') || path.includes('\\') || path.includes('\0')) return invalid;
  if (path === '/') return { kind: 'home', organizationId: '', section: '' };
  if (path === '/organizations' || path === '/gateways') return { kind: 'list', organizationId: '', section: '' };
  if (Object.hasOwn(aliases, path)) {
    const requested = new URLSearchParams(search).getAll('organization');
    if (requested.length > 1 || (requested[0] && !validObjectId(requested[0]))) return invalid;
    return { kind: 'legacy', organizationId: requested[0] ?? '', section: aliases[path] };
  }
  const parts = path.split('/').slice(1);
  if (parts[0] !== 'au' || !validObjectId(parts[1] ?? '')) return invalid;
  const section = (parts[2] ?? '') as OrganizationSection;
  if (!organizationSections.some(item => item.path === section)) return invalid;
  const valid = parts.length === 2 ||
    (parts.length === 3 && section !== '') ||
    (section === 'work' && validObjectId(parts[3] ?? '') &&
      (parts.length === 4 || (parts.length === 6 && parts[4] === 'results' && validObjectId(parts[5]))));
  return valid ? { kind: 'au', organizationId: parts[1], section: parts.length === 6 ? 'results' : section } : invalid;
}
