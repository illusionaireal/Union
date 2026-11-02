import copy
import unittest
from ai_union.engine import Rejected
from ai_union.model_billing import allocate, vouchers
from tests import test_model_api as api_tests


class CostAllocationTests(unittest.TestCase):
    setUp=api_tests.ModelAPITests.setUp
    command=api_tests.ModelAPITests.command
    configure=api_tests.ModelAPITests.configure
    probe=api_tests.ModelAPITests.probe

    def test_period_allocation_preserves_original_usage_and_is_idempotent(self):
        self.configure(dict(self.config,billing={'basis':'subscription','currency':'USD','revision':'plan-1'}))
        self.provider.outputs=[{'ok':True},{'ok':True}]
        self.probe();self.probe()
        runs=self.e.runs(); before=copy.deepcopy(runs)
        self.assertEqual(runs[0]['usage']['cost_basis'],'subscription')
        self.assertIsNone(runs[0]['usage']['cost_minor'])
        voucher={'id':'allocation-1','basis':'subscription','currency':'USD','period':'2026-11','amount_minor':5,'run_ids':[r['id'] for r in runs]}
        key=(self.e.root/'board.key').read_text(encoding='utf-8').strip()
        result=allocate(self.e,key,voucher,'subscription invoice fixture')
        self.assertEqual(sum(result['allocations'].values()),5)
        self.assertEqual(allocate(self.e,key,voucher,'same invoice'),result)
        self.assertEqual(self.e.runs(),before)
        with self.assertRaises(Rejected):allocate(self.e,key,dict(voucher,id='second'), 'duplicate invoice')
        self.assertEqual(len(vouchers(self.e)),1)

    def test_metered_estimate_is_recomputed_from_recorded_connection_version(self):
        self.configure(dict(self.config,billing={'basis':'metered','currency':'CNY','revision':'price-1','input_per_million_minor':10000,'output_per_million_minor':10000}))
        self.probe()
        usage=self.e.runs()[-1]['usage']
        self.assertEqual(usage['cost_minor'],1);self.assertEqual(usage['currency'],'CNY')
        self.assertEqual(usage['billing_revision'],'price-1')
        self.assertEqual(usage['cost_status'],'estimated')

    def test_owned_period_uses_measured_elapsed_weight(self):
        self.configure(dict(self.config,billing={'basis':'owned','currency':'CNY','revision':'host-1'}))
        self.provider.delay=0.05
        self.probe();run=self.e.runs()[-1]
        self.assertGreater(run['usage']['elapsed_ms'],0)
        key=(self.e.root/'board.key').read_text(encoding='utf-8').strip()
        voucher={'id':'host-allocation','basis':'owned','currency':'CNY','period':'2026-11','amount_minor':3,'run_ids':[run['id']]}
        result=allocate(self.e,key,voucher,'measured host period fixture')
        self.assertEqual(result['allocations'],{run['id']:3})
