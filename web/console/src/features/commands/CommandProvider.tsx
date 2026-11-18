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
import { useLocation } from 'react-router-dom';
import { api, errorText } from '../../api/client';
import type { CommandKind, PendingRequest, Receipt, Session, Snapshot } from '../../api/types';
import { useWorkspace } from '../../app/workspace';
import { Dialog } from '../../components/Dialog';
import { ReceiptView, CommandForm } from './CommandForm';
import { acceptReceipt, inspectableCreation, loadPending, matchesRequest, ownedCreation, savePending } from './receipts';
import { blocked, titles, isCreation, sameCoreIdentity } from './model';
export interface CommandOptions {
  gateway?: import('../../api/client').GatewayChoice;
  connection?: import('../../api/types').ModelConnection;
  connectionId?: string;
}
interface Draft {
  key: string;
  kind: CommandKind;
  organizationId: string | null;
  data?: Snapshot;
  session: Session;
  options?: CommandOptions;
}
interface Commands {
  open: (kind: CommandKind, options?: CommandOptions) => void;
  pending: PendingRequest[];
  receipts: Record<string, Receipt>;
  remember: (item: PendingRequest) => void;
  forget: (id: string) => void;
  record: (receipt: Receipt, expected?: PendingRequest) => Receipt;
  lookup: (item: PendingRequest) => Promise<Receipt>;
  inspect: (item: PendingRequest) => void;
}
const Context = createContext<Commands | null>(null);
export function CommandProvider({ children }: { children: ReactNode }) {
  const workspace = useWorkspace();
  const location = useLocation();
  const currentLocation = useRef(location.key);
  currentLocation.current = location.key;
  const foreground = useRef(new Map<string, string>());
  const currentSession = useRef(workspace.session);
  currentSession.current = workspace.session;
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const client = useQueryClient();
  const [pending, setPending] = useState(loadPending);
  const pendingRef = useRef(pending);
  const [receipts, setReceipts] = useState<Record<string, Receipt>>({});
  const known = useRef(receipts);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [inspection, setInspection] = useState<PendingRequest | null>(null);
  const [lookupError, setLookupError] = useState('');
  const remember = useCallback((item: PendingRequest) => {
    if (item.kind === 'create_v1') {
      const session = currentSession.current;
      if (!session?.principal_id || session.core_protocol !== 'core.au.v1') throw new Error('缺少可信核心身份');
      item = { id: item.id, kind: item.kind, organization_id: item.organization_id,
        principal_id: session.principal_id, service_instance: session.service_instance, service_origin: window.location.origin };
    }
    const next = [...pendingRef.current.filter((p) => p.id !== item.id), item];
    savePending(next);
    foreground.current.set(item.id, currentLocation.current);
    pendingRef.current = next;
    setPending(next);
  }, []);
  const forget = useCallback((id: string) => {
    const next = pendingRef.current.filter((item) => item.id !== id);
    pendingRef.current = next;
    setPending(next);
    try { savePending(next); } catch { /* The retained identity can still be queried. */ }
  }, []);
  const record = useCallback(
    (receipt: Receipt, expected?: PendingRequest) => {
      if (!mounted.current) throw new Error('会话已结束；请用原身份查询原请求');
      const original = pendingRef.current.find(item => item.id === receipt.id) ?? expected;
      if (original && !matchesRequest(original, receipt)) throw new Error('回执与原请求不匹配');
      if (original?.kind === 'create_v1' && !sameCoreIdentity(workspace.session, currentSession.current))
        throw new Error('核心登录身份或服务已变化；请用原身份查询原请求');
      if (original?.kind === 'create_v1' && !inspectableCreation(original, currentSession.current) && !ownedCreation(original, currentSession.current))
        throw new Error('请切回原账户查询原创建');
      const previous = known.current[receipt.id];
      const value = acceptReceipt(previous, receipt);
      if (value === previous) return value;
      known.current = { ...known.current, [value.id]: value };
      setReceipts(known.current);
      const wasPending = pendingRef.current.some((p) => p.id === value.id);
      if (['succeeded', 'rejected'].includes(value.status) && wasPending) {
        const next = pendingRef.current.filter((p) => p.id !== value.id);
        pendingRef.current = next;
        setPending(next);
        try {
          savePending(next);
        } catch {
          /* Stored original identity remains safe to query after reload. */
        }
        if (value.kind === 'create_v1' && value.status === 'succeeded' && value.organization_id &&
            foreground.current.get(value.id) === currentLocation.current)
          workspace.selectOrg(value.organization_id);
        foreground.current.delete(value.id);
        void client.invalidateQueries({ queryKey: ['workspace'] });
      }
      return value;
    },
    [client, workspace.selectOrg, workspace.session],
  );
  const lookup = useCallback(
    async (item: PendingRequest) => {
      const scope = currentSession.current;
      if (item.kind !== 'create_v1' || (!ownedCreation(item, scope) && !inspectableCreation(item, scope)))
        throw new Error('此引用需由原账户或原受控客户端核对');
      const before = await api.session();
      if (!sameCoreIdentity(scope, before)) {
        void workspace.refresh();
        throw new Error('核心登录身份或服务已变化；请用原身份查询原请求');
      }
      const { receipt } = await api.receipt(item.id, item.organization_id, item.kind);
      const after = await api.session();
      if (!sameCoreIdentity(before, after) || !sameCoreIdentity(scope, currentSession.current)) {
        void workspace.refresh();
        throw new Error('核心登录身份或服务已变化；请用原身份查询原请求');
      }
      return record(receipt, item);
    },
    [record, workspace.refresh],
  );
  const recoverable = pending.filter(item => ownedCreation(item, workspace.session));
  const queries = useQuery({
    queryKey: [
      'pending-receipts',
      workspace.session?.service_instance,
      workspace.session?.principal_id ?? workspace.session?.session_scope,
      recoverable.map((p) => p.id).join(','),
    ],
    enabled: !!workspace.session?.principal_id && recoverable.length > 0,
    queryFn: async ({ signal }) => {
      const before = await api.session(signal);
      signal.throwIfAborted();
      if (!sameCoreIdentity(workspace.session, before)) { void workspace.refresh(); return []; }
      const receipts = await Promise.all(
        recoverable.map((p) =>
          api
            .receipt(p.id, p.organization_id, p.kind)
            .then((result) => {
              if (!matchesRequest(p, result.receipt)) return null;
              return result.receipt;
            })
            .catch(() => null),
        ),
      );
      signal.throwIfAborted();
      const after = await api.session(signal);
      signal.throwIfAborted();
      if (!sameCoreIdentity(before, after)) { void workspace.refresh(); return []; }
      return receipts;
    },
    refetchInterval: 2000,
    retry: false,
  });
  useEffect(() => {
    queries.data?.forEach((r) => {
      if (r) record(r);
    });
  }, [queries.data, record]);
  useEffect(() => {
    workspace.data?.receipts.forEach(receipt => record(receipt));
  }, [workspace.data?.receipts, record]);
  const inspect = (item: PendingRequest) => {
    foreground.current.set(item.id, currentLocation.current);
    setDraft(null);
    setInspection(item);
    setLookupError('');
    void lookup(item).catch((error) => setLookupError(errorText(error)));
  };
  const open = (kind: CommandKind, options?: CommandOptions) => {
    if (blocked(kind, workspace.connected, workspace.session, workspace.data) || !workspace.session)
      return;
    setInspection(null);
    setDraft({
      key: crypto.randomUUID(),
      kind,
      organizationId: isCreation(kind) ? null : workspace.orgId,
      data: workspace.data,
      session: workspace.session,
      options,
    });
  };
  return (
    <Context.Provider value={{ open, pending, receipts, remember, forget, record, lookup, inspect }}>
      {children}
      {draft && (
        <Dialog
          key={draft.key}
          id="operation-dialog"
          title={titles[draft.kind]}
          closeId="close-operation"
          onClose={() => setDraft(null)}
        >
          <CommandForm draft={draft} onClose={() => setDraft(null)} />
        </Dialog>
      )}
      {inspection && (
        <Dialog
          id="operation-dialog"
          title="查询操作回执"
          closeId="close-operation"
          onClose={() => setInspection(null)}
        >
          <div id="operation-result" role="status">
            {receipts[inspection.id] ? (
              <ReceiptView receipt={receipts[inspection.id]} onQuery={() => inspect(inspection)} />
            ) : (
              <p>正在查询原请求 {inspection.id}，不会重复提交。</p>
            )}
          </div>
          {lookupError && (
            <p role="alert" className="operation-error">
              {lookupError}
            </p>
          )}
        </Dialog>
      )}
    </Context.Provider>
  );
}
export function useCommands() {
  const value = useContext(Context);
  if (!value) throw new Error('CommandProvider is required');
  return value;
}
export function CommandButton({
  kind,
  children,
  primary = false,
  options,
}: {
  kind: CommandKind;
  children?: ReactNode;
  primary?: boolean;
  options?: CommandOptions;
}) {
  const { connected, session, data } = useWorkspace();
  const { open } = useCommands();
  const reason = blocked(kind, connected, session, data);
  return (
    <button
      className={`button ${primary ? 'primary' : 'secondary'}`}
      data-command={kind}
      disabled={!!reason}
      title={reason || titles[kind]}
      onClick={() => open(kind, options)}
    >
      {children || titles[kind]}
    </button>
  );
}
export type { Draft };
