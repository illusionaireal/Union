// Independent controlled HTTP evidence. Only a temporary local credential DB
// and a loopback provider are used; any non-loopback fetch is rejected.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { Kernel } from '../../src/kernel.ts';
import { startService } from '../../src/server.ts';
import { Credential } from '../../vendor/opencode/packages/core/src/credential.ts';
import { Integration } from '../../vendor/opencode/packages/core/src/integration.ts';

const directory = mkdtempSync(join(tmpdir(), 'union-kernel-review-'));
const requests: { account: string; body: any; url: string }[] = [];
let mode: 'ordinary' | 'reject' | 'slow-first' = 'ordinary';
let denyProvider = false;
let refreshRequests = 0;
const expectedSecrets: Record<string, string> = { a: 'review-key-a', b: 'review-key-b' };
let kernel: Kernel | undefined;
const realFetch = globalThis.fetch;
const frame = (data: unknown) => 'data: ' + JSON.stringify(data) + '\n\n';
const sse = (account: string, tool: boolean) => {
  const common = { id: 'review-completion', model: 'reported-review-model', object: 'chat.completion.chunk', created: 1 };
  const chunks = tool ? [
    { ...common, choices: [{ index: 0, delta: { role: 'assistant', tool_calls: [{ index: 0, id: 'review-call', type: 'function', function: { name: 'review_tool', arguments: '{"n":' } }] } }] },
    { ...common, choices: [{ index: 0, delta: { tool_calls: [{ index: 0, function: { arguments: '1}' } }] } }] },
    { ...common, choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }] },
  ] : [
    { ...common, choices: [{ index: 0, delta: { role: 'assistant', content: 'done-' + account } }] },
    { ...common, choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] },
  ];
  chunks.push({ ...common, choices: [], usage: { prompt_tokens: 20, completion_tokens: 9,
    total_tokens: 29, prompt_tokens_details: { cached_tokens: 3 }, completion_tokens_details: { reasoning_tokens: 2 }, cost: 0 } } as any);
  return chunks.map(frame).join('') + 'data: [DONE]\n\n';
};
const local = Bun.serve({ hostname: '127.0.0.1', port: 0, async fetch(request) {
  const url = new URL(request.url);
  if (url.pathname === '/console/auth/device/token') {
    refreshRequests++;
    assert.deepEqual(await request.json(), { grant_type: 'refresh_token', refresh_token: 'review-refresh-a', client_id: 'opencode-cli' });
    await new Promise(resolve => setTimeout(resolve, 40));
    expectedSecrets.a = 'review-refreshed-a';
    return Response.json({ access_token: expectedSecrets.a, refresh_token: 'review-rotated-refresh-a', expires_in: 3600, org_id: 'a' });
  }
  if (url.pathname === '/console/api/v2/config') {
    const org = request.headers.get('x-org-id');
    assert.ok(org === 'a' || org === 'b');
    assert.equal(request.headers.get('authorization'), 'Bearer ' + expectedSecrets[org!]);
    return Response.json({
      policies: denyProvider ? [{ action: 'provider.use', resource: 'opencode-go', effect: 'deny' }] : [],
      providers: { 'opencode-go': {
        canonical: 'openai', package: '@opencode/ai/providers/openai/chat',
        settings: { baseURL: local.url.origin + '/' + org + '/v1' },
        headers: { 'x-opencode-org-id': org },
        models: { 'review-model': { type: 'chat', modelID: 'review-native-model', name: 'Review controlled model',
          capabilities: { tools: true, input: ['text/plain'], output: ['text/plain'] },
          limit: { context: 4096, output: 256 } } },
      } },
    });
  }
  const path = url.pathname.match(/^\/([ab])\/v1\/chat\/completions$/);
  assert.ok(path, 'Unexpected local endpoint: ' + url.pathname);
  const account = path[1];
  assert.equal(request.headers.get('authorization'), 'Bearer ' + expectedSecrets[account]);
  assert.equal(request.headers.get('x-opencode-org-id'), account);
  const body = await request.json() as any;
  assert.equal(body.model, 'review-native-model');
  assert.equal(body.stream, true);
  requests.push({ account, body, url: url.pathname });
  if (mode === 'reject') return Response.json({ error: { message: 'Controlled provider unavailable' } }, { status: 503 });
  const tool = account === 'a' && !body.messages.some((message: any) => message.role === 'tool');
  const bodyText = sse(account, tool);
  if (mode === 'slow-first') {
    let timer: ReturnType<typeof setTimeout>;
    return new Response(new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(': heartbeat\n\n'));
      timer = setTimeout(() => { controller.enqueue(new TextEncoder().encode(bodyText)); controller.close(); }, 250);
    }, cancel() { clearTimeout(timer); } }), { headers: { 'Content-Type': 'text/event-stream' } });
  }
  return new Response(bodyText, { headers: { 'Content-Type': 'text/event-stream' } });
} });
const allowedOrigins = new Set([local.url.origin]);
globalThis.fetch = ((input: any, init?: any) => {
  const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
  assert.ok(allowedOrigins.has(url.origin), 'Outbound request forbidden by offline review probe');
  return realFetch(input, init);
}) as typeof fetch;

const input = (account: string, messages: any[]) => ({
  id: 'review-' + account, au_id: 'au-' + account, run_id: 'review-' + account,
  connection_id: 'connection-' + account, connection_revision: 1, grant_ref: 'grant-' + account,
  grant_revision: 1, model_id: 'review-model', messages,
  tools: [{ type: 'function', function: { name: 'review_tool', description: 'Controlled review tool',
    parameters: { type: 'object', properties: { n: { type: 'integer' } }, required: ['n'] } } }],
  generation: { maxOutputTokens: 128 }, deadlines: { first_event_ms: 2000, idle_ms: 2000, task_ms: 5000 },
});
const checks: string[] = [];
try {
  kernel = await Kernel.create(directory);
  const internals = kernel as any;
  const accounts: string[] = [];
  for (const account of ['a', 'b']) {
    const saved = await internals.runtime.runPromise(internals.credentials.create({
      integrationID: Integration.ID.make('opencode'), label: 'Controlled account ' + account,
      value: Credential.Key.make({ type: 'key', key: 'review-key-' + account,
        metadata: { server: local.url.origin + '/console', orgID: account, orgName: account } }),
    }));
    accounts.push(saved.id);
  }
  const catalogue = await kernel.models(accounts[0]);
  assert.ok(catalogue.some((model: any) => model.id === 'review-model'));
  const native = await internals.context(accounts[0]);
  assert.equal(native.models.find((model: any) => model.id === 'review-model').canonical, 'openai');
  checks.push('account-local remote catalog materializes canonical provider');
  const collected: any[] = [];
  const [a, b] = await Promise.all([
    kernel.infer(accounts[0], input('a', [{ role: 'user', content: 'Use the review tool' }]), new AbortController().signal,
      (type, value) => collected.push({ type, value })),
    kernel.infer(accounts[1], input('b', [{ role: 'user', content: 'Plain reply' }]), new AbortController().signal, () => {}),
  ]) as any[];
  assert.equal(requests.length, 2);
  assert.equal(b.message.content, 'done-b');
  assert.equal(a.message.tool_calls[0].function.arguments, '{"n":1}');
  assert.equal(a.usage.input_tokens, 20);
  assert.equal(a.usage.cached_input_tokens, 3);
  assert.equal(a.usage.reasoning_tokens, 2);
  assert.equal(a.usage.modeld_usage.cost, 0);
  assert.ok(collected.some(item => item.type === 'native_event' && item.value.type === 'raw'));
  checks.push('parallel accounts preserve endpoint/token/workspace despite globally active last account');
  checks.push('one inference POST per call; fragmented tool input, raw frames and usage retained');
  const followup = await kernel.infer(accounts[0], input('a', [
    { role: 'user', content: 'Use the review tool' }, JSON.parse(JSON.stringify(a.message)),
    { role: 'tool', tool_call_id: 'review-call', content: 'tool complete' },
  ]), new AbortController().signal, () => {}) as any;
  assert.equal(followup.message.content, 'done-a');
  assert.equal(requests.length, 3);
  checks.push('serialized native assistant/tool-result roundtrip reaches second stream');
  denyProvider = true;
  await assert.rejects(() => kernel!.infer(accounts[0], input('a', [{ role: 'user', content: 'denied' }]), new AbortController().signal, () => {}));
  assert.equal(requests.length, 3);
  denyProvider = false;
  checks.push('provider.use deny blocks inference before model POST');
  mode = 'reject';
  await assert.rejects(() => kernel!.infer(accounts[1], input('b', [{ role: 'user', content: 'reject' }]), new AbortController().signal, () => {}));
  assert.equal(requests.length, 4);
  checks.push('503 does not silently retry model POST');
  mode = 'slow-first';
  const short = input('b', [{ role: 'user', content: 'slow' }]);
  short.deadlines.first_event_ms = 60;
  let firstEventTimedOut = false;
  try { await kernel.infer(accounts[1], short, new AbortController().signal, () => {}); }
  catch { firstEventTimedOut = true; }
  mode = 'ordinary';
  const admin = 'review-admin-token-never-real-000000000000';
  const worker = 'review-worker-token-never-real-0000000000';
  const borrowed = {
    accounts: () => kernel!.accounts(), models: (id: string) => kernel!.models(id),
    connect: () => kernel!.connect(), infer: (...args: any[]) => (kernel!.infer as any)(...args),
    close: async () => {},
  };
  const service = await startService({ directory: join(directory, 'http-service'), adminToken: admin,
    workerToken: worker, port: 0, upstream: 'review-fixture', kernel: async () => borrowed });
  allowedOrigins.add(new URL(service.url).origin);
  const api = (path: string, token: string, method = 'GET', body?: unknown, headers = {}) => fetch(service.url.replace(/\/$/, '') + path, {
    method, headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json', ...headers },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const settled = async (id: string) => {
    for (let i = 0; i < 100; i++) {
      const body = await (await api('/v1/requests/' + id + '?au_id=au-b', worker)).json() as any;
      if (['completed', 'failed', 'interrupted'].includes(body.state)) return body;
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    throw new Error('Controlled request did not settle');
  };
  try {
    assert.equal((await api('/v1/accounts', worker)).status, 403);
    assert.equal((await api('/v1/runtime', worker, 'GET', undefined, { Origin: 'https://review.invalid' })).status, 403);
    const created = await api('/v1/grants', admin, 'POST', { id: 'grant-b', au_id: 'au-b', account_ref: accounts[1], model_ids: ['review-model'] });
    assert.equal(created.status, 201);
    const task: any = input('b', [{ role: 'user', content: 'Public contract' }]);
    task.id = task.run_id = 'review-server-1';
    task.generation = { maxOutputTokens: 21 };
    assert.equal((await api('/v1/requests', admin, 'POST', task)).status, 403);
    const before = requests.length;
    assert.equal((await api('/v1/requests', worker, 'POST', task)).status, 202);
    const result = await settled(task.id);
    assert.equal(result.state, 'completed');
    assert.equal(result.result.message.content, 'done-b');
    assert.equal(requests.length, before + 1);
    assert.equal(requests.at(-1)!.body.max_tokens ?? requests.at(-1)!.body.max_completion_tokens, 21,
      'Public maxOutputTokens must reach upstream maxTokens lowering');
    assert.equal((await api('/v1/requests', worker, 'POST', task)).status, 202);
    assert.equal(requests.length, before + 1);
    assert.equal((await api('/v1/requests/' + task.id + '?au_id=au-a', worker)).status, 404);
    checks.push('HTTP admin/worker/Origin/AU boundaries and durable no-resend replay');
    checks.push('public maxOutputTokens is enforced in actual upstream request');
    mode = 'slow-first';
    task.id = task.run_id = 'review-server-2';
    assert.equal((await api('/v1/requests', worker, 'POST', task)).status, 202);
    for (let i = 0; requests.length < before + 2 && i < 100; i++) await new Promise(resolve => setTimeout(resolve, 5));
    assert.equal(requests.length, before + 2);
    assert.equal((await api('/v1/grants/grant-b/revoke', admin, 'POST', { revision: 1 })).status, 200);
    assert.equal((await settled(task.id)).state, 'interrupted');
    task.id = task.run_id = 'review-server-3';
    assert.equal((await api('/v1/requests', worker, 'POST', task)).status, 403);
    assert.equal(requests.length, before + 2);
    checks.push('grant revocation fences an in-flight stream and rejects later dispatch');
    await assert.rejects(() => startService({ directory: join(directory, 'http-service'), adminToken: admin,
      workerToken: worker, port: 0, upstream: 'review-fixture', kernel: async () => borrowed }));
    checks.push('second service cannot acquire the same owner database lock');
  } finally { await service.close(); }
  mode = 'ordinary';
  await internals.runtime.runPromise(internals.credentials.update(accounts[0], {
    value: Credential.OAuth.make({ type: 'oauth', methodID: Integration.MethodID.make('device'),
      access: 'review-key-a', refresh: 'review-refresh-a', expires: Date.now() - 1000,
      metadata: { server: local.url.origin + '/console', orgID: 'a', orgName: 'a' } }),
  }));
  const postsBeforeRefresh = requests.length;
  await Promise.all([kernel.models(accounts[0]), kernel.models(accounts[0])]);
  assert.equal(refreshRequests, 1);
  assert.equal(requests.length, postsBeforeRefresh);
  const refreshed = await internals.runtime.runPromise(internals.credentials.get(accounts[0]));
  assert.equal(refreshed.value.access, 'review-refreshed-a');
  assert.equal(refreshed.value.refresh, 'review-rotated-refresh-a');
  assert.ok(refreshed.value.expires > Date.now());
  const active = await internals.runtime.runPromise(internals.integrations.connection.active(Integration.ID.make('opencode')));
  assert.equal(active.id, accounts[1]);
  checks.push('parallel explicit-account reads share one upstream OAuth refresh and persist rotated tokens without switching active account');
  console.log(JSON.stringify({ checks, first_event_timeout_enforced: firstEventTimedOut,
    inference_posts: requests.length, oauth_refresh_requests: refreshRequests,
    real_model_calls: 0, providers: 'controlled_loopback_only' }));
} finally {
  await kernel?.close();
  await local.stop(true);
  globalThis.fetch = realFetch;
  assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
  assert.ok(basename(directory).startsWith('union-kernel-review-'));
  rmSync(directory, { recursive: true, force: true });
}
