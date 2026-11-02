import unittest
from ai_union.engine import Rejected


class ContextTests(unittest.TestCase):
    def test_trim_keeps_authority_current_work_and_tool_pairs(self):
        from ai_union.model_context import prepare_context
        messages=[{'role':'system','content':'authority'}, {'role':'user','content':'current work'},
            {'role':'assistant','content':'old'*3000,'tool_calls':[{'id':'old-call','function':{'name':'read','arguments':'{}'}}]},
            {'role':'tool','tool_call_id':'old-call','content':'old result'}, {'role':'user','content':'continue'}]
        body,report=prepare_context({'model':'unknown','context_policy':{'window':2000,'strategy':'trim_history'},'max_output_tokens':100}, {'messages':messages})
        self.assertEqual(body['messages'][:2],messages[:2])
        self.assertEqual(body['messages'][-1],messages[-1])
        self.assertEqual(report['dropped_messages'],2)
        self.assertNotIn('old result',str(body))

    def test_oversized_current_work_and_unknown_multimodal_are_rejected(self):
        from ai_union.model_context import prepare_context
        with self.assertRaises(Rejected):
            prepare_context({'model':'unknown','max_output_tokens':100,'context_policy':{'window':1000}}, {'messages':[{'role':'system','content':'authority'},{'role':'user','content':'x'*2000}]})
        with self.assertRaisesRegex(Rejected,'能力'):
            prepare_context({'model':'no-such-model','max_output_tokens':100}, {'messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,AAAA'}}]}]})

    def test_orphan_tool_result_is_rejected(self):
        from ai_union.model_context import prepare_context
        with self.assertRaises(Rejected):
            prepare_context({'model':'unknown','max_output_tokens':100},{'messages':[{'role':'tool','tool_call_id':'missing','content':'result'}]})
