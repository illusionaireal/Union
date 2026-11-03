"""Install actual builds, restart empty services and preserve a local test login.

All state and credentials are generated in a new temporary directory. No account
authorization, provider inference, network deployment or existing AU is used.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

from release_package import activate, install, pack, read_config, selected, verify_directory

sys.dont_write_bytecode = True


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def request_http(number, path, body=None):
    connection = http.client.HTTPConnection('127.0.0.1', number, timeout=5)
    try:
        headers = {'Origin': f'http://127.0.0.1:{number}', 'Content-Type': 'application/json'}
        connection.request('POST' if body is not None else 'GET', path,
                           json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        data = response.read()
        assert response.status == 200, 'Installed Console returned an unexpected status'
        return data
    finally:
        connection.close()


def start(args, directory):
    process = subprocess.Popen(args, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return process


def stop(process):
    process.terminate()
    try:
        process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--bun', required=True)
    args = parser.parse_args()
    checkout = Path(__file__).resolve().parents[1]
    checks = []
    with tempfile.TemporaryDirectory(prefix='union-release-install-') as folder:
        root = Path(folder)
        service_private = root / 'modeld'
        service_private.mkdir(mode=0o700)
        for role in ('admin', 'worker'):
            path = service_private / (role + '.token')
            path.write_text(secrets.token_urlsafe(48), encoding='utf-8')
            path.chmod(0o600)
        model_config = service_private / 'modeld.json'
        model_config.write_text(json.dumps({'origin': f'http://127.0.0.1:{port()}', 'state_directory': 'state',
                                           'admin_token_file': 'admin.token', 'worker_token_file': 'worker.token'}), encoding='utf-8')
        model_config.chmod(0o600)
        configuration = {'installation_root': str(root / 'code'), 'console_state': str(root / 'business'),
                         'modeld_config': str(model_config), 'python': sys.executable,
                         'bun': str(Path(args.bun).resolve()), 'console_port': port()}
        config_path = root / 'deployment.json'
        config_path.write_text(json.dumps(configuration), encoding='utf-8')
        config = read_config(config_path)
        archives = []
        for release_id in ('candidate-a', 'candidate-b'):
            archive = root / (release_id + '.zip')
            manifest = pack(checkout, archive, release_id)
            archives.append({'id': release_id, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                             'files': len(manifest['files']), 'git_baseline': manifest['git_baseline'],
                             'source_state': manifest['source_state']})
            install(archive, config)
        checks.append('Actual Python, React, catalog and pinned model service install without checkout dependencies')
        # Test-only sentinel represents newest state that a code rollback must leave untouched.
        config['console_state'].mkdir()
        sentinel = config['console_state'] / 'latest-reservations-test.txt'
        sentinel.write_bytes(b'test-only latest reservations, never refund on rollback')
        token_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in service_private.glob('*.token')}
        password = secrets.token_urlsafe(24)
        for index, release_id in enumerate(('candidate-a', 'candidate-b', 'candidate-a')):
            activate(release_id, config, stopped=True)
            directory = selected(config)
            tool = directory / 'scripts/release_package.py'
            modeld = start([sys.executable, '-B', str(tool), 'run', 'modeld', '--config', str(config_path)], directory)
            console = start([sys.executable, '-B', str(tool), 'run', 'console', '--config', str(config_path)], directory)
            try:
                # Import the installed client, with no real authorization or inference request.
                sys.path.insert(0, str(directory))
                from ai_union.model_service import ModelServiceClient, ServiceError
                client = ModelServiceClient(model_config)
                deadline = time.monotonic() + 60
                while True:
                    for component, process in (('modeld', modeld), ('console', console)):
                        if process.poll() is not None:
                            stdout, stderr = process.communicate()
                            raise AssertionError(component + f' exited before readiness (code {process.returncode}): ' +
                                                 stderr.decode('utf-8', errors='replace') + stdout.decode('utf-8', errors='replace'))
                    try:
                        status = json.loads(request_http(config['console_port'], '/api/auth/status'))
                        runtime = client.runtime()
                        break
                    except (OSError, ServiceError):
                        if time.monotonic() > deadline:
                            raise AssertionError('Installed services did not become ready') from None
                        time.sleep(.1)
                assert runtime['upstream'] == '805a42ffaa56b29a88baef87c7567f1ab9a40a8f'
                assert client.call('GET', '/v1/accounts', admin=True)['accounts'] == []
                assert b'<html' in request_http(config['console_port'], '/')
                if index == 0:
                    assert status['configured'] is False
                    request_http(config['console_port'], '/api/auth/setup', {'username': 'release-check', 'password': password, 'remember': False})
                else:
                    assert status['configured'] is True
                    request_http(config['console_port'], '/api/auth/login', {'username': 'release-check', 'password': password, 'remember': False})
                checks.append(('Initial install starts both services and local test administrator setup' if index == 0 else
                               'New code selection preserves the existing test login' if index == 1 else
                               'Explicit code rollback preserves the latest test login and empty model account state'))
            finally:
                # Terminate full local trees when the launcher owns a runtime child on Windows.
                for process in (console, modeld):
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    stop(process)
            verify_directory(directory)
        assert sentinel.read_bytes() == b'test-only latest reservations, never refund on rollback'
        assert token_hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in service_private.glob('*.token')}
        checks.append('Switch and rollback never replace newest business bytes or private service tokens')
    output = {'checks': checks, 'passed': len(checks), 'archives': archives,
              'real_model_calls': 0, 'real_accounts': 0, 'deployment': False,
              'scope': 'Same source in two candidate IDs; code switching and existing login compatibility, no schema migration'}
    Path(args.output).write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': len(checks), 'real_model_calls': 0}))


if __name__ == '__main__':
    main()
