"""Historical external-engineering journal operations (Python stdlib, 3.8+).

Development dispatch and adoption are retired. Only existing run/job inspection,
pause intent and original-job observations remain; no model, task or Git writes.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import sqlite3

TERMINAL = {'accepted', 'blocked', 'failed', 'rejected', 'no_action', 'reconciled'}
RETIREMENT_REASON = (
    'Legacy development dispatch and adoption are retired. '
    'Use scripts/kanban-operations.mjs with the current online owner/version, '
    'then deliver a task-branch PR to rewrite/charter-v1.'
)


class RetiredOperation(RuntimeError):
    """A removed development authority was requested through an old entry point."""


def retirement():
    return {'decision': 'retired', 'reason': RETIREMENT_REASON, 'model_calls': 0}


def dump(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    if path.is_symlink() or tmp.is_symlink():
        raise ValueError('unsafe metadata path')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def validate_id(value, kind):
    if not isinstance(value, str) or len(value) != 32 or any(x not in '0123456789abcdef' for x in value):
        raise ValueError('invalid ' + kind + ' id')


@contextmanager
def lock(path):
    f = open(path, 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            f.seek(0)
            f.write(b'0')
            f.flush()
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        f.close()


class Controller:
    def __init__(self, config):
        self.c = config
        self.repo = Path(config['repository']).resolve()
        self.state = Path(config['state_directory']).resolve()
        if self.state == self.repo or self.repo in self.state.parents:
            raise ValueError('state must be outside target repository')
        path = self.state / 'state.sqlite'
        self.history_available = path.is_file()
        # Read commands never initialize/migrate an on-disk journal. An absent
        # journal has an empty in-memory view; it cannot create a development run.
        self.db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=10) if self.history_available else sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        if not self.history_available:
            self.db.executescript('''
                CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE runs(id TEXT PRIMARY KEY, state TEXT, base TEXT, data TEXT);
                CREATE TABLE calls(id TEXT PRIMARY KEY, run_id TEXT, role TEXT, state TEXT, receipt TEXT);
            ''')

    def _retired(self, *args, **kwargs):
        raise RetiredOperation(RETIREMENT_REASON)

    # Explicit rejection preserves an actionable answer to old callers. The
    # dispatch, planning, adoption, run-creation and Git implementations are gone.
    invoke = probe_models = claim_task = finalize = save = git = resume = _retired

    def setting(self, key, value=None):
        if value is not None:
            if key != 'paused' or value is not True:
                raise RetiredOperation(RETIREMENT_REASON)
            if not self.history_available:
                raise ValueError('historical journal not found; development dispatch is retired')
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('paused', 'true'))
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def _run(self, rid):
        validate_id(rid, 'run')
        row = self.db.execute('SELECT * FROM runs WHERE id=?', (rid,)).fetchone()
        if not row:
            raise ValueError('run not found')
        return row

    def directory(self, rid):
        self._run(rid)
        path = self.state / rid
        if path.is_symlink() or path.resolve().parent != self.state:
            raise ValueError('unsafe evidence path')
        return path

    def inspect(self, rid):
        return dict(self._run(rid), evidence_directory=str(self.directory(rid)))

    def status(self):
        return dict(retirement(), enabled=False, configured_enabled=bool(self.c.get('enabled')),
                    paused=bool(self.setting('paused')), history_available=self.history_available,
                    calls_reserved=self.db.execute("SELECT count(*) FROM calls WHERE role NOT IN ('validator','finalize')").fetchone()[0],
                    max_calls=self.c.get('max_calls', 0), cost='unknown',
                    runs=[dict(x) for x in self.db.execute('SELECT id,state,base FROM runs ORDER BY rowid DESC LIMIT 10')])

    def unfinished(self):
        return [dict(x) for x in self.db.execute('SELECT id,state FROM runs') if x['state'] not in TERMINAL]

    def preflight(self):
        return self.status()

    def once(self, dry=False, trial=False):
        return dict(retirement(), dry_run=bool(dry))

    def broker(self, req):
        if req.get('action') != 'poll':
            raise RetiredOperation(RETIREMENT_REASON)
        if set(req) != {'action', 'job_id'}:
            raise ValueError('only original job polling is supported')
        jid = req['job_id']
        validate_id(jid, 'job')
        recorded = self.db.execute('SELECT calls.id FROM calls JOIN runs ON runs.id=calls.run_id WHERE calls.id=?', (jid,)).fetchone()
        if not recorded:
            raise ValueError('recorded original job not found')
        with socket.socket(socket.AF_UNIX) as conn:
            conn.settimeout(60)
            conn.connect(self.c['broker_socket'])
            conn.sendall((json.dumps(req) + '\n').encode())
            with conn.makefile('rb') as stream:
                result = json.loads(stream.readline(16000001))
        if not result['ok']:
            raise RuntimeError(result['error'])
        return result['result']

    def reconcile(self, rid, resolve=None):
        if resolve not in (None, 'blocked'):
            raise ValueError('only explicit blocked archival is supported')
        directory = self.directory(rid)
        with lock(self.repo / '.git' / 'union-dev.lock'):
            row = self._run(rid)
            calls = self.db.execute('SELECT * FROM calls WHERE run_id=?', (rid,)).fetchall()
            for call in calls:
                validate_id(call['id'], 'job')
            jobs = []
            for call in calls:
                result = self.broker({'action': 'poll', 'job_id': call['id']})
                if result.get('job_id') != call['id']:
                    raise ValueError('original job identity mismatch')
                if result.get('state') not in ('running', 'exited', 'unknown'):
                    raise ValueError('invalid original job observation')
                if result['state'] == 'exited' and type(result.get('exit_code')) is not int:
                    raise ValueError('original job exit is unconfirmed')
                # Only existing identities receive observation metadata. Original
                # receipts/logs/patches and all call reservations remain in place.
                directory.mkdir(exist_ok=True, mode=0o700)
                dump(directory / (call['id'] + '-reconciled.json'), result)
                with self.db:
                    self.db.execute('UPDATE calls SET state=?,receipt=? WHERE id=?',
                                    (result['state'], json.dumps(result), call['id']))
                jobs.append({'job_id': call['id'], 'state': result['state']})
            data = json.loads(row['data'])
            data['reconciliation'] = jobs
            data['reconciliation_note'] = 'Original jobs observed; no replay, next stage or automatic adoption.'
            unresolved = any(job['state'] != 'exited' for job in jobs)
            state = row['state']
            if resolve and not unresolved:
                state = 'blocked'
                data['manual_resolution'] = 'Archived blocked; original changes and reservations preserved; no replay or automatic commit.'
            with self.db:
                self.db.execute('UPDATE runs SET state=?,data=? WHERE id=?', (state, json.dumps(data), rid))
            directory.mkdir(exist_ok=True, mode=0o700)
            dump(directory / 'manifest.json', dict(data, run_id=rid, state=state))
            if resolve and unresolved:
                raise ValueError('cannot resolve running/unknown original job')
            return {'run_id': rid, 'state': state, 'jobs': jobs, 'action': 'inspect before explicit resolution'}


def main():
    parser = argparse.ArgumentParser(description='Historical operations only; development dispatch/adoption retired.')
    parser.add_argument('--config', default=os.environ.get('UNION_DEV_CONFIG', '/volume1/docker/union-dev/config.json'))
    parser.add_argument('command', choices=['preflight', 'once', 'status', 'pause', 'resume', 'inspect', 'reconcile'])
    parser.add_argument('run_id', nargs='?')
    parser.add_argument('--dry-run', action='store_true', help='Read the development retirement notice only')
    parser.add_argument('--trial', action='store_true', help='Retired; cannot enable development dispatch')
    parser.add_argument('--probe-models', action='store_true', help='Retired; model probes are refused')
    parser.add_argument('--resolve', choices=['blocked'], help='Archive an observed stopped run without replay or releasing reservations')
    args = parser.parse_args()
    controller = None
    code = 0
    try:
        controller = Controller(json.loads(Path(args.config).read_text(encoding='utf-8')))
        if args.command == 'once':
            result = controller.once(args.dry_run, args.trial)
            code = 0 if args.dry_run else 2
        elif args.command == 'preflight':
            result = controller.probe_models() if args.probe_models else controller.preflight()
        elif args.command == 'status':
            result = controller.status()
        elif args.command == 'pause':
            result = {'paused': controller.setting('paused', True), 'enabled': False,
                      'note': 'Pause intent recorded; this does not cancel an original remote job.'}
        elif args.command == 'resume':
            result = controller.resume()
        elif args.command == 'reconcile':
            result = controller.reconcile(args.run_id, args.resolve)
        else:
            result = controller.inspect(args.run_id)
    except RetiredOperation:
        result, code = retirement(), 2
    except (ValueError, RuntimeError, OSError, sqlite3.DatabaseError) as exc:
        result, code = {'error': str(exc)}, 2
    finally:
        if controller is not None:
            controller.db.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
