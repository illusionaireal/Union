// Actual pinned SDK + authenticated modeld + loopback Responses. No real accounts.
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { Kernel, UPSTREAM } from '../../src/kernel';
import { startService } from '../../src/server';

const directory = mkdtempSync(join(tmpdir(), 'union-responses-'));
const secret = 'responses-fixture-credential-639817', encrypted = 'fixture-encrypted-reasoning';
const posts: any[] = [];
let rejected = 0, service: Awaited<ReturnType<typeof startService>> | undefined;
const realFetch = globalThis.fetch;
const frame = (data: any) => 'event: ' + data.type + '\ndata: ' + JSON.stringify(data) + '\n\n';
const provider = Bun.serve({ hostname: '127.0.0.1', port: 0, async fetch(request) {
  assert.equal(new URL(request.url).pathname, '/v1/responses');
  assert.equal(request.headers.get('authorization'), 'Bearer ' + secret);
  const body = await request.json() as any;
  posts.push(body);
  assert.equal(body.model, 'gpt-6-astra'); assert.equal(body.reasoning.effort, 'max');
  assert.equal(body.max_output_tokens, 512); assert.equal(body.stream, true); assert.equal(body.store, false);
  if (rejected) return Response.json({ error: { message: 'private echo ' + secret } }, { status: rejected });
  const tool = body.input.find((item: any) => item.type === 'function_call_output');
  const reasoning = { id: 'rs_fixture', type: 'reasoning', encrypted_content: encrypted, summary: [] };
  const call = { id: 'fc_fixture', type: 'function_call', call_id: 'read-call', name: 'read_document',
    arguments: '{"document_id":"document-a"}', status: 'completed' };
  const message = { id: 'msg_fixture', type: 'message', role: 'assistant', status: 'completed',
    content: [{ type: 'output_text', text: 'Verified ' + (tool?.output ?? ''), annotations: [] }] };
  if (tool) {
    assert.equal(tool.call_id, 'read-call');
    assert.ok(body.input.some((item: any) => item.type === 'reasoning' && item.encrypted_content === encrypted));
    assert.ok(body.input.some((item: any) => item.type === 'function_call' && item.call_id === 'read-call'));
  }
  const output = tool ? [message] : [reasoning, call];
  const frames = [{ type: 'response.created', response: { id: 'resp_fixture', status: 'in_progress' } }];
  for (const [index, item] of output.entries()) {
    frames.push({ type: 'response.output_item.added', output_index: index, item } as any);
    frames.push({ type: 'response.output_item.done', output_index: index, item } as any);
  }
  frames.push({ type: 'response.completed', response: { id: 'resp_fixture', status: 'completed', output,
    usage: { input_tokens: tool ? 49 : 17, output_tokens: tool ? 13 : 8,
      input_tokens_details: { cached_tokens: 3 }, output_tokens_details: { reasoning_tokens: 2 }, total_tokens: tool ? 62 : 25 } } } as any);
  return new Response(frames.map(frame).join(''), { headers: { 'content-type': 'text/event-stream' } });
} });
const allowed = new Set([provider.url.origin]);
globalThis.fetch = ((input: any, init?: any) => {
  const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
  assert.ok(allowed.has(url.origin), 'Only isolated loopback origins are allowed');
  return realFetch(input, init);
}) as typeof fetch;
try {
  const admin = 'responses-admin-fixture-'.padEnd(48, 'a'), worker = 'responses-worker-fixture-'.padEnd(48, 'w');
  service = await startService({ directory, port: 0, adminToken: admin, workerToken: worker, upstream: UPSTREAM,
    kernel: () => Kernel.create(join(directory, 'kernel')) });
  allowed.add(new URL(service.url).origin);
  const api = (path: string, method = 'GET', body?: any, managing = false) => fetch(new URL(path, service!.url), {
    method, headers: { authorization: 'Bearer ' + (managing ? admin : worker), 'content-type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const input = { id: randomUUID(), au_id: randomUUID(), principal_id: randomUUID(), name: 'Responses fixture',
    base_url: provider.url.origin + '/v1', api_key: secret, model_id: 'gpt-6-astra', wire_api: 'responses', reasoning_effort: 'max' };
  const saved = await api('/v1/api-connections', 'POST', input, true);
  assert.equal(saved.status, 201); const receipt = await saved.json() as any;
  assert.equal(posts.length, 0);
  const task = (messages: any[]) => {
    const id = randomUUID();
    return { id, run_id: id, au_id: input.au_id, connection_id: randomUUID(), connection_revision: 1,
      grant_ref: receipt.grant_ref, grant_revision: 1, model_id: input.model_id, messages,
      tools: [{ type: 'function', function: { name: 'read_document', parameters: { type: 'object', properties: {
        document_id: { type: 'string' } }, required: ['document_id'], additionalProperties: false } } }],
      generation: { maxOutputTokens: 512 }, deadlines: { first_event_ms: 1000, idle_ms: 1000, task_ms: 5000 } };
  };
  const submit = async (body: ReturnType<typeof task>) => {
    assert.equal((await api('/v1/requests', 'POST', body)).status, 202);
    for (let i = 0; i < 200; i++) {
      const row = await (await api(`/v1/requests/${body.id}?au_id=${body.au_id}`)).json() as any;
      if (['completed', 'interrupted', 'failed'].includes(row.state)) return row;
      await Bun.sleep(10);
    }
    throw new Error('Responses request did not settle');
  };
  const first = task([{ role: 'user', content: 'Read document-a with read_document.' }]);
  const initial = await submit(first);
  assert.equal(initial.state, 'completed', JSON.stringify(initial));
  assert.equal(initial.result.usage.input_tokens, 17);
  const native = initial.result.message;
  assert.equal(native.tool_calls[0].function.arguments, '{"document_id":"document-a"}');
  const second = task([...first.messages, native, { role: 'tool', tool_call_id: 'read-call', content: 'document-a check-code: 73951' }]);
  const final = await submit(second);
  assert.equal(final.state, 'completed'); assert.ok(final.result.message.content.includes('73951'));
  assert.equal(final.result.usage.input_tokens, 49); assert.equal(final.result.usage.reasoning_tokens, 2);
  assert.equal(posts.length, 2);
  const events = await (await api(`/v1/requests/${first.id}/events?au_id=${first.au_id}`)).json() as any;
  assert.ok(events.events.some((e: any) => e.type === 'usage' && e.payload.input_tokens === 17));
  for (const [status, code] of [[401, 'provider_authentication_failed'], [403, 'provider_authentication_failed'],
    [404, 'model_not_found'], [429, 'provider_rate_limited'], [503, 'provider_unavailable']] as const) {
    rejected = status;
    const before = posts.length, row = await submit(task(first.messages));
    assert.equal(row.state, 'interrupted'); assert.equal(row.error, code); assert.equal(posts.length, before + 1);
    assert.ok(!JSON.stringify(row).includes(secret));
  }
  console.log(JSON.stringify({ real_model_calls: 0, roundtrip: true, native_replay: true, separate_usage: true,
    exact_settings: true, safe_errors: true, no_retry: true, inference_posts: posts.length }));
} finally {
  await service?.close(); await provider.stop(true); globalThis.fetch = realFetch;
  assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
  assert.ok(basename(directory).startsWith('union-responses-'));
  rmSync(directory, { recursive: true, force: true });
}
