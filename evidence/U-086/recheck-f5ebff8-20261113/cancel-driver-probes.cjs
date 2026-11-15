const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const { createRequire } = require('node:module');
const { test } = require('node:test');

const candidate = process.env.UNION_REVIEW_CANDIDATE;
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'source-manifest.json'), 'utf8'));
const unavailable = [];
for (const [name, expected] of Object.entries(manifest.files)) {
  if (!candidate || !fs.existsSync(path.join(candidate, name))) unavailable.push({ name, reason: 'missing' });
  else if (createHash('sha256').update(fs.readFileSync(path.join(candidate, name))).digest('hex') !== expected) {
    unavailable.push({ name, reason: 'mismatched' });
  }
}
if (unavailable.length) {
  console.log(JSON.stringify({ status: 'input_unavailable', tests: 0, unavailable }));
  process.exit(2);
}

const filename = path.join(candidate, 'scripts/exit22b_page.cjs');
const source = fs.readFileSync(filename, 'utf8');
const requireCandidate = createRequire(filename);
const readCancelEvidence = requireCandidate('./exit22-cancel-evidence.cjs').readCancelEvidence;
const reference = Object.fromEntries(['organization_id', 'work_id', 'cancel_id', 'principal_id',
  'step_ref', 'attempt_id', 'command_id', 'model_request_id'].map(key => [key, 'original-' + key]));
reference.connection = { id: 'original-connection', revision: 1 };
const response = {
  session: { status: 409, body: { code: 'unsupported_capability' } },
  work: { status: 503, body: { code: 'service_unavailable' } },
  receipt: { status: 404, body: { code: 'receipt_missing' } },
  current: { status: 200, body: { core_protocol: 'core.au.v1' } },
};

function harness(phase, mode) {
  const variable = phase === 'before' ? 'cancelEvidenceBefore' : 'cancelEvidenceAfter';
  const name = `cancel-receipt-${phase}-restart`;
  const start = source.indexOf(`  const ${variable} = `);
  const checkStart = source.indexOf("  check('original ", start);
  const end = source.indexOf('\n', checkStart);
  assert.ok(start >= 0 && checkStart > start && end > checkStart, 'exact driver call and archive exist');
  const segment = source.slice(start, end);
  const files = new Map(), checks = [], calls = [];
  const expected = { id: reference.cancel_id, marker: 'unchanged-receipt-control' };
  const successfulEvidence = { protocol: 'acceptance.cancel-receipt.v1', receipt: expected };
  const originalError = new Error('synthetic loader rejection');
  const page = { evaluate: async () => structuredClone(response) };
  const loader = async (actualPage, actualReference, actualExpected) => {
    calls.push({ page: actualPage, reference: actualReference, expected: actualExpected });
    if (mode === 'reject') throw originalError;
    if (mode === 'http') return readCancelEvidence(actualPage, actualReference, actualExpected);
    return successfulEvidence;
  };
  const context = {
    fs: { writeFileSync: (p, text) => files.set(path.basename(p), JSON.parse(text)) },
    path, output: 'synthetic-output', workId: reference.work_id, page,
    originalCancelReference: reference, cancelOutcome: { receipt: expected },
    cancelEvidenceBefore: { receipt: expected }, check: (...args) => checks.push(args),
    require: name => name === './exit22-cancel-evidence.cjs'
      ? { readCancelEvidence: loader } : requireCandidate(name),
  };
  return {
    files, checks, calls, expected, originalError, name, page, successfulEvidence,
    run: () => vm.runInNewContext(`(async () => {\n${segment}\nreturn ${variable};\n})()`, context,
      { filename: `exact-candidate-cancel-${phase}-segment.cjs` }),
  };
}

for (const phase of ['before', 'after']) {
  test(`${phase}: failure is archived and the original error is rethrown`, async () => {
    const h = harness(phase, 'reject');
    await assert.rejects(h.run, error => error === h.originalError);
    const record = h.files.get(h.name + '-failure.json');
    assert.equal(record.status, 'failed');
    assert.equal(record.work_id, reference.work_id);
    assert.equal(record.dispatch_count, null);
    assert.equal(record.reason, h.originalError.message);
    assert.equal(Object.hasOwn(record, 'receipt'), false);
    assert.equal(Object.hasOwn(record, 'new_dispatches'), false);
    assert.equal(h.files.has(h.name + '.json'), false);
    assert.equal(h.checks.length, 0);
  });

  test(`${phase}: successful loader result and original input binding are preserved`, async () => {
    const h = harness(phase, 'success');
    assert.equal(await h.run(), h.successfulEvidence);
    assert.equal(h.calls.length, 1);
    assert.equal(h.calls[0].page, h.page);
    assert.equal(h.calls[0].reference, reference);
    assert.equal(h.calls[0].expected, h.expected);
    assert.deepEqual(h.files.get(h.name + '.json'), h.successfulEvidence);
    assert.equal(h.files.has(h.name + '-failure.json'), false);
    assert.equal(h.checks.length, 1);
  });

  test(`${phase}: durable failed record preserves all already observed HTTP outcomes`, async () => {
    const h = harness(phase, 'http');
    await assert.rejects(h.run, /session read failed.*HTTP 409/);
    const record = h.files.get(h.name + '-failure.json');
    assert.equal(record.status, 'failed');
    assert.equal(record.dispatch_count, null);
    const diagnostic = JSON.stringify(record);
    const missing = [['session', '409'], ['work', '503'], ['receipt', '404'], ['current', '200']]
      .filter(([name, status]) => !diagnostic.includes(name) || !diagnostic.includes(status))
      .map(([name]) => name);
    assert.deepEqual(missing, [], 'durable diagnostic lost completed reads: ' + missing.join(', '));
  });
}
