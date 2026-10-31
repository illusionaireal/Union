"""No credentials/models. Record actual tool versions and Codex sandbox exit."""
import json
from pathlib import Path
import subprocess

root = Path('/volume1/docker/union-dev/install')
image = 'union-dev-tools:2026-11-01'
common = ['/usr/local/bin/docker', 'run', '--rm', '--read-only', '--cap-drop', 'ALL',
          '--security-opt', 'no-new-privileges', '--user', '10002:10001',
          '--tmpfs', '/tmp:rw,exec,uid=10002,gid=10001',
          '--tmpfs', '/run/union:rw,exec,uid=10002,gid=10001',
          '-e', 'CODEX_HOME=/run/union/codex', image]
results = []
for name, argv in [('versions', ['sh', '-ec', 'node --version; python3 --version; codex --version; chromium --version']),
                   ('sandbox', ['sh', '-ec', 'mkdir -p /run/union/codex; exec codex sandbox linux -- sh -c "echo SANDBOX_COMMAND_RAN"'])]:
    result = subprocess.run(common + argv, capture_output=True, text=True, timeout=60)
    (root / (name + '.stdout.log')).write_text(result.stdout)
    (root / (name + '.stderr.log')).write_text(result.stderr)
    results.append({'check': name, 'argv': common + argv, 'exit_code': result.returncode,
                    'command_ran': 'SANDBOX_COMMAND_RAN' in result.stdout})
(root / 'diagnostics.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
