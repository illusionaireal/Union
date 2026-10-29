import assert from 'node:assert/strict';
import { existsSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { resolve, relative, isAbsolute, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const states = { backlog: '待依赖', candidate: '候选', ready: '就绪', doing: '进行中', blocked: '阻塞', review: '待验收', done: '完成' };
const scopes = ['documentation', 'controlled', 'real', 'sustained'];
const text = x => typeof x === 'string' && x.trim().length > 0;
const date = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && Number.isFinite(Date.parse(x)) && new Date(x).toISOString().slice(0, 10) === x;
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
function main() {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const mode = process.argv[2];
  assert(['check', 'render', 'status'].includes(mode), 'usage: node scripts/project-management.mjs check|render|status');
  const data = validateProject(JSON.parse(readFileSync(resolve(root, 'management/project.json'), 'utf8')), root);
  if (mode === 'status') { console.log(JSON.stringify({ updated_at: data.updated_at, ...flowSummary(data), ready: data.tasks.filter(t => t.status === 'ready').map(t => t.id), blocked: data.tasks.filter(t => t.status === 'blocked').map(t => ({ id: t.id, ...t.blocker })) }, null, 2)); return; }
  const views = buildViews(data, readFileSync(resolve(root, 'PROJECT.md'), 'utf8').replaceAll('\r\n', '\n'));
  if (mode === 'render') for (const [file, content] of Object.entries(views)) writeFileSync(resolve(root, file), content);
  else checkViews(views, root);
  console.log(`Management ${mode}: ${data.modules.length} modules, ${data.milestones.length} milestones, ${data.tasks.length} tasks; PASS`);
}
if (process.argv[1] && relative(resolve(process.argv[1]), fileURLToPath(import.meta.url)) === '') {
  try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
