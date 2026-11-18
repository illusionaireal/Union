import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { WorkspaceProvider, useWorkspace } from './workspace';
import { organizationPath, organizationRoute } from './organization-routes';
import { CommandProvider } from '../features/commands/CommandProvider';
import { GovernanceProvider } from '../features/governance/GovernanceProvider';
import { IdentityBoundary } from '../pages/Identity';
import { Layout } from './Layout';
import { Organizations, OrganizationOverview, OrganizationSectionPage, EntryProblem } from '../pages/Organizations';

function ResolveEntry() {
  const { core, loading, error } = useWorkspace();
  const location = useLocation();
  const route = organizationRoute(location.pathname, location.search);
  if (loading) return <p role="status">正在核对组织入口…</p>;
  if (route.kind === 'home' && !core) return <Navigate replace to="/organizations" />;
  if (location.pathname === '/gateways') return <Navigate replace to="/organizations?entry=platform" />;
  if (error || route.kind === 'invalid') return <EntryProblem />;
  return <Navigate replace to={core ? organizationPath(core.au.id, route.section) : '/organizations'} />;
}

function DeclaredRouteBoundary() {
  const location = useLocation();
  return organizationRoute(location.pathname, location.search).kind === 'invalid'
    ? <EntryProblem /> : <Outlet />;
}

function OrganizationBoundary() {
  const { core, loading } = useWorkspace();
  if (loading) return <p role="status">正在核对当前组织与访问权限…</p>;
  if (!core) return <EntryProblem />;
  return <div key={core.au.id}><Outlet /></div>;
}

function SignedInWorkspace() {
  const { session, error, refresh } = useWorkspace();
  if (!session) return <main className="identity-page"><div>
    <p role="status">{error || '正在核对当前核心身份…'}</p>
    {error && <button className="button secondary" onClick={() => void refresh()}>重试连接</button>}
  </div></main>;
  // Same-principal login renewal retains drafts. Other identities and service
  // instances cannot inherit protected component state or late responses.
  const identity = `${session?.service_instance ?? ''}:${session?.principal_id ?? session?.session_scope ?? ''}`;
  return <CommandProvider key={identity}>
    <GovernanceProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route element={<DeclaredRouteBoundary />}>
          <Route index element={<ResolveEntry />} />
          <Route path="organizations" element={<Organizations />} />
          <Route path="au/:auId" element={<OrganizationBoundary />}>
            <Route index element={<OrganizationOverview />} />
            <Route path="work" element={<OrganizationSectionPage section="work" />} />
            <Route path="work/:workId" element={<OrganizationSectionPage section="work" />} />
            <Route path="results" element={<OrganizationSectionPage section="results" />} />
            <Route path="work/:workId/results/:resultId" element={<OrganizationSectionPage section="results" />} />
            <Route path="attention" element={<OrganizationSectionPage section="attention" />} />
            <Route path="resources" element={<OrganizationSectionPage section="resources" />} />
            <Route path="governance" element={<OrganizationSectionPage section="governance" />} />
            <Route path="improvement" element={<OrganizationSectionPage section="improvement" />} />
            <Route path="collaboration" element={<OrganizationSectionPage section="collaboration" />} />
          </Route>
          <Route path="*" element={<ResolveEntry />} />
          </Route>
        </Route>
      </Routes>
    </GovernanceProvider>
  </CommandProvider>;
}

export default function App() {
  return <WorkspaceProvider><IdentityBoundary><SignedInWorkspace /></IdentityBoundary></WorkspaceProvider>;
}
