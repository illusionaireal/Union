// Use a project virtual environment; never install packages into system Python.
import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

function invoke(command, args, root, quiet = false) {
  return new Promise(resolve => {
    const child = spawn(command, args, { cwd: root, stdio: quiet ? 'ignore' : 'inherit' });
    child.once('error', () => resolve(1));
    child.once('exit', code => resolve(code ?? 1));
  });
}

export async function ensurePython(root) {
  const windows = process.platform === 'win32';
  const configured = process.env.UNION_PYTHON;
  const local = path.join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
  const check = ['-c', "from importlib.metadata import version; assert version('deepagents') == '0.7.28'; assert version('langgraph-checkpoint-sqlite') == '3.1.2'"];
  if (configured) {
    if (await invoke(configured, check, root, true) !== 0)
      throw new Error('UNION_PYTHON 指定的解释器缺少 Harness 依赖。请先用该 Python 执行 -m pip install -r requirements-harness.lock -e .');
    return configured;
  }
  if (!existsSync(local)) {
    console.log('正在为 UNION 建立 Python 虚拟环境…');
    if (await invoke(windows ? 'python' : 'python3', ['-m', 'venv', '.venv'], root) !== 0)
      throw new Error('无法建立 Python 环境；请安装 Python 3.11+（Linux 还需 python3-venv）。');
  }
  if (await invoke(local, check, root, true) !== 0) {
    console.log('正在安装固定版本的 Agent Harness 依赖…');
    if (await invoke(local, ['-m', 'pip', 'install', '-r', 'requirements-harness.lock', '-e', '.'], root) !== 0)
      throw new Error('Harness 依赖安装失败；检查网络后重新运行 npm start。');
  }
  return local;
}
