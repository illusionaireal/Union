import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync, mkdirSync, realpathSync, symlinkSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = dirname(fileURLToPath(import.meta.url)), vendor = join(root, 'vendor/opencode');
const lock = JSON.parse(readFileSync(join(root, 'upstream.lock.json'), 'utf8'));
const bun = process.env.UNION_BUN || 'bun';
const bunVersion = execFileSync(bun, ['--version'], { encoding: 'utf8' }).trim();
if (bunVersion !== lock.tested_bun) throw new Error('Use Bun ' + lock.tested_bun + ' (UNION_BUN may select the executable)');
const run = (cmd, args, cwd = vendor) => execFileSync(cmd, args, { cwd, stdio: 'inherit', windowsHide: true });
run('git', ['submodule', 'update', '--init', '--', 'vendor/opencode'], root);
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: vendor, encoding: 'utf8' }).trim();
if (commit !== lock.commit) throw new Error('Upstream commit does not match lock');
for (const [name, hash] of Object.entries(lock.files)) {
  if (createHash('sha256').update(readFileSync(join(root, name), 'utf8').replaceAll('\r\n','\n')).digest('hex') !== hash)
    throw new Error('Upstream integrity mismatch: ' + name);
}
const patch = join(root, lock.patch);
try { execFileSync('git', ['apply', '--reverse', '--check', patch], { cwd: vendor, stdio: 'ignore' }); }
catch { run('git', ['apply', '--check', patch]); run('git', ['apply', patch]); }
const expected = readFileSync(patch, 'utf8').replaceAll('\r\n','\n').trim();
const actual = execFileSync('git', ['diff', '--no-ext-diff'], { cwd: vendor, encoding: 'utf8' }).replaceAll('\r\n','\n').trim();
if (actual !== expected) throw new Error('Unrecorded upstream changes');
run(bun, ['install', '--frozen-lockfile', '--ignore-scripts', '--filter', '@opencode/ai', '--filter', '@opencode/core']);
const coreRequire = createRequire(join(vendor, 'packages/core/package.json'));
const effectRoot = dirname(realpathSync(coreRequire.resolve('effect/package.json')));
mkdirSync(join(root, 'node_modules'), { recursive: true });
const effectLink = join(root, 'node_modules/effect');
if (!existsSync(effectLink)) symlinkSync(effectRoot, effectLink, process.platform === 'win32' ? 'junction' : 'dir');
else if (realpathSync(effectLink) !== effectRoot) throw new Error('Unexpected Effect installation');
run(bun, ['run', 'build.ts'], root);
