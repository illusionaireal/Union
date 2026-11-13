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
const reference = Object.fromEntries(['organization_id', 'work_id', 'cancel_id', 'principal_id', 'step_ref', 'attempt_id', 'command_id', 'model_request_id'].map(k => [k, 'synthetic-' + k]));
reference.connection = { id: 'synthetic-connection', revision: 1 };
const receipt = { id: reference.cancel_id, organization_id: reference.organization_id, actor_principal_id: reference.principal_id, kind: 'cancel_step', status: 'succeeded', effect: 'applied', model_request_id: reference.model_request_id, cancel_accepted: true, step: { step_ref: reference.step_ref, model_request_id: reference.model_request_id }, cancel_connection: reference.connection, base_version: 1, version: 2, message: 'synthetic accepted', delivery: { cancel_accepted: true, message: 'synthetic accepted' } };
function payload() {
  const session = { status: 200, body: { core_protocol: 'core.au.v1', principal_id: reference.principal_id, service_instance: 'synthetic-service' } };
  return { session: structuredClone(session), current: structuredClone(session), work: { status: 200, body: { protocol: 'core.work.v1', organization_id: reference.organization_id, access: { principal_id: reference.principal_id }, version: 2, works: [{ id: reference.work_id, steps: [{ step_ref: reference.step_ref, attempt_id: reference.attempt_id, command_id: reference.command_id, model_request_id: reference.model_request_id, connection: reference.connection }] }] } }, receipt: { status: 200, body: { receipt: structuredClone(receipt) } } };
}
function harness(phase, response) {
  const variable = phase === 'before' ? 'cancelEvidenceBefore' : 'cancelEvidenceAfter';
  const name = `cancel-receipt-${phase}-restart`;
  const start = source.indexOf(`  const ${variable} = `);
  const checkStart = source.indexOf("  check('original ", start);
  const end = source.indexOf('\n', checkStart);
  assert.ok(start >= 0 && checkStart > start && end > checkStart);
  const files = new Map(), checks = [], calls = [];
  const page = { evaluate: async () => structuredClone(response) };
  let originalError;
  const context = { fs: { writeFileSync: (p, text) => files.set(path.basename(p), JSON.parse(text)) }, path, output: 'synthetic-output', workId: reference.work_id, page, originalCancelReference: reference, cancelOutcome: { receipt }, cancelEvidenceBefore: { receipt }, check: (...args) => checks.push(args), require: name => name === './exit22-cancel-evidence.cjs' ? { readCancelEvidence: async (...args) => { calls.push(args); try { return await readCancelEvidence(...args); } catch(error) { originalError = error; throw error; } } } : requireCandidate(name) };
  return { files, name, checks, calls, originalError: () => originalError, run: () => vm.runInNewContext(`(async () => {\n${source.slice(start, end)}\nreturn ${variable};\n})()`, context) };
}
for (const phase of ['before','after']) {
  test(`${phase}: all-200 original identity and receipt remain valid`, async () => {
    const h = harness(phase, payload());
    const result = await h.run();
    assert.deepEqual(result.receipt, receipt);
    assert.equal(h.files.has(h.name + '-failure.json'), false);
    assert.equal(h.files.has(h.name + '.json'), true);
    assert.equal(h.calls.length, 1);
    assert.equal(h.checks.length, 1);
  });
  for (const mismatch of ['principal','receipt']) {
    test(`${phase}: completed HTTP outcomes survive strict ${mismatch} rejection`, async () => {
      const response = payload();
      if (mismatch === 'principal') response.current.body.principal_id = 'synthetic-other-principal';
      else response.receipt.body.receipt.id = 'synthetic-other-receipt';
      const h = harness(phase, response);
      await assert.rejects(h.run, error => error === h.originalError() && /original cancel (principal|receipt id)/.test(error.message));
      const record = h.files.get(h.name + '-failure.json');
      assert.equal(record.status, 'failed');
      assert.equal(record.dispatch_count, null);
      assert.equal(Object.hasOwn(record, 'receipt'), false);
      assert.equal(h.files.has(h.name + '.json'), false);
      assert.equal(h.checks.length, 0);
      assert.deepEqual(record.http, { session: { route: '/api/session', status: 200 }, work: { route: '/api/v1/work', status: 200 }, receipt: { route: '/api/v1/governance/receipts', status: 200 }, current: { route: '/api/session', status: 200 } }, 'completed route diagnostics must survive semantic rejection');
    });
  }
}
