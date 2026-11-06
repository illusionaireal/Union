// Uses only new temporary credentials and actual loopback HTTP. Never reads a
// host account or contacts an external provider; guard every fetch origin.
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { Kernel, UPSTREAM } from '../../src/kernel';
import { startService } from '../../src/server';

const directory = mkdtempSync(join(tmpdir(), 'union-api-kernel-'));
const realFetch = globalThis.fetch;
const secret = 'api-loopback-only-credential-478963123';
const requests: any[] = [];
let configRequests = 0;
let mode: 'ordinary' | 'reject' | 'echo-secret' | 'usage-before-cancel' | 'half-json' | 'length-prefix' = 'ordinary';
let service: Awaited<ReturnType<typeof startService>> | undefined;
const signature = 'controlled-native-thought-signature';
const reasoning = 'Read the supplied document once.';
const frame = (data: unknown) => 'data: ' + JSON.stringify(data) + '\n\n';
const provider = Bun.serve({ hostname: '127.0.0.1', port: 0, async fetch(request) {
  const url = new URL(request.url);
  if (url.pathname !== '/v1/chat/completions') { configRequests++; return new Response('unexpected endpoint', { status: 500 }); }
  assert.equal(request.headers.get('authorization'), 'Bearer ' + secret);
  const body = await request.json() as any;
  assert.equal(body.model, 'controlled-api-model'); assert.equal(body.stream, true);
  assert.ok(request.headers.get('x-opencode-session'));
  assert.equal(body.max_tokens ?? body.max_completion_tokens, 43);
  requests.push(body);
  if (mode === 'reject') return Response.json({ error: { message: 'controlled unavailable' } }, { status: 503 });
  const common = { id: 'api-controlled-completion', model: 'controlled-api-model', object: 'chat.completion.chunk', created: 1 };
  if (mode === 'usage-before-cancel') {
    let timer: ReturnType<typeof setTimeout>;
    return new Response(new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(frame({ ...common, choices: [], usage: {
        prompt_tokens: 18, completion_tokens: 8, total_tokens: 26, cost: 0.0012 } })));
      timer = setTimeout(() => { controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n')); controller.close(); }, 5000);
    }, cancel() { clearTimeout(timer); } }), { headers: { 'content-type': 'text/event-stream' } });
  }
  if (mode === 'half-json' || mode === 'length-prefix') {
    const delta = mode === 'half-json' ? { tool_calls: [{ index: 0, id: 'half-call', type: 'function',
      function: { name: 'read_document', arguments: '{"document_id":' } }] } : { content: 'safe unfinished a' };
    const items = [{ ...common, choices: [{ index: 0, delta: { role: 'assistant', ...delta } }] },
      { ...common, choices: [{ index: 0, delta: {}, finish_reason: mode === 'half-json' ? 'tool_calls' : 'length' }] },
      { ...common, choices: [], usage: { prompt_tokens: 18, completion_tokens: 8, total_tokens: 26 } }];
    return new Response(items.map(frame).join('') + 'data: [DONE]\n\n', { headers: { 'content-type': 'text/event-stream' } });
  }
  const tool = body.messages.find((message: any) => message.role === 'tool');
  const chunks = tool || mode === 'echo-secret' ? [
    { ...common, choices: [{ index: 0, delta: { role: 'assistant', content: mode === 'echo-secret' ? secret : 'Verified ' + tool.content } }] },
    { ...common, choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] },
  ] : [
    { ...common, choices: [{ index: 0, delta: { role: 'assistant', reasoning_content: reasoning } }] },
    { ...common, choices: [{ index: 0, delta: { tool_calls: [{ index: 0, id: 'read-call', type: 'function',
      function: { name: 'read_document', arguments: '{"document_id":' }, extra_content: { google: { thought_signature: signature } } }] } }] },
    { ...common, choices: [{ index: 0, delta: { tool_calls: [{ index: 0, function: { arguments: '"document-a"}' } }] } }] },
    { ...common, choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }] },
  ];
  chunks.push({ ...common, choices: [], usage: { prompt_tokens: 18, completion_tokens: 8, total_tokens: 26,
    prompt_tokens_details: { cached_tokens: 4 }, completion_tokens_details: { reasoning_tokens: 2 }, cost: 0.0012 } } as any);
  return new Response(chunks.map(frame).join('') + 'data: [DONE]\n\n', { headers: { 'content-type': 'text/event-stream' } });
} });
const allowed = new Set([provider.url.origin]);
globalThis.fetch = ((input: any, init?: any) => {
  const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
  assert.ok(allowed.has(url.origin), 'Non-loopback fetch forbidden in API profile probe');
  return realFetch(input, init);
}) as typeof fetch;
const admin = 'api-kernel-admin-'.padEnd(48, 'a'), worker = 'api-kernel-worker-'.padEnd(48, 'w');
try {
  service = await startService({ directory: join(directory, 'service'), port: 0, adminToken: admin, workerToken: worker,
    upstream: UPSTREAM, kernel: () => Kernel.create(join(directory, 'kernel')) });
  allowed.add(new URL(service.url).origin);
  const api = (path: string, method = 'GET', body?: unknown, asAdmin = false) => fetch(new URL(path, service!.url), {
    method, headers: { authorization: 'Bearer ' + (asAdmin ? admin : worker), 'content-type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const saved = { id: 'save-api-' + randomUUID(), au_id: 'org-' + randomUUID().replaceAll('-', ''), principal_id: randomUUID(), name: 'Loopback API profile',
    base_url: provider.url.origin + '/v1', api_key: secret, model_id: 'controlled-api-model' };
  const registration = await api('/v1/api-connections', 'POST', saved, true);
  assert.equal(registration.status, 201);
  const receipt = await registration.json() as any;
  assert.equal(requests.length, 0, 'Saving is never a model probe');
  assert.equal(configRequests, 0, 'Saving never refreshes a Go account');
  const task = (messages: any[]) => {
    const id = randomUUID();
    return { id, run_id: id, au_id: saved.au_id, connection_id: randomUUID(), connection_revision: 1,
      grant_ref: receipt.grant_ref, grant_revision: receipt.grant_revision, model_id: saved.model_id, messages,
      tools: [{ type: 'function', function: { name: 'read_document', description: 'Read the selected controlled document',
        parameters: { type: 'object', properties: { document_id: { type: 'string' } }, required: ['document_id'], additionalProperties: false } } }],
      generation: { maxOutputTokens: 43 }, deadlines: { first_event_ms: 1000, idle_ms: 1000, task_ms: 5000 } };
  };
  const settle = async (input: ReturnType<typeof task>) => {
    for (let i = 0; i < 200; i++) {
      const response = await api(`/v1/requests/${input.id}?au_id=${input.au_id}`);
      assert.equal(response.status, 200);
      const row = await response.json() as any;
      if (['completed', 'failed', 'interrupted'].includes(row.state)) return row;
      await Bun.sleep(10);
    }
    throw new Error('API request failed to settle');
  };
  const submit = async (input: ReturnType<typeof task>) => {
    const response = await api('/v1/requests', 'POST', input);
    assert.equal(response.status, 202);
    return settle(input);
  };
  const first = task([{ role: 'user', content: 'Read document-a with read_document.' }]);
  const firstRow = await submit(first);
  assert.equal(firstRow.state, 'completed', 'API profile must use the native kernel without a Go account');
  assert.equal(firstRow.action_authorized, true);
  assert.equal(requests.length, 1);
  assert.deepEqual(requests[0].tools[0].function.parameters, first.tools[0].function.parameters);
  const native = firstRow.result.message;
  assert.equal(native.tool_calls[0].function.arguments, '{"document_id":"document-a"}');
  assert.equal(native._native.au_id, saved.au_id); assert.equal(native._native.upstream, UPSTREAM);
  assert.equal(firstRow.result.usage.input_tokens, 18); assert.equal(firstRow.result.usage.cached_input_tokens, 4);
  assert.equal(firstRow.result.usage.reasoning_tokens, 2); assert.equal(firstRow.result.usage.modeld_usage.cost, 0.0012);
  const toolResult = 'document-a contents; controlled-check-code: 49173';
  const followup = task([...first.messages, JSON.parse(JSON.stringify(native)), { role: 'tool', tool_call_id: 'read-call', content: toolResult }]);
  const secondRow = await submit(followup);
  assert.equal(secondRow.state, 'completed'); assert.ok(secondRow.result.message.content.includes('49173'));
  const assistantReplay = requests[1].messages.find((m: any) => m.role === 'assistant');
  assert.equal(assistantReplay.reasoning_content, reasoning);
  assert.equal(assistantReplay.tool_calls[0].extra_content.google.thought_signature, signature);
  assert.equal(requests[1].messages.find((m: any) => m.role === 'tool').tool_call_id, 'read-call');
  assert.equal(requests[1].messages.find((m: any) => m.role === 'tool').content, toolResult);
  assert.equal((await api('/v1/requests', 'POST', followup)).status, 202);
  assert.equal(requests.length, 2, 'An identical request cannot start another inference');
  const replayEvents = await (await api(`/v1/requests/${first.id}/events?au_id=${saved.au_id}`)).json() as any;
  assert.ok(replayEvents.events.some((e: any) => e.type === 'native_event' && e.payload.type === 'raw'));
  assert.ok(!JSON.stringify(replayEvents).includes(secret));
  for (const changed of [
    { au_id: randomUUID() }, { account_ref: 'other-api-account' }, { model_id: 'other-model' }, { upstream: 'different-upstream' },
  ]) {
    const copied = JSON.parse(JSON.stringify(native)); Object.assign(copied._native, changed);
    const rejected = await submit(task([...first.messages, copied]));
    assert.equal(rejected.state, 'interrupted'); assert.equal(rejected.error, 'native_context_scope_mismatch');
  }
  assert.equal(requests.length, 2, 'Wrong native context must be rejected before provider HTTP');
  const mismatchedCall = JSON.parse(JSON.stringify(native));
  mismatchedCall.tool_calls[0].function.arguments = '{"document_id":"different-document"}';
  const mismatched = await submit(task([...first.messages, mismatchedCall]));
  assert.equal(mismatched.state, 'interrupted'); assert.equal(mismatched.error, 'native_tool_calls_mismatch');
  const orphan = await submit(task([...first.messages, native, { role: 'tool', tool_call_id: 'other-call', name: 'read_document', content: 'orphan' }]));
  assert.equal(orphan.state, 'interrupted'); assert.equal(orphan.error, 'tool_result_pair_mismatch');
  assert.equal(requests.length, 2, 'A native call and its public projection/result must remain paired');
  const media = task([{ role: 'user', content: [{ type: 'image_url', image_url: { url: 'https://media.invalid/a.png' } }] }]);
  const nativeMedia = JSON.parse(JSON.stringify(native));
  nativeMedia._native.message.content.push({ type: 'media', mediaType: 'image/png', url: 'https://media.invalid/b.png' });
  const hosted = task(first.messages); hosted.tools = [{ type: 'web_search' }] as any;
  const badFunction = task(first.messages); (badFunction.tools[0] as any).function.extra_headers = { x: 'unsupported' };
  for (const unsupported of [media, task([...first.messages, nativeMedia]), hosted, badFunction]) {
    const rejected = await submit(unsupported);
    assert.equal(rejected.state, 'interrupted'); assert.match(rejected.error, /unsupported_|hosted_tools_forbidden/);
  }
  assert.equal(requests.length, 2, 'Unsupported capability must not silently lower or contact media hosts');
  for (const withNative of [true, false]) {
    const custom = JSON.parse(JSON.stringify(native)); custom.tool_calls[0].type = 'custom';
    if (!withNative) delete custom._native;
    const before = requests.length, row = await submit(task([...first.messages, custom]));
    assert.equal(row.state, 'interrupted', 'Unsupported public tool types must be refused');
    assert.equal(row.error, 'unsupported_tool_call'); assert.equal(requests.length, before);
  }
  const privateInput = await submit(task([{ role: 'user', content: secret }]));
  assert.equal(privateInput.state, 'interrupted'); assert.equal(privateInput.error, 'credential_in_model_content');
  assert.equal(requests.length, 2, 'Credential cannot enter the model message');
  const encodedSecret = [...secret].map(c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0')).join('');
  const encodedInput = await submit(task([{ role: 'assistant', content: '', tool_calls: [{ id: 'encoded-secret', type: 'function',
    function: { name: 'read_document', arguments: '{"document_id":"' + encodedSecret + '"}' } }] }]));
  assert.equal(encodedInput.state, 'interrupted'); assert.equal(encodedInput.error, 'credential_in_model_content');
  assert.equal(requests.length, 2, 'JSON argument decoding must not bypass the credential guard');
  mode = 'reject';
  const failed = await submit(task(first.messages));
  assert.equal(failed.state, 'interrupted'); assert.equal(requests.length, 3, 'Provider failures are single attempt');
  mode = 'echo-secret';
  const echoedTask = task(first.messages), echoed = await submit(echoedTask);
  assert.equal(echoed.state, 'interrupted'); assert.equal(echoed.error, 'credential_in_model_content');
  assert.equal(echoed.result, null); assert.ok(!JSON.stringify(echoed).includes(secret));
  const echoedEvents = await (await api(`/v1/requests/${echoedTask.id}/events?au_id=${saved.au_id}`)).json();
  assert.ok(!JSON.stringify(echoedEvents).includes(secret));
  assert.equal(requests.length, 4);
  mode = 'usage-before-cancel';
  const cancelledTask = task(first.messages);
  assert.equal((await api('/v1/requests', 'POST', cancelledTask)).status, 202);
  let observedUsage = false;
  for (let i = 0; i < 100; i++) {
    const history = await (await api(`/v1/requests/${cancelledTask.id}/events?au_id=${saved.au_id}`)).json();
    if (JSON.stringify(history).includes('0.0012')) { observedUsage = true; break; }
    await Bun.sleep(10);
  }
  assert.ok(observedUsage, 'Actual streamed usage must be durable before stopping the request');
  assert.equal((await api(`/v1/requests/${cancelledTask.id}/cancel?au_id=${saved.au_id}`, 'POST')).status, 202);
  const cancelled = await settle(cancelledTask);
  assert.equal(cancelled.state, 'interrupted'); assert.equal(cancelled.action_authorized, false);
  assert.equal(cancelled.result, null, 'No complete result was received before transport cancellation');
  const cancelledEvents = await (await api(`/v1/requests/${cancelledTask.id}/events?au_id=${saved.au_id}`)).json();
  assert.ok(JSON.stringify(cancelledEvents).includes('0.0012'), 'Cancellation cannot erase known raw usage');
  assert.equal(requests.length, 5);
  for (const incomplete of ['half-json', 'length-prefix'] as const) {
    mode = incomplete;
    const next = task(first.messages), row = await submit(next);
    assert.equal(row.state, 'interrupted', 'Incomplete model output cannot be a completed result');
    assert.equal(row.result, null); assert.equal(row.error, 'incomplete_model_result');
    const history = await (await api(`/v1/requests/${next.id}/events?au_id=${saved.au_id}`)).json() as any;
    assert.ok(history.events.some((event: any) => event.type === 'usage' && event.payload.input_tokens === 18));
    if (incomplete === 'length-prefix') assert.ok(history.events.some((event: any) => event.type === 'text_delta' && event.payload.text === 'safe unfinished a'));
  }
  assert.equal(requests.length, 7);
  assert.equal(configRequests, 0);
  console.log(JSON.stringify({ real_model_calls: 0, account_config_requests: configRequests, inference_posts: requests.length,
    tool_roundtrip: true, native_scope_and_signature: true, unsupported_capabilities_rejected: true, no_automatic_retry: true,
    known_usage_survives_cancel: true }));
} finally {
  await service?.close(); await provider.stop(true); globalThis.fetch = realFetch;
  assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
  assert.ok(basename(directory).startsWith('union-api-kernel-'));
  rmSync(directory, { recursive: true, force: true });
}
