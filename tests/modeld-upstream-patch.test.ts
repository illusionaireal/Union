import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import test from 'node:test';
import { assertRecordedUpstreamPatch } from '../services/modeld/verify-upstream.mjs';

function fixture(t) {
  const directory = mkdtempSync(join(tmpdir(), 'union-modeld-patch-'));
  t.after(() => {
    assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
    rmSync(directory, { recursive: true, force: true });
  });
  const git = (...args) => execFileSync('git', args, {
    cwd: directory, encoding: 'utf8', windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
  git('init', '--quiet');
  git('config', 'core.autocrlf', 'false');
  git('config', 'core.hooksPath', join(directory, 'no-hooks'));
  git('config', 'core.abbrev', '7');
  const source = join(directory, 'kernel.ts');
  writeFileSync(source, 'const provider = "fixed";\nconst version = 1;\n');
  git('add', 'kernel.ts');
  git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
      '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Synthetic pinned source');
  writeFileSync(source, 'export const provider = "fixed";\nconst version = 1;\n');
  const expected = git('diff', '--no-ext-diff', '--abbrev=7');
  return { directory, git, source, expected };
}

for (const abbreviation of ['12', '40']) {
  test(`recorded patch remains valid with Git core.abbrev=${abbreviation}`, t => {
    const f = fixture(t);
    f.git('config', 'core.abbrev', abbreviation);
    // Real Git produces different index formatting for identical source bytes.
    assert.notEqual(f.git('diff', '--no-ext-diff'), f.expected);
    assert.doesNotThrow(() => assertRecordedUpstreamPatch(f.directory, f.expected));
    assert.equal(f.git('config', '--get', 'core.abbrev'), abbreviation);
  });
}

test('the complete comparison still rejects additional tracked source changes', t => {
  const f = fixture(t);
  assert.doesNotThrow(() => assertRecordedUpstreamPatch(f.directory, f.expected));
  writeFileSync(f.source, readFileSync(f.source, 'utf8') + 'export const unrecorded = true;\n');
  assert.throws(() => assertRecordedUpstreamPatch(f.directory, f.expected), /Unrecorded upstream changes/);
});

test('normalizes recorded line endings while retaining index and hunk validation', t => {
  const f = fixture(t);
  assert.doesNotThrow(() => assertRecordedUpstreamPatch(f.directory, f.expected.replaceAll('\n', '\r\n')));
  assert.throws(() => assertRecordedUpstreamPatch(f.directory, f.expected.replace('index ', 'index 0')),
                /Unrecorded upstream changes/);
});
