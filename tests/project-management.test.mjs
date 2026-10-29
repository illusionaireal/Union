import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { validateProject, buildViews, checkViews, flowSummary } from '../scripts/project-management.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'union-management-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  writeFileSync(join(root, 'proof.md'), 'Evidence');
  const task = (id, status = 'ready') => ({ id, title: id, priority: 'P0', milestone: 'G1', module: 'org', status, owner: null, role: '工程', acceptance: '真实交付', dependencies: [], blocker: null, started_at: null, updated_at: '2026-10-28', completion: null });
  const data = { schema_version: 1, updated_at: '2026-10-28', wip_limit: 2,
    modules: [{ id: 'org', name: '组织', implemented: '代码', validation: 'V1 受控', gap: '真实交付', evidence: ['proof.md'] }],
    milestones: [{ id: 'G1', name: '成立', outcome: '团队真实成立', status: 'pending', evidence: [] }], tasks: [task('U-001'), task('U-002')] };
  return { root, data };
}
test('rejects missing owners at start and unfinished dependencies, but permits honest unassigned backlog', t => {
  const { root, data } = fixture(t);
  validateProject(data, root);
  Object.assign(data.tasks[0], { status: 'doing', started_at: '2026-10-28' });
  assert.throws(() => validateProject(data, root), /owner/);
  data.tasks[0].owner = 'external-engineer';
  data.tasks[0].dependencies = ['U-002'];
  assert.throws(() => validateProject(data, root), /unfinished dependency/);
});
test('completion requires scope, reviewer and existing evidence, and does not promote milestones', t => {
  const { root, data } = fixture(t);
  Object.assign(data.tasks[0], { status: 'done', owner: 'external-engineer', started_at: '2026-10-28' });
  assert.throws(() => validateProject(data, root), /completion/);
  data.tasks[0].completion = { scope: 'controlled', reviewer: 'external-engineer (self-review)', evidence: ['missing.md'], note: 'Controlled only' };
  assert.throws(() => validateProject(data, root), /missing evidence/);
  data.tasks[0].completion.evidence = ['proof.md'];
  validateProject(data, root);
  assert.equal(data.milestones[0].status, 'pending');
});
test('rejects duplicate IDs, unknown references and dependency cycles', t => {
  const { root, data } = fixture(t);
  const copy = structuredClone(data); copy.tasks[1].id = 'U-001';
  assert.throws(() => validateProject(copy, root), /duplicate/);
  data.tasks[0].dependencies = ['U-404'];
  assert.throws(() => validateProject(data, root), /unknown dependency/);
  data.tasks[0].dependencies = ['U-002']; data.tasks[1].dependencies = ['U-001'];
  data.tasks.forEach(x => x.status = 'backlog');
  assert.throws(() => validateProject(data, root), /cycle/);
});
test('blocked work needs an unblock action; already-started blocked work counts toward WIP', t => {
  const { root, data } = fixture(t);
  const a = data.tasks[0]; a.status = 'blocked';
  assert.throws(() => validateProject(data, root), /blocker/);
  a.blocker = { reason: 'Host absent', action: 'Supply host', owner: null }; validateProject(data, root);
  Object.assign(a, { started_at: '2026-10-28', owner: 'engineer' });
  Object.assign(data.tasks[1], { status: 'review', started_at: '2026-10-28', owner: 'engineer' });
  data.wip_limit = 1;
  assert.throws(() => validateProject(data, root), /WIP/);
});
test('rejects evidence outside repository, invalid scope and malformed dates', t => {
  const { root, data } = fixture(t);
  data.modules[0].evidence = ['../secret.md'];
  assert.throws(() => validateProject(data, root), /repository-relative/);
  data.modules[0].evidence = ['proof.md']; data.tasks[0].updated_at = '2026-02-30';
  assert.throws(() => validateProject(data, root), /date/);
});
test('deterministic generated views reject stale output and preserve surrounding narrative', t => {
  const { root, data } = fixture(t);
  const project = '# Project\nCustom narrative\n' + ['modules', 'milestones', 'tasks'].map(x => `<!-- management:${x}:start -->\nold\n<!-- management:${x}:end -->`).join('\n');
  const views = buildViews(data, project);
  assert.match(views['PROJECT.md'], /Custom narrative/);
  assert.match(views['TASKS.md'], /待认领/);
  for (const [file, content] of Object.entries(views)) writeFileSync(join(root, file), content);
  checkViews(views, root);
  writeFileSync(join(root, 'TASKS.md'), 'stale');
  assert.throws(() => checkViews(views, root), /stale/);
  assert.deepEqual(buildViews(data, views['PROJECT.md']), views);
  assert.throws(() => buildViews(data, '# no markers'), /marker/);
});
test('flow summary keeps empty live evidence distinct from completion counts', t => {
  const { data } = fixture(t);
  const s = flowSummary(data);
  assert.equal(s.wip, 0); assert.equal(s.ready, 2); assert.equal(s.done, 0);
  assert.equal(s.realAccepted, 0);
});
test('milestone acceptance and task scope cannot be asserted without their review metadata', t => {
  const { root, data } = fixture(t);
  data.milestones[0].status = 'accepted'; data.milestones[0].evidence = ['proof.md'];
  assert.throws(() => validateProject(data, root), /reviewer and date/);
  data.milestones[0].status = 'pending';
  Object.assign(data.tasks[0], { status: 'done', owner: 'engineer', started_at: '2026-10-28', completion: { scope: 'production-ish', reviewer: 'engineer', evidence: ['proof.md'], note: 'Unrecognized claim' } });
  assert.throws(() => validateProject(data, root), /completion/);
});
