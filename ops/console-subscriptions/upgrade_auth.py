"""Adopt reviewed native account authentication, retaining the previous stopped frontend for rollback.

Install prerequisite (operator, NAS Docker): official @opencode/cli@2.2.5 via
npm install --global --prefix /out --allow-scripts=@opencode/cli @opencode/cli@2.2.5
in union-dev-tools:2026-11-01, /out mounted to go-auth-runtime. Never export credentials.
"""
import base64,json,os,subprocess,time,urllib.request,urllib.error
from pathlib import Path
base=Path('/volume1/docker/union-dev');docker='/usr/local/bin/docker'
runtime=base/'go-auth-runtime';home=base/'go-auth-home';private=base/'ui-private'
assert json.loads((runtime/'lib/node_modules/@opencode/cli/package.json').read_text())['version']=='2.2.5'
assert os.path.commonpath([str((runtime/'bin/opencode').resolve()),str(runtime)])==str(runtime)
home.mkdir(mode=0o700,exist_ok=True);home.chmod(0o700);os.chown(home,10001,10001)
def run(*args):return subprocess.check_output([docker,*args],stderr=subprocess.PIPE).decode().strip()
def inspect(name):
    p=subprocess.run([docker,'inspect',name],capture_output=True,text=True)
    return json.loads(p.stdout)[0] if p.returncode==0 else None
native=inspect('union-go-auth')
if native:
    assert native['Config']['User']=='10001:10001'
    assert native['Config']['Cmd']==['/opt/go-auth/bin/opencode','serve','--hostname','127.0.0.1','--port','4097']
    assert native['HostConfig']['ReadonlyRootfs'] and native['HostConfig']['NetworkMode']=='host'
    mounts={m['Destination']:m for m in native['Mounts']}
    assert mounts['/opt/go-auth']['Source']==str(runtime) and not mounts['/opt/go-auth']['RW']
    assert mounts['/home/go-auth']['Source']==str(home)
else:
    run('run','-d','--name','union-go-auth','--restart','unless-stopped','--network','host',
        '--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges',
        '--memory','1g','--tmpfs','/tmp:rw,exec,uid=10001,gid=10001',
        '--env-file','/volume1/docker/union-accounts/web.env','-e','HOME=/home/go-auth',
        '-v',str(runtime)+':/opt/go-auth:ro','-v',str(home)+':/home/go-auth:rw',
        'union-dev-tools:2026-11-01','/opt/go-auth/bin/opencode','serve','--hostname','127.0.0.1','--port','4097')
# Verify the native service is authenticated before handing it to the UI.
time.sleep(2)
try:
    urllib.request.urlopen('http://127.0.0.1:4097/api/integration',timeout=5)
    raise RuntimeError('native backend unexpectedly allows anonymous access')
except urllib.error.HTTPError as e:assert e.code==401
env=dict(l.split('=',1) for l in (private/'subscription-backend.env').read_text().splitlines() if '=' in l)
header={'Authorization':'Basic '+base64.b64encode((env['OPENCODE_SERVER_USERNAME']+':'+env['OPENCODE_SERVER_PASSWORD']).encode()).decode()}
with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4097/api/integration',headers=header),timeout=10) as r:
    assert isinstance(json.load(r)['data'],list)
old='ai-union-console-pre-auth-repair';assert inspect(old) is None, 'rollback container already exists; inspect before another adoption'
assert inspect('ai-union-console')['State']['Running']
run('stop','ai-union-console');run('rename','ai-union-console',old)
try:
    run('run','-d','--name','ai-union-console','--restart','unless-stopped',
        '--user','10001:10001','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
        '--network','host','--memory','2g','--tmpfs','/tmp:rw,exec,uid=10001,gid=10001',
        '-e','PYTHONPATH=/repo','-e','HOME=/tmp','-e','PYTHONDONTWRITEBYTECODE=1',
        '-e','UNION_SUBSCRIPTION_AUTH_FILE=/private/subscription-backend.env',
        '-e','UNION_SUBSCRIPTION_V2_AUTH_FILE=/private/subscription-backend.env',
        '-v',str(base/'Union')+':/repo:ro','-v',str(private)+':/private:rw',
        '-v',str(base/'install/run_frontend.py')+':/run_frontend.py:ro','-w','/repo',
        'union-dev-tools:2026-11-01','/repo/.venv/bin/python','/run_frontend.py')
    time.sleep(2)
    assert inspect('ai-union-console')['State']['Running']
except Exception:
    if inspect('ai-union-console'):
        run('stop','ai-union-console');run('rename','ai-union-console','ai-union-console-auth-repair-failed')
    run('rename',old,'ai-union-console');run('start','ai-union-console');raise
print('Reviewed native auth adopted; old frontend retained stopped; private account data preserved; model calls 0.')
