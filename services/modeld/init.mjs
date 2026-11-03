import { mkdirSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { resolve, join } from 'node:path';
if (!process.argv[2]) throw new Error('Usage: node services/modeld/init.mjs PRIVATE_DIRECTORY');
const root = resolve(process.argv[2]);
mkdirSync(root, { recursive: true, mode: 0o700 });
// Exclusive creation: never replace an existing credential or deployment configuration.
for (const name of ['admin', 'worker']) writeFileSync(join(root, name + '.token'), randomBytes(48).toString('base64url'), { flag: 'wx', mode: 0o600 });
writeFileSync(join(root, 'modeld.json'), JSON.stringify({ origin: 'http://127.0.0.1:4098', state_directory: 'state',
  admin_token_file: 'admin.token', worker_token_file: 'worker.token' }, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
console.log('Private service configuration created; no account or model request started.');
