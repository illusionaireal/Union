"""Controlled fixtures only; none of these tests call a model or Docker."""
import importlib.util
from contextlib import closing, redirect_stdout
import io
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'ops/dev-orchestrator/union_dev.py'
spec = importlib.util.spec_from_file_location('union_dev', MODULE_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
broker_spec = importlib.util.spec_from_file_location('union_broker', MODULE_PATH.with_name('broker.py'))
b = importlib.util.module_from_spec(broker_spec)
broker_spec.loader.exec_module(b)


class LegacyFixture(unittest.TestCase):
    """A private old checkout and journal, with all former dispatch gates open."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.fixture_git('init', '-b', 'dev')
        self.fixture_git('config', 'user.name', 'Fixture')
        self.fixture_git('config', 'user.email', 'fixture@localhost')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/a.txt').write_text('original source\n', encoding='utf-8')
        (self.repo / 'management').mkdir()
        (self.repo / 'management/project.json').write_text(json.dumps({
            'wip_limit': 2, 'tasks': [{'id': 'U-1', 'status': 'ready', 'dependencies': []}]
        }), encoding='utf-8')
        self.fixture_git('add', '.')
        self.fixture_git('commit', '-m', 'fixture')
        self.base = self.fixture_git('rev-parse', 'HEAD')
        self.state = self.root / 'state'
        self.state.mkdir()
        with closing(sqlite3.connect(self.state / 'state.sqlite')) as db:
            db.executescript('''
                CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE runs(id TEXT PRIMARY KEY, state TEXT, base TEXT, data TEXT);
                CREATE TABLE calls(id TEXT PRIMARY KEY, run_id TEXT, role TEXT, state TEXT, receipt TEXT);
            ''')
        self.socket_path = self.root / 'broker.sock'
        # A plain file satisfies the old preflight but can never dispatch a job.
        self.socket_path.write_text('not a real broker', encoding='utf-8')
        self.cfg = dict(repository=str(self.repo), state_directory=str(self.state),
                        broker_socket=str(self.socket_path), branch='dev', enabled=True,
                        planner_model='gpt-6-astra', worker_model='gpt-6.1-sol', reviewer_model='gpt-6-astra',
                        source_ready=True, model_access_verified=True, sandbox_verified=True,
                        credentials_isolation_verified=True, unknown_cost_authorized=True,
                        max_calls=20, max_repair_rounds=2, job_wall_time_limit_seconds=14400,
                        no_progress_warning_seconds=1800, automatic_push=False,
                        automatic_main_merge=False, production_deploy=False, allowed_paths=['src'],
                        test_profiles={'fixture': [['python', '-V']]}, non_authority_tasks=['U-1'])
        self.config_path = self.root / 'config.json'
        self.config_path.write_text(json.dumps(self.cfg), encoding='utf-8')
        self.c = m.Controller(self.cfg)
        self.addCleanup(self.c.db.close)
        self.plan = dict(base_sha=self.base, decision='execute', task_id='U-1', objective='fixture',
                         allowed_paths=['src'], acceptance=['changed'], test_profile='fixture',
                         stop_conditions=['scope drift'], requires_independent_authority_review=False)

    def fixture_git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True, text=True, encoding='utf-8').stdout.strip()

    def files(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
                if p.is_file() and p.name != 'union-dev.lock'}

    def journal(self):
        return {table: [tuple(row) for row in self.c.db.execute('SELECT * FROM ' + table)]
                for table in ('settings', 'runs', 'calls')}

    def seed_run(self, state='unknown', roles=('worker',), call_state='reserved'):
        rid = uuid.uuid4().hex
        data = {'base_sha': self.base, 'created': time.time() - 15000,
                'original_error': 'lost response; execution may have happened'}
        self.c.db.execute('INSERT INTO runs VALUES (?,?,?,?)', (rid, state, self.base, json.dumps(data)))
        directory = self.state / rid
        directory.mkdir()
        m.dump(directory / 'manifest.json', dict(data, run_id=rid, state=state))
        (directory / 'original-events.jsonl').write_bytes(b'original failure evidence\n')
        (directory / 'change.patch').write_bytes(b'original unadopted diff\n')
        jobs = []
        for role in roles:
            jid = uuid.uuid4().hex
            self.c.db.execute('INSERT INTO calls VALUES (?,?,?,?,?)',
                              (jid, rid, role, call_state, json.dumps({'job_id': jid, 'original': True})))
            jobs.append(jid)
        self.c.db.commit()
        return rid, jobs

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(MODULE_PATH), '--config', str(self.config_path), *args],
                                cwd=self.repo, capture_output=True, text=True, encoding='utf-8', timeout=15)
        return result, json.loads(result.stdout) if result.stdout.strip() else None

    def cli_with_broker(self, args, receipt):
        # Execute the actual parser/handler with a local broker response only.
        output = io.StringIO()
        controller = m.Controller(self.cfg)
        self.addCleanup(controller.db.close)
        with patch.object(sys, 'argv', [str(MODULE_PATH), '--config', str(self.config_path), *args]), \
             patch.object(m, 'Controller', return_value=controller), \
             patch.object(controller, 'broker', return_value=receipt) as broker, redirect_stdout(output):
            try:
                code = m.main()
            except (ValueError, RuntimeError) as exc:
                return 2, {'error': str(exc)}, broker.call_args_list
        return code or 0, json.loads(output.getvalue()), broker.call_args_list


class RetirementTests(LegacyFixture):
    def test_once_retires_before_run_reservation_or_broker_even_with_all_gates_open(self):
        before, repo_before = self.journal(), self.files(self.repo)
        with patch.object(self.c, 'broker', side_effect=RuntimeError('unexpected dispatch')) as broker:
            result = self.c.once(trial=True)
        self.assertEqual(result.get('decision'), 'retired', result)
        self.assertIn('scripts/kanban-operations.mjs', result['reason'])
        self.assertIn('rewrite/charter-v1', result['reason'])
        broker.assert_not_called()
        self.assertEqual(self.journal(), before)
        self.assertEqual(self.files(self.repo), repo_before)

    def test_real_cli_rejects_once_trial_probe_and_resume_without_side_effects(self):
        for args in (('once',), ('once', '--trial'), ('preflight', '--probe-models'), ('resume',)):
            with self.subTest(args=args):
                before, repo_before = self.journal(), self.files(self.repo)
                result, body = self.cli(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(body['decision'], 'retired')
                self.assertEqual(body['model_calls'], 0)
                self.assertIn('scripts/kanban-operations.mjs', body['reason'])
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.repo), repo_before)

    def test_cli_dry_run_and_preflight_are_read_only_retirement_reports(self):
        for args in (('once', '--dry-run'), ('once', '--dry-run', '--trial'), ('preflight',)):
            with self.subTest(args=args):
                before, repo_before, state_before = self.journal(), self.files(self.repo), self.files(self.state)
                result, body = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(body.get('decision'), 'retired', body)
                self.assertEqual(body['model_calls'], 0)
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.repo), repo_before)
                self.assertEqual(self.files(self.state), state_before)

    def test_direct_invocation_of_every_role_is_retired_before_any_reservation(self):
        before, repo_before = self.journal(), self.files(self.repo)
        for role in ('planner', 'worker', 'reviewer', 'probe_astra', 'probe_sol', 'validator', 'finalize', 'setup', 'chromium'):
            with self.subTest(role=role), patch.object(self.c, 'broker', side_effect=RuntimeError('unexpected dispatch')) as broker:
                with self.assertRaisesRegex(RuntimeError, 'retired'):
                    self.c.invoke(uuid.uuid4().hex, role, 'Do work', argv=['evil'], profile='fixture', index=0)
                broker.assert_not_called()
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.repo), repo_before)

    def test_direct_probe_cannot_create_run_or_call(self):
        before = self.journal()
        with patch.object(self.c, 'broker', side_effect=RuntimeError('unexpected dispatch')) as broker:
            with self.assertRaisesRegex(RuntimeError, 'retired'):
                self.c.probe_models()
        broker.assert_not_called()
        self.assertEqual(self.journal(), before)

    def test_claim_and_finalize_cannot_write_ledger_report_or_git(self):
        for action in ('claim_task', 'finalize'):
            with self.subTest(action=action):
                rid, _ = self.seed_run(state='finalizing', roles=())
                before, repo_before = self.journal(), self.files(self.repo)
                with patch.object(self.c, 'invoke', return_value={}) as invoke:
                    with self.assertRaisesRegex(RuntimeError, 'retired'):
                        if action == 'claim_task':
                            self.c.claim_task(rid, dict(self.plan))
                        else:
                            self.c.finalize(rid, dict(self.plan), {'commit_sha': self.base})
                invoke.assert_not_called()
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.repo), repo_before)

    def test_generic_save_cannot_create_run_or_adopt_existing_run(self):
        original, _ = self.seed_run()
        for rid, state in ((uuid.uuid4().hex, 'created'), (original, 'accepted')):
            with self.subTest(state=state):
                before, state_before = self.journal(), self.files(self.state)
                with self.assertRaisesRegex(RuntimeError, 'retired'):
                    self.c.save(rid, state, {'base_sha': self.base, 'created': time.time()})
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.state), state_before)

    def test_generic_git_cannot_commit_even_when_directly_called(self):
        before = self.files(self.repo)
        with self.assertRaisesRegex(RuntimeError, 'retired'):
            self.c.git('commit', '--allow-empty', '-m', 'not authorized')
        self.assertEqual(self.files(self.repo), before)

    def test_tampered_or_failed_evidence_never_reenables_adoption(self):
        for name, content in (('tests.json', '[{"status":"fail","exit_code":1}]'),
                              ('checksums.json', '{}'), ('change.patch', 'tampered source')):
            with self.subTest(name=name):
                rid, _ = self.seed_run(state='reviewing', roles=())
                (self.state / rid / name).write_text(content, encoding='utf-8')
                (self.repo / 'src/a.txt').write_text('unreviewed change\n', encoding='utf-8')
                before, state_before, repo_before = self.journal(), self.files(self.state), self.files(self.repo)
                with patch.object(self.c, 'invoke', return_value={}):
                    try:
                        self.c.finalize(rid, self.plan, {'commit_sha': self.base})
                    except (ValueError, RuntimeError):
                        pass
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.state), state_before)
                self.assertEqual(self.files(self.repo), repo_before)

    def test_broker_start_and_not_started_resolution_are_not_exposed(self):
        for action in ('start', 'resolve_not_started'):
            with self.subTest(action=action), patch.object(m.socket, 'AF_UNIX', 1, create=True), patch.object(m.socket, 'socket') as socket:
                socket.return_value.__enter__.return_value.makefile.return_value.__enter__.return_value.readline.return_value = b'{"ok":true,"result":{}}\n'
                with self.assertRaisesRegex(RuntimeError, 'retired'):
                    self.c.broker({'action': action, 'job_id': uuid.uuid4().hex, 'role': 'worker'})
                socket.assert_not_called()

    def test_pause_cannot_be_cleared_to_restore_old_dispatch(self):
        self.c.setting('paused', True)
        with self.assertRaisesRegex(RuntimeError, 'retired'):
            self.c.setting('paused', False)
        self.assertTrue(self.c.setting('paused'))
        self.assertFalse(self.c.status()['enabled'])

    def test_budget_sandbox_authority_and_expired_run_never_restore_dispatch(self):
        rid, _ = self.seed_run(state='executing', roles=())
        for overrides in ({'max_calls': 0}, {'sandbox_verified': False},
                          {'credentials_isolation_verified': False}, {'unknown_cost_authorized': False},
                          {'non_authority_tasks': ['U-1'], 'independent_reviews': {'U-1': {'base_sha': self.base}}}):
            with self.subTest(overrides=overrides), patch.dict(self.c.c, overrides), patch.object(self.c, 'broker') as broker:
                before = self.journal()
                with self.assertRaisesRegex(RuntimeError, 'retired'):
                    self.c.invoke(rid, 'worker', **self.plan)
                broker.assert_not_called()
                self.assertEqual(self.journal(), before)


class HistoryTests(LegacyFixture):
    def test_state_directory_still_cannot_be_inside_repository(self):
        for path in (self.repo, self.repo / 'state'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'outside'):
                m.Controller(dict(self.cfg, state_directory=str(path)))
        self.assertFalse((self.repo / 'state').exists())

    def test_status_and_inspect_preserve_history_bytes_without_broker(self):
        rid, jobs = self.seed_run(roles=('planner', 'worker', 'validator'))
        before, repo_before, state_before = self.journal(), self.files(self.repo), self.files(self.state)
        for args in (('status',), ('inspect', rid)):
            with self.subTest(args=args):
                result, body = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                if args[0] == 'status':
                    self.assertFalse(body['enabled'])
                    self.assertEqual(body['calls_reserved'], 2)
                    self.assertEqual(body['runs'][0]['id'], rid)
                else:
                    self.assertEqual(body['id'], rid)
                    self.assertEqual(json.loads(body['data'])['original_error'], 'lost response; execution may have happened')
                    # Windows TEMP may use an 8.3 alias; inspect returns the resolved path.
                    self.assertEqual(Path(body['evidence_directory']), (self.state / rid).resolve())
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.repo), repo_before)
                self.assertEqual(self.files(self.state), state_before)

    def test_read_commands_do_not_initialize_missing_state(self):
        missing = self.root / 'absent-state'
        cfg = dict(self.cfg, state_directory=str(missing))
        self.config_path.write_text(json.dumps(cfg), encoding='utf-8')
        for args in (('status',), ('preflight',), ('once', '--dry-run')):
            with self.subTest(args=args):
                result, body = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(missing.exists())
                self.assertEqual(body.get('calls_reserved', 0), 0)

    def test_pause_is_durable_and_never_claims_remote_cancellation(self):
        rid, _ = self.seed_run()
        before = self.journal()
        result, body = self.cli('pause')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(body['paused'])
        self.assertEqual(self.journal()['runs'], before['runs'])
        self.assertEqual(self.journal()['calls'], before['calls'])
        restarted = m.Controller(self.cfg)
        self.addCleanup(restarted.db.close)
        self.assertTrue(restarted.status()['paused'])
        self.assertEqual(restarted.status()['calls_reserved'], 1)
        self.assertEqual(restarted.status()['runs'][0], {'id': rid, 'state': 'unknown', 'base': self.base})

    def test_missing_and_unsafe_run_ids_do_not_create_evidence(self):
        before, state_before = self.journal(), self.files(self.state)
        for rid in (uuid.uuid4().hex, '../outside', '/tmp/foreign', 'C:/foreign', 'x' * 32):
            with self.subTest(rid=rid), patch.object(self.c, 'broker') as broker:
                with self.assertRaises(ValueError):
                    self.c.directory(rid)
                with self.assertRaises(ValueError):
                    self.c.reconcile(rid)
                broker.assert_not_called()
                self.assertEqual(self.journal(), before)
                self.assertEqual(self.files(self.state), state_before)

    def test_unknown_job_id_cannot_be_polled_even_directly(self):
        with patch.object(m.socket, 'AF_UNIX', 1, create=True), patch.object(m.socket, 'socket') as socket:
            socket.return_value.__enter__.return_value.makefile.return_value.__enter__.return_value.readline.return_value = b'{"ok":true,"result":{}}\n'
            with self.assertRaisesRegex(ValueError, 'recorded original job'):
                self.c.broker({'action': 'poll', 'job_id': uuid.uuid4().hex})
            socket.assert_not_called()

    def test_inspect_missing_run_does_not_create_evidence_directory(self):
        rid = uuid.uuid4().hex
        result, body = self.cli('inspect', rid)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('run not found', body['error'])
        self.assertFalse((self.state / rid).exists())

    def test_malformed_stored_job_cannot_escape_evidence_directory(self):
        rid, jobs = self.seed_run()
        self.c.db.execute('UPDATE calls SET id=? WHERE id=?', ('../escape', jobs[0]))
        self.c.db.commit()
        before, state_before = self.journal(), self.files(self.state)
        with patch.object(self.c, 'broker', return_value={'job_id': '../escape', 'state': 'unknown'}) as broker:
            with self.assertRaisesRegex(ValueError, 'job id'):
                self.c.reconcile(rid)
            broker.assert_not_called()
        self.assertEqual(self.journal(), before)
        self.assertEqual(self.files(self.state), state_before)

    def test_evidence_directory_symlink_cannot_escape_state(self):
        rid = uuid.uuid4().hex
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.state / rid).symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest('symlink creation unavailable: ' + str(exc))
        self.c.db.execute('INSERT INTO runs VALUES (?,?,?,?)', (rid, 'unknown', self.base, json.dumps({'base_sha': self.base})))
        self.c.db.commit()
        with patch.object(self.c, 'broker') as broker:
            with self.assertRaisesRegex(ValueError, 'path'):
                self.c.reconcile(rid)
            broker.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_broker_poll_sends_only_recorded_original_identity(self):
        _, jobs = self.seed_run()
        jid = jobs[0]
        receipt = {'job_id': jid, 'state': 'unknown', 'original': True}
        with patch.object(m.socket, 'AF_UNIX', 1, create=True), patch.object(m.socket, 'socket') as socket:
            connection = socket.return_value.__enter__.return_value
            connection.makefile.return_value.__enter__.return_value.readline.return_value = json.dumps({'ok': True, 'result': receipt}).encode() + b'\n'
            self.assertEqual(self.c.broker({'action': 'poll', 'job_id': jid}), receipt)
            connection.sendall.assert_called_once_with((json.dumps({'action': 'poll', 'job_id': jid}) + '\n').encode())

    def test_reconcile_observes_original_without_replay_adoption_or_task_writes(self):
        rid, jobs = self.seed_run(roles=('planner', 'worker', 'validator'))
        repo_before = self.files(self.repo)
        originals = {name: (self.state / rid / name).read_bytes() for name in ('original-events.jsonl', 'change.patch')}
        before = self.journal()
        with patch.object(self.c, 'broker', side_effect=lambda req: {'job_id': req['job_id'], 'state': 'exited', 'exit_code': 0}) as broker:
            result = self.c.reconcile(rid)
        self.assertEqual(result['state'], 'unknown')
        self.assertEqual([call.args[0] for call in broker.call_args_list], [{'action': 'poll', 'job_id': jid} for jid in jobs])
        self.assertEqual(self.c.status()['calls_reserved'], 2)
        self.assertEqual(len(self.journal()['calls']), len(before['calls']))
        self.assertEqual(self.files(self.repo), repo_before)
        for name, content in originals.items():
            self.assertEqual((self.state / rid / name).read_bytes(), content)
        data = json.loads(self.journal()['runs'][0][3])
        self.assertEqual(data['original_error'], 'lost response; execution may have happened')
        self.assertEqual([job['job_id'] for job in data['reconciliation']], jobs)

    def test_missing_container_remains_unknown_and_keeps_reservation_after_restart(self):
        rid, jobs = self.seed_run()
        with patch.object(self.c, 'broker', return_value={'job_id': jobs[0], 'state': 'unknown', 'phase': 'reserved'}):
            result = self.c.reconcile(rid)
        self.assertEqual(result['state'], 'unknown')
        self.assertEqual(result['jobs'][0]['state'], 'unknown')
        restarted = m.Controller(self.cfg)
        self.addCleanup(restarted.db.close)
        with patch.object(restarted, 'broker') as broker:
            self.assertEqual(restarted.status()['calls_reserved'], 1)
            self.assertEqual(restarted.once()['decision'], 'retired')
            broker.assert_not_called()
        self.assertEqual(len(self.journal()['calls']), 1)

    def test_reconcile_failure_preserves_original_call_and_history(self):
        rid, _ = self.seed_run()
        before, state_before, repo_before = self.journal(), self.files(self.state), self.files(self.repo)
        with patch.object(self.c, 'broker', side_effect=ConnectionError('original job unavailable')):
            with self.assertRaises(ConnectionError):
                self.c.reconcile(rid)
        self.assertEqual(self.journal(), before)
        self.assertEqual(self.files(self.state), state_before)
        self.assertEqual(self.files(self.repo), repo_before)

    def test_wrong_job_receipt_cannot_replace_original_observation(self):
        rid, _ = self.seed_run()
        before, state_before = self.journal(), self.files(self.state)
        with patch.object(self.c, 'broker', return_value={'job_id': uuid.uuid4().hex, 'state': 'exited', 'exit_code': 0}):
            with self.assertRaisesRegex(ValueError, 'identity'):
                self.c.reconcile(rid)
        self.assertEqual(self.journal(), before)
        self.assertEqual(self.files(self.state), state_before)

    def test_controller_and_retired_broker_share_original_unknown_identity(self):
        rid, jobs = self.seed_run()
        jid = jobs[0]
        broker_jobs = self.root / 'broker-jobs'
        original = broker_jobs / jid
        original.mkdir(parents=True)
        receipt = {'job_id': jid, 'container': 'uniondev-' + jid, 'phase': 'reserved', 'role': 'worker'}
        (original / 'job.json').write_text(json.dumps(receipt), encoding='utf-8')
        broker = b.Broker({'broker_jobs': str(broker_jobs), 'repository': str(self.repo)})
        before = self.files(broker_jobs)
        repo_before = self.files(self.repo)
        with patch.object(self.c, 'broker', side_effect=broker.request), \
             patch.object(b, 'docker', return_value=SimpleNamespace(returncode=1, stdout='', stderr='No such object')) as docker:
            result = self.c.reconcile(rid)
        self.assertEqual(result['jobs'], [{'job_id': jid, 'state': 'unknown'}])
        self.assertEqual(self.c.status()['calls_reserved'], 1)
        self.assertEqual(self.files(broker_jobs), before)
        self.assertEqual(self.files(self.repo), repo_before)
        docker.assert_called_once_with('inspect', 'uniondev-' + jid, check=False)

    def test_explicit_resolution_requires_observed_exit_and_never_releases_calls(self):
        rid, jobs = self.seed_run()
        for state in ('running', 'unknown', 'exited'):
            with self.subTest(state=state):
                repo_before = self.files(self.repo)
                code, result, requests = self.cli_with_broker(
                    ['reconcile', rid, '--resolve', 'blocked'],
                    {'job_id': jobs[0], 'state': state, 'exit_code': 1})
                self.assertEqual(code, 0 if state == 'exited' else 2)
                self.assertEqual([call.args[0] for call in requests], [{'action': 'poll', 'job_id': jobs[0]}])
                row = self.c.db.execute('SELECT state,data FROM runs WHERE id=?', (rid,)).fetchone()
                self.assertEqual(row['state'], 'blocked' if state == 'exited' else 'unknown')
                self.assertEqual(self.c.status()['calls_reserved'], 1)
                self.assertEqual(self.files(self.repo), repo_before)
                self.assertNotIn('commit_sha', json.loads(row['data']))

    def test_same_repository_second_controller_cannot_reconcile_concurrently(self):
        if os.name == 'nt':
            self.skipTest('POSIX flock behavior; Windows uses msvcrt locking')
        rid, _ = self.seed_run()
        c2 = m.Controller(self.cfg)
        self.addCleanup(c2.db.close)
        with m.lock(self.repo / '.git/union-dev.lock'), patch.object(c2, 'broker') as broker:
            with self.assertRaises(BlockingIOError):
                c2.reconcile(rid)
            broker.assert_not_called()


class BrokerRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jobs = self.root / 'jobs'
        self.cfg = dict(broker_jobs=str(self.jobs), repository=str(self.root / 'repo'),
                        image='sha256:fixture', auth_directory=str(self.root / 'fake-auth'),
                        sandbox_verified=True, credentials_isolation_verified=True,
                        test_profiles={'fixed': [['python', '-V']]})
        self.broker = b.Broker(self.cfg)

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def seed_job(self):
        jid = uuid.uuid4().hex
        directory = self.jobs / jid
        directory.mkdir(parents=True)
        receipt = dict(job_id=jid, container='uniondev-' + jid, role='worker', phase='reserved',
                       created=123, argv=['codex', 'exec'], image='sha256:fixture')
        (directory / 'job.json').write_text(json.dumps(receipt), encoding='utf-8')
        return jid, receipt

    def inspection(self, jid, running=True):
        details = {'Config': {'Labels': {'union-dev.job': jid}},
                   'State': {'Running': running, 'ExitCode': 1, 'OOMKilled': False,
                             'StartedAt': 'fixture-start', 'FinishedAt': 'fixture-end'}}
        return SimpleNamespace(returncode=0, stdout=json.dumps([details]), stderr='')

    def test_all_new_roles_refused_before_docker_or_job_creation(self):
        for role in ('planner', 'worker', 'reviewer', 'probe_astra', 'probe_sol', 'validator', 'finalize', 'setup', 'chromium'):
            with self.subTest(role=role):
                before = self.files()
                with patch.object(b, 'docker', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')) as docker:
                    with self.assertRaisesRegex(RuntimeError, 'retired'):
                        self.broker.request({'action': 'start', 'job_id': uuid.uuid4().hex, 'role': role,
                                             'profile': 'fixed', 'index': 0, 'argv': ['evil'], 'prompt': 'fixture'})
                    docker.assert_not_called()
                self.assertEqual(self.files(), before)

    def test_existing_running_or_reserved_job_cannot_enable_start(self):
        self.seed_job()
        before = self.files()
        with patch.object(b, 'docker', return_value=SimpleNamespace(stdout='original-running')) as docker:
            error = None
            try:
                self.broker.request({'action': 'start', 'job_id': uuid.uuid4().hex, 'role': 'worker'})
            except (ValueError, RuntimeError) as exc:
                error = exc
            self.assertIsInstance(error, RuntimeError)
            self.assertIn('retired', str(error))
            docker.assert_not_called()
        self.assertEqual(self.files(), before)

    def test_not_started_resolution_refused_without_docker_or_history_writes(self):
        jid, _ = self.seed_job()
        before = self.files()
        replies = [SimpleNamespace(returncode=0, stdout='fixture-version', stderr=''),
                   SimpleNamespace(returncode=1, stdout='', stderr='No such object')]
        with patch.object(b, 'docker', side_effect=replies) as docker:
            with self.assertRaisesRegex(RuntimeError, 'retired'):
                self.broker.request({'action': 'resolve_not_started', 'job_id': jid})
            docker.assert_not_called()
        self.assertEqual(self.files(), before)

    def test_missing_history_directory_is_not_created(self):
        absent = self.root / 'absent-jobs'
        broker = b.Broker(dict(self.cfg, broker_jobs=str(absent)))
        self.assertFalse(absent.exists())
        with patch.object(b, 'docker') as docker:
            with self.assertRaises(ValueError):
                broker.request({'action': 'poll', 'job_id': uuid.uuid4().hex})
            docker.assert_not_called()
        self.assertFalse(absent.exists())

    def test_unknown_or_malformed_job_never_contacts_docker(self):
        before = self.files()
        for jid in (uuid.uuid4().hex, '../outside', '/tmp/job', 'C:/job', 'x' * 32):
            with self.subTest(jid=jid), patch.object(b, 'docker') as docker:
                with self.assertRaises(ValueError):
                    self.broker.request({'action': 'poll', 'job_id': jid})
                docker.assert_not_called()
        self.assertEqual(self.files(), before)

    def test_poll_running_original_reads_logs_without_history_mutation(self):
        jid, receipt = self.seed_job()
        before = self.files()
        replies = [self.inspection(jid), SimpleNamespace(stdout='original stdout', stderr='original stderr')]
        with patch.object(b, 'docker', side_effect=replies) as docker:
            result = self.broker.request({'action': 'poll', 'job_id': jid})
        self.assertEqual(result['job_id'], jid)
        self.assertEqual(result['state'], 'running')
        self.assertEqual(result['phase'], receipt['phase'])
        self.assertEqual(result['stdout'], 'original stdout')
        self.assertEqual(result['stderr'], 'original stderr')
        self.assertEqual([call.args for call in docker.call_args_list], [('inspect', 'uniondev-' + jid), ('logs', 'uniondev-' + jid)])
        self.assertTrue(all(call.kwargs == {'check': False} for call in docker.call_args_list))
        self.assertEqual(self.files(), before)

    def test_poll_exited_original_keeps_identity_and_failure_evidence(self):
        jid, receipt = self.seed_job()
        replies = [self.inspection(jid, running=False), SimpleNamespace(stdout='original failed output', stderr='original failure')]
        with patch.object(b, 'docker', side_effect=replies) as docker:
            result = self.broker.request({'action': 'poll', 'job_id': jid})
        self.assertEqual(result['state'], 'exited')
        self.assertEqual(result['exit_code'], 1)
        self.assertEqual(result['stderr'], 'original failure')
        saved = json.loads((self.jobs / jid / 'job.json').read_text(encoding='utf-8'))
        self.assertEqual(saved, dict(receipt, phase='complete'))
        self.assertEqual([p.name for p in self.jobs.iterdir()], [jid])
        self.assertEqual([call.args[0] for call in docker.call_args_list], ['inspect', 'logs'])

    def test_missing_container_remains_unknown_without_changing_reservation(self):
        jid, receipt = self.seed_job()
        before = self.files()
        with patch.object(b, 'docker', return_value=SimpleNamespace(returncode=1, stdout='', stderr='No such object')) as docker:
            result = self.broker.request({'action': 'poll', 'job_id': jid})
        self.assertEqual(result, dict(receipt, state='unknown'))
        self.assertEqual(self.files(), before)
        self.assertEqual([call.args for call in docker.call_args_list], [('inspect', 'uniondev-' + jid)])

    def test_foreign_container_label_cannot_be_read_or_change_history(self):
        jid, _ = self.seed_job()
        before = self.files()
        with patch.object(b, 'docker', return_value=self.inspection(uuid.uuid4().hex)) as docker:
            with self.assertRaisesRegex(ValueError, 'identity'):
                self.broker.request({'action': 'poll', 'job_id': jid})
            self.assertEqual(docker.call_count, 1)
        self.assertEqual(self.files(), before)

    def test_foreign_recorded_job_identity_is_rejected_before_docker(self):
        jid, receipt = self.seed_job()
        (self.jobs / jid / 'job.json').write_text(json.dumps(dict(receipt, job_id=uuid.uuid4().hex)), encoding='utf-8')
        before = self.files()
        with patch.object(b, 'docker', return_value=SimpleNamespace(returncode=1)) as docker:
            with self.assertRaisesRegex(ValueError, 'identity'):
                self.broker.request({'action': 'poll', 'job_id': jid})
            docker.assert_not_called()
        self.assertEqual(self.files(), before)

    def test_symlinked_job_record_is_not_read_or_written(self):
        jid, receipt = self.seed_job()
        alias = uuid.uuid4().hex
        try:
            (self.jobs / alias).symlink_to(self.jobs / jid, target_is_directory=True)
        except OSError as exc:
            self.skipTest('symlink creation unavailable: ' + str(exc))
        before = (self.jobs / jid / 'job.json').read_bytes()
        with patch.object(b, 'docker', return_value=SimpleNamespace(returncode=1)) as docker:
            with self.assertRaisesRegex(ValueError, 'path'):
                self.broker.request({'action': 'poll', 'job_id': alias})
            docker.assert_not_called()
        self.assertEqual((self.jobs / jid / 'job.json').read_bytes(), before)


class InstallerIsolationTests(unittest.TestCase):
    def test_installer_refuses_before_private_paths_or_host_side_effects(self):
        installer = str(MODULE_PATH.with_name('install.py'))
        root = MagicMock()
        root.resolve.return_value = root
        root.__str__.return_value = '/volume1/docker/union-dev'
        root.__truediv__.return_value.mkdir.side_effect = RuntimeError('host mkdir attempted')
        output = io.StringIO()
        with patch.object(sys, 'argv', [installer, '/volume1/docker/union-dev']), \
             patch('pathlib.Path', return_value=root) as paths, \
             patch('subprocess.run', side_effect=RuntimeError('host subprocess attempted')) as process, \
             patch('shutil.copyfile', side_effect=RuntimeError('host copy attempted')) as copy, \
             patch('os.chmod', side_effect=RuntimeError('host chmod attempted')) as chmod, \
             patch('os.chown', side_effect=RuntimeError('host chown attempted'), create=True) as chown, \
             redirect_stdout(output):
            error = None
            try:
                runpy.run_path(installer, run_name='__main__')
            except (SystemExit, RuntimeError) as exc:
                error = exc
            self.assertEqual(root.__truediv__.return_value.mkdir.call_count, 0, str(error))
            paths.assert_not_called()
            process.assert_not_called()
            copy.assert_not_called()
            chmod.assert_not_called()
            chown.assert_not_called()
        self.assertIsInstance(error, SystemExit)
        self.assertEqual(error.code, 2)
        self.assertEqual(json.loads(output.getvalue())['decision'], 'retired')

    def test_retired_installer_cli_leaves_supplied_directory_untouched(self):
        # Added only after the isolated RED/GREEN proves the candidate refuses
        # before host operations. The old installer was never run unguarded.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private_config = root / 'config.json'
            private_config.write_text('{"enabled":true}', encoding='utf-8')
            result = subprocess.run([sys.executable, str(MODULE_PATH.with_name('install.py')), str(root)],
                                    cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            body = json.loads(result.stdout)
            self.assertEqual(body['decision'], 'retired')
            self.assertIn('scripts/kanban-operations.mjs', body['reason'])
            self.assertEqual(private_config.read_text(encoding='utf-8'), '{"enabled":true}')
            self.assertEqual([p.name for p in root.iterdir()], ['config.json'])


if __name__ == '__main__':
    unittest.main()
