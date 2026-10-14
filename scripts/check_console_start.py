"""Verify the documented one-command entrypoint with a private, empty service root."""
import argparse
import http.client
import json
import os
import queue
import re
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    checks = []
    with tempfile.TemporaryDirectory(prefix='union-startup-') as folder:
        command = ['npm.cmd' if os.name == 'nt' else 'npm', 'start', '--', '--root', folder, '--port', '0']
        child = subprocess.Popen(command, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding='utf-8', errors='replace',
                                 start_new_session=os.name != 'nt', shell=os.name == 'nt',
                                 env=os.environ | {'PYTHONUTF8': '1'})
        lines = queue.Queue()
        threading.Thread(target=lambda: [lines.put(line) for line in child.stdout], daemon=True).start()
        try:
            origin = None
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise RuntimeError('Startup exited before serving the console')
                try:
                    match = re.search(r'工作台：(http://127\.0\.0\.1:\d+)', lines.get(timeout=0.2))
                    if match:
                        origin = match[1]
                        break
                except queue.Empty:
                    continue
            if not origin:
                raise RuntimeError('Startup did not become ready within 30 seconds')
            port = urlsplit(origin).port

            def request(method, path, headers=None):
                cx = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                try:
                    cx.request(method, path, headers={'Origin': origin} | (headers or {}))
                    response = cx.getresponse()
                    return response.status, response.read(), dict(response.getheaders())
                finally:
                    cx.close()

            status, shell, headers = request('GET', '/tasks?organization=test')
            assert status == 200 and b'id="root"' in shell
            checks.append('npm start builds and serves a deep SPA route')
            assert "script-src 'self'" in headers['Content-Security-Policy']
            checks.append('same-origin CSP is present')
            asset = re.search(rb'src="(/assets/[^\"]+\.js)"', shell)[1].decode()
            status, content, headers = request('GET', asset)
            assert status == 200 and content and headers['Content-Type'].startswith('text/javascript')
            checks.append('built JavaScript asset is served')
            access = json.loads((Path(folder) / 'local-access.json').read_text(encoding='utf-8'))
            ticket = urlsplit(access['board']).fragment.removeprefix('launch=')
            status, content, headers = request('POST', '/api/session', {'X-Union-Launch': ticket})
            assert status == 200 and json.loads(content)['role'] == 'board'
            cookie = headers['Set-Cookie'].split(';')[0]
            status, content, _ = request('GET', '/api/session', {'Cookie': cookie})
            assert status == 200 and json.loads(content)['organizations'] == []
            checks.append('private one-time session connects without creating or running an organization')
            assert request('GET', '/assets/missing.js')[0] == 404
            checks.append('unknown assets do not return the SPA shell')
        finally:
            if child.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], stdout=subprocess.DEVNULL, check=False)
                else:
                    os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name != 'nt': os.killpg(child.pid, signal.SIGKILL)
                    child.kill()
                    child.wait()
    report = {'passed': len(checks), 'checks': checks, 'real_model_calls': 0, 'platform': os.name}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
