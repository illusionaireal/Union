import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
const json = path => JSON.parse(readFileSync(new URL('../'+path,import.meta.url),'utf8'));
const {tasks} = json('docs/kickoff/tasks.json');
const byId = new Map(tasks.map(t=>[t.id,t]));
assert.equal(tasks.length,82);assert.equal(byId.size,82);
for (const [prefix,count] of [['PLAN',6],['OPS',40],['ENG',36]])
  for(let i=1;i<=count;i++) assert(byId.has(`${prefix}-${String(i).padStart(3,'0')}`));
const active=new Set(), done=new Set();
function visit(id) {
  assert(!active.has(id),`cycle: ${[...active,id].join(' -> ')}`);
  if(done.has(id)) return;
  active.add(id);
  for(const dep of byId.get(id).dependencies) {
    assert(byId.has(dep),`${id} missing ${dep}`);
    if(byId.get(id).status!=='延期') assert.notEqual(byId.get(dep).status,'延期',`${id} depends on deferred ${dep}`);
    visit(dep);
  }
  active.delete(id);done.add(id);
}
for(const t of tasks) {
  visit(t.id);
  const source=readFileSync(new URL('../'+t.source,import.meta.url),'utf8');
  assert(source.includes(t.detail),`${t.id} detail differs from baseline`);
  const line=t.detail.match(/^\*\*依赖\*\*：(.+)$/m);
  assert.deepEqual(t.dependencies,[...line[1].matchAll(/(?:PLAN|OPS|ENG)-\d{3}/g)].map(m=>m[0]));
}
for(const [name,hash] of Object.entries(json('docs/kickoff/baseline-sha256.json'))) {
  const path=new URL('../docs/baseline/'+name,import.meta.url);
  const content=readFileSync(path);
  assert.equal(createHash('sha256').update(content).digest('hex'),hash,`baseline changed: ${name}`);
  for(const [,href] of content.toString().matchAll(/\]\(([^)]+\.md)\)/g)) {
    if(!/^[a-z]+:/i.test(href)) assert(existsSync(new URL(href,path)),`broken link ${name}: ${href}`);
  }
}
const mapping=json('docs/kickoff/github-issues.json');
assert.equal(new Set(mapping.issues.map(i=>i.id)).size,mapping.issues.length);
for(const issue of mapping.issues) assert(byId.has(issue.id),`unrecognized GitHub task ${issue.id}`);
console.log(JSON.stringify({baseline:'UNION-B1',tasks:tasks.length,dependencies:tasks.reduce((n,t)=>n+t.dependencies.length,0),cycles:0,missingDependencies:0,baselineFiles:5,githubTasks:mapping.issues.length}));
