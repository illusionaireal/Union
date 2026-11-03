"""Run the copied build outside the checkout, with fresh empty private state."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai_union.model_service import ModelServiceClient, ServiceError


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    bun=os.environ.get('UNION_BUN') or shutil.which('bun')
    checks=[]
    with tempfile.TemporaryDirectory(prefix='union-modeld-install-') as folder:
        private=Path(folder);release=private/'release';release.mkdir()
        for name in ('main.js','LICENSE.opencode','upstream.lock.json','THIRD_PARTY_NOTICES.json'):
            shutil.copy2(root/'services/modeld/dist'/name,release/name)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        config={'origin':f'http://127.0.0.1:{port}','state_directory':'state','admin_token_file':'admin.token','worker_token_file':'worker.token'}
        for role in ('admin','worker'):
            path=private/(role+'.token');path.write_text(secrets.token_urlsafe(48),encoding='utf-8');path.chmod(0o600)
        path=private/'modeld.json';path.write_text(json.dumps(config),encoding='utf-8');path.chmod(0o600)
        client=ModelServiceClient(path)
        env=os.environ|{'UNION_MODELD_CONFIG':str(path)}
        for iteration in range(2):
            process=subprocess.Popen([bun,str(release/'main.js')],cwd=release,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                deadline=time.monotonic()+30
                while True:
                    if process.poll() is not None: raise AssertionError('Copied model service exited before readiness')
                    try:
                        runtime=client.runtime()
                        assert runtime['upstream']=='805a42ffaa56b29a88baef87c7567f1ab9a40a8f'
                        break
                    except ServiceError:
                        if time.monotonic()>deadline: raise
                        time.sleep(.1)
                assert client.call('GET','/v1/accounts',admin=True)['accounts']==[]
                if iteration==0:
                    other=subprocess.run([bun,str(release/'main.js')],cwd=release,env=env,capture_output=True,timeout=30,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    assert other.returncode==1
                    checks.append('Second process cannot open the active private state')
                checks.append('Copied build starts without checkout dependencies' if iteration==0 else 'Same private state reopens after process exit')
            finally:
                process.terminate()
                try: process.communicate(timeout=15)
                except subprocess.TimeoutExpired: process.kill();process.communicate()
        assert (release/'THIRD_PARTY_NOTICES.json').stat().st_size>100
        checks.append('Pinned upstream record and dependency notices accompany the build')
    result={'checks':checks,'passed':len(checks),'real_model_calls':0,'real_accounts':0,'deployment':False}
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
