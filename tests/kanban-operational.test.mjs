import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

async function fixture(t, options = {}) {
  const root = mkdtempSync(join(tmpdir(), 'union-live-board-'));
  mkdirSync(join(root, 'management'));
  writeFileSync(join(root, 'management/project.json'), '{invalid historical mirror');
  writeFileSync(join(root, 'proof.md'), 'actual controlled evidence');
  const task = { id: 31, title: 'Online-only task · U-077', status: 'ready', assignee: null,
    version: 4, archived: 0, priority: 'P0', dependencies: [], ...options.task };
  const board = { user: { id: 'member-real', name: 'reviewer', active: 1 }, members: [],
    tasks: [task, ...(options.extra ?? [])], revision: 8, ...options.board };
  const calls = [];
  const server = http.createServer(async (req, res) => {
    let raw = ''; for await (const data of req) raw += data;
    calls.push({ method: req.method, url: req.url, body: raw ? JSON.parse(raw) : null });
    res.setHeader('Content-Type', 'application/json');
    if (req.method === 'GET' && req.url === '/api/board') return res.end(JSON.stringify(board));
    if (req.method === 'PATCH') {
      if (options.failPatch) { res.statusCode = options.failPatch; return res.end(JSON.stringify({error:'conflict'})); }
      Object.assign(task, JSON.parse(raw), {version: task.version + 1});
      if (options.lostResponse) return req.socket.destroy();
      if (options.acceptedOnly) res.statusCode = 202;
      return res.end(JSON.stringify(task));
    }
    res.statusCode = 404; res.end('{}');
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  t.after(async () => { server.closeAllConnections(); await new Promise(r => server.close(r)); rmSync(root, { recursive: true, force: true }); });
  const env = { ...process.env, UNION_REPO_ROOT: root, UNION_BOARD_SOURCE: 'kanban',
    UNION_KANBAN_URL: `http://127.0.0.1:${server.address().port}`, UNION_KANBAN_KEY: 'test-key',
    UNION_KANBAN_CONFIG: join(root, 'missing.env'), ...(options.env ?? {}),
    HTTP_PROXY: '', HTTPS_PROXY: '', ALL_PROXY: '', NODE_USE_ENV_PROXY: '', NO_PROXY: '127.0.0.1' };
  function run(script, args, input) {
    return new Promise((resolveRun, reject) => {
      const child = spawn(process.execPath, [resolve('scripts', script), ...args], { env, windowsHide: true });
      let output = ''; child.stdout.on('data', d => output += d); child.stderr.on('data', d => output += d);
      child.on('error', reject); child.on('close', code => resolveRun({code, output})); child.stdin.end(input);
    });
  }
  return { root, task, board, calls, pick: () => run('../ops/automation/pick-next.mjs', []), cli: (...args) => run('project-management.mjs', args),
    mcp: (name, args) => run('union-board-mcp.mjs', [], JSON.stringify({jsonrpc:'2.0', id:1, method:'tools/call', params:{name,arguments:args}})+'\n') };
}

test('CLI claims online-only card with real user/version without reading damaged local mirror', async t => {
  const f = await fixture(t);
  const result = await f.cli('claim', 'U-077', '--actor', 'codex/test');
  assert.equal(result.code, 0, result.output);
  assert.equal(f.task.assignee, 'member-real');
  assert.equal(f.task.status, 'progress');
  assert.equal(f.calls.find(c => c.method === 'PATCH').body.version, 4);
  assert.equal(readFileSync(join(f.root, 'management/project.json'), 'utf8'), '{invalid historical mirror');
});

test('CLI refuses a foreign assignee and unmet dependencies before PATCH', async t => {
  for (const task of [{assignee:'someone-else'}, {dependencies:[99]}]) {
    const f = await fixture(t, {task}); const result = await f.cli('claim', 'U-077', '--actor', 'codex/test');
    assert.notEqual(result.code, 0); assert.equal(f.calls.filter(c => c.method === 'PATCH').length, 0);
    assert.ok(f.calls.some(c => c.method === 'GET'), 'refusal must use online facts');
  }
});

test('MCP uses the same owner protection and does not steal a card', async t => {
  const f = await fixture(t, {task:{assignee:'someone-else'}});
  const result = await f.mcp('union_card_claim', {id:'U-077', actor:'codex/test'});
  const answer = JSON.parse(result.output.split('\n').find(line => line.startsWith('{')));
  assert.equal(answer.result.isError, true);
  assert.equal(f.calls.filter(c => c.method === 'PATCH').length, 0);
});

test('409 produces one PATCH, reads back the card and preserves mirror', async t => {
  const f = await fixture(t, {failPatch:409});
  const result = await f.cli('claim', 'U-077', '--actor', 'codex/test');
  assert.notEqual(result.code, 0);
  assert.equal(f.calls.filter(c => c.method === 'PATCH').length, 1);
  assert.equal(f.calls.filter(c => c.method === 'GET').length, 2);
});

test('completion without real evidence is refused before changing online status', async t => {
  const f = await fixture(t, {task:{status:'progress',assignee:'member-real'}});
  const result = await f.mcp('union_card_record', {id:'U-077',actor:'codex/test',scope:'controlled',reviewer:'reviewer',note:'done',evidence:['absent.md']});
  assert.match(result.output, /isError/);
  assert.equal(f.calls.filter(c => c.method === 'PATCH').length, 0);
});

test('configured live WIP includes blocked work and refuses a further claim', async t => {
  const f = await fixture(t, {board:{wip_limit:1},extra:[{id:9,title:'Waiting · U-009',priority:'P1',status:'blocked',assignee:'other',archived:0,dependencies:[]}]});
  const result = await f.cli('claim', 'U-077', '--actor', 'codex/test');
  assert.notEqual(result.code,0); assert.equal(f.calls.filter(c => c.method==='PATCH').length,0);
  assert.match(result.output,/WIP/);
});


test('lost PATCH response and HTTP 202 are read back without replay', async t => {
  for (const options of [{lostResponse:true}, {acceptedOnly:true}]) {
    const f = await fixture(t, options);
    const result = await f.cli('claim', 'U-077', '--actor', 'codex/test');
    assert.notEqual(result.code, 0, result.output);
    assert.equal(f.task.assignee, 'member-real');
    assert.equal(f.calls.filter(c => c.method === 'PATCH').length, 1);
    assert.equal(f.calls.filter(c => c.method === 'GET').length, 2);
    assert.match(result.output, /no retry; readback/);
  }
});

test('successful CLI and MCP records preserve complete evidence without a second write', async t => {
  for (const entry of ['cli', 'mcp']) {
    const f = await fixture(t, {task:{status:'progress',assignee:'member-real'}});
    const result = entry === 'cli'
      ? await f.cli('record','U-077','--actor','codex/test','--scope','controlled','--reviewer','independent','--note','checked','--evidence','proof.md')
      : await f.mcp('union_card_record',{id:'U-077',actor:'codex/test',scope:'controlled',reviewer:'independent',note:'checked',evidence:['proof.md']});
    assert.equal(result.code, 0, result.output);
    assert.equal(f.task.status, 'done', result.output);
    assert.match(f.task.evidence, /proof.md/);
    assert.match(f.task.evidence, /independent/);
    assert.equal(f.calls.filter(c => c.method !== 'GET').length, 1);
  }
});

test('own started claim is idempotent and cannot release or force-hide started work', async t => {
  const f = await fixture(t, {task:{status:'blocked',assignee:'member-real'}});
  assert.equal((await f.cli('claim','U-077','--actor','codex/test')).code, 0);
  assert.notEqual((await f.cli('release','U-077','--actor','codex/test','--force')).code, 0);
  assert.notEqual((await f.cli('move','U-077','ready','--actor','codex/test','--force','--note','erase')).code, 0);
  assert.equal(f.calls.filter(c => c.method === 'PATCH').length, 0);
});

test('missing credentials never fall back to a local operational write', async t => {
  const f = await fixture(t, {env:{UNION_KANBAN_URL:'',UNION_KANBAN_KEY:''}});
  assert.notEqual((await f.cli('claim','U-077','--actor','codex/test')).code, 0);
  assert.equal(f.calls.length, 0);
});

test('status reads online despite damaged historical ledger and exposes absent WIP configuration', async t => {
  const f = await fixture(t);
  const result = await f.cli('status');
  assert.equal(result.code, 0, result.output);
  const view = JSON.parse(result.output);
  assert.equal(view.source, 'kanban');
  assert.equal(view.wip_limit, null);
});

test('picker resumes only current user, does not select foreign work or backlog, and counts blocked WIP', async t => {
  const f = await fixture(t, {board:{wip_limit:1},extra:[
    {id:22,title:'Foreign · U-067',status:'progress',assignee:'other',archived:0,priority:'P0',dependencies:[]},
    {id:23,title:'Backlog · U-068',status:'backlog',assignee:null,archived:0,priority:'P0',dependencies:[]},
    {id:24,title:'Blocked · U-069',status:'blocked',assignee:'other',archived:0,priority:'P1',dependencies:[]}
  ]});
  const result = await f.pick();
  assert.equal(result.code, 0, result.output);
  const view = JSON.parse(result.output);
  assert.equal(view.next, null);
  assert.equal(view.in_flight, 2);
  assert.equal(view.wip_limit, 1);
  assert.deepEqual(view.resume, []);
});
