import json
import tempfile
import unittest
from pathlib import Path

from ai_union.diagnostics import decision_diagnostics
from ai_union.engine import Rejected, encoded
from ai_union.agent_protocol import model_input
from tests.support import init, organization


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(Path(self.temp.name), max_calls=100)
        organization(self.e)

    def test_history_excludes_private_material_and_reconstructs_failure(self):
        p = self.e.begin_work('w1', 'fixture')
        self.e.fail_run(p['run_id'], 'PRIVATE raw output /root/secret', failure={'code':'api_timeout','message':'PRIVATE injected','recovery':'PRIVATE injected'})
        with self.e.transaction() as cx:
            cx.execute('UPDATE runs SET usage=? WHERE id=?', (encoded({'input_tokens':12,'output_tokens':3,'actual_model':'PRIVATE','api_key':'PRIVATE','cost':0}),p['run_id']))
        before = self.e.state()
        with self.e.read_transaction() as cx:
            result = decision_diagnostics(self.e, cx, before)
        raw = json.dumps(result)
        self.assertNotIn('PRIVATE', raw)
        self.assertNotIn('package', raw)
        self.assertEqual(result['recent_runs'][0]['failure']['code'], 'api_timeout')
        self.assertEqual(result['recent_runs'][0]['usage'], {'input_tokens':12,'output_tokens':3,'cost':None,'cost_status':'unknown'})
        self.assertEqual(self.e.state(), before)
        self.assertEqual(self.e.status()['budget']['calls_reserved'], 1)

    def test_history_is_bounded_and_ordinary_work_has_no_diagnostics(self):
        for _ in range(15):
            p = self.e.begin_decision('fixture')
            self.e.fail_run(p['run_id'], 'private')
        with self.e.read_transaction() as cx:
            data = decision_diagnostics(self.e, cx, self.e._state(cx))
        self.assertEqual(len(data['recent_runs']),12)
        self.assertEqual(data['run_count'],15)
        self.assertTrue(data['runs_truncated'])
        self.assertEqual(data['recent_runs'][0]['id'],p['run_id'])
        p = self.e.begin_work('w1','fixture')
        self.assertNotIn('diagnostics',model_input(p)['context'])
        self.e.finish_work(p['run_id'],{'status':'blocked','summary':'need input','artifacts':[]},{})
        q = self.e.begin_decision('fixture')
        self.assertEqual(len(model_input(q)['context']['diagnostics']['recent_runs']),12)

    def test_bootstrap_not_given_history_and_invalid_limits_rejected(self):
        other = init(Path(self.temp.name)/'other')
        self.assertNotIn('diagnostics',model_input(other.begin_decision('fixture'))['context'])
        for limit in (0,31,True):
            with self.e.read_transaction() as cx:
                with self.assertRaises(Rejected):decision_diagnostics(self.e,cx,self.e._state(cx),limit=limit)

    def test_artifact_references_omit_text_paths_and_unknown_fields(self):
        p = self.e.begin_work('w1','fixture')
        self.e.finish_work(p['run_id'],{'status':'delivered','summary':'PRIVATE','artifacts':[{'name':'private-name.md','content':'PRIVATE content'}]},{})
        with self.e.read_transaction() as cx:
            data = decision_diagnostics(self.e,cx,self.e._state(cx))
        self.assertEqual(data['artifact_count'],1)
        self.assertEqual(data['recent_artifacts'][0]['work_id'],'w1')
        self.assertNotIn('PRIVATE',json.dumps(data))
        self.assertNotIn('path',json.dumps(data))
        self.assertNotIn('private-name',json.dumps(data))

    def test_legacy_decision_failure_scalars_do_not_break_future_context(self):
        from tests.support import decision
        for value in (42, True, "not-json-text", ["not-object"]):
            p = self.e.begin_decision('fixture')
            d = decision(self.e, [{'op':'record_memory','content':'hypothesis','conditions':'test','uncertainty':'unknown'}], failure=value)
            self.e.finish_decision(p['run_id'], d, {})
            history = self.e.context()['context']['diagnostics']['recent_runs']
            self.assertNotIn('failure', history[0])
