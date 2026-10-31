"""Installation diagnostics through fixed broker roles; never model calls."""
import argparse
import json
from pathlib import Path
import socket
import uuid

p = argparse.ArgumentParser()
p.add_argument('action', choices=['setup', 'chromium', 'validator', 'poll', 'finalize', 'resolve_not_started'])
p.add_argument('--job-id')
p.add_argument('--profile', default='union')
p.add_argument('--index', type=int, default=0)
a = p.parse_args()
jid = a.job_id or uuid.uuid4().hex
req = dict(action=a.action if a.action in ('poll', 'resolve_not_started') else 'start', job_id=jid)
if a.action not in ('poll', 'resolve_not_started'):
    req.update(role=a.action, profile=a.profile, index=a.index)
with socket.socket(socket.AF_UNIX) as conn:
    conn.connect('/volume1/docker/union-dev/broker.sock')
    conn.sendall((json.dumps(req) + '\n').encode())
    with conn.makefile('rb') as stream:
        result = json.loads(stream.readline(16000001))
path = Path('/volume1/docker/union-dev/install') / (jid + '.json')
path.write_text(json.dumps(result, indent=2))
if result['ok']:
    out = result['result']
    print(json.dumps({k: out[k] for k in ('job_id', 'role', 'state', 'phase', 'exit_code') if k in out}))
else:
    print(json.dumps(result))
print('Private receipt: ' + str(path))
