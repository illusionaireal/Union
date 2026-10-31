"""Run fixed project checks on NAS, no models. Original receipts stay private."""
import argparse
import json
from pathlib import Path
import socket
import time
import uuid

p = argparse.ArgumentParser()
p.add_argument('--indices', nargs='+', type=int, default=[1, 2, 3])
a = p.parse_args()
def request(req):
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(60)
        conn.connect('/volume1/docker/union-dev/broker.sock')
        conn.sendall((json.dumps(req) + '\n').encode())
        with conn.makefile('rb') as stream:
            result = json.loads(stream.readline(16000001))
    if not result['ok']:
        raise RuntimeError(result['error'])
    return result['result']

root = Path('/volume1/docker/union-dev/install')
outcomes = []
for index in a.indices:
    jid = uuid.uuid4().hex
    result = request(dict(action='start', job_id=jid, role='validator', profile='union_gateways', index=index))
    print('Started fixed check index=%s job=%s' % (index, jid), flush=True)
    while True:
        result = request(dict(action='poll', job_id=jid))
        if result['state'] != 'running':
            break
        time.sleep(5)
    (root / (jid + '-validation.json')).write_text(json.dumps(result, indent=2))
    (root / (jid + '.stdout.log')).write_text(result.get('stdout', ''))
    (root / (jid + '.stderr.log')).write_text(result.get('stderr', ''))
    outcomes.append(dict(index=index, job_id=jid, state=result['state'], exit_code=result.get('exit_code')))
    print(json.dumps(outcomes[-1]), flush=True)
(root / ('validation-' + uuid.uuid4().hex + '.json')).write_text(json.dumps(outcomes, indent=2))
if any(x['state'] != 'exited' or x['exit_code'] for x in outcomes):
    raise SystemExit(1)
