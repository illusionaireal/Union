import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import {
  validateProject, claimTask, releaseTask, moveTask, claimState, boardView,
  serializeLedger, mutateLedger, withLedgerLock, readLedger,
} from '../scripts/project-management.mjs';

const T0 = Date.parse('2026-11-04T02:00:00Z');

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'union-board-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(join(root, 'management'), { recursive: true });
  writeFileSync(join(root, 'proof.md'), 'Evidence');
  const task = (id, status = 'ready', extra = {}) => ({
    id, title: id, priority: 'P0', milestone: 'G1', module: 'org', status, owner: null, role: '工程',
    acceptance: '真实交付', dependencies: [], blocker: null, started_at: null, updated_at: '2026-11-04', completion: null, ...extra,
  });
  const data = {
    schema_version: 1, updated_at: '2026-11-04', wip_limit: 2,
    modules: [{ id: 'org', name: '组织', implemented: '代码', validation: 'V1 受控', gap: '真实交付', evidence: ['proof.md'] }],
    milestones: [{ id: 'G1', name: '成立', outcome: '团队真实成立', status: 'pending', evidence: [] }],
    tasks: [task('U-001'), task('U-002')],
  };
  return { root, data };
}

test('claim writes a lease and enters doing, and blocks a second harness until the lease expires', t => {
  const { root, data } = fixture(t);
  const task = claimTask(data, { id: 'U-001', actor: 'codex/gpt-5', now: T0 });
  assert.equal(task.status, 'doing');
  assert.equal(task.owner, 'codex/gpt-5');
  assert.equal(task.claim.actor, 'codex/gpt-5');
  assert.equal(claimState(task, T0), 'held');
  validateProject(data, root);

  assert.throws(() => claimTask(data, { id: 'U-001', actor: 'opencode/glm-4.6', now: T0 + 60_000 }), /held by codex/);

  const takenOver = claimTask(data, { id: 'U-001', actor: 'opencode/glm-4.6', now: T0 + 3 * 60 * 60 * 1000 + 1 });
  assert.equal(takenOver.owner, 'opencode/glm-4.6');
  validateProject(data, root);
});

test('claim refuses cards that are not ready and refuses to exceed the WIP limit', t => {
  const { root, data } = fixture(t);
  data.tasks[1].status = 'backlog';
  assert.throws(() => claimTask(data, { id: 'U-002', actor: 'a', now: T0 }), /only ready/);

  data.tasks[1].status = 'doing';
  Object.assign(data.tasks[1], { owner: 'x', started_at: '2026-11-04', claim: { actor: 'x', at: '2026-11-04T01:00:00.000Z', lease_until: '2026-11-05T01:00:00.000Z' } });
  data.wip_limit = 1;
  assert.throws(() => claimTask(data, { id: 'U-001', actor: 'a', now: T0 }), /above the limit 1/);
  assert.equal(data.tasks[0].status, 'ready');
  validateProject(data, root);
});

test('claim requires a real actor and refuses unknown cards', t => {
  const { data } = fixture(t);
  assert.throws(() => claimTask(data, { id: 'U-001', actor: '  ', now: T0 }), /actor/);
  assert.throws(() => claimTask(data, { id: 'U-404', actor: 'a', now: T0 }), /unknown task/);
});

test('release only gives back an unstarted claim and clears the lease', t => {
  const { root, data } = fixture(t);
  claimTask(data, { id: 'U-001', actor: 'codex', now: T0 });
  assert.throws(() => releaseTask(data, { id: 'U-001', actor: 'opencode', now: T0 }), /held by codex/);
  const released = releaseTask(data, { id: 'U-001', actor: 'codex', now: T0 });
  assert.equal(released.status, 'ready');
  assert.equal(released.owner, null);
  assert.equal(released.claim, null);
  validateProject(data, root);
});

test('done needs scope, reviewer, note and real evidence; completion clears the lease', t => {
  const { root, data } = fixture(t);
  claimTask(data, { id: 'U-001', actor: 'codex', now: T0 });
  assert.throws(() => moveTask(data, { id: 'U-001', status: 'done', actor: 'codex', now: T0 }), /completion needs/);
  moveTask(data, {
    id: 'U-001', status: 'done', actor: 'codex', now: T0,
    completion: { scope: 'controlled', reviewer: 'codex', note: '受控', evidence: ['missing.md'] },
  });
  assert.throws(() => validateProject(data, root), /missing evidence/);

  const done = moveTask(data, {
    id: 'U-001', status: 'done', actor: 'codex', now: T0,
    completion: { scope: 'controlled', reviewer: 'codex（自检）', note: '受控验证通过', evidence: ['proof.md'] },
  });
  assert.equal(done.status, 'done');
  assert.equal(done.claim, null);
  validateProject(data, root);
  assert.equal(data.milestones[0].status, 'pending', 'done 卡不会自动推进里程碑');
});

test('a non-holder cannot move a card, and force cannot smuggle a foreign lease silently', t => {
  const { root, data } = fixture(t);
  claimTask(data, { id: 'U-001', actor: 'codex', now: T0 });
  assert.throws(() => moveTask(data, { id: 'U-001', status: 'review', actor: 'opencode', now: T0 }), /held by codex/);
  const forced = moveTask(data, { id: 'U-001', status: 'review', actor: 'opencode', force: true, now: T0, note: 'codex 失联，代为转入待验收' });
  assert.equal(forced.status, 'review');
  assert.equal(forced.claim.actor, 'codex', 'force 不偷租约，只绕过状态限制');
  validateProject(data, root);
});

test('blocked needs a reason and an unblock action, and started work cannot hide back in ready', t => {
  const { root, data } = fixture(t);
  assert.throws(() => moveTask(data, { id: 'U-001', status: 'blocked', actor: 'codex', now: T0 }), /blocker.reason/);
  const blocked = moveTask(data, {
    id: 'U-001', status: 'blocked', actor: 'codex', now: T0,
    blocker: { reason: '缺少真实 Docker 主机', action: '准备主机与镜像', owner: null },
  });
  assert.equal(blocked.blocker.owner, null);

  claimTask(data, { id: 'U-002', actor: 'codex', now: T0 });
  assert.equal(data.tasks[1].status, 'doing');
  assert.throws(() => moveTask(data, { id: 'U-002', status: 'ready', actor: 'codex', now: T0 }), /已经开工/);
  const forced = moveTask(data, { id: 'U-002', status: 'ready', actor: 'codex', force: true, now: T0, note: '拆分后重排，放弃已开始的占用' });
  assert.equal(forced.owner, null);
  assert.equal(forced.history.at(-1).to, 'ready');
  validateProject(data, root);
});

test('board view exposes columns, the ready queue and lease state', t => {
  const { data } = fixture(t);
  claimTask(data, { id: 'U-001', actor: 'codex', now: T0 });
  const view = boardView(data, T0);
  assert.deepEqual(view.columns.doing, ['U-001']);
  assert.deepEqual(view.columns.ready, ['U-002']);
  assert.deepEqual(view.next, ['U-002']);
  assert.equal(view.counts.wip, 1);
  assert.equal(view.in_flight[0].claim_state, 'held');
});

test('serializeLedger keeps the ledger byte format (4 spaces, CRLF, trailing newline)', t => {
  const { data } = fixture(t);
  const text = serializeLedger(data);
  assert.match(text, /^\{\r\n {4}"schema_version": 1,/);
  assert.ok(text.endsWith('}\r\n'));
  assert.deepEqual(JSON.parse(text), data);
});

test('the ledger lock refuses a second writer, then recovers after the holder finishes', async t => {
  const { root } = fixture(t);
  await assert.rejects(
    withLedgerLock(root, () => withLedgerLock(root, () => 'inner', { timeoutMs: 100 }), { timeoutMs: 1000 }),
    /ledger busy/,
  );
  const value = await withLedgerLock(root, () => 'after');
  assert.equal(value, 'after');
  assert.equal(existsSync(join(root, 'management/.ledger.lock')), false);
});

test('mutateLedger writes the ledger and rebuilds both generated views in one locked step', async t => {
  const { root, data } = fixture(t);
  writeFileSync(join(root, 'management/project.json'), serializeLedger(data));
  const project = ['# Project', 'narrative', '<!-- management:modules:start -->', '<!-- management:modules:end -->',
    '<!-- management:milestones:start -->', '<!-- management:milestones:end -->',
    '<!-- management:tasks:start -->', '<!-- management:tasks:end -->'].join('\n');
  writeFileSync(join(root, 'PROJECT.md'), project);

  await mutateLedger(root, current => claimTask(current, { id: 'U-001', actor: 'codex', now: T0 }));
  const stored = readLedger(root);
  assert.equal(stored.tasks[0].status, 'doing');
  assert.equal(stored.tasks[0].claim.actor, 'codex');
  assert.match(readFileSync(join(root, 'TASKS.md'), 'utf8'), /进行中/);
  assert.equal(existsSync(join(root, 'management/.ledger.lock')), false);

  await mutateLedger(root, current => {
    assert.equal(current.tasks[0].claim.actor, 'codex');
    return releaseTask(current, { id: 'U-001', actor: 'codex', now: T0 });
  });
  assert.equal(readLedger(root).tasks[0].status, 'ready');
});

test('a rejected mutation leaves the ledger untouched', async t => {
  const { root, data } = fixture(t);
  writeFileSync(join(root, 'management/project.json'), serializeLedger(data));
  writeFileSync(join(root, 'PROJECT.md'), ['<!-- management:modules:start -->', '<!-- management:modules:end -->',
    '<!-- management:milestones:start -->', '<!-- management:milestones:end -->',
    '<!-- management:tasks:start -->', '<!-- management:tasks:end -->'].join('\n'));
  const before = readFileSync(join(root, 'management/project.json'), 'utf8');
  await assert.rejects(mutateLedger(root, current => claimTask(current, { id: 'U-404', actor: 'codex', now: T0 })), /unknown task/);
  assert.equal(readFileSync(join(root, 'management/project.json'), 'utf8'), before);
  assert.equal(existsSync(join(root, 'TASKS.md')), false);
});

test('a doing card with no live lease can be claimed, but a live lease still blocks it', t => {
  const { root, data } = fixture(t);
  Object.assign(data.tasks[0], { status: 'doing', owner: 'legacy-member', started_at: '2026-11-02' });
  const claimed = claimTask(data, { id: 'U-001', actor: 'codex/gpt-5', now: T0 });
  assert.equal(claimed.claim.actor, 'codex/gpt-5');
  assert.equal(claimed.status, 'doing', '补领租约不会重启开工日期');
  assert.equal(claimed.started_at, '2026-11-02');
  validateProject(data, root);

  assert.throws(() => claimTask(data, { id: 'U-001', actor: 'opencode/glm-4.6', now: T0 + 1000 }), /held by codex/);
});

test('a view failure cannot leave a half-written ledger behind', async t => {
  const { root, data } = fixture(t);
  writeFileSync(join(root, 'management/project.json'), serializeLedger(data));
  writeFileSync(join(root, 'PROJECT.md'), '# no management markers here');
  const before = readFileSync(join(root, 'management/project.json'), 'utf8');
  await assert.rejects(mutateLedger(root, current => claimTask(current, { id: 'U-001', actor: 'codex', now: T0 })), /marker/);
  assert.equal(readFileSync(join(root, 'management/project.json'), 'utf8'), before, '视图算不出来时主账不能已经写掉');
  assert.equal(existsSync(join(root, 'TASKS.md')), false);
});

test('a forced transition must record why and keeps the reason in the task history', t => {
  const { root, data } = fixture(t);
  claimTask(data, { id: 'U-001', actor: 'codex', now: T0 });
  assert.throws(() => moveTask(data, { id: 'U-001', status: 'review', actor: 'opencode', force: true, now: T0 }), /must record why/);

  const moved = moveTask(data, {
    id: 'U-001', status: 'review', actor: 'opencode', force: true, now: T0,
    note: 'codex 会话断开，接手复核',
  });
  assert.equal(moved.status, 'review');
  assert.equal(moved.history.length, 1);
  assert.deepEqual(
    { from: moved.history[0].from, to: moved.history[0].to, actor: moved.history[0].actor },
    { from: 'doing', to: 'review', actor: 'opencode' },
  );
  validateProject(data, root);

  assert.throws(() => moveTask(data, {
    id: 'U-001', status: 'ready', actor: 'opencode', force: true, now: T0, note: '',
  }), /must record why/);
});

test('a failed view write keeps the ledger unchanged, so the state stays recoverable', async t => {
  const { root, data } = fixture(t);
  writeFileSync(join(root, 'management/project.json'), serializeLedger(data));
  writeFileSync(join(root, 'PROJECT.md'), ['<!-- management:modules:start -->', '<!-- management:modules:end -->',
    '<!-- management:milestones:start -->', '<!-- management:milestones:end -->',
    '<!-- management:tasks:start -->', '<!-- management:tasks:end -->'].join('\n'));
  mkdirSync(join(root, 'TASKS.md')); // 让派生视图写不进去
  const before = readFileSync(join(root, 'management/project.json'), 'utf8');
  await assert.rejects(mutateLedger(root, current => claimTask(current, { id: 'U-001', actor: 'codex', now: T0 })));
  assert.equal(readFileSync(join(root, 'management/project.json'), 'utf8'), before, '主账必须最后写，写失败时仍是旧值');
});

test('the MCP server refuses local operational writes even with force', async t => {
  const { root, data } = fixture(t);
  Object.assign(data.tasks[0], {
    status: 'doing', owner: 'codex', started_at: '2026-11-04',
    claim: { actor: 'codex', at: '2026-11-04T01:00:00.000Z', lease_until: '2026-11-05T01:00:00.000Z' },
  });
  writeFileSync(join(root, 'management/project.json'), serializeLedger(data));
  writeFileSync(join(root, 'PROJECT.md'), ['<!-- management:modules:start -->', '<!-- management:modules:end -->',
    '<!-- management:milestones:start -->', '<!-- management:milestones:end -->',
    '<!-- management:tasks:start -->', '<!-- management:tasks:end -->'].join('\n'));

  const requests = [
    { jsonrpc: '2.0', id: 1, method: 'initialize', params: {} },
    {
      jsonrpc: '2.0', id: 2, method: 'tools/call',
      params: {
        name: 'union_card_record',
        arguments: { id: 'U-001', actor: 'opencode/glm-4.6', scope: 'controlled', reviewer: 'opencode/glm-4.6', evidence: ['proof.md'], note: 'codex 失联，接手完成', force: true },
      },
    },
  ];
  const lines = await runMcpServer(root, requests);
  const response = lines.find(line => line.id === 2);
  assert.ok(response, 'MCP 必须有应答');
  assert.equal(response.result.isError, true);
  assert.match(response.result.content[0].text, /local history is read-only/);
  assert.equal(readLedger(root).tasks[0].status, 'doing');

});

function runMcpServer(root, requests) {
  return new Promise((resolvePromise, rejectPromise) => {
    const script = join(import.meta.dirname, '..', 'scripts', 'union-board-mcp.mjs');
    const child = spawn(process.execPath, [script], { env: { ...process.env, UNION_REPO_ROOT: root, UNION_BOARD_SOURCE: 'local' } });
    let out = '';
    child.stdout.on('data', chunk => { out += chunk; });
    child.stderr.on('data', () => {});
    child.on('error', rejectPromise);
    child.on('close', () => resolvePromise(out.split('\n').filter(Boolean).map(line => JSON.parse(line))));
    child.stdin.end(`${requests.map(request => JSON.stringify(request)).join('\n')}\n`);
  });
}
