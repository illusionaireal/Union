// Structural evidence for this design revision; does not prove product behavior.
import assert from 'node:assert/strict';
import { readFileSync, existsSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

const read = path => readFileSync(path, 'utf8');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const charterBytes = readFileSync('docs/UNION_CHARTER_v1.0.md');
const charterHash = hash(charterBytes);
assert.equal(charterHash, '01b2c7f0b40be6e761376cd719e2c7b61c0d782df6f53ca9b9e4ad0ad50e6174');
const ids = [...charterBytes.toString('utf8').matchAll(/^\* \*\*([A-Z]-\d{2}) /gm)].map(m => m[1]);
const trace = read('specs/053-union-rewrite/charter-traceability.md');
const rows = [...trace.matchAll(/^\| ([A-Z]-\d{2}) \|/gm)].map(m => m[1]);
assert.equal(ids.length, 40);
assert.equal(rows.length, 40);
assert.deepEqual([...rows].sort(), [...ids].sort());
assert.equal(new Set(rows).size, 40);

const product = read('docs/product-design.md');
const frontend = read('docs/FRONTEND.md');
const journeys = [...product.matchAll(/^\| (VJ\d{2}) [^|]+\| ([^|]+) \|/gm)];
const ux = [...product.matchAll(/^\| (UX-\d{2}) \|/gm)].map(m => m[1]);
assert.equal(journeys.length, 10);
assert.equal(new Set(journeys.map(m => m[1])).size, 10);
assert.equal(ux.length, 10);
const mapping = ['J01', 'J02', 'J03', 'J03', 'J04', 'J05', 'J05', 'F19 / J04', 'J07', 'J06'];
assert.deepEqual(journeys.map(m => m[2].trim()), mapping);
const journeyIds = new Set(journeys.map(m => m[1]));
for (const match of trace.matchAll(/VJ\d{2}/g)) assert(journeyIds.has(match[0]));
for (const suffix of 'abcdef') assert(trace.includes(suffix === 'a' ? 'X-01(a)' : '(' + suffix + ')'));
for (const suffix of 'abcde') assert(trace.includes(suffix === 'a' ? 'X-02(a)' : '(' + suffix + ')'));
assert(product.includes('/au/:auId/work/:workId/results/:resultId'));
assert(!product.includes('/au/:auId/results/:resultId'));
assert(frontend.includes('WorkService.result_content'));
assert(read('ai_union/application/work.py').includes('def result_content('));
assert(product.includes('会话到期不丢运行责任'));

const files = ['docs/product-design.md', 'docs/FRONTEND.md', 'docs/PRD.md',
  'docs/FORMAL_DEVELOPMENT.md', 'specs/053-union-rewrite/charter-traceability.md'];
let links = 0;
for (const file of files) {
  for (const match of read(file).matchAll(/\[[^\]]+\]\(([^)]+)\)/g)) {
    const target = match[1].split('#')[0];
    if (!target || /^[a-z]+:/i.test(target)) continue;
    assert(existsSync(resolve(dirname(file), decodeURIComponent(target))), file + ': missing ' + target);
    links += 1;
  }
}
const marker = '<a id="u-065-development"></a>';
const historicalFile = 'specs/053-union-rewrite/tasks.md';
const before = execFileSync('git', ['show', 'd27d543e044a4111204c898130f9187c9e4770f7:' + historicalFile], { encoding: 'utf8' });
const after = read(historicalFile);
assert(before.includes(marker) && after.includes(marker));
assert.equal(after.slice(after.indexOf(marker)), before.slice(before.indexOf(marker)));
const result = {
  date: '2026-11-13', scope: 'documentation structure and checked source references only',
  charter_sha256: charterHash, normative_rows: rows.length, unique_rows: new Set(rows).size,
  journeys: journeys.length, acceptance_rows: ux.length, local_link_targets: links,
  historical_appendix_sha256: hash(after.slice(after.indexOf(marker))),
  result: 'pass', limitations: 'No browser, model, runtime, authorization or sustained-operation acceptance. Subclause semantics independently reviewed.'
};
writeFileSync('evidence/U-110/design-structure.json', JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result));
