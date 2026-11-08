import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from tests.test_core_work_registration import WorkRegistrationTests

class IndependentRegistrationReview(WorkRegistrationTests):
    def test_independent_budget_cannot_be_elevated_by_form(self):
        request=copy.deepcopy(self.original)
        request['data']['max_calls']=self.read()['au']['resources']['max_calls']+1
        status,value,_=self.request('/api/v1/work/commands',request)
        self.assertEqual(status,200,value)
        self.assertEqual(value['receipt']['status'],'rejected')
        self.assertEqual(self.read()['au']['version'],self.before)
        self.assertEqual(self.read()['au'].get('work_runtime',{}).get('works',{}),{})
        self.assertEqual(self.provider.requests,{})

    def test_independent_tool_cannot_be_elevated_by_form(self):
        request=copy.deepcopy(self.original)
        request['data']['tools']=['shell']
        status,value,_=self.request('/api/v1/work/commands',request)
        self.assertIn(status,(200,400),value)
        if status==200:self.assertEqual(value['receipt']['status'],'rejected')
        self.assertEqual(self.read()['au']['version'],self.before)
        self.assertEqual(self.read()['au'].get('work_runtime',{}).get('works',{}),{})
        self.assertEqual(self.provider.requests,{})

    def test_independent_same_id_different_payload_cannot_replace_original_work(self):
        status,value,_=self.request('/api/v1/work/commands',self.original)
        self.assertEqual(status,200,value)
        self.assertEqual(value['receipt']['status'],'succeeded')
        original=value['receipt']
        conflict=copy.deepcopy(self.original);conflict['data']['goal']='replacement goal'
        status,value,_=self.request('/api/v1/work/commands',conflict)
        self.assertIn(status,(400,409),value)
        self.assertEqual(self.receipt()[1]['receipt'],original)
        state=self.read()['au']
        self.assertEqual(state['version'],self.before+1)
        self.assertEqual(len(state['work_runtime']['works']),1)
        self.assertEqual(next(iter(state['work_runtime']['works'].values()))['goal'],self.original['data']['goal'])
        self.assertEqual(self.provider.requests,{})

suite=unittest.TestSuite(IndependentRegistrationReview(name) for name in unittest.defaultTestLoader.getTestCaseNames(IndependentRegistrationReview) if name.startswith('test_independent_'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
