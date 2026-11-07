#!/usr/bin/env node
/**
 * 团队动态：只读在线看板的“团队动态”（活动流 + 留言板），或在留言板发求助。
 *
 * 用途：定时任务每轮启动时先跑一次，先看团队在做什么、有没有待处理的求助/阻塞，
 * 再决定本轮推进什么；自己卡住时用 `--ask` 在留言板求助（会出现在团队动态里）。
 *
 * 用法：
 *   node ops/automation/team-feed.mjs                 # 读：活动流、留言、待处理求助、阻塞卡
 *   node ops/automation/team-feed.mjs --limit 15      # 只取最近 15 条动态
 *   node ops/automation/team-feed.mjs --ask "【求助｜U-0xx】现象/已尝试/需要谁做什么"
 *   node ops/automation/team-feed.mjs --ask "补充说明" --reply 4
 *
 * 凭据只在宿主环境或 ~/.union-kanban.env；本脚本不打印密钥。
 * 需要代理时先 `$env:NODE_OPTIONS='--use-env-proxy'`（脚本会补 HTTPS_PROXY）。
 */
import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

const args = process.argv.slice(2);
const has = (name) => args.includes(`--${name}`);
const flag = (name) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && i + 1 < args.length && !args[i + 1].startsWith('--') ? args[i + 1] : undefined;
};

function loadEnvFile(file) {
  const out = {};
  if (!fs.existsSync(file)) return out;
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/.exec(line);
    if (m && !line.trim().startsWith('#')) out[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
  return out;
}

const hostEnv = loadEnvFile(path.join(process.env.USERPROFILE || '', '.union-kanban.env'));
const url = (process.env.UNION_KANBAN_URL || hostEnv.UNION_KANBAN_URL || '').trim().replace(/\/+$/, '');
const key = (process.env.UNION_KANBAN_KEY || hostEnv.UNION_KANBAN_KEY || '').trim();
for (const name of ['HTTPS_PROXY', 'HTTP_PROXY', 'https_proxy', 'http_proxy']) {
  if (!process.env[name] && hostEnv[name]) process.env[name] = hostEnv[name];
}

function fail(reason, code = 2) {
  console.log(JSON.stringify({ source: 'none', reason }, null, 2));
  process.exit(code);
}

if (!url || !key) fail('kanban credentials missing（宿主环境或 ~/.union-kanban.env）');

async function api(pathname, { method = 'GET', body } = {}) {
  const response = await fetch(`${url}/api${pathname}`, {
    method,
    headers: {
      authorization: `Bearer ${key}`,
      accept: 'application/json',
      ...(body ? { 'content-type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(30_000),
  });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = { raw: text.slice(0, 500) }; }
  if (!response.ok) {
    const error = new Error(`在线看板 ${method} ${pathname} → HTTP ${response.status}: ${payload?.error ?? text.slice(0, 200)}`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

const clip = (value, size = 700) => {
  const text = String(value ?? '').replace(/\s*\n\s*/g, ' ').trim();
  return text.length > size ? `${text.slice(0, size)}…` : text;
};

async function main() {
  const ask = flag('ask');
  if (ask !== undefined) {
    const body = ask.trim();
    if (!body) fail('--ask 需要一段求助内容');
    const replyTo = flag('reply') === undefined ? null : Number(flag('reply'));
    if (replyTo !== null && !Number.isInteger(replyTo)) fail('--reply 需要整数留言编号');
    const payload = await api('/messages', {
      method: 'POST',
      body: { body, reply_to: replyTo, client_id: randomUUID() },
    });
    const posted = payload?.message ?? payload;
    console.log(JSON.stringify({ posted: { id: posted?.id ?? null, reply_to: posted?.reply_to ?? replyTo, at: posted?.created_at ?? null } }, null, 2));
    return;
  }

  const limit = Math.max(1, Math.min(100, Number(flag('limit') || 30)));
  const board = await api('/board');
  const members = new Map((board.members || []).map((member) => [member.id, member.name]));
  const tasks = new Map((board.tasks || []).map((task) => [Number(task.id), task]));
  const activities = (board.activities || []).slice(0, limit);
  const messagePayload = await api('/messages?limit=50');
  const messages = Array.isArray(messagePayload?.messages) ? messagePayload.messages : [];

  const uOf = (task) => (/U-\d{3}/.exec(task?.title || '') || [])[0] || null;
  const taskLabel = (id) => {
    const task = tasks.get(Number(id));
    return task ? `${uOf(task) ?? `#${id}`} ${clip(task.title, 80)}` : `#${id}`;
  };
  const taskOf = (id) => tasks.get(Number(id)) || null;

  const commentsByTask = new Map();
  const commentTasks = [...new Set(activities.filter((a) => a.action === 'commented' && a.task_id).map((a) => Number(a.task_id)))];
  for (const id of commentTasks) {
    try {
      const payload = await api(`/tasks/${id}/comments`);
      commentsByTask.set(id, Array.isArray(payload) ? payload : payload?.comments ?? []);
    } catch { /* 读不到评论不阻断整体动态 */ }
  }
  const messageById = new Map(messages.map((message) => [Number(message.id), message]));

  const detailOf = (activity) => {
    if (typeof activity.detail === 'string') {
      try { return JSON.parse(activity.detail); } catch { return {}; }
    }
    return activity.detail || {};
  };

  const recent = activities.map((activity) => {
    const detail = detailOf(activity);
    let text = '';
    if (activity.action === 'commented') {
      const comment = (commentsByTask.get(Number(activity.task_id)) || []).find((item) => Number(item.id) === Number(detail.comment_id));
      text = comment?.body ?? '';
    } else if (activity.action === 'message_posted') {
      text = messageById.get(Number(detail.message_id))?.body ?? '';
    } else {
      text = detail.summary ?? detail.title ?? detail.status ?? '';
    }
    return {
      at: activity.created_at,
      member: members.get(activity.member_id) ?? activity.member_id ?? 'unknown',
      action: activity.action,
      task: activity.task_id ? taskLabel(activity.task_id) : null,
      text: clip(text),
    };
  });

  const asks = [];
  for (const message of messages) {
    if (message.deleted_at || message.reply_to) continue;
    const replied = messages.some((candidate) => Number(candidate.reply_to) === Number(message.id) && !candidate.deleted_at);
    const looksLikeAsk = /求助|请求|需要|协助|帮忙|阻塞|问题|失败|不确定|复核|补充|支持/i.test(message.body || '');
    if (!replied && looksLikeAsk) {
      asks.push({
        kind: 'message',
        id: message.id,
        at: message.created_at,
        member: message.author_name ?? members.get(message.member_id) ?? message.member_id,
        text: clip(message.body, 900),
      });
    }
  }
  for (const task of board.tasks || []) {
    if (task.archived || task.status !== 'blocked') continue;
    const comments = commentsByTask.get(Number(task.id)) ?? [];
    const latest = comments[comments.length - 1];
    asks.push({
      kind: 'blocked_card',
      id: task.id,
      u: uOf(task),
      at: latest?.created_at ?? task.updated_at ?? null,
      member: members.get(task.assignee) ?? task.assignee ?? null,
      text: clip(`[blocked] ${task.title} · 阻塞：${task.blocker ?? '（未填写）'}${latest ? ` · 最新评论：${latest.body}` : ''}`, 900),
    });
  }

  const blocked = (board.tasks || [])
    .filter((task) => !task.archived && task.status === 'blocked')
    .map((task) => ({
      u: uOf(task),
      title: clip(task.title, 90),
      owner: members.get(task.assignee) ?? task.assignee ?? null,
      version: task.version,
      blocker: clip(task.blocker, 400),
    }));

  console.log(JSON.stringify({
    source: 'online',
    generated_at: new Date().toISOString(),
    board_revision: board.revision ?? null,
    me: board.user?.name ?? board.user?.id ?? null,
    blocked,
    asks,
    recent,
    messages: messages.slice(0, 20).map((message) => ({
      id: message.id,
      at: message.created_at,
      member: message.author_name ?? members.get(message.member_id) ?? message.member_id,
      reply_to: message.reply_to,
      deleted: Boolean(message.deleted_at),
      text: clip(message.body, 700),
    })),
  }, null, 2));
}

main().catch((error) => {
  console.log(JSON.stringify({ source: 'online', error: error.message, status: error.status ?? null }, null, 2));
  process.exit(3);
});
