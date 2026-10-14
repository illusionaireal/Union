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
import { useUrlState } from './url-state';
import { api, errorText } from '../api/client';
import type { Session, Snapshot } from '../api/types';

interface ReadResult {
  session: Session;
  snapshot: Snapshot | null;
  successAt: string;
}
interface Workspace {
  session?: Session;
  data?: Snapshot;
  orgId: string;
  offset: number;
  connected: boolean;
  loading: boolean;
  error: string;
  lastSuccess: string;
  selectOrg: (id: string) => void;
  setOffset: (offset: number) => void;
  refresh: () => Promise<void>;
}
const Context = createContext<Workspace | null>(null);
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
  const [params, update] = useUrlState();
  const requested = params.get('organization') || '';
  const offset = Math.max(0, Number(params.get('offset')) || 0);
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [launchError, setLaunchError] = useState('');
  const initialized = useRef(false);
  const key = ['workspace', requested, offset] as const;
  const read = useQuery({
    queryKey: key,
    enabled: ready,
    queryFn: async ({ signal }): Promise<ReadResult> => {
      const session = await api.session(signal);
      const target = session.organizations.some((o) => o.id === requested)
        ? requested
        : session.organizations[0]?.id;
      const snapshot = target ? await api.snapshot(target, offset, signal) : null;
      if (
        snapshot &&
        (snapshot.service_instance !== session.service_instance ||
          snapshot.organization.id !== target)
      ) {
        throw new Error('服务或组织已切换，请重新读取');
      }
      const old = client.getQueryData<ReadResult>(key);
      if (
        snapshot &&
        old?.snapshot?.service_instance === snapshot.service_instance &&
        old.snapshot.organization.id === target &&
        old.snapshot.snapshot_sequence >= snapshot.snapshot_sequence
      )
        return old;
      return { session, snapshot, successAt: new Date().toLocaleTimeString('zh-CN') };
    },
    retry: false,
    networkMode: 'always',
    refetchInterval: 4000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  });
  const refresh = useCallback(async () => {
    await client.cancelQueries({ queryKey: key, exact: true });
    await read.refetch();
    // Query identity is the organization + pagination; refetch always belongs to that observer.
  }, [client, requested, offset, read.refetch]);
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
  const data = read.data?.snapshot ?? undefined;
  const orgId = data?.organization.id || requested;
  const selectOrg = useCallback(
    (id: string) => {
      update((next) => {
        next.set('organization', id);
        next.delete('offset');
      }, false);
    },
    [update],
  );
  const setOffset = (value: number) =>
    update((next) => {
      next.set('offset', String(Math.max(0, value)));
    }, false);
  return (
    <Context.Provider
      value={{
        session: read.data?.session,
        data,
        orgId,
        offset,
        selectOrg,
        setOffset,
        refresh,
        connected: ready && online && read.isSuccess && read.isFetchedAfterMount && !launchError,
        loading: !launchError && (read.isPending || !read.isFetchedAfterMount || !ready),
        error: !online
          ? '浏览器网络已断开'
          : launchError || (read.isError ? errorText(read.error) : ''),
        lastSuccess: read.data?.successAt || '',
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
