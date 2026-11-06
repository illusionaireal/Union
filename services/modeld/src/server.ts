import { Database } from 'bun:sqlite';
import { mkdirSync, chmodSync } from 'node:fs';
import { join } from 'node:path';
import { Journal, Rejected, requireValue, equalSecret, identifier, type InferenceInput } from './journal';
import { uuid, validateAPIRegistration, type APIAccount } from './api-accounts';

export interface InferenceKernel {
  accounts(): Promise<unknown[]>;
  models(account: string): Promise<unknown[]>;
  connect(): Promise<{ attempt: any; complete: () => Promise<unknown> }>;
  infer(account: string, input: InferenceInput, signal: AbortSignal, event: (type: string, value: unknown) => void): Promise<unknown>;
  inferAPI?(account: APIAccount, input: InferenceInput, signal: AbortSignal, event: (type: string, value: unknown) => void): Promise<unknown>;
  close(): Promise<void>;
}

/** A separate rollback-journal lock releases on process death, before request recovery. */
export function own(directory: string) {
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const path = join(directory, 'owner.sqlite3');
  const db = new Database(path, { create: true });
  chmodSync(path, 0o600);
  try { db.exec('PRAGMA busy_timeout=0; BEGIN EXCLUSIVE'); }
  catch { db.close(); throw new Rejected(409, 'model_service_already_running'); }
  return () => { db.exec('ROLLBACK'); db.close(); };
}

export async function startService(options: {
  directory: string; adminToken: string; workerToken: string; port?: number;
  kernel: () => Promise<InferenceKernel>; upstream: string;
}) {
  for (const token of [options.adminToken, options.workerToken])
    requireValue(/^[\x21-\x7e]{32,256}$/.test(token), 'invalid_service_token');
  requireValue(!equalSecret(options.adminToken, options.workerToken), 'separate_tokens_required');
  const release = own(options.directory);
  let kernel: InferenceKernel, journal: Journal;
  try { kernel = await options.kernel(); journal = new Journal(options.directory); }
  catch (error) { release(); throw error; }
  journal.db.exec(`CREATE TABLE IF NOT EXISTS auth_commands(id TEXT PRIMARY KEY,state TEXT NOT NULL,receipt TEXT NOT NULL);
    UPDATE auth_commands SET state='unknown',receipt='{"state":"unknown","error":"auth_interrupted_check_account"}'
      WHERE state IN ('starting','authorizing');`);
  let stopping = false;
  const active = new Map<string, AbortController>();
  const jobs = new Set<Promise<unknown>>();
  function track(job: Promise<unknown>) { jobs.add(job); void job.finally(() => jobs.delete(job)).catch(() => {}); }
  function pump() {
    if (stopping || active.size) return;
    const row = journal.queued()[0];
    if (!row) return;
    let grant;
    try { grant = journal.begin(row.id, row.au_id); }
    catch { journal.finish(row.id, 'failed', null, 'grant_unavailable_before_dispatch'); queueMicrotask(pump); return; }
    if (!grant) { queueMicrotask(pump); return; }
    const controller = new AbortController(); active.set(row.id, controller);
    const input: InferenceInput = JSON.parse(row.payload);
    const timer = input.deadlines.task_ms === null ? null : setTimeout(() => controller.abort(), input.deadlines.task_ms);
    track((async () => {
      try {
        const account = journal.apiAccount(grant.account_ref);
        const event = (type: string, value: unknown) => journal.event(row.id, type, value);
        let result: unknown;
        if (account) {
          requireValue(account.au_id === input.au_id && account.grant_ref === input.grant_ref &&
            account.grant_revision === input.grant_revision && account.model_id === input.model_id, 'api_account_scope_mismatch', 403);
          requireValue(kernel.inferAPI, 'api_profile_unavailable', 503);
          result = await kernel.inferAPI(account, input, controller.signal, event);
        } else result = await kernel.infer(grant.account_ref, input, controller.signal, event);
        let authorized = !controller.signal.aborted;
        try { journal.authorize(input); } catch { authorized = false; }
        journal.finish(row.id, authorized ? 'completed' : 'interrupted', result,
          authorized ? null : 'result_observed_after_interruption');
      } catch (error) {
        // Once dispatch starts, errors must not imply a free/cancelled remote request.
        journal.finish(row.id, 'interrupted', null, error instanceof Rejected ? error.code : 'provider_result_unconfirmed');
      } finally {
        if (timer) clearTimeout(timer);
        active.delete(row.id); queueMicrotask(pump);
      }
    })());
  }
  const json = (value: unknown, status = 200) => Response.json(value, { status,
    headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
  const publicRequest = (row: ReturnType<Journal['get']>) => {
    let actionAuthorized = !row.cancel_requested && !['failed','interrupted'].includes(row.state);
    try { journal.authorize(JSON.parse(row.payload)); } catch { actionAuthorized = false; }
    return { id: row.id, au_id: row.au_id, request_digest: row.digest, action_authorized: actionAuthorized,
    state: row.state, created_at: row.created_at, cancel_requested: !!row.cancel_requested,
    result: row.result ? JSON.parse(row.result) : null, error: row.error };
  };
  const server = Bun.serve({ hostname: '127.0.0.1', port: options.port ?? 4098,
    maxRequestBodySize: 8 * 1024 * 1024, idleTimeout: 30,
    async fetch(request) {
      try {
        const url = new URL(request.url), path = url.pathname, method = request.method;
        requireValue(!request.headers.has('origin'), 'browser_access_forbidden', 403);
        const token = (request.headers.get('authorization') ?? '').replace(/^Bearer /, '');
        const admin = equalSecret(token, options.adminToken), worker = equalSecret(token, options.workerToken);
        requireValue(admin || worker, 'unauthorized', 401);
        requireValue(!stopping, 'service_stopping', 503);
        if (method === 'GET' && path === '/v1/runtime') return json({ protocol_version: 1,
          upstream: options.upstream, inference: 'single_native_stream', queue: 'persistent_serial', real_model_calls: 'not_inferred',
          profiles: ['modeld_grant', ...(kernel.inferAPI ? ['openai_compatible'] : [])] });
        const adminPath = /^\/v1\/(accounts|auth|grants|api-connections)(\/|$)/.test(path);
        requireValue(adminPath ? admin : worker, 'role_forbidden', 403);
        if (method === 'POST' && path === '/v1/api-connections')
          return json(journal.registerAPI(validateAPIRegistration(await request.json())), 201);
        const registration = path.match(/^\/v1\/api-connections\/([^/]+)$/);
        if (method === 'GET' && registration) {
          const au = url.searchParams.get('au_id'), principal = url.searchParams.get('principal_id');
          identifier(registration[1]); identifier(au); uuid(principal);
          return json(journal.apiConnection(registration[1], au, principal));
        }
        if (method === 'GET' && path === '/v1/accounts') return json({ accounts: await kernel.accounts() });
        const models = path.match(/^\/v1\/accounts\/([^/]+)\/models$/);
        if (method === 'GET' && models) {
          identifier(models[1]); requireValue(!journal.isAPIAccount(models[1]), 'api_account_not_host_account', 403);
          return json({ models: await kernel.models(models[1]) });
        }
        const auth = path.match(/^\/v1\/auth\/([^/]+)$/);
        if (auth) {
          identifier(auth[1]);
          const prior = journal.db.query('SELECT receipt FROM auth_commands WHERE id=?').get(auth[1]) as any;
          if (method === 'GET') { requireValue(prior, 'auth_not_found', 404); return json({ id: auth[1], ...JSON.parse(prior.receipt) }); }
          if (method === 'POST') {
            if (prior) return json({ id: auth[1], ...JSON.parse(prior.receipt) }, 202);
            const save = (value: any) => journal.db.query('UPDATE auth_commands SET state=?,receipt=? WHERE id=?')
              .run(value.state, JSON.stringify(value), auth[1]);
            journal.db.query('INSERT INTO auth_commands VALUES(?,?,?)').run(auth[1], 'starting', '{"state":"starting"}');
            track((async () => {
              try {
                const flow = await kernel.connect();
                save({ state: 'authorizing', ...flow.attempt });
                await flow.complete(); save({ state: 'connected' });
              } catch { save({ state: 'unknown', error: 'auth_result_unconfirmed' }); }
            })());
            return json({ id: auth[1], state: 'starting' }, 202);
          }
        }
        if (method === 'POST' && path === '/v1/grants') {
          const input = await request.json() as any;
          requireValue(input && Object.keys(input).sort().join() === 'account_ref,au_id,id,model_ids', 'invalid_grant');
          identifier(input.account_ref);
          requireValue(!journal.isAPIAccount(input.account_ref), 'api_account_not_host_account', 403);
          requireValue((await kernel.accounts() as any[]).some(a => a.id === input.account_ref), 'account_unavailable', 403);
          const models = await kernel.models(input.account_ref) as any[];
          requireValue(Array.isArray(input.model_ids) && input.model_ids.every((id: string) => models.some(m => m.id === id)), 'model_unavailable', 403);
          return json(journal.createGrant(input), 201);
        }
        const grant = path.match(/^\/v1\/grants\/([^/]+)(\/revoke)?$/);
        if (grant) {
          identifier(grant[1]);
          if (method === 'GET' && !grant[2]) return json(journal.grant(grant[1]));
          if (method === 'POST' && grant[2]) {
            const body = await request.json() as any;
            const value = journal.revoke(grant[1], body.revision);
            for (const [id, controller] of active) {
              const row = journal.db.query('SELECT grant_ref FROM requests WHERE id=?').get(id) as any;
              if (row.grant_ref === grant[1]) controller.abort();
            }
            return json(value);
          }
        }
        if (method === 'POST' && path === '/v1/requests') {
          const result = journal.submit(await request.json() as InferenceInput);
          queueMicrotask(pump); return json(publicRequest(result.request), 202);
        }
        const match = path.match(/^\/v1\/requests\/([^/]+)(\/(events|cancel))?$/);
        if (match) {
          identifier(match[1]); const au = url.searchParams.get('au_id'); identifier(au);
          const row = journal.get(match[1], au);
          if (method === 'GET' && !match[2]) return json(publicRequest(row));
          if (method === 'GET' && match[3] === 'events') {
            const after = Number(url.searchParams.get('after') ?? 0);
            requireValue(Number.isSafeInteger(after) && after >= 0, 'invalid_sequence');
            if (request.headers.get('accept') === 'text/event-stream') {
              let timer: ReturnType<typeof setInterval> | undefined;
              const encoder = new TextEncoder();
              const stream = new ReadableStream({ start(controller) {
                let cursor = after;
                const emit = () => {
                  try {
                    const events = journal.events(row.id, au, cursor);
                    for (const item of events) {
                      cursor = item.seq;
                      controller.enqueue(encoder.encode(`id: ${item.seq}\ndata: ${JSON.stringify(item)}\n\n`));
                    }
                    const state = journal.get(row.id, au).state;
                    if (stopping || events.length < 500 && ['completed','failed','interrupted'].includes(state)) {
                      if (timer) clearInterval(timer); controller.close();
                    }
                  } catch { if (timer) clearInterval(timer); controller.close(); }
                };
                timer = setInterval(emit, 200); emit();
              }, cancel() { if (timer) clearInterval(timer); } });
              return new Response(stream, { headers:{'Content-Type':'text/event-stream','Cache-Control':'no-store'} });
            }
            return json({ events: journal.events(row.id, au, after), state: row.state });
          }
          if (method === 'POST' && match[3] === 'cancel') {
            journal.cancel(row.id, au); active.get(row.id)?.abort(); return json(publicRequest(journal.get(row.id, au)), 202);
          }
        }
        return json({ error: 'not_found' }, 404);
      } catch (error) { return json({ error: error instanceof Rejected ? error.code : 'service_operation_failed' }, error instanceof Rejected ? error.status : 500); }
    }
  });
  queueMicrotask(pump);
  return { url: server.url.toString(), journal, async close() {
    stopping = true;
    await server.stop(true);
    for (const controller of active.values()) controller.abort();
    await kernel.close();
    await Promise.allSettled([...jobs]);
    journal.close(); release();
  } };
}
