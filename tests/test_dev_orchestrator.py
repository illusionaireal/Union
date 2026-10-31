"""Controlled fixtures only; none of these tests call a model or Docker."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'ops/dev-orchestrator/union_dev.py'
spec = importlib.util.spec_from_file_location('union_dev', MODULE_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
broker_spec = importlib.util.spec_from_file_location('union_broker', MODULE_PATH.with_name('broker.py'))
b = importlib.util.module_from_spec(broker_spec)
broker_spec.loader.exec_module(b)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / 'repo'
        self.repo.mkdir()
        def git(*args):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
        git('init', '-b', 'dev')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@localhost')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/a.txt').write_text('before\n')
        (self.repo / 'management').mkdir()
        (self.repo / 'management/project.json').write_text(json.dumps({'wip_limit': 2, 'tasks': [{'id': 'U-1', 'status': 'ready', 'dependencies': []}]}))
        git('add', '.')
        git('commit', '-m', 'fixture')
        self.cfg = json.loads(MODULE_PATH.with_name('config.example.json').read_text())
        self.cfg.update(repository=str(self.repo), state_directory=str(root / 'state'), enabled=True,
                        source_ready=True, model_access_verified=True, sandbox_verified=True,
                        credentials_isolation_verified=True, unknown_cost_authorized=True, max_calls=20,
                        allowed_paths=['src'], test_profiles={'fixture': [['python', '-V']]}, non_authority_tasks=['U-1'])
        self.c = m.Controller(self.cfg)
        self.addCleanup(self.c.db.close)
        self.base = self.c.git('rev-parse', 'HEAD')
        self.plan = dict(base_sha=self.base, decision='execute', task_id='U-1', objective='fixture change',
                         allowed_paths=['src'], acceptance=['content changed'], test_profile='fixture', stop_conditions=['scope drift'])

    def test_plan_path_escape_and_fake_test_rejected(self):
        for field, value in [('allowed_paths', ['src/../.git']), ('allowed_paths', ['C:/secrets']),
                             ('allowed_paths', ['/etc']), ('test_profile', 'echo evil'), ('base_sha', 'stale')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.c.plan_valid(dict(self.plan, **{field: value}), self.base)

    def test_model_cannot_waive_authority_review(self):
        self.c.c['non_authority_tasks'] = []
        with self.assertRaisesRegex(ValueError, 'review missing'):
            self.c.plan_valid(dict(self.plan, requires_independent_authority_review=False), self.base)

    def test_dependencies_block_dispatch(self):
        path = self.repo / 'management/project.json'
        data = json.loads(path.read_text())
        data['tasks'][0]['dependencies'] = ['U-2']
        data['tasks'].append({'id': 'U-2', 'status': 'blocked'})
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'dependency'):
            self.c.plan_valid(self.plan, self.base)

    def test_unknown_preserves_call_reservation_after_restart(self):
        rid = uuid.uuid4().hex
        self.c.save(rid, 'planning', {'base_sha': self.base, 'created': time.time()})
        with patch.object(self.c, 'broker', side_effect=ConnectionError('lost after send')):
            with self.assertRaises(ConnectionError):
                self.c.invoke(rid, 'planner', 'fixture')
        self.assertEqual(self.c.status()['calls_reserved'], 1)
        restarted = m.Controller(self.cfg)
        self.addCleanup(restarted.db.close)
        with patch.object(restarted, 'broker') as broker:
            result = restarted.once()
            self.assertEqual(result['decision'], 'blocked')
            broker.assert_not_called()

    def test_budget_pause_and_sandbox_block_before_broker(self):
        rid = uuid.uuid4().hex
        with patch.object(self.c, 'broker') as broker:
            self.c.c['max_calls'] = 0
            with self.assertRaises(RuntimeError):
                self.c.invoke(rid, 'worker')
            self.c.c['max_calls'] = 20
            self.c.c['sandbox_verified'] = False
            with self.assertRaises(RuntimeError):
                self.c.invoke(rid, 'worker')
            self.c.setting('paused', True)
            with self.assertRaises(RuntimeError):
                self.c.invoke(rid, 'planner')
            broker.assert_not_called()
        self.assertEqual(self.c.status()['calls_reserved'], 0)

    def test_whole_cycle_deadline_blocks_new_stage(self):
        rid = uuid.uuid4().hex
        self.c.save(rid, 'executing', {'base_sha': self.base, 'created': time.time() - 15000})
        with patch.object(self.c, 'broker') as broker, self.assertRaisesRegex(RuntimeError, 'whole-cycle'):
            self.c.invoke(rid, 'worker')
        broker.assert_not_called()

    def test_wip_limit_rejects_claim_before_metadata_or_execution(self):
        path = self.repo / 'management/project.json'
        data = json.loads(path.read_text())
        data['wip_limit'] = 1
        data['tasks'].append({'id': 'U-2', 'status': 'blocked', 'started_at': '2026-10-30'})
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        with patch.object(self.c, 'invoke') as invoke, self.assertRaisesRegex(ValueError, 'WIP limit'):
            self.c.claim_task(uuid.uuid4().hex, self.plan)
        invoke.assert_not_called()
        self.assertEqual(path.read_bytes(), before)

    def prepare_evidence(self):
        rid = uuid.uuid4().hex
        (self.repo / 'src/a.txt').write_text('after\n')
        self.c.snapshot(rid, self.plan)
        m.dump(self.c.directory(rid) / 'tests.json', [{'argv': ['python', '-V'], 'status': 'pass', 'exit_code': 0}])
        return rid, self.c.seal(rid)

    def test_tampered_evidence_and_checksum_index_rejected(self):
        for name in ('tests.json', 'change.patch', 'checksums.json'):
            rid, sealed = self.prepare_evidence()
            (self.c.directory(rid) / name).write_text('{}')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.c.gates(rid, self.plan, self.base, sealed)

    def test_source_drift_rejected_without_overwriting_patch(self):
        rid, sealed = self.prepare_evidence()
        original = (self.c.directory(rid) / 'change.patch').read_bytes()
        (self.repo / 'src/a.txt').write_text('unreviewed\n')
        with self.assertRaises(ValueError):
            self.c.gates(rid, self.plan, self.base, sealed)
        self.assertEqual((self.c.directory(rid) / 'change.patch').read_bytes(), original)

    @unittest.skipIf(os.name == 'nt', 'Linux executable bits required')
    def test_mode_only_drift_rejected(self):
        rid, sealed = self.prepare_evidence()
        (self.repo / 'src/a.txt').chmod(0o755)
        with self.assertRaises(ValueError):
            self.c.gates(rid, self.plan, self.base, sealed)

    def test_head_drift_rejected(self):
        rid, sealed = self.prepare_evidence()
        self.c.git('commit', '--allow-empty', '-m', 'drift')
        with self.assertRaisesRegex(ValueError, 'HEAD drift'):
            self.c.gates(rid, self.plan, self.base, sealed)

    def test_scope_drift_and_new_file_in_patch(self):
        rid = uuid.uuid4().hex
        (self.repo / 'src/new.txt').write_text('new fixture\n')
        self.c.snapshot(rid, self.plan)
        self.assertIn('new fixture', (self.c.directory(rid) / 'change.patch').read_text())
        (self.repo / 'out-of-scope').write_text('bad')
        with self.assertRaisesRegex(ValueError, 'exceeds plan'):
            self.c.snapshot(rid, self.plan)

    def test_failed_validation_cannot_be_accepted(self):
        rid, _ = self.prepare_evidence()
        m.dump(self.c.directory(rid) / 'tests.json', [{'argv': ['python', '-V'], 'status': 'fail', 'exit_code': 1}])
        sealed = self.c.seal(rid)
        with self.assertRaisesRegex(ValueError, 'tests incomplete'):
            self.c.gates(rid, self.plan, self.base, sealed)

    def test_no_action_never_dispatches_worker(self):
        with patch.object(self.c, 'preflight', return_value={'head': self.base, 'issues': []}), \
             patch.object(self.c, 'invoke', return_value={'base_sha': self.base, 'decision': 'no_action', 'reason': 'empty queue'}) as invoke:
            self.assertEqual(self.c.once()['decision'], 'no_action')
        self.assertEqual([x.args[1] for x in invoke.call_args_list], ['planner'])
        self.assertEqual(self.c.git('rev-parse', 'HEAD'), self.base)

    def test_reconcile_observes_original_without_replay(self):
        rid, jid = uuid.uuid4().hex, uuid.uuid4().hex
        self.c.save(rid, 'unknown', {'base_sha': self.base, 'created': time.time()})
        self.c.db.execute('INSERT INTO calls VALUES (?,?,?,?,?)', (jid, rid, 'worker', 'reserved', '{}'))
        self.c.db.commit()
        with patch.object(self.c, 'broker', return_value={'state': 'exited', 'exit_code': 0}) as broker:
            self.assertEqual(self.c.reconcile(rid)['state'], 'unknown')
            self.assertEqual(broker.call_args.args[0], {'action': 'poll', 'job_id': jid})

    def test_failed_validation_revision_acceptance_and_explicit_commits(self):
        requests = {}
        workers = []
        validators = []
        reviews = []
        def broker(req):
            jid = req['job_id']
            if req['action'] == 'start':
                requests[jid] = req
                return {'job_id': jid}
            role = requests[jid]['role']
            code = 0
            text = ''
            if role == 'planner':
                text = json.dumps(self.plan)
            elif role == 'worker':
                workers.append(jid)
                (self.repo / 'src/a.txt').write_text('controlled attempt ' + str(len(workers)) + '\n')
                text = 'Controlled worker fixture; no real model.'
            elif role == 'validator':
                validators.append(jid)
                code = 1 if len(validators) == 1 else 0
            elif role == 'reviewer':
                reviews.append(jid)
                text = json.dumps({'decision': 'revise' if len(reviews) == 1 else 'accept',
                                   'reasons': ['Controlled test evidence'], 'evidence': ['tests.json'], 'next_task': None})
            elif role == 'finalize':
                (self.repo / 'PROJECT.md').write_text('controlled generated view')
                (self.repo / 'TASKS.md').write_text('controlled generated view')
            events = [dict(type='thread.started', thread_id=jid),
                      dict(type='item.completed', item=dict(type='agent_message', text=text)),
                      dict(type='turn.completed', usage=dict(input_tokens=1, output_tokens=1))]
            return dict(job_id=jid, state='exited', exit_code=code, stdout='\n'.join(json.dumps(e) for e in events), stderr='')
        with patch.object(self.c, 'preflight', return_value={'head': self.base, 'issues': []}), patch.object(self.c, 'broker', side_effect=broker):
            result = self.c.once()
        self.assertEqual(result.get('state'), 'accepted', result)
        self.assertEqual(len(workers), 2)
        self.assertEqual(len(validators), 2)
        self.assertEqual(len(reviews), 2)
        history = self.c.directory(result['run_id']) / 'attempt-0'
        self.assertEqual(json.loads((history / 'tests.json').read_text())[0]['exit_code'], 1)
        self.assertEqual(json.loads((self.repo / 'management/project.json').read_text())['tasks'][0]['status'], 'done')
        self.assertNotEqual(result['commit_sha'], result['management_commit_sha'])
        self.assertFalse(self.c.git('status', '--porcelain'))

    def test_same_repo_second_state_directory_cannot_take_cycle_lock(self):
        if os.name == 'nt':
            self.skipTest('Windows locking conflict raises OS error before POSIX path')
        c2 = m.Controller(dict(self.cfg, state_directory=str(Path(self.temp.name) / 'state2')))
        self.addCleanup(c2.db.close)
        with m.lock(self.repo / '.git/union-dev.lock'):
            with self.assertRaises(BlockingIOError):
                c2.once(dry=True)


class BrokerTests(unittest.TestCase):
    def test_running_original_blocks_second_container(self):
        with tempfile.TemporaryDirectory() as temp:
            broker = b.Broker({'broker_jobs': temp, 'repository': temp})
            with patch.object(b, 'docker', return_value=type('P', (), {'stdout': 'original-running'})()) as docker:
                with self.assertRaisesRegex(ValueError, 'still running'):
                    broker.request({'action': 'start', 'job_id': uuid.uuid4().hex, 'role': 'worker'})
                self.assertEqual(docker.call_count, 1)

    def test_validator_mounts_no_credentials_or_socket_and_fixes_argv(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = {'broker_jobs': temp, 'repository': '/fixture/repo', 'test_profiles': {'fixed': [['python', '-V']]}, 'image': 'sha256:fixture'}
            broker = b.Broker(cfg)
            responses = [type('P', (), {'stdout': ''})(), type('P', (), {'stdout': 'container-id'})()]
            with patch.object(b, 'docker', side_effect=responses) as docker:
                broker.request({'action': 'start', 'job_id': uuid.uuid4().hex, 'role': 'validator', 'profile': 'fixed', 'index': 0, 'argv': ['evil']})
            args = list(docker.call_args.args)
            self.assertIn('/fixture/repo/.git:/repo/.git:ro', args)
            self.assertIn('none', args)
            self.assertNotIn('/auth', ' '.join(args))
            self.assertNotIn('docker.sock', ' '.join(args))
            self.assertEqual(args[-2:], ['python', '-V'])


if __name__ == '__main__':
    unittest.main()
