/** Online operational authority shared by CLI and MCP. No ledger writes. */
import assert from 'node:assert/strict';
import { realpathSync, statSync } from 'node:fs';
import { isAbsolute, resolve, relative } from 'node:path';
import { fetchHostedBoard, findHostedTask, hostedBoardView, onlineStatus, patchHostedTask } from './kanban-client.mjs';

const present = value => typeof value === 'string' && value.trim().length > 0;
const started = status => ['progress', 'review', 'blocked'].includes(status);
const states = ['backlog', 'candidate', 'ready', 'doing', 'blocked', 'review', 'done'];

function completionEvidence(args, root) {
  assert(['documentation', 'controlled', 'real', 'sustained'].includes(args.scope), 'completion needs a valid scope');
  assert(present(args.reviewer) && present(args.note), 'completion needs reviewer and note');
  assert(Array.isArray(args.evidence) && args.evidence.length, 'completion needs evidence paths');
  const base = realpathSync(root);
  for (const path of args.evidence) {
    assert(present(path) && !isAbsolute(path) && !path.includes('\\') && !path.includes(':') && !path.split('/').includes('..'), 'evidence must be repository-relative');
    const target = realpathSync(resolve(root, path));
    const rel = relative(base, target);
    assert(rel && !isAbsolute(rel) && rel !== '..' && !rel.startsWith('../') && !rel.startsWith('..\\'), 'evidence must stay inside repository');
    assert(statSync(target).isFile(), `missing evidence file: ${path}`);
  }
  return `${args.note}\n验收：${args.reviewer}（${args.scope}）\n执行：${args.actor}\n证据：${args.evidence.join(', ')}`;
}

function dependenciesDone(board, task) {
  return (task.dependencies ?? []).every(id => board.tasks.some(t => t.id === id && !t.archived && t.status === 'done'));
}

export async function operateHosted(command, args, root) {
  assert(process.env.UNION_BOARD_SOURCE !== 'local' && !args.local, 'local history is read-only; operational writes require online Kanban');
  assert(['claim', 'release', 'move', 'record'].includes(command), 'unknown board operation');
  assert(present(args.actor), 'record the actual harness/model/session actor');
  const status = command === 'record' ? 'done' : args.status;
  if (command === 'move') assert(states.includes(status), `unknown status ${status}`);
  // Validate delivery before any remote side effect, even if the local ledger is invalid.
  const evidence = status === 'done' ? completionEvidence(args, root) : undefined;
  if (status === 'blocked') assert(present(args.blocker_reason) && present(args.blocker_action), 'blocked needs reason and action');

  const board = await fetchHostedBoard();
  assert(present(board.user?.id) && board.user.active !== 0 && board.user.active !== false, 'online authenticated active user is required');
  const task = findHostedTask(board, args.id);
  assert(task, `${args.id} is not an active online card`);
  assert(Number.isInteger(task.version), 'online task must have an integer version');
  assert(!task.assignee || task.assignee === board.user.id, `${args.id} is held by another member; explicit coordinator handover required`);
  assert(!args.owner || args.owner === board.user.id, 'owner must be the authenticated online user.id');
  const view = hostedBoardView(board);
  const patch = {};
  if (command === 'claim') {
    if (task.assignee === board.user.id && started(task.status)) return { source: 'kanban', id: args.id, task, unchanged: true, wip_limit: view.wip_limit };
    assert(task.status === 'ready', 'claim requires a ready card');
    Object.assign(patch, { status: 'progress', assignee: board.user.id });
  } else if (command === 'release') {
    assert(task.assignee === board.user.id && task.status === 'ready', 'release requires own ready card; started work retains responsibility');
    Object.assign(patch, { assignee: '' });
  } else {
    assert(task.status !== 'done', 'completed card requires explicit coordinator reopening');
    patch.status = onlineStatus(status);
    assert(!(started(task.status) && ['backlog', 'ready'].includes(patch.status)), 'started work cannot hide in backlog; retain owner and record handover');
    if (['progress', 'review', 'done'].includes(patch.status)) {
      assert(command !== 'move' || patch.status !== 'progress' || task.status === 'ready' || started(task.status), 'start requires ready card');
      Object.assign(patch, { assignee: board.user.id });
    }
    if (patch.status === 'blocked') patch.blocker = `${args.blocker_reason}\n解除：${args.blocker_action}${args.blocker_owner ? `\n负责：${args.blocker_owner}` : ''}`;
    else if (task.status === 'blocked') patch.blocker = '';
    if (evidence) patch.evidence = evidence;
  }
  if (['ready', 'progress', 'review', 'done'].includes(patch.status)) assert(dependenciesDone(board, task), 'unfinished online dependencies');
  if (started(patch.status) && !started(task.status)) {
    assert(view.wip_limit === null || view.counts.wip < view.wip_limit, `online WIP limit ${view.wip_limit} reached (blocked work counts)`);
  }
  try {
    const response = await patchHostedTask(task.id, patch, task.version);
    return { source: 'kanban', id: args.id, previous_version: task.version, task: response.task ?? response, wip_limit: view.wip_limit, mirror: 'unchanged; delivery mirror is explicit' };
  } catch (error) {
    let observed;
    try {
      const current = findHostedTask(await fetchHostedBoard(), args.id);
      observed = current ? JSON.stringify({ id: current.id, version: current.version, status: current.status, assignee: current.assignee }) : 'card no longer active';
    } catch { observed = 'readback unavailable'; }
    throw new Error(`online write uncertain/rejected (${error.status ? `HTTP ${error.status}` : 'transport error'}); no retry; readback: ${observed}`);
  }
}
