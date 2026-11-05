import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.txt': 'text/plain', '.xml': 'application/xml' };
const assets = {};
for (const name of (await readdir(path.join(root, 'public'))).sort()) {
  const content = await readFile(path.join(root, 'public', name), 'utf8');
  assets['/' + name] = { content, type: types[path.extname(name)] + '; charset=utf-8', etag: '"' + createHash('sha256').update(content).digest('hex') + '"' };
}
const handler = await readFile(path.join(root, 'handler.mjs'), 'utf8');
await mkdir(path.join(root, 'dist'), { recursive: true });
await writeFile(path.join(root, 'dist', 'worker.mjs'), 'const assets = ' + JSON.stringify(assets) + ';\n' + handler);
console.log('Built website/dist/worker.mjs (' + Object.keys(assets).length + ' assets)');
