#!/usr/bin/env node
/**
 * 在线 UNION Kanban 客户端（Cloudflare Worker，Bearer 鉴权）。
 *
 * 只做一件事：把在线卡读/写成与本地主账同一套形状，好让 `union-board` 的
 * CLI 与 MCP 用一个数据源。凭据只在宿主环境或 ~/.union-kanban.env，绝不进仓库。
 */
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const STATUS_ONLINE_TO_LOCAL = { backlog: 'backlog', ready: 'ready', progress: 'doing', review: 'review', blocked: 'blocked', done: 'done' };
const STATUS_LOCAL_TO_ONLINE = { backlog: 'backlog', candidate: 'backlog', ready: 'ready', doing: 'progress', review: 'review', blocked: 'blocked', done: 'done' };
const LOCAL_STATUS_LABEL = { backlog: '待依赖', candidate: '候选', ready: '就绪', doing: '进行中', blocked: '阻塞', review: '待验收', done: '完成' };

export function kanbanConfig() {
  if (process.env.UNION_KANBAN_URL && process.env.UNION_KANBAN_KEY) {
    return { url: process.env.UNION_KANBAN_URL.replace(/\/+$/, ''), key: process.env.UNION_KANBAN_KEY };
  }
  try {
    const parsed = Object.fromEntries(
      readFileSync(join(homedir(), '.union-kanban.env'), 'utf8')
        .split(/\r?\n/)
        .map(line => line.match(/^([A-Z_]+)=(.*)$/))
        .filter(Boolean)
        .map(m => [m[1], m[2].trim()]),
    );
    if (parsed.UNION_KANBAN_URL && parsed.UNION_KANBAN_KEY) {
      return { url: parsed.UNION_KANBAN_URL.replace(/\/+$/, ''), key: parsed.UNION_KANBAN_KEY };
    }
  } catch { /* 没有配置文件就走离线 */ }
  return null;
}

export const kanbanConfigured = () => kanbanConfig() !== null;

async function request(config, path, { method = 'GET', body, headers = {} } = {}) {
  const response = await fetch(`${config.url}/api${path}`, {
    method,
    headers: {
      authorization: `Bearer ${config.key}`,
      accept: 'application/json',
      ...(body ? { 'content-type': 'application/json' } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = { raw: text }; }
  if (!response.ok) {
    const error = new Error(`在线看板 ${method} ${path} → HTTP ${response.status}: ${payload?.error ?? text.slice(0, 200)}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return { payload, etag: response.headers.get('etag') ?? null };
}

export async function fetchHostedBoard({ etag } = {}) {
  const config = kanbanConfig();
  if (!config) throw new Error('未配置 UNION_KANBAN_URL / UNION_KANBAN_KEY（宿主环境或 ~/.union-kanban.env）');
  const { payload } = await request(config, '/board', { headers: etag ? { 'if-none-match': etag } : {} });
  return payload;
}

/**
 * 写在线卡：必须带最新整数 version，成功以 HTTP 200 为准；
 * 409 说明有人先改了，原样抛出让人先读回再决定，不自动重试。
 */
export async function patchHostedTask(id, patch, version) {
  const config = kanbanConfig();
  if (!config) throw new Error('未配置 UNION_KANBAN_URL / UNION_KANBAN_KEY');
  if (!Number.isInteger(version)) throw new Error('写在线卡必须带最新整数 version');
  const { payload } = await request(config, `/tasks/${Number(id)}`, { method: 'PATCH', body: { ...patch, version } });
  return payload;
}

export async function commentHostedTask(id, text) {
  const config = kanbanConfig();
  if (!config) throw new Error('未配置 UNION_KANBAN_URL / UNION_KANBAN_KEY');
  const { payload } = await request(config, `/tasks/${Number(id)}/comments`, { method: 'POST', body: { body: text } });
  return payload;
}

const uIdOf = task => (String(task.title ?? '').match(/U-\d{3}/) ?? [null])[0];
const stripPrefix = title => String(title ?? '').replace(/^\s*S\d{2}\s*\/\s*U-\d{3}\s*·\s*/, '');

/** 把在线 board 归一成与本地 `boardView` 相同的形状，供 MCP/CLI 共用。 */
export function hostedBoardView(board, { now = Date.now() } = {}) {
  const memberName = id => board.members.find(m => m.id === id)?.name ?? null;
  const byOnlineId = new Map(board.tasks.map(task => [task.id, task]));
  const uOf = task => uIdOf(task) ?? `UNI-${String(task.id).padStart(3, '0')}`;

  const cards = board.tasks
    .filter(task => !task.archived)
    .map(task => {
      const status = STATUS_ONLINE_TO_LOCAL[task.status] ?? 'backlog';
      const dependencies = (task.dependencies ?? []).map(id => uOf(byOnlineId.get(id) ?? { id, title: '' }));
      const checklist = Array.isArray(task.checklist) ? task.checklist : [];
      return {
        id: uOf(task),
        online_id: task.id,
        version: task.version,
        title: stripPrefix(task.title),
        full_title: task.title,
        status,
        status_label: LOCAL_STATUS_LABEL[status],
        priority: task.priority,
        milestone: task.milestone,
        module: task.track,
        owner: memberName(task.assignee) ?? task.assignee ?? null,
        role: trackLabel(task.track),
        dependencies,
        acceptance: task.description ?? '',
        blocker: task.status === 'blocked' ? { reason: task.blocker ?? '（未填写阻塞原因）', action: '见在线卡讨论', owner: null } : null,
        evidence: task.evidence ? [task.evidence] : [],
        branch: task.branch || null,
        pr_url: task.pr_url || null,
        checklist_done: checklist.filter(item => item.done).length,
        checklist_total: checklist.length,
        comment_count: task.comment_count ?? 0,
        claim: null,
        claim_state: task.assignee ? 'held' : 'free',
        deps_done: dependencies.every(u => {
          const dependency = board.tasks.find(candidate => !candidate.archived && uOf(candidate) === u);
          return dependency ? dependency.status === 'done' : false;
        }),
        updated_at: (task.updated_at ?? '').slice(0, 10) || null,
      };
    })
    .sort((a, b) => a.priority.localeCompare(b.priority) || a.id.localeCompare(b.id));

  const columns = Object.fromEntries(Object.keys(LOCAL_STATUS_LABEL).map(status => [status, cards.filter(card => card.status === status).map(card => card.id)]));
  const counts = {
    ...Object.fromEntries(Object.keys(LOCAL_STATUS_LABEL).map(status => [status, columns[status].length])),
    wip: cards.filter(card => ['doing', 'blocked', 'review'].includes(card.status)).length,
    realAccepted: 0,
  };

  return {
    source: 'kanban',
    revision: board.revision ?? null,
    online_url: kanbanConfig()?.url ?? null,
    user: board.user ?? null,
    generated_at: new Date(now).toISOString(),
    ledger_updated_at: cards.reduce((latest, card) => (card.updated_at && card.updated_at > latest ? card.updated_at : latest), ''),
    wip_limit: null,
    counts,
    columns,
    next: cards.filter(card => card.status === 'ready' && card.deps_done).map(card => card.id),
    in_flight: cards.filter(card => ['doing', 'review'].includes(card.status)),
    blocked: cards.filter(card => card.status === 'blocked'),
    milestones: [...new Set(cards.map(card => card.milestone).filter(Boolean))].sort().map(id => ({ id, name: id, status: 'pending', evidence: [] })),
    cards,
  };
}

function trackLabel(track) {
  return { core: 'ai-union 核心', platform: 'Platform 平台', infra: '工程基建' }[track] ?? track ?? '';
}

export const onlineStatus = localStatus => STATUS_LOCAL_TO_ONLINE[localStatus] ?? 'backlog';
export const findHostedTask = (board, uId) => board.tasks.find(task => !task.archived && uIdOf(task) === uId);
