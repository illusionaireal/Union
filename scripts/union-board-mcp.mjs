#!/usr/bin/env node
/**
 * UNION 开发工作台的 MCP server（stdio，零依赖）。
 *
 * 一份实现，Codex / OpenCode / Claude Code / Goose / DSH 共用；主账仍是
 * management/project.json，本进程只是它的结构化适配器，不持有任何状态。
 */
import { createInterface } from 'node:readline';
import { spawn } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  boardView, claimState, claimTask, moveTask, readLedger, releaseTask, validateProject, mutateLedger,
} from './project-management.mjs';
import {
  fetchHostedBoard, hostedBoardView, kanbanConfigured, patchHostedTask, commentHostedTask, findHostedTask, onlineStatus,
} from './kanban-client.mjs';

const root = process.env.UNION_REPO_ROOT
  ? resolve(process.env.UNION_REPO_ROOT)
  : resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SERVER_INFO = { name: 'union-board', version: '0.1.0' };
const log = (...parts) => process.stderr.write(`[union-board] ${parts.join(' ')}\n`);

// 数据来源：kanban = 在线 UNION Kanban（用户 2026-11-06 指定），local = 本地 project.json。
// 在线可用时默认走 kanban；离线或显式 UNION_BOARD_SOURCE=local 时退回本地主账。
const SOURCE = process.env.UNION_BOARD_SOURCE ?? (kanbanConfigured() ? 'kanban' : 'local');
const useHosted = () => SOURCE === 'kanban' && kanbanConfigured();

async function boardSnapshot() {
  if (useHosted()) return hostedBoardView(await fetchHostedBoard());
  return { source: 'local', ...boardView(loadLedger()) };
}

/** 在线写入成功后，把同一事实镜像回本地主账；镜像失败不撤销在线结果，只如实报告。 */
async function mirrorLocal(mutate) {
  try {
    await mutateLedger(root, mutate);
    return 'ok';
  } catch (error) {
    return `未同步（${error.message}）`;
  }
}

const ACTOR_DOC = '真实执行者身份，写清 harness 与模型/会话（例如 "codex/gpt-5"、"opencode/glm-4.6"），不要编造公司成员。';
const TASK_ID = { type: 'string', description: '工作项编号，如 U-054' };

const TOOLS = [
  {
    name: 'union_board_status',
    description: 'UNION 开发看板快照：各状态分列、在制/WIP 上限、可开工队列、在制租约、阻塞项、里程碑。选工作前先调它。',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'union_card_list',
    description: '列出工作项卡片（可按状态、里程碑过滤），含验收条件、依赖、负责人与租约。',
    inputSchema: {
      type: 'object',
      properties: {
        status: { type: 'string', enum: ['backlog', 'candidate', 'ready', 'doing', 'blocked', 'review', 'done'], description: '只列该状态' },
        milestone: { type: 'string', description: '只列该里程碑，如 G0、G3' },
        limit: { type: 'number', description: '最多返回数量，默认 30' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'union_card_get',
    description: '读取单个工作项的完整信息：验收条件、依赖、阻塞、证据、租约。',
    inputSchema: { type: 'object', properties: { id: TASK_ID }, required: ['id'], additionalProperties: false },
  },
  {
    name: 'union_card_claim',
    description: '认领一张 ready 卡：写租约并进入进行中。租约有效期内别人不能认领；超过 lease_minutes 后可被接管。开工前必须先认领。',
    inputSchema: {
      type: 'object',
      properties: {
        id: TASK_ID,
        actor: { type: 'string', description: ACTOR_DOC },
        lease_minutes: { type: 'number', description: '租约分钟数，默认 180' },
      },
      required: ['id', 'actor'],
      additionalProperties: false,
    },
  },
  {
    name: 'union_card_release',
    description: '放弃认领，把还没开工的卡退回就绪。已开工的卡请用 union_card_move 显式改状态。',
    inputSchema: {
      type: 'object',
      properties: { id: TASK_ID, actor: { type: 'string', description: ACTOR_DOC }, force: { type: 'boolean' } },
      required: ['id', 'actor'],
      additionalProperties: false,
    },
  },
  {
    name: 'union_card_move',
    description: '改变工作项状态。blocked 需要 blocker_reason+blocker_action；done 需要 scope/reviewer/note/evidence，且证据文件必须真实存在。',
    inputSchema: {
      type: 'object',
      properties: {
        id: TASK_ID,
        status: { type: 'string', enum: ['backlog', 'candidate', 'ready', 'doing', 'blocked', 'review', 'done'] },
        actor: { type: 'string', description: ACTOR_DOC },
        owner: { type: 'string', description: '实际承担者；省略则沿用或使用 actor' },
        blocker_reason: { type: 'string' },
        blocker_action: { type: 'string' },
        blocker_owner: { type: 'string' },
        scope: { type: 'string', enum: ['documentation', 'controlled', 'real', 'sustained'] },
        reviewer: { type: 'string' },
        evidence: { type: 'array', items: { type: 'string' }, description: '仓库相对路径列表' },
        note: { type: 'string' },
        force: { type: 'boolean', description: '越过租约或已开工退回等限制；必须同时提供 note 说明原因，强制流转会记入任务历史' },
      },
      required: ['id', 'status', 'actor'],
      additionalProperties: false,
    },
  },
  {
    name: 'union_card_record',
    description: '记录验收完成（等价于 move 到 done）。必须提供验收范围、验收者、结论与真实存在的证据路径；不能只声明完成。',
    inputSchema: {
      type: 'object',
      properties: {
        id: TASK_ID,
        actor: { type: 'string', description: ACTOR_DOC },
        scope: { type: 'string', enum: ['documentation', 'controlled', 'real', 'sustained'] },
        reviewer: { type: 'string' },
        evidence: { type: 'array', items: { type: 'string' } },
        note: { type: 'string' },
        force: { type: 'boolean' },
      },
      required: ['id', 'actor', 'scope', 'reviewer', 'evidence', 'note'],
      additionalProperties: false,
    },
  },
  {
    name: 'union_board_verify',
    description: '跑仓库检查：默认 npm run check:management（主账规则+视图一致性+管理测试）；full=true 时跑完整 npm run check。返回真实输出，不代替人的验收判断。',
    inputSchema: { type: 'object', properties: { full: { type: 'boolean' } }, additionalProperties: false },
  },
];

function loadLedger() {
  const data = readLedger(root);
  return validateProject(data, root);
}
function card(task) {
  const { id, title, status, priority, milestone, module, owner, role, dependencies, acceptance, blocker, started_at, updated_at, completion, claim } = task;
  return { id, title, status, priority, milestone, module, owner, role, dependencies, acceptance, blocker, started_at, updated_at, completion: completion ?? null, claim: claim ?? null, claim_state: claimState(task) };
}
function summary(task) {
  const lease = task.claim ? `，租约 ${task.claim.actor} 至 ${task.claim.lease_until}` : '';
  return `${task.id} → ${task.status}；负责人 ${task.owner ?? '待认领'}${lease}。主账与 PROJECT.md/TASKS.md 已同步。`;
}

function runNpm(scriptArgs, timeoutMs = 600_000) {
  return new Promise(resolvePromise => {
    const command = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    const child = spawn(command, ['run', ...scriptArgs], { cwd: root, shell: true });
    let output = '';
    const cap = chunk => { output += chunk.toString('utf8'); };
    child.stdout.on('data', cap);
    child.stderr.on('data', cap);
    const timer = setTimeout(() => child.kill(), timeoutMs);
    child.on('error', error => { clearTimeout(timer); resolvePromise({ ok: false, output: `${output}\n${error.message}`.trim() }); });
    child.on('close', code => { clearTimeout(timer); resolvePromise({ ok: code === 0, output: output.trim() }); });
  });
}

async function call(name, args = {}) {
  switch (name) {
    case 'union_board_status': {
      const view = await boardSnapshot();
      return {
        source: view.source ?? 'local',
        repo: root,
        online_url: view.online_url ?? null,
        user: view.user ?? null,
        revision: view.revision ?? null,
        updated_at: view.updated_at ?? view.ledger_updated_at,
        counts: view.counts,
        wip_limit: view.wip_limit,
        columns: view.columns,
        next: view.next,
        in_flight: view.in_flight.map(c => ({ id: c.id, owner: c.owner, status: c.status, claim: c.claim, claim_state: c.claim_state, version: c.version })),
        blocked: view.blocked.map(c => ({ id: c.id, blocker: c.blocker })),
        milestones: view.milestones,
      };
    }
    case 'union_card_list': {
      const view = await boardSnapshot();
      const list = view.cards.filter(t => (!args.status || t.status === args.status) && (!args.milestone || t.milestone === args.milestone));
      return { source: view.source ?? 'local', total: list.length, cards: list.slice(0, args.limit ?? 30) };
    }
    case 'union_card_get': {
      const view = await boardSnapshot();
      const found = view.cards.find(t => t.id === args.id);
      if (!found) throw new Error(`unknown task ${args.id}`);
      return found;
    }
    case 'union_card_claim': {
      if (!useHosted()) return summary(await mutateLedger(root, data => claimTask(data, { id: args.id, actor: args.actor, leaseMinutes: args.lease_minutes ?? 180 })));
      const board = await fetchHostedBoard();
      const task = findHostedTask(board, args.id);
      if (!task) throw new Error(`${args.id} 不在在线看板的活动卡里`);
      const patched = await patchHostedTask(task.id, { status: 'progress', assignee: board.user.id }, task.version);
      const mirror = await mirrorLocal(local => claimTask(local, { id: args.id, actor: args.actor, leaseMinutes: args.lease_minutes ?? 180 }));
      return `已认领在线卡 #${task.id}（${args.id} → progress，assignee=${board.user.name}，version ${task.version}→${patched.task?.version ?? patched.version ?? '?'}）；本地主账镜像：${mirror}`;
    }
    case 'union_card_release': {
      if (!useHosted()) return summary(await mutateLedger(root, data => releaseTask(data, { id: args.id, actor: args.actor, force: Boolean(args.force) })));
      const board = await fetchHostedBoard();
      const task = findHostedTask(board, args.id);
      if (!task) throw new Error(`${args.id} 不在在线看板的活动卡里`);
      await patchHostedTask(task.id, { status: 'ready', assignee: '' }, task.version);
      const mirror = await mirrorLocal(local => releaseTask(local, { id: args.id, actor: args.actor, force: Boolean(args.force) }));
      return `已释放在线卡 #${task.id}（${args.id} → ready，取消 assignee）；本地主账镜像：${mirror}`;
    }
    case 'union_card_move': {
      if (!useHosted()) return summary(await mutateLedger(root, data => moveTask(data, {
        id: args.id,
        status: args.status,
        actor: args.actor,
        owner: args.owner,
        force: Boolean(args.force),
        note: args.note,
        blocker: args.status === 'blocked' ? { reason: args.blocker_reason, action: args.blocker_action, owner: args.blocker_owner ?? null } : undefined,
        completion: args.status === 'done' ? { scope: args.scope, reviewer: args.reviewer, evidence: args.evidence ?? [], note: args.note } : undefined,
      })));
      const board = await fetchHostedBoard();
      const task = findHostedTask(board, args.id);
      if (!task) throw new Error(`${args.id} 不在在线看板的活动卡里`);
      const patch = { status: onlineStatus(args.status) };
      if (args.status === 'blocked') patch.blocker = args.blocker_reason ?? '';
      if (args.status === 'done') {
        patch.evidence = args.note ?? '';
        if (args.evidence?.length) patch.branch = task.branch ?? '';
      }
      const patched = await patchHostedTask(task.id, patch, task.version);
      if (args.note) await commentHostedTask(task.id, args.note);
      const mirror = await mirrorLocal(local => moveTask(local, {
        id: args.id, status: args.status, actor: args.actor, owner: args.owner, force: Boolean(args.force), note: args.note,
        blocker: args.status === 'blocked' ? { reason: args.blocker_reason, action: args.blocker_action, owner: args.blocker_owner ?? null } : undefined,
        completion: args.status === 'done' ? { scope: args.scope, reviewer: args.reviewer, evidence: args.evidence ?? [], note: args.note } : undefined,
      }));
      return `在线卡 #${task.id} ${args.id} → ${patch.status}（version ${task.version}→${patched.task?.version ?? '?'}）；本地主账镜像：${mirror}`;
    }
    case 'union_card_record': {
      if (!useHosted()) return summary(await mutateLedger(root, data => moveTask(data, {
        id: args.id, status: 'done', actor: args.actor, force: Boolean(args.force), note: args.note,
        completion: { scope: args.scope, reviewer: args.reviewer, evidence: args.evidence ?? [], note: args.note },
      })));
      const board = await fetchHostedBoard();
      const task = findHostedTask(board, args.id);
      if (!task) throw new Error(`${args.id} 不在在线看板的活动卡里`);
      await patchHostedTask(task.id, {
        status: 'done',
        evidence: `${args.note ?? ''}${args.reviewer ? `\n验收：${args.reviewer}（${args.scope}）` : ''}`.trim(),
      }, task.version);
      if (args.note) await commentHostedTask(task.id, `${args.note}${args.reviewer ? `\n验收者：${args.reviewer}；范围：${args.scope}` : ''}`);
      const mirror = await mirrorLocal(local => moveTask(local, {
        id: args.id, status: 'done', actor: args.actor, force: Boolean(args.force), note: args.note,
        completion: { scope: args.scope, reviewer: args.reviewer, evidence: args.evidence ?? [], note: args.note },
      }));
      return `在线卡 #${task.id} ${args.id} → done 并已留言；本地主账镜像：${mirror}`;
    }
    case 'union_board_verify': {
      const result = args.full ? await runNpm(['check']) : await runNpm(['check:management']);
      if (!result.ok) throw new Error(`check failed:\n${result.output}`);
      return result.output;
    }
    default:
      throw new Error(`unknown tool ${name}`);
  }
}

function reply(id, body) { process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, ...body })}\n`); }

async function dispatch(message) {
  const { id, method, params } = message;
  if (method === 'initialize') {
    return reply(id, { result: { protocolVersion: params?.protocolVersion ?? '2024-11-05', capabilities: { tools: {} }, serverInfo: SERVER_INFO } });
  }
  if (method === 'notifications/initialized' || method === 'initialized') return undefined;
  if (method === 'ping') return reply(id, { result: {} });
  if (method === 'tools/list') return reply(id, { result: { tools: TOOLS } });
  // 客户端会主动探测这些能力；明确回空表，避免把 -32601 当成连接失败。
  if (method === 'resources/list') return reply(id, { result: { resources: [] } });
  if (method === 'resources/templates/list') return reply(id, { result: { resourceTemplates: [] } });
  if (method === 'prompts/list') return reply(id, { result: { prompts: [] } });
  if (method === 'tools/call') {
    const name = params?.name;
    const args = params?.arguments ?? {};
    try {
      const value = await call(name, args);
      const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
      return reply(id, { result: { content: [{ type: 'text', text }] } });
    } catch (error) {
      log(name, 'failed:', error.message);
      return reply(id, { result: { content: [{ type: 'text', text: error.message }], isError: true } });
    }
  }
  if (id === undefined) return undefined;
  return reply(id, { error: { code: -32601, message: `method not found: ${method}` } });
}

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
const inflight = new Set();
lines.on('line', line => {
  const trimmed = line.trim();
  if (!trimmed) return;
  let message;
  try { message = JSON.parse(trimmed); } catch { log('ignored non-JSON line'); return; }
  // 在线看板是异步 HTTP：把未完成的调用记下来，stdin 关闭后等它们写完再退出。
  const task = dispatch(message).catch(error => {
    log('dispatch failed:', error.message);
    if (message?.id !== undefined) reply(message.id, { error: { code: -32603, message: error.message } });
  });
  inflight.add(task);
  task.finally(() => inflight.delete(task));
});
lines.on('close', async () => {
  await Promise.all([...inflight]);
  process.exit(0);
});
log(`ready; repo=${root} source=${SOURCE}`);
