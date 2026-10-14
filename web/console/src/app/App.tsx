import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { WorkspaceProvider } from './workspace';
import { CommandProvider } from '../features/commands/CommandProvider';
import { DetailsProvider } from '../features/details/Details';
import { Layout } from './Layout';
import Overview from '../pages/Overview';
import Members from '../pages/Members';
import Tasks from '../pages/Tasks';
import Artifacts from '../pages/Artifacts';
import Activity from '../pages/Activity';
import Resources from '../pages/Resources';
import Settings from '../pages/Settings';
function Home() {
  const { search } = useLocation();
  return <Navigate to={{ pathname: '/overview', search }} replace />;
}
export default function App() {
  return (
    <WorkspaceProvider>
      <CommandProvider>
        <DetailsProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="overview" element={<Overview />} />
              <Route path="members" element={<Members />} />
              <Route path="tasks" element={<Tasks />} />
              <Route path="artifacts" element={<Artifacts />} />
              <Route path="activity" element={<Activity />} />
              <Route path="resources" element={<Resources />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<p>页面不存在，请从左侧导航选择工作台页面。</p>} />
            </Route>
          </Routes>
        </DetailsProvider>
      </CommandProvider>
    </WorkspaceProvider>
  );
}
