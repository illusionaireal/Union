import os
from pathlib import Path
import subprocess

base=Path('/volume1/docker/union-dev')
private=base/'ui-private'
private.mkdir(mode=0o700,exist_ok=True);private.chmod(0o700)
tls=private/'tls';tls.mkdir(mode=0o700,exist_ok=True)
if not (tls/'key.pem').exists():
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','365',
        '-keyout',str(tls/'key.pem'),'-out',str(tls/'cert.pem'),'-subj','/CN=192.168.1.29',
        '-addext','subjectAltName=IP:192.168.1.29'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(private/'subscription-backend.env').write_bytes(Path('/volume1/docker/union-accounts/web.env').read_bytes())
(private/'subscription-backend.env').chmod(0o600)
for p in [private,tls,*tls.iterdir(),private/'subscription-backend.env']:
    os.chown(p,10001,10001)
(tls/'key.pem').chmod(0o600)
docker='/usr/local/bin/docker'
subprocess.run([docker,'stop','union-account-web'],check=True,stdout=subprocess.DEVNULL)
image=Path('/volume1/docker/union-accounts/image.txt').read_text().strip()
subprocess.run([docker,'run','-d','--name','union-account-auth','--restart','unless-stopped',
    '--user','10001:10001','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--network','host','--memory','1g','--tmpfs','/tmp:rw,exec,uid=10001,gid=10001',
    '--env-file','/volume1/docker/union-accounts/web.env','-e','HOME=/home/accounts',
    '-v','/volume1/docker/union-accounts/home:/home/accounts:rw',image,
    'opencode','serve','--hostname','127.0.0.1','--port','4096'],check=True,stdout=subprocess.DEVNULL)
Path('/volume1/docker/union-accounts/managed-by-union').touch()
subprocess.run([docker,'run','-d','--name','ai-union-console','--restart','unless-stopped',
    '--user','10001:10001','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--network','host','--memory','2g','--tmpfs','/tmp:rw,exec,uid=10001,gid=10001',
    '-e','PYTHONPATH=/repo','-e','HOME=/tmp','-e','PYTHONDONTWRITEBYTECODE=1',
    '-e','UNION_SUBSCRIPTION_AUTH_FILE=/private/subscription-backend.env',
    '-v',str(base/'Union')+':/repo:ro','-v',str(private)+':/private:rw',
    '-v',str(base/'install/run_frontend.py')+':/run_frontend.py:ro','-w','/repo',
    'union-dev-tools:2026-11-01','/repo/.venv/bin/python','/run_frontend.py'],check=True,stdout=subprocess.DEVNULL)
print('AI-UNION HTTPS frontend deployed; private backend only; no model calls or dispatch enabled.')
