import { Database } from 'bun:sqlite';
import { createHash, randomUUID, timingSafeEqual } from 'node:crypto';
import { chmodSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import type { APIAccount, APIConnectionReceipt, APIRegistration } from './api-accounts';

export type RequestState = 'queued' | 'connecting' | 'streaming' | 'completed' | 'failed' | 'interrupted';
export class Rejected extends Error {
  constructor(public readonly status: number, public readonly code: string) { super(code); }
}
export function requireValue(value: unknown, code: string, status = 400): asserts value {
  if (!value) throw new Rejected(status, code);
}
export function identifier(value: unknown): asserts value is string {
  requireValue(typeof value === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,159}$/.test(value), 'invalid_identifier');
}
export function canonical(value: any): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
const digest = (value: unknown) => createHash('sha256').update(canonical(value)).digest('hex');
export const equalSecret = (a: string, b: string) => {
  const x = Buffer.from(a), y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};
export interface Grant {
  id: string; au_id: string; account_ref: string; model_ids: string[];
  revision: number; revoked_at: string | null;
}
export interface InferenceInput {
  id: string; au_id: string; run_id: string; connection_id: string; connection_revision: number;
  grant_ref: string; grant_revision: number; model_id: string; messages: unknown[];
  tools: unknown[]; generation: Record<string, unknown>;
  deadlines: { first_event_ms: number; idle_ms: number; task_ms: number | null };
}
export interface StoredRequest {
  id: string; au_id: string; grant_ref: string; grant_revision: number; digest: string;
  payload: string; state: RequestState; cancel_requested: number;
  result: string | null; error: string | null; created_at: string;
}

/** Durable inbox: committing a connecting state is the point after which replay is forbidden. */
export class Journal {
  readonly db: Database;
  constructor(directory: string) {
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    const path = join(directory, 'modeld.sqlite3');
    this.db = new Database(path, { create: true, strict: true });
    try {
      requireValue([0, 1].includes(this.schemaVersion()), 'unsupported_modeld_schema', 409);
      if (this.schemaVersion() === 1) requireValue(
        (this.db.query('PRAGMA table_info(api_connections)').all() as { name: string }[]).some(x => x.name === 'options'),
        'incomplete_modeld_schema', 409);
    } catch (error) { this.db.close(); throw error; }
    chmodSync(path, 0o600);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;
      CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY, au_id TEXT NOT NULL, account_ref TEXT NOT NULL,
        model_ids TEXT NOT NULL, revision INTEGER NOT NULL, revoked_at TEXT);
      CREATE TABLE IF NOT EXISTS api_connections(id TEXT PRIMARY KEY, au_id TEXT NOT NULL, principal_id TEXT NOT NULL,
        name TEXT NOT NULL, base_url TEXT NOT NULL, api_key TEXT NOT NULL, model_id TEXT NOT NULL, digest TEXT NOT NULL,
        account_ref TEXT NOT NULL UNIQUE, grant_ref TEXT NOT NULL UNIQUE REFERENCES grants(id), grant_revision INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, au_id TEXT NOT NULL, grant_ref TEXT NOT NULL,
        grant_revision INTEGER NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL,
        cancel_requested INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT, created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS events(request_id TEXT NOT NULL, seq INTEGER NOT NULL, type TEXT NOT NULL,
        payload TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(request_id,seq));
      CREATE TABLE IF NOT EXISTS grant_audit(id INTEGER PRIMARY KEY, grant_id TEXT NOT NULL,
        revision INTEGER NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL);`);
    this.db.transaction(() => {
      for (const row of this.db.query("SELECT id FROM requests WHERE state IN ('connecting','streaming')").all() as { id: string }[]) {
        this.finish(row.id, 'interrupted', null, 'service_restarted_result_unknown');
      }
    })();
  }
  close() { this.db.close(); }
  private schemaVersion() { return (this.db.query('PRAGMA user_version').get() as { user_version: number }).user_version; }
  private apiOptions(id: string): Pick<APIRegistration, 'wire_api' | 'reasoning_effort'> {
    if (this.schemaVersion() === 0) return {};
    const row = this.db.query('SELECT options FROM api_connections WHERE id=?').get(id) as { options: string | null };
    if (!row.options) return {};
    const value = JSON.parse(row.options);
    requireValue(value && Object.keys(value).every(k => ['wire_api', 'reasoning_effort'].includes(k)) &&
      ['chat_completions','responses'].includes(value.wire_api) &&
      (!Object.hasOwn(value, 'reasoning_effort') || value.wire_api === 'responses' &&
        ['none','minimal','low','medium','high','xhigh','max'].includes(value.reasoning_effort)), 'invalid_api_account_options', 409);
    return value;
  }
  registerAPI(input: APIRegistration): APIConnectionReceipt {
    return this.db.transaction(() => {
      const prior = this.db.query('SELECT digest FROM api_connections WHERE id=?').get(input.id) as { digest: string } | null;
      if (prior) {
        requireValue(prior.digest === digest(input), 'api_connection_id_conflict', 409);
        return this.apiConnection(input.id, input.au_id, input.principal_id);
      }
      const options = input.wire_api === undefined ? null : { wire_api: input.wire_api,
        ...(input.reasoning_effort === undefined ? {} : { reasoning_effort: input.reasoning_effort }) };
      if (options && this.schemaVersion() === 0) {
        // Only explicit successful registration changes persistence. The ALTER,
        // version marker, account and grant all roll back together on failure.
        this.db.exec('ALTER TABLE api_connections ADD COLUMN options TEXT; PRAGMA user_version=1');
      }
      const reference = randomUUID();
      const grant = this.createGrant({ id: 'api-grant-' + reference, au_id: input.au_id,
        account_ref: 'api-' + reference, model_ids: [input.model_id] });
      this.db.query(`INSERT INTO api_connections(id,au_id,principal_id,name,base_url,api_key,model_id,digest,
        account_ref,grant_ref,grant_revision) VALUES(?,?,?,?,?,?,?,?,?,?,?)`).run(
        input.id, input.au_id, input.principal_id, input.name, input.base_url, input.api_key, input.model_id,
        digest(input), grant.account_ref, grant.id, grant.revision);
      if (options) this.db.query('UPDATE api_connections SET options=? WHERE id=?').run(JSON.stringify(options), input.id);
      return this.apiConnection(input.id, input.au_id, input.principal_id);
    })();
  }
  apiConnection(id: string, au: string, principal: string): APIConnectionReceipt {
    const row = this.db.query(`SELECT id,au_id,principal_id,name,model_id,grant_ref,grant_revision
      FROM api_connections WHERE id=?`).get(id) as Omit<APIConnectionReceipt, 'profile'> | null;
    requireValue(row, 'api_connection_not_found', 404);
    requireValue(row.au_id === au && row.principal_id === principal, 'api_connection_scope_mismatch', 403);
    const options = this.apiOptions(id);
    return { ...row, profile: options.wire_api === 'responses' ? 'openai_responses' : 'openai_compatible', ...options };
  }
  isAPIAccount(account: string): boolean {
    return !!this.db.query('SELECT 1 FROM api_connections WHERE account_ref=?').get(account);
  }
  apiAccount(account: string): APIAccount | null {
    const row = this.db.query(`SELECT id,au_id,principal_id,name,base_url,api_key,model_id,account_ref,grant_ref,grant_revision
      FROM api_connections WHERE account_ref=?`).get(account) as APIAccount | null;
    return row ? { ...row, ...this.apiOptions(row.id) } : null;
  }
  grant(id: string): Grant {
    const row = this.db.query('SELECT * FROM grants WHERE id=?').get(id) as any;
    requireValue(row, 'grant_not_found', 404);
    return { ...row, model_ids: JSON.parse(row.model_ids) };
  }
  authorize(input: Pick<InferenceInput, 'au_id' | 'grant_ref' | 'grant_revision' | 'model_id'>): Grant {
    const grant = this.grant(input.grant_ref);
    requireValue(grant.au_id === input.au_id && grant.revision === input.grant_revision && !grant.revoked_at,
      'grant_unavailable', 403);
    requireValue(grant.model_ids.includes(input.model_id), 'model_not_granted', 403);
    return grant;
  }
  createGrant(input: Omit<Grant, 'revision' | 'revoked_at'>): Grant {
    identifier(input.id); identifier(input.au_id); identifier(input.account_ref);
    requireValue(Array.isArray(input.model_ids) && input.model_ids.length > 0 && input.model_ids.length <= 100,
      'invalid_models');
    requireValue(input.model_ids.every(x => typeof x === 'string' && x.length > 0 && x.length <= 256), 'invalid_models');
    return this.db.transaction(() => {
      const prior = this.db.query('SELECT id FROM grants WHERE id=?').get(input.id);
      if (prior) {
        const old = this.grant(input.id);
        requireValue(!old.revoked_at && old.au_id === input.au_id && old.account_ref === input.account_ref &&
          canonical(old.model_ids) === canonical(input.model_ids), 'grant_id_conflict', 409);
        return old;
      }
      this.db.query('INSERT INTO grants VALUES(?,?,?,?,1,NULL)').run(input.id, input.au_id, input.account_ref, JSON.stringify(input.model_ids));
      this.db.query('INSERT INTO grant_audit(grant_id,revision,action,created_at) VALUES(?,1,?,?)')
        .run(input.id, 'created', new Date().toISOString());
      return this.grant(input.id);
    })();
  }
  revoke(id: string, revision: number): Grant {
    return this.db.transaction(() => {
      const old = this.grant(id);
      requireValue(old.revision === revision, 'grant_revision_conflict', 409);
      if (old.revoked_at) return old;
      this.db.query('UPDATE grants SET revision=revision+1,revoked_at=? WHERE id=?').run(new Date().toISOString(), id);
      this.db.query('INSERT INTO grant_audit(grant_id,revision,action,created_at) VALUES(?,?,?,?)')
        .run(id, revision + 1, 'revoked', new Date().toISOString());
      for (const row of this.db.query("SELECT id FROM requests WHERE grant_ref=? AND state='queued'").all(id) as { id: string }[])
        this.finish(row.id, 'failed', null, 'grant_revoked_before_dispatch');
      return this.grant(id);
    })();
  }
  submit(input: InferenceInput): { request: StoredRequest; created: boolean } {
    requireValue(input && typeof input === 'object' && Object.keys(input).sort().join() ===
      'au_id,connection_id,connection_revision,deadlines,generation,grant_ref,grant_revision,id,messages,model_id,run_id,tools', 'invalid_request_fields');
    for (const field of ['id','au_id','run_id','connection_id','grant_ref'] as const) identifier(input[field]);
    requireValue(input.run_id === input.id, 'request_must_match_reserved_run');
    requireValue(Number.isSafeInteger(input.connection_revision) && input.connection_revision > 0, 'invalid_revision');
    requireValue(Number.isSafeInteger(input.grant_revision) && input.grant_revision > 0, 'invalid_revision');
    requireValue(Array.isArray(input.messages) && input.messages.length > 0 && Array.isArray(input.tools), 'invalid_messages');
    requireValue(input.messages.length <= 10000 && input.tools.length <= 200, 'request_too_large', 413);
    requireValue(input.generation && Object.keys(input.generation).join() === 'maxOutputTokens' &&
      Number.isSafeInteger(input.generation.maxOutputTokens) && (input.generation.maxOutputTokens as number) >= 1 &&
      (input.generation.maxOutputTokens as number) <= 32768, 'invalid_generation');
    requireValue(input.deadlines && Object.keys(input.deadlines).sort().join() === 'first_event_ms,idle_ms,task_ms', 'invalid_deadlines');
    for (const key of ['first_event_ms', 'idle_ms'] as const)
      requireValue(Number.isSafeInteger(input.deadlines[key]) && input.deadlines[key] >= 1000 && input.deadlines[key] <= 3600000, 'invalid_deadlines');
    requireValue(input.deadlines.task_ms === null || Number.isSafeInteger(input.deadlines.task_ms) && input.deadlines.task_ms >= 1000 && input.deadlines.task_ms <= 3600000, 'invalid_deadlines');
    const body = canonical(input);
    requireValue(Buffer.byteLength(body) <= 8 * 1024 * 1024, 'request_too_large', 413);
    return this.db.transaction(() => {
      this.authorize(input);
      const old = this.db.query('SELECT * FROM requests WHERE id=?').get(input.id) as StoredRequest | null;
      if (old) {
        requireValue(old.digest === digest(input) && old.au_id === input.au_id, 'request_id_conflict', 409);
        return { request: old, created: false };
      }
      this.db.query(`INSERT INTO requests(id,au_id,grant_ref,grant_revision,digest,payload,state,created_at)
        VALUES(?,?,?,?,?,?,'queued',?)`).run(input.id, input.au_id, input.grant_ref, input.grant_revision,
          digest(input), body, new Date().toISOString());
      this.append(input.id, 'queued', {});
      return { request: this.get(input.id, input.au_id), created: true };
    })();
  }
  get(id: string, au: string): StoredRequest {
    const row = this.db.query('SELECT * FROM requests WHERE id=? AND au_id=?').get(id, au) as StoredRequest | null;
    requireValue(row, 'request_not_found', 404);
    return row;
  }
  queued(): StoredRequest[] {
    return this.db.query("SELECT * FROM requests WHERE state='queued' ORDER BY created_at,id").all() as StoredRequest[];
  }
  begin(id: string, au: string): Grant | null {
    return this.db.transaction(() => {
      const row = this.get(id, au);
      if (row.state !== 'queued' || row.cancel_requested) return null;
      const grant = this.authorize(JSON.parse(row.payload));
      this.db.query("UPDATE requests SET state='connecting' WHERE id=?").run(id);
      this.append(id, 'started', { account_ref: grant.account_ref });
      return grant;
    })();
  }
  append(id: string, type: string, payload: unknown) {
    requireValue(Buffer.byteLength(JSON.stringify(payload)) <= 8 * 1024 * 1024, 'event_too_large', 413);
    return this.db.transaction(() => {
      const row = this.db.query('SELECT COALESCE(MAX(seq),0)+1 AS seq FROM events WHERE request_id=?').get(id) as { seq: number };
      this.db.query('INSERT INTO events VALUES(?,?,?,?,?)').run(id, row.seq, type, JSON.stringify(payload), new Date().toISOString());
      return row.seq;
    })();
  }
  event(id: string, type: string, payload: unknown) {
    this.db.transaction(() => {
      const row = this.db.query('SELECT state,cancel_requested FROM requests WHERE id=?').get(id) as any;
      // An already-dispatched response is evidence even after local cancellation.
      // Retaining it neither reopens the request nor authorizes a tool/action.
      requireValue(row && ['connecting','streaming','interrupted'].includes(row.state), 'attempt_no_longer_current', 409);
      if (row.state !== 'interrupted') this.db.query("UPDATE requests SET state='streaming' WHERE id=?").run(id);
      this.append(id, type, payload);
    })();
  }
  finish(id: string, state: 'completed' | 'failed' | 'interrupted', result: unknown, error: string | null = null) {
    this.db.transaction(() => {
      const row = this.db.query('SELECT state,cancel_requested,result FROM requests WHERE id=?').get(id) as any;
      requireValue(row, 'request_not_found', 404);
      if (['completed','failed','interrupted'].includes(row.state)) {
        if (result !== null && row.state === 'interrupted') {
          if (row.result !== null) requireValue(canonical(JSON.parse(row.result)) === canonical(result), 'result_conflict', 409);
          else {
            this.db.query('UPDATE requests SET result=? WHERE id=?').run(JSON.stringify(result), id);
            this.append(id, 'late_result_observed', { action_authorized: false });
          }
        }
        return;
      }
      if (row.cancel_requested && state === 'completed') { state = 'interrupted'; error = 'cancel_requested_remote_result_unconfirmed'; }
      this.db.query('UPDATE requests SET state=?,result=?,error=? WHERE id=?')
        .run(state, result === null ? null : JSON.stringify(result), error, id);
      this.append(id, state, { error });
    })();
  }
  cancel(id: string, au: string) {
    this.db.transaction(() => {
      const row = this.get(id, au);
      if (['completed','failed','interrupted'].includes(row.state)) return;
      this.db.query('UPDATE requests SET cancel_requested=1 WHERE id=?').run(id);
      this.append(id, 'cancel_requested', { remote_cancellation_confirmed: false });
      if (row.state === 'queued') this.finish(id, 'failed', null, 'cancelled_before_dispatch');
    })();
  }
  events(id: string, au: string, after: number) {
    this.get(id, au);
    requireValue(Number.isSafeInteger(after) && after >= 0, 'invalid_sequence');
    return (this.db.query('SELECT seq,type,payload,created_at FROM events WHERE request_id=? AND seq>? ORDER BY seq LIMIT 500')
      .all(id, after) as any[]).map(row => ({ ...row, request_id: id, payload: JSON.parse(row.payload) }));
  }
}
