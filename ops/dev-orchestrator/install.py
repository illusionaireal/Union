"""Run once as host root: python3 install.py /volume1/docker/union-dev.

Idempotent service installation; does not enable model dispatch, copy credentials,
pull/overwrite the checkout, or touch other NAS services.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

base = Path(sys.argv[1]).resolve()
if str(base) != '/volume1/docker/union-dev':
    raise SystemExit('Unexpected installation root')
source = Path(__file__).parent
target = base / 'controller'
target.mkdir(exist_ok=True)
for name in ('union_dev.py', 'broker.py'):
    if (source / name).resolve() != (target / name).resolve():
        shutil.copyfile(source / name, target / name)
    os.chown(target / name, 0, 0)
    os.chmod(target / name, 0o644)
cfg_path = base / 'config.json'
if not cfg_path.exists():
    cfg_path.write_bytes((source / 'config.example.json').read_bytes())
os.chmod(cfg_path, 0o644)
broker_cfg = json.loads(cfg_path.read_text())
broker_cfg.update(broker_jobs=str(base / 'broker-jobs'), auth_directory=str(base / 'auth'),
                  image='sha256:1d6e909941870743eb6677a392e685df38c4c346d7dd1eb4f83a258ba83b1dac')
(base / 'broker.json').write_text(json.dumps(broker_cfg, indent=2) + '\n')
os.chmod(base / 'broker.json', 0o600)
for directory, uid, gid, mode in [('state', 10001, 10001, 0o700), ('auth', 0, 10001, 0o750), ('broker-jobs', 0, 0, 0o700)]:
    path = base / directory
    path.mkdir(exist_ok=True)
    os.chown(path, uid, gid)
    os.chmod(path, mode)
    if directory == 'state':
        for child in path.rglob('*'):
            if not child.is_symlink():
                os.chown(child, uid, gid)
repo_lock = base / 'Union/.git/union-dev.lock'
if repo_lock.exists():
    os.chown(repo_lock, 10001, 10001)
    os.chmod(repo_lock, 0o600)
git_dir = base / 'Union/.git'
if git_dir.is_symlink() or git_dir.resolve().parent != (base / 'Union').resolve():
    raise SystemExit('Unexpected repository metadata path')
for path in [git_dir, *git_dir.rglob('*')]:
    if path.is_symlink():
        raise SystemExit('Unexpected metadata symlink')
    os.chown(path, 10001, 10001)
    os.chmod(path, (path.stat().st_mode & 0o777 | 0o600) & ~0o022)
home = base / 'state/home'
home.mkdir(exist_ok=True, mode=0o700)
os.chown(home, 10001, 10001)
units = {
    'union-dev-broker.service': '''[Unit]
Description=UNION fixed container execution broker
After=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /volume1/docker/union-dev/controller/broker.py /volume1/docker/union-dev/broker.json
Restart=on-failure
RestartSec=10
UMask=0077
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
''',
    'union-dev.service': '''[Unit]
Description=UNION serial external development cycle
After=union-dev-broker.service
Requires=union-dev-broker.service

[Service]
Type=oneshot
UMask=0077
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/local/bin/union-dev once
TimeoutStartSec=15000
KillMode=process
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
''',
    'union-dev.timer': '''[Unit]
Description=UNION hourly external development trigger

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Unit=union-dev.service

[Install]
WantedBy=timers.target
'''}
for name, content in units.items():
    (source / name).write_text(content)
    Path('/etc/systemd/system', name).write_text(content)
wrapper = Path('/usr/local/bin/union-dev')
wrapper.write_text('''#!/usr/bin/python3
import os, sys
if os.geteuid() == 0:
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
os.environ['HOME'] = '/volume1/docker/union-dev/state/home'
os.environ['XDG_CONFIG_HOME'] = '/volume1/docker/union-dev/state/home/.config'
os.execv('/usr/bin/python3', ['python3', '/volume1/docker/union-dev/controller/union_dev.py', *sys.argv[1:]])
''')
wrapper.chmod(0o755)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
network = subprocess.run(['/usr/local/bin/docker', 'network', 'inspect', 'union-dev-validation'], capture_output=True)
if network.returncode:
    subprocess.run(['/usr/local/bin/docker', 'network', 'create', '--internal', '--subnet', '172.31.244.0/28',
                    '--opt', 'com.docker.network.bridge.inhibit_ipv4=true', 'union-dev-validation'], check=True)
else:
    data = json.loads(network.stdout)[0]
    if not data['Internal'] or data['Options'].get('com.docker.network.bridge.inhibit_ipv4') != 'true':
        raise SystemExit('Existing browser network has unexpected policy; not changed')
data = json.loads(subprocess.run(['/usr/local/bin/docker', 'network', 'inspect', 'union-dev-validation'], capture_output=True, check=True).stdout)[0]
if data['Driver'] != 'bridge' or data['EnableIPv6']:
    raise SystemExit('Unexpected browser network driver/IPv6')
broker_cfg['validation_network_id'] = data['Id']
(base / 'broker.json').write_text(json.dumps(broker_cfg, indent=2) + '\n')
subprocess.run(['systemctl', 'enable', 'union-dev-broker.service'], check=True)
subprocess.run(['systemctl', 'start', 'union-dev-broker.service'], check=True)
print('Installed broker and controller. Timer not enabled; model dispatch remains disabled.')
