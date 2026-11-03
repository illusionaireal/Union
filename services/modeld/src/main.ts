import { readFileSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { Kernel, UPSTREAM } from './kernel';
import { startService } from './server';
import { requireValue } from './journal';

function privateFile(path: string) {
  const stat = statSync(path);
  requireValue(stat.isFile() && (process.platform === 'win32' || (stat.mode & 0o077) === 0), 'private_config_required');
  return readFileSync(path, 'utf8');
}
const configPath = resolve(process.env.UNION_MODELD_CONFIG ?? process.argv[2] ?? '');
try {
  const config = JSON.parse(privateFile(configPath));
  const origin = new URL(config.origin);
  requireValue(origin.protocol === 'http:' && origin.hostname === '127.0.0.1' && origin.pathname === '/' &&
    !origin.username && !origin.password && !origin.search && !origin.hash, 'invalid_model_service_origin');
  const directory = resolve(dirname(configPath), config.state_directory);
  const service = await startService({ directory, port: Number(origin.port || 80), upstream: UPSTREAM,
    adminToken: privateFile(resolve(dirname(configPath), config.admin_token_file)).trim(),
    workerToken: privateFile(resolve(dirname(configPath), config.worker_token_file)).trim(),
    kernel: () => Kernel.create(resolve(directory, 'kernel')) });
  console.log('UNION model service ready (loopback, authenticated, no model request started)');
  let closed = false;
  for (const signal of ['SIGINT', 'SIGTERM'] as const) process.on(signal, async () => {
    if (closed) return; closed = true;
    await service.close(); process.exit(0);
  });
} catch { console.error('UNION model service could not start; check private configuration and instance ownership.'); process.exit(1); }
