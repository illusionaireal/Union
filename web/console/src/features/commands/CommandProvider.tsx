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
import { api, errorText } from '../../api/client';
import type { CommandKind, PendingRequest, Receipt, Session, Snapshot } from '../../api/types';
import { useWorkspace } from '../../app/workspace';
import { Dialog } from '../../components/Dialog';
import { ReceiptView, CommandForm } from './CommandForm';
import { acceptReceipt, loadPending, savePending } from './receipts';
import { blocked, titles } from './model';
export interface CommandOptions {
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
  record: (receipt: Receipt) => Receipt;
  lookup: (item: PendingRequest) => Promise<Receipt>;
  inspect: (item: PendingRequest) => void;
}
const Context = createContext<Commands | null>(null);
export function CommandProvider({ children }: { children: ReactNode }) {
  const workspace = useWorkspace();
  const client = useQueryClient();
  const [pending, setPending] = useState(loadPending);
  const pendingRef = useRef(pending);
  const [receipts, setReceipts] = useState<Record<string, Receipt>>({});
  const known = useRef(receipts);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [inspection, setInspection] = useState<PendingRequest | null>(null);
  const [lookupError, setLookupError] = useState('');
  const remember = useCallback((item: PendingRequest) => {
    const next = [...pendingRef.current.filter((p) => p.id !== item.id), item];
    savePending(next);
    pendingRef.current = next;
    setPending(next);
  }, []);
  const record = useCallback(
    (receipt: Receipt) => {
      const previous = known.current[receipt.id];
      const value = acceptReceipt(previous, receipt);
      if (value === previous) return value;
      known.current = { ...known.current, [value.id]: value };
      setReceipts(known.current);
      const wasPending = pendingRef.current.some((p) => p.id === value.id);
      if (value.status !== 'accepted' && wasPending) {
        const next = pendingRef.current.filter((p) => p.id !== value.id);
        pendingRef.current = next;
        setPending(next);
        try {
          savePending(next);
        } catch {
          /* Stored original identity remains safe to query after reload. */
        }
        if (value.kind === 'create' && value.status === 'succeeded' && value.organization_id)
          workspace.selectOrg(value.organization_id);
        void client.invalidateQueries({ queryKey: ['workspace'] });
      }
      return value;
    },
    [client, workspace.selectOrg],
  );
  const lookup = useCallback(
    async (item: PendingRequest) => {
      const { receipt } = await api.receipt(item.id, item.organization_id);
      if (
        receipt.id !== item.id ||
        (item.organization_id && receipt.organization_id !== item.organization_id)
      )
        throw new Error('回执与原请求不匹配');
      return record(receipt);
    },
    [record],
  );
  const queries = useQuery({
    queryKey: [
      'pending-receipts',
      workspace.session?.service_instance,
      pending.map((p) => p.id).join(','),
    ],
    enabled: workspace.connected && pending.length > 0,
    queryFn: () =>
      Promise.all(
        pending.map((p) =>
          api
            .receipt(p.id, p.organization_id)
            .then((result) => {
              if (
                result.receipt.id !== p.id ||
                (p.organization_id && result.receipt.organization_id !== p.organization_id)
              )
                return null;
              return result.receipt;
            })
            .catch(() => null),
        ),
      ),
    refetchInterval: 2000,
    retry: false,
  });
  useEffect(() => {
    queries.data?.forEach((r) => {
      if (r) record(r);
    });
  }, [queries.data, record]);
  useEffect(() => {
    workspace.data?.receipts.forEach(record);
  }, [workspace.data?.receipts, record]);
  const inspect = (item: PendingRequest) => {
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
      organizationId: kind === 'create' ? null : workspace.orgId,
      data: workspace.data,
      session: workspace.session,
      options,
    });
  };
  return (
    <Context.Provider value={{ open, pending, receipts, remember, record, lookup, inspect }}>
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
