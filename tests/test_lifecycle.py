import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_union.lifecycle import work_metrics
from ai_union.engine import Engine
from tests.support import init, organization, decision

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.e=init(Path(self.temp.name));organization(self.e)

    def test_dispatch_resume_and_delivery_have_persistent_host_times(self):
        w=self.e.state()['work']['w1'];self.assertEqual(w['lifecycle']['coverage'],'complete')
        with patch('ai_union.engine.now',return_value='2026-10-28T00:00:00+00:00'):
            p=self.e.begin_work('w1','fixture')
        with patch('ai_union.engine.now',return_value='2026-10-28T00:01:00+00:00'):
            self.e.finish_work(p['run_id'],{'status':'blocked','summary':'need input','artifacts':[]},{})
        with patch('ai_union.engine.now',return_value='2026-10-28T00:02:00+00:00'):
            self.e.apply_decision(decision(self.e,[{'op':'resume_work','work_id':'w1'}]),'m1','a1')
            q=self.e.begin_work('w1','fixture')
        with patch('ai_union.engine.now',return_value='2026-10-28T00:03:00+00:00'):
            self.e.finish_work(q['run_id'],{'status':'delivered','summary':'done','artifacts':[{'name':'a.md','content':'actual text'}]},{})
        data=Engine(self.e.root).state()['work']['w1']['lifecycle']
        self.assertEqual(data['first_started_at'],'2026-10-28T00:00:00+00:00')
        self.assertEqual(data['last_resumed_at'],'2026-10-28T00:02:00+00:00')
        self.assertEqual(data['last_delivered_at'],'2026-10-28T00:03:00+00:00')
        self.assertEqual(data['dispatch_count'],2)
        metrics=work_metrics(self.e.state(),at='2026-10-28T00:04:00+00:00')
        self.assertEqual(metrics['cycle_seconds']['known_count'],1)
        self.assertEqual(metrics['cycle_seconds']['mean'],180)
        self.assertNotIn('success_rate',metrics)

    def test_old_work_read_is_unchanged_and_first_change_remains_partial(self):
        with self.e.transaction() as cx:
            s=self.e._state(cx)
            for w in s['work'].values():w.pop('lifecycle',None)
            from ai_union.engine import encoded
            cx.execute('UPDATE state SET data=?',(encoded(s),))
        before=self.e.state();metrics=work_metrics(before)
        self.assertEqual(metrics['lifecycle_unknown_count'],2)
        self.assertEqual(self.e.status()['work_metrics'],metrics)
        self.assertEqual(self.e.state(),before)
        p=self.e.begin_work('w1','fixture')
        life=self.e.state()['work']['w1']['lifecycle']
        self.assertEqual(life['coverage'],'partial')
        self.assertIsNone(life['created_at'])
        self.assertIsNone(life['first_started_at'])
        self.assertEqual(life['dispatch_count'],1)

    def test_same_status_saves_do_not_rewrite_times_or_read_state(self):
        before=copy.deepcopy(self.e.state()['work'])
        self.e.configure_resources('test-key',{'max_calls':20,'timeout_seconds':30},'configured')
        self.assertEqual(self.e.state()['work'],before)
        p=self.e.begin_work('w1','fixture');self.e.fail_run(p['run_id'],'unknown',unknown=True)
        self.assertIsNotNone(self.e.state()['work']['w1']['lifecycle']['status_since'])
        before=self.e.state();self.e.status();work_metrics(before)
        self.assertEqual(before,self.e.state())
