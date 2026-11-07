import fs from 'node:fs';
import path from 'node:path';

const V1_PREFIX = 'U-0';
const WIP_LIMIT = Number(process.env.UNION_WIP_LIMIT || 6);
const ORDER = (id) => Number(String(id).replace('U-', ''));

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
const url = (process.env.UNION_KANBAN_URL || hostEnv.UNION_KANBAN_URL || '').trim().replace(/\/$/, '');
const key = (process.env.UNION_KANBAN_KEY || hostEnv.UNION_KANBAN_KEY || '').trim();
for (const k of ['HTTPS_PROXY', 'HTTP_PROXY']) {
  if (!process.env[k] && hostEnv[k]) process.env[k] = hostEnv[k];
}

if (!url || !key) {
  console.log(JSON.stringify({ source: 'none', reason: 'kanban credentials missing' }));
  process.exit(2);
}

let res;
try {
  res = await fetch(`${url}/api/board`, { headers: { Authorization: `Bearer ${key}` } });
} catch (error) {
  console.log(JSON.stringify({ source: 'online', reason: `board unreachable: ${error.message}` }));
  process.exit(3);
}
if (!res.ok) {
  console.log(JSON.stringify({ source: 'online', reason: `board read failed HTTP ${res.status}` }));
  process.exit(3);
}
const board = await res.json();
const cards = (board.tasks || []).filter((c) => !c.archived);

const idOf = (title) => (/U-\d{3}/.exec(title || '') || [])[0] || null;
const byTask = new Map();
for (const c of cards) {
  const id = idOf(c.title);
  if (id) byTask.set(id, c);
}

const byCardId = new Map();
for (const [id, c] of byTask) byCardId.set(String(c.id), id);

const DONE = new Set([...byTask.entries()].filter(([, c]) => c.status === 'done').map(([id]) => id));
const inFlight = cards.filter((c) => ['progress', 'review'].includes(c.status));
const eligible = [];
for (const [id, c] of byTask) {
  if (!id.startsWith(V1_PREFIX)) continue;
  if (!['backlog', 'ready'].includes(c.status)) continue;
  const deps = (c.dependencies || []).map((d) => byCardId.get(String(d)) || String(d));
  const missing = deps.filter((d) => !DONE.has(d));
  if (missing.length === 0) eligible.push({ id, card: c.id, version: c.version, status: c.status, title: c.title, deps });
  else eligible.push({ blocked: id, missing });
}

const ready = eligible.filter((e) => !e.blocked).sort((a, b) => ORDER(a.id) - ORDER(b.id));
const blocked = eligible.filter((e) => e.blocked);

// Resuming in-flight work comes first: an already-claimed card that is not done
// is the most valuable thing to advance, and starting new cards while old ones
// sit in progress would just raise WIP.
const resume = cards
  .filter((c) => ['progress', 'review'].includes(c.status))
  .map((c) => ({ id: idOf(c.title), card: c.id, version: c.version, status: c.status, title: c.title }))
  .filter((c) => c.id && c.id.startsWith(V1_PREFIX))
  .sort((a, b) => ORDER(a.id) - ORDER(b.id));

const next = resume[0] || (inFlight.length >= WIP_LIMIT ? null : ready[0] || null);
console.log(JSON.stringify({
  source: 'online',
  generated_at: new Date().toISOString(),
  revision: board.revision ?? null,
  in_flight: inFlight.length,
  resume,
  wip_limit: WIP_LIMIT,
  ready: ready.map((r) => ({ id: r.id, card: r.card, version: r.version, status: r.status, title: r.title, deps: r.deps })),
  blocked: blocked.map((b) => ({ id: b.blocked, missing: b.missing })),
  done: [...DONE].sort(),
  next,
  all_v1_done: cards.filter((c) => idOf(c.title)?.startsWith(V1_PREFIX)).every((c) => c.status === 'done'),
}, null, 2));
