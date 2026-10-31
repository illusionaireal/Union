"""Root-owned, local Unix-socket broker. No arbitrary argv, paths or models from clients.

Python 3.8 compatible for DSM. Install outside the target repo; configuration is
root-owned. Each job is a named, retained container, so controller/SSH restarts
do not kill it. Workers never see the socket, controller state, or host root.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socketserver
import subprocess
import time


def docker(*args, check=True):
    p = subprocess.run(['/usr/local/bin/docker', *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return p


class Broker:
    def __init__(self, config):
        self.c = config
        self.jobs = Path(config['broker_jobs'])
        self.jobs.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.repository_id = hashlib.sha256(str(Path(config['repository']).resolve()).encode()).hexdigest()

    def request(self, req):
        jid = req.get('job_id', '')
        if not re.fullmatch(r'[a-f0-9]{32}', jid):
            raise ValueError('invalid job identity')
        directory = self.jobs / jid
        name = 'uniondev-' + jid
        if req['action'] == 'start':
            active = docker('ps', '-q', '--filter', 'label=union-dev.repository=' + self.repository_id).stdout.strip()
            if active:
                raise ValueError('original repository job is still running')
            for previous in self.jobs.glob('*/job.json'):
                if json.loads(previous.read_text()).get('phase') == 'reserved':
                    raise ValueError('reserved original job requires reconciliation')
            directory.mkdir(mode=0o700)  # Existing identity is never replayed.
            role = req.get('role')
            if role not in ('planner', 'worker', 'reviewer', 'validator', 'probe_astra', 'probe_sol', 'setup', 'chromium', 'finalize'):
                raise ValueError('role not allowed')
            validator = role in ('validator', 'chromium', 'finalize')
            ro = role in ('planner', 'reviewer', 'probe_astra', 'probe_sol')
            cmd = ['run', '-d', '--name', name, '--label', 'union-dev.job=' + jid,
                   '--label', 'union-dev.repository=' + self.repository_id,
                   '--user', '10002:10001', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                   '--read-only', '--pids-limit', '512', '--memory', '4g', '--cpu-shares', '512',
                   '--tmpfs', '/tmp:rw,exec,nosuid,size=1g,uid=10002,gid=10001',
                   '--tmpfs', '/run/union:rw,exec,nosuid,size=128m,uid=10002,gid=10001',
                   '--shm-size', '256m', '--workdir', '/repo', '-e', 'HOME=/tmp',
                   '-e', 'UNION_PYTHON=/repo/.venv/bin/python',
                   '-e', 'UNION_CHROMIUM_PATH=/usr/bin/chromium',
                   '-e', 'GIT_CONFIG_COUNT=1', '-e', 'GIT_CONFIG_KEY_0=safe.directory', '-e', 'GIT_CONFIG_VALUE_0=/repo',
                   '-v', self.c['repository'] + ':/repo' + (':ro' if ro else ':rw'),
                   '-v', self.c['repository'] + '/.git:/repo/.git:ro']
            if validator:
                cmd += ['--network', 'none']
            if role == 'finalize':
                argv = ['sh', '-ec', 'node scripts/project-management.mjs render; node scripts/project-management.mjs check']
            elif role == 'validator':
                profile = self.c['test_profiles'].get(req.get('profile'))
                index = req.get('index')
                if not profile or type(index) is not int or not 0 <= index < len(profile):
                    raise ValueError('test profile/index not allowed')
                argv = profile[index]
            elif role == 'setup':
                # Explicit installer action only. Never accepted from a model plan.
                argv = ['sh', '-ec', 'npm ci --ignore-scripts; python3 -m venv .venv; .venv/bin/pip install -r requirements-harness.lock -e .; npm run build:console']
            elif role == 'chromium':
                argv = ['node', '-e', "const {chromium}=require('playwright-core'); (async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']}); const p=await b.newPage(); await p.setContent('<title>union-smoke</title>'); if(await p.title()!=='union-smoke')throw Error('title'); await b.close(); console.log('CHROMIUM_START_STOP_PASS')})().catch(e=>{console.error(e);process.exit(1)})"]
            else:
                if not self.c.get('sandbox_verified') or not self.c.get('credentials_isolation_verified'):
                    raise ValueError('model execution disabled: sandbox/credential isolation not verified')
                prompt = req.get('prompt', '')
                if not isinstance(prompt, str) or len(prompt.encode()) > 800000:
                    raise ValueError('prompt size')
                (directory / 'prompt').write_text(prompt, encoding='utf-8')
                os.chmod(directory, 0o755)
                os.chmod(directory / 'prompt', 0o444)
                cmd += ['-v', str(directory) + ':/input:ro', '-v', self.c['auth_directory'] + ':/auth:ro']
                model = 'gpt-6.1-sol' if role in ('worker', 'probe_sol') else 'gpt-6-astra'
                argv = ['sh', '-ec', 'umask 077; mkdir -p /run/union/codex; cp /auth/auth.json /run/union/codex/auth.json; export CODEX_HOME=/run/union/codex; umask 002; exec "$@" < /input/prompt', 'union-dev',
                        'codex', '-a', 'never', 'exec', '--model', model, '--sandbox',
                        'read-only' if ro else 'workspace-write', '--json', '-']
            if role == 'validator' and argv[:2] == ['npm', 'run'] and argv[2:] in (['test:browser'], ['test:gateways']):
                # Chromium reports navigator.onLine=false with a loopback-only NIC.
                # Dedicated internal bridge has no host IPv4 address; never attach
                # a validation job to the default/production bridge for this check.
                network = json.loads(docker('network', 'inspect', 'union-dev-validation').stdout)[0]
                if (not network['Internal'] or network['Driver'] != 'bridge' or network['EnableIPv6']
                        or network['Id'] != self.c.get('validation_network_id') or network.get('Containers')
                        or network['Options'].get('com.docker.network.bridge.inhibit_ipv4') != 'true'):
                    raise ValueError('isolated browser network policy missing')
                at = cmd.index('--network')
                cmd[at + 1] = 'union-dev-validation'
            receipt = {'job_id': jid, 'role': role, 'created': time.time(), 'container': name,
                       'phase': 'reserved', 'argv': argv, 'image': self.c['image']}
            (directory / 'job.json').write_text(json.dumps(receipt), encoding='utf-8')
            result = docker(*cmd, self.c['image'], *argv)
            receipt.update(phase='started', container_id=result.stdout.strip())
            (directory / 'job.json').write_text(json.dumps(receipt), encoding='utf-8')
            return receipt
        if req['action'] == 'resolve_not_started' and (directory / 'job.json').exists():
            docker('version', '--format', '{{.Server.Version}}')
            check = docker('inspect', name, check=False)
            if check.returncode == 0 or 'No such object' not in check.stderr:
                raise ValueError('cannot prove container was not created')
            receipt = json.loads((directory / 'job.json').read_text())
            receipt.update(phase='resolved_not_started', resolution='Explicit inspection confirmed no original container')
            (directory / 'job.json').write_text(json.dumps(receipt))
            return receipt
        if req['action'] != 'poll' or not (directory / 'job.json').exists():
            raise ValueError('unknown action/job')
        receipt = json.loads((directory / 'job.json').read_text())
        p = docker('inspect', name, check=False)
        if p.returncode:
            return dict(receipt, state='unknown')
        details = json.loads(p.stdout)[0]
        if details['Config']['Labels'].get('union-dev.job') != jid:
            raise ValueError('container identity mismatch')
        state = details['State']
        if not state['Running']:
            receipt['phase'] = 'complete'
            (directory / 'job.json').write_text(json.dumps(receipt), encoding='utf-8')
        logs = docker('logs', name, check=False)
        return dict(receipt, state='running' if state['Running'] else 'exited',
                    exit_code=state['ExitCode'], oom_killed=state['OOMKilled'],
                    started_at=state['StartedAt'], finished_at=state['FinishedAt'],
                    stdout=logs.stdout, stderr=logs.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('config')
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    broker = Broker(cfg)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                raw = self.rfile.readline(1000001)
                if len(raw) > 1000000:
                    raise ValueError('request too large')
                result = {'ok': True, 'result': broker.request(json.loads(raw))}
            except Exception as exc:
                result = {'ok': False, 'error': str(exc)}
            self.wfile.write((json.dumps(result) + '\n').encode())

    sock = Path(cfg['broker_socket'])
    if sock.exists():
        # systemd ensures a single instance; only remove an inactive socket.
        import socket
        with socket.socket(socket.AF_UNIX) as probe:
            if probe.connect_ex(str(sock)) == 0:
                raise RuntimeError('broker already active')
        sock.unlink()
    with socketserver.UnixStreamServer(str(sock), Handler) as server:
        os.chown(sock, 10001, 10001)
        os.chmod(sock, 0o600)
        server.serve_forever()


if __name__ == '__main__':
    main()
