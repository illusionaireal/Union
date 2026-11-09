// Real modeld + pinned SDK over loopback. Keys and all storage are test-only.
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { Kernel, UPSTREAM } from '../../src/kernel';
import { startService } from '../../src/server';

const directory = mkdtempSync(join(tmpdir(), 'union-secret-boundaries-'));
const ordinaryKey = 'fixture-only-credential-738461923';
const quotedKey = 'fixture-only-"slash\\-credential-738461923';
const scenarios = [
  'ordinary', 'quoted-ordinary', 'safe-prefix', 'plain-input', 'quoted-input',
  'quoted-native-input', 'quoted-tool-input', 'quoted-schema-input', 'plain-output',
  'quoted-output', 'fragmented-text', 'fragmented-quoted-text', 'fragmented-reasoning',
  'fragmented-quoted-reasoning', 'fragmented-tool', 'fragmented-quoted-tool',
  'fragmented-unicode-tool', 'quoted-raw-metadata', 'usage-before-cancel', 'cancel-safe-partial', 'cancel-safe-prefix-id',
  'safe-shadow-reasoning-text', 'shadow-reasoning-text', 'shadow-reasoning-summary', 'shadow-choice-refusal',
  'shadow-choice-reasoning-text-detail', 'shadow-choice-reasoning-summary-detail', 'shadow-choice-custom-tool-input',
];
const keyFor = (scenario: string) => scenario.includes('quoted') ? quotedKey : ordinaryKey;
const outputFor = (scenario: string) => scenario === 'safe-prefix'
  ? ordinaryKey.slice(0, 13) + 'public answer' : 'safe ordinary answer';
const requests: { scenario: string; body: any }[] = [];
const observations: Record<string, unknown> = { external_provider_calls: 0 };
const realFetch = globalThis.fetch;
let service: Awaited<ReturnType<typeof startService>> | undefined;
const frame = (data: unknown) => 'data: ' + JSON.stringify(data) + '\n\n';
const usage = { prompt_tokens: 13, completion_tokens: 7, total_tokens: 20,
  prompt_tokens_details: { cached_tokens: 3 }, completion_tokens_details: { reasoning_tokens: 2 }, cost: 0.004 };
const provider = Bun.serve({ hostname: '127.0.0.1', port: 0, async fetch(request) {
  const path = new URL(request.url).pathname;
  const scenario = path.split('/')[1];
  assert.ok(scenarios.includes(scenario));
  assert.equal(path, '/' + scenario + '/v1/chat/completions');
  assert.equal(request.headers.get('authorization'), 'Bearer ' + keyFor(scenario));
  requests.push({ scenario, body: await request.json() });
  const common = { id: scenario === 'cancel-safe-prefix-id' ? 'fixture-completion-f' : 'fixture-completion', model: 'fixture-model', object: 'chat.completion.chunk', created: 1 };
  const chunk = (delta: unknown) => ({ ...common, choices: [{ index: 0, delta }] });
  if (scenario === 'usage-before-cancel' || scenario.startsWith('cancel-safe')) {
    let timer: ReturnType<typeof setTimeout>;
    return new Response(new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(frame({ ...common, choices: [], usage })));
      controller.enqueue(new TextEncoder().encode(frame(chunk({ role: 'assistant',
        content: scenario.startsWith('cancel-safe') ? 'safe partial evidence' : ordinaryKey.slice(0, 17) }))));
      timer = setTimeout(() => { controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n')); controller.close(); }, 5000);
    }, cancel() { clearTimeout(timer); } }), { headers: { 'content-type': 'text/event-stream' } });
  }
  let chunks: unknown[];
  let finish = 'stop';
  if (scenario.includes('shadow')) {
    const text = scenario === 'safe-shadow-reasoning-text' ? 'ordinary hidden raw reasoning' : keyFor(scenario);
    const parts = [text.slice(0, Math.floor(text.length / 2)), text.slice(Math.floor(text.length / 2))];
    chunks = parts.map((part, index) => {
      const selected = { role: 'assistant', content: index ? '' : outputFor(scenario), reasoning_content: 'safe visible reasoning' };
      if (scenario === 'shadow-reasoning-summary') return chunk({ ...selected,
        reasoning_details: [{ type: 'summary', index: 0, summary: part }] });
      if (!scenario.startsWith('shadow-choice')) return chunk({ ...selected, reasoning_text: part });
      // The SDK selects choice zero. Every raw choice still crosses modeld's
      // confidentiality boundary, including data absent from normalized events.
      const hidden = scenario === 'shadow-choice-refusal' ? { refusal: part }
        : scenario === 'shadow-choice-custom-tool-input'
          ? { tool_calls: [{ index: 0, id: 'hidden-call', custom: { name: 'fixture_tool', input: part } }] }
          : { reasoning_details: [{ id: 'hidden-detail', index: 0,
            ...(scenario === 'shadow-choice-reasoning-text-detail' ? { type: 'reasoning.text', text: part }
              : { type: 'reasoning.summary', summary: part }) }] };
      return { ...common, choices: [{ index: 0, delta: selected }, { index: 1, delta: hidden }] };
    });
  } else if (scenario.includes('fragmented') && scenario.endsWith('tool')) {
    const argument = scenario === 'fragmented-unicode-tool'
      ? '{"document_id":"' + [...ordinaryKey].map(c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0')).join('') + '"}'
      : JSON.stringify({ document_id: keyFor(scenario) });
    const split = Math.floor(argument.length / 2);
    chunks = [
      chunk({ role: 'assistant', tool_calls: [{ index: 0, id: 'fixture-call', type: 'function',
        function: { name: 'read_document', arguments: argument.slice(0, split) } }] }),
      chunk({ tool_calls: [{ index: 0, function: { arguments: argument.slice(split) } }] }),
    ];
    finish = 'tool_calls';
  } else {
    const leaks = scenario.endsWith('output') || scenario.startsWith('fragmented');
    const text = leaks ? keyFor(scenario) : outputFor(scenario);
    const split = Math.floor(text.length / 2);
    const pieces = scenario.startsWith('fragmented') || scenario === 'safe-prefix'
      ? [text.slice(0, split), text.slice(split)] : [text];
    const field = scenario.includes('reasoning') ? 'reasoning_content' : 'content';
    chunks = pieces.map(part => chunk({ role: 'assistant', [field]: part }));
    if (scenario === 'quoted-raw-metadata') (chunks[0] as any).private_echo = { [quotedKey]: quotedKey };
  }
  chunks.push({ ...common, choices: [{ index: 0, delta: {}, finish_reason: finish }] });
  chunks.push({ ...common, choices: [], usage });
  if (scenario === 'ordinary') {
    // Exercise safe streaming across scheduler/network latency, including the
    // final usage frame. This suite does not test a one-second service target.
    let timer: ReturnType<typeof setTimeout>;
    return new Response(new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(frame(chunks[0])));
      timer = setTimeout(() => {
        controller.enqueue(new TextEncoder().encode(chunks.slice(1).map(frame).join('') + 'data: [DONE]\n\n'));
        controller.close();
      }, 1200);
    }, cancel() { clearTimeout(timer); } }), { headers: { 'content-type': 'text/event-stream' } });
  }
  return new Response(chunks.map(frame).join('') + 'data: [DONE]\n\n', { headers: { 'content-type': 'text/event-stream' } });
} });
const allowed = new Set([provider.url.origin]);
globalThis.fetch = ((input: any, init?: any) => {
  const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
  assert.ok(allowed.has(url.origin), 'Non-loopback network is forbidden');
  return realFetch(input, init);
}) as typeof fetch;
const admin = 'secret-fixture-admin-'.padEnd(48, 'a');
const worker = 'secret-fixture-worker-'.padEnd(48, 'w');

function containsKey(value: unknown, key: string): boolean {
  if (typeof value === 'string') {
    if (value.includes(key)) return true;
    try { const decoded = JSON.parse(value); return decoded !== value && containsKey(decoded, key); }
    catch { return false; }
  }
  return !!value && typeof value === 'object' && Object.entries(value).some(([name, item]) => name.includes(key) || containsKey(item, key));
}
function leaks(events: any[], row: unknown, key: string) {
  if (containsKey(row, key) || containsKey(events, key)) return true;
  const native = events.filter(entry => entry.type === 'native_event').map(entry => entry.payload);
  const raw = native.filter(item => item.type === 'raw').map(item => item.data);
  for (const parts of [
    events.filter(entry => entry.type === 'text_delta').map(entry => entry.payload.text),
    native.filter(item => item.type === 'text-delta').map(item => item.text),
    native.filter(item => item.type === 'reasoning-delta').map(item => item.text),
    native.filter(item => item.type === 'tool-input-delta').map(item => item.text),
    raw.map(item => item.choices?.[0]?.delta?.content ?? ''),
    raw.map(item => item.choices?.[0]?.delta?.reasoning_content ?? ''),
    raw.map(item => item.choices?.[0]?.delta?.tool_calls?.[0]?.function?.arguments ?? ''),
  ]) if (containsKey(parts.join(''), key)) return true;
  // Reconstruct each wire projection independently; safe selected content must
  // not hide a credential in another raw reasoning field or ignored choice.
  for (const choice of [0, 1]) {
    for (const field of ['refusal', 'reasoning', 'reasoning_text'])
      if (containsKey(raw.map(item => item.choices?.[choice]?.delta?.[field] ?? '').join(''), key)) return true;
    for (const field of ['text', 'summary'])
      if (containsKey(raw.map(item => item.choices?.[choice]?.delta?.reasoning_details?.[0]?.[field] ?? '').join(''), key)) return true;
    if (containsKey(raw.map(item => item.choices?.[choice]?.delta?.tool_calls?.[0]?.custom?.input ?? '').join(''), key)) return true;
  }
  return false;
}
const knownUsage = (events: any[]) => events.some(entry => entry.type === 'usage' &&
  entry.payload.input_tokens === 13 && entry.payload.output_tokens === 7 && entry.payload.cached_input_tokens === 3 &&
  entry.payload.reasoning_tokens === 2 && JSON.stringify(entry.payload).includes('0.004'));
const safePartial = (events: any[]) => events.some(entry => entry.type === 'text_delta' && entry.payload.text === 'safe partial evidence') &&
  events.some(entry => entry.type === 'native_event' && entry.payload.type === 'raw' &&
    entry.payload.data.choices?.[0]?.delta?.content === 'safe partial evidence');
async function open() {
  service = await startService({ directory: join(directory, 'service'), port: 0, adminToken: admin, workerToken: worker,
    upstream: UPSTREAM, kernel: () => Kernel.create(join(directory, 'kernel')) });
  allowed.add(new URL(service.url).origin);
}

try {
  await open();
  const api = (path: string, method = 'GET', body?: unknown, asAdmin = false) => fetch(new URL(path, service!.url), {
    method, headers: { authorization: 'Bearer ' + (asAdmin ? admin : worker), 'content-type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  for (const scenario of scenarios) {
    const key = keyFor(scenario);
    const saved = { id: randomUUID(), au_id: 'org-' + randomUUID().replaceAll('-', ''), principal_id: randomUUID(),
      name: 'Secret boundary fixture', base_url: provider.url.origin + '/' + scenario + '/v1', api_key: key, model_id: 'fixture-model' };
    const registration = await api('/v1/api-connections', 'POST', saved, true);
    assert.equal(registration.status, 201);
    const receipt = await registration.json() as any;
    const id = randomUUID();
    const input = { id, run_id: id, au_id: saved.au_id, connection_id: randomUUID(), connection_revision: 1,
      grant_ref: receipt.grant_ref, grant_revision: receipt.grant_revision, model_id: saved.model_id,
      messages: [{ role: 'user', content: 'ordinary safe prompt' }] as any[],
      tools: [{ type: 'function', function: { name: 'read_document', description: 'Read a fixture document',
        parameters: { type: 'object', properties: { document_id: { type: 'string' } }, required: ['document_id'] } } }] as any[],
      generation: { maxOutputTokens: 30 }, deadlines: { first_event_ms: 5000, idle_ms: 5000, task_ms: 15000 } };
    if (scenario === 'plain-input' || scenario === 'quoted-input') input.messages[0].content = key;
    if (scenario === 'quoted-native-input') input.messages.push({ role: 'assistant', content: '',
      _native: { au_id: input.au_id, account_ref: service.journal.grant(receipt.grant_ref).account_ref,
        model_id: input.model_id, upstream: UPSTREAM, message: { role: 'assistant', content: [{ type: 'text', text: key }] } } });
    if (scenario === 'quoted-tool-input') input.messages.push({ role: 'assistant', content: '',
      tool_calls: [{ id: 'fixture-prior-call', type: 'function', function: { name: 'read_document', arguments: JSON.stringify({ document_id: key }) } }] });
    if (scenario === 'quoted-schema-input') input.tools[0].function.parameters.properties[key] = { type: 'string' };
    assert.equal((await api('/v1/requests', 'POST', input)).status, 202);
    const history = async () => (await (await api(`/v1/requests/${id}/events?au_id=${saved.au_id}`)).json() as any).events;
    let beforeCancel: any[] = [];
    const cancel = scenario === 'usage-before-cancel' || scenario.startsWith('cancel-safe');
    if (cancel) {
      for (let i = 0; i < 45; i++) {
        beforeCancel = await history();
        if (knownUsage(beforeCancel) && (!scenario.startsWith('cancel-safe') || safePartial(beforeCancel))) break;
        await Bun.sleep(10);
      }
      assert.equal((await api(`/v1/requests/${id}/cancel?au_id=${saved.au_id}`, 'POST')).status, 202);
    }
    let row: any;
    const settleBy = performance.now() + 20000;
    while (performance.now() < settleBy) {
      row = await (await api(`/v1/requests/${id}?au_id=${saved.au_id}`)).json();
      if (['completed', 'failed', 'interrupted'].includes(row.state)) break;
      await Bun.sleep(10);
    }
    assert.ok(['completed', 'failed', 'interrupted'].includes(row.state), 'The bounded fixture did not settle');
    const events = await history();
    const sent = requests.filter(entry => entry.scenario === scenario);
    let reopened = false;
    if (scenario.startsWith('cancel-safe')) {
      await service!.close(); service = undefined;
      await open();
      reopened = JSON.stringify(await history()) === JSON.stringify(events);
    }
    observations[scenario] = { state: row.state, error: row.error, provider_posts: sent.length,
      input_leaks: sent.some(entry => containsKey(entry.body, key)), output_leaks: leaks(events, row, key),
      result_absent: row.result === null, expected_output: row.result?.message.content === outputFor(scenario),
      native_events_preserved: events.some(entry => entry.type === 'native_event' && entry.payload.type === 'raw') &&
        events.some(entry => entry.type === 'native_event' && entry.payload.type === 'text-delta') &&
        events.filter(entry => entry.type === 'text_delta').map(entry => entry.payload.text).join('') === outputFor(scenario),
      usage_preserved: cancel ? knownUsage(events) :
        row.result?.usage.input_tokens === 13 && row.result?.usage.output_tokens === 7 && row.result?.usage.modeld_usage.cost === 0.004,
      ...(cancel ? { usage_before_cancel: knownUsage(beforeCancel),
        unverified_content_private: !containsKey(beforeCancel, ordinaryKey.slice(0, 17)) } : {}),
      ...(scenario.startsWith('cancel-safe') ? { partial_before_cancel: safePartial(beforeCancel),
        partial_after_cancel: safePartial(events), reopen_preserves_events: reopened } : {}),
    };
  }
  console.log(JSON.stringify(observations));
} finally {
  await service?.close(); await provider.stop(true); globalThis.fetch = realFetch;
  assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
  assert.ok(basename(directory).startsWith('union-secret-boundaries-'));
  rmSync(directory, { recursive: true, force: true });
}
