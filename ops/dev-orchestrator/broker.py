"""Root-owned local broker for existing job inspection only (Python 3.8+).

New starts and not-started resolution are retired. Original named containers and
receipts remain available for polling; disappearance is an unknown outcome.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import socketserver
import subprocess


def docker(*args, check=True):
    p = subprocess.run(['/usr/local/bin/docker', *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return p


class Broker:
    def __init__(self, config):
        self.c = config
        self.jobs = Path(config['broker_jobs']).resolve()

    def request(self, req):
        if req.get('action') != 'poll':
            raise RuntimeError('Legacy broker starts and not-started resolution are retired; only original job polling is supported. Use scripts/kanban-operations.mjs for new development.')
        jid = req.get('job_id', '')
        if not isinstance(jid, str) or not re.fullmatch(r'[a-f0-9]{32}', jid):
            raise ValueError('invalid job identity')
        directory = self.jobs / jid
        path = directory / 'job.json'
        if directory.is_symlink() or directory.resolve().parent != self.jobs or path.is_symlink():
            raise ValueError('unsafe original job path')
        if not path.is_file():
            raise ValueError('unknown original job')
        receipt = json.loads(path.read_text(encoding='utf-8'))
        name = 'uniondev-' + jid
        if receipt.get('job_id') != jid or receipt.get('container') != name:
            raise ValueError('original job identity mismatch')
        p = docker('inspect', name, check=False)
        if p.returncode:
            return dict(receipt, state='unknown')
        details = json.loads(p.stdout)[0]
        if details['Config']['Labels'].get('union-dev.job') != jid:
            raise ValueError('container identity mismatch')
        state = details['State']
        if not state['Running']:
            receipt['phase'] = 'complete'
            path.write_text(json.dumps(receipt), encoding='utf-8')
        logs = docker('logs', name, check=False)
        return dict(receipt, state='running' if state['Running'] else 'exited',
                    exit_code=state['ExitCode'], oom_killed=state['OOMKilled'],
                    started_at=state['StartedAt'], finished_at=state['FinishedAt'],
                    stdout=logs.stdout, stderr=logs.stderr)


def main():
    p = argparse.ArgumentParser(description='Poll existing historical jobs; all new starts are retired.')
    p.add_argument('config')
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
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
