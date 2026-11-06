// Persistent, offline-only host for the coordinator's real core HTTP probe.
// Write one JSON object to stdin and close stdin. The three credential files
// must be inside the supplied temporary directory. No credential is printed.
import { readFileSync, realpathSync, statSync } from 'node:fs';
import { isAbsolute, join, relative, resolve } from 'node:path';
import { Kernel, UPSTREAM } from '../../src/kernel';
import { startService } from '../../src/server';

console.log = (...args: unknown[]) => console.error(...args);
console.info = (...args: unknown[]) => console.error(...args);
const config = JSON.parse(await Bun.stdin.text()) as {
  directory: string; admin_token_file: string; worker_token_file: string; api_key_file: string; model_id?: string;
};
const directory = realpathSync(resolve(config.directory));
function credential(file: string) {
  const path = realpathSync(resolve(directory, file)), child = relative(directory, path);
  if (!child || child.startsWith('..') || isAbsolute(child) || !statSync(path).isFile()) throw new Error('fixture_credential_scope_mismatch');
  const value = readFileSync(path, 'utf8').trim();
  if (!/^[\x21-\x7e]{1,4096}$/.test(value)) throw new Error('fixture_credential_invalid');
  return value;
}
const adminToken = credential(config.admin_token_file), workerToken = credential(config.worker_token_file);
const apiKey = credential(config.api_key_file), modelID = config.model_id ?? 'controlled-core-model';
const calls: { body: any; session: string | null }[] = [];
const frame = (value: unknown) => 'data: ' + JSON.stringify(value) + '\n\n';
const signature = 'controlled-core-native-signature';
const provider = Bun.serve({ hostname: '127.0.0.1', port: 0, async fetch(request) {
  const path = new URL(request.url).pathname;
  if (request.method === 'GET' && path === '/__probe/status')
    return Response.json({ inference_posts: calls.length, calls, real_model_calls: 0 });
  if (request.method !== 'POST' || path !== '/v1/chat/completions') return new Response('not_found', { status: 404 });
  if (request.headers.get('authorization') !== 'Bearer ' + apiKey)
    return Response.json({ error: { message: 'controlled_authentication_failed' } }, { status: 401 });
  const body = await request.json() as any;
  const fault = typeof body.model === 'string' && body.model.startsWith(modelID + ':') ? body.model.slice(modelID.length + 1) : null;
  if ((body.model !== modelID && !['auth','missing','limit','unavailable','interrupt'].includes(fault)) || body.stream !== true)
    return Response.json({ error: { message: 'controlled_model_or_stream_mismatch' } }, { status: 400 });
  calls.push({ body, session: request.headers.get('x-opencode-session') });
  const faultStatus = ({ auth: 401, missing: 404, limit: 429, unavailable: 503 } as Record<string, number>)[fault];
  if (faultStatus) return Response.json({ error: { message: 'private provider detail ' + apiKey } }, { status: faultStatus });
  const common = { id: 'controlled-core-' + calls.length, model: modelID, object: 'chat.completion.chunk', created: 1 };
  if (fault === 'interrupt') return new Response(new ReadableStream({ start(controller) {
    controller.enqueue(new TextEncoder().encode(frame({ ...common, choices: [], usage: { prompt_tokens: 37, completion_tokens: 9 } })));
    setTimeout(() => controller.error(new Error('Controlled stream interruption')), 70);
  } }), { headers: { 'content-type': 'text/event-stream' } });
  const toolResult = body.messages.findLast((m: any) => m.role === 'tool');
  let chunks: any[];
  if (toolResult) {
    let material: any;
    try { material = JSON.parse(toolResult.content); } catch { return new Response('controlled_tool_result_not_json', { status: 400 }); }
    if (typeof material.content !== 'string' || typeof material.challenge !== 'string')
      return new Response('controlled_tool_material_missing', { status: 400 });
    chunks = [
      { ...common, choices: [{ index: 0, delta: { role: 'assistant', content: '资料概要：' + material.content + '；校验码：' + material.challenge } }] },
      { ...common, choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] },
    ];
  } else {
    const tool = body.tools?.find((t: any) => t.type === 'function' && t.function.name === 'read_document');
    const documentID = tool?.function.parameters?.properties?.document_id?.enum?.[0];
    if (typeof documentID !== 'string') return new Response('controlled_document_schema_missing', { status: 400 });
    const args = JSON.stringify({ document_id: documentID }), split = Math.floor(args.length / 2);
    chunks = [
      { ...common, choices: [{ index: 0, delta: { role: 'assistant', reasoning_content: '读取已明确选择的资料。' } }] },
      { ...common, choices: [{ index: 0, delta: { tool_calls: [{ index: 0, id: 'core-read-call', type: 'function',
        function: { name: 'read_document', arguments: args.slice(0, split) }, extra_content: { google: { thought_signature: signature } } }] } }] },
      { ...common, choices: [{ index: 0, delta: { tool_calls: [{ index: 0, function: { arguments: args.slice(split) } }] } }] },
      { ...common, choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }] },
    ];
  }
  chunks.push({ ...common, choices: [], usage: { prompt_tokens: 18, completion_tokens: 8, total_tokens: 26,
    prompt_tokens_details: { cached_tokens: 4 }, completion_tokens_details: { reasoning_tokens: 2 } } });
  return new Response(chunks.map(frame).join('') + 'data: [DONE]\n\n', { headers: { 'content-type': 'text/event-stream' } });
} });
const allowed = new Set([provider.url.origin]), realFetch = globalThis.fetch;
globalThis.fetch = ((input: any, init?: any) => {
  const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
  if (!allowed.has(url.origin)) throw new Error('fixture_non_loopback_fetch_forbidden');
  return realFetch(input, init);
}) as typeof fetch;
const service = await startService({ directory: join(directory, 'modeld'), port: 0, adminToken, workerToken,
  upstream: UPSTREAM, kernel: () => Kernel.create(join(directory, 'kernel')) });
allowed.add(new URL(service.url).origin);
let closing = false;
for (const signal of ['SIGINT', 'SIGTERM'] as const) process.on(signal, async () => {
  if (closing) return; closing = true;
  await service.close(); await provider.stop(true); process.exit(0);
});
process.stdout.write(JSON.stringify({ ready: true, modeld_url: service.url, provider_base_url: provider.url.origin + '/v1',
  stats_url: provider.url.origin + '/__probe/status', model_id: modelID, protocol_version: 1, real_model_calls: 0 }) + '\n');
