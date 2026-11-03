import { resolve, dirname, join } from 'node:path';
import { copyFileSync, existsSync, readFileSync } from 'node:fs';
const result = await Bun.build({ entrypoints: [resolve(import.meta.dir, 'src/main.ts')],
  target: 'bun', outdir: resolve(import.meta.dir, 'dist'), minify: false, sourcemap: 'external' });
if (!result.success) { console.error(result.logs); process.exit(1); }
for (const [source, target] of [['vendor/opencode/LICENSE','LICENSE.opencode'], ['upstream.lock.json','upstream.lock.json']])
  copyFileSync(resolve(import.meta.dir, source), resolve(import.meta.dir, 'dist', target));
const installed = resolve(import.meta.dir, 'vendor/opencode/node_modules/.bun'), notices = new Map<string, unknown>();
for await (const name of new Bun.Glob('*/node_modules/**/package.json').scan({ cwd:installed, followSymlinks:false })) {
  const path = join(installed, name), pkg = JSON.parse(readFileSync(path, 'utf8'));
  if (!pkg.name || !pkg.version) continue;
  const license = ['LICENSE','LICENSE.md','LICENSE.txt','license','license.md','license.txt'].map(n => join(dirname(path),n)).find(existsSync);
  notices.set(pkg.name + '@' + pkg.version, { name:pkg.name, version:pkg.version, license:pkg.license ?? null,
    text:license ? readFileSync(license,'utf8') : null });
}
await Bun.write(resolve(import.meta.dir,'dist/THIRD_PARTY_NOTICES.json'), JSON.stringify([...notices.entries()].sort().map(([,v])=>v),null,2)+'\n');
console.log('Built UNION model service from pinned source');
