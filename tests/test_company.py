import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_union.console import Console
from ai_union.engine import Engine, Rejected, OPERATIONS
from ai_union.company import create, totals, view
from ai_union.novel_demo import NovelDemoExecutor, CONFIG
from ai_union.runner import run, step
from ai_union.observation import snapshot
from ai_union.evaluation import evaluate
from tests.support import CHARTER, decision


class CompanyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.charter = copy.deepcopy(CHARTER)
        self.charter['allowed_operations'] = sorted(OPERATIONS)
        self.e = Engine.create(Path(self.temp.name) / 'org', 'test novel', '连续交付同一本小说三章', self.charter,
                               {'max_calls': 32, 'timeout_seconds': 30}, 'test board', 'test-key')
        with self.e.transaction() as cx:
            s = self.e._state(cx)
            s['company'] = create(CONFIG)
            self.e._save(cx, s)
        self.executor = NovelDemoExecutor()

    def proposal(self, ops, refs):
        return decision(self.e, ops, evidence_refs=refs)

    def apply(self, ops, refs=()):
        return self.e.apply_decision(self.proposal(ops, list(refs)), 'planner', 'a-planner')

    def first_chapter(self):
        result = run(self.e, self.executor, 4)
        self.assertNotEqual(result[-1]['action'], 'blocked', result)
        return self.e.state()['company']['chapters'][0]

    def test_three_cycles_persist_cross_member_feedback_and_stop(self):
        actions = run(self.e, self.executor, 30)
        self.assertEqual(actions[-1]['action'], 'wait', actions)
        reopened = Engine(self.e.root)
        c = snapshot(reopened)['company']
        self.assertTrue(c['completed'])
        self.assertEqual(len(c['chapters']), 3)
        self.assertEqual([ch['subscriptions'] for ch in c['chapters']], [12, 2, 8])
        self.assertEqual(c['totals']['income_minor'], 660)
        self.assertEqual(c['totals']['operating_cost_minor'], 101)
        self.assertEqual(len(c['ledger']), len(self.e.runs()) + 9)
        self.assertEqual(c['feedback_actions'][1]['delivered_work_ids'], ['chapter-3'])
        task = next(r for r in reopened.runs() if r['work_id'] == 'chapter-3')
        self.assertIn('十秒限时', task['package']['context']['task']['instruction'])
        self.assertEqual(len(task['package']['context']['company']['published_texts']), 2)
        self.assertFalse(evaluate(reopened)['real_agent_verified'])
        self.assertTrue(evaluate(reopened)['mechanism_scenario_passed'])
        before = len(reopened.runs())
        run(reopened, self.executor, 10)
        self.assertEqual(len(reopened.runs()), before)
        state = reopened.state()
        for ch in c['chapters']:
            self.assertGreaterEqual(len(reopened._read_artifact(state['artifacts'][ch['artifact_id']])), 800)

    def test_submission_is_idempotent_and_atomic_with_feedback(self):
        ch = self.first_chapter()
        op = {'op': 'submit_chapter', 'chapter_number': 1, 'artifact_id': ch['artifact_id'], 'title': ch['title'], 'book_title': '借来的明天'}
        before = copy.deepcopy(self.e.state()['company'])
        self.apply([op], [ch['artifact_id']])
        self.assertEqual(before, self.e.state()['company'])
        with self.assertRaises(Rejected):
            self.apply([op | {'title': 'changed'}], [ch['artifact_id']])
        self.assertEqual(len([e for e in self.e.events() if e['kind'] == 'novel_feedback']), 1)
        # Invalid operation after posting must roll back the publication and its settlement.
        with tempfile.TemporaryDirectory() as temp:
            other = Engine.create(temp, 'x', 'x', self.charter, {'max_calls': 32, 'timeout_seconds': 30}, 'b', 'k')
            with other.transaction() as cx:
                state = other._state(cx); state['company'] = create(CONFIG); other._save(cx, state)
            run(other, self.executor, 3)
            aid = other.state()['work']['chapter-1']['artifact_ids'][0]
            proposal = decision(other, [op | {'artifact_id': aid}, {'op': 'wait', 'until': 'invalid', 'reason': 'test'}], evidence_refs=[aid])
            with self.assertRaises(Rejected):
                other.apply_decision(proposal, 'planner', 'a-planner')
            self.assertEqual(other.state()['company']['chapters'], [])
            self.assertFalse(any(e['kind'] == 'novel_feedback' for e in other.events()))
            self.assertFalse(any(r['kind'] == 'subscription' for r in other.state()['company']['ledger']))

    def test_feedback_requires_new_action_and_cannot_be_written_by_agent(self):
        ch = self.first_chapter()
        review = {'op': 'review_cycle', 'chapter_number': 1, 'response': '只有反思', 'next_work_ids': []}
        with self.assertRaises(Rejected):
            self.apply([review], [ch['feedback_event_id']])
        with self.assertRaises(Rejected):
            self.apply([review | {'next_work_ids': ['chapter-1']}], [ch['feedback_event_id']])
        with self.assertRaises(Rejected):
            self.apply([{'op': 'change_revenue', 'amount': 100000}])
        self.assertEqual(self.e.state()['company']['platform']['subscriptions'], [12, 2, 8])

    def test_charter_revocation_blocks_submission_without_ledger_changes(self):
        run(self.e, self.executor, 3)
        charter = copy.deepcopy(self.charter); charter['allowed_operations'].remove('submit_chapter')
        self.e.amend('test-key', charter, 'revoke publication')
        before = self.e.state()['company']
        result = run(self.e, self.executor, 1)
        self.assertEqual(result[-1]['action'], 'blocked')
        self.assertEqual(self.e.state()['company']['chapters'], [])
        self.assertEqual(len(self.e.state()['company']['ledger']), len(before['ledger']) + 1)  # Failed model call still costs.

    def test_budget_missing_usage_and_rounding_are_conservative(self):
        with self.e.transaction() as cx:
            state = self.e._state(cx); state['company']['config']['initial_budget_minor'] = 1; self.e._save(cx, state)
        run(self.e, self.executor, 30)
        self.assertEqual(len(self.e.runs()), 1)
        self.assertIn('预算', snapshot(self.e)['budget']['blocked_reason'])
        self.assertEqual(totals(self.e.state()['company'])['model_estimate_minor'], 1)
        self.assertEqual(totals(self.e.state()['company'])['balance_minor'], 0)

    def test_unknown_usage_never_counts_as_zero_and_duplicate_result_never_charges_twice(self):
        package = self.e.begin_decision('api', {'transport_source': 'provider_api'})
        result, _ = self.executor.execute(package)
        self.e.finish_decision(package['run_id'], result, {})
        self.e.finish_decision(package['run_id'], result, {})
        c = self.e.state()['company']
        self.assertEqual(len(c['ledger']), 1)
        self.assertIsNone(c['ledger'][0]['amount_minor'])
        self.assertEqual(c['ledger'][0]['source'], 'provider_usage_estimate')
        self.assertIn('用量缺失', snapshot(self.e)['budget']['blocked_reason'])

    def test_feedback_preempts_preplanned_work(self):
        ch = self.first_chapter()
        self.apply([{'op': 'create_work', 'id': 'premature', 'title': 'future', 'instruction': 'preplanned', 'position_id': 'writing', 'dependencies': []}])
        package = []
        class Capture:
            name = 'fixture'
            def execute(inner, p):
                package.append(p)
                return self.executor.execute(p)
        run(self.e, Capture(), 1)
        self.assertEqual(package[0]['kind'], 'decision')
        self.assertEqual(self.e.state()['work']['premature']['status'], 'pending')

    def test_company_configuration_is_scoped_and_validated_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Console(directory, fixture=[])
            try:
                board = app.new_session('board'); observer = app.new_session('observer')
                req = {'id': 'create-company', 'organization_id': None, 'base_version': None, 'kind': 'create', 'data': {
                    'name': 'company', 'goal': 'novel', 'board_name': 'b', 'charter': self.charter,
                    'resources': {'max_calls': 32, 'timeout_seconds': 30}, 'company': CONFIG}}
                with self.assertRaises(Rejected): app.command(observer, req)
                receipt = app.command(board, req)
                self.assertEqual(receipt['status'], 'succeeded')
                self.assertEqual(app.command(board, req), receipt)
                self.assertEqual(app.observe(board, receipt['organization_id'])['company']['target_cycles'], 3)
                req['id'] = 'bad'; req['data']['company'] = CONFIG | {'initial_budget_minor': True}
                self.assertEqual(app.command(board, req)['status'], 'rejected')
                self.assertEqual(len(app.organizations()), 1)
            finally:
                app.close()

    def test_old_artifact_cannot_pass_as_post_negative_feedback_delivery(self):
        run(self.e, self.executor, 7)  # Cycle 2 submitted; negative feedback now available.
        state = self.e.state(); feedback = state['company']['chapters'][1]['feedback_event_id']
        # Manufacture a pre-feedback manuscript, then reopen its task in the review.
        self.apply([self.executor.work(3, ['chapter-2'])])
        package = self.e.begin_work('chapter-3', 'fixture')
        result, usage = self.executor.execute(package)
        self.e.finish_work(package['run_id'], result, usage)
        old_artifact = self.e.state()['work']['chapter-3']['artifact_ids'][-1]
        self.apply([{'op': 'update_work', 'work_id': 'chapter-3', 'title': '改写第三章', 'instruction': '落实负面反馈，冲突前置', 'dependencies': ['chapter-2']},
                    {'op': 'review_cycle', 'chapter_number': 2, 'response': '反馈后改写', 'next_work_ids': ['chapter-3']}], [feedback])
        package = self.e.begin_work('chapter-3', 'fixture')
        result, usage = self.executor.execute(package)
        self.e.finish_work(package['run_id'], result, usage)
        op = {'op': 'submit_chapter', 'artifact_id': old_artifact, 'chapter_number': 3, 'book_title': '借来的明天', 'title': 'old'}
        with self.assertRaisesRegex(Rejected, '当前已完成工作版本'):
            self.apply([op], [old_artifact])
        self.assertEqual(len(self.e.state()['company']['chapters']), 2)
        new_artifact = self.e.state()['work']['chapter-3']['artifact_ids'][-1]
        self.apply([op | {'artifact_id': new_artifact, 'title': 'new'}], [new_artifact])
        self.assertEqual(len(self.e.state()['company']['chapters']), 3)

    def test_feedback_collision_rolls_back_entire_publication(self):
        run(self.e, self.executor, 3)
        self.e.add_event('occupied-feedback', 'external_feedback', {'source': 'board', 'simulated': True})
        with patch('ai_union.company.uid', return_value='occupied-feedback'):
            result = run(self.e, self.executor, 1)
        self.assertEqual(result[-1]['action'], 'blocked')
        self.assertEqual(self.e.state()['company']['chapters'], [])
        self.assertFalse(any(row['kind'] == 'subscription' for row in self.e.state()['company']['ledger']))

    def test_board_can_resolve_missing_usage_after_failed_probe_without_erasing_history(self):
        from ai_union.company import resolve_usage
        package = self.e.begin_connection_test({'transport_source': 'provider_api'})
        self.e.fail_run(package['run_id'], 'provider rejected request', usage={})
        self.assertIn('用量缺失', snapshot(self.e)['budget']['blocked_reason'])
        with self.assertRaises(Rejected):
            resolve_usage(self.e, 'wrong-key', package['run_id'], 0, 0, 'provider confirmed no charge')
        resolve_usage(self.e, 'test-key', package['run_id'], 0, 0, 'provider receipt confirms no charge')
        self.assertIsNone(snapshot(self.e)['budget']['blocked_reason'])
        row = self.e.state()['company']['ledger'][0]
        self.assertEqual(row['source'], 'board_usage_estimate')
        self.assertEqual(row['amount_minor'], 0)
        self.assertIsNone(row['original_usage']['input_tokens'])
        self.assertEqual(self.e.runs()[0]['status'], 'failed')
        self.assertNotIn('input_tokens', self.e.runs()[0]['usage'])
        with self.assertRaises(Rejected):
            resolve_usage(self.e, 'test-key', package['run_id'], 0, 0, 'duplicate correction')
        self.assertEqual(len(self.e.state()['company']['ledger']), 1)
        self.assertEqual(len([e for e in self.e.events() if e['kind'] == 'company_usage_reconciled']), 1)
        run(self.e, self.executor, 1)
        self.assertEqual(len(self.e.runs()), 2)

    def test_unreviewed_feedback_remains_actionable_even_when_event_was_consumed(self):
        self.first_chapter()
        with self.e.transaction() as cx:
            cx.execute('UPDATE events SET consumed=1')
        actions = run(self.e, self.executor, 1)
        self.assertEqual(actions[0]['action'], 'decision')
        self.assertEqual(len(self.e.state()['company']['reviews']), 1)

    def test_http_api_three_cycle_execution_and_private_connection_binding(self):
        import threading
        from http.server import ThreadingHTTPServer
        from tests.novel_browser_host import NovelProvider
        provider = ThreadingHTTPServer(('127.0.0.1', 0), NovelProvider)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        self.addCleanup(thread.join); self.addCleanup(provider.server_close); self.addCleanup(provider.shutdown)
        app = Console(Path(self.temp.name) / 'http-console', fixture=[])
        self.addCleanup(app.close)
        board = app.new_session('board'); count = 0
        def command(kind, data, org=None):
            nonlocal count
            count += 1
            return app.command(board, {'id': f'http-{count}', 'kind': kind, 'organization_id': org,
                                       'base_version': app.engine(board, org).state()['version'] if org else None, 'data': data})
        receipt = command('create', {'name': 'API company', 'goal': 'three chapters', 'board_name': 'test board', 'charter': self.charter,
                                    'resources': {'max_calls': 32, 'timeout_seconds': 30}, 'company': CONFIG})
        org = receipt['organization_id']; engine = app.engine(board, org)
        cfg = {'name': 'local HTTP double', 'base_url': f'http://127.0.0.1:{provider.server_port}/v1', 'model': 'test-model', 'response_format': 'json_schema',
               'token_limit_field': 'max_completion_tokens', 'max_output_tokens': 8192, 'timeout_seconds': 10, 'enabled': True}
        key = 'never-a-real-key-novel-test'
        saved = command('api_connection', {'connection_id': 'primary', 'config': cfg, 'api_key': key, 'bind_default': True, 'reason': 'test'}, org)
        self.assertEqual(saved['status'], 'succeeded')
        self.assertEqual(app.observe(board, org)['execution_config']['api_connection_id'], 'primary')
        self.assertNotIn(key, json.dumps(saved) + json.dumps(app.model_connections(board, org)))
        with engine.read_transaction() as cx:
            self.assertFalse(any(key in r[0] for r in cx.execute('SELECT payload FROM commands')))
        probe = command('api_test', {'allow_unknown_cost': True}, org); app.join_jobs()
        self.assertEqual(app.receipt(board, org, probe['id'])['status'], 'succeeded')
        started = command('start', {'executor': 'api', 'max_steps': 30, 'allow_unknown_cost': True}, org); app.join_jobs()
        self.assertEqual(app.receipt(board, org, started['id'])['status'], 'succeeded')
        snap = app.observe(board, org)
        self.assertTrue(snap['company']['completed'])
        self.assertTrue(all(r['executor'] == 'api' and r['simulated'] for r in snap['runs']))
        self.assertEqual(len(snap['runs']), 12)
        self.assertEqual(snap['source'], 'fixture')
        self.assertTrue(all(row['source'] == 'simulated_usage' for row in snap['company']['ledger'] if row['kind'] == 'model'))
        self.assertFalse(evaluate(engine)['real_agent_verified'])
