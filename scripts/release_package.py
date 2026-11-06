"""Local candidate packaging and code-only version switching; no model calls.

Run with Python 3.11+. Deployment configuration and all business state stay outside
the installation. Hashes detect corruption, not an untrusted package publisher.
"""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import zipfile

if __package__ in (None, ""):
    # Use the schema owner shipped beside this release tool, including when
    # invoked directly from an installed candidate.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ReleaseError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def name(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}', value)
            and value not in ('.', '..'), 'Invalid release ID')
    require(value.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL',
            *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}, 'Reserved release ID')
    return value


def member_path(value):
    require(isinstance(value, str) and value and '\\' not in value and ':' not in value,
            'Invalid package path')
    parts = value.split('/')
    require(not PurePosixPath(value).is_absolute() and all(p not in ('', '.', '..') for p in parts),
            'Package path escapes release')
    for part in parts:
        require(not part.endswith((' ', '.')) and not any(ord(c) < 32 for c in part), 'Invalid package path')
        require(len(part) <= 255 and bool(re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9._-]*', part)), 'Invalid package path')
        require(part.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL',
                *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}, 'Reserved package path')
    return value


def linked(path):
    return path.is_symlink() or getattr(path, 'is_junction', lambda: False)()


def regular(path):
    path = Path(path)
    require(path.is_file() and not linked(path), 'Expected a regular file')
    require(not any(linked(p) for p in path.parents), 'Linked parent directory is not supported')
    return path.read_bytes()


def pack(root, output, release_id):
    root, output = Path(root).resolve(), Path(output).absolute()
    name(release_id)
    require(not output.exists(), 'Package already exists')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    source_names = sorted(p for p in tracked if p and (
        p.startswith('ai_union/') and p.endswith('.py') or p.startswith('data/') or
        p.startswith('examples/') or p in {'pyproject.toml', 'requirements-harness.lock',
              'services/modeld/upstream.lock.json', 'services/modeld/init.mjs', 'services/modeld/README.md'}))
    payload = {p: regular(root / p) for p in source_names}
    # Explicit additional sources belong to this release tool, never all untracked files.
    for p in ('scripts/release_package.py', 'scripts/upgrade_core_identity.py', 'scripts/reset_owner.py', 'ops/release/README.md', 'ops/release/deployment.example.json'):
        payload[p] = regular(root / p)
        source_names.append(p)
    build_sources = [p for p in tracked if p and (
        p.startswith('web/console/src/') or p.startswith('web/console/public/') or
        p.startswith('services/modeld/src/') or p.startswith('services/modeld/patches/') or
        p in {'package.json', 'package-lock.json', 'web/console/package.json', 'web/console/index.html',
              'web/console/vite.config.ts', 'services/modeld/build.ts', 'services/modeld/prepare.mjs'})]
    source_bytes = {p: regular(root / p) for p in sorted(set(source_names + build_sources))}
    source_hashes = {p: digest(data) for p, data in source_bytes.items()}
    for directory in ('web/console/dist', 'services/modeld/dist'):
        require((root / directory).is_dir(), 'Build Console and model service before packaging')
        for path in sorted((root / directory).rglob('*')):
            require(not linked(path), 'Linked build output is not supported')
            if path.is_file():
                relative = path.relative_to(root / directory).as_posix()
                if directory == 'services/modeld/dist':
                    allowed = relative in {'main.js', 'LICENSE.opencode', 'THIRD_PARTY_NOTICES.json', 'upstream.lock.json'}
                else:
                    allowed = relative == 'index.html' or relative.startswith('assets/') and path.suffix in {
                        '.js', '.css', '.woff', '.woff2', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.ico'}
                if allowed:
                    payload[path.relative_to(root).as_posix()] = regular(path)
    required = {'web/console/dist/index.html', 'services/modeld/dist/main.js',
                'services/modeld/dist/LICENSE.opencode', 'services/modeld/dist/THIRD_PARTY_NOTICES.json',
                'services/modeld/dist/upstream.lock.json', 'ai_union/server.py', 'data/model-catalog.json'}
    require(required <= payload.keys(), 'Required release files are missing')
    require(payload['services/modeld/upstream.lock.json'] == payload['services/modeld/dist/upstream.lock.json'],
            'Model service build has a different upstream lock')
    baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    changed = sorted(set(subprocess.check_output(
        ['git', 'diff', '--name-only', '-z', 'HEAD', '--', *source_bytes], cwd=root).decode().split('\0')) - {''}
        | (set(source_bytes) - set(tracked)))
    manifest = {'schema_version': 1, 'release_id': release_id, 'git_baseline': baseline,
                'core_schemas': {'auth': 2, 'catalog': 1},
                'core_au_schemas': [1, 2, 3],
                'modeld_schemas': [0, 1],
                'source_state': 'working_tree' if changed else 'committed', 'changed_sources': changed,
                'source_hashes': source_hashes, 'upstream': json.loads(payload['services/modeld/upstream.lock.json']),
                'toolchain': {'python_minimum': '3.11', 'node_build_required': '24.19.0', 'bun': '1.4.2'},
                'files': {p: {'sha256': digest(data), 'size': len(data)} for p, data in sorted(payload.items())}}
    for p in payload:
        member_path(p)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p, data in sorted((payload | {'manifest.json': encoded(manifest)}).items()):
            info = zipfile.ZipInfo(p, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    verify_archive(output)
    return manifest


def validate_manifest(manifest):
    require(isinstance(manifest, dict) and manifest.get('schema_version') == 1, 'Unsupported release manifest')
    name(manifest.get('release_id'))
    schemas = manifest.get('core_schemas', {'auth': 0, 'catalog': 0})
    require(isinstance(schemas, dict) and set(schemas) == {'auth', 'catalog'}
            and all(type(value) is int and value >= 0 for value in schemas.values()), 'Invalid core schema declaration')
    au_schemas = manifest.get('core_au_schemas', [])
    require(isinstance(au_schemas, list) and all(type(value) is int and value >= 1 for value in au_schemas)
            and len(set(au_schemas)) == len(au_schemas), 'Invalid core AU schema declaration')
    modeld_schemas = manifest.get('modeld_schemas', [0])
    require(isinstance(modeld_schemas, list) and modeld_schemas
            and all(type(value) is int and value >= 0 for value in modeld_schemas)
            and len(set(modeld_schemas)) == len(modeld_schemas), 'Invalid modeld schema declaration')
    files = manifest.get('files')
    require(isinstance(files, dict) and 1 <= len(files) <= 10000, 'Invalid release file list')
    case_names = set()
    for p, record in files.items():
        member_path(p)
        require(p.lower() not in case_names and p != 'manifest.json', 'Duplicate or reserved package path')
        case_names.add(p.lower())
        require(isinstance(record, dict) and type(record.get('size')) is int and 0 <= record['size'] <= 128 * 1024**2
                and bool(re.fullmatch('[0-9a-f]{64}', record.get('sha256', ''))), 'Invalid file digest')
    require(sum(r['size'] for r in files.values()) <= 512 * 1024**2, 'Release package is too large')
    return manifest


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(1 < len(infos) <= 10001, 'Invalid archive file count')
        names = [i.filename for i in infos]
        require(len(names) == len(set(n.lower() for n in names)) and 'manifest.json' in names,
                'Duplicate files or missing manifest')
        require(archive.getinfo('manifest.json').file_size <= 4 * 1024**2, 'Manifest is too large')
        for info in infos:
            member_path(info.filename)
            mode = info.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG) and not info.is_dir(), 'Non-regular archive member')
            require(not info.flag_bits & 1, 'Encrypted archive members are not supported')
        manifest = validate_manifest(json.loads(archive.read('manifest.json')))
        require(set(names) == set(manifest['files']) | {'manifest.json'}, 'Archive contains missing or extra files')
        for p, record in manifest['files'].items():
            require(archive.getinfo(p).file_size == record['size'], 'File size mismatch')
            require(digest(archive.read(p)) == record['sha256'], 'File digest mismatch')
        return manifest


def verify_directory(directory):
    directory = Path(directory)
    require(directory.is_dir() and not linked(directory), 'Invalid release directory')
    manifest = validate_manifest(json.loads(regular(directory / 'manifest.json')))
    actual = set()
    for path in directory.rglob('*'):
        require(not linked(path), 'Release contains a link')
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    require(actual == set(manifest['files']) | {'manifest.json'}, 'Installed release has missing or extra files')
    for p, record in manifest['files'].items():
        data = regular(directory / p)
        require(len(data) == record['size'] and digest(data) == record['sha256'], 'Installed release was modified')
    return manifest


def read_config(path):
    path = Path(path).absolute()
    config = json.loads(regular(path))
    require(set(config) == {'installation_root', 'console_state', 'modeld_config', 'python', 'bun', 'console_port'},
            'Deployment configuration fields are missing or invalid')
    for field in ('installation_root', 'console_state', 'modeld_config', 'python', 'bun'):
        require(isinstance(config[field], str) and Path(config[field]).is_absolute(), 'Configuration paths must be absolute')
        original = Path(config[field])
        if field not in ('python', 'bun'):
            require(not linked(original) and not any(linked(p) for p in original.parents), 'Deployment paths cannot contain links')
        config[field] = original.resolve()
    install, state, private = config['installation_root'], config['console_state'], config['modeld_config'].parent
    for a, b in ((install, state), (install, private), (state, private)):
        require(not a.is_relative_to(b) and not b.is_relative_to(a), 'Code and private state paths must be separate')
    require(not path.is_relative_to(install), 'Deployment configuration must stay outside installation')
    require(type(config['console_port']) is int and 1024 <= config['console_port'] <= 65535, 'Invalid Console port')
    require(config['python'].is_file() and config['bun'].is_file() and config['modeld_config'].is_file(),
            'Configured Python, Bun or modeld configuration is missing')
    return config


@contextmanager
def operation_lock(root):
    root = Path(root)
    require(not linked(root) and not any(linked(p) for p in root.parents), 'Installation path cannot contain links')
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.operation.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ReleaseError('Another release operation or an unresolved operation lock exists') from None
    try:
        os.write(fd, str(os.getpid()).encode('ascii'))
        yield
    finally:
        os.close(fd)
        lock.unlink()


def install(archive, config):
    manifest = verify_archive(archive)  # Reject bad inputs before any installation write.
    root = config['installation_root']
    with operation_lock(root):
        releases = root / 'releases'
        require(not linked(releases), 'Release directory cannot be linked')
        releases.mkdir(exist_ok=True)
        target = releases / name(manifest['release_id'])
        require(not target.exists() and not linked(target), 'Release is already installed; it will not be overwritten')
        staging = Path(tempfile.mkdtemp(prefix='.staging-', dir=releases))
        try:
            # Keep the same open archive and revalidate it before extracting to avoid replaced input paths.
            with Path(archive).open('rb') as stream:
                require(verify_archive(stream) == manifest, 'Archive changed during installation')
                stream.seek(0)
                with zipfile.ZipFile(stream) as source:
                    for p in [*manifest['files'], 'manifest.json']:
                        destination = staging / p
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(source.read(p))
            verify_directory(staging)
            staging.rename(target)
        finally:
            if staging.exists():
                require(staging.resolve().is_relative_to(releases.resolve()) and not linked(staging),
                        'Staging cleanup path escaped installation')
                shutil.rmtree(staging)
    return manifest


def check_core_schemas(manifest, config):
    """Read-only host compatibility at activation/run, including old manifests."""
    check_modeld_schemas(manifest, config)
    database = config['console_state'] / 'console.sqlite3'
    if not database.exists():
        return
    require(database.is_file() and not linked(database), 'Core catalog must be a regular database')
    try:
        from ai_union.identity_schema import versions
        actual = versions(database)
        if actual is None:
            return
        require(actual == manifest.get('core_schemas', {'auth': 0, 'catalog': 0}),
                'Candidate auth/catalog schema is incompatible; explicitly upgrade or select compatible code, never erase newer state')
        if actual['catalog'] >= 1:
            check_au_schemas(database, manifest, config['console_state'])
    except (ValueError, OSError, sqlite3.Error) as error:
        raise ReleaseError('Core catalog compatibility cannot be verified; retain current code and data') from error


def check_modeld_schemas(manifest, config):
    """The private single-call service owns its schema; never migrate on selection."""
    config_path = config.get('modeld_config')
    if config_path is None or not Path(config_path).exists():
        return  # No configured modeld state; runtime preflight still validates config.
    try:
        config_path = Path(config_path)
        private = json.loads(regular(config_path))
        state = private.get('state_directory')
        require(isinstance(state, str) and state, 'Invalid modeld state directory')
        database = (config_path.parent / state).resolve() / 'modeld.sqlite3'
        if not database.exists():
            return
        require(database.is_file() and not linked(database)
                and not any(linked(parent) for parent in database.parents), 'Invalid modeld database')
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as cx:
            cx.execute('PRAGMA query_only=ON')
            version = cx.execute('PRAGMA user_version').fetchone()[0]
        require(version in manifest.get('modeld_schemas', [0]),
                'Candidate modeld schema is incompatible; retain compatible code and original accounts/requests')
    except (ValueError, OSError, sqlite3.Error) as error:
        raise ReleaseError('Private modeld compatibility cannot be verified; retain current code and data') from error


def check_au_schemas(database, manifest, root):
    """Use the same identity/creation validator as runtime before code selection."""
    from ai_union.adapters.au_catalog import resolve_directory
    from ai_union.adapters.core_au_store import CoreAUStore
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as cx:
        cx.row_factory = sqlite3.Row
        cx.execute('PRAGMA query_only=ON')
        cx.execute('BEGIN')
        for entry in cx.execute("SELECT * FROM organizations WHERE profile='core_v1'").fetchall():
            intents = cx.execute("SELECT * FROM creations WHERE allocated_au_id=? AND profile='core_v1'", (entry['id'],)).fetchall()
            require(len(intents) == 1, 'Core AU has no unique original creation intent')
            intent = dict(intents[0])
            directory, _ = resolve_directory(root, dict(entry), creation=intent)
            state = CoreAUStore().read(directory, entry['id'], creation=intent)['au']
            require(state['schema_version'] in manifest.get('core_au_schemas', []),
                    'Candidate does not declare support for the persisted AU schema; keep compatible code and original history')


def preflight(directory, config):
    manifest = verify_directory(directory)
    check_core_schemas(manifest, config)
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPATH'] = str(directory)
    probe = """import sys, pathlib, importlib.metadata as m
assert sys.version_info >= (3, 11)
for line in pathlib.Path('requirements-harness.lock').read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        package, version = line.split('=='); assert m.version(package) == version, package
import ai_union.server, ai_union.model_service
assert pathlib.Path(ai_union.server.__file__).resolve().is_relative_to(pathlib.Path.cwd())
"""
    result = subprocess.run([str(config['python']), '-I', '-B', '-X', 'utf8', '-c', 'import sys; sys.path.insert(0, "."); ' + probe],
                            cwd=directory, env=env, capture_output=True, timeout=60,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(result.returncode == 0, 'Candidate Python imports or locked dependencies failed preflight')
    result = subprocess.run([str(config['bun']), '--version'], capture_output=True, text=True, timeout=10,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(result.returncode == 0 and result.stdout.strip() == manifest['toolchain']['bun'], 'Bun version does not match release')
    # Existing host config validation is read-only: no credential generation, service launch or inference.
    result = subprocess.run([str(config['python']), '-I', '-B', '-X', 'utf8', '-c',
        'import sys; sys.path.insert(0, "."); from ai_union.model_service import ModelServiceClient; ModelServiceClient(sys.argv[1])',
        str(config['modeld_config'])], cwd=directory, env=env, capture_output=True, timeout=10,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(result.returncode == 0, 'Private model service configuration failed preflight')
    return manifest


def activate(release_id, config, *, stopped=False):
    require(stopped, 'Stop both services and confirm in-flight state before code switching (--services-stopped)')
    root = config['installation_root']
    with operation_lock(root):
        target = root / 'releases' / name(release_id)
        manifest = preflight(target, config)
        check_core_schemas(manifest, config)
        require(manifest['release_id'] == release_id, 'Installed release ID mismatch')
        current = root / 'current.json'
        previous = None
        if current.exists():
            previous = name(json.loads(regular(current))['release_id'])
        pointer = encoded({'schema_version': 1, 'release_id': release_id, 'previous_release_id': previous})
        fd, tmp = tempfile.mkstemp(prefix='.current-', dir=root)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(pointer)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, current)
        finally:
            if Path(tmp).exists():
                Path(tmp).unlink()
    return manifest


def selected(config):
    root = config['installation_root']
    pointer = json.loads(regular(root / 'current.json'))
    require(pointer.get('schema_version') == 1, 'Unsupported current pointer')
    directory = root / 'releases' / name(pointer['release_id'])
    require(verify_directory(directory)['release_id'] == pointer['release_id'], 'Current release ID mismatch')
    return directory


def run(component, config):
    directory = selected(config)
    manifest = preflight(directory, config)
    check_core_schemas(manifest, config)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(directory), UNION_MODELD_CONFIG=str(config['modeld_config']))
    if component == 'console':
        args = [str(config['python']), '-I', '-B', '-X', 'utf8', '-c',
                'import sys; sys.path.insert(0, "."); from ai_union.server import main; main()',
                '--root', str(config['console_state']), '--port', str(config['console_port'])]
    else:
        args = [str(config['bun']), str(directory / 'services/modeld/dist/main.js')]
    # Foreground runtime: forward stop to the local tree; no remote cancellation claim.
    process = subprocess.Popen(args, cwd=directory, env=env, start_new_session=True,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    received = []
    def stop_local(signum=None, frame=None):
        if signum is not None:
            received.append(signum)
        if process.poll() is not None:
            return
        if os.name == 'nt':
            result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                    capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            require(result.returncode == 0 or process.poll() is not None, 'Local runtime stop could not be confirmed')
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=10)
    previous = {s: signal.signal(s, stop_local) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        result = process.wait()
        return 128 + received[0] if received else result
    finally:
        try:
            stop_local()
        finally:
            for s, handler in previous.items():
                signal.signal(s, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('pack'); build.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    build.add_argument('--output', required=True); build.add_argument('--release-id', required=True)
    verify = sub.add_parser('verify'); verify.add_argument('archive')
    for command in ('install', 'activate', 'rollback', 'status', 'run'):
        item = sub.add_parser(command); item.add_argument('--config', required=True)
        if command == 'install': item.add_argument('archive')
        if command in ('activate', 'rollback'):
            item.add_argument('release_id'); item.add_argument('--services-stopped', action='store_true')
        if command == 'run': item.add_argument('component', choices=('console', 'modeld'))
    args = parser.parse_args(argv)
    try:
        if args.command == 'pack': result = pack(args.root, args.output, args.release_id)
        elif args.command == 'verify': result = verify_archive(args.archive)
        else:
            config = read_config(args.config)
            if args.command == 'install': result = install(args.archive, config)
            elif args.command in ('activate', 'rollback'): result = activate(args.release_id, config, stopped=args.services_stopped)
            elif args.command == 'run': return run(args.component, config)
            else: result = verify_directory(selected(config))
        print(json.dumps({'release_id': result['release_id'], 'git_baseline': result['git_baseline'],
                          'source_state': result['source_state'], 'files': len(result['files'])}))
        return 0
    except ReleaseError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, subprocess.SubprocessError):
        print('Release operation failed; check package integrity, explicit configuration, dependencies and operation lock.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
