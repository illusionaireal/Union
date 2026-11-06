import assert from 'node:assert/strict';
import { existsSync, readFileSync, writeFileSync, statSync, openSync, closeSync, rmSync } from 'node:fs';
import { resolve, relative, isAbsolute, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const states = { backlog: '待依赖', candidate: '候选', ready: '就绪', doing: '进行中', blocked: '阻塞', review: '待验收', done: '完成' };
const scopes = ['documentation', 'controlled', 'real', 'sustained'];
const text = x => typeof x === 'string' && x.trim().length > 0;
const date = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && Number.isFinite(Date.parse(x)) && new Date(x).toISOString().slice(0, 10) === x;
const instant = x => typeof x === 'string' && Number.isFinite(Date.parse(x));
const cell = x => String(x ?? '待认领').replaceAll('|', '\\|').replaceAll('\n', ' ');
const links = paths => paths.map(p => `[${p}](${p})`).join('、') || '—';
function evidence(paths, root, required = false) {
  assert(Array.isArray(paths), 'evidence must be an array');
  assert(!required || paths.length > 0, 'missing evidence');
  for (const p of paths) {
    assert(text(p) && !isAbsolute(p) && !p.includes('\\') && !p.includes(':') && !p.split('/').includes('..'), 'evidence must be repository-relative');
    assert(existsSync(resolve(root, p)) && statSync(resolve(root, p)).isFile(), `missing evidence: ${p}`);
  }
}
function index(items, label) {
  assert(Array.isArray(items) && items.length > 0, `${label} must be a nonempty array`);
  const map = new Map();
  for (const item of items) {
    assert(item && text(item.id), `${label} id required`);
    assert(!map.has(item.id), `duplicate ${label} id: ${item.id}`);
    map.set(item.id, item);
  }
  return map;
}
export function flowSummary(data) {
  const counts = Object.fromEntries(Object.keys(states).map(s => [s, data.tasks.filter(t => t.status === s).length]));
  return { ...counts, wip: data.tasks.filter(t => t.started_at && t.status !== 'done').length,
    realAccepted: data.tasks.filter(t => t.status === 'done' && ['real', 'sustained'].includes(t.completion?.scope)).length };
}
export function validateProject(data, root) {
  assert(data.schema_version === 1, 'unsupported schema_version');
  assert(date(data.updated_at), 'invalid project date');
  assert(Number.isInteger(data.wip_limit) && data.wip_limit > 0, 'invalid wip_limit');
  const modules = index(data.modules, 'module'), milestones = index(data.milestones, 'milestone'), tasks = index(data.tasks, 'task');
  for (const m of modules.values()) {
    for (const field of ['name', 'implemented', 'validation', 'gap']) assert(text(m[field]), `${m.id} missing ${field}`);
    evidence(m.evidence, root, true);
  }
  for (const m of milestones.values()) {
    assert(text(m.name) && text(m.outcome), `${m.id} missing milestone outcome`);
    assert(['pending', 'baseline', 'accepted'].includes(m.status), `${m.id} invalid milestone status`);
    evidence(m.evidence, root, m.status !== 'pending');
    if (m.status === 'accepted') assert(text(m.reviewer) && date(m.accepted_at), `${m.id} acceptance needs reviewer and date`);
  }
  for (const t of tasks.values()) {
    assert(/^U-\d{3}$/.test(t.id), `invalid task id ${t.id}`);
    for (const field of ['title', 'role', 'acceptance']) assert(text(t[field]), `${t.id} missing ${field}`);
    assert(['P0', 'P1', 'P2'].includes(t.priority), `${t.id} invalid priority`);
    assert(Object.hasOwn(states, t.status), `${t.id} invalid status`);
    assert(modules.has(t.module) && milestones.has(t.milestone), `${t.id} unknown module or milestone`);
    assert(date(t.updated_at) && t.updated_at <= data.updated_at, `${t.id} invalid update date`);
    assert(t.started_at === null || (date(t.started_at) && t.started_at <= t.updated_at), `${t.id} invalid start date`);
    assert(t.owner === null || text(t.owner), `${t.id} invalid owner`);
    if (['doing', 'review', 'done'].includes(t.status) || t.started_at) assert(text(t.owner) && date(t.started_at), `${t.id} started work needs owner and start date`);
    assert(!t.started_at || !['candidate', 'ready', 'backlog'].includes(t.status), `${t.id} started work cannot hide in backlog`);
    assert(Array.isArray(t.dependencies) && new Set(t.dependencies).size === t.dependencies.length, `${t.id} invalid dependencies`);
    for (const dep of t.dependencies) assert(tasks.has(dep), `${t.id} unknown dependency ${dep}`);
    if (t.status === 'blocked') {
      assert(t.blocker && text(t.blocker.reason) && text(t.blocker.action) && (t.blocker.owner === null || text(t.blocker.owner)), `${t.id} blocker needs reason, action and owner (null if unassigned)`);
    } else assert(t.blocker === null, `${t.id} blocker must be null outside blocked state`);
    if (t.status === 'done') {
      assert(t.completion && scopes.includes(t.completion.scope) && text(t.completion.reviewer) && text(t.completion.note), `${t.id} completion needs scope, reviewer and note`);
      evidence(t.completion.evidence, root, true);
    } else assert(t.completion === null, `${t.id} unfinished task cannot claim completion`);
    const lease = t.claim ?? null;
    assert(lease === null || (text(lease.actor) && instant(lease.at) && instant(lease.lease_until) && Date.parse(lease.lease_until) > Date.parse(lease.at)), `${t.id} invalid claim lease`);
    assert(lease === null || ['doing', 'blocked', 'review'].includes(t.status), `${t.id} claim requires a started state`);
    if (t.history !== undefined) {
      assert(Array.isArray(t.history) && t.history.length > 0, `${t.id} invalid history`);
      for (const entry of t.history) {
        assert(entry && instant(entry.at) && text(entry.actor) && Object.hasOwn(states, entry.from)
          && Object.hasOwn(states, entry.to) && text(entry.note), `${t.id} invalid history entry`);
      }
    }
  }
  const active = new Set(), visited = new Set();
  function visit(id) {
    assert(!active.has(id), `dependency cycle at ${id}`);
    if (visited.has(id)) return;
    active.add(id); for (const dep of tasks.get(id).dependencies) visit(dep);
    active.delete(id); visited.add(id);
  }
  for (const t of tasks.values()) visit(t.id);
  for (const t of tasks.values()) if (['ready', 'doing', 'review', 'done'].includes(t.status)) {
    for (const dep of t.dependencies) assert(tasks.get(dep).status === 'done', `${t.id} unfinished dependency ${dep}`);
  }
  assert(flowSummary(data).wip <= data.wip_limit, `WIP exceeds ${data.wip_limit}; started blocked work counts too`);
  return data;
}
function table(headers, rows) {
  return ['| ' + headers.join(' | ') + ' |', '| ' + headers.map(() => '---').join(' | ') + ' |', ...rows.map(r => '| ' + r.map(cell).join(' | ') + ' |')].join('\n');
}
function replaceBlock(source, name, content) {
  const start = `<!-- management:${name}:start -->`, end = `<!-- management:${name}:end -->`;
  assert(source.split(start).length === 2 && source.split(end).length === 2 && source.indexOf(start) < source.indexOf(end), `missing or duplicate marker: ${name}`);
  return source.slice(0, source.indexOf(start) + start.length) + '\n' + content + '\n' + source.slice(source.indexOf(end));
}
export function buildViews(data, project) {
  const summary = flowSummary(data);
  const moduleView = table(['模块', '已实现', '验收范围', '下一缺口', '证据'], data.modules.map(m => [m.name, m.implemented, m.validation, m.gap, links(m.evidence)]));
  const milestoneView = table(['阶段', '结果 / 退出条件', '状态', '证据'], data.milestones.map(m => [m.id + ' ' + m.name, m.outcome, { pending: '待验收', baseline: '底座已具备（范围有限）', accepted: '已验收' }[m.status], links(m.evidence)]));
  const order = Object.keys(states);
  const tasks = [...data.tasks].sort((a, b) => a.priority.localeCompare(b.priority) || a.id.localeCompare(b.id));
  const rows = tasks.map(t => [`[${t.id}](TASKS.md#${t.id.toLowerCase()})`, t.title, `${t.priority} / ${t.milestone}`, states[t.status], t.owner, t.dependencies.join(', ') || '—']);
  const taskView = `数据日期：${data.updated_at}；在制 ${summary.wip}/${data.wip_limit}，就绪 ${summary.ready}，阻塞 ${summary.blocked}，完成 ${summary.done}。这是工作项统计，不是产品完成率。\n\n` + table(['任务', '内容', '优先级 / 阶段', '状态', '实际负责人', '依赖'], rows) + '\n\n完整验收条件、阻塞与证据见 [TASKS.md](TASKS.md)；主账为 [management/project.json](management/project.json)。';
  let output = project;
  for (const [name, block] of Object.entries({ modules: moduleView, milestones: milestoneView, tasks: taskView })) output = replaceBlock(output, name, block);
  const board = ['# 工作看板与验收卡片', '', '<!-- Generated by npm run management:render; edit management/project.json. -->', '', `数据日期：${data.updated_at}。[目标与模块](PROJECT.md) · [维护方法](management/README.md)`, '', '负责人为空表示待认领；责任角色不是已成立的公司岗位。本文件是主账视图，不另行修改状态。', '', '## 看板', '', table(['状态', '任务'], order.map(s => [states[s], tasks.filter(t => t.status === s).map(t => `[${t.id}](#${t.id.toLowerCase()})`).join('、') || '—'])), ''];
  for (const t of tasks) {
    board.push(`## ${t.id}`, '', `**${t.title}**`, '', `状态：${states[t.status]}；优先级：${t.priority}；里程碑：${t.milestone}；模块：${t.module}。`, '', `实际负责人：${t.owner ?? '待认领'}；所需责任：${t.role}。开始：${t.started_at ?? '未开始'}；更新：${t.updated_at}。`, '', `依赖：${t.dependencies.map(d => `[${d}](#${d.toLowerCase()})`).join('、') || '无'}。`, '', `验收条件：${t.acceptance}`, '');
    if (t.blocker) board.push(`阻塞：${t.blocker.reason}\n\n解除动作：${t.blocker.action}；解除负责人：${t.blocker.owner ?? '待认领'}。`, '');
    if (t.completion) board.push(`验收范围：${t.completion.scope}；验收者：${t.completion.reviewer}。\n\n${t.completion.note}\n\n证据：${links(t.completion.evidence)}`, '');
  }
  return { 'PROJECT.md': output, 'TASKS.md': board.join('\n') };
}
export function checkViews(views, root) {
  for (const [file, content] of Object.entries(views)) assert(existsSync(resolve(root, file)) && readFileSync(resolve(root, file), 'utf8').replaceAll('\r\n', '\n') === content, `stale ${file}; run npm run management:render`);
}
// ---------------------------------------------------------------------------
// 工作台：跨 harness 的同一套读写接口（CLI 与 MCP 共用；主账仍是 management/project.json）
// ---------------------------------------------------------------------------

const LEASE_MINUTES = 180;
const LOCK_STALE_MS = 30_000;
const lockPath = root => resolve(root, 'management/.ledger.lock');
const stamp = ms => new Date(ms).toISOString();
const dayOf = ms => new Date(ms).toISOString().slice(0, 10);

/** `free` 无租约；`held` 租约有效；`expired` 租约过期，别人可以接管。 */
export function claimState(task, now = Date.now()) {
  if (!task.claim) return 'free';
  return Date.parse(task.claim.lease_until) > now ? 'held' : 'expired';
}
function findTask(data, id) {
  const task = data.tasks.find(t => t.id === id);
  assert(task, `unknown task ${id}`);
  return task;
}
function depsDone(data, task) {
  const byId = new Map(data.tasks.map(t => [t.id, t]));
  return task.dependencies.every(id => byId.get(id)?.status === 'done');
}
function touch(data, task, now) {
  const today = dayOf(now);
  task.updated_at = today;
  if (today > data.updated_at) data.updated_at = today;
}

export function boardView(data, now = Date.now()) {
  const cards = data.tasks.map(t => ({
    id: t.id, title: t.title, status: t.status, priority: t.priority, milestone: t.milestone, module: t.module,
    owner: t.owner, role: t.role, dependencies: t.dependencies, acceptance: t.acceptance, blocker: t.blocker,
    started_at: t.started_at, updated_at: t.updated_at, evidence: t.completion ? t.completion.evidence : [],
    claim: t.claim ?? null, claim_state: claimState(t, now), deps_done: depsDone(data, t),
  })).sort((a, b) => a.priority.localeCompare(b.priority) || a.id.localeCompare(b.id));
  return {
    updated_at: data.updated_at,
    wip_limit: data.wip_limit,
    counts: flowSummary(data),
    columns: Object.fromEntries(Object.keys(states).map(status => [status, cards.filter(c => c.status === status).map(c => c.id)])),
    next: cards.filter(c => c.status === 'ready' && c.deps_done).map(c => c.id),
    in_flight: cards.filter(c => ['doing', 'review'].includes(c.status)),
    blocked: cards.filter(c => c.status === 'blocked'),
    milestones: data.milestones.map(m => ({ id: m.id, name: m.name, status: m.status, evidence: m.evidence })),
    cards,
  };
}

/** 认领：写租约、进入 doing。同一张卡在租约有效期内只属于一个 actor；无有效租约的 doing 卡可被补领。 */
export function claimTask(data, { id, actor, leaseMinutes = LEASE_MINUTES, now = Date.now() }) {
  assert(text(actor), 'claim needs an actor: record who you really are (harness + model)');
  const task = findTask(data, id);
  const state = claimState(task, now);
  if (state === 'held' && task.claim.actor !== actor) {
    throw new Error(`${id} is held by ${task.claim.actor} until ${task.claim.lease_until}; wait, or take over after the lease expires`);
  }
  const takeover = task.status === 'doing' && state !== 'held';
  assert(task.status === 'ready' || takeover,
    `${id} is ${states[task.status]}; only ready cards, or a doing card without a live lease, can be claimed`);
  const today = dayOf(now);
  const wip = flowSummary({ ...data, tasks: data.tasks.map(t => (t.id === id ? { ...t, started_at: t.started_at ?? today } : t)) }).wip;
  assert(wip <= data.wip_limit, `claiming ${id} would put WIP at ${wip}, above the limit ${data.wip_limit}`);
  Object.assign(task, {
    status: 'doing', owner: actor, started_at: task.started_at ?? today,
    claim: { actor, at: stamp(now), lease_until: stamp(now + leaseMinutes * 60_000) },
  });
  touch(data, task, now);
  return task;
}

/** 放弃认领：只用于「认领了但还没开工」的占用释放；已开工的卡要用 move 显式改状态。 */
export function releaseTask(data, { id, actor, force = false, now = Date.now() }) {
  const task = findTask(data, id);
  assert(task.claim, `${id} holds no lease`);
  assert(force || task.claim.actor === actor, `${id} is held by ${task.claim.actor}; pass force to override`);
  assert(task.status === 'doing', `${id} is ${states[task.status]}; move it explicitly instead of releasing started work`);
  Object.assign(task, { status: 'ready', owner: null, started_at: null, claim: null });
  touch(data, task, now);
  return task;
}

export function moveTask(data, { id, status, actor, owner, blocker, completion, force = false, note, now = Date.now() }) {
  assert(Object.hasOwn(states, status), `unknown status ${status}`);
  assert(text(actor), 'move needs an actor: record who you really are (harness + model)');
  const task = findTask(data, id);
  assert(!force || text(note), `${id}: a forced move must record why in note`);
  assert(force || claimState(task, now) !== 'held' || task.claim.actor === actor, `${id} is held by ${task.claim?.actor}; pass force to override`);
  const from = task.status;
  const today = dayOf(now);
  if (status === 'blocked') {
    assert(blocker && text(blocker.reason) && text(blocker.action), `${id} needs blocker.reason and blocker.action`);
    task.blocker = { reason: blocker.reason, action: blocker.action, owner: blocker.owner ?? null };
  } else task.blocker = null;
  if (status === 'done') {
    assert(completion && scopes.includes(completion.scope) && text(completion.reviewer) && text(completion.note)
      && Array.isArray(completion.evidence) && completion.evidence.length > 0,
      `${id} completion needs scope (${scopes.join('/')}), reviewer, note and evidence paths`);
    task.completion = { scope: completion.scope, reviewer: completion.reviewer, evidence: completion.evidence, note: completion.note };
    task.claim = null;
  } else task.completion = null;
  if (['candidate', 'backlog', 'ready'].includes(status)) {
    assert(force || !task.started_at, `${id}已经开工；退回待办会隐藏占用，确认要退回请加 force 并记录原因`);
    Object.assign(task, { owner: null, started_at: null, claim: null });
  } else if (['doing', 'review', 'done'].includes(status)) {
    task.owner = text(owner) ? owner : (task.owner ?? actor);
    task.started_at = task.started_at ?? today;
  } else if (text(owner)) task.owner = owner;
  task.status = status;
  if (force && from !== status) {
    task.history = [...(task.history ?? []), { at: stamp(now), actor, from, to: status, note }];
  }
  touch(data, task, now);
  return task;
}

export function ledgerPath(root) { return resolve(root, 'management/project.json'); }
export function readLedger(root) { return JSON.parse(readFileSync(ledgerPath(root), 'utf8')); }
export function serializeLedger(data) { return JSON.stringify(data, null, 4).replaceAll('\n', '\r\n') + '\r\n'; }
export function renderViews(root, data) {
  const views = buildViews(data, readFileSync(resolve(root, 'PROJECT.md'), 'utf8').replaceAll('\r\n', '\n'));
  for (const [file, content] of Object.entries(views)) writeFileSync(resolve(root, file), content);
  return views;
}
export function writeLedger(root, data) {
  validateProject(data, root);
  writeFileSync(ledgerPath(root), serializeLedger(data));
  renderViews(root, data);
  return data;
}

/**
 * 极简跨 harness 互斥：O_EXCL 建锁文件，超时视为陈旧锁接管。
 * 只保证同机同 checkout 的互斥，不是分布式锁。
 */
export async function withLedgerLock(root, operation, { timeoutMs = 3000, staleMs = LOCK_STALE_MS } = {}) {
  const file = lockPath(root);
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      const handle = openSync(file, 'wx');
      try { writeFileSync(handle, `${process.pid}\n`); } finally { closeSync(handle); }
      break;
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      let age;
      try { age = Date.now() - statSync(file).mtimeMs; } catch { continue; }
      if (age > staleMs) { try { rmSync(file); } catch { /* already gone */ } continue; }
      if (Date.now() > deadline) throw new Error('ledger busy: another harness is editing management/project.json; retry shortly');
      await new Promise(r => setTimeout(r, 60));
    }
  }
  try { return await operation(); } finally { try { rmSync(file); } catch { /* already gone */ } }
}

/** 锁内完成「读 → 改 → 校验 → 重建视图 → 写视图 → 最后写主账」。 */
export async function mutateLedger(root, mutate, options) {
  return withLedgerLock(root, () => {
    const data = readLedger(root);
    const result = mutate(data);
    validateProject(data, root);
    const views = buildViews(data, readFileSync(resolve(root, 'PROJECT.md'), 'utf8').replaceAll('\r\n', '\n'));
    for (const [file, content] of Object.entries(views)) writeFileSync(resolve(root, file), content);
    writeFileSync(ledgerPath(root), serializeLedger(data));
    return result;
  }, options);
}

const USAGE = [
  'usage: node scripts/project-management.mjs <command>',
  '  check | render | status          既有校验与视图生成',
  '  board [--json] [--local]         看板快照（默认读在线 Kanban）',
  '  next [--json] [--local]          依赖已完成的 ready 卡',
  '  claim <U-###> --actor <name> [--lease <minutes>]',
  '  release <U-###> --actor <name> [--force]',
  '  move <U-###> <status> --actor <name> [--owner <name>] [--reason <r> --action <a>] [--scope <s> --reviewer <r> --evidence <p1,p2> --note <n>] [--force]',
  '  record <U-###> --actor <name> --scope <s> --reviewer <r> --evidence <p1,p2> --note <n>',
  'actor 必须写真实身份（harness + 模型/会话），不能凭空编造公司成员。',
].join('\n');

function parseArgs(argv) {
  const positional = [], flags = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) { positional.push(token); continue; }
    const [name, inline] = token.slice(2).split('=');
    if (inline !== undefined) flags[name] = inline;
    else if (argv[i + 1] && !argv[i + 1].startsWith('--')) { flags[name] = argv[i + 1]; i += 1; }
    else flags[name] = true;
  }
  return { positional, flags };
}
const list = value => String(value ?? '').split(',').map(s => s.trim()).filter(Boolean);
function describe(task) {
  const lease = task.claim ? `；租约 ${task.claim.actor} 至 ${task.claim.lease_until}` : '';
  return `${task.id} ${states[task.status]}；负责人 ${task.owner ?? '待认领'}${lease}`;
}

async function hostedView() {
  const { fetchHostedBoard, hostedBoardView, kanbanConfigured } = await import('./kanban-client.mjs');
  if (!kanbanConfigured()) throw new Error('未配置在线看板（UNION_KANBAN_URL / UNION_KANBAN_KEY）');
  return hostedBoardView(await fetchHostedBoard());
}

async function main() {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const [mode, ...rest] = process.argv.slice(2);
  const { positional, flags } = parseArgs(rest);
  if (!mode || !['check', 'render', 'status', 'board', 'next', 'claim', 'release', 'move', 'record'].includes(mode)) {
    throw new Error(USAGE);
  }
  const data = readLedger(root);
  validateProject(data, root);
  if (mode === 'status') {
    console.log(JSON.stringify({ updated_at: data.updated_at, ...flowSummary(data), ready: data.tasks.filter(t => t.status === 'ready').map(t => t.id), blocked: data.tasks.filter(t => t.status === 'blocked').map(t => ({ id: t.id, ...t.blocker })) }, null, 2));
    return;
  }
  if (mode === 'render' || mode === 'check') {
    const views = buildViews(data, readFileSync(resolve(root, 'PROJECT.md'), 'utf8').replaceAll('\r\n', '\n'));
    if (mode === 'render') for (const [file, content] of Object.entries(views)) writeFileSync(resolve(root, file), content);
    else checkViews(views, root);
    console.log(`Management ${mode}: ${data.modules.length} modules, ${data.milestones.length} milestones, ${data.tasks.length} tasks; PASS`);
    return;
  }
  if (mode === 'board' || mode === 'next') {
    const view = flags.local ? boardView(data) : await hostedView();
    if (!flags.json) {
      const rows = Object.keys(states).map(status => [states[status], (view.columns[status] ?? []).join('、') || '—']);
      console.log(`来源：${view.source === 'kanban' ? `在线 Kanban ${view.online_url ?? ''}` : '本地主账 project.json'}；数据日期 ${view.updated_at ?? view.ledger_updated_at}`);
      console.log(table(['状态', '卡片'], rows));
      const flying = view.in_flight.map(c => `- ${c.id} ${states[c.status]}；${c.owner ?? '待认领'}；${c.claim ? `租约 ${c.claim.actor} 至 ${c.claim.lease_until}` : `在线版本 v${c.version ?? '-'}`}`);
      console.log(`\n可开工：${view.next.join('、') || '—'}`);
      if (flying.length) console.log(`在制：\n${flying.join('\n')}`);
    } else {
      console.log(JSON.stringify(mode === 'next' ? view.cards.filter(c => view.next.includes(c.id)) : view, null, 2));
    }
    return;
  }
  const id = positional[0];
  assert(text(id), `${mode} needs a card id`);
  const actor = flags.actor;
  const changed = await mutateLedger(root, current => {
    if (mode === 'claim') return claimTask(current, { id, actor, leaseMinutes: Number(flags.lease ?? LEASE_MINUTES) });
    if (mode === 'release') return releaseTask(current, { id, actor, force: Boolean(flags.force) });
    const status = mode === 'record' ? 'done' : positional[1];
    assert(text(status), 'move needs a target status');
    const completion = status === 'done'
      ? { scope: flags.scope, reviewer: flags.reviewer, evidence: list(flags.evidence), note: flags.note }
      : undefined;
    const blocker = status === 'blocked'
      ? { reason: flags.reason, action: flags.action, owner: text(flags.blockerOwner) ? flags.blockerOwner : null }
      : undefined;
    return moveTask(current, { id, status, actor, owner: text(flags.owner) ? flags.owner : undefined, blocker, completion, force: Boolean(flags.force), note: text(flags.note) ? flags.note : undefined });
  });
  console.log(`已更新（本地主账）：${describe(changed)}`);
  console.log('主账与 PROJECT.md / TASKS.md 已同步；提交前运行 npm run check:management。');
}

if (process.argv[1] && relative(resolve(process.argv[1]), fileURLToPath(import.meta.url)) === '') {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
