#!/usr/bin/env node
/**
 * UNION 开发工作台的 MCP server（stdio，零依赖）。
 *
 * CLI 与 MCP 共用在线操作实现；本地 project.json 仅保存历史路线和交付证据。
 */
import { createInterface } from 'node:readline';
import { spawn } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { boardView, readLedger, validateProject } from './project-management.mjs';
import { fetchHostedBoard, hostedBoardView } from './kanban-client.mjs';
import { operateHosted } from './kanban-operations.mjs';

const root = process.env.UNION_REPO_ROOT
  ? resolve(process.env.UNION_REPO_ROOT)
  : resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SERVER_INFO = { name: 'union-board', version: '0.1.0' };
const log = (...parts) => process.stderr.write(`[union-board] ${parts.join(' ')}\n`);

const SOURCE = process.env.UNION_BOARD_SOURCE ?? 'kanban';
async function boardSnapshot() {
  if (SOURCE === 'local') return { ...boardView(loadLedger()), source: 'local-history' };
  return hostedBoardView(await fetchHostedBoard());
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
    description: '使用实际在线 user.id/version 认领 ready 卡；检查实时依赖、负责人和服务端 WIP。开工前认领，不按本地租约接管。',
    inputSchema: {
      type: 'object',
      properties: {
        id: TASK_ID,
        actor: { type: 'string', description: ACTOR_DOC },
        lease_minutes: { type: 'number', description: '兼容旧调用参数；在线所有权不会自动过期' },
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
        force: { type: 'boolean', description: '兼容旧调用参数；不绕过在线所有权或已开工责任' },
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
    case 'union_card_claim':
    case 'union_card_release':
    case 'union_card_move':
    case 'union_card_record':
      return operateHosted(name.replace('union_card_', ''), args, root);
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
