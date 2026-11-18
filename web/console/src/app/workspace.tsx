import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUrlState } from './url-state';
import { organizationPath, organizationRoute, validObjectId } from './organization-routes';
import { api, ApiError, errorText } from '../api/client';
import { matchesCoreRead } from '../api/core-boundary';
import type { CoreAURead, Session, Snapshot } from '../api/types';

interface ReadResult {
  session?: Session;
  snapshot: Snapshot | null;
  core: CoreAURead | null;
  successAt: string;
  readError?: string;
}
interface Workspace {
  session?: Session;
  data?: Snapshot;
  core?: CoreAURead;
  orgId: string;
  offset: number;
  connected: boolean;
  loading: boolean;
  error: string;
  lastSuccess: string;
  selectOrg: (id: string) => void;
  setOffset: (offset: number) => void;
  refresh: () => Promise<Snapshot | undefined>;
}
const Context = createContext<Workspace | null>(null);
function sameIdentity(left: Session | undefined, right: Session | undefined) {
  if (!left || !right) return left === right;
  return left.core_protocol === right.core_protocol && left.service_instance === right.service_instance &&
    (left.principal_id ?? left.session_scope) === (right.principal_id ?? right.session_scope);
}
const recentKey = 'union-recent-au-v1';
function recentOrganization(session: Session): string {
  try {
    const value = JSON.parse(localStorage.getItem(recentKey) || 'null');
    return value?.version === 1 && value.principal_id === session.principal_id &&
      value.service_instance === session.service_instance && typeof value.au_id === 'string' &&
      validObjectId(value.au_id) && session.organizations.some(item => item.id === value.au_id && item.profile === 'core_v1')
      ? value.au_id : '';
  } catch { return ''; }
}
function rememberOrganization(session: Session, id: string) {
  try {
    localStorage.setItem(recentKey, JSON.stringify({ version: 1,
      principal_id: session.principal_id, service_instance: session.service_instance, au_id: id }));
  } catch { /* Navigation remains usable when preference storage is unavailable. */ }
}
// One-time credentials are consumed once, including React development remounts.
let exchange: Promise<void> | undefined;
function exchangeLaunch() {
  const ticket = new URLSearchParams(window.location.hash.slice(1)).get('launch');
  if (ticket) {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    exchange = api.exchange(ticket).then(() => undefined);
  }
  return exchange ?? Promise.resolve();
}
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const location = useLocation();
  const navigate = useNavigate();
  const [params, update] = useUrlState();
  const route = organizationRoute(location.pathname, location.search);
  const requested = route.organizationId;
  const offset = Math.max(0, Number(params.get('offset')) || 0);
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [launchError, setLaunchError] = useState('');
  // Only an actual session read can change the current identity; an AU cache cannot.
  const [currentSession, setCurrentSession] = useState<Session>();
  const initialized = useRef(false);
  const key = ['workspace', route.kind, requested, offset] as const;
  const eraseProjections = (matches: (value: ReadResult) => boolean, message: string) => {
    client.setQueriesData<ReadResult>({ queryKey: ['workspace'] }, value =>
      value && (value.core || value.snapshot) && matches(value)
        ? { ...value, core: null, snapshot: null, successAt: '', readError: message } : value);
  };
  const read = useQuery<ReadResult>({
    queryKey: key,
    enabled: ready,
    // Organization/pagination reads keep the login boundary mounted, but must
    // never expose the previous organization's snapshot or enable commands.
    placeholderData: (previous) => previous ? { ...previous, snapshot: null, core: null } : undefined,
    queryFn: async ({ signal }): Promise<ReadResult> => {
      let session: Session;
      try {
        session = await api.session(signal);
        signal.throwIfAborted();
      } catch (failure) {
        if (!signal.aborted && failure instanceof ApiError && [401, 403].includes(failure.status ?? 0)) {
          eraseProjections(() => true, errorText(failure));
          setCurrentSession(undefined);
          return { snapshot: null, core: null, successAt: '', readError: errorText(failure) };
        }
        throw failure;
      }
      eraseProjections(value => !sameIdentity(value.session, session), '身份或服务已变化，请重新读取');
      setCurrentSession(session);
      const old = client.getQueryData<ReadResult>(key);
      const identityChanged = !!old && !sameIdentity(old.session, session);
      const targetId = route.kind === 'home' ? recentOrganization(session) : requested;
      const target = session.organizations.find(item => item.id === targetId && item.profile === 'core_v1');
      if (route.error || (targetId && !target)) {
        const message = route.error || '当前账户无法打开这个 V1 组织。请返回列表选择有权访问的组织。';
        if (targetId) eraseProjections(value => sameIdentity(value.session, session) && value.core?.au.id === targetId, message);
        return { session, snapshot: null, core: null, successAt: '', readError: message };
      }
      let core: CoreAURead | null = null;
      try { if (target) {
        if (session.core_protocol !== 'core.au.v1' || !session.principal_id)
          throw new ApiError('服务版本或核心身份不兼容，请重新登录并核对服务版本', 409, 'incompatible_state');
        core = await api.coreAU(target.id, signal);
        signal.throwIfAborted();
        if (!matchesCoreRead(core, session, target.id))
          throw new ApiError('AU记录与当前身份不一致，请保留原记录核对', 409, 'incompatible_state');
      } } catch (failure) {
        signal.throwIfAborted();
        const denied = failure instanceof ApiError &&
          ([400, 401, 403, 404, 409].includes(failure.status ?? 0) || failure.code === 'incompatible_state');
        // Every entry for this AU shares revocation knowledge. Keeping a
        // canonical URL cache after an alias was denied can reveal it offline.
        if (denied) eraseProjections(value => sameIdentity(value.session, session) && value.core?.au.id === targetId, errorText(failure));
        // A denial or changed principal must erase the old projection, while
        // retaining the current login for its own original receipt lookups.
        if (identityChanged || !old || denied) {
          return { session, snapshot: null, core: null, successAt: '', readError: errorText(failure) };
        }
        throw failure;
      }
      signal.throwIfAborted();
      if (core) rememberOrganization(session, core.au.id);
      return { session, snapshot: null, core, successAt: new Date().toLocaleTimeString('zh-CN') };
    },
    retry: false,
    networkMode: 'always',
    // Only poll once a read succeeded. Anonymous visitors get 401 on every
    // tick, and the repeated failures would otherwise churn the identity form.
    refetchInterval: (query) => (query.state.data?.session ? 4000 : false),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  });
  const refresh = useCallback(async () => {
    await client.cancelQueries({ queryKey: key, exact: true });
    const result=await read.refetch();
    return result.isError || result.data?.readError ? undefined : result.data?.snapshot ?? undefined;
    // Query identity is the organization + pagination; refetch always belongs to that observer.
  }, [client, route.kind, requested, offset, read.refetch]);
  useEffect(() => {
    const launch = () => {
      setReady(false);
      void exchangeLaunch()
        .then(() => {
          setLaunchError('');
          setReady(true);
          void client.invalidateQueries({ queryKey: ['workspace'] });
        })
        .catch((error) => {
          setLaunchError(errorText(error));
          setReady(false);
        });
    };
    if (!initialized.current) {
      initialized.current = true;
      launch();
    }
    window.addEventListener('hashchange', launch);
    return () => window.removeEventListener('hashchange', launch);
  }, [client]);
  useEffect(() => {
    const visible = () => {
      if (document.visibilityState === 'visible' && ready) void refresh();
    };
    document.addEventListener('visibilitychange', visible);
    return () => document.removeEventListener('visibilitychange', visible);
  }, [ready, refresh]);
  useEffect(() => {
    const offline = () => setOnline(false);
    const reconnect = () => {
      setOnline(true);
      if (ready) void refresh();
    };
    window.addEventListener('offline', offline);
    window.addEventListener('online', reconnect);
    return () => {
      window.removeEventListener('offline', offline);
      window.removeEventListener('online', reconnect);
    };
  }, [ready, refresh]);
  const projectedId = read.data?.core?.au.id ?? read.data?.snapshot?.organization.id;
  const inCurrentScope = !projectedId || currentSession?.organizations.some((item) => item.id === projectedId && item.profile === 'core_v1');
  const currentRead = read.isFetchedAfterMount && !read.isPlaceholderData &&
    sameIdentity(read.data?.session, currentSession) && inCurrentScope ? read.data : undefined;
  const data = currentRead?.snapshot ?? undefined;
  const core = currentRead?.core ?? undefined;
  const orgId = core?.au.id || data?.organization.id || requested;
  const selectOrg = useCallback(
    (id: string) => {
      navigate(id ? organizationPath(id) : '/organizations');
    },
    [navigate],
  );
  const setOffset = (value: number) =>
    update((next) => {
      next.set('offset', String(Math.max(0, value)));
    }, false);
  return (
    <Context.Provider
      value={{
        session: currentSession,
        data,
        core,
        orgId,
        offset,
        selectOrg,
        setOffset,
        refresh,
        connected: ready && online && !!currentRead?.session && read.isSuccess && !currentRead.readError && !read.isPlaceholderData && read.isFetchedAfterMount && !launchError,
        loading: !launchError && (read.isPending || read.isPlaceholderData || !read.isFetchedAfterMount || !ready),
        error: !online
          ? '浏览器网络已断开'
          : launchError || (read.isError ? errorText(read.error) : currentRead?.readError || ''),
        lastSuccess: currentRead?.successAt || '',
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useWorkspace() {
  const value = useContext(Context);
  if (!value) throw new Error('WorkspaceProvider is required');
  return value;
}
