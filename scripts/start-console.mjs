// Build and serve one same-origin application. No credentials pass through this wrapper.
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { ensurePython } from './ensure-python.mjs';
const root = fileURLToPath(new URL('../', import.meta.url));
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
let python;
try { python = await ensurePython(root); }
catch (error) { console.error(error.message); process.exit(1); }
const args = process.argv.slice(2);
const watch = args[0] === '--watch';
if (watch) args.shift();
function launch(command, arguments_) {
  return spawn(command, arguments_, { cwd: root, stdio: 'inherit', shell: process.platform === 'win32' && command === npm });
}
const build = launch(npm, ['run', 'build:console']);
const result = await new Promise(resolve => { build.once('error', error => { console.error(error.message); resolve(1); }); build.once('exit', resolve); });
if (result !== 0) process.exit(typeof result === 'number' ? result : 1);
const watcher = watch ? launch(npm, ['run', 'dev:console']) : null;
const server = launch(python, ['-m', 'ai_union.server', ...args]);
function stop() { server.kill(); watcher?.kill(); }
process.on('SIGINT', stop); process.on('SIGTERM', stop);
server.on('error', error => { console.error(error.message); watcher?.kill(); process.exitCode = 1; });
server.on('exit', code => { watcher?.kill(); process.exitCode = code ?? 0; });
