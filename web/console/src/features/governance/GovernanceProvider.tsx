import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { api, errorText } from '../../api/client';
import { useWorkspace } from '../../app/workspace';
import { Dialog } from '../../components/Dialog';
import { governanceApi } from './api';
import { available, sameScope, titles, type GovernanceDraft, type GovernanceScope } from './model';
import {
  loadReferences,
  matchesGovernanceReceipt,
  referenceKey,
  saveReferences,
  type GovernanceReference,
} from './receipts';
import type { GovernanceKind, GovernanceReceipt } from './types';
import { GovernanceForm } from './GovernanceForm';
import { GovernanceReceiptView } from './GovernanceReceiptView';
import './governance.css';

interface GovernanceContext {
  open: (kind: GovernanceKind, defaults?: Record<string, string>) => void;
  references: GovernanceReference[];
  receipts: Record<string, GovernanceReceipt>;
  remember: (reference: GovernanceReference) => void;
  forget: (reference: GovernanceReference) => void;
  record: (
    reference: GovernanceReference,
    receipt: GovernanceReceipt,
    scope: GovernanceScope,
  ) => Promise<GovernanceReceipt>;
  lookup: (reference: GovernanceReference, scope: GovernanceScope) => Promise<GovernanceReceipt>;
  inspect: (reference: GovernanceReference) => void;
}
const Context = createContext<GovernanceContext | null>(null);
export function GovernanceProvider({ children }: { children: ReactNode }) {
  const workspace = useWorkspace();
  const current = useRef(workspace);
  current.current = workspace;
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const [references, setReferences] = useState(loadReferences);
  const referencesRef = useRef(references);
  const [receipts, setReceipts] = useState<Record<string, GovernanceReceipt>>({});
  const receiptsRef = useRef(receipts);
  const [draft, setDraft] = useState<GovernanceDraft>();
  const [inspection, setInspection] = useState<{
    reference: GovernanceReference;
    scope: GovernanceScope;
    key: string;
  }>();
  const requireScope = (scope: GovernanceScope) => {
    if (!mounted.current || !sameScope(scope, current.current.session, current.current.orgId))
      throw new Error('核心身份或服务已变化，或已切换 AU；请用原身份查询原请求');
  };
  const remember = (reference: GovernanceReference) => {
    const next = [
      ...referencesRef.current.filter((item) => referenceKey(item) !== referenceKey(reference)),
      reference,
    ];
    saveReferences(next);
    referencesRef.current = next;
    setReferences(next);
  };
  const forget = (reference: GovernanceReference) => {
    const next = referencesRef.current.filter(
      (item) => referenceKey(item) !== referenceKey(reference),
    );
    referencesRef.current = next;
    setReferences(next);
    try {
      saveReferences(next);
    } catch {
      /* An old identity remains safe to query. */
    }
  };
  const record = async (
    reference: GovernanceReference,
    receipt: GovernanceReceipt,
    scope: GovernanceScope,
  ) => {
    requireScope(scope);
    if (!matchesGovernanceReceipt(reference, receipt)) throw new Error('回执与原请求不匹配');
    // The cookie may have changed in another tab since the last workspace read.
    const session = await api.session();
    requireScope(scope);
    if (!sameScope(scope, session, scope.organizationId))
      throw new Error('核心身份或服务已变化；请用原身份查询原请求');
    const key = referenceKey(reference);
    const value = receiptsRef.current[key] ?? receipt;
    receiptsRef.current = { ...receiptsRef.current, [key]: value };
    setReceipts(receiptsRef.current);
    const next = referencesRef.current.map((item) =>
      referenceKey(item) === key ? { ...item, resolved: true } : item,
    );
    referencesRef.current = next;
    setReferences(next);
    try {
      saveReferences(next);
    } catch {
      /* Keep the original reference for recovery. */
    }
    // A rejected late submission may still have durably saved unadopted evidence.
    void current.current.refresh();
    return value;
  };
  const lookup = async (reference: GovernanceReference, scope: GovernanceScope) => {
    requireScope(scope);
    if (reference.principal_id !== scope.principalId) throw new Error('请使用原提交主体查询回执');
    const session = await api.session();
    requireScope(scope);
    if (!sameScope(scope, session, scope.organizationId))
      throw new Error('核心身份或服务已变化；请用原身份查询原请求');
    const result = await governanceApi.receipt(reference.organization_id, reference.id);
    return record(reference, result.receipt, scope);
  };
  const open = (kind: GovernanceKind, defaults: Record<string, string> = {}) => {
    const { session, core, connected, orgId } = current.current;
    if (!session?.principal_id || !core || !connected || !available(core, kind)) return;
    setInspection(undefined);
    setDraft({
      key: crypto.randomUUID(),
      kind,
      read: structuredClone(core),
      scope: {
        principalId: session.principal_id,
        serviceInstance: session.service_instance,
        organizationId: orgId,
      },
      defaults: {
        member_id: crypto.randomUUID(),
        new_binding_id: crypto.randomUUID(),
        new_work_id: crypto.randomUUID(),
        new_mandate_id: crypto.randomUUID(),
        new_attempt_id: crypto.randomUUID(),
        ...defaults,
      },
    });
  };
  const inspect = (reference: GovernanceReference) => {
    const { session, orgId } = current.current;
    if (!session?.principal_id || reference.principal_id !== session.principal_id) return;
    setDraft(undefined);
    setInspection({
      reference,
      key: crypto.randomUUID(),
      scope: {
        principalId: session.principal_id,
        serviceInstance: session.service_instance,
        organizationId: orgId,
      },
    });
  };
  return (
    <Context.Provider
      value={{ open, references, receipts, remember, forget, record, lookup, inspect }}
    >
      {children}
      {draft && sameScope(draft.scope, workspace.session, workspace.orgId) && (
        <Dialog
          key={draft.key}
          id="governance-dialog"
          closeId="close-governance"
          title={titles[draft.kind]}
          onClose={() => setDraft(undefined)}
        >
          <GovernanceForm draft={draft} onClose={() => setDraft(undefined)} />
        </Dialog>
      )}
      {inspection && sameScope(inspection.scope, workspace.session, workspace.orgId) && (
        <Dialog
          key={inspection.key}
          id="governance-receipt-dialog"
          closeId="close-governance-receipt"
          title="查询原治理请求"
          onClose={() => setInspection(undefined)}
        >
          <ReceiptInspection reference={inspection.reference} scope={inspection.scope} />
        </Dialog>
      )}
    </Context.Provider>
  );
}
export function useGovernance() {
  const context = useContext(Context);
  if (!context) throw new Error('GovernanceProvider is required');
  return context;
}
export function GovernanceButton({
  kind,
  defaults,
  children,
  primary = false,
}: {
  kind: GovernanceKind;
  defaults?: Record<string, string>;
  children?: ReactNode;
  primary?: boolean;
}) {
  const workspace = useWorkspace();
  const governance = useGovernance();
  if (!workspace.core || !available(workspace.core, kind)) return null;
  return (
    <button
      type="button"
      className={`button ${primary ? 'primary' : 'secondary'}`}
      data-governance={kind}
      disabled={!workspace.connected}
      onClick={() => governance.open(kind, defaults)}
    >
      {children ?? titles[kind]}
    </button>
  );
}
export function GovernanceRecovery() {
  const { session, core } = useWorkspace();
  const governance = useGovernance();
  const references = governance.references.filter(
    (item) => item.principal_id === session?.principal_id,
  );
  if (!references.length) return null;
  const pending = references.filter((item) => !item.resolved);
  return (
    <details className="governance-recovery" open={!core || pending.length > 0}>
      <summary>
        我的治理请求 · {pending.length ? `${pending.length} 项结果待核对` : '原请求回执'}
      </summary>
      <p>仅查询你原来提交的请求。当前 AU 权限变化不改变这些回执的归属。</p>
      <ul>
        {[...references].reverse().map((reference) => (
          <li key={referenceKey(reference)}>
            <span>
              {titles[reference.kind]} · {reference.resolved ? '已有回执' : '结果待核对'}
            </span>
            <button
              type="button"
              className="text-button"
              aria-label={`查询原请求 ${reference.id}`}
              onClick={() => governance.inspect(reference)}
            >
              查询原请求 {reference.id}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
function ReceiptInspection({
  reference,
  scope,
}: {
  reference: GovernanceReference;
  scope: GovernanceScope;
}) {
  const governance = useGovernance();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);
  const query = async () => {
    setError('');
    setBusy(true);
    try {
      await governance.lookup(reference, scope);
    } catch (failure) {
      if (alive.current)
        setError(errorText(failure) + '；原请求标识已保留，请恢复原身份或连接后再查询。');
    } finally {
      if (alive.current) setBusy(false);
    }
  };
  useEffect(() => {
    alive.current = true;
    void query();
    return () => {
      alive.current = false;
    };
  }, []);
  const receipt = governance.receipts[referenceKey(reference)];
  return (
    <>
      {receipt ? (
        <GovernanceReceiptView receipt={receipt} />
      ) : (
        <p role="status">
          {busy ? '正在查询' : '尚未确认'}原请求 {reference.id}。
        </p>
      )}
      <button
        type="button"
        className="button secondary"
        disabled={busy}
        onClick={() => void query()}
      >
        查询原请求回执
      </button>
      {error && (
        <p role="alert" className="operation-error">
          {error}
        </p>
      )}
    </>
  );
}
