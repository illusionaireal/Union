const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const { createRequire } = require('node:module');
const { test } = require('node:test');

const candidate = process.env.UNION_REVIEW_CANDIDATE;
const validation = JSON.parse(fs.readFileSync(path.join(__dirname, 'source-manifest.json'), 'utf8'));
const unavailable = [];
for (const [name, expected] of Object.entries(validation.files)) {
  if (!candidate || !fs.existsSync(path.join(candidate, name))) unavailable.push({ file: name, reason: 'missing' });
  else if (createHash('sha256').update(fs.readFileSync(path.join(candidate, name))).digest('hex') !== expected) {
    unavailable.push({ file: name, reason: 'mismatched' });
  }
}
if (unavailable.length) {
  console.log(JSON.stringify({ status: 'input_unavailable', tests: 0, candidate_imported: false, unavailable }));
  process.exit(2);
}
const filename = path.join(candidate, 'scripts/exit22b_page.cjs');
const source = fs.readFileSync(filename, 'utf8');
const start = source.indexOf("  require('./exit22-replay-observation.cjs').recordReplayObservation({");
const end = source.indexOf('  const cancelEvidenceAfter = ', start);
assert.ok(start >= 0 && end > start, 'exact driver observation segment exists');
const segment = source.slice(start, end);
const requireCandidate = createRequire(filename);
const helpers = requireCandidate('./exit22-restart-evidence.cjs');
const { recordReplayObservation } = requireCandidate('./exit22-replay-observation.cjs');

function body(ids = ['request-original']) {
  return {
    protocol: 'core.work.v1', organization_id: 'au-original', version: 12,
    access: { principal_id: 'principal-original' },
    works: [{
      id: 'work-original', results: [], delivered_result_id: null,
      attempts: [{ id: 'attempt-original' }],
      budget: { max_calls: 3, used: 1, reserved: ids.length - 1 },
      steps: ids.map((id, index) => ({
        step_ref: 'step-' + index, attempt_id: 'attempt-original',
        command_id: 'command-' + index, model_request_id: id,
        status: index ? 'unknown' : 'used', usage: null,
        cost_status: 'unknown', reason: index ? 'interrupted' : 'completed',
        connection: { id: 'connection-original', revision: 1 },
      })),
    }],
  };
}

function harness(before, after) {
  const files = new Map(), checks = [];
  return {
    files, checks,
    deps: {
      fs: { writeFileSync: (name, text) => files.set(path.basename(name), JSON.parse(text)) },
      path, output: 'synthetic-output', before, after, workId: 'work-original',
      check: (label, passed = true) => checks.push({ label, passed }),
    },
  };
}

function executeDriverSegment(h) {
  return vm.runInNewContext(segment, {
    ...h.deps, require: requireCandidate,
    createdReceipt: { organization_id: 'au-original' },
  }, { filename: 'exact-candidate-driver-observation-segment.cjs' });
}

test('control: unchanged valid snapshots reach the actual recorder call site', () => {
  const h = harness(body(), body());
  executeDriverSegment(h);
  assert.equal(h.files.get('replay-observation.json')?.status, 'unchanged');
  assert.equal(h.checks.length, 0);
});

test('a rejected changed snapshot still records the promised failed observation', () => {
  const h = harness(body(), body(['request-original', 'request-new']));
  assert.throws(() => executeDriverSegment(h), /restart preserves every original request fact/);
  assert.ok(h.files.has('replay-observation.json'),
    'original rejection must survive, but must not bypass the failed observation record');
  assert.equal(h.files.get('replay-observation.json').status, 'failed');
});

test('persisted snapshots alone do not establish an actual replay dispatch count', () => {
  const before = body(), after = body();
  const comparison = helpers.compareSnapshots(before, after, 'au-original', 'work-original');
  assert.equal(comparison.no_new_request_identity, true);
  assert.equal(comparison.transport_dispatch_count, null);
  const h = harness(before, after);
  recordReplayObservation(h.deps);
  assert.equal(h.files.get('replay-observation.json').dispatch_count, null,
    'no replay or transport counter was supplied; persisted identity counts cannot certify zero dispatches');
});


test('same-count request identity replacement leaves a failed observation', () => {
  const before = body(), after = body();
  after.works[0].steps[0].model_request_id = 'request-replaced';
  const h = harness(before, after);
  assert.throws(() => executeDriverSegment(h), /restart preserves every original request fact/);
  const record = h.files.get('replay-observation.json');
  assert.ok(record, 'strict rejection must leave a durable observation');
  assert.equal(record.status, 'failed', JSON.stringify(record));
  assert.notEqual(record.persistent_differences, 0);
});

test('same-count result content change leaves a failed observation', () => {
  const before = body(), after = body();
  before.works[0].results = [{id: 'result-original', content: 'original'}];
  after.works[0].results = [{id: 'result-original', content: 'changed'}];
  const h = harness(before, after);
  assert.throws(() => executeDriverSegment(h), /restart preserves every original result fact/);
  const record = h.files.get('replay-observation.json');
  assert.ok(record, 'strict rejection must leave a durable observation');
  assert.equal(record.status, 'failed', JSON.stringify(record));
  assert.notEqual(record.persistent_differences, 0);
});
