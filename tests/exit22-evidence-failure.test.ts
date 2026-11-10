import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

// A failed read must leave a record behind, never only an unhandled rejection.
const requireHelper = createRequire(new URL('../scripts/exit22-evidence-failure.cjs', import.meta.url));
const { recordEvidenceFailure, readWithFailureRecord } = requireHelper('../scripts/exit22-evidence-failure.cjs');

function harness() {
  const files = new Map<string, any>();
  return {
    files,
    deps: {
      fs: { writeFileSync: (name: string, text: string) => files.set(name.split('/').at(-1)!, JSON.parse(text)) },
      path: { join: (...parts: string[]) => parts.join('/') },
      output: 'out',
      workId: 'work-original',
    },
  };
}

test('a failed cancel-evidence read is written to its own failure record', () => {
  const { deps, files } = harness();
  recordEvidenceFailure({ ...deps, name: 'cancel-receipt-before-restart',
    error: new Error('original cancel evidence session read failed: /api/session HTTP 409 unsupported_capability') });
  const record = files.get('cancel-receipt-before-restart-failure.json');
  assert.equal(record.status, 'failed');
  assert.equal(record.name, 'cancel-receipt-before-restart');
  assert.equal(record.work_id, 'work-original');
  assert.match(record.reason, /HTTP 409/);
  assert.match(record.reason, /unsupported_capability/);
  assert.ok(typeof record.recorded_at === 'string' && record.recorded_at.length > 0);
});

test('the failure record never claims a receipt or a zero dispatch count', () => {
  const { deps, files } = harness();
  recordEvidenceFailure({ ...deps, name: 'cancel-receipt-after-restart', error: new Error('boom') });
  const record = files.get('cancel-receipt-after-restart-failure.json');
  assert.ok(!('receipt' in record));
  assert.ok(!('new_dispatches' in record));
  assert.equal(record.dispatch_count ?? null, null);
});

test('the wrapper records a failure and rethrows the original error', async () => {
  const { deps, files } = harness();
  const original = new Error('original cancel evidence work read failed: /api/v1/work HTTP 409 incompatible_state');
  await assert.rejects(
    () => readWithFailureRecord({ ...deps, name: 'cancel-receipt-before-restart',
      reference: 'ref', expected: 'receipt',
      loader: async () => { throw original; } }),
    (error: any) => error === original,
  );
  const record = files.get('cancel-receipt-before-restart-failure.json');
  assert.equal(record.status, 'failed');
  assert.match(record.reason, /HTTP 409/);
});

test('the wrapper returns the loader result untouched on success', async () => {
  const { deps, files } = harness();
  const value = await readWithFailureRecord({ ...deps, name: 'cancel-receipt-before-restart',
    reference: 'ref', expected: 'receipt', loader: async (args: any) => ({ ok: args.reference }) });
  assert.deepEqual(value, { ok: 'ref' });
  assert.equal(files.size, 0);
});