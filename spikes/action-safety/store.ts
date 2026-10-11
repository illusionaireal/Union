// Offline PLAN-002 experiment. Not a production authorization or payment service.
import { DatabaseSync } from 'node:sqlite';
import { createHash } from 'node:crypto';

export type Request = {
  unionId: string; key: string; actor: string; policyVersion: string;
  action: string; target: string; currency: string; maxMinor: number;
};
export type Receipt = { state: 'succeeded'; actualMinor: number } | { state: 'failed' | 'unknown' };
export type Policy = { unionId: string; actor: string; version: string; currency: string; target: string };
export type Action = Request & { hash: string; status: string; actualMinor: number | null };

function amount(value: number, allowZero = false) {
  if (!Number.isSafeInteger(value) || value < (allowZero ? 0 : 1)) throw new Error('invalid amount');
}
function fingerprint(r: Request) {
  return createHash('sha256').update(JSON.stringify([
    r.unionId, r.key, r.actor, r.policyVersion, r.action, r.target, r.currency, r.maxMinor,
  ])).digest('hex');
}
export class Store {
  db: DatabaseSync;
  constructor(path: string) {
    this.db = new DatabaseSync(path);
    this.db.exec('PRAGMA busy_timeout=10000; PRAGMA foreign_keys=ON;');
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS budgets (
        unionId TEXT PRIMARY KEY, currency TEXT NOT NULL,
        limitMinor INTEGER NOT NULL CHECK(limitMinor >= 0),
        heldMinor INTEGER NOT NULL DEFAULT 0 CHECK(heldMinor >= 0),
        spentMinor INTEGER NOT NULL DEFAULT 0 CHECK(spentMinor >= 0),
        CHECK(heldMinor + spentMinor <= limitMinor)
      );
      CREATE TABLE IF NOT EXISTS actions (
        unionId TEXT NOT NULL REFERENCES budgets(unionId), key TEXT NOT NULL,
        actor TEXT NOT NULL, policyVersion TEXT NOT NULL, action TEXT NOT NULL,
        target TEXT NOT NULL, currency TEXT NOT NULL, maxMinor INTEGER NOT NULL,
        hash TEXT NOT NULL, status TEXT NOT NULL, actualMinor INTEGER,
        PRIMARY KEY(unionId, key)
      );
    `);
  }
  close() { this.db.close(); }
  transaction<T>(fn: () => T): T {
    this.db.exec('BEGIN IMMEDIATE');
    try { const value = fn(); this.db.exec('COMMIT'); return value; }
    catch (error) { this.db.exec('ROLLBACK'); throw error; }
  }
  seed(unionId: string, currency: string, limitMinor: number) {
    amount(limitMinor);
    this.db.prepare('INSERT INTO budgets(unionId,currency,limitMinor) VALUES(?,?,?)')
      .run(unionId, currency, limitMinor);
  }
  budget(unionId: string) {
    return this.db.prepare('SELECT * FROM budgets WHERE unionId=?').get(unionId) as
      { unionId: string; currency: string; limitMinor: number; heldMinor: number; spentMinor: number };
  }
  get(unionId: string, key: string): Action | undefined {
    return this.db.prepare('SELECT * FROM actions WHERE unionId=? AND key=?').get(unionId, key) as Action | undefined;
  }
  reserve(r: Request, trustedPolicy: Policy): Action {
    // In production the policy and actor must come from authenticated service context.
    amount(r.maxMinor);
    if (typeof r.key !== 'string' || !r.key.trim() || r.key.length > 128) throw new Error('invalid key');
    if (r.unionId !== trustedPolicy.unionId || r.actor !== trustedPolicy.actor ||
        r.policyVersion !== trustedPolicy.version || r.currency !== trustedPolicy.currency ||
        r.target !== trustedPolicy.target || r.action !== 'mock.purchase') throw new Error('unauthorized');
    const hash = fingerprint(r);
    return this.transaction(() => {
      const existing = this.get(r.unionId, r.key);
      if (existing) {
        if (existing.hash !== hash) throw new Error('idempotency conflict');
        return existing;
      }
      const change = this.db.prepare(`UPDATE budgets SET heldMinor=heldMinor+?
        WHERE unionId=? AND currency=? AND ? <= limitMinor-heldMinor-spentMinor`)
        .run(r.maxMinor, r.unionId, r.currency, r.maxMinor);
      if (change.changes !== 1) throw new Error('budget unavailable');
      this.db.prepare(`INSERT INTO actions
        (unionId,key,actor,policyVersion,action,target,currency,maxMinor,hash,status)
        VALUES(?,?,?,?,?,?,?,?,?,'reserved')`).run(r.unionId,r.key,r.actor,r.policyVersion,
          r.action,r.target,r.currency,r.maxMinor,hash);
      return this.get(r.unionId, r.key)!;
    });
  }
  claim(unionId: string, key: string): Action | undefined {
    return this.transaction(() => {
      const changed = this.db.prepare(`UPDATE actions SET status='executing'
        WHERE unionId=? AND key=? AND status='reserved'`).run(unionId, key);
      return changed.changes === 1 ? this.get(unionId, key) : undefined;
    });
  }
  finish(unionId: string, key: string, receipt: Receipt) {
    return this.transaction(() => {
      const a = this.get(unionId, key);
      if (!a) throw new Error('unknown action');
      if (a.status === 'succeeded' || a.status === 'failed') {
        if (receipt.state !== a.status ||
            (receipt.state === 'succeeded' && receipt.actualMinor !== a.actualMinor)) throw new Error('conflicting receipt');
        return a;
      }
      if (!['executing','unknown'].includes(a.status)) throw new Error('not executing');
      if (receipt.state === 'unknown') {
        this.db.prepare("UPDATE actions SET status='unknown' WHERE unionId=? AND key=?").run(unionId,key);
      } else {
        const cost = receipt.state === 'succeeded' ? receipt.actualMinor : 0;
        amount(cost,true);
        if (cost > a.maxMinor) throw new Error('receipt exceeds reservation');
        this.db.prepare('UPDATE budgets SET heldMinor=heldMinor-?, spentMinor=spentMinor+? WHERE unionId=?')
          .run(a.maxMinor,cost,unionId);
        this.db.prepare('UPDATE actions SET status=?, actualMinor=? WHERE unionId=? AND key=?')
          .run(receipt.state,cost,unionId,key);
      }
      return this.get(unionId,key)!;
    });
  }
}

// Separate database represents an external provider. No shared transaction with Store.
export class MockProvider {
  db: DatabaseSync;
  constructor(path: string) {
    this.db = new DatabaseSync(path);
    this.db.exec('PRAGMA busy_timeout=10000; CREATE TABLE IF NOT EXISTS effects (id TEXT PRIMARY KEY, hash TEXT NOT NULL, cost INTEGER NOT NULL)');
  }
  close() { this.db.close(); }
  execute(a: Action): Receipt {
    const id = JSON.stringify([a.unionId,a.key]);
    this.db.prepare('INSERT OR IGNORE INTO effects(id,hash,cost) VALUES(?,?,?)').run(id,a.hash,a.maxMinor);
    const row = this.db.prepare('SELECT * FROM effects WHERE id=?').get(id)!;
    if (row.hash !== a.hash) throw new Error('provider idempotency conflict');
    return { state: 'succeeded', actualMinor: Number(row.cost) };
  }
  lookup(a: Action): Receipt {
    const row = this.db.prepare('SELECT * FROM effects WHERE id=?').get(JSON.stringify([a.unionId,a.key]));
    if (!row) return { state: 'unknown' }; // Absence is not definitive failure.
    if (row.hash !== a.hash) throw new Error('provider receipt mismatch');
    return { state: 'succeeded', actualMinor: Number(row.cost) };
  }
  count() { return Number(this.db.prepare('SELECT COUNT(*) AS count FROM effects').get()!.count); }
}
export function execute(store: Store, provider: MockProvider, unionId: string, key: string) {
  const a = store.claim(unionId,key);
  if (!a) return store.get(unionId,key); // Never blindly repeat an executing/unknown action.
  let receipt: Receipt;
  try { receipt = provider.execute(a); }
  catch { receipt = { state: 'unknown' }; }
  return store.finish(unionId,key,receipt);
}
export function reconcile(store: Store, provider: MockProvider, unionId: string, key: string) {
  const a = store.get(unionId,key);
  if (!a) throw new Error('unknown action');
  return store.finish(unionId,key,provider.lookup(a));
}
