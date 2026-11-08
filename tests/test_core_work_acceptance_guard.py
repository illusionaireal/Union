"""The acceptance evidence must reject a run that proves nothing.

Review finding on #22: an acceptance script may not pass on zero calls, zero document
reads or zero results, and a failed original-request lookup may not be counted as a
successful cancellation. These checks run offline against synthetic payloads.
"""
import unittest

from tests.test_core_work_real import acceptance_problems


def work(calls=1, results=1, tools=None, usage=None, cost="unknown"):
    return {
        "budget": {"max_calls": 2, "reserved": 0, "used": calls},
        "usage": usage if usage is not None else {"input_tokens": 396, "output_tokens": 29},
        "cost_status": cost,
        "tool_calls": tools if tools is not None else [{"tool": "list_documents", "count": 2}],
        "results": [{"id": "result-%d" % index, "status": "candidate"} for index in range(results)],
    }


def receipt(status="succeeded", turns=1, result=True):
    return {"status": status, "turns": turns, "result": result, "usage": {"input_tokens": 396, "output_tokens": 29}}


class AcceptanceGuardTests(unittest.TestCase):
    def test_a_real_shaped_run_reports_no_problem(self):
        self.assertEqual(acceptance_problems(work(), receipt(), 512), [])

    def test_a_zero_call_run_cannot_pass(self):
        problems = acceptance_problems(work(calls=0), receipt(turns=0, result=False), 512)
        self.assertTrue(problems, "a run without any call must be rejected")
        self.assertTrue(any("调用" in item for item in problems), problems)

    def test_a_run_without_any_document_read_cannot_pass(self):
        problems = acceptance_problems(work(tools=[{"tool": "list_documents", "count": 0}]), receipt(), 512)
        self.assertTrue(any("资料" in item for item in problems), problems)

    def test_a_run_without_a_result_cannot_pass(self):
        problems = acceptance_problems(work(results=0), receipt(result=False), 512)
        self.assertTrue(any("成果" in item for item in problems), problems)

    def test_unknown_cost_is_required_and_zero_usage_is_suspicious(self):
        problems = acceptance_problems(work(usage={"input_tokens": 0, "output_tokens": 0}), receipt(), 512)
        self.assertTrue(any("用量" in item for item in problems), problems)
        problems = acceptance_problems(work(cost="estimated"), receipt(), 512)
        self.assertTrue(any("费用" in item for item in problems), problems)

    def test_a_read_document_call_must_carry_a_digest(self):
        problems = acceptance_problems(work(tools=[{"tool": "read_document", "sha256": None, "bytes": None}]),
                                       receipt(), 512)
        self.assertTrue(any("摘要" in item for item in problems), problems)


if __name__ == "__main__":
    unittest.main()
