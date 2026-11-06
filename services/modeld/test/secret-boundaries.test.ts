import { beforeAll, expect, test } from 'bun:test';
import { join } from 'node:path';
import { CredentialContent } from '../src/credential-content';

let observed: Record<string, any>;
beforeAll(async () => {
  const child = Bun.spawn([process.execPath, join(import.meta.dir, 'fixtures/secret-boundaries-probe.ts')], {
    stdout: 'pipe', stderr: 'pipe',
  });
  const [stdout, stderr, code] = await Promise.all([
    new Response(child.stdout).text(), new Response(child.stderr).text(), child.exited,
  ]);
  if (code) throw new Error(stdout + stderr);
  observed = JSON.parse(stdout.trim().split('\n').at(-1)!);
  expect(observed.external_provider_calls).toBe(0);
}, 30000);

for (const scenario of ['ordinary', 'quoted-ordinary', 'safe-prefix', 'safe-shadow-reasoning-text']) {
  test(`credential protection preserves ${scenario} output, original events and usage`, () => {
    expect(observed[scenario]).toMatchObject({
      state: 'completed', error: null, provider_posts: 1, input_leaks: false, output_leaks: false,
      expected_output: true, native_events_preserved: true, usage_preserved: true,
    });
  });
}

for (const scenario of ['plain-input', 'quoted-input', 'quoted-native-input', 'quoted-tool-input', 'quoted-schema-input']) {
  test(`${scenario} is rejected before provider dispatch without exposing the credential`, () => {
    expect(observed[scenario]).toMatchObject({
      state: 'interrupted', error: 'credential_in_model_content', provider_posts: 0,
      input_leaks: false, output_leaks: false, result_absent: true,
    });
  });
}

for (const scenario of [
  'plain-output', 'quoted-output', 'fragmented-text', 'fragmented-quoted-text',
  'fragmented-reasoning', 'fragmented-quoted-reasoning', 'fragmented-tool',
  'fragmented-quoted-tool', 'fragmented-unicode-tool', 'quoted-raw-metadata',
  'shadow-reasoning-text', 'shadow-reasoning-summary', 'shadow-choice-refusal',
  'shadow-choice-reasoning-text-detail', 'shadow-choice-reasoning-summary-detail',
  'shadow-choice-custom-tool-input',
]) {
  test(`${scenario} never reaches results or recombined public/native/raw events`, () => {
    expect(observed[scenario]).toMatchObject({
      state: 'interrupted', error: 'credential_in_model_content', provider_posts: 1,
      input_leaks: false, output_leaks: false, result_absent: true,
    });
  });
}

test('known usage is published while credential fragments remain private, and survives cancellation', () => {
  expect(observed['usage-before-cancel']).toMatchObject({
    state: 'interrupted', provider_posts: 1, result_absent: true, output_leaks: false,
    usage_before_cancel: true, usage_preserved: true, unverified_content_private: true,
  });
});

for (const scenario of ['cancel-safe-partial', 'cancel-safe-prefix-id']) test(`${scenario} content streams before cancellation and survives reopen`, () => {
  expect(observed[scenario]).toMatchObject({
    state: 'interrupted', provider_posts: 1, result_absent: true, output_leaks: false,
    usage_before_cancel: true, usage_preserved: true, partial_before_cancel: true,
    partial_after_cancel: true, reopen_preserves_events: true,
  });
});

const boundaryKey = 'raw-boundary-fixture-credential-298614';
const firstHalf = boundaryKey.slice(0, 18), secondHalf = boundaryKey.slice(18);
const chatRaw = (delta: unknown) => ({ type: 'raw', data: { choices: [{ index: 0, delta }] } });
const detailRaw = (detail: unknown) => chatRaw({ reasoning_details: [detail] });
const responseRaw = (type: string, delta: string) => ({ type: 'raw', data: { type,
  item_id: 'fixture-item', output_index: 0, content_index: 0, summary_index: 0, delta } });
const rawFragments: [string, (text: string) => any][] = [
  ['Chat refusal', text => chatRaw({ refusal: text })],
  ['Chat reasoning_text', text => chatRaw({ reasoning_text: text })],
  ['Chat reasoning.text detail', text => detailRaw({ type: 'reasoning.text', id: 'a', index: 0, text })],
  ['Chat reasoning.summary detail', summary => detailRaw({ type: 'reasoning.summary', id: 'a', index: 0, summary })],
  ['Chat summary detail', summary => detailRaw({ type: 'summary', index: 0, summary })],
  ['Chat custom tool input', input => chatRaw({ tool_calls: [{ index: 0, id: 'a', custom: { name: 'fixture_tool', input } }] })],
  ['Responses refusal delta', text => responseRaw('response.refusal.delta', text)],
  ['Responses reasoning delta', text => responseRaw('response.reasoning.delta', text)],
];
for (const [name, fragment] of rawFragments) test(`${name} holds a raw credential prefix before any normalized event`, () => {
  const boundary = new CredentialContent(boundaryKey);
  expect(boundary.observe(fragment(firstHalf))).toBe(false);
  expect(boundary.pending).toBe(true);
  expect(boundary.observe(fragment(secondHalf))).toBe(true);
});

test('reasoning detail continuation keeps its identity when later fragments add metadata', () => {
  const boundary = new CredentialContent(boundaryKey);
  expect(boundary.observe(detailRaw({ type: 'reasoning.text', text: firstHalf }))).toBe(false);
  expect(boundary.pending).toBe(true);
  expect(boundary.observe(detailRaw({ type: 'reasoning.text', text: secondHalf,
    id: 'late-id', index: 1, format: 'fixture', signature: 'late-signature' }))).toBe(true);
});

for (const [name, changed] of [
  ['id', { id: 'b' }], ['index', { index: 1 }], ['format', { format: 'b' }],
  ['signature', { signature: 'b' }], ['type', { type: 'reasoning.summary', summary: secondHalf }],
] as const) test(`reasoning details with a different ${name} are not combined`, () => {
  const boundary = new CredentialContent(boundaryKey);
  const identity = { type: 'reasoning.text', id: 'a', index: 0, format: 'a', signature: 'a' };
  expect(boundary.observe(detailRaw({ ...identity, text: firstHalf }))).toBe(false);
  expect(boundary.observe(detailRaw({ ...identity, text: secondHalf, ...changed }))).toBe(false);
});

for (const [name, closing] of [
  ['a different detail identity', { type: 'reasoning.text', id: 'b', text: 'safe continuing text' }],
  ['an opaque detail', { type: 'reasoning.encrypted', id: 'a', data: 'atomic metadata-r' }],
] as const) test(`${name} closes the previous raw prefix without delaying later safe content`, () => {
  const boundary = new CredentialContent(boundaryKey);
  expect(boundary.observe(detailRaw({ type: 'reasoning.text', id: 'a', text: firstHalf }))).toBe(false);
  expect(boundary.pending).toBe(true);
  expect(boundary.observe(detailRaw(closing))).toBe(false);
  expect(boundary.pending).toBe(false);
});

test('detail runs closed within one raw frame do not leave an obsolete pending prefix', () => {
  const boundary = new CredentialContent(boundaryKey);
  expect(boundary.observe(chatRaw({ reasoning_details: [
    { type: 'reasoning.text', id: 'a', text: firstHalf },
    { type: 'reasoning.text', id: 'b', text: 'safe continuing text' },
  ] }))).toBe(false);
  expect(boundary.pending).toBe(false);
});

for (const [name, frame] of [
  ['function name', (name: string) => chatRaw({ tool_calls: [{ index: 0, id: 'a', function: { name } }] })],
  ['encrypted detail', (encrypted: string) => detailRaw({ type: 'encrypted', index: 0, encrypted })],
  ['encrypted data', (data: string) => detailRaw({ type: 'reasoning.encrypted', id: 'a', data })],
] as [string, (text: string) => any][]) test(`${name} stays atomic and cannot hold safe streaming content pending`, () => {
  const boundary = new CredentialContent(boundaryKey);
  expect(boundary.observe(frame(firstHalf))).toBe(false);
  expect(boundary.pending).toBe(false);
  expect(boundary.observe(frame(secondHalf))).toBe(false);
  expect(boundary.pending).toBe(false);
});
